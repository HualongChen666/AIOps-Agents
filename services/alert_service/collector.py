# -*- coding: utf-8 -*-
"""Alert collector microservice: receives Prometheus webhook alerts."""

from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import FastAPI
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from pydantic import ValidationError
from starlette.responses import Response

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

logger = logging.getLogger(__name__)


class CollectorState:
    """Shared state for the collector service."""

    def __init__(self) -> None:
        self.repository: AlertRepository = InMemoryAlertRepository()
        self.mq = InMemoryMessageQueue()
        self.start_time = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI):
    state = CollectorState()
    app.state.repo = state.repository
    app.state.mq = state.mq
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

    tags = {k: v for k, v in labels.items() if k not in ("alertname", "instance", "host")}

    return Alert(
        id=alert_id,
        level=_severity_from_label(str(labels.get("severity", "warning"))),
        status=AlertStatus.PENDING,
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
        saved = 0
        ids: List[str] = []

        for prom_alert in group.alerts:
            try:
                alert = _parse_prometheus_alert(prom_alert)
                await app.state.repo.save(alert)
                await app.state.mq.publish(
                    "alerts.raw",
                    {"type": "alert", "alert": alert.model_dump()},
                )
                saved += 1
                ids.append(alert.id)
            except ValidationError as exc:
                logger.warning(f"Validation error parsing alert: {exc}")
                ALERTS_RECEIVED.labels(status="invalid").inc()
            except Exception as exc:
                logger.error(f"Error processing alert: {exc}")
                ALERTS_RECEIVED.labels(status="error").inc()

        ALERTS_RECEIVED.labels(status="ok").inc(saved)
        ALERTS_SAVED.inc(saved)
        return {"received": received, "saved": saved, "ids": ids}


@app.get("/alerts")
async def list_alerts(limit: int = 100) -> Dict[str, Any]:
    alerts = await app.state.repo.list(limit=limit)
    return {"total": len(alerts), "alerts": [a.model_dump() for a in alerts]}
