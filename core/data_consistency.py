# -*- coding: utf-8 -*-
"""
Data Consistency Checker
Validates consistency between SQLite and VictoriaMetrics data
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger


class DataConsistencyChecker:
    """
    Checks data consistency between SQLite and VictoriaMetrics
    """

    def __init__(self, victoria_metrics_url: str = "http://localhost:8428"):
        """
        Initialize consistency checker

        Args:
            victoria_metrics_url: VictoriaMetrics URL
        """
        self.victoria_metrics_url = victoria_metrics_url
        self.vm_storage: Optional[Any] = None
        self._inconsistencies: List[Dict[str, Any]] = []

    async def initialize(self) -> bool:
        """Initialize VictoriaMetrics storage"""
        try:
            from core.storage.l4.storage_manager import init_l4_storage_manager

            config = {"victoriametrics": {"enabled": True, "base_url": self.victoria_metrics_url}}

            manager = init_l4_storage_manager(config)
            self.vm_storage = manager.get_victoriametrics()

            if self.vm_storage and self.vm_storage.initialize():
                logger.info("VictoriaMetrics initialized for consistency check")
                return True
            else:
                logger.error("Failed to initialize VictoriaMetrics")
                return False

        except Exception as e:
            logger.error(f"Failed to initialize consistency checker: {e}")
            return False

    async def check_metric_consistency(
        self, metric_name: str, labels: Dict[str, str], sqlite_value: float, vm_query: str
    ) -> Dict[str, Any]:
        """
        Check consistency of a single metric between SQLite and VictoriaMetrics

        Args:
            metric_name: Name of the metric
            labels: Metric labels
            sqlite_value: Value from SQLite
            vm_query: PromQL query to get VictoriaMetrics value

        Returns:
            Consistency check result
        """
        try:
            # Query VictoriaMetrics
            if self.vm_storage is None:
                return {
                    "metric": metric_name,
                    "consistent": False,
                    "reason": "VictoriaMetrics storage not initialized",
                    "sqlite_value": sqlite_value,
                    "vm_value": None,
                }
            vm_result = await self.vm_storage.query({"query": vm_query})

            if not vm_result:
                return {
                    "metric": metric_name,
                    "consistent": False,
                    "reason": "VictoriaMetrics query returned no data",
                    "sqlite_value": sqlite_value,
                    "vm_value": None,
                }

            # Extract value from VictoriaMetrics result
            vm_value = vm_result.get("value", 0) if isinstance(vm_result, dict) else vm_result

            # Compare values (allow small floating point tolerance)
            tolerance = 0.001
            is_consistent = abs(sqlite_value - vm_value) <= tolerance

            if not is_consistent:
                self._inconsistencies.append(
                    {
                        "metric": metric_name,
                        "labels": labels,
                        "sqlite_value": sqlite_value,
                        "vm_value": vm_value,
                        "difference": abs(sqlite_value - vm_value),
                    }
                )

            return {
                "metric": metric_name,
                "labels": labels,
                "consistent": is_consistent,
                "sqlite_value": sqlite_value,
                "vm_value": vm_value,
                "difference": abs(sqlite_value - vm_value),
            }

        except Exception as e:
            logger.error(f"Failed to check metric {metric_name}: {e}")
            return {
                "metric": metric_name,
                "consistent": False,
                "reason": f"Error: {str(e)}",
                "sqlite_value": sqlite_value,
                "vm_value": None,
            }

    async def check_time_range_consistency(
        self, start_time: datetime, end_time: datetime
    ) -> Dict[str, Any]:
        """
        Check consistency for all metrics in a time range

        Args:
            start_time: Start of time range
            end_time: End of time range

        Returns:
            Consistency check summary
        """
        logger.info(f"Checking consistency from {start_time} to {end_time}")

        # This is a placeholder - actual implementation would:
        # 1. Query SQLite for metrics in time range
        # 2. Query VictoriaMetrics for same metrics
        # 3. Compare values
        # 4. Report inconsistencies

        results = {
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "metrics_checked": 0,
            "consistent": 0,
            "inconsistent": 0,
            "inconsistencies": self._inconsistencies,
        }

        return results

    async def check_latest_metrics(self, metric_names: List[str]) -> Dict[str, Any]:
        """
        Check consistency for latest values of specified metrics

        Args:
            metric_names: List of metric names to check

        Returns:
            Consistency check summary
        """
        logger.info(f"Checking consistency for {len(metric_names)} metrics")

        results = []
        for metric_name in metric_names:
            # This is a placeholder - actual implementation would:
            # 1. Get latest value from SQLite
            # 2. Query VictoriaMetrics for latest value
            # 3. Compare and record result

            result = await self.check_metric_consistency(
                metric_name=metric_name,
                labels={"host": "localhost"},
                sqlite_value=0.0,  # Placeholder
                vm_query=f"{metric_name}",  # Placeholder
            )
            results.append(result)

        summary = {
            "metrics_checked": len(metric_names),
            "consistent": sum(1 for r in results if r.get("consistent", False)),
            "inconsistent": sum(1 for r in results if not r.get("consistent", False)),
            "results": results,
            "inconsistencies": self._inconsistencies,
        }

        return summary

    def get_inconsistencies(self) -> List[Dict[str, Any]]:
        """Get list of inconsistencies found"""
        return self._inconsistencies

    def clear_inconsistencies(self) -> None:
        """Clear inconsistencies list"""
        self._inconsistencies = []


async def run_consistency_check(
    victoria_metrics_url: str = "http://localhost:8428", metric_names: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Run consistency check

    Args:
        victoria_metrics_url: VictoriaMetrics URL
        metric_names: List of metric names to check (if None, checks common metrics)

    Returns:
        Consistency check summary
    """
    if metric_names is None:
        metric_names = [
            "aiops_cpu_usage_percent",
            "aiops_memory_usage_percent",
            "aiops_disk_usage_percent",
        ]

    checker = DataConsistencyChecker(victoria_metrics_url)

    if not await checker.initialize():
        logger.error("Failed to initialize consistency checker")
        return {"error": "Failed to initialize"}

    summary = await checker.check_latest_metrics(metric_names)

    logger.info("Consistency check completed")
    logger.info(f"Consistent: {summary['consistent']}/{summary['metrics_checked']}")
    logger.info(f"Inconsistent: {summary['inconsistent']}/{summary['metrics_checked']}")

    return summary
