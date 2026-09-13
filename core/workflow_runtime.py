# -*- coding: utf-8 -*-
"""Workflow runtime — real, durable execution of workflow definitions.

The ``workflow-execution`` / ``workflow-status`` / ``task-scheduler`` /
``executor`` pages all need to *run* a workflow definition and observe its
progress.  This module owns that execution:

* :func:`create_execution` opens a durable ``workflow_executions`` row.
* :func:`run_execution` walks the workflow definition's steps in order,
  recording a real per-step log line and updating progress as it goes.
* :func:`list_logs` returns the log lines captured for an execution.

The executor is intentionally definition-driven: a step may carry an ``action``
(``noop`` / ``log`` / ``sleep``) and an optional ``fail`` flag.  Anything that
would require an external side effect is delegated to the caller's registered
step handler if one is provided — the runtime never fabricates success.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from sqlalchemy.orm.attributes import flag_modified

from core.database import SessionLocal
from core.models import Workflow, WorkflowExecution

logger = logging.getLogger(__name__)


def _flush(db: Any, execution: WorkflowExecution) -> None:
    """Commit, explicitly flagging the JSON ``result`` column as modified.

    SQLAlchemy's ``JSON`` type does not track in-place mutations of the payload
    dict, so ``execution.result["logs"].append(...)`` alone would be lost.
    """
    flag_modified(execution, "result")
    db.commit()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _new_execution_id() -> str:
    return f"exec-{uuid.uuid4().hex[:16]}"


def _result_of(execution: WorkflowExecution) -> dict[str, Any]:
    """Return the mutable result payload for an execution (never ``None``)."""
    if not isinstance(execution.result, dict):
        execution.result = {}
    return execution.result


def _steps_of(workflow: Workflow) -> list[dict[str, Any]]:
    definition = workflow.definition if isinstance(workflow.definition, dict) else {}
    steps = definition.get("steps")
    if not isinstance(steps, list):
        return []
    return [s for s in steps if isinstance(s, dict)]


def create_execution(
    workflow_id: str,
    *,
    params: Optional[dict[str, Any]] = None,
    triggered_by: str = "user",
    trigger_source: str = "manual",
    executor: Optional[str] = None,
    queued: bool = False,
) -> WorkflowExecution:
    """Create and persist a new execution for *workflow_id*.

    When *queued* is true the execution is stored in the ``pending`` state
    (waiting for the executor to be resumed) instead of ``running``.

    Raises:
        ValueError: when the workflow definition does not exist.
    """
    db = SessionLocal()
    try:
        workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
        if workflow is None:
            raise ValueError(f"工作流 {workflow_id} 不存在")

        steps = _steps_of(workflow)
        execution = WorkflowExecution(
            id=_new_execution_id(),
            workflow_id=workflow_id,
            status="pending" if queued else "running",
            triggered_by=triggered_by,
            trigger_source=trigger_source,
            executor=executor,
            started_at=None if queued else _utcnow(),
        )
        execution.result = {
            "logs": [],
            "progress": 0,
            "currentStep": None,
            "totalSteps": len(steps),
            "params": params or {},
            "workflowName": workflow.name,
        }
        db.add(execution)
        db.commit()
        db.refresh(execution)
        logger.info("Created workflow execution %s for %s", execution.id, workflow_id)
        return execution
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _append_log(execution: WorkflowExecution, line: str) -> None:
    result = _result_of(execution)
    logs = result.setdefault("logs", [])
    logs.append(f"{_utcnow().strftime('%H:%M:%S')} {line}")


async def _execute_step(
    step: dict[str, Any],
    context: dict[str, Any],
    step_handler: Optional[Callable[[dict[str, Any], dict[str, Any]], Any]],
) -> None:
    """Run one step's inline action (and/or the caller-supplied handler)."""
    action = str(step.get("action") or "noop")
    if action == "sleep":
        seconds = float(step.get("seconds", 0) or 0)
        if seconds > 0:
            await asyncio.sleep(min(seconds, 30.0))
    elif action == "log":
        logger.info("workflow step log: %s", step.get("message", step.get("title", "")))
    elif action != "noop":
        raise ValueError(f"未知的节点动作: {action}")

    if step_handler is not None:
        outcome = step_handler(step, context)
        if asyncio.iscoroutine(outcome):
            await outcome


def _finalize(execution: WorkflowExecution, result: dict[str, Any], *, failed: bool) -> None:
    """Fill the trailing result fields once an execution reaches a terminal state."""
    result.setdefault("logs", [])
    result["progress"] = result.get("progress", 0) if failed else 100
    result["currentStep"] = None
    if isinstance(execution.started_at, datetime) and isinstance(execution.completed_at, datetime):
        execution.duration_sec = max(
            0.0, (execution.completed_at - execution.started_at).total_seconds()
        )


async def run_execution(
    execution_id: str,
    *,
    step_handler: Optional[Callable[[dict[str, Any], dict[str, Any]], Any]] = None,
    step_delay: float = 0.0,
) -> WorkflowExecution:
    """Execute *execution_id*'s steps in order, updating durable state.

    Args:
        execution_id: target execution.
        step_handler: optional ``(step, context) -> Any`` coroutine/function used
            to perform a step's real side effect.  When ``None`` the step is
            handled purely by its inline ``action`` field.
        step_delay: optional inter-step delay in seconds (0 for tests/speed).

    Returns:
        The refreshed execution row.
    """
    db = SessionLocal()
    try:
        execution = (
            db.query(WorkflowExecution).filter(WorkflowExecution.id == execution_id).first()
        )
        if execution is None:
            raise ValueError(f"执行记录 {execution_id} 不存在")

        # A queued (paused) execution starts its clock when it actually runs.
        if execution.started_at is None:
            execution.started_at = _utcnow()
        if execution.status == "pending":
            execution.status = "running"

        workflow = db.query(Workflow).filter(Workflow.id == execution.workflow_id).first()
        if workflow is None:
            execution.status = "failed"
            execution.error_message = f"工作流 {execution.workflow_id} 不存在"
            execution.completed_at = _utcnow()
            db.commit()
            db.refresh(execution)
            return execution

        steps = _steps_of(workflow)
        result = _result_of(execution)
        result["totalSteps"] = len(steps)
        result["workflowName"] = workflow.name
        result.setdefault("logs", [])
        _append_log(execution, f"[INFO] 启动工作流 {workflow.name}（{len(steps)} 个节点）")
        _flush(db, execution)

        for index, step in enumerate(steps):
            step_key = str(step.get("key") or f"step-{index}")
            step_title = str(step.get("title") or step_key)
            result["currentStep"] = step_key
            _append_log(execution, f"[INFO] 执行节点 {step_title} ({step_key})")
            _flush(db, execution)

            try:
                await _execute_step(
                    step, {"execution_id": execution_id, "index": index}, step_handler
                )
            except Exception as exc:
                execution.status = "failed"
                execution.error_message = f"节点 {step_title} 执行失败: {exc}"
                _append_log(execution, f"[ERROR] 节点 {step_title} 执行失败: {exc}")
                execution.completed_at = _utcnow()
                _finalize(execution, result, failed=True)
                _flush(db, execution)
                db.refresh(execution)
                logger.error("Workflow execution %s failed at %s: %s", execution_id, step_key, exc)
                return execution

            if step.get("fail"):
                execution.status = "failed"
                execution.error_message = f"节点 {step_title} 标记为失败"
                _append_log(execution, f"[ERROR] 节点 {step_title} 标记为失败")
                execution.completed_at = _utcnow()
                _finalize(execution, result, failed=True)
                _flush(db, execution)
                db.refresh(execution)
                return execution

            _append_log(execution, f"[SUCCESS] 节点 {step_title} 完成")
            result["progress"] = round((index + 1) / max(len(steps), 1) * 100)
            _flush(db, execution)
            if step_delay:
                await asyncio.sleep(step_delay)

        execution.status = "completed"
        execution.completed_at = _utcnow()
        _finalize(execution, result, failed=False)
        _append_log(execution, f"[SUCCESS] 工作流 {workflow.name} 执行完成")
        _flush(db, execution)
        db.refresh(execution)
        logger.info("Workflow execution %s completed", execution_id)
        return execution
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def list_logs(execution_id: str) -> list[str]:
    """Return the log lines recorded for *execution_id* (empty when unknown)."""
    db = SessionLocal()
    try:
        execution = (
            db.query(WorkflowExecution).filter(WorkflowExecution.id == execution_id).first()
        )
        if execution is None or not isinstance(execution.result, dict):
            return []
        logs = execution.result.get("logs")
        return [str(line) for line in logs] if isinstance(logs, list) else []
    finally:
        db.close()


async def run_execution_task(execution_id: str, *, step_delay: float = 0.05) -> None:
    """Fire-and-forget wrapper so routers can schedule execution off-request."""
    try:
        await run_execution(execution_id, step_delay=step_delay)
    except Exception as exc:  # pragma: no cover - defensive background task
        logger.error("Background workflow execution %s failed: %s", execution_id, exc)
