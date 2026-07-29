# -*- coding: utf-8 -*-
"""Pydantic schemas for the user microservice."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class UserStatus(str, Enum):
    """User lifecycle states."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    DELETED = "deleted"


class UserRole(str, Enum):
    """Predefined user roles."""

    ADMIN = "admin"
    OPERATOR = "operator"
    VIEWER = "viewer"


class User(BaseModel):
    """User aggregate."""

    user_id: str = Field(..., min_length=1, max_length=128)
    username: str = Field(..., min_length=1, max_length=128)
    email: str
    full_name: str = ""
    role: UserRole = UserRole.VIEWER
    status: UserStatus = UserStatus.ACTIVE
    organization_id: Optional[str] = None
    tenant_id: str = "default"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class UserCreate(BaseModel):
    """User creation request."""

    username: str
    email: str
    full_name: str = ""
    role: UserRole = UserRole.VIEWER
    organization_id: Optional[str] = None
    tenant_id: str = "default"
    password: str = ""


class UserUpdate(BaseModel):
    """User update request."""

    email: Optional[str] = None
    full_name: Optional[str] = None
    role: Optional[UserRole] = None
    status: Optional[UserStatus] = None
    organization_id: Optional[str] = None


class Permission(BaseModel):
    """Permission definition."""

    permission_id: str
    resource: str
    action: str
    description: str = ""


class Role(BaseModel):
    """Role with permissions."""

    role_id: str
    name: str
    permissions: List[str] = Field(default_factory=list)
    tenant_id: str = "default"


class Organization(BaseModel):
    """Organization node in a tree."""

    org_id: str
    name: str
    parent_id: Optional[str] = None
    tenant_id: str = "default"
    children: List[str] = Field(default_factory=list)


class Session(BaseModel):
    """User session."""

    session_id: str
    user_id: str
    token: str
    expires_at: datetime
    tenant_id: str = "default"
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AuthToken(BaseModel):
    """OAuth2/JWT token response."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int = 3600
    refresh_token: str = ""


class AuditLogEntry(BaseModel):
    """User audit log entry."""

    log_id: str
    user_id: str
    action: str
    details: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ServiceHealth(BaseModel):
    """Service health response."""

    status: str
    service: str
    uptime_seconds: int = 0
    user_count: int = 0


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
