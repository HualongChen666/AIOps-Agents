# -*- coding: utf-8 -*-
"""Targeted coverage tests for Batch A uncovered service modules."""

from __future__ import annotations

import asyncio  # noqa: F401  # Imported for test setup
import sys  # noqa: F401  # Imported for test setup
import time  # noqa: F401  # Imported for test setup
import types
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest  # noqa: F401  # Imported for test setup

import services.agent_orchestration_service.cache as agent_cache_module
import services.agent_orchestration_service.orchestrator as orchestrator_module
import services.alert_service.processor_core as processor_core_module
import services.alert_service.router as alert_router_module
import services.audit_service.alerting as alerting_module
import services.repair_service.health_check as health_check_module
from services.agent_orchestration_service.cache import CacheManager
from services.agent_orchestration_service.orchestrator import AgentOrchestrator, LangGraphAdapter
from services.agent_orchestration_service.schemas import (
    AgentRequest,
    AgentResult,
    AgentType,
    AggregateRequest,
    CollaborateRequest,
    CoordinateRequest,
    DecomposeRequest,
    ErrorHandleRequest,
    SubTask,
)
from services.alert_service.classifier import Classifier
from services.alert_service.mq import InMemoryMessageQueue
from services.alert_service.processor_core import AlertPipeline
from services.alert_service.repository import InMemoryAlertRepository
from services.alert_service.router import Router
from services.alert_service.saga import (
    SagaContext,
)
from services.alert_service.saga import SagaOrchestrator as AlertSagaOrchestrator
from services.alert_service.saga import (
    SagaStep,
)
from services.alert_service.schemas import (
    Alert,
    AlertSeverity,
    AlertStatus,
    ClassificationRule,
    RoutingRule,
)
from services.audit_service.alerting import AlertingEngine
from services.audit_service.event_router import AuditEventRouter
from services.audit_service.repository import InMemoryAuditRepository
from services.audit_service.saga import SagaOrchestrator as AuditSagaOrchestrator
from services.audit_service.schemas import (
    AlertRule,
    AuditEvent,
    AuditEventSeverity,
)
from services.audit_service.schemas import SagaStep as AuditSagaStep
from services.audit_service.schemas import SagaTransaction as AuditSagaTransaction
from services.repair_service.health_check import HealthCheckEngine
from services.repair_service.saga import SagaOrchestrator as RepairSagaOrchestrator
from services.repair_service.schemas import SagaStep as RepairSagaStep
from services.repair_service.schemas import SagaTransaction as RepairSagaTransaction


def _run(coro):
    return asyncio.run(coro)


# ------------------------------------------------------------------
# audit_service/alerting.py
# ------------------------------------------------------------------


def test_alerting_engine_evaluates_default_rules():
    repo = InMemoryAuditRepository()
    engine = AlertingEngine(repo)
    event = AuditEvent(
        event_id="e1",
        action="unauthorized_access",
        resource="r1",
        user_id="u1",
        severity=AuditEventSeverity.HIGH,
    )
    matched = _run(engine.evaluate(event))
    assert any(r.rule_id == "r3" for r in matched)


def test_alerting_engine_adds_and_uses_custom_rule():
    repo = InMemoryAuditRepository()
    engine = AlertingEngine(repo)
    rule = AlertRule(
        rule_id="custom",
        name="custom",
        condition="severity == 'critical' and action == 'admin_delete'",
        severity=AuditEventSeverity.CRITICAL,
        action="block",
    )
    _run(engine.add_rule(rule))
    event = AuditEvent(
        event_id="e2",
        action="admin_delete",
        resource="r2",
        user_id="u2",
        severity=AuditEventSeverity.CRITICAL,
    )
    matched = _run(engine.evaluate(event))
    assert any(r.rule_id == "custom" for r in matched)


def test_alerting_engine_handles_disabled_rule_and_bad_condition():
    repo = InMemoryAuditRepository()
    engine = AlertingEngine(repo)
    engine.rules["r1"].enabled = False
    event = AuditEvent(
        event_id="e3",
        action="delete",
        resource="r3",
        user_id="u3",
        severity=AuditEventSeverity.CRITICAL,
    )
    matched = _run(engine.evaluate(event))
    assert not any(r.rule_id == "r1" for r in matched)

    engine.rules["r2"].condition = "severity + 1"
    matched = _run(engine.evaluate(event))
    assert all(r.rule_id != "r2" for r in matched)


# ------------------------------------------------------------------
# audit_service/saga.py
# ------------------------------------------------------------------


def test_audit_saga_success_and_compensation():
    repo = InMemoryAuditRepository()
    saga = AuditSagaOrchestrator(repo)
    step = AuditSagaStep(
        step_id="s1",
        service="audit",
        action="save",
        compensation="undo_save",
    )
    transaction = AuditSagaTransaction(saga_id="sg1", task_id="t1", steps=[step])

    async def action_handler(st):
        st.result = {"ok": True}  # noqa: F841  # Variable for test verification
        return {"ok": True}

    async def comp_handler(st):
        st.result = {"compensated": True}  # noqa: F841  # Variable for test verification
        return {"compensated": True}

    saga.register("save", action_handler, comp_handler)
    result = _run(saga.execute(transaction))  # noqa: F841  # Variable for test verification
    assert result.status == "success"
    assert result.steps[0].status == "success"

    # failure triggers compensation
    step2 = AuditSagaStep(
        step_id="s2",
        service="audit",
        action="fail",
        compensation="undo_fail",
    )
    transaction2 = AuditSagaTransaction(saga_id="sg2", task_id="t1", steps=[step, step2])

    async def fail_handler(st):
        raise ValueError("boom")

    saga.register("fail", fail_handler, comp_handler)
    with pytest.raises(ValueError):
        _run(saga.execute(transaction2))
    assert transaction2.status == "compensating"
    assert transaction2.steps[0].status == "compensated"


# ------------------------------------------------------------------
# audit_service/event_router.py
# ------------------------------------------------------------------


def test_audit_event_router():
    router = AuditEventRouter()
    high = AuditEvent(
        event_id="eh1",
        action="write",
        resource="r",
        user_id="u",
        severity=AuditEventSeverity.HIGH,
    )
    read = AuditEvent(
        event_id="er1",
        action="read_report",
        resource="r",
        user_id="u",
        severity=AuditEventSeverity.LOW,
    )
    std = AuditEvent(
        event_id="es1",
        action="create",
        resource="r",
        user_id="u",
        severity=AuditEventSeverity.LOW,
    )
    assert _run(router.route(high)) == "priority"
    assert _run(router.route(read)) == "analytics"
    assert _run(router.route(std)) == "standard"
    result = _run(
        router.batch_route([high, read, std, std])
    )  # noqa: F841  # Variable for test verification
    assert result["priority"] == 1
    assert result["analytics"] == 1
    assert result["standard"] == 2


# ------------------------------------------------------------------
# alert_service/router.py
# ------------------------------------------------------------------


def test_alert_router_rules_and_default_routing(monkeypatch):
    router = Router()
    router.add_rule(
        RoutingRule(
            name="db_rule",
            conditions={"category": "database"},
            destination="pagerduty-db",
            priority=10,
        )
    )
    assert len(router.list_rules()) == 1

    db_alert = Alert(id="a1", title="db", category="database", level=AlertSeverity.WARNING)
    assert router.route(db_alert) == "pagerduty-db"

    sec_alert = Alert(
        id="a2",
        title="sec",
        category="security",
        level=AlertSeverity.CRITICAL,
        alert_type="api",
    )
    assert router.route(sec_alert) == "team:security"

    infra_alert = Alert(
        id="a3",
        title="net",
        category="network",
        level=AlertSeverity.CRITICAL,
        alert_type="api",
    )
    assert router.route(infra_alert) == "team:infrastructure"

    default_alert = Alert(
        id="a4",
        title="ok",
        category="other",
        level=AlertSeverity.WARNING,
        alert_type="api",
    )
    assert router.route(default_alert) == "default"

    # on-call adapter path
    class FakeAdapter:
        def lookup(self, **kwargs):
            return [types.SimpleNamespace(team="sre")]

    monkeypatch.setattr(alert_router_module, "get_oncall_adapter", lambda: FakeAdapter())
    oncall_alert = Alert(
        id="a5",
        title="oncall",
        category="unknown",
        level=AlertSeverity.HIGH,
        alert_type="api",
    )
    assert router.route(oncall_alert) == "oncall:sre"


# ------------------------------------------------------------------
# alert_service/classifier.py
# ------------------------------------------------------------------


def test_classifier_rules_and_fallback():
    c = Classifier()
    c.add_rule(
        ClassificationRule(
            name="db_rule",
            conditions={"category": "database"},
            category="database",
            priority="P1",
        )
    )
    assert len(c.list_rules()) == 1

    rule_alert = Alert(
        id="c1",
        title="db down",
        category="database",
        level=AlertSeverity.CRITICAL,
    )
    result = c.classify(rule_alert)  # noqa: F841  # Variable for test verification
    assert result.category == "database"
    assert result.priority == "P1"
    assert result.tags.get("classification_rule") == "db_rule"

    ssh_alert = Alert(
        id="c2",
        title="ssh brute force attack",
        description="unauthorized access",
        level=AlertSeverity.CRITICAL,
    )
    result = c.classify(ssh_alert)  # noqa: F841  # Variable for test verification
    assert result.category == "security"
    assert result.priority == "P0"
    assert result.tags.get("priority_override") == "critical_business_impact"

    perf_alert = Alert(
        id="c3",
        title="cpu high load",
        description="memory pressure",
        level=AlertSeverity.WARNING,
    )
    result = c.classify(perf_alert)  # noqa: F841  # Variable for test verification
    assert result.category == "performance"

    disabled_rule = ClassificationRule(
        name="disabled",
        conditions={"title": "nomatch"},
        category="x",
        priority="P0",
        enabled=False,
    )
    c.add_rule(disabled_rule)
    other = Alert(id="c4", title="something else", level=AlertSeverity.WARNING)
    result = c.classify(other)  # noqa: F841  # Variable for test verification
    assert result.category == "system"


# ------------------------------------------------------------------
# alert_service/saga.py
# ------------------------------------------------------------------


def test_alert_saga_success_and_compensation():
    async def action(ctx):
        ctx.data["step1"] = True
        return "ok"

    async def fail(ctx):
        raise RuntimeError("step failed")

    async def comp(ctx):
        ctx.data["comp1"] = True
        return "compensated"

    saga = AlertSagaOrchestrator()
    completed = _run(
        saga.execute([SagaStep(name="a", action=action), SagaStep(name="b", action=action)])
    )
    assert completed["status"] == "completed"
    assert completed["executed"] == ["a", "b"]

    failed = _run(
        saga.execute(
            [SagaStep(name="a", action=action, compensation=comp), SagaStep(name="b", action=fail)]
        )
    )
    assert failed["status"] == "failed"
    assert "a" in failed["compensated"]


# ------------------------------------------------------------------
# alert_service/processor_core.py
# ------------------------------------------------------------------


def _make_pipeline(monkeypatch, max_retries=1):
    # prevent real dead-letter file I/O and heavy auto-heal work
    monkeypatch.setattr(processor_core_module, "_append_dead_letter", lambda payload: None)
    monkeypatch.setitem(
        sys.modules,
        "core.auto_heal",
        types.SimpleNamespace(try_auto_heal=AsyncMock(return_value={"status": "healed"})),
    )
    repo = InMemoryAlertRepository()
    mq = InMemoryMessageQueue()
    pipeline = AlertPipeline(repository=repo, mq=mq, max_retries=max_retries)
    return pipeline


def test_alert_pipeline_process_and_flush(monkeypatch):
    pipeline = _make_pipeline(monkeypatch)
    alert = Alert(
        id="p1",
        title="ssh brute force",
        description="unauthorized access attempt",
        level=AlertSeverity.CRITICAL,
        status=AlertStatus.PENDING,
        category="security",
    )
    result = _run(pipeline.process_and_flush(alert))  # noqa: F841  # Variable for test verification
    assert result["status"] == "buffered"
    assert result["alert_id"] == "p1"
    assert len(result["flushed"]) == 1


def test_alert_pipeline_suppressed_and_duplicate(monkeypatch):
    pipeline = _make_pipeline(monkeypatch)
    pipeline.noise_suppressor.is_noise = lambda alert: True
    a1 = Alert(id="p2", title="noise", level=AlertSeverity.WARNING)
    result = _run(pipeline.process_alert(a1))  # noqa: F841  # Variable for test verification
    assert result["status"] == "suppressed"

    pipeline2 = _make_pipeline(monkeypatch)
    pipeline2.deduplicator.is_duplicate = lambda alert: True
    a2 = Alert(id="p3", title="dup", level=AlertSeverity.WARNING)
    result = _run(pipeline2.process_alert(a2))  # noqa: F841  # Variable for test verification
    assert result["status"] == "duplicate"


def test_alert_pipeline_resolved_and_stats(monkeypatch):
    pipeline = _make_pipeline(monkeypatch)
    resolved = Alert(
        id="p4",
        title="resolved",
        level=AlertSeverity.WARNING,
        status=AlertStatus.RESOLVED,
        fingerprint="fp1",
    )
    _run(pipeline._handle_resolved(resolved))
    assert _run(pipeline._is_resolved("fp1")) is True
    assert pipeline.uptime_seconds() >= 0
    stats = pipeline.get_stats()
    assert "dedup" in stats
    assert "queue_sizes" in stats


def test_alert_pipeline_preprocess_and_stop(monkeypatch):
    pipeline = _make_pipeline(monkeypatch)
    assert pipeline._preprocess_payload({"type": "x"}) is None
    assert pipeline._preprocess_payload({"type": "alert", "alert": None}) is None
    assert pipeline._preprocess_payload({"type": "alert", "alert": {"bad": "data"}}) is None
    _run(pipeline.stop())
    assert pipeline._running is False


# ------------------------------------------------------------------
# repair_service/saga.py
# ------------------------------------------------------------------


def test_repair_saga_success():
    orch = RepairSagaOrchestrator()
    step = RepairSagaStep(
        step_id="rs1",
        service="repair",
        action="reboot",
        compensation="undo_reboot",
    )
    transaction = RepairSagaTransaction(saga_id="rsg1", task_id="t1", steps=[step])

    async def act():
        return {"rebooted": True}

    async def comp():
        return {"undone": True}

    orch.register("rsg1", transaction.steps, {"reboot": act}, {"undo_reboot": comp})
    result = _run(orch.execute("rsg1"))  # noqa: F841  # Variable for test verification
    assert result["success"] is True
    assert orch.get_transaction("rsg1").status == "success"


def test_repair_saga_failure_and_compensation():
    orch = RepairSagaOrchestrator()
    step = RepairSagaStep(
        step_id="rs2",
        service="repair",
        action="reboot",
        compensation="undo_reboot",
    )
    step2 = RepairSagaStep(
        step_id="rs3",
        service="repair",
        action="crash",
        compensation="undo_crash",
    )
    transaction = RepairSagaTransaction(saga_id="rsg2", task_id="t1", steps=[step, step2])

    async def act():
        return {"rebooted": True}

    async def crash():
        raise Exception("boom")

    async def comp():
        return {"undone": True}

    orch.register(
        "rsg2",
        transaction.steps,
        {"reboot": act, "crash": crash},
        {"undo_reboot": comp, "undo_crash": comp},
    )
    result = _run(orch.execute("rsg2"))  # noqa: F841  # Variable for test verification
    assert result["success"] is False
    assert orch.get_transaction("rsg2").status == "compensating"
    assert step.status == "compensated"


def test_repair_saga_not_found_and_missing_action():
    orch = RepairSagaOrchestrator()
    assert _run(orch.execute("missing"))["success"] is False

    step = RepairSagaStep(
        step_id="rs4",
        service="repair",
        action="noop",
        compensation="undo",
    )
    transaction = RepairSagaTransaction(saga_id="rsg3", task_id="t1", steps=[step])
    orch.register("rsg3", transaction.steps, {}, {})
    result = _run(orch.execute("rsg3"))  # noqa: F841  # Variable for test verification
    assert result["success"] is False
    assert "No action" in result["error"]


# ------------------------------------------------------------------
# repair_service/health_check.py
# ------------------------------------------------------------------


def test_health_check_success(monkeypatch):
    fake_proc = MagicMock()
    fake_proc.returncode = 0
    fake_proc.communicate = AsyncMock(return_value=(b"active\n", b""))
    monkeypatch.setattr(asyncio, "create_subprocess_shell", AsyncMock(return_value=fake_proc))

    engine = HealthCheckEngine(timeout=1)
    result = _run(
        engine.check_service_status("nginx")
    )  # noqa: F841  # Variable for test verification
    assert result["success"] is True
    result = _run(engine.check_process_exists(1234))  # noqa: F841  # Variable for test verification
    assert result["success"] is True
    result = _run(
        engine.check_metric_threshold("cpu", 100.0, 50.0, 10.0)
    )  # noqa: F841  # Variable for test verification
    assert result["success"] is True


def test_health_check_timeout_and_exception(monkeypatch):
    engine = HealthCheckEngine(timeout=1)
    monkeypatch.setattr(
        asyncio, "create_subprocess_shell", AsyncMock(side_effect=asyncio.TimeoutError)
    )
    result = _run(
        engine.check_service_status("nginx")
    )  # noqa: F841  # Variable for test verification
    assert result["success"] is False
    assert result["stderr"] == "timeout"

    monkeypatch.setattr(
        asyncio, "create_subprocess_shell", AsyncMock(side_effect=Exception("boom"))
    )
    result = _run(
        engine.check_service_status("nginx")
    )  # noqa: F841  # Variable for test verification
    assert result["success"] is True  # fallback simulation
    assert result["stderr"] == "boom"


# ------------------------------------------------------------------
# agent_orchestration_service/orchestrator.py
# ------------------------------------------------------------------


def _make_orchestrator():
    cache = CacheManager(redis_url="")
    return AgentOrchestrator(cache=cache, memory_orchestrator=None)


def test_orchestrator_basic_methods():
    orch = _make_orchestrator()
    assert "decompose_task" in orch.list_methods()
    stats = _run(orch.get_stats())
    assert stats.service == "agent-orchestration-service"
    assert isinstance(stats.cache_size, int)


def test_orchestrator_decompose():
    orch = _make_orchestrator()
    request = DecomposeRequest(
        task="Monitor CPU, diagnose root cause, repair the service, and summarize",
        max_subtasks=2,
    )
    response = _run(orch.decompose_task(request))
    assert response.task == request.task
    assert 1 <= len(response.subtasks) <= 2
    assert response.plan_id


def test_orchestrator_run_and_coordinate():
    orch = _make_orchestrator()
    req = AgentRequest(agent_type=AgentType.GENERIC, input_data={"task": "test"})
    response = _run(orch.run_agent(req))
    assert response.agent_type == "generic"

    subtasks = [
        SubTask(task_id="t1", description="Collect metrics", agent_type=AgentType.MONITOR),
        SubTask(
            task_id="t2",
            description="Diagnose",
            agent_type=AgentType.DIAGNOSTIC,
            dependencies=["t1"],
        ),
    ]
    coord = _run(orch.coordinate(CoordinateRequest(subtasks=subtasks, run_parallel=False)))
    assert coord.completed == ["t1", "t2"]
    assert coord.failed == []

    # parallel branch
    subtasks2 = [
        SubTask(task_id="p1", description="Repair", agent_type=AgentType.REPAIR),
        SubTask(task_id="p2", description="Analyze", agent_type=AgentType.ANALYSIS),
    ]
    coord2 = _run(orch.coordinate(CoordinateRequest(subtasks=subtasks2, run_parallel=True)))
    assert "p1" in coord2.completed and "p2" in coord2.completed


def test_orchestrator_collaborate_and_aggregate():
    orch = _make_orchestrator()
    collab = _run(
        orch.collaborate(
            CollaborateRequest(
                task="repair the database", agent_types=[AgentType.REPAIR], run_parallel=False
            )
        )
    )
    assert collab.task == "repair the database"
    assert collab.aggregated_output

    results = [
        AgentResult(agent_type="repair", output="fix1", confidence=0.8),
        AgentResult(agent_type="repair", output="fix1", confidence=0.8),
        AgentResult(agent_type="repair", output="fix2", confidence=0.7),
    ]
    concat = _run(orch.aggregate(AggregateRequest(results=results, strategy="concat")))
    assert "fix1" in concat.aggregated_output
    merge = _run(orch.aggregate(AggregateRequest(results=results, strategy="merge")))
    assert "fix2" in merge.aggregated_output
    vote = _run(orch.aggregate(AggregateRequest(results=results, strategy="vote")))
    assert "fix1" in vote.aggregated_output


def test_orchestrator_error_handling():
    orch = _make_orchestrator()
    cases = [
        ("timeout from upstream", "retry_with_backoff"),
        ("permission denied", "escalate"),
        ("404 not found", "verify_input"),
        ("rate limit exceeded", "throttle"),
        ("something weird", "retry"),
    ]
    for error, strategy in cases:
        response = _run(orch.handle_error(ErrorHandleRequest(error=error)))
        assert response.strategy == strategy


def test_langgraph_adapter_fallback():
    adapter = LangGraphAdapter()
    result = _run(
        adapter.execute(object(), {"task": "x"})
    )  # noqa: F841  # Variable for test verification
    assert "fallback result" in result["result"]


# ------------------------------------------------------------------
# agent_orchestration_service/cache.py
# ------------------------------------------------------------------


def test_cache_manager_memory_and_redis(monkeypatch):
    cache = CacheManager(redis_url="")
    _run(cache.set("k1", {"v": 1}))
    assert _run(cache.get("k1")) == {"v": 1}
    _run(cache.clear())
    assert _run(cache.get("k1")) is None

    # cover redis branch
    fake_client = MagicMock()
    fake_client.get = AsyncMock(return_value='{"v": 2}')
    fake_client.setex = AsyncMock()
    fake_client.flushdb = AsyncMock()
    fake_module = types.SimpleNamespace(from_url=MagicMock(return_value=fake_client))
    monkeypatch.setattr(agent_cache_module, "aioredis", fake_module)
    cache2 = CacheManager(redis_url="redis://test")
    assert _run(cache2.get("k2")) == {"v": 2}
    _run(cache2.set("k2", {"v": 3}))
    fake_client.setex.assert_awaited_once()
    _run(cache2.clear())
    fake_client.flushdb.assert_awaited_once()


def test_alert_router_branches(monkeypatch):
    router = Router()
    router.add_rule(
        RoutingRule(
            name="disabled",
            conditions={"category": "x"},
            destination="x",
            priority=10,
            enabled=False,
        )
    )
    router.add_rule(
        RoutingRule(
            name="tag",
            conditions={"tags.env": "prod"},
            destination="tagged",
            priority=5,
        )
    )

    # disabled rule skipped, _default_route backend branch
    a1 = Alert(
        id="rb1",
        title="t",
        category="backend",
        level=AlertSeverity.WARNING,
        alert_type="api",
    )
    assert router.route(a1) == "team:backend"

    # team tag short-circuit
    a2 = Alert(
        id="rb2",
        title="t",
        category="other",
        level=AlertSeverity.CRITICAL,
        alert_type="api",
        tags={"team": "sre"},
    )
    assert router.route(a2) == "team:sre"

    # on-call adapter raises -> fallback to default
    class BadAdapter:
        def lookup(self, **kwargs):
            raise RuntimeError("no")

    monkeypatch.setattr(alert_router_module, "get_oncall_adapter", lambda: BadAdapter())
    a3 = Alert(
        id="rb3",
        title="t",
        category="other",
        level=AlertSeverity.HIGH,
        alert_type="api",
    )
    assert router.route(a3) == "default"

    # no callable adapter -> category branches in _resolve_team_route
    monkeypatch.setattr(alert_router_module, "get_oncall_adapter", None)
    a4 = Alert(
        id="rb4",
        title="t",
        category="database",
        level=AlertSeverity.CRITICAL,
        alert_type="api",
    )
    assert router.route(a4) == "team:infrastructure"
    a5 = Alert(
        id="rb5",
        title="t",
        category="frontend",
        level=AlertSeverity.CRITICAL,
        alert_type="api",
    )
    assert router.route(a5) == "team:frontend"

    # _default_route direct calls
    a6 = Alert(
        id="rb6",
        title="t",
        category="security",
        level=AlertSeverity.WARNING,
        alert_type="api",
    )
    assert router._default_route(a6) == "team:security"
    a7 = Alert(
        id="rb7",
        title="t",
        category="other",
        level=AlertSeverity.FATAL,
        alert_type="api",
    )
    assert router._default_route(a7) == "immediate"


# ------------------------------------------------------------------
# alert_service/processor_core.py - additional coverage
# ------------------------------------------------------------------


def test_alert_pipeline_run_and_drain(monkeypatch):
    pipeline = _make_pipeline(monkeypatch)
    alert = Alert(id="run1", title="run", level=AlertSeverity.WARNING)
    payload = {"type": "alert", "alert": alert.model_dump()}
    monkeypatch.setattr(
        pipeline.mq,
        "consume",
        AsyncMock(side_effect=[payload, asyncio.CancelledError()]),
    )
    _run(pipeline.run())
    assert pipeline._running is False


def test_alert_pipeline_is_resolved_expiration(monkeypatch):
    pipeline = _make_pipeline(monkeypatch)
    monkeypatch.setattr(
        processor_core_module,
        "time",
        types.SimpleNamespace(time=lambda: 1000.0),
    )
    pipeline._resolved_fingerprints["old"] = 1.0
    assert _run(pipeline._is_resolved("old")) is False
    assert "old" not in pipeline._resolved_fingerprints
    pipeline._resolved_fingerprints["new"] = 2000.0
    assert _run(pipeline._is_resolved("new")) is True


def test_alert_pipeline_route_and_publish_resolved(monkeypatch):
    pipeline = _make_pipeline(monkeypatch)
    alert = Alert(
        id="rp1",
        title="t",
        level=AlertSeverity.CRITICAL,
        category="security",
        fingerprint="fp",
    )
    monkeypatch.setattr(pipeline, "_is_resolved", AsyncMock(return_value=True))
    result = _run(
        pipeline._route_and_publish(alert)
    )  # noqa: F841  # Variable for test verification
    assert result["status"] == "resolved"


def test_alert_pipeline_flush_aggregates(monkeypatch):
    pipeline = _make_pipeline(monkeypatch)
    now = datetime.utcnow()
    a1 = Alert(
        id="ag1",
        title="agg",
        level=AlertSeverity.CRITICAL,
        category="security",
        detected_at=now,
    )
    a2 = Alert(
        id="ag2",
        title="agg",
        level=AlertSeverity.CRITICAL,
        category="security",
        detected_at=now,
    )
    _run(pipeline.process_alert(a1))
    _run(pipeline.process_alert(a2))
    flushed = _run(pipeline.flush(force=True))
    assert len(flushed) == 1


def test_alert_pipeline_saga_retry_and_compensation(monkeypatch):
    pipeline = _make_pipeline(monkeypatch, max_retries=2)
    monkeypatch.setattr(asyncio, "sleep", AsyncMock())
    dead = []
    monkeypatch.setattr(processor_core_module, "_append_dead_letter", dead.append)

    # save succeeds on second attempt
    monkeypatch.setattr(
        pipeline.repository,
        "save",
        AsyncMock(side_effect=[Exception("err"), "ok"]),
    )
    # publish always fails to trigger compensation
    monkeypatch.setattr(
        pipeline.mq,
        "publish",
        AsyncMock(side_effect=Exception("pub fail")),
    )

    alert = Alert(
        id="saga1",
        title="t",
        level=AlertSeverity.CRITICAL,
        category="security",
    )
    result = _run(
        pipeline._saga_save_and_publish(alert)
    )  # noqa: F841  # Variable for test verification
    assert result["status"] == "failed"
    assert result["failed_step"] == "publish"
