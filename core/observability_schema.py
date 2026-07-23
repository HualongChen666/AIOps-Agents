# -*- coding: utf-8 -*-
"""Observability data models (metrics, logs, traces).

These models provide a **canonical JSON schema** for log records, metric metadata
and trace context that all services should emit.  The definitions are used by
runtime helpers (e.g., `core.trace_monitor`, `core.log_router`) and by CI
validation scripts.
"""

from __future__ import annotations

import datetime as _dt
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, validator


class CommonLabels(BaseModel):
    service: str = Field(..., description="Logical service name, e.g. 'aiops-agent'")
    env: str = Field(..., description="Deployment environment: dev|staging|prod")
    region: str = Field(..., description="Cloud region or data‑center identifier")
    tenant: Optional[str] = Field(None, description="Tenant ID for multi‑tenant setups")
    instance: str = Field(..., description="Hostname / pod name / container ID")

    @validator("env")
    def _env_allowed(cls, v: str) -> str:
        allowed = {"dev", "staging", "prod"}
        if v not in allowed:
            raise ValueError(f"env must be one of {allowed}, got {v}")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "service": "example",
                "env": "example",
                "region": "example",
                "tenant": "example",
                "instance": "example",
            }
        }
    }


class LogRecord(BaseModel):
    timestamp: _dt.datetime = Field(
        default_factory=_dt.datetime.utcnow, description="UTC ISO‑8601 timestamp"
    )
    level: str = Field(..., description="Log level: INFO, DEBUG, WARN, ERROR")
    message: str = Field(..., description="Human‑readable log message")
    extra: Optional[Dict[str, Any]] = Field(default_factory=dict)
    service: str = Field(...)
    env: str = Field(...)
    region: str = Field(...)
    tenant: Optional[str] = None
    instance: str = Field(...)
    trace_id: Optional[str] = Field(None, description="W3C trace‑parent trace_id (32 hex chars)")
    span_id: Optional[str] = Field(None, description="W3C trace‑parent span_id (16 hex chars)")

    @validator("level")
    def _level_allowed(cls, v: str) -> str:
        allowed = {"DEBUG", "INFO", "WARN", "ERROR"}
        if v not in allowed:
            raise ValueError(f"level must be one of {allowed}, got {v}")
        return v

    model_config = {
        "from_attributes": True,
        "json_encoders": {"datetime": lambda v: v.isoformat(timespec="milliseconds") + "Z"},
    }


class MetricInfo(BaseModel):
    name: str = Field(..., description="Metric name in snake_case, prefixed with service name")
    description: str = Field(..., description="Human readable description")
    unit: Optional[str] = Field(None, description="Unit, e.g. 'seconds', 'bytes', 'requests'")
    type: str = Field(..., description="counter | gauge | histogram | summary")
    labels: List[str] = Field(
        default_factory=list, description="List of label keys attached to the metric"
    )

    @validator("type")
    def _type_allowed(cls, v: str) -> str:
        allowed = {"counter", "gauge", "histogram", "summary"}
        if v not in allowed:
            raise ValueError(f"type must be one of {allowed}, got {v}")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "example",
                "description": "example",
                "unit": "example",
                "type": "example",
                "labels": [],
            }
        }
    }


class TraceContext(BaseModel):
    trace_id: str = Field(..., min_length=32, max_length=32, pattern="^[0-9a-f]{32}$")
    span_id: str = Field(..., min_length=16, max_length=16, pattern="^[0-9a-f]{16}$")
    trace_flags: str = Field(default="01", min_length=2, max_length=2, pattern="^[0-9a-f]{2}$")
    tracestate: Optional[str] = None

    def to_header(self) -> str:
        """Return the `traceparent` header string."""
        return f"00-{self.trace_id}-{self.span_id}-{self.trace_flags}"

    model_config = {
        "json_schema_extra": {
            "example": {
                "trace_id": "example",
                "span_id": "example",
                "trace_flags": "example",
                "tracestate": "example",
            }
        }
    }


def build_log_record(payload: Dict[str, Any]) -> LogRecord:
    """Create a `LogRecord` instance from an arbitrary dict.

    Missing fields will raise a ``pydantic.ValidationError`` – callers can decide
    whether to drop the record or fallback to a minimal safe representation.
    """
    return LogRecord(**payload)


"""End of observability schema definitions."""
