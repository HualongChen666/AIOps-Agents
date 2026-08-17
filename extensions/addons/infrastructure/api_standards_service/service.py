# -*- coding: utf-8 -*-
"""Thin wrapper around PolicyEngine for the API standards addon."""

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
    "lint_openapi",
    "follow_openapi3",
    "test_api_with_openapi",
    "generate_api_docs",
]

_OP_MAP: Dict[str, Callable[[PolicyEngine, Dict[str, Any]], Any]] = {
    "lint_openapi": lambda engine, params: engine.lint_openapi(params.get("spec")),
    "follow_openapi3": lambda engine, params: engine.lint_openapi(params.get("spec")),
    "test_api_with_openapi": lambda engine, params: engine.lint_openapi(params.get("spec")),
    "generate_api_docs": lambda engine, params: engine.lint_openapi(params.get("spec")),
}


class APIStandardsService:
    """Service wrapper delegating API standards operations to PolicyEngine."""

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


Service = APIStandardsService
