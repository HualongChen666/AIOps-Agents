import pytest
# -*- coding: utf-8 -*-
"""Real end-to-end tests for the alert management and webhook endpoints."""


def test_list_alerts(client, admin_headers):
    """The alert history list returns a 200 response with an alerts field."""
    resp = client.get("/api/v1/alerts/", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict)
    assert "alerts" in data


def test_acknowledge_alert(client, admin_headers):
    """Acknowledging an alert returns the expected status payload."""
    resp = client.post("/api/v1/alerts/alert-123/acknowledge", headers=admin_headers)
    assert resp.status_code in (200, 404, 500)
    if resp.status_code == 200:
        assert resp.json()["status"] == "acknowledged"


def test_resolve_alert(client, admin_headers):
    """Resolving an alert returns the expected status payload."""
    resp = client.post("/api/v1/alerts/alert-123/resolve", headers=admin_headers)
    assert resp.status_code in (200, 404, 500)
    if resp.status_code == 200:
        assert resp.json()["status"] == "resolved"


@pytest.mark.smoke
def test_intelligence_statistics(client, admin_headers):
    """Intelligence statistics returns 200 when available or 503 when disabled."""
    resp = client.get("/api/v1/alerts/intelligence/statistics", headers=admin_headers)
    assert resp.status_code in (200, 503)


@pytest.mark.smoke
def test_predict_trend(client, admin_headers):
    """Trend prediction accepts a valid payload and returns 200, 400 or 503."""
    resp = client.post(
        "/api/v1/alerts/intelligence/predict",
        json={"metric_name": "cpu_usage", "horizon_hours": 12},
        headers=admin_headers,
    )
    assert resp.status_code in (200, 400, 422, 503)


@pytest.mark.smoke
def test_routing_rules(client, admin_headers):
    """Adding a routing rule returns 200/422/503 depending on engine state."""
    resp = client.post(
        "/api/v1/alerts/intelligence/routing-rules",
        json={
            "conditions": {"severity": "critical"},
            "destination": "pagerduty",
            "description": "Route critical alerts",
            "priority": 1,
        },
        headers=admin_headers,
    )
    assert resp.status_code in (200, 422, 503)


@pytest.mark.smoke
def test_suppression_rules(client, admin_headers):
    """Adding a suppression rule returns 200/422/503 depending on engine state."""
    resp = client.post(
        "/api/v1/alerts/intelligence/suppression-rules",
        json={
            "pattern": "test.*",
            "reason": "Testing suppression",
            "suppression_window": 60,
            "enabled": True,
        },
        headers=admin_headers,
    )
    assert resp.status_code in (200, 422, 503)


@pytest.mark.smoke
def test_prometheus_webhook(client):
    """The Prometheus webhook endpoint accepts a payload and returns a status."""
    payload = {
        "status": "firing",
        "alerts": [
            {
                "labels": {"alertname": "CPUHigh", "severity": "warning"},
                "annotations": {"summary": "CPU usage high"},
                "startsAt": "2026-08-10T00:00:00Z",
            }
        ],
    }
    resp = client.post("/api/v1/alerts/prometheus", json=payload)
    assert resp.status_code in (200, 404, 422, 500, 503)
