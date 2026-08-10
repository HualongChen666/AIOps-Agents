# -*- coding: utf-8 -*-
"""
Security Audit Enhancement (Phase 4)
Enterprise-grade security audit system with comprehensive logging and monitoring
"""

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from loguru import logger


class AuditEventType(Enum):
    """Audit event types"""

    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    DATA_ACCESS = "data_access"
    CONFIGURATION_CHANGE = "configuration_change"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    SECURITY_INCIDENT = "security_incident"
    POLICY_VIOLATION = "policy_violation"
    API_ACCESS = "api_access"
    SYSTEM_CHANGE = "system_change"


class AuditSeverity(Enum):
    """Audit event severity"""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class AuditEvent:
    """Audit event"""

    event_id: str
    event_type: AuditEventType
    severity: AuditSeverity
    user_id: Optional[str] = None
    ip_address: Optional[str] = None
    resource: Optional[str] = None
    action: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AuditPolicy:
    """Audit policy configuration"""

    policy_id: str
    policy_name: str
    event_types: List[AuditEventType] = field(default_factory=list)
    severity_filter: Optional[AuditSeverity] = None
    retention_period: int = 90  # days
    alert_threshold: int = 10
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


class SecurityAuditSystem:
    """Enterprise-grade security audit system"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize security audit system

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}

        # Audit events
        self.audit_events: List[AuditEvent] = []

        # Audit policies
        self.audit_policies: Dict[str, AuditPolicy] = {}
        self._initialize_default_policies()

        # Audit log storage
        self.audit_log_dir = Path(self.config.get("audit_log_dir", "./audit_logs"))
        self.audit_log_dir.mkdir(parents=True, exist_ok=True)

        # Alert handlers
        self.alert_handlers: List[Callable] = []

        # Configuration
        self.max_events = self.config.get("max_events", 10000)
        self.real_time_monitoring = self.config.get("real_time_monitoring", True)

        # Statistics
        self.total_events = 0
        self.critical_events = 0

        logger.info("Security audit system initialized")

    def _initialize_default_policies(self):
        """Initialize default audit policies"""
        # Security events policy
        self.audit_policies["security_events"] = AuditPolicy(
            policy_id="security_events",
            policy_name="Security Events Policy",
            event_types=[
                AuditEventType.USER_LOGIN,
                AuditEventType.USER_LOGOUT,
                AuditEventType.PRIVILEGE_ESCALATION,
                AuditEventType.SECURITY_INCIDENT,
                AuditEventType.POLICY_VIOLATION,
            ],
            severity_filter=AuditSeverity.WARNING,
            retention_period=180,
            alert_threshold=5,
        )

        # Data access policy
        self.audit_policies["data_access"] = AuditPolicy(
            policy_id="data_access",
            policy_name="Data Access Policy",
            event_types=[AuditEventType.DATA_ACCESS],
            severity_filter=AuditSeverity.INFO,
            retention_period=365,
            alert_threshold=20,
        )

        # Configuration changes policy
        self.audit_policies["config_changes"] = AuditPolicy(
            policy_id="config_changes",
            policy_name="Configuration Changes Policy",
            event_types=[AuditEventType.CONFIGURATION_CHANGE, AuditEventType.SYSTEM_CHANGE],
            severity_filter=AuditSeverity.WARNING,
            retention_period=365,
            alert_threshold=10,
        )

        # API access policy
        self.audit_policies["api_access"] = AuditPolicy(
            policy_id="api_access",
            policy_name="API Access Policy",
            event_types=[AuditEventType.API_ACCESS],
            severity_filter=AuditSeverity.INFO,
            retention_period=90,
            alert_threshold=50,
        )

        logger.info(f"Initialized {len(self.audit_policies)} default audit policies")

    def register_policy(self, policy: AuditPolicy) -> None:
        """
        Register audit policy

        Args:
            policy: Audit policy
        """
        self.audit_policies[policy.policy_id] = policy
        logger.info(f"Registered audit policy: {policy.policy_id}")

    async def log_event(
        self,
        event_type: AuditEventType,
        action: str,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        resource: Optional[str] = None,
        severity: AuditSeverity = AuditSeverity.INFO,
        details: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Log audit event

        Args:
            event_type: Event type
            action: Action description
            user_id: User ID
            ip_address: IP address
            resource: Resource affected
            severity: Event severity
            details: Additional details

        Returns:
            Event ID
        """
        event_id = f"audit_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f')}"

        event = AuditEvent(
            event_id=event_id,
            event_type=event_type,
            severity=severity,
            user_id=user_id,
            ip_address=ip_address,
            resource=resource,
            action=action,
            details=details or {},
        )

        self.audit_events.append(event)
        self.total_events += 1

        if severity == AuditSeverity.CRITICAL:
            self.critical_events += 1

        # Check policies
        await self._check_policies(event)

        # Store event
        await self._store_event(event)

        logger.debug(f"Logged audit event: {event_id}")

        return event_id

    async def _check_policies(self, event: AuditEvent) -> None:
        """
        Check event against policies

        Args:
            event: Audit event
        """
        for policy in self.audit_policies.values():
            if not policy.enabled:
                continue

            if event.event_type not in policy.event_types:
                continue

            if policy.severity_filter and event.severity != policy.severity_filter:
                continue

            # Check alert threshold
            recent_events = [
                e
                for e in self.audit_events[-policy.alert_threshold:]
                if e.event_type == event.event_type
            ]

            if len(recent_events) >= policy.alert_threshold:
                await self._trigger_alert(policy, event, recent_events)

    async def _trigger_alert(
        self, policy: AuditPolicy, event: AuditEvent, related_events: List[AuditEvent]
    ) -> None:
        """
        Trigger policy alert

        Args:
            policy: Audit policy
            event: Triggering event
            related_events: Related events
        """
        alert_data = {
            "policy_id": policy.policy_id,
            "policy_name": policy.policy_name,
            "triggering_event": {
                "event_id": event.event_id,
                "event_type": event.event_type.value,
                "severity": event.severity.value,
                "timestamp": event.timestamp.isoformat(),
            },
            "related_events_count": len(related_events),
            "threshold": policy.alert_threshold,
        }

        for handler in self.alert_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(alert_data)
                else:
                    handler(alert_data)
            except Exception as e:
                logger.error(f"Alert handler failed: {e}")

        logger.warning(f"Alert triggered for policy: {policy.policy_id}")

    async def _store_event(self, event: AuditEvent) -> None:
        """
        Store audit event to persistent storage

        Args:
            event: Audit event
        """
        event_log_path = (
            self.audit_log_dir / f"audit_{datetime.now(timezone.utc).strftime('%Y%m%d')}.jsonl"
        )

        event_dict = {
            "event_id": event.event_id,
            "event_type": event.event_type.value,
            "severity": event.severity.value,
            "user_id": event.user_id,
            "ip_address": event.ip_address,
            "resource": event.resource,
            "action": event.action,
            "details": event.details,
            "timestamp": event.timestamp.isoformat(),
            "metadata": event.metadata,
        }

        with open(event_log_path, "a") as f:
            f.write(json.dumps(event_dict) + "\n")

        # Prune old events
        if len(self.audit_events) > self.max_events:
            self.audit_events = self.audit_events[-self.max_events:]

    def query_events(
        self,
        event_type: Optional[AuditEventType] = None,
        severity: Optional[AuditSeverity] = None,
        user_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Query audit events

        Args:
            event_type: Filter by event type
            severity: Filter by severity
            user_id: Filter by user ID
            start_time: Filter by start time
            end_time: Filter by end time
            limit: Maximum number of records

        Returns:
            Query results
        """
        events = self.audit_events

        if event_type:
            events = [e for e in events if e.event_type == event_type]
        if severity:
            events = [e for e in events if e.severity == severity]
        if user_id:
            events = [e for e in events if e.user_id == user_id]
        if start_time:
            events = [e for e in events if e.timestamp >= start_time]
        if end_time:
            events = [e for e in events if e.timestamp <= end_time]

        events = events[-limit:]

        return [
            {
                "event_id": e.event_id,
                "event_type": e.event_type.value,
                "severity": e.severity.value,
                "user_id": e.user_id,
                "ip_address": e.ip_address,
                "resource": e.resource,
                "action": e.action,
                "details": e.details,
                "timestamp": e.timestamp.isoformat(),
            }
            for e in events
        ]

    def get_audit_summary(
        self, start_time: Optional[datetime] = None, end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get audit summary

        Args:
            start_time: Start time for summary
            end_time: End time for summary

        Returns:
            Audit summary
        """
        events = self.audit_events

        if start_time:
            events = [e for e in events if e.timestamp >= start_time]
        if end_time:
            events = [e for e in events if e.timestamp <= end_time]

        return {
            "total_events": len(events),
            "by_severity": {
                "critical": len([e for e in events if e.severity == AuditSeverity.CRITICAL]),
                "error": len([e for e in events if e.severity == AuditSeverity.ERROR]),
                "warning": len([e for e in events if e.severity == AuditSeverity.WARNING]),
                "info": len([e for e in events if e.severity == AuditSeverity.INFO]),
            },
            "by_type": {
                et.value: len([e for e in events if e.event_type == et]) for et in AuditEventType
            },
            "unique_users": len(set(e.user_id for e in events if e.user_id)),
            "time_range": {
                "start": start_time.isoformat() if start_time else None,
                "end": end_time.isoformat() if end_time else None,
            },
        }

    def register_alert_handler(self, handler: Callable) -> None:
        """
        Register alert handler

        Args:
            handler: Handler function
        """
        self.alert_handlers.append(handler)
        logger.info("Registered audit alert handler")

    async def generate_audit_report(
        self, start_time: datetime, end_time: datetime, format: str = "json"
    ) -> str:
        """
        Generate audit report

        Args:
            start_time: Report start time
            end_time: Report end time
            format: Report format (json, csv)

        Returns:
            Report file path
        """
        events = [e for e in self.audit_events if start_time <= e.timestamp <= end_time]

        report_id = f"audit_report_{start_time.strftime('%Y%m%d')}_{end_time.strftime('%Y%m%d')}"

        if format == "json":
            report_path = self.audit_log_dir / f"{report_id}.json"

            report_data = {
                "report_id": report_id,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "summary": self.get_audit_summary(start_time, end_time),
                "events": [
                    {
                        "event_id": e.event_id,
                        "event_type": e.event_type.value,
                        "severity": e.severity.value,
                        "user_id": e.user_id,
                        "ip_address": e.ip_address,
                        "resource": e.resource,
                        "action": e.action,
                        "details": e.details,
                        "timestamp": e.timestamp.isoformat(),
                    }
                    for e in events
                ],
            }

            with open(report_path, "w") as f:
                json.dump(report_data, f, indent=2)

        logger.info(f"Generated audit report: {report_path}")

        return str(report_path)

    def get_statistics(self) -> Dict[str, Any]:
        """Get audit statistics"""
        return {
            "total_events": self.total_events,
            "critical_events": self.critical_events,
            "enabled_policies": len([p for p in self.audit_policies.values() if p.enabled]),
            "registered_policies": len(self.audit_policies),
            "event_retention_limit": self.max_events,
        }


def get_security_audit_system(config: Optional[Dict[str, Any]] = None) -> SecurityAuditSystem:
    """
    Factory function to get security audit system instance

    Args:
        config: Optional configuration dictionary

    Returns:
        SecurityAuditSystem: System instance
    """
    return SecurityAuditSystem(config)
