# -*- coding: utf-8 -*-
"""Unit tests for core/agent/tools.py."""

from core.agent.tools import (
    Tool,
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
