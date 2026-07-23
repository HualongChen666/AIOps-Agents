# -*- coding: utf-8 -*-
"""
Approval History
Tracks and provides audit trail for approvals
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

from loguru import logger


@dataclass
class ApprovalRecord:
    """
    Approval record

    Attributes:
        record_id: Record identifier
        request_id: Request identifier
        workflow_id: Workflow identifier
        action: Action taken
        actor: Actor who took action
        timestamp: Action timestamp
        details: Additional details
    """

    record_id: str
    request_id: str
    workflow_id: str
    action: str
    actor: str
    timestamp: datetime = field(default_factory=datetime.now)
    details: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "record_id": self.record_id,
            "request_id": self.request_id,
            "workflow_id": self.workflow_id,
            "action": self.action,
            "actor": self.actor,
            "timestamp": self.timestamp.isoformat(),
            "details": self.details,
        }


class ApprovalHistory:
    """
    Approval history tracker

    Maintains audit trail of all approval actions
    """

    def __init__(self):
        """Initialize approval history"""
        self.records: List[ApprovalRecord] = []

    def record_action(
        self,
        request_id: str,
        workflow_id: str,
        action: str,
        actor: str,
        details: Optional[Dict] = None,
    ) -> ApprovalRecord:
        """
        Record approval action

        Args:
            request_id: Request identifier
            workflow_id: Workflow identifier
            action: Action taken
            actor: Actor who took action
            details: Additional details

        Returns:
            Approval record
        """
        record_id = f"{request_id}-{int(datetime.now().timestamp())}"

        record = ApprovalRecord(
            record_id=record_id,
            request_id=request_id,
            workflow_id=workflow_id,
            action=action,
            actor=actor,
            details=details or {},
        )

        self.records.append(record)

        logger.info(f"Recorded approval action: {action} by {actor} for {request_id}")

        return record

    def get_history(
        self,
        request_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
        actor: Optional[str] = None,
        since: Optional[datetime] = None,
    ) -> List[ApprovalRecord]:
        """
        Get approval history with filters

        Args:
            request_id: Filter by request ID
            workflow_id: Filter by workflow ID
            actor: Filter by actor
            since: Filter by timestamp

        Returns:
            Filtered approval records
        """
        filtered = self.records

        if request_id:
            filtered = [r for r in filtered if r.request_id == request_id]

        if workflow_id:
            filtered = [r for r in filtered if r.workflow_id == workflow_id]

        if actor:
            filtered = [r for r in filtered if r.actor == actor]

        if since:
            filtered = [r for r in filtered if r.timestamp >= since]

        return filtered

    def get_audit_trail(self, request_id: str) -> List[Dict]:
        """
        Get complete audit trail for a request

        Args:
            request_id: Request identifier

        Returns:
            Audit trail
        """
        records = self.get_history(request_id=request_id)

        return [r.to_dict() for r in records]
