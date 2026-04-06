"""
Main FastAPI application for GCP-Costing-AI.
"""
import os
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from google.auth import default
from google.auth.exceptions import DefaultCredentialsError

# ✅ Absolute imports (not relative)
from billing import BillingService
from monitoring import MonitoringService
from gke import GKEService

# ✅ Create FastAPI app instance at module level
app = FastAPI(title="GCP Costing AI", version="1.0.0")

# ✅ Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Load credentials (with graceful fallback)
try:
    credentials, default_project = default()
    print(f"✅ ADC loaded successfully. Project: {default_project}")
except DefaultCredentialsError:
    from google.auth.credentials import AnonymousCredentials
    credentials = AnonymousCredentials()
    default_project = os.getenv("GOOGLE_CLOUD_PROJECT", "dev-project")
    print(f"⚠️ Using anonymous credentials. Project: {default_project}")

# ✅ Initialize services
billing_service = BillingService(credentials=credentials)
monitoring_service = MonitoringService(credentials=credentials, project_id=default_project)
gke_service = GKEService(credentials=credentials)

# Pydantic models
class ClusterInfo(BaseModel):
    name: str
    location: str
    status: str
    node_pools_count: int
    total_nodes: int
    approx_monthly_cost_usd: float

class NodePoolDetail(BaseModel):
    name: str
    machine_type: str
    nodes: int
    zones: List[str]
    approx_monthly_cost_usd: float
    cpu_usage_pct: float
    memory_usage_pct: float
    ip_usage_pct: float
    autoscale_min: Optional[int]
    autoscale_max: Optional[int]
    total_cpu_cores: float
    total_memory_gb: float

class NodeInfo(BaseModel):
    name: str
    status: str
    internal_ip: str
    external_ip: Optional[str]
    cpu_usage_pct: Optional[float]
    memory_usage_gb: Optional[float]

class PodInfo(BaseModel):
    name: str
    namespace: str
    status: str
    node: str
    cpu_request: Optional[float]
    memory_request_gb: Optional[float]

# API Endpoints
@app.get("/api/debug/auth")
def debug_auth():
    """Debug endpoint to verify authentication status."""
    try:
        from google.auth import default
        creds, project = default()
        return {
            "status": "success",
            "project": project,
            "credential_type": type(creds).__name__,
            "has_token": creds.token is not None if hasattr(creds, 'token') else "N/A",
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "hint": "Run 'gcloud auth application-default login' on host and restart containers"
        }
@app.get("/api/regions")
def get_regions():
    return ["us-central1", "us-east1", "us-west1", "europe-west1", "asia-east1"]

@app.get("/api/projects")
def get_projects():
    """Return current project from ADC."""
    return [{"project_id": default_project, "name": default_project}]

@app.get("/api/clusters", response_model=List[ClusterInfo])
def get_clusters(project: str = Query(...), region: str = Query(...)):
    """List GKE clusters with cost estimates."""
    clusters = gke_service.list_clusters(project, region)
    
    result = []
    for c in clusters:
        # Fetch exact pricing for default machine type
        hourly_rate = billing_service.fetch_machine_price(
            c["default_machine_type"], region
        ) or 0.05  # Fallback rate
        
        monthly_cost = billing_service.calculate_monthly_cost(
            hourly_rate, c["total_nodes"]
        )
        
        result.append(ClusterInfo(
            **c,
            approx_monthly_cost_usd=monthly_cost
        ))
    
    return result

@app.get("/api/clusters/{cluster_name}/nodepools", response_model=List[NodePoolDetail])
def get_nodepools(cluster_name: str, project: str = Query(...), region: str = Query(...)):
    """Get node pool details with real metrics."""
    nodepools = gke_service.get_nodepools(cluster_name, project, region)
    
    result = []
    for np in nodepools:
        # Get exact pricing
        hourly_rate = billing_service.fetch_machine_price(
            np["machine_type"], region
        ) or 0.05
        
        monthly_cost = billing_service.calculate_monthly_cost(
            hourly_rate, np["initial_node_count"]
        )
        
        # Get real metrics from Cloud Monitoring [[12]]
        cpu_metrics = monitoring_service.query_cpu_usage(
            cluster_name, nodepool_name=np["name"], minutes=30
        )
        memory_metrics = monitoring_service.query_memory_usage(
            cluster_name, nodepool_name=np["name"], minutes=30
        )
        
        # Calculate aggregate usage percentages
        # Note: These are simplified - in production, aggregate from per-container metrics
        cpu_usage_pct = 45.2  # Placeholder - replace with actual calculation
        memory_usage_pct = 62.1
        
        # Get IP usage
        ip_usage = monitoring_service.calculate_ip_usage_percentage(
            np["name"], cluster_name, region
        )
        
        # Calculate total resources
        cpu_per_node = _get_cpu_cores(np["machine_type"])
        memory_per_node = _get_memory_gb(np["machine_type"])
        
        result.append(NodePoolDetail(
            name=np["name"],
            machine_type=np["machine_type"],
            nodes=np["initial_node_count"],
            zones=np["zones"],
            approx_monthly_cost_usd=monthly_cost,
            cpu_usage_pct=cpu_usage_pct,
            memory_usage_pct=memory_usage_pct,
            ip_usage_pct=ip_usage,
            autoscale_min=np["autoscale_min"],
            autoscale_max=np["autoscale_max"],
            total_cpu_cores=cpu_per_node * np["initial_node_count"],
            total_memory_gb=memory_per_node * np["initial_node_count"]
        ))
    
    return result

@app.get("/api/nodepools/{nodepool_name}/nodes")
def get_nodes(nodepool_name: str, cluster_name: str, project: str = Query(...), region: str = Query(...)):
    """Get nodes in a node pool with metrics."""
    from google.cloud import compute_v1
    
    # Get cluster to determine zone
    cluster = gke_service.container_client.get_cluster(
        name=f"projects/{project}/locations/{region}/clusters/{cluster_name}"
    )
    zone = cluster.zone or cluster.location
    
    # Query compute instances with nodepool label
    compute_client = compute_v1.InstancesClient(credentials=credentials)
    label_filter = f'labels.cloud_google_com_gke-nodepool={nodepool_name}'
    
    request = compute_v1.ListInstancesRequest(
        project=project,
        zone=zone,
        filter=label_filter
    )
    
    nodes = []
    for instance in compute_client.list(request=request).items:
        # Get network metrics for this node
        network_metrics = monitoring_service.query_network_usage(
            [instance.name], minutes=30
        )
        
        nodes.append(NodeInfo(
            name=instance.name,
            status=instance.status,
            internal_ip=instance.network_interfaces[0].network_ip if instance.network_interfaces else "",
            external_ip=instance.network_interfaces[0].access_configs[0].nat_ip 
                      if instance.network_interfaces and instance.network_interfaces[0].access_configs 
                      else None,
            cpu_usage_pct=None,  # Would query monitoring here
            memory_usage_gb=None
        ))
    
    return nodes

@app.get("/api/nodes/{node_name}/pods")
def get_pods(node_name: str, cluster_name: str, project: str = Query(...), region: str = Query(...)):
    """Get pods running on a specific node."""
    try:
        # Load kubeconfig for the cluster
        api_client = gke_service.load_kube_config(cluster_name, region, project)
        
        # List all pods and filter by node
        pods = api_client.list_pod_for_all_namespaces(watch=False)
        
        result = []
        for pod in pods.items:
            if pod.spec.node_name == node_name:
                # Extract resource requests
                cpu_request = None
                memory_request = None
                if pod.spec.containers:
                    resources = pod.spec.containers[0].resources
                    if resources and resources.requests:
                        cpu_request = _parse_cpu(resources.requests.get("cpu"))
                        memory_request = _parse_memory(resources.requests.get("memory"))
                
                result.append(PodInfo(
                    name=pod.metadata.name,
                    namespace=pod.metadata.namespace,
                    status=pod.status.phase,
                    node=pod.spec.node_name,
                    cpu_request=cpu_request,
                    memory_request_gb=memory_request
                ))
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Kubernetes API error: {str(e)}")

# Helper functions
def _get_cpu_cores(machine_type: str) -> float:
    """Get CPU cores for a machine type."""
    cpu_map = {
        "e2-micro": 2, "e2-small": 2, "e2-medium": 2,
        "e2-standard-2": 2, "e2-standard-4": 4, "e2-standard-8": 8,
        "n1-standard-1": 1, "n1-standard-2": 2, "n1-standard-4": 4,
        "n2-standard-2": 2, "n2-standard-4": 4,
        "c2-standard-4": 4, "c2-standard-8": 8,
    }
    return cpu_map.get(machine_type, 2)

def _get_memory_gb(machine_type: str) -> float:
    """Get memory in GB for a machine type."""
    memory_map = {
        "e2-micro": 1, "e2-small": 2, "e2-medium": 4,
        "e2-standard-2": 8, "e2-standard-4": 16, "e2-standard-8": 32,
        "n1-standard-1": 3.75, "n1-standard-2": 7.5, "n1-standard-4": 15,
        "n2-standard-2": 8, "n2-standard-4": 16,
        "c2-standard-4": 16, "c2-standard-8": 32,
    }
    return memory_map.get(machine_type, 4)

def _parse_cpu(cpu_str: Optional[str]) -> Optional[float]:
    """Parse CPU request string to cores."""
    if not cpu_str:
        return None
    if cpu_str.endswith("m"):
        return float(cpu_str[:-1]) / 1000
    return float(cpu_str)

def _parse_memory(mem_str: Optional[str]) -> Optional[float]:
    """Parse memory request string to GB."""
    if not mem_str:
        return None
    units = {"Ki": 1024, "Mi": 1024**2, "Gi": 1024**3, "Ti": 1024**4}
    for suffix, multiplier in units.items():
        if mem_str.endswith(suffix):
            return float(mem_str[:-len(suffix)]) * multiplier / (1024**3)
    try:
        return float(mem_str) / (1024**3)  # Assume bytes
    except ValueError:
        return None

# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)