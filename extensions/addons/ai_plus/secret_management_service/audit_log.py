# -*- coding: utf-8 -*-
"""Audit log service for tracking secret access and modifications."""

import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from .config import Config
except ImportError:
    from config import Config
from loguru import logger


class AuditLogEntry:
    """Represents an audit log entry."""

    def __init__(
        self,
        secret_id: str,
        action: str,
        principal: str,
        principal_type: str = "user",
        result: str = "success",
        details: str = "",
        metadata: Dict[str, str] = None,
    ):
        """Initialize audit log entry.

        Args:
            secret_id: Secret identifier
            action: Action performed (create, read, update, delete, rotate, grant_access, revoke_access)
            principal: User or service account
            principal_type: Type of principal
            result: Result of action (success, failure)
            details: Additional details
            metadata: Additional metadata
        """
        self.log_id = str(uuid.uuid4())
        self.secret_id = secret_id
        self.action = action
        self.principal = principal
        self.principal_type = principal_type
        self.timestamp = int(datetime.now().timestamp() * 1000)
        self.result = result
        self.details = details
        self.metadata = metadata or {}

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "log_id": self.log_id,
            "secret_id": self.secret_id,
            "action": self.action,
            "principal": self.principal,
            "principal_type": self.principal_type,
            "timestamp": self.timestamp,
            "result": self.result,
            "details": self.details,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "AuditLogEntry":
        """Create from dictionary."""
        entry = cls(
            secret_id=data["secret_id"],
            action=data["action"],
            principal=data["principal"],
            principal_type=data.get("principal_type", "user"),
            result=data.get("result", "success"),
            details=data.get("details", ""),
            metadata=data.get("metadata", {}),
        )
        entry.log_id = data["log_id"]
        entry.timestamp = data["timestamp"]
        return entry


class AuditLog:
    """Audit log manager."""

    VALID_ACTIONS = {
        "create",
        "read",
        "update",
        "delete",
        "rotate",
        "grant_access",
        "revoke_access",
        "list",
        "get_versions",
        "revert_version",
    }

    def __init__(self, log_path: str = None):
        """Initialize audit log.

        Args:
            log_path: Path to store audit logs
        """
        self.log_path = Path(log_path or Config.AUDIT_LOG_PATH)
        self.log_path.mkdir(parents=True, exist_ok=True)

        self._logs: List[AuditLogEntry] = []
        self._load_logs()

        logger.info("Audit log initialized")

    def _load_logs(self):
        """Load audit logs from storage."""
        try:
            log_file = self.log_path / "audit_log.json"
            if log_file.exists():
                with open(log_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._logs = [AuditLogEntry.from_dict(entry) for entry in data]
                logger.info(f"Loaded {len(self._logs)} audit log entries")
            else:
                logger.info("No existing audit logs found")
        except Exception as e:
            logger.error(f"Failed to load audit logs: {e}")
            self._logs = []

    def _save_logs(self) -> bool:
        """Save audit logs to storage."""
        try:
            log_file = self.log_path / "audit_log.json"
            data = [entry.to_dict() for entry in self._logs]

            with open(log_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            # Set file permissions
            try:
                import stat
                os.chmod(log_file, stat.S_IRUSR | stat.S_IWUSR)
            except Exception:
                pass

            logger.debug(f"Saved {len(self._logs)} audit log entries")
            return True
        except Exception as e:
            logger.error(f"Failed to save audit logs: {e}")
            return False

    def log(
        self,
        secret_id: str,
        action: str,
        principal: str,
        principal_type: str = "user",
        result: str = "success",
        details: str = "",
        metadata: Dict[str, str] = None,
    ) -> AuditLogEntry:
        """Log an audit event.

        Args:
            secret_id: Secret identifier
            action: Action performed
            principal: User or service account
            principal_type: Type of principal
            result: Result of action
            details: Additional details
            metadata: Additional metadata

        Returns:
            Created audit log entry
        """
        if action not in self.VALID_ACTIONS:
            logger.warning(f"Invalid audit action: {action}")

        entry = AuditLogEntry(
            secret_id=secret_id,
            action=action,
            principal=principal,
            principal_type=principal_type,
            result=result,
            details=details,
            metadata=metadata,
        )

        self._logs.append(entry)

        # Save immediately for critical logs
        if action in {"delete", "rotate", "grant_access", "revoke_access"}:
            self._save_logs()

        logger.debug(f"Logged audit event: {action} by {principal} on {secret_id}")
        return entry

    def query(
        self,
        secret_id: str = None,
        action: str = None,
        principal: str = None,
        start_time: int = None,
        end_time: int = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict]:
        """Query audit logs.

        Args:
            secret_id: Filter by secret ID
            action: Filter by action
            principal: Filter by principal
            start_time: Filter by start timestamp
            end_time: Filter by end timestamp
            limit: Maximum number of results
            offset: Offset for pagination

        Returns:
            List of audit log entries
        """
        results = []

        for entry in self._logs:
            # Filter by secret_id
            if secret_id and entry.secret_id != secret_id:
                continue

            # Filter by action
            if action and entry.action != action:
                continue

            # Filter by principal
            if principal and entry.principal != principal:
                continue

            # Filter by time range
            if start_time and entry.timestamp < start_time:
                continue
            if end_time and entry.timestamp > end_time:
                continue

            results.append(entry.to_dict())

        # Sort by timestamp (newest first)
        results.sort(key=lambda x: x["timestamp"], reverse=True)

        # Pagination
        total = len(results)
        results = results[offset:offset + limit]

        return results

    def get_by_secret(self, secret_id: str, limit: int = 100) -> List[Dict]:
        """Get all audit logs for a secret.

        Args:
            secret_id: Secret identifier
            limit: Maximum number of results

        Returns:
            List of audit log entries
        """
        return self.query(secret_id=secret_id, limit=limit)

    def get_by_principal(self, principal: str, limit: int = 100) -> List[Dict]:
        """Get all audit logs for a principal.

        Args:
            principal: Principal identifier
            limit: Maximum number of results

        Returns:
            List of audit log entries
        """
        return self.query(principal=principal, limit=limit)

    def get_failed_attempts(self, limit: int = 100) -> List[Dict]:
        """Get all failed access attempts.

        Args:
            limit: Maximum number of results

        Returns:
            List of failed audit log entries
        """
        failed = [entry for entry in self._logs if entry.result == "failure"]
        return [entry.to_dict() for entry in failed[:limit]]

    def cleanup_old_logs(self, retention_days: int = None) -> int:
        """Clean up old audit logs beyond retention period.

        Args:
            retention_days: Retention period in days

        Returns:
            Number of logs cleaned up
        """
        retention = retention_days or Config.AUDIT_LOG_RETENTION_DAYS
        cutoff_time = int((datetime.now() - timedelta(days=retention)).timestamp() * 1000)

        old_count = len(self._logs)
        self._logs = [entry for entry in self._logs if entry.timestamp > cutoff_time]
        cleaned = old_count - len(self._logs)

        if cleaned > 0:
            self._save_logs()
            logger.info(f"Cleaned up {cleaned} old audit log entries")

        return cleaned

    def get_statistics(self) -> Dict[str, Any]:
        """Get audit log statistics.

        Returns:
            Statistics dictionary
        """
        if not self._logs:
            return {
                "total_entries": 0,
                "by_action": {},
                "by_result": {},
                "by_principal": {},
            }

        by_action = {}
        by_result = {}
        by_principal = {}

        for entry in self._logs:
            # Count by action
            by_action[entry.action] = by_action.get(entry.action, 0) + 1

            # Count by result
            by_result[entry.result] = by_result.get(entry.result, 0) + 1

            # Count by principal
            by_principal[entry.principal] = by_principal.get(entry.principal, 0) + 1

        return {
            "total_entries": len(self._logs),
            "by_action": by_action,
            "by_result": by_result,
            "by_principal": by_principal,
        }
