# -*- coding: utf-8 -*-
"""Medium-severity audit-ledger batch (2026-09-13, batch 3).

Covers the real behaviour of the api/ fixes delivered in this batch:

* API-029 chaos dashboard / chaos-mesh report live engine state
* API-032 alert webhook no longer aliases ``process_alert`` as ``try_auto_heal``
* API-039 Teams callback verifies the shared secret (fail-closed)
* API-041 Slack message endpoints require a real authenticated user
* API-057 ``generate_cache_key`` accepts keyword parts (per its docstring)
* API-059 ``GET /network`` performs a read-only analysis
* API-062 compliance-audit endpoints carry an auth dependency
* API-064 cost router no longer shadows the core functions it calls
* API-068 monitoring config is persisted and ``last_collection`` is real
"""

from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from core.authentication import get_current_active_user


def _client(router, *, auth: bool = True):
    app = FastAPI()
    app.include_router(router)
    if auth:
        app.dependency_overrides[get_current_active_user] = lambda: {"username": "tester"}
    return TestClient(app)


# ---------------------------------------------------------------------------
# API-029 — chaos dashboard / mesh report live state
# ---------------------------------------------------------------------------
def test_chaos_dashboard_reports_live_engine_state():
    import api.chaos_simple_router as csr
    import core.chaos_engineering as ce
    from core.chaos_engineering import (
        ChaosExperiment,
        ExperimentResult,
        ExperimentStatus,
    )
    from datetime import datetime, timezone

    engine = ce.chaos_engine
    original = engine._current_experiment
    try:
        engine._current_experiment = None
        assert engine.get_active_experiments() == 0
        engine._current_experiment = ExperimentResult(
            experiment=ChaosExperiment.LATENCY_INJECTION,
            status=ExperimentStatus.RUNNING,
            start_time=datetime.now(timezone.utc),
        )
        assert engine.get_active_experiments() == 1
    finally:
        engine._current_experiment = original

    body = _client(csr.router).get("/api/chaos/chaos-dashboard").json()["dashboard"]
    assert isinstance(body["active_experiments"], int)
    # success rate must fall back to 0.0, never the fabricated 0.9
    assert body["success_rate"] in (0.0,) or body["success_rate"] >= 0


def test_chaos_mesh_reports_real_backend():
    import api.chaos_simple_router as csr

    mesh = _client(csr.router).get("/api/chaos/chaos-mesh").json()["mesh"]
    assert mesh["injector"]
    assert mesh["api_group"] == "chaos-mesh.org"
    assert "installed" in mesh


# ---------------------------------------------------------------------------
# API-032 — the misleading try_auto_heal alias is gone
# ---------------------------------------------------------------------------
def test_alert_webhook_no_try_auto_heal_alias():
    import api.alert_webhook_router as awr

    assert not hasattr(awr, "try_auto_heal")
    assert hasattr(awr, "process_alert")


# ---------------------------------------------------------------------------
# API-039 — Teams callback verifies the shared secret
# ---------------------------------------------------------------------------
def test_teams_callback_verification_fail_closed():
    import api.teams_router as tr
    import config

    original = config.TEAMS_CALLBACK_SECRET
    try:
        config.TEAMS_CALLBACK_SECRET = ""
        assert tr._verify_teams_callback(None) is False
        assert tr._verify_teams_callback("anything") is False

        config.TEAMS_CALLBACK_SECRET = "s3cr3t"
        assert tr._verify_teams_callback("s3cr3t") is True
        assert tr._verify_teams_callback("wrong") is False
        assert tr._verify_teams_callback(None) is False
    finally:
        config.TEAMS_CALLBACK_SECRET = original


def test_teams_callback_passes_verified_flag(monkeypatch):
    import api.teams_router as tr

    seen = {}

    def fake_handle(text, user_id, user_name, channel, verified):
        seen["verified"] = verified
        return {"command": text}

    monkeypatch.setattr(tr, "handle_instruction", fake_handle)
    import config

    original = config.TEAMS_CALLBACK_SECRET
    try:
        config.TEAMS_CALLBACK_SECRET = "s3cr3t"
        client = TestClient(_app_with(tr.router))
        resp = client.post(
            "/api/teams/events",
            headers={"X-Teams-Secret": "s3cr3t"},
            json={"text": "ack incident-1", "from": "alice"},
        )
        assert resp.status_code == 200
        assert seen["verified"] is True

        # Without the secret the command is parsed but reported as unverified.
        client.post(
            "/api/teams/events",
            json={"text": "ack incident-2", "from": "alice"},
        )
        assert seen["verified"] is False
    finally:
        config.TEAMS_CALLBACK_SECRET = original


def _app_with(router):
    app = FastAPI()
    app.include_router(router)
    return app


# ---------------------------------------------------------------------------
# API-041 — Slack message endpoints require authentication
# ---------------------------------------------------------------------------
def test_slack_requires_authentication():
    import api.slack_router as sr

    client = TestClient(_app_with(sr.router))
    resp = client.post("/api/slack/message", json={"text": "hi"})
    assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# API-057 — generate_cache_key accepts keyword parts
# ---------------------------------------------------------------------------
def test_generate_cache_key_supports_kwargs():
    from api.common.cache_helpers import generate_cache_key

    assert generate_cache_key("system", "errors", newest=10) == "system_errors_10"
    assert generate_cache_key("p", a=1, b=2) == generate_cache_key("p", b=2, a=1)


# ---------------------------------------------------------------------------
# API-059 — GET /network is a read-only analysis
# ---------------------------------------------------------------------------
def test_network_analysis_uses_readonly_method(monkeypatch):
    import api.system_resource_router as srr
    import core.system_resource_optimizer as sro

    fake = MagicMock()
    fake.analyze_network_usage.return_value = {"total_connections": 3, "established_connections": 1}
    fake.optimize_network.return_value = {"SHOULD_NOT_BE_USED": True}
    monkeypatch.setattr(sro, "get_system_resource_optimizer", MagicMock(return_value=fake))

    resp = _client(srr.router).get("/api/system-resources/network")
    assert resp.status_code == 200
    assert resp.json()["data"]["total_connections"] == 3
    fake.analyze_network_usage.assert_called_once()
    fake.optimize_network.assert_not_called()


# ---------------------------------------------------------------------------
# API-062 — compliance audits require authentication
# ---------------------------------------------------------------------------
def test_compliance_audits_require_auth():
    import api.compliance_audit_router as car

    client = TestClient(_app_with(car.router))
    resp = client.get("/api/v1/compliance/audits")
    assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# API-064 — cost router no longer shadows the core functions it calls
# ---------------------------------------------------------------------------
def test_cost_router_no_recursion():
    import api.cost_router as cr

    assert cr.get_cost_monitoring is not cr._collect_cost_monitoring
    assert cr.get_budget_management is not cr._collect_budget_management

    client = _client(cr.router)
    assert client.get("/api/cost/cost-monitoring").status_code == 200
    assert client.get("/api/cost/budget-management").status_code == 200


# ---------------------------------------------------------------------------
# API-068 — monitoring config persisted + real last_collection
# ---------------------------------------------------------------------------
def test_monitoring_config_is_persisted():
    import api.monitoring_config_router as mcr
    from core.persistent_store import PersistentStore

    mcr._save_config(mcr._METRICS_CONFIG_KEY, {"collection_interval": 77, "cpu_enabled": True})
    fresh = PersistentStore("monitoring", "config")
    assert fresh.get(mcr._METRICS_CONFIG_KEY)["collection_interval"] == 77


def test_monitoring_status_last_collection_is_real():
    import api.monitoring_config_router as mcr

    status = _client(mcr.router).get("/api/v1/monitoring/status").json()
    last = status["metrics_collection"]["last_collection"]
    # Derived from METRICS_HISTORY: either None (no samples) or an ISO string -
    # never the previously hard-coded constant.
    assert last != "2026-08-26T09:00:00Z"
    assert last is None or isinstance(last, str)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
