# -*- coding: utf-8 -*-
"""Core service logic for the Grafana Integration microservice."""

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
    "manage_dashboards",
    "configure_datasources",
    "manage_panels",
    "manage_users",
    "manage_organizations",
    "manage_permissions",
    "integrate_visualization_layer",
    "query_data",
    "test_and_optimize_grafana",
    "write_integration_docs",
    "manage_templates",
]


class GrafanaIntegrationService:
    """Domain service for Grafana Integration."""

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

    async def manage_dashboards(self, request: Any = None) -> Dict[str, Any]:
        """Manage Dashboards."""
        self.metrics.inc_request("manage_dashboards")
        config = self._get_config(request)
        request_id = self.idempotency.get_key(request, "manage_dashboards")
        async with self.lock_manager.acquire("manage_dashboards", request_id):
            if await self.idempotency.is_processed(request_id):
                return {
                    "feature": "manage_dashboards",
                    "success": True,
                    "status": "idempotent",
                    "config": config,
                    "result": {"service": settings.service_name, "display": "Grafana Integration"},
                    "message": "manage_dashboards already processed",
                }
            await self.cache.set(f"{settings.service_name}:manage_dashboards", config)
            self._state["manage_dashboards"] = config
            self._operations["manage_dashboards"] = self._operations.get("manage_dashboards", 0) + 1
            self.metrics.inc_operation("manage_dashboards")
            result = {
                "feature": "manage_dashboards",
                "success": True,
                "status": "configured",
                "config": config,
                "result": {"service": settings.service_name, "display": "Grafana Integration"},
                "message": "manage_dashboards completed",
            }
            await self.idempotency.mark_processed(request_id, result)
            return result

    async def configure_datasources(self, request: Any = None) -> Dict[str, Any]:
        """Configure Datasources."""
        self.metrics.inc_request("configure_datasources")
        config = self._get_config(request)
        request_id = self.idempotency.get_key(request, "configure_datasources")
        async with self.lock_manager.acquire("configure_datasources", request_id):
            if await self.idempotency.is_processed(request_id):
                return {
                    "feature": "configure_datasources",
                    "success": True,
                    "status": "idempotent",
                    "config": config,
                    "result": {"service": settings.service_name, "display": "Grafana Integration"},
                    "message": "configure_datasources already processed",
                }
            await self.cache.set(f"{settings.service_name}:configure_datasources", config)
            self._state["configure_datasources"] = config
            self._operations["configure_datasources"] = (
                self._operations.get("configure_datasources", 0) + 1
            )
            self.metrics.inc_operation("configure_datasources")
            result = {
                "feature": "configure_datasources",
                "success": True,
                "status": "configured",
                "config": config,
                "result": {"service": settings.service_name, "display": "Grafana Integration"},
                "message": "configure_datasources completed",
            }
            await self.idempotency.mark_processed(request_id, result)
            return result

    async def manage_panels(self, request: Any = None) -> Dict[str, Any]:
        """Manage Panels."""
        self.metrics.inc_request("manage_panels")
        config = self._get_config(request)
        request_id = self.idempotency.get_key(request, "manage_panels")
        async with self.lock_manager.acquire("manage_panels", request_id):
            if await self.idempotency.is_processed(request_id):
                return {
                    "feature": "manage_panels",
                    "success": True,
                    "status": "idempotent",
                    "config": config,
                    "result": {"service": settings.service_name, "display": "Grafana Integration"},
                    "message": "manage_panels already processed",
                }
            await self.cache.set(f"{settings.service_name}:manage_panels", config)
            self._state["manage_panels"] = config
            self._operations["manage_panels"] = self._operations.get("manage_panels", 0) + 1
            self.metrics.inc_operation("manage_panels")
            result = {
                "feature": "manage_panels",
                "success": True,
                "status": "configured",
                "config": config,
                "result": {"service": settings.service_name, "display": "Grafana Integration"},
                "message": "manage_panels completed",
            }
            await self.idempotency.mark_processed(request_id, result)
            return result

    async def manage_users(self, request: Any = None) -> Dict[str, Any]:
        """Manage Users."""
        self.metrics.inc_request("manage_users")
        config = self._get_config(request)
        request_id = self.idempotency.get_key(request, "manage_users")
        async with self.lock_manager.acquire("manage_users", request_id):
            if await self.idempotency.is_processed(request_id):
                return {
                    "feature": "manage_users",
                    "success": True,
                    "status": "idempotent",
                    "config": config,
                    "result": {"service": settings.service_name, "display": "Grafana Integration"},
                    "message": "manage_users already processed",
                }
            await self.cache.set(f"{settings.service_name}:manage_users", config)
            self._state["manage_users"] = config
            self._operations["manage_users"] = self._operations.get("manage_users", 0) + 1
            self.metrics.inc_operation("manage_users")
            result = {
                "feature": "manage_users",
                "success": True,
                "status": "configured",
                "config": config,
                "result": {"service": settings.service_name, "display": "Grafana Integration"},
                "message": "manage_users completed",
            }
            await self.idempotency.mark_processed(request_id, result)
            return result

    async def manage_organizations(self, request: Any = None) -> Dict[str, Any]:
        """Manage Organizations."""
        self.metrics.inc_request("manage_organizations")
        config = self._get_config(request)
        request_id = self.idempotency.get_key(request, "manage_organizations")
        async with self.lock_manager.acquire("manage_organizations", request_id):
            if await self.idempotency.is_processed(request_id):
                return {
                    "feature": "manage_organizations",
                    "success": True,
                    "status": "idempotent",
                    "config": config,
                    "result": {"service": settings.service_name, "display": "Grafana Integration"},
                    "message": "manage_organizations already processed",
                }
            await self.cache.set(f"{settings.service_name}:manage_organizations", config)
            self._state["manage_organizations"] = config
            self._operations["manage_organizations"] = (
                self._operations.get("manage_organizations", 0) + 1
            )
            self.metrics.inc_operation("manage_organizations")
            result = {
                "feature": "manage_organizations",
                "success": True,
                "status": "configured",
                "config": config,
                "result": {"service": settings.service_name, "display": "Grafana Integration"},
                "message": "manage_organizations completed",
            }
            await self.idempotency.mark_processed(request_id, result)
            return result

    async def manage_permissions(self, request: Any = None) -> Dict[str, Any]:
        """Manage Permissions."""
        self.metrics.inc_request("manage_permissions")
        config = self._get_config(request)
        request_id = self.idempotency.get_key(request, "manage_permissions")
        async with self.lock_manager.acquire("manage_permissions", request_id):
            if await self.idempotency.is_processed(request_id):
                return {
                    "feature": "manage_permissions",
                    "success": True,
                    "status": "idempotent",
                    "config": config,
                    "result": {"service": settings.service_name, "display": "Grafana Integration"},
                    "message": "manage_permissions already processed",
                }
            await self.cache.set(f"{settings.service_name}:manage_permissions", config)
            self._state["manage_permissions"] = config
            self._operations["manage_permissions"] = (
                self._operations.get("manage_permissions", 0) + 1
            )
            self.metrics.inc_operation("manage_permissions")
            result = {
                "feature": "manage_permissions",
                "success": True,
                "status": "configured",
                "config": config,
                "result": {"service": settings.service_name, "display": "Grafana Integration"},
                "message": "manage_permissions completed",
            }
            await self.idempotency.mark_processed(request_id, result)
            return result

    async def integrate_visualization_layer(self, request: Any = None) -> Dict[str, Any]:
        """Integrate Visualization Layer."""
        self.metrics.inc_request("integrate_visualization_layer")
        config = self._get_config(request)
        request_id = self.idempotency.get_key(request, "integrate_visualization_layer")
        async with self.lock_manager.acquire("integrate_visualization_layer", request_id):
            if await self.idempotency.is_processed(request_id):
                return {
                    "feature": "integrate_visualization_layer",
                    "success": True,
                    "status": "idempotent",
                    "config": config,
                    "result": {"service": settings.service_name, "display": "Grafana Integration"},
                    "message": "integrate_visualization_layer already processed",
                }
            await self.cache.set(f"{settings.service_name}:integrate_visualization_layer", config)
            self._state["integrate_visualization_layer"] = config
            self._operations["integrate_visualization_layer"] = (
                self._operations.get("integrate_visualization_layer", 0) + 1
            )
            self.metrics.inc_operation("integrate_visualization_layer")
            result = {
                "feature": "integrate_visualization_layer",
                "success": True,
                "status": "configured",
                "config": config,
                "result": {"service": settings.service_name, "display": "Grafana Integration"},
                "message": "integrate_visualization_layer completed",
            }
            await self.idempotency.mark_processed(request_id, result)
            return result

    async def query_data(self, request: Any = None) -> Dict[str, Any]:
        """Query Grafana dashboards via the search API."""
        self.metrics.inc_request("query_data")
        config = self._get_config(request)

        base_url = config.get("url", config.get("grafana_url"))
        api_key = config.get("api_key") or config.get("token")
        query = config.get("query", "")
        if not base_url:
            return {
                "feature": "query_data",
                "success": False,
                "status": "error",
                "config": {},
                "result": {},
                "message": "Missing grafana url in config",
            }

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        search_url = base_url.rstrip("/") + "/api/search"
        params = {"query": query, "limit": config.get("limit", 50)}
        try:
            async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
                resp = await client.get(search_url, headers=headers, params=params)
                resp.raise_for_status()
                data = resp.json()
            return {
                "feature": "query_data",
                "success": True,
                "status": "ok",
                "config": {"url": base_url, "query": query},
                "result": data,
                "message": f"Found {len(data) if isinstance(data, list) else 0} items",
            }
        except httpx.HTTPStatusError as exc:
            return {
                "feature": "query_data",
                "success": False,
                "status": "error",
                "config": {"url": base_url, "query": query},
                "result": {"status_code": exc.response.status_code, "body": exc.response.text},
                "message": f"Grafana API error: {exc}",
            }
        except Exception as exc:
            return {
                "feature": "query_data",
                "success": False,
                "status": "error",
                "config": {"url": base_url, "query": query},
                "result": {},
                "message": f"Query failed: {exc}",
            }

    async def test_and_optimize_grafana(self, request: Any = None) -> Dict[str, Any]:
        """Test And Optimize Grafana."""
        self.metrics.inc_request("test_and_optimize_grafana")
        config = self._get_config(request)
        request_id = self.idempotency.get_key(request, "test_and_optimize_grafana")
        async with self.lock_manager.acquire("test_and_optimize_grafana", request_id):
            if await self.idempotency.is_processed(request_id):
                return {
                    "feature": "test_and_optimize_grafana",
                    "success": True,
                    "status": "idempotent",
                    "config": config,
                    "result": {"service": settings.service_name, "display": "Grafana Integration"},
                    "message": "test_and_optimize_grafana already processed",
                }
            await self.cache.set(f"{settings.service_name}:test_and_optimize_grafana", config)
            self._state["test_and_optimize_grafana"] = config
            self._operations["test_and_optimize_grafana"] = (
                self._operations.get("test_and_optimize_grafana", 0) + 1
            )
            self.metrics.inc_operation("test_and_optimize_grafana")
            result = {
                "feature": "test_and_optimize_grafana",
                "success": True,
                "status": "configured",
                "config": config,
                "result": {"service": settings.service_name, "display": "Grafana Integration"},
                "message": "test_and_optimize_grafana completed",
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
                    "result": {"service": settings.service_name, "display": "Grafana Integration"},
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
                "result": {"service": settings.service_name, "display": "Grafana Integration"},
                "message": "write_integration_docs completed",
            }
            await self.idempotency.mark_processed(request_id, result)
            return result

    async def manage_templates(self, request: Any = None) -> Dict[str, Any]:
        """Manage Templates."""
        self.metrics.inc_request("manage_templates")
        config = self._get_config(request)
        request_id = self.idempotency.get_key(request, "manage_templates")
        async with self.lock_manager.acquire("manage_templates", request_id):
            if await self.idempotency.is_processed(request_id):
                return {
                    "feature": "manage_templates",
                    "success": True,
                    "status": "idempotent",
                    "config": config,
                    "result": {"service": settings.service_name, "display": "Grafana Integration"},
                    "message": "manage_templates already processed",
                }
            await self.cache.set(f"{settings.service_name}:manage_templates", config)
            self._state["manage_templates"] = config
            self._operations["manage_templates"] = self._operations.get("manage_templates", 0) + 1
            self.metrics.inc_operation("manage_templates")
            result = {
                "feature": "manage_templates",
                "success": True,
                "status": "configured",
                "config": config,
                "result": {"service": settings.service_name, "display": "Grafana Integration"},
                "message": "manage_templates completed",
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


Service = GrafanaIntegrationService
