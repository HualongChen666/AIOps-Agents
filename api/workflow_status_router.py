# -*- coding: utf-8 -*-
"""Workflow status API (``/api/v1/workflow-status``).

Backs ``frontend/app/workflow/workflow-status`` — a live monitor that polls the
aggregated status of every workflow.  All figures are computed from the durable
``workflows`` / ``workflow_executions`` tables, never from a static template.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from sqlalchemy.exc import SQLAlchemyError

from core.database import SessionLocal
from core.models import Workflow, WorkflowExecution
from core.workflow_page_support import utcnow

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/workflow-status", tags=["工作流状态"])


def _latest_execution(executions: list[WorkflowExecution]) -> WorkflowExecution | None:
    latest = None
    for execution in executions:
        if latest is None or (execution.started_at or utcnow()) > (latest.started_at or utcnow()):
            latest = execution
    return latest


def _status_of(workflow: Workflow, executions: list[WorkflowExecution]) -> str:
    latest = _latest_execution(executions)
    if latest is None:
        return "idle"
    if latest.status == "running":
        return "running"
    if latest.status == "failed":
        return "error"
    if workflow.status == "inactive":
        return "idle"
    if latest.status == "completed":
        return "completed"
    return "idle"


def _steps_count(workflow: Workflow) -> int:
    definition = workflow.definition if isinstance(workflow.definition, dict) else {}
    steps = definition.get("steps")
    return len(steps) if isinstance(steps, list) else 0


def _build_status(workflow: Workflow, executions: list[WorkflowExecution]) -> dict[str, Any]:
    total_steps = max(_steps_count(workflow), 1)
    latest = _latest_execution(executions)
    result = latest.result if latest and isinstance(latest.result, dict) else {}
    progress = result.get("progress", 0)
    completed_steps = min(total_steps, round(progress / 100 * total_steps))

    finished = [e for e in executions if e.status in {"completed", "failed"}]
    completed = [e for e in finished if e.status == "completed"]
    durations = [e.duration_sec for e in executions if e.duration_sec is not None]

    return {
        "id": workflow.id,
        "workflowId": workflow.id,
        "workflowName": workflow.name,
        "status": _status_of(workflow, executions),
        "currentStep": result.get("currentStep") or "",
        "totalSteps": total_steps,
        "completedSteps": completed_steps,
        "lastExecution": (
            latest.started_at.isoformat()
            if latest and latest.started_at
            else (workflow.updated_at.isoformat() if workflow.updated_at else None)
        ),
        "successRate": round(len(completed) / len(finished) * 100) if finished else 0,
        "avgDuration": round(sum(durations) / len(durations), 1) if durations else 0.0,
        "errorMessage": latest.error_message if latest and latest.status == "failed" else None,
    }


@router.get("", summary="获取工作流状态汇总")
async def get_workflow_status() -> dict[str, Any]:
    """Aggregate live status + summary counters for every workflow."""
    db = SessionLocal()
    try:
        workflows = db.query(Workflow).all()
        executions = (
            db.query(WorkflowExecution)
            .order_by(WorkflowExecution.started_at.desc())
            .limit(2000)
            .all()
        )
        by_workflow: dict[str, list[WorkflowExecution]] = {}
        for execution in executions:
            by_workflow.setdefault(execution.workflow_id, []).append(execution)

        statuses = [_build_status(w, by_workflow.get(w.id, [])) for w in workflows]
        summary = {
            "total": len(statuses),
            "running": sum(1 for s in statuses if s["status"] == "running"),
            "idle": sum(1 for s in statuses if s["status"] == "idle"),
            "error": sum(1 for s in statuses if s["status"] == "error"),
            "completed": sum(1 for s in statuses if s["status"] == "completed"),
        }
        return {"statuses": statuses, "summary": summary}
    except SQLAlchemyError as exc:
        logger.error("获取工作流状态失败: %s", exc)
        raise HTTPException(status_code=500, detail="获取工作流状态失败") from exc
    finally:
        db.close()
