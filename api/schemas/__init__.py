# -*- coding: utf-8 -*-
# api/schemas/__init__.py
"""API Schemas Package

This package contains unified Pydantic models for API requests/responses
to eliminate duplicate code patterns across routers.
"""

from .examples import (
    EXAMPLE_MODELS,
    AIAnalysisRequest,
    AIAnalysisResponse,
    AlertExample,
    AnomalyExample,
    AuditLogEntry,
    AutoHealApprovalRequest,
    AutoHealApprovalResponse,
    BackupRequest,
    BackupResponse,
    CodeSample,
    CostForecast,
    ErrorResponse,
    FeedbackRequest,
    FeedbackResponse,
    HealthResponse,
    MetricExample,
    NotifyRequest,
    NotifyResponse,
    RepairRequest,
    RepairResponse,
    TopologyNode,
    UserExample,
    WorkflowStatus,
    WorkflowTrigger,
)
from .repair import (
    CloudRepairRequest,
    DockerRepairRequest,
    K8sRepairRequest,
    LinuxRepairRequest,
    UnifiedRepairRequest,
    WindowsRepairRequest,
)
from .responses import ErrorDetail, StandardResponse

__all__ = [
    "K8sRepairRequest",
    "CloudRepairRequest",
    "UnifiedRepairRequest",
    "LinuxRepairRequest",
    "WindowsRepairRequest",
    "DockerRepairRequest",
    # response / example models
    "StandardResponse",
    "ErrorDetail",
    "ErrorResponse",
    "CodeSample",
    "HealthResponse",
    "AlertExample",
    "AIAnalysisRequest",
    "AIAnalysisResponse",
    "FeedbackRequest",
    "FeedbackResponse",
    "RepairRequest",
    "RepairResponse",
    "MetricExample",
    "AnomalyExample",
    "AutoHealApprovalRequest",
    "AutoHealApprovalResponse",
    "AuditLogEntry",
    "UserExample",
    "NotifyRequest",
    "NotifyResponse",
    "TopologyNode",
    "WorkflowTrigger",
    "WorkflowStatus",
    "BackupRequest",
    "BackupResponse",
    "CostForecast",
    "EXAMPLE_MODELS",
]
