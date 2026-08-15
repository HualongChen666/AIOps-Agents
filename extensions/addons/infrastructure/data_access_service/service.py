# -*- coding: utf-8 -*-
"""Thin wrapper around StorageDriver for the data access service."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from extensions.addons.engines.storage_driver import StorageDriver

OPERATIONS: List[str] = ["sql", "get_stats"]


class Service:
    """Data access service wrapper dispatching to StorageDriver."""

    def __init__(self, dry_run: bool = True, **kwargs: Any) -> None:
        self.driver = StorageDriver(dry_run=dry_run, **kwargs)

    def execute_operation(
        self, name: str, params: Optional[Dict[str, Any]] = None
    ) -> Any:
        if params is None:
            params = {}
        if hasattr(params, "model_dump"):
            params = params.model_dump()
        if name not in OPERATIONS:
            raise ValueError(f"Unknown operation: {name}")
        method = getattr(self.driver, name)
        return method(**params)


Service.OPERATIONS = OPERATIONS


DataAccessService = Service
