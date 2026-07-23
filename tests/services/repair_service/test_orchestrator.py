# -*- coding: utf-8 -*-
"""Tests for repair orchestrator and saga integration."""

from __future__ import annotations

import pytest

from services.repair_service.orchestrator import app as orchestrator_app


class TestOrchestrator:
    @pytest.fixture(scope="module")
    def client(self):
        from fastapi.testclient import TestClient

        with TestClient(orchestrator_app) as c:
            yield c

    def test_health(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["service"] == "repair-orchestrator"

    def test_create_and_get_repair(self, client):
        request = {
            "alert_id": "ALERT-CPU-001",
            "host": "server-01",
            "platform": "linux",
            "metric": "cpu_percent",
            "auto_approve": False,
        }
        response = client.post("/repairs", json=request)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "pending"
        assert "task_id" in data

        response = client.get(f"/repairs/{data['task_id']}")
        assert response.status_code == 200
        assert response.json()["task_id"] == data["task_id"]

    def test_approve_low_risk(self, client):
        request = {
            "alert_id": "ALERT-MEM-002",
            "host": "server-02",
            "platform": "linux",
            "metric": "memory_percent",
            "auto_approve": True,
        }
        response = client.post("/repairs", json=request)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "approved"

    def test_approve_manual(self, client):
        request = {
            "alert_id": "ALERT-CPU-003",
            "host": "server-03",
            "platform": "linux",
            "metric": "cpu_percent",
            "auto_approve": False,
        }
        response = client.post("/repairs", json=request)
        data = response.json()
        response = client.post(f"/repairs/{data['task_id']}/approve")
        assert response.status_code == 200
        result = response.json()
        # Pipeline may complete or end with rollback due to verifier fallback
        assert result["status"] in ("completed", "verified", "rollbacked")

    def test_reject(self, client):
        request = {
            "alert_id": "ALERT-CPU-004",
            "host": "server-04",
            "platform": "linux",
            "metric": "cpu_percent",
        }
        response = client.post("/repairs", json=request)
        data = response.json()
        response = client.post(f"/repairs/{data['task_id']}/reject")
        assert response.status_code == 200
        assert response.json()["status"] == "completed"

    def test_list_repairs(self, client):
        response = client.get("/repairs")
        assert response.status_code == 200
        assert "items" in response.json()

    def test_metrics(self, client):
        response = client.get("/metrics")
        assert response.status_code == 200
        assert "repair" in response.text

    def test_saga_endpoint(self, client):
        request = {
            "alert_id": "ALERT-SAGA-001",
            "host": "server-saga",
            "platform": "linux",
            "metric": "memory_percent",
            "auto_approve": True,
        }
        response = client.post("/repairs", json=request)
        task_id = response.json()["task_id"]

        response = client.post(f"/repairs/{task_id}/saga")
        assert response.status_code == 200
        result = response.json()
        assert "saga_id" in result

    def test_approve_nonexistent(self, client):
        response = client.post("/repairs/nonexistent/approve")
        assert response.status_code == 200
        assert response.json().get("error") == "task not found"

    def test_reject_nonexistent(self, client):
        response = client.post("/repairs/nonexistent/reject")
        assert response.status_code == 200
        assert response.json().get("error") == "task not found"

    def test_high_risk_not_auto_approved(self, client):
        request = {
            "alert_id": "ALERT-SVC-005",
            "host": "server-05",
            "platform": "linux",
            "metric": "service_down",
            "auto_approve": True,
        }
        response = client.post("/repairs", json=request)
        assert response.status_code == 200
        assert response.json()["status"] == "pending"
