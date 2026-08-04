# -*- coding: utf-8 -*-
"""Real endpoint tests for core/mcp_server.py APIRouter."""

from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from core.mcp_server import router


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


class TestMcpServerRouter:
    """Test the five MCP server JSON-RPC style endpoints."""

    def test_get_host_health_success(self, client, monkeypatch):
        monkeypatch.setattr(
            "core.mcp_server.get_host_health", AsyncMock(return_value={"status": "healthy"})
        )
        response = client.post("/mcp/get_host_health", json={"host_id": "host-1"})
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_get_host_health_error(self, client, monkeypatch):
        monkeypatch.setattr(
            "core.mcp_server.get_host_health", AsyncMock(side_effect=RuntimeError("boom"))
        )
        response = client.post("/mcp/get_host_health", json={"host_id": "host-1"})
        assert response.status_code == 500

    def test_trigger_repair_with_hitl_success(self, client, monkeypatch):
        monkeypatch.setattr(
            "core.mcp_server.trigger_repair_with_hitl",
            AsyncMock(return_value={"triggered": True}),
        )
        response = client.post(
            "/mcp/trigger_repair_with_hitl",
            json={"alert_id": "a1", "user": "admin", "comment": "go"},
        )
        assert response.status_code == 200
        assert response.json()["triggered"] is True

    def test_search_incident_history_success(self, client, monkeypatch):
        monkeypatch.setattr(
            "core.mcp_server.search_incident_history",
            AsyncMock(return_value=[{"id": "i1"}]),
        )
        response = client.post("/mcp/search_incident_history", json={"query": "cpu", "limit": 5})
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_metrics_success(self, client, monkeypatch):
        monkeypatch.setattr(
            "core.mcp_server.get_metrics", AsyncMock(return_value={"cpu": 12.3})
        )
        response = client.post(
            "/mcp/get_metrics", json={"host_id": "host-1", "metrics": ["cpu"]}
        )
        assert response.status_code == 200
        assert response.json()["cpu"] == 12.3

    def test_approve_repair_success(self, client, monkeypatch):
        monkeypatch.setattr(
            "core.mcp_server.approve_repair", AsyncMock(return_value={"approved": True})
        )
        response = client.post(
            "/mcp/approve_repair",
            json={"repair_id": "r1", "approved": True, "comment": "ok"},
        )
        assert response.status_code == 200
        assert response.json()["approved"] is True
