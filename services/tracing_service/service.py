# -*- coding: utf-8 -*-
"""Core service logic for the Tracing microservice."""

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
    "evaluate_tracing_backend",
    "select_tracing_backend",
    "install_jaeger",
    "install_zipkin",
    "install_skywalking",
    "configure_collector",
    "configure_storage",
    "install_opentelemetry_sdk",
    "configure_automatic_tracing",
    "configure_manual_tracing",
    "propagate_context",
    "add_span_tags",
    "add_baggage",
    "configure_sampling",
    "configure_span_filtering",
    "integrate_tracing_dashboard",
    "test_and_optimize_tracing",
]


class TracingService:
    """Domain service for Tracing."""

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

    async def evaluate_tracing_backend(self, request: Any = None) -> Dict[str, Any]:
        """Evaluate Tracing Backend."""
        self.metrics.inc_request("evaluate_tracing_backend")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:evaluate_tracing_backend", config)
        self._state["evaluate_tracing_backend"] = config
        self._operations["evaluate_tracing_backend"] = (
            self._operations.get("evaluate_tracing_backend", 0) + 1
        )
        self.metrics.inc_operation("evaluate_tracing_backend")
        return {
            "feature": "evaluate_tracing_backend",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "Tracing"},
            "message": "evaluate_tracing_backend completed",
        }

    async def select_tracing_backend(self, request: Any = None) -> Dict[str, Any]:
        """Select Tracing Backend."""
        self.metrics.inc_request("select_tracing_backend")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:select_tracing_backend", config)
        self._state["select_tracing_backend"] = config
        self._operations["select_tracing_backend"] = (
            self._operations.get("select_tracing_backend", 0) + 1
        )
        self.metrics.inc_operation("select_tracing_backend")
        return {
            "feature": "select_tracing_backend",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "Tracing"},
            "message": "select_tracing_backend completed",
        }

    async def install_jaeger(self, request: Any = None) -> Dict[str, Any]:
        """Install Jaeger."""
        self.metrics.inc_request("install_jaeger")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:install_jaeger", config)
        self._state["install_jaeger"] = config
        self._operations["install_jaeger"] = self._operations.get("install_jaeger", 0) + 1
        self.metrics.inc_operation("install_jaeger")
        return {
            "feature": "install_jaeger",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "Tracing"},
            "message": "install_jaeger completed",
        }

    async def install_zipkin(self, request: Any = None) -> Dict[str, Any]:
        """Install Zipkin."""
        self.metrics.inc_request("install_zipkin")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:install_zipkin", config)
        self._state["install_zipkin"] = config
        self._operations["install_zipkin"] = self._operations.get("install_zipkin", 0) + 1
        self.metrics.inc_operation("install_zipkin")
        return {
            "feature": "install_zipkin",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "Tracing"},
            "message": "install_zipkin completed",
        }

    async def install_skywalking(self, request: Any = None) -> Dict[str, Any]:
        """Install Skywalking."""
        self.metrics.inc_request("install_skywalking")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:install_skywalking", config)
        self._state["install_skywalking"] = config
        self._operations["install_skywalking"] = self._operations.get("install_skywalking", 0) + 1
        self.metrics.inc_operation("install_skywalking")
        return {
            "feature": "install_skywalking",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "Tracing"},
            "message": "install_skywalking completed",
        }

    async def configure_collector(self, request: Any = None) -> Dict[str, Any]:
        """Configure Collector."""
        self.metrics.inc_request("configure_collector")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:configure_collector", config)
        self._state["configure_collector"] = config
        self._operations["configure_collector"] = self._operations.get("configure_collector", 0) + 1
        self.metrics.inc_operation("configure_collector")
        return {
            "feature": "configure_collector",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "Tracing"},
            "message": "configure_collector completed",
        }

    async def configure_storage(self, request: Any = None) -> Dict[str, Any]:
        """Configure Storage."""
        self.metrics.inc_request("configure_storage")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:configure_storage", config)
        self._state["configure_storage"] = config
        self._operations["configure_storage"] = self._operations.get("configure_storage", 0) + 1
        self.metrics.inc_operation("configure_storage")
        return {
            "feature": "configure_storage",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "Tracing"},
            "message": "configure_storage completed",
        }

    async def install_opentelemetry_sdk(self, request: Any = None) -> Dict[str, Any]:
        """Install Opentelemetry Sdk."""
        self.metrics.inc_request("install_opentelemetry_sdk")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:install_opentelemetry_sdk", config)
        self._state["install_opentelemetry_sdk"] = config
        self._operations["install_opentelemetry_sdk"] = (
            self._operations.get("install_opentelemetry_sdk", 0) + 1
        )
        self.metrics.inc_operation("install_opentelemetry_sdk")
        return {
            "feature": "install_opentelemetry_sdk",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "Tracing"},
            "message": "install_opentelemetry_sdk completed",
        }

    async def configure_automatic_tracing(self, request: Any = None) -> Dict[str, Any]:
        """Configure Automatic Tracing."""
        self.metrics.inc_request("configure_automatic_tracing")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:configure_automatic_tracing", config)
        self._state["configure_automatic_tracing"] = config
        self._operations["configure_automatic_tracing"] = (
            self._operations.get("configure_automatic_tracing", 0) + 1
        )
        self.metrics.inc_operation("configure_automatic_tracing")
        return {
            "feature": "configure_automatic_tracing",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "Tracing"},
            "message": "configure_automatic_tracing completed",
        }

    async def configure_manual_tracing(self, request: Any = None) -> Dict[str, Any]:
        """Configure Manual Tracing."""
        self.metrics.inc_request("configure_manual_tracing")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:configure_manual_tracing", config)
        self._state["configure_manual_tracing"] = config
        self._operations["configure_manual_tracing"] = (
            self._operations.get("configure_manual_tracing", 0) + 1
        )
        self.metrics.inc_operation("configure_manual_tracing")
        return {
            "feature": "configure_manual_tracing",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "Tracing"},
            "message": "configure_manual_tracing completed",
        }

    async def propagate_context(self, request: Any = None) -> Dict[str, Any]:
        """Propagate Context."""
        self.metrics.inc_request("propagate_context")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:propagate_context", config)
        self._state["propagate_context"] = config
        self._operations["propagate_context"] = self._operations.get("propagate_context", 0) + 1
        self.metrics.inc_operation("propagate_context")
        return {
            "feature": "propagate_context",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "Tracing"},
            "message": "propagate_context completed",
        }

    async def add_span_tags(self, request: Any = None) -> Dict[str, Any]:
        """Add Span Tags."""
        self.metrics.inc_request("add_span_tags")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:add_span_tags", config)
        self._state["add_span_tags"] = config
        self._operations["add_span_tags"] = self._operations.get("add_span_tags", 0) + 1
        self.metrics.inc_operation("add_span_tags")
        return {
            "feature": "add_span_tags",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "Tracing"},
            "message": "add_span_tags completed",
        }

    async def add_baggage(self, request: Any = None) -> Dict[str, Any]:
        """Add Baggage."""
        self.metrics.inc_request("add_baggage")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:add_baggage", config)
        self._state["add_baggage"] = config
        self._operations["add_baggage"] = self._operations.get("add_baggage", 0) + 1
        self.metrics.inc_operation("add_baggage")
        return {
            "feature": "add_baggage",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "Tracing"},
            "message": "add_baggage completed",
        }

    async def configure_sampling(self, request: Any = None) -> Dict[str, Any]:
        """Configure Sampling."""
        self.metrics.inc_request("configure_sampling")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:configure_sampling", config)
        self._state["configure_sampling"] = config
        self._operations["configure_sampling"] = self._operations.get("configure_sampling", 0) + 1
        self.metrics.inc_operation("configure_sampling")
        return {
            "feature": "configure_sampling",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "Tracing"},
            "message": "configure_sampling completed",
        }

    async def configure_span_filtering(self, request: Any = None) -> Dict[str, Any]:
        """Configure Span Filtering."""
        self.metrics.inc_request("configure_span_filtering")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:configure_span_filtering", config)
        self._state["configure_span_filtering"] = config
        self._operations["configure_span_filtering"] = (
            self._operations.get("configure_span_filtering", 0) + 1
        )
        self.metrics.inc_operation("configure_span_filtering")
        return {
            "feature": "configure_span_filtering",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "Tracing"},
            "message": "configure_span_filtering completed",
        }

    async def integrate_tracing_dashboard(self, request: Any = None) -> Dict[str, Any]:
        """Integrate Tracing Dashboard."""
        self.metrics.inc_request("integrate_tracing_dashboard")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:integrate_tracing_dashboard", config)
        self._state["integrate_tracing_dashboard"] = config
        self._operations["integrate_tracing_dashboard"] = (
            self._operations.get("integrate_tracing_dashboard", 0) + 1
        )
        self.metrics.inc_operation("integrate_tracing_dashboard")
        return {
            "feature": "integrate_tracing_dashboard",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "Tracing"},
            "message": "integrate_tracing_dashboard completed",
        }

    async def test_and_optimize_tracing(self, request: Any = None) -> Dict[str, Any]:
        """Test And Optimize Tracing."""
        self.metrics.inc_request("test_and_optimize_tracing")
        config = self._get_config(request)
        await self.cache.set(f"{settings.service_name}:test_and_optimize_tracing", config)
        self._state["test_and_optimize_tracing"] = config
        self._operations["test_and_optimize_tracing"] = (
            self._operations.get("test_and_optimize_tracing", 0) + 1
        )
        self.metrics.inc_operation("test_and_optimize_tracing")
        return {
            "feature": "test_and_optimize_tracing",
            "success": True,
            "status": "configured",
            "config": config,
            "result": {"service": settings.service_name, "display": "Tracing"},
            "message": "test_and_optimize_tracing completed",
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


Service = TracingService
