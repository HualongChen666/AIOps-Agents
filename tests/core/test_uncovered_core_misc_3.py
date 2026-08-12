# -*- coding: utf-8 -*-
"""Focused unit tests to push core.db_engine, core.auto_heal,
core.runbook_generator and core.user_service above 80% statement coverage."""

import asyncio
import json
from typing import Any, Optional
from unittest.mock import AsyncMock, MagicMock

import pytest
import sqlalchemy

import core.auto_heal as auto_heal
import core.db_engine as db_engine
import core.runbook_generator as runbook_gen
import core.user_service as user_service
from core.command_guard import RiskLevel
from core.models import Alert, PendingApproval, RepairRecord, User

pytestmark = [pytest.mark.core]


# ------------------------------------------------------------------
# Shared fake SQLAlchemy async session helpers
# ------------------------------------------------------------------
class _FakeScalars:
    def __init__(self, items: Any):
        self._items = items

    def all(self):
        return self._items


class _FakeResult:
    def __init__(
        self,
        scalars: Optional[list] = None,
        scalar_one_or_none: Any = None,
        scalar: Any = 0,
        rowcount: int = 0,
    ):
        self._scalars = scalars or []
        self._scalar_one = scalar_one_or_none
        self._scalar = scalar
        self.rowcount = rowcount

    def scalars(self):
        return _FakeScalars(self._scalars)

    def scalar_one_or_none(self):
        return self._scalar_one

    def scalar(self):
        return self._scalar


class _FakeSession:
    def __init__(self, result: Optional[_FakeResult] = None):
        self._result = result or _FakeResult()
        self.committed = False
        self.rolled_back = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if exc:
            await self.rollback()
        return False

    async def execute(self, stmt):
        return self._result

    async def commit(self):
        self.committed = True

    async def rollback(self):
        self.rolled_back = True

    async def refresh(self, obj):
        return obj

    def add(self, obj):
        pass


def _patch_session(monkeypatch, result: Optional[_FakeResult] = None):
    """Patch AsyncSessionLocal to yield a fake session without a real DB."""
    monkeypatch.setattr(db_engine, "_ENGINE", MagicMock())
    monkeypatch.setattr(
        db_engine,
        "_AsyncSessionLocal",
        lambda *args, **kwargs: _FakeSession(result=result),
    )


# ------------------------------------------------------------------
# core.db_engine
# ------------------------------------------------------------------
@pytest.mark.asyncio
async def test_db_engine_async_get_session_ok(monkeypatch):
    _patch_session(monkeypatch)
    async with db_engine.async_get_session() as session:
        assert isinstance(session, _FakeSession)
        assert await session.execute("stmt") is not None


@pytest.mark.asyncio
async def test_db_engine_async_init_db(monkeypatch):
    class _FakeConn:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def run_sync(self, fn, *args, **kwargs):
            return None

    class _FakeEngine:
        def begin(self):
            return _FakeConn()

    monkeypatch.setenv("USE_SQLITE", "true")
    monkeypatch.setattr(db_engine, "_ENGINE", _FakeEngine())
    await db_engine.async_init_db()


@pytest.mark.asyncio
async def test_db_engine_async_insert_alert(monkeypatch):
    _patch_session(monkeypatch)
    alert_id = await db_engine.async_insert_alert({
        "id": "a1",
        "level": "critical",
        "title": "t",
    })
    assert alert_id.startswith("a1")


@pytest.mark.asyncio
async def test_db_engine_async_query_alerts(monkeypatch):
    alert = Alert(id="a1", level="warning")
    _patch_session(monkeypatch, _FakeResult(scalars=[alert]))
    rows = await db_engine.async_query_alerts(limit=5, level="warning")
    assert isinstance(rows, list)
    assert rows[0]["id"] == "a1"


@pytest.mark.asyncio
async def test_db_engine_async_count_alerts(monkeypatch):
    _patch_session(monkeypatch, _FakeResult(scalar=7))
    assert await db_engine.async_count_alerts(status="pending") == 7


@pytest.mark.asyncio
async def test_db_engine_async_clear_alerts(monkeypatch):
    _patch_session(monkeypatch, _FakeResult(rowcount=3))
    assert await db_engine.async_clear_alerts() == 3


@pytest.mark.asyncio
async def test_db_engine_async_insert_and_query_repair(monkeypatch):
    _patch_session(monkeypatch)
    rid = await db_engine.async_insert_repair_record(
        success=True,
        alert_time="2026-01-01T00:00:00",
        repair_time="2026-01-01T00:01:00",
        repair_duration_sec=1.0,
        rule_name="cpu",
        script_key="cpu_high_script",
        platform="windows",
        output="ok",
    )
    assert rid.startswith("repair-")

    repair = RepairRecord(id=rid, script_key="cpu_high_script")
    _patch_session(monkeypatch, _FakeResult(scalars=[repair]))
    rows = await db_engine.async_query_repairs(today_only=False, limit=5)
    assert isinstance(rows, list)
    assert rows[0]["id"] == rid


@pytest.mark.asyncio
async def test_db_engine_async_pending_approval(monkeypatch):
    _patch_session(monkeypatch)
    approval_id = await db_engine.async_upsert_pending_approval(
        alert_id="a1",
        rule_name="cpu",
        script_key="cpu_high_script",
        proposal="p",
        alert_json="{}",
    )
    assert approval_id.startswith("approval-")

    approval = PendingApproval(id=approval_id, alert_id="a1")
    _patch_session(monkeypatch, _FakeResult(scalar_one_or_none=approval))
    got = await db_engine.async_get_pending_approval("a1")
    assert got is not None
    assert got["alert_id"] == "a1"

    got2 = await db_engine.async_get_approval_by_alert("a1")
    assert got2 is not None
    assert got2["id"] == approval_id

    _patch_session(monkeypatch, _FakeResult(scalars=[approval]))
    all_pending = await db_engine.async_get_all_pending_approvals()
    assert len(all_pending) == 1

    _patch_session(monkeypatch, _FakeResult(scalar_one_or_none=approval))
    assert await db_engine.async_update_approval_status(approval_id, "approved")

    _patch_session(monkeypatch, _FakeResult(scalar_one_or_none=approval))
    assert await db_engine.async_update_approval_status_by_alert("a1", "rejected")


def test_db_engine_sync_wrappers(monkeypatch):
    _patch_session(monkeypatch)
    db_engine.insert_alert({"id": "s1", "title": "t"})
    assert db_engine.query_alerts(limit=1) == []
    assert db_engine.count_alerts() == 0
    assert db_engine.clear_alerts() == 0
    rid = db_engine.insert_repair_record(
        success=True,
        alert_time="2026-01-01T00:00:00",
        repair_time="2026-01-01T00:01:00",
        repair_duration_sec=1.0,
        rule_name="r",
        script_key="s",
        platform="linux",
        output="o",
    )
    assert rid in (0, -1)
    assert db_engine.query_repairs() == []
    assert db_engine.upsert_pending_approval("a", "r", "s", "p", "{}") in (0, -1)
    assert db_engine.get_pending_approval("a") is None
    assert db_engine.get_all_pending_approvals() == []
    assert db_engine.insert_verify_record(x=1) == 0
    assert db_engine.db_clear_alerts() == 0


@pytest.mark.asyncio
async def test_db_engine_connection_error_detection(monkeypatch):
    result = _FakeResult()
    result.rowcount = 0

    class _FailingSession(_FakeSession):
        async def execute(self, stmt):
            err = ValueError("db down")
            err.__cause__ = OSError("conn refused")
            raise err

        async def commit(self):
            err = ValueError("db down")
            err.__cause__ = OSError("conn refused")
            raise err

    monkeypatch.setattr(db_engine, "_ENGINE", MagicMock())
    monkeypatch.setattr(
        db_engine, "_AsyncSessionLocal", lambda *a, **k: _FailingSession(result=result)
    )
    assert await db_engine.async_query_alerts(limit=1) == []
    assert await db_engine.async_count_alerts(status="x") == 0
    assert await db_engine.async_clear_alerts() == 0

    # async_insert_alert should re-raise a connection error after logging
    monkeypatch.setattr(
        db_engine,
        "_AsyncSessionLocal",
        lambda *a, **k: _FailingSession(result=result),
    )
    with pytest.raises(ValueError):
        await db_engine.async_insert_alert({"id": "x"})


@pytest.mark.asyncio
async def test_postgresql_alert_repository(monkeypatch):
    _patch_session(monkeypatch)
    rid = await db_engine.alert_repository.save({"id": "a1", "title": "t"})
    assert rid.startswith("a1")

    alert = Alert(id="a1", level="warning")
    _patch_session(monkeypatch, _FakeResult(scalar_one_or_none=alert))
    got = await db_engine.alert_repository.get_by_id("a1")
    assert got is not None
    assert got["id"] == "a1"

    _patch_session(monkeypatch, _FakeResult(scalar_one_or_none=alert))
    assert await db_engine.alert_repository.update_status("a1", "resolved")

    _patch_session(monkeypatch, _FakeResult(rowcount=1))
    assert await db_engine.alert_repository.delete("a1")

    _patch_session(monkeypatch, _FakeResult(scalars=[alert]))
    rows = await db_engine.alert_repository.query({"level": "warning"})
    assert isinstance(rows, list)

    _patch_session(monkeypatch, _FakeResult(scalar=5))
    assert await db_engine.alert_repository.count({"level": "warning"}) == 5

    _patch_session(monkeypatch, _FakeResult(rowcount=2))
    assert await db_engine.alert_repository.clear_all()

    _patch_session(monkeypatch, _FakeResult(scalars=[alert]))
    rows = await db_engine.alert_repository.get_recent(10)
    assert isinstance(rows, list)


@pytest.mark.asyncio
async def test_db_engine_component_database_engine(monkeypatch):
    class _SyncResult:
        rowcount = 3

        def mappings(self):
            return _SyncResult

        @classmethod
        def all(cls):
            return [{"id": 1, "name": "x"}]

        def close(self):
            pass

    class _SyncConn:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def execute(self, query, params):
            return _SyncResult()

    class _SyncEngine:
        def begin(self):
            return _SyncConn()

        def connect(self):
            return _SyncConn()

        def dispose(self):
            pass

    monkeypatch.setattr(
        sqlalchemy, "create_engine", lambda *args, **kwargs: _SyncEngine()
    )
    monkeypatch.setattr(sqlalchemy, "text", lambda q: q)

    engine = db_engine.DatabaseEngine(connection_string="sqlite:///:memory:")
    assert not engine.connected
    rows_affected = await engine.execute("INSERT INTO t VALUES (:x)", {"x": 1})
    assert engine.connected
    assert rows_affected == 3
    await engine.disconnect()
    assert not engine.connected
    rows = await engine.fetchall("SELECT * FROM t", {})
    assert rows == [{"id": 1, "name": "x"}]
    engine._engine = None
    await engine.disconnect()
    assert not engine.connected


def test_db_engine_simple_repair_db():
    assert db_engine.db.get_repair_record("missing") is None
    db_engine.db.update_repair_status("r1", "done", "all good")
    rec = db_engine.db.get_repair_record("r1")
    assert rec["repair_id"] == "r1"
    assert rec["status"] == "done"
    assert rec["comment"] == "all good"


def test_db_engine_get_alert_repository():
    repo_pair = db_engine._get_alert_repository()
    assert isinstance(repo_pair, tuple)


# ------------------------------------------------------------------
# core.user_service
# ------------------------------------------------------------------
@pytest.mark.asyncio
async def test_user_service_crud(monkeypatch):
    user = User(id=1, username="alice")
    _patch_session(monkeypatch, _FakeResult(scalar_one_or_none=user, scalars=[user]))

    assert await user_service.UserService.get_user_by_username("alice") is user
    assert await user_service.UserService.get_user_by_email("a@b.com") is user
    assert await user_service.UserService.get_user_by_id(1) is user

    _patch_session(monkeypatch, _FakeResult(scalar_one_or_none=None))
    created = await user_service.UserService.create_user(
        "bob", "h", "b@b.com", "Bob", "user"
    )
    assert created is not None
    assert created.username == "bob"

    _patch_session(monkeypatch, _FakeResult(scalar_one_or_none=user))
    assert await user_service.UserService.update_user(
        "alice", email="new@b.com", full_name="A", role="admin", disabled=False
    )
    assert await user_service.UserService.update_password("alice", "h")

    _patch_session(monkeypatch, _FakeResult(rowcount=1))
    assert await user_service.UserService.delete_user("alice")

    _patch_session(monkeypatch, _FakeResult(scalars=[user]))
    users = await user_service.UserService.list_users()
    assert users and users[0].username == "alice"

    _patch_session(monkeypatch, _FakeResult(scalar_one_or_none=user))
    assert await user_service.UserService.update_last_login("alice")

    _patch_session(monkeypatch, _FakeResult(scalar_one_or_none=user))
    assert await user_service.UserService.enable_mfa("alice", "secret", ["c1", "c2"])

    _patch_session(monkeypatch, _FakeResult(scalar_one_or_none=user))
    assert await user_service.UserService.disable_mfa("alice")

    user_dict = user_service.UserService.user_to_dict(user)
    assert user_dict["username"] == "alice"
    assert "id" in user_dict


@pytest.mark.asyncio
async def test_user_service_update_user_no_data(monkeypatch):
    _patch_session(monkeypatch, _FakeResult(scalar_one_or_none=User(id=1, username="u")))
    assert not await user_service.UserService.update_user("u")


@pytest.mark.asyncio
async def test_user_service_exceptions(monkeypatch):
    monkeypatch.setattr(db_engine, "_ENGINE", MagicMock())
    monkeypatch.setattr(
        db_engine,
        "_AsyncSessionLocal",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    assert await user_service.UserService.get_user_by_username("x") is None
    assert await user_service.UserService.create_user("x", "h") is None
    assert not await user_service.UserService.update_user("x", email="x")
    assert not await user_service.UserService.delete_user("x")
    assert await user_service.UserService.list_users() == []


# ------------------------------------------------------------------
# core.auto_heal
# ------------------------------------------------------------------
class _FakeDateTime:
    class _Now:
        def __init__(self, hour, is_str=False):
            self.hour = hour
            self._is_str = is_str

        def time(self):
            from datetime import time as _time
            return _time(self.hour, 0)

        def isoformat(self):
            return "now"

    @classmethod
    def now(cls, tz=None):
        return cls._Now(2)

    @classmethod
    def strptime(cls, s, fmt):
        h, m = map(int, s.split(":"))
        return cls._Now(h, is_str=True)


def test_auto_heal_handle_alert_and_trigger(monkeypatch):
    monkeypatch.setattr(auto_heal, "analyze", lambda *a, **k: "runbook text")
    monkeypatch.setattr(auto_heal, "search_similar", lambda *a, **k: [])
    _patch_session(monkeypatch)

    alert = {
        "id": "42",
        "title": "CPU high",
        "rule_name": "cpu",
        "platform": "windows",
        "detected_at": "2026-01-01T00:00:00",
    }
    result = auto_heal.handle_alert(alert)
    assert result["alert_id"] == "42"
    assert "repair_id" in result
    assert "runbook" in result

    triggered = auto_heal.trigger_auto_heal(alert)
    assert "alert_id" in triggered


def test_auto_heal_simulate_and_verify():
    ok_result = auto_heal.simulate_repair({"platform": "windows"}, "memory_high_script")
    assert isinstance(ok_result, dict)

    bad_result = auto_heal.simulate_repair({"platform": "windows"}, "missing_script")
    assert bad_result.get("success") is False

    cpu_result = auto_heal.simulate_repair({"platform": "windows"}, "cpu_high_script")
    assert cpu_result.get("requires_approval") or not cpu_result.get("success")

    success_verify = auto_heal.simulate_verify({"id": "1"}, ok_result)
    assert success_verify["verified"] is True
    failure_verify = auto_heal.simulate_verify({"id": "1"}, bad_result)
    assert failure_verify["needs_human"] is True


def test_auto_heal_repair_script_library():
    lib = auto_heal.RepairScriptLibrary()
    assert lib.get_script("memory_high_script") is not None
    assert lib.get_script("missing") is None
    windows_scripts = lib.get_scripts_for_platform(auto_heal.PlatformType.WINDOWS)
    assert any(s.script_key == "memory_high_script" for s in windows_scripts)
    new_script = auto_heal.RepairScript(
        script_key="custom",
        name="Custom",
        description="d",
        platforms=[auto_heal.PlatformType.LINUX],
        risk_level=RiskLevel.LOW,
        script_content="print(1)",
    )
    lib.register_script(new_script)
    assert lib.get_script("custom") is new_script


def test_auto_heal_risk_assessment_engine(monkeypatch):
    monkeypatch.setattr(auto_heal, "datetime", _FakeDateTime)
    script = auto_heal.RepairScript(
        script_key="s",
        name="n",
        description="d",
        platforms=[auto_heal.PlatformType.WINDOWS],
        risk_level=RiskLevel.LOW,
        script_content="",
        rollback_script="rb",
        requires_approval=False,
    )
    assessment = auto_heal.risk_assessment_engine.assess_repair_risk(
        script, {"environment": "production", "affected_components": ["db"]}
    )
    assert assessment.approval_required is True
    assert assessment.risk_level in RiskLevel
    assert 0.0 <= assessment.confidence_score <= 1.0


def test_auto_heal_cross_platform_executor():
    executor = auto_heal.CrossPlatformScriptExecutor()
    assert executor.current_platform in auto_heal.PlatformType
    available = executor.get_available_scripts()
    assert isinstance(available, list)
    not_found = executor.execute_script("no_such_script")
    assert not_found.get("success") is False


@pytest.mark.asyncio
async def test_auto_heal_try_auto_heal(monkeypatch):
    final_state = MagicMock()
    final_state.error = ""
    final_state.approval_status = "approved"
    final_state.fix_applied = True
    final_state.verification = {"passed": True}
    final_state.runbook = {}

    monkeypatch.setattr("core.heal_graph.run_heal", AsyncMock(return_value=final_state))
    monkeypatch.setattr("core.heal_graph.HealState", MagicMock())

    result = await auto_heal.try_auto_heal({"id": "1"})
    assert result["healed"] is True
    assert result["alert_id"] == "1"


@pytest.mark.asyncio
async def test_auto_heal_maintenance_window(monkeypatch):
    monkeypatch.setenv("HEAL_MAINTENANCE_MODE", "true")
    result = await auto_heal.try_auto_heal({"id": "1"})
    assert result.get("maintenance") is True


@pytest.mark.asyncio
async def test_auto_heal_escalation(monkeypatch):
    key = auto_heal._get_resource_key({"id": "1"})
    monkeypatch.setattr(auto_heal, "_HEAL_FAILURE_TRACKER", {key: {"count": 10}})
    result = await auto_heal.try_auto_heal({"id": "1"})
    assert result.get("escalated") is True


@pytest.mark.asyncio
async def test_auto_heal_approve_reject_and_pending(monkeypatch):
    monkeypatch.setattr(
        auto_heal,
        "async_update_approval_status_by_alert",
        AsyncMock(return_value=True),
    )
    approved = await auto_heal.approve_repair("1", "admin")
    assert approved["success"] is True
    assert approved["status"] == "approved"

    rejected = await auto_heal.reject_repair("1", "unsafe", "admin", "unsafe")
    assert rejected["success"] is True
    assert rejected["status"] == "rejected"

    monkeypatch.setattr(
        auto_heal, "async_update_approval_status_by_alert", None
    )
    fallback = await auto_heal.approve_repair("2")
    assert fallback["success"] is True

    monkeypatch.setattr(
        auto_heal,
        "async_get_all_pending_approvals",
        AsyncMock(return_value=[{"alert_id": "1"}]),
    )
    monkeypatch.setattr(
        "core.approval_store.get_pending_only_snapshot",
        lambda: {"2": {"info": "x"}},
    )
    pending = await auto_heal.get_pending_approvals()
    assert any(p.get("alert_id") == "1" for p in pending)
    assert any(p.get("alert_id") == "2" for p in pending)


def test_auto_heal_helpers():
    assert auto_heal._get_resource_key({"resource_id": "r1"}) == "r1"
    assert auto_heal._get_resource_key({"id": "i"}) == "i"
    assert auto_heal._get_resource_key({}) == "unknown"

    in_maint, reason = auto_heal._is_in_maintenance_window()
    assert in_maint is False
    assert reason is None

    assert auto_heal._is_pending_approval_error(
        MagicMock(error="pending approval", approval_status="approved")
    )
    assert auto_heal._is_pending_approval_error(
        MagicMock(error="", approval_status="pending")
    )
    assert not auto_heal._is_pending_approval_error(
        MagicMock(error="", approval_status="approved")
    )

    lock = asyncio.run(auto_heal._acquire_heal_lock("k"))
    assert isinstance(lock, asyncio.Lock)

    assert auto_heal._resolve_script_key("cpu", {}) == "cpu_high_script"
    assert auto_heal._resolve_script_key("memory", {}) == "memory_high_script"
    assert auto_heal._resolve_script_key("x", {"script_key": "memory_high_script"}) == "memory_high_script"
    assert auto_heal._resolve_script_key("x", {}) == "service_restart_script"


def test_auto_heal_failure_tracker():
    alert = {"id": "dev1"}
    assert not auto_heal._should_escalate(alert)[0]
    auto_heal._record_heal_failure(alert)
    assert auto_heal._should_escalate(alert)[1]["count"] >= 1
    auto_heal._record_heal_success(alert)
    assert auto_heal._should_escalate(alert)[1]["count"] == 0


def test_auto_heal_maintenance_env(monkeypatch):
    monkeypatch.setenv("HEAL_MAINTENANCE_WINDOW", "not-a-valid-window")
    in_maint, _ = auto_heal._is_in_maintenance_window()
    assert in_maint is False


# ------------------------------------------------------------------
# core.runbook_generator
# ------------------------------------------------------------------
@pytest.fixture
def runbook_mocks(monkeypatch):
    monkeypatch.setattr(
        runbook_gen,
        "analyze",
        AsyncMock(
            return_value=json.dumps({
                "summary": "restart service",
                "commands": ["echo ok"],
                "risk_level": "low",
                "rollback": "echo rollback",
                "confidence": 0.85,
                "reasoning": "safe",
            })
        ),
    )
    monkeypatch.setattr(
        runbook_gen,
        "search_similar",
        lambda *a, **k: [{"payload": {"summary": "s", "commands": ["c"]}}],
    )
    monkeypatch.setattr(
        runbook_gen,
        "analyze_command",
        lambda cmd: {"risk_level": RiskLevel.LOW},
    )
    monkeypatch.setattr(
        runbook_gen,
        "upsert_pending_approval",
        MagicMock(return_value=None),
    )
    monkeypatch.setattr(
        runbook_gen,
        "moderate_content",
        lambda *a, **k: (True, []),
    )
    monkeypatch.setattr(runbook_gen, "anonymize_dict", lambda x: x)
    monkeypatch.setattr(runbook_gen, "anonymize_text", lambda x: x)
    monkeypatch.setenv("VERIFY_CONFIG", "{}")
    import config
    monkeypatch.setattr(config, "VERIFY_CONFIG", {"self_learning_enabled": True})


@pytest.mark.asyncio
async def test_generate_repair_runbook_success(runbook_mocks):
    alert = {
        "id": "r1",
        "level": "warning",
        "title": "Service down",
        "desc": "service stopped",
        "metric": "status",
        "value": 0,
        "platform": "linux",
    }
    rich = {
        "top_processes": [{"name": "svc", "pid": 1, "cpu_percent": 5, "memory_percent": 10}],
        "recent_alerts": [{"level": "warning", "title": "prev"}],
        "stats": {"current_anomalies": 1, "heal_rate": 50, "total_alerts": 3},
    }
    result = await runbook_gen.generate_repair_runbook(alert, rich)
    assert result["success"] is True
    assert result["alert_id"] == "r1"
    assert result["worst_risk"] == RiskLevel.LOW.value
    assert result["auto_executable"] is True


@pytest.mark.asyncio
async def test_generate_repair_runbook_blocked(monkeypatch, runbook_mocks):
    monkeypatch.setattr(
        runbook_gen,
        "analyze_command",
        lambda cmd: {"risk_level": RiskLevel.BLOCKED},
    )
    alert = {
        "id": "r2",
        "level": "critical",
        "title": "Bad",
        "desc": "bad",
        "metric": "x",
        "value": 1,
        "platform": "windows",
    }
    result = await runbook_gen.generate_repair_runbook(alert)
    assert result["success"] is False
    assert "BLOCKED" in result["error"] or result.get("worst_risk") == RiskLevel.BLOCKED.value


@pytest.mark.asyncio
async def test_generate_repair_runbook_invalid_inputs(monkeypatch, runbook_mocks):
    result = await runbook_gen.generate_repair_runbook("not-a-dict")
    assert result["success"] is False

    result = await runbook_gen.generate_repair_runbook({})
    assert result["success"] is False


@pytest.mark.asyncio
async def test_generate_repair_runbook_moderation_fail(monkeypatch, runbook_mocks):
    monkeypatch.setattr(
        runbook_gen,
        "moderate_content",
        lambda *a, **k: (False, ["injection"]),
    )
    alert = {
        "id": "r3",
        "level": "warning",
        "title": "T",
        "desc": "d",
        "metric": "x",
        "value": 1,
        "platform": "windows",
    }
    result = await runbook_gen.generate_repair_runbook(alert)
    assert result["success"] is False
    assert "Prompt content violation" in result["error"]


def test_runbook_json_extractors():
    assert runbook_gen._extract_json_from_llm_output('{"a":1}') == {"a": 1}
    md = '```json\n{"a":1}\n```'
    assert runbook_gen._extract_json_from_llm_output(md) == {"a": 1}
    assert runbook_gen._extract_json_from_llm_output("garbage") is None
    assert runbook_gen._extract_first_json_object('{"x":1}') == '{"x":1}'
    assert runbook_gen._extract_first_json_object('x {"a": "}"}') == '{"a": "}"}'


def test_validate_and_normalize_runbook():
    valid = {
        "summary": "s",
        "commands": ["c1"],
        "risk_level": "low",
        "rollback": "r",
        "confidence": 0.5,
        "reasoning": "r",
    }
    ok, err, runbook = runbook_gen._validate_and_normalize_runbook(valid)
    assert ok and not err
    assert runbook["risk_level"] == "low"

    ok, err, _ = runbook_gen._validate_and_normalize_runbook({"summary": "s"})
    assert not ok
    ok, err, _ = runbook_gen._validate_and_normalize_runbook("bad")
    assert not ok
    ok, err, _ = runbook_gen._validate_and_normalize_runbook({
        "summary": "s", "commands": [], "risk_level": "low"
    })
    assert not ok
    ok, err, _ = runbook_gen._validate_and_normalize_runbook({
        "summary": "s", "commands": ["c"], "risk_level": "nope"
    })
    assert not ok


def test_infer_candidate_script_key():
    assert runbook_gen._infer_candidate_script_key({"metric": "cpu_percent"}) == "kill_high_cpu"
    assert runbook_gen._infer_candidate_script_key({"metric": "disk_percent"}) == "clear_temp"
    assert runbook_gen._infer_candidate_script_key(
        {"metric": "memory_percent", "platform": "windows"}
    ) == "free_memory"
    assert runbook_gen._infer_candidate_script_key(
        {"metric": "memory_percent", "platform": "linux"}
    ) == "free_cache"
    assert runbook_gen._infer_candidate_script_key({"metric": "unknown"}) is None
    assert runbook_gen._infer_candidate_script_key("bad") is None


def test_build_metrics_snapshot():
    rich = {
        "top_processes": [{"name": "p1", "pid": 1, "cpu_percent": 50, "memory_percent": 20}],
        "recent_alerts": [{"level": "warning", "title": "t"}],
        "stats": {"current_anomalies": 1, "heal_rate": 80, "total_alerts": 5},
    }
    snap = runbook_gen._build_metrics_snapshot(rich)
    assert "p1" in snap
    assert "80%" in snap
    assert "WARNING" in snap
    assert runbook_gen._build_metrics_snapshot({}) == "(无系统快照)"


def test_runbook_redact():
    assert runbook_gen._redact_text(123) == "123"
    assert runbook_gen._redact_value({"a": 1}) == {"a": 1}


def test_db_engine_url_and_lazy_helpers(monkeypatch):
    import config

    monkeypatch.delenv("USE_SQLITE", raising=False)
    assert db_engine._effective_database_url() == config.POSTGRES_URL

    monkeypatch.setenv("USE_SQLITE", "true")
    assert db_engine._effective_database_url().startswith("sqlite")

    assert repr(db_engine.AsyncSessionLocal) == "<LazyAsyncSessionLocal>"

    monkeypatch.setattr(db_engine, "_ENGINE", MagicMock())
    monkeypatch.setattr(db_engine, "_AsyncSessionLocal", None)
    with pytest.raises(RuntimeError):
        db_engine.AsyncSessionLocal()

    monkeypatch.setattr(db_engine, "_ENGINE", None)
    monkeypatch.setattr(db_engine, "_AsyncSessionLocal", None)
    monkeypatch.setattr(
        db_engine, "create_async_engine", MagicMock(return_value=MagicMock())
    )
    monkeypatch.setattr(
        db_engine, "async_sessionmaker", lambda **kwargs: MagicMock()
    )
    db_engine._ensure_engine()
    assert db_engine._ENGINE is not None


class _BadCommit(_FakeSession):
    async def commit(self):
        raise RuntimeError("commit fail")


class _BadExecute(_FakeSession):
    async def execute(self, stmt):
        raise RuntimeError("execute fail")


@pytest.mark.asyncio
async def test_async_get_session_exception(monkeypatch):
    monkeypatch.setattr(db_engine, "_ENGINE", MagicMock())
    monkeypatch.setattr(db_engine, "_AsyncSessionLocal", lambda *a, **k: _BadCommit())
    with pytest.raises(RuntimeError):
        async with db_engine.async_get_session() as session:
            pass


@pytest.mark.asyncio
async def test_db_engine_async_commit_errors(monkeypatch):
    monkeypatch.setattr(db_engine, "_ENGINE", MagicMock())
    monkeypatch.setattr(
        db_engine,
        "_AsyncSessionLocal",
        lambda *a, **k: _BadCommit(result=_FakeResult(scalar_one_or_none=MagicMock())),
    )
    with pytest.raises(RuntimeError):
        await db_engine.async_insert_alert({"id": "x"})
    with pytest.raises(RuntimeError):
        await db_engine.async_insert_repair_record(
            success=True,
            alert_time="2026-01-01T00:00:00",
            repair_time="2026-01-01T00:01:00",
            repair_duration_sec=1.0,
            rule_name="r",
            script_key="s",
            platform="linux",
            output="o",
        )
    with pytest.raises(RuntimeError):
        await db_engine.async_upsert_pending_approval("a", "r", "s", "p", "{}")
    assert await db_engine.async_update_approval_status("a", "approved") is False
    assert await db_engine.async_update_approval_status_by_alert("a", "approved") is False
    assert await db_engine.async_clear_alerts() == 0
    with pytest.raises(RuntimeError):
        await db_engine.alert_repository.save({"id": "x"})
    assert await db_engine.alert_repository.update_status("x", "y") is False
    assert await db_engine.alert_repository.delete("x") is False


@pytest.mark.asyncio
async def test_db_engine_async_execute_errors(monkeypatch):
    monkeypatch.setattr(db_engine, "_ENGINE", MagicMock())
    monkeypatch.setattr(db_engine, "_AsyncSessionLocal", lambda *a, **k: _BadExecute())
    assert await db_engine.async_query_alerts() == []
    assert await db_engine.async_count_alerts() == 0
    assert await db_engine.async_clear_alerts() == 0
    assert await db_engine.async_query_repairs() == []
    assert await db_engine.async_get_pending_approval("x") is None
    assert await db_engine.async_get_approval_by_alert("x") is None
    assert await db_engine.async_get_all_pending_approvals() == []
    assert await db_engine.async_update_approval_status("x", "y") is False
    assert await db_engine.async_update_approval_status_by_alert("x", "y") is False
    assert await db_engine.alert_repository.get_by_id("x") is None
    assert await db_engine.alert_repository.update_status("x", "y") is False
    assert await db_engine.alert_repository.delete("x") is False
    assert await db_engine.alert_repository.query() == []
    assert await db_engine.alert_repository.count() == 0
    assert await db_engine.alert_repository.get_recent(5) == []


def test_db_engine_sync_wrapper_errors(monkeypatch):
    monkeypatch.setattr(db_engine, "_ENGINE", MagicMock())
    monkeypatch.setattr(db_engine, "_AsyncSessionLocal", lambda *a, **k: _BadCommit())
    db_engine.insert_alert({"id": "x"})
    db_engine.insert_repair_record(
        success=True,
        alert_time="2026-01-01T00:00:00",
        repair_time="2026-01-01T00:01:00",
        repair_duration_sec=1.0,
        rule_name="r",
        script_key="s",
        platform="linux",
        output="o",
    )
    db_engine.upsert_pending_approval("a", "r", "s", "p", "{}")
    db_engine.update_approval_status("a", "approved")
    db_engine.update_approval_status_by_alert("a", "approved")

    monkeypatch.setattr(db_engine, "_AsyncSessionLocal", lambda *a, **k: _BadExecute())
    assert db_engine.query_alerts() == []
    assert db_engine.count_alerts() == 0
    assert db_engine.clear_alerts() == 0
    assert db_engine.query_repairs() == []
    assert db_engine.get_pending_approval("x") is None
    assert db_engine.get_all_pending_approvals() == []
    assert db_engine.insert_verify_record(x=1) == 0
    assert db_engine.db_clear_alerts() == 0


@pytest.mark.asyncio
async def test_generate_repair_runbook_edge_cases(monkeypatch, runbook_mocks):
    # invalid/empty JSON from LLM
    monkeypatch.setattr(runbook_gen, "analyze", AsyncMock(return_value="{}"))
    result = await runbook_gen.generate_repair_runbook({
        "id": "r4", "level": "warning", "title": "T", "desc": "d",
        "metric": "x", "value": 1, "platform": "macos",
    })
    assert result["success"] is False

    # LLM raises
    monkeypatch.setattr(runbook_gen, "analyze", AsyncMock(side_effect=RuntimeError("llm")))
    result = await runbook_gen.generate_repair_runbook({
        "id": "r5", "level": "warning", "title": "T", "desc": "d",
        "metric": "x", "value": 1, "platform": "windows",
    })
    assert result["success"] is False
    assert "AI 引擎调用失败" in result["error"]

    # empty LLM output
    monkeypatch.setattr(runbook_gen, "analyze", AsyncMock(return_value=""))
    result = await runbook_gen.generate_repair_runbook({
        "id": "r6", "level": "warning", "title": "T", "desc": "d",
        "metric": "x", "value": 1, "platform": "windows",
    })
    assert result["success"] is False

    # markdown JSON
    good = json.dumps({
        "summary": "s", "commands": ["c1"], "risk_level": "low",
        "rollback": "r", "confidence": 0.5, "reasoning": "r",
    })
    monkeypatch.setattr(runbook_gen, "analyze", AsyncMock(return_value=f"```json\n{good}\n```"))
    result = await runbook_gen.generate_repair_runbook({
        "id": "r7", "level": "warning", "title": "T", "desc": "d",
        "metric": "x", "value": 1, "platform": "windows",
    })
    assert result["success"] is True

    # moderation disabled
    monkeypatch.setattr(runbook_gen, "MODERATION_AVAILABLE", False)
    monkeypatch.setattr(runbook_gen, "analyze", AsyncMock(return_value=good))
    result = await runbook_gen.generate_repair_runbook({
        "id": "r8", "level": "warning", "title": "T", "desc": "d",
        "metric": "x", "value": 1, "platform": "windows",
    })
    assert result["success"] is True

    # audit disabled
    monkeypatch.setattr(runbook_gen, "MODERATION_AVAILABLE", True)
    monkeypatch.setattr(runbook_gen, "AUDIT_AVAILABLE", False)
    monkeypatch.setattr(runbook_gen, "analyze", AsyncMock(return_value=good))
    result = await runbook_gen.generate_repair_runbook({
        "id": "r9", "level": "warning", "title": "T", "desc": "d",
        "metric": "x", "value": 1, "platform": "windows",
    })
    assert result["success"] is True

    # guard analysis raises
    monkeypatch.setattr(runbook_gen, "AUDIT_AVAILABLE", True)
    monkeypatch.setattr(
        runbook_gen,
        "analyze_command",
        lambda cmd: (_ for _ in ()).throw(RuntimeError("bad")),
    )
    monkeypatch.setattr(runbook_gen, "analyze", AsyncMock(return_value=good))
    result = await runbook_gen.generate_repair_runbook({
        "id": "r10", "level": "warning", "title": "T", "desc": "d",
        "metric": "x", "value": 1, "platform": "windows",
    })
    assert result["success"] is False
    assert "护栏审查异常" in result["error"]

    # upsert pending approval raises
    monkeypatch.setattr(runbook_gen, "analyze_command", lambda cmd: {"risk_level": RiskLevel.LOW})
    monkeypatch.setattr(
        runbook_gen, "upsert_pending_approval", MagicMock(side_effect=RuntimeError("queue"))
    )
    monkeypatch.setattr(runbook_gen, "analyze", AsyncMock(return_value=good))
    result = await runbook_gen.generate_repair_runbook({
        "id": "r11", "level": "warning", "title": "T", "desc": "d",
        "metric": "x", "value": 1, "platform": "windows",
    })
    assert result["success"] is False
    assert "审批队列写入失败" in result["error"]

    # RAG empty list
    monkeypatch.setattr(runbook_gen, "upsert_pending_approval", MagicMock(return_value=None))
    monkeypatch.setattr(runbook_gen, "search_similar", lambda *a, **k: [])
    monkeypatch.setattr(runbook_gen, "analyze", AsyncMock(return_value=good))
    result = await runbook_gen.generate_repair_runbook({
        "id": "r12", "level": "warning", "title": "T", "desc": "d",
        "metric": "x", "value": 1, "platform": "windows",
    })
    assert result["success"] is True

    # RAG raises
    monkeypatch.setattr(
        runbook_gen, "search_similar", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("rag"))
    )
    monkeypatch.setattr(runbook_gen, "analyze", AsyncMock(return_value=good))
    result = await runbook_gen.generate_repair_runbook({
        "id": "r13", "level": "warning", "title": "T", "desc": "d",
        "metric": "x", "value": 1, "platform": "windows",
    })
    assert result["success"] is True


def test_validate_and_normalize_runbook_more():
    too_many = {
        "summary": "s", "commands": ["c"] * 6, "risk_level": "low",
    }
    ok, err, _ = runbook_gen._validate_and_normalize_runbook(too_many)
    assert not ok and "最多 5 条" in err

    bad_conf = {
        "summary": "s", "commands": ["c"], "risk_level": "low",
        "confidence": 99.0,
    }
    ok, _, rb = runbook_gen._validate_and_normalize_runbook(bad_conf)
    assert ok and rb["confidence"] == 1.0

    bad_rollback = {
        "summary": "s", "commands": ["c"], "risk_level": "low",
        "rollback": 123, "reasoning": 456,
    }
    ok, _, rb = runbook_gen._validate_and_normalize_runbook(bad_rollback)
    assert ok and rb["rollback"] == "无需回滚" and "AI 自动生成" in rb["reasoning"]


def test_extract_first_json_object_tricky():
    nested = 'x {"a": {"b": 1}, "c": "}"} y'
    assert runbook_gen._extract_first_json_object(nested) == '{"a": {"b": 1}, "c": "}"}'
    escaped = '{"a": "b\\"c", "d": "}"}'
    assert runbook_gen._extract_first_json_object(escaped) == escaped

