# -*- coding: utf-8 -*-
"""Executor API (``/api/v1/executor``).

Backs ``frontend/app/workflow/executor``.  The executor is the *control surface*
over the workflow execution queue:

* the task list is the real set of ``workflow_executions`` rows (with
  ``pending`` rows representing work queued while the executor is paused);
* ``retry`` re-runs a failed execution, ``cancel`` stops a running one;
* ``pause``/``resume`` gate the queue — while paused, new executions are queued
  (see :mod:`core.executor_state`), and ``resume`` drains them.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy.exc import SQLAlchemyError

from core.database import SessionLocal
from core.executor_state import set_paused
from core.models import Workflow, WorkflowExecution
from core.workflow_page_support import tenant_of, to_iso
from core.workflow_runtime import create_execution, run_execution_task

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/executor", tags=["执行器"])

_STATUS_MAP = {
    "pending": "pending",
    "running": "running",
    "completed": "completed",
    "failed": "failed",
    "cancelled": "failed",
}


def _definition_int(definition: Any, key: str, default: int) -> int:
    if isinstance(definition, dict):
        try:
            return int(definition.get(key, default))
        except (TypeError, ValueError):
            return default
    return default


def _serialize(
    execution: WorkflowExecution, workflow: Optional[Workflow]
) -> dict[str, Any]:
    result = execution.result if isinstance(execution.result, dict) else {}
    definition = workflow.definition if workflow and isinstance(workflow.definition, dict) else {}
    priority = str(definition.get("priority") or "medium")
    max_retries = _definition_int(definition, "maxRetries", 3)
    return {
        "id": execution.id,
        "name": result.get("workflowName") or (workflow.name if workflow else execution.workflow_id),
        "type": "async" if execution.trigger_source in {"schedule", "retry"} else "sync",
        "status": _STATUS_MAP.get(execution.status, "pending"),
        "priority": priority,
        "workflowId": execution.workflow_id,
        "workflowName": (workflow.name if workflow else execution.workflow_id),
        "startedAt": to_iso(execution.started_at),
        "completedAt": to_iso(execution.completed_at),
        "duration": round(execution.duration_sec, 1) if execution.duration_sec else None,
        "retryCount": 1 if execution.trigger_source == "retry" else 0,
        "maxRetries": max_retries,
        "error": execution.error_message,
    }


def _load_tasks(limit: int = 200) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    db = SessionLocal()
    try:
        executions = (
            db.query(WorkflowExecution)
            .order_by(WorkflowExecution.started_at.desc())
            .limit(limit)
            .all()
        )
        workflows = {w.id: w for w in db.query(Workflow).all()}
        tasks = [_serialize(e, workflows.get(e.workflow_id)) for e in executions]

        finished = [t for t in tasks if t["status"] in {"completed", "failed"}]
        completed = [t for t in tasks if t["status"] == "completed"]
        durations = [t["duration"] for t in tasks if isinstance(t.get("duration"), (int, float))]
        stats = {
            "totalTasks": len(tasks),
            "runningTasks": sum(1 for t in tasks if t["status"] == "running"),
            "completedTasks": len(completed),
            "failedTasks": sum(1 for t in tasks if t["status"] == "failed"),
            "avgDuration": round(sum(durations) / len(durations), 1) if durations else 0,
            "successRate": round(len(completed) / len(finished) * 100, 1) if finished else 0,
        }
        return tasks, stats
    finally:
        db.close()


@router.get("", summary="列出执行任务")
async def list_executor_tasks() -> dict[str, Any]:
    """Return the execution queue plus aggregate stats."""
    tasks, stats = _load_tasks()
    return {"tasks": tasks, "stats": stats}


@router.post("/{task_id}/retry", summary="重试执行任务")
async def retry_task(task_id: str, request: Request) -> dict[str, Any]:
    """Re-run a failed execution by creating a fresh one."""
    db = SessionLocal()
    try:
        previous = db.query(WorkflowExecution).filter(WorkflowExecution.id == task_id).first()
        if previous is None:
            raise HTTPException(status_code=404, detail="执行任务不存在")
        workflow_id = previous.workflow_id
        params = (previous.result or {}).get("params", {}) if isinstance(previous.result, dict) else {}
    finally:
        db.close()

    try:
        execution = create_execution(
            workflow_id, params=params, triggered_by="user", trigger_source="retry"
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    try:
        loop = asyncio.get_running_loop()
        loop.create_task(run_execution_task(execution.id))
    except RuntimeError:  # pragma: no cover
        logger.warning("No loop; retry execution %s not scheduled", execution.id)
    return {"status": "success", "executionId": execution.id}


@router.post("/{task_id}/cancel", summary="取消执行任务")
async def cancel_task(task_id: str) -> dict[str, Any]:
    """Cancel a running execution task."""
    db = SessionLocal()
    try:
        execution = db.query(WorkflowExecution).filter(WorkflowExecution.id == task_id).first()
        if execution is None:
            raise HTTPException(status_code=404, detail="执行任务不存在")
        if execution.status not in {"running", "pending"}:
            raise HTTPException(status_code=400, detail="只有运行中的任务可以取消")
        execution.status = "cancelled"
        execution.completed_at = datetime.utcnow()
        db.commit()
        return {"status": "success", "message": "任务已取消"}
    except HTTPException:
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="取消任务失败") from exc
    finally:
        db.close()


@router.post("/pause", summary="暂停执行器")
async def pause_executor(request: Request) -> dict[str, Any]:
    """Pause the execution queue (new executions will be queued)."""
    set_paused(tenant_of(request), True)
    return {"status": "success", "paused": True}


@router.post("/resume", summary="恢复执行器")
async def resume_executor(request: Request) -> dict[str, Any]:
    """Resume the queue and launch every pending execution."""
    tenant = tenant_of(request)
    set_paused(tenant, False)

    launched = 0
    db = SessionLocal()
    try:
        pending = (
            db.query(WorkflowExecution).filter(WorkflowExecution.status == "pending").all()
        )
        pending_ids = [e.id for e in pending]
    finally:
        db.close()

    try:
        loop = asyncio.get_running_loop()
        for execution_id in pending_ids:
            loop.create_task(run_execution_task(execution_id))
            launched += 1
    except RuntimeError:  # pragma: no cover
        logger.warning("No loop; %d pending executions not launched", len(pending_ids))

    return {"status": "success", "paused": False, "launched": launched}
