# -*- coding: utf-8 -*-
"""
Approval Workflow
Implements approval workflow with visualization support
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from loguru import logger


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
        status: Current status
        approved_at: Approval timestamp
        rejected_at: Rejection timestamp
        comment: Approval/rejection comment
    """

    step_id: str
    name: str
    approver: str
    required: bool = True
    timeout_minutes: int = 60
    status: ApprovalStatus = ApprovalStatus.PENDING
    approved_at: Optional[datetime] = None
    rejected_at: Optional[datetime] = None
    comment: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "step_id": self.step_id,
            "name": self.name,
            "approver": self.approver,
            "required": self.required,
            "timeout_minutes": self.timeout_minutes,
            "status": self.status.value,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "rejected_at": self.rejected_at.isoformat() if self.rejected_at else None,
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

        # Move to next step
        self._advance_workflow(request)

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
