# -*- coding: utf-8 -*-
"""Pydantic schemas for the configuration microservice."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List

from pydantic import BaseModel, Field


class ConfigNamespace(str, Enum):
    """Configuration namespaces."""

    DEFAULT = "default"
    DEV = "dev"
    STAGING = "staging"
    PROD = "prod"


class ConfigValue(BaseModel):
    """Configuration value aggregate."""

    config_id: str = Field(..., min_length=1, max_length=128)
    key: str
    value: str
    namespace: ConfigNamespace = ConfigNamespace.DEFAULT
    version: str = "1.0.0"
    encrypted: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    updated_by: str = "system"


class ConfigSnapshot(BaseModel):
    """Configuration snapshot for rollback."""

    snapshot_id: str
    namespace: str
    version: str
    configs: Dict[str, str] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ConfigVersion(BaseModel):
    """Git-like configuration version."""

    version_id: str
    namespace: str
    commit_hash: str
    message: str
    author: str = "system"
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ConfigUpdateEvent(BaseModel):
    """Configuration update event for WebSocket hot updates."""

    event_id: str
    config_id: str
    namespace: str
    old_value: str = ""
    new_value: str = ""
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class AuditLogEntry(BaseModel):
    """Configuration audit log entry."""

    log_id: str
    config_id: str
    action: str
    details: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ServiceHealth(BaseModel):
    """Service health response."""

    status: str
    service: str
    uptime_seconds: int = 0
    config_count: int = 0


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
