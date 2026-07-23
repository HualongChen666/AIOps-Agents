# -*- coding: utf-8 -*-
"""Pydantic schemas for the alert microservice."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


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
    alerts: List[PrometheusAlert] = Field(default_factory=list)


class Alert(BaseModel):
    """标准化告警模型."""

    id: str
    level: AlertSeverity = AlertSeverity.WARNING
    status: AlertStatus = AlertStatus.PENDING
    category: str = "system"
    alert_type: str = "unknown"
    title: str
    description: str = ""
    metric: Optional[str] = None
    value: Optional[float] = None
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    metric_time: Optional[datetime] = None
    host: Optional[str] = None
    platform: str = "unknown"
    priority: str = "P3"
    source: str = "prometheus"
    fingerprint: Optional[str] = None
    routed_to: Optional[str] = None
    suppressed: bool = False
    suppression_reason: Optional[str] = None
    aggregated_count: int = 1
    prev_suppressed: int = 0
    tags: Dict[str, Any] = Field(default_factory=dict)

    model_config = {"extra": "allow"}


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
