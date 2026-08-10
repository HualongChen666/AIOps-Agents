# -*- coding: utf-8 -*-
"""CloudWatch alarm webhook adapter (via SNS or direct alarm payload)."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

from .base import AlertProvider, register_alert_provider


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value) if value is not None else default
    except (TypeError, ValueError):
        return default


def _unwrap_sns(payload: Dict[str, Any]) -> Any:
    """If the payload is an SNS notification, extract the embedded message."""
    if payload.get("Type") == "Notification" and "Message" in payload:
        msg = payload["Message"]
        if isinstance(msg, str):
            try:
                return json.loads(msg)
            except json.JSONDecodeError:
                return msg
        return msg
    return payload


@register_alert_provider
class CloudWatchAlertProvider(AlertProvider):
    """Convert a CloudWatch alarm payload into internal alert dicts."""

    name = "cloudwatch"

    def normalize(self, raw_payload: Any) -> List[Dict[str, Any]]:
        if isinstance(raw_payload, list):
            raw_alarms = raw_payload
        elif isinstance(raw_payload, dict):
            raw_alarms = raw_payload.get("alarms", [_unwrap_sns(raw_payload)])
            if not isinstance(raw_alarms, list):
                raw_alarms = [raw_alarms]
        else:
            return []

        normalized: List[Dict[str, Any]] = []
        for raw in raw_alarms:
            if not isinstance(raw, dict):
                continue
            alert = self._normalize_one(raw)
            if alert:
                normalized.append(alert)
        return normalized

    def _normalize_one(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        alarm_name = raw.get("AlarmName") or raw.get("alarm_name") or "cloudwatch-alarm"
        description = raw.get("AlarmDescription") or raw.get("alarm_description") or ""
        state = str(raw.get("NewStateValue") or raw.get("new_state_value") or "ALARM").lower()
        reason = raw.get("NewStateReason") or raw.get("new_state_reason") or ""

        trigger = raw.get("Trigger") or raw.get("trigger") or {}
        if not isinstance(trigger, dict):
            trigger = {}
        metric = str(trigger.get("MetricName") or trigger.get("metric_name") or alarm_name)[:256]
        namespace = str(trigger.get("Namespace") or trigger.get("namespace") or "AWS/Unknown")[:256]

        dimensions = trigger.get("Dimensions") or []
        if isinstance(dimensions, list):
            labels = {d.get("name") or d.get("Name"): d.get("value") or d.get("Value")
                      for d in dimensions if isinstance(d, dict)}
        else:
            labels = {}

        value = _safe_float(raw.get("Threshold") or trigger.get("Threshold"))
        instance = labels.get("InstanceId") or labels.get("instance_id") or ""
        service = labels.get("ServiceName") or labels.get("service") or namespace
        severity = "critical" if state == "alarm" else "warning"
        fingerprint = str(raw.get("AlarmName") or uuid.uuid4().hex[:16])[:64]
        started_at = raw.get("StateChangeTime") or raw.get(
            "state_change_time") or datetime.now(timezone.utc).isoformat()

        return {
            "id": f"CW-{fingerprint}",
            "source": "cloudwatch",
            "title": str(alarm_name)[:512],
            "desc": f"{description} {reason}".strip()[:4096],
            "severity": severity,
            "status": "firing" if state == "alarm" else "resolved",
            "metric": f"{namespace}/{metric}"[:256],
            "value": value,
            "host": instance[:256],
            "service": str(service)[:256],
            "platform": "aws",
            "labels": labels,
            "annotations": {"namespace": namespace},
            "started_at": started_at,
            "fingerprint": fingerprint,
            "raw": raw,
            "trace_id": uuid.uuid4().hex,
        }
