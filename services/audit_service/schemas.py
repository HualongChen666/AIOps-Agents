# -*- coding: utf-8 -*-
"""Pydantic schemas for the audit microservice."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List

from pydantic import BaseModel, Field


class AuditEventStatus(str, Enum):
    """Audit event lifecycle states."""

    PENDING = "pending"
    RECORDED = "recorded"
    ROUTED = "routed"
    ANALYZED = "analyzed"
    ARCHIVED = "archived"


class AuditEventSeverity(str, Enum):
    """Severity levels for audit events."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AuditEvent(BaseModel):
    """Audit event aggregate."""

    event_id: str = Field(..., min_length=1, max_length=128)
    action: str
    resource: str
    user_id: str
    tenant_id: str = "default"
    severity: AuditEventSeverity = AuditEventSeverity.LOW
    status: AuditEventStatus = AuditEventStatus.PENDING
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class OperationLog(BaseModel):
    """Operation log entry."""

    log_id: str
    event_id: str
    action: str
    actor: str
    before_state: Dict[str, Any] = Field(default_factory=dict)
    after_state: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class AuditReport(BaseModel):
    """Generated compliance report."""

    report_id: str
    report_type: str
    tenant_id: str = "default"
    start_time: datetime
    end_time: datetime
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    content: str
    rendered_template: str = ""


class AlertRule(BaseModel):
    """Audit alert rule."""

    rule_id: str
    name: str
    condition: str
    severity: AuditEventSeverity = AuditEventSeverity.MEDIUM
    enabled: bool = True
    action: str = "log"


class EncryptedBlob(BaseModel):
    """Encrypted audit data blob."""

    blob_id: str
    ciphertext: str
    nonce: str
    tag: str
    algorithm: str = "AES-256-GCM"
    created_at: datetime = Field(default_factory=datetime.utcnow)


class RetentionPolicy(BaseModel):
    """Audit data retention policy."""

    policy_id: str
    tenant_id: str = "default"
    ttl_days: int = Field(default=365, ge=1)
    archive_after_days: int = Field(default=90, ge=1)
    auto_archive: bool = True


class SagaStep(BaseModel):
    """Single saga step."""

    step_id: str
    service: str
    action: str
    compensation: str
    status: str = "pending"
    result: Dict[str, Any] = Field(default_factory=dict)


class SagaTransaction(BaseModel):
    """Saga transaction aggregate."""

    saga_id: str
    task_id: str
    steps: List[SagaStep] = Field(default_factory=list)
    status: str = "pending"
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ServiceHealth(BaseModel):
    """Service health response."""

    status: str
    service: str
    uptime_seconds: int = 0
    audit_count: int = 0
