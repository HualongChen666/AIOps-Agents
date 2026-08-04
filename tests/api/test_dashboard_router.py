# -*- coding: utf-8 -*-
"""Real endpoint tests for api/dashboard_router.py."""

import sys
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Mock authentication dependency before importing the real router
sys.modules["core.authentication"] = type(sys)("core.authentication")
sys.modules["core.authentication"].role_required = lambda role: lambda: {"role": role}

from api.dashboard_router import router  # noqa: E402


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr("config.LINUX_HOSTS", ["host1", "host2"])
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


class TestDashboardRouter:
    """Tests the real /dashboard/summary endpoint."""

    def test_summary_success(self, client, monkeypatch):
        """DB helpers return real numbers: summary is aggregated correctly."""
        monkeypatch.setattr("core.db_engine.async_count_alerts", AsyncMock(return_value=5))
        monkeypatch.setattr(
            "core.db_engine.async_get_all_pending_approvals",
            AsyncMock(return_value=["a", "b"]),
        )
        response = client.get("/dashboard/summary")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["total_hosts"] == 2
        assert data["healthy_hosts"] == 2
        assert data["total_alerts"] == 5
        assert data["pending_repairs"] == 2
        assert data["message"] == "Dashboard default_value"

    def test_summary_db_unavailable(self, client):
        """When DB helpers cannot be used, the endpoint still returns a valid summary."""
        response = client.get("/dashboard/summary")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["total_hosts"] == 2
        assert data["message"] == "Dashboard default_value"
