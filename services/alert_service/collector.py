# -*- coding: utf-8 -*-
"""Alert collector microservice: receives Prometheus webhook alerts."""

from __future__ import annotations

import logging
import time
from collections import deque
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Deque, Dict, List, Optional

from fastapi import FastAPI, HTTPException, status
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest
from pydantic import ValidationError
from starlette.responses import Response

from services.alert_service.config import settings
from services.alert_service.mq import InMemoryMessageQueue
from services.alert_service.repository import AlertRepository, InMemoryAlertRepository
from services.alert_service.schemas import (
    Alert,
    AlertSeverity,
    AlertStatus,
    PrometheusAlert,
    PrometheusAlertGroup,
    ServiceHealth,
)

ALERTS_RECEIVED = Counter(
    "alerts_collector_received_total",
    "Total alerts received",
    ["status"],
)
ALERTS_SAVED = Counter(
    "alerts_collector_saved_total",
    "Total alerts saved and published",
)
ALERT_PROCESSING_TIME = Histogram(
    "alerts_collector_processing_seconds",
    "Time spent processing alerts",
)
ALERTS_QUEUE_SIZE = Gauge(
    "alerts_collector_queue_size",
    "Current size of the raw alert queue",
)

logger = logging.getLogger(__name__)


class _SlidingWindowRateLimiter:
    """Simple async sliding-window rate limiter."""

    def __init__(self, max_rate: int, window_seconds: float = 1.0) -> None:
        self.max_rate = max_rate
        self.window_seconds = window_seconds
        self._timestamps: Deque[float] = deque()

    async def acquire(self, count: int = 1) -> bool:
        now = time.time()
        cutoff = now - self.window_seconds
        while self._timestamps and self._timestamps[0] < cutoff:
            self._timestamps.popleft()
        if len(self._timestamps) + count > self.max_rate:
            return False
        for _ in range(count):
            self._timestamps.append(now)
        return True


class CollectorState:
    """Shared state for the collector service."""

    def __init__(self) -> None:
        self.repository: AlertRepository = InMemoryAlertRepository()
        self.mq = InMemoryMessageQueue()
        self.start_time = time.time()
        self.rate_limiter = _SlidingWindowRateLimiter(
            max_rate=settings.collector_max_alerts_per_second,
            window_seconds=1.0,
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    state = CollectorState()
    app.state.repo = state.repository
    app.state.mq = state.mq
    app.state.rate_limiter = state.rate_limiter
    app.state.start_time = state.start_time
    yield


app = FastAPI(
    title="Alert Collector",
    description="Receives Prometheus alerts and publishes to the alert pipeline.",
    version="0.1.0",
    lifespan=lifespan,
)


def _severity_from_label(level: str) -> AlertSeverity:
    mapping = {
        "critical": AlertSeverity.CRITICAL,
        "warning": AlertSeverity.WARNING,
        "info": AlertSeverity.INFO,
        "high": AlertSeverity.HIGH,
        "fatal": AlertSeverity.FATAL,
    }
    return mapping.get(level.lower(), AlertSeverity.WARNING)


_SEVERITY_WEIGHT = {
    "critical": 4,
    "high": 3,
    "warning": 2,
    "info": 1,
    "fatal": 5,
}

_PRIORITY_WEIGHT = {"P0": 30, "P1": 20, "P2": 10, "P3": 0}


def _alert_priority(alert: Alert) -> int:
    """Compute a queue priority where lower values are consumed first."""
    if alert.status == AlertStatus.RESOLVED:
        return -1000
    level = str(alert.level.value).lower() if alert.level else "info"
    sw = _SEVERITY_WEIGHT.get(level, 0)
    pw = _PRIORITY_WEIGHT.get(alert.priority, 0) if alert.priority else 0
    return -(sw * 10 + pw)


def _parse_prometheus_alert(prom_alert: PrometheusAlert) -> Alert:
    labels = prom_alert.labels or {}
    annotations = prom_alert.annotations or {}
    name = labels.get("alertname", "unknown")
    instance = labels.get("instance", labels.get("host", "unknown"))
    detected = prom_alert.startsAt or datetime.utcnow()
    alert_id = f"{name}-{instance}-{detected.isoformat()}"

    value: Optional[float] = None
    raw_value = labels.get("value")
    if raw_value is not None:
        try:
            value = float(raw_value)
        except (ValueError, TypeError):
            value = None

    status = AlertStatus.PENDING
    if prom_alert.status and str(prom_alert.status).lower() == "resolved":
        status = AlertStatus.RESOLVED

    tags = {k: v for k, v in labels.items() if k not in ("alertname", "instance", "host")}

    return Alert(
        id=alert_id,
        level=_severity_from_label(str(labels.get("severity", "warning"))),
        status=status,
        category=labels.get("category", "system"),
        alert_type=name,
        title=annotations.get("summary", name),
        description=annotations.get("description", ""),
        metric=labels.get("__name__", labels.get("metric", name)),
        value=value,
        detected_at=detected,
        metric_time=prom_alert.startsAt,
        host=instance,
        platform=labels.get("platform", "unknown"),
        priority=labels.get("priority", "P3"),
        source="prometheus",
        fingerprint=prom_alert.fingerprint or alert_id,
        tags=tags,
    )


@app.get("/health", response_model=ServiceHealth)
async def health() -> ServiceHealth:
    return ServiceHealth(
        status="ok",
        service="alert-collector",
        uptime_seconds=int(time.time() - app.state.start_time),
    )


@app.get("/metrics")
async def metrics() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/alerts")
async def receive_alerts(group: PrometheusAlertGroup) -> Dict[str, Any]:
    with ALERT_PROCESSING_TIME.time():
        received = len(group.alerts)

        if not await app.state.rate_limiter.acquire(received):
            ALERTS_RECEIVED.labels(status="rate_limited").inc(received)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Alert rate limit exceeded",
            )

        saved = 0
        ids: List[str] = []

        for prom_alert in group.alerts:
            try:
                alert = _parse_prometheus_alert(prom_alert)
                await app.state.repo.save(alert)
                await app.state.mq.publish(
                    "alerts.raw",
                    {"type": "alert", "alert": alert.model_dump()},
                    priority=_alert_priority(alert),
                )
                saved += 1
                ids.append(alert.id)
            except ValidationError as exc:
                logger.warning(f"Validation error parsing alert: {exc}")
                ALERTS_RECEIVED.labels(status="invalid").inc()
            except Exception as exc:
                logger.error(f"Error processing alert: {exc}")
                ALERTS_RECEIVED.labels(status="error").inc()

        ALERTS_QUEUE_SIZE.set(app.state.mq.qsize("alerts.raw"))
        ALERTS_RECEIVED.labels(status="ok").inc(saved)
        ALERTS_SAVED.inc(saved)
        return {"received": received, "saved": saved, "ids": ids}


def _normalize_alert(source: str, payload: Dict[str, Any]) -> Alert:
    """Normalize alerts from multiple upstream sources into the unified Alert model."""
    source = source.lower()
    now = datetime.utcnow()

    if source == "grafana":
        return _from_grafana(payload, now)
    if source == "zabbix":
        return _from_zabbix(payload, now)
    return _from_generic(payload, now)


def _from_grafana(payload: Dict[str, Any], now: datetime) -> Alert:
    title = payload.get("title") or payload.get("ruleName") or "grafana-alert"
    message = payload.get("message") or ""
    state = str(payload.get("state", "alerting")).lower()
    status = AlertStatus.RESOLVED if state in ("ok", "paused", "resolved") else AlertStatus.PENDING

    eval_matches = payload.get("evalMatches") or [{}]
    first_match = eval_matches[0] if eval_matches else {}
    metric = first_match.get("metric") or "unknown"
    raw_value = first_match.get("value")
    tags = first_match.get("tags") or {}
    if isinstance(tags, dict):
        instance = tags.get("host") or tags.get("instance") or "unknown"
    else:
        instance = "unknown"

    value: Optional[float] = None
    try:
        value = float(raw_value)
    except (ValueError, TypeError):
        value = None

    severity = _extract_severity(message) or "warning"
    alert_id = f"grafana-{title}-{instance}-{now.isoformat()}"
    return Alert(
        id=alert_id,
        level=_severity_from_label(severity),
        status=status,
        category="system",
        alert_type=title,
        title=title,
        description=message,
        metric=metric,
        value=value,
        detected_at=now,
        metric_time=now,
        host=instance,
        platform="grafana",
        priority="P3",
        source="grafana",
        fingerprint=alert_id,
        tags={"tags": tags} if isinstance(tags, dict) else {},
    )


def _from_zabbix(payload: Dict[str, Any], now: datetime) -> Alert:
    host = payload.get("hostname") or payload.get("host") or "unknown"
    name = (
        payload.get("alert_name")
        or payload.get("trigger_name")
        or payload.get("name")
        or "zabbix-alert"
    )
    message = payload.get("message") or payload.get("description") or ""
    status_str = str(payload.get("status", "PROBLEM")).upper()
    status = (
        AlertStatus.RESOLVED
        if status_str in ("RESOLVED", "OK", "RECOVERED")
        else AlertStatus.PENDING
    )
    value_raw = payload.get("value")
    value: Optional[float] = None
    try:
        value = float(value_raw)
    except (ValueError, TypeError):
        value = None

    severity = _extract_severity(message) or str(payload.get("severity", "warning"))
    alert_id = f"zabbix-{name}-{host}-{now.isoformat()}"
    return Alert(
        id=alert_id,
        level=_severity_from_label(severity),
        status=status,
        category="system",
        alert_type=name,
        title=name,
        description=message,
        metric=payload.get("item", "unknown"),
        value=value,
        detected_at=now,
        metric_time=now,
        host=host,
        platform="zabbix",
        priority="P3",
        source="zabbix",
        fingerprint=alert_id,
        tags={},
    )


def _from_generic(payload: Dict[str, Any], now: datetime) -> Alert:
    if isinstance(payload, list) and payload:
        payload = payload[0]
    if not isinstance(payload, dict):
        raise ValueError("Generic alert payload must be a JSON object")

    alert = Alert(**payload)
    if not alert.id:
        alert.id = f"generic-{alert.title}-{now.isoformat()}"
    if not alert.fingerprint:
        alert.fingerprint = alert.id
    return alert


def _extract_severity(text: str) -> Optional[str]:
    if not text:
        return None
    lower = text.lower()
    for sev in ("critical", "fatal", "high", "warning", "info"):
        if sev in lower:
            return sev
    return None


@app.post("/alerts/{source}")
async def receive_generic_alert(source: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Receive alerts from Grafana, Zabbix, or any custom source and normalize them."""
    with ALERT_PROCESSING_TIME.time():
        if not await app.state.rate_limiter.acquire(1):
            ALERTS_RECEIVED.labels(status="rate_limited").inc(1)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Alert rate limit exceeded",
            )

        try:
            alert = _normalize_alert(source, payload)
            await app.state.repo.save(alert)
            await app.state.mq.publish(
                "alerts.raw",
                {"type": "alert", "alert": alert.model_dump()},
                priority=_alert_priority(alert),
            )
            ALERTS_QUEUE_SIZE.set(app.state.mq.qsize("alerts.raw"))
            ALERTS_RECEIVED.labels(status="ok").inc(1)
            ALERTS_SAVED.inc(1)
            return {"received": 1, "saved": 1, "ids": [alert.id]}
        except ValidationError as exc:
            logger.warning(f"Validation error normalizing {source} alert: {exc}")
            ALERTS_RECEIVED.labels(status="invalid").inc(1)
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid {source} alert payload",
            ) from exc
        except Exception as exc:
            logger.error(f"Error processing {source} alert: {exc}")
            ALERTS_RECEIVED.labels(status="error").inc(1)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to process alert",
            ) from exc


@app.get("/alerts")
async def list_alerts(limit: int = 100) -> Dict[str, Any]:
    alerts = await app.state.repo.list(limit=limit)
    return {"total": len(alerts), "alerts": [a.model_dump() for a in alerts]}
