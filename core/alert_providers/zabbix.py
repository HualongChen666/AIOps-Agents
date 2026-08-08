# -*- coding: utf-8 -*-
"""Zabbix media type JSON webhook adapter."""

from __future__ import annotations

import re
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
class ZabbixAlertProvider(AlertProvider):
    """Convert a Zabbix media webhook payload into internal alert dicts."""

    name = "zabbix"

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
        subject = str(raw.get("subject") or raw.get("summary") or "")[:512]
        message = str(raw.get("message") or raw.get("body") or "")[:4096]

        status_raw = str(raw.get("status") or raw.get("event_value") or "").lower()
        if status_raw in ("0", "ok", "resolved", "recovery", "recovered"):
            status = "resolved"
        elif status_raw in ("1", "problem", "firing", "trigger"):
            status = "firing"
        elif "resolved" in subject.lower() or "recovery" in subject.lower():
            status = "resolved"
        else:
            status = "firing"

        severity = str(raw.get("severity") or raw.get("trigger_severity") or "warning").lower()

        hostname = str(raw.get("hostname") or raw.get("host") or raw.get("host_name") or "")[:256]
        item_name = str(raw.get("itemname") or raw.get("item_name") or raw.get("key") or "")[:256]
        item_value = raw.get("itemvalue") or raw.get("item_value") or raw.get("value")

        event_id = str(raw.get("eventid") or raw.get("event_id") or raw.get("id") or uuid.uuid4().hex[:16])[:64]
        started_at = raw.get("event_time") or raw.get("timestamp") or datetime.now(timezone.utc).isoformat()

        title = subject or (message.split("\n")[0] if message else "Zabbix alert")
        desc = message or subject

        labels: Dict[str, Any] = {
            "hostname": hostname,
            "itemname": item_name,
        }
        trigger_name = str(raw.get("trigger_name") or "")
        if trigger_name:
            labels["trigger"] = trigger_name

        return {
            "id": f"ZABB-{event_id}",
            "source": "zabbix",
            "title": title,
            "desc": desc,
            "severity": re.sub(r"[^a-z]", "", severity) or "warning",
            "status": status,
            "metric": item_name,
            "value": _safe_float(item_value),
            "host": hostname,
            "service": str(raw.get("service") or labels.get("service") or hostname or "")[:256],
            "platform": str(raw.get("platform") or labels.get("platform") or "linux").lower(),
            "labels": labels,
            "annotations": {"trigger_name": trigger_name},
            "started_at": started_at,
            "fingerprint": event_id,
            "raw": raw,
            "trace_id": uuid.uuid4().hex,
        }
