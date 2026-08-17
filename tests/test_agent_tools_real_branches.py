# -*- coding: utf-8 -*-
"""Branch-coverage tests for core/agent/tools.py using real inputs.

These tests exercise the default tools and the surrounding classes with real
parameters and local files.  They do not mock or monkeypatch internal code.
"""

from pathlib import Path

import pytest  # noqa: F401  # Imported for test setup

from core.agent.tools import (
    Tool,
    ToolCategory,
    ToolExecutor,
    ToolRegistry,
    ToolSelector,
    create_tool_executor,
    create_tool_registry,
)


def _log_file(service: str, content: str) -> None:
    Path("logs").mkdir(exist_ok=True)
    Path(f"logs/{service}.log").write_text(content, encoding="utf-8")


def _clean_log_file(service: str) -> None:
    p = Path(f"logs/{service}.log")
    if p.exists():
        p.unlink()


def test_tool_execute_ignores_timeout_for_functions_without_timeout_param():
    """Tool.execute pops `timeout` from params when the function doesn't accept it."""
    reg = create_tool_registry()
    tool = reg.get_tool("collect_metrics")
    plan = tool.execute(target="node", timeout=10, dry_run=True)
    assert plan["dry_run"] is True
    assert "timeout" not in plan["parameters"]


def test_analyze_anomaly_rejects_bool_threshold():
    reg = create_tool_registry()
    tool = reg.get_tool("analyze_anomaly")
    with pytest.raises(ValueError, match="float"):
        tool.execute(data=[1.0, 2.0, 3.0], threshold=True)


def test_root_cause_analysis_rejects_oversized_alert_list():
    reg = create_tool_registry()
    tool = reg.get_tool("root_cause_analysis")
    with pytest.raises(ValueError, match="list length"):
        tool.execute(alert_id="a1", alert=[0] * 10001)


def test_dispatch_subagent_available_tools_and_context_validation():
    """Exercise list-string, empty items, and dict parameter validation branches."""
    reg = create_tool_registry()
    tool = reg.get_tool("dispatch_subagent")

    # string with an empty item -> continue branch
    res = tool.execute(goal="x", _depth=3, available_tools="a,,b")
    assert isinstance(res, dict)

    # list of strings branch
    res = tool.execute(goal="x", _depth=3, available_tools=["a", "b"])
    assert isinstance(res, dict)

    # None branch
    res = tool.execute(goal="x", _depth=3)
    assert isinstance(res, dict)

    # empty-string context exercises the unpatterned empty-string validation path
    res = tool.execute(goal="x", _depth=3, context="")
    assert isinstance(res, dict)

    # dict context exercises dict generic validation (command key, bool, scalar, nested)
    res = tool.execute(
        goal="x",
        _depth=3,
        context={
            "rollback_command": "echo test",
            "flag": True,
            "count": 1,
            "nested": {"x": "value"},
        },
    )
    assert isinstance(res, dict)

    with pytest.raises(ValueError, match="maximum length"):
        tool.execute(goal="x", _depth=3, available_tools="a" * 1001)

    with pytest.raises(ValueError, match="must be a list"):
        tool.execute(goal="x", _depth=3, available_tools=123)


def test_analyze_anomaly_empty_and_normal():
    reg = create_tool_registry()
    tool = reg.get_tool("analyze_anomaly")

    empty = tool.execute(data=[])
    assert empty["is_anomaly"] is False

    normal = tool.execute(data=[1.0, 2.0, 3.0], threshold=0.5, method="threshold")
    assert "is_anomaly" in normal


def test_root_cause_analysis_with_alert_and_verification():
    reg = create_tool_registry()
    tool = reg.get_tool("root_cause_analysis")
    result = tool.execute(  # noqa: F841  # Variable for test verification
        alert_id="a1",
        alert={"id": "a1", "title": "incident"},
        verification_data={"verified": True},
    )
    assert isinstance(result, dict)
    assert result["alert_id"] == "a1"


def test_collect_logs_reads_file_and_fallback():
    service = "testservice"
    try:
        _log_file(service, "INFO start\nERROR boom\nINFO end\n")
        reg = create_tool_registry()
        tool = reg.get_tool("collect_logs")

        found = tool.execute(service=service, level="INFO")
        assert isinstance(found, list)
        assert any("INFO" in line for line in found)

        missing = tool.execute(service="no_such_service_xyz")
        assert isinstance(missing, list)
        assert "No log file" in missing[0]
    finally:
        _clean_log_file(service)


def test_health_check_http_and_invalid_port():
    reg = create_tool_registry()
    tool = reg.get_tool("check_health")

    http = tool.execute(target="http://127.0.0.1:1")
    assert isinstance(http, dict)
    assert "healthy" in http

    invalid_port = tool.execute(target="127.0.0.1:abc")
    assert isinstance(invalid_port, dict)
    assert "healthy" in invalid_port


def test_run_diagnostic_localhost():
    reg = create_tool_registry()
    tool = reg.get_tool("run_diagnostic")
    result = tool.execute(target="localhost", type="basic")  # noqa: F841  # Variable for test verification
    assert isinstance(result, dict)
    assert "health" in result


def test_all_default_tools_real_inputs():
    """Call every default tool with real, safe parameters."""
    reg = create_tool_registry()

    results = {}
    results["collect_metrics"] = reg.get_tool("collect_metrics").execute(target="node")
    results["collect_service_metrics"] = reg.get_tool("collect_service_metrics").execute(
        service_name="svc"
    )
    results["collect_network_metrics"] = reg.get_tool("collect_network_metrics").execute(
        target="node"
    )
    results["collect_change_events"] = reg.get_tool("collect_change_events").execute(
        target="node", change_events=[{"timestamp": 1.0, "type": "deploy"}]
    )
    results["collect_kubernetes_events"] = reg.get_tool("collect_kubernetes_events").execute(
        namespace="default", limit=10
    )
    results["collect_container_metrics"] = reg.get_tool("collect_container_metrics").execute(
        pod_name="pod1", namespace="default", container_metrics={"x": 1}
    )
    results["collect_host_metrics"] = reg.get_tool("collect_host_metrics").execute(
        node_name="node1", host_metrics={"x": 1}
    )
    results["collect_database_metrics"] = reg.get_tool("collect_database_metrics").execute(
        database="db1", database_metrics={"x": 1}
    )
    results["collect_correlated_alerts"] = reg.get_tool("collect_correlated_alerts").execute(
        service="svc"
    )
    results["collect_topology"] = reg.get_tool("collect_topology").execute(service="svc")
    results["restart_service"] = reg.get_tool("restart_service").execute(service_name="nginx")
    results["scale_service"] = reg.get_tool("scale_service").execute(
        service_name="nginx", replicas=2
    )

    for name, value in results.items():
        assert value is not None, f"{name} returned None"


def test_tool_approval_flows():
    reg = ToolRegistry(approval_required=True)

    new_tool = Tool(
        name="approval_test_tool",
        description="for approval tests",
        category=ToolCategory.MONITORING,
        function=lambda: "ok",
    )

    # pre-approve and register
    reg.approve_tool("approval_test_tool", "admin")
    reg.register(new_tool)
    assert reg.is_tool_approved("approval_test_tool")

    # request approval
    req_id = reg.request_tool_approval("another_tool", "user")
    assert req_id.startswith("approval_")

    # revoke approval (via the approval manager)
    reg.approval_manager.revoke("approval_test_tool")
    assert not reg.is_tool_approved("approval_test_tool")

    # re-approve and unregister
    reg.approve_tool("approval_test_tool", "admin")
    reg.unregister("approval_test_tool", approved_by="admin")

    # register without approval should raise
    unapproved = Tool(
        name="unapproved_tool",
        description="unapproved",
        category=ToolCategory.MONITORING,
        function=lambda: "ok",
    )
    with pytest.raises(PermissionError):
        reg.register(unapproved)


def test_tool_selector_empty_registry_and_happy_path():
    # empty registry forces all for-loops to exit without a match
    reg = create_tool_registry()
    reg.tools.clear()
    selector = ToolSelector(reg)
    assert (
        selector.select_tool(
            "log metrics anomaly root cause restart scale change alert "
            "network database pod topology health",
            {},
        )
        is None
    )
    assert selector.select_tools_for_chain(["log", "health"], {}) == []

    # happy path
    reg2 = create_tool_registry()
    selector2 = ToolSelector(reg2)
    chosen = selector2.select_tool("collect system metrics", {"target": "node"})
    assert chosen is not None
    assert "metric" in chosen.name.lower()


def test_tool_executor_chain_break_and_auto_selection():
    reg = create_tool_registry()
    executor = create_tool_executor(reg)

    # first item is missing required param -> caught, break
    results = executor.execute_chain(
        [
            ("collect_metrics", {}),  # missing target
            ("collect_logs", {"service": "nonexistent_xyz"}),
        ]
    )
    assert len(results) == 0

    # no matching tool
    with pytest.raises(ValueError, match="No tool found"):
        executor.execute_with_auto_selection("foobar not matching anything", {})

    # infer target from service, optional level from context
    result = executor.execute_with_auto_selection(  # noqa: F841  # Variable for test verification
        "collect system logs", {"service": "nonexistent_xyz", "level": "ERROR"}
    )
    assert isinstance(result, list)

    # infer data from metrics
    result = executor.execute_with_auto_selection("detect anomaly", {"metrics": [1.0, 2.0, 3.0]})  # noqa: F841  # Variable for test verification
    assert isinstance(result, dict)

    # infer required target from service
    result = executor.execute_with_auto_selection("collect system metrics", {"service": "node"})  # noqa: F841  # Variable for test verification
    assert isinstance(result, dict)

    # infer required service from target
    result = executor.execute_with_auto_selection(  # noqa: F841  # Variable for test verification
        "collect system logs", {"target": "nonexistent_xyz"}
    )
    assert isinstance(result, list)

    # infer required service_name from target (restart_service)
    result = executor.execute_with_auto_selection("restart nginx", {"target": "nginx"})  # noqa: F841  # Variable for test verification
    assert isinstance(result, dict)

    # infer required alert_id from context alert
    result = executor.execute_with_auto_selection("root cause analysis", {"alert": {"id": "a1"}})  # noqa: F841  # Variable for test verification
    assert isinstance(result, dict)


def test_tool_selector_mismatched_tools():
    """Force ToolSelector for-loop bodies to run and miss the inner return."""
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
    reg.register(
        Tool(
            name="analyze_x",
            description="x",
            category=ToolCategory.ANALYSIS,
            function=lambda data: {},
        )
    )
    reg.register(
        Tool(
            name="exec_x",
            description="x",
            category=ToolCategory.EXECUTION,
            function=lambda service_name: {},
        )
    )
    reg.register(
        Tool(
            name="diag_x",
            description="x",
            category=ToolCategory.DIAGNOSTIC,
            function=lambda target: {},
        )
    )
    selector = ToolSelector(reg)
    # each keyword triggers a category, the single tool there does not match the
    # inner filter, so every for-loop exits and select_tool finally returns None
    result = selector.select_tool(  # noqa: F841  # Variable for test verification
        "log metrics anomaly root cause restart scale change network database pod topology health",
        {},
    )
    assert result is None
