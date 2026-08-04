# -*- coding: utf-8 -*-
"""Real endpoint tests for api/itsm_router.py."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.itsm_router import router


class _FakeAsyncClient:
    """A fake httpx.AsyncClient that returns a controlled response."""

    def __init__(self, status_code: int = 201, json_data=None, text: str = ""):
        self.status_code = status_code
        self.json_data = json_data or {}
        self.text = text
        self.post = AsyncMock(side_effect=self._respond)
        self.put = AsyncMock(side_effect=self._respond)

    async def _respond(self, *args, **kwargs):
        mock_resp = MagicMock()
        mock_resp.status_code = self.status_code
        mock_resp.text = self.text
        mock_resp.json = MagicMock(return_value=self.json_data)
        return mock_resp

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


class TestITSMCreateIncident:
    """Tests POST /api/itsm/incident."""

    def test_create_servicenow_no_config(self, client, monkeypatch):
        monkeypatch.setattr("api.itsm_router.SERVICE_NOW_URL", None)
        monkeypatch.setattr("api.itsm_router.SERVICE_NOW_TOKEN", None)
        response = client.post("/api/itsm/incident?provider=servicenow", json={"title": "x"})
        assert response.status_code == 500
        assert "ServiceNow" in response.json()["detail"]

    def test_create_jira_no_config(self, client, monkeypatch):
        monkeypatch.setattr("api.itsm_router.JIRA_URL", None)
        monkeypatch.setattr("api.itsm_router.JIRA_TOKEN", None)
        response = client.post("/api/itsm/incident?provider=jira", json={"title": "x"})
        assert response.status_code == 500
        assert "Jira" in response.json()["detail"]

    def test_create_unsupported_provider(self, client):
        response = client.post("/api/itsm/incident?provider=foo", json={"title": "x"})
        assert response.status_code == 400

    def test_create_servicenow_remote_success(self, client, monkeypatch):
        monkeypatch.setattr("api.itsm_router.SERVICE_NOW_URL", "https://snow.example")
        monkeypatch.setattr("api.itsm_router.SERVICE_NOW_TOKEN", "tok")
        fake = _FakeAsyncClient(201, {"result": {"sys_id": "SN-123"}})
        with patch("httpx.AsyncClient", return_value=fake):
            response = client.post("/api/itsm/incident?provider=servicenow", json={"summary": "x"})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "created"
        assert data["incident_id"] == "SN-123"
        assert data["provider"] == "servicenow"

    def test_create_jira_remote_success(self, client, monkeypatch):
        monkeypatch.setattr("api.itsm_router.JIRA_URL", "https://jira.example")
        monkeypatch.setattr("api.itsm_router.JIRA_TOKEN", "tok")
        fake = _FakeAsyncClient(201, {"key": "PROJ-1"})
        with patch("httpx.AsyncClient", return_value=fake):
            response = client.post("/api/itsm/incident?provider=jira", json={"project_key": "PROJ"})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "created"
        assert data["incident_id"] == "PROJ-1"
        assert data["provider"] == "jira"

    def test_create_remote_failure_falls_back_local(self, client, monkeypatch):
        monkeypatch.setattr("api.itsm_router.SERVICE_NOW_URL", "https://snow.example")
        monkeypatch.setattr("api.itsm_router.SERVICE_NOW_TOKEN", "tok")
        fake = _FakeAsyncClient(500, {}, "fail")
        with patch("httpx.AsyncClient", return_value=fake):
            response = client.post("/api/itsm/incident?provider=servicenow", json={"summary": "x"})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "created"
        assert data["provider"] == "servicenow"
        assert "本地记录" in data["message"]


class TestITSMResolveIncident:
    """Tests PATCH /api/itsm/incident/{incident_id}."""

    def test_resolve_servicenow_no_config(self, client, monkeypatch):
        monkeypatch.setattr("api.itsm_router.SERVICE_NOW_URL", None)
        monkeypatch.setattr("api.itsm_router.SERVICE_NOW_TOKEN", None)
        response = client.patch("/api/itsm/incident/INC123?provider=servicenow")
        assert response.status_code == 500
        assert "ServiceNow" in response.json()["detail"]

    def test_resolve_jira_no_config(self, client, monkeypatch):
        monkeypatch.setattr("api.itsm_router.JIRA_URL", None)
        monkeypatch.setattr("api.itsm_router.JIRA_TOKEN", None)
        response = client.patch("/api/itsm/incident/INC123?provider=jira")
        assert response.status_code == 500
        assert "Jira" in response.json()["detail"]

    def test_resolve_unsupported_provider(self, client):
        response = client.patch("/api/itsm/incident/INC123?provider=foo")
        assert response.status_code == 400

    def test_resolve_servicenow_remote_success(self, client, monkeypatch):
        monkeypatch.setattr("api.itsm_router.SERVICE_NOW_URL", "https://snow.example")
        monkeypatch.setattr("api.itsm_router.SERVICE_NOW_TOKEN", "tok")
        fake = _FakeAsyncClient(204, {})
        with patch("httpx.AsyncClient", return_value=fake):
            response = client.patch("/api/itsm/incident/INC123?provider=servicenow")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "resolved"
        assert data["incident_id"] == "INC123"

    def test_resolve_jira_remote_success(self, client, monkeypatch):
        monkeypatch.setattr("api.itsm_router.JIRA_URL", "https://jira.example")
        monkeypatch.setattr("api.itsm_router.JIRA_TOKEN", "tok")
        fake = _FakeAsyncClient(204, {})
        with patch("httpx.AsyncClient", return_value=fake):
            response = client.patch("/api/itsm/incident/INC123?provider=jira")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "resolved"
        assert data["incident_id"] == "INC123"

    def test_resolve_remote_failure_falls_back_local(self, client, monkeypatch):
        monkeypatch.setattr("api.itsm_router.SERVICE_NOW_URL", "https://snow.example")
        monkeypatch.setattr("api.itsm_router.SERVICE_NOW_TOKEN", "tok")
        fake = _FakeAsyncClient(503, {}, "fail")
        with patch("httpx.AsyncClient", return_value=fake):
            response = client.patch("/api/itsm/incident/INC123?provider=servicenow")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "resolved"
        assert "本地记录" in data["message"]
