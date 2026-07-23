# -*- coding: utf-8 -*-
"""
Azure Cloud Collector for AIOps Platform
Collects metrics from Azure Monitor, Azure Resources, and Azure Cost Management
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

try:
    from azure.identity import DefaultAzureCredential
    from azure.mgmt.compute import ComputeManagementClient
    from azure.mgmt.costmanagement import CostManagementClient
    from azure.mgmt.network import NetworkManagementClient
    from azure.mgmt.resource import ResourceManagementClient
    from azure.mgmt.storage import StorageManagementClient
    from azure.monitor.query import MetricsQueryClient

    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class AzureMetric:
    """Represents a collected Azure metric"""

    name: str
    value: float
    timestamp: datetime
    unit: str
    resource_id: str
    resource_type: str
    tags: Dict[str, str]


class AzureCloudCollector:
    """
    Azure Cloud Metrics Collector
    Collects metrics from various Azure services for AIOps monitoring
    """

    def __init__(self, subscription_id: str, credential: Optional[Any] = None):
        """
        Initialize Azure Cloud Collector

        Args:
            subscription_id: Azure subscription ID
            credential: Azure credential (DefaultAzureCredential if None)
        """
        if not AZURE_AVAILABLE:
            raise ImportError(
                "Azure SDK not installed. Install with: pip install "
                "azure-identity azure-monitor-query azure-mgmt-resource "
                "azure-mgmt-costmanagement azure-mgmt-compute "
                "azure-mgmt-storage azure-mgmt-network"
            )

        self.subscription_id = subscription_id
        self.credential = credential or DefaultAzureCredential()

        # Initialize Azure clients
        self.metrics_client = MetricsQueryClient(self.credential)
        self.resource_client = ResourceManagementClient(self.credential, subscription_id)
        self.cost_client = CostManagementClient(self.credential, subscription_id)
        self.compute_client = ComputeManagementClient(self.credential, subscription_id)
        self.storage_client = StorageManagementClient(self.credential, subscription_id)
        self.network_client = NetworkManagementClient(self.credential, subscription_id)

        logger.info(f"Azure Cloud Collector initialized for subscription: {subscription_id}")

    async def collect_vm_metrics(self, resource_group: str, vm_name: str) -> List[AzureMetric]:
        """
        Collect VM performance metrics

        Args:
            resource_group: Resource group name
            vm_name: Virtual machine name

        Returns:
            List of AzureMetric objects
        """
        metrics = []
        resource_id = (
            f"/subscriptions/{self.subscription_id}/resourceGroups/"
            f"{resource_group}/providers/Microsoft.Compute/virtualMachines/{vm_name}"
        )

        try:
            # Define metrics to collect
            metric_names = [
                "Percentage CPU",
                "Network In",
                "Network Out",
                "Disk Read Bytes",
                "Disk Write Bytes",
                "Disk Read Operations/Sec",
                "Disk Write Operations/Sec",
            ]

            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(hours=1)

            for metric_name in metric_names:
                try:
                    response = self.metrics_client.query_resource(
                        resource_id=resource_id,
                        metric_names=[metric_name],
                        timespan=f"{start_time.isoformat()}/{end_time.isoformat()}",
                    )

                    for metric in response.metrics:
                        for timeseries in metric.timeseries:
                            for data_point in timeseries.data:
                                if data_point.average is not None:
                                    metrics.append(
                                        AzureMetric(
                                            name=metric.name.localized_value,
                                            value=data_point.average,
                                            timestamp=data_point.time_stamp,
                                            unit=metric.unit,
                                            resource_id=resource_id,
                                            resource_type="Microsoft.Compute/virtualMachines",
                                            tags={},
                                        )
                                    )
                except Exception as e:
                    logger.error(f"Failed to collect metric {metric_name} for VM {vm_name}: {e}")

        except Exception as e:
            logger.error(f"Failed to collect VM metrics for {vm_name}: {e}")

        return metrics

    async def collect_storage_metrics(
        self, resource_group: str, account_name: str
    ) -> List[AzureMetric]:
        """
        Collect Storage account metrics

        Args:
            resource_group: Resource group name
            account_name: Storage account name

        Returns:
            List of AzureMetric objects
        """
        metrics = []
        resource_id = (
            f"/subscriptions/{self.subscription_id}/resourceGroups/"
            f"{resource_group}/providers/Microsoft.Storage/storageAccounts/"
            f"{account_name}"
        )

        try:
            metric_names = [
                "UsedCapacity",
                "Ingress",
                "Egress",
                "TransactionCount",
                "SuccessE2ELatency",
                "ServerLatency",
            ]

            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(hours=1)

            for metric_name in metric_names:
                try:
                    response = self.metrics_client.query_resource(
                        resource_id=resource_id,
                        metric_names=[metric_name],
                        timespan=f"{start_time.isoformat()}/{end_time.isoformat()}",
                    )

                    for metric in response.metrics:
                        for timeseries in metric.timeseries:
                            for data_point in timeseries.data:
                                if data_point.average is not None:
                                    metrics.append(
                                        AzureMetric(
                                            name=metric.name.localized_value,
                                            value=data_point.average,
                                            timestamp=data_point.time_stamp,
                                            unit=metric.unit,
                                            resource_id=resource_id,
                                            resource_type="Microsoft.Storage/storageAccounts",
                                            tags={},
                                        )
                                    )
                except Exception as e:
                    logger.error(
                        f"Failed to collect metric {metric_name} for storage {account_name}: {e}"
                    )

        except Exception as e:
            logger.error(f"Failed to collect storage metrics for {account_name}: {e}")

        return metrics

    async def collect_network_metrics(self, resource_group: str) -> List[AzureMetric]:
        """
        Collect network metrics (Load Balancer, Application Gateway)

        Args:
            resource_group: Resource group name

        Returns:
            List of AzureMetric objects
        """
        metrics = []

        try:
            # Collect Load Balancer metrics
            for lb in self.network_client.load_balancers.list(resource_group):
                resource_id = lb.id
                metric_names = ["ByteCount", "PacketCount", "SnatConnectionCount"]

                end_time = datetime.now(timezone.utc)
                start_time = end_time - timedelta(hours=1)

                for metric_name in metric_names:
                    try:
                        response = self.metrics_client.query_resource(
                            resource_id=resource_id,
                            metric_names=[metric_name],
                            timespan=f"{start_time.isoformat()}/{end_time.isoformat()}",
                        )

                        for metric in response.metrics:
                            for timeseries in metric.timeseries:
                                for data_point in timeseries.data:
                                    if data_point.average is not None:
                                        metrics.append(
                                            AzureMetric(
                                                name=metric.name.localized_value,
                                                value=data_point.average,
                                                timestamp=data_point.time_stamp,
                                                unit=metric.unit,
                                                resource_id=resource_id,
                                                resource_type="Microsoft.Network/loadBalancers",
                                                tags={},
                                            )
                                        )
                    except Exception as e:
                        logger.error(
                            f"Failed to collect metric {metric_name} for LB {lb.name}: {e}"
                        )

        except Exception as e:
            logger.error(f"Failed to collect network metrics: {e}")

        return metrics

    async def collect_cost_metrics(
        self, start_date: datetime, end_date: datetime
    ) -> Dict[str, Any]:
        """
        Collect cost management data

        Args:
            start_date: Start date for cost query
            end_date: End date for cost query

        Returns:
            Dictionary containing cost data
        """
        cost_data = {}

        try:
            scope = f"/subscriptions/{self.subscription_id}"

            query = {
                "type": "ActualCost",
                "timeframe": "Custom",
                "timePeriod": {
                    "start": start_date.strftime("%Y-%m-%d"),
                    "end": end_date.strftime("%Y-%m-%d"),
                },
                "dataset": {
                    "granularity": "Daily",
                    "aggregation": {"totalCost": {"name": "Cost", "function": "Sum"}},
                    "grouping": [{"type": "Dimension", "name": "ResourceGroup"}],
                },
            }

            response = self.cost_client.query.usage(scope, query)

            if response.rows:
                cost_data = {
                    "total_cost": sum(row[0] for row in response.rows),
                    "currency": response.columns[0].name,
                    "details": [],
                }

                for row in response.rows:
                    # SECURITY: Check if row has enough elements to avoid IndexError
                    if not row or len(row) < 3:
                        continue  # Skip malformed rows
                    cost_data["details"].append(
                        {"date": row[0], "resource_group": row[1], "cost": row[2]}
                    )

        except Exception as e:
            logger.error(f"Failed to collect cost metrics: {e}")

        return cost_data

    async def collect_all_resources(
        self, resource_group: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Collect all resources in subscription or resource group

        Args:
            resource_group: Optional resource group name (None for all resources)

        Returns:
            List of resource dictionaries
        """
        resources = []

        try:
            if resource_group:
                resource_list = self.resource_client.resource_groups.list_by_resource_group(
                    resource_group
                )
            else:
                resource_list = self.resource_client.resources.list()

            for resource in resource_list:
                resources.append(
                    {
                        "id": resource.id,
                        "name": resource.name,
                        "type": resource.type,
                        "location": resource.location,
                        "tags": resource.tags or {},
                    }
                )

        except Exception as e:
            logger.error(f"Failed to collect resources: {e}")

        return resources

    async def collect_health_metrics(self) -> List[Dict[str, Any]]:
        """
        Collect Azure service health status

        Returns:
            List of health status dictionaries
        """
        health_status = []

        try:
            # This would require Azure Resource Health API
            # Placeholder for implementation
            health_status.append(
                {
                    "service": "Azure",
                    "status": "operational",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )

        except Exception as e:
            logger.error(f"Failed to collect health metrics: {e}")

        return health_status

    async def collect_all_metrics(self, resource_group: Optional[str] = None) -> Dict[str, Any]:
        """
        Collect all metrics from Azure

        Args:
            resource_group: Optional resource group name

        Returns:
            Dictionary containing all collected metrics
        """
        all_metrics: Dict[str, Any] = {
            "vm_metrics": [],
            "storage_metrics": [],
            "network_metrics": [],
            "cost_metrics": {},
            "resources": [],
            "health_metrics": [],
        }

        try:
            # Collect resources
            all_metrics["resources"] = await self.collect_all_resources(resource_group)

            # Collect VM metrics in parallel
            vm_tasks = []
            for resource in all_metrics["resources"]:
                if resource["type"] == "Microsoft.Compute/virtualMachines":
                    rg = resource["id"].split("/resourceGroups/")[1].split("/")[0]
                    vm_name = resource["name"]
                    vm_tasks.append(self.collect_vm_metrics(rg, vm_name))
            if vm_tasks:
                vm_results = await asyncio.gather(*vm_tasks, return_exceptions=True)
                for result in vm_results:
                    if isinstance(result, list):
                        all_metrics["vm_metrics"].extend(result)
                    elif isinstance(result, Exception):
                        logger.error(f"Failed to collect VM metrics: {result}")

            # Collect storage metrics in parallel
            storage_tasks = []
            for resource in all_metrics["resources"]:
                if resource["type"] == "Microsoft.Storage/storageAccounts":
                    rg = resource["id"].split("/resourceGroups/")[1].split("/")[0]
                    account_name = resource["name"]
                    storage_tasks.append(self.collect_storage_metrics(rg, account_name))
            if storage_tasks:
                storage_results = await asyncio.gather(*storage_tasks, return_exceptions=True)
                for result in storage_results:
                    if isinstance(result, list):
                        all_metrics["storage_metrics"].extend(result)
                    elif isinstance(result, Exception):
                        logger.error(f"Failed to collect storage metrics: {result}")

            # Collect network metrics
            if resource_group:
                all_metrics["network_metrics"] = await self.collect_network_metrics(resource_group)

            # Collect cost metrics (last 30 days)
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=30)
            all_metrics["cost_metrics"] = await self.collect_cost_metrics(start_date, end_date)

            # Collect health metrics
            all_metrics["health_metrics"] = await self.collect_health_metrics()

        except Exception as e:
            logger.error(f"Failed to collect all metrics: {e}")

        return all_metrics


def create_azure_collector(subscription_id: str) -> Optional[AzureCloudCollector]:
    """
    Factory function to create Azure Cloud Collector

    Args:
        subscription_id: Azure subscription ID

    Returns:
        AzureCloudCollector instance or None if SDK not available
    """
    if not AZURE_AVAILABLE:
        logger.warning("Azure SDK not available")
        return None

    try:
        return AzureCloudCollector(subscription_id)
    except Exception as e:
        logger.error(f"Failed to create Azure collector: {e}")
        return None
