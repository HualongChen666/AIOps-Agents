# -*- coding: utf-8 -*-
"""
GCP Cloud Collector for AIOps Platform
Collects metrics from Google Cloud Platform services including Compute Engine,
Cloud Storage, BigQuery, and Cloud Billing
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

try:
    from google.cloud import billing_v1, compute_v1, monitoring_v3, resource_manager_v3, storage
    from google.oauth2 import service_account

    GCP_AVAILABLE = True
except ImportError:
    GCP_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class GCPMetric:
    """Represents a collected GCP metric"""

    name: str
    value: float
    timestamp: datetime
    unit: str
    resource_id: str
    resource_type: str
    labels: Dict[str, str]


class GCPCloudCollector:
    """
    GCP Cloud Metrics Collector
    Collects metrics from various GCP services for AIOps monitoring
    """

    def __init__(self, project_id: str, credentials_path: Optional[str] = None):
        """
        Initialize GCP Cloud Collector

        Args:
            project_id: GCP project ID
            credentials_path: Path to service account JSON file (None for default credentials)
        """
        if not GCP_AVAILABLE:
            raise ImportError(
                "GCP SDK not installed. Install with: pip install "
                "google-cloud-monitoring google-cloud-compute "
                "google-cloud-storage google-cloud-billing "
                "google-cloud-resource-manager"
            )

        self.project_id = project_id

        # Initialize credentials
        if credentials_path:
            self.credentials = service_account.Credentials.from_service_account_file(
                credentials_path
            )
        else:
            self.credentials = None

        # Initialize GCP clients
        self.monitoring_client = monitoring_v3.MetricServiceClient(credentials=self.credentials)
        self.compute_client = compute_v1.InstancesClient(credentials=self.credentials)
        self.storage_client = storage.Client(project=project_id, credentials=self.credentials)
        self.billing_client = billing_v1.CloudBillingClient(credentials=self.credentials)
        self.resource_client = resource_manager_v3.ProjectsClient(credentials=self.credentials)

        logger.info(f"GCP Cloud Collector initialized for project: {project_id}")

    async def collect_vm_metrics(self, zone: str, instance_name: str) -> List[GCPMetric]:
        """
        Collect Compute Engine VM metrics

        Args:
            zone: GCP zone (e.g., us-central1-a)
            instance_name: Instance name

        Returns:
            List of GCPMetric objects
        """
        metrics = []
        project_name = f"projects/{self.project_id}"

        try:
            # Define metrics to collect
            metric_types = [
                "compute.googleapis.com/instance/cpu/utilization",
                "compute.googleapis.com/instance/disk/read_bytes_count",
                "compute.googleapis.com/instance/disk/write_bytes_count",
                "compute.googleapis.com/instance/network/received_bytes_count",
                "compute.googleapis.com/instance/network/sent_bytes_count",
            ]

            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(hours=1)

            interval = monitoring_v3.TimeInterval(
                {
                    "end_time": {"seconds": int(end_time.timestamp())},
                    "start_time": {"seconds": int(start_time.timestamp())},
                }
            )

            for metric_type in metric_types:
                try:
                    request = monitoring_v3.ListTimeSeriesRequest(
                        name=project_name,
                        filter=(
                            f'metric.type="{metric_type}" AND '
                            f'resource.labels.instance_name="{instance_name}" AND '
                            f'resource.labels.zone="{zone}"'
                        ),
                        interval=interval,
                        view=monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.FULL,
                    )

                    results = self.monitoring_client.list_time_series(request=request)

                    for result in results:
                        for point in result.points:
                            metrics.append(
                                GCPMetric(
                                    name=metric_type.split("/")[-1],
                                    value=point.value.double_value,
                                    timestamp=datetime.fromtimestamp(
                                        point.interval.end_time.seconds
                                    ),
                                    unit=result.metric.kind,
                                    resource_id=result.resource.name,
                                    resource_type=result.resource.type,
                                    labels=dict(result.metric.labels),
                                )
                            )
                except Exception as e:
                    logger.error(
                        f"Failed to collect metric {metric_type} for VM {instance_name}: {e}"
                    )

        except Exception as e:
            logger.error(f"Failed to collect VM metrics for {instance_name}: {e}")

        return metrics

    async def collect_storage_metrics(self, bucket_name: str) -> List[GCPMetric]:
        """
        Collect Cloud Storage bucket metrics

        Args:
            bucket_name: Storage bucket name

        Returns:
            List of GCPMetric objects
        """
        metrics = []
        project_name = f"projects/{self.project_id}"

        try:
            metric_types = [
                "storage.googleapis.com/storage/total_bytes",
                "storage.googleapis.com/storage/object_count",
                "storage.googleapis.com/api/request_count",
            ]

            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(hours=1)

            interval = monitoring_v3.TimeInterval(
                {
                    "end_time": {"seconds": int(end_time.timestamp())},
                    "start_time": {"seconds": int(start_time.timestamp())},
                }
            )

            for metric_type in metric_types:
                try:
                    request = monitoring_v3.ListTimeSeriesRequest(
                        name=project_name,
                        filter=(
                            f'metric.type="{metric_type}" AND '
                            f'resource.labels.bucket_name="{bucket_name}"'
                        ),
                        interval=interval,
                        view=monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.FULL,
                    )

                    results = self.monitoring_client.list_time_series(request=request)

                    for result in results:
                        for point in results.points:
                            metrics.append(
                                GCPMetric(
                                    name=metric_type.split("/")[-1],
                                    value=point.value.double_value,
                                    timestamp=datetime.fromtimestamp(
                                        point.interval.end_time.seconds
                                    ),
                                    unit=result.metric.kind,
                                    resource_id=result.resource.name,
                                    resource_type=result.resource.type,
                                    labels=dict(result.metric.labels),
                                )
                            )
                except Exception as e:
                    logger.error(
                        f"Failed to collect metric {metric_type} for bucket {bucket_name}: {e}"
                    )

        except Exception as e:
            logger.error(f"Failed to collect storage metrics for {bucket_name}: {e}")

        return metrics

    async def collect_bigquery_metrics(self, dataset_id: str) -> List[GCPMetric]:
        """
        Collect BigQuery metrics

        Args:
            dataset_id: BigQuery dataset ID

        Returns:
            List of GCPMetric objects
        """
        metrics = []
        project_name = f"projects/{self.project_id}"

        try:
            metric_types = [
                "bigquery.googleapis.com/query/execution_times",
                "bigquery.googleapis.com/query/scanned_bytes",
                "bigquery.googleapis.com/warehouse/byte_count",
            ]

            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(hours=1)

            interval = monitoring_v3.TimeInterval(
                {
                    "end_time": {"seconds": int(end_time.timestamp())},
                    "start_time": {"seconds": int(start_time.timestamp())},
                }
            )

            for metric_type in metric_types:
                try:
                    request = monitoring_v3.ListTimeSeriesRequest(
                        name=project_name,
                        filter=(
                            f'metric.type="{metric_type}" AND '
                            f'resource.labels.dataset_id="{dataset_id}"'
                        ),
                        interval=interval,
                        view=monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.FULL,
                    )

                    results = self.monitoring_client.list_time_series(request=request)

                    for result in results:
                        for point in result.points:
                            metrics.append(
                                GCPMetric(
                                    name=metric_type.split("/")[-1],
                                    value=point.value.double_value,
                                    timestamp=datetime.fromtimestamp(
                                        point.interval.end_time.seconds
                                    ),
                                    unit=result.metric.kind,
                                    resource_id=result.resource.name,
                                    resource_type=result.resource.type,
                                    labels=dict(result.metric.labels),
                                )
                            )
                except Exception as e:
                    logger.error(
                        f"Failed to collect metric {metric_type} for dataset {dataset_id}: {e}"
                    )

        except Exception as e:
            logger.error(f"Failed to collect BigQuery metrics for {dataset_id}: {e}")

        return metrics

    async def collect_cost_metrics(
        self, start_date: datetime, end_date: datetime
    ) -> Dict[str, Any]:
        """
        Collect Cloud Billing cost data

        Args:
            start_date: Start date for cost query
            end_date: End date for cost query

        Returns:
            Dictionary containing cost data
        """
        cost_data = {}

        try:
            f"projects/{self.project_id}"

            # This is a simplified implementation
            # In production, you would use BigQuery export of billing data
            cost_data = {
                "total_cost": 0.0,
                "currency": "USD",
                "details": [],
                "message": "BigQuery billing export required for detailed cost analysis",
            }

        except Exception as e:
            logger.error(f"Failed to collect cost metrics: {e}")

        return cost_data

    async def collect_all_instances(self, zone: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Collect all Compute Engine instances

        Args:
            zone: Optional zone (None for all zones)

        Returns:
            List of instance dictionaries
        """
        instances = []

        try:
            if zone:
                request = compute_v1.ListInstancesRequest(project=self.project_id, zone=zone)
                instance_list = self.compute_client.list(request=request)
            else:
                # List all zones first
                zones_client = compute_v1.ZonesClient(credentials=self.credentials)
                zones_request = compute_v1.ListZonesRequest(project=self.project_id)
                zones = zones_client.list(request=zones_request)

                for zone_obj in zones:
                    request = compute_v1.ListInstancesRequest(
                        project=self.project_id, zone=zone_obj.name
                    )
                    instance_list = self.compute_client.list(request=request)

                    for instance in instance_list:
                        instances.append(
                            {
                                "id": instance.id,
                                "name": instance.name,
                                "zone": zone_obj.name,
                                "machine_type": instance.machine_type.split("/")[-1],
                                "status": instance.status,
                                "labels": dict(instance.labels) if instance.labels else {},
                            }
                        )

        except Exception as e:
            logger.error(f"Failed to collect instances: {e}")

        return instances

    async def collect_all_buckets(self) -> List[Dict[str, Any]]:
        """
        Collect all Cloud Storage buckets

        Returns:
            List of bucket dictionaries
        """
        buckets = []

        try:
            for bucket in self.storage_client.list_buckets():
                buckets.append(
                    {
                        "name": bucket.name,
                        "location": bucket.location,
                        "storage_class": bucket.storage_class,
                        "created": bucket.time_created,
                        "labels": dict(bucket.labels) if bucket.labels else {},
                    }
                )

        except Exception as e:
            logger.error(f"Failed to collect buckets: {e}")

        return buckets

    async def collect_health_metrics(self) -> List[Dict[str, Any]]:
        """
        Collect GCP service health status

        Returns:
            List of health status dictionaries
        """
        health_status = []

        try:
            # This would require GCP Service Health API
            # Placeholder for implementation
            health_status.append(
                {
                    "service": "GCP",
                    "status": "operational",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )

        except Exception as e:
            logger.error(f"Failed to collect health metrics: {e}")

        return health_status

    async def collect_all_metrics(self) -> Dict[str, Any]:
        """
        Collect all metrics from GCP

        Returns:
            Dictionary containing all collected metrics
        """
        all_metrics: Dict[str, Any] = {
            "vm_metrics": [],
            "storage_metrics": [],
            "bigquery_metrics": [],
            "cost_metrics": {},
            "instances": [],
            "buckets": [],
            "health_metrics": [],
        }

        try:
            # Collect instances
            all_metrics["instances"] = await self.collect_all_instances()

            # Collect VM metrics in parallel
            vm_tasks = [
                self.collect_vm_metrics(instance["zone"], instance["name"])
                for instance in all_metrics["instances"]
            ]
            vm_results = await asyncio.gather(*vm_tasks, return_exceptions=True)
            for result in vm_results:
                if isinstance(result, list):
                    all_metrics["vm_metrics"].extend(result)
                elif isinstance(result, Exception):
                    logger.error(f"Failed to collect VM metrics: {result}")

            # Collect buckets
            all_metrics["buckets"] = await self.collect_all_buckets()

            # Collect storage metrics in parallel
            storage_tasks = [
                self.collect_storage_metrics(bucket["name"]) for bucket in all_metrics["buckets"]
            ]
            storage_results = await asyncio.gather(*storage_tasks, return_exceptions=True)
            for result in storage_results:
                if isinstance(result, list):
                    all_metrics["storage_metrics"].extend(result)
                elif isinstance(result, Exception):
                    logger.error(f"Failed to collect storage metrics: {result}")

            # Collect cost metrics (last 30 days)
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=30)
            all_metrics["cost_metrics"] = await self.collect_cost_metrics(start_date, end_date)

            # Collect health metrics
            all_metrics["health_metrics"] = await self.collect_health_metrics()

        except Exception as e:
            logger.error(f"Failed to collect all metrics: {e}")

        return all_metrics


def create_gcp_collector(
    project_id: str, credentials_path: Optional[str] = None
) -> Optional[GCPCloudCollector]:
    """
    Factory function to create GCP Cloud Collector

    Args:
        project_id: GCP project ID
        credentials_path: Optional path to service account JSON

    Returns:
        GCPCloudCollector instance or None if SDK not available
    """
    if not GCP_AVAILABLE:
        logger.warning("GCP SDK not available")
        return None

    try:
        return GCPCloudCollector(project_id, credentials_path)
    except Exception as e:
        logger.error(f"Failed to create GCP collector: {e}")
        return None
