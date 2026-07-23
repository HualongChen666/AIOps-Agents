# -*- coding: utf-8 -*-
"""Pydantic schemas for the workflow microservice."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class WorkflowStatus(str, Enum):
    """Workflow lifecycle states."""

    PENDING = "pending"
    APPROVED = "approved"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    PAUSED = "paused"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    RETRYING = "retrying"
    TIMEOUT = "timeout"
    COMPLETED = "completed"


class TaskPriority(str, Enum):
    """Task priority levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class WorkflowNode(BaseModel):
    """A node in a workflow DAG."""

    node_id: str = Field(..., min_length=1, max_length=128)
    name: str = Field(..., min_length=1, max_length=128)
    node_type: str = "task"
    command: str = ""
    dependencies: List[str] = Field(default_factory=list)
    retries: int = 0
    timeout_seconds: int = 60
    params: Dict[str, Any] = Field(default_factory=dict)


class WorkflowDefinition(BaseModel):
    """Workflow definition (DAG-like)."""

    workflow_id: str = Field(..., min_length=1, max_length=128)
    name: str = Field(..., min_length=1, max_length=128)
    description: str = ""
    nodes: List[WorkflowNode] = Field(default_factory=list)
    schedule: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class WorkflowRequest(BaseModel):
    """Request to execute a workflow."""

    workflow_id: str = Field(..., min_length=1, max_length=128)
    params: Dict[str, Any] = Field(default_factory=dict)
    requested_by: str = "system"
    priority: TaskPriority = TaskPriority.MEDIUM


class WorkflowTask(BaseModel):
    """Workflow execution task aggregate."""

    task_id: str = Field(..., min_length=1, max_length=128)
    workflow_id: str
    status: WorkflowStatus = WorkflowStatus.PENDING
    current_node: Optional[str] = None
    completed_nodes: List[str] = Field(default_factory=list)
    failed_nodes: List[str] = Field(default_factory=list)
    params: Dict[str, Any] = Field(default_factory=dict)
    result: Dict[str, Any] = Field(default_factory=dict)
    retry_count: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class WorkflowExecutionResult(BaseModel):
    """Result of workflow execution."""

    task_id: str
    workflow_id: str
    success: bool
    duration_seconds: float
    node_results: Dict[str, Any] = Field(default_factory=dict)
    error: str = ""


class WorkflowVersion(BaseModel):
    """Workflow version snapshot."""

    version: str
    workflow_id: str
    commit_hash: str
    message: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class WorkflowTemplate(BaseModel):
    """Jinja2 workflow template."""

    template_id: str = Field(..., min_length=1, max_length=128)
    name: str
    description: str = ""
    source: str = ""
    default_params: Dict[str, Any] = Field(default_factory=dict)


class RetryPolicy(BaseModel):
    """Retry policy with exponential backoff."""

    name: str
    max_retries: int = Field(default=3, ge=0)
    base_delay_seconds: float = Field(default=1.0, ge=0)
    max_delay_seconds: float = Field(default=60.0, ge=0)
    exponential_base: float = Field(default=2.0, ge=1.0)
    retryable_errors: List[str] = Field(default_factory=list)


class ScheduledTask(BaseModel):
    """Scheduled workflow task."""

    schedule_id: str
    workflow_id: str
    cron: str
    next_run: Optional[datetime] = None
    enabled: bool = True
    params: Dict[str, Any] = Field(default_factory=dict)


class WorkflowMetric(BaseModel):
    """Workflow execution metric."""

    metric_name: str
    value: float
    labels: Dict[str, str] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ServiceHealth(BaseModel):
    """Service health response."""

    status: str
    service: str
    uptime_seconds: int = 0
    workflow_count: int = 0


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
