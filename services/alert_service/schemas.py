# -*- coding: utf-8 -*-
"""Pydantic schemas for the alert microservice."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

try:
    from core.content_moderation import moderate_content as _moderate_content
except ImportError:
    _moderate_content = None  # type: ignore[assignment]


# Content-size limits to protect downstream caches, queues and LLM prompts.
MAX_TITLE_LENGTH = 512
MAX_DESCRIPTION_LENGTH = 4096
MAX_TAG_VALUE_LENGTH = 1024
MAX_TAG_KEYS = 64
MAX_LABEL_VALUE_LENGTH = 1024
MAX_LABEL_KEYS = 64


def _truncate_str(value: Any, max_length: int) -> Any:
    if isinstance(value, str):
        return value[:max_length]
    return value


def _sanitize_dict(value: Any, max_keys: int = 64, max_value_length: int = 1024) -> Dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    sanitized: Dict[str, Any] = {}
    for idx, (k, v) in enumerate(value.items()):
        if idx >= max_keys:
            sanitized["__truncated"] = True
            break
        if isinstance(v, str):
            sanitized[k] = v[:max_value_length]
        else:
            sanitized[k] = v
    return sanitized


class AlertSeverity(str, Enum):
    """告警严重级别."""

    INFO = "info"
    WARNING = "warning"
    HIGH = "high"
    CRITICAL = "critical"
    FATAL = "fatal"


class AlertStatus(str, Enum):
    """告警状态."""

    PENDING = "pending"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    ESCALATED = "escalated"
    SUPPRESSED = "suppressed"


class PrometheusAlert(BaseModel):
    """Prometheus webhook alert payload."""

    status: str = "firing"
    labels: Dict[str, Any] = Field(default_factory=dict)
    annotations: Dict[str, Any] = Field(default_factory=dict)
    startsAt: datetime = Field(default_factory=datetime.utcnow)
    endsAt: Optional[datetime] = None
    generatorURL: Optional[str] = None
    fingerprint: Optional[str] = None

    @field_validator("labels", "annotations", mode="before")
    @classmethod
    def _sanitize_labels(cls, v: Any) -> Dict[str, Any]:
        return _sanitize_dict(v, max_keys=MAX_LABEL_KEYS, max_value_length=MAX_LABEL_VALUE_LENGTH)

    @field_validator("status", mode="before")
    @classmethod
    def _normalize_status(cls, v: Any) -> str:
        if isinstance(v, str):
            return v.lower()
        return "firing"


class PrometheusAlertGroup(BaseModel):
    """Prometheus webhook request body."""

    version: str = "4"
    groupKey: str = ""
    truncatedAlerts: int = 0
    status: str = "firing"
    receiver: str = ""
    groupLabels: Dict[str, Any] = Field(default_factory=dict)
    commonLabels: Dict[str, Any] = Field(default_factory=dict)
    commonAnnotations: Dict[str, Any] = Field(default_factory=dict)
    externalURL: str = ""
    alerts: List[PrometheusAlert] = Field(default_factory=list, max_length=10_000)

    @field_validator("groupLabels", "commonLabels", "commonAnnotations", mode="before")
    @classmethod
    def _sanitize_group_labels(cls, v: Any) -> Dict[str, Any]:
        return _sanitize_dict(v, max_keys=MAX_LABEL_KEYS, max_value_length=MAX_LABEL_VALUE_LENGTH)

    @field_validator("status", mode="before")
    @classmethod
    def _normalize_group_status(cls, v: Any) -> str:
        if isinstance(v, str):
            return v.lower()
        return "firing"


class Alert(BaseModel):
    """标准化告警模型."""

    id: str
    level: AlertSeverity = AlertSeverity.WARNING
    status: AlertStatus = AlertStatus.PENDING
    category: str = "system"
    alert_type: str = "unknown"
    title: str
    description: str = ""
    desc: Optional[str] = None
    metric: Optional[str] = None
    value: Optional[float] = None
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    metric_time: Optional[datetime] = None
    host: Optional[str] = None
    service: Optional[str] = None
    platform: str = "unknown"
    priority: str = "P3"
    source: str = "prometheus"
    severity: Optional[str] = None
    fingerprint: Optional[str] = None
    trace_id: Optional[str] = None
    labels: Dict[str, Any] = Field(default_factory=dict)
    annotations: Dict[str, Any] = Field(default_factory=dict)
    raw: Dict[str, Any] = Field(default_factory=dict)
    routed_to: Optional[str] = None
    suppressed: bool = False
    suppression_reason: Optional[str] = None
    aggregated_count: int = 1
    prev_suppressed: int = 0
    tags: Dict[str, Any] = Field(default_factory=dict)

    model_config = {"extra": "allow"}

    @field_validator("id", "title", "description", mode="before")
    @classmethod
    def _truncate_strings(cls, v: Any, info) -> Any:
        if not isinstance(v, str):
            return v
        if info.field_name == "id":
            return v[:256]
        if info.field_name == "title":
            return v[:MAX_TITLE_LENGTH]
        if info.field_name == "description":
            return v[:MAX_DESCRIPTION_LENGTH]
        return v

    @field_validator("title", "description", mode="before")
    @classmethod
    def _reject_malicious_content(cls, v: Any) -> Any:
        if not isinstance(v, str) or not callable(_moderate_content):
            return v
        allowed, reasons = _moderate_content(v)
        if not allowed:
            raise ValueError(f"Alert content rejected by moderation: {reasons}")
        return v

    @field_validator("tags", mode="before")
    @classmethod
    def _sanitize_tags(cls, v: Any) -> Dict[str, Any]:
        return _sanitize_dict(v, max_keys=MAX_TAG_KEYS, max_value_length=MAX_TAG_VALUE_LENGTH)


class RoutingRule(BaseModel):
    """告警路由规则."""

    name: str
    conditions: Dict[str, Any] = Field(default_factory=dict)
    destination: str
    priority: int = 0
    enabled: bool = True


class SuppressionRule(BaseModel):
    """告警抑制规则."""

    name: str
    pattern: str = ""  # fingerprint or signature
    window_seconds: int = 300
    reason: str = ""
    enabled: bool = True


class EscalationRule(BaseModel):
    """告警升级规则."""

    name: str
    level_threshold: AlertSeverity = AlertSeverity.CRITICAL
    time_threshold_seconds: int = 900
    escalation_target: str = "oncall"
    enabled: bool = True


class ClassificationRule(BaseModel):
    """告警分类规则."""

    name: str
    conditions: Dict[str, Any] = Field(default_factory=dict)
    category: str = ""
    priority: str = "P3"
    enabled: bool = True


class AggregatedAlert(Alert):
    """聚合后的告警."""

    aggregated_count: int = 1
    aggregated_alerts: List[Alert] = Field(default_factory=list)
    cluster_id: Optional[str] = None


class RouteResult(BaseModel):
    """路由结果."""

    route: str
    alert_id: str


class NotificationPayload(BaseModel):
    """通知载荷."""

    channel: str
    alert: Alert
    content: str


class ServiceHealth(BaseModel):
    """服务健康状态."""

    status: str = "ok"
    service: str = ""
    uptime_seconds: int = 0
    alert_count: int = 0
