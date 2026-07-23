# -*- coding: utf-8 -*-
"""Pydantic schemas for the repair microservice."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class PlatformType(str, Enum):
    """Supported target platforms."""

    WINDOWS = "windows"
    LINUX = "linux"
    MACOS = "macos"
    DOCKER = "docker"
    KUBERNETES = "kubernetes"


class RiskLevel(str, Enum):
    """Risk levels for repair operations."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RepairStatus(str, Enum):
    """Repair lifecycle states."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTING = "executing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    VERIFYING = "verifying"
    VERIFIED = "verified"
    VERIFY_FAILED = "verify_failed"
    ROLLBACK_PENDING = "rollback_pending"
    ROLLBACKING = "rollbacking"
    ROLLBACKED = "rollbacked"
    ROLLBACK_FAILED = "rollback_failed"
    COMPLETED = "completed"
    TIMEOUT = "timeout"


class RepairStrategy(BaseModel):
    """Repair strategy definition."""

    name: str
    conditions: Dict[str, Any] = Field(default_factory=dict)
    params: Dict[str, Any] = Field(default_factory=dict)
    script_key: str
    platform: PlatformType = PlatformType.LINUX
    risk_level: RiskLevel = RiskLevel.LOW
    priority: int = 0
    enabled: bool = True
    max_retries: int = 0
    rollback_script_key: Optional[str] = None
    timeout_seconds: int = 120


class RepairScript(BaseModel):
    """Pre-defined repair script model."""

    script_key: str
    name: str
    description: str = ""
    platform: PlatformType = PlatformType.LINUX
    risk_level: RiskLevel = RiskLevel.LOW
    command_template: str = ""
    params: List[str] = Field(default_factory=list)
    requires_approval: bool = False
    estimated_duration_seconds: int = 60
    rollback_script_key: Optional[str] = None


class RepairRequest(BaseModel):
    """Incoming repair request."""

    alert_id: str = Field(..., min_length=1, max_length=128)
    host: str = Field(..., min_length=1, max_length=128)
    platform: PlatformType
    metric: str = ""
    metric_value: Optional[float] = None
    description: str = ""
    params: Dict[str, Any] = Field(default_factory=dict)
    requested_by: str = "system"
    auto_approve: bool = False


class RepairStep(BaseModel):
    """Single runbook step."""

    name: str
    command: str
    timeout_seconds: int = 60
    rollback_command: Optional[str] = None
    verify_command: Optional[str] = None


class RepairRunbook(BaseModel):
    """Runbook definition."""

    runbook_id: str
    name: str
    description: str = ""
    platform: PlatformType = PlatformType.LINUX
    risk_level: RiskLevel = RiskLevel.LOW
    steps: List[RepairStep] = Field(default_factory=list)
    params: Dict[str, Any] = Field(default_factory=dict)


class RepairTask(BaseModel):
    """Repair task aggregate."""

    task_id: str
    alert_id: str
    host: str
    platform: PlatformType
    status: RepairStatus = RepairStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    runbook: Optional[RepairRunbook] = None
    strategy: Optional[RepairStrategy] = None
    result: Dict[str, Any] = Field(default_factory=dict)
    audit_log: List[Dict[str, Any]] = Field(default_factory=list)
    rollback_result: Optional[Dict[str, Any]] = None


class RepairExecutionResult(BaseModel):
    """Result of a repair execution."""

    task_id: str
    success: bool
    output: str = ""
    error: str = ""
    duration_seconds: float = 0.0
    return_code: int = 0
    executed_steps: int = 0


class VerificationResult(BaseModel):
    """Repair verification result."""

    task_id: str
    verified: Optional[bool] = None
    strategy: str = ""
    confidence: float = 0.0
    evidence: Dict[str, Any] = Field(default_factory=dict)
    duration_seconds: float = 0.0
    error_msg: str = ""
    recommendation: str = ""


class ServiceHealth(BaseModel):
    """Service health status."""

    status: str = "ok"
    service: str = ""
    uptime_seconds: int = 0
    repair_count: int = 0


class AuditEvent(BaseModel):
    """Audit event for repair operations."""

    event_id: str
    task_id: str
    event_type: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    actor: str = ""
    payload: Dict[str, Any] = Field(default_factory=dict)


class SagaStep(BaseModel):
    """Saga distributed transaction step."""

    step_id: str
    service: str
    action: str
    compensation: str
    status: str = "pending"
    result: Dict[str, Any] = Field(default_factory=dict)


class SagaTransaction(BaseModel):
    """Saga transaction."""

    saga_id: str
    task_id: str
    steps: List[SagaStep] = Field(default_factory=list)
    status: str = "pending"
    created_at: datetime = Field(default_factory=datetime.utcnow)
