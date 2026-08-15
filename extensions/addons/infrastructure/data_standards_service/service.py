# -*- coding: utf-8 -*-
"""Thin wrapper around PolicyEngine for the Data standards addon."""

from __future__ import annotations

from typing import Any, Callable, Dict, List

from extensions.addons.engines.doc_policy_engine import PolicyEngine

BASE_METHODS: List[str] = [
    "get_state",
    "backup_state",
    "restore_state",
    "get_stats",
    "list_methods",
]

OPERATIONS: List[str] = [
    "validate_schema",
    "define_data_model_spec",
    "implement_json_schema_validation",
    "implement_data_compliance_check",
]

_OP_MAP: Dict[str, Callable[[PolicyEngine, Dict[str, Any]], Any]] = {
    "validate_schema": lambda engine, params: engine.validate_schema(
        params.get("obj"), params.get("schema")
    ),
    "define_data_model_spec": lambda engine, params: engine.validate_schema(
        params.get("obj", {}), params.get("schema", {})
    ),
    "implement_json_schema_validation": lambda engine, params: engine.validate_schema(
        params.get("obj", {}), params.get("schema", {})
    ),
    "implement_data_compliance_check": lambda engine, params: engine.validate_schema(
        params.get("obj", {}), params.get("schema", {})
    ),
}


class DataStandardsService:
    """Service wrapper delegating data standards operations to PolicyEngine."""

    _engine = PolicyEngine(dry_run=True)

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        pass

    @classmethod
    def execute_operation(cls, name: str, params: Any = None) -> Dict[str, Any]:
        params = params or {}
        if name not in OPERATIONS and name not in BASE_METHODS:
            raise ValueError(f"Unknown operation: {name}")

        handler = _OP_MAP.get(name)
        if handler is None:
            return {
                "success": True,
                "operation": name,
                "dry_run": True,
                "result": {"message": "not implemented"},
            }

        return {
            "success": True,
            "operation": name,
            "dry_run": cls._engine.dry_run,
            "result": handler(cls._engine, params),
        }


Service = DataStandardsService
