# -*- coding: utf-8 -*-
"""Unit tests for core/agent/tools.py."""

import pytest

from core.agent.tools import (
    Tool,
    ToolApprovalManager,
    ToolCategory,
    ToolExecutor,
    ToolRegistry,
    ToolSelector,
    create_tool_registry,
)


def test_create_tool_registry_and_list():
    registry = create_tool_registry()
    tools = registry.list_tools()
    assert isinstance(tools, list)
    if tools:
        assert registry.get_tool(tools[0].name) is not None


def _make_registry():
    registry = ToolRegistry(approval_required=False)
    tool = Tool(
        name="echo",
        description="Echo service",
        category=ToolCategory.DIAGNOSTIC,
        function=lambda service: f"ok {service}",
        required_params=["service"],
    )
    registry.register(tool)
    return registry


def test_custom_tool_lifecycle():
    registry = _make_registry()
    tool = registry.get_tool("echo")
    result = tool.execute(service="foo", dry_run=True)
    assert result["dry_run"] is True
    assert "foo" in result["parameters"]["service"]
    assert tool.to_dict()["name"] == "echo"


def test_tool_executor():
    registry = _make_registry()
    executor = ToolExecutor(registry, dry_run=True)
    result = executor.execute_tool("echo", service="bar")
    assert "bar" in str(result)
    chain = executor.execute_chain([("echo", {"service": "baz"})])
    assert isinstance(chain, list)
    stats = executor.get_execution_statistics()
    assert isinstance(stats, dict)


def test_tool_selector():
    registry = _make_registry()
    selector = ToolSelector(registry)
    selected = selector.select_tool("collect metrics", {})
    assert isinstance(selected, (Tool, type(None)))
    selected = selector.select_tool("restart service", {})
    assert isinstance(selected, (Tool, type(None)))


def test_tool_validation():
    tool = Tool(
        name="echo",
        description="Echo service",
        category=ToolCategory.DIAGNOSTIC,
        function=lambda service: f"ok {service}",
        required_params=["service"],
    )
    with pytest.raises(ValueError):
        tool.execute(service="foo; rm -rf")
    with pytest.raises(ValueError):
        tool.execute()


def test_tool_approval_manager():
    manager = ToolApprovalManager(approval_required=True)
    request_id = manager.request_approval("restart", "admin")
    assert isinstance(request_id, str)
    assert manager.is_approved("restart") is False
    manager.approve("restart", "approver")
    assert manager.is_approved("restart") is True
    manager.revoke("restart")
    assert manager.is_approved("restart") is False


def test_tool_registry_approval_flow():
    registry = ToolRegistry(approval_required=True)
    tool = Tool(
        name="restart",
        description="Restart",
        category=ToolCategory.EXECUTION,
        function=lambda service: f"restarted {service}",
        required_params=["service"],
    )
    assert registry.is_tool_approved("restart") is False
    request_id = registry.request_tool_approval("restart", "admin")
    assert isinstance(request_id, str)
    registry.approve_tool("restart", "approver")
    assert registry.is_tool_approved("restart") is True
    registry.register(tool)
