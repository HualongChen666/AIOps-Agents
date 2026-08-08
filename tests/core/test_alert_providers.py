# -*- coding: utf-8 -*-
"""Smoke tests for alert provider normalization."""

import json
from pathlib import Path

import pytest

from core.alert_providers import get_alert_provider, list_alert_providers


def _load_example(name: str):
    path = Path(__file__).resolve().parents[2] / "examples" / f"{name}_alert.json"
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def test_all_providers_are_registered():
    providers = list_alert_providers()
    for name in ("prometheus", "grafana", "datadog", "zabbix", "cloudwatch", "pagerduty"):
        assert name in providers


def test_cloudwatch_normalize_sns():
    payload = _load_example("cloudwatch")
    provider = get_alert_provider("cloudwatch")
    alerts = provider.normalize(payload)
    assert len(alerts) == 1
    alert = alerts[0]
    assert alert["source"] == "cloudwatch"
    assert alert["title"] == "HighCPU"
    assert alert["metric"] == "AWS/EC2/CPUUtilization"
    assert alert["status"] == "firing"


def test_pagerduty_normalize_webhook():
    payload = _load_example("pagerduty")
    provider = get_alert_provider("pagerduty")
    alerts = provider.normalize(payload)
    assert len(alerts) == 1
    alert = alerts[0]
    assert alert["source"] == "pagerduty"
    assert alert["title"] == "Database latency high"
    assert alert["status"] == "firing"
