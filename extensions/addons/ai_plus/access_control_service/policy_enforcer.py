# -*- coding: utf-8 -*-
"""Policy Enforcer - Enforces access control policies."""

import logging
import sys
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

# Add project root to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))

logger = logging.getLogger(__name__)


class PolicyEnforcer:
    """Policy Enforcer for access control decisions."""

    def __init__(self, access_control_manager):
        """
        Initialize Policy Enforcer.

        Args:
            access_control_manager: AccessControlManager instance
        """
        self.access_control_manager = access_control_manager
        self._audit_log: List[Dict[str, Any]] = []

    def enforce_policy(
        self,
        subject_id: str,
        subject_type: str,
        subject_attributes: Dict[str, Any],
        subject_roles: List[str],
        subject_groups: List[str],
        resource_id: str,
        resource_type: str,
        resource_attributes: Dict[str, Any],
        resource_owner: Optional[str],
        action: str,
        environment_attributes: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Enforce access control policy.

        Args:
            subject_id: Subject ID
            subject_type: Subject type
            subject_attributes: Subject attributes
            subject_roles: Subject roles
            subject_groups: Subject groups
            resource_id: Resource ID
            resource_type: Resource type
            resource_attributes: Resource attributes
            resource_owner: Resource owner
            action: Action
            environment_attributes: Environment attributes

        Returns:
            Access decision
        """
        # Check access using the access control manager
        decision = self.access_control_manager.check_access(
            subject_id=subject_id,
            subject_type=subject_type,
            subject_attributes=subject_attributes,
            subject_roles=subject_roles,
            subject_groups=subject_groups,
            resource_id=resource_id,
            resource_type=resource_type,
            resource_attributes=resource_attributes,
            resource_owner=resource_owner,
            action=action,
            environment_attributes=environment_attributes,
        )

        # Log the decision
        self._log_decision(
            subject_id=subject_id,
            resource_id=resource_id,
            action=action,
            decision=decision,
        )

        return decision

    def _log_decision(
        self,
        subject_id: str,
        resource_id: str,
        action: str,
        decision: Dict[str, Any],
    ) -> None:
        """
        Log access decision for audit.

        Args:
            subject_id: Subject ID
            resource_id: Resource ID
            action: Action
            decision: Access decision
        """
        log_entry = {
            "id": str(len(self._audit_log) + 1),
            "subject_id": subject_id,
            "resource_id": resource_id,
            "action": action,
            "allowed": decision["allowed"],
            "decision_type": decision["decision_type"],
            "reason": decision["reason"],
            "matched_policies": decision["matched_policies"],
            "matched_roles": decision["matched_roles"],
            "timestamp": decision["evaluated_at"],
        }

        self._audit_log.append(log_entry)

        logger.info(
            f"Access decision logged: subject={subject_id}, "
            f"resource={resource_id}, action={action}, allowed={decision['allowed']}"
        )

    def get_audit_logs(
        self,
        subject_id: Optional[str] = None,
        resource_id: Optional[str] = None,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Get audit logs with optional filtering.

        Args:
            subject_id: Filter by subject ID
            resource_id: Filter by resource ID
            start_time: Filter by start time (timestamp)
            end_time: Filter by end time (timestamp)
            limit: Maximum number of results
            offset: Offset for pagination

        Returns:
            List of audit log entries
        """
        logs = self._audit_log

        # Apply filters
        if subject_id:
            logs = [log for log in logs if log["subject_id"] == subject_id]

        if resource_id:
            logs = [log for log in logs if log["resource_id"] == resource_id]

        if start_time:
            logs = [log for log in logs if log["timestamp"] >= start_time]

        if end_time:
            logs = [log for log in logs if log["timestamp"] <= end_time]

        # Sort by timestamp descending
        logs = sorted(logs, key=lambda x: x["timestamp"], reverse=True)

        # Apply pagination
        return logs[offset : offset + limit]

    def clear_audit_logs(self) -> None:
        """Clear all audit logs."""
        self._audit_log.clear()
        logger.info("Audit logs cleared")

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get access control statistics.

        Returns:
            Statistics dictionary
        """
        total_decisions = len(self._audit_log)
        allowed_count = sum(1 for log in self._audit_log if log["allowed"])
        denied_count = total_decisions - allowed_count

        decision_type_counts = {}
        for log in self._audit_log:
            decision_type = log["decision_type"]
            decision_type_counts[decision_type] = decision_type_counts.get(decision_type, 0) + 1

        return {
            "total_decisions": total_decisions,
            "allowed_count": allowed_count,
            "denied_count": denied_count,
            "allow_rate": allowed_count / total_decisions if total_decisions > 0 else 0,
            "decision_type_counts": decision_type_counts,
        }
