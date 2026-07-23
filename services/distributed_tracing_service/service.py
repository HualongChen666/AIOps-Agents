# -*- coding: utf-8 -*-
"""Core service logic for the Distributed Tracing microservice."""

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
    "collect_traces_jaeger",
    "store_traces",
    "analyze_traces",
    "visualize_traces",
    "search_traces",
    "alert_on_traces",
    "analyze_trace_performance",
    "identify_trace_bottlenecks",
    "write_tracing_docs",
    "test_and_optimize_distributed_tracing",
]


class DistributedTracingService:
    """Domain service for Distributed Tracing."""

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

    async def collect_traces_jaeger(self, request: Any = None) -> Dict[str, Any]:
        """Collect Traces Jaeger."""
        self.metrics.inc_request("collect_traces_jaeger")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:collect_traces_jaeger", config)
        self._state["collect_traces_jaeger"] = config
        self._operations["collect_traces_jaeger"] = (
            self._operations.get("collect_traces_jaeger", 0) + 1
        )
        self.metrics.inc_operation("collect_traces_jaeger")
        return {
            "feature": "collect_traces_jaeger",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "Distributed Tracing"},
            "message": "collect_traces_jaeger completed",
        }

    async def store_traces(self, request: Any = None) -> Dict[str, Any]:
        """Store Traces."""
        self.metrics.inc_request("store_traces")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:store_traces", config)
        self._state["store_traces"] = config
        self._operations["store_traces"] = self._operations.get("store_traces", 0) + 1
        self.metrics.inc_operation("store_traces")
        return {
            "feature": "store_traces",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "Distributed Tracing"},
            "message": "store_traces completed",
        }

    async def analyze_traces(self, request: Any = None) -> Dict[str, Any]:
        """Analyze Traces."""
        self.metrics.inc_request("analyze_traces")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:analyze_traces", config)
        self._state["analyze_traces"] = config
        self._operations["analyze_traces"] = self._operations.get("analyze_traces", 0) + 1
        self.metrics.inc_operation("analyze_traces")
        return {
            "feature": "analyze_traces",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "Distributed Tracing"},
            "message": "analyze_traces completed",
        }

    async def visualize_traces(self, request: Any = None) -> Dict[str, Any]:
        """Visualize Traces."""
        self.metrics.inc_request("visualize_traces")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:visualize_traces", config)
        self._state["visualize_traces"] = config
        self._operations["visualize_traces"] = self._operations.get("visualize_traces", 0) + 1
        self.metrics.inc_operation("visualize_traces")
        return {
            "feature": "visualize_traces",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "Distributed Tracing"},
            "message": "visualize_traces completed",
        }

    async def search_traces(self, request: Any = None) -> Dict[str, Any]:
        """Search Traces."""
        self.metrics.inc_request("search_traces")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:search_traces", config)
        self._state["search_traces"] = config
        self._operations["search_traces"] = self._operations.get("search_traces", 0) + 1
        self.metrics.inc_operation("search_traces")
        return {
            "feature": "search_traces",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "Distributed Tracing"},
            "message": "search_traces completed",
        }

    async def alert_on_traces(self, request: Any = None) -> Dict[str, Any]:
        """Alert On Traces."""
        self.metrics.inc_request("alert_on_traces")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:alert_on_traces", config)
        self._state["alert_on_traces"] = config
        self._operations["alert_on_traces"] = self._operations.get("alert_on_traces", 0) + 1
        self.metrics.inc_operation("alert_on_traces")
        return {
            "feature": "alert_on_traces",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "Distributed Tracing"},
            "message": "alert_on_traces completed",
        }

    async def analyze_trace_performance(self, request: Any = None) -> Dict[str, Any]:
        """Analyze Trace Performance."""
        self.metrics.inc_request("analyze_trace_performance")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:analyze_trace_performance", config)
        self._state["analyze_trace_performance"] = config
        self._operations["analyze_trace_performance"] = (
            self._operations.get("analyze_trace_performance", 0) + 1
        )
        self.metrics.inc_operation("analyze_trace_performance")
        return {
            "feature": "analyze_trace_performance",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "Distributed Tracing"},
            "message": "analyze_trace_performance completed",
        }

    async def identify_trace_bottlenecks(self, request: Any = None) -> Dict[str, Any]:
        """Identify Trace Bottlenecks."""
        self.metrics.inc_request("identify_trace_bottlenecks")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:identify_trace_bottlenecks", config)
        self._state["identify_trace_bottlenecks"] = config
        self._operations["identify_trace_bottlenecks"] = (
            self._operations.get("identify_trace_bottlenecks", 0) + 1
        )
        self.metrics.inc_operation("identify_trace_bottlenecks")
        return {
            "feature": "identify_trace_bottlenecks",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "Distributed Tracing"},
            "message": "identify_trace_bottlenecks completed",
        }

    async def write_tracing_docs(self, request: Any = None) -> Dict[str, Any]:
        """Write Tracing Docs."""
        self.metrics.inc_request("write_tracing_docs")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:write_tracing_docs", config)
        self._state["write_tracing_docs"] = config
        self._operations["write_tracing_docs"] = self._operations.get("write_tracing_docs", 0) + 1
        self.metrics.inc_operation("write_tracing_docs")
        return {
            "feature": "write_tracing_docs",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "Distributed Tracing"},
            "message": "write_tracing_docs completed",
        }

    async def test_and_optimize_distributed_tracing(self, request: Any = None) -> Dict[str, Any]:
        """Test And Optimize Distributed Tracing."""
        self.metrics.inc_request("test_and_optimize_distributed_tracing")
        config = self._get_config(request)
        await self.cache.set(
            f"{settings.service_name}:test_and_optimize_distributed_tracing", config
        )
        self._state["test_and_optimize_distributed_tracing"] = config
        self._operations["test_and_optimize_distributed_tracing"] = (
            self._operations.get("test_and_optimize_distributed_tracing", 0) + 1
        )
        self.metrics.inc_operation("test_and_optimize_distributed_tracing")
        return {
            "feature": "test_and_optimize_distributed_tracing",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "Distributed Tracing"},
            "message": "test_and_optimize_distributed_tracing completed",
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


Service = DistributedTracingService
