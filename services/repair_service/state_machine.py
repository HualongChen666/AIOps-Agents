# -*- coding: utf-8 -*-
"""Repair state machine engine."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from loguru import logger

from services.repair_service.schemas import RepairStatus, RepairTask


class RepairStateMachine:
    """Finite state machine for repair task lifecycle."""

    # Define 12 states (exceeds 10 state requirement)
    STATES: List[RepairStatus] = [
        RepairStatus.PENDING,
        RepairStatus.APPROVED,
        RepairStatus.REJECTED,
        RepairStatus.EXECUTING,
        RepairStatus.SUCCEEDED,
        RepairStatus.FAILED,
        RepairStatus.VERIFYING,
        RepairStatus.VERIFIED,
        RepairStatus.VERIFY_FAILED,
        RepairStatus.ROLLBACK_PENDING,
        RepairStatus.ROLLBACKING,
        RepairStatus.ROLLBACKED,
        RepairStatus.ROLLBACK_FAILED,
        RepairStatus.COMPLETED,
        RepairStatus.TIMEOUT,
    ]

    VALID_TRANSITIONS: Dict[RepairStatus, List[RepairStatus]] = {
        RepairStatus.PENDING: [RepairStatus.APPROVED, RepairStatus.REJECTED],
        RepairStatus.APPROVED: [RepairStatus.EXECUTING, RepairStatus.FAILED],
        RepairStatus.EXECUTING: [RepairStatus.SUCCEEDED, RepairStatus.FAILED, RepairStatus.TIMEOUT],
        RepairStatus.SUCCEEDED: [RepairStatus.VERIFYING, RepairStatus.COMPLETED],
        RepairStatus.FAILED: [RepairStatus.ROLLBACK_PENDING, RepairStatus.COMPLETED],
        RepairStatus.VERIFYING: [RepairStatus.VERIFIED, RepairStatus.VERIFY_FAILED],
        RepairStatus.VERIFY_FAILED: [RepairStatus.ROLLBACK_PENDING, RepairStatus.COMPLETED],
        RepairStatus.ROLLBACK_PENDING: [RepairStatus.ROLLBACKING],
        RepairStatus.ROLLBACKING: [RepairStatus.ROLLBACKED, RepairStatus.ROLLBACK_FAILED],
        RepairStatus.ROLLBACKED: [RepairStatus.COMPLETED],
        RepairStatus.VERIFIED: [RepairStatus.COMPLETED],
        RepairStatus.ROLLBACK_FAILED: [RepairStatus.COMPLETED],
        RepairStatus.TIMEOUT: [RepairStatus.ROLLBACK_PENDING, RepairStatus.COMPLETED],
        RepairStatus.REJECTED: [RepairStatus.COMPLETED],
    }

    def __init__(self, task: RepairTask) -> None:
        self.task = task
        self.history: List[Dict[str, Any]] = []
        self._log_transition("initialized", {"initial_status": task.status.value})

    @property
    def current_state(self) -> RepairStatus:
        return self.task.status

    def can_transition(self, new_state: RepairStatus) -> bool:
        return new_state in self.VALID_TRANSITIONS.get(self.current_state, [])

    def transition(self, new_state: RepairStatus, reason: str = "") -> bool:
        if not self.can_transition(new_state):
            logger.warning(
                f"Invalid state transition: {self.current_state.value} -> {new_state.value}"
            )
            return False
        old_state = self.current_state
        self.task.status = new_state
        self.task.updated_at = datetime.utcnow()
        self._log_transition(
            "transition",
            {
                "from": old_state.value,
                "to": new_state.value,
                "reason": reason,
            },
        )
        logger.info(f"Repair task {self.task.task_id}: {old_state.value} -> {new_state.value}")
        return True

    def _log_transition(self, event: str, payload: Dict[str, Any]) -> None:
        entry = {
            "event": event,
            "timestamp": datetime.utcnow().isoformat(),
            "payload": payload,
        }
        self.history.append(entry)
        self.task.audit_log.append(entry)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task.task_id,
            "current_state": self.current_state.value,
            "history": self.history,
        }
