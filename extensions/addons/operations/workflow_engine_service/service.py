# -*- coding: utf-8 -*-
"""Thin wrapper for the Workflow Engine addon."""

from __future__ import annotations

from typing import Any, Dict

from extensions.addons.engines.workflow_engine import WorkflowEngine

OPERATIONS = ["execute_workflow"]
_DISPATCH = {"execute_workflow": "run_workflow"}


class Service:
    """Workflow Engine service wrapper."""

    _engine: WorkflowEngine | None = None
    OPERATIONS = OPERATIONS

    @classmethod
    def _get_engine(cls) -> WorkflowEngine:
        if cls._engine is None:
            cls._engine = WorkflowEngine()
        return cls._engine

    @classmethod
    def execute_operation(cls, name: str, params: Dict[str, Any]) -> Any:
        """Dispatch an operation to the workflow engine."""
        if name not in cls.OPERATIONS:
            raise ValueError(f"Unknown operation: {name}")
        method = _DISPATCH.get(name, name)
        return getattr(cls._get_engine(), method)(**params)
