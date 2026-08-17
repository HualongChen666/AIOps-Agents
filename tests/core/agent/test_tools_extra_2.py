# -*- coding: utf-8 -*-
"""Additional coverage tests for core/agent/tools.py (remaining branches)."""

import asyncio

import pytest

from core.agent.tools import (
    Tool,
    ToolApprovalManager,
    ToolCategory,
    ToolExecutor,
    ToolRegistry,
    ToolSelector,
    create_tool_executor,
    create_tool_registry,
)

pytestmark = [pytest.mark.core]


def _add(x, y):
    return x + y


async def _async_add(x, y):
    return x + y


def test_tool_execute_sync_and_async():
    sync_tool = Tool(
        name="add",
        description="add numbers",
        category=ToolCategory.ANALYSIS,
        function=_add,
        required_params=["x", "y"],
    )
    assert sync_tool.execute(x=2, y=3) == 5

    async_tool = Tool(
        name="async_add",
        description="async add",
        category=ToolCategory.ANALYSIS,
        function=_async_add,
        required_params=["x", "y"],
    )
    assert async_tool.execute(x=2, y=3) == 5


def test_tool_execute_invalid_timeout():
    tool = Tool(
        name="inc",
        description="increment",
        category=ToolCategory.ANALYSIS,
        function=lambda x: x,
        required_params=["x"],
        optional_params=["timeout"],
    )
    with pytest.raises(ValueError, match="Invalid timeout"):
        tool.execute(x=1, timeout="abc")


def test_tool_validate_parameters_varkw():
    def _fn(**kwargs):
        return kwargs

    tool = Tool(
        name="kw",
        description="var kwargs",
        category=ToolCategory.ANALYSIS,
        function=_fn,
        required_params=["x"],
    )
    # unknown params allowed because function accepts **kwargs
    tool._validate_parameters({"x": 1, "extra": 2, "another": 3})


def test_tool_validate_value_extended():
    def _fn(**kwargs):
        return kwargs

    tool = Tool(
        name="probe",
        description="probe",
        category=ToolCategory.DIAGNOSTIC,
        function=_fn,
        required_params=[],
        optional_params=[
            "threshold",
            "wait",
            "tools",
            "alert",
            "description",
            "service",
            "context",
        ],
    )
    # float within range
    tool._validate_value("threshold", 0.5)
    # boolean
    tool._validate_value("wait", True)
    # list-like as comma separated string
    tool._validate_value("tools", "a,b,c")
    # data container with command-like key (safe command)
    tool._validate_value("alert", {"command": "ls -la"})
    # arbitrary dict string values
    tool._validate_value("context", {"foo": "bar"})
    # empty allowed for text parameter
    tool._validate_value("description", "")
    # empty disallowed for name-pattern parameter
    with pytest.raises(ValueError, match="cannot be empty"):
        tool._validate_value("service", "")


def test_tool_clamp_time_range_hours():
    tool = Tool(
        name="range",
        description="range",
        category=ToolCategory.ANALYSIS,
        function=lambda time_range_hours: time_range_hours,
        required_params=["time_range_hours"],
    )
    # valid int range, then clamped to 24
    assert tool.execute(time_range_hours=50) == 24


def test_tool_registry_approval_edge_cases(monkeypatch):
    # default from explicit False
    reg = ToolRegistry(approval_required=False)
    assert reg.approval_manager.approval_required is False

    # auto-approve via approved_by
    reg2 = ToolRegistry(approval_required=True)
    reg2.register(
        Tool(
            name="auto",
            description="auto approved",
            category=ToolCategory.ANALYSIS,
            function=lambda: None,
        ),
        approved_by="admin",
    )
    assert reg2.get_tool("auto") is not None
    assert reg2.is_tool_approved("auto") is True

    # unregister non-existent does not raise
    reg2.unregister("missing")

    # revoking approval
    mgr = ToolApprovalManager(approval_required=True)
    mgr.approve("x", "admin")
    assert mgr.is_approved("x") is True
    mgr.revoke("x")
    assert mgr.is_approved("x") is False
    mgr.revoke("x")  # idempotent


def test_tool_selector_select_tool_branches():
    registry = create_tool_registry()
    selector = ToolSelector(registry)
    cases = [
        ("collect system metrics", "collect_metrics"),
        ("detect anomaly in data", "analyze_anomaly"),
        ("root cause analysis", "root_cause_analysis"),
        ("scale api service", "scale_service"),
        ("recent changes for host", "collect_change_events"),
        ("related alerts for api", "collect_correlated_alerts"),
        ("sli for api", "collect_service_metrics"),
        ("network packet loss to gateway", "collect_network_metrics"),
        ("database slow query", "collect_database_metrics"),
        ("kubernetes pod OOMKilled", "collect_kubernetes_events"),
        ("health check target", "check_health"),
        ("do something weird", None),
    ]
    for task, expected in cases:
        selected = selector.select_tool(task, {})
        if expected is None:
            assert selected is None, f"task={task!r}"
        else:
            assert selected is not None, f"task={task!r}"
            assert selected.name == expected, f"task={task!r}"


def test_tool_executor_retry_success(monkeypatch):
    monkeypatch.setattr("core.agent.tools.time.sleep", lambda x: None)
    calls = []

    def flaky():
        calls.append(1)
        if len(calls) < 2:
            raise asyncio.TimeoutError("to")
        return "ok"

    registry = ToolRegistry(approval_required=False)
    registry.register(
        Tool(
            name="flaky",
            description="flaky",
            category=ToolCategory.MONITORING,
            function=flaky,
        )
    )
    executor = ToolExecutor(registry)
    result = executor.execute_tool("flaky")
    assert result == "ok"
    assert len(calls) == 2


def test_tool_executor_should_retry():
    registry = ToolRegistry(approval_required=False)
    executor = ToolExecutor(registry)
    tool = Tool(
        name="monitor",
        description="monitor",
        category=ToolCategory.MONITORING,
        function=lambda: None,
    )
    assert executor._should_retry(tool, asyncio.TimeoutError()) is True
    assert executor._should_retry(tool, OSError()) is True
    exec_tool = Tool(
        name="exec",
        description="exec",
        category=ToolCategory.EXECUTION,
        function=lambda: None,
    )
    assert executor._should_retry(exec_tool, asyncio.TimeoutError()) is False


def test_tool_executor_execute_chain_breaks_on_failure():
    def ok_fn():
        return "ok"

    def bad_fn():
        raise ValueError("boom")

    registry = ToolRegistry(approval_required=False)
    registry.register(
        Tool(name="ok", description="ok", category=ToolCategory.ANALYSIS, function=ok_fn)
    )
    registry.register(
        Tool(name="bad", description="bad", category=ToolCategory.ANALYSIS, function=bad_fn)
    )
    executor = ToolExecutor(registry)
    results = executor.execute_chain([("ok", {}), ("bad", {}), ("ok", {})])
    assert results == ["ok"]
    stats = executor.get_execution_statistics()
    assert stats["failed"] == 1
    assert stats["successful"] == 1


def test_tool_executor_auto_selection_no_match():
    executor = ToolExecutor(create_tool_registry(), dry_run=True)
    with pytest.raises(ValueError, match="No tool found"):
        executor.execute_with_auto_selection("do something weird", {})


def test_tool_executor_infer_parameters():
    executor = create_tool_executor()

    metrics_tool = executor.registry.get_tool("collect_metrics")
    params = executor._infer_parameters(
        metrics_tool, {"target": "host1", "duration": 15, "extra": "ignored"}
    )
    assert params == {"target": "host1", "duration": 15}

    restart_tool = executor.registry.get_tool("restart_service")
    params = executor._infer_parameters(restart_tool, {"service": "nginx", "timeout": 60})
    assert params == {"service_name": "nginx", "timeout": 60}

    anomaly_tool = executor.registry.get_tool("analyze_anomaly")
    params = executor._infer_parameters(anomaly_tool, {"metrics": [1, 2, 3]})
    assert params == {"data": [1, 2, 3]}

    root_tool = executor.registry.get_tool("root_cause_analysis")
    params = executor._infer_parameters(root_tool, {"alert": {"id": "a1"}})
    assert params == {"alert_id": "a1", "alert": {"id": "a1"}}
