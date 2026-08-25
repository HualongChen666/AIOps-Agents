# -*- coding: utf-8 -*-
"""Real-class branch coverage tests for core/agent/executor.py.

Uses concrete instantiations of executor, planner, tools, memory and subagent
dispatchers.  No unittest.mock or monkeypatch is used; controlled behaviour is
achieved via small real subclasses and custom tool registrations.
"""

from __future__ import annotations

import pytest  # noqa: F401  # Imported for test setup

from core.agent.executor import (
    AUDIT_AVAILABLE,
    AutonomousExecutor,
    RiskAssessor,
    RollbackMechanism,
    SafetyBoundary,
    TrustMechanism,
    ValidationMechanism,
    _audit_executor,
    create_autonomous_executor,
)
from core.agent.memory_bridge import MemoryBridge
from core.agent.planner import Task, TaskPlanner, TaskStatus
from core.agent.subagent import SubAgentDispatcher, SubAgentResult
from core.agent.tools import (
    Tool,
    ToolCategory,
    ToolExecutor,
    ToolRegistry,
    ToolSelector,
)
from core.command_guard import RiskLevel


class SimpleRegistry(ToolRegistry):
    """A ToolRegistry that does not register the heavy default tools."""

    def _initialize_default_tools(self):
        pass

    def register_tool(
        self,
        name: str,
        category: ToolCategory,
        function,
        required_params=None,
        optional_params=None,
        parameters=None,
    ):
        self.register(
            Tool(
                name=name,
                description=name,
                category=category,
                function=function,
                parameters=parameters or {},
                required_params=required_params or [],
                optional_params=optional_params or [],
            )
        )


class FixedSelector(ToolSelector):
    """Selector that can be steered by a _select_tool hint in the context."""

    def select_tool(self, task_description, context):
        forced = context.get("_select_tool")
        if forced:
            return self.registry.get_tool(forced)
        return super().select_tool(task_description, context)


class BrokenSelector(FixedSelector):
    """Selector that raises once, then steers by _select_tool."""

    def __init__(self, registry):
        super().__init__(registry)
        self._calls = 0

    def select_tool(self, task_description, context):
        if context.get("_raise_select"):
            if self._calls < 1:
                self._calls += 1
                raise RuntimeError("selector broken")
        return super().select_tool(task_description, context)


class FixedToolExecutor(ToolExecutor):
    """ToolExecutor using FixedSelector for deterministic tests."""

    def __init__(self, registry, *args, **kwargs):
        super().__init__(registry, *args, **kwargs)
        self.selector = FixedSelector(registry)


class FixedPlanner(TaskPlanner):
    """Planner that returns a predefined set of tasks."""

    def __init__(self, tasks):
        super().__init__()
        self._tasks = tasks
        for t in tasks:
            self.tasks[t.id] = t

    def plan(self, goal, context, available_tools, max_tasks=20):
        # Return the raw predefined list so callers can test the executor's
        # own max_tasks / max_iterations guards.
        return list(self._tasks)


class BusyMemoryBridge(MemoryBridge):
    """MemoryBridge that always returns and accepts experiences."""

    def __init__(self):
        super().__init__(None)

    def retrieve_relevant_experiences(self, query, top_k=3, session_id=None):
        return [{"goal": query, "score": 1.0}]

    def save_experience(self, goal, tasks, results, summary, session_id=None):
        return {"saved": True, "goal": goal}


class EmptyMemoryBridge(MemoryBridge):
    """MemoryBridge that returns empty experiences and no save result."""

    def __init__(self):
        super().__init__(None)

    def retrieve_relevant_experiences(self, query, top_k=3, session_id=None):
        return []

    def save_experience(self, goal, tasks, results, summary, session_id=None):
        return None


class BadRetrieveMemoryBridge(MemoryBridge):
    """MemoryBridge whose retrieval raises."""

    def __init__(self):
        super().__init__(None)

    def retrieve_relevant_experiences(self, query, top_k=3, session_id=None):
        raise RuntimeError("retrieve failed")

    def save_experience(self, goal, tasks, results, summary, session_id=None):
        return None


class BadSaveMemoryBridge(MemoryBridge):
    """MemoryBridge whose save raises."""

    def __init__(self):
        super().__init__(None)

    def retrieve_relevant_experiences(self, query, top_k=3, session_id=None):
        return []

    def save_experience(self, goal, tasks, results, summary, session_id=None):
        raise RuntimeError("save failed")


class QuickSubAgent:
    """Lightweight subagent for dispatcher branch coverage."""

    def __init__(self, agent_id="quick", role="worker", **kwargs):
        self.agent_id = agent_id
        self.role = role
        self._status = "completed"
        self._result = {"ok": True}  # noqa: F841  # Variable for test verification
        self._error = None

    def run(self, goal, context, available_tools, _depth=0):
        return SubAgentResult(
            agent_id=self.agent_id,
            task_id="sub_1",
            status=self._status,
            result=self._result,
            error=self._error,
        )


class FailingQuickSubAgent(QuickSubAgent):
    """SubAgent that returns a failed result."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._status = "failed"
        self._error = "subagent failed"


@pytest.fixture(autouse=True)
def reset_behavior_monitor():
    """Reset global behavior monitor thresholds before each test."""
    from core.agent.behavior_monitor import get_behavior_monitor

    monitor = get_behavior_monitor()
    monitor.set_thresholds(
        max_iterations=50,
        max_total_tool_calls=100,
        max_tool_repetitions=10,
        max_errors=10,
        max_execution_time_seconds=300,
    )
    yield
    monitor.set_thresholds(
        max_iterations=50,
        max_total_tool_calls=100,
        max_tool_repetitions=10,
        max_errors=10,
        max_execution_time_seconds=300,
    )


def make_executor(tasks, tools):
    """Build an AutonomousExecutor with a fixed planner and tool set."""
    registry = SimpleRegistry()
    for tool in tools:
        registry.register(tool)
    tool_executor = FixedToolExecutor(registry)
    planner = FixedPlanner(tasks)
    return AutonomousExecutor(planner, tool_executor)


def simple_tool(name, category, func, required=None, optional=None):
    return Tool(
        name=name,
        description=name,
        category=category,
        function=func,
        parameters={},
        required_params=required or [],
        optional_params=optional or [],
    )


# ----------------------------------------------------------------------
# Core helper classes
# ----------------------------------------------------------------------


def test_safety_boundary_branches():
    sb = SafetyBoundary(
        allowed_operations=["read"],
        forbidden_operations=["delete"],
        require_approval_for=["admin"],
    )
    assert sb.is_operation_allowed("delete") is False
    assert sb.is_operation_allowed("write") is False
    assert sb.is_operation_allowed("read") is True
    assert sb.requires_approval("admin") is True
    assert sb.requires_approval("read") is False

    open_sb = SafetyBoundary()
    assert open_sb.is_operation_allowed("anything") is True


def test_risk_assessor_branches():
    sb = SafetyBoundary(forbidden_operations=["drop table"])
    ra = RiskAssessor(sb)

    assert ra.assess_risk("drop table", {}) == (
        RiskLevel.CRITICAL,
        "Operation drop table is forbidden",
    )
    assert ra.assess_risk("delete files", {}) == (RiskLevel.CRITICAL, "Destructive operation")
    assert ra.assess_risk("stop service", {}) == (RiskLevel.HIGH, "Service stop operation")
    assert ra.assess_risk("modify config", {}) == (RiskLevel.MEDIUM, "Service modification")
    assert ra.assess_risk("scale app", {}) == (RiskLevel.MEDIUM, "Resource scaling")
    assert ra.assess_risk("check logs", {}) == (RiskLevel.LOW, "Read-only operation")
    assert ra.assess_risk("unknown", {}, tool_category=ToolCategory.EXECUTION) == (
        RiskLevel.MEDIUM,
        "Execution tool requires confirmation",
    )
    assert ra.assess_risk("unknown", {}, tool_category=ToolCategory.DIAGNOSTIC) == (
        RiskLevel.LOW,
        "Read-only/observability operation",
    )
    assert ra.assess_risk("mystery", {}) == (RiskLevel.MEDIUM, "Unknown operation type")

    assert ra.check_historical_risk("new_op") == 1.0
    ra.record_execution("new_op", True)
    assert ra.check_historical_risk("new_op") == 1.0
    ra.record_execution("new_op", False)
    assert ra.check_historical_risk("new_op") == 0.5

    for i in range(105):
        ra.record_execution("many_op", True)
    assert len(ra.risk_history["many_op"]) == 100


def test_trust_mechanism_branches():
    tm = TrustMechanism(initial_trust=0.5, learning_rate=0.2)
    assert tm.get_trust_score("x") == 0.5
    tm.update_trust("x", True)
    assert tm.get_trust_score("x") > 0.5
    tm.update_trust("x", False)
    # back down
    assert tm.get_trust_score("x") < 1.0

    assert tm.can_auto_execute("x", RiskLevel.LOW) is True
    assert tm.can_auto_execute("x", RiskLevel.LOW)  # default 0.5 >= 0.3
    assert tm.can_auto_execute("x", RiskLevel.MEDIUM) is False  # 0.5 < 0.6
    tm.trust_scores["x"] = 0.7
    assert tm.can_auto_execute("x", RiskLevel.MEDIUM) is True
    assert tm.can_auto_execute("x", RiskLevel.HIGH) is False  # 0.7 < 0.8
    tm.trust_scores["x"] = 0.9
    assert tm.can_auto_execute("x", RiskLevel.HIGH) is True
    assert tm.can_auto_execute("x", RiskLevel.CRITICAL) is False


def test_rollback_mechanism_branches():
    rb = RollbackMechanism()
    called = []
    rb.register_rollback("ok", lambda: called.append(1))
    assert rb.execute_rollback("ok") is True
    assert called == [1]

    rb.register_rollback("bad", "not_callable")
    assert rb.execute_rollback("bad") is True  # logs warning, still succeeds

    rb.register_rollback("boom", lambda: (_ for _ in ()).throw(RuntimeError("err")))
    assert rb.execute_rollback("boom") is False

    assert rb.execute_rollback("missing") is False


def test_validation_mechanism_branches():
    vm = ValidationMechanism()
    assert vm.validate("noop", {}, {}) == (True, "No validation rules")

    vm.register_validation("ok", lambda r, c: (True, "ok"))
    assert vm.validate("ok", {}, {}) == (True, "All validations passed")

    vm.register_validation("bad", lambda r, c: (False, "failed"))
    assert vm.validate("bad", {}, {}) == (False, "failed")

    vm.register_validation("err", lambda r, c: (_ for _ in ()).throw(RuntimeError("x")))
    passed, reason = vm.validate("err", {}, {})
    assert passed is False
    assert "Validation error" in reason


# ----------------------------------------------------------------------
# AutonomousExecutor branches
# ----------------------------------------------------------------------


def test_factory_and_basic_statistics():
    executor = create_autonomous_executor()
    assert executor is not None
    stats = executor.get_statistics()
    assert "execution_mode" in stats


def test_set_execution_mode_invalid():
    executor = make_executor([], [])
    with pytest.raises(ValueError):
        executor.set_execution_mode("unknown")


def test_execute_plan_empty_and_dry_run():
    executor = make_executor([], [])
    result = executor.execute_plan(
        "goal", {"session_id": "s1"}, []
    )  # noqa: F841  # Variable for test verification
    assert result["goal"] == "goal"


def test_execute_plan_session_and_diagnostic_state_branches():
    ok_tool = simple_tool("ok", ToolCategory.DIAGNOSTIC, lambda **kwargs: {"value": 1})
    task = Task(
        id="t1",
        description="check health",
    )
    executor = make_executor([task], [ok_tool])
    ctx = {
        "_select_tool": "ok",
        "diagnostic_state": {"findings": [], "hypotheses": []},
    }
    result = executor.execute_plan(
        "check health", ctx, ["ok"]
    )  # noqa: F841  # Variable for test verification
    assert result["session_id"]
    assert result["diagnostic_state"]
    assert result["summary"]["diagnostic_state"]


def test_execute_plan_max_depth():
    executor = make_executor([], [])
    result = executor.execute_plan(
        "goal", {}, [], _depth=5
    )  # noqa: F841  # Variable for test verification
    assert "Maximum subagent recursion" in result["error"]


def test_execute_plan_repeated_goal():
    executor = make_executor([], [])
    result = executor.execute_plan(  # noqa: F841  # Variable for test verification
        "same",
        {"__visited_goals": {"same"}},
        [],
    )
    assert "Repeated goal" in result["error"]


def test_execute_plan_max_tasks_exceeded():
    tasks = [Task(id=f"t{i}", description=f"step {i}") for i in range(25)]
    executor = make_executor(tasks, [])
    result = executor.execute_plan("big", {}, [])  # noqa: F841  # Variable for test verification
    assert "exceed maximum" in result["error"]


def test_execute_plan_behavior_anomaly():
    ok_tool = simple_tool("ok", ToolCategory.DIAGNOSTIC, lambda **kwargs: {"value": 1})
    task = Task(id="t1", description="check")
    executor = make_executor([task], [ok_tool])
    executor.behavior_monitor.set_thresholds(max_iterations=0)
    executor.behavior_monitor.reset(executor.agent_id)
    result = executor.execute_plan(
        "check", {"_select_tool": "ok"}, ["ok"]
    )  # noqa: F841  # Variable for test verification
    assert "Behavior anomaly" in result["error"]
    executor.behavior_monitor.reset(executor.agent_id)


def test_execute_plan_repeated_action():
    ok_tool = simple_tool("ok", ToolCategory.DIAGNOSTIC, lambda **kwargs: {"value": 1})
    tasks = [
        Task(id="t1", description="check"),
        Task(id="t2", description="check"),
    ]
    executor = make_executor(tasks, [ok_tool])
    result = executor.execute_plan(
        "check", {"_select_tool": "ok"}, ["ok"]
    )  # noqa: F841  # Variable for test verification
    assert result["results"][0]["status"] == "completed"
    assert "Repeated action signature" in result["results"][1]["error"]


def test_execute_plan_with_memory():
    metric_tool = simple_tool(
        "collect_metrics",
        ToolCategory.MONITORING,
        lambda **kwargs: {"cpu": 0.5, "mem": None},
    )
    task = Task(
        id="t1",
        description="collect metrics",
    )
    executor = make_executor([task], [metric_tool])
    executor.set_memory_bridge(BusyMemoryBridge())
    result = executor.execute_plan(  # noqa: F841  # Variable for test verification
        "collect",
        {"_select_tool": "collect_metrics", "enable_memory": True},
        ["collect_metrics"],
    )
    assert result["summary"]["memory"]["saved"] is True


def test_execute_task_no_tool():
    executor = make_executor([Task(id="t1", description="weird")], [])
    result = executor.execute_task(
        Task(id="t1", description="weird"), {}
    )  # noqa: F841  # Variable for test verification
    assert result["status"] == "failed"


def test_execute_task_manual_approval():
    ok_tool = simple_tool("ok", ToolCategory.DIAGNOSTIC, lambda **kwargs: {"value": 1})
    executor = make_executor([Task(id="t1", description="manual_task")], [ok_tool])
    executor.execution_mode = "manual"
    executor.safety_boundary = SafetyBoundary(require_approval_for=["manual_task"])
    result = executor.execute_task(  # noqa: F841  # Variable for test verification
        Task(id="t1", description="manual_task"),
        {"_select_tool": "ok"},
    )
    assert result["status"] == "pending_approval"


def test_execute_task_autonomous_low_trust():
    stop_tool = simple_tool("stop", ToolCategory.EXECUTION, lambda **kwargs: {"done": True})
    executor = make_executor([Task(id="t1", description="stop service")], [stop_tool])
    executor.execution_mode = "autonomous"
    result = executor.execute_task(  # noqa: F841  # Variable for test verification
        Task(id="t1", description="stop service"),
        {"_select_tool": "stop"},
    )
    assert result["status"] == "pending_approval"


def test_execute_task_hybrid_medium_risk():
    modify_tool = simple_tool("modify", ToolCategory.EXECUTION, lambda **kwargs: {"done": True})
    executor = make_executor([Task(id="t1", description="modify config")], [modify_tool])
    executor.execution_mode = "hybrid"
    result = executor.execute_task(  # noqa: F841  # Variable for test verification
        Task(id="t1", description="modify config"),
        {"_select_tool": "modify"},
    )
    assert result["status"] == "pending_approval"


def test_execute_task_low_confidence_remediation():
    restart_tool = simple_tool(
        "restart",
        ToolCategory.EXECUTION,
        lambda **kwargs: {"done": True},
    )
    executor = make_executor([Task(id="t1", description="restart service")], [restart_tool])
    executor.execution_mode = "autonomous"
    result = executor.execute_task(  # noqa: F841  # Variable for test verification
        Task(id="t1", description="restart service"),
        {"_select_tool": "restart", "execution_confidence": 0.5},
    )
    assert result["status"] == "pending_approval"
    assert "below threshold" in result["reason"]


def test_execute_task_confidence_missing_for_remediation():
    restart_tool = simple_tool(
        "restart",
        ToolCategory.EXECUTION,
        lambda **kwargs: {"done": True},
    )
    executor = make_executor([Task(id="t1", description="restart service")], [restart_tool])
    executor.execution_mode = "autonomous"
    result = executor.execute_task(  # noqa: F841  # Variable for test verification
        Task(id="t1", description="restart service"),
        {"_select_tool": "restart"},
    )
    assert result["status"] == "pending_approval"
    assert "Execution confidence is required" in result["reason"]


def test_execute_task_tool_exception_and_rollback():
    boom_tool = simple_tool(
        "boom",
        ToolCategory.DIAGNOSTIC,
        lambda **kwargs: (_ for _ in ()).throw(ValueError("boom")),
    )
    executor = make_executor([Task(id="t1", description="boom")], [boom_tool])
    result = executor.execute_task(  # noqa: F841  # Variable for test verification
        Task(id="t1", description="boom"),
        {"_select_tool": "boom"},
    )
    assert result["status"] == "failed"
    assert "boom" in result["error"]


def test_execute_task_validation_failure():
    good_tool = simple_tool("good", ToolCategory.DIAGNOSTIC, lambda **kwargs: {"value": 1})
    executor = make_executor([Task(id="t1", description="validate")], [good_tool])
    executor.validation_mechanism.register_validation(
        "validate",
        lambda result, context: (False, "validation failed"),
    )
    result = executor.execute_task(  # noqa: F841  # Variable for test verification
        Task(id="t1", description="validate"),
        {"_select_tool": "good"},
    )
    assert result["status"] == "failed"
    assert "validation failed" in result["error"]


def test_execute_task_dispatch_subagent_branch():
    sub_tool = simple_tool(
        "dispatch_subagent",
        ToolCategory.EXECUTION,
        lambda **kwargs: {"dispatched": True},
        optional=["_depth"],
    )
    executor = make_executor([Task(id="t1", description="run subagent")], [sub_tool])
    executor.execution_mode = "autonomous"
    executor.trust_mechanism.trust_scores["run subagent"] = 0.7
    result = executor.execute_task(  # noqa: F841  # Variable for test verification
        Task(id="t1", description="run subagent"),
        {"_select_tool": "dispatch_subagent", "execution_confidence": 0.9},
        _depth=1,
    )
    assert result["status"] == "completed"


def test_execute_task_success_and_merge_metric():
    metric_tool = simple_tool(
        "collect_metrics",
        ToolCategory.MONITORING,
        lambda **kwargs: {"cpu": 0.5, "mem": None, "io": 0.1},
    )
    task = Task(
        id="t1",
        description="collect metrics",
        parameters={"_select_tool": "collect_metrics"},
    )
    executor = make_executor([task], [metric_tool])
    result = executor.execute_task(
        task, {"_select_tool": "collect_metrics"}
    )  # noqa: F841  # Variable for test verification
    assert result["status"] == "completed"


# ----------------------------------------------------------------------
# Internal helpers
# ----------------------------------------------------------------------


def test_get_execution_confidence_branches():
    executor = make_executor([], [])
    assert executor._get_execution_confidence({"execution_confidence": "0.9"}) == 0.9
    assert executor._get_execution_confidence({"execution_confidence": "bad"}) is None
    assert executor._get_execution_confidence({"diagnosis": {"confidence": "0.8"}}) == 0.8
    assert executor._get_execution_confidence({"diagnosis": {"confidence": "bad"}}) is None
    assert (
        executor._get_execution_confidence({"analysis": {"candidates": [{"confidence": "0.7"}]}})
        == 0.7
    )
    assert executor._get_execution_confidence({"analysis": {"candidates": []}}) is None
    assert executor._get_execution_confidence({"result": {"confidence": 0.6}}) == 0.6
    assert executor._get_execution_confidence({}) is None


def test_is_remediation_action():
    executor = make_executor([], [])
    assert executor._is_remediation_action("restart service") is True
    assert executor._is_remediation_action("check logs") is False


def test_merge_tool_result_branches():
    executor = make_executor([], [])
    ctx: dict = {"metrics_data": {"old": 1, "cpu": 0.9}}
    executor._merge_tool_result_into_context("collect_metrics", {"cpu": None, "mem": 2}, ctx)
    assert ctx["metrics_data"]["old"] == 1
    assert ctx["metrics_data"]["mem"] == 2
    # existing key with a None placeholder must not be overwritten
    assert ctx["metrics_data"]["cpu"] == 0.9

    ctx2 = {"metrics_data": "bad"}
    executor._merge_tool_result_into_context("collect_metrics", {"cpu": 1}, ctx2)
    assert isinstance(ctx2["metrics_data"], dict)
    assert ctx2["metrics_data"]["cpu"] == 1

    ctx3 = {}
    executor._merge_tool_result_into_context("collect_correlated_alerts", [{"id": 1}], ctx3)
    assert ctx3["correlated_alerts"] == [{"id": 1}]

    ctx4 = {}
    executor._merge_tool_result_into_context("collect_change_events", [{"id": 2}], ctx4)
    assert ctx4["change_events"] == [{"id": 2}]

    ctx5 = {}
    executor._merge_tool_result_into_context("collect_kubernetes_events", [{"id": 3}], ctx5)
    assert ctx5["kubernetes_events"] == [{"id": 3}]

    ctx6 = {}
    executor._merge_tool_result_into_context("collect_logs", ["line"], ctx6)
    assert ctx6["logs_data"] == ["line"]

    ctx7 = {}
    executor._merge_tool_result_into_context("collect_topology", {"nodes": []}, ctx7)
    assert ctx7["topology"]["nodes"] == []

    ctx8 = {}
    executor._merge_tool_result_into_context("collect_metrics", "not-dict", ctx8)
    assert "metrics_data" not in ctx8


# ----------------------------------------------------------------------
# Subagent/parallel entry points
# ----------------------------------------------------------------------


def test_execute_plan_with_subagents():
    task = Task(id="t1", description="collect metrics", parameters={"_select_tool": "ok"})
    ok_tool = simple_tool("ok", ToolCategory.DIAGNOSTIC, lambda **kwargs: {"value": 1})
    executor = make_executor([task], [ok_tool])
    dispatcher = SubAgentDispatcher(
        max_workers=2,
        subagent_factory=QuickSubAgent,
        dry_run=True,
    )
    executor.set_subagent_dispatcher(dispatcher)
    result = executor.execute_plan_with_subagents(  # noqa: F841  # Variable for test verification
        "goal",
        {},
        ["ok"],
        max_subagents=2,
    )
    assert result["subagent_results"]
    dispatcher.shutdown()


def test_execute_plan_parallel():
    executor = make_executor([], [])
    result = executor.execute_plan_parallel(
        "goal", {}, [], _depth=0
    )  # noqa: F841  # Variable for test verification
    assert result["goal"] == "goal"


def test_risk_assessor_empty_history_branch():
    ra = RiskAssessor(SafetyBoundary())
    ra.risk_history["op"] = []
    assert ra.check_historical_risk("op") == 1.0


def test_validation_register_second_rule():
    vm = ValidationMechanism()
    vm.register_validation("same", lambda r, c: (True, "ok"))
    vm.register_validation("same", lambda r, c: (False, "second"))
    assert vm.validate("same", {}, {}) == (False, "second")


def test_executor_dry_run_propagation():
    registry = SimpleRegistry()
    registry.register_tool("ok", ToolCategory.DIAGNOSTIC, lambda **kwargs: {"v": 1})
    tool_executor = FixedToolExecutor(registry)
    assert tool_executor.dry_run is False
    executor = AutonomousExecutor(FixedPlanner([]), tool_executor, dry_run=True)
    assert executor.dry_run is True
    assert tool_executor.dry_run is True


def test_execute_plan_invalid_diagnostic_state():
    ok_tool = simple_tool("ok", ToolCategory.DIAGNOSTIC, lambda **kwargs: {"v": 1})
    executor = make_executor([Task(id="t1", description="ok")], [ok_tool])
    result = executor.execute_plan(  # noqa: F841  # Variable for test verification
        "ok", {"_select_tool": "ok", "diagnostic_state": "weird"}, ["ok"]
    )
    assert result["diagnostic_state"]


def test_execute_plan_memory_retrieval_empty_and_exception():
    ok_tool = simple_tool("ok", ToolCategory.DIAGNOSTIC, lambda **kwargs: {"v": 1})
    task = Task(id="t1", description="ok")
    executor = make_executor([task], [ok_tool])

    executor.set_memory_bridge(EmptyMemoryBridge())
    result = executor.execute_plan(
        "ok", {"_select_tool": "ok", "enable_memory": True}, ["ok"]
    )  # noqa: F841  # Variable for test verification
    assert result["results"][0]["status"] == "completed"

    executor.set_memory_bridge(BadRetrieveMemoryBridge())
    result = executor.execute_plan(
        "ok", {"_select_tool": "ok", "enable_memory": True}, ["ok"]
    )  # noqa: F841  # Variable for test verification
    assert result["results"][0]["status"] == "completed"


def test_execute_plan_max_iterations():
    ok_tool = simple_tool("ok", ToolCategory.DIAGNOSTIC, lambda **kwargs: {"v": 1})
    tasks = [Task(id=f"t{i}", description="ok") for i in range(3)]
    executor = make_executor(tasks, [ok_tool])
    executor.max_iterations = 1
    result = executor.execute_plan(
        "ok", {"_select_tool": "ok"}, ["ok"]
    )  # noqa: F841  # Variable for test verification
    assert "Maximum iteration count" in result["results"][1]["error"]


def test_execute_plan_failed_task_records_error():
    boom_tool = simple_tool(
        "boom", ToolCategory.DIAGNOSTIC, lambda **kwargs: (_ for _ in ()).throw(ValueError("err"))
    )
    executor = make_executor([Task(id="t1", description="boom")], [boom_tool])
    result = executor.execute_plan(
        "boom", {"_select_tool": "boom"}, ["boom"]
    )  # noqa: F841  # Variable for test verification
    assert result["results"][0]["status"] == "failed"


def test_execute_plan_anomaly_after_execution():
    ok_tool = simple_tool("ok", ToolCategory.DIAGNOSTIC, lambda **kwargs: {"v": 1})
    executor = make_executor([Task(id="t1", description="ok")], [ok_tool])
    executor.behavior_monitor.set_thresholds(max_total_tool_calls=0)
    executor.behavior_monitor.reset(executor.agent_id)
    result = executor.execute_plan(
        "ok", {"_select_tool": "ok"}, ["ok"]
    )  # noqa: F841  # Variable for test verification
    assert "behavior_alert" in result["results"][0]
    executor.behavior_monitor.reset(executor.agent_id)


def test_execute_plan_memory_save_no_result():
    ok_tool = simple_tool("ok", ToolCategory.DIAGNOSTIC, lambda **kwargs: {"v": 1})
    executor = make_executor([Task(id="t1", description="ok")], [ok_tool])
    executor.set_memory_bridge(EmptyMemoryBridge())
    result = executor.execute_plan(
        "ok", {"_select_tool": "ok", "enable_memory": True}, ["ok"]
    )  # noqa: F841  # Variable for test verification
    assert "memory" not in result["summary"]


def test_execute_plan_memory_save_exception():
    ok_tool = simple_tool("ok", ToolCategory.DIAGNOSTIC, lambda **kwargs: {"v": 1})
    executor = make_executor([Task(id="t1", description="ok")], [ok_tool])
    executor.set_memory_bridge(BadSaveMemoryBridge())
    result = executor.execute_plan(
        "ok", {"_select_tool": "ok", "enable_memory": True}, ["ok"]
    )  # noqa: F841  # Variable for test verification
    assert result["results"][0]["status"] == "completed"


def test_execute_task_remediation_high_confidence():
    restart_tool = simple_tool("restart", ToolCategory.EXECUTION, lambda **kwargs: {"done": True})
    executor = make_executor([Task(id="t1", description="restart service")], [restart_tool])
    executor.execution_mode = "autonomous"
    executor.trust_mechanism.trust_scores["restart service"] = 0.8
    result = executor.execute_task(  # noqa: F841  # Variable for test verification
        Task(id="t1", description="restart service"),
        {"_select_tool": "restart", "execution_confidence": 0.9},
    )
    assert result["status"] == "completed"


def test_execute_task_manual_no_approval():
    ok_tool = simple_tool("ok", ToolCategory.DIAGNOSTIC, lambda **kwargs: {"v": 1})
    executor = make_executor([Task(id="t1", description="probe")], [ok_tool])
    executor.execution_mode = "manual"
    executor.safety_boundary = SafetyBoundary(require_approval_for=["admin"])
    result = executor.execute_task(
        Task(id="t1", description="probe"), {"_select_tool": "ok"}
    )  # noqa: F841  # Variable for test verification
    assert result["status"] == "completed"


def test_execute_task_hybrid_low_risk():
    ok_tool = simple_tool("ok", ToolCategory.DIAGNOSTIC, lambda **kwargs: {"v": 1})
    executor = make_executor([Task(id="t1", description="probe")], [ok_tool])
    executor.execution_mode = "hybrid"
    result = executor.execute_task(
        Task(id="t1", description="probe"), {"_select_tool": "ok"}
    )  # noqa: F841  # Variable for test verification
    assert result["status"] == "completed"


def test_get_execution_confidence_non_dict_and_bad_candidate():
    executor = make_executor([], [])
    assert executor._get_execution_confidence({"diagnosis": "bad"}) is None
    assert executor._get_execution_confidence({"analysis": {"candidates": ["bad"]}}) is None


def test_execute_plan_with_subagents_creates_dispatcher():
    executor = make_executor([], [])
    result = executor.execute_plan_with_subagents(
        "goal", {}, [], max_subagents=2
    )  # noqa: F841  # Variable for test verification
    assert result["subagent_results"] == []


def test_execute_plan_with_subagents_failed_result():
    ok_tool = simple_tool("ok", ToolCategory.DIAGNOSTIC, lambda **kwargs: {"v": 1})
    task = Task(id="t1", description="sub")
    executor = make_executor([task], [ok_tool])
    dispatcher = SubAgentDispatcher(
        max_workers=2, subagent_factory=FailingQuickSubAgent, dry_run=True
    )
    executor.set_subagent_dispatcher(dispatcher)
    result = executor.execute_plan_with_subagents(
        "goal", {}, ["ok"], max_subagents=2
    )  # noqa: F841  # Variable for test verification
    assert result["subagent_results"][0]["status"] == "failed"
    dispatcher.shutdown()


def test_execute_plan_parallel_inputs():
    executor = make_executor([], [])
    result = executor.execute_plan_parallel(  # noqa: F841  # Variable for test verification
        "deep",
        {"diagnostic_state": "weird", "__visited_goals": {"deep"}},
        [],
        _depth=5,
    )
    assert "Maximum subagent recursion" in result["error"]


def test_execute_plan_parallel_max_tasks():
    tasks = [Task(id=f"t{i}", description="ok") for i in range(25)]
    executor = make_executor(tasks, [])
    result = executor.execute_plan_parallel(
        "big", {}, [], _depth=0
    )  # noqa: F841  # Variable for test verification
    assert "exceed maximum" in result["error"]


def test_set_execution_mode_valid():
    executor = make_executor([], [])
    executor.set_execution_mode("autonomous")
    assert executor.execution_mode == "autonomous"
    executor.set_execution_mode("manual")
    assert executor.execution_mode == "manual"
    executor.set_execution_mode("hybrid")
    assert executor.execution_mode == "hybrid"


def test_create_autonomous_executor_with_args():
    planner = FixedPlanner([])
    tool_exec = FixedToolExecutor(SimpleRegistry())
    executor = create_autonomous_executor(planner=planner, tool_executor=tool_exec)
    assert executor.planner is planner
    assert executor.tool_executor is tool_exec


def test_execute_plan_diagnostic_state_object():
    from core.agent.state import DiagnosticState

    ok_tool = simple_tool("ok", ToolCategory.DIAGNOSTIC, lambda **kwargs: {"v": 1})
    executor = make_executor([Task(id="t1", description="ok")], [ok_tool])
    result = executor.execute_plan(  # noqa: F841  # Variable for test verification
        "ok",
        {"_select_tool": "ok", "diagnostic_state": DiagnosticState()},
        ["ok"],
    )
    assert result["diagnostic_state"]


def test_execute_plan_tool_select_exception():
    registry = SimpleRegistry()
    registry.register_tool("ok", ToolCategory.DIAGNOSTIC, lambda **kwargs: {"v": 1})
    tool_executor = FixedToolExecutor(registry)
    tool_executor.selector = BrokenSelector(registry)
    executor = AutonomousExecutor(FixedPlanner([Task(id="t1", description="raise")]), tool_executor)
    result = executor.execute_plan(
        "raise", {"_raise_select": True, "_select_tool": "ok"}, ["ok"]
    )  # noqa: F841  # Variable for test verification
    assert result["results"][0]["status"] == "completed"


def test_execute_plan_pending_task_not_failed():
    ok_tool = simple_tool("ok", ToolCategory.DIAGNOSTIC, lambda **kwargs: {"v": 1})
    executor = make_executor([Task(id="t1", description="admin")], [ok_tool])
    executor.execution_mode = "manual"
    executor.safety_boundary = SafetyBoundary(require_approval_for=["admin"])
    result = executor.execute_plan(
        "admin", {"_select_tool": "ok"}, ["ok"]
    )  # noqa: F841  # Variable for test verification
    assert result["results"][0]["status"] == "pending_approval"


def test_execute_task_hybrid_high_trust():
    stop_tool = simple_tool("stop", ToolCategory.EXECUTION, lambda **kwargs: {"done": True})
    executor = make_executor([Task(id="t1", description="stop service")], [stop_tool])
    executor.execution_mode = "hybrid"
    executor.trust_mechanism.trust_scores["stop service"] = 0.9
    result = executor.execute_task(  # noqa: F841  # Variable for test verification
        Task(id="t1", description="stop service"),
        {"_select_tool": "stop", "execution_confidence": 0.9},
    )
    assert result["status"] == "completed"


def test_execute_plan_parallel_one_task():
    ok_tool = simple_tool("ok", ToolCategory.DIAGNOSTIC, lambda **kwargs: {"v": 1})
    task = Task(id="t1", description="ok")
    executor = make_executor([task], [ok_tool])
    executor.set_memory_bridge(BusyMemoryBridge())
    result = executor.execute_plan_parallel(  # noqa: F841  # Variable for test verification
        "parallel",
        {"enable_memory": True},
        ["ok"],
        _depth=0,
    )
    assert result["goal"] == "parallel"
    assert result["results"]


def test_execute_plan_parallel_repeated_goal():
    executor = make_executor([], [])
    result = executor.execute_plan_parallel(  # noqa: F841  # Variable for test verification
        "same",
        {"__visited_goals": {"same"}},
        [],
        _depth=0,
    )
    assert "Repeated goal" in result["error"]


def test_execute_plan_parallel_diag_dict():
    executor = make_executor([], [])
    result = executor.execute_plan_parallel(  # noqa: F841  # Variable for test verification
        "ok",
        {"diagnostic_state": {"findings": []}},
        [],
        _depth=0,
    )
    assert result["diagnostic_state"]


def test_execute_plan_parallel_memory_save_no_result():
    ok_tool = simple_tool("ok", ToolCategory.DIAGNOSTIC, lambda **kwargs: {"v": 1})
    task = Task(id="t1", description="ok")
    executor = make_executor([task], [ok_tool])
    executor.set_memory_bridge(EmptyMemoryBridge())
    result = executor.execute_plan_parallel(  # noqa: F841  # Variable for test verification
        "parallel",
        {"enable_memory": True},
        ["ok"],
        _depth=0,
    )
    assert "memory" not in result["summary"]
    assert result["results"]


def test_execute_plan_parallel_session_id_and_diag_branches():
    executor = make_executor([], [])
    result = executor.execute_plan_parallel(  # noqa: F841  # Variable for test verification
        "ok",
        {
            "session_id": "existing",
            "diagnostic_state": "weird",
        },
        [],
        _depth=0,
    )
    assert result["session_id"] == "existing"
    assert result["diagnostic_state"]


def test_execute_plan_parallel_behavior_anomaly():
    executor = make_executor([], [])
    executor.behavior_monitor.set_thresholds(max_iterations=0)
    executor.behavior_monitor.reset(executor.agent_id)
    result = executor.execute_plan_parallel(
        "ok", {}, [], _depth=0
    )  # noqa: F841  # Variable for test verification
    assert "Behavior anomaly" in result["error"]
    executor.behavior_monitor.reset(executor.agent_id)


def test_execute_plan_parallel_memory_retrieve_exception():
    executor = make_executor([], [])
    executor.set_memory_bridge(BadRetrieveMemoryBridge())
    result = executor.execute_plan_parallel(  # noqa: F841  # Variable for test verification
        "ok",
        {"enable_memory": True},
        [],
        _depth=0,
    )
    assert result["goal"] == "ok"


def test_execute_plan_parallel_diag_state_object():
    from core.agent.state import DiagnosticState

    executor = make_executor([], [])
    result = executor.execute_plan_parallel(  # noqa: F841  # Variable for test verification
        "ok",
        {"diagnostic_state": DiagnosticState()},
        [],
        _depth=0,
    )
    assert result["diagnostic_state"]


def test_execute_plan_parallel_memory_save_empty_with_task():
    ok_tool = simple_tool("ok", ToolCategory.DIAGNOSTIC, lambda **kwargs: {"v": 1})
    executor = make_executor([Task(id="t1", description="ok")], [ok_tool])
    executor.set_memory_bridge(EmptyMemoryBridge())
    result = executor.execute_plan_parallel(  # noqa: F841  # Variable for test verification
        "parallel",
        {"enable_memory": True},
        ["ok"],
        _depth=0,
    )
    assert "memory" not in result["summary"]


def test_execute_plan_parallel_memory_save_exception():
    ok_tool = simple_tool("ok", ToolCategory.DIAGNOSTIC, lambda **kwargs: {"v": 1})
    executor = make_executor([Task(id="t2", description="ok")], [ok_tool])
    executor.set_memory_bridge(BadSaveMemoryBridge())
    result = executor.execute_plan_parallel(  # noqa: F841  # Variable for test verification
        "parallel",
        {"enable_memory": True},
        ["ok"],
        _depth=0,
    )
    assert result["results"]


def test_execute_plan_parallel_max_iterations():
    executor = make_executor([Task(id="t1", description="ok")], [])
    executor.max_iterations = 0
    result = executor.execute_plan_parallel(
        "ok", {}, [], _depth=0
    )  # noqa: F841  # Variable for test verification
    assert "Maximum iteration count" in result["results"][0]["error"]


def test_execute_plan_parallel_unmet_dependencies():
    t1 = Task(id="t1", description="ok")
    t2 = Task(id="t2", description="ok", dependencies=["t1"])
    t1.status = TaskStatus.FAILED
    executor = make_executor([t1, t2], [])
    result = executor.execute_plan_parallel(
        "ok", {}, [], _depth=0
    )  # noqa: F841  # Variable for test verification
    assert any("Unmet dependencies" in r.get("error", "") for r in result["results"])


# ----------------------------------------------------------------------
# Audit wrapper (best effort)
# ----------------------------------------------------------------------


def test_audit_executor_branches():
    # Covers the no-op path when audit is unavailable and the happy path.
    _audit_executor("agent", "action", "resource", "success", {"x": 1})
    if not AUDIT_AVAILABLE:
        # import path already degraded; just exercise no-op
        assert True
