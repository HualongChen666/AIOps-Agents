# -*- coding: utf-8 -*-
"""Targeted unit tests for core.abac, core.agent.executor and core.business_impact_engine."""

import asyncio
import hashlib
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import core.abac as abac_mod
import core.agent.executor as executor_mod
import core.business_impact_engine as bie_mod
from core.abac import (
    ABACEngine,
    ActionType,
    Environment,
    Resource,
    ResourceType,
    Subject,
    create_abac_engine,
)
from core.agent.executor import (
    AutonomousExecutor,
    RiskAssessor,
    RollbackMechanism,
    SafetyBoundary,
    TrustMechanism,
    ValidationMechanism,
    create_autonomous_executor,
)
from core.agent.planner import Task, TaskStatus
from core.agent.tools import ToolCategory
from core.business_impact_engine import (
    BusinessImpactEngine,
    assess_business_impact,
    list_business_impact_services,
    list_business_impact_ux_metrics,
)
from core.command_guard import RiskLevel

pytestmark = pytest.mark.core


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
class FakeCursor:
    def __init__(self, fetchone_val=None, execute_side=None):
        self.fetchone_val = fetchone_val
        self._execute_side = execute_side
        self.execute = MagicMock(side_effect=execute_side)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def fetchone(self):
        return self.fetchone_val

    def fetchall(self):
        return self.fetchone_val or []


class FakeConn:
    def __init__(self, cursor):
        self._cursor = cursor
        self.commit = MagicMock()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def cursor(self):
        return self._cursor


class FakeStorage:
    def __init__(self, policies=None, query_result=None, fetchone_val=None, execute_side=None):
        self._policies = policies or []
        self._query_result = query_result
        self.cursor = FakeCursor(fetchone_val=fetchone_val, execute_side=execute_side)
        self.conn = FakeConn(self.cursor)
        self.execute_query = MagicMock(return_value=self._query_result or self._policies)

    def get_connection(self):
        return self.conn


def _policy_row(**overrides):
    base = {
        "id": 1,
        "name": "test-policy",
        "description": "",
        "enabled": True,
        "effect": "allow",
        "subject_conditions": {},
        "resource_conditions": {},
        "environment_conditions": {},
        "actions": ["read"],
        "priority": 0,
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
    }
    base.update(overrides)
    return base


@pytest.fixture
def executor(monkeypatch):
    monitor = MagicMock()
    monitor.record_iteration.return_value = None
    monitor.check_anomaly.return_value = None
    monitor.record_tool_call.return_value = None
    monitor.record_action.return_value = None
    monitor.record_error.return_value = None

    monkeypatch.setattr(executor_mod, "get_behavior_monitor", lambda: monitor)
    monkeypatch.setattr(executor_mod, "AUDIT_AVAILABLE", True)
    monkeypatch.setattr(executor_mod, "_log_audit_event", MagicMock())
    monkeypatch.setattr(executor_mod, "_action_signature", lambda g, d, t, p: f"{g}|{d}|{t}|{str(p)}")
    monkeypatch.setattr("core.observability_query.prepare_for_llm", lambda result, **kw: result)

    planner = MagicMock()
    planner.get_plan_summary.return_value = {}
    planner.tasks = {}
    planner.get_ready_tasks.return_value = []

    tool_executor = MagicMock()
    tool_executor.dry_run = False
    tool_executor.default_timeout = 30
    tool_executor.selector.select_tool.return_value = MagicMock(category=ToolCategory.ANALYSIS, name="collect_metrics")
    tool_executor.execute_with_auto_selection.return_value = {"ok": True}

    exe = AutonomousExecutor(planner, tool_executor)
    exe.behavior_monitor = monitor
    return exe


# ---------------------------------------------------------------------------
# Executor helpers / classes
# ---------------------------------------------------------------------------
class TestSafetyBoundary:
    def test_operation_allowed_and_forbidden(self):
        sb = SafetyBoundary(
            allowed_operations=["a", "b"],
            forbidden_operations=["b"],
            require_approval_for=["c"],
        )
        assert sb.is_operation_allowed("a")
        assert not sb.is_operation_allowed("b")
        assert not sb.is_operation_allowed("d")
        assert sb.requires_approval("c")
        assert not sb.requires_approval("a")


class TestRiskAssessor:
    def test_assess_risk_branches(self):
        sb = SafetyBoundary(forbidden_operations=["forbidden"])
        ra = RiskAssessor(sb)
        ra.risk_history["op"] = [{"success": True, "error": None, "timestamp": datetime.now().isoformat()}]

        assert ra.assess_risk("forbidden", {}, None) == (RiskLevel.CRITICAL, "Operation forbidden is forbidden")
        assert ra.assess_risk("delete db", {}) == (RiskLevel.CRITICAL, "Destructive operation")
        assert ra.assess_risk("stop app", {}) == (RiskLevel.HIGH, "Service stop operation")
        assert ra.assess_risk("restart app", {}) == (RiskLevel.MEDIUM, "Service modification")
        assert ra.assess_risk("scale up", {}) == (RiskLevel.MEDIUM, "Resource scaling")
        assert ra.assess_risk("check logs", {}) == (RiskLevel.LOW, "Read-only operation")
        assert ra.assess_risk("unknown", {}, ToolCategory.EXECUTION) == (
            RiskLevel.MEDIUM,
            "Execution tool requires confirmation",
        )
        assert ra.assess_risk("unknown", {}, ToolCategory.DIAGNOSTIC) == (
            RiskLevel.LOW,
            "Read-only/observability operation",
        )
        assert ra.assess_risk("unknown", {}) == (RiskLevel.MEDIUM, "Unknown operation type")

        assert ra.check_historical_risk("missing") == 1.0
        assert ra.check_historical_risk("op") == 1.0
        assert ra.check_historical_risk("op") == 1.0

    def test_record_execution_history(self):
        sb = SafetyBoundary()
        ra = RiskAssessor(sb)
        for i in range(110):
            ra.record_execution("op", i % 2 == 0, None)
        assert len(ra.risk_history["op"]) == 100


class TestTrustMechanism:
    def test_update_and_can_auto_execute(self):
        tm = TrustMechanism(initial_trust=0.5, learning_rate=0.1)
        assert tm.get_trust_score("op") == 0.5
        tm.update_trust("op", True)
        assert tm.get_trust_score("op") > 0.5
        tm.update_trust("op", False)
        assert tm.get_trust_score("op") < 0.55

        tm.trust_scores["low"] = 0.1
        tm.trust_scores["mid"] = 0.7
        tm.trust_scores["high"] = 0.9
        assert not tm.can_auto_execute("low", RiskLevel.LOW)
        assert tm.can_auto_execute("mid", RiskLevel.MEDIUM)
        assert tm.can_auto_execute("high", RiskLevel.HIGH)
        assert not tm.can_auto_execute("high", RiskLevel.CRITICAL)


class TestRollbackMechanism:
    def test_rollback_branches(self):
        rb = RollbackMechanism()
        assert not rb.execute_rollback("missing")

        action = MagicMock()
        rb.register_rollback("ok", action)
        assert rb.execute_rollback("ok")
        action.assert_called_once()

        rb.register_rollback("not_callable", "x")
        assert rb.execute_rollback("not_callable")

        rb.register_rollback("boom", MagicMock(side_effect=RuntimeError("fail")))
        assert not rb.execute_rollback("boom")
        assert len(rb.rollback_history) == 3


class TestValidationMechanism:
    def test_validate_branches(self):
        vm = ValidationMechanism()
        assert vm.validate("op", None, {}) == (True, "No validation rules")

        vm.register_validation("pass", lambda r, c: (True, "ok"))
        assert vm.validate("pass", None, {}) == (True, "All validations passed")

        vm.register_validation("fail", lambda r, c: (False, "bad"))
        assert vm.validate("fail", None, {}) == (False, "bad")

        def boom(result, context):
            raise RuntimeError("boom")

        vm.register_validation("boom", boom)
        passed, reason = vm.validate("boom", None, {})
        assert not passed
        assert "Validation error" in reason


class TestExecutorHelpers:
    def test_get_execution_confidence(self, executor):
        assert executor._get_execution_confidence({}) is None
        assert executor._get_execution_confidence({"execution_confidence": "0.9"}) == 0.9
        assert executor._get_execution_confidence({"execution_confidence": "bad"}) is None
        assert executor._get_execution_confidence({"diagnosis": {"confidence": 0.8}}) == 0.8
        assert executor._get_execution_confidence({"root_cause_analysis": {"candidates": [{"confidence": 0.7}]}}) == 0.7
        assert executor._get_execution_confidence({"analysis": {"confidence": "x"}}) is None

    def test_is_remediation_action(self, executor):
        assert executor._is_remediation_action("restart service")
        assert executor._is_remediation_action("scale up")
        assert executor._is_remediation_action("delete logs")
        assert executor._is_remediation_action("deploy app")
        assert not executor._is_remediation_action("check metrics")

    def test_merge_tool_result(self, executor):
        ctx = {"metrics_data": {"x": 1}}
        executor._merge_tool_result_into_context("collect_metrics", {"cpu": 50}, ctx)
        assert "cpu" in ctx["metrics_data"]

        executor._merge_tool_result_into_context("collect_correlated_alerts", [1, 2], ctx)
        assert ctx["correlated_alerts"] == [1, 2]

        executor._merge_tool_result_into_context("collect_change_events", [3], ctx)
        assert ctx["change_events"] == [3]

        executor._merge_tool_result_into_context("collect_kubernetes_events", [4], ctx)
        assert ctx["kubernetes_events"] == [4]

        executor._merge_tool_result_into_context("collect_logs", {"log": "text"}, ctx)
        assert ctx["logs_data"] == {"log": "text"}

        executor._merge_tool_result_into_context("collect_topology", {"nodes": []}, ctx)
        assert ctx["topology"] == {"nodes": []}

        executor._merge_tool_result_into_context("unknown", "x", ctx)


class TestAutonomousExecutor:
    def test_set_execution_mode_and_statistics(self, executor):
        executor.set_execution_mode("autonomous")
        assert executor.execution_mode == "autonomous"
        executor.set_execution_mode("manual")
        assert executor.execution_mode == "manual"
        with pytest.raises(ValueError):
            executor.set_execution_mode("bad")

        stats = executor.get_statistics()
        assert "execution_mode" in stats
        assert "trust_scores" in stats
        assert "risk_history" in stats
        assert "rollback_history" in stats

    def test_execute_task_manual_pending(self, executor):
        executor.execution_mode = "manual"
        executor.approval_required = True
        task = Task(id="t1", description="restart app")
        result = executor.execute_task(task, {})
        assert result["status"] == "pending_approval"

    def test_execute_task_autonomous_low_confidence(self, executor):
        executor.execution_mode = "autonomous"
        task = Task(id="t1", description="restart app")
        result = executor.execute_task(task, {})
        assert result["status"] == "pending_approval"
        assert "confidence" in result["reason"].lower() or "trust" in result["reason"].lower()

    def test_execute_task_hybrid_pending(self, executor):
        executor.execution_mode = "hybrid"
        task = Task(id="t1", description="restart app")
        result = executor.execute_task(task, {})
        assert result["status"] == "pending_approval"

    def test_execute_task_success(self, executor):
        task = Task(id="t1", description="check cpu usage")
        result = executor.execute_task(task, {})
        assert result["status"] == "completed"
        assert result["result"]["ok"]

    def test_execute_task_validation_fails(self, executor):
        executor.validation_mechanism.register_validation("check cpu usage", lambda r, c: (False, "bad"))
        task = Task(id="t1", description="check cpu usage")
        result = executor.execute_task(task, {})
        assert result["status"] == "failed"
        assert "bad" in result["error"]

    def test_execute_task_exception(self, executor):
        executor.tool_executor.execute_with_auto_selection.side_effect = RuntimeError("boom")
        task = Task(id="t1", description="check cpu usage")
        result = executor.execute_task(task, {})
        assert result["status"] == "failed"

    def test_execute_plan_success(self, executor):
        task = Task(id="t1", description="check cpu usage", parameters={"target": "cpu"})
        executor.planner.plan.return_value = [task]
        executor.memory_bridge = MagicMock()
        executor.memory_bridge.retrieve_relevant_experiences.return_value = []
        executor.memory_bridge.save_experience.return_value = {"id": 1}
        result = executor.execute_plan("goal", {"enable_memory": True}, ["tool"])
        assert result["goal"] == "goal"
        assert result["results"][0]["status"] == "completed"

    def test_execute_plan_anomaly(self, executor):
        executor.behavior_monitor.check_anomaly.return_value = {"messages": "bad"}
        result = executor.execute_plan("goal", {}, ["tool"])
        assert "Behavior anomaly" in result["error"]

    def test_execute_plan_depth_limit(self, executor):
        result = executor.execute_plan("goal", {}, ["tool"], _depth=5)
        assert "recursion depth" in result["error"]

    def test_execute_plan_repeated_goal(self, executor):
        result = executor.execute_plan("goal", {"__visited_goals": {"goal"}}, ["tool"])
        assert "Repeated goal" in result["error"]

    def test_execute_plan_too_many_tasks(self, executor):
        executor.planner.plan.return_value = [Task(id=str(i), description="t") for i in range(25)]
        result = executor.execute_plan("goal", {}, ["tool"])
        assert "exceed maximum" in result["error"]

    def test_execute_plan_max_iterations(self, executor):
        executor.max_iterations = 1
        executor.planner.plan.return_value = [
            Task(id="a", description="check a"),
            Task(id="b", description="check b"),
        ]
        executor.memory_bridge = None
        result = executor.execute_plan("goal", {"enable_memory": False}, ["tool"])
        statuses = [r["status"] for r in result["results"]]
        assert "failed" in statuses

    def test_execute_plan_repeated_action(self, executor):
        executor.planner.plan.return_value = [
            Task(id="a", description="check"),
            Task(id="b", description="check"),
        ]
        executor.memory_bridge = None
        monkeypatch = None
        result = executor.execute_plan("goal", {"__visited_goals": set(), "enable_memory": False}, ["tool"])
        assert any("Repeated action" in r.get("error", "") for r in result["results"])

    def test_execute_plan_memory_retrieval_error(self, executor):
        executor.memory_bridge = MagicMock()
        executor.memory_bridge.retrieve_relevant_experiences.side_effect = RuntimeError("boom")
        task = Task(id="t1", description="check", parameters={"target": "cpu"})
        executor.planner.plan.return_value = [task]
        result = executor.execute_plan("goal", {"enable_memory": True}, ["tool"])
        assert result["results"][0]["status"] == "completed"

    def test_create_autonomous_executor(self):
        planner = MagicMock()
        planner.get_plan_summary.return_value = {}
        tool = MagicMock()
        tool.dry_run = False
        tool.default_timeout = 30
        tool.selector = MagicMock()
        tool.execute_with_auto_selection = MagicMock(return_value={})
        with patch("core.agent.planner.create_planner", return_value=planner) as cp, patch(
            "core.agent.tools.create_tool_executor", return_value=tool
        ) as ct:
            exe = create_autonomous_executor()
            assert exe is not None
            cp.assert_called_once()
            ct.assert_called_once()

    def test_execute_plan_with_subagents(self, executor, monkeypatch):
        task = Task(id="s1", description="sub task", parameters={"action": "worker"})
        executor.planner.plan.return_value = [task]

        sub_res = MagicMock()
        sub_res.status = "completed"
        sub_res.result = {"ok": 1}
        sub_res.error = None
        sub_res.to_dict = lambda: {"status": "completed"}

        dispatcher = MagicMock()
        dispatcher.dispatch_batch.return_value = [sub_res]
        dispatcher.shutdown.return_value = None

        monkeypatch.setattr("core.agent.subagent.SubAgentDispatcher", MagicMock(return_value=dispatcher))
        result = executor.execute_plan_with_subagents("goal", {}, ["tool"])
        assert result["subagent_results"]

    def test_execute_plan_parallel(self, executor, monkeypatch):
        t1 = Task(id="p1", description="task one")
        t2 = Task(id="p2", description="task two")
        executor.planner.plan.return_value = [t1, t2]
        executor.planner.tasks = {"p1": t1, "p2": t2}

        def _adjust(task_id, status, result=None, error=None):
            if task_id in executor.planner.tasks:
                executor.planner.tasks[task_id].status = status
                executor.planner.tasks[task_id].result = result
                executor.planner.tasks[task_id].error = error

        executor.planner.adjust_plan.side_effect = _adjust
        executor.planner.get_ready_tasks.side_effect = lambda: [
            t for t in executor.planner.tasks.values() if t.status == TaskStatus.PENDING
        ]

        sub_res = MagicMock()
        sub_res.status = "completed"
        sub_res.result = {"ok": 1}
        sub_res.error = None
        sub_res.agent_id = "agent"

        dispatcher = MagicMock()
        dispatcher.dispatch_parallel.return_value = {"p1": sub_res, "p2": sub_res}
        dispatcher.shutdown.return_value = None

        monkeypatch.setattr("core.agent.subagent.SubAgentDispatcher", MagicMock(return_value=dispatcher))
        result = executor.execute_plan_parallel("goal", {}, ["tool"])
        assert "results" in result


# ---------------------------------------------------------------------------
# ABAC
# ---------------------------------------------------------------------------
class TestABAC:
    def test_engine_not_initialized(self):
        storage = FakeStorage()
        engine = ABACEngine(storage)
        subject = Subject("u1", "user", {"role": "admin"}, {"admin"}, set())
        resource = Resource("r1", ResourceType.ANOMALY, {}, None)
        assert not engine.evaluate(subject, resource, ActionType.READ)

    def test_evaluate_allow_and_deny(self):
        policies = [
            _policy_row(
                id=1,
                name="allow-admin",
                effect="allow",
                subject_conditions={"role": {"in": ["admin"]}},
                resource_conditions={"type": "anomaly"},
                actions=["read"],
                priority=10,
            ),
            _policy_row(
                id=2,
                name="deny-guest",
                effect="deny",
                subject_conditions={"role": {"equals": "guest"}},
                resource_conditions={},
                actions=["read"],
                priority=20,
            ),
        ]
        storage = FakeStorage(policies=policies)
        engine = ABACEngine(storage)
        assert engine.initialize()

        admin = Subject("u1", "user", {"role": "admin"}, {"admin"}, set())
        resource = Resource("r1", ResourceType.ANOMALY, {"type": "anomaly"}, None)
        assert engine.evaluate(admin, resource, ActionType.READ)

        guest = Subject("u2", "user", {"role": "guest"}, {"guest"}, set())
        assert not engine.evaluate(guest, resource, ActionType.READ)

        other = Subject("u3", "user", {"role": "user"}, set(), set())
        assert not engine.evaluate(other, resource, ActionType.WRITE)
        assert not engine.evaluate(other, resource, ActionType.READ)

    def test_matches_conditions(self):
        engine = ABACEngine(FakeStorage())
        attrs = {
            "role": "admin",
            "level": 5,
            "tags": ["prod", "x"],
            "name": "svc-01",
        }
        assert engine._matches_conditions(attrs, {"role": "admin"})
        assert not engine._matches_conditions(attrs, {"role": "user"})
        assert not engine._matches_conditions(attrs, {"missing": 1})

        conditions = {
            "role": {"in": ["admin", "ops"]},
            "level": {"gte": 1, "lte": 10},
            "tags": {"contains": "prod"},
            "name": {"regex": r"svc-\d+"},
        }
        assert engine._matches_conditions(attrs, conditions)

        assert not engine._matches_conditions(attrs, {"level": {"gt": 10}})
        assert not engine._matches_conditions(attrs, {"level": {"lt": 1}})
        assert not engine._matches_conditions(attrs, {"tags": {"contains": "missing"}})
        assert not engine._matches_conditions(attrs, {"name": {"regex": r"^db-"}})

    def test_crud_policies(self):
        storage = FakeStorage(policies=[], fetchone_val=(42,))
        engine = ABACEngine(storage)
        assert engine.initialize()

        pid = engine.create_policy(
            "p1",
            "desc",
            "allow",
            {"role": "admin"},
            {"type": "anomaly"},
            {},
            ["read"],
            priority=5,
        )
        assert pid == "42"

        assert engine.update_policy("42", name="p2")
        assert engine.update_policy("42", enabled=False, effect="deny")
        assert engine.update_policy("42")

        assert engine.delete_policy("42")

        storage.execute_query.return_value = [
            _policy_row(id=1, name="listed", subject_conditions={"role": "admin"}, resource_conditions={"type": "anomaly"}, environment_conditions={}),
        ]
        listed = engine.list_policies(enabled_only=True)
        assert listed
        listed_all = engine.list_policies(enabled_only=False)
        assert listed_all

    def test_update_and_delete_errors(self):
        storage = FakeStorage(execute_side=RuntimeError("db"))
        engine = ABACEngine(storage)
        assert not engine.update_policy("1", name="x")
        assert not engine.delete_policy("1")
        storage.execute_query = MagicMock(return_value=[])
        assert engine.list_policies() == []

    def test_initialize_failure(self):
        storage = FakeStorage()
        storage.get_connection = MagicMock(side_effect=RuntimeError("conn"))
        engine = ABACEngine(storage)
        assert not engine.initialize()

    def test_log_evaluation_failure(self):
        storage = FakeStorage()
        storage.get_connection = MagicMock(side_effect=RuntimeError("conn"))
        engine = ABACEngine(storage)
        engine._is_initialized = True
        engine._log_evaluation("1", "u", "r", "read", True)

    def test_create_abac_engine_factory(self):
        storage = FakeStorage(policies=[])
        engine = create_abac_engine(storage)
        assert engine is not None

        storage = FakeStorage()
        storage.get_connection = MagicMock(side_effect=RuntimeError("conn"))
        assert create_abac_engine(storage) is None


# ---------------------------------------------------------------------------
# Business impact engine
# ---------------------------------------------------------------------------
def _patch_bie(monkeypatch, topo, manager, summary, history, linux_hosts, priority_available=True):
    monkeypatch.setattr(bie_mod, "get_full_link_topology", AsyncMock(return_value=topo))
    monkeypatch.setattr(bie_mod, "get_service_monitoring_manager", lambda: manager)
    monkeypatch.setattr(bie_mod, "get_real_summary", AsyncMock(return_value=summary))
    monkeypatch.setattr(bie_mod, "metrics_history", MagicMock(to_dict=MagicMock(return_value=history)))
    monkeypatch.setattr(bie_mod, "LINUX_HOSTS", linux_hosts)
    monkeypatch.setattr(bie_mod, "PRIORITY_AVAILABLE", priority_available)
    if priority_available:
        monkeypatch.setattr(bie_mod, "BusinessImpactAssessor", MagicMock())


class TestBusinessImpactEngine:
    @pytest.fixture
    def engine(self, monkeypatch):
        topo = {
            "nodes": [
                {"id": "payment-service", "pagerank": 0.9},
                {"id": "cache-service", "pagerank": 0.5},
                {"id": "other-service", "pagerank": 0.1},
                "bad-node",
            ],
            "edges": [
                {"source": "payment-service", "target": "cache-service"},
                {"source": "cache-service", "target": "other-service"},
            ],
        }
        manager = MagicMock()
        manager.get_monitoring_summary.return_value = {"services": ["api-service"]}

        manager.analyze_service_performance = MagicMock(return_value={
            "metric_analysis": {
                "api_error_rate": {"avg": 0.15, "count": 10, "max": 0.2},
                "api_response_time": {"avg": 1200.0, "count": 10},
                "cpu_usage": {"avg": 80.0, "count": 10},
                "memory_usage": {"avg": 90.0, "count": 10},
            }
        })
        manager.get_service_metrics.return_value = [
            SimpleNamespace(timestamp=datetime.now(timezone.utc)),
        ]

        summary = {"alerts": {"total": 5}}
        history = {
            "cpu": [10.0, 20.0],
            "memory": [30.0, 40.0],
            "net_in": [100.0, 110.0],
        }
        linux_hosts = {"hosts": [{"host_name": "host-1"}, {"name": "host-2"}, "host-3"]}

        _patch_bie(monkeypatch, topo, manager, summary, history, linux_hosts)

        monkeypatch.setattr("asyncio.get_event_loop", lambda: MagicMock(time=MagicMock(return_value=0.0)))
        eng = BusinessImpactEngine()
        if eng._assessor:
            assessment = MagicMock()
            assessment.impact_score = 0.8
            assessment.revenue_impact = 9999
            eng._assessor.assess.return_value = assessment
        return eng

    @pytest.mark.asyncio
    async def test_get_topology_cache(self, monkeypatch):
        topo = {"nodes": [{"id": "x"}], "edges": []}
        manager = MagicMock()
        manager.get_monitoring_summary.return_value = {"services": []}
        _patch_bie(monkeypatch, topo, manager, {}, {"cpu": [], "memory": [], "net_in": []}, {})

        fake_loop = MagicMock()
        fake_loop.time.side_effect = [0.0, 10.0, 11.0]
        monkeypatch.setattr("asyncio.get_event_loop", lambda: fake_loop)

        eng = BusinessImpactEngine()
        first = await eng._get_topology()
        assert first == topo
        second = await eng._get_topology()
        assert second == topo
        third = await eng._get_topology()
        assert third == topo

    @pytest.mark.asyncio
    async def test_get_all_service_names(self, engine):
        names = await engine._get_all_service_names()
        assert "payment-service" in names
        assert "cache-service" in names
        assert "other-service" in names
        assert "api-service" in names
        assert "host-1" in names
        assert "host-3" in names

    def test_pagerank_and_degrees(self, engine):
        topo = {"nodes": [{"id": "payment-service", "pagerank": 0.9}], "edges": []}
        assert engine._get_pagerank(topo, "payment-service") == 0.9
        assert engine._get_pagerank(topo, "missing") == 0.3
        in_d, out_d = engine._get_degrees(topo, "payment-service")
        assert in_d == 0 and out_d == 0

    def test_get_metric_analysis(self, engine):
        status, error_rate, response_time, cpu, memory, _ = engine._get_metric_analysis("payment-service")
        assert status == "down"
        assert error_rate > 0.1
        assert response_time > 1000

    @pytest.mark.asyncio
    async def test_compute_impact_priority_assessor(self, engine):
        impact = await engine._compute_impact("payment-service")
        assert impact["name"] == "payment-service"
        assert impact["impactScore"] >= 4.0
        assert "category" in impact
        assert "metrics" in impact

    @pytest.mark.asyncio
    async def test_compute_impact_no_assessor(self, monkeypatch):
        topo = {"nodes": [{"id": "other-service", "pagerank": 0.1}], "edges": []}
        manager = MagicMock()
        manager.get_monitoring_summary.return_value = {"services": []}

        manager.analyze_service_performance = MagicMock(return_value={
            "metric_analysis": {
                "error_rate": {"avg": 0.01, "count": 5},
                "response_time": {"avg": 100.0, "count": 5},
                "cpu_usage": {"avg": 50.0, "count": 5},
                "memory_usage": {"avg": 60.0, "count": 5},
            }
        })
        manager.get_service_metrics.return_value = []

        _patch_bie(monkeypatch, topo, manager, {}, {"cpu": [], "memory": [], "net_in": []}, {}, priority_available=False)
        eng = BusinessImpactEngine()
        impact = await eng._compute_impact("other-service")
        assert impact["status"] == "healthy"
        assert impact["affectedUsers"] == 0

    @pytest.mark.asyncio
    async def test_list_services_and_assess(self, monkeypatch):
        topo = {"nodes": [{"id": "api-service", "pagerank": 0.5}], "edges": []}
        manager = MagicMock()
        manager.get_monitoring_summary.return_value = {"services": []}

        manager.analyze_service_performance = MagicMock(return_value={
            "metric_analysis": {
                "error_rate": {"avg": 0.05, "count": 5},
                "response_time": {"avg": 600.0, "count": 5},
                "cpu_usage": {"avg": 70.0, "count": 5},
                "memory_usage": {"avg": 80.0, "count": 5},
            }
        })
        manager.get_service_metrics.return_value = [SimpleNamespace(timestamp=datetime.now(timezone.utc))]

        _patch_bie(monkeypatch, topo, manager, {"alerts": {"total": 1}}, {"cpu": [], "memory": [], "net_in": []}, {}, priority_available=False)
        eng = BusinessImpactEngine()
        services = await eng.list_services()
        assert services
        assert services[0]["name"] == "api-service"

        fallback = await eng.list_services()

        eng._get_all_service_names = AsyncMock(return_value=[])
        fallback2 = await eng.list_services()
        assert fallback2
        assert fallback2[0]["name"] in {"api-service", "payment-service", "auth-service", "search-service"}

        assessed = await eng.assess("unknown-service")
        assert assessed["name"] == "unknown-service"

    @pytest.mark.asyncio
    async def test_get_ux_metrics(self, monkeypatch):
        topo = {
            "nodes": [
                {"id": "api-service", "pagerank": 0.5},
            ],
            "edges": [],
        }

        manager = MagicMock()
        manager.analyze_service_performance = MagicMock(return_value={
            "metric_analysis": {
                "error_rate": {"avg": 0.02, "count": 5},
                "response_time": {"avg": 300.0, "count": 5},
                "cpu_usage": {"avg": 60.0, "count": 5},
                "memory_usage": {"avg": 70.0, "count": 5},
            }
        })
        manager.get_service_metrics.return_value = [SimpleNamespace(timestamp=datetime.now(timezone.utc))]
        manager.get_monitoring_summary.return_value = {"services": ["api-service"]}

        history = {
            "cpu": [10.0, 20.0],
            "memory": [30.0, 40.0],
            "net_in": [100.0, 110.0],
        }
        summary = {"alerts": {"total": 10}}

        _patch_bie(monkeypatch, topo, manager, summary, history, {}, priority_available=False)
        eng = BusinessImpactEngine()
        ux = await eng.get_ux_metrics()
        assert len(ux) == 7
        assert ux[0]["id"] == "UX-001"

    @pytest.mark.asyncio
    async def test_topology_load_failure(self, monkeypatch):
        manager = MagicMock()
        manager.get_monitoring_summary.return_value = {"services": []}
        _patch_bie(monkeypatch, None, manager, {}, {"cpu": [], "memory": [], "net_in": []}, {})
        monkeypatch.setattr(bie_mod, "get_full_link_topology", AsyncMock(side_effect=RuntimeError("topo")))
        eng = BusinessImpactEngine()
        topo = await eng._get_topology()
        assert topo == {"nodes": [], "edges": []}

    def test_service_id(self):
        assert BusinessImpactEngine._service_id("foo") == f"SVC-{hashlib.md5('foo'.encode()).hexdigest()[:3].upper()}"

    @pytest.mark.asyncio
    async def test_module_level_functions(self, monkeypatch):
        topo = {"nodes": [{"id": "payment-service", "pagerank": 0.9}], "edges": []}
        manager = MagicMock()
        manager.get_monitoring_summary.return_value = {"services": []}

        manager.analyze_service_performance = MagicMock(return_value={
            "metric_analysis": {
                "error_rate": {"avg": 0.01, "count": 5},
                "response_time": {"avg": 100.0, "count": 5},
                "cpu_usage": {"avg": 50.0, "count": 5},
                "memory_usage": {"avg": 60.0, "count": 5},
            }
        })
        manager.get_service_metrics.return_value = []

        _patch_bie(monkeypatch, topo, manager, {}, {"cpu": [], "memory": [], "net_in": []}, {}, priority_available=False)

        monkeypatch.setattr(bie_mod, "_engine", BusinessImpactEngine())
        single = await assess_business_impact("payment-service")
        assert single["name"] == "payment-service"

        all_services = await list_business_impact_services()
        assert isinstance(all_services, list)

        monkeypatch.setattr(bie_mod, "metrics_history", MagicMock(to_dict=MagicMock(return_value={"cpu": [], "memory": [], "net_in": []})))
        ux = await list_business_impact_ux_metrics()
        assert len(ux) == 7
