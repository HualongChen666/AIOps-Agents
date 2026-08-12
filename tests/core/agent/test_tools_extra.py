# -*- coding: utf-8 -*-
"""Additional coverage tests for core/agent/tools.py."""

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


def _add_fn(x, y, **kwargs):
    return x + y


def _identity(data):
    return data


def test_create_tool_registry_lists_default_tools():
    registry = create_tool_registry()
    tools = registry.list_tools()
    assert isinstance(tools, list)
    assert len(tools) > 0
    assert all(isinstance(t, Tool) for t in tools)


def test_tool_registry_register_get_search_and_list_by_category():
    registry = create_tool_registry()
    registry.register(
        Tool(
            name="custom_add",
            description="add two numbers",
            category=ToolCategory.ANALYSIS,
            function=_add_fn,
            required_params=["x", "y"],
        )
    )
    assert registry.get_tool("custom_add") is not None
    assert registry.get_tool("custom_add").name == "custom_add"
    assert registry.get_tool("missing") is None

    search = registry.search_tools("collect")
    assert isinstance(search, list)
    assert any("collect" in t.name for t in search)

    monitoring = registry.list_tools(category=ToolCategory.MONITORING)
    assert all(t.category == ToolCategory.MONITORING for t in monitoring)
    assert len(monitoring) > 0


def test_tool_registry_unregister_and_approval(monkeypatch):
    monkeypatch.setenv("AIOPS_TOOL_REGISTRATION_APPROVAL_REQUIRED", "true")
    registry = ToolRegistry(approval_required=True)

    registry.approve_tool("custom_add", "admin")
    registry.register(
        Tool(
            name="custom_add",
            description="add two numbers",
            category=ToolCategory.ANALYSIS,
            function=_add_fn,
            required_params=["x", "y"],
        )
    )
    assert registry.get_tool("custom_add") is not None

    with pytest.raises(PermissionError):
        registry.register(
            Tool(
                name="another_tool",
                description="unapproved tool",
                category=ToolCategory.ANALYSIS,
                function=_add_fn,
                required_params=["x", "y"],
            )
        )

    registry.approve_tool("another_tool", "admin")
    assert registry.is_tool_approved("another_tool") is True
    req_id = registry.request_tool_approval("newtool", "tester", "need it")
    assert req_id.startswith("approval_newtool")

    registry.unregister("custom_add")
    assert registry.get_tool("custom_add") is None


def test_tool_approval_manager():
    mgr = ToolApprovalManager(approval_required=False)
    assert mgr.is_approved("anything") is True
    assert mgr.request_approval("x", "user", "reason").startswith("approval_x_")
    mgr.approve("y", "admin")
    assert mgr.is_approved("y") is True
    mgr.revoke("y")
    mgr2 = ToolApprovalManager(approval_required=True)
    assert mgr2.is_approved("z") is False


def test_tool_to_dict_and_execute_dry_run():
    tool = Tool(
        name="add",
        description="add numbers",
        category=ToolCategory.ANALYSIS,
        function=_add_fn,
        required_params=["x", "y"],
        optional_params=["note"],
        parameters={"note": "default"},
        examples=[{"x": 1, "y": 2}],
    )
    d = tool.to_dict()
    assert d["name"] == "add"
    assert "required_params" in d
    assert d["examples"] == [{"x": 1, "y": 2}]

    dry = tool.execute(x=3, y=4, dry_run=True)
    assert dry["dry_run"] is True
    assert dry["tool"] == "add"
    assert dry["parameters"]["x"] == "3"
    assert dry["parameters"]["y"] == "4"
    assert dry["parameters"]["note"] == "default"

    assert tool.execute(x=5, y=6) == 11


def test_tool_validate_parameters():
    tool = Tool(
        name="add",
        description="add numbers",
        category=ToolCategory.ANALYSIS,
        function=lambda x, y: x + y,
        required_params=["x", "y"],
        optional_params=["note"],
    )
    with pytest.raises(ValueError, match="Missing required"):
        tool.execute(x=1)
    with pytest.raises(ValueError, match="is not allowed"):
        tool._validate_parameters({"x": 1, "y": 2, "unknown": 3})


def test_tool_validate_value_types():
    tool = Tool(
        name="probe",
        description="probe",
        category=ToolCategory.DIAGNOSTIC,
        function=lambda duration, threshold, wait=False, data=None: (duration, threshold, wait, data),
        required_params=["duration"],
        optional_params=["threshold", "wait", "data"],
    )
    # integer parameter with range
    tool._validate_value("duration", 30)
    with pytest.raises(ValueError, match="between"):
        tool._validate_value("duration", 400)

    # float parameter
    tool._validate_value("threshold", 0.5)
    with pytest.raises(ValueError, match="between"):
        tool._validate_value("threshold", 1.5)

    # boolean
    tool._validate_value("wait", True)
    with pytest.raises(ValueError, match="boolean"):
        tool._validate_value("wait", "yes")

    # list
    tool._validate_value("data", [1, 2, 3])
    with pytest.raises(ValueError, match="list"):
        tool._validate_value("data", "not list")

    # string shell metachar rejection
    with pytest.raises(ValueError, match="dangerous characters"):
        tool._validate_value("target", "a;b")

    # path traversal rejection
    with pytest.raises(ValueError, match="path traversal"):
        tool._validate_value("target", "../etc")


def test_tool_clamp_parameter_ranges():
    tool = Tool(
        name="range_test",
        description="range test",
        category=ToolCategory.ANALYSIS,
        function=lambda duration: duration,
        required_params=["duration"],
    )
    assert tool.execute(duration=5, dry_run=True)["parameters"]["duration"] == "10"
    assert tool.execute(duration=300, dry_run=True)["parameters"]["duration"] == "300"


def test_tool_executor_execute_default_tool_dry_run():
    registry = create_tool_registry()
    executor = ToolExecutor(registry, dry_run=True)
    result = executor.execute_tool("collect_metrics", target="localhost", duration=30)
    assert isinstance(result, dict)
    assert result["dry_run"] is True
    assert result["tool"] == "collect_metrics"
    assert "parameters" in result


def test_tool_executor_execute_chain_and_statistics():
    registry = create_tool_registry()
    executor = ToolExecutor(registry, dry_run=True)
    results = executor.execute_chain(
        [
            ("collect_metrics", {"target": "host1"}),
            ("check_health", {"target": "localhost:8080"}),
        ]
    )
    assert isinstance(results, list)
    assert len(results) == 2

    stats = executor.get_execution_statistics()
    assert stats["total"] == 2
    assert stats["successful"] == 2
    assert stats["failed"] == 0
    assert stats["success_rate"] == 1.0


def test_tool_executor_execute_not_found():
    executor = ToolExecutor(create_tool_registry(), dry_run=True)
    with pytest.raises(ValueError, match="Tool not found"):
        executor.execute_tool("non_existent_tool")


def test_tool_executor_auto_selection():
    registry = create_tool_registry()
    executor = ToolExecutor(registry, dry_run=True)
    result = executor.execute_with_auto_selection(
        "collect metrics for myhost",
        {"target": "myhost"},
    )
    assert isinstance(result, dict)
    assert result["dry_run"] is True
    assert result["tool"] == "collect_metrics"


def test_tool_selector_select_tools_for_chain():
    registry = create_tool_registry()
    selector = ToolSelector(registry)
    tools = selector.select_tools_for_chain(
        ["collect logs", "restart service", "unknown weird thing"],
        {},
    )
    assert isinstance(tools, list)
    assert len(tools) == 2
    assert tools[0].name == "collect_logs"
    assert tools[1].name == "restart_service"


def test_tool_executor_sanitize_params():
    executor = ToolExecutor(create_tool_registry())
    out = executor._sanitize_params(
        {
            "password": "secret",
            "apikey": "xyz",
            "nested": {"api_key": "key", "public": "ok"},
            "items": [{"secret": "x"}, "plain"],
        }
    )
    assert out["password"] == "***"
    assert out["apikey"] == "***"
    assert out["nested"]["api_key"] == "***"
    assert out["nested"]["public"] == "ok"
    assert out["items"][0]["secret"] == "***"
