# -*- coding: utf-8 -*-
"""Data privacy protection and compliance module.

This module provides data anonymization, PII detection,
data retention policies, and privacy compliance features.
"""

import hashlib
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from loguru import logger

# PII patterns for detection
_PII_PATTERNS = {
    "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
    "phone": r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b",
    "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
    "credit_card": r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b",
    "ip_address": r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b",
}

# Data retention policies (in days)
_RETENTION_POLICIES = {
    "alerts": 90,
    "audit_logs": 365,
    "metrics": 180,
    "repair_history": 365,
    "user_sessions": 30,
}


class DataPrivacyConfig:
    """Data privacy configuration."""

    def __init__(
        self,
        anonymization_enabled: bool = True,
        pii_detection_enabled: bool = True,
        data_retention_enabled: bool = True,
        consent_required: bool = False,
        gdpr_compliance: bool = False,
    ):
        self.anonymization_enabled = anonymization_enabled
        self.pii_detection_enabled = pii_detection_enabled
        self.data_retention_enabled = data_retention_enabled
        self.consent_required = consent_required
        self.gdpr_compliance = gdpr_compliance


_privacy_config = DataPrivacyConfig()


def configure_privacy(config: DataPrivacyConfig) -> None:
    """Configure data privacy settings.

    Args:
        config: Privacy configuration object
    """
    global _privacy_config
    _privacy_config = config
    logger.info("Data privacy configuration updated")


def get_privacy_config() -> DataPrivacyConfig:
    """Get current privacy configuration.

    Returns:
        Current privacy configuration
    """
    return _privacy_config


def detect_pii(text: str) -> Dict[str, List[str]]:
    """Detect personally identifiable information in text.

    Args:
        text: Text to analyze

    Returns:
        Dictionary of PII type to list of matches
    """
    if not _privacy_config.pii_detection_enabled:
        return {}

    detected = {}

    for pii_type, pattern in _PII_PATTERNS.items():
        matches = re.findall(pattern, text)
        if matches:
            detected[pii_type] = matches

    return detected


def contains_pii(text: str) -> bool:
    """Check if text contains PII.

    Args:
        text: Text to check

    Returns:
        True if PII detected
    """
    detected = detect_pii(text)
    return len(detected) > 0


def anonymize_email(email: str) -> str:
    """Anonymize email address.

    Args:
        email: Email address to anonymize

    Returns:
        Anonymized email
    """
    if "@" not in email:
        return email

    local, domain = email.split("@", 1)
    if len(local) > 2:
        local = local[0] + "*" * (len(local) - 2) + local[-1]

    return f"{local}@{domain}"


def anonymize_phone(phone: str) -> str:
    """Anonymize phone number.

    Args:
        phone: Phone number to anonymize

    Returns:
        Anonymized phone number
    """
    digits = re.sub(r"\D", "", phone)
    if len(digits) >= 4:
        return digits[:2] + "*" * (len(digits) - 4) + digits[-2:]
    return "*" * len(phone)


def anonymize_ssn(ssn: str) -> str:
    """Anonymize Social Security Number.

    Args:
        ssn: SSN to anonymize

    Returns:
        Anonymized SSN
    """
    digits = re.sub(r"\D", "", ssn)
    if len(digits) == 9:
        return f"***-**-{digits[-4:]}"
    return "*" * len(ssn)


def anonymize_credit_card(card: str) -> str:
    """Anonymize credit card number.

    Args:
        card: Credit card number to anonymize

    Returns:
        Anonymized credit card number
    """
    digits = re.sub(r"\D", "", card)
    if len(digits) >= 4:
        return "*" * (len(digits) - 4) + digits[-4:]
    return "*" * len(card)


def anonymize_ip(ip: str) -> str:
    """Anonymize IP address.

    Args:
        ip: IP address to anonymize

    Returns:
        Anonymized IP address
    """
    parts = ip.split(".")
    if len(parts) == 4:
        return f"{parts[0]}.{parts[1]}.*.*"
    return ip


def anonymize_text(text: str) -> str:
    """Anonymize PII in text.

    Args:
        text: Text to anonymize

    Returns:
        Anonymized text
    """
    if not _privacy_config.anonymization_enabled:
        return text

    detected = detect_pii(text)

    for pii_type, matches in detected.items():
        for match in matches:
            if pii_type == "email":
                text = text.replace(match, anonymize_email(match))
            elif pii_type == "phone":
                text = text.replace(match, anonymize_phone(match))
            elif pii_type == "ssn":
                text = text.replace(match, anonymize_ssn(match))
            elif pii_type == "credit_card":
                text = text.replace(match, anonymize_credit_card(match))
            elif pii_type == "ip_address":
                text = text.replace(match, anonymize_ip(match))

    return text


def hash_pii(data: str) -> str:
    """Hash PII data for privacy protection.

    Args:
        data: PII data to hash

    Returns:
        Hashed data
    """
    return hashlib.sha256(data.encode()).hexdigest()


def anonymize_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """Anonymize PII in dictionary values.

    Args:
        data: Dictionary to anonymize

    Returns:
        Anonymized dictionary
    """
    if not _privacy_config.anonymization_enabled:
        return data

    anonymized: Dict[str, Any] = {}

    for key, value in data.items():
        if isinstance(value, str):
            anonymized[key] = anonymize_text(value)
        elif isinstance(value, dict):
            anonymized[key] = anonymize_dict(value)
        elif isinstance(value, list):
            anonymized[key] = [
                anonymize_text(item) if isinstance(item, str) else item for item in value
            ]
        else:
            anonymized[key] = value

    return anonymized


class DataRetentionPolicy:
    """Data retention policy manager."""

    def __init__(self, data_type: str, retention_days: int):
        self.data_type = data_type
        self.retention_days = retention_days

    def should_retain(self, created_at: datetime) -> bool:
        """Check if data should be retained based on age.

        Args:
            created_at: Data creation timestamp

        Returns:
            True if data should be retained
        """
        if not _privacy_config.data_retention_enabled:
            return True

        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)

        age = datetime.now(timezone.utc) - created_at
        return age.days < self.retention_days

    def get_expiry_date(self, created_at: datetime) -> datetime:
        """Get expiry date for data.

        Args:
            created_at: Data creation timestamp

        Returns:
            Expiry date
        """
        return created_at + timedelta(days=self.retention_days)


def get_retention_policy(data_type: str) -> Optional[DataRetentionPolicy]:
    """Get retention policy for data type.

    Args:
        data_type: Type of data

    Returns:
        Retention policy or None
    """
    if data_type in _RETENTION_POLICIES:
        return DataRetentionPolicy(data_type, _RETENTION_POLICIES[data_type])
    return None


def set_retention_policy(data_type: str, retention_days: int) -> None:
    """Set retention policy for data type.

    Args:
        data_type: Type of data
        retention_days: Number of days to retain
    """
    _RETENTION_POLICIES[data_type] = retention_days
    logger.info(f"Set retention policy for {data_type}: {retention_days} days")


class ConsentRecord:
    """User consent record."""

    def __init__(
        self,
        user_id: str,
        consent_type: str,
        granted: bool,
        timestamp: Optional[datetime] = None,
    ):
        self.user_id = user_id
        self.consent_type = consent_type
        self.granted = granted
        self.timestamp = timestamp or datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "user_id": self.user_id,
            "consent_type": self.consent_type,
            "granted": self.granted,
            "timestamp": self.timestamp.isoformat(),
        }


# Consent storage
_consent_records: Dict[str, List[ConsentRecord]] = {}


def record_consent(user_id: str, consent_type: str, granted: bool) -> None:
    """Record user consent.

    Args:
        user_id: User identifier
        consent_type: Type of consent
        granted: Whether consent was granted
    """
    if user_id not in _consent_records:
        _consent_records[user_id] = []

    record = ConsentRecord(user_id, consent_type, granted)
    _consent_records[user_id].append(record)

    logger.info(f"Recorded consent for {user_id}: {consent_type} = {granted}")


def has_consent(user_id: str, consent_type: str) -> bool:
    """Check if user has granted consent.

    Args:
        user_id: User identifier
        consent_type: Type of consent

    Returns:
        True if consent granted
    """
    if not _privacy_config.consent_required:
        return True

    if user_id not in _consent_records:
        return False

    user_consents = _consent_records[user_id]

    # Check latest consent record for this type
    for record in reversed(user_consents):
        if record.consent_type == consent_type:
            return record.granted

    return False


def get_user_consents(user_id: str) -> List[Dict[str, Any]]:
    """Get all consent records for user.

    Args:
        user_id: User identifier

    Returns:
        List of consent records
    """
    if user_id not in _consent_records:
        return []

    return [record.to_dict() for record in _consent_records[user_id]]


class PrivacyAuditLog:
    """Privacy audit log entry."""

    def __init__(
        self,
        event_type: str,
        user_id: Optional[str],
        data_type: str,
        action: str,
        timestamp: Optional[datetime] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.event_type = event_type
        self.user_id = user_id
        self.data_type = data_type
        self.action = action
        self.timestamp = timestamp or datetime.now(timezone.utc)
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "event_type": self.event_type,
            "user_id": self.user_id,
            "data_type": self.data_type,
            "action": self.action,
            "timestamp": self.timestamp.isoformat(),
            "details": self.details,
        }


# Audit log storage
_privacy_audit_logs: List[PrivacyAuditLog] = []


def log_privacy_event(
    event_type: str,
    user_id: Optional[str],
    data_type: str,
    action: str,
    details: Optional[Dict[str, Any]] = None,
) -> None:
    """Log privacy-related event for compliance.

    Args:
        event_type: Type of privacy event
        user_id: User identifier
        data_type: Type of data involved
        action: Action performed
        details: Additional details
    """
    log_entry = PrivacyAuditLog(
        event_type=event_type,
        user_id=user_id,
        data_type=data_type,
        action=action,
        details=details,
    )

    _privacy_audit_logs.append(log_entry)
    logger.info(f"Privacy event logged: {event_type} - {action}")


def get_privacy_audit_logs(
    user_id: Optional[str] = None,
    event_type: Optional[str] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """Get privacy audit logs with optional filtering.

    Args:
        user_id: Filter by user ID
        event_type: Filter by event type
        limit: Maximum number of results

    Returns:
        List of audit log entries
    """
    logs = _privacy_audit_logs

    if user_id:
        logs = [log for log in logs if log.user_id == user_id]

    if event_type:
        logs = [log for log in logs if log.event_type == event_type]

    logs = logs[-limit:]

    return [log.to_dict() for log in logs]


def get_privacy_stats() -> Dict[str, Any]:
    """Get privacy statistics.

    Returns:
        Statistics dictionary
    """
    return {
        "config": {
            "anonymization_enabled": _privacy_config.anonymization_enabled,
            "pii_detection_enabled": _privacy_config.pii_detection_enabled,
            "data_retention_enabled": _privacy_config.data_retention_enabled,
            "consent_required": _privacy_config.consent_required,
            "gdpr_compliance": _privacy_config.gdpr_compliance,
        },
        "retention_policies": _RETENTION_POLICIES,
        "consent_records": len(_consent_records),
        "audit_log_entries": len(_privacy_audit_logs),
    }


__all__ = [
    "DataPrivacyConfig",
    "configure_privacy",
    "get_privacy_config",
    "detect_pii",
    "contains_pii",
    "anonymize_email",
    "anonymize_phone",
    "anonymize_ssn",
    "anonymize_credit_card",
    "anonymize_ip",
    "anonymize_text",
    "hash_pii",
    "anonymize_dict",
    "DataRetentionPolicy",
    "get_retention_policy",
    "set_retention_policy",
    "ConsentRecord",
    "record_consent",
    "has_consent",
    "get_user_consents",
    "PrivacyAuditLog",
    "log_privacy_event",
    "get_privacy_audit_logs",
    "get_privacy_stats",
]
