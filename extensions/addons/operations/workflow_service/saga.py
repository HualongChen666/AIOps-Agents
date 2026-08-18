# -*- coding: utf-8 -*-
"""Saga distributed transaction orchestrator for workflow service."""

from __future__ import annotations

import asyncio
from typing import Any, Callable, Dict, List

from loguru import logger

from extensions.addons.operations.workflow_service.metrics import WORKFLOW_SAGA_STATUS
from extensions.addons.operations.workflow_service.schemas import SagaStep, SagaTransaction

SagaAction = Callable[..., Any]
SagaCompensation = Callable[..., Any]


class WorkflowSagaOrchestrator:
    """Saga pattern orchestrator with compensation support."""

    def __init__(self) -> None:
        self._transactions: Dict[str, SagaTransaction] = {}
        self._actions: Dict[str, Dict[str, SagaAction]] = {}
        self._compensations: Dict[str, Dict[str, SagaCompensation]] = {}

    def register(
        self,
        saga_id: str,
        steps: List[SagaStep],
        actions: Dict[str, SagaAction],
        compensations: Dict[str, SagaCompensation],
    ) -> None:
        # Convert SagaStep objects to dictionaries for Pydantic v2
        steps_dict = [step.model_dump() if hasattr(step, 'model_dump') else step for step in steps]
        transaction = SagaTransaction(
            saga_id=saga_id,
            task_id=steps[0].step_id if steps else "",
            steps=steps_dict,
        )
        self._transactions[saga_id] = transaction
        self._actions[saga_id] = actions
        self._compensations[saga_id] = compensations

    async def execute(self, saga_id: str) -> Dict[str, Any]:
        transaction = self._transactions.get(saga_id)
        if not transaction:
            return {"success": False, "error": f"Saga {saga_id} not found"}

        WORKFLOW_SAGA_STATUS.labels(saga_id=saga_id).set(0)
        executed: List[str] = []

        for step in transaction.steps:
            step.status = "executing"
            action = self._actions[saga_id].get(step.action)
            if not action:
                step.status = "failed"
                await self._compensate(saga_id, executed)
                WORKFLOW_SAGA_STATUS.labels(saga_id=saga_id).set(2)
                return {"success": False, "error": f"No action for step {step.step_id}"}

            try:
                if asyncio.iscoroutinefunction(action):
                    result = await action()
                else:
                    result = action()
                step.status = "success"
                step.result = result
                executed.append(step.step_id)
            except Exception as exc:
                logger.error(f"Saga step {step.step_id} failed: {exc}")
                step.status = "failed"
                step.result = {"error": str(exc)}
                await self._compensate(saga_id, executed)
                WORKFLOW_SAGA_STATUS.labels(saga_id=saga_id).set(2)
                return {
                    "success": False,
                    "error": str(exc),
                    "failed_step": step.step_id,
                    "saga_id": saga_id,
                }

        transaction.status = "success"
        WORKFLOW_SAGA_STATUS.labels(saga_id=saga_id).set(1)
        return {"success": True, "saga_id": saga_id, "steps": executed}

    async def _compensate(self, saga_id: str, executed_steps: List[str]) -> None:
        transaction = self._transactions[saga_id]
        transaction.status = "compensating"
        WORKFLOW_SAGA_STATUS.labels(saga_id=saga_id).set(3)
        for step_id in reversed(executed_steps):
            step = next((s for s in transaction.steps if s.step_id == step_id), None)
            if not step:
                continue
            comp = self._compensations[saga_id].get(step.compensation)
            try:
                if comp:
                    if asyncio.iscoroutinefunction(comp):
                        await comp()
                    else:
                        comp()
                step.status = "compensated"
            except Exception as exc:
                logger.error(f"Compensation failed for step {step_id}: {exc}")
                step.status = "compensation_failed"

    def get_transaction(self, saga_id: str) -> SagaTransaction:
        return self._transactions[saga_id]
