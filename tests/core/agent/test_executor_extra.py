# -*- coding: utf-8 -*-
"""Additional coverage tests for core/agent/executor.py (AutonomousExecutor)."""

from unittest.mock import MagicMock

import pytest

from core.agent.behavior_monitor import BehaviorMonitor
from core.agent.executor import (
    AutonomousExecutor,
    SafetyBoundary,
    create_autonomous_executor,
)
from core.agent.planner import Task, TaskPlanner
from core.agent.tools import (
    Tool,
    ToolCategory,
    ToolExecutor,
    ToolRegistry,
)

pytestmark = [pytest.mark.core]


def _noop(**kwargs):
    return "ok"


def _make_planner(tasks):
    planner = TaskPlanner()
    planner.tasks = {t.id: t for t in tasks}

    def plan(*args, **kwargs):
        return list(tasks)

    planner.plan = plan
    return planner


def _make_tool_executor():
    registry = ToolRegistry(approval_required=False)
    registry.register(
        Tool(
            name="noop",
            description="noop",
            category=ToolCategory.ANALYSIS,
            function=_noop,
            required_params=[],
        )
    )
    executor = ToolExecutor(registry, dry_run=True)
    noop = registry.get_tool("noop")
    executor.selector.select_tool = lambda *args, **kwargs: noop
    return executor


def _make_executor(tasks, safety_boundary=None, monkeypatch=None):
    planner = _make_planner(tasks)
    tool_executor = _make_tool_executor()
    executor = AutonomousExecutor(
        planner,
        tool_executor,
        safety_boundary=safety_boundary or SafetyBoundary(),
    )
    executor.trust_mechanism.initial_trust = 0.95
    return executor


def test_autonomous_executor_execute_plan_and_get_statistics():
    tasks = [Task(id="t1", description="check health", parameters={"target": "localhost"})]
    executor = _make_executor(tasks)
    result = executor.execute_plan(
        "check health",
        {"execution_confidence": 0.9},
        ["noop"],
    )
    assert result["goal"] == "check health"
    assert len(result["results"]) == 1
    assert result["results"][0]["status"] == "completed"
    assert "session_id" in result
    assert "diagnostic_state" in result

    stats = executor.get_statistics()
    assert "execution_mode" in stats
    assert "trust_scores" in stats
    assert "risk_history" in stats
    assert "rollback_history" in stats


def test_autonomous_executor_validation_failure_and_rollback():
    tasks = [Task(id="t1", description="check health", parameters={"target": "localhost"})]
    executor = _make_executor(tasks)
    executor.validation_mechanism.register_validation(
        "check health",
        lambda result, ctx: (False, "validation failed"),
    )
    result = executor.execute_plan(
        "check health",
        {"execution_confidence": 0.9},
        ["noop"],
    )
    assert result["results"][0]["status"] == "failed"
    assert "validation failed" in result["results"][0]["error"]

    # Trust should decrease after a failed validation.
    assert executor.trust_mechanism.get_trust_score("check health") < 0.95
    # Risk history should record a failure.
    assert executor.risk_assessor.check_historical_risk("check health") == 0.0


def test_autonomous_executor_no_tool_found():
    tasks = [Task(id="t1", description="weird task", parameters={})]
    executor = _make_executor(tasks)
    executor.tool_executor.selector.select_tool = lambda *args, **kwargs: None
    result = executor.execute_plan("weird task", {}, ["noop"])
    assert result["results"][0]["status"] == "failed"
    assert "No tool found" in result["results"][0]["error"]


def test_autonomous_executor_manual_mode_pending_approval():
    tasks = [
        Task(
            id="t1",
            description="restart service",
            parameters={"service_name": "nginx"},
        )
    ]
    boundary = SafetyBoundary(require_approval_for=["restart service"])
    executor = _make_executor(tasks, safety_boundary=boundary)
    executor.set_execution_mode("manual")
    result = executor.execute_plan(
        "restart service",
        {"execution_confidence": 0.9},
        ["noop"],
    )
    assert result["results"][0]["status"] == "pending_approval"


def test_autonomous_executor_set_execution_mode_invalid():
    executor = _make_executor([])
    with pytest.raises(ValueError, match="Invalid execution mode"):
        executor.set_execution_mode("unknown")


def test_autonomous_executor_goal_loop_detection():
    tasks = [Task(id="t1", description="check health", parameters={"target": "localhost"})]
    executor = _make_executor(tasks)
    result = executor.execute_plan(
        "check health",
        {"__visited_goals": {"check health"}},
        ["noop"],
    )
    assert "Repeated goal detected" in result["error"]


def test_autonomous_executor_max_depth():
    tasks = [Task(id="t1", description="check health", parameters={})]
    executor = _make_executor(tasks)
    result = executor.execute_plan("check health", {}, ["noop"], _depth=10)
    assert "Maximum subagent recursion depth" in result["error"]


def test_autonomous_executor_max_tasks():
    tasks = [Task(id=f"t{i}", description=f"task {i}", parameters={}) for i in range(25)]
    executor = _make_executor(tasks)
    result = executor.execute_plan("many tasks", {}, ["noop"])
    assert "Planned tasks" in result["error"]


def test_autonomous_executor_max_iterations():
    tasks = [Task(id=f"t{i}", description=f"check health {i}", parameters={}) for i in range(60)]
    executor = _make_executor(tasks)
    executor.max_tasks = 100
    executor.max_iterations = 5
    result = executor.execute_plan("many iterations", {}, ["noop"])
    assert any("Maximum iteration count" in str(r.get("error", "")) for r in result["results"])


def test_autonomous_executor_memory_bridge():
    tasks = [Task(id="t1", description="check health", parameters={"target": "localhost"})]
    executor = _make_executor(tasks)
    bridge = MagicMock()
    bridge.retrieve_relevant_experiences.return_value = [{"experience": 1}]
    bridge.save_experience.return_value = {"memory_id": "m1"}
    executor.set_memory_bridge(bridge)

    result = executor.execute_plan(
        "check health",
        {"execution_confidence": 0.9},
        ["noop"],
    )
    bridge.retrieve_relevant_experiences.assert_called_once()
    bridge.save_experience.assert_called_once()
    assert result["summary"]["memory"] == {"memory_id": "m1"}


def test_autonomous_executor_behavior_anomaly(monkeypatch):
    monkeypatch.setattr(
        "core.agent.executor.get_behavior_monitor",
        lambda: BehaviorMonitor(),
    )
    tasks = [Task(id="t1", description="check health", parameters={"target": "localhost"})]
    executor = _make_executor(tasks, monkeypatch=monkeypatch)
    executor.behavior_monitor.set_thresholds(max_iterations=0)
    result = executor.execute_plan("check health", {}, ["noop"])
    assert "Behavior anomaly detected" in result["error"]


def test_create_autonomous_executor_factory():
    executor = create_autonomous_executor()
    assert executor.execution_mode == "hybrid"
    stats = executor.get_statistics()
    assert isinstance(stats, dict)
    assert "trust_scores" in stats
