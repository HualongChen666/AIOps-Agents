# -*- coding: utf-8 -*-
"""Tests for core/agent/tools.py."""

import pytest

from core.agent.tools import Tool, ToolCategory


def sample_tool(x, y):
    return x + y


def test_tool_category_values():
    assert ToolCategory.MONITORING.value == "monitoring"
    assert ToolCategory.EXECUTION.value == "execution"


def test_tool_dry_run_and_execution():
    tool = Tool(
        name="add",
        description="add two numbers",
        category=ToolCategory.ANALYSIS,
        function=sample_tool,
        required_params=["x", "y"],
    )

    dry = tool.execute(x=1, y=2, dry_run=True)
    assert dry["dry_run"] is True
    assert dry["tool"] == "add"

    assert tool.execute(x=3, y=4) == 7


def test_tool_missing_required_param():
    tool = Tool(
        name="add",
        description="add",
        category=ToolCategory.ANALYSIS,
        function=sample_tool,
        required_params=["x", "y"],
    )
    with pytest.raises(ValueError):
        tool.execute(x=1)
