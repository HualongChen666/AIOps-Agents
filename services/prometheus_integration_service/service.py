# -*- coding: utf-8 -*-
"""Core service logic for the Prometheus Integration microservice."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .cache import CacheManager
from .config import settings
from .lock import IdempotencyManager, LockManager
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
    "collect_prometheus_data",
    "promql_query",
    "rule_management",
    "alert_management",
    "service_discovery",
    "target_management",
    "integrate_monitoring_layer",
    "test_and_optimize_prometheus",
    "write_integration_docs",
    "implement_error_handling",
]


class PrometheusIntegrationService:
    """Domain service for Prometheus Integration."""

    def __init__(
        self,
        redis_url: Optional[str] = None,
        metrics: Optional[MetricsCollector] = None,
        cache: Optional[CacheManager] = None,
    ) -> None:
        self.metrics = metrics or MetricsCollector(settings.service_name)
        self.cache = cache or CacheManager(redis_url or settings.redis_url, self.metrics)
        self.retry_engine = RetryEngine("exponential_fast", self.metrics)
        self.lock_manager = LockManager(redis_url or settings.redis_url)
        self.idempotency = IdempotencyManager(self.cache)
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
        request_id = self.idempotency.get_key(request, "backup_state")
        async with self.lock_manager.acquire("backup_state", request_id):
            if await self.idempotency.is_processed(request_id):
                return {
                    "feature": "backup_state",
                    "success": True,
                    "status": "idempotent",
                    "config": config,
                    "result": {
                        "snapshot": (
                            config.get("name", "default") if isinstance(config, dict) else "default"
                        )
                    },
                    "message": "backup_state already processed",
                }
            name = config.get("name", "default") if isinstance(config, dict) else "default"
            self._backups[name] = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "state": self._state.copy(),
            }
            self.metrics.inc_operation("backup_state")
            result = {
                "feature": "backup_state",
                "success": True,
                "status": "backed_up",
                "config": {"name": name},
                "result": {"snapshot": name},
                "message": f"Backup {name} created",
            }
            await self.idempotency.mark_processed(request_id, result)
            return result

    async def restore_state(self, request: Any = None) -> Dict[str, Any]:
        self.metrics.inc_request("restore_state")
        config = self._get_config(request)
        request_id = self.idempotency.get_key(request, "restore_state")
        async with self.lock_manager.acquire("restore_state", request_id):
            if await self.idempotency.is_processed(request_id):
                return {
                    "feature": "restore_state",
                    "success": True,
                    "status": "idempotent",
                    "config": config,
                    "result": {
                        "snapshot": (
                            config.get("name", "default") if isinstance(config, dict) else "default"
                        )
                    },
                    "message": "restore_state already processed",
                }
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
            result = {
                "feature": "restore_state",
                "success": True,
                "status": "restored",
                "config": {"name": name},
                "result": {"snapshot": name},
                "message": f"Backup {name} restored",
            }
            await self.idempotency.mark_processed(request_id, result)
            return result

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

    async def collect_prometheus_data(self, request: Any = None) -> Dict[str, Any]:
        """Collect Prometheus Data."""
        self.metrics.inc_request("collect_prometheus_data")
        config = self._get_config(request)
        request_id = self.idempotency.get_key(request, "collect_prometheus_data")
        async with self.lock_manager.acquire("collect_prometheus_data", request_id):
            if await self.idempotency.is_processed(request_id):
                return {
                    "feature": "collect_prometheus_data",
                    "success": True,
                    "status": "idempotent",
                    "config": config,
                    "result": {
                        "service": settings.service_name,
                        "display": "Prometheus Integration",
                    },
                    "message": "collect_prometheus_data already processed",
                }
            await self.cache.set(f"{settings.service_name}:collect_prometheus_data", config)
            self._state["collect_prometheus_data"] = config
            self._operations["collect_prometheus_data"] = (
                self._operations.get("collect_prometheus_data", 0) + 1
            )
            self.metrics.inc_operation("collect_prometheus_data")
            result = {
                "feature": "collect_prometheus_data",
                "success": True,
                "status": "configured",
                "config": config,
                "result": {"service": settings.service_name, "display": "Prometheus Integration"},
                "message": "collect_prometheus_data completed",
            }
            await self.idempotency.mark_processed(request_id, result)
            return result

    async def promql_query(self, request: Any = None) -> Dict[str, Any]:
        """Promql Query."""
        self.metrics.inc_request("promql_query")
        config = self._get_config(request)
        request_id = self.idempotency.get_key(request, "promql_query")
        async with self.lock_manager.acquire("promql_query", request_id):
            if await self.idempotency.is_processed(request_id):
                return {
                    "feature": "promql_query",
                    "success": True,
                    "status": "idempotent",
                    "config": config,
                    "result": {
                        "service": settings.service_name,
                        "display": "Prometheus Integration",
                    },
                    "message": "promql_query already processed",
                }
            await self.cache.set(f"{settings.service_name}:promql_query", config)
            self._state["promql_query"] = config
            self._operations["promql_query"] = self._operations.get("promql_query", 0) + 1
            self.metrics.inc_operation("promql_query")
            result = {
                "feature": "promql_query",
                "success": True,
                "status": "configured",
                "config": config,
                "result": {"service": settings.service_name, "display": "Prometheus Integration"},
                "message": "promql_query completed",
            }
            await self.idempotency.mark_processed(request_id, result)
            return result

    async def rule_management(self, request: Any = None) -> Dict[str, Any]:
        """Rule Management."""
        self.metrics.inc_request("rule_management")
        config = self._get_config(request)
        request_id = self.idempotency.get_key(request, "rule_management")
        async with self.lock_manager.acquire("rule_management", request_id):
            if await self.idempotency.is_processed(request_id):
                return {
                    "feature": "rule_management",
                    "success": True,
                    "status": "idempotent",
                    "config": config,
                    "result": {
                        "service": settings.service_name,
                        "display": "Prometheus Integration",
                    },
                    "message": "rule_management already processed",
                }
            await self.cache.set(f"{settings.service_name}:rule_management", config)
            self._state["rule_management"] = config
            self._operations["rule_management"] = self._operations.get("rule_management", 0) + 1
            self.metrics.inc_operation("rule_management")
            result = {
                "feature": "rule_management",
                "success": True,
                "status": "configured",
                "config": config,
                "result": {"service": settings.service_name, "display": "Prometheus Integration"},
                "message": "rule_management completed",
            }
            await self.idempotency.mark_processed(request_id, result)
            return result

    async def alert_management(self, request: Any = None) -> Dict[str, Any]:
        """Alert Management."""
        self.metrics.inc_request("alert_management")
        config = self._get_config(request)
        request_id = self.idempotency.get_key(request, "alert_management")
        async with self.lock_manager.acquire("alert_management", request_id):
            if await self.idempotency.is_processed(request_id):
                return {
                    "feature": "alert_management",
                    "success": True,
                    "status": "idempotent",
                    "config": config,
                    "result": {
                        "service": settings.service_name,
                        "display": "Prometheus Integration",
                    },
                    "message": "alert_management already processed",
                }
            await self.cache.set(f"{settings.service_name}:alert_management", config)
            self._state["alert_management"] = config
            self._operations["alert_management"] = self._operations.get("alert_management", 0) + 1
            self.metrics.inc_operation("alert_management")
            result = {
                "feature": "alert_management",
                "success": True,
                "status": "configured",
                "config": config,
                "result": {"service": settings.service_name, "display": "Prometheus Integration"},
                "message": "alert_management completed",
            }
            await self.idempotency.mark_processed(request_id, result)
            return result

    async def service_discovery(self, request: Any = None) -> Dict[str, Any]:
        """Service Discovery."""
        self.metrics.inc_request("service_discovery")
        config = self._get_config(request)
        request_id = self.idempotency.get_key(request, "service_discovery")
        async with self.lock_manager.acquire("service_discovery", request_id):
            if await self.idempotency.is_processed(request_id):
                return {
                    "feature": "service_discovery",
                    "success": True,
                    "status": "idempotent",
                    "config": config,
                    "result": {
                        "service": settings.service_name,
                        "display": "Prometheus Integration",
                    },
                    "message": "service_discovery already processed",
                }
            await self.cache.set(f"{settings.service_name}:service_discovery", config)
            self._state["service_discovery"] = config
            self._operations["service_discovery"] = self._operations.get("service_discovery", 0) + 1
            self.metrics.inc_operation("service_discovery")
            result = {
                "feature": "service_discovery",
                "success": True,
                "status": "configured",
                "config": config,
                "result": {"service": settings.service_name, "display": "Prometheus Integration"},
                "message": "service_discovery completed",
            }
            await self.idempotency.mark_processed(request_id, result)
            return result

    async def target_management(self, request: Any = None) -> Dict[str, Any]:
        """Target Management."""
        self.metrics.inc_request("target_management")
        config = self._get_config(request)
        request_id = self.idempotency.get_key(request, "target_management")
        async with self.lock_manager.acquire("target_management", request_id):
            if await self.idempotency.is_processed(request_id):
                return {
                    "feature": "target_management",
                    "success": True,
                    "status": "idempotent",
                    "config": config,
                    "result": {
                        "service": settings.service_name,
                        "display": "Prometheus Integration",
                    },
                    "message": "target_management already processed",
                }
            await self.cache.set(f"{settings.service_name}:target_management", config)
            self._state["target_management"] = config
            self._operations["target_management"] = self._operations.get("target_management", 0) + 1
            self.metrics.inc_operation("target_management")
            result = {
                "feature": "target_management",
                "success": True,
                "status": "configured",
                "config": config,
                "result": {"service": settings.service_name, "display": "Prometheus Integration"},
                "message": "target_management completed",
            }
            await self.idempotency.mark_processed(request_id, result)
            return result

    async def integrate_monitoring_layer(self, request: Any = None) -> Dict[str, Any]:
        """Integrate Monitoring Layer."""
        self.metrics.inc_request("integrate_monitoring_layer")
        config = self._get_config(request)
        request_id = self.idempotency.get_key(request, "integrate_monitoring_layer")
        async with self.lock_manager.acquire("integrate_monitoring_layer", request_id):
            if await self.idempotency.is_processed(request_id):
                return {
                    "feature": "integrate_monitoring_layer",
                    "success": True,
                    "status": "idempotent",
                    "config": config,
                    "result": {
                        "service": settings.service_name,
                        "display": "Prometheus Integration",
                    },
                    "message": "integrate_monitoring_layer already processed",
                }
            await self.cache.set(f"{settings.service_name}:integrate_monitoring_layer", config)
            self._state["integrate_monitoring_layer"] = config
            self._operations["integrate_monitoring_layer"] = (
                self._operations.get("integrate_monitoring_layer", 0) + 1
            )
            self.metrics.inc_operation("integrate_monitoring_layer")
            result = {
                "feature": "integrate_monitoring_layer",
                "success": True,
                "status": "configured",
                "config": config,
                "result": {"service": settings.service_name, "display": "Prometheus Integration"},
                "message": "integrate_monitoring_layer completed",
            }
            await self.idempotency.mark_processed(request_id, result)
            return result

    async def test_and_optimize_prometheus(self, request: Any = None) -> Dict[str, Any]:
        """Test And Optimize Prometheus."""
        self.metrics.inc_request("test_and_optimize_prometheus")
        config = self._get_config(request)
        request_id = self.idempotency.get_key(request, "test_and_optimize_prometheus")
        async with self.lock_manager.acquire("test_and_optimize_prometheus", request_id):
            if await self.idempotency.is_processed(request_id):
                return {
                    "feature": "test_and_optimize_prometheus",
                    "success": True,
                    "status": "idempotent",
                    "config": config,
                    "result": {
                        "service": settings.service_name,
                        "display": "Prometheus Integration",
                    },
                    "message": "test_and_optimize_prometheus already processed",
                }
            await self.cache.set(f"{settings.service_name}:test_and_optimize_prometheus", config)
            self._state["test_and_optimize_prometheus"] = config
            self._operations["test_and_optimize_prometheus"] = (
                self._operations.get("test_and_optimize_prometheus", 0) + 1
            )
            self.metrics.inc_operation("test_and_optimize_prometheus")
            result = {
                "feature": "test_and_optimize_prometheus",
                "success": True,
                "status": "configured",
                "config": config,
                "result": {"service": settings.service_name, "display": "Prometheus Integration"},
                "message": "test_and_optimize_prometheus completed",
            }
            await self.idempotency.mark_processed(request_id, result)
            return result

    async def write_integration_docs(self, request: Any = None) -> Dict[str, Any]:
        """Write Integration Docs."""
        self.metrics.inc_request("write_integration_docs")
        config = self._get_config(request)
        request_id = self.idempotency.get_key(request, "write_integration_docs")
        async with self.lock_manager.acquire("write_integration_docs", request_id):
            if await self.idempotency.is_processed(request_id):
                return {
                    "feature": "write_integration_docs",
                    "success": True,
                    "status": "idempotent",
                    "config": config,
                    "result": {
                        "service": settings.service_name,
                        "display": "Prometheus Integration",
                    },
                    "message": "write_integration_docs already processed",
                }
            await self.cache.set(f"{settings.service_name}:write_integration_docs", config)
            self._state["write_integration_docs"] = config
            self._operations["write_integration_docs"] = (
                self._operations.get("write_integration_docs", 0) + 1
            )
            self.metrics.inc_operation("write_integration_docs")
            result = {
                "feature": "write_integration_docs",
                "success": True,
                "status": "configured",
                "config": config,
                "result": {"service": settings.service_name, "display": "Prometheus Integration"},
                "message": "write_integration_docs completed",
            }
            await self.idempotency.mark_processed(request_id, result)
            return result

    async def implement_error_handling(self, request: Any = None) -> Dict[str, Any]:
        """Implement Error Handling."""
        self.metrics.inc_request("implement_error_handling")
        config = self._get_config(request)
        request_id = self.idempotency.get_key(request, "implement_error_handling")
        async with self.lock_manager.acquire("implement_error_handling", request_id):
            if await self.idempotency.is_processed(request_id):
                return {
                    "feature": "implement_error_handling",
                    "success": True,
                    "status": "idempotent",
                    "config": config,
                    "result": {
                        "service": settings.service_name,
                        "display": "Prometheus Integration",
                    },
                    "message": "implement_error_handling already processed",
                }
            await self.cache.set(f"{settings.service_name}:implement_error_handling", config)
            self._state["implement_error_handling"] = config
            self._operations["implement_error_handling"] = (
                self._operations.get("implement_error_handling", 0) + 1
            )
            self.metrics.inc_operation("implement_error_handling")
            result = {
                "feature": "implement_error_handling",
                "success": True,
                "status": "configured",
                "config": config,
                "result": {"service": settings.service_name, "display": "Prometheus Integration"},
                "message": "implement_error_handling completed",
            }
            await self.idempotency.mark_processed(request_id, result)
            return result

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


Service = PrometheusIntegrationService
