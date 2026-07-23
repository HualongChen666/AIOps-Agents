# -*- coding: utf-8 -*-
"""Core service logic for the Metrics Monitoring microservice."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .cache import CacheManager
from .config import settings
from .metrics import MetricsCollector
from .retry import RetryEngine

BASE_METHODS: List[str] = [
    "get_state",
    "backup_state",
    "restore_state",
    "get_stats",
    "list_methods",
]
OPERATIONS: List[str] = [
    "collect_metrics_prometheus",
    "aggregate_metrics",
    "analyze_metrics",
    "visualize_metrics",
    "alert_on_metrics",
    "monitor_sli_slo",
    "monitor_performance",
    "monitor_resources",
    "write_metrics_docs",
    "test_and_optimize_metrics_monitoring",
]


class MetricsMonitoringService:
    """Domain service for Metrics Monitoring."""

    def __init__(
        self,
        redis_url: Optional[str] = None,
        metrics: Optional[MetricsCollector] = None,
        cache: Optional[CacheManager] = None,
    ) -> None:
        self.metrics = metrics or MetricsCollector(settings.service_name)
        self.cache = cache or CacheManager(redis_url or settings.redis_url, self.metrics)
        self.retry_engine = RetryEngine("exponential_fast", self.metrics)
        self._state: Dict[str, Any] = {}
        self._backups: Dict[str, Any] = {}
        self._operations: Dict[str, int] = {}
        self._feature_count = len(OPERATIONS)

    @staticmethod
    def _get_config(request: Any) -> Dict[str, Any]:
        if request is None:
            return {}
        if hasattr(request, "model_dump"):
            data = request.model_dump()
        elif isinstance(request, dict):
            data = request
        else:
            return {}
        if not isinstance(data, dict):
            return {}
        return data.get("config", data) if "config" in data else data

    async def get_state(self, request: Any = None) -> Dict[str, Any]:
        self.metrics.inc_request("get_state")
        config = self._get_config(request)
        feature = config.get("feature") if isinstance(config, dict) else None
        if feature and feature in self._state:
            return {
                "feature": "get_state",
                "success": True,
                "status": "found",
                "config": {"feature": feature},
                "result": {"state": self._state[feature]},
                "message": f"State for {feature}",
            }
        return {
            "feature": "get_state",
            "success": False,
            "status": "not_found",
            "config": config,
            "result": {},
            "message": "State not found",
        }

    async def backup_state(self, request: Any = None) -> Dict[str, Any]:
        self.metrics.inc_request("backup_state")
        config = self._get_config(request)
        name = config.get("name", "default") if isinstance(config, dict) else "default"
        self._backups[name] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "state": self._state.copy(),
        }
        self.metrics.inc_operation("backup_state")
        return {
            "feature": "backup_state",
            "success": True,
            "status": "backed_up",
            "config": {"name": name},
            "result": {"snapshot": name},
            "message": f"Backup {name} created",
        }

    async def restore_state(self, request: Any = None) -> Dict[str, Any]:
        self.metrics.inc_request("restore_state")
        config = self._get_config(request)
        name = config.get("name", "default") if isinstance(config, dict) else "default"
        data = self._backups.get(name)
        if not data:
            return {
                "feature": "restore_state",
                "success": False,
                "status": "not_found",
                "config": {"name": name},
                "result": {},
                "message": f"Backup {name} not found",
            }
        self._state = data["state"].copy()
        self.metrics.inc_operation("restore_state")
        return {
            "feature": "restore_state",
            "success": True,
            "status": "restored",
            "config": {"name": name},
            "result": {"snapshot": name},
            "message": f"Backup {name} restored",
        }

    async def get_stats(self, request: Any = None) -> Dict[str, Any]:
        self.metrics.inc_request("get_stats")
        return {
            "feature": "get_stats",
            "success": True,
            "status": "ok",
            "config": {},
            "result": {
                "total_requests": self.metrics.request_count,
                "cache_hits": self.metrics.cache_hits_count,
                "cache_misses": self.metrics.cache_misses_count,
                "operations": self._operations.copy(),
                "index_size": len(self._state),
                "feature_count": self._feature_count,
            },
            "message": "Statistics",
        }

    async def list_methods(self, request: Any = None) -> Dict[str, Any]:
        self.metrics.inc_request("list_methods")
        return {
            "feature": "list_methods",
            "success": True,
            "status": "ok",
            "config": {},
            "result": {"methods": OPERATIONS + BASE_METHODS},
            "message": "Methods listed",
        }

    async def collect_metrics_prometheus(self, request: Any = None) -> Dict[str, Any]:
        """Collect Metrics Prometheus."""
        self.metrics.inc_request("collect_metrics_prometheus")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:collect_metrics_prometheus", config)
        self._state["collect_metrics_prometheus"] = config
        self._operations["collect_metrics_prometheus"] = (
            self._operations.get("collect_metrics_prometheus", 0) + 1
        )
        self.metrics.inc_operation("collect_metrics_prometheus")
        return {
            "feature": "collect_metrics_prometheus",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "Metrics Monitoring"},
            "message": "collect_metrics_prometheus completed",
        }

    async def aggregate_metrics(self, request: Any = None) -> Dict[str, Any]:
        """Aggregate Metrics."""
        self.metrics.inc_request("aggregate_metrics")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:aggregate_metrics", config)
        self._state["aggregate_metrics"] = config
        self._operations["aggregate_metrics"] = self._operations.get("aggregate_metrics", 0) + 1
        self.metrics.inc_operation("aggregate_metrics")
        return {
            "feature": "aggregate_metrics",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "Metrics Monitoring"},
            "message": "aggregate_metrics completed",
        }

    async def analyze_metrics(self, request: Any = None) -> Dict[str, Any]:
        """Analyze Metrics."""
        self.metrics.inc_request("analyze_metrics")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:analyze_metrics", config)
        self._state["analyze_metrics"] = config
        self._operations["analyze_metrics"] = self._operations.get("analyze_metrics", 0) + 1
        self.metrics.inc_operation("analyze_metrics")
        return {
            "feature": "analyze_metrics",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "Metrics Monitoring"},
            "message": "analyze_metrics completed",
        }

    async def visualize_metrics(self, request: Any = None) -> Dict[str, Any]:
        """Visualize Metrics."""
        self.metrics.inc_request("visualize_metrics")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:visualize_metrics", config)
        self._state["visualize_metrics"] = config
        self._operations["visualize_metrics"] = self._operations.get("visualize_metrics", 0) + 1
        self.metrics.inc_operation("visualize_metrics")
        return {
            "feature": "visualize_metrics",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "Metrics Monitoring"},
            "message": "visualize_metrics completed",
        }

    async def alert_on_metrics(self, request: Any = None) -> Dict[str, Any]:
        """Alert On Metrics."""
        self.metrics.inc_request("alert_on_metrics")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:alert_on_metrics", config)
        self._state["alert_on_metrics"] = config
        self._operations["alert_on_metrics"] = self._operations.get("alert_on_metrics", 0) + 1
        self.metrics.inc_operation("alert_on_metrics")
        return {
            "feature": "alert_on_metrics",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "Metrics Monitoring"},
            "message": "alert_on_metrics completed",
        }

    async def monitor_sli_slo(self, request: Any = None) -> Dict[str, Any]:
        """Monitor Sli Slo."""
        self.metrics.inc_request("monitor_sli_slo")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:monitor_sli_slo", config)
        self._state["monitor_sli_slo"] = config
        self._operations["monitor_sli_slo"] = self._operations.get("monitor_sli_slo", 0) + 1
        self.metrics.inc_operation("monitor_sli_slo")
        return {
            "feature": "monitor_sli_slo",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "Metrics Monitoring"},
            "message": "monitor_sli_slo completed",
        }

    async def monitor_performance(self, request: Any = None) -> Dict[str, Any]:
        """Monitor Performance."""
        self.metrics.inc_request("monitor_performance")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:monitor_performance", config)
        self._state["monitor_performance"] = config
        self._operations["monitor_performance"] = self._operations.get("monitor_performance", 0) + 1
        self.metrics.inc_operation("monitor_performance")
        return {
            "feature": "monitor_performance",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "Metrics Monitoring"},
            "message": "monitor_performance completed",
        }

    async def monitor_resources(self, request: Any = None) -> Dict[str, Any]:
        """Monitor Resources."""
        self.metrics.inc_request("monitor_resources")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:monitor_resources", config)
        self._state["monitor_resources"] = config
        self._operations["monitor_resources"] = self._operations.get("monitor_resources", 0) + 1
        self.metrics.inc_operation("monitor_resources")
        return {
            "feature": "monitor_resources",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "Metrics Monitoring"},
            "message": "monitor_resources completed",
        }

    async def write_metrics_docs(self, request: Any = None) -> Dict[str, Any]:
        """Write Metrics Docs."""
        self.metrics.inc_request("write_metrics_docs")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:write_metrics_docs", config)
        self._state["write_metrics_docs"] = config
        self._operations["write_metrics_docs"] = self._operations.get("write_metrics_docs", 0) + 1
        self.metrics.inc_operation("write_metrics_docs")
        return {
            "feature": "write_metrics_docs",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "Metrics Monitoring"},
            "message": "write_metrics_docs completed",
        }

    async def test_and_optimize_metrics_monitoring(self, request: Any = None) -> Dict[str, Any]:
        """Test And Optimize Metrics Monitoring."""
        self.metrics.inc_request("test_and_optimize_metrics_monitoring")
        config = self._get_config(request)
        await self.cache.set(
            f"{settings.service_name}:test_and_optimize_metrics_monitoring", config
        )
        self._state["test_and_optimize_metrics_monitoring"] = config
        self._operations["test_and_optimize_metrics_monitoring"] = (
            self._operations.get("test_and_optimize_metrics_monitoring", 0) + 1
        )
        self.metrics.inc_operation("test_and_optimize_metrics_monitoring")
        return {
            "feature": "test_and_optimize_metrics_monitoring",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "Metrics Monitoring"},
            "message": "test_and_optimize_metrics_monitoring completed",
        }

    async def call(self, method: str, **kwargs: Any) -> Any:
        self.metrics.inc_request("call")
        if method == "list_methods":
            return await self.list_methods(**kwargs)
        if method == "get_stats":
            return await self.get_stats(**kwargs)
        if method == "get_state":
            return await self.get_state(**kwargs)
        if method == "backup_state":
            return await self.backup_state(**kwargs)
        if method == "restore_state":
            return await self.restore_state(**kwargs)
        if method in OPERATIONS:
            fn = getattr(self, method, None)
            if fn is None:
                raise ValueError(f"Unknown method: {method}")
            return await fn(**kwargs)
        raise ValueError(f"Unknown method: {method}")


Service = MetricsMonitoringService
