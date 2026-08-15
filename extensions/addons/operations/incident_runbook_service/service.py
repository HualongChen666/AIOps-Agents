# -*- coding: utf-8 -*-
"""Thin wrapper for the Incident Runbook addon."""

from __future__ import annotations

from typing import Any, Dict

from extensions.addons.engines.workflow_engine import RunbookRunner

OPERATIONS = ["run_runbook"]


class Service:
    """Incident Runbook service wrapper."""

    _engine: RunbookRunner | None = None
    OPERATIONS = OPERATIONS

    @classmethod
    def _get_engine(cls) -> RunbookRunner:
        if cls._engine is None:
            cls._engine = RunbookRunner()
        return cls._engine

    @classmethod
    def execute_operation(cls, name: str, params: Dict[str, Any]) -> Any:
        """Dispatch an operation to the runbook runner."""
        if name not in cls.OPERATIONS:
            raise ValueError(f"Unknown operation: {name}")
        return getattr(cls._get_engine(), name)(**params)
