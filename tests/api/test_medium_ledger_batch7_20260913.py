# -*- coding: utf-8 -*-
"""Regression tests for the 7th batch of medium-severity ledger fixes.

Covered ledger items (2026-09-13):
  - API-048 api/itsm_router.py            external ITSM failures are reported honestly
  - API-052 api/localization_resource_router.py  translation I/O path whitelist
  - API-067 api/health_router.py          remote health probes require a Bearer token
  - API-074 api/root_cause_router.py      root-cause engine encapsulation accessors
  - API-078 api/tracing_router.py         tracing metrics are measured, not constants
  - API-080 api/chaos_router.py           error branches return the declared HTTP status
  - API-087 api/grpc_service_router.py    deletion goes through the manager API
  - API-099 api/log_router.py             case_sensitive is finally honoured
  - API-102 api/frontend_enhancement_router.py  view-modes guards the unavailable state
  - API-104 api/alert_router.py           metric timestamps parse ISO and time-only forms
"""

import asyncio
import sys
import types
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

pytestmark = [pytest.mark.api]


# ---------------------------------------------------------------------------
# API-048 — ITSM: external failures must not masquerade as "created"
# ---------------------------------------------------------------------------
class _FakeHTTPX:
    def __init__(self, status_code=201, body=None):
        self.status_code = status_code
        self.body = body or {}
        outer = self

        class _Resp:
            status_code = outer.status_code
            text = "boom"

            def json(self):  # noqa: ANN001
                return outer.body

        class _Client:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                return False

            async def post(self, *args, **kwargs):
                return _Resp()

            async def put(self, *args, **kwargs):
                return _Resp()

        self.AsyncClient = _Client


def _itsm_module():
    import api.itsm_router as mod

    return mod


def test_itsm_create_marks_external_success(monkeypatch):
    mod = _itsm_module()
    monkeypatch.setitem(sys.modules, "httpx", _FakeHTTPX(201, {"key": "OPS-1"}))
    monkeypatch.setattr(mod, "JIRA_URL", "http://jira.local")
    monkeypatch.setattr(mod, "JIRA_TOKEN", "tok")

    result = asyncio.run(mod.create_incident({"summary": "disk full"}, provider="jira"))
    assert result["status"] == "created"
    assert result["incident_id"] == "OPS-1"
    assert result["external_created"] is True


def test_itsm_create_external_failure_is_502(monkeypatch):
    mod = _itsm_module()
    monkeypatch.setitem(sys.modules, "httpx", _FakeHTTPX(500, {"error": "down"}))
    monkeypatch.setattr(mod, "SERVICE_NOW_URL", "http://snow.local")
    monkeypatch.setattr(mod, "SERVICE_NOW_TOKEN", "tok")

    with pytest.raises(HTTPException) as excinfo:
        asyncio.run(mod.create_incident({"summary": "disk full"}, provider="servicenow"))
    assert excinfo.value.status_code == 502


def test_itsm_create_without_httpx_is_503(monkeypatch):
    mod = _itsm_module()
    monkeypatch.setitem(sys.modules, "httpx", None)
    # `import httpx` then resolves to None -> treated as unavailable
    monkeypatch.setattr(mod, "JIRA_URL", "http://jira.local")
    monkeypatch.setattr(mod, "JIRA_TOKEN", "tok")

    with pytest.raises(HTTPException) as excinfo:
        asyncio.run(mod.create_incident({"summary": "x"}, provider="jira"))
    assert excinfo.value.status_code == 503


def test_itsm_resolve_external_failure_is_502(monkeypatch):
    mod = _itsm_module()
    monkeypatch.setitem(sys.modules, "httpx", _FakeHTTPX(500, {"error": "down"}))
    monkeypatch.setattr(mod, "JIRA_URL", "http://jira.local")
    monkeypatch.setattr(mod, "JIRA_TOKEN", "tok")

    with pytest.raises(HTTPException) as excinfo:
        asyncio.run(mod.resolve_incident("OPS-1", provider="jira"))
    assert excinfo.value.status_code == 502


# ---------------------------------------------------------------------------
# API-052 — translation export/import path whitelist
# ---------------------------------------------------------------------------
def test_translation_path_accepts_tempfile(tmp_path):
    import api.localization_resource_router as mod

    target = tmp_path / "translations.json"
    resolved = mod._validate_translation_path(str(target))
    assert resolved == str(target.resolve())


def test_translation_path_rejects_outside_root():
    import api.localization_resource_router as mod

    with pytest.raises(HTTPException) as excinfo:
        mod._validate_translation_path("/etc/passwd")
    assert excinfo.value.status_code == 400


def test_translation_path_rejects_traversal():
    import api.localization_resource_router as mod

    with pytest.raises(HTTPException):
        mod._validate_translation_path("../../../../etc/shadow")


def test_translation_path_rejects_empty():
    import api.localization_resource_router as mod

    with pytest.raises(HTTPException) as excinfo:
        mod._validate_translation_path("   ")
    assert excinfo.value.status_code == 400


# ---------------------------------------------------------------------------
# API-067 — remote health probes require authentication
# ---------------------------------------------------------------------------
def _health_client():
    from api import health_router

    app = FastAPI()
    app.include_router(health_router.router)
    return TestClient(app)


def test_health_detailed_remote_requires_bearer():
    client = _health_client()
    resp = client.get("/api/v1/health/detailed")
    assert resp.status_code == 401


def test_health_trigger_remote_requires_bearer():
    client = _health_client()
    resp = client.post("/api/v1/health/check")
    assert resp.status_code == 401


def test_health_detailed_with_bearer_reaches_probe():
    client = _health_client()
    resp = client.get("/api/v1/health/detailed", headers={"Authorization": "Bearer t"})
    assert resp.status_code != 401


# ---------------------------------------------------------------------------
# API-074 — root cause engine public accessors
# ---------------------------------------------------------------------------
def test_root_cause_engine_public_accessors():
    from core.root_cause_intelligence import RootCauseIntelligenceEngine

    engine = RootCauseIntelligenceEngine()
    assert engine.get_topology_summary()["total_nodes"] == len(engine.topology_graph)
    assert engine.list_topology_nodes() == {}
    assert engine.list_active_hypotheses() == []
    assert engine.get_hypothesis("missing") is None
    assert engine.remove_hypothesis("missing") is False


def test_root_cause_router_does_not_touch_private_state():
    import inspect

    import api.root_cause_router as mod

    source = inspect.getsource(mod)
    assert "_get_topology_summary()" not in source
    assert ".topology_graph" not in source
    assert ".active_hypotheses" not in source
    assert "hypothesis_history" not in source


# ---------------------------------------------------------------------------
# API-078 — tracing metrics are measured, deterministic values
# ---------------------------------------------------------------------------
def test_tracing_aggregate_traces_measures_real_values():
    import api.tracing_router as mod

    stats = mod._aggregate_traces([{"duration_ms": 10.0}, {"duration_ms": 30.0}])
    assert stats["avg"] == 20.0
    assert stats["max"] == 30.0
    assert stats["p99"] > 0


def test_tracing_stable_seed_is_deterministic():
    import api.tracing_router as mod

    assert mod._stable_seed("svc") == mod._stable_seed("svc")
    assert mod._stable_seed("svc") != mod._stable_seed("other")


def test_tracing_dashboard_latency_is_not_constant():
    import api.tracing_router as mod

    client = TestClient(_app_for(mod.router))
    resp = client.get("/api/tracing/dashboard")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["avg_latency"] != 42.0
    assert data["metrics_source"] == "alert_history+sampled_traces"


def test_tracing_hotspots_use_measured_latency():
    import api.tracing_router as mod

    client = TestClient(_app_for(mod.router))
    resp = client.get("/api/tracing/performance/hotspots")
    assert resp.status_code == 200
    body = resp.json()["data"]
    assert body["slow_operations"]
    for op in body["slow_operations"]:
        assert op["avg_duration_ms"] > 0
        assert op["avg_duration_ms"] <= op["p99_duration_ms"]
    # host resource bottlenecks are real psutil probes, never fabricated
    assert all(b["service"] == "host" for b in body["resource_bottlenecks"])


# ---------------------------------------------------------------------------
# API-080 — chaos error branches use the declared status codes
# ---------------------------------------------------------------------------
def test_chaos_error_response_status_codes():
    import api.chaos_router as mod

    resp = mod._error_response(400, "bad", "INVALID_EXPERIMENT")
    assert resp.status_code == 400
    resp = mod._error_response(500, "boom", "EXPERIMENT_ERROR")
    assert resp.status_code == 500


def test_chaos_invalid_experiment_returns_400():
    import api.chaos_router as mod

    client = TestClient(_app_for(mod.router))
    resp = client.post("/api/v1/chaos/experiment/not_a_real_type", json={})
    assert resp.status_code == 400
    assert resp.json()["success"] is False


# ---------------------------------------------------------------------------
# API-087 — gRPC service deletion keeps manager state in sync
# ---------------------------------------------------------------------------
def test_grpc_delete_service_via_manager():
    from core.grpc_service_manager import GRPCServiceManager

    manager = GRPCServiceManager()
    created = manager.create_monitoring_service()
    name = created.service_name
    assert manager.get_service(name) is not None
    assert manager.get_service_methods(name)

    assert manager.delete_service(name) is True
    assert manager.get_service(name) is None
    assert manager.get_service_methods(name) == []
    assert manager.delete_service(name) is False


def test_grpc_router_uses_manager_api():
    import inspect

    import api.grpc_service_router as mod

    source = inspect.getsource(mod)
    assert "manager.services[" not in source
    assert "manager.methods" not in source
    assert "total_services_defined" not in source


# ---------------------------------------------------------------------------
# API-099 — case_sensitive actually changes the grep invocation
# ---------------------------------------------------------------------------
def _fake_linux_collector(raw_value):
    sem = MagicMock()
    ssh = AsyncMock(return_value=raw_value)
    module = types.SimpleNamespace(
        _get_host_semaphore=MagicMock(return_value=sem),
        _ssh_execute=ssh,
    )
    return module


@pytest.mark.asyncio
async def test_search_linux_logs_case_sensitive_command(monkeypatch):
    import core.log_collector as lc

    fake = _fake_linux_collector("Jan 15 10:30:45 ERROR here")
    monkeypatch.setitem(sys.modules, "core.linux_collector", fake)

    await lc.search_linux_logs({"host": "h1"}, "error", 50, case_sensitive=True)
    cmd_case = fake._ssh_execute.await_args.args[1]
    assert "grep 'error'" in cmd_case
    assert "grep -i 'error'" not in cmd_case

    fake._ssh_execute.reset_mock()
    await lc.search_linux_logs({"host": "h1"}, "error", 50, case_sensitive=False)
    cmd_insensitive = fake._ssh_execute.await_args.args[1]
    assert "grep -i 'error'" in cmd_insensitive


# ---------------------------------------------------------------------------
# API-102 — view-modes guards the unavailable state
# ---------------------------------------------------------------------------
def test_frontend_view_modes_guards_unavailable(monkeypatch):
    import api.frontend_enhancement_router as mod

    monkeypatch.setattr(mod, "FRONTEND_AVAILABLE", False)
    with pytest.raises(HTTPException) as excinfo:
        asyncio.run(mod.get_view_modes())
    assert excinfo.value.status_code == 503


def test_frontend_view_modes_returns_modes():
    import api.frontend_enhancement_router as mod

    result = asyncio.run(mod.get_view_modes())
    assert result["status"] == "success"
    assert result["view_modes"]


# ---------------------------------------------------------------------------
# API-104 — metric timestamp parsing
# ---------------------------------------------------------------------------
def test_parse_metric_timestamp_variants():
    import api.alert_router as mod

    assert mod._parse_metric_timestamp("2026-09-13T10:00:00Z").year == 2026
    assert mod._parse_metric_timestamp("2026-09-13 10:00:00").hour == 10
    assert mod._parse_metric_timestamp("10:30:00").hour == 10
    with pytest.raises(ValueError):
        mod._parse_metric_timestamp("not-a-time")


def _app_for(router):
    app = FastAPI()
    app.include_router(router)
    return app


# ---------------------------------------------------------------------------
# API-058 — the RBAC middleware must reject revoked (logged-out) tokens
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_rbac_middleware_rejects_revoked_token(monkeypatch):
    import api.middleware.rbac_middleware as mw
    import core.token_blacklist as tbl
    from starlette.requests import Request
    from starlette.responses import JSONResponse

    monkeypatch.delenv("TEST_MODE", raising=False)
    monkeypatch.setattr(
        mw, "decode_token", lambda token: {"jti": "revoked-jti", "role": "admin"}
    )
    monkeypatch.setattr(tbl, "is_blacklisted", lambda jti: jti == "revoked-jti")

    middleware = mw.RBACMiddleware(app=None)
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/v1/alerts",
        "headers": [(b"authorization", b"Bearer a.b.c")],
        "query_string": b"",
        "scheme": "http",
        "server": ("testserver", 80),
        "client": ("10.0.0.1", 1234),
    }
    request = Request(scope)

    async def call_next(_request):
        return JSONResponse({"ok": True})

    response = await middleware.dispatch(request, call_next)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_rbac_middleware_allows_unrevoked_token(monkeypatch):
    import api.middleware.rbac_middleware as mw
    import core.token_blacklist as tbl
    from starlette.requests import Request
    from starlette.responses import JSONResponse

    monkeypatch.delenv("TEST_MODE", raising=False)
    monkeypatch.setattr(
        mw, "decode_token", lambda token: {"jti": "good-jti", "role": "admin"}
    )
    monkeypatch.setattr(tbl, "is_blacklisted", lambda jti: False)

    middleware = mw.RBACMiddleware(app=None)
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/v1/alerts",
        "headers": [(b"authorization", b"Bearer a.b.c")],
        "query_string": b"",
        "scheme": "http",
        "server": ("testserver", 80),
        "client": ("10.0.0.1", 1234),
    }
    request = Request(scope)

    async def call_next(_request):
        return JSONResponse({"ok": True})

    response = await middleware.dispatch(request, call_next)
    assert response.status_code == 200
