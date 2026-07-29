# -*- coding: utf-8 -*-
"""Reusable Pydantic examples for AIOps Agent API requests and responses.

The module provides 23 example schemas that can be referenced by routers
via ``responses`` / ``openapi_extra`` so that every endpoint exposes
``description``, ``codeSamples`` and error responses.
"""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

# 23 Pydantic example schemas


class _ExampleBase(BaseModel):
    """Base marker carrying json_schema_extra for all example schemas."""

    model_config = {"json_schema_extra": {"example": {}}}


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ErrorResponse(BaseModel):
    error: str = Field(..., description="Short error code")
    message: str = Field(..., description="Human-readable error message")
    detail: dict[str, Any] = Field(default_factory=dict, description="Extra context")


class AlertExample(BaseModel):
    id: str = "ALERT-20250101103045-CPU"
    severity: Literal["critical", "warning", "info"] = "critical"
    message: str = "CPU usage above 90%"
    source: str = "windows-host-01"
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class AIAnalysisRequest(BaseModel):
    query: str = "CPU usage is high, analyze root cause"
    platform: Literal["windows", "linux"] = "windows"
    include_metrics: bool = True


class AIAnalysisResponse(BaseModel):
    query: str = "CPU usage is high, analyze root cause"
    root_cause: str = "High CPU caused by process XYZ"
    confidence: float = 0.92
    recommendations: list[str] = ["Restart process XYZ", "Scale up CPU"]


class FeedbackRequest(BaseModel):
    feedback_type: Literal["positive", "negative"] = "positive"
    analysis_text: str = "CPU root cause analysis"
    query_text: str = "CPU usage is high"
    comment: str = "Accurate"


class FeedbackResponse(BaseModel):
    status: str = "recorded"
    feedback_id: str = "FB-001"


class RepairRequest(BaseModel):
    target: str = "windows-host-01"
    action: str = "restart_service"
    params: dict[str, Any] = {"service_name": "w3svc"}


class RepairResponse(BaseModel):
    repair_id: str = "REP-001"
    status: Literal["pending", "running", "completed", "failed"] = "completed"
    output: str = "Service restarted successfully"


class MetricExample(BaseModel):
    name: str = "cpu_usage_percent"
    value: float = 78.5
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    labels: dict[str, str] = Field(default_factory=dict)


class AnomalyExample(BaseModel):
    metric: str = "cpu_usage_percent"
    score: float = 0.95
    expected: float = 45.0
    actual: float = 95.0


class AutoHealApprovalRequest(BaseModel):
    alert_id: str = "ALERT-001"
    action: str = "restart_service"
    approver: str = "admin"


class AutoHealApprovalResponse(BaseModel):
    approval_id: str = "APPROVAL-001"
    status: Literal["approved", "rejected"] = "approved"


class AuditLogEntry(BaseModel):
    id: str = "AUDIT-001"
    action: str = "repair_executed"
    user: str = "admin"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    details: dict[str, Any] = Field(default_factory=dict)


class UserExample(BaseModel):
    id: int = 1
    username: str = "admin"
    role: Literal["admin", "operator", "viewer"] = "admin"
    active: bool = True


class NotifyRequest(BaseModel):
    channel: Literal["email", "slack", "teams", "webhook"] = "email"
    recipients: list[str] = ["ops@example.com"]
    subject: str = "AIOps alert notification"
    body: str = "CPU usage is high on windows-host-01"


class NotifyResponse(BaseModel):
    notification_id: str = "NOTIFY-001"
    status: Literal["queued", "sent", "failed"] = "queued"


class TopologyNode(BaseModel):
    id: str = "node-1"
    name: str = "windows-host-01"
    type: Literal["host", "service", "container"] = "host"
    edges: list[str] = ["node-2"]


class WorkflowTrigger(BaseModel):
    workflow_id: str = "wf-diagnose-cpu"
    params: dict[str, Any] = Field(default_factory=dict)


class WorkflowStatus(BaseModel):
    execution_id: str = "EXEC-001"
    workflow_id: str = "wf-diagnose-cpu"
    status: Literal["pending", "running", "completed", "failed"] = "running"
    progress: float = 0.5


class BackupRequest(BaseModel):
    target: str = "database"
    destination: str = "s3://aiops-backups/"


class BackupResponse(BaseModel):
    backup_id: str = "BK-001"
    status: Literal["pending", "running", "completed", "failed"] = "completed"
    url: str = "s3://aiops-backups/BK-001"


class CostForecast(BaseModel):
    service: str = "compute"
    forecast_days: int = 30
    predicted_cost: float = 1234.56
    currency: str = "USD"


class CodeSample(BaseModel):
    language: str = "python"
    code: str = "print('hello world')"
    description: str = "Example code snippet"


EXAMPLE_MODELS: list[type[BaseModel]] = [
    HealthResponse,
    ErrorResponse,
    AlertExample,
    AIAnalysisRequest,
    AIAnalysisResponse,
    FeedbackRequest,
    FeedbackResponse,
    RepairRequest,
    RepairResponse,
    MetricExample,
    AnomalyExample,
    AutoHealApprovalRequest,
    AutoHealApprovalResponse,
    AuditLogEntry,
    UserExample,
    NotifyRequest,
    NotifyResponse,
    TopologyNode,
    WorkflowTrigger,
    WorkflowStatus,
    BackupRequest,
    BackupResponse,
    CostForecast,
]
