# -*- coding: utf-8 -*-
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = [pytest.mark.core]


# ---------------------------------------------------------------------------
# windows_repair
# ---------------------------------------------------------------------------
from core import windows_repair as wr


def test_windows_repair_registry():
    assert "restart_service" in wr.WINDOWS_REPAIR_SCRIPTS
    assert wr.WINDOWS_REPAIR_SCRIPTS["clear_cache"]["params"] == []
    history = wr.get_windows_repair_history(limit=5)
    assert history == []


@pytest.mark.asyncio
async def test_execute_windows_repair():
    result = await wr.execute_windows_repair("clear_cache", {})
    assert result == {}


# ---------------------------------------------------------------------------
# workflow/engine/state_machine
# ---------------------------------------------------------------------------
from core.workflow.engine import state_machine as sm


def test_workflow_state_machine_full_lifecycle():
    machine = sm.WorkflowStateMachine("wf-1")
    assert machine.current_state == sm.WorkflowState.IDLE
    assert not machine.is_terminal()
    assert not machine.is_running()
    assert not machine.is_paused()
    assert machine.can_transition(sm.WorkflowEvent.START)

    # invalid transition raises
    with pytest.raises(ValueError):
        machine.transition(sm.WorkflowEvent.COMPLETE)

    # start
    assert machine.transition(sm.WorkflowEvent.START)
    assert machine.current_state == sm.WorkflowState.RUNNING
    assert machine.is_running()

    # pause and resume
    assert machine.transition(sm.WorkflowEvent.PAUSE)
    assert machine.is_paused()
    assert machine.transition(sm.WorkflowEvent.RESUME)
    assert machine.current_state == sm.WorkflowState.RUNNING

    # complete with failing action
    action_called = {}

    def action(ctx):
        action_called["ctx"] = ctx
        raise RuntimeError("boom")

    machine.register_transition_action(sm.WorkflowState.RUNNING, sm.WorkflowEvent.COMPLETE, action)
    assert machine.transition(sm.WorkflowEvent.COMPLETE, {"payload": 1})
    assert action_called == {"ctx": {"payload": 1}}
    assert machine.current_state == sm.WorkflowState.COMPLETED
    assert machine.is_terminal()

    history = machine.get_history()
    assert len(history) == 4
    assert history[-1]["to_state"] == "completed"

    machine.reset()
    assert machine.current_state == sm.WorkflowState.IDLE
    assert machine.get_history() == []


def test_workflow_state_machine_cancel_and_retry():
    # cancel from running
    m1 = sm.WorkflowStateMachine("wf-2")
    m1.transition(sm.WorkflowEvent.START)
    m1.transition(sm.WorkflowEvent.CANCEL)
    assert m1.current_state == sm.WorkflowState.CANCELLED
    assert m1.is_terminal()

    # retry from failed
    m2 = sm.WorkflowStateMachine("wf-3")
    m2.transition(sm.WorkflowEvent.START)
    m2.transition(sm.WorkflowEvent.FAIL)
    assert m2.current_state == sm.WorkflowState.FAILED
    m2.transition(sm.WorkflowEvent.RETRY)
    assert m2.current_state == sm.WorkflowState.RUNNING

    # cancel from paused
    m3 = sm.WorkflowStateMachine("wf-4")
    m3.transition(sm.WorkflowEvent.START)
    m3.transition(sm.WorkflowEvent.PAUSE)
    m3.transition(sm.WorkflowEvent.CANCEL)
    assert m3.current_state == sm.WorkflowState.CANCELLED


def test_state_transition_dataclass():
    t = sm.StateTransition(
        from_state=sm.WorkflowState.IDLE,
        to_state=sm.WorkflowState.RUNNING,
        event=sm.WorkflowEvent.START,
    )
    assert t.from_state == sm.WorkflowState.IDLE
    assert t.action is None


# ---------------------------------------------------------------------------
# agent/state
# ---------------------------------------------------------------------------
from core.agent import state as agent_state


def test_diagnostic_state_update_branches():
    state = agent_state.DiagnosticState()

    # collection branch
    state.update_from_task("collect metrics", {"summary": "cpu=80"})
    assert len(state.data_collected) == 1

    # analysis branch
    state.update_from_task("analyze logs", {"summary": "disk issue"})
    assert state.current_hypothesis == "disk issue"
    assert "disk issue" in state.pending_verification

    # verification branch with pending
    state.update_from_task("verify hypothesis", {"summary": "disk full"})
    assert len(state.confirmed_findings) == 1
    assert state.pending_verification == []

    # verification branch without pending
    state2 = agent_state.DiagnosticState()
    state2.update_from_task("validate config", {"summary": "ok"})
    assert len(state2.confirmed_findings) == 1
    assert state2.confirmed_findings[0]["confidence"] == 0.6

    # execution branch
    state2.update_from_task("restart service", {"summary": "done"})
    assert state2.recommended_action == "done"
    assert state2.confidence >= 0.75

    # report branch
    state3 = agent_state.DiagnosticState()
    state3.update_from_task("generate report", {"summary": "report data"})
    assert state3.recommended_action == "report data"

    # generic branch
    state4 = agent_state.DiagnosticState()
    state4.update_from_task("foo", {"summary": "generic"})
    assert len(state4.data_collected) == 1


def test_diagnostic_state_error_and_helpers():
    state = agent_state.DiagnosticState()
    state.update_from_task("collect", {"ok": 1}, error="timeout")
    assert len(state.ruled_out) == 1

    state.set_hypothesis("memory leak")
    assert state.current_hypothesis == "memory leak"
    assert "memory leak" in state.pending_verification

    state.add_data("cpu", 99)
    assert state.data_collected[-1] == {"key": "cpu", "value": 99}

    state.rule_out("memory leak", "not present")
    assert state.current_hypothesis is None
    assert len(state.ruled_out) == 2

    state.confirm("disk", "df -h", 0.95)
    assert state.confidence == 0.95


def test_diagnostic_state_serialization():
    state = agent_state.DiagnosticState(
        confirmed_findings=[{"finding": "x"}],
        current_hypothesis="x",
        confidence=0.5,
    )
    d = state.to_dict()
    assert d["current_hypothesis"] == "x"
    restored = agent_state.DiagnosticState.from_dict(d)
    assert restored.current_hypothesis == "x"


def test_summarize_result():
    assert agent_state.DiagnosticState._summarize_result(None) == "no result"
    assert agent_state.DiagnosticState._summarize_result({"summary": "ok"}) == "ok"
    assert "status=" in agent_state.DiagnosticState._summarize_result({"status": "ok", "result": "r"})
    assert "list[2]" in agent_state.DiagnosticState._summarize_result([1, 2])
    assert agent_state.DiagnosticState._summarize_result("x" * 300) == "x" * 200


# ---------------------------------------------------------------------------
# query_optimization
# ---------------------------------------------------------------------------
import core.query_optimization as qo


class _FakeColumn:
    def in_(self, *args, **kwargs):
        return MagicMock()


class _FakeModel:
    id = _FakeColumn()


@pytest.fixture
def fake_session():
    sess = MagicMock()
    # AsyncMock called returns the MagicMock result so non-await downstream works
    sess.execute = AsyncMock(return_value=MagicMock())
    return sess


@pytest.mark.asyncio
async def test_batch_get_by_ids(monkeypatch, fake_session):
    obj1 = MagicMock(id=1)
    obj2 = MagicMock(id=2)
    fake_session.execute.return_value.scalars.return_value.all.return_value = [obj1, obj2]
    stmt = MagicMock()
    select_mock = MagicMock(return_value=stmt)
    monkeypatch.setattr(qo, "select", select_mock)

    result = await qo.BatchQueryOptimizer.batch_get_by_ids(fake_session, _FakeModel, [1, 2])
    assert result == {1: obj1, 2: obj2}

    # empty/invalid cases
    assert await qo.BatchQueryOptimizer.batch_get_by_ids(fake_session, _FakeModel, []) == {}
    assert await qo.BatchQueryOptimizer.batch_get_by_ids(fake_session, None, [1]) == {}
    assert await qo.BatchQueryOptimizer.batch_get_by_ids(None, _FakeModel, [1]) == {}


@pytest.mark.asyncio
async def test_batch_get_relations(monkeypatch, fake_session):
    parent1 = MagicMock(id=10)
    parent2 = MagicMock(id=20)
    rel1 = MagicMock(id=10)
    rel2 = MagicMock(id=10)
    rel3 = MagicMock(id=20)
    fake_session.execute.return_value.scalars.return_value.all.return_value = [rel1, rel2, rel3]
    stmt = MagicMock()
    monkeypatch.setattr(qo, "select", MagicMock(return_value=stmt))

    result = await qo.BatchQueryOptimizer.batch_get_relations(
        fake_session, [parent1, parent2], "children", _FakeModel
    )
    assert set(result.keys()) == {10, 20}
    assert len(result[10]) == 2
    assert result[20] == [rel3]
    assert await qo.BatchQueryOptimizer.batch_get_relations(fake_session, [], "children", _FakeModel) == {}


def test_with_eager_loading():
    stmt = MagicMock()
    stmt.options.return_value = stmt
    opt1 = MagicMock()
    opt2 = MagicMock()
    result = qo.BatchQueryOptimizer.with_eager_loading(stmt, opt1, opt2)
    assert stmt.options.call_count == 2
    assert result is stmt


def test_query_cache():
    cache = qo.QueryCache()
    assert cache.get("missing") is None
    cache.set("key", "value")
    assert cache.get("key") == "value"
    cache.invalidate("key")
    assert cache.get("key") is None

    # expiration by negative ttl
    cache.set("x", 1, ttl=-1)
    assert cache.get("x") is None

    cache.set("a", 1)
    cache.set("b", 2)
    cache.cleanup_expired()
    assert cache.get("a") is None
    assert cache.get("b") is None


@pytest.mark.asyncio
async def test_optimize_alert_query(monkeypatch, fake_session):
    import core.models as _models

    class FakeAlert:
        details = "details"
        tags = "tags"
        assignee = "assignee"

    monkeypatch.setattr(_models, "Alert", FakeAlert)

    stmt = MagicMock()
    stmt.options.return_value = stmt
    stmt.limit.return_value = stmt
    stmt.offset.return_value = stmt
    load_mock = MagicMock()
    select_mock = MagicMock(return_value=stmt)
    monkeypatch.setattr(qo, "select", select_mock)
    monkeypatch.setattr(qo, "selectinload", load_mock)

    fake_alert = MagicMock()
    fake_session.execute.return_value.scalars.return_value.all.return_value = [fake_alert]

    result = qo.optimize_alert_query(fake_session)
    assert result is stmt
    assert select_mock.called
    alerts = await qo.get_alerts_with_relations(fake_session, limit=10, offset=0)
    assert alerts == [fake_alert]
    assert load_mock.call_count >= 3


@pytest.mark.asyncio
async def test_optimize_metrics_query(monkeypatch, fake_session):
    import core.models as _models

    class FakeMetrics:
        source = "source"

    monkeypatch.setattr(_models, "Metrics", FakeMetrics)

    stmt = MagicMock()
    stmt.options.return_value = stmt
    stmt.limit.return_value = stmt
    stmt.offset.return_value = stmt
    load_mock = MagicMock()
    select_mock = MagicMock(return_value=stmt)
    monkeypatch.setattr(qo, "select", select_mock)
    monkeypatch.setattr(qo, "joinedload", load_mock)

    fake_metric = MagicMock()
    fake_session.execute.return_value.scalars.return_value.all.return_value = [fake_metric]

    result = qo.optimize_metrics_query(fake_session)
    assert result is stmt
    metrics = await qo.get_metrics_with_sources(fake_session, limit=5, offset=0)
    assert metrics == [fake_metric]
    assert load_mock.called


# ---------------------------------------------------------------------------
# auth_service
# ---------------------------------------------------------------------------
import core.auth_service as auth
import config as _config


@pytest.fixture
def auth_config(monkeypatch):
    monkeypatch.setattr(_config, "JWT_SECRET_KEY", "secret", raising=False)
    monkeypatch.setattr(_config, "JWT_ALGORITHM", "HS256", raising=False)
    monkeypatch.setattr(_config, "JWT_ISSUER", "test-issuer", raising=False)
    monkeypatch.setattr(_config, "JWT_AUDIENCE", "test-aud", raising=False)
    monkeypatch.setattr(_config, "JWT_ACCESS_EXPIRE_MINUTES", 30, raising=False)
    monkeypatch.setattr(_config, "INTERNAL_API_KEY", "internal-key", raising=False)
    monkeypatch.setattr(auth, "is_blacklisted", lambda jti: False)


def fake_user(**kwargs):
    defaults = {"id": 1, "username": "alice", "role": "viewer", "is_active": True, "tenant_id": "default"}
    defaults.update(kwargs)
    return MagicMock(**defaults)


def fake_db_session(query_result=None, count_result=0):
    sess = MagicMock()
    sess.__enter__ = MagicMock(return_value=sess)
    sess.__exit__ = MagicMock(return_value=False)
    sess.query.return_value.filter.return_value.first.return_value = query_result
    sess.query.return_value.filter.return_value.count.return_value = count_result
    sess.query.return_value.filter.return_value.all.return_value = [MagicMock()] if query_result else []
    return sess


def test_hash_and_verify_password():
    h = auth.hash_password("pw")
    assert isinstance(h, str)
    assert auth.verify_password("pw", h)
    assert not auth.verify_password("wrong", h)


def test_create_and_decode_token(auth_config):
    token = auth.create_access_token({"sub": "alice"})
    payload = auth.decode_token(token)
    assert payload["sub"] == "alice"
    assert payload["tenant_id"] == "default"
    assert "jti" in payload
    assert "iss" in payload


def test_decode_token_blacklisted(auth_config, monkeypatch):
    token = auth.create_access_token({"sub": "alice"})
    monkeypatch.setattr(auth, "is_blacklisted", lambda jti: True)
    with pytest.raises(Exception):
        auth.decode_token(token)


def test_get_current_user_found(auth_config, monkeypatch):
    user = fake_user(username="alice")
    sess = fake_db_session(query_result=user)
    monkeypatch.setattr(auth, "SessionLocal", lambda: sess)
    token = auth.create_access_token({"sub": "alice"})
    result = auth.get_current_user(token)
    assert result == user
    assert result.tenant_id == "default"


def test_get_current_user_missing_or_inactive(auth_config, monkeypatch):
    sess = fake_db_session(query_result=None)
    monkeypatch.setattr(auth, "SessionLocal", lambda: sess)
    with pytest.raises(Exception):
        auth.get_current_user("no-token")

    token = auth.create_access_token({"sub": "invalid"})
    with pytest.raises(Exception):
        auth.get_current_user(token)

    inactive = fake_user(username="bob", is_active=False)
    sess2 = fake_db_session(query_result=inactive)
    monkeypatch.setattr(auth, "SessionLocal", lambda: sess2)
    with pytest.raises(Exception):
        auth.get_current_user(token)


def test_get_current_user_bad_payload(auth_config):
    with pytest.raises(Exception):
        auth.get_current_user(auth.create_access_token({"sub": 123}))


def test_has_role():
    user = fake_user(role="admin")
    assert auth.has_role(user, "admin")
    assert not auth.has_role(user, "viewer")
    user.is_active = False
    assert not auth.has_role(user, "admin")


def test_require_roles():
    admin = fake_user(role="admin")
    dep = auth.require_roles("admin")
    assert dep(admin) == admin

    viewer = fake_user(role="viewer")
    dep2 = auth.require_roles("admin")
    with pytest.raises(Exception):
        dep2(viewer)


def test_require_permission_admin():
    admin = fake_user(role="admin")
    dep = auth.require_permission("edit", "asset")
    assert dep(admin) == admin


def test_require_permission_missing(monkeypatch):
    user = fake_user(username="user", role="viewer")
    sess = fake_db_session(query_result=None)
    monkeypatch.setattr(auth, "SessionLocal", lambda: sess)
    dep = auth.require_permission("edit", "asset")
    with pytest.raises(Exception):
        dep(user)


def test_admin_count_and_max_admin_check():
    sess = fake_db_session(count_result=2)
    assert auth.admin_count(sess) == 2
    auth.max_admin_check(sess)

    sess3 = fake_db_session(count_result=3)
    with pytest.raises(Exception):
        auth.max_admin_check(sess3)


def test_asset_permission_checks(monkeypatch):
    user = fake_user(role="admin")
    assert auth.can_edit_asset(user, 1)
    assert auth.can_view_asset(user, 1)

    user2 = fake_user(role="operator")
    assert auth.can_edit_asset(user2, 1)

    user3 = fake_user(role="business")
    sess = fake_db_session(query_result=MagicMock())
    monkeypatch.setattr(auth, "SessionLocal", lambda: sess)
    assert auth.can_edit_asset(user3, 1)
    assert auth.can_view_asset(user3, 1)

    user4 = fake_user(role="viewer")
    assert auth.can_view_asset(user4, 1)
    assert not auth.can_edit_asset(user4, 1)

    user5 = fake_user(role="business")
    sess2 = fake_db_session(query_result=None)
    monkeypatch.setattr(auth, "SessionLocal", lambda: sess2)
    assert not auth.can_edit_asset(user5, 1)


def test_is_internal_key(monkeypatch):
    monkeypatch.setattr(_config, "INTERNAL_API_KEY", "internal-key", raising=False)
    req = MagicMock()
    req.headers = {"X-Internal-Key": "internal-key"}
    assert auth.is_internal_key(req)
    req.headers = {}
    assert not auth.is_internal_key(req)


# ---------------------------------------------------------------------------
# llm_cost_monitor
# ---------------------------------------------------------------------------
import core.llm_cost_monitor as lcm


@pytest.fixture
def fake_token_budget(monkeypatch):
    import core.ai.token_budget as tb

    monkeypatch.setattr(tb, "estimate_tokens", lambda text, model=None: len(text.split()))


def test_safe_float_env(monkeypatch):
    monkeypatch.setenv("TEST_FLOAT", "12.5")
    assert lcm._safe_float_env("TEST_FLOAT", 0.0) == 12.5

    monkeypatch.setenv("TEST_FLOAT2", "abc")
    assert lcm._safe_float_env("TEST_FLOAT2", 5.0) == 5.0

    monkeypatch.setenv("TEST_FLOAT3", "0.5")
    assert lcm._safe_float_env("TEST_FLOAT3", 0.0, min_val=1.0) == 1.0

    monkeypatch.setenv("TEST_FLOAT4", "100")
    assert lcm._safe_float_env("TEST_FLOAT4", 0.0, max_val=50.0) == 50.0


def test_llm_cost_monitor_default_and_config(fake_token_budget):
    monitor = lcm.LLMCostMonitor()
    assert monitor.get_model_config("gpt-4o-mini") is not None
    assert monitor.get_cost_per_1k("gpt-4o-mini") == 0.015
    assert monitor.get_cost_per_1k("missing", default=0.1) == 0.1

    cfg = [{"model": "custom", "cost_per_1k": 0.5, "name": "custom"}]
    m2 = lcm.LLMCostMonitor(model_configs=cfg, token_cost_threshold=1000, budget_per_request=1.0)
    assert m2.get_model_config("custom") == cfg[0]
    assert m2.token_cost_threshold == 1000


def test_estimate_and_check_budget(fake_token_budget):
    monitor = lcm.LLMCostMonitor()
    cost = monitor.estimate_cost("gpt-4o-mini", 1000, 500)
    expected = (1500 / 1000.0) * 0.015
    assert abs(cost - expected) < 1e-9

    assert monitor.check_budget(cost)
    assert not monitor.check_budget(1000.0)


def test_record_and_stats(fake_token_budget, monkeypatch):
    monitor = lcm.LLMCostMonitor()
    now = 100000.0
    monkeypatch.setattr(lcm.time, "time", lambda: now)
    assert monitor.check_budget(0.1)
    monitor.record_cost(0.1)
    stats = monitor.get_hourly_stats()
    assert stats["hourly_cost"] == 0.1
    assert stats["daily_cost"] == 0.1
    assert stats["avg_cost_per_request"] == 0.1

    # advance > 1 hour to reset hour window
    monkeypatch.setattr(lcm.time, "time", lambda: now + 4000)
    monitor.record_cost(0.1)
    stats = monitor.get_hourly_stats()
    assert stats["hourly_cost"] == 0.1
    assert stats["daily_cost"] == 0.2


def test_llm_cost_monitor_singleton(monkeypatch):
    lcm.reset_llm_cost_monitor()
    m1 = lcm.get_llm_cost_monitor()
    m2 = lcm.get_llm_cost_monitor()
    assert m1 is m2
    custom = lcm.LLMCostMonitor()
    lcm.set_llm_cost_monitor(custom)
    assert lcm.get_llm_cost_monitor() is custom
    lcm.reset_llm_cost_monitor()


def test_session_budget():
    budget = lcm.SessionBudget("s-1", max_tokens=100, max_cost=1.0)
    assert budget.check_and_record(50, 0.5)
    assert budget.tokens_used == 50
    assert budget.cost_used == 0.5
    assert not budget.check_and_record(60)
    assert not budget.check_and_record(10, 0.6)
    budget.record_cost(0.1)
    assert budget.cost_used == 0.6


def test_get_session_budget(monkeypatch):
    monkeypatch.setattr(lcm, "_SESSION_BUDGETS", {}, raising=False)
    monkeypatch.setattr(lcm, "_DEFAULT_SESSION_TOKEN_BUDGET", 1000, raising=False)
    monkeypatch.setattr(lcm, "_DEFAULT_SESSION_COST_BUDGET", 1.0, raising=False)
    assert lcm.get_session_budget(None) is None
    b1 = lcm.get_session_budget("sess-1")
    b2 = lcm.get_session_budget("sess-1")
    assert b1 is b2
