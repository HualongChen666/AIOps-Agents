# -*- coding: utf-8 -*-
"""Real branch-coverage tests for api/itsm_router.py.

A small FastAPI app mounts the ITSM router and a local in-memory HTTP server
returns real request/response payloads for the ServiceNow and Jira branches.
No external ITSM services are contacted.
"""
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import api.itsm_router as itsm_mod


class _InMemoryITSMServer(HTTPServer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.response_status = 201
        self.response_body = {}

    @property
    def url(self):
        host, port = self.server_address
        return f"http://{host}:{port}"


class _ITSMHandler(BaseHTTPRequestHandler):
    def log_message(self, *args, **kwargs):
        pass

    def _send_json(self):
        body = json.dumps(self.server.response_body).encode("utf-8")
        self.send_response(self.server.response_status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_empty(self):
        self.send_response(self.server.response_status)
        self.end_headers()

    def do_POST(self):
        if self.path.startswith("/rest/api/2/issue"):
            if self.server.response_status in (204,):
                self._send_empty()
            else:
                self._send_json()
        elif self.path.startswith("/api/now/table/incident"):
            self._send_json()
        else:
            self.send_error(404)

    def do_PUT(self):
        if self.path.startswith("/api/now/table/incident/"):
            if self.server.response_status in (204,):
                self._send_empty()
            else:
                self._send_json()
        else:
            self.send_error(404)


@pytest.fixture(scope="module", autouse=True)
def ensure_database():
    """Override the root conftest DB setup; this module exercises the ITSM router only."""
    yield


@pytest.fixture
def itsm_server():
    server = _InMemoryITSMServer(("127.0.0.1", 0), _ITSMHandler)
    server.response_status = 201
    server.response_body = {}
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(itsm_mod.router)
    with TestClient(app) as c:
        yield c


def _set_jira_config(monkeypatch, server_url):
    monkeypatch.setattr(itsm_mod, "JIRA_URL", server_url)
    monkeypatch.setattr(itsm_mod, "JIRA_TOKEN", "test-jira-token")


def _set_snow_config(monkeypatch, server_url):
    monkeypatch.setattr(itsm_mod, "SERVICE_NOW_URL", server_url)
    monkeypatch.setattr(itsm_mod, "SERVICE_NOW_TOKEN", "test-snow-token")


# ---------------------------------------------------------------------------
# Ticket creation branches
# ---------------------------------------------------------------------------
def test_create_incident_jira_success(client, itsm_server, monkeypatch):
    itsm_server.response_status = 201
    itsm_server.response_body = {"key": "OPS-1"}
    _set_jira_config(monkeypatch, itsm_server.url)
    resp = client.post(
        "/api/itsm/incident",
        params={"provider": "jira"},
        json={
            "project_key": "OPS",
            "summary": "Disk full",
            "description": "test description",
            "issue_type": "Bug",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "created"
    assert data["provider"] == "jira"
    assert data["incident_id"] == "OPS-1"


def test_create_incident_servicenow_success(client, itsm_server, monkeypatch):
    itsm_server.response_status = 201
    itsm_server.response_body = {"result": {"sys_id": "snow-123"}}
    _set_snow_config(monkeypatch, itsm_server.url)
    resp = client.post(
        "/api/itsm/incident",
        params={"provider": "servicenow"},
        json={"summary": "Disk full", "description": "test", "urgency": "1"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "created"
    assert data["provider"] == "servicenow"
    assert data["incident_id"] == "snow-123"


def test_create_incident_unsupported_provider(client):
    resp = client.post(
        "/api/itsm/incident",
        params={"provider": "unknown"},
        json={"summary": "x"},
    )
    assert resp.status_code == 400
    assert "Unsupported ITSM provider" in resp.text


def test_create_incident_jira_missing_config(client, monkeypatch):
    monkeypatch.setattr(itsm_mod, "JIRA_URL", "")
    monkeypatch.setattr(itsm_mod, "JIRA_TOKEN", "")
    resp = client.post(
        "/api/itsm/incident",
        params={"provider": "jira"},
        json={"summary": "x"},
    )
    assert resp.status_code == 500
    assert "Jira" in resp.text


def test_create_incident_servicenow_missing_config(client, monkeypatch):
    monkeypatch.setattr(itsm_mod, "SERVICE_NOW_URL", "")
    monkeypatch.setattr(itsm_mod, "SERVICE_NOW_TOKEN", "")
    resp = client.post(
        "/api/itsm/incident",
        params={"provider": "servicenow"},
        json={"summary": "x"},
    )
    assert resp.status_code == 500
    assert "ServiceNow" in resp.text


def test_create_incident_jira_non_2xx(client, itsm_server, monkeypatch):
    itsm_server.response_status = 500
    itsm_server.response_body = {"error": "Jira is down"}
    _set_jira_config(monkeypatch, itsm_server.url)
    resp = client.post(
        "/api/itsm/incident",
        params={"provider": "jira"},
        json={"summary": "x"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "created"
    assert data["provider"] == "jira"
    assert "本地记录" in data["message"] or "local" in data["message"].lower()


def test_create_incident_servicenow_non_2xx(client, itsm_server, monkeypatch):
    itsm_server.response_status = 500
    itsm_server.response_body = {"error": "ServiceNow is down"}
    _set_snow_config(monkeypatch, itsm_server.url)
    resp = client.post(
        "/api/itsm/incident",
        params={"provider": "servicenow"},
        json={"summary": "x"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "created"
    assert data["provider"] == "servicenow"
    assert "本地记录" in data["message"] or "local" in data["message"].lower()


def test_create_incident_connection_refused(client, monkeypatch):
    _set_jira_config(monkeypatch, "http://127.0.0.1:1")
    resp = client.post(
        "/api/itsm/incident",
        params={"provider": "jira"},
        json={"summary": "x"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "created"
    assert data["provider"] == "jira"
    assert "本地记录" in data["message"] or "local" in data["message"].lower()


def test_create_incident_httpx_not_available(client, itsm_server, monkeypatch):
    _set_jira_config(monkeypatch, itsm_server.url)
    monkeypatch.setitem(sys.modules, "httpx", None)
    resp = client.post(
        "/api/itsm/incident",
        params={"provider": "jira"},
        json={"summary": "x"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "created"
    assert data["provider"] == "jira"
    assert "本地记录" in data["message"] or "local" in data["message"].lower()


# ---------------------------------------------------------------------------
# Ticket update / resolve branches
# ---------------------------------------------------------------------------
def test_resolve_incident_jira_success(client, itsm_server, monkeypatch):
    itsm_server.response_status = 204
    itsm_server.response_body = {}
    _set_jira_config(monkeypatch, itsm_server.url)
    resp = client.patch(
        "/api/itsm/incident/OPS-42",
        params={"provider": "jira"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "resolved"
    assert data["incident_id"] == "OPS-42"
    assert data["provider"] == "jira"


def test_resolve_incident_servicenow_success(client, itsm_server, monkeypatch):
    itsm_server.response_status = 200
    itsm_server.response_body = {}
    _set_snow_config(monkeypatch, itsm_server.url)
    resp = client.patch(
        "/api/itsm/incident/snow-123",
        params={"provider": "servicenow"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "resolved"
    assert data["incident_id"] == "snow-123"
    assert data["provider"] == "servicenow"


def test_resolve_incident_unsupported_provider(client):
    resp = client.patch(
        "/api/itsm/incident/x",
        params={"provider": "bad"},
    )
    assert resp.status_code == 400
    assert "Unsupported ITSM provider" in resp.text


def test_resolve_incident_jira_missing_config(client, monkeypatch):
    monkeypatch.setattr(itsm_mod, "JIRA_URL", "")
    monkeypatch.setattr(itsm_mod, "JIRA_TOKEN", "")
    resp = client.patch(
        "/api/itsm/incident/OPS-42",
        params={"provider": "jira"},
    )
    assert resp.status_code == 500
    assert "Jira" in resp.text


def test_resolve_incident_servicenow_missing_config(client, monkeypatch):
    monkeypatch.setattr(itsm_mod, "SERVICE_NOW_URL", "")
    monkeypatch.setattr(itsm_mod, "SERVICE_NOW_TOKEN", "")
    resp = client.patch(
        "/api/itsm/incident/snow-123",
        params={"provider": "servicenow"},
    )
    assert resp.status_code == 500
    assert "ServiceNow" in resp.text


def test_resolve_incident_jira_non_2xx(client, itsm_server, monkeypatch):
    itsm_server.response_status = 500
    itsm_server.response_body = {"error": "transition failed"}
    _set_jira_config(monkeypatch, itsm_server.url)
    resp = client.patch(
        "/api/itsm/incident/OPS-42",
        params={"provider": "jira"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "resolved"
    assert "本地记录" in data["message"] or "local" in data["message"].lower()


def test_resolve_incident_servicenow_non_2xx(client, itsm_server, monkeypatch):
    itsm_server.response_status = 500
    itsm_server.response_body = {"error": "update failed"}
    _set_snow_config(monkeypatch, itsm_server.url)
    resp = client.patch(
        "/api/itsm/incident/snow-123",
        params={"provider": "servicenow"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "resolved"
    assert "本地记录" in data["message"] or "local" in data["message"].lower()


def test_resolve_incident_connection_refused(client, monkeypatch):
    _set_snow_config(monkeypatch, "http://127.0.0.1:1")
    resp = client.patch(
        "/api/itsm/incident/snow-123",
        params={"provider": "servicenow"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "resolved"
    assert data["provider"] == "servicenow"
    assert "本地记录" in data["message"] or "local" in data["message"].lower()


def test_resolve_incident_httpx_not_available(client, monkeypatch):
    _set_snow_config(monkeypatch, "http://127.0.0.1:1")
    monkeypatch.setitem(sys.modules, "httpx", None)
    resp = client.patch(
        "/api/itsm/incident/snow-123",
        params={"provider": "servicenow"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "resolved"
    assert data["provider"] == "servicenow"
    assert "本地记录" in data["message"] or "local" in data["message"].lower()
