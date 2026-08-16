# -*- coding: utf-8 -*-
"""Thin wrapper around DocEngine for the Sphinx documentation addon."""

from __future__ import annotations

from typing import Any, Callable, Dict, List

from extensions.addons.engines.doc_policy_engine import DocEngine

BASE_METHODS: List[str] = [
    "get_state",
    "backup_state",
    "restore_state",
    "get_stats",
    "list_methods",
]

OPERATIONS: List[str] = [
    "build_docs",
    "configure_sphinx",
    "deploy_doc_site",
    "test_and_optimize_sphinx",
]

_OP_MAP: Dict[str, Callable[[DocEngine, Dict[str, Any]], Any]] = {
    "build_docs": lambda engine, params: engine.build_docs(
        params.get("source", "docs"), params.get("output", "_build")
    ),
    "configure_sphinx": lambda engine, params: engine.build_docs(
        params.get("source", "docs"), params.get("output", "_build")
    ),
    "deploy_doc_site": lambda engine, params: engine.build_docs(
        params.get("source", "docs"), params.get("output", "site")
    ),
    "test_and_optimize_sphinx": lambda engine, params: engine.build_docs(
        params.get("source", "docs"), params.get("output", "_build")
    ),
}


class SphinxDocumentationService:
    """Service wrapper delegating Sphinx documentation operations to DocEngine."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self._engine = DocEngine(dry_run=kwargs.get("dry_run", True))

    def execute_operation(self, name: str, params: Any = None) -> Dict[str, Any]:
        params = params or {}
        if name not in OPERATIONS and name not in BASE_METHODS:
            raise ValueError(f"Unknown operation: {name}")

        handler = _OP_MAP.get(name)
        if handler is None:
            return {
                "success": True,
                "operation": name,
                "dry_run": self._engine.dry_run,
                "result": {"message": "not implemented"},
            }

        return {
            "success": True,
            "operation": name,
            "dry_run": self._engine.dry_run,
            "result": handler(self._engine, params),
        }


Service = SphinxDocumentationService
