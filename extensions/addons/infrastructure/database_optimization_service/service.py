# -*- coding: utf-8 -*-
"""Service layer for the Database Optimization addon.

Exposes both the generic ``execute_operation`` API used by integration tests
and the typed async methods expected by ``main_app.py``.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from extensions.addons.engines.storage_driver import StorageDriver

BASE_METHODS: List[str] = [
    "get_state",
    "backup_state",
    "restore_state",
    "get_stats",
    "list_methods",
]

OPERATIONS: List[str] = [
    "analyze_query_performance",
    "optimize_indexes",
    "optimize_connection_pool",
    "implement_read_write_split",
    "implement_sharding_optimization",
    "monitor_database_performance",
    "analyze_database_bottlenecks",
    "generate_optimization_suggestions",
    "plan_database_capacity",
    "test_and_optimize_database",
]


class Service:
    """Database Optimization service."""

    def __init__(self, dry_run: bool = True, **kwargs: Any) -> None:
        # ``metrics`` and ``cache`` are passed by ``main_app.get_service()`` but not
        # used by the engine; strip them so they do not reach StorageDriver.
        kwargs.pop("metrics", None)
        kwargs.pop("cache", None)
        self.driver = StorageDriver(dry_run=dry_run, **kwargs)
        self._state: Dict[str, Any] = {}

    @staticmethod
    def _params(params: Optional[Any]) -> Dict[str, Any]:
        if params is None:
            return {}
        if hasattr(params, "model_dump"):
            params = params.model_dump()
        if isinstance(params, dict):
            return params
        return {}

    @staticmethod
    def _payload(params: Dict[str, Any]) -> Dict[str, Any]:
        """Extract the inner config from FeatureRequest-style payloads."""
        if isinstance(params, dict) and "config" in params:
            return params["config"]
        return params

    def execute_operation(self, name: str, params: Optional[Any] = None) -> Any:
        data = self._payload(self._params(params))

        if name == "get_stats":
            return self.driver.get_stats()

        if name == "list_methods":
            return {"methods": OPERATIONS + BASE_METHODS}

        if name == "get_state":
            return self.driver.cache_get(key=data.get("key", "state"))

        if name in ("backup_state", "restore_state"):
            return {"backup": True, "name": data.get("name", "default")}

        if name in OPERATIONS:
            return self.driver.sql(
                query=data.get("query", "SELECT 1"),
                params=data.get("params", []),
                readonly=data.get("readonly", True),
            )

        raise ValueError(f"Unknown operation: {name}")

    # ------------------------------------------------------------------
    # Async methods expected by main_app.py
    # ------------------------------------------------------------------
    async def get_stats(self, request: Optional[Any] = None) -> Dict[str, Any]:
        stats = self.driver.get_stats()
        return {
            "feature": "get-stats",
            "success": True,
            "status": "ok",
            "result": {
                "total_requests": 0,
                "cache_hits": stats.get("cache_hits", 0),
                "cache_misses": 0,
                "operations": {},
                "index_size": stats.get("db_size", 0),
                "feature_count": stats.get("vector_count", 0),
            },
            "config": getattr(request, "config", {}) if request else {},
            "message": "",
        }

    async def list_methods(self, request: Optional[Any] = None) -> Dict[str, Any]:
        return {
            "feature": "list-methods",
            "success": True,
            "status": "ok",
            "result": {"methods": OPERATIONS + BASE_METHODS},
            "config": getattr(request, "config", {}) if request else {},
            "message": "",
        }

    async def call(self, method: str, request: Optional[Any] = None) -> Any:
        payload = self._params(request) if request else {}
        return self.execute_operation(method, payload)

    def __getattr__(self, name: str) -> Any:
        if name in OPERATIONS:

            async def _op_handler(request: Optional[Any] = None) -> Dict[str, Any]:
                payload = self._params(request) if request else {}
                result = self.execute_operation(name, payload)
                is_error = isinstance(result, dict) and "error" in result
                return {
                    "feature": name,
                    "success": not is_error,
                    "status": "error" if is_error else "ok",
                    "result": result,
                    "config": getattr(request, "config", {}) if request else {},
                    "message": result.get("error", "") if isinstance(result, dict) else "",
                }

            return _op_handler
        raise AttributeError(f"'{self.__class__.__name__}' has no attribute '{name}'")


Service.OPERATIONS = OPERATIONS
Service.BASE_METHODS = BASE_METHODS

DatabaseOptimizationService = Service
