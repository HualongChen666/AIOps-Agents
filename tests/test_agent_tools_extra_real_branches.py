# -*- coding: utf-8 -*-
"""Extra branch-coverage tests for core/agent/tools.py using real objects.

These tests exercise remaining branches around validation, execution success/failure,
retrys, timeouts, permissions, tool-not-found, and selector/inference paths.
They do not use mocks: inputs are real Tool / ToolRegistry / ToolExecutor instances
and real data where feasible.
"""

import asyncio
import time

import pytest

from core.agent.tools import (
    Tool,
    ToolCategory,
    ToolExecutor,
    ToolRegistry,
    ToolSelector,
    _guard_command_param,
    create_tool_executor,
    create_tool_registry,
)


def _make_flaky():
    """Return a sync function that raises ConnectionError once, then succeeds."""
    state = [0]

    def flaky(target: str) -> dict:
        state[0] += 1
        if state[0] < 2:
            raise ConnectionError("boom")
        return {"ok": True, "attempts": state[0]}

    return flaky


def _make_slow():
    """Return a sync function that sleeps longer than any test timeout."""

    def slow(target: str) -> None:
        time.sleep(0.2)

    return slow


def _custom_registry():
    reg = ToolRegistry()
    reg.register(
        Tool(
            name="flaky",
            description="fails once then succeeds",
            category=ToolCategory.MONITORING,
            function=_make_flaky(),
            required_params=["target"],
        )
    )
    reg.register(
        Tool(
            name="slow",
            description="always times out",
            category=ToolCategory.MONITORING,
            function=_make_slow(),
            required_params=["target"],
        )
    )
    reg.register(
        Tool(
            name="svc_infer",
            description="infers optional service_name",
            category=ToolCategory.MONITORING,
            function=lambda service_name="": {"got": service_name},
            optional_params=["service_name"],
        )
    )
    return reg


def test_guard_command_param_ignores_non_string():
    """_guard_command_param should short-circuit when value is not a string."""
    # No exception means the non-string branch was taken and returned early.
    _guard_command_param("command", {"not": "string"})


def test_validate_string_value_ignores_non_string():
    """_validate_string_value returns immediately for non-string values."""
    tool = Tool(
        name="validate_string_test",
        description="for validation",
        category=ToolCategory.MONITORING,
        function=lambda x: x,
    )
    tool._validate_string_value("any_name", 123)


def test_tool_signature_failure_except_branches():
    """Tool.execute and _validate_parameters handle uninspectable callables."""
    tool = Tool(
        name="builtin_tool",
        description="uses int as function",
        category=ToolCategory.MONITORING,
        function=int,
    )
    plan = tool.execute(dry_run=True)
    assert plan["dry_run"] is True
    assert plan["tool"] == "builtin_tool"


def test_analyze_anomaly_rejects_oversized_data_list():
    """The list length guard in _validate_value must reject > _MAX_LIST_LENGTH."""
    reg = create_tool_registry()
    tool = reg.get_tool("analyze_anomaly")
    with pytest.raises(ValueError, match="list length"):
        tool.execute(data=list(range(10001)))


def test_dispatch_subagent_available_tools_list_branch():
    """_dispatch_subagent parses a list of available_tools."""
    reg = create_tool_registry()
    result = reg._dispatch_subagent(
        goal="x",
        _depth=0,
        available_tools=["a", "b"],
        wait=True,
        dry_run=True,
    )
    assert isinstance(result, dict)


def test_dispatch_subagent_available_tools_unhandled_type():
    """_dispatch_subagent leaves tools empty for unhandled available_tools types."""
    reg = create_tool_registry()
    result = reg._dispatch_subagent(
        goal="x",
        _depth=0,
        available_tools=123,
        wait=True,
        dry_run=True,
    )
    assert isinstance(result, dict)


def test_tool_selector_service_and_database_branches():
    """Cover the inner for-loop return branches for service/database metrics."""
    reg = create_tool_registry()
    selector = ToolSelector(reg)

    service_tool = selector.select_tool("sli traffic latency", {})
    assert service_tool is not None and "collect_service_metrics" == service_tool.name

    db_tool = selector.select_tool("database slow query", {})
    assert db_tool is not None and "database" in db_tool.name.lower()


def test_tool_selector_unmatched_category_loops():
    """Cover the for-loop exit branches when no monitoring tool matches the filter."""
    reg = create_tool_registry()
    reg.tools.clear()
    reg.register(
        Tool(
            name="collect_x",
            description="x",
            category=ToolCategory.MONITORING,
            function=lambda target: {},
        )
    )
    selector = ToolSelector(reg)
    assert selector.select_tool("sli traffic", {}) is None
    assert selector.select_tool("database slow", {}) is None


def test_infer_parameters_target_to_optional_service_name():
    """_infer_parameters falls back from target to optional service_name."""
    reg = _custom_registry()
    executor = ToolExecutor(reg)
    tool = reg.get_tool("svc_infer")
    params = executor._infer_parameters(tool, {"target": "nginx"})
    assert params["service_name"] == "nginx"


def test_infer_parameters_service_to_optional_service_name():
    """_infer_parameters prefers service over target for optional service_name."""
    reg = _custom_registry()
    executor = ToolExecutor(reg)
    tool = reg.get_tool("svc_infer")
    params = executor._infer_parameters(tool, {"service": "svc", "target": "nginx"})
    assert params["service_name"] == "svc"


def test_tool_executor_retry_and_success():
    """_execute_with_retry retries ConnectionError and records success."""
    reg = _custom_registry()
    executor = ToolExecutor(reg, retry_policy={"max_retries": 2, "backoff": [0, 0]})
    result = executor.execute_tool("flaky", target="x")
    assert result["ok"] is True
    assert result["attempts"] == 2
    assert executor.get_execution_statistics()["successful"] == 1


def test_tool_executor_timeout_and_failure_history():
    """execute_tool records a failed history entry on asyncio.TimeoutError."""
    reg = _custom_registry()
    executor = ToolExecutor(reg, retry_policy={"max_retries": 0, "backoff": [0, 0]})
    with pytest.raises(asyncio.TimeoutError):
        executor.execute_tool("slow", target="x", timeout=0.05)
    stats = executor.get_execution_statistics()
    assert stats["total"] == 1
    assert stats["failed"] == 1


def test_tool_executor_missing_and_invalid_arguments():
    """Missing and invalid parameters lead to ValueError and failure history."""
    reg = create_tool_registry()
    executor = ToolExecutor(reg, retry_policy={"max_retries": 0, "backoff": [0, 0]})

    with pytest.raises(ValueError, match="Missing required"):
        executor.execute_tool("collect_logs")

    with pytest.raises(ValueError, match="integer"):
        executor.execute_tool("scale_service", service_name="nginx", replicas="two")


def test_tool_executor_dry_run_success():
    """A successful dry-run execution is recorded."""
    reg = create_tool_registry()
    executor = ToolExecutor(reg)
    result = executor.execute_tool("collect_metrics", target="node", dry_run=True)
    assert result["dry_run"] is True
    assert executor.get_execution_statistics()["successful"] == 1


def test_tool_not_found_and_unregistered():
    """execute_tool raises for a missing/disabled tool."""
    reg = create_tool_registry()
    reg.unregister("collect_logs")
    executor = ToolExecutor(reg)
    with pytest.raises(ValueError, match="Tool not found"):
        executor.execute_tool("collect_logs", service="x")


def test_tool_registry_approval_permission():
    """Register/unregister require approval when approval is enforced."""
    reg = ToolRegistry(approval_required=True)
    tool = Tool(
        name="new_tool",
        description="needs approval",
        category=ToolCategory.MONITORING,
        function=lambda: "ok",
    )

    with pytest.raises(PermissionError):
        reg.register(tool)

    reg.approve_tool("new_tool", "admin")
    reg.register(tool)
    assert reg.is_tool_approved("new_tool")

    reg.approval_manager.revoke("new_tool")
    with pytest.raises(PermissionError):
        reg.unregister("new_tool")


def test_collect_change_events_local_audit_branches():
    """_collect_change_events exercises local audit-log filter branches."""
    from core.config_manager import config_manager

    # Matching entry with a current timestamp.
    config_manager.audit_config_change("user", "match_target", {})
    # Non-matching target with a current timestamp.
    config_manager.audit_config_change("user", "other_target", {})
    # Entry with an out-of-range (old) timestamp.
    config_manager.audit_config_change("user", "old_target", {})
    config_manager._audit_log[-1]["timestamp"] = 0.0

    reg = create_tool_registry()
    events = reg._collect_change_events("match_target", hours=24)
    assert all(e["target"] == "match_target" for e in events)


def test_collect_correlated_alerts_non_match_branch():
    """_collect_correlated_alerts continues past non-matching alerts."""
    from core.alert_engine import alert_history

    alert_history.append({"title": "svc down", "desc": "", "host": "", "source": ""})
    alert_history.append({"title": "other", "desc": "", "host": "", "source": "other"})

    reg = create_tool_registry()
    matched = reg.get_tool("collect_correlated_alerts").execute(service="svc")
    assert any("svc" in a["title"] for a in matched)

    non = reg.get_tool("collect_correlated_alerts").execute(service="nomatch_xyz")
    assert non == []
