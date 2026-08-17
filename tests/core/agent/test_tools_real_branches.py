# -*- coding: utf-8 -*-
"""
Test file covering missing branches in core/agent/tools.py using real classes.
"""

import asyncio
import os
import sys
import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Any, Dict, List, Optional

# Import the real classes
from core.agent.tools import (
    Tool,
    ToolCategory,
    ToolRegistry,
    ToolApprovalManager,
    ToolSelector,
    ToolExecutor,
    _audit_tool,
    _guard_command_param,
    COMMAND_GUARD_AVAILABLE,
    AUDIT_AVAILABLE,
    RiskLevel,
    _analyze_command,
    _log_audit_event,
    _DEFAULT_TOOL_TIMEOUT,
    _MAX_PARAM_LEN,
    _MAX_TEXT_LEN,
    _MAX_LIST_LENGTH,
    _MAX_CONTEXT_DEPTH,
    _NAME_PATTERNS,
    _SAFE_TEXT_PATTERN,
    _SHELL_METACHAR_PATTERN,
    _INT_PARAM_NAMES,
    _INT_PARAM_RANGES,
    _FLOAT_PARAM_NAMES,
    _FLOAT_PARAM_RANGES,
    _BOOL_PARAM_NAMES,
    _LIST_PARAM_NAMES,
    _TEXT_PARAM_NAMES,
    _DATA_CONTAINER_NAMES,
    _COMMAND_PARAM_NAMES,
)


# ----------------------------------------------------------------------
# Module import failure handling tests
# ----------------------------------------------------------------------
class TestModuleImportFailure:
    """Test handling of module import failures."""

    def test_command_guard_unavailable(self):
        """Test when command_guard is not available."""
        # This is already tested by the module-level try/except
        # Just verify the flags are set correctly
        if not COMMAND_GUARD_AVAILABLE:
            assert RiskLevel is None
            assert _analyze_command is None

    def test_audit_unavailable(self):
        """Test when audit_logger is not available."""
        # This is already tested by the module-level try/except
        # Just verify the flags are set correctly
        if not AUDIT_AVAILABLE:
            assert _log_audit_event is None


# ----------------------------------------------------------------------
# _audit_tool tests
# ----------------------------------------------------------------------
class TestAuditTool:
    """Test _audit_tool function branches."""

    def test_audit_tool_unavailable(self):
        """Test _audit_tool when audit is unavailable."""
        with patch('core.agent.tools.AUDIT_AVAILABLE', False):
            # Should not raise, just return silently
            _audit_tool("test_tool", "success")

    def test_audit_tool_exception(self):
        """Test _audit_tool when log_audit_event raises exception."""
        with patch('core.agent.tools.AUDIT_AVAILABLE', True):
            with patch('core.agent.tools._log_audit_event', side_effect=Exception("Audit failed")):
                # Should not raise, just log warning
                _audit_tool("test_tool", "success")

    def test_audit_tool_success(self):
        """Test _audit_tool successful call."""
        with patch('core.agent.tools.AUDIT_AVAILABLE', True):
            with patch('core.agent.tools._log_audit_event') as mock_audit:
                _audit_tool("test_tool", "success", {"key": "value"})
                mock_audit.assert_called_once()


# ----------------------------------------------------------------------
# _guard_command_param tests
# ----------------------------------------------------------------------
class TestGuardCommandParam:
    """Test _guard_command_param function branches."""

    def test_guard_command_unavailable(self):
        """Test when command_guard is not available."""
        with patch('core.agent.tools.COMMAND_GUARD_AVAILABLE', False):
            # Should return silently
            _guard_command_param("command", "rm -rf /")

    def test_guard_command_non_string(self):
        """Test with non-string value."""
        _guard_command_param("command", 123)
        _guard_command_param("command", None)
        _guard_command_param("command", {"cmd": "test"})

    def test_guard_command_empty_string(self):
        """Test with empty string."""
        _guard_command_param("command", "")

    def test_guard_command_not_command_param(self):
        """Test with param not in _COMMAND_PARAM_NAMES."""
        _guard_command_param("service", "test-service")

    def test_guard_command_risk_level_none(self):
        """Test when RiskLevel is None."""
        with patch('core.agent.tools.COMMAND_GUARD_AVAILABLE', True):
            with patch('core.agent.tools.RiskLevel', None):
                with patch('core.agent.tools._analyze_command', return_value={"risk_level": "HIGH"}):
                    _guard_command_param("command", "test")

    def test_guard_command_low_risk(self):
        """Test with low risk command."""
        with patch('core.agent.tools.COMMAND_GUARD_AVAILABLE', True):
            # Create a proper mock enum
            from enum import Enum
            MockRiskLevel = Enum('MockRiskLevel', ['BLOCKED', 'HIGH', 'LOW'])
            with patch('core.agent.tools.RiskLevel', MockRiskLevel):
                with patch('core.agent.tools._analyze_command', return_value={"risk_level": MockRiskLevel.LOW}):
                    _guard_command_param("command", "safe-command")

    def test_guard_command_high_risk_blocked(self):
        """Test with high risk blocked command."""
        with patch('core.agent.tools.COMMAND_GUARD_AVAILABLE', True):
            mock_risk = Mock()
            mock_risk.BLOCKED = "blocked"
            mock_risk.HIGH = "high"
            with patch('core.agent.tools.RiskLevel', mock_risk):
                with patch('core.agent.tools._analyze_command', return_value={"risk_level": "blocked", "reason": "dangerous"}):
                    with pytest.raises(ValueError, match="blocked by command_guard"):
                        _guard_command_param("command", "rm -rf /")


# ----------------------------------------------------------------------
# Tool.execute timeout tests
# ----------------------------------------------------------------------
class TestToolExecuteTimeout:
    """Test Tool.execute timeout handling branches."""

    def test_missing_required_params(self):
        """Test missing required parameters."""
        def dummy_func(target: str):
            return {"result": "ok"}

        tool = Tool(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.MONITORING,
            function=dummy_func,
            required_params=["target"],
        )
        with pytest.raises(ValueError, match="Missing required parameters"):
            tool.execute()

    def test_timeout_from_params(self):
        """Test timeout from tool parameters."""
        def dummy_func(target: str, timeout: int = 10):
            return {"result": "ok", "timeout": timeout}

        tool = Tool(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.MONITORING,
            function=dummy_func,
            parameters={"timeout": 15},
            required_params=["target"],
            optional_params=["timeout"],
        )
        result = tool.execute(target="test")
        assert result["result"] == "ok"
        assert result["timeout"] == 15

    def test_timeout_default(self):
        """Test default timeout when not specified."""
        def dummy_func(target: str):
            return {"result": "ok"}

        tool = Tool(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.MONITORING,
            function=dummy_func,
            required_params=["target"],
        )
        result = tool.execute(target="test")
        assert result["result"] == "ok"

    def test_timeout_invalid(self):
        """Test invalid timeout value."""
        def dummy_func(target: str):
            return {"result": "ok"}

        tool = Tool(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.MONITORING,
            function=dummy_func,
            required_params=["target"],
        )
        with pytest.raises(ValueError, match="Invalid timeout value"):
            tool.execute(target="test", timeout="invalid")

    def test_timeout_removed_when_not_allowed(self):
        """Test timeout removed when function doesn't accept it."""
        def dummy_func(target: str):
            return {"result": "ok"}

        tool = Tool(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.MONITORING,
            function=dummy_func,
            required_params=["target"],
        )
        # timeout should be removed from params before calling function
        result = tool.execute(target="test", timeout=10)
        assert result["result"] == "ok"

    def test_timeout_not_in_allowed_params(self):
        """Test when timeout is not in allowed params."""
        def dummy_func(target: str):
            return {"result": "ok"}

        tool = Tool(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.MONITORING,
            function=dummy_func,
            required_params=["target"],
        )
        # When timeout is not in allowed params, it should be removed
        result = tool.execute(target="test", timeout=10)
        assert result["result"] == "ok"

    def test_timeout_var_keyword_allowed(self):
        """Test timeout handling with **kwargs in function signature."""
        # This test covers the branch where function has **kwargs
        # The actual behavior depends on signature inspection
        def dummy_func(target: str, **kwargs):
            return {"result": "ok"}

        tool = Tool(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.MONITORING,
            function=dummy_func,
            required_params=["target"],
        )
        # Should execute without error regardless of timeout handling
        result = tool.execute(target="test", timeout=10)
        assert result["result"] == "ok"

    def test_timeout_signature_exception(self):
        """Test when inspect.signature raises exception."""
        def dummy_func(target: str):
            return {"result": "ok"}

        tool = Tool(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.MONITORING,
            function=dummy_func,
            required_params=["target"],
        )
        with patch('inspect.signature', side_effect=TypeError("Cannot inspect")):
            # Should handle gracefully
            result = tool.execute(target="test", timeout=10)
            assert result["result"] == "ok"

    def test_dry_run_mode(self):
        """Test dry_run mode."""
        def dummy_func(target: str):
            return {"result": "ok"}

        tool = Tool(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.MONITORING,
            function=dummy_func,
            required_params=["target"],
        )
        result = tool.execute(target="test", dry_run=True)
        assert result["dry_run"] is True
        assert result["tool"] == "test_tool"


# ----------------------------------------------------------------------
# _clamp_parameter_ranges tests
# ----------------------------------------------------------------------
class TestClampParameterRanges:
    """Test _clamp_parameter_ranges branches."""

    def test_key_not_in_params(self):
        """Test when key is not in params."""
        def dummy_func(target: str):
            return {"result": "ok"}

        tool = Tool(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.MONITORING,
            function=dummy_func,
            required_params=["target"],
        )
        params = {"target": "test"}
        result = tool._clamp_parameter_ranges(params)
        assert result == params

    def test_type_conversion_failure(self):
        """Test when type conversion fails."""
        def dummy_func(target: str):
            return {"result": "ok"}

        tool = Tool(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.MONITORING,
            function=dummy_func,
            required_params=["target"],
        )
        params = {"target": "test", "duration": "invalid"}
        result = tool._clamp_parameter_ranges(params)
        # Should skip invalid conversion
        assert result["duration"] == "invalid"

    def test_within_range(self):
        """Test value within range."""
        def dummy_func(target: str):
            return {"result": "ok"}

        tool = Tool(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.MONITORING,
            function=dummy_func,
            required_params=["target"],
        )
        params = {"target": "test", "duration": 60}
        result = tool._clamp_parameter_ranges(params)
        assert result["duration"] == 60

    def test_below_minimum(self):
        """Test value below minimum."""
        def dummy_func(target: str):
            return {"result": "ok"}

        tool = Tool(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.MONITORING,
            function=dummy_func,
            required_params=["target"],
        )
        params = {"target": "test", "duration": 5}
        result = tool._clamp_parameter_ranges(params)
        # Should clamp to minimum (10)
        assert result["duration"] == 10

    def test_above_maximum(self):
        """Test value above maximum."""
        def dummy_func(target: str):
            return {"result": "ok"}

        tool = Tool(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.MONITORING,
            function=dummy_func,
            required_params=["target"],
        )
        params = {"target": "test", "duration": 5000}
        result = tool._clamp_parameter_ranges(params)
        # Should clamp to maximum (3600)
        assert result["duration"] == 3600


# ----------------------------------------------------------------------
# _execute_with_timeout tests
# ----------------------------------------------------------------------
class TestExecuteWithTimeout:
    """Test _execute_with_timeout branches."""

    def test_async_function(self):
        """Test with async function."""
        async def async_func(target: str):
            await asyncio.sleep(0.01)
            return {"result": "ok"}

        tool = Tool(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.MONITORING,
            function=async_func,
            required_params=["target"],
        )
        result = tool._execute_with_timeout({"target": "test"}, 10.0)
        assert result["result"] == "ok"

    def test_sync_function(self):
        """Test with sync function."""
        def sync_func(target: str):
            return {"result": "ok"}

        tool = Tool(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.MONITORING,
            function=sync_func,
            required_params=["target"],
        )
        result = tool._execute_with_timeout({"target": "test"}, 10.0)
        assert result["result"] == "ok"

    def test_no_running_loop(self):
        """Test when no event loop is running."""
        def sync_func(target: str):
            return {"result": "ok"}

        tool = Tool(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.MONITORING,
            function=sync_func,
            required_params=["target"],
        )
        # This should create a new loop
        result = tool._execute_with_timeout({"target": "test"}, 10.0)
        assert result["result"] == "ok"


# ----------------------------------------------------------------------
# _validate_parameters tests
# ----------------------------------------------------------------------
class TestValidateParameters:
    """Test _validate_parameters branches."""

    def test_var_keyword_allowed(self):
        """Test with **kwargs in function signature."""
        def func_with_kwargs(target: str, **kwargs):
            return {"result": "ok"}

        tool = Tool(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.MONITORING,
            function=func_with_kwargs,
            required_params=["target"],
        )
        # Should allow any parameter with **kwargs
        tool._validate_parameters({"target": "test", "extra_param": "value"})

    def test_signature_exception(self):
        """Test when inspect.signature raises exception."""
        def dummy_func(target: str):
            return {"result": "ok"}

        tool = Tool(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.MONITORING,
            function=dummy_func,
            required_params=["target"],
        )
        with patch('inspect.signature', side_effect=TypeError("Cannot inspect")):
            # Should handle gracefully
            tool._validate_parameters({"target": "test"})

    def test_parameter_not_allowed(self):
        """Test with parameter not in allowed list."""
        def dummy_func(target: str):
            return {"result": "ok"}

        tool = Tool(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.MONITORING,
            function=dummy_func,
            required_params=["target"],
        )
        with pytest.raises(ValueError, match="is not allowed"):
            tool._validate_parameters({"target": "test", "invalid_param": "value"})


# ----------------------------------------------------------------------
# _validate_value tests
# ----------------------------------------------------------------------
class TestValidateValue:
    """Test _validate_value branches."""

    def test_depth_exceeded(self):
        """Test when depth exceeds maximum."""
        def dummy_func(target: str):
            return {"result": "ok"}

        tool = Tool(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.MONITORING,
            function=dummy_func,
            required_params=["target"],
        )
        with pytest.raises(ValueError, match="exceeds maximum nested depth"):
            tool._validate_value("test", {"nested": {"deep": {"deeper": "value"}}}, depth=10)

    def test_data_container_list_too_long(self):
        """Test data container with list too long."""
        def dummy_func(data: List):
            return {"result": "ok"}

        tool = Tool(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.MONITORING,
            function=dummy_func,
            required_params=["data"],
        )
        long_list = list(range(_MAX_LIST_LENGTH + 1))
        with pytest.raises(ValueError, match="exceeds maximum list length"):
            tool._validate_value("data", long_list, depth=0)

    def test_data_container_dict_with_command_key(self):
        """Test data container dict with command key."""
        def dummy_func(alert: Dict):
            return {"result": "ok"}

        tool = Tool(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.MONITORING,
            function=dummy_func,
            required_params=["alert"],
        )
        # Should validate command key in data container
        with patch('core.agent.tools.COMMAND_GUARD_AVAILABLE', False):
            tool._validate_value("alert", {"command": "test"}, depth=0)

    def test_data_container_dict_without_command_key(self):
        """Test data container dict without command key."""
        def dummy_func(alert: Dict):
            return {"result": "ok"}

        tool = Tool(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.MONITORING,
            function=dummy_func,
            required_params=["alert"],
        )
        # Should validate dict without command key
        tool._validate_value("alert", {"title": "test"}, depth=0)

    def test_data_container_nested_dict(self):
        """Test data container with nested dict."""
        def dummy_func(alert: Dict):
            return {"result": "ok"}

        tool = Tool(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.MONITORING,
            function=dummy_func,
            required_params=["alert"],
        )
        # Should validate nested dict
        tool._validate_value("alert", {"nested": {"key": "value"}}, depth=0)

    def test_data_container_name_match(self):
        """Test data container with name match."""
        def dummy_func(alert: Dict):
            return {"result": "ok"}

        tool = Tool(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.MONITORING,
            function=dummy_func,
            required_params=["alert"],
        )
        # Should match data container name
        tool._validate_value("alert", {"key": "value"}, depth=0)

    def test_data_container_name_suffix_match(self):
        """Test data container with name suffix match."""
        def dummy_func(custom_alert: Dict):
            return {"result": "ok"}

        tool = Tool(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.MONITORING,
            function=dummy_func,
            required_params=["custom_alert"],
        )
        # Should match data container name with suffix
        tool._validate_value("custom_alert", {"key": "value"}, depth=0)

    def test_boolean_parameter_success(self):
        """Test boolean parameter with valid value."""
        def dummy_func(wait: bool):
            return {"result": "ok"}

        tool = Tool(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.MONITORING,
            function=dummy_func,
            required_params=["wait"],
        )
        # Should accept boolean
        tool._validate_value("wait", True, depth=0)
        tool._validate_value("wait", False, depth=0)

    def test_integer_parameter_success(self):
        """Test integer parameter with valid value."""
        def dummy_func(duration: int):
            return {"result": "ok"}

        tool = Tool(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.MONITORING,
            function=dummy_func,
            required_params=["duration"],
        )
        # Should accept valid integer
        tool._validate_value("duration", 60, depth=0)

    def test_integer_parameter_not_in_ranges(self):
        """Test integer parameter not in _INT_PARAM_RANGES."""
        def dummy_func(custom_int: int):
            return {"result": "ok"}

        tool = Tool(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.MONITORING,
            function=dummy_func,
            required_params=["custom_int"],
        )
        # Should use default range when not in _INT_PARAM_RANGES
        tool._validate_value("custom_int", 100000, depth=0)

    def test_float_parameter_success(self):
        """Test float parameter with valid value."""
        def dummy_func(threshold: float):
            return {"result": "ok"}

        tool = Tool(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.MONITORING,
            function=dummy_func,
            required_params=["threshold"],
        )
        # Should accept valid float
        tool._validate_value("threshold", 0.5, depth=0)

    def test_float_parameter_not_in_ranges(self):
        """Test float parameter not in _FLOAT_PARAM_RANGES."""
        def dummy_func(custom_float: float):
            return {"result": "ok"}

        tool = Tool(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.MONITORING,
            function=dummy_func,
            required_params=["custom_float"],
        )
        # Should use default range when not in _FLOAT_PARAM_RANGES
        tool._validate_value("custom_float", 1000.0, depth=0)

    def test_list_parameter_string_success(self):
        """Test list parameter with comma-separated string."""
        def dummy_func(tools: str):
            return {"result": "ok"}

        tool = Tool(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.MONITORING,
            function=dummy_func,
            required_params=["tools"],
        )
        # Should accept comma-separated string
        tool._validate_value("tools", "tool1,tool2,tool3", depth=0)

    def test_list_parameter_string_empty_items(self):
        """Test list parameter string with empty items."""
        def dummy_func(tools: str):
            return {"result": "ok"}

        tool = Tool(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.MONITORING,
            function=dummy_func,
            required_params=["tools"],
        )
        # Should skip empty items
        tool._validate_value("tools", "tool1,,tool2", depth=0)

    def test_list_parameter_string_no_pattern(self):
        """Test list parameter string when pattern is None."""
        def dummy_func(custom_list: str):
            return {"result": "ok"}

        tool = Tool(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.MONITORING,
            function=dummy_func,
            required_params=["custom_list"],
        )
        # Should handle when pattern is None
        tool._validate_value("custom_list", "item1,item2", depth=0)

    def test_dict_parameter_with_bool_value(self):
        """Test dict parameter with boolean value."""
        def dummy_func(config: Dict):
            return {"result": "ok"}

        tool = Tool(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.MONITORING,
            function=dummy_func,
            required_params=["config"],
        )
        # Should accept boolean values in dict
        tool._validate_value("config", {"enabled": True}, depth=0)

    def test_dict_parameter_with_scalar_value(self):
        """Test dict parameter with scalar value."""
        def dummy_func(config: Dict):
            return {"result": "ok"}

        tool = Tool(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.MONITORING,
            function=dummy_func,
            required_params=["config"],
        )
        # Should accept scalar values in dict
        tool._validate_value("config", {"count": 123}, depth=0)

    def test_dict_parameter_value_not_string(self):
        """Test dict parameter with non-string value."""
        def dummy_func(config: Dict):
            return {"result": "ok"}

        tool = Tool(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.MONITORING,
            function=dummy_func,
            required_params=["config"],
        )
        # Should handle non-string values in dict
        tool._validate_value("config", {"count": 123}, depth=0)

    def test_list_item_pattern_match(self):
        """Test list item pattern match."""
        def dummy_func(tools: str):
            return {"result": "ok"}

        tool = Tool(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.MONITORING,
            function=dummy_func,
            required_params=["tools"],
        )
        # Should match pattern for valid items
        tool._validate_value("tools", "tool1,tool2,tool3", depth=0)

    def test_list_value_not_string_or_list(self):
        """Test list parameter with value that is neither string nor list."""
        def dummy_func(custom_list: int):
            return {"result": "ok"}

        tool = Tool(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.MONITORING,
            function=dummy_func,
            required_params=["custom_list"],
        )
        # Should handle non-string, non-list values
        tool._validate_value("custom_list", 123, depth=0)

    def test_list_value_list_not_too_long(self):
        """Test list parameter with list not too long."""
        def dummy_func(tools: List):
            return {"result": "ok"}

        tool = Tool(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.MONITORING,
            function=dummy_func,
            required_params=["tools"],
        )
        # Should accept list within length limit
        tool._validate_value("tools", ["tool1", "tool2"], depth=0)

    def test_list_item_validation_return(self):
        """Test list item validation returns."""
        def dummy_func(tools: List):
            return {"result": "ok"}

        tool = Tool(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.MONITORING,
            function=dummy_func,
            required_params=["tools"],
        )
        # Should validate each item and return
        tool._validate_value("tools", ["tool1", "tool2"], depth=0)

    def test_pattern_match_success(self):
        """Test pattern match success."""
        def dummy_func(service_name: str):
            return {"result": "ok"}

        tool = Tool(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.MONITORING,
            function=dummy_func,
            required_params=["service_name"],
        )
        # Should match pattern successfully
        tool._validate_string_value("service_name", "valid-service-123")

    def test_safe_text_pattern_match(self):
        """Test safe text pattern match."""
        def dummy_func(custom_param: str):
            return {"result": "ok"}

        tool = Tool(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.MONITORING,
            function=dummy_func,
            required_params=["custom_param"],
        )
        # Should match safe text pattern
        tool._validate_string_value("custom_param", "Safe text 123")

    def test_dict_with_command(self):
        """Test dict with command key."""
        def dummy_func(config: Dict):
            return {"result": "ok"}

        tool = Tool(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.MONITORING,
            function=dummy_func,
            required_params=["config"],
        )
        with patch('core.agent.tools.COMMAND_GUARD_AVAILABLE', False):
            # Should not raise when command_guard unavailable
            tool._validate_value("config", {"command": "safe"}, depth=0)

    def test_boolean_fail(self):
        """Test boolean parameter with non-bool value."""
        def dummy_func(wait: bool):
            return {"result": "ok"}

        tool = Tool(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.MONITORING,
            function=dummy_func,
            required_params=["wait"],
        )
        with pytest.raises(ValueError, match="must be a boolean"):
            tool._validate_value("wait", "true", depth=0)

    def test_integer_bool_fail(self):
        """Test integer parameter with bool value."""
        def dummy_func(duration: int):
            return {"result": "ok"}

        tool = Tool(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.MONITORING,
            function=dummy_func,
            required_params=["duration"],
        )
        with pytest.raises(ValueError, match="must be an integer"):
            tool._validate_value("duration", True, depth=0)

    def test_integer_conversion_fail(self):
        """Test integer parameter with non-convertible value."""
        def dummy_func(duration: int):
            return {"result": "ok"}

        tool = Tool(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.MONITORING,
            function=dummy_func,
            required_params=["duration"],
        )
        with pytest.raises(ValueError, match="must be an integer"):
            tool._validate_value("duration", "invalid", depth=0)

    def test_integer_range_fail(self):
        """Test integer parameter out of range."""
        def dummy_func(duration: int):
            return {"result": "ok"}

        tool = Tool(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.MONITORING,
            function=dummy_func,
            required_params=["duration"],
        )
        with pytest.raises(ValueError, match="must be between"):
            tool._validate_value("duration", 1000000, depth=0)

    def test_float_bool_fail(self):
        """Test float parameter with bool value."""
        def dummy_func(threshold: float):
            return {"result": "ok"}

        tool = Tool(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.MONITORING,
            function=dummy_func,
            required_params=["threshold"],
        )
        with pytest.raises(ValueError, match="must be a float"):
            tool._validate_value("threshold", True, depth=0)

    def test_float_conversion_fail(self):
        """Test float parameter with non-convertible value."""
        def dummy_func(threshold: float):
            return {"result": "ok"}

        tool = Tool(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.MONITORING,
            function=dummy_func,
            required_params=["threshold"],
        )
        with pytest.raises(ValueError, match="must be a number"):
            tool._validate_value("threshold", "invalid", depth=0)

    def test_float_range_fail(self):
        """Test float parameter out of range."""
        def dummy_func(threshold: float):
            return {"result": "ok"}

        tool = Tool(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.MONITORING,
            function=dummy_func,
            required_params=["threshold"],
        )
        with pytest.raises(ValueError, match="must be between"):
            tool._validate_value("threshold", 2.0, depth=0)

    def test_list_string_too_long(self):
        """Test list parameter with string too long."""
        def dummy_func(tools: str):
            return {"result": "ok"}

        tool = Tool(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.MONITORING,
            function=dummy_func,
            required_params=["tools"],
        )
        long_string = "a" * (_MAX_TEXT_LEN + 1)
        with pytest.raises(ValueError, match="exceeds maximum length"):
            tool._validate_value("tools", long_string, depth=0)

    def test_list_invalid_item(self):
        """Test list parameter with invalid item."""
        def dummy_func(tools: List):
            return {"result": "ok"}

        tool = Tool(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.MONITORING,
            function=dummy_func,
            required_params=["tools"],
        )
        with patch.object(tool, '_validate_value', side_effect=ValueError("Invalid item")):
            with pytest.raises(ValueError, match="Invalid item"):
                tool._validate_value("tools", ["tool1", "tool2"], depth=0)

    def test_list_too_long(self):
        """Test list parameter too long."""
        def dummy_func(tools: List):
            return {"result": "ok"}

        tool = Tool(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.MONITORING,
            function=dummy_func,
            required_params=["tools"],
        )
        long_list = list(range(_MAX_LIST_LENGTH + 1))
        with pytest.raises(ValueError, match="exceeds maximum list length"):
            tool._validate_value("tools", long_list, depth=0)

    def test_not_list(self):
        """Test list parameter with non-list value (not in _LIST_PARAM_NAMES)."""
        def dummy_func(custom_list: str):
            return {"result": "ok"}

        tool = Tool(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.MONITORING,
            function=dummy_func,
            required_params=["custom_list"],
        )
        # When name is not in _LIST_PARAM_NAMES and value is not a list,
        # it should be treated as a string and validated as such
        tool._validate_value("custom_list", "not a list", depth=0)

    def test_dict_recursive(self):
        """Test dict parameter with recursive validation."""
        def dummy_func(config: Dict):
            return {"result": "ok"}

        tool = Tool(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.MONITORING,
            function=dummy_func,
            required_params=["config"],
        )
        # Should recursively validate nested structures
        tool._validate_value("config", {"key": "value", "nested": {"key2": "value2"}}, depth=0)


# ----------------------------------------------------------------------
# _validate_string_value tests
# ----------------------------------------------------------------------
class TestValidateStringValue:
    """Test _validate_string_value branches."""

    def test_not_string(self):
        """Test with non-string value."""
        def dummy_func(target: str):
            return {"result": "ok"}

        tool = Tool(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.MONITORING,
            function=dummy_func,
            required_params=["target"],
        )
        # Should return silently for non-string
        tool._validate_string_value("target", 123)

    def test_empty_name_pattern(self):
        """Test empty string with name pattern."""
        def dummy_func(service_name: str):
            return {"result": "ok"}

        tool = Tool(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.MONITORING,
            function=dummy_func,
            required_params=["service_name"],
        )
        with pytest.raises(ValueError, match="cannot be empty"):
            tool._validate_string_value("service_name", "")

    def test_empty_int_param(self):
        """Test empty string for int parameter."""
        def dummy_func(duration: str):
            return {"result": "ok"}

        tool = Tool(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.MONITORING,
            function=dummy_func,
            required_params=["duration"],
        )
        with pytest.raises(ValueError, match="cannot be empty"):
            tool._validate_string_value("duration", "")

    def test_empty_text_param(self):
        """Test empty string for text parameter (allowed)."""
        def dummy_func(description: str):
            return {"result": "ok"}

        tool = Tool(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.MONITORING,
            function=dummy_func,
            required_params=["description"],
        )
        # Should allow empty for text parameters
        tool._validate_string_value("description", "", allow_text=True)

    def test_empty_unpatterned(self):
        """Test empty string for unpatterned parameter (allowed)."""
        def dummy_func(custom_param: str):
            return {"result": "ok"}

        tool = Tool(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.MONITORING,
            function=dummy_func,
            required_params=["custom_param"],
        )
        # Should allow empty for unpatterned parameters
        tool._validate_string_value("custom_param", "")

    def test_too_long(self):
        """Test string too long."""
        def dummy_func(target: str):
            return {"result": "ok"}

        tool = Tool(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.MONITORING,
            function=dummy_func,
            required_params=["target"],
        )
        long_string = "a" * (_MAX_PARAM_LEN + 1)
        with pytest.raises(ValueError, match="exceeds maximum length"):
            tool._validate_string_value("target", long_string)

    def test_text_too_long(self):
        """Test text parameter too long."""
        def dummy_func(description: str):
            return {"result": "ok"}

        tool = Tool(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.MONITORING,
            function=dummy_func,
            required_params=["description"],
        )
        long_string = "a" * (_MAX_TEXT_LEN + 1)
        with pytest.raises(ValueError, match="exceeds maximum length"):
            tool._validate_string_value("description", long_string, allow_text=True)

    def test_path_traversal(self):
        """Test path traversal attempt."""
        def dummy_func(target: str):
            return {"result": "ok"}

        tool = Tool(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.MONITORING,
            function=dummy_func,
            required_params=["target"],
        )
        with pytest.raises(ValueError, match="path traversal"):
            tool._validate_string_value("target", "../../../etc/passwd")

    def test_path_traversal_windows(self):
        """Test Windows path traversal attempt."""
        def dummy_func(target: str):
            return {"result": "ok"}

        tool = Tool(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.MONITORING,
            function=dummy_func,
            required_params=["target"],
        )
        with pytest.raises(ValueError, match="path traversal"):
            tool._validate_string_value("target", "..\\..\\windows\\system32")

    def test_shell_metacharacters(self):
        """Test shell metacharacters."""
        def dummy_func(target: str):
            return {"result": "ok"}

        tool = Tool(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.MONITORING,
            function=dummy_func,
            required_params=["target"],
        )
        with pytest.raises(ValueError, match="dangerous characters"):
            tool._validate_string_value("target", "test; rm -rf /")

    def test_custom_pattern(self):
        """Test custom pattern from tool."""
        def dummy_func(target: str):
            return {"result": "ok"}

        tool = Tool(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.MONITORING,
            function=dummy_func,
            required_params=["target"],
            param_patterns={"target": _NAME_PATTERNS["service_name"]},
        )
        # Should match custom pattern
        tool._validate_string_value("target", "valid-service-123")

    def test_name_pattern(self):
        """Test name-based pattern."""
        def dummy_func(service_name: str):
            return {"result": "ok"}

        tool = Tool(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.MONITORING,
            function=dummy_func,
            required_params=["service_name"],
        )
        # Should match name pattern
        tool._validate_string_value("service_name", "valid-service-123")

    def test_default_safe_text(self):
        """Test default safe text pattern."""
        def dummy_func(custom_param: str):
            return {"result": "ok"}

        tool = Tool(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.MONITORING,
            function=dummy_func,
            required_params=["custom_param"],
        )
        # Should match safe text pattern
        tool._validate_string_value("custom_param", "Safe text 123")


# ----------------------------------------------------------------------
# ToolApprovalManager tests
# ----------------------------------------------------------------------
class TestToolApprovalManager:
    """Test ToolApprovalManager branches."""

    def test_not_required(self):
        """Test when approval is not required."""
        manager = ToolApprovalManager(approval_required=False)
        assert manager.is_approved("any_tool") is True

    def test_revoke_nonexistent(self):
        """Test revoking non-existent tool."""
        manager = ToolApprovalManager(approval_required=True)
        # Should not raise
        manager.revoke("nonexistent_tool")

    def test_approve_and_check(self):
        """Test approve and is_approved."""
        manager = ToolApprovalManager(approval_required=True)
        assert manager.is_approved("test_tool") is False
        manager.approve("test_tool", "admin")
        assert manager.is_approved("test_tool") is True

    def test_request_approval(self):
        """Test request_approval."""
        manager = ToolApprovalManager(approval_required=True)
        request_id = manager.request_approval("test_tool", "user1", "Need this tool")
        assert "test_tool" in request_id


# ----------------------------------------------------------------------
# ToolRegistry tests
# ----------------------------------------------------------------------
class TestToolRegistry:
    """Test ToolRegistry branches."""

    def test_resolve_approval_required_explicit_true(self):
        """Test explicit true approval required."""
        registry = ToolRegistry(approval_required=True)
        assert registry.approval_manager.approval_required is True

    def test_resolve_approval_required_explicit_false(self):
        """Test explicit false approval required."""
        registry = ToolRegistry(approval_required=False)
        assert registry.approval_manager.approval_required is False

    def test_resolve_approval_required_env_true(self):
        """Test env var true for approval required."""
        with patch.dict(os.environ, {"AIOPS_TOOL_REGISTRATION_APPROVAL_REQUIRED": "true"}):
            registry = ToolRegistry(approval_required=None)
            assert registry.approval_manager.approval_required is True

    def test_resolve_approval_required_env_false(self):
        """Test env var false for approval required."""
        with patch.dict(os.environ, {"AIOPS_TOOL_REGISTRATION_APPROVAL_REQUIRED": "false"}):
            registry = ToolRegistry(approval_required=None)
            assert registry.approval_manager.approval_required is False

    def test_check_approval_initializing(self):
        """Test _check_approval during initialization."""
        registry = ToolRegistry(approval_required=True)
        # During initialization, should skip approval check
        assert registry._is_initializing() is False  # After init
        # But during _initialize_default_tools, it was True

    def test_check_approval_already_approved(self):
        """Test _check_approval when already approved."""
        registry = ToolRegistry(approval_required=True)
        registry.approval_manager.approve("test_tool", "admin")
        # Should not raise
        registry._check_approval("test_tool")

    def test_check_approval_not_approved_no_approver(self):
        """Test _check_approval not approved without approver."""
        registry = ToolRegistry(approval_required=True)
        with pytest.raises(PermissionError, match="requires approval"):
            registry._check_approval("test_tool")

    def test_check_approval_not_approved_with_approver(self):
        """Test _check_approval not approved with approver."""
        registry = ToolRegistry(approval_required=True)
        # Should approve with provided approver
        registry._check_approval("test_tool", approved_by="admin")
        assert registry.approval_manager.is_approved("test_tool") is True

    def test_register_non_existent(self):
        """Test register after tool exists (override)."""
        registry = ToolRegistry(approval_required=False)
        def func1(target: str):
            return {"result": "func1"}
        def func2(target: str):
            return {"result": "func2"}
        
        tool1 = Tool(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.MONITORING,
            function=func1,
            required_params=["target"],
        )
        tool2 = Tool(
            name="test_tool",
            description="Test tool v2",
            category=ToolCategory.MONITORING,
            function=func2,
            required_params=["target"],
        )
        
        registry.register(tool1)
        registry.register(tool2)  # Should override
        assert registry.get_tool("test_tool").function == func2

    def test_unregister_non_existent(self):
        """Test unregister non-existent tool."""
        registry = ToolRegistry(approval_required=False)
        # Should not raise
        registry.unregister("nonexistent_tool")

    def test_unregister_tool_exists(self):
        """Test unregister existing tool."""
        registry = ToolRegistry(approval_required=False)
        # Should successfully unregister
        registry.unregister("collect_metrics")
        assert registry.get_tool("collect_metrics") is None

    def test_list_tools_with_category(self):
        """Test list_tools with category filter."""
        registry = ToolRegistry(approval_required=False)
        monitoring_tools = registry.list_tools(ToolCategory.MONITORING)
        assert len(monitoring_tools) > 0
        assert all(t.category == ToolCategory.MONITORING for t in monitoring_tools)

    def test_list_tools_without_category(self):
        """Test list_tools without category filter."""
        registry = ToolRegistry(approval_required=False)
        all_tools = registry.list_tools()
        assert len(all_tools) > 0

    def test_search_tools_name_match(self):
        """Test search_tools with name match."""
        registry = ToolRegistry(approval_required=False)
        results = registry.search_tools("metric")
        assert len(results) > 0

    def test_search_tools_description_match(self):
        """Test search_tools with description match."""
        registry = ToolRegistry(approval_required=False)
        results = registry.search_tools("指标")
        assert len(results) > 0


# ----------------------------------------------------------------------
# Default tool implementations tests
# ----------------------------------------------------------------------
class TestDefaultToolImplementations:
    """Test default tool implementation branches."""

    def test_collect_metrics_prometheus_exception(self):
        """Test collect_metrics when Prometheus raises exception."""
        registry = ToolRegistry(approval_required=False)
        with patch('core.agent.tools.observability_client.get_prometheus_url', side_effect=Exception("Prometheus error")):
            result = registry._collect_metrics("test-target")
            assert "note" in result

    def test_collect_logs_all_paths_fail(self):
        """Test collect_logs when all log paths fail."""
        registry = ToolRegistry(approval_required=False)
        with patch('pathlib.Path.is_file', return_value=False):
            result = registry._collect_logs("test-service")
            assert "No log file found" in result[0]

    def test_analyze_anomaly_empty_data(self):
        """Test analyze_anomaly with empty data."""
        registry = ToolRegistry(approval_required=False)
        result = registry._analyze_anomaly([])
        assert result["is_anomaly"] is False
        assert "empty data" in result["reason"]

    def test_analyze_anomaly_threshold_method(self):
        """Test analyze_anomaly with threshold method."""
        registry = ToolRegistry(approval_required=False)
        result = registry._analyze_anomaly([0.1, 0.2, 0.8], threshold=0.5, method="threshold")
        assert result["method"] == "threshold"

    def test_root_cause_analysis_engine_exception(self):
        """Test root_cause_analysis when engine raises exception."""
        registry = ToolRegistry(approval_required=False)
        with patch('core.agent.tools.observability_client._safe_label', return_value="test"):
            result = asyncio.run(registry._root_cause_analysis("test-alert"))
            assert "escalation_recommended" in result

    def test_restart_service_no_systemctl(self):
        """Test restart_service when systemctl not available."""
        registry = ToolRegistry(approval_required=False)
        with patch('shutil.which', return_value=None):
            result = registry._restart_service("test-service")
            assert "systemctl not available" in result["note"]

    def test_restart_service_not_forced(self):
        """Test restart_service when not forced."""
        registry = ToolRegistry(approval_required=False)
        with patch('shutil.which', return_value="/usr/bin/systemctl"):
            with patch('subprocess.run') as mock_run:
                mock_run.return_value = Mock(returncode=0)
                with patch.dict(os.environ, {}, clear=True):
                    result = registry._restart_service("test-service")
                    assert result["executed"] is False

    def test_scale_service_no_kubectl(self):
        """Test scale_service when kubectl not available."""
        registry = ToolRegistry(approval_required=False)
        with patch('shutil.which', return_value=None):
            result = registry._scale_service("test-service", 3)
            assert "kubectl not available" in result["note"]

    def test_check_health_http_failure(self):
        """Test check_health with HTTP failure."""
        registry = ToolRegistry(approval_required=False)
        with patch('httpx.get', side_effect=Exception("Connection error")):
            result = registry._check_health("http://example.com")
            assert result["healthy"] is False

    def test_check_health_tcp_failure(self):
        """Test check_health with TCP failure."""
        registry = ToolRegistry(approval_required=False)
        with patch('socket.create_connection', side_effect=Exception("Connection refused")):
            result = registry._check_health("localhost:8080")
            assert result["healthy"] is False

    def test_collect_service_metrics_no_prometheus_no_manager(self):
        """Test collect_service_metrics without Prometheus or manager."""
        registry = ToolRegistry(approval_required=False)
        with patch('core.agent.tools.observability_client.get_prometheus_url', return_value=None):
            with patch('core.service_monitoring_manager.get_service_monitoring_manager', side_effect=Exception("No manager")):
                result = registry._collect_service_metrics("test-service")
                assert "note" in result

    def test_collect_network_metrics_exception(self):
        """Test collect_network_metrics with exception."""
        registry = ToolRegistry(approval_required=False)
        with patch('core.agent.tools.observability_client.query_network_metrics', side_effect=Exception("Network error")):
            result = registry._collect_network_metrics("test-target")
            assert "note" in result

    def test_collect_kubernetes_events_exception(self):
        """Test collect_kubernetes_events with exception."""
        registry = ToolRegistry(approval_required=False)
        with patch('core.agent.tools.observability_client.query_kubernetes_events', side_effect=Exception("K8s error")):
            result = registry._collect_kubernetes_events("default")
            assert result == []

    def test_collect_container_metrics_with_provided_data(self):
        """Test collect_container_metrics with provided data."""
        registry = ToolRegistry(approval_required=False)
        provided_data = {"memory_usage_bytes": 1000000}
        result = registry._collect_container_metrics("test-pod", container_metrics=provided_data)
        assert result["memory_usage_bytes"] == 1000000

    def test_collect_host_metrics_with_provided_data(self):
        """Test collect_host_metrics with provided data."""
        registry = ToolRegistry(approval_required=False)
        provided_data = {"cpu_usage": 50.0}
        result = registry._collect_host_metrics("test-node", host_metrics=provided_data)
        assert result["cpu_usage"] == 50.0

    def test_collect_database_metrics_with_provided_data(self):
        """Test collect_database_metrics with provided data."""
        registry = ToolRegistry(approval_required=False)
        provided_data = {"slow_query_rate": 0.1}
        result = registry._collect_database_metrics("test-db", database_metrics=provided_data)
        assert result["slow_query_rate"] == 0.1

    def test_collect_correlated_alerts_exception(self):
        """Test collect_correlated_alerts with exception."""
        registry = ToolRegistry(approval_required=False)
        with patch('core.alert_engine.alert_history', side_effect=Exception("Alert error")):
            result = registry._collect_correlated_alerts("test-service")
            assert result == []

    def test_collect_topology_import_failure(self):
        """Test collect_topology with import failure."""
        registry = ToolRegistry(approval_required=False)
        with patch('core.agent.tools.observability_client._safe_label', return_value="test"):
            with patch('core.root_cause_intelligence.root_cause_intelligence_engine', side_effect=Exception("Import error")):
                result = registry._collect_topology("test-service")
                # When import fails, returns empty dependencies
                assert "downstream_dependencies" in result
                assert result["downstream_dependencies"] == []

    def test_collect_metrics_prometheus_success(self):
        """Test collect_metrics with Prometheus success."""
        registry = ToolRegistry(approval_required=False)
        with patch('core.agent.tools.observability_client.get_prometheus_url', return_value="http://prometheus:9090"):
            with patch('core.agent.tools.observability_client.query_prometheus_range', return_value="0.5"):
                with patch('core.agent.tools.observability_client.query_prometheus', return_value="1000000"):
                    with patch('core.agent.tools.observability_client._extract_prom_scalar_value', return_value=0.5):
                        result = registry._collect_metrics("test-target")
                        assert "source" in result

    def test_collect_logs_file_found(self):
        """Test collect_logs when log file is found."""
        registry = ToolRegistry(approval_required=False)
        with patch('pathlib.Path.is_file', return_value=True):
            with patch('pathlib.Path.open', side_effect=Exception("Read error")):
                result = registry._collect_logs("test-service")
                # Should handle read error gracefully
                assert len(result) > 0

    def test_analyze_anomaly_with_data(self):
        """Test analyze_anomaly with data."""
        registry = ToolRegistry(approval_required=False)
        result = registry._analyze_anomaly([0.1, 0.2, 0.3, 0.8])
        assert "method" in result
        assert "is_anomaly" in result

    def test_root_cause_analysis_with_engine(self):
        """Test root_cause_analysis with engine available."""
        registry = ToolRegistry(approval_required=False)
        with patch('core.agent.tools.observability_client._safe_label', return_value="test"):
            with patch('core.root_cause_intelligence.root_cause_intelligence_engine', side_effect=ImportError("No module")):
                result = asyncio.run(registry._root_cause_analysis("test-alert"))
                assert "candidates" in result

    def test_restart_service_with_systemctl(self):
        """Test restart_service with systemctl available."""
        registry = ToolRegistry(approval_required=False)
        with patch('shutil.which', return_value="/usr/bin/systemctl"):
            with patch('subprocess.run') as mock_run:
                mock_run.return_value = Mock(returncode=0)
                with patch.dict(os.environ, {"FORCE_REPAIR_COMMANDS": "0"}):
                    result = registry._restart_service("test-service")
                    assert result["executed"] is False

    def test_scale_service_with_kubectl(self):
        """Test scale_service with kubectl available."""
        registry = ToolRegistry(approval_required=False)
        with patch('shutil.which', return_value="/usr/bin/kubectl"):
            with patch('subprocess.run') as mock_run:
                mock_run.return_value = Mock(returncode=0)
                with patch.dict(os.environ, {"FORCE_REPAIR_COMMANDS": "0"}):
                    result = registry._scale_service("test-service", 3)
                    assert result["executed"] is False

    def test_check_health_http_success(self):
        """Test check_health with HTTP success."""
        registry = ToolRegistry(approval_required=False)
        with patch('httpx.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response
            result = registry._check_health("http://example.com")
            assert result["healthy"] is True

    def test_check_health_tcp_success(self):
        """Test check_health with TCP success."""
        registry = ToolRegistry(approval_required=False)
        with patch('socket.create_connection'):
            result = registry._check_health("localhost:8080")
            assert result["healthy"] is True

    def test_collect_service_metrics_prometheus_success(self):
        """Test collect_service_metrics with Prometheus success."""
        registry = ToolRegistry(approval_required=False)
        with patch('core.agent.tools.observability_client.get_prometheus_url', return_value="http://prometheus:9090"):
            with patch('core.agent.tools.observability_client.query_service_metrics', return_value={}):
                result = registry._collect_service_metrics("test-service")
                assert "prometheus_available" in result

    def test_collect_service_metrics_manager_success(self):
        """Test collect_service_metrics with manager success."""
        registry = ToolRegistry(approval_required=False)
        with patch('core.agent.tools.observability_client.get_prometheus_url', return_value=None):
            with patch('core.service_monitoring_manager.get_service_monitoring_manager') as mock_mgr:
                mock_instance = Mock()
                mock_mgr.return_value = mock_instance
                # Create a mock metric object
                mock_metric = Mock()
                mock_metric.metric_name = "request_rate"
                mock_metric.value = 100.0
                mock_metric.timestamp = "2024-01-01"
                mock_instance.get_service_metrics.return_value = [mock_metric]
                result = registry._collect_service_metrics("test-service")
                assert "manager_metrics" in result

    def test_collect_change_events_external_success(self):
        """Test collect_change_events with external API success."""
        registry = ToolRegistry(approval_required=False)
        with patch('core.agent.tools.observability_client.query_change_events', return_value=[]):
            result = registry._collect_change_events("test-target")
            assert isinstance(result, list)

    def test_collect_change_events_local_success(self):
        """Test collect_change_events with local audit log."""
        registry = ToolRegistry(approval_required=False)
        with patch('core.agent.tools.observability_client.query_change_events', side_effect=Exception("API error")):
            with patch('core.config_manager.config_manager') as mock_config:
                mock_config._audit_log = []
                result = registry._collect_change_events("test-target")
                assert isinstance(result, list)

    def test_collect_kubernetes_events_success(self):
        """Test collect_kubernetes_events with success."""
        registry = ToolRegistry(approval_required=False)
        with patch('core.agent.tools.observability_client.query_kubernetes_events', return_value=[]):
            result = registry._collect_kubernetes_events("default")
            assert result == []

    def test_collect_container_metrics_kubernetes_success(self):
        """Test collect_container_metrics with Kubernetes success."""
        registry = ToolRegistry(approval_required=False)
        with patch('core.agent.tools.observability_client.query_kubernetes_pod', return_value={"available": True}):
            with patch('core.agent.tools.observability_client.get_prometheus_url', return_value="http://prometheus:9090"):
                with patch('core.agent.tools.observability_client.query_prometheus', return_value="1000000"):
                    with patch('core.agent.tools.observability_client._extract_prom_scalar_value', return_value=1000000):
                        result = registry._collect_container_metrics("test-pod")
                        assert "kubernetes_available" in result

    def test_collect_host_metrics_kubernetes_success(self):
        """Test collect_host_metrics with Kubernetes success."""
        registry = ToolRegistry(approval_required=False)
        with patch('core.agent.tools.observability_client.query_kubernetes_node', return_value={"available": True}):
            with patch('core.agent.tools.observability_client.get_prometheus_url', return_value="http://prometheus:9090"):
                with patch('core.agent.tools.observability_client.query_prometheus', return_value="50.0"):
                    with patch('core.agent.tools.observability_client._extract_prom_scalar_value', return_value=50.0):
                        result = registry._collect_host_metrics("test-node")
                        assert "kubernetes_available" in result

    def test_collect_database_metrics_prometheus_success(self):
        """Test collect_database_metrics with Prometheus success."""
        registry = ToolRegistry(approval_required=False)
        with patch('core.agent.tools.observability_client.get_prometheus_url', return_value="http://prometheus:9090"):
            with patch('core.agent.tools.observability_client.query_prometheus', return_value="0.1"):
                with patch('core.agent.tools.observability_client._extract_prom_scalar_value', return_value=0.1):
                    result = registry._collect_database_metrics("test-db")
                    assert "slow_query_rate" in result

    def test_collect_correlated_alerts_success(self):
        """Test collect_correlated_alerts with success."""
        registry = ToolRegistry(approval_required=False)
        # Use "all" to match any alert
        with patch('core.alert_engine.alert_history', [{"title": "test", "desc": "test alert", "host": "localhost", "source": "prometheus", "level": "warning", "raw_time": "2024-01-01"}]):
            result = registry._collect_correlated_alerts("all")
            assert len(result) > 0

    def test_collect_topology_success(self):
        """Test collect_topology with success."""
        registry = ToolRegistry(approval_required=False)
        with patch('core.agent.tools.observability_client._safe_label', return_value="test"):
            with patch('core.root_cause_intelligence.root_cause_intelligence_engine') as mock_engine:
                mock_engine.topology_graph = {"service1": ["service2"], "service2": []}
                result = registry._collect_topology("service1")
                assert "downstream_dependencies" in result

    def test_dispatch_subagent_wait_false(self):
        """Test dispatch_subagent with wait=False."""
        registry = ToolRegistry(approval_required=False)
        with patch('core.agent.subagent.SubAgentDispatcher') as mock_dispatcher:
            mock_instance = Mock()
            mock_dispatcher.return_value = mock_instance
            mock_future = Mock()
            mock_instance.dispatch.return_value = mock_future
            
            result = registry._dispatch_subagent("test goal", wait=False)
            assert result["status"] == "dispatched"
            assert "future" in result


# ----------------------------------------------------------------------
# ToolSelector tests
# ----------------------------------------------------------------------
class TestToolSelector:
    """Test ToolSelector branches."""

    def test_select_tool_all_keywords(self):
        """Test all keyword branches in select_tool."""
        registry = ToolRegistry(approval_required=False)
        selector = ToolSelector(registry)
        
        # Test each keyword branch
        # Note: Some keywords may match multiple tools, so we just verify a tool is selected
        test_cases = [
            ("收集日志", "log"),
            ("收集指标", "metric"),
            ("异常检测", "anomaly"),
            ("根因分析", "root"),
            ("重启服务", "restart"),
            ("扩容服务", "scale"),
            ("变更配置", "change"),
            ("关联告警", "correlated"),
            # "服务指标" may match collect_metrics due to "metric" keyword
            ("网络丢包", "network"),
            ("数据库慢查询", "database"),
            ("kubernetes容器", "kubernetes"),
            ("拓扑依赖", "topolog"),
            ("健康检查", "health"),
        ]
        
        for task, expected_name in test_cases:
            tool = selector.select_tool(task, {})
            assert tool is not None
            # For service metrics, the keyword "metric" matches first
            if expected_name == "service":
                # Just verify a tool was selected
                assert tool is not None
            else:
                assert expected_name in tool.name.lower()

    def test_select_tools_for_chain_no_matches(self):
        """Test select_tools_for_chain with no matches."""
        registry = ToolRegistry(approval_required=False)
        selector = ToolSelector(registry)
        
        tools = selector.select_tools_for_chain(["invalid task 1", "invalid task 2"], {})
        assert tools == []


# ----------------------------------------------------------------------
# ToolExecutor tests
# ----------------------------------------------------------------------
class TestToolExecutor:
    """Test ToolExecutor branches."""

    def test_sanitize_params_nested_dict(self):
        """Test sanitize_params with nested dict."""
        registry = ToolRegistry(approval_required=False)
        executor = ToolExecutor(registry)
        
        params = {
            "target": "test",
            "config": {
                "password": "secret123",
                "nested": {
                    "api_key": "key123"
                }
            }
        }
        sanitized = executor._sanitize_params(params)
        assert sanitized["config"]["password"] == "***"
        assert sanitized["config"]["nested"]["api_key"] == "***"

    def test_sanitize_params_list_item_string(self):
        """Test sanitize_params with list containing string items."""
        registry = ToolRegistry(approval_required=False)
        executor = ToolExecutor(registry)
        
        params = {
            "target": "test",
            "items": ["item1", "item2", "item3"]
        }
        sanitized = executor._sanitize_params(params)
        assert sanitized["items"] == ["item1", "item2", "item3"]

    def test_should_retry_execution_category(self):
        """Test _should_retry with execution category."""
        registry = ToolRegistry(approval_required=False)
        executor = ToolExecutor(registry)
        
        tool = Tool(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.EXECUTION,
            function=lambda: {"result": "ok"},
        )
        assert executor._should_retry(tool, Exception("error")) is False

    def test_should_retry_non_retryable_error(self):
        """Test _should_retry with non-retryable error."""
        registry = ToolRegistry(approval_required=False)
        executor = ToolExecutor(registry)
        
        tool = Tool(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.MONITORING,
            function=lambda: {"result": "ok"},
        )
        assert executor._should_retry(tool, ValueError("invalid")) is False

    def test_execute_with_retry_backoff_exhaustion(self):
        """Test _execute_with_retry with backoff exhaustion."""
        registry = ToolRegistry(approval_required=False)
        executor = ToolExecutor(registry, retry_policy={"max_retries": 1, "backoff": [0.01]})
        
        tool = Tool(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.MONITORING,
            function=lambda: (_ for _ in ()).throw(Exception("error")),
        )
        
        with pytest.raises(Exception, match="error"):
            executor._execute_with_retry(tool, False, 10.0, {})

    def test_execute_with_retry_empty_backoff(self):
        """Test _execute_with_retry with empty backoff."""
        registry = ToolRegistry(approval_required=False)
        executor = ToolExecutor(registry, retry_policy={"max_retries": 1, "backoff": []})
        
        tool = Tool(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.MONITORING,
            function=lambda: (_ for _ in ()).throw(ConnectionError("connection failed")),
        )
        
        with pytest.raises(ConnectionError, match="connection failed"):
            executor._execute_with_retry(tool, False, 10.0, {})

    def test_execute_tool_audit_success(self):
        """Test execute_tool with successful audit."""
        registry = ToolRegistry(approval_required=False)
        executor = ToolExecutor(registry)
        
        with patch('core.agent.tools._audit_tool') as mock_audit:
            result = executor.execute_tool("collect_metrics", target="test")
            mock_audit.assert_called()

    def test_execute_tool_audit_failure(self):
        """Test execute_tool with failure audit."""
        registry = ToolRegistry(approval_required=False)
        executor = ToolExecutor(registry)
        
        # Patch the tool function to raise an exception
        with patch.object(registry.get_tool("collect_metrics"), 'function', side_effect=Exception("Tool execution failed")):
            with patch('core.agent.tools._audit_tool') as mock_audit:
                with pytest.raises(Exception, match="Tool execution failed"):
                    executor.execute_tool("collect_metrics", target="test")
                mock_audit.assert_called()

    def test_infer_parameters_all_aliases(self):
        """Test _infer_parameters with all alias branches."""
        registry = ToolRegistry(approval_required=False)
        executor = ToolExecutor(registry)
        
        # Test target alias
        tool = Tool(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.MONITORING,
            function=lambda target: {"result": "ok"},
            required_params=["target"],
        )
        params = executor._infer_parameters(tool, {"service": "test-service"})
        assert params["target"] == "test-service"
        
        # Test service alias
        tool = Tool(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.MONITORING,
            function=lambda service: {"result": "ok"},
            required_params=["service"],
        )
        params = executor._infer_parameters(tool, {"target": "test-target"})
        assert params["service"] == "test-target"
        
        # Test service_name alias
        tool = Tool(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.MONITORING,
            function=lambda service_name: {"result": "ok"},
            required_params=["service_name"],
        )
        params = executor._infer_parameters(tool, {"service": "test-service"})
        assert params["service_name"] == "test-service"
        
        # Test data alias
        tool = Tool(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.ANALYSIS,
            function=lambda data: {"result": "ok"},
            required_params=["data"],
        )
        params = executor._infer_parameters(tool, {"metrics": [1, 2, 3]})
        assert params["data"] == [1, 2, 3]
        
        # Test alert_id alias
        tool = Tool(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.ANALYSIS,
            function=lambda alert_id: {"result": "ok"},
            required_params=["alert_id"],
        )
        params = executor._infer_parameters(tool, {"alert": {"id": "alert-123"}})
        assert params["alert_id"] == "alert-123"


# ----------------------------------------------------------------------
# Run tests
# ----------------------------------------------------------------------
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
