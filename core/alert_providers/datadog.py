# -*- coding: utf-8 -*-
"""Datadog monitor webhook adapter."""

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


@register_alert_provider
class DatadogAlertProvider(AlertProvider):
    """Convert a Datadog monitor alert payload into internal alert dicts."""

    name = "datadog"

    def normalize(self, raw_payload: Any) -> List[Dict[str, Any]]:
        if isinstance(raw_payload, list):
            raw_alerts = raw_payload
        elif isinstance(raw_payload, dict):
            raw_alerts = [raw_payload]
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
        title = str(raw.get("title") or raw.get("alert_title") or "")[:512]
        text = str(raw.get("text") or raw.get("message") or raw.get("body") or "")[:4096]
        hostname = str(raw.get("hostname") or raw.get("host") or "")[:256]

        alert_metric = str(raw.get("alert_metric") or "")[:256]
        metric_snapshot = raw.get("metric_snapshot") or {}
        if not isinstance(metric_snapshot, dict):
            metric_snapshot = {}
        metric = alert_metric or (list(metric_snapshot.keys())[0] if metric_snapshot else "")
        value = _safe_float(list(metric_snapshot.values())[0] if metric_snapshot else None)

        event_type = str(
            raw.get("event_type") or raw.get("alert_transition") or raw.get("status") or "trigger"
        ).lower()
        status = (
            "resolved" if event_type in ("recovery", "recovered", "ok", "resolved") else "firing"
        )

        priority = str(raw.get("priority") or "normal").lower()
        severity_map = {
            "1": "info",
            "2": "low",
            "3": "warning",
            "4": "high",
            "5": "critical",
            "p1": "info",
            "p2": "low",
            "p3": "warning",
            "p4": "high",
            "p5": "critical",
        }
        severity = severity_map.get(priority, priority if priority else "warning")

        fingerprint = str(
            raw.get("alert_id") or raw.get("id") or raw.get("event_id") or uuid.uuid4().hex[:16]
        )[:64]
        started_at = (
            raw.get("date") or raw.get("date_event") or datetime.now(timezone.utc).isoformat()
        )

        tags = raw.get("tags")
        labels: Dict[str, Any] = {}
        if isinstance(tags, list):
            for tag in tags:
                if isinstance(tag, str) and ":" in tag:
                    key, _, val = tag.partition(":")
                    labels[key] = val
                elif isinstance(tag, str):
                    labels[tag] = "true"
        elif isinstance(tags, dict):
            labels = tags

        return {
            "id": f"DD-{fingerprint}",
            "source": "datadog",
            "title": title,
            "desc": text,
            "severity": severity,
            "status": status,
            "metric": metric,
            "value": value,
            "host": hostname,
            "service": str(labels.get("service") or hostname or "")[:256],
            "platform": str(labels.get("platform") or "linux").lower(),
            "labels": labels,
            "annotations": {"priority": priority},
            "started_at": started_at,
            "fingerprint": fingerprint,
            "raw": raw,
            "trace_id": uuid.uuid4().hex,
        }
