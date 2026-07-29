# -*- coding: utf-8 -*-
"""Saga distributed transaction support (task 30.10)."""

from __future__ import annotations

from typing import Any, Callable, Dict

from services.config_service.repository import ConfigRepository
from services.config_service.schemas import SagaTransaction


class ConfigSagaOrchestrator:
    """Saga orchestrator for config distributed transactions."""

    def __init__(self, repo: ConfigRepository) -> None:
        self.repo = repo
        self._actions: Dict[str, Callable[..., Any]] = {}
        self._compensations: Dict[str, Callable[..., Any]] = {}

    def register(
        self,
        action: str,
        handler: Callable[..., Any],
        compensation: Callable[..., Any],
    ) -> None:
        self._actions[action] = handler
        self._compensations[action] = compensation

    async def execute(self, saga: SagaTransaction) -> SagaTransaction:
        try:
            for step in saga.steps:
                handler = self._actions.get(step.action)
                if handler:
                    step.result = await handler(step)
                step.status = "success"
            saga.status = "success"
        except Exception as exc:
            saga.status = "failed"
            await self.compensate(saga)
            raise exc
        await self.repo.save_saga(saga)
        return saga

    async def compensate(self, saga: SagaTransaction) -> None:
        for step in reversed(saga.steps):
            if step.status == "success":
                handler = self._compensations.get(step.action)
                if handler:
                    step.result = await handler(step)
                step.status = "compensated"
        saga.status = "compensating"
