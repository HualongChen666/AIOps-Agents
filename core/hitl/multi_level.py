# -*- coding: utf-8 -*-
"""
Multi-level Approval
Implements multi-level approval mechanism
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional

from loguru import logger

from .approval import ApprovalStatus, ApprovalStep, ApprovalWorkflow


class ApprovalLevel(Enum):
    """Approval level"""

    L1 = "l1"  # Team lead
    L2 = "l2"  # Manager
    L3 = "l3"  # Director
    L4 = "l4"  # VP


@dataclass
class ApprovalConfig:
    """
    Approval configuration

    Attributes:
        level: Approval level
        approvers: List of approvers at this level
        required: Whether approval is required
        timeout_minutes: Timeout in minutes
    """

    level: ApprovalLevel
    approvers: List[str]
    required: bool = True
    timeout_minutes: int = 60


class MultiLevelApprover:
    """
    Multi-level approver

    Implements hierarchical approval workflows
    """

    def __init__(self, workflow: ApprovalWorkflow):
        """
        Initialize multi-level approver

        Args:
            workflow: Approval workflow
        """
        self.workflow = workflow
        self.level_configs: Dict[ApprovalLevel, ApprovalConfig] = {}

    def configure_level(self, config: ApprovalConfig) -> None:
        """
        Configure approval level

        Args:
            config: Approval configuration
        """
        self.level_configs[config.level] = config
        logger.info(f"Configured approval level {config.level.value}")

    def create_multi_level_request(
        self,
        workflow_id: str,
        title: str,
        description: str,
        min_level: ApprovalLevel = ApprovalLevel.L1,
        context: Optional[Dict] = None,
    ):
        """
        Create multi-level approval request

        Args:
            workflow_id: Workflow identifier
            title: Request title
            description: Request description
            min_level: Minimum approval level required
            context: Additional context

        Returns:
            Approval request
        """
        steps = []

        # Create steps for each configured level
        for level in [ApprovalLevel.L1, ApprovalLevel.L2, ApprovalLevel.L3, ApprovalLevel.L4]:
            config = self.level_configs.get(level)
            if config and config.level.value >= min_level.value:
                # Create step for each approver at this level
                for i, approver in enumerate(config.approvers):
                    step = ApprovalStep(
                        step_id=f"{level.value}_{i}",
                        name=f"{level.value.upper()} Approval ({approver})",
                        approver=approver,
                        required=config.required,
                        timeout_minutes=config.timeout_minutes,
                    )
                    steps.append(step)

        return self.workflow.create_request(
            workflow_id=workflow_id,
            title=title,
            description=description,
            steps=steps,
            context=context,
        )

    def get_required_approvers(self, request_id: str) -> List[str]:
        """
        Get required approvers for request

        Args:
            request_id: Request identifier

        Returns:
            List of required approvers
        """
        request = self.workflow.active_requests.get(request_id)
        if not request:
            return []

        return [step.approver for step in request.steps if step.required]

    def get_pending_approvals(self, approver: str) -> List[Dict]:
        """
        Get pending approvals for an approver

        Args:
            approver: Approver identifier

        Returns:
            List of pending approvals
        """
        pending = []

        for request in self.workflow.active_requests.values():
            for step in request.steps:
                if step.approver == approver and step.status == ApprovalStatus.PENDING:
                    pending.append(
                        {
                            "request_id": request.request_id,
                            "title": request.title,
                            "step_id": step.step_id,
                            "step_name": step.name,
                            "created_at": request.created_at.isoformat(),
                        }
                    )

        return pending
