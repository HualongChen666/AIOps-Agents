# -*- coding: utf-8 -*-
"""Grafana alert webhook adapter."""

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


def _first_numeric(values: Any) -> float:
    if not isinstance(values, dict):
        return 0.0
    for v in values.values():
        try:
            return float(v)
        except (TypeError, ValueError):
            continue
    return 0.0


@register_alert_provider
class GrafanaAlertProvider(AlertProvider):
    """Convert a Grafana alert webhook payload into internal alert dicts."""

    name = "grafana"

    def normalize(self, raw_payload: Any) -> List[Dict[str, Any]]:
        payload = raw_payload or {}
        if isinstance(payload, list):
            raw_alerts = payload
        elif isinstance(payload, dict):
            raw_alerts = payload.get("alerts", [payload])
        else:
            return []

        normalized: List[Dict[str, Any]] = []
        for raw in raw_alerts:
            if not isinstance(raw, dict):
                continue
            alert = self._normalize_one(raw)
            if alert:
                normalized.append(alert)
        return normalized

    def _normalize_one(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        labels = raw.get("labels") or {}
        if not isinstance(labels, dict):
            labels = {}
        annotations = raw.get("annotations") or {}
        if not isinstance(annotations, dict):
            annotations = {}

        status = str(raw.get("status", "firing")).lower()
        fingerprint = str(
            raw.get("fingerprint") or labels.get("alertname") or uuid.uuid4().hex[:16]
        )[:64]
        starts_at = raw.get("startsAt") or datetime.now(timezone.utc).isoformat()

        values = raw.get("values")
        value_float = _first_numeric(values)
        if value_float == 0.0:
            value_float = _safe_float(labels.get("value"))

        return {
            "id": f"GRAF-{fingerprint}",
            "source": "grafana",
            "title": str(annotations.get("summary") or labels.get("alertname") or "")[:512],
            "desc": str(annotations.get("description") or "")[:4096],
            "severity": str(labels.get("severity", "warning")).lower(),
            "status": "firing" if status == "firing" else "resolved",
            "metric": str(labels.get("__name__") or labels.get("alertname") or "")[:256],
            "value": value_float,
            "host": str(labels.get("instance") or labels.get("host") or "")[:256],
            "service": str(labels.get("job") or labels.get("service") or "")[:256],
            "platform": str(labels.get("platform", "linux")).lower(),
            "labels": labels,
            "annotations": annotations,
            "started_at": starts_at,
            "fingerprint": fingerprint,
            "raw": raw,
            "trace_id": uuid.uuid4().hex,
        }
