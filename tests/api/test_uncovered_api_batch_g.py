# -*- coding: utf-8 -*-
"""Real API tests for uncovered routers (batch G)."""

import asyncio  # noqa: F401  # Imported for test setup
import datetime
import json  # noqa: F401  # Imported for test setup
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest  # noqa: F401  # Imported for test setup

pytestmark = [pytest.mark.api]


def _async_return(value):
    """Return an async callable that returns *value*."""

    async def _inner(*args, **kwargs):
        return value

    return _inner


def _async_raise(exc):
    """Return an async callable that raises *exc*."""

    async def _inner(*args, **kwargs):
        raise exc

    return _inner


class _FakeUserService:
    """In-memory stand-in for core.user_service.user_service."""

    def __init__(self):
        self._users = {}
        self._counter = 1
        self._users["admin"] = SimpleNamespace(
            id=0,
            username="admin",
            email="admin@example.com",
            full_name="Admin User",
            role="admin",
            disabled=False,
            mfa_enabled=False,
            hashed_password="",
            created_at=datetime.datetime.utcnow(),
            last_login_at=None,
        )
        self._counter += 1

    async def get_user_by_username(self, username: str):
        return self._users.get(username)

    async def get_user_by_email(self, email: str):
        for user in self._users.values():
            if user.email == email:  # noqa: F841  # Variable for test verification
                return user
        return None

    async def create_user(self, username, hashed_password, email=None, full_name=None, role="user"):
        if username in self._users:
            return None
        user = SimpleNamespace(
            id=self._counter,
            username=username,
            email=email,
            full_name=full_name,
            hashed_password=hashed_password,
            role=role,
            disabled=False,
            mfa_enabled=False,
            created_at=datetime.datetime.utcnow(),
            last_login_at=None,
        )
        self._users[username] = user
        self._counter += 1
        return user

    async def list_users(self, limit=100, offset=0):
        return list(self._users.values())[offset : offset + limit]

    async def update_user(self, username, email=None, full_name=None, role=None, disabled=None):
        user = self._users.get(username)
        if not user:
            return False
        if email is not None:
            user.email = email  # noqa: F841  # Variable for test verification
        if full_name is not None:
            user.full_name = full_name
        if role is not None:
            user.role = role
        if disabled is not None:
            user.disabled = disabled
        return True

    async def update_password(self, username, hashed_password):
        user = self._users.get(username)
        if not user:
            return False
        user.hashed_password = hashed_password
        return True

    async def delete_user(self, username):
        return self._users.pop(username, None) is not None


class _FakeMfaService:
    """Fake MFA service."""

    async def is_mfa_enabled(self, username: str) -> bool:
        return False

    async def enable_mfa_for_user(self, username: str):
        return ("fake-secret", "data:image/png;base64,fake", ["code1", "code2"])

    async def disable_mfa_for_user(self, username: str) -> bool:
        return True

    async def get_mfa_status(self, username: str) -> dict:
        return {"enabled": False, "method": "totp"}


class _FakeAuditService:
    """Fake audit service."""

    async def log_action(self, **kwargs):
        return None

    async def get_audit_logs(self, **kwargs):
        return [
            {
                "id": 1,
                "action": "login",
                "resource_type": "user",
                "resource_id": "1",
                "username": "admin",
                "ip_address": "127.0.0.1",
                "status": "success",
                "details": "",
                "created_at": None,
            }
        ]


class _FakeResourceManager:
    """Fake localization resource manager."""

    def get_resource_summary(self):
        return {"total_languages": 2, "total_translations": 10}

    def get_translations(self, language: str, namespace: str):
        return {"hello": "world"}

    def add_translation(self, language: str, namespace: str, key: str, value: str):
        return True

    def export_translations(self, language: str, namespace: str, output_path: str):
        return True

    def import_translations(self, language: str, namespace: str, input_path: str):
        return True

    def get_missing_translations(self, source_language: str, target_language: str, namespace: str):
        return ["missing"]


class _FakeAdapter:
    """Fake localization adapter."""

    def get_adapter_summary(self):
        return {"available": True, "current_locale": "zh-CN"}

    def get_supported_locales(self):
        return ["zh-CN", "en-US"]

    def set_current_locale(self, locale_id: str):
        return True

    def format_date(self, date_obj, format_type, locale=None):
        return "2026-07-03"

    def format_datetime(self, datetime_obj, format_type, locale=None):
        return "2026-07-03 10:00"

    def format_number(self, number, format_type, locale=None, decimals=2):
        return "1.23"

    def format_currency(self, amount, currency_code=None, locale=None, decimals=2):
        return "¥1.23"

    def format_unit(self, value, unit, target_system_enum=None, locale=None):
        return "1.23 kg"


class _FakeMeshManager:
    """Fake service mesh manager."""

    def generate_service_mesh_summary(self):
        return {"mesh_id": "mesh-1"}

    def generate_istio_control_plane_config(self, mesh_id, namespace, profile):
        return SimpleNamespace(
            mesh_id=mesh_id,
            control_plane_config={"namespace": namespace, "profile": profile},
            auto_injection_enabled=True,
        )

    def generate_auto_injection_config(self, namespace, enabled):
        return {"namespace": namespace, "enabled": enabled}

    def generate_virtual_service_config(self, service_name, routing_rules, namespace):
        return SimpleNamespace(service_name=service_name, routing_rules=routing_rules)

    def generate_mtls_config(self, mesh_id, namespace, strict_mode):
        return SimpleNamespace(mesh_id=mesh_id, mtls_enabled=True, authentication_policies=[])


@pytest.fixture(autouse=True)
def _patch_batch_g(monkeypatch):
    """Stub all core dependencies touched by the batch G routers."""

    # Bypass the global RBAC middleware so tests can focus on router logic.
    import api.middleware.rbac_middleware as _rbac

    async def _rbac_bypass(self, request, call_next):
        return await call_next(request)

    monkeypatch.setattr(_rbac.RBACMiddleware, "dispatch", _rbac_bypass)

    # Mount the real user_router for this batch by temporarily replacing
    # the /api/v1/users routes in the global app (users_router currently
    # shadows user_router because only users_router is wired in main.py).
    import api.user_router as _ur
    import api.users_router as _users
    from main import app

    original_routes = list(app.router.routes)  # noqa: F841  # Variable for test verification
    filtered_routes = [
        r for r in app.router.routes if not (getattr(r, "original_router", None) is _users.router)
    ]
    monkeypatch.setattr(app.router, "routes", filtered_routes + list(_ur.router.routes))

    # batch_router ----------------------------------------------------------
    import core.alert_engine as _ce
    import core.collector as _cc

    monkeypatch.setattr(
        _ce,
        "alert_history",
        [{"id": "alert-1", "title": "CPU告警", "level": "critical"}],
    )
    monkeypatch.setattr(
        _cc,
        "collect_all",
        lambda: {
            "cpu_usage": {"value": 45.2, "unit": "%"},
            "memory_usage": {"value": 68.3, "unit": "%"},
        },
    )

    # macos_router ----------------------------------------------------------
    import api.macos_router as _mr

    monkeypatch.setattr(
        _mr, "collect_macos_metrics", _async_return({"mac1": {"cpu": 0.1, "mem": 0.2}})
    )
    monkeypatch.setattr(
        _mr,
        "execute_macos_repair",
        _async_return({"success": True, "output": "repaired"}),
    )

    # service_mesh_router ---------------------------------------------------
    import core.service_mesh_manager as _smm

    monkeypatch.setattr(_smm, "get_service_mesh_manager", lambda: _FakeMeshManager())

    # team_collaboration_router ---------------------------------------------
    import api.team_collaboration_router as _tcr

    monkeypatch.setattr(_tcr, "list_teams", _async_return([{"id": "t1", "name": "T1"}]))
    monkeypatch.setattr(
        _tcr, "get_team_oncall", _async_return({"primary": "u1", "secondary": "u2"})
    )
    monkeypatch.setattr(_tcr, "create_handoff", _async_return({"handoff_id": "h1"}))
    monkeypatch.setattr(_tcr, "list_handoffs", _async_return([{"id": "h1", "notes": "n"}]))
    monkeypatch.setattr(_tcr, "escalate_incident", _async_return({"escalated": True}))
    monkeypatch.setattr(_tcr, "list_dashboards", _async_return([{"id": "d1"}]))

    # localization_resource_router ------------------------------------------
    import core.localization_resource_manager as _lrm

    monkeypatch.setattr(_lrm, "get_resource_manager", lambda: _FakeResourceManager())

    # localization_adapter_router -------------------------------------------
    import core.localization_adapter as _la

    monkeypatch.setattr(_la, "get_localization_adapter", lambda: _FakeAdapter())

    # user_router ------------------------------------------------------------
    import api.user_router as _ur

    _fake_user_service = _FakeUserService()
    _fake_user = SimpleNamespace(
        id=0,
        username="admin",
        full_name="Admin User",
        email="admin@example.com",
        role="admin",
        disabled=False,
        hashed_password="",
        created_at=None,
        last_login_at=None,
        mfa_enabled=False,
    )
    monkeypatch.setattr(_ur, "user_service", _fake_user_service)
    monkeypatch.setattr(
        _ur,
        "verify_token",
        lambda token: {"sub": "admin", "role": "admin"},
    )
    monkeypatch.setattr(_ur, "get_user", _async_return(_fake_user))
    monkeypatch.setattr(_ur, "mfa_service", _FakeMfaService())
    monkeypatch.setattr(_ur, "audit_service", _FakeAuditService())
    monkeypatch.setattr(_ur, "validate_password_complexity", lambda p: (True, ""))
    monkeypatch.setattr(_ur, "get_password_hash", lambda p: f"hash-{p}")
    monkeypatch.setattr(_ur, "verify_password", lambda plain, hashed: True)

    # stats_router -----------------------------------------------------------
    import api.stats_router as _sr

    monkeypatch.setattr(_sr, "get_real_summary", _async_return({"total_alerts": 1}))
    monkeypatch.setattr(_sr, "record_repair", _async_return(None))
    monkeypatch.setattr(_sr, "_summary_cache", {"data": None, "ts": 0.0})

    # slo_router -------------------------------------------------------------
    import api.slo_router as _slo
    import core.metrics_history as _cmh

    _fake_slo = SimpleNamespace(
        id="1",
        name="slo1",
        service="svc",
        metric="m",
        target=0.99,
        window=1,
        aggregation="good_ratio",
    )
    monkeypatch.setattr(_slo, "list_slos", lambda: [_fake_slo])
    monkeypatch.setattr(_slo, "get_slo", lambda sid: _fake_slo if sid == "1" else None)
    monkeypatch.setattr(_slo, "create_slo", lambda **kwargs: _fake_slo)
    monkeypatch.setattr(_slo, "update_slo", lambda sid, **kwargs: _fake_slo)
    monkeypatch.setattr(_slo, "delete_slo", lambda sid: True)
    monkeypatch.setattr(_slo, "parse_window", lambda w: 1)
    monkeypatch.setattr(_slo, "format_window", lambda h: "1h")
    monkeypatch.setattr(
        _slo,
        "evaluate_slo",
        lambda rule, points: {
            "current": 0.99,
            "error_budget_remaining_percent": 0.95,
            "burn_rate": 1.0,
            "status": "ok",
        },
    )
    monkeypatch.setattr(_slo.metrics_history, "query", lambda *args, **kwargs: [])
    monkeypatch.setattr(_slo, "generate_sla_report", lambda period: [{"id": "new"}])
    monkeypatch.setattr(_slo, "save_sla_reports", lambda reports: ["new"])
    monkeypatch.setattr(
        _slo, "list_sla_reports", lambda period=None: [{"id": "r1", "period": period or "30d"}]
    )
    monkeypatch.setattr(_slo, "get_sla_report", lambda rid: {"id": rid, "period": "30d"})
    monkeypatch.setattr(_slo, "delete_sla_report", lambda rid: True)

    def _fake_user_factory(*roles, **kwargs):
        def _get_user():
            return SimpleNamespace(username="admin", role="admin")

        return _get_user

    async def _fake_current_user_or_internal(*args, **kwargs):
        return SimpleNamespace(username="admin", role="admin")

    monkeypatch.setattr(_slo, "require_roles", _fake_user_factory)
    monkeypatch.setattr(_slo, "_get_current_user_or_internal", _fake_current_user_or_internal)

    # linux_router -----------------------------------------------------------
    import api.linux_router as _lrx

    # these three helpers are called synchronously by the router
    monkeypatch.setattr(
        _lrx,
        "get_configured_hosts",
        lambda: [{"name": "h1", "host": "1.1.1.1", "role": "app"}],
    )
    monkeypatch.setattr(_lrx, "get_available_metrics", lambda: [{"key": "cpu", "name": "CPU"}])
    monkeypatch.setattr(
        _lrx,
        "collect_all_linux",
        _async_return([{"host": "h1", "cpu": 1.0}]),
    )
    monkeypatch.setattr(
        _lrx,
        "collect_linux_host",
        _async_return({"host": "h1", "cpu": {"usage_percent": 1.0}}),
    )
    monkeypatch.setattr(_lrx, "get_linux_repair_scripts", lambda: [{"key": "clear_tmp"}])
    monkeypatch.setattr(
        _lrx,
        "execute_linux_repair",
        _async_return({"success": True, "output": "ok", "exit_code": 0}),
    )
    monkeypatch.setattr(
        _lrx, "find_linux_host_config", lambda host: {"name": host, "host": "1.1.1.1"}
    )
    monkeypatch.setattr(_lrx, "LINUX_HOSTS", {"h1": {"name": "h1", "host": "1.1.1.1"}})

    # workflow_router --------------------------------------------------------
    import api.workflow_router as _wr

    _fake_wf_definitions = {"wf1": {"key": "wf1", "name": "WF1"}}
    monkeypatch.setattr(_wr, "WORKFLOW_DEFINITIONS", _fake_wf_definitions)
    monkeypatch.setattr(_wr, "get_workflow_definitions", lambda: _fake_wf_definitions)
    monkeypatch.setattr(_wr, "create_workflow_definition", lambda key, payload: {"created": key})
    monkeypatch.setattr(_wr, "update_workflow_definition", lambda key, payload: {"updated": key})
    monkeypatch.setattr(_wr, "delete_workflow_definition", lambda key: None)

    async def _fake_sim_stream(key):
        yield {"type": "workflow_start", "wf_name": "WF1"}
        yield {"type": "step_complete", "node_key": "n1"}
        yield {"type": "workflow_done", "total_ms": 10}

    monkeypatch.setattr(_wr, "simulate_workflow_stream", _fake_sim_stream)
    monkeypatch.setattr(_wr, "parse_json_workflow", lambda s: SimpleNamespace())

    async def _fake_executor_execute(dag):
        return SimpleNamespace(
            workflow_id="w1",
            run_id="r1",
            status=SimpleNamespace(value="completed"),
            results={},
            errors={},
        )

    monkeypatch.setattr(_wr._executor, "execute", _fake_executor_execute)

    # tracing_router uses config.LINUX_HOSTS inside _services() ---------------
    import config as _cfg

    monkeypatch.setattr(_cfg, "LINUX_HOSTS", ["h1", "h2"])


# =============================================================================
# batch_router
# =============================================================================


def test_batch_alerts(client):
    resp = client.post("/api/v1/batch/alerts", json=["alert-1", "alert-2"])
    assert resp.status_code == 200
    data = resp.json()
    assert data["results"][0]["id"] == "alert-1"
    assert data["results"][1] is None


def test_batch_alerts_exception(client, monkeypatch):
    import core.alert_engine as _ce

    monkeypatch.setattr(_ce, "alert_history", object())
    resp = client.post("/api/v1/batch/alerts", json=["alert-1"])
    assert resp.status_code == 200
    assert resp.json()["results"] == [None]


def test_batch_metrics(client):
    resp = client.post("/api/v1/batch/metrics", json=["cpu_usage", "missing"])
    assert resp.status_code == 200
    data = resp.json()
    assert "cpu_usage" in data["results"]
    assert "missing" not in data["results"]


def test_batch_metrics_error(client, monkeypatch):
    import core.collector as _cc

    def _raise():
        raise Exception("boom")

    monkeypatch.setattr(_cc, "collect_all", _raise)
    resp = client.post("/api/v1/batch/metrics", json=["cpu_usage"])
    assert resp.status_code == 500


# =============================================================================
# macos_router
# =============================================================================


def test_macos_metrics(client):
    resp = client.get("/api/macos/metrics", params={"hosts": ["mac1"]})
    assert resp.status_code == 200
    assert "mac1" in resp.json()


def test_macos_metrics_error(client, monkeypatch):
    import api.macos_router as _mr

    monkeypatch.setattr(_mr, "collect_macos_metrics", _async_raise(Exception("boom")))
    resp = client.get("/api/macos/metrics")
    assert resp.status_code == 500


def test_macos_repair(client):
    resp = client.post("/api/macos/repair?host=mac1&script_name=clear")
    assert resp.status_code == 200
    data = resp.json()
    assert data["host"] == "mac1"
    assert data["result"]["success"] is True


def test_macos_repair_error(client, monkeypatch):
    import api.macos_router as _mr

    monkeypatch.setattr(_mr, "execute_macos_repair", _async_raise(Exception("boom")))
    resp = client.post("/api/macos/repair?host=mac1&script_name=clear")
    assert resp.status_code == 500


# =============================================================================
# service_mesh_router
# =============================================================================


def test_mesh_status(client):
    resp = client.get("/api/service-mesh/status")
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"


def test_mesh_istio_control_plane(client):
    resp = client.post(
        "/api/service-mesh/istio/control-plane",
        params={"mesh_id": "m1", "namespace": "istio-system", "profile": "default"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["data"]["mesh_id"] == "m1"


def test_mesh_auto_injection(client):
    resp = client.post(
        "/api/service-mesh/istio/auto-injection",
        params={"namespace": "default", "enabled": True},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["enabled"] is True


def test_mesh_virtual_service(client):
    resp = client.post(
        "/api/service-mesh/istio/virtual-service",
        params={"service_name": "svc", "namespace": "default"},
        json={"weight": 100},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["data"]["service_name"] == "svc"


def test_mesh_mtls(client):
    resp = client.post(
        "/api/service-mesh/istio/mtls",
        params={"mesh_id": "m1", "namespace": "istio-system", "strict_mode": True},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["mtls_enabled"] is True


def test_mesh_error(client, monkeypatch):
    import core.service_mesh_manager as _smm

    monkeypatch.setattr(
        _smm, "get_service_mesh_manager", lambda: (_ for _ in ()).throw(Exception("boom"))
    )
    resp = client.get("/api/service-mesh/status")
    assert resp.status_code == 500


# =============================================================================
# team_collaboration_router
# =============================================================================


def test_team_teams(client):
    resp = client.get("/api/v1/team-collaboration/teams")
    assert resp.status_code == 200
    assert resp.json()[0]["id"] == "t1"


def test_team_oncall(client):
    resp = client.get("/api/v1/team-collaboration/teams/t1/oncall")
    assert resp.status_code == 200
    assert resp.json()["primary"] == "u1"


def test_team_oncall_no_primary(client, monkeypatch):
    import api.team_collaboration_router as _tcr

    monkeypatch.setattr(_tcr, "get_team_oncall", _async_return({"primary": "", "secondary": ""}))
    resp = client.get("/api/v1/team-collaboration/teams/t1/oncall")
    assert resp.status_code == 404


def test_team_oncall_not_found(client, monkeypatch):
    import api.team_collaboration_router as _tcr

    monkeypatch.setattr(_tcr, "get_team_oncall", _async_raise(ValueError("no team")))
    resp = client.get("/api/v1/team-collaboration/teams/t1/oncall")
    assert resp.status_code == 404


def test_team_handoff_create(client):
    resp = client.post(
        "/api/v1/team-collaboration/teams/t1/handoffs",
        json={"from_user_id": "u1", "to_user_id": "u2", "notes": "handoff"},
    )
    assert resp.status_code == 201


def test_team_handoff_create_not_found(client, monkeypatch):
    import api.team_collaboration_router as _tcr

    monkeypatch.setattr(_tcr, "create_handoff", _async_raise(ValueError("no team")))
    resp = client.post(
        "/api/v1/team-collaboration/teams/t1/handoffs",
        json={"from_user_id": "u1", "to_user_id": "u2", "notes": "handoff"},
    )
    assert resp.status_code == 404


def test_team_handoffs_list(client):
    resp = client.get("/api/v1/team-collaboration/teams/t1/handoffs")
    assert resp.status_code == 200


def test_team_handoffs_list_not_found(client, monkeypatch):
    import api.team_collaboration_router as _tcr

    monkeypatch.setattr(_tcr, "list_handoffs", _async_raise(ValueError("no team")))
    resp = client.get("/api/v1/team-collaboration/teams/t1/handoffs")
    assert resp.status_code == 404


def test_team_escalate(client):
    resp = client.post(
        "/api/v1/team-collaboration/incidents/i1/escalate",
        json={"team_id": "t1", "reason": "urgent"},
    )
    assert resp.status_code == 200


def test_team_escalate_bad(client, monkeypatch):
    import api.team_collaboration_router as _tcr

    monkeypatch.setattr(_tcr, "escalate_incident", _async_raise(ValueError("bad")))
    resp = client.post(
        "/api/v1/team-collaboration/incidents/i1/escalate",
        json={"team_id": "t1", "reason": "urgent"},
    )
    assert resp.status_code == 400


def test_team_dashboards(client):
    resp = client.get("/api/v1/team-collaboration/dashboards")
    assert resp.status_code == 200


def test_team_dashboards_error(client, monkeypatch):
    import api.team_collaboration_router as _tcr

    monkeypatch.setattr(_tcr, "list_dashboards", _async_raise(Exception("boom")))
    resp = client.get("/api/v1/team-collaboration/dashboards")
    assert resp.status_code == 500


# =============================================================================
# localization_resource_router
# =============================================================================


def test_localization_status(client):
    resp = client.get("/api/localization/status")
    assert resp.status_code == 200


def test_localization_translations(client):
    resp = client.get("/api/localization/translations?language=zh-CN&namespace=common")
    assert resp.status_code == 200
    assert resp.json()["data"]["translations"]["hello"] == "world"


def test_localization_translations_not_found(client, monkeypatch):
    import core.localization_resource_manager as _lrm

    class _Empty(_FakeResourceManager):
        def get_translations(self, language, namespace):
            return {}

    monkeypatch.setattr(_lrm, "get_resource_manager", lambda: _Empty())
    resp = client.get("/api/localization/translations?language=zh-CN&namespace=common")
    assert resp.status_code == 404


def test_localization_add(client):
    resp = client.post(
        "/api/localization/translation/add?language=zh-CN&namespace=common&key=k&value=v"
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["added"] is True


def test_localization_export(client):
    resp = client.post(
        "/api/localization/translation/export?language=zh-CN&namespace=common&output_path=/tmp/out.json"  # noqa: E501  # Line too long (intentional)
    )
    assert resp.status_code == 200


def test_localization_import(client):
    resp = client.post(
        "/api/localization/translation/import?language=zh-CN&namespace=common&input_path=/tmp/in.json"  # noqa: E501  # Line too long (intentional)
    )
    assert resp.status_code == 200


def test_localization_missing(client):
    resp = client.get(
        "/api/localization/translations/missing?source_language=en&target_language=zh-CN&namespace=common"  # noqa: E501  # Line too long (intentional)
    )
    assert resp.status_code == 200
    assert "missing" in resp.json()["data"]["missing_keys"]


def test_localization_error(client, monkeypatch):
    import core.localization_resource_manager as _lrm

    monkeypatch.setattr(
        _lrm, "get_resource_manager", lambda: (_ for _ in ()).throw(Exception("boom"))
    )
    resp = client.get("/api/localization/status")
    assert resp.status_code == 500


# =============================================================================
# localization_adapter_router
# =============================================================================


def test_adapter_status(client):
    resp = client.get("/api/localization-adapter/status")
    assert resp.status_code == 200


def test_adapter_locales(client):
    resp = client.get("/api/localization-adapter/locales")
    assert resp.status_code == 200
    assert resp.json()["data"]["count"] == 2


def test_adapter_set_locale(client):
    resp = client.post("/api/localization-adapter/locale/set?locale_id=zh-CN")
    assert resp.status_code == 200
    assert resp.json()["data"]["set"] is True


def test_adapter_format_date(client):
    resp = client.get(
        "/api/localization-adapter/format/date?date_str=2026-07-03&format_type=short&locale=zh-CN"
    )
    assert resp.status_code == 200


def test_adapter_format_date_error(client):
    resp = client.get("/api/localization-adapter/format/date?date_str=invalid&format_type=short")
    assert resp.status_code == 500


def test_adapter_format_datetime(client):
    resp = client.get(
        "/api/localization-adapter/format/datetime?datetime_str=2026-07-03T10:00:00&format_type=full"  # noqa: E501  # Line too long (intentional)
    )
    assert resp.status_code == 200


def test_adapter_format_number(client):
    resp = client.get(
        "/api/localization-adapter/format/number?number=1.234&format_type=decimal&locale=zh-CN"
    )
    assert resp.status_code == 200


def test_adapter_format_currency(client):
    resp = client.get(
        "/api/localization-adapter/format/currency?amount=9.9&currency_code=CNY&locale=zh-CN"
    )
    assert resp.status_code == 200


def test_adapter_format_unit(client):
    resp = client.get(
        "/api/localization-adapter/format/unit?value=1.5&unit=kg&target_system=metric&locale=zh-CN"
    )
    assert resp.status_code == 200


def test_adapter_error(client, monkeypatch):
    import core.localization_adapter as _la

    class _Bad(_FakeAdapter):
        def get_supported_locales(self):
            raise Exception("boom")

    monkeypatch.setattr(_la, "get_localization_adapter", lambda: _Bad())
    resp = client.get("/api/localization-adapter/locales")
    assert resp.status_code == 500


# =============================================================================
# user_router
# =============================================================================


def test_user_create(client, admin_headers):
    resp = client.post(
        "/api/v1/users/",
        headers=admin_headers,
        json={
            "username": "batchuser",
            "email": "batch@example.com",
            "full_name": "Batch User",
            "password": "ComplexPass123!",
            "role": "operator",
        },
    )
    assert resp.status_code == 201
    assert resp.json()["username"] == "batchuser"


def test_user_create_invalid_password(client, admin_headers, monkeypatch):
    import api.user_router as _ur

    monkeypatch.setattr(_ur, "validate_password_complexity", lambda p: (False, "weak"))
    resp = client.post(
        "/api/v1/users/",
        headers=admin_headers,
        json={
            "username": "batchuser2",
            "email": "batch2@example.com",
            "full_name": "Batch User",
            "password": "shortpasswor",
            "role": "operator",
        },
    )
    assert resp.status_code == 400


def test_user_create_conflict(client, admin_headers, monkeypatch):
    import api.user_router as _ur

    monkeypatch.setattr(_ur.user_service, "get_user_by_username", _async_return(SimpleNamespace()))
    resp = client.post(
        "/api/v1/users/",
        headers=admin_headers,
        json={
            "username": "batchuser",
            "email": "batch@example.com",
            "full_name": "Batch User",
            "password": "ComplexPass123!",
            "role": "operator",
        },
    )
    assert resp.status_code == 409


def test_user_create_server_error(client, admin_headers, monkeypatch):
    import api.user_router as _ur

    monkeypatch.setattr(_ur.user_service, "create_user", _async_return(None))
    resp = client.post(
        "/api/v1/users/",
        headers=admin_headers,
        json={
            "username": "batchuser",
            "email": "batch@example.com",
            "full_name": "Batch User",
            "password": "ComplexPass123!",
            "role": "operator",
        },
    )
    assert resp.status_code == 500


def test_user_list(client, admin_headers):
    resp = client.get("/api/v1/users/", headers=admin_headers)
    assert resp.status_code == 200
    assert any(u["username"] == "admin" for u in resp.json())


def test_user_me(client, admin_headers):
    resp = client.get("/api/v1/users/me", headers=admin_headers)
    assert resp.status_code == 200


def test_user_audit_logs(client, admin_headers):
    resp = client.get("/api/v1/users/audit-logs", headers=admin_headers)
    assert resp.status_code == 200


def test_user_get(client, admin_headers):
    resp = client.get("/api/v1/users/admin", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["username"] == "admin"


def test_user_get_not_found(client, admin_headers, monkeypatch):
    import api.user_router as _ur

    monkeypatch.setattr(_ur.user_service, "get_user_by_username", _async_return(None))
    resp = client.get("/api/v1/users/nobody", headers=admin_headers)
    assert resp.status_code == 404


def test_user_update(client, admin_headers):
    resp = client.put(
        "/api/v1/users/admin",
        headers=admin_headers,
        json={"full_name": "New Admin"},
    )
    assert resp.status_code == 200


def test_user_update_failed(client, admin_headers, monkeypatch):
    import api.user_router as _ur

    monkeypatch.setattr(_ur.user_service, "update_user", _async_return(False))
    resp = client.put(
        "/api/v1/users/admin",
        headers=admin_headers,
        json={"full_name": "New Admin"},
    )
    assert resp.status_code == 404


def test_user_delete(client, admin_headers):
    # create then delete a disposable user in one test
    client.post(
        "/api/v1/users/",
        headers=admin_headers,
        json={
            "username": "todelete",
            "email": "td@example.com",
            "full_name": "To Delete",
            "password": "ComplexPass123!",
            "role": "user",
        },
    )
    resp = client.delete("/api/v1/users/todelete", headers=admin_headers)
    assert resp.status_code == 204


def test_user_delete_own(client, admin_headers):
    resp = client.delete("/api/v1/users/admin", headers=admin_headers)
    assert resp.status_code == 400


def test_user_delete_not_found(client, admin_headers, monkeypatch):
    import api.user_router as _ur

    monkeypatch.setattr(_ur.user_service, "delete_user", _async_return(False))
    resp = client.delete("/api/v1/users/nobody", headers=admin_headers)
    assert resp.status_code == 404


def test_user_change_password(client, admin_headers):
    resp = client.post(
        "/api/v1/users/me/change-password",
        headers=admin_headers,
        json={"current_password": "any", "new_password": "ComplexPass123!"},
    )
    assert resp.status_code == 200


def test_user_change_password_current_wrong(client, admin_headers, monkeypatch):
    import api.user_router as _ur

    monkeypatch.setattr(_ur, "verify_password", lambda plain, hashed: False)
    resp = client.post(
        "/api/v1/users/me/change-password",
        headers=admin_headers,
        json={"current_password": "any", "new_password": "ComplexPass123!"},
    )
    assert resp.status_code == 400


def test_user_change_password_update_fail(client, admin_headers, monkeypatch):
    import api.user_router as _ur

    monkeypatch.setattr(_ur.user_service, "update_password", _async_return(False))
    resp = client.post(
        "/api/v1/users/me/change-password",
        headers=admin_headers,
        json={"current_password": "any", "new_password": "ComplexPass123!"},
    )
    assert resp.status_code == 500


def test_user_mfa_enable(client, admin_headers):
    resp = client.post(
        "/api/v1/users/me/mfa/enable",
        headers=admin_headers,
        json={"password": "any"},
    )
    assert resp.status_code == 200
    assert "secret" in resp.json()


def test_user_mfa_enable_wrong(client, admin_headers, monkeypatch):
    import api.user_router as _ur

    monkeypatch.setattr(_ur, "verify_password", lambda plain, hashed: False)
    resp = client.post(
        "/api/v1/users/me/mfa/enable",
        headers=admin_headers,
        json={"password": "any"},
    )
    assert resp.status_code == 400


def test_user_mfa_enable_already(client, admin_headers, monkeypatch):
    import api.user_router as _ur

    monkeypatch.setattr(_ur.mfa_service, "is_mfa_enabled", _async_return(True))
    resp = client.post(
        "/api/v1/users/me/mfa/enable",
        headers=admin_headers,
        json={"password": "any"},
    )
    assert resp.status_code == 400


def test_user_mfa_disable(client, admin_headers):
    resp = client.post("/api/v1/users/me/mfa/disable", headers=admin_headers)
    assert resp.status_code == 200


def test_user_mfa_disable_fail(client, admin_headers, monkeypatch):
    import api.user_router as _ur

    monkeypatch.setattr(_ur.mfa_service, "disable_mfa_for_user", _async_return(False))
    resp = client.post("/api/v1/users/me/mfa/disable", headers=admin_headers)
    assert resp.status_code == 500


def test_user_mfa_status(client, admin_headers):
    resp = client.get("/api/v1/users/me/mfa/status", headers=admin_headers)
    assert resp.status_code == 200


def test_user_my_audit_logs(client, admin_headers):
    resp = client.get("/api/v1/users/me/audit-logs", headers=admin_headers)
    assert resp.status_code == 200


def test_user_user_audit_logs(client, admin_headers):
    resp = client.get("/api/v1/users/admin/audit-logs", headers=admin_headers)
    assert resp.status_code == 200


# =============================================================================
# stats_router
# =============================================================================


def test_stats_summary(client):
    resp = client.get("/api/v1/stats/summary")
    assert resp.status_code == 200
    assert "total_alerts" in resp.json()


def test_stats_summary_cache(client):
    # second call should hit the in-module cache
    client.get("/api/v1/stats/summary")
    resp = client.get("/api/v1/stats/summary")
    assert resp.status_code == 200


def test_stats_summary_error(client, monkeypatch):
    import api.stats_router as _sr

    monkeypatch.setattr(_sr, "get_real_summary", _async_raise(Exception("boom")))
    resp = client.get("/api/v1/stats/summary")
    assert resp.status_code == 500


def test_stats_record_repair(client, monkeypatch):
    import api.stats_router as _sr

    monkeypatch.setattr(_sr, "ALLOWED_LOCAL_IPS", "testclient")
    monkeypatch.setattr(_sr, "INTERNAL_API_KEY", "")
    monkeypatch.setattr(_sr, "TRUST_PROXY_HEADER", False)
    resp = client.post(
        "/api/v1/stats/repair/record",
        json={
            "success": True,
            "rule_name": "r1",
            "script_key": "s1",
            "platform": "windows",
            "output": "ok",
        },
    )
    assert resp.status_code == 200


def test_stats_record_repair_forbidden(client, monkeypatch):
    import api.stats_router as _sr

    monkeypatch.setattr(_sr, "INTERNAL_API_KEY", "secret")
    monkeypatch.setattr(_sr, "TRUST_PROXY_HEADER", False)
    resp = client.post(
        "/api/v1/stats/repair/record",
        json={
            "success": True,
            "rule_name": "r1",
            "script_key": "s1",
            "platform": "windows",
        },
    )
    assert resp.status_code == 403


def test_stats_record_repair_error(client, monkeypatch):
    import api.stats_router as _sr

    monkeypatch.setattr(_sr, "ALLOWED_LOCAL_IPS", "testclient")
    monkeypatch.setattr(_sr, "INTERNAL_API_KEY", "")
    monkeypatch.setattr(_sr, "TRUST_PROXY_HEADER", False)
    monkeypatch.setattr(_sr, "record_repair", _async_raise(Exception("boom")))
    resp = client.post(
        "/api/v1/stats/repair/record",
        json={
            "success": True,
            "rule_name": "r1",
            "script_key": "s1",
            "platform": "windows",
        },
    )
    assert resp.status_code == 500


# =============================================================================
# tracing_router
# =============================================================================


def test_tracing_dashboard(client):
    resp = client.get("/api/tracing/dashboard")
    assert resp.status_code == 200


def test_tracing_list(client):
    resp = client.get("/api/tracing/traces?limit=2&min_duration=10ms")
    assert resp.status_code == 200
    assert resp.json()["source"] == "synthetic"


def test_tracing_details(client):
    resp = client.get("/api/tracing/traces/abc123")
    assert resp.status_code == 200
    assert resp.json()["data"]["trace_id"] == "abc123"


def test_tracing_topology(client):
    resp = client.get("/api/tracing/topology")
    assert resp.status_code == 200
    assert "nodes" in resp.json()["data"]


def test_tracing_hotspots(client):
    resp = client.get("/api/tracing/performance/hotspots?service_name=host-0")
    assert resp.status_code == 200


def test_tracing_errors(client):
    resp = client.get("/api/tracing/errors/analysis?service_name=host-1")
    assert resp.status_code == 200


def test_tracing_export(client):
    resp = client.get("/api/tracing/export/trace-config")
    assert resp.status_code == 200
    assert "otlp_endpoint" in resp.json()["data"]


def test_tracing_error(client, monkeypatch):
    import api.tracing_router as _tr

    monkeypatch.setattr(_tr, "_services", lambda: (_ for _ in ()).throw(Exception("boom")))
    resp = client.get("/api/tracing/topology")
    assert resp.status_code == 500


# =============================================================================
# slo_router
# =============================================================================


def test_slo_list(client, admin_headers):
    resp = client.get("/api/v1/slo/", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["slos"][0]["name"] == "slo1"


def test_slo_create(client, admin_headers):
    resp = client.post(
        "/api/v1/slo/",
        headers=admin_headers,
        json={
            "name": "slo2",
            "service": "svc",
            "metric": "m",
            "target": 99.99,
            "window": "1h",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "slo1"


def test_slo_create_invalid(client, admin_headers, monkeypatch):
    import api.slo_router as _slo

    def _raise(**kwargs):
        raise ValueError("bad")

    monkeypatch.setattr(_slo, "create_slo", _raise)
    resp = client.post(
        "/api/v1/slo/",
        headers=admin_headers,
        json={
            "name": "slo2",
            "service": "svc",
            "metric": "m",
            "target": 99.99,
            "window": "1h",
        },
    )
    assert resp.status_code == 400


def test_slo_get(client, admin_headers):
    resp = client.get("/api/v1/slo/1", headers=admin_headers)
    assert resp.status_code == 200


def test_slo_get_not_found(client, admin_headers, monkeypatch):
    import api.slo_router as _slo

    monkeypatch.setattr(_slo, "get_slo", lambda sid: None)
    resp = client.get("/api/v1/slo/1", headers=admin_headers)
    assert resp.status_code == 404


def test_slo_update(client, admin_headers):
    resp = client.put(
        "/api/v1/slo/1",
        headers=admin_headers,
        json={"name": "new"},
    )
    assert resp.status_code == 200


def test_slo_update_not_found(client, admin_headers, monkeypatch):
    import api.slo_router as _slo

    monkeypatch.setattr(_slo, "update_slo", lambda sid, **kwargs: None)
    resp = client.put(
        "/api/v1/slo/1",
        headers=admin_headers,
        json={"name": "new"},
    )
    assert resp.status_code == 404


def test_slo_delete(client, admin_headers):
    resp = client.delete("/api/v1/slo/1", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


def test_slo_delete_not_found(client, admin_headers, monkeypatch):
    import api.slo_router as _slo

    monkeypatch.setattr(_slo, "get_slo", lambda sid: None)
    resp = client.delete("/api/v1/slo/1", headers=admin_headers)
    assert resp.status_code == 404


def test_slo_create_reports(client, admin_headers):
    resp = client.post("/api/v1/slo/reports", headers=admin_headers, params={"period": "7d"})
    assert resp.status_code == 200


def test_slo_list_reports(client, admin_headers):
    resp = client.get("/api/v1/slo/reports", headers=admin_headers, params={"period": "30d"})
    assert resp.status_code == 200


def test_slo_get_report(client, admin_headers):
    resp = client.get("/api/v1/slo/reports/r1", headers=admin_headers)
    assert resp.status_code == 200


def test_slo_get_report_not_found(client, admin_headers, monkeypatch):
    import api.slo_router as _slo

    monkeypatch.setattr(_slo, "get_sla_report", lambda rid: None)
    resp = client.get("/api/v1/slo/reports/r1", headers=admin_headers)
    assert resp.status_code == 404


def test_slo_delete_report(client, admin_headers):
    resp = client.delete("/api/v1/slo/reports/r1", headers=admin_headers)
    assert resp.status_code == 200


def test_slo_delete_report_not_found(client, admin_headers, monkeypatch):
    import api.slo_router as _slo

    monkeypatch.setattr(_slo, "get_sla_report", lambda rid: None)
    resp = client.delete("/api/v1/slo/reports/r1", headers=admin_headers)
    assert resp.status_code == 404


# =============================================================================
# linux_router
# =============================================================================


def test_linux_hosts(client):
    resp = client.get("/api/v1/platforms/linux/hosts")
    assert resp.status_code == 200
    assert resp.json()["total"] == 1


def test_linux_hosts_error(client, monkeypatch):
    import api.linux_router as _lrx

    monkeypatch.setattr(_lrx, "get_configured_hosts", _async_raise(Exception("boom")))
    resp = client.get("/api/v1/platforms/linux/hosts")
    assert resp.status_code == 500


def test_linux_available_metrics(client):
    resp = client.get("/api/v1/platforms/linux/metrics/available")
    assert resp.status_code == 200
    assert resp.json()["total"] == 1


def test_linux_collect_all(client):
    resp = client.get("/api/v1/platforms/linux/collect/all")
    assert resp.status_code == 200
    assert resp.json()["total"] == 1


def test_linux_collect_all_empty(client, monkeypatch):
    import api.linux_router as _lrx

    monkeypatch.setattr(_lrx, "LINUX_HOSTS", [])
    resp = client.get("/api/v1/platforms/linux/collect/all")
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


def test_linux_collect_all_timeout(client, monkeypatch):
    import api.linux_router as _lrx

    monkeypatch.setattr(_lrx, "collect_all_linux", _async_raise(asyncio.TimeoutError()))
    resp = client.get("/api/v1/platforms/linux/collect/all")
    assert resp.status_code == 504


def test_linux_collect_host(client):
    resp = client.post(
        "/api/v1/platforms/linux/collect/host", json={"host_name": "h1", "metrics": ["cpu"]}
    )
    assert resp.status_code == 200


def test_linux_collect_host_not_found(client, monkeypatch):
    import api.linux_router as _lrx

    monkeypatch.setattr(_lrx, "find_linux_host_config", lambda host: None)
    resp = client.post(
        "/api/v1/platforms/linux/collect/host", json={"host_name": "h1", "metrics": ["cpu"]}
    )
    assert resp.status_code == 404


def test_linux_collect_host_timeout(client, monkeypatch):
    import api.linux_router as _lrx

    monkeypatch.setattr(_lrx, "collect_linux_host", _async_raise(asyncio.TimeoutError()))
    resp = client.post(
        "/api/v1/platforms/linux/collect/host", json={"host_name": "h1", "metrics": ["cpu"]}
    )
    assert resp.status_code == 504


def test_linux_repair_scripts(client):
    resp = client.get("/api/v1/platforms/linux/repair/scripts")
    assert resp.status_code == 200
    assert resp.json()["scripts"][0]["key"] == "clear_tmp"


def test_linux_repair_success(client):
    resp = client.post(
        "/api/v1/platforms/linux/repair/execute",
        json={"host_name": "h1", "script_key": "clear_tmp", "params": {}},
    )
    assert resp.status_code == 200


def test_linux_repair_blocked(client, monkeypatch):
    import api.linux_router as _lrx

    monkeypatch.setattr(
        _lrx,
        "execute_linux_repair",
        _async_return({"blocked": True, "reason": "unsafe", "safe_alternative": "use-rm-safe"}),
    )
    resp = client.post(
        "/api/v1/platforms/linux/repair/execute",
        json={"host_name": "h1", "script_key": "rm", "params": {}},
    )
    assert resp.status_code == 403


def test_linux_repair_pending(client, monkeypatch):
    import api.linux_router as _lrx

    monkeypatch.setattr(
        _lrx,
        "execute_linux_repair",
        _async_return(
            {
                "pending_approval": True,
                "alert_id": "a1",
                "reason": "high risk",
                "proposal": "do it",
            }
        ),
    )
    resp = client.post(
        "/api/v1/platforms/linux/repair/execute",
        json={"host_name": "h1", "script_key": "reboot", "params": {}},
    )
    assert resp.status_code == 202


def test_linux_repair_not_found(client, monkeypatch):
    import api.linux_router as _lrx

    monkeypatch.setattr(
        _lrx,
        "execute_linux_repair",
        _async_return({"success": False, "error": "未知修复脚本 reboot"}),
    )
    resp = client.post(
        "/api/v1/platforms/linux/repair/execute",
        json={"host_name": "h1", "script_key": "reboot", "params": {}},
    )
    assert resp.status_code == 404


def test_linux_repair_param_error(client, monkeypatch):
    import api.linux_router as _lrx

    monkeypatch.setattr(
        _lrx,
        "execute_linux_repair",
        _async_return({"success": False, "error": "缺少参数 pid"}),
    )
    resp = client.post(
        "/api/v1/platforms/linux/repair/execute",
        json={"host_name": "h1", "script_key": "kill", "params": {}},
    )
    assert resp.status_code == 422


def test_linux_repair_general_error(client, monkeypatch):
    import api.linux_router as _lrx

    monkeypatch.setattr(
        _lrx, "execute_linux_repair", _async_return({"success": False, "error": "boom"})
    )
    resp = client.post(
        "/api/v1/platforms/linux/repair/execute",
        json={"host_name": "h1", "script_key": "x", "params": {}},
    )
    assert resp.status_code == 500


def test_linux_repair_none(client, monkeypatch):
    import api.linux_router as _lrx

    monkeypatch.setattr(_lrx, "execute_linux_repair", _async_return(None))
    resp = client.post(
        "/api/v1/platforms/linux/repair/execute",
        json={"host_name": "h1", "script_key": "x", "params": {}},
    )
    assert resp.status_code == 500


def test_linux_repair_nondict(client, monkeypatch):
    import api.linux_router as _lrx

    monkeypatch.setattr(_lrx, "execute_linux_repair", _async_return("bad"))
    resp = client.post(
        "/api/v1/platforms/linux/repair/execute",
        json={"host_name": "h1", "script_key": "x", "params": {}},
    )
    assert resp.status_code == 500


def test_linux_repair_exception(client, monkeypatch):
    import api.linux_router as _lrx

    monkeypatch.setattr(_lrx, "execute_linux_repair", _async_raise(Exception("boom")))
    resp = client.post(
        "/api/v1/platforms/linux/repair/execute",
        json={"host_name": "h1", "script_key": "x", "params": {}},
    )
    assert resp.status_code == 500


# =============================================================================
# workflow_router
# =============================================================================


def test_workflow_list(client):
    resp = client.get("/api/v1/workflows/definitions")
    assert resp.status_code == 200
    assert "wf1" in resp.json()


def test_workflow_get(client):
    resp = client.get("/api/v1/workflows/definitions/wf1")
    assert resp.status_code == 200


def test_workflow_get_not_found(client):
    resp = client.get("/api/v1/workflows/definitions/unknown")
    assert resp.status_code == 404


def test_workflow_create(client):
    resp = client.post(
        "/api/v1/workflows/definitions",
        json={
            "wf_key": "wf2",
            "name": "WF2",
            "description": "",
            "steps": [{"key": "s1", "title": "Step", "desc": ""}],
            "time": "N/A",
            "rate": "N/A",
        },
    )
    assert resp.status_code == 201


def test_workflow_create_error(client, monkeypatch):
    import api.workflow_router as _wr

    def _raise(*args, **kwargs):
        raise ValueError("bad")

    monkeypatch.setattr(_wr, "create_workflow_definition", _raise)
    resp = client.post(
        "/api/v1/workflows/definitions",
        json={
            "wf_key": "wf2",
            "name": "WF2",
            "description": "",
            "steps": [{"key": "s1", "title": "Step", "desc": ""}],
            "time": "N/A",
            "rate": "N/A",
        },
    )
    assert resp.status_code == 400


def test_workflow_update(client):
    resp = client.put(
        "/api/v1/workflows/definitions/wf1",
        json={"name": "New"},
    )
    assert resp.status_code == 200


def test_workflow_update_not_found(client, monkeypatch):
    import api.workflow_router as _wr

    def _raise(*args, **kwargs):
        raise ValueError("不存在")

    monkeypatch.setattr(_wr, "update_workflow_definition", _raise)
    resp = client.put("/api/v1/workflows/definitions/wf1", json={"name": "New"})
    assert resp.status_code == 404


def test_workflow_update_empty(client):
    resp = client.put("/api/v1/workflows/definitions/wf1", json={})
    assert resp.status_code == 400


def test_workflow_delete(client):
    resp = client.delete("/api/v1/workflows/definitions/wf1")
    assert resp.status_code == 200


def test_workflow_delete_not_found(client, monkeypatch):
    import api.workflow_router as _wr

    def _raise(key):
        raise ValueError("不存在")

    monkeypatch.setattr(_wr, "delete_workflow_definition", _raise)
    resp = client.delete("/api/v1/workflows/definitions/wf1")
    assert resp.status_code == 404


def test_workflow_simulate(client):
    resp = client.get("/api/v1/workflows/simulate/wf1")
    assert resp.status_code == 200


def test_workflow_simulate_not_found(client):
    resp = client.get("/api/v1/workflows/simulate/unknown")
    assert resp.status_code == 404


def test_workflow_simulate_concurrent_full(client, monkeypatch):
    import api.workflow_router as _wr

    monkeypatch.setattr(
        _wr,
        "_sse_semaphore",
        SimpleNamespace(locked=lambda: True, _value=0),
    )
    resp = client.get("/api/v1/workflows/simulate/wf1")
    assert resp.status_code == 503


def test_workflow_concurrent(client):
    resp = client.get("/api/v1/workflows/concurrent")
    assert resp.status_code == 200
    assert "max_concurrent" in resp.json()


def test_workflow_execute(client):
    resp = client.post("/api/v1/workflows/execute", json={"workflow": {"nodes": []}})
    assert resp.status_code == 200
    assert resp.json()["workflow_id"] == "w1"
