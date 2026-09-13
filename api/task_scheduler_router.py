# -*- coding: utf-8 -*-
"""Task scheduler API (``/api/v1/task-scheduler``).

Backs ``frontend/app/workflow/task-scheduler`` with a **real** cron scheduler:

* tasks are durably persisted (``persistent_records``);
* ``nextRun`` is computed with APScheduler's ``CronTrigger`` — never fabricated;
* a background loop wakes every 30s and executes every due task's workflow
  through :mod:`core.workflow_runtime`, updating run/success/failure counters;
* ``run-now`` executes the referenced workflow immediately.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from core.workflow_page_support import (
    STORE_DOMAIN,
    get_store,
    is_valid_cron,
    new_id,
    next_cron_run,
    utcnow,
)
from core.workflow_runtime import create_execution, run_execution

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/task-scheduler", tags=["任务调度"])

_KIND = "task_scheduler"
_SCHEDULER_TASK: Optional[asyncio.Task] = None
_TICK_SECONDS = 30


class _FakeRequest:
    """Minimal request shim so the background loop can reuse :func:`get_store`."""

    def __init__(self, tenant_id: str) -> None:
        self.state = type("_S", (), {"tenant_id": tenant_id})()


class TaskUpsert(BaseModel):
    """创建/更新调度任务的请求体。"""

    name: str = Field(..., min_length=1)
    description: str = Field(default="")
    workflowId: str = Field(..., min_length=1)
    schedule: str = Field(..., description="5 段 cron 表达式")
    timezone: str = Field(default="Asia/Shanghai")


class ToggleBody(BaseModel):
    enabled: bool


def _serialize(task: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": task.get("id"),
        "name": task.get("name"),
        "description": task.get("description", ""),
        "workflowId": task.get("workflowId"),
        "workflowName": task.get("workflowName") or task.get("workflowId"),
        "schedule": task.get("schedule"),
        "timezone": task.get("timezone", "Asia/Shanghai"),
        "enabled": bool(task.get("enabled", True)),
        "lastRun": task.get("lastRun"),
        "nextRun": task.get("nextRun"),
        "runCount": int(task.get("runCount", 0)),
        "successCount": int(task.get("successCount", 0)),
        "failureCount": int(task.get("failureCount", 0)),
        "createdAt": task.get("createdAt"),
    }


def _stats(tasks: list[dict[str, Any]]) -> dict[str, Any]:
    total_runs = sum(int(t.get("runCount", 0)) for t in tasks)
    successes = sum(int(t.get("successCount", 0)) for t in tasks)
    return {
        "totalTasks": len(tasks),
        "enabledTasks": sum(1 for t in tasks if t.get("enabled")),
        "disabledTasks": sum(1 for t in tasks if not t.get("enabled")),
        "totalRuns": total_runs,
        "successRate": round(successes / total_runs * 100, 1) if total_runs else 0,
    }


def _resolve_workflow_name(workflow_id: str) -> Optional[str]:
    from core.database import SessionLocal
    from core.models import Workflow

    db = SessionLocal()
    try:
        workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
        return workflow.name if workflow else None
    finally:
        db.close()


async def _execute_task(store: Any, task_id: str) -> None:
    """Run the task's workflow and update its counters + next run time."""
    task = store.get(task_id)
    if not task:
        return
    workflow_id = task.get("workflowId")
    now = utcnow()
    try:
        execution = create_execution(workflow_id, triggered_by="schedule", trigger_source=task_id)
        finished = await run_execution(execution.id)
        completed = finished.status == "completed"
    except ValueError as exc:
        logger.error("调度任务 %s 执行失败: %s", task_id, exc)
        completed = False

    task["runCount"] = int(task.get("runCount", 0)) + 1
    if completed:
        task["successCount"] = int(task.get("successCount", 0)) + 1
    else:
        task["failureCount"] = int(task.get("failureCount", 0)) + 1
    task["lastRun"] = now.isoformat()
    task["nextRun"] = next_cron_run(
        task.get("schedule", ""), base=now, tz=task.get("timezone", "UTC")
    )
    store[task_id] = task


async def _run_due_tasks() -> None:
    """Execute tasks whose ``nextRun`` has passed."""
    from core.database import SessionLocal
    from core.models import PersistentRecordDB

    db = SessionLocal()
    try:
        tenants = {
            row.tenant_id
            for row in db.query(PersistentRecordDB)
            .filter(
                PersistentRecordDB.domain == STORE_DOMAIN,
                PersistentRecordDB.kind == _KIND,
            )
            .all()
        }
    finally:
        db.close()

    now = utcnow()
    for tenant in tenants:
        store = get_store(_FakeRequest(tenant), _KIND)
        for task_id, task in list(store.items()):
            if not isinstance(task, dict) or not task.get("enabled"):
                continue
            next_run = task.get("nextRun")
            if not next_run:
                continue
            try:
                due = datetime.fromisoformat(next_run)
            except (TypeError, ValueError):
                continue
            if due.tzinfo is None:
                due = due.replace(tzinfo=now.tzinfo)
            if due <= now:
                await _execute_task(store, task_id)


async def _scheduler_loop() -> None:
    """Periodically execute every due task across all tenants."""
    while True:
        try:
            await _run_due_tasks()
        except Exception as exc:  # pragma: no cover - defensive background loop
            logger.error("调度循环异常: %s", exc)
        await asyncio.sleep(_TICK_SECONDS)


def _ensure_scheduler() -> None:
    """Start the background scheduler loop once per event loop."""
    global _SCHEDULER_TASK
    if _SCHEDULER_TASK is not None and not _SCHEDULER_TASK.done():
        return
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:  # pragma: no cover - no loop (sync context)
        return
    _SCHEDULER_TASK = loop.create_task(_scheduler_loop())


@router.get("", summary="列出调度任务")
async def list_tasks(request: Request) -> dict[str, Any]:
    """Return all scheduled tasks plus aggregate stats."""
    store = get_store(request, _KIND)
    tasks = [dict(t) for t in store.values_list() if isinstance(t, dict)]
    for task in tasks:
        if task.get("workflowId") and not task.get("workflowName"):
            task["workflowName"] = _resolve_workflow_name(task["workflowId"])
    tasks.sort(key=lambda t: str(t.get("createdAt") or ""))
    _ensure_scheduler()
    return {"tasks": [_serialize(t) for t in tasks], "stats": _stats(tasks)}


@router.post("", status_code=201, summary="创建调度任务")
async def create_task(payload: TaskUpsert, request: Request) -> dict[str, Any]:
    """Create a scheduled task; the cron expression is validated for real."""
    if not is_valid_cron(payload.schedule):
        raise HTTPException(status_code=400, detail=f"无效的 cron 表达式: {payload.schedule}")
    workflow_name = _resolve_workflow_name(payload.workflowId)
    if workflow_name is None:
        raise HTTPException(status_code=400, detail="引用的工作流不存在")

    store = get_store(request, _KIND)
    task_id = new_id("task")
    task = {
        "id": task_id,
        "name": payload.name.strip(),
        "description": payload.description,
        "workflowId": payload.workflowId,
        "workflowName": workflow_name,
        "schedule": payload.schedule,
        "timezone": payload.timezone,
        "enabled": True,
        "lastRun": None,
        "nextRun": next_cron_run(payload.schedule, tz=payload.timezone),
        "runCount": 0,
        "successCount": 0,
        "failureCount": 0,
        "createdAt": utcnow().isoformat(),
    }
    store[task_id] = task
    _ensure_scheduler()
    return _serialize(task)


@router.put("/{task_id}", summary="更新调度任务")
async def update_task(task_id: str, payload: TaskUpsert, request: Request) -> dict[str, Any]:
    """Update a scheduled task's definition."""
    if not is_valid_cron(payload.schedule):
        raise HTTPException(status_code=400, detail=f"无效的 cron 表达式: {payload.schedule}")
    store = get_store(request, _KIND)
    task = store.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="调度任务不存在")
    task["name"] = payload.name.strip()
    task["description"] = payload.description
    task["workflowId"] = payload.workflowId
    task["workflowName"] = _resolve_workflow_name(payload.workflowId)
    task["schedule"] = payload.schedule
    task["timezone"] = payload.timezone
    task["nextRun"] = next_cron_run(payload.schedule, tz=payload.timezone)
    store[task_id] = task
    return _serialize(task)


@router.delete("/{task_id}", summary="删除调度任务")
async def delete_task(task_id: str, request: Request) -> dict[str, Any]:
    """Delete a scheduled task."""
    store = get_store(request, _KIND)
    if task_id not in store:
        raise HTTPException(status_code=404, detail="调度任务不存在")
    del store[task_id]
    return {"status": "success", "message": "调度任务已删除"}


@router.patch("/{task_id}/toggle", summary="启用/禁用调度任务")
async def toggle_task(task_id: str, payload: ToggleBody, request: Request) -> dict[str, Any]:
    """Enable or disable a scheduled task."""
    store = get_store(request, _KIND)
    task = store.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="调度任务不存在")
    task["enabled"] = payload.enabled
    if payload.enabled:
        task["nextRun"] = next_cron_run(task.get("schedule", ""), tz=task.get("timezone", "UTC"))
    store[task_id] = task
    return _serialize(task)


@router.post("/{task_id}/run-now", summary="立即执行调度任务")
async def run_now(task_id: str, request: Request) -> dict[str, Any]:
    """Run the task's workflow immediately and refresh its counters."""
    store = get_store(request, _KIND)
    task = store.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="调度任务不存在")
    if _resolve_workflow_name(task.get("workflowId", "")) is None:
        raise HTTPException(status_code=400, detail="引用的工作流不存在")
    await _execute_task(store, task_id)
    return _serialize(store.get(task_id) or task)
