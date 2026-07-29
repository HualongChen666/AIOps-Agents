# -*- coding: utf-8 -*-
"""Unit tests for the alert provider adapters."""

from __future__ import annotations

from core.alert_providers import get_alert_provider, list_alert_providers


def test_list_providers():
    providers = list_alert_providers()
    assert "prometheus" in providers


def test_get_prometheus_provider():
    provider = get_alert_provider("prometheus")
    assert provider is not None
    assert provider.name == "prometheus"


def test_prometheus_normalize_group():
    provider = get_alert_provider("prometheus")
    payload = {
        "alerts": [
            {
                "labels": {
                    "__name__": "memory_high",
                    "severity": "warning",
                    "instance": "h1",
                },
                "annotations": {
                    "summary": "Memory high",
                    "description": "Memory usage high",
                },
                "status": "firing",
            }
        ]
    }
    alerts = provider.normalize(payload)
    assert len(alerts) == 1
    assert alerts[0]["id"].startswith("PROM-")
    assert alerts[0]["metric"] == "memory_high"
    assert alerts[0]["status"] == "firing"
    assert alerts[0]["host"] == "h1"


def test_prometheus_resolved_alert():
    provider = get_alert_provider("prometheus")
    payload = {
        "alerts": [
            {
                "labels": {"__name__": "x"},
                "annotations": {},
                "status": "resolved",
            }
        ]
    }
    alerts = provider.normalize(payload)
    assert alerts[0]["status"] == "resolved"
