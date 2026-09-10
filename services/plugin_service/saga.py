# -*- coding: utf-8 -*-
"""Saga support for the plugin microservice.

Plugin operations that touch several tables (register plugin -> persist config
-> record execution) must not leave partial state behind when one step fails.
:class:`PluginSaga` executes an ordered list of steps and runs the compensating
action of every already-completed step on failure.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class SagaStep:
    """A single saga step with its compensating action."""

    name: str
    action: Callable[[], Awaitable[Any]]
    compensation: Optional[Callable[[], Awaitable[Any]]] = None
    status: str = "pending"
    result: Any = None


@dataclass
class PluginSaga:
    """Ordered saga with automatic compensation on failure."""

    saga_id: str
    steps: List[SagaStep] = field(default_factory=list)
    status: str = "pending"
    results: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

    def add_step(
        self,
        name: str,
        action: Callable[[], Awaitable[Any]],
        compensation: Optional[Callable[[], Awaitable[Any]]] = None,
    ) -> "PluginSaga":
        """Append a step (action + optional compensating action)."""
        self.steps.append(SagaStep(name=name, action=action, compensation=compensation))
        return self

    async def execute(self) -> "PluginSaga":
        """Run every step; compensate completed steps if one raises."""
        for step in self.steps:
            try:
                step.result = await step.action()
                step.status = "success"
                self.results[step.name] = step.result
            except Exception as exc:  # noqa: BLE001 - saga boundary converts to state
                step.status = "failed"
                self.error = f"{step.name}: {exc}"
                logger.error("Saga %s failed at step %s: %s", self.saga_id, step.name, exc)
                await self.compensate()
                self.status = "compensated"
                return self
        self.status = "success"
        return self

    async def compensate(self) -> None:
        """Run compensating actions for completed steps, newest first."""
        for step in reversed(self.steps):
            if step.status != "success" or step.compensation is None:
                continue
            try:
                await step.compensation()
                step.status = "compensated"
            except Exception as exc:  # noqa: BLE001 - compensation must not mask the original error
                logger.error("Compensation for %s failed: %s", step.name, exc)
                step.status = "compensation_failed"
