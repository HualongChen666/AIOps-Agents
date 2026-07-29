# -*- coding: utf-8 -*-
"""E2E test for the Prometheus -> alert webhook -> heal_graph closed loop.

This test exercises the real ``api/alert_webhook_router`` endpoint with a
synthetic Prometheus Alertmanager payload and confirms that the alert is
normalized, persisted and dispatched through ``heal_graph.run_heal``.
"""

from __future__ import annotations

import os
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

os.environ.setdefault("HEAL_EXECUTE_ENABLED", "false")
os.environ.setdefault("HARDWARE_EXECUTE_ENABLED", "false")

from api.alert_webhook_router import router as alert_webhook_router
from core.alert_engine import alert_history
from core.alert_providers.prometheus import PrometheusAlertProvider
from core.heal_graph import HealState, run_heal


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(alert_webhook_router)
    with TestClient(app) as c:
        yield c


PROMETHEUS_PAYLOAD = {
    "status": "firing",
    "externalURL": "http://alertmanager.example.com",
    "alerts": [
        {
            "status": "firing",
            "labels": {
                "alertname": "HighCPU",
                "severity": "warning",
                "instance": "host-01",
                "job": "node-exporter",
                "platform": "linux",
                "value": "92.5",
            },
            "annotations": {
                "summary": "CPU usage high on host-01",
                "description": "CPU usage is above 90% for 5 minutes",
            },
            "startsAt": "2024-01-01T00:00:00.000Z",
        }
    ],
}


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_prometheus_alert_provider_normalization():
    provider = PrometheusAlertProvider()
    alerts = provider.normalize(PROMETHEUS_PAYLOAD)
    assert len(alerts) == 1
    alert = alerts[0]
    assert alert["source"] == "prometheus"
    assert alert["id"].startswith("PROM-")
    assert alert["title"] == "CPU usage high on host-01"
    assert alert["severity"] == "warning"


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_prometheus_alert_run_heal_graph():
    provider = PrometheusAlertProvider()
    alerts = provider.normalize(PROMETHEUS_PAYLOAD)
    alert = alerts[0]
    state = HealState(alert=alert)
    final = await run_heal(state)
    assert final is not None
    assert final.runbook is not None
    assert final.error is None or "not approved" in final.error.lower()


@pytest.mark.e2e
def test_prometheus_http_webhook(client):
    # Clear any previous history to keep assertions deterministic
    alert_history.clear()
    response = client.post("/api/v1/alerts/prometheus", json=PROMETHEUS_PAYLOAD)
    assert response.status_code == 200
    data = response.json()
    assert data["source"] == "prometheus"
    assert data["received"] == 1
    assert data["processed"] == 1
    assert len(data["results"]) == 1
    result = data["results"][0]
    assert result["alert_id"].startswith("PROM-")
    assert result["status"] == "processed"
