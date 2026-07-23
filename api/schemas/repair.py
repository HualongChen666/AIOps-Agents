# -*- coding: utf-8 -*-
"""Unified Repair Request Models

Provides reusable Pydantic models for repair requests across different platforms
(Linux, Windows, Docker, K8s, Cloud) to eliminate duplicate code patterns.
"""

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator

from core.api_helpers import hostname_field_validator


class BaseRepairRequest(BaseModel):
    """Base repair request model with common fields."""

    host: str = Field(..., min_length=1, max_length=128, description="Target host address")
    script_name: str = Field(..., min_length=1, max_length=64, description="Repair script name")
    args: dict[str, Any] = Field(default_factory=dict, description="Repair script parameters")

    @field_validator("host")
    @classmethod
    def _validate_host(cls, v: str) -> str:
        """Hostname validation."""
        return hostname_field_validator(v)

    model_config = {
        "extra": "ignore",
        "json_schema_extra": {"example": {"host": "example", "script_name": "example", "args": {}}},
    }


class LinuxRepairRequest(BaseModel):
    """Linux repair request model."""

    host_name: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="Target Linux host name or IP",
        examples=["linux-server-01"],
    )
    script_key: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Repair script key name",
        examples=["clear_tmp"],
    )
    params: dict[str, str] = Field(default_factory=dict, description="Script parameters")

    @field_validator("host_name")
    @classmethod
    def _validate_host_name(cls, v: str) -> str:
        return hostname_field_validator(v)

    model_config = {
        "extra": "ignore",
        "json_schema_extra": {
            "example": {"host_name": "example", "script_key": "example", "params": {}}
        },
    }


class WindowsRepairRequest(BaseModel):
    """Windows repair request model."""

    host_name: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="Target Windows host name or IP",
        examples=["win-server-01"],
    )
    script_key: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Repair script key name",
        examples=["restart_service"],
    )
    params: dict[str, str] = Field(
        default_factory=dict,
        description="Script placeholder parameters (e.g., {'service_name': 'Spooler'})",
    )

    @field_validator("host_name")
    @classmethod
    def _validate_host_name(cls, v: str) -> str:
        return hostname_field_validator(v)

    model_config = {
        "extra": "ignore",
        "json_schema_extra": {
            "example": {"host_name": "example", "script_key": "example", "params": {}}
        },
    }


class DockerRepairRequest(BaseModel):
    """Docker repair request model."""

    host: str = Field(..., min_length=1, max_length=128, description="Docker host address")
    script_name: str = Field(..., min_length=1, max_length=64, description="Repair script name")
    args: dict[str, Any] = Field(default_factory=dict, description="Repair script parameters")

    @field_validator("host")
    @classmethod
    def _validate_host(cls, v: str) -> str:
        return hostname_field_validator(v)

    model_config = {
        "extra": "ignore",
        "json_schema_extra": {"example": {"host": "example", "script_name": "example", "args": {}}},
    }


class K8sRepairRequest(BaseModel):
    """Kubernetes repair request model."""

    host: str = Field(..., min_length=1, max_length=128, description="Kubernetes host address")
    script_name: str = Field(..., min_length=1, max_length=64, description="Repair script name")
    args: dict[str, Any] = Field(default_factory=dict, description="Repair script parameters")

    @field_validator("host")
    @classmethod
    def _validate_host(cls, v: str) -> str:
        return hostname_field_validator(v)

    model_config = {
        "extra": "ignore",
        "json_schema_extra": {"example": {"host": "example", "script_name": "example", "args": {}}},
    }


class CloudRepairRequest(BaseModel):
    """Cloud repair request model."""

    host: str = Field(..., min_length=1, max_length=128, description="Cloud host address")
    script_name: str = Field(..., min_length=1, max_length=64, description="Repair script name")
    args: dict[str, Any] = Field(default_factory=dict, description="Repair script parameters")

    @field_validator("host")
    @classmethod
    def _validate_host(cls, v: str) -> str:
        return hostname_field_validator(v)

    model_config = {
        "extra": "ignore",
        "json_schema_extra": {"example": {"host": "example", "script_name": "example", "args": {}}},
    }


PlatformType = Literal["windows", "linux", "docker", "kubernetes"]


class UnifiedRepairRequest(BaseModel):
    """Unified repair request model for all platforms."""

    platform: PlatformType = Field(
        ..., description="Target platform: windows, linux, docker, kubernetes"
    )
    script_key: str = Field(..., min_length=1, max_length=64, description="Repair script key name")
    host_name: Optional[str] = Field(
        None,
        min_length=1,
        max_length=128,
        description="Target host name or IP (Linux/Docker/K8s needed)",
    )
    params: dict[str, str] = Field(default_factory=dict, description="Repair script parameters")

    model_config = {
        "extra": "ignore",
        "json_schema_extra": {
            "example": {
                "platform": None,
                "script_key": "example",
                "host_name": "example",
                "params": {},
            },
        },
    }
