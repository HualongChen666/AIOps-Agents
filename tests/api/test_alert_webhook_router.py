# -*- coding: utf-8 -*-
"""Tests for the alert webhook router."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import api.alert_webhook_router as webhook_module
from api.alert_webhook_router import router as alert_webhook_router


async def _mock_try_auto_heal(alert: dict) -> dict:
    return {"healed": True, "alert_id": alert.get("id")}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(webhook_module, "try_auto_heal", _mock_try_auto_heal)
    monkeypatch.setattr(webhook_module, "AUTO_HEAL_AVAILABLE", True)
    app = FastAPI()
    app.include_router(alert_webhook_router)
    return TestClient(app)


def test_prometheus_webhook(client):
    payload = {
        "alerts": [
            {
                "labels": {
                    "__name__": "memory_high",
                    "severity": "warning",
                    "instance": "h1",
                },
                "annotations": {"summary": "Memory high"},
                "status": "firing",
            }
        ]
    }
    resp = client.post("/api/v1/alerts/webhook/prometheus", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["source"] == "prometheus"
    assert data["processed"] == 1
    assert data["results"][0]["status"] == "processed"


def test_resolved_alert_is_skipped(client):
    payload = {
        "alerts": [
            {
                "labels": {"__name__": "x"},
                "annotations": {},
                "status": "resolved",
            }
        ]
    }
    resp = client.post("/api/v1/alerts/webhook/prometheus", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["results"][0]["status"] == "skipped"


def test_unknown_provider_returns_404(client):
    resp = client.post("/api/v1/alerts/webhook/unknown", json={"alerts": []})
    assert resp.status_code == 404


def test_auto_heal_unavailable_returns_503(monkeypatch):
    monkeypatch.setattr(webhook_module, "AUTO_HEAL_AVAILABLE", False)
    app = FastAPI()
    app.include_router(alert_webhook_router)
    client = TestClient(app)
    payload = {"alerts": [{"labels": {"__name__": "x"}, "annotations": {}, "status": "firing"}]}
    resp = client.post("/api/v1/alerts/webhook/prometheus", json=payload)
    assert resp.status_code == 503


def test_auto_heal_error_still_processes_alert(monkeypatch):
    async def _mock_failing_auto_heal(alert: dict) -> dict:
        raise ValueError("Auto heal failed")

    monkeypatch.setattr(webhook_module, "try_auto_heal", _mock_failing_auto_heal)
    monkeypatch.setattr(webhook_module, "AUTO_HEAL_AVAILABLE", True)
    app = FastAPI()
    app.include_router(alert_webhook_router)
    client = TestClient(app)
    payload = {
        "alerts": [
            {
                "labels": {"__name__": "memory_high", "severity": "warning"},
                "annotations": {"summary": "Memory high"},
                "status": "firing",
            }
        ]
    }
    resp = client.post("/api/v1/alerts/webhook/prometheus", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["processed"] == 0  # error status is not counted as processed
    assert data["results"][0]["status"] == "error"
    assert "Auto heal failed" in data["results"][0]["error"]


def test_prometheus_root_endpoint(client):
    payload = {
        "alerts": [
            {
                "labels": {"__name__": "cpu_high", "severity": "critical"},
                "annotations": {"summary": "CPU high"},
                "status": "firing",
            }
        ]
    }
    resp = client.post("/api/v1/alerts/prometheus", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["source"] == "prometheus"
    assert data["processed"] == 1


def test_multiple_alerts_mixed_status(client):
    payload = {
        "alerts": [
            {
                "labels": {"__name__": "alert1"},
                "annotations": {},
                "status": "firing",
            },
            {
                "labels": {"__name__": "alert2"},
                "annotations": {},
                "status": "resolved",
            },
            {
                "labels": {"__name__": "alert3"},
                "annotations": {},
                "status": "firing",
            },
        ]
    }
    resp = client.post("/api/v1/alerts/webhook/prometheus", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["received"] == 3
    assert data["processed"] == 3
    assert data["results"][0]["status"] == "processed"
    assert data["results"][1]["status"] == "skipped"
    assert data["results"][2]["status"] == "processed"


def test_alert_with_missing_status_defaults_to_firing(client):
    payload = {
        "alerts": [
            {
                "labels": {"__name__": "no_status"},
                "annotations": {},
            }
        ]
    }
    resp = client.post("/api/v1/alerts/webhook/prometheus", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["results"][0]["status"] == "processed"
