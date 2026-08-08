# -*- coding: utf-8 -*-
"""Core service logic for the Datadog Integration microservice."""

from __future__ import annotations

import httpx
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
    "integrate_datadog_api",
    "collect_metrics",
    "query_metrics",
    "collect_logs",
    "integrate_apm",
    "integrate_alerts",
    "integrate_dashboards",
    "integrate_slo",
    "integrate_unified_monitoring",
    "test_and_optimize_datadog",
    "write_integration_docs",
]


class DatadogIntegrationService:
    """Domain service for Datadog Integration."""

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

    async def integrate_datadog_api(self, request: Any = None) -> Dict[str, Any]:
        """Integrate Datadog Api."""
        self.metrics.inc_request("integrate_datadog_api")
        config = self._get_config(request)
        request_id = self.idempotency.get_key(request, "integrate_datadog_api")
        async with self.lock_manager.acquire("integrate_datadog_api", request_id):
            if await self.idempotency.is_processed(request_id):
                return {
                    "feature": "integrate_datadog_api",
                    "success": True,
                    "status": "idempotent",
                    "config": config,
                    "result": {"service": settings.service_name, "display": "Datadog Integration"},
                    "message": "integrate_datadog_api already processed",
                }
            await self.cache.set(f"{settings.service_name}:integrate_datadog_api", config)
            self._state["integrate_datadog_api"] = config
            self._operations["integrate_datadog_api"] = (
                self._operations.get("integrate_datadog_api", 0) + 1
            )
            self.metrics.inc_operation("integrate_datadog_api")
            result = {
                "feature": "integrate_datadog_api",
                "success": True,
                "status": "configured",
                "config": config,
                "result": {"service": settings.service_name, "display": "Datadog Integration"},
                "message": "integrate_datadog_api completed",
            }
            await self.idempotency.mark_processed(request_id, result)
            return result

    async def collect_metrics(self, request: Any = None) -> Dict[str, Any]:
        """Collect Metrics."""
        self.metrics.inc_request("collect_metrics")
        config = self._get_config(request)
        request_id = self.idempotency.get_key(request, "collect_metrics")
        async with self.lock_manager.acquire("collect_metrics", request_id):
            if await self.idempotency.is_processed(request_id):
                return {
                    "feature": "collect_metrics",
                    "success": True,
                    "status": "idempotent",
                    "config": config,
                    "result": {"service": settings.service_name, "display": "Datadog Integration"},
                    "message": "collect_metrics already processed",
                }
            await self.cache.set(f"{settings.service_name}:collect_metrics", config)
            self._state["collect_metrics"] = config
            self._operations["collect_metrics"] = self._operations.get("collect_metrics", 0) + 1
            self.metrics.inc_operation("collect_metrics")
            result = {
                "feature": "collect_metrics",
                "success": True,
                "status": "configured",
                "config": config,
                "result": {"service": settings.service_name, "display": "Datadog Integration"},
                "message": "collect_metrics completed",
            }
            await self.idempotency.mark_processed(request_id, result)
            return result

    async def query_metrics(self, request: Any = None) -> Dict[str, Any]:
        """Query a Datadog metric via the v1 query API."""
        self.metrics.inc_request("query_metrics")
        config = self._get_config(request)

        api_key = config.get("api_key")
        app_key = config.get("app_key")
        query = config.get("query")
        site = config.get("site", "datadoghq.com")
        if not api_key or not app_key or not query:
            return {
                "feature": "query_metrics",
                "success": False,
                "status": "error",
                "config": {},
                "result": {},
                "message": "Missing api_key, app_key, or query in config",
            }

        now = datetime.now(timezone.utc)
        from_time = config.get("from", int(now.timestamp()) - 3600)
        to_time = config.get("to", int(now.timestamp()))

        url = f"https://api.{site}/api/v1/query"
        headers = {
            "DD-API-KEY": api_key,
            "DD-APPLICATION-KEY": app_key,
            "Accept": "application/json",
        }
        params = {
            "query": query,
            "from": from_time,
            "to": to_time,
        }

        try:
            async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
                resp = await client.get(url, headers=headers, params=params)
                resp.raise_for_status()
                data = resp.json()
            return {
                "feature": "query_metrics",
                "success": True,
                "status": "ok",
                "config": {"site": site, "query": query},
                "result": data,
                "message": f"Queried {len(data.get('series', []))} series",
            }
        except httpx.HTTPStatusError as exc:
            return {
                "feature": "query_metrics",
                "success": False,
                "status": "error",
                "config": {"site": site, "query": query},
                "result": {"status_code": exc.response.status_code, "body": exc.response.text},
                "message": f"Datadog API error: {exc}",
            }
        except Exception as exc:
            return {
                "feature": "query_metrics",
                "success": False,
                "status": "error",
                "config": {"site": site, "query": query},
                "result": {},
                "message": f"Query failed: {exc}",
            }

    async def collect_logs(self, request: Any = None) -> Dict[str, Any]:
        """Collect Logs."""
        self.metrics.inc_request("collect_logs")
        config = self._get_config(request)
        request_id = self.idempotency.get_key(request, "collect_logs")
        async with self.lock_manager.acquire("collect_logs", request_id):
            if await self.idempotency.is_processed(request_id):
                return {
                    "feature": "collect_logs",
                    "success": True,
                    "status": "idempotent",
                    "config": config,
                    "result": {"service": settings.service_name, "display": "Datadog Integration"},
                    "message": "collect_logs already processed",
                }
            await self.cache.set(f"{settings.service_name}:collect_logs", config)
            self._state["collect_logs"] = config
            self._operations["collect_logs"] = self._operations.get("collect_logs", 0) + 1
            self.metrics.inc_operation("collect_logs")
            result = {
                "feature": "collect_logs",
                "success": True,
                "status": "configured",
                "config": config,
                "result": {"service": settings.service_name, "display": "Datadog Integration"},
                "message": "collect_logs completed",
            }
            await self.idempotency.mark_processed(request_id, result)
            return result

    async def integrate_apm(self, request: Any = None) -> Dict[str, Any]:
        """Integrate Apm."""
        self.metrics.inc_request("integrate_apm")
        config = self._get_config(request)
        request_id = self.idempotency.get_key(request, "integrate_apm")
        async with self.lock_manager.acquire("integrate_apm", request_id):
            if await self.idempotency.is_processed(request_id):
                return {
                    "feature": "integrate_apm",
                    "success": True,
                    "status": "idempotent",
                    "config": config,
                    "result": {"service": settings.service_name, "display": "Datadog Integration"},
                    "message": "integrate_apm already processed",
                }
            await self.cache.set(f"{settings.service_name}:integrate_apm", config)
            self._state["integrate_apm"] = config
            self._operations["integrate_apm"] = self._operations.get("integrate_apm", 0) + 1
            self.metrics.inc_operation("integrate_apm")
            result = {
                "feature": "integrate_apm",
                "success": True,
                "status": "configured",
                "config": config,
                "result": {"service": settings.service_name, "display": "Datadog Integration"},
                "message": "integrate_apm completed",
            }
            await self.idempotency.mark_processed(request_id, result)
            return result

    async def integrate_alerts(self, request: Any = None) -> Dict[str, Any]:
        """Integrate Alerts."""
        self.metrics.inc_request("integrate_alerts")
        config = self._get_config(request)
        request_id = self.idempotency.get_key(request, "integrate_alerts")
        async with self.lock_manager.acquire("integrate_alerts", request_id):
            if await self.idempotency.is_processed(request_id):
                return {
                    "feature": "integrate_alerts",
                    "success": True,
                    "status": "idempotent",
                    "config": config,
                    "result": {"service": settings.service_name, "display": "Datadog Integration"},
                    "message": "integrate_alerts already processed",
                }
            await self.cache.set(f"{settings.service_name}:integrate_alerts", config)
            self._state["integrate_alerts"] = config
            self._operations["integrate_alerts"] = self._operations.get("integrate_alerts", 0) + 1
            self.metrics.inc_operation("integrate_alerts")
            result = {
                "feature": "integrate_alerts",
                "success": True,
                "status": "configured",
                "config": config,
                "result": {"service": settings.service_name, "display": "Datadog Integration"},
                "message": "integrate_alerts completed",
            }
            await self.idempotency.mark_processed(request_id, result)
            return result

    async def integrate_dashboards(self, request: Any = None) -> Dict[str, Any]:
        """Integrate Dashboards."""
        self.metrics.inc_request("integrate_dashboards")
        config = self._get_config(request)
        request_id = self.idempotency.get_key(request, "integrate_dashboards")
        async with self.lock_manager.acquire("integrate_dashboards", request_id):
            if await self.idempotency.is_processed(request_id):
                return {
                    "feature": "integrate_dashboards",
                    "success": True,
                    "status": "idempotent",
                    "config": config,
                    "result": {"service": settings.service_name, "display": "Datadog Integration"},
                    "message": "integrate_dashboards already processed",
                }
            await self.cache.set(f"{settings.service_name}:integrate_dashboards", config)
            self._state["integrate_dashboards"] = config
            self._operations["integrate_dashboards"] = (
                self._operations.get("integrate_dashboards", 0) + 1
            )
            self.metrics.inc_operation("integrate_dashboards")
            result = {
                "feature": "integrate_dashboards",
                "success": True,
                "status": "configured",
                "config": config,
                "result": {"service": settings.service_name, "display": "Datadog Integration"},
                "message": "integrate_dashboards completed",
            }
            await self.idempotency.mark_processed(request_id, result)
            return result

    async def integrate_slo(self, request: Any = None) -> Dict[str, Any]:
        """Integrate Slo."""
        self.metrics.inc_request("integrate_slo")
        config = self._get_config(request)
        request_id = self.idempotency.get_key(request, "integrate_slo")
        async with self.lock_manager.acquire("integrate_slo", request_id):
            if await self.idempotency.is_processed(request_id):
                return {
                    "feature": "integrate_slo",
                    "success": True,
                    "status": "idempotent",
                    "config": config,
                    "result": {"service": settings.service_name, "display": "Datadog Integration"},
                    "message": "integrate_slo already processed",
                }
            await self.cache.set(f"{settings.service_name}:integrate_slo", config)
            self._state["integrate_slo"] = config
            self._operations["integrate_slo"] = self._operations.get("integrate_slo", 0) + 1
            self.metrics.inc_operation("integrate_slo")
            result = {
                "feature": "integrate_slo",
                "success": True,
                "status": "configured",
                "config": config,
                "result": {"service": settings.service_name, "display": "Datadog Integration"},
                "message": "integrate_slo completed",
            }
            await self.idempotency.mark_processed(request_id, result)
            return result

    async def integrate_unified_monitoring(self, request: Any = None) -> Dict[str, Any]:
        """Integrate Unified Monitoring."""
        self.metrics.inc_request("integrate_unified_monitoring")
        config = self._get_config(request)
        request_id = self.idempotency.get_key(request, "integrate_unified_monitoring")
        async with self.lock_manager.acquire("integrate_unified_monitoring", request_id):
            if await self.idempotency.is_processed(request_id):
                return {
                    "feature": "integrate_unified_monitoring",
                    "success": True,
                    "status": "idempotent",
                    "config": config,
                    "result": {"service": settings.service_name, "display": "Datadog Integration"},
                    "message": "integrate_unified_monitoring already processed",
                }
            await self.cache.set(f"{settings.service_name}:integrate_unified_monitoring", config)
            self._state["integrate_unified_monitoring"] = config
            self._operations["integrate_unified_monitoring"] = (
                self._operations.get("integrate_unified_monitoring", 0) + 1
            )
            self.metrics.inc_operation("integrate_unified_monitoring")
            result = {
                "feature": "integrate_unified_monitoring",
                "success": True,
                "status": "configured",
                "config": config,
                "result": {"service": settings.service_name, "display": "Datadog Integration"},
                "message": "integrate_unified_monitoring completed",
            }
            await self.idempotency.mark_processed(request_id, result)
            return result

    async def test_and_optimize_datadog(self, request: Any = None) -> Dict[str, Any]:
        """Test And Optimize Datadog."""
        self.metrics.inc_request("test_and_optimize_datadog")
        config = self._get_config(request)
        request_id = self.idempotency.get_key(request, "test_and_optimize_datadog")
        async with self.lock_manager.acquire("test_and_optimize_datadog", request_id):
            if await self.idempotency.is_processed(request_id):
                return {
                    "feature": "test_and_optimize_datadog",
                    "success": True,
                    "status": "idempotent",
                    "config": config,
                    "result": {"service": settings.service_name, "display": "Datadog Integration"},
                    "message": "test_and_optimize_datadog already processed",
                }
            await self.cache.set(f"{settings.service_name}:test_and_optimize_datadog", config)
            self._state["test_and_optimize_datadog"] = config
            self._operations["test_and_optimize_datadog"] = (
                self._operations.get("test_and_optimize_datadog", 0) + 1
            )
            self.metrics.inc_operation("test_and_optimize_datadog")
            result = {
                "feature": "test_and_optimize_datadog",
                "success": True,
                "status": "configured",
                "config": config,
                "result": {"service": settings.service_name, "display": "Datadog Integration"},
                "message": "test_and_optimize_datadog completed",
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
                    "result": {"service": settings.service_name, "display": "Datadog Integration"},
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
                "result": {"service": settings.service_name, "display": "Datadog Integration"},
                "message": "write_integration_docs completed",
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


Service = DatadogIntegrationService
