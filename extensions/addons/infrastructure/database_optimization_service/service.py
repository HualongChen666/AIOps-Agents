# -*- coding: utf-8 -*-
"""Thin wrapper around StorageDriver for the Database Optimization service."""

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
    """Database Optimization service wrapper dispatching to StorageDriver."""

    def __init__(self, dry_run: bool = True, **kwargs: Any) -> None:
        self.driver = StorageDriver(dry_run=dry_run, **kwargs)

    @staticmethod
    def _params(params: Optional[Any]) -> Dict[str, Any]:
        if params is None:
            return {}
        if hasattr(params, "model_dump"):
            return params.model_dump()
        if isinstance(params, dict):
            return params
        return {}

    def execute_operation(self, name: str, params: Optional[Any] = None) -> Any:
        data = self._params(params)

        if name == "get_stats":
            return self.driver.get_stats()

        if name == "list_methods":
            return {"methods": OPERATIONS + BASE_METHODS}

        if name == "get_state":
            return self.driver.cache_get(key=data.get("key", "state"))

        if name == "backup_state":
            return {"backup": True, "name": data.get("name", "default")}

        if name == "restore_state":
            return {"restore": True, "name": data.get("name", "default")}

        if name in OPERATIONS:
            return self.driver.sql(
                query=data.get("query", "SELECT 1"),
                params=data.get("params", []),
                readonly=data.get("readonly", True),
            )

        raise ValueError(f"Unknown operation: {name}")


Service.OPERATIONS = OPERATIONS
Service.BASE_METHODS = BASE_METHODS


DatabaseOptimizationService = Service
