# -*- coding: utf-8 -*-
"""Workflow execution API (``/api/v1/workflow-execution``).

Backs ``frontend/app/workflow/workflow-execution``.  Executions are durable rows
in ``workflow_executions``; starting one actually launches
:func:`core.workflow_runtime.run_execution` as a background task, so the page's
progress bar, log viewer and status badges reflect real execution state.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm.attributes import flag_modified

from core.database import SessionLocal
from core.executor_state import is_paused
from core.models import Workflow, WorkflowExecution
from core.workflow_page_support import tenant_of, to_iso
from core.workflow_runtime import create_execution, list_logs, run_execution_task

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/workflow-execution", tags=["工作流执行"])


class ExecutionStart(BaseModel):
    """启动工作流执行的请求体。"""

    workflowId: str = Field(..., description="工作流 ID")
    params: dict[str, Any] = Field(default_factory=dict, description="输入参数")


def _schedule(execution_id: str) -> None:
    """Launch the execution in the background when an event loop is available."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:  # pragma: no cover - sync context fallback
        logger.warning("No running loop; execution %s queued only", execution_id)
        return
    loop.create_task(run_execution_task(execution_id))


def _serialize(execution: WorkflowExecution, workflow_name: Optional[str]) -> dict[str, Any]:
    result = execution.result if isinstance(execution.result, dict) else {}
    total_steps = result.get("totalSteps", 0)
    progress = result.get("progress", 100 if execution.status == "completed" else 0)
    duration = execution.duration_sec
    if duration is None and execution.status == "running" and execution.started_at:
        started = execution.started_at
        if isinstance(started, datetime):
            duration = round(max(0.0, (datetime.utcnow() - started).total_seconds()), 1)
    output = result.get("output")
    return {
        "id": execution.id,
        "workflowId": execution.workflow_id,
        "workflowName": workflow_name or result.get("workflowName") or execution.workflow_id,
        "status": execution.status,
        "startedAt": to_iso(execution.started_at),
        "completedAt": to_iso(execution.completed_at),
        "duration": round(duration, 1) if isinstance(duration, (int, float)) else None,
        "currentStep": result.get("currentStep"),
        "totalSteps": total_steps,
        "progress": progress,
        "inputParams": result.get("params", {}),
        "output": output if isinstance(output, dict) else None,
        "error": execution.error_message,
    }


def _workflow_name(db: Any, workflow_id: str) -> Optional[str]:
    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    return workflow.name if workflow else None


@router.get("", summary="列出执行记录")
async def list_executions(
    workflowId: Optional[str] = Query(None, description="按工作流过滤"),
    status: Optional[str] = Query(None, description="按状态过滤"),
    limit: int = Query(200, ge=1, le=1000),
) -> list[dict[str, Any]]:
    """Return execution records, newest first."""
    db = SessionLocal()
    try:
        query = db.query(WorkflowExecution)
        if workflowId:
            query = query.filter(WorkflowExecution.workflow_id == workflowId)
        if status:
            query = query.filter(WorkflowExecution.status == status)
        executions = query.order_by(WorkflowExecution.started_at.desc()).limit(limit).all()
        names = {
            w.id: w.name
            for w in db.query(Workflow).filter(
                Workflow.id.in_({e.workflow_id for e in executions})
            ).all()
        }
        return [_serialize(e, names.get(e.workflow_id)) for e in executions]
    except SQLAlchemyError as exc:
        logger.error("列出执行记录失败: %s", exc)
        raise HTTPException(status_code=500, detail="列出执行记录失败") from exc
    finally:
        db.close()


@router.post("", status_code=201, summary="启动工作流执行")
async def start_execution(payload: ExecutionStart, request: Request) -> dict[str, Any]:
    """Create an execution row and launch it (or queue it while paused)."""
    db = SessionLocal()
    try:
        name = _workflow_name(db, payload.workflowId)
        if name is None:
            raise HTTPException(status_code=404, detail="工作流不存在")
    finally:
        db.close()

    paused = is_paused(tenant_of(request))
    try:
        execution = create_execution(payload.workflowId, params=payload.params, queued=paused)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    if not paused:
        _schedule(execution.id)
    return _serialize(execution, name)


@router.post("/{execution_id}/cancel", summary="取消执行")
async def cancel_execution(execution_id: str) -> dict[str, Any]:
    """Cancel a running execution."""
    db = SessionLocal()
    try:
        execution = (
            db.query(WorkflowExecution).filter(WorkflowExecution.id == execution_id).first()
        )
        if execution is None:
            raise HTTPException(status_code=404, detail="执行记录不存在")
        if execution.status not in {"running", "pending"}:
            raise HTTPException(status_code=400, detail="只有运行中的执行可以取消")
        execution.status = "cancelled"
        execution.completed_at = datetime.utcnow()
        result = execution.result if isinstance(execution.result, dict) else {}
        result["currentStep"] = None
        execution.result = result
        flag_modified(execution, "result")
        db.commit()
        db.refresh(execution)
        return _serialize(execution, _workflow_name(db, execution.workflow_id))
    except HTTPException:
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error("取消执行失败: %s", exc)
        raise HTTPException(status_code=500, detail="取消执行失败") from exc
    finally:
        db.close()


@router.post("/{execution_id}/retry", summary="重试执行")
async def retry_execution(execution_id: str) -> dict[str, Any]:
    """Re-run a failed/cancelled execution by creating a fresh execution."""
    db = SessionLocal()
    try:
        previous = (
            db.query(WorkflowExecution).filter(WorkflowExecution.id == execution_id).first()
        )
        if previous is None:
            raise HTTPException(status_code=404, detail="执行记录不存在")
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

    _schedule(execution.id)
    db2 = SessionLocal()
    try:
        return _serialize(execution, _workflow_name(db2, workflow_id))
    finally:
        db2.close()


@router.get("/{execution_id}/logs", summary="获取执行日志")
async def get_execution_logs(execution_id: str) -> dict[str, Any]:
    """Return the captured log lines for an execution."""
    db = SessionLocal()
    try:
        exists = (
            db.query(WorkflowExecution).filter(WorkflowExecution.id == execution_id).first()
        )
        if exists is None:
            raise HTTPException(status_code=404, detail="执行记录不存在")
    finally:
        db.close()
    return {"logs": list_logs(execution_id)}
