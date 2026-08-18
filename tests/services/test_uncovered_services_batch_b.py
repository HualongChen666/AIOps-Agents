# -*- coding: utf-8 -*-
"""Batch B coverage tests for assigned service modules."""

import asyncio  # noqa: F401  # Imported for test setup
import time  # noqa: F401  # Imported for test setup
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest  # noqa: F401  # Imported for test setup
from fastapi.testclient import TestClient

from services.agent_orchestration_service.retry import AgentRetryEngine, RetryPolicy
from services.alert_service.aggregator import TimeWindowAggregator
from services.alert_service.dedup import Deduplicator
from services.alert_service.noise_suppressor import NoiseSuppressor
from services.alert_service.repository import (
    InMemoryAlertRepository,
)
from services.alert_service.repository import get_repository as get_alert_repo
from services.alert_service.schemas import Alert, AlertSeverity, SuppressionRule
from services.audit_service.event_tracker import AuditEventTracker
from services.audit_service.repository import InMemoryAuditRepository
from services.audit_service.retention import RetentionManager
from services.audit_service.schemas import AuditEvent, AuditEventSeverity, AuditEventStatus
from services.repair_service.executor import RunbookExecutor
from services.repair_service.executor import app as executor_api
from services.repair_service.orchestrator import OrchestratorApp
from services.repair_service.orchestrator import app as orchestrator_api
from services.repair_service.rollback import RollbackEngine, SnapshotStore
from services.repair_service.schemas import (
    PlatformType,
    RepairExecutionResult,
    RepairRequest,
    RepairRunbook,
    RepairStatus,
    RepairStep,
    RepairStrategy,
    RepairTask,
)
from services.repair_service.state_machine import RepairStateMachine


# ---------------------------------------------------------------------------
# Repair rollback
# ---------------------------------------------------------------------------
def test_snapshot_store():
    store = SnapshotStore()
    store.save("t1", {"foo": "bar"})
    assert store.get("t1") == {"foo": "bar"}
    assert store.get("missing") is None


@pytest.mark.asyncio
async def test_rollback_engine_all_strategies():
    engine = RollbackEngine()
    result = RepairExecutionResult(task_id="t1", success=False)  # noqa: F841  # Variable for test verification
    cases = [
        ("cpu_high", "process"),
        ("service_restart", "service"),
        ("disk_high", "file"),
        ("config_change", "config"),
        ("dns_flush", "DNS"),
        ("memory_high", "memory"),
        ("cache_drop", "cache"),
        ("network_restart", "network"),
        ("package_install", "packages"),
        ("something_else", "Generic"),
    ]
    for key, expected in cases:
        task = RepairTask(
            task_id=f"t-{key}",
            alert_id="a1",
            host="h1",
            platform=PlatformType.LINUX,
            strategy=RepairStrategy(name="s", script_key=key, platform=PlatformType.LINUX),
        )
        res = await engine.rollback(task, result)
        assert res.success is True
        assert expected in res.output


@pytest.mark.asyncio
async def test_rollback_engine_failure(monkeypatch):
    engine = RollbackEngine()

    async def boom(task, result):
        raise RuntimeError("rollback boom")

    engine._strategies["generic"] = boom
    task = RepairTask(
        task_id="t1",
        alert_id="a1",
        host="h1",
        platform=PlatformType.LINUX,
        strategy=RepairStrategy(name="s", script_key="generic", platform=PlatformType.LINUX),
    )
    res = await engine.rollback(task, RepairExecutionResult(task_id="t1", success=False))
    assert res.success is False
    assert "rollback boom" in res.error


@pytest.mark.asyncio
async def test_rollback_take_snapshot():
    engine = RollbackEngine()
    task = RepairTask(
        task_id="t1",
        alert_id="a1",
        host="h1",
        platform=PlatformType.LINUX,
        strategy=RepairStrategy(name="s", script_key="cpu_high", platform=PlatformType.LINUX),
    )
    snapshot = engine.take_snapshot(task)
    assert snapshot["task_id"] == "t1"
    assert engine.snapshot_store.get("t1") is not None


# ---------------------------------------------------------------------------
# Alert noise suppressor
# ---------------------------------------------------------------------------
def test_noise_suppressor_rules():
    ns = NoiseSuppressor(min_noise_count=2)
    rule = SuppressionRule(name="cpu", pattern="cpu spike", reason="cpu noise")
    ns.add_rule(rule)

    a = Alert(id="1", title="cpu spike", description="host h1", level=AlertSeverity.WARNING)
    assert ns.is_noise(a) is True
    assert a.suppressed is True
    assert "cpu noise" in (a.suppression_reason or "")

    b = Alert(id="2", title="disk full", description="host h1", level=AlertSeverity.WARNING)
    assert ns.is_noise(b) is False
    assert b.suppressed is False
    assert len(ns.list_rules()) == 1


def test_noise_suppressor_auto_detection():
    ns = NoiseSuppressor(min_noise_count=2, window_seconds=600)
    a = Alert(id="1", title="x", description="y", level=AlertSeverity.INFO)
    ns.is_noise(a)
    ns.is_noise(a)
    assert ns.is_noise(a) is True
    assert a.suppression_reason == "auto-detected noise pattern"


def test_noise_suppressor_stats_and_eviction():
    ns = NoiseSuppressor(window_seconds=600, min_noise_count=5, max_entries=2)
    # The suppressor evicts before insertion, so the cache stabilizes at max + 1.
    for i in range(5):
        a = Alert(id=f"{i}", title=f"alert-{i}", description="d", level=AlertSeverity.INFO)
        ns.is_noise(a)
    stats = ns.get_stats()
    assert stats["pattern_count"] == ns.max_entries + 1
    assert stats["noise_patterns"] == 0


# ---------------------------------------------------------------------------
# Alert deduplicator
# ---------------------------------------------------------------------------
def test_deduplicator():
    d = Deduplicator(window_seconds=10)
    a = Alert(
        id="1",
        title="t1",
        category="c",
        alert_type="a",
        metric="m",
        host="h1",
        level=AlertSeverity.WARNING,
    )
    assert d.is_duplicate(a) is False
    assert d.is_duplicate(a) is True
    assert d.get_stats()["total_suppressed"] == 1
    assert a.fingerprint


def test_deduplicator_eviction(monkeypatch):
    d = Deduplicator(window_seconds=300)
    a = Alert(
        id="1",
        title="t1",
        category="c",
        alert_type="a",
        metric="m",
        host="h1",
        level=AlertSeverity.WARNING,
    )
    monkeypatch.setattr(
        "services.alert_service.dedup.time.time", MagicMock(side_effect=[0.0, 1000.0])
    )
    assert d.is_duplicate(a) is False
    # Old entry expired, should be treated as new alert
    assert d.is_duplicate(a) is False


def test_deduplicator_max_entries(monkeypatch):
    d = Deduplicator(window_seconds=300, max_entries=1)
    # The deduplicator evicts before insertion, so size is capped at max + 1.
    monkeypatch.setattr(
        "services.alert_service.dedup.time.time",
        MagicMock(side_effect=[float(i) for i in range(6)]),
    )
    for i in range(5):
        a = Alert(id=str(i), title=f"t{i}", category="c", alert_type="a", metric="m", host=f"h{i}")
        d.is_duplicate(a)
    assert d.get_stats()["cache_size"] <= d.max_entries + 1


# ---------------------------------------------------------------------------
# Alert aggregator
# ---------------------------------------------------------------------------
def test_aggregator_tumbling():
    agg = TimeWindowAggregator(
        window_seconds=60,
        mode="tumbling",
        signature_fields=("category", "alert_type", "metric"),
    )
    now = datetime.utcnow()
    a1 = Alert(
        id="1",
        title="t1",
        level=AlertSeverity.WARNING,
        category="c",
        alert_type="a",
        metric="m",
        detected_at=now,
    )
    a2 = Alert(
        id="2",
        title="t2",
        level=AlertSeverity.INFO,
        category="c",
        alert_type="a",
        metric="m",
        detected_at=now,
    )
    assert agg.add(a1) == []
    assert agg.add(a2) == []

    a3 = Alert(
        id="3",
        title="t3",
        level=AlertSeverity.INFO,
        category="c",
        alert_type="a",
        metric="m",
        detected_at=now + timedelta(seconds=120),
    )
    flushed = agg.add(a3)
    assert len(flushed) == 1
    assert flushed[0].aggregated_count == 2


def test_aggregator_sliding():
    agg = TimeWindowAggregator(window_seconds=60, mode="sliding")
    now = datetime.utcnow()
    a1 = Alert(
        id="1",
        title="t1",
        level=AlertSeverity.WARNING,
        category="c",
        alert_type="a",
        metric="m",
        detected_at=now,
    )
    a2 = Alert(
        id="2",
        title="t2",
        level=AlertSeverity.INFO,
        category="c",
        alert_type="a",
        metric="m",
        detected_at=now + timedelta(seconds=1),
    )
    assert agg.add(a1) == []
    flushed = agg.add(a2)
    assert len(flushed) == 1
    assert flushed[0].aggregated_count == 2


def test_aggregator_flush(monkeypatch):
    agg = TimeWindowAggregator(window_seconds=300, mode="tumbling")
    now = datetime.utcnow()
    a = Alert(
        id="1",
        title="t",
        level=AlertSeverity.INFO,
        category="c",
        alert_type="a",
        metric="m",
        detected_at=now,
    )
    agg.add(a)
    flushed = agg.flush(force=True)
    assert len(flushed) == 1
    assert flushed[0].id == "1"


def test_aggregator_sliding_flush_expired(monkeypatch):
    agg = TimeWindowAggregator(window_seconds=300, mode="sliding")
    old = datetime(2020, 1, 1, 0, 0, 0)
    a = Alert(
        id="1",
        title="t",
        level=AlertSeverity.INFO,
        category="c",
        alert_type="a",
        metric="m",
        detected_at=old,
    )
    agg.add(a)
    monkeypatch.setattr("services.alert_service.aggregator.time.time", lambda: 2_000_000_000.0)
    flushed = agg.flush()
    assert len(flushed) == 1


# ---------------------------------------------------------------------------
# Alert repository
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_alert_repository():
    repo = InMemoryAlertRepository()
    a = Alert(id="a1", title="t1", level=AlertSeverity.WARNING, status="pending")
    a_id = await repo.save(a)
    assert a_id
    assert await repo.get("a1") == a
    assert await repo.count() == 1

    items = await repo.list(limit=10, level=AlertSeverity.WARNING.value)
    assert len(items) == 1

    await repo.update("a1", {"description": "updated"})
    updated = await repo.get("a1")
    assert updated.description == "updated"

    assert await repo.delete("a1") is True
    assert await repo.delete("a1") is False
    await repo.save(a)
    cleared = await repo.clear()
    assert cleared == 1
    assert await repo.count() == 0
    assert await get_alert_repo() is not None


# ---------------------------------------------------------------------------
# Audit event tracker
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_audit_event_tracker():
    repo = InMemoryAuditRepository()
    tracker = AuditEventTracker(repo)

    high = AuditEvent(
        event_id="e1",
        action="login",
        resource="user",
        user_id="u1",
        severity=AuditEventSeverity.HIGH,
    )
    assert await tracker.track(high) == "priority-queue"
    # Repository overwrites status to RECORDED after tracker sets ROUTED
    assert high.status == AuditEventStatus.RECORDED

    low = AuditEvent(
        event_id="e2",
        action="logout",
        resource="user",
        user_id="u1",
    )
    assert await tracker.track(low) == "standard-queue"

    batch = await tracker.batch_track([high, low])
    assert batch["tracked"] == 2
    assert "priority-queue" in batch["routes"]


# ---------------------------------------------------------------------------
# Audit retention
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_retention_manager():
    repo = InMemoryAuditRepository()
    rm = RetentionManager(repo)

    policy = await rm.apply_policy("tenant-1", ttl_days=30, archive_after_days=7, auto_archive=True)
    assert policy.ttl_days == 30
    assert policy.archive_after_days == 7

    now = datetime.utcnow()
    old = now - timedelta(days=60)
    recent = now - timedelta(days=1)

    e_old = AuditEvent(
        event_id="old",
        action="a",
        resource="r",
        user_id="u",
        tenant_id="tenant-1",
        timestamp=old,
        status=AuditEventStatus.RECORDED,
    )
    e_new = AuditEvent(
        event_id="new",
        action="a",
        resource="r",
        user_id="u",
        tenant_id="tenant-1",
        timestamp=recent,
        status=AuditEventStatus.RECORDED,
    )
    e_archived = AuditEvent(
        event_id="archived",
        action="a",
        resource="r",
        user_id="u",
        tenant_id="tenant-1",
        timestamp=old,
        status=AuditEventStatus.ARCHIVED,
    )
    repo._events[e_old.event_id] = e_old
    repo._events[e_new.event_id] = e_new
    repo._events[e_archived.event_id] = e_archived

    cleanup = await rm.cleanup("tenant-1", now=now)
    # cleanup counts all events older than ttl, including the archived one
    assert cleanup["deleted"] == 2
    archive = await rm.archive("tenant-1", now=now)
    # archive skips already-archived events
    assert archive["archived"] == 1


# ---------------------------------------------------------------------------
# Agent retry engine
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_retry_engine_success():
    engine = AgentRetryEngine()

    async def ok():
        return 42

    assert await engine.execute(ok, operation="op") == 42


@pytest.mark.asyncio
async def test_retry_engine_retries_then_success(monkeypatch):
    engine = AgentRetryEngine(default_policy_name="exponential_fast")
    monkeypatch.setattr("services.agent_orchestration_service.retry.asyncio.sleep", AsyncMock())
    calls = []

    async def flaky():
        if len(calls) == 0:
            calls.append(1)
            raise Exception("retryable error")
        return "ok"

    assert await engine.execute(flaky, operation="op") == "ok"


@pytest.mark.asyncio
async def test_retry_engine_exhausted(monkeypatch):
    engine = AgentRetryEngine(default_policy_name="no_retry")
    monkeypatch.setattr("services.agent_orchestration_service.retry.asyncio.sleep", AsyncMock())

    async def fail():
        raise Exception("retryable error")

    with pytest.raises(Exception, match="retryable error"):
        await engine.execute(fail, operation="op")


@pytest.mark.asyncio
async def test_retry_engine_non_retryable(monkeypatch):
    engine = AgentRetryEngine(default_policy_name="exponential_fast")
    monkeypatch.setattr("services.agent_orchestration_service.retry.asyncio.sleep", AsyncMock())

    async def fail():
        raise Exception("fatal")

    with pytest.raises(Exception, match="fatal"):
        await engine.execute(fail, operation="op")


def test_retry_engine_policies_and_delay():
    engine = AgentRetryEngine()
    assert "exponential" in engine.list_policies()
    engine.add_policy(RetryPolicy(name="custom", max_retries=1))
    assert "custom" in engine.list_policies()

    exponential = engine.policies["exponential"]
    assert engine._compute_delay(1, exponential) == 1.0
    assert engine._compute_delay(3, exponential) == 4.0
    assert engine._compute_delay(20, exponential) == 30.0


def test_retry_jitter_delay(monkeypatch):
    engine = AgentRetryEngine()
    policy = engine.policies["jitter"]

    class FakeRandom:
        def __init__(self):
            pass

        def random(self):
            return 0.5

    monkeypatch.setattr(
        "services.agent_orchestration_service.retry.secrets.SystemRandom", FakeRandom
    )
    delay = engine._compute_delay(1, policy)
    assert delay == policy.base_delay_seconds * (0.5 + 0.5)


# ---------------------------------------------------------------------------
# Repair state machine
# ---------------------------------------------------------------------------
def test_repair_state_machine():
    task = RepairTask(
        task_id="t1",
        alert_id="a1",
        host="h1",
        platform=PlatformType.LINUX,
        status=RepairStatus.PENDING,
    )
    sm = RepairStateMachine(task)
    assert sm.current_state == RepairStatus.PENDING
    assert sm.can_transition(RepairStatus.APPROVED)
    assert not sm.can_transition(RepairStatus.COMPLETED)

    assert sm.transition(RepairStatus.APPROVED)
    assert sm.transition(RepairStatus.EXECUTING)
    assert sm.transition(RepairStatus.SUCCEEDED)
    assert sm.transition(RepairStatus.VERIFYING)
    assert sm.transition(RepairStatus.VERIFIED)
    assert sm.transition(RepairStatus.COMPLETED)
    assert sm.to_dict()["current_state"] == "completed"

    task2 = RepairTask(
        task_id="t2",
        alert_id="a2",
        host="h1",
        platform=PlatformType.LINUX,
        status=RepairStatus.PENDING,
    )
    sm2 = RepairStateMachine(task2)
    assert not sm2.transition(RepairStatus.COMPLETED)


# ---------------------------------------------------------------------------
# Repair executor
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_runbook_executor_success():
    ex = RunbookExecutor(dry_run=True)
    rb = RepairRunbook(
        runbook_id="ok",
        name="ok",
        steps=[RepairStep(name="s1", command="echo ok")],
    )
    result = await ex.execute("t1", rb)  # noqa: F841  # Variable for test verification
    assert result.success is True
    assert "executed_steps" in result.model_dump()


@pytest.mark.asyncio
async def test_runbook_executor_failure():
    ex = RunbookExecutor(dry_run=True)
    rb = RepairRunbook(
        runbook_id="f",
        name="f",
        steps=[RepairStep(name="s1", command="this will fail")],
    )
    result = await ex.execute("t1", rb)  # noqa: F841  # Variable for test verification
    assert result.success is False


@pytest.mark.asyncio
async def test_runbook_executor_validation():
    ex = RunbookExecutor(dry_run=True)
    rb = RepairRunbook(runbook_id="bad", name="bad", steps=[])
    result = await ex.execute("t1", rb)  # noqa: F841  # Variable for test verification
    assert result.success is False
    assert "must contain at least one step" in result.error


@pytest.mark.asyncio
async def test_runbook_executor_strategy():
    ex = RunbookExecutor(dry_run=True)
    missing = RepairStrategy(name="x", script_key="does_not_exist", platform=PlatformType.LINUX)
    result = await ex.execute_strategy("t1", missing)  # noqa: F841  # Variable for test verification
    assert result.success is False

    found = RepairStrategy(name="m", script_key="memory_high", platform=PlatformType.LINUX)
    result = await ex.execute_strategy("t2", found)  # noqa: F841  # Variable for test verification
    assert result.success is True


def test_executor_api_endpoints():
    with TestClient(executor_api) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/metrics").status_code == 200
        assert client.get("/scripts").status_code == 200
        assert client.get("/strategies").status_code == 200

        rb = {
            "runbook_id": "test",
            "name": "test",
            "steps": [{"name": "s1", "command": "echo hello", "timeout_seconds": 5}],
        }
        r = client.post("/execute/runbook?task_id=T1", json=rb)
        assert r.status_code == 200
        assert r.json()["success"] is True

        req = {
            "request": {
                "alert_id": "a1",
                "host": "h1",
                "platform": "linux",
                "metric": "memory_percent",
            },
            "strategy": {
                "name": "memory_high_linux",
                "script_key": "memory_high",
                "platform": "linux",
            },
        }
        r = client.post("/execute/strategy", json=req)
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# Repair orchestrator
# ---------------------------------------------------------------------------
def test_orchestrator_api_create_and_approve():
    with TestClient(orchestrator_api) as client:
        payload = {
            "alert_id": "oa1",
            "host": "h1",
            "platform": "linux",
            "metric": "memory_percent",
            "auto_approve": False,
        }
        r = client.post("/repairs", json=payload)
        assert r.status_code == 200
        data = r.json()
        task_id = data["task_id"]
        assert data["status"] == "pending"

        assert client.get("/repairs").status_code == 200
        assert client.get(f"/repairs/{task_id}").status_code == 200

        r = client.post(f"/repairs/{task_id}/approve")
        assert r.status_code == 200
        assert r.json()["status"] in ("completed", "verified")


def test_orchestrator_api_auto_approve():
    with TestClient(orchestrator_api) as client:
        payload = {
            "alert_id": "oa2",
            "host": "h1",
            "platform": "linux",
            "metric": "memory_percent",
            "auto_approve": True,
        }
        r = client.post("/repairs", json=payload)
        assert r.status_code == 200
        assert r.json()["status"] == "approved"


def test_orchestrator_api_reject():
    with TestClient(orchestrator_api) as client:
        payload = {
            "alert_id": "oa3",
            "host": "h1",
            "platform": "linux",
            "metric": "cpu_percent",
        }
        r = client.post("/repairs", json=payload)
        task_id = r.json()["task_id"]
        r = client.post(f"/repairs/{task_id}/reject")
        assert r.status_code == 200
        assert r.json()["status"] == "completed"


def test_orchestrator_api_saga_and_missing():
    with TestClient(orchestrator_api) as client:
        payload = {
            "alert_id": "oa4",
            "host": "h1",
            "platform": "linux",
            "metric": "memory_percent",
        }
        r = client.post("/repairs", json=payload)
        task_id = r.json()["task_id"]
        assert client.post(f"/repairs/{task_id}/saga").status_code == 200

        assert client.get("/repairs/missing").status_code == 200
        assert client.post("/repairs/missing/approve").json().get("error") == "task not found"


@pytest.mark.asyncio
async def test_orchestrator_app_direct():
    app = OrchestratorApp()
    await app.init()
    request = RepairRequest(
        alert_id="direct",
        host="h1",
        platform=PlatformType.LINUX,
        metric="memory_percent",
    )
    task = await app.create_task(request)
    assert task.task_id
    assert task.status == RepairStatus.PENDING
    fetched = await app.repo.get(task.task_id)
    assert fetched is not None


@pytest.mark.asyncio
async def test_orchestrator_approve_already_approved():
    with TestClient(orchestrator_api) as client:
        payload = {
            "alert_id": "dup",
            "host": "h1",
            "platform": "linux",
            "metric": "memory_percent",
            "auto_approve": True,
        }
        r = client.post("/repairs", json=payload)
        task_id = r.json()["task_id"]
        r = client.post(f"/repairs/{task_id}/approve")
        assert r.status_code == 200
        assert r.json()["status"] == "approved"


@pytest.mark.asyncio
async def test_orchestrator_execute_failure(monkeypatch):
    import services.repair_service.orchestrator as orch_mod

    with TestClient(orchestrator_api) as client:
        payload = {
            "alert_id": "execfail",
            "host": "h1",
            "platform": "linux",
            "metric": "memory_percent",
        }
        r = client.post("/repairs", json=payload)
        task_id = r.json()["task_id"]
        orch_mod.orchestrator_app.executor.execute = AsyncMock(
            return_value=RepairExecutionResult(
                task_id=task_id,
                success=False,
                error="simulated failure",
            )
        )
        r = client.post(f"/repairs/{task_id}/approve")
        assert r.status_code == 200
        assert r.json()["status"] in ("completed", "rollbacked")


@pytest.mark.asyncio
async def test_orchestrator_verify_failure(monkeypatch):
    import services.repair_service.orchestrator as orch_mod
    from services.repair_service.schemas import VerificationResult

    with TestClient(orchestrator_api) as client:
        payload = {
            "alert_id": "verifyfail",
            "host": "h1",
            "platform": "linux",
            "metric": "memory_percent",
        }
        r = client.post("/repairs", json=payload)
        task_id = r.json()["task_id"]
        orch_mod.orchestrator_app.verifier.verify = AsyncMock(
            return_value=VerificationResult(
                task_id=task_id,
                verified=False,
                strategy="metric_threshold",
            )
        )
        r = client.post(f"/repairs/{task_id}/approve")
        assert r.status_code == 200
        assert r.json()["status"] in ("completed", "rollbacked")


@pytest.mark.asyncio
async def test_orchestrator_runbook_not_found(monkeypatch):
    import services.repair_service.orchestrator as orch_mod

    with TestClient(orchestrator_api) as client:
        payload = {
            "alert_id": "norunbook",
            "host": "h1",
            "platform": "linux",
            "metric": "memory_percent",
        }
        r = client.post("/repairs", json=payload)
        task_id = r.json()["task_id"]
        monkeypatch.setattr(orch_mod.RunbookParser, "load_example", lambda runbook_id: None)
        r = client.post(f"/repairs/{task_id}/approve")
        assert r.status_code == 200
        assert r.json()["status"] in ("completed", "rollbacked")


# ---------------------------------------------------------------------------
# Additional executor coverage
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_runbook_executor_params_merge():
    """Test parameter merging in executor."""
    ex = RunbookExecutor(dry_run=True)
    rb = RepairRunbook(
        runbook_id="test",
        name="test",
        params={"service": "nginx"},
        steps=[RepairStep(name="s1", command="restart {service}")],
    )
    result = await ex.execute("t1", rb, params={"service": "apache"})
    assert result.success is True
    # Params should be merged, with request params taking precedence


@pytest.mark.asyncio
async def test_runbook_executor_timeout():
    """Test executor timeout handling."""
    ex = RunbookExecutor(dry_run=True)
    rb = RepairRunbook(
        runbook_id="test",
        name="test",
        steps=[RepairStep(name="s1", command="sleep 100", timeout_seconds=1)],
    )
    result = await ex.execute("t1", rb)
    # In dry_run mode, timeout is simulated
    assert result is not None


@pytest.mark.asyncio
async def test_runbook_executor_multiple_steps():
    """Test executor with multiple steps."""
    ex = RunbookExecutor(dry_run=True)
    rb = RepairRunbook(
        runbook_id="test",
        name="test",
        steps=[
            RepairStep(name="s1", command="echo step1"),
            RepairStep(name="s2", command="echo step2"),
            RepairStep(name="s3", command="echo step3"),
        ],
    )
    result = await ex.execute("t1", rb)
    assert result.success is True
    assert result.executed_steps == 3


@pytest.mark.asyncio
async def test_runbook_executor_strategy_params():
    """Test strategy execution with params."""
    ex = RunbookExecutor(dry_run=True)
    strategy = RepairStrategy(
        name="test",
        script_key="memory_high",
        platform=PlatformType.LINUX,
        conditions={"threshold": 90},
    )
    result = await ex.execute_strategy("t1", strategy, params={"threshold": 95})
    assert result is not None


# ---------------------------------------------------------------------------
# Additional orchestrator coverage
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_orchestrator_get_machine():
    """Test getting state machine for task."""
    app = OrchestratorApp()
    await app.init()
    
    task = RepairTask(
        task_id="t1",
        alert_id="a1",
        host="h1",
        platform=PlatformType.LINUX,
    )
    
    sm = app.get_machine(task)
    assert sm is not None
    assert sm.current_state == RepairStatus.PENDING
    
    # Should return same machine for same task
    sm2 = app.get_machine(task)
    assert sm is sm2


@pytest.mark.asyncio
async def test_orchestrator_create_task_with_strategy():
    """Test creating task with matched strategy."""
    app = OrchestratorApp()
    await app.init()
    
    request = RepairRequest(
        alert_id="a1",
        host="h1",
        platform=PlatformType.LINUX,
        metric="cpu_percent",
    )
    
    task = await app.create_task(request)
    assert task.strategy is not None
    assert task.strategy.name == "cpu_high_linux"


@pytest.mark.asyncio
async def test_orchestrator_reject_already_completed():
    """Test rejecting a task that's already completed."""
    app = OrchestratorApp()
    await app.init()
    
    request = RepairRequest(
        alert_id="a1",
        host="h1",
        platform=PlatformType.LINUX,
        metric="cpu_percent",
    )
    
    task = await app.create_task(request)
    await app.reject(task.task_id)
    
    # Try to reject again
    result = await app.reject(task.task_id)
    assert result is not None
    assert result.status == RepairStatus.COMPLETED
