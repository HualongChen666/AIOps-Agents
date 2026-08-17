# -*- coding: utf-8 -*-
"""Additional coverage tests for core/agent/tools.py (remaining branches)."""

import asyncio
import re
import sys
import types
from unittest.mock import AsyncMock

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


def _noop(**kwargs):
    return "ok"


async def _async_noop(**kwargs):
    return "ok"


def test_tool_execute_pop_timeout_when_not_allowed():
    """Timeout should be removed from kwargs when the wrapped function does not accept it."""
    tool = Tool(
        name="identity",
        description="identity",
        category=ToolCategory.ANALYSIS,
        function=lambda x: x,
        required_params=["x"],
    )
    assert tool.execute(x=1, timeout=5) == 1


def test_tool_execute_timeout_from_default_parameters():
    """Execution timeout can be provided by tool default parameters."""
    tool = Tool(
        name="identity",
        description="identity",
        category=ToolCategory.ANALYSIS,
        function=lambda x: x,
        required_params=["x"],
        parameters={"timeout": 15},
    )
    dry = tool.execute(x=1, dry_run=True)
    assert dry["execution_timeout"] == 15.0
    assert dry["parameters"]["timeout"] == "15"


def test_tool_execute_dry_run_timeout_default():
    tool = Tool(
        name="noop",
        description="noop",
        category=ToolCategory.ANALYSIS,
        function=_noop,
        required_params=["x"],
    )
    dry = tool.execute(x=1, dry_run=True)
    assert dry["dry_run"] is True
    assert isinstance(dry["execution_timeout"], float)
    assert dry["parameters"]["x"] == "1"


async def test_async_tool_inside_running_loop():
    """When called inside a running loop the tool returns a coroutine that can be awaited."""
    tool = Tool(
        name="async_noop",
        description="async noop",
        category=ToolCategory.ANALYSIS,
        function=_async_noop,
        required_params=["x"],
    )
    assert await tool.execute(x=3) == "ok"


def test_tool_validate_value_depth_exceeded():
    tool = Tool(
        name="ctx",
        description="ctx",
        category=ToolCategory.ANALYSIS,
        function=_noop,
        required_params=["ctx"],
    )
    nested = {"l1": {"l2": {"l3": {"l4": {"l5": "deep"}}}}}
    with pytest.raises(ValueError, match="exceeds maximum nested depth"):
        tool._validate_value("ctx", nested)


def test_tool_validate_string_value_patterns_and_empty():
    tool = Tool(
        name="probe",
        description="probe",
        category=ToolCategory.DIAGNOSTIC,
        function=_noop,
        required_params=[],
        optional_params=["service", "description", "custom"],
    )
    # Empty value is not allowed for name-patterned parameters.
    with pytest.raises(ValueError, match="cannot be empty"):
        tool._validate_value("service", "")

    # Empty value is allowed for free-form text parameters.
    tool._validate_value("description", "")

    # Empty value is also allowed for unpatterned parameters.
    tool._validate_value("custom", "")

    # Text parameter max length is 1000.
    long_text = "a" * 1001
    with pytest.raises(ValueError, match="exceeds maximum length of 1000"):
        tool._validate_value("description", long_text)

    # Unpatterned strings must still pass the safe-text whitelist.
    with pytest.raises(ValueError, match="disallowed characters"):
        tool._validate_value("custom", "hello#world")


def test_tool_validate_param_patterns_custom():
    pattern = re.compile(r"^abc$")
    tool = Tool(
        name="probe",
        description="probe",
        category=ToolCategory.ANALYSIS,
        function=_noop,
        required_params=["custom"],
        param_patterns={"custom": pattern},
    )
    tool._validate_value("custom", "abc")
    with pytest.raises(ValueError, match="does not match allowed pattern"):
        tool._validate_value("custom", "def")


def test_tool_validate_list_string_and_invalid_items():
    tool = Tool(
        name="probe",
        description="probe",
        category=ToolCategory.ANALYSIS,
        function=_noop,
        required_params=["tools"],
        optional_params=["available_tools"],
    )
    # Valid comma-separated list.
    tool._validate_value("tools", "a,b,c")

    # Item with disallowed characters.
    with pytest.raises(ValueError, match="contains disallowed characters"):
        tool._validate_value("tools", "a;b")

    # String too long.
    with pytest.raises(ValueError, match="exceeds maximum length"):
        tool._validate_value("available_tools", "x" * 1001)


def test_tool_validate_data_container_command_blocked(monkeypatch):
    from core.command_guard import RiskLevel

    monkeypatch.setattr(
        "core.agent.tools._analyze_command",
        lambda cmd: {"risk_level": RiskLevel.HIGH, "reason": "dangerous"},
    )
    tool = Tool(
        name="alert_tool",
        description="alert tool",
        category=ToolCategory.ANALYSIS,
        function=_noop,
        required_params=["alert"],
    )
    with pytest.raises(ValueError, match="blocked by command_guard"):
        tool._validate_value("alert", {"command": "rm -rf /"})


def test_tool_audit_failure_does_not_break_execution(monkeypatch):
    def _raise(*args, **kwargs):
        raise RuntimeError("audit unavailable")

    monkeypatch.setattr("core.agent.tools._log_audit_event", _raise)
    tool = Tool(
        name="add",
        description="add",
        category=ToolCategory.ANALYSIS,
        function=lambda x: x,
        required_params=["x"],
    )
    # The audit warning is swallowed; the tool should still execute.
    assert tool.execute(x=1) == 1


def test_tool_executor_execute_tool_failure_and_history():
    def _bad():
        raise ValueError("boom")

    registry = ToolRegistry(approval_required=False)
    registry.register(
        Tool(
            name="bad",
            description="bad",
            category=ToolCategory.ANALYSIS,
            function=_bad,
        )
    )
    executor = ToolExecutor(registry)
    with pytest.raises(ValueError, match="boom"):
        executor.execute_tool("bad")

    stats = executor.get_execution_statistics()
    assert stats["total"] == 1
    assert stats["failed"] == 1
    assert stats["successful"] == 0
    assert stats["success_rate"] == 0.0


def test_tool_executor_sanitize_sensitive_list_and_nested_dict():
    executor = create_tool_executor()
    out = executor._sanitize_params(
        {
            "passwords": ["secret", "x"],
            "items": [{"auth_token": "x"}, "plain"],
        }
    )
    # Sensitive keys have their entire value replaced, even if it is a list.
    assert out["passwords"] == "***"
    # Non-sensitive list items that are dicts are recursively sanitized.
    assert out["items"][0]["auth_token"] == "***"
    assert out["items"][1] == "plain"


def test_tool_selector_unknown_returns_none_and_empty_chain():
    registry = create_tool_registry()
    selector = ToolSelector(registry)
    assert selector.select_tool("", {}) is None
    assert selector.select_tools_for_chain(["unknown weird thing"], {}) == []


def test_tool_registry_approval_from_env(monkeypatch):
    monkeypatch.setenv("AIOPS_TOOL_REGISTRATION_APPROVAL_REQUIRED", "true")
    reg = ToolRegistry()
    assert reg.approval_manager.approval_required is True

    monkeypatch.setenv("AIOPS_TOOL_REGISTRATION_APPROVAL_REQUIRED", "false")
    reg2 = ToolRegistry()
    assert reg2.approval_manager.approval_required is False


def test_tool_approval_manager_revoke_and_idempotent():
    mgr = ToolApprovalManager(approval_required=True)
    assert mgr.is_approved("x") is False
    mgr.approve("x", "admin")
    assert mgr.is_approved("x") is True
    mgr.revoke("x")
    mgr.revoke("x")  # idempotent
    assert mgr.is_approved("x") is False


def test_tool_to_dict_excludes_internal_param_patterns():
    tool = Tool(
        name="t",
        description="d",
        category=ToolCategory.ANALYSIS,
        function=_noop,
        param_patterns={"x": re.compile(r".*")},
    )
    d = tool.to_dict()
    assert "param_patterns" not in d
    assert d["name"] == "t"


def test_root_cause_analysis_async_success(monkeypatch):
    """Exercise the async root cause tool path with a mocked intelligence engine."""
    hypothesis = types.SimpleNamespace(
        root_cause="network",
        confidence=0.8,
        expected_observations=["packet loss"],
        missing_data=[],
        verification_status="verified",
        evidence=["metric"],
    )
    fake_engine = types.SimpleNamespace(
        analyze_root_causes_enhanced=AsyncMock(return_value=[hypothesis])
    )
    monkeypatch.setattr(
        "core.root_cause_intelligence.root_cause_intelligence_engine",
        fake_engine,
    )

    registry = create_tool_registry()
    tool = registry.get_tool("root_cause_analysis")
    result = tool.execute(alert_id="a1")
    assert result["alert_id"] == "a1"
    assert result["method"] == "causal"
    assert len(result["candidates"]) == 1
    assert result["candidates"][0]["root_cause"] == "network"
    assert result["escalation_recommended"] is False


def test_tool_execute_type_validation_int_and_float():
    int_tool = Tool(
        name="duration_tool",
        description="duration",
        category=ToolCategory.ANALYSIS,
        function=lambda duration: duration,
        required_params=["duration"],
    )
    with pytest.raises(ValueError, match="must be an integer"):
        int_tool.execute(duration="abc")
    with pytest.raises(ValueError, match="must be an integer"):
        int_tool.execute(duration=True)

    float_tool = Tool(
        name="threshold_tool",
        description="threshold",
        category=ToolCategory.ANALYSIS,
        function=lambda threshold: threshold,
        required_params=["threshold"],
    )
    with pytest.raises(ValueError, match="must be a number"):
        float_tool.execute(threshold="abc")
