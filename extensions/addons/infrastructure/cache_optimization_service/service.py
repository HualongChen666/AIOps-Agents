# -*- coding: utf-8 -*-
"""Thin wrapper around StorageDriver for the Cache Optimization service."""

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
    "design_multi_level_cache",
    "implement_cache_preheating",
    "implement_cache_invalidation",
    "implement_cache_monitoring",
    "analyze_cache_performance",
    "generate_cache_suggestions",
    "plan_cache_capacity",
    "write_cache_docs",
    "benchmark_cache",
    "test_and_optimize_cache",
]


class Service:
    """Cache Optimization service wrapper dispatching to StorageDriver."""

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
            return self.driver.cache_set(
                key=name,
                value=data.get("config", data),
                ttl=data.get("ttl", 3600),
            )

        raise ValueError(f"Unknown operation: {name}")


Service.OPERATIONS = OPERATIONS
Service.BASE_METHODS = BASE_METHODS


CacheOptimizationService = Service
