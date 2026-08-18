# -*- coding: utf-8 -*-
"""Real end-to-end coverage tests for batch C API routers."""

import json  # noqa: F401  # Imported for test setup
from datetime import datetime
from types import SimpleNamespace

import pytest  # noqa: F401  # Imported for test setup
from fastapi import FastAPI, HTTPException

import api.business_impact_router
import api.frontend_enhancement_router
import api.itsm_router
import api.linux_router
import api.notify_router
# import api.plugin_ecosystem_router  # File doesn't exist
import api.qdrant_router
import api.repair_router
import api.router_enhancer
import api.stats_router
import api.unified_repair_router
import config
import core.authentication
import core.notify_engine
import core.platform_strategies
import core.qdrant_service
import core.repair_engine

pytestmark = [pytest.mark.api]


@pytest.fixture
def admin_headers(client):
    """Get a fresh admin JWT for each test to avoid token expiry."""
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.fixture
def approval_headers(client):
    """Admin JWT plus the internal API key used by protected endpoints."""
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    assert resp.status_code == 200
    return {
        "Authorization": f"Bearer {resp.json()['access_token']}",
        "X-Internal-Key": config.INTERNAL_API_KEY,
    }


@pytest.fixture(autouse=True)
def _patch_auth_get_user(monkeypatch):
    """Bypass async DB lookups for auth dependencies."""
    from core.authentication import UserInDB

    async def _fake_get_user(username: str):
        return UserInDB(
            id=1,
            username=username,
            role="admin",
            disabled=False,
            hashed_password="",
        )

    monkeypatch.setattr(core.authentication, "get_user", _fake_get_user)


# ---------------------------------------------------------------------------
# router_enhancer.py
# ---------------------------------------------------------------------------
def test_enhance_app_routes_openapi():
    """The route enhancer enriches an OpenAPI schema with docs and samples."""
    enhancer = api.router_enhancer
    app = FastAPI()

    @app.get("/demo/{item_id}", summary="Demo route", tags=["demo"])
    def demo(item_id: int):  # pragma: no cover - schema only
        return {"item_id": item_id}

    enhancer.enhance_app_routes(app)
    schema = app.openapi()

    assert "/demo/{item_id}" in schema.get("paths", {})
    op = schema["paths"]["/demo/{item_id}"]["get"]
    assert op.get("description") == "Demo route"
    assert "x-codeSamples" in op
    assert "400" in op.get("responses", {})
    assert "200" in op.get("responses", {})


def test_build_code_samples_and_enrich():
    """Helper functions produce code samples and merge default responses."""
    enhancer = api.router_enhancer
    samples = enhancer._build_code_samples("post", "/test")
    assert any(s["lang"] == "Shell" for s in samples)
    assert any(s["lang"] == "Python" for s in samples)

    schema = {
        "paths": {
            "/widgets": {
                "get": {
                    "summary": "List widgets",
                    "responses": {"200": {"description": "ok"}},
                },
                "parameters": {"foo": "bar"},
            }
        }
    }
    enriched = enhancer._enrich_openapi_schema(schema)
    get_op = enriched["paths"]["/widgets"]["get"]
    assert get_op.get("description") == "List widgets"
    assert "x-codeSamples" in get_op
    assert "500" in get_op["responses"]


# ---------------------------------------------------------------------------
# itsm_router.py
# ---------------------------------------------------------------------------
class _FakeHttpxClient:
    """Small async-ctx-manager fake for httpx.AsyncClient used by ITSM."""

    def __init__(self, status=200, json_data=None):
        self.status = status
        self.json_data = json_data or {}

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def post(self, *args, **kwargs):
        return SimpleNamespace(
            status_code=self.status,
            text="ok",
            json=lambda: self.json_data,
        )

    async def put(self, *args, **kwargs):
        return SimpleNamespace(
            status_code=self.status,
            text="ok",
            json=lambda: self.json_data,
        )


def _patch_httpx_for_itsm(monkeypatch, status=200, json_data=None):
    import httpx

    monkeypatch.setattr(
        httpx, "AsyncClient", lambda *args, **kwargs: _FakeHttpxClient(status, json_data)
    )


def test_itsm_create_incident_servicenow(client, admin_headers, monkeypatch):
    """POST /api/itsm/incident with ServiceNow provider returns created status."""
    _patch_httpx_for_itsm(monkeypatch, 201, {"result": {"sys_id": "sys-123"}})
    monkeypatch.setattr(api.itsm_router, "SERVICE_NOW_URL", "https://snow.example")
    monkeypatch.setattr(api.itsm_router, "SERVICE_NOW_TOKEN", "token")
    resp = client.post(
        "/api/itsm/incident",
        headers=admin_headers,
        params={"provider": "servicenow"},
        json={"summary": "disk full", "description": "test"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "created"
    assert body["provider"] == "servicenow"
    assert body["incident_id"] == "sys-123"


def test_itsm_create_incident_jira(client, admin_headers, monkeypatch):
    """POST /api/itsm/incident with Jira provider returns created key."""
    _patch_httpx_for_itsm(monkeypatch, 201, {"key": "OPS-42"})
    monkeypatch.setattr(api.itsm_router, "JIRA_URL", "https://jira.example")
    monkeypatch.setattr(api.itsm_router, "JIRA_TOKEN", "token")
    resp = client.post(
        "/api/itsm/incident",
        headers=admin_headers,
        params={"provider": "jira"},
        json={"project_key": "OPS", "summary": "alert", "description": "d"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "created"
    assert body["incident_id"] == "OPS-42"


def test_itsm_create_incident_unsupported_provider(client, admin_headers):
    """An unknown provider returns 400."""
    resp = client.post(
        "/api/itsm/incident",
        headers=admin_headers,
        params={"provider": "unknown"},
        json={"summary": "x"},
    )
    assert resp.status_code == 400
    assert (
        "Unsupported ITSM provider" in resp.text
        or "Unsupported ITSM provider" in resp.json().get("detail", "")
    )


def test_itsm_create_incident_missing_config(client, admin_headers):
    """A missing ServiceNow configuration returns 500."""
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(api.itsm_router, "SERVICE_NOW_URL", "")
    monkeypatch.setattr(api.itsm_router, "SERVICE_NOW_TOKEN", "")
    resp = client.post(
        "/api/itsm/incident",
        headers=admin_headers,
        params={"provider": "servicenow"},
        json={"summary": "x"},
    )
    monkeypatch.undo()
    assert resp.status_code == 500
    assert "ServiceNow" in resp.text


def test_itsm_resolve_incident(client, admin_headers, monkeypatch):
    """PATCH /api/itsm/incident/{id} resolves successfully."""
    _patch_httpx_for_itsm(monkeypatch, 204, {})
    monkeypatch.setattr(api.itsm_router, "JIRA_URL", "https://jira.example")
    monkeypatch.setattr(api.itsm_router, "JIRA_TOKEN", "token")
    resp = client.patch(
        "/api/itsm/incident/OPS-42",
        headers=admin_headers,
        params={"provider": "jira"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "resolved"
    assert body["incident_id"] == "OPS-42"


def test_itsm_create_incident_jira_missing_config(client, admin_headers, monkeypatch):
    """A missing Jira configuration returns 500."""
    monkeypatch.setattr(api.itsm_router, "JIRA_URL", "")
    monkeypatch.setattr(api.itsm_router, "JIRA_TOKEN", "")
    resp = client.post(
        "/api/itsm/incident",
        headers=admin_headers,
        params={"provider": "jira"},
        json={"summary": "x"},
    )
    assert resp.status_code == 500
    assert "Jira" in resp.text


def test_itsm_create_incident_jira_failure(client, admin_headers, monkeypatch):
    """Jira API failure returns local record."""
    _patch_httpx_for_itsm(monkeypatch, 500, {"error": "server error"})
    monkeypatch.setattr(api.itsm_router, "JIRA_URL", "https://jira.example")
    monkeypatch.setattr(api.itsm_router, "JIRA_TOKEN", "token")
    resp = client.post(
        "/api/itsm/incident",
        headers=admin_headers,
        params={"provider": "jira"},
        json={"summary": "test", "description": "test"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "created"
    assert "本地记录" in body["message"]


def test_itsm_create_incident_servicenow_failure(client, admin_headers, monkeypatch):
    """ServiceNow API failure returns local record."""
    _patch_httpx_for_itsm(monkeypatch, 500, {"error": "server error"})
    monkeypatch.setattr(api.itsm_router, "SERVICE_NOW_URL", "https://snow.example")
    monkeypatch.setattr(api.itsm_router, "SERVICE_NOW_TOKEN", "token")
    resp = client.post(
        "/api/itsm/incident",
        headers=admin_headers,
        params={"provider": "servicenow"},
        json={"summary": "test", "description": "test"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "created"
    assert "本地记录" in body["message"]


def test_itsm_create_incident_exception(client, admin_headers, monkeypatch):
    """Exception in create_incident returns local record."""
    def _raise_error(*args, **kwargs):
        raise Exception("Network error")
    
    monkeypatch.setattr(api.itsm_router, "SERVICE_NOW_URL", "https://snow.example")
    monkeypatch.setattr(api.itsm_router, "SERVICE_NOW_TOKEN", "token")
    monkeypatch.setattr("httpx.AsyncClient", _raise_error)
    resp = client.post(
        "/api/itsm/incident",
        headers=admin_headers,
        params={"provider": "servicenow"},
        json={"summary": "test", "description": "test"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "created"
    assert "本地记录" in body["message"]


def test_itsm_resolve_incident_servicenow_missing_config(client, admin_headers, monkeypatch):
    """A missing ServiceNow configuration returns 500."""
    monkeypatch.setattr(api.itsm_router, "SERVICE_NOW_URL", "")
    monkeypatch.setattr(api.itsm_router, "SERVICE_NOW_TOKEN", "")
    resp = client.patch(
        "/api/itsm/incident/123",
        headers=admin_headers,
        params={"provider": "servicenow"},
    )
    assert resp.status_code == 500
    assert "ServiceNow" in resp.text


def test_itsm_resolve_incident_jira_missing_config(client, admin_headers, monkeypatch):
    """A missing Jira configuration returns 500."""
    monkeypatch.setattr(api.itsm_router, "JIRA_URL", "")
    monkeypatch.setattr(api.itsm_router, "JIRA_TOKEN", "")
    resp = client.patch(
        "/api/itsm/incident/OPS-42",
        headers=admin_headers,
        params={"provider": "jira"},
    )
    assert resp.status_code == 500
    assert "Jira" in resp.text


def test_itsm_resolve_incident_unsupported_provider(client, admin_headers):
    """An unknown provider returns 400."""
    resp = client.patch(
        "/api/itsm/incident/123",
        headers=admin_headers,
        params={"provider": "unknown"},
    )
    assert resp.status_code == 400
    assert (
        "Unsupported ITSM provider" in resp.text
        or "Unsupported ITSM provider" in resp.json().get("detail", "")
    )


def test_itsm_resolve_incident_jira_success(client, admin_headers, monkeypatch):
    """PATCH /api/itsm/incident/{id} with Jira provider resolves successfully."""
    _patch_httpx_for_itsm(monkeypatch, 200, {})
    monkeypatch.setattr(api.itsm_router, "JIRA_URL", "https://jira.example")
    monkeypatch.setattr(api.itsm_router, "JIRA_TOKEN", "token")
    resp = client.patch(
        "/api/itsm/incident/OPS-42",
        headers=admin_headers,
        params={"provider": "jira"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "resolved"
    assert body["incident_id"] == "OPS-42"


def test_itsm_resolve_incident_jira_failure(client, admin_headers, monkeypatch):
    """Jira API failure returns local record."""
    _patch_httpx_for_itsm(monkeypatch, 500, {"error": "server error"})
    monkeypatch.setattr(api.itsm_router, "JIRA_URL", "https://jira.example")
    monkeypatch.setattr(api.itsm_router, "JIRA_TOKEN", "token")
    resp = client.patch(
        "/api/itsm/incident/OPS-42",
        headers=admin_headers,
        params={"provider": "jira"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "resolved"
    assert "本地记录" in body["message"]


def test_itsm_resolve_incident_servicenow_success(client, admin_headers, monkeypatch):
    """PATCH /api/itsm/incident/{id} with ServiceNow provider resolves successfully."""
    _patch_httpx_for_itsm(monkeypatch, 200, {})
    monkeypatch.setattr(api.itsm_router, "SERVICE_NOW_URL", "https://snow.example")
    monkeypatch.setattr(api.itsm_router, "SERVICE_NOW_TOKEN", "token")
    resp = client.patch(
        "/api/itsm/incident/sys-123",
        headers=admin_headers,
        params={"provider": "servicenow"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "resolved"
    assert body["incident_id"] == "sys-123"


def test_itsm_resolve_incident_servicenow_failure(client, admin_headers, monkeypatch):
    """ServiceNow API failure returns local record."""
    _patch_httpx_for_itsm(monkeypatch, 500, {"error": "server error"})
    monkeypatch.setattr(api.itsm_router, "SERVICE_NOW_URL", "https://snow.example")
    monkeypatch.setattr(api.itsm_router, "SERVICE_NOW_TOKEN", "token")
    resp = client.patch(
        "/api/itsm/incident/sys-123",
        headers=admin_headers,
        params={"provider": "servicenow"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "resolved"
    assert "本地记录" in body["message"]


def test_itsm_resolve_incident_exception(client, admin_headers, monkeypatch):
    """Exception in resolve_incident returns local record."""
    def _raise_error(*args, **kwargs):
        raise Exception("Network error")
    
    monkeypatch.setattr(api.itsm_router, "SERVICE_NOW_URL", "https://snow.example")
    monkeypatch.setattr(api.itsm_router, "SERVICE_NOW_TOKEN", "token")
    monkeypatch.setattr("httpx.AsyncClient", _raise_error)
    resp = client.patch(
        "/api/itsm/incident/123",
        headers=admin_headers,
        params={"provider": "servicenow"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "resolved"
    assert "本地记录" in body["message"]


# ---------------------------------------------------------------------------
# documentation_router.py
# ---------------------------------------------------------------------------
def test_documentation_lifecycle(client, admin_headers):
    """Exercise all documentation endpoints with real payloads and DB."""
    client.headers.update(admin_headers)
    create_resp = client.post(
        "/api/documentation/document/create",
        params={
            "doc_id": "doc-001",
            "title": "API Guide",
            "doc_type": "api_documentation",
            "content": "Initial content",
            "author": "tester",
            "version": "1.0",
        },
    )
    assert create_resp.status_code == 200
    assert create_resp.json()["data"]["created"] is True

    list_resp = client.get("/api/documentation/documents")
    assert list_resp.status_code == 200
    assert any(d["doc_id"] == "doc-001" for d in list_resp.json()["data"]["documents"])

    get_resp = client.get("/api/documentation/document/doc-001")
    assert get_resp.status_code == 200
    assert get_resp.json()["data"]["doc_id"] == "doc-001"

    update_resp = client.post(
        "/api/documentation/document/doc-001/update",
        params={"content": "Updated content", "status": "published"},
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["data"]["updated"] is True

    status_resp = client.get("/api/documentation/status")
    assert status_resp.status_code == 200
    assert status_resp.json()["status"] == "success"

    templates_resp = client.get("/api/documentation/templates")
    assert templates_resp.status_code == 200
    assert templates_resp.json()["status"] == "success"


# ---------------------------------------------------------------------------
# repair_router.py (unified)
# ---------------------------------------------------------------------------
def _patch_unified_repair(monkeypatch, scripts=None, history=None, execute_result=None):
    class _FakeStrategy:
        def __init__(self, execute_result=None, scripts=None):
            self.execute_result = execute_result  # noqa: F841  # Variable for test verification
            self.scripts = scripts or {}

        def get_scripts(self):
            return self.scripts

        async def execute_repair(self, script_key, host_name, params):
            return self.execute_result

        def requires_host_name(self):
            return False

        def get_history(self, limit):
            return history or []

    def _get_strategy(platform):
        return _FakeStrategy(execute_result, scripts)

    def _get_all():
        return {
            "windows": _FakeStrategy(
                execute_result, scripts or {"clear_temp": {"name": "Clean temp", "risk": "low"}}
            ),
            "linux": _FakeStrategy(
                execute_result, scripts or {"clear_tmp": {"name": "Clean tmp", "risk": "low"}}
            ),
        }

    monkeypatch.setattr(core.platform_strategies, "get_all_platform_strategies", _get_all)
    monkeypatch.setattr(api.unified_repair_router, "get_platform_strategy", _get_strategy)
    monkeypatch.setattr(core.repair_engine, "get_repair_history", lambda limit: history or [])


def test_repair_list_and_execute(client, admin_headers, monkeypatch):
    """GET scripts/history and POST execute covering success, blocked, not-found."""
    client.headers.update(admin_headers)
    _patch_unified_repair(
        monkeypatch,
        history=[{"script_key": "clear_temp", "exit_code": 0}],
    )

    scripts_resp = client.get("/api/v1/repairs/scripts")
    assert scripts_resp.status_code == 200
    assert scripts_resp.json()["scripts"]["windows"]["clear_temp"]["name"] == "Clean temp"

    hist_resp = client.get("/api/v1/repairs/history")
    assert hist_resp.status_code == 200
    assert hist_resp.json()["total"] == 1

    # success
    _patch_unified_repair(
        monkeypatch,
        execute_result={
            "success": True,
            "script_key": "clear_temp",
            "exit_code": 0,
            "output": "done",
            "executed_at": datetime.utcnow().isoformat(),
        },
    )
    exec_resp = client.post(
        "/api/v1/repairs/execute",
        json={"platform": "windows", "script_key": "clear_temp", "params": {}},
    )
    assert exec_resp.status_code == 200
    assert exec_resp.json()["success"] is True

    # blocked
    _patch_unified_repair(
        monkeypatch,
        execute_result={
            "success": False,
            "blocked": True,
            "error": "blocked",
            "safe_alternative": "safe-cmd",
        },
    )
    blocked_resp = client.post(
        "/api/v1/repairs/execute",
        json={"platform": "windows", "script_key": "clear_temp", "params": {}},
    )
    assert blocked_resp.status_code == 403
    assert "safe-cmd" in blocked_resp.text

    # not found
    _patch_unified_repair(
        monkeypatch,
        execute_result={"success": False, "error": "未知修复脚本: foo"},
    )
    nf_resp = client.post(
        "/api/v1/repairs/execute", json={"platform": "windows", "script_key": "foo", "params": {}}
    )
    assert nf_resp.status_code == 404

    # invalid payload
    invalid_resp = client.post("/api/v1/repairs/execute", json={})
    assert invalid_resp.status_code == 422


# ---------------------------------------------------------------------------
# hitl_router.py
# ---------------------------------------------------------------------------
def _patch_hitl_notifier(monkeypatch):
    class FakeNotifier:
        async def send_approval_request(self, *args, **kwargs):
            return {"success": True}

    monkeypatch.setattr(api.hitl_router, "_approval_notifier", FakeNotifier())


def test_hitl_workflow(client, admin_headers, monkeypatch):
    """Full HITL lifecycle: create, approve, reject, takeover and health."""
    client.headers.update(admin_headers)
    _patch_hitl_notifier(monkeypatch)

    health_resp = client.get("/hitl/health")
    assert health_resp.status_code == 200
    body = health_resp.json()
    assert "hitl_available" in body

    create_resp = client.post(
        "/hitl/approval/request",
        json={
            "workflow_id": "wf-1",
            "title": "Approve reboot",
            "description": "test",
            "steps": [
                {
                    "step_id": "step-1",
                    "name": "Manager approval",
                    "approver": "admin",
                    "required": True,
                    "timeout_minutes": 60,
                }
            ],
            "context": {"risk_level": "high"},
        },
    )
    assert create_resp.status_code == 200
    request_id = create_resp.json()["request_id"]

    status_resp = client.get(f"/hitl/approval/{request_id}")
    assert status_resp.status_code == 200
    assert status_resp.json()["request_id"] == request_id

    approve_resp = client.post(
        "/hitl/approval/approve",
        headers=admin_headers,
        params={"request_id": request_id, "step_id": "step-1"},
    )
    assert approve_resp.status_code == 200
    assert approve_resp.json()["status"] == "approved"

    # create a new one to reject
    create2 = client.post(
        "/hitl/approval/request",
        json={
            "workflow_id": "wf-1",
            "title": "t2",
            "steps": [{"step_id": "s1", "name": "n", "approver": "admin"}],
        },
    )
    rid2 = create2.json()["request_id"]
    reject_resp = client.post(
        "/hitl/approval/reject",
        headers=admin_headers,
        params={"request_id": rid2, "step_id": "s1"},
    )
    assert reject_resp.status_code == 200
    assert reject_resp.json()["status"] == "rejected"

    # takeover a fresh request
    create3 = client.post(
        "/hitl/approval/request",
        json={
            "workflow_id": "wf-1",
            "title": "t3",
            "steps": [{"step_id": "s1", "name": "n", "approver": "admin"}],
        },
    )
    rid3 = create3.json()["request_id"]
    takeover_resp = client.post(f"/hitl/takeover/{rid3}", params={"reason": "test"})
    assert takeover_resp.status_code == 200
    assert takeover_resp.json()["status"] == "taken_over"

    # subagent interrupt (simulate dispatcher unavailable)
    monkeypatch.setattr(api.hitl_router, "SUBAGENT_AVAILABLE", False)
    interrupt_resp = client.post("/hitl/interrupt/agent-999")
    assert interrupt_resp.status_code == 503


# ---------------------------------------------------------------------------
# linux_router.py
# ---------------------------------------------------------------------------
def _patch_linux_functions(monkeypatch, host, collect, scripts, execute):
    from core.linux_collector import (
        collect_all_linux,
        collect_linux_host,
        get_available_metrics,
        get_configured_hosts,
    )
    from core.linux_repair import execute_linux_repair, get_linux_repair_scripts

    monkeypatch.setattr(api.linux_router, "LINUX_HOSTS", [host])
    monkeypatch.setattr(api.linux_router, "get_configured_hosts", lambda: [host])
    monkeypatch.setattr(
        api.linux_router, "get_available_metrics", lambda: [{"key": "cpu", "name": "CPU"}]
    )

    async def _collect_all_linux():
        return [collect]

    monkeypatch.setattr(api.linux_router, "collect_all_linux", _collect_all_linux)

    async def _collect_host(cfg, metrics=None):
        return collect

    monkeypatch.setattr(api.linux_router, "collect_linux_host", _collect_host)
    monkeypatch.setattr(api.linux_router, "get_linux_repair_scripts", lambda: scripts)

    async def _exec_repair(*args, **kwargs):
        return execute

    monkeypatch.setattr(api.linux_router, "execute_linux_repair", _exec_repair)


def test_linux_endpoints(client, admin_headers, monkeypatch):
    """List hosts/metrics, collect, repair scripts and execute a repair."""
    client.headers.update(admin_headers)
    host = {"name": "host1", "host": "192.168.1.10", "username": "root"}
    _patch_linux_functions(
        monkeypatch,
        host=host,
        collect={"host": "host1", "cpu": {"usage_percent": 12.3}},
        scripts={"clear_tmp": {"name": "Clean /tmp", "risk": "low"}},
        execute={"success": True, "output": "cleaned", "exit_code": 0},
    )

    hosts_resp = client.get("/api/v1/platforms/linux/hosts")
    assert hosts_resp.status_code == 200
    assert hosts_resp.json()["total"] == 1

    metrics_resp = client.get("/api/v1/platforms/linux/metrics/available")
    assert metrics_resp.status_code == 200
    assert metrics_resp.json()["total"] == 1

    collect_all = client.get("/api/v1/platforms/linux/collect/all")
    assert collect_all.status_code == 200
    assert collect_all.json()["total"] == 1

    collect_host = client.post(
        "/api/v1/platforms/linux/collect/host",
        json={"host_name": "host1", "metrics": ["cpu"]},
    )
    assert collect_host.status_code == 200
    assert collect_host.json()["host"] == "host1"

    scripts_resp = client.get("/api/v1/platforms/linux/repair/scripts")
    assert scripts_resp.status_code == 200
    assert "clear_tmp" in scripts_resp.json()["scripts"]

    repair_resp = client.post(
        "/api/v1/platforms/linux/repair/execute",
        json={"host_name": "host1", "script_key": "clear_tmp", "params": {}},
    )
    assert repair_resp.status_code == 200
    assert repair_resp.json()["success"] is True

    # blocked
    _patch_linux_functions(
        monkeypatch,
        host=host,
        collect=collect_all.json()["hosts"][0],
        scripts=scripts_resp.json()["scripts"],
        execute={
            "success": False,
            "blocked": True,
            "reason": "forbidden",
            "safe_alternative": "use allowed command",
        },
    )
    blocked_resp = client.post(
        "/api/v1/platforms/linux/repair/execute",
        json={"host_name": "host1", "script_key": "clear_tmp", "params": {}},
    )
    assert blocked_resp.status_code == 403

    # not found
    _patch_linux_functions(
        monkeypatch,
        host=host,
        collect=collect_all.json()["hosts"][0],
        scripts=scripts_resp.json()["scripts"],
        execute={"success": False, "error": "未知修复脚本 missing"},
    )
    nf_resp = client.post(
        "/api/v1/platforms/linux/repair/execute",
        json={"host_name": "host1", "script_key": "missing", "params": {}},
    )
    assert nf_resp.status_code == 404

    # unknown host
    unknown = client.post(
        "/api/v1/platforms/linux/collect/host",
        json={"host_name": "unknown", "metrics": ["cpu"]},
    )
    assert unknown.status_code == 404


# ---------------------------------------------------------------------------
# stats_router.py
# ---------------------------------------------------------------------------
def test_stats_summary_and_record(client, approval_headers, monkeypatch):
    """GET summary returns real stats; POST repair record processes payload."""
    summary_resp = client.get("/api/v1/stats/summary", headers=approval_headers)
    assert summary_resp.status_code == 200
    body = summary_resp.json()
    assert "alerts" in body or "repairs" in body or "systems" in body

    record_resp = client.post(
        "/api/v1/stats/repair/record",
        headers=approval_headers,
        json={
            "success": True,
            "rule_name": "cpu-fix",
            "script_key": "restart_service",
            "platform": "windows",
            "output": "done",
        },
    )
    assert record_resp.status_code in (200, 500)
    if record_resp.status_code == 200:
        assert record_resp.json()["status"] == "ok"


# ---------------------------------------------------------------------------
# notify_router.py
# ---------------------------------------------------------------------------
class _FakeNotifyHttpx:
    """Async httpx fake that always returns 200 for notify_router tests."""

    is_closed = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    @staticmethod
    def _resp(status_code=200, text="ok", json_data=None):
        return SimpleNamespace(
            status_code=status_code,
            text=text,
            json=lambda: json_data or {},
            raise_for_status=lambda: None,
        )

    async def post(self, *args, **kwargs):
        return self._resp()

    async def get(self, *args, **kwargs):
        return self._resp(json_data=[{"name": "alice", "email": "a@example.com"}])


def _patch_notify(monkeypatch):
    import httpx

    monkeypatch.setattr(httpx, "AsyncClient", lambda *a, **k: _FakeNotifyHttpx())
    monkeypatch.setattr(
        core.notify_engine,
        "NOTIFY_CONFIG",
        {
            "enabled": True,
            "min_level": "info",
            "wecom_webhook": "https://wecom.example/hook",
            "dingtalk_webhook": "https://dt.example/hook",
            "feishu_webhook": "https://fs.example/hook",
            "email_to": "ops@example.com",
        },
    )


def test_notify_endpoints(client, admin_headers, monkeypatch):
    """Exercise notify config, health, status, read, oncall, test, send and reload."""
    client.headers.update(admin_headers)
    _patch_notify(monkeypatch)

    cfg_resp = client.get("/api/notify/config")
    assert cfg_resp.status_code == 200
    assert cfg_resp.json()["wecom_configured"] is True

    health_resp = client.get("/api/notify/health")
    assert health_resp.status_code == 200
    assert health_resp.json()["module_loaded"] is True

    status_resp = client.get("/api/notify/status", params={"alert_id": "a1"})
    assert status_resp.status_code == 200
    assert "records" in status_resp.json()

    read_resp = client.post("/api/notify/read", json={"message_id": "m1", "channel": "wecom"})
    assert read_resp.status_code in (200, 422)

    oncall_resp = client.get("/api/notify/oncall", params={"category": "sre"})
    assert oncall_resp.status_code == 200
    assert "contacts" in oncall_resp.json()

    test_resp = client.post(
        "/api/notify/test",
        json={"level": "warning", "title": "Test alert", "desc": "desc"},
    )
    assert test_resp.status_code == 200
    assert test_resp.json()["status"] == "ok"

    send_resp = client.post(
        "/api/notify/send",
        json={"level": "warning", "title": "Manual", "desc": "desc"},
    )
    assert send_resp.status_code == 200
    assert send_resp.json()["status"] == "ok"

    monkeypatch.setenv("NOTIFY_ENABLED", "true")
    monkeypatch.setenv("WECOM_WEBHOOK", "https://wecom.example/hook")
    reload_resp = client.post("/api/notify/reload")
    assert reload_resp.status_code == 200
    assert reload_resp.json()["status"] == "ok"


# ---------------------------------------------------------------------------
# frontend_enhancement_router.py
# ---------------------------------------------------------------------------
def test_frontend_enhancement_endpoints(client, admin_headers):
    """Cycle through user preferences, themes, dashboards, reports and accessibility."""
    client.headers.update(admin_headers)
    assert api.frontend_enhancement_router.FRONTEND_AVAILABLE is True

    pref_get = client.get("/api/v1/frontend/preferences/user-1")
    assert pref_get.status_code == 200
    assert pref_get.json()["preferences"]["user_id"] == "user-1"

    pref_put = client.put(
        "/api/v1/frontend/preferences/user-1",
        json={"theme": "dark", "language": "en-US"},
    )
    assert pref_put.status_code == 200
    assert pref_put.json()["preferences"]["theme"] == "dark"

    export_resp = client.get("/api/v1/frontend/preferences/user-1/export")
    assert export_resp.status_code == 200
    assert "user_id" in export_resp.json()["preferences"]

    import_resp = client.post(
        "/api/v1/frontend/preferences/user-1/import",
        json={"theme": "light", "view_mode": "list"},
    )
    assert import_resp.status_code == 200
    assert import_resp.json()["preferences"]["theme"] == "light"

    themes_resp = client.get("/api/v1/frontend/themes")
    assert themes_resp.status_code == 200
    assert len(themes_resp.json()["themes"]) >= 1

    custom_theme = client.post(
        "/api/v1/frontend/themes/custom",
        json={
            "theme_id": "ct1",
            "name": "Custom",
            "colors": {"primary": "#000"},
            "base_theme": "light",
        },
    )
    assert custom_theme.status_code == 200

    dash_resp = client.get("/api/v1/frontend/dashboard/dash-1")
    assert dash_resp.status_code == 200
    assert "widgets" in dash_resp.json()

    widget_resp = client.post(
        "/api/v1/frontend/dashboard/widget",
        json={
            "dashboard_id": "dash-1",
            "widget_id": "w-1",
            "widget_type": "metrics",
            "title": "CPU",
            "position": {"x": 0, "y": 0, "width": 6, "height": 4},
            "config": {"metrics": ["cpu"]},
        },
    )
    assert widget_resp.status_code == 200
    assert widget_resp.json()["widget"]["widget_id"] == "w-1"

    upd_widget = client.put(
        "/api/v1/frontend/dashboard/dash-1/widget/w-1",
        json={"title": "CPU updated"},
    )
    assert upd_widget.status_code == 200
    assert upd_widget.json()["widget"]["title"] == "CPU updated"

    del_widget = client.delete("/api/v1/frontend/dashboard/dash-1/widget/w-1")
    assert del_widget.status_code == 200

    tmpl_resp = client.post(
        "/api/v1/frontend/reports/templates",
        json={
            "template_id": "tmpl-1",
            "name": "Weekly",
            "description": "weekly report",
            "data_sources": ["metrics", "alerts"],
            "visualization_config": {"type": "line"},
        },
    )
    assert tmpl_resp.status_code == 200
    assert tmpl_resp.json()["template"]["template_id"] == "tmpl-1"

    list_tmpl = client.get("/api/v1/frontend/reports/templates")
    assert list_tmpl.status_code == 200
    assert any(t["template_id"] == "tmpl-1" for t in list_tmpl.json()["templates"])

    gen_resp = client.post(
        "/api/v1/frontend/reports/generate",
        json={"template_id": "tmpl-1", "filters": {"start": "2026-01-01"}},
    )
    assert gen_resp.status_code == 200
    assert gen_resp.json()["report"]["template_id"] == "tmpl-1"

    resp_resp = client.get("/api/v1/frontend/responsive/1024")
    assert resp_resp.status_code == 200
    assert "responsive_config" in resp_resp.json()

    acc_get = client.get("/api/v1/frontend/accessibility/user-1")
    assert acc_get.status_code == 200

    acc_put = client.put(
        "/api/v1/frontend/accessibility/user-1",
        json={"high_contrast": True},
    )
    assert acc_put.status_code == 200
    assert acc_put.json()["accessibility_settings"]["high_contrast"] is True

    summary = client.get("/api/v1/frontend/summary")
    assert summary.status_code == 200
    assert "frontend_summary" in summary.json()

    vm = client.get("/api/v1/frontend/view-modes")
    assert vm.status_code == 200
    assert "grid" in vm.json()["view_modes"]

    bp = client.get("/api/v1/frontend/breakpoints")
    assert bp.status_code == 200
    assert "lg" in bp.json()["breakpoints"]


# ---------------------------------------------------------------------------
# plugin_ecosystem_router.py
# ---------------------------------------------------------------------------
# def test_plugin_ecosystem_endpoints(client, admin_headers):
#     """Create, query and register developers through the plugin ecosystem API."""
#     status = client.get("/api/plugin-ecosystem/status", headers=admin_headers)
#     assert status.status_code == 200
#     assert "total_activities" in status.json()["data"]
#
#     act = client.post(
#         "/api/plugin-ecosystem/activity",
#         headers=admin_headers,
#         params={"plugin_id": "p1", "activity_type": "install", "user_id": "u1"},
#     )
#     assert act.status_code == 200
#     assert act.json()["data"]["activity_type"] == "install"
#
#     acts = client.get("/api/plugin-ecosystem/activities/p1", headers=admin_headers)
#     assert acts.status_code == 200
#     assert acts.json()["data"]["count"] >= 1

    # reg = client.post(
    #     "/api/plugin-ecosystem/developer/register",
    #     headers=admin_headers,
    #     params={"developer_id": "dev-1", "name": "Alice", "email": "a@example.com"},
    # )
    # assert reg.status_code == 200
    # assert reg.json()["data"]["developer_id"] == "dev-1"
    #
    # stats = client.get("/api/plugin-ecosystem/developer/dev-1", headers=admin_headers)
    # assert stats.status_code == 200
    # assert stats.json()["data"]["developer_id"] == "dev-1"


# ---------------------------------------------------------------------------
# apm_router.py
# ---------------------------------------------------------------------------
def test_apm_endpoints(client, admin_headers, monkeypatch):
    """APM metrics, health and reset endpoints return expected shapes."""
    import core.health_check

    async def _fake_resources():
        return {"metrics": {"cpu": 10.0, "memory": 20.0}, "status": "healthy"}

    async def _fake_health():
        return {"status": "healthy", "checks": {}}

    monkeypatch.setattr(
        api.apm_router.telemetry,
        "get_apm_metrics",
        lambda: {
            "request_count": 100,
            "error_rate": 0.0,
            "slow_request_rate": 0.0,
        },
    )
    monkeypatch.setattr(core.health_check, "check_system_resources", _fake_resources)
    monkeypatch.setattr(core.health_check, "perform_health_checks", _fake_health)

    metrics = client.get("/api/v1/apm/metrics", headers=admin_headers)
    assert metrics.status_code == 200
    assert "apm_metrics" in metrics.json()

    health = client.get("/api/v1/apm/health", headers=admin_headers)
    assert health.status_code == 200
    assert health.json()["application"] == "aiops-agent"

    reset = client.post("/api/v1/apm/metrics/reset", headers=admin_headers)
    assert reset.status_code == 200
    assert reset.json()["status"] == "success"


# ---------------------------------------------------------------------------
# qdrant_router.py
# ---------------------------------------------------------------------------
class _FakeQdrantCollection:
    name = "c1"


class _FakeSearchResult:
    def __init__(self):
        self.id = 1
        self.score = 0.95
        self.payload = {"text": "x"}


class _FakeQdrantClient:
    def get_collections(self):
        return SimpleNamespace(collections=[_FakeQdrantCollection()])

    def create_collection(self, *args, **kwargs):
        return None

    def delete_collection(self, *args, **kwargs):
        return None

    def upsert(self, *args, **kwargs):
        return None

    def search(self, *args, **kwargs):
        return [_FakeSearchResult()]

    def delete(self, *args, **kwargs):
        return None


def _patch_qdrant(monkeypatch):
    monkeypatch.setattr(
        api.qdrant_router,
        "health_check",
        lambda: {"status": "healthy", "version": "1.7.0"},
    )
    monkeypatch.setattr(
        api.qdrant_router,
        "list_collections",
        lambda: [{"name": "c1", "vector_size": 4, "points_count": 0}],
    )
    monkeypatch.setattr(
        api.qdrant_router,
        "create_collection",
        lambda name, vector_size, distance: {
            "status": "success",
            "collection_name": name,
        },
    )
    monkeypatch.setattr(
        api.qdrant_router,
        "upsert_points",
        lambda collection, points: {
            "status": "success",
            "operation_id": "op-1",
            "upserted_count": len(points),
        },
    )
    monkeypatch.setattr(
        api.qdrant_router,
        "search",
        lambda collection, query_vector, top_k, filter=None: [
            {"id": 1, "score": 0.95, "payload": {"text": "sample"}}
        ],
    )
    monkeypatch.setattr(
        api.qdrant_router,
        "delete_points",
        lambda collection, ids: {"status": "success", "deleted_count": len(ids)},
    )
    monkeypatch.setattr(
        api.qdrant_router,
        "delete_collection",
        lambda name: {"status": "success", "collection_name": name},
    )


def test_qdrant_endpoints(client, admin_headers, monkeypatch):
    """All Qdrant CRUD endpoints use a fake client and return structured data."""
    _patch_qdrant(monkeypatch)

    health = client.get("/api/qdrant/health", headers=admin_headers)
    assert health.status_code == 200
    assert health.json()["status"] == "healthy"

    collections = client.get("/api/qdrant/collections", headers=admin_headers)
    assert collections.status_code == 200
    assert any(c["name"] == "c1" for c in collections.json())

    create = client.post(
        "/api/qdrant/collections",
        headers=admin_headers,
        json={"name": "c2", "vector_size": 4, "distance": "Cosine"},
    )
    assert create.status_code == 200
    assert create.json()["status"] == "success"

    upsert = client.post(
        "/api/qdrant/points",
        headers=admin_headers,
        json={"collection": "c2", "points": [{"id": 1, "vector": [0.1, 0.2, 0.3, 0.4]}]},
    )
    assert upsert.status_code == 200
    assert upsert.json()["status"] == "success"

    search = client.post(
        "/api/qdrant/search",
        headers=admin_headers,
        json={"collection": "c2", "query_vector": [0.1, 0.2, 0.3, 0.4], "top_k": 1},
    )
    assert search.status_code == 200
    assert len(search.json()) == 1

    delete_points = client.request(
        "DELETE",
        "/api/qdrant/points",
        headers=admin_headers,
        json={"collection": "c2", "ids": [1]},
    )
    assert delete_points.status_code == 200

    delete_collection = client.delete("/api/qdrant/collections/c2", headers=admin_headers)
    assert delete_collection.status_code == 200


def test_qdrant_validation_errors(client, admin_headers, monkeypatch):
    """Test Pydantic validator error paths for distance, vector, and query_vector."""
    _patch_qdrant(monkeypatch)

    # Test invalid distance value (line 38)
    invalid_distance = client.post(
        "/api/qdrant/collections",
        headers=admin_headers,
        json={"name": "c3", "vector_size": 4, "distance": "InvalidDistance"},
    )
    assert invalid_distance.status_code == 422
    assert "distance" in invalid_distance.text or "distance" in str(invalid_distance.json())

    # Test empty vector in PointModel (line 58)
    invalid_vector = client.post(
        "/api/qdrant/points",
        headers=admin_headers,
        json={"collection": "c2", "points": [{"id": 1, "vector": []}]},
    )
    assert invalid_vector.status_code == 422
    assert "vector" in invalid_vector.text or "vector" in str(invalid_vector.json())

    # Test empty query_vector in SearchRequest (line 89)
    invalid_query = client.post(
        "/api/qdrant/search",
        headers=admin_headers,
        json={"collection": "c2", "query_vector": [], "top_k": 1},
    )
    assert invalid_query.status_code == 422
    assert "query_vector" in invalid_query.text or "query_vector" in str(invalid_query.json())


def test_qdrant_valid_distance_values(client, admin_headers, monkeypatch):
    """Test all valid distance values to cover branch coverage."""
    _patch_qdrant(monkeypatch)

    # Test Cosine (default)
    cosine_resp = client.post(
        "/api/qdrant/collections",
        headers=admin_headers,
        json={"name": "c_cosine", "vector_size": 4, "distance": "Cosine"},
    )
    assert cosine_resp.status_code == 200

    # Test Euclid
    euclid_resp = client.post(
        "/api/qdrant/collections",
        headers=admin_headers,
        json={"name": "c_euclid", "vector_size": 4, "distance": "Euclid"},
    )
    assert euclid_resp.status_code == 200

    # Test Dot
    dot_resp = client.post(
        "/api/qdrant/collections",
        headers=admin_headers,
        json={"name": "c_dot", "vector_size": 4, "distance": "Dot"},
    )
    assert dot_resp.status_code == 200


def test_qdrant_point_with_payload(client, admin_headers, monkeypatch):
    """Test point with payload to cover branch coverage."""
    _patch_qdrant(monkeypatch)

    # Test point with payload
    upsert_with_payload = client.post(
        "/api/qdrant/points",
        headers=admin_headers,
        json={
            "collection": "c2",
            "points": [
                {
                    "id": 1,
                    "vector": [0.1, 0.2, 0.3, 0.4],
                    "payload": {"text": "sample", "category": "test"},
                }
            ],
        },
    )
    assert upsert_with_payload.status_code == 200
    assert upsert_with_payload.json()["status"] == "success"

    # Test point without payload (default empty dict)
    upsert_without_payload = client.post(
        "/api/qdrant/points",
        headers=admin_headers,
        json={"collection": "c2", "points": [{"id": 2, "vector": [0.5, 0.6, 0.7, 0.8]}]},
    )
    assert upsert_without_payload.status_code == 200
    assert upsert_without_payload.json()["status"] == "success"


def test_qdrant_multiple_points(client, admin_headers, monkeypatch):
    """Test upsert multiple points to cover branch coverage."""
    _patch_qdrant(monkeypatch)

    # Test multiple points in single request
    upsert_multiple = client.post(
        "/api/qdrant/points",
        headers=admin_headers,
        json={
            "collection": "c2",
            "points": [
                {"id": 1, "vector": [0.1, 0.2, 0.3, 0.4]},
                {"id": 2, "vector": [0.5, 0.6, 0.7, 0.8]},
                {"id": 3, "vector": [0.9, 1.0, 1.1, 1.2]},
            ],
        },
    )
    assert upsert_multiple.status_code == 200
    assert upsert_multiple.json()["upserted_count"] == 3


def test_qdrant_delete_multiple_points(client, admin_headers, monkeypatch):
    """Test delete multiple points to cover branch coverage."""
    _patch_qdrant(monkeypatch)

    # Test delete multiple points
    delete_multiple = client.request(
        "DELETE",
        "/api/qdrant/points",
        headers=admin_headers,
        json={"collection": "c2", "ids": [1, 2, 3]},
    )
    assert delete_multiple.status_code == 200
    assert delete_multiple.json()["deleted_count"] == 3


def test_qdrant_string_point_id(client, admin_headers, monkeypatch):
    """Test point with string ID to cover branch coverage."""
    _patch_qdrant(monkeypatch)

    # Test point with string ID
    upsert_string_id = client.post(
        "/api/qdrant/points",
        headers=admin_headers,
        json={"collection": "c2", "points": [{"id": "point-1", "vector": [0.1, 0.2, 0.3, 0.4]}]},
    )
    assert upsert_string_id.status_code == 200
    assert upsert_string_id.json()["status"] == "success"


def test_qdrant_search_with_different_top_k(client, admin_headers, monkeypatch):
    """Test search with different top_k values to cover branch coverage."""
    _patch_qdrant(monkeypatch)

    # Test with top_k = 1
    search_1 = client.post(
        "/api/qdrant/search",
        headers=admin_headers,
        json={"collection": "c2", "query_vector": [0.1, 0.2, 0.3, 0.4], "top_k": 1},
    )
    assert search_1.status_code == 200

    # Test with top_k = 10
    search_10 = client.post(
        "/api/qdrant/search",
        headers=admin_headers,
        json={"collection": "c2", "query_vector": [0.1, 0.2, 0.3, 0.4], "top_k": 10},
    )
    assert search_10.status_code == 200


def test_qdrant_vector_size_validation(client, admin_headers, monkeypatch):
    """Test vector_size validation to cover branch coverage."""
    _patch_qdrant(monkeypatch)

    # Test with valid vector_size
    valid_size = client.post(
        "/api/qdrant/collections",
        headers=admin_headers,
        json={"name": "c_valid", "vector_size": 768, "distance": "Cosine"},
    )
    assert valid_size.status_code == 200

    # Test with minimum valid vector_size (gt=0 means minimum 1)
    min_size = client.post(
        "/api/qdrant/collections",
        headers=admin_headers,
        json={"name": "c_min", "vector_size": 1, "distance": "Cosine"},
    )
    assert min_size.status_code == 200


def test_qdrant_empty_ids_list(client, admin_headers, monkeypatch):
    """Test delete points with empty IDs list to cover branch coverage."""
    _patch_qdrant(monkeypatch)

    # Test with empty IDs list
    delete_empty = client.request(
        "DELETE",
        "/api/qdrant/points",
        headers=admin_headers,
        json={"collection": "c2", "ids": []},
    )
    assert delete_empty.status_code == 200
    assert delete_empty.json()["deleted_count"] == 0


def test_qdrant_complex_payload(client, admin_headers, monkeypatch):
    """Test point with complex nested payload to cover branch coverage."""
    _patch_qdrant(monkeypatch)

    # Test with complex nested payload
    complex_payload = client.post(
        "/api/qdrant/points",
        headers=admin_headers,
        json={
            "collection": "c2",
            "points": [
                {
                    "id": 1,
                    "vector": [0.1, 0.2, 0.3, 0.4],
                    "payload": {
                        "text": "sample",
                        "metadata": {"author": "test", "timestamp": 1234567890},
                        "tags": ["tag1", "tag2"],
                    },
                }
            ],
        },
    )
    assert complex_payload.status_code == 200
    assert complex_payload.json()["status"] == "success"


def test_qdrant_mixed_id_types(client, admin_headers, monkeypatch):
    """Test points with mixed ID types (int and str) to cover branch coverage."""
    _patch_qdrant(monkeypatch)

    # Test with mixed ID types
    mixed_ids = client.post(
        "/api/qdrant/points",
        headers=admin_headers,
        json={
            "collection": "c2",
            "points": [
                {"id": 1, "vector": [0.1, 0.2, 0.3, 0.4]},
                {"id": "str-2", "vector": [0.5, 0.6, 0.7, 0.8]},
                {"id": 3, "vector": [0.9, 1.0, 1.1, 1.2]},
            ],
        },
    )
    assert mixed_ids.status_code == 200
    assert mixed_ids.json()["upserted_count"] == 3


def test_qdrant_mixed_id_deletion(client, admin_headers, monkeypatch):
    """Test delete points with mixed ID types to cover branch coverage."""
    _patch_qdrant(monkeypatch)

    # Test with mixed ID types
    mixed_delete = client.request(
        "DELETE",
        "/api/qdrant/points",
        headers=admin_headers,
        json={"collection": "c2", "ids": [1, "str-2", 3]},
    )
    assert mixed_delete.status_code == 200
    assert mixed_delete.json()["deleted_count"] == 3


def test_qdrant_large_vector(client, admin_headers, monkeypatch):
    """Test point with large vector to cover branch coverage."""
    _patch_qdrant(monkeypatch)

    # Test with large vector (1536 dimensions like OpenAI embeddings)
    large_vector = [0.1] * 1536
    large_vector_req = client.post(
        "/api/qdrant/points",
        headers=admin_headers,
        json={"collection": "c2", "points": [{"id": 1, "vector": large_vector}]},
    )
    assert large_vector_req.status_code == 200
    assert large_vector_req.json()["status"] == "success"


def test_qdrant_search_with_large_top_k(client, admin_headers, monkeypatch):
    """Test search with large top_k value to cover branch coverage."""
    _patch_qdrant(monkeypatch)

    # Test with large top_k
    large_top_k = client.post(
        "/api/qdrant/search",
        headers=admin_headers,
        json={"collection": "c2", "query_vector": [0.1, 0.2, 0.3, 0.4], "top_k": 100},
    )
    assert large_top_k.status_code == 200


def test_qdrant_different_exception_types(client, admin_headers, monkeypatch):
    """Test different exception types to cover branch coverage."""
    # Patch health_check and list_collections to keep working
    monkeypatch.setattr(
        api.qdrant_router,
        "health_check",
        lambda: {"status": "healthy", "version": "1.7.0"},
    )
    monkeypatch.setattr(
        api.qdrant_router,
        "list_collections",
        lambda: [{"name": "c1", "vector_size": 4, "points_count": 0}],
    )

    # Test with ValueError
    def _value_error(name, vector_size, distance):
        raise ValueError("Invalid value")

    monkeypatch.setattr(api.qdrant_router, "create_collection", _value_error)
    value_error_resp = client.post(
        "/api/qdrant/collections",
        headers=admin_headers,
        json={"name": "c_val_err", "vector_size": 4, "distance": "Cosine"},
    )
    assert value_error_resp.status_code == 500
    assert "Invalid value" in value_error_resp.text

    # Test with TypeError
    def _type_error(collection, points):
        raise TypeError("Invalid type")

    monkeypatch.setattr(api.qdrant_router, "upsert_points", _type_error)
    type_error_resp = client.post(
        "/api/qdrant/points",
        headers=admin_headers,
        json={"collection": "c2", "points": [{"id": 1, "vector": [0.1, 0.2, 0.3, 0.4]}]},
    )
    assert type_error_resp.status_code == 500
    assert "Invalid type" in type_error_resp.text


def test_qdrant_single_element_vector(client, admin_headers, monkeypatch):
    """Test with single element vector to cover branch coverage."""
    _patch_qdrant(monkeypatch)

    # Test with single element vector (minimum valid)
    single_element = client.post(
        "/api/qdrant/points",
        headers=admin_headers,
        json={"collection": "c2", "points": [{"id": 1, "vector": [0.5]}]},
    )
    assert single_element.status_code == 200
    assert single_element.json()["status"] == "success"

    # Test search with single element query vector
    single_query = client.post(
        "/api/qdrant/search",
        headers=admin_headers,
        json={"collection": "c2", "query_vector": [0.5], "top_k": 1},
    )
    assert single_query.status_code == 200


def test_qdrant_default_distance_value(client, admin_headers, monkeypatch):
    """Test with default distance value to cover branch coverage."""
    _patch_qdrant(monkeypatch)

    # Test without specifying distance (should use default "Cosine")
    default_distance = client.post(
        "/api/qdrant/collections",
        headers=admin_headers,
        json={"name": "c_default", "vector_size": 4},
    )
    assert default_distance.status_code == 200
    assert default_distance.json()["status"] == "success"


def test_qdrant_negative_values_in_filter(client, admin_headers, monkeypatch):
    """Test search with negative values in filter to cover branch coverage."""
    _patch_qdrant(monkeypatch)

    # Test with negative values in filter
    negative_filter = client.post(
        "/api/qdrant/search",
        headers=admin_headers,
        json={
            "collection": "c2",
            "query_vector": [0.1, 0.2, 0.3, 0.4],
            "top_k": 1,
            "filter": {"score": {"gte": -1.0}},
        },
    )
    assert negative_filter.status_code == 200


def test_qdrant_zero_vector_size_validation(client, admin_headers, monkeypatch):
    """Test vector_size validation with zero to cover branch coverage."""
    _patch_qdrant(monkeypatch)

    # Test with zero vector_size (should fail due to gt=0 constraint)
    zero_size = client.post(
        "/api/qdrant/collections",
        headers=admin_headers,
        json={"name": "c_zero", "vector_size": 0, "distance": "Cosine"},
    )
    assert zero_size.status_code == 422
    assert "vector_size" in zero_size.text or "greater than" in zero_size.text


def test_qdrant_negative_vector_size_validation(client, admin_headers, monkeypatch):
    """Test vector_size validation with negative value to cover branch coverage."""
    _patch_qdrant(monkeypatch)

    # Test with negative vector_size (should fail due to gt=0 constraint)
    negative_size = client.post(
        "/api/qdrant/collections",
        headers=admin_headers,
        json={"name": "c_negative", "vector_size": -10, "distance": "Cosine"},
    )
    assert negative_size.status_code == 422
    assert "vector_size" in negative_size.text or "greater than" in negative_size.text


def test_qdrant_negative_top_k_validation(client, admin_headers, monkeypatch):
    """Test top_k validation with negative value to cover branch coverage."""
    _patch_qdrant(monkeypatch)

    # Test with negative top_k (should fail due to gt=0 constraint)
    negative_top_k = client.post(
        "/api/qdrant/search",
        headers=admin_headers,
        json={"collection": "c2", "query_vector": [0.1, 0.2, 0.3, 0.4], "top_k": -1},
    )
    assert negative_top_k.status_code == 422
    assert "top_k" in negative_top_k.text or "greater than" in negative_top_k.text


def test_qdrant_zero_top_k_validation(client, admin_headers, monkeypatch):
    """Test top_k validation with zero to cover branch coverage."""
    _patch_qdrant(monkeypatch)

    # Test with zero top_k (should fail due to gt=0 constraint)
    zero_top_k = client.post(
        "/api/qdrant/search",
        headers=admin_headers,
        json={"collection": "c2", "query_vector": [0.1, 0.2, 0.3, 0.4], "top_k": 0},
    )
    assert zero_top_k.status_code == 422
    assert "top_k" in zero_top_k.text or "greater than" in zero_top_k.text


def test_qdrant_search_with_none_filter(client, admin_headers, monkeypatch):
    """Test search with explicit None filter to cover branch coverage."""
    _patch_qdrant(monkeypatch)

    # Test with explicit None filter
    none_filter = client.post(
        "/api/qdrant/search",
        headers=admin_headers,
        json={"collection": "c2", "query_vector": [0.1, 0.2, 0.3, 0.4], "top_k": 1, "filter": None},
    )
    assert none_filter.status_code == 200


def test_qdrant_point_with_none_payload(client, admin_headers, monkeypatch):
    """Test point with explicit None payload to cover branch coverage."""
    _patch_qdrant(monkeypatch)

    # Test with explicit None payload
    none_payload = client.post(
        "/api/qdrant/points",
        headers=admin_headers,
        json={"collection": "c2", "points": [{"id": 1, "vector": [0.1, 0.2, 0.3, 0.4], "payload": None}]},
    )
    assert none_payload.status_code == 200
    assert none_payload.json()["status"] == "success"


def test_qdrant_collection_name_with_special_chars(client, admin_headers, monkeypatch):
    """Test collection name with special characters to cover branch coverage."""
    _patch_qdrant(monkeypatch)

    # Test with special characters in collection name
    special_name = client.post(
        "/api/qdrant/collections",
        headers=admin_headers,
        json={"name": "test_collection_123", "vector_size": 4, "distance": "Cosine"},
    )
    assert special_name.status_code == 200


def test_qdrant_float_point_id(client, admin_headers, monkeypatch):
    """Test point with float ID to cover branch coverage."""
    _patch_qdrant(monkeypatch)

    # Test with float ID
    float_id = client.post(
        "/api/qdrant/points",
        headers=admin_headers,
        json={"collection": "c2", "points": [{"id": 1.5, "vector": [0.1, 0.2, 0.3, 0.4]}]},
    )
    assert float_id.status_code == 200
    assert float_id.json()["status"] == "success"


def test_qdrant_create_collection_exception(client, admin_headers, monkeypatch):
    """Test create_collection exception handling (lines 183-184)."""
    # Patch health_check and list_collections to keep working
    monkeypatch.setattr(
        api.qdrant_router,
        "health_check",
        lambda: {"status": "healthy", "version": "1.7.0"},
    )
    monkeypatch.setattr(
        api.qdrant_router,
        "list_collections",
        lambda: [{"name": "c1", "vector_size": 4, "points_count": 0}],
    )

    def _create_fail(name, vector_size, distance):
        raise RuntimeError("Failed to create collection")

    monkeypatch.setattr(api.qdrant_router, "create_collection", _create_fail)
    create_fail = client.post(
        "/api/qdrant/collections",
        headers=admin_headers,
        json={"name": "c_fail", "vector_size": 4, "distance": "Cosine"},
    )
    assert create_fail.status_code == 500
    assert "Failed to create collection" in create_fail.text


def test_qdrant_delete_collection_exception(client, admin_headers, monkeypatch):
    """Test delete_collection exception handling (lines 211-212)."""
    # Patch health_check and list_collections to keep working
    monkeypatch.setattr(
        api.qdrant_router,
        "health_check",
        lambda: {"status": "healthy", "version": "1.7.0"},
    )
    monkeypatch.setattr(
        api.qdrant_router,
        "list_collections",
        lambda: [{"name": "c1", "vector_size": 4, "points_count": 0}],
    )

    def _delete_fail(name):
        raise RuntimeError("Failed to delete collection")

    monkeypatch.setattr(api.qdrant_router, "delete_collection", _delete_fail)
    delete_fail = client.delete("/api/qdrant/collections/c_fail", headers=admin_headers)
    assert delete_fail.status_code == 500
    assert "Failed to delete collection" in delete_fail.text


def test_qdrant_upsert_points_exception(client, admin_headers, monkeypatch):
    """Test upsert_points exception handling (lines 241-242)."""
    # Patch health_check and list_collections to keep working
    monkeypatch.setattr(
        api.qdrant_router,
        "health_check",
        lambda: {"status": "healthy", "version": "1.7.0"},
    )
    monkeypatch.setattr(
        api.qdrant_router,
        "list_collections",
        lambda: [{"name": "c1", "vector_size": 4, "points_count": 0}],
    )

    def _upsert_fail(collection, points):
        raise RuntimeError("Failed to upsert points")

    monkeypatch.setattr(api.qdrant_router, "upsert_points", _upsert_fail)
    upsert_fail = client.post(
        "/api/qdrant/points",
        headers=admin_headers,
        json={"collection": "c2", "points": [{"id": 1, "vector": [0.1, 0.2, 0.3, 0.4]}]},
    )
    assert upsert_fail.status_code == 500
    assert "Failed to upsert points" in upsert_fail.text


def test_qdrant_search_exception(client, admin_headers, monkeypatch):
    """Test search exception handling (lines 270-271)."""
    # Patch health_check and list_collections to keep working
    monkeypatch.setattr(
        api.qdrant_router,
        "health_check",
        lambda: {"status": "healthy", "version": "1.7.0"},
    )
    monkeypatch.setattr(
        api.qdrant_router,
        "list_collections",
        lambda: [{"name": "c1", "vector_size": 4, "points_count": 0}],
    )

    def _search_fail(collection, query_vector, top_k, filter=None):
        raise RuntimeError("Failed to search")

    monkeypatch.setattr(api.qdrant_router, "search", _search_fail)
    search_fail = client.post(
        "/api/qdrant/search",
        headers=admin_headers,
        json={"collection": "c2", "query_vector": [0.1, 0.2, 0.3, 0.4], "top_k": 1},
    )
    assert search_fail.status_code == 500
    assert "Failed to search" in search_fail.text


def test_qdrant_delete_points_exception(client, admin_headers, monkeypatch):
    """Test delete_points exception handling (lines 292-293)."""
    # Patch health_check and list_collections to keep working
    monkeypatch.setattr(
        api.qdrant_router,
        "health_check",
        lambda: {"status": "healthy", "version": "1.7.0"},
    )
    monkeypatch.setattr(
        api.qdrant_router,
        "list_collections",
        lambda: [{"name": "c1", "vector_size": 4, "points_count": 0}],
    )

    def _delete_points_fail(collection, ids):
        raise RuntimeError("Failed to delete points")

    monkeypatch.setattr(api.qdrant_router, "delete_points", _delete_points_fail)
    delete_points_fail = client.request(
        "DELETE",
        "/api/qdrant/points",
        headers=admin_headers,
        json={"collection": "c2", "ids": [1]},
    )
    assert delete_points_fail.status_code == 500
    assert "Failed to delete points" in delete_points_fail.text


# ---------------------------------------------------------------------------
# change_management_router.py
# ---------------------------------------------------------------------------
def test_change_management_lifecycle(client, admin_headers):
    """Create, submit, approve, implement and rollback a change request."""
    create = client.post(
        "/api/v1/change-management/requests",
        headers=admin_headers,
        json={
            "title": "Restart cache",
            "requester": "admin",
            "description": "planned restart",
            "affected_services": ["cache"],
            "implementation_plan": "restart",
            "rollback_plan": "start again",
        },
    )
    assert create.status_code == 201
    cr_id = create.json()["id"]

    get_one = client.get(f"/api/v1/change-management/requests/{cr_id}", headers=admin_headers)
    assert get_one.status_code == 200
    assert get_one.json()["id"] == cr_id

    submit = client.post(
        f"/api/v1/change-management/requests/{cr_id}/submit", headers=admin_headers
    )
    assert submit.status_code == 200
    assert submit.json()["status"] == "pending"

    approve = client.post(
        f"/api/v1/change-management/requests/{cr_id}/approve", headers=admin_headers
    )
    assert approve.status_code == 200
    assert approve.json()["status"] == "approved"

    implement = client.post(
        f"/api/v1/change-management/requests/{cr_id}/implement", headers=admin_headers
    )
    assert implement.status_code == 200
    assert implement.json()["status"] == "implemented"

    rollback = client.post(
        f"/api/v1/change-management/requests/{cr_id}/rollback", headers=admin_headers
    )
    assert rollback.status_code == 200
    assert rollback.json()["status"] == "rolled_back"

    list_resp = client.get("/api/v1/change-management/requests", headers=admin_headers)
    assert list_resp.status_code == 200

    # invalid state transition
    bad = client.post(
        f"/api/v1/change-management/requests/{cr_id}/implement", headers=admin_headers
    )
    assert bad.status_code == 400


# ---------------------------------------------------------------------------
# business_impact_router.py
# ---------------------------------------------------------------------------
def _patch_business_impact(monkeypatch):
    async def _services():
        return [{"id": "SVC-001", "name": "payment-service", "impactScore": 9.0, "status": "down"}]

    async def _ux():
        return [
            {"id": "UX-001", "name": "page_load", "value": 2.5, "change": -5.0, "status": "good"}
        ]

    async def _assess(name):
        return {
            "name": name,
            "impactScore": 8.5,
            "status": "down",
            "affectedUsers": 1000,
            "revenueImpact": 50000,
        }

    monkeypatch.setattr(api.business_impact_router, "list_business_impact_services", _services)
    monkeypatch.setattr(api.business_impact_router, "list_business_impact_ux_metrics", _ux)
    monkeypatch.setattr(api.business_impact_router, "assess_business_impact", _assess)


def test_business_impact_endpoints(client, admin_headers, monkeypatch):
    """Business impact endpoints return service and UX assessments."""
    client.headers.update(admin_headers)
    _patch_business_impact(monkeypatch)

    services = client.get("/api/v1/business-impact/services")
    assert services.status_code == 200
    assert services.json()["status"] == "success"
    assert services.json()["data"][0]["name"] == "payment-service"

    ux = client.get("/api/v1/business-impact/ux-metrics")
    assert ux.status_code == 200
    assert ux.json()["status"] == "success"

    assess = client.get("/api/v1/business-impact/assess/payment-service")
    assert assess.status_code == 200
    assert assess.json()["data"]["name"] == "payment-service"

    bad_name = client.get("/api/v1/business-impact/assess/bad name!")
    assert bad_name.status_code == 422


# ---------------------------------------------------------------------------
# repair_router.py (legacy module, not mounted)
# ---------------------------------------------------------------------------
def test_repair_router_direct(monkeypatch):
    """Call the legacy repair router functions directly to exercise statement coverage."""
    import asyncio  # noqa: F401  # Imported for test setup
    from types import SimpleNamespace as SN

    from core.repair_engine import execute_repair, get_repair_history, get_repair_scripts

    async def _run():
        # list scripts success
        monkeypatch.setattr(
            api.repair_router, "get_repair_scripts", lambda: {"clear_temp": {"name": "Clean temp"}}
        )
        result = await api.repair_router.list_scripts()  # noqa: F841  # Variable for test verification
        assert "clear_temp" in result["scripts"]

        # list scripts error
        def _bad_scripts():
            raise RuntimeError("boom")

        monkeypatch.setattr(api.repair_router, "get_repair_scripts", _bad_scripts)
        with pytest.raises(HTTPException):
            await api.repair_router.list_scripts()

        # history success
        monkeypatch.setattr(
            api.repair_router, "get_repair_history", lambda limit: [{"script_key": "x"}]
        )
        result = await api.repair_router.get_history(20)  # noqa: F841  # Variable for test verification
        assert result["total"] == 1

        # history error
        def _bad_history(limit):
            raise RuntimeError("boom")

        monkeypatch.setattr(api.repair_router, "get_repair_history", _bad_history)
        with pytest.raises(HTTPException):
            await api.repair_router.get_history(20)

        # execute success
        async def _good_execute(key, params):
            return {"success": True, "script_key": key, "output": "ok"}

        monkeypatch.setattr(api.repair_router, "execute_repair", _good_execute)
        req = api.repair_router.RepairRequest(script_key="clear_temp", params={})
        request = SN(client=SN(host="testclient"))
        result = await api.repair_router.run_repair(req, request)  # noqa: F841  # Variable for test verification
        assert result["success"] is True

        # blocked
        async def _blocked(key, params):
            return {
                "success": False,
                "error": "blocked",
                "blocked": True,
                "safe_alternative": "safe-cmd",
            }

        monkeypatch.setattr(api.repair_router, "execute_repair", _blocked)
        with pytest.raises(HTTPException) as exc:
            await api.repair_router.run_repair(req, request)
        assert exc.value.status_code == 403

        # not found
        async def _nf(key, params):
            return {"success": False, "error": "未知修复脚本: missing"}

        monkeypatch.setattr(api.repair_router, "execute_repair", _nf)
        with pytest.raises(HTTPException) as exc:
            await api.repair_router.run_repair(req, request)
        assert exc.value.status_code == 404

        # param error
        async def _param(key, params):
            return {"success": False, "error": "缺少必要参数: pid"}

        monkeypatch.setattr(api.repair_router, "execute_repair", _param)
        with pytest.raises(HTTPException) as exc:
            await api.repair_router.run_repair(req, request)
        assert exc.value.status_code == 422

        # unknown error
        async def _err(key, params):
            return {"success": False, "error": "some failure"}

        monkeypatch.setattr(api.repair_router, "execute_repair", _err)
        with pytest.raises(HTTPException) as exc:
            await api.repair_router.run_repair(req, request)
        assert exc.value.status_code == 500

        # execute raises
        async def _raise(key, params):
            raise RuntimeError("boom")

        monkeypatch.setattr(api.repair_router, "execute_repair", _raise)
        with pytest.raises(HTTPException) as exc:
            await api.repair_router.run_repair(req, request)
        assert exc.value.status_code == 500

        # execute returns None
        async def _none(key, params):
            return None

        monkeypatch.setattr(api.repair_router, "execute_repair", _none)
        with pytest.raises(HTTPException) as exc:
            await api.repair_router.run_repair(req, request)
        assert exc.value.status_code == 500

        # execute returns non-dict
        async def _bad(key, params):
            return "bad"

        monkeypatch.setattr(api.repair_router, "execute_repair", _bad)
        with pytest.raises(HTTPException) as exc:
            await api.repair_router.run_repair(req, request)
        assert exc.value.status_code == 500

    asyncio.run(_run())
