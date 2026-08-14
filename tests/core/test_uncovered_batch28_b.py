# -*- coding: utf-8 -*-
"""Batch 28b tests for low-coverage core modules."""
import asyncio
import json
import platform
from datetime import datetime, timezone, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = [pytest.mark.core]


# ------------------------------------------------------------------
# helpers for mocking core.db_engine AsyncSession
# ------------------------------------------------------------------
class _FakeResult:
    def __init__(self):
        self.rowcount = 0
        self.scalar_one_or_none = MagicMock(return_value=None)
        self.scalar = MagicMock(return_value=0)
        self._scalars_all = []

    def scalars(self):
        m = MagicMock()
        m.all = MagicMock(return_value=self._scalars_all)
        return m


class _FakeSession:
    def __init__(self):
        self.add = MagicMock()
        self.commit = AsyncMock()
        self.rollback = AsyncMock()
        self.execute = AsyncMock(return_value=_FakeResult())

    def set_scalars(self, items):
        self.execute.return_value._scalars_all = items
        return self

    def set_scalar_one_or_none(self, value):
        self.execute.return_value.scalar_one_or_none.return_value = value
        return self

    def set_scalar(self, value):
        self.execute.return_value.scalar.return_value = value
        return self

    def set_rowcount(self, n):
        self.execute.return_value.rowcount = n
        return self


class _FakeSessionCtx:
    def __init__(self, session):
        self._session = session

    async def __aenter__(self):
        return self._session

    async def __aexit__(self, *args):
        pass


class _FakeEngineConn:
    def __init__(self):
        self.run_sync = AsyncMock()


class _FakeEngine:
    def begin(self):
        return _FakeSessionCtx(_FakeEngineConn())


@pytest.fixture
def fake_db_session(monkeypatch):
    session = _FakeSession()
    monkeypatch.setattr(
        "core.db_engine.AsyncSessionLocal", lambda *a, **k: _FakeSessionCtx(session)
    )
    return session


class _FakeAlert:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


# ------------------------------------------------------------------
# core/priority/resource_allocator.py
# ------------------------------------------------------------------
from core.priority.resource_allocator import Resource, ResourceAllocator


def test_resource_allocator_basic():
    allocator = ResourceAllocator()
    allocator.add_resource(Resource(id="r1", type="cpu", capacity=10, available=10))
    tasks = [
        {"id": "t1", "priority": 1, "resource_requirement": {"cpu": 3}},
        {"id": "t2", "priority": 9, "resource_requirement": {"cpu": 2}},
        {"id": "t3", "priority": 5, "resource_requirement": {"cpu": 0}},
    ]
    allocs = allocator.allocate(tasks, "cpu")
    assert allocs[0].task_id == "t2"
    assert len(allocs) == 2
    assert allocator.get_utilization("r1")["allocated"] == 5
    allocator.release("t1")
    assert allocator.get_utilization("r1")["allocated"] == 2
    overall = allocator.get_utilization()
    assert overall["total_capacity"] == 10
    assert "r1" in overall["resources"]


def test_resource_allocator_no_resources():
    allocator = ResourceAllocator()
    assert allocator.allocate([{"id": "t", "priority": 1, "resource_requirement": {"cpu": 1}}], "cpu") == []
    assert allocator.get_utilization("missing") == {}


def test_resource_allocator_optimize():
    allocator = ResourceAllocator()
    allocator.add_resource(Resource(id="r1", type="cpu", capacity=10, available=10))
    allocator.allocate([{"id": "lo", "priority": 0.1, "resource_requirement": {"cpu": 2}}], "cpu")
    allocator.optimize_allocation()
    assert allocator.resources["r1"].available == 10


# ------------------------------------------------------------------
# core/agent/behavior_monitor.py
# ------------------------------------------------------------------
from core.agent.behavior_monitor import BehaviorMonitor, get_behavior_monitor


def test_behavior_monitor_anomalies():
    monitor = BehaviorMonitor()
    monitor.set_thresholds(
        max_iterations=2,
        max_total_tool_calls=3,
        max_tool_repetitions=1,
        max_errors=1,
        max_execution_time_seconds=0,
    )
    agent = "agent-1"
    monitor.record_iteration(agent)
    monitor.record_iteration(agent)
    monitor.record_iteration(agent)
    assert monitor.check_anomaly(agent) is not None
    assert "iteration limit exceeded" in monitor.check_anomaly(agent)["messages"][0]


def test_behavior_monitor_tool_and_actions():
    monitor = BehaviorMonitor()
    monitor.set_thresholds(max_total_tool_calls=1, max_tool_repetitions=1)
    agent = "a2"
    monitor.record_tool_call(agent, "tool_x")
    monitor.record_tool_call(agent, "tool_x")
    anomaly = monitor.check_anomaly(agent)
    assert anomaly and any("total tool call limit" in m for m in anomaly["messages"])

    monitor2 = BehaviorMonitor()
    monitor2.set_thresholds(max_tool_repetitions=1)
    monitor2.record_action(agent, "action_sig")
    monitor2.record_action(agent, "action_sig")
    anomaly2 = monitor2.check_anomaly(agent)
    assert anomaly2 and any("repeated action" in m for m in anomaly2["messages"])


def test_behavior_monitor_summary_and_reset():
    monitor = BehaviorMonitor()
    monitor.record_error("a3")
    assert monitor.get_summary("a3")["errors"] == 1
    assert not monitor.get_summary("missing")["found"]
    monitor.reset("a3")
    assert monitor.get_summary("a3")["found"] is False
    monitor.reset()
    assert monitor.get_summary() == {}


def test_behavior_monitor_global():
    g1 = get_behavior_monitor()
    g2 = get_behavior_monitor()
    assert g1 is g2


# ------------------------------------------------------------------
# core/logging/level/level_manager.py
# ------------------------------------------------------------------
from core.logging.level.level_manager import (
    LogLevel,
    LogLevelConfig,
    LogLevelManager,
    get_level_manager,
    get_log_level,
    set_log_level,
)


def test_log_level_enum():
    assert LogLevel.from_string("debug") == LogLevel.DEBUG
    assert LogLevel.from_int(20) == LogLevel.INFO
    assert LogLevel.WARNING.to_string() == "WARNING"
    with pytest.raises(ValueError):
        LogLevel.from_string("nope")
    with pytest.raises(ValueError):
        LogLevel.from_int(999)


def test_log_level_manager(tmp_path):
    config = LogLevelConfig(
        default_level=LogLevel.INFO,
        module_levels={"mod1": LogLevel.ERROR},
    )
    mgr = LogLevelManager(config)
    assert mgr.get_default_level() == LogLevel.INFO
    mgr.set_default_level(LogLevel.DEBUG)
    assert mgr.get_default_level() == LogLevel.DEBUG
    assert mgr.get_module_level("mod1") == LogLevel.ERROR
    assert mgr.get_effective_level("mod1") == LogLevel.ERROR
    assert mgr.get_effective_level("other") == LogLevel.DEBUG

    mgr.set_module_level("mod2", LogLevel.WARNING)
    mgr.remove_module_level("mod2")
    assert mgr.get_effective_level("mod2") == LogLevel.DEBUG

    mgr.set_level_from_string("error", "mod3")
    assert mgr.get_effective_level("mod3") == LogLevel.ERROR
    mgr.set_level_from_string("critical")
    assert mgr.get_default_level() == LogLevel.CRITICAL

    cfg_file = tmp_path / "levels.json"
    cfg_file.write_text(json.dumps({"default_level": "INFO", "module_levels": {"x": "DEBUG"}}))
    mgr2 = LogLevelManager()
    mgr2.load_config_from_file(str(cfg_file))
    assert mgr2.get_default_level() == LogLevel.INFO
    assert mgr2.get_effective_level("x") == LogLevel.DEBUG

    out_file = tmp_path / "out.json"
    mgr2.save_config_to_file(str(out_file))
    data = json.loads(out_file.read_text())
    assert data["default_level"] == "INFO"
    assert "x" in data["module_levels"]

    assert len(mgr2.get_level_history()) > 0
    mgr2.clear_level_history()
    assert mgr2.get_level_history() == []
    assert isinstance(mgr2.get_all_module_levels(), dict)

    mgr2.reset_to_defaults()
    assert mgr2.get_default_level() == LogLevel.INFO


def test_log_level_manager_invalid_file(tmp_path, caplog):
    mgr = LogLevelManager()
    missing = tmp_path / "missing.json"
    mgr.load_config_from_file(str(missing))
    yaml = tmp_path / "cfg.yaml"
    yaml.write_text("a: 1")
    mgr.load_config_from_file(str(yaml))
    assert mgr.get_default_level() == LogLevel.INFO


def test_log_level_global():
    mgr = get_level_manager()
    assert isinstance(mgr, LogLevelManager)
    set_log_level(LogLevel.CRITICAL)
    assert get_log_level() == LogLevel.CRITICAL


# ------------------------------------------------------------------
# core/logging/analysis/log_analyzer.py
# ------------------------------------------------------------------
from core.logging.analysis.log_analyzer import LogAnalyzer, get_log_analyzer


def test_log_analyzer_statistics_and_trends():
    analyzer = LogAnalyzer()
    now = datetime.now().isoformat()
    entries = [
        {
            "timestamp": now,
            "level": "ERROR",
            "message": "error 123 on /api/v1/resource",
            "module": "core.x",
            "context": {"response_time": 0.2, "user_id": "u1", "trace_id": "t1"},
        },
        {
            "timestamp": now,
            "level": "INFO",
            "message": "ok 456",
            "module": "core.x",
            "context": {"response_time": 0.1, "user_id": "u2", "trace_id": "t2"},
        },
    ]
    analyzer.add_logs(entries)
    assert analyzer.get_buffer_size() == 2
    stats = analyzer.calculate_statistics()
    assert stats.total_logs == 2
    assert stats.error_rate == 0.5
    assert stats.unique_users == 2
    assert stats.unique_traces == 2
    assert "ERROR" in stats.level_counts

    trends = analyzer.calculate_trends(interval=timedelta(minutes=1))
    assert len(trends.time_series) == 1
    assert trends.peak_value == 2
    assert trends.growth_rate == 0.0


def test_log_analyzer_time_filter_and_patterns():
    analyzer = LogAnalyzer()
    start = datetime(2024, 1, 1, 10, 0, 0)
    mid = datetime(2024, 1, 1, 10, 5, 0)
    end = datetime(2024, 1, 1, 10, 10, 0)
    entries = [
        {
            "timestamp": start.isoformat(),
            "level": "WARNING",
            "message": "timeout 192.168.1.1 uuid-1234-retry-5",
            "module": "core.y",
        },
        {
            "timestamp": mid.isoformat(),
            "level": "WARNING",
            "message": "timeout 192.168.1.2 uuid-1234-retry-6",
            "module": "core.y",
        },
        {
            "timestamp": end.isoformat(),
            "level": "INFO",
            "message": "done",
            "module": "core.z",
        },
    ]
    analyzer.add_logs(entries)
    stats = analyzer.calculate_statistics(time_range=(start, mid))
    assert stats.total_logs == 2
    patterns = analyzer.detect_patterns(min_occurrences=2)
    assert any("timeout" in p.pattern for p in patterns)
    analyzer.clear_buffer()
    assert analyzer.get_buffer_size() == 0


def test_log_analyzer_to_dicts():
    from core.logging.analysis.log_analyzer import (
        LogStatistics,
        LogTrends,
        LogPattern,
    )

    s = LogStatistics()
    assert "total_logs" in s.to_dict()
    t = LogTrends()
    assert "time_series" in t.to_dict()
    p = LogPattern(pattern="p")
    assert p.to_dict()["pattern"] == "p"


def test_log_analyzer_global():
    g = get_log_analyzer()
    assert isinstance(g, LogAnalyzer)


# ------------------------------------------------------------------
# core/workflow/engine/executor.py
# ------------------------------------------------------------------
from core.workflow.engine.dag import DAG, DAGNode
from core.workflow.engine.executor import ExecutionContext, WorkflowExecutor
from core.workflow.engine.state_machine import WorkflowState


def test_execution_context_to_dict():
    ctx = ExecutionContext(workflow_id="wf", run_id="r1")
    d = ctx.to_dict()
    assert d["workflow_id"] == "wf"
    assert d["end_time"] is None
    ctx.end_time = datetime.now()
    assert ctx.to_dict()["end_time"] is not None


@pytest.mark.asyncio
async def test_workflow_executor_success():
    executor = WorkflowExecutor(default_timeout=1, default_max_retries=0)

    async def handler(node, context):
        return {"node": node.id}

    executor.register_handler("noop", handler)
    dag = DAG("wf")
    dag.add_node(DAGNode(id="n1", name="N1", type="noop"))
    dag.add_node(DAGNode(id="n2", name="N2", type="noop", dependencies=["n1"]))
    ctx = await executor.execute(dag)
    assert ctx.status == WorkflowState.COMPLETED
    assert ctx.results == {"n1": {"node": "n1"}, "n2": {"node": "n2"}}


@pytest.mark.asyncio
async def test_workflow_executor_failure_and_timeout():
    executor = WorkflowExecutor(default_timeout=0.01, default_max_retries=0)

    async def bad(node, context):
        raise RuntimeError("boom")

    async def slow(node, context):
        await asyncio.sleep(5)
        return {}

    executor.register_handler("bad", bad)
    executor.register_handler("slow", slow)

    dag = DAG("f")
    dag.add_node(DAGNode(id="bad1", name="B", type="bad"))
    ctx = await executor.execute(dag)
    assert ctx.status == WorkflowState.COMPLETED
    assert "bad1" in ctx.errors

    dag2 = DAG("t")
    dag2.add_node(DAGNode(id="s1", name="S", type="slow"))
    ctx2 = await executor.execute(dag2)
    assert ctx2.status == WorkflowState.COMPLETED
    assert "s1" in ctx2.errors
    assert "timed out" in ctx2.errors["s1"]


@pytest.mark.asyncio
async def test_workflow_executor_retry():
    executor = WorkflowExecutor(
        default_timeout=1, default_max_retries=2, retry_backoff_base=0.001
    )
    attempts = {"n": 0}

    async def flaky(node, context):
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise RuntimeError("retry")
        return {"ok": True}

    executor.register_handler("flaky", flaky)
    dag = DAG("r")
    dag.add_node(DAGNode(id="n1", name="F", type="flaky"))
    ctx = await executor.execute(dag)
    assert ctx.status == WorkflowState.COMPLETED
    assert ctx.results["n1"] == {"ok": True}


def test_workflow_executor_controls():
    executor = WorkflowExecutor()
    ctx = ExecutionContext(workflow_id="wf", run_id="run-1")
    ctx.status = WorkflowState.RUNNING
    executor._active_executions[ctx.run_id] = ctx
    assert executor.pause_workflow(ctx.run_id)
    assert ctx.status == WorkflowState.PAUSED
    assert executor.resume_workflow(ctx.run_id)
    assert ctx.status == WorkflowState.RUNNING
    assert executor.cancel_workflow(ctx.run_id)
    assert ctx.status == WorkflowState.CANCELLED
    status = executor.get_execution_status(ctx.run_id)
    assert status["status"] == "cancelled"
    executor._active_executions.clear()
    assert executor.get_execution_status("missing") is None


# ------------------------------------------------------------------
# core/db_engine.py
# ------------------------------------------------------------------
import core.db_engine as db_engine


@pytest.mark.asyncio
async def test_db_engine_get_session_ok(fake_db_session):
    async with db_engine.async_get_session() as session:
        await session.execute("stmt")
    assert fake_db_session.commit.called


@pytest.mark.asyncio
async def test_db_engine_get_session_rollback(fake_db_session):
    with pytest.raises(RuntimeError):
        async with db_engine.async_get_session() as session:
            await session.execute("stmt")
            raise RuntimeError("fail")
    assert fake_db_session.rollback.called


@pytest.mark.asyncio
async def test_db_engine_init_db(monkeypatch):
    monkeypatch.setattr("core.db_engine.engine", _FakeEngine())
    await db_engine.async_init_db()


def test_db_engine_effective_url(monkeypatch):
    monkeypatch.setenv("USE_SQLITE", "true")
    monkeypatch.setenv("SQLITE_PATH", "C:\\tmp\\batch28b_test.db")
    url = db_engine._effective_database_url()
    assert url.endswith("batch28b_test.db")
    monkeypatch.delenv("USE_SQLITE")
    assert db_engine._effective_database_url() == db_engine.POSTGRES_URL


def test_db_engine_is_db_connection_error():
    assert db_engine._is_db_connection_error(ConnectionError("x"))
    e = Exception("x")
    e.__cause__ = OSError("y")
    assert db_engine._is_db_connection_error(e)
    assert not db_engine._is_db_connection_error(ValueError("x"))


@pytest.mark.asyncio
async def test_db_engine_async_insert_alert(fake_db_session, monkeypatch):
    monkeypatch.setattr("core.db_engine.Alert", _FakeAlert)
    alert = {
        "id": "a1",
        "level": "error",
        "title": "t",
        "desc": "d",
        "metadata": {},
        "platform": "windows",
        "priority": "P1",
    }
    aid = await db_engine.async_insert_alert(alert)
    assert aid == "a1"
    assert fake_db_session.add.called
    assert fake_db_session.commit.called


@pytest.mark.asyncio
async def test_db_engine_async_insert_alert_connection_error(fake_db_session, monkeypatch):
    monkeypatch.setattr("core.db_engine.Alert", _FakeAlert)
    fake_db_session.commit = AsyncMock(side_effect=ConnectionError("down"))
    alert = {"id": "a1", "title": "t", "desc": "d"}
    with pytest.raises(ConnectionError):
        await db_engine.async_insert_alert(alert)


@pytest.mark.asyncio
async def test_db_engine_async_query_alerts(fake_db_session):
    now = datetime.now()
    a = SimpleNamespace(
        id="a1",
        level="error",
        category="c",
        alert_type="t",
        title="title",
        description="desc",
        metric="m",
        value=1.0,
        detected_at=now,
        metric_time=None,
        status="pending",
        host="h",
        platform="windows",
        priority="P1",
        bis_score=0.5,
        metadata={},
        prev_suppressed=False,
        approval_id=None,
        repair_id=None,
    )
    fake_db_session.set_scalars([a])
    rows = await db_engine.async_query_alerts(limit=10, level="error")
    assert len(rows) == 1
    assert rows[0]["id"] == "a1"


@pytest.mark.asyncio
async def test_db_engine_async_count_and_clear(fake_db_session):
    fake_db_session.set_scalar(7)
    assert await db_engine.async_count_alerts(level="error") == 7
    fake_db_session.set_rowcount(5)
    assert await db_engine.async_clear_alerts() == 5


@pytest.mark.asyncio
async def test_db_engine_async_insert_and_query_repairs(fake_db_session):
    repair_id = await db_engine.async_insert_repair_record(
        success=True,
        alert_time="2024-01-01T00:00:00",
        repair_time="2024-01-01T00:00:01",
        repair_duration_sec=1.0,
        rule_name="cpu",
        script_key="cpu_high_script",
        platform="windows",
        output="ok",
    )
    assert repair_id.startswith("repair-")
    r = SimpleNamespace(
        id="r1",
        alert_id="a1",
        script_key="cpu_high_script",
        script_name="n",
        success=True,
        status="success",
        repair_time=datetime.now(),
        repair_duration_sec=1.0,
        platform="windows",
        host="h",
        output="ok",
        risk="low",
    )
    fake_db_session.set_scalars([r])
    rows = await db_engine.async_query_repairs(today_only=False, limit=5)
    assert len(rows) == 1


@pytest.mark.asyncio
async def test_db_engine_async_upsert_and_get_pending(fake_db_session):
    fake_db_session.set_scalar_one_or_none(None)
    new_id = await db_engine.async_upsert_pending_approval(
        alert_id="a1",
        rule_name="r1",
        script_key="s1",
        proposal="p1",
        alert_json="{}",
    )
    assert new_id.startswith("approval-")

    existing = SimpleNamespace(
        id="e1",
        alert_id="a1",
        alert_json="{}",
        rule_name="r1",
        script_key="s1",
        proposal="old",
        status="pending",
        risk_level="medium",
        submitted_at=None,
    )
    fake_db_session.set_scalar_one_or_none(existing)
    upd = await db_engine.async_upsert_pending_approval(
        alert_id="a1", rule_name="r1", script_key="s1", proposal="p2", alert_json="{}"
    )
    assert upd == "e1"

    app = SimpleNamespace(
        id="e1",
        alert_id="a1",
        alert_json="{}",
        rule_name="r1",
        script_key="s1",
        proposal="p2",
        status="pending",
        risk_level="medium",
        submitted_at=None,
    )
    fake_db_session.set_scalar_one_or_none(app)
    got = await db_engine.async_get_pending_approval("a1")
    assert got["id"] == "e1"


@pytest.mark.asyncio
async def test_db_engine_async_get_approval_by_alert(fake_db_session):
    app = SimpleNamespace(
        id="e1",
        alert_id="a1",
        alert_json="{}",
        rule_name="r1",
        script_key="s1",
        proposal="p",
        status="approved",
        risk_level="medium",
        approver="admin",
        approved_at=None,
        submitted_at=None,
    )
    fake_db_session.set_scalar_one_or_none(app)
    got = await db_engine.async_get_approval_by_alert("a1")
    assert got["status"] == "approved"


@pytest.mark.asyncio
async def test_db_engine_async_get_all_and_update_approvals(fake_db_session):
    a = SimpleNamespace(
        id="e1",
        alert_id="a1",
        alert_json="{}",
        rule_name="r1",
        script_key="s1",
        proposal="p",
        status="pending",
        risk_level="medium",
        submitted_at=None,
    )
    fake_db_session.set_scalars([a])
    all_ = await db_engine.async_get_all_pending_approvals()
    assert len(all_) == 1

    app = SimpleNamespace(
        id="e1",
        alert_id="a1",
        alert_json="{}",
        rule_name="r1",
        script_key="s1",
        proposal="p",
        status="pending",
        risk_level="medium",
        approver=None,
        approved_at=None,
        rejection_reason=None,
    )
    fake_db_session.set_scalar_one_or_none(app)
    assert await db_engine.async_update_approval_status("e1", "approved", approver="admin")
    fake_db_session.set_scalar_one_or_none(app)
    assert await db_engine.async_update_approval_status_by_alert("a1", "rejected", rejection_reason="no")


@pytest.mark.asyncio
async def test_db_engine_alert_repository_save(fake_db_session, monkeypatch):
    monkeypatch.setattr("core.db_engine.Alert", _FakeAlert)
    repo = db_engine.PostgreSQLAlertRepository()
    sid = await repo.save({"id": "a1", "title": "t", "desc": "d"})
    assert sid == "a1"


@pytest.mark.asyncio
async def test_db_engine_alert_repository_query_and_manage(fake_db_session):
    repo = db_engine.PostgreSQLAlertRepository()
    a = SimpleNamespace(
        id="a1",
        level="error",
        category="c",
        alert_type="t",
        title="title",
        description="desc",
        metric=None,
        value=None,
        detected_at=datetime.now(),
        metric_time=None,
        status="pending",
        host="h",
        platform="windows",
        priority="P1",
        bis_score=None,
        metadata={},
        prev_suppressed=None,
        approval_id=None,
        repair_id=None,
    )
    fake_db_session.set_scalars([a])
    rows = await repo.query(filters={"level": "error"}, limit=10)
    assert len(rows) == 1

    fake_db_session.set_scalar_one_or_none(a)
    got = await repo.get_by_id("a1")
    assert got["id"] == "a1"

    fake_db_session.set_scalar_one_or_none(a)
    assert await repo.update_status("a1", "resolved")

    fake_db_session.set_rowcount(1)
    assert await repo.delete("a1")
    fake_db_session.set_scalar(5)
    assert await repo.count() == 5
    fake_db_session.set_scalars([a])
    assert len(await repo.get_recent(limit=10)) == 1
    fake_db_session.set_rowcount(0)
    assert await repo.clear_all()


@pytest.mark.asyncio
async def test_db_engine_database_engine_component():
    from sqlalchemy import text

    db = db_engine.DatabaseEngine("sqlite:///:memory:")
    await db.connect()
    assert db.connected
    await db.execute("CREATE TABLE test (x INTEGER)")
    await db.execute("INSERT INTO test (x) VALUES (:x)", {"x": 1})
    rows = await db.fetchall("SELECT * FROM test")
    assert rows == [{"x": 1}]
    await db.disconnect()


def test_db_engine_simple_repair_db():
    db_engine.db.update_repair_status("r1", "done", "comment")
    assert db_engine.db.get_repair_record("r1")["status"] == "done"
    assert db_engine.db.get_repair_record("r1")["comment"] == "comment"


def test_db_engine_sync_wrappers(fake_db_session, monkeypatch):
    monkeypatch.setattr("core.db_engine.Alert", _FakeAlert)
    db_engine.insert_alert({"id": "a1", "title": "t", "desc": "d"})
    db_engine.insert_repair_record(
        True,
        "2024-01-01T00:00:00",
        "2024-01-01T00:00:01",
        1.0,
        "cpu",
        "cpu_high_script",
        "windows",
        "ok",
    )
    db_engine.upsert_pending_approval("a1", "r1", "s1", "p1", "{}")
    assert db_engine.get_pending_approval("missing") is None
    assert db_engine.get_all_pending_approvals() == []
    db_engine.update_approval_status("e1", "approved")
    db_engine.update_approval_status_by_alert("a1", "rejected")
    assert db_engine.count_alerts() == 0
    assert db_engine.query_alerts(limit=5) == []
    assert db_engine.clear_alerts() == 0
    assert db_engine.query_repairs(limit=5) == []
    assert db_engine.insert_verify_record(x=1) == 0


def test_db_engine_lazy_proxy_repr():
    assert repr(db_engine.AsyncSessionLocal) == "<LazyAsyncSessionLocal>"
    assert "_LazyEngineProxy" in repr(db_engine.engine)


@pytest.mark.asyncio
async def test_db_engine_ensure_and_lazy_proxy(monkeypatch):
    monkeypatch.setenv("USE_SQLITE", "true")
    monkeypatch.setenv("SQLITE_URL", "sqlite+aiosqlite:///:memory:")
    monkeypatch.setattr("core.db_engine._ENGINE", None)
    monkeypatch.setattr("core.db_engine._AsyncSessionLocal", None)
    # force lazy creation of the engine and session factory
    async with db_engine.engine.begin() as conn:
        await conn.run_sync(lambda c: None)
    async with db_engine.AsyncSessionLocal() as session:
        pass


@pytest.mark.asyncio
async def test_db_engine_database_engine_auto_connect(tmp_path):
    db_path = tmp_path / "auto.db"
    db = db_engine.DatabaseEngine(f"sqlite:///{db_path}")
    await db.execute("CREATE TABLE t (x INTEGER)")
    await db.execute("INSERT INTO t (x) VALUES (:x)", {"x": 1})
    rows = await db.fetchall("SELECT * FROM t")
    assert rows == [{"x": 1}]
    await db.disconnect()


@pytest.mark.asyncio
async def test_db_engine_alert_repository_exceptions(fake_db_session):
    fake_db_session.execute = AsyncMock(side_effect=RuntimeError("boom"))
    repo = db_engine.PostgreSQLAlertRepository()
    assert await repo.get_by_id("x") is None
    assert await repo.update_status("x", "resolved") is False
    assert await repo.delete("x") is False


def test_db_engine_sync_wrapper_exceptions(monkeypatch):
    async def _raise(*a, **k):
        raise RuntimeError("fail")

    monkeypatch.setattr("core.db_engine.async_insert_alert", _raise)
    db_engine.insert_alert({"id": "x"})

    monkeypatch.setattr("core.db_engine.async_query_alerts", _raise)
    assert db_engine.query_alerts(limit=5) == []

    monkeypatch.setattr("core.db_engine.async_count_alerts", _raise)
    assert db_engine.count_alerts() == 0

    monkeypatch.setattr("core.db_engine.async_clear_alerts", _raise)
    assert db_engine.clear_alerts() == 0

    monkeypatch.setattr("core.db_engine.async_insert_repair_record", _raise)
    assert db_engine.insert_repair_record(True, "2024-01-01T00:00:00", "2024-01-01T00:00:01", 1.0, "r", "s", "windows", "out") == -1

    monkeypatch.setattr("core.db_engine.async_query_repairs", _raise)
    assert db_engine.query_repairs(limit=5) == []

    monkeypatch.setattr("core.db_engine.async_upsert_pending_approval", _raise)
    assert db_engine.upsert_pending_approval("a", "r", "s", "p", "{}") == -1

    monkeypatch.setattr("core.db_engine.async_get_pending_approval", _raise)
    assert db_engine.get_pending_approval("a") is None

    monkeypatch.setattr("core.db_engine.async_get_all_pending_approvals", _raise)
    assert db_engine.get_all_pending_approvals() == []

    monkeypatch.setattr("core.db_engine.async_update_approval_status", _raise)
    db_engine.update_approval_status("a", "approved")

    monkeypatch.setattr("core.db_engine.async_update_approval_status_by_alert", _raise)
    db_engine.update_approval_status_by_alert("a", "rejected")

    assert db_engine.db_clear_alerts() == 0


# ------------------------------------------------------------------
# core/auto_heal.py
# ------------------------------------------------------------------


@pytest.fixture
def auto_heal_module(monkeypatch, fake_db_session):
    """Import core.auto_heal and patch external deps."""
    import core.auto_heal as auto_heal

    monkeypatch.setattr(auto_heal, "search_similar", lambda *a, **k: [{"payload": {"content": "doc"}}])
    monkeypatch.setattr(auto_heal, "analyze", lambda *a, **k: "runbook text")
    # ensure ApprovalStatus values do not block the wrappers
    monkeypatch.setattr(auto_heal, "upsert_pending_approval", lambda *a, **k: 0)
    monkeypatch.setattr(auto_heal, "update_approval_status", lambda *a, **k: None)
    return auto_heal


def test_auto_heal_helpers(auto_heal_module):
    ah = auto_heal_module
    assert ah._get_resource_key({"resource_id": "r1"}) == "r1"
    assert ah._get_resource_key({}) == "unknown"
    assert not ah._is_pending_approval_error(SimpleNamespace(error="", approval_status="approved"))
    ns = SimpleNamespace(error="approval required", approval_status="pending")
    assert ah._is_pending_approval_error(ns)


def test_auto_heal_maintenance_window(auto_heal_module, monkeypatch):
    ah = auto_heal_module
    monkeypatch.setenv("HEAL_MAINTENANCE_MODE", "true")
    assert ah._is_in_maintenance_window() == (True, "HEAL_MAINTENANCE_MODE enabled")
    monkeypatch.delenv("HEAL_MAINTENANCE_MODE")
    monkeypatch.setenv("HEAL_MAINTENANCE_WINDOW", "not-a-time")
    assert ah._is_in_maintenance_window()[0] is False
    monkeypatch.setenv("HEAL_MAINTENANCE_WINDOW", "00:00-23:59")
    assert ah._is_in_maintenance_window() == (True, "maintenance window 00:00-23:59")
    monkeypatch.delenv("HEAL_MAINTENANCE_WINDOW")


def test_auto_heal_escalation(auto_heal_module, monkeypatch):
    ah = auto_heal_module
    key = "res-1"
    alert = {"resource_id": key}
    monkeypatch.setattr(ah, "_FAILURE_ESCALATION_THRESHOLD", 1)
    ah._record_heal_failure(alert)
    assert ah._should_escalate(alert)[0]
    ah._record_heal_success(alert)
    assert not ah._should_escalate(alert)[0]


def test_auto_heal_resolve_script_key(auto_heal_module):
    ah = auto_heal_module
    assert ah._resolve_script_key("cpu_high", {}) == "cpu_high_script"
    assert ah._resolve_script_key("mem", {}) == "memory_high_script"
    assert ah._resolve_script_key("disk usage", {}) == "disk_high_script"
    assert ah._resolve_script_key("service down", {}) == "service_restart_script"
    assert ah._resolve_script_key("unknown", {"script_key": "memory_high_script"}) == "memory_high_script"


def test_auto_heal_risk_assessment(auto_heal_module, monkeypatch):
    ah = auto_heal_module

    class FakeDT:
        @classmethod
        def now(cls):
            return SimpleNamespace(hour=2)

    monkeypatch.setattr(ah, "datetime", FakeDT)
    engine = ah.RiskAssessmentEngine()
    script = ah.repair_script_library.get_script("cpu_high_script")
    assessment = engine.assess_repair_risk(script, {"environment": "production"})
    assert assessment.approval_required is True
    assert assessment.risk_level == ah.RiskLevel.BLOCKED


def test_auto_heal_cross_platform_executor(auto_heal_module):
    ah = auto_heal_module
    executor = ah.CrossPlatformScriptExecutor()
    assert isinstance(executor.current_platform, ah.PlatformType)
    # memory_high_script does not require approval and should succeed
    result = executor.execute_script("memory_high_script")
    assert result["success"] is True
    assert "Executed script" in result["output"]

    result = executor.execute_script("no_such_script")
    assert result["success"] is False

    executor.current_platform = ah.PlatformType.KUBERNETES
    result = executor.execute_script("memory_high_script")
    assert result["success"] is False
    assert "not compatible" in result["error"]

    assert isinstance(executor.get_available_scripts(), list)


def test_auto_heal_simulate_functions(auto_heal_module):
    ah = auto_heal_module
    result = ah.simulate_repair({"platform": "windows"}, "memory_high_script")
    assert result["success"] is True
    verify = ah.simulate_verify({}, result)
    assert verify["verified"] is True

    fail = ah.simulate_repair({"platform": "windows"}, "cpu_high_script")
    assert fail["success"] is False
    verify2 = ah.simulate_verify({}, fail)
    assert verify2["needs_human"] is True


def test_auto_heal_handle_alert_memory(auto_heal_module, monkeypatch, fake_db_session):
    ah = auto_heal_module
    monkeypatch.setattr("core.db_engine.Alert", _FakeAlert)
    payload = {
        "id": "a1",
        "rule_name": "memory_high",
        "title": "memory high",
        "desc": "mem",
        "platform": "windows",
        "host": "h1",
        "detected_at": "2024-01-01T00:00:00",
    }
    result = ah.handle_alert(payload)
    assert "alert_id" in result
    assert result["runbook"] == ""
    assert ah.trigger_auto_heal(payload)["alert_id"] == result["alert_id"]


def test_auto_heal_handle_alert_cpu(auto_heal_module, monkeypatch, fake_db_session):
    ah = auto_heal_module
    monkeypatch.setattr("core.db_engine.Alert", _FakeAlert)
    monkeypatch.setattr(ah, "upsert_pending_approval", lambda *a, **k: 0)
    payload = {
        "id": "a1",
        "rule_name": "cpu_high",
        "title": "cpu high",
        "desc": "cpu",
        "platform": "windows",
        "host": "h1",
        "detected_at": "2024-01-01T00:00:00",
    }
    result = ah.handle_alert(payload)
    assert result["runbook"]


@pytest.mark.asyncio
async def test_auto_heal_try_auto_heal(auto_heal_module, monkeypatch):
    ah = auto_heal_module
    import core.heal_graph as heal_graph

    state = SimpleNamespace(
        alert={"id": "a1"},
        fix_applied=True,
        verification={"passed": True},
        error=None,
        approval_status="approved",
        runbook="",
    )
    monkeypatch.setattr(heal_graph, "run_heal", AsyncMock(return_value=state))

    alert = {"id": "a1", "resource_id": "r1"}
    result = await ah.try_auto_heal(alert)
    assert result["healed"] is True

    # maintenance window
    monkeypatch.setenv("HEAL_MAINTENANCE_MODE", "true")
    maint = await ah.try_auto_heal(alert)
    assert maint["maintenance"] is True
    monkeypatch.delenv("HEAL_MAINTENANCE_MODE")

    # escalation
    monkeypatch.setattr(ah, "_FAILURE_ESCALATION_THRESHOLD", 1)
    monkeypatch.setattr(ah, "_HEAL_FAILURE_TRACKER", {alert["resource_id"]: {"count": 1}})
    esc = await ah.try_auto_heal(alert)
    assert esc["escalated"] is True


@pytest.mark.asyncio
async def test_auto_heal_approve_reject_and_pending(auto_heal_module, monkeypatch, fake_db_session):
    ah = auto_heal_module
    monkeypatch.setattr(
        ah, "async_update_approval_status_by_alert", AsyncMock(return_value=True)
    )
    monkeypatch.setattr(
        ah, "async_get_all_pending_approvals", AsyncMock(return_value=[])
    )
    import core.approval_store as approval_store

    monkeypatch.setattr(approval_store, "get_pending_only_snapshot", lambda: {})

    assert (await ah.approve_repair("a1", "admin"))["status"] == "approved"
    assert (await ah.reject_repair("a1", reason="no", approver="admin"))["status"] == "rejected"
    assert await ah.get_pending_approvals() == []


@pytest.mark.asyncio
async def test_auto_heal_internal_errors(auto_heal_module, monkeypatch, fake_db_session):
    ah = auto_heal_module
    monkeypatch.setattr("core.db_engine.alert_repository.save", AsyncMock(side_effect=RuntimeError("boom")))
    with pytest.raises(ah.HTTPException):
        await ah._create_alert_record({"id": "x"})

    monkeypatch.setattr(ah, "insert_verify_record", MagicMock(side_effect=RuntimeError("boom")))
    with pytest.raises(ah.HTTPException):
        ah._create_verify_record(x=1)

    monkeypatch.setattr(ah, "upsert_pending_approval", MagicMock(side_effect=RuntimeError("boom")))
    with pytest.raises(ah.HTTPException):
        ah._create_pending_approval("a1", "r", "s", "p")

    monkeypatch.setattr(ah, "update_approval_status", MagicMock(side_effect=RuntimeError("boom")))
    with pytest.raises(ah.HTTPException):
        ah._finalize_approval("a1", "approved")
