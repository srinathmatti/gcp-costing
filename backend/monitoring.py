"""
Cloud Monitoring API for real-time metrics.
Queries: kubernetes.io/container/cpu/core_usage_time, 
         compute.googleapis.com/instance/network/received_bytes
Reference: https://docs.cloud.google.com/monitoring/api/metrics_kubernetes [[12]]
"""
from google.cloud import monitoring_v3
from google.auth import default
from google.api_core import exceptions
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import asyncio

class MonitoringService:
    def __init__(self, credentials=None, project_id: str = None):
        self.credentials = credentials or default()[0]
        self.project_id = project_id or default()[1]
        self.client = monitoring_v3.MetricServiceClient(credentials=self.credentials)

    def _build_time_range(self, minutes: int = 60) -> tuple:
        """Build start/end times for metric queries."""
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(minutes=minutes)
        return (
            monitoring_v3.TimeInterval({
                "start_time": {"seconds": int(start_time.timestamp())},
                "end_time": {"seconds": int(end_time.timestamp())}
            })
        )

    def query_cpu_usage(self, cluster_name: str, nodepool_name: str = None, 
                       namespace: str = None, container_name: str = None,
                       minutes: int = 60) -> Dict[str, float]:
        """
        Query CPU usage time for containers/nodes.
        Metric: kubernetes.io/container/cpu/core_usage_time
        Returns: {resource_name: cpu_seconds}
        """
        try:
            # Build filter - reference GKE metrics docs [[12]]
            filter_parts = [
                'metric.type="kubernetes.io/container/cpu/core_usage_time"',
                f'resource.type="k8s_container"',
                f'resource.label."cluster_name"="{cluster_name}"'
            ]
            
            if nodepool_name:
                filter_parts.append(f'resource.label."node_name"=monitoring.regex.full_match(".*{nodepool_name}.*")')
            if namespace:
                filter_parts.append(f'metric.label."namespace"="{namespace}"')
            if container_name:
                filter_parts.append(f'metric.label."container_name"="{container_name}"')
            
            filter_query = " AND ".join(filter_parts)
            
            # Query time series
            request = monitoring_v3.ListTimeSeriesRequest(
                name=f"projects/{self.project_id}",
                filter=filter_query,
                interval=self._build_time_range(minutes),
                view=monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.FULL
            )
            
            results = {}
            for ts in self.client.list_time_series(request=request):
                # Extract resource name
                resource = ts.resource
                node_name = resource.labels.get("node_name", "unknown")
                container = resource.labels.get("container_name", "unknown")
                key = f"{node_name}/{container}"
                
                # Get latest value (CUMULATIVE metric - calculate delta)
                if ts.points:
                    # For cumulative metrics, we'd normally calculate rate
                    # Here we return the raw value for simplicity
                    value = ts.points[-1].value.double_value
                    results[key] = value
            
            return results
            
        except exceptions.GoogleAPIError as e:
            print(f"⚠️ Monitoring CPU query error: {e}")
            return {}

    def query_network_usage(self, instance_names: List[str], 
                           minutes: int = 60) -> Dict[str, Dict[str, float]]:
        """
        Query network received bytes for compute instances.
        Metric: compute.googleapis.com/instance/network/received_bytes
        Returns: {instance_name: {received_bytes, sent_bytes}}
        """
        results = {}
        
        for metric_type, direction in [
            ("compute.googleapis.com/instance/network/received_bytes", "received"),
            ("compute.googleapis.com/instance/network/sent_bytes", "sent")
        ]:
            try:
                filter_query = (
                    f'metric.type="{metric_type}" AND '
                    f'resource.type="gce_instance" AND '
                    f'resource.label."instance_name"=monitoring.regex.full_match("{"|".join(instance_names)}")'
                )
                
                request = monitoring_v3.ListTimeSeriesRequest(
                    name=f"projects/{self.project_id}",
                    filter=filter_query,
                    interval=self._build_time_range(minutes),
                    view=monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.FULL
                )
                
                for ts in self.client.list_time_series(request=request):
                    instance_name = ts.resource.labels.get("instance_name", "unknown")
                    if instance_name not in results:
                        results[instance_name] = {"received_bytes": 0, "sent_bytes": 0}
                    
                    if ts.points:
                        value = ts.points[-1].value.int64_value
                        results[instance_name][f"{direction}_bytes"] = value
                        
            except exceptions.GoogleAPIError as e:
                print(f"⚠️ Monitoring network query error for {metric_type}: {e}")
                continue
        
        return results

    def query_memory_usage(self, cluster_name: str, nodepool_name: str = None,
                          minutes: int = 60) -> Dict[str, float]:
        """
        Query memory usage for containers.
        Metric: kubernetes.io/container/memory/used_bytes
        """
        try:
            filter_query = (
                'metric.type="kubernetes.io/container/memory/used_bytes" AND '
                f'resource.type="k8s_container" AND '
                f'resource.label."cluster_name"="{cluster_name}"'
            )
            if nodepool_name:
                filter_query += f' AND resource.label."node_name"=monitoring.regex.full_match(".*{nodepool_name}.*")'
            
            request = monitoring_v3.ListTimeSeriesRequest(
                name=f"projects/{self.project_id}",
                filter=filter_query,
                interval=self._build_time_range(minutes),
                view=monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.FULL
            )
            
            results = {}
            for ts in self.client.list_time_series(request=request):
                node = ts.resource.labels.get("node_name", "unknown")
                container = ts.resource.labels.get("container_name", "unknown")
                key = f"{node}/{container}"
                
                if ts.points:
                    # Value is in bytes
                    results[key] = ts.points[-1].value.int64_value / (1024**3)  # Convert to GB
            
            return results
            
        except exceptions.GoogleAPIError as e:
            print(f"⚠️ Monitoring memory query error: {e}")
            return {}

    def calculate_ip_usage_percentage(self, nodepool_name: str, cluster_name: str,
                                     region: str) -> float:
        """
        Estimate IP address usage for a node pool.
        This is a simplified calculation based on node count vs subnet capacity.
        In production, you'd query VPC subnet metrics.
        """
        try:
            # Get node count from GKE API
            from .gke import GKEService
            gke = GKEService(credentials=self.credentials)
            node_count = gke.get_nodepool_node_count(cluster_name, nodepool_name, region)
            
            # Assume /24 subnet (251 usable IPs) - adjust based on your VPC config
            subnet_capacity = 251
            # Reserve some IPs for GKE system pods (~10%)
            reserved = int(subnet_capacity * 0.1)
            available = subnet_capacity - reserved
            
            usage_pct = min(100, (node_count / available) * 100)
            return round(usage_pct, 1)
            
        except Exception as e:
            print(f"⚠️ IP usage calculation error: {e}")
            return 0.0