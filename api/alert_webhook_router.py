# -*- coding: utf-8 -*-
"""Alert webhook router for external monitoring systems.

Supports Prometheus, Grafana, Zabbix, Datadog, etc.
"""

from __future__ import annotations

import logging
from typing import Any, List, Optional

from fastapi import APIRouter, Body, HTTPException, status
from pydantic import BaseModel

from core.alert_engine import alert_history
from core.alert_providers import get_alert_provider, list_alert_providers

process_alert: Any = None
try_auto_heal: Any = None

try:
    from gateway.services_client import process_alert

    PROCESS_AVAILABLE = True
    AUTO_HEAL_AVAILABLE = True
    try_auto_heal = process_alert
except Exception as e:
    logging.exception("Unexpected exception: %s", e)
    PROCESS_AVAILABLE = False
    process_alert = None
    try_auto_heal = None
    AUTO_HEAL_AVAILABLE = False

try:
    from core.command_guard import record_audit
except Exception as e:
    logging.exception("Unexpected exception: %s", e)
    record_audit = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/alerts", tags=["告警接入"])


class WebhookResult(BaseModel):
    alert_id: Optional[str] = None
    status: str
    error: Optional[str] = None


class WebhookResponse(BaseModel):
    source: str
    received: int
    total: int
    processed: int
    results: List[WebhookResult]


@router.post("/webhook/{provider}", response_model=WebhookResponse)
async def receive_alert(provider: str, payload: Any = Body(...)) -> WebhookResponse:
    """Receive an alert payload from any supported monitoring provider."""
    provider_impl = get_alert_provider(provider)
    if provider_impl is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(f"Unknown alert provider: {provider}. " f"Available: {list_alert_providers()}"),
        )

    if not AUTO_HEAL_AVAILABLE or try_auto_heal is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Auto-heal engine is not available",
        )

    alerts = provider_impl.normalize(payload)
    for alert in alerts:
        if isinstance(alert, dict):
            alert_history.appendleft(alert)
    results: List[WebhookResult] = []

    for alert in alerts:
        alert_id = alert.get("id") if isinstance(alert, dict) else None
        status_flag = ""
        if isinstance(alert, dict):
            status_flag = str(alert.get("status", "firing")).lower()
        if status_flag != "firing":
            results.append(
                WebhookResult(
                    alert_id=alert_id,
                    status="skipped",
                    error="status is not firing",
                )
            )
            continue

        if record_audit is not None:
            try:
                record_audit(
                    host=str(alert.get("host", alert_id or "unknown")),
                    command="ALERT_RECEIVED",
                    risk_level=str(alert.get("severity", "info")),
                    result="received",
                    executor="alert_webhook",
                    trace_id=str(alert.get("trace_id", "")),
                )
            except Exception as e:
                logging.exception("Unexpected exception: %s", e)

        try:
            result = await try_auto_heal(alert)
            results.append(
                WebhookResult(
                    alert_id=result.get("alert_id", alert_id),
                    status="processed",
                )
            )
        except Exception as exc:
            logger.exception("try_auto_heal failed for alert %s", alert_id)
            results.append(WebhookResult(alert_id=alert_id, status="error", error=str(exc)[:200]))

    return WebhookResponse(
        source=provider,
        received=len(alerts),
        total=len(alerts),
        processed=len([r for r in results if r.status in ("processed", "skipped")]),
        results=results,
    )


@router.post("/webhook/prometheus", response_model=WebhookResponse)
async def receive_prometheus(payload: Any = Body(...)) -> WebhookResponse:
    """Dedicated Prometheus / Alertmanager webhook endpoint."""
    return await receive_alert("prometheus", payload)


@router.post("/prometheus", response_model=WebhookResponse)
async def receive_prometheus_root(payload: Any = Body(...)) -> WebhookResponse:
    """Prometheus / Alertmanager webhook endpoint at /api/v1/alerts/prometheus."""
    return await receive_alert("prometheus", payload)
