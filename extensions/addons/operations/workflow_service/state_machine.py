# -*- coding: utf-8 -*-
"""Workflow state machine management (XState-like abstraction)."""

from __future__ import annotations

from typing import Any, Dict, List

from extensions.addons.operations.workflow_service.schemas import WorkflowStatus, WorkflowTask


class StateTransition:
    """A transition between workflow states."""

    def __init__(self, event: str, source: str, target: str) -> None:
        self.event = event
        self.source = source
        self.target = target


class WorkflowStateMachine:
    """State machine for a workflow task."""

    TRANSITIONS: List[StateTransition] = [
        StateTransition("start", WorkflowStatus.PENDING.value, WorkflowStatus.RUNNING.value),
        StateTransition("start", WorkflowStatus.SCHEDULED.value, WorkflowStatus.RUNNING.value),
        StateTransition("pause", WorkflowStatus.RUNNING.value, WorkflowStatus.PAUSED.value),
        StateTransition("resume", WorkflowStatus.PAUSED.value, WorkflowStatus.RUNNING.value),
        StateTransition("succeed", WorkflowStatus.RUNNING.value, WorkflowStatus.SUCCEEDED.value),
        StateTransition("retry", WorkflowStatus.FAILED.value, WorkflowStatus.RETRYING.value),
        StateTransition("fail", WorkflowStatus.RUNNING.value, WorkflowStatus.FAILED.value),
        StateTransition("timeout", WorkflowStatus.RUNNING.value, WorkflowStatus.TIMEOUT.value),
        StateTransition("complete", WorkflowStatus.SUCCEEDED.value, WorkflowStatus.COMPLETED.value),
        StateTransition("complete", WorkflowStatus.FAILED.value, WorkflowStatus.COMPLETED.value),
    ]

    def __init__(self, task: WorkflowTask) -> None:
        self.task = task
        self.history: List[Dict[str, Any]] = [
            {"state": task.status.value, "event": "init", "reason": "state machine created"}
        ]

    def transition(self, event: WorkflowStatus, reason: str = "") -> bool:
        source = self.task.status.value
        target = event.value
        valid = any(t.source == source and t.target == target for t in self.TRANSITIONS)
        if valid or source == target:
            self.task.status = event
            self.history.append({"state": target, "event": event.value, "reason": reason})
            return True
        return False

    def get_state(self) -> Dict[str, Any]:
        return {
            "task_id": self.task.task_id,
            "status": self.task.status.value,
            "history": self.history,
        }
