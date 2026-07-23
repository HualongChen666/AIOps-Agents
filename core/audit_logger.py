# -*- coding: utf-8 -*-
"""Audit logging for security and compliance.

This module provides centralized audit logging for security events,
user actions, and system operations required for enterprise compliance.
"""

import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from loguru import logger

# Audit event types
AUDIT_EVENT_TYPES = {
    "LOGIN": "user_login",
    "LOGOUT": "user_logout",
    "TOKEN_REFRESH": "token_refresh",  # nosec B105
    "PERMISSION_GRANTED": "permission_granted",
    "PERMISSION_REVOKED": "permission_revoked",
    "REPAIR_EXECUTED": "repair_executed",
    "ALERT_GENERATED": "alert_generated",
    "CONFIG_CHANGED": "config_changed",
    "DATA_ACCESS": "data_access",
}


def log_audit_event(
    event_type: str,
    user: str,
    resource: Optional[str] = None,
    action: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    status: str = "success",
) -> None:
    """Log an audit event for security and compliance.

    Args:
        event_type: Type of audit event (e.g., "LOGIN", "REPAIR_EXECUTED")
        user: Username or user identifier
        resource: Resource being accessed or modified
        action: Action performed on the resource
        details: Additional details about the event
        ip_address: IP address of the user
        status: Status of the operation (success, failure, denied)
    """
    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": event_type,
        "user": user,
        "resource": resource,
        "action": action,
        "details": details or {},
        "ip_address": ip_address,
        "status": status,
    }

    # Log to file for audit trail
    logger.info(f"AUDIT: {json.dumps(event)}")

    # In production, this would also write to a dedicated audit database
    # or send to a centralized logging system


def log_login_event(user: str, ip_address: Optional[str] = None, status: str = "success") -> None:
    """Log a user login event."""
    log_audit_event(
        event_type="LOGIN",
        user=user,
        ip_address=ip_address,
        status=status,
    )


def log_logout_event(user: str, ip_address: Optional[str] = None) -> None:
    """Log a user logout event."""
    log_audit_event(
        event_type="LOGOUT",
        user=user,
        ip_address=ip_address,
        status="success",
    )


def log_token_refresh(user: str, ip_address: Optional[str] = None) -> None:
    """Log a token refresh event."""
    log_audit_event(
        event_type="TOKEN_REFRESH",
        user=user,
        ip_address=ip_address,
        status="success",
    )


def log_repair_executed(
    user: str,
    script_key: str,
    target_host: str,
    status: str = "success",
    details: Optional[Dict[str, Any]] = None,
) -> None:
    """Log a repair execution event."""
    log_audit_event(
        event_type="REPAIR_EXECUTED",
        user=user,
        resource=target_host,
        action=script_key,
        details=details or {},
        status=status,
    )


def log_permission_change(
    user: str,
    target_user: str,
    permission: str,
    action: str,
    status: str = "success",
) -> None:
    """Log a permission change event."""
    log_audit_event(
        event_type=f"PERMISSION_{action.upper()}",
        user=user,
        resource=target_user,
        action=permission,
        status=status,
    )


def log_alert_generated(
    alert_type: str,
    severity: str,
    details: Optional[Dict[str, Any]] = None,
) -> None:
    """Log an alert generation event."""
    log_audit_event(
        event_type="ALERT_GENERATED",
        user="system",
        resource=alert_type,
        action="generate",
        details=details or {"severity": severity},
        status="success",
    )


def log_data_access(
    user: str,
    resource: str,
    action: str,
    ip_address: Optional[str] = None,
) -> None:
    """Log a data access event."""
    log_audit_event(
        event_type="DATA_ACCESS",
        user=user,
        resource=resource,
        action=action,
        ip_address=ip_address,
        status="success",
    )


__all__ = [
    "log_audit_event",
    "log_login_event",
    "log_logout_event",
    "log_token_refresh",
    "log_repair_executed",
    "log_permission_change",
    "log_alert_generated",
    "log_data_access",
    "AUDIT_EVENT_TYPES",
]
