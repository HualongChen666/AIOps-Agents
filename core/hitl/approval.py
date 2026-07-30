# -*- coding: utf-8 -*-
import logging

"""
Approval Workflow
Implements approval workflow with visualization support
"""

import asyncio
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from loguru import logger

from .history import ApprovalHistory

try:
    from core.agent.subagent import SubAgentDispatcher

    SUBAGENT_AVAILABLE = True
except Exception as e:
    logging.exception("Unexpected exception: %s", e)
    SubAgentDispatcher = None  # type: ignore[misc,assignment]
    SUBAGENT_AVAILABLE = False


class ApprovalStatus(Enum):
    """Approval status"""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


@dataclass
class ApprovalStep:
    """
    Approval step in workflow

    Attributes:
        step_id: Step identifier
        name: Step name
        approver: Approver identifier
        required: Whether approval is required
        timeout_minutes: Timeout in minutes
        validity_minutes: Approval validity window in minutes (default 5)
        status: Current status
        approved_at: Approval timestamp
        rejected_at: Rejection timestamp
        expires_at: Approval expiration timestamp
        comment: Approval/rejection comment
    """

    step_id: str
    name: str
    approver: str
    required: bool = True
    timeout_minutes: int = 60
    validity_minutes: int = 5
    status: ApprovalStatus = ApprovalStatus.PENDING
    approved_at: Optional[datetime] = None
    rejected_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    comment: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "step_id": self.step_id,
            "name": self.name,
            "approver": self.approver,
            "required": self.required,
            "timeout_minutes": self.timeout_minutes,
            "validity_minutes": self.validity_minutes,
            "status": self.status.value,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "rejected_at": self.rejected_at.isoformat() if self.rejected_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "comment": self.comment,
        }


@dataclass
class ApprovalRequest:
    """
    Approval request

    Attributes:
        request_id: Request identifier
        workflow_id: Workflow identifier
        title: Request title
        description: Request description
        context: Additional context
        requester: Requester identifier
        created_at: Creation timestamp
        status: Overall status
        steps: Approval steps
        current_step: Current step index
        precondition_checker: Optional callable to re-evaluate preconditions
    """

    request_id: str
    workflow_id: str
    title: str
    description: str
    context: Dict[str, Any] = field(default_factory=dict)
    requester: str = "system"
    created_at: datetime = field(default_factory=datetime.now)
    status: ApprovalStatus = ApprovalStatus.PENDING
    steps: List[ApprovalStep] = field(default_factory=list)
    current_step: int = 0
    precondition_checker: Optional[Any] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "request_id": self.request_id,
            "workflow_id": self.workflow_id,
            "title": self.title,
            "description": self.description,
            "context": self.context,
            "requester": self.requester,
            "created_at": self.created_at.isoformat(),
            "status": self.status.value,
            "steps": [step.to_dict() for step in self.steps],
            "current_step": self.current_step,
        }


class ApprovalWorkflow:
    """
    Approval workflow manager

    Manages approval workflows with visualization support
    """

    def __init__(self):
        """Initialize approval workflow"""
        self.active_requests: Dict[str, ApprovalRequest] = {}
        self.completed_requests: Dict[str, ApprovalRequest] = {}
        self.history = ApprovalHistory()
        self._lock = threading.RLock()
        self._request_locks: Dict[str, threading.RLock] = {}

    def _get_request_lock(self, request_id: str) -> threading.RLock:
        """Return a per-request reentrant lock, creating it on first use."""
        lock = self._request_locks.get(request_id)
        if lock is None:
            with self._lock:
                lock = self._request_locks.get(request_id)
                if lock is None:
                    lock = threading.RLock()
                    self._request_locks[request_id] = lock
        return lock

    def create_request(
        self,
        workflow_id: str,
        title: str,
        description: str,
        steps: List[ApprovalStep],
        context: Optional[Dict] = None,
    ) -> ApprovalRequest:
        """
        Create approval request

        Args:
            workflow_id: Workflow identifier
            title: Request title
            description: Request description
            steps: Approval steps
            context: Additional context

        Returns:
            Approval request
        """
        request_id = f"{workflow_id}-{int(datetime.now().timestamp())}"

        request = ApprovalRequest(
            request_id=request_id,
            workflow_id=workflow_id,
            title=title,
            description=description,
            context=context or {},
            steps=steps,
        )

        self.active_requests[request_id] = request

        logger.info(f"Created approval request {request_id} with {len(steps)} steps")

        return request

    def approve_step(
        self, request_id: str, step_id: str, approver: str, comment: Optional[str] = None
    ) -> bool:
        """
        Approve a step

        Args:
            request_id: Request identifier
            step_id: Step identifier
            approver: Approver identifier
            comment: Approval comment

        Returns:
            True if approved successfully
        """
        with self._get_request_lock(request_id):
            request = self.active_requests.get(request_id)
            if not request:
                logger.warning(f"Request {request_id} not found")
                return False

            step = next((s for s in request.steps if s.step_id == step_id), None)
            if not step:
                logger.warning(f"Step {step_id} not found in request {request_id}")
                return False

            # Verify approver
            if step.approver != approver:
                logger.warning(f"Approver mismatch: expected {step.approver}, got {approver}")
                return False

            # Update step
            step.status = ApprovalStatus.APPROVED
            step.approved_at = datetime.now()
            step.comment = comment
            step.expires_at = datetime.now() + timedelta(minutes=step.validity_minutes)

            # Move to next step
            self._advance_workflow(request)

            self.history.record_action(
                request_id=request_id,
                workflow_id=request.workflow_id,
                action="approved",
                actor=approver,
                details={"step_id": step_id, "comment": comment},
            )

            logger.info(f"Step {step_id} approved by {approver}")

            return True

    def reject_step(
        self, request_id: str, step_id: str, approver: str, comment: Optional[str] = None
    ) -> bool:
        """
        Reject a step

        Args:
            request_id: Request identifier
            step_id: Step identifier
            approver: Approver identifier
            comment: Rejection comment

        Returns:
            True if rejected successfully
        """
        with self._get_request_lock(request_id):
            request = self.active_requests.get(request_id)
            if not request:
                return False

            step = next((s for s in request.steps if s.step_id == step_id), None)
            if not step:
                return False

            # Verify approver
            if step.approver != approver:
                return False

            # Update step
            step.status = ApprovalStatus.REJECTED
            step.rejected_at = datetime.now()
            step.comment = comment

            # Reject entire workflow
            request.status = ApprovalStatus.REJECTED

            # Move to completed
            self.completed_requests[request_id] = request
            del self.active_requests[request_id]

            self.history.record_action(
                request_id=request_id,
                workflow_id=request.workflow_id,
                action="rejected",
                actor=approver,
                details={"step_id": step_id, "comment": comment},
            )

            logger.info(f"Step {step_id} rejected by {approver}")

            return True

    def _advance_workflow(self, request: ApprovalRequest) -> None:
        """Advance workflow to next step"""
        # Check if all steps are approved
        all_approved = all(s.status == ApprovalStatus.APPROVED for s in request.steps)

        if all_approved:
            request.status = ApprovalStatus.APPROVED
            self.completed_requests[request.request_id] = request
            del self.active_requests[request.request_id]
            logger.info(f"Workflow {request.request_id} fully approved")
        else:
            # Move to next pending step
            for i, step in enumerate(request.steps):
                if step.status == ApprovalStatus.PENDING:
                    request.current_step = i
                    break

    def cancel_request(self, request_id: str, reason: str = "manual takeover") -> bool:
        """Cancel / manually take over an active workflow and move it to completed."""
        with self._get_request_lock(request_id):
            request = self.active_requests.get(request_id)
            if not request:
                return False
            request.status = ApprovalStatus.REJECTED
            for step in request.steps:
                if step.status == ApprovalStatus.PENDING:
                    step.status = ApprovalStatus.REJECTED
                    step.rejected_at = datetime.now()
                    step.comment = reason
            self.completed_requests[request_id] = request
            del self.active_requests[request_id]
            self.history.record_action(
                request_id=request_id,
                workflow_id=request.workflow_id,
                action="cancelled",
                actor="system",
                details={"reason": reason},
            )
            self._interrupt_associated_agent(request)
            logger.info(f"Request {request_id} cancelled/taken over: {reason}")
            return True

    def _interrupt_associated_agent(self, request: ApprovalRequest) -> bool:
        """Terminate any running subagent associated with this request."""
        if not SUBAGENT_AVAILABLE or not callable(SubAgentDispatcher):
            return False
        agent_id = request.context.get("agent_id") if request.context else None
        if not agent_id:
            return False
        try:
            dispatcher = getattr(SubAgentDispatcher, "_instance", None) or SubAgentDispatcher()
            terminated = dispatcher.terminate(agent_id)
            logger.info(
                f"Interrupted agent {agent_id} for request {request.request_id}: {terminated}"
            )
            return terminated
        except Exception as exc:  # pragma: no cover
            logger.warning(f"Failed to interrupt agent {agent_id}: {exc}")
            return False

    def get_request_status(self, request_id: str) -> Optional[Dict]:
        """
        Get request status

        Args:
            request_id: Request identifier

        Returns:
            Request status dictionary
        """
        request = self.active_requests.get(request_id) or self.completed_requests.get(request_id)
        if request:
            return request.to_dict()
        return None

    def get_visualization_data(self, request_id: str) -> Optional[Dict]:
        """
        Get visualization data for request

        Args:
            request_id: Request identifier

        Returns:
            Visualization data
        """
        request = self.active_requests.get(request_id) or self.completed_requests.get(request_id)
        if not request:
            return None

        return {
            "request_id": request.request_id,
            "workflow_id": request.workflow_id,
            "title": request.title,
            "status": request.status.value,
            "steps": [
                {
                    "step_id": step.step_id,
                    "name": step.name,
                    "status": step.status.value,
                    "approver": step.approver,
                    "is_current": (
                        step == request.steps[request.current_step]
                        if request.current_step < len(request.steps)
                        else False
                    ),
                }
                for step in request.steps
            ],
            "progress": self._calculate_progress(request),
        }

    def _calculate_progress(self, request: ApprovalRequest) -> float:
        """Calculate workflow progress"""
        if not request.steps:
            return 0.0

        approved_count = sum(1 for s in request.steps if s.status == ApprovalStatus.APPROVED)
        return approved_count / len(request.steps)

    def is_timed_out(self, request_id: str) -> bool:
        """Check whether the current pending step has exceeded its timeout."""
        request = self.active_requests.get(request_id)
        if not request or request.current_step >= len(request.steps):
            return False
        step = request.steps[request.current_step]
        if step.status != ApprovalStatus.PENDING:
            return False
        elapsed = (datetime.now() - request.created_at).total_seconds() / 60.0
        return elapsed > step.timeout_minutes

    def is_approval_valid(self, request_id: str) -> bool:
        """Check whether the latest approval is still within its validity window."""
        request = self.active_requests.get(request_id) or self.completed_requests.get(request_id)
        if not request:
            return False
        if request.status != ApprovalStatus.APPROVED:
            return False
        # The latest approved step determines validity.
        approved_steps = [s for s in request.steps if s.status == ApprovalStatus.APPROVED]
        if not approved_steps:
            return False
        latest = max(approved_steps, key=lambda s: s.approved_at or datetime.min)
        if latest.expires_at is None:
            return True
        return datetime.now() < latest.expires_at

    def revalidate_before_execution(self, request_id: str) -> tuple[bool, str]:
        """
        Re-validate preconditions before executing an approved request.

        Returns (ok, reason) where ok=True means execution is still allowed.
        """
        request = self.active_requests.get(request_id) or self.completed_requests.get(request_id)
        if not request:
            return False, "request not found"
        if request.status != ApprovalStatus.APPROVED:
            return False, f"status is {request.status.value}, not approved"
        if not self.is_approval_valid(request_id):
            return False, "approval has expired"
        if request.context.get("agent_interrupted"):
            return False, "agent execution was interrupted"
        if request.precondition_checker is not None:
            try:
                checker = request.precondition_checker
                result = checker(request)
                if asyncio.iscoroutine(result):
                    result = asyncio.run(result)
                if result is not True:
                    return False, f"precondition check failed: {result}"
            except Exception as exc:
                return False, f"precondition checker error: {exc}"
        return True, ""
