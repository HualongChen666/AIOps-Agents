# -*- coding: utf-8 -*-
"""Saga pattern for distributed transactions in alert processing."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine, Dict, List, Optional


@dataclass
class SagaContext:
    """Mutable context shared between saga steps."""

    data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SagaStep:
    """A saga step with action and optional compensation."""

    name: str
    action: Callable[[SagaContext], Coroutine[Any, Any, Any]]
    compensation: Optional[Callable[[SagaContext], Coroutine[Any, Any, Any]]] = None


class SagaOrchestrator:
    """Execute a list of saga steps with compensation on failure."""

    async def execute(
        self,
        steps: List[SagaStep],
        context: Optional[SagaContext] = None,
    ) -> Dict[str, Any]:
        ctx = context or SagaContext()
        executed: List[str] = []

        for step in steps:
            try:
                result = await step.action(ctx)
                ctx.data[step.name] = result
                executed.append(step.name)
            except Exception as exc:
                compensated = await self._compensate(steps, executed, ctx)
                return {
                    "status": "failed",
                    "failed_step": step.name,
                    "error": str(exc),
                    "executed": executed,
                    "compensated": compensated,
                }

        return {
            "status": "completed",
            "executed": executed,
            "compensated": [],
            "data": ctx.data,
        }

    async def _compensate(
        self,
        steps: List[SagaStep],
        executed: List[str],
        context: SagaContext,
    ) -> List[str]:
        compensated: List[str] = []
        step_map = {s.name: s for s in steps}
        for name in reversed(executed):
            step = step_map.get(name)
            if step and step.compensation:
                try:
                    await step.compensation(context)
                    compensated.append(name)
                except Exception as exc:
                    compensated.append(f"{name}_failed:{exc}")
        return compensated
