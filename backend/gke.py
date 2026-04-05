"""
GKE cluster and node pool operations using Cloud Container API.
"""
from google.cloud import container_v1
from google.auth import default
from google.api_core import exceptions
from typing import List, Dict, Optional
import kubernetes
import kubernetes.config

class GKEService:
    def __init__(self, credentials=None):
        self.credentials = credentials or default()[0]
        self.container_client = container_v1.ClusterManagerClient(credentials=self.credentials)

    def list_clusters(self, project: str, location: str) -> List[Dict]:
        """List GKE clusters in a region/zone."""
        try:
            parent = f"projects/{project}/locations/{location}"
            response = self.container_client.list_clusters(parent=parent)
            
            clusters = []
            for c in response.clusters:
                # Calculate total node count across all node pools
                total_nodes = sum(
                    (np.initial_node_count or 0) if np.initial_node_count 
                    else len(np.instance_group_urls)
                    for np in c.node_pools
                )
                
                clusters.append({
                    "name": c.name,
                    "location": c.location,
                    "status": container_v1.Cluster.Status.Name(c.status),
                    "node_pools_count": len(c.node_pools),
                    "total_nodes": total_nodes,
                    "endpoint": c.endpoint,
                    "create_time": c.create_time,
                    "default_machine_type": c.node_pools[0].config.machine_type if c.node_pools else "unknown"
                })
            return clusters
        except exceptions.GoogleAPIError as e:
            print(f"⚠️ Error listing clusters: {e}")
            return []

    def get_nodepools(self, cluster_name: str, project: str, region: str) -> List[Dict]:
        """Get detailed node pool information for a cluster."""
        try:
            name = f"projects/{project}/locations/{region}/clusters/{cluster_name}"
            cluster = self.container_client.get_cluster(name=name)
            
            nodepools = []
            for np in cluster.node_pools:
                # Extract zones from instance group URLs
                zones = list(set(
                    url.split("/")[-1] 
                    for url in np.instance_group_urls 
                    if url
                )) or [cluster.location]
                
                # Get autoscaling config
                autoscale = np.autoscaling
                nodepools.append({
                    "name": np.name,
                    "machine_type": np.config.machine_type,
                    "disk_size_gb": np.config.disk_size_gb,
                    "zones": zones,
                    "initial_node_count": np.initial_node_count or len(np.instance_group_urls),
                    "autoscale_min": autoscale.min_node_count if autoscale else None,
                    "autoscale_max": autoscale.max_node_count if autoscale else None,
                    "labels": dict(np.config.labels) if np.config.labels else {},
                    "taints": [{"key": t.key, "value": t.value, "effect": t.effect.name} 
                              for t in np.config.taints] if np.config.taints else []
                })
            return nodepools
        except exceptions.GoogleAPIError as e:
            print(f"⚠️ Error getting nodepools: {e}")
            return []

    def get_nodepool_node_count(self, cluster_name: str, nodepool_name: str, 
                               region: str, project: str = None) -> int:
        """Get actual node count for a node pool."""
        if not project:
            project = default()[1]
        
        try:
            name = f"projects/{project}/locations/{region}/clusters/{cluster_name}"
            cluster = self.container_client.get_cluster(name=name)
            
            for np in cluster.node_pools:
                if np.name == nodepool_name:
                    # Prefer actual instance count over initial_node_count
                    if np.instance_group_urls:
                        return len(np.instance_group_urls)
                    return np.initial_node_count or 0
            return 0
        except Exception:
            return 0

    def load_kube_config(self, cluster_name: str, region: str, project: str = None):
        """Load kubernetes config for a specific cluster."""
        if not project:
            project = default()[1]
        
        # Use gcloud to get credentials
        import subprocess
        import os
        
        cmd = [
            "gcloud", "container", "clusters", "get-credentials",
            cluster_name, "--region", region, "--project", project
        ]
        subprocess.run(cmd, capture_output=True, check=True)
        
        # Load the config
        kubernetes.config.load_kube_config()
        return kubernetes.client.CoreV1Api()