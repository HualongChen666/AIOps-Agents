# -*- coding: utf-8 -*-
"""PagerDuty webhook adapter (incident events v3)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

from .base import AlertProvider, register_alert_provider


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value) if value is not None else default
    except (TypeError, ValueError):
        return default


def _extract_value(summary: str) -> float:
    """Try to pull a numeric value out of a PagerDuty summary string."""
    import re

    if not isinstance(summary, str):
        return 0.0
    matches = re.findall(r"[-+]?\d*\.?\d+", summary)
    for m in matches:
        try:
            return float(m)
        except ValueError:
            continue
    return 0.0


@register_alert_provider
class PagerDutyAlertProvider(AlertProvider):
    """Convert a PagerDuty v3 webhook payload into internal alert dicts."""

    name = "pagerduty"

    def normalize(self, raw_payload: Any) -> List[Dict[str, Any]]:
        payload = raw_payload or {}
        if isinstance(payload, list):
            raw_messages = payload
        elif isinstance(payload, dict):
            raw_messages = payload.get("messages", [payload])
            if not isinstance(raw_messages, list):
                raw_messages = [raw_messages]
        else:
            return []

        normalized: List[Dict[str, Any]] = []
        for raw in raw_messages:
            if not isinstance(raw, dict):
                continue
            event = raw.get("event") or raw
            incident = raw.get("incident") or raw.get("data", {}).get("incident", {}) or event
            if not isinstance(incident, dict):
                incident = raw
            alert = self._normalize_one(incident)
            if alert:
                normalized.append(alert)
        return normalized

    def _normalize_one(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        title = (
            raw.get("title") or raw.get("summary") or raw.get("description") or "pagerduty-incident"
        )
        description = raw.get("description") or raw.get("summary") or ""
        status = str(raw.get("status") or "triggered").lower()
        severity = str(raw.get("urgency") or raw.get("priority", {}).get("name") or "high").lower()
        if severity not in {"critical", "error", "warning", "info", "debug"}:
            severity = "high" if severity in {"high", "page"} else "warning"
        if severity == "page":
            severity = "critical"

        service = raw.get("service", {}) or {}
        if not isinstance(service, dict):
            service = {}
        service_name = service.get("summary") or service.get("name") or "pagerduty"
        service_id = service.get("id") or ""

        labels = {}
        if service_id:
            labels["service_id"] = service_id
        priority = raw.get("priority", {})
        if isinstance(priority, dict) and priority.get("name"):
            labels["priority"] = priority["name"]

        fingerprint = str(raw.get("id") or raw.get("incident_number") or uuid.uuid4().hex[:16])[:64]
        started_at = (
            raw.get("created_at") or raw.get("created") or datetime.now(timezone.utc).isoformat()
        )
        value = _safe_float(raw.get("value")) or _extract_value(description)

        return {
            "id": f"PD-{fingerprint}",
            "source": "pagerduty",
            "title": str(title)[:512],
            "desc": str(description)[:4096],
            "severity": severity,
            "status": "firing" if status in {"triggered", "acknowledged"} else "resolved",
            "metric": str(raw.get("incident_key") or title)[:256],
            "value": value,
            "host": str(service.get("html_url") or "")[:256],
            "service": str(service_name)[:256],
            "platform": "pagerduty",
            "labels": labels,
            "annotations": {"incident_id": fingerprint},
            "started_at": started_at,
            "fingerprint": fingerprint,
            "raw": raw,
            "trace_id": uuid.uuid4().hex,
        }
