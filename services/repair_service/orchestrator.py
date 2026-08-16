# -*- coding: utf-8 -*-
"""Repair orchestrator microservice."""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional, cast

from fastapi import FastAPI
from loguru import logger
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.responses import Response

from services.repair_service.audit import AuditStore
from services.repair_service.config import settings
from services.repair_service.executor import RunbookExecutor
from services.repair_service.metrics import REPAIR_TASKS_COMPLETED, REPAIR_TASKS_CREATED
from services.repair_service.mq import message_queue
from services.repair_service.repository import RepairRepository, get_repository
from services.repair_service.rollback import RollbackEngine
from services.repair_service.runbook_parser import RunbookParser
from services.repair_service.saga import SagaOrchestrator
from services.repair_service.schemas import (
    RepairExecutionResult,
    RepairRequest,
    RepairStatus,
    RepairTask,
    ServiceHealth,
)
from services.repair_service.state_machine import RepairStateMachine
from services.repair_service.strategy_manager import RepairStrategyManager
from services.repair_service.verifier import RepairVerifier


class OrchestratorApp:
    """Container for orchestrator components."""

    def __init__(self) -> None:
        self.repo: RepairRepository = cast(RepairRepository, None)  # initialized in lifespan
        self.strategy_manager = RepairStrategyManager()
        self.executor = RunbookExecutor(dry_run=settings.use_in_memory)
        self.verifier = RepairVerifier(timeout=settings.default_execution_timeout)
        self.rollback = RollbackEngine()
        self.audit = AuditStore()
        self.saga = SagaOrchestrator()
        self.machines: Dict[str, RepairStateMachine] = {}

    async def init(self) -> None:
        self.repo = await get_repository(settings.use_in_memory)

    def get_machine(self, task: RepairTask) -> RepairStateMachine:
        if task.task_id not in self.machines:
            self.machines[task.task_id] = RepairStateMachine(task)
        return self.machines[task.task_id]

    async def create_task(self, request: RepairRequest) -> RepairTask:
        task_id = f"REPAIR-{uuid.uuid4().hex[:16].upper()}"
        task = self.strategy_manager.create_task_from_request(request, task_id)
        if (
            request.auto_approve
            and task.strategy
            and task.strategy.risk_level
            in (
                "low",
                "medium",
            )
        ):
            task.status = RepairStatus.APPROVED
        await self.repo.save(task)
        REPAIR_TASKS_CREATED.labels(platform=task.platform.value).inc()
        await self.audit.record(task_id, "created", request.requested_by, request.model_dump())
        await message_queue.publish(
            "repair.created", {"task_id": task_id, "alert_id": request.alert_id}
        )
        return task

    async def approve(self, task_id: str) -> Optional[RepairTask]:
        task = await self.repo.get(task_id)
        if not task:
            return None
        machine = self.get_machine(task)
        if not machine.transition(RepairStatus.APPROVED, reason="user/system approved"):
            return task
        await self.audit.record(task_id, "approved", "system", {})
        return await self._execute_pipeline(task)

    async def reject(self, task_id: str) -> Optional[RepairTask]:
        task = await self.repo.get(task_id)
        if not task:
            return None
        machine = self.get_machine(task)
        machine.transition(RepairStatus.REJECTED, reason="rejected by user/system")
        machine.transition(RepairStatus.COMPLETED, reason="finalized")
        await self.repo.save(task)
        await self.audit.record(task_id, "rejected", "system", {})
        return task

    async def _execute_pipeline(self, task: RepairTask) -> RepairTask:
        machine = self.get_machine(task)
        task = await self._execute(task)
        if task.status == RepairStatus.SUCCEEDED:
            task = await self._verify(task)
            if task.status == RepairStatus.VERIFIED:
                machine.transition(RepairStatus.COMPLETED, reason="verified")
            else:
                await self._rollback(task)
                if task.status == RepairStatus.ROLLBACKED:
                    machine.transition(RepairStatus.COMPLETED, reason="rollbacked")
                else:
                    machine.transition(RepairStatus.COMPLETED, reason="rollback failed")
        else:
            await self._rollback(task)
            machine.transition(RepairStatus.COMPLETED, reason="executed and rolled back")

        await self.repo.save(task)
        REPAIR_TASKS_COMPLETED.labels(status=task.status.value, platform=task.platform.value).inc()
        await self.audit.record(task.task_id, "completed", "system", task.model_dump())
        return task

    async def _execute(self, task: RepairTask) -> RepairTask:
        machine = self.get_machine(task)
        machine.transition(RepairStatus.EXECUTING, reason="start execution")

        strategy = task.strategy
        if strategy:
            runbook = RunbookParser.load_example(strategy.script_key)
        else:
            runbook = RunbookParser.load_example("memory_high")

        if not runbook:
            machine.transition(RepairStatus.FAILED, reason="runbook not found")
            await self.repo.save(task)
            return task

        runbook = runbook.model_copy(deep=True)
        runbook.params.update(task.runbook.params if task.runbook else {})

        result = await self.executor.execute(
            task.task_id, runbook, task.runbook.params if task.runbook else {}
        )
        task.result = result.model_dump()
        if result.success:
            machine.transition(RepairStatus.SUCCEEDED, reason="execution success")
        else:
            machine.transition(RepairStatus.FAILED, reason=result.error)
        await self.repo.save(task)
        await self.audit.record(task.task_id, "executed", "executor", result.model_dump())
        return task

    async def _verify(self, task: RepairTask) -> RepairTask:
        machine = self.get_machine(task)
        machine.transition(RepairStatus.VERIFYING, reason="start verification")
        result_obj = RepairExecutionResult(**task.result) if task.result else None
        outcome = await self.verifier.verify(task, result_obj)
        task.result["verification"] = outcome.model_dump()
        if outcome.verified:
            machine.transition(RepairStatus.VERIFIED, reason="verification success")
        else:
            machine.transition(RepairStatus.VERIFY_FAILED, reason="verification failed")
        await self.repo.save(task)
        await self.audit.record(task.task_id, "verified", "verifier", outcome.model_dump())
        return task

    async def _rollback(self, task: RepairTask) -> RepairTask:
        machine = self.get_machine(task)
        machine.transition(RepairStatus.ROLLBACK_PENDING, reason="prepare rollback")
        machine.transition(RepairStatus.ROLLBACKING, reason="executing rollback")
        result_obj = RepairExecutionResult(**task.result) if task.result else None
        if result_obj:
            rollback_result = await self.rollback.rollback(task, result_obj)
            task.rollback_result = rollback_result.model_dump()
            if rollback_result.success:
                machine.transition(RepairStatus.ROLLBACKED, reason="rollback success")
            else:
                machine.transition(RepairStatus.ROLLBACK_FAILED, reason=rollback_result.error)
        else:
            machine.transition(RepairStatus.ROLLBACK_FAILED, reason="no result to rollback")
        await self.repo.save(task)
        await self.audit.record(
            task.task_id, "rollback", "rollback-engine", task.rollback_result or {}
        )
        return task

    async def execute_saga(self, task_id: str) -> Dict[str, Any]:
        """Demonstrate Saga distributed transaction across repair steps."""
        from services.repair_service.schemas import SagaStep

        task = await self.repo.get(task_id)
        if not task:
            return {"success": False, "error": "task not found"}

        saga_id = f"SAGA-{uuid.uuid4().hex[:16].upper()}"
        steps = [
            SagaStep(
                step_id="approve", service="orchestrator", action="approve", compensation="reject"
            ),
            SagaStep(
                step_id="execute", service="executor", action="execute", compensation="rollback"
            ),
            SagaStep(
                step_id="verify", service="verifier", action="verify", compensation="rollback"
            ),
        ]

        async def _approve() -> Dict[str, Any]:
            return {"success": True}

        async def _execute() -> Dict[str, Any]:
            task_local = await self.repo.get(task_id)
            if not task_local:
                return {"success": False, "error": "task not found"}
            await self._execute(task_local)
            return {
                "success": task_local.status in (RepairStatus.SUCCEEDED, RepairStatus.VERIFYING)
            }

        async def _verify() -> Dict[str, Any]:
            task_local = await self.repo.get(task_id)
            if not task_local:
                return {"success": False, "error": "task not found"}
            if task_local.status == RepairStatus.VERIFYING:
                await self._verify(task_local)
            return {"success": task_local.status == RepairStatus.VERIFIED}

        async def _reject() -> Dict[str, Any]:
            return {"success": True}

        async def _rollback() -> Dict[str, Any]:
            task_local = await self.repo.get(task_id)
            if not task_local:
                return {"success": False, "error": "task not found"}
            await self._rollback(task_local)
            return {"success": True}

        self.saga.register(
            saga_id,
            steps,
            {
                "approve": _approve,
                "execute": _execute,
                "verify": _verify,
            },
            {
                "reject": _reject,
                "rollback": _rollback,
            },
        )

        result = await self.saga.execute(saga_id)
        return result


orchestrator_app = OrchestratorApp()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await orchestrator_app.init()
    logger.info("Repair orchestrator started")
    yield
    logger.info("Repair orchestrator stopped")


app = FastAPI(
    title="Repair Orchestrator",
    description="Coordinates repair task lifecycle across executor and verifier.",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health", response_model=ServiceHealth)
async def health() -> ServiceHealth:
    return ServiceHealth(
        status="ok", service="repair-orchestrator", uptime_seconds=0, repair_count=0
    )


@app.get("/metrics")
async def metrics() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/repairs")
async def create_repair(request: RepairRequest) -> Dict[str, Any]:
    o = cast(OrchestratorApp, orchestrator_app)
    task = await o.create_task(request)
    return task.model_dump()


@app.get("/repairs")
async def list_repairs(limit: int = 100) -> Dict[str, Any]:
    o = cast(OrchestratorApp, orchestrator_app)
    tasks = await o.repo.list(limit=limit)
    return {"total": len(tasks), "items": [t.model_dump() for t in tasks]}


@app.get("/repairs/{task_id}")
async def get_repair(task_id: str) -> Dict[str, Any]:
    o = cast(OrchestratorApp, orchestrator_app)
    task = await o.repo.get(task_id)
    if not task:
        return {"error": "task not found"}
    return task.model_dump()


@app.post("/repairs/{task_id}/approve")
async def approve_repair(task_id: str) -> Dict[str, Any]:
    o = cast(OrchestratorApp, orchestrator_app)
    task = await o.approve(task_id)
    if not task:
        return {"error": "task not found"}
    return task.model_dump()


@app.post("/repairs/{task_id}/reject")
async def reject_repair(task_id: str) -> Dict[str, Any]:
    o = cast(OrchestratorApp, orchestrator_app)
    task = await o.reject(task_id)
    if not task:
        return {"error": "task not found"}
    return task.model_dump()


@app.post("/repairs/{task_id}/saga")
async def run_saga(task_id: str) -> Dict[str, Any]:
    o = cast(OrchestratorApp, orchestrator_app)
    return await o.execute_saga(task_id)
