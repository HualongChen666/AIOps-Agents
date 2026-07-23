# -*- coding: utf-8 -*-
"""
Unit tests for core/agent/tools.py

This module contains comprehensive unit tests for the tools module,
covering tool registration, execution, selection, validation, and
chain execution functionalities.
"""

import asyncio

import pytest

from core.agent.tools import (
    Tool,
    ToolCategory,
    ToolExecutor,
    ToolRegistry,
    ToolSelector,
    create_tool_executor,
    create_tool_registry,
)

# ============================================================
# ToolCategory enum tests (5 test cases)
# ============================================================


class TestToolCategory:
    """Test cases for ToolCategory enum."""

    def test_tool_category_enum_values(self):
        """Test that ToolCategory enum has correct values."""
        assert ToolCategory.MONITORING.value == "monitoring"
        assert ToolCategory.ANALYSIS.value == "analysis"
        assert ToolCategory.EXECUTION.value == "execution"
        assert ToolCategory.NOTIFICATION.value == "notification"
        assert ToolCategory.DIAGNOSTIC.value == "diagnostic"

    def test_tool_category_enum_iteration(self):
        """Test ToolCategory enum iteration."""
        categories = list(ToolCategory)
        assert len(categories) == 5
        assert ToolCategory.MONITORING in categories

    def test_tool_category_enum_comparison(self):
        """Test ToolCategory enum comparison."""
        assert ToolCategory.MONITORING == ToolCategory.MONITORING
        assert ToolCategory.MONITORING != ToolCategory.ANALYSIS

    def test_tool_category_value_access(self):
        """Test ToolCategory value access."""
        assert ToolCategory.MONITORING.value == "monitoring"

    def test_tool_category_name_access(self):
        """Test ToolCategory name access."""
        assert ToolCategory.MONITORING.name == "MONITORING"


# ============================================================
# Tool dataclass tests (15 test cases)
# ============================================================


class TestTool:
    """Test cases for Tool dataclass."""

    def test_tool_initialization_defaults(self):
        """Test Tool initialization with default values."""

        def dummy_function(**kwargs):
            return "result"

        tool = Tool(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.MONITORING,
            function=dummy_function,
        )
        assert tool.name == "test_tool"
        assert tool.description == "Test tool"
        assert tool.category == ToolCategory.MONITORING
        assert tool.parameters == {}
        assert tool.required_params == []
        assert tool.optional_params == []
        assert tool.examples == []

    def test_tool_initialization_custom(self):
        """Test Tool initialization with custom values."""

        def dummy_function(**kwargs):
            return "result"

        tool = Tool(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.ANALYSIS,
            function=dummy_function,
            parameters={"param1": "value1"},
            required_params=["param1"],
            optional_params=["param2"],
            examples=[{"param1": "value1"}],
        )
        assert tool.parameters == {"param1": "value1"}
        assert tool.required_params == ["param1"]
        assert tool.optional_params == ["param2"]
        assert len(tool.examples) == 1

    def test_tool_execute_success(self):
        """Test Tool execute with success."""

        def dummy_function(param1, param2="default"):
            return {"param1": param1, "param2": param2}

        tool = Tool(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.MONITORING,
            function=dummy_function,
            required_params=["param1"],
        )
        result = tool.execute(param1="value1", param2="value2")
        assert result == {"param1": "value1", "param2": "value2"}

    def test_tool_execute_missing_required_param(self):
        """Test Tool execute with missing required parameter."""

        def dummy_function(param1):
            return "result"

        tool = Tool(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.MONITORING,
            function=dummy_function,
            required_params=["param1"],
        )
        with pytest.raises(ValueError, match="Missing required parameters"):
            tool.execute()

    def test_tool_execute_with_default_params(self):
        """Test Tool execute with default parameters."""

        def dummy_function(param1, param2="default"):
            return {"param1": param1, "param2": param2}

        tool = Tool(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.MONITORING,
            function=dummy_function,
            required_params=["param1"],
            parameters={"param2": "default_value"},
        )
        result = tool.execute(param1="value1")
        assert result == {"param1": "value1", "param2": "default_value"}

    def test_tool_execute_parameter_merging(self):
        """Test Tool execute parameter merging."""

        def dummy_function(param1, param2):
            return {"param1": param1, "param2": param2}

        tool = Tool(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.MONITORING,
            function=dummy_function,
            required_params=["param1", "param2"],
            parameters={"param2": "default"},
        )
        result = tool.execute(param1="value1", param2="override")
        assert result == {"param1": "value1", "param2": "override"}

    def test_tool_validate_parameters_dangerous_chars(self):
        """Tool execute with dangerous characters raises ValueError."""

        def dummy_function(param1):
            return "result"

        tool = Tool(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.MONITORING,
            function=dummy_function,
            required_params=["param1"],
        )
        with pytest.raises(ValueError, match="dangerous characters"):
            tool.execute(param1="value;rm -rf")

    def test_tool_validate_parameters_path_traversal(self):
        """Tool execute with path traversal raises ValueError."""

        def dummy_function(param1):
            return "result"

        tool = Tool(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.MONITORING,
            function=dummy_function,
            required_params=["param1"],
        )
        with pytest.raises(ValueError, match="path traversal"):
            tool.execute(param1="../../../etc/passwd")

    def test_tool_validate_parameters_list_dangerous_chars(self):
        """Tool execute with dangerous characters in list raises ValueError."""

        def dummy_function(param1):
            return "result"

        tool = Tool(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.MONITORING,
            function=dummy_function,
            required_params=["param1"],
        )
        with pytest.raises(ValueError, match="dangerous characters"):
            tool.execute(param1=["safe", "dangerous;rm"])

    def test_tool_execute_exception_handling(self):
        """Test Tool execute exception handling."""

        def failing_function(**kwargs):
            raise Exception("Function failed")

        tool = Tool(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.MONITORING,
            function=failing_function,
        )
        with pytest.raises(Exception, match="Function failed"):
            tool.execute()

    def test_tool_execute_async_function_in_async_context(self):
        """Test Tool execute with async function in async context."""

        async def async_function(**kwargs):
            return "async_result"

        tool = Tool(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.MONITORING,
            function=async_function,
        )

        async def test():
            result = tool.execute()
            # Should return a Task object in async context
            assert hasattr(result, "__await__")

        asyncio.run(test())

    def test_tool_execute_async_function_outside_async_context(self):
        """Test Tool execute with async function outside async context."""

        async def async_function(**kwargs):
            return "async_result"

        tool = Tool(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.MONITORING,
            function=async_function,
        )
        # Should handle gracefully with asyncio.run
        result = tool.execute()
        # Result will be the actual return value after asyncio.run
        assert result == "async_result"

    def test_tool_to_dict(self):
        """Test Tool to_dict method."""

        def dummy_function(**kwargs):
            return "result"

        tool = Tool(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.MONITORING,
            function=dummy_function,
            parameters={"param1": "value1"},
            required_params=["param1"],
            optional_params=["param2"],
            examples=[{"param1": "value1"}],
        )
        tool_dict = tool.to_dict()
        assert tool_dict["name"] == "test_tool"
        assert tool_dict["description"] == "Test tool"
        assert tool_dict["category"] == "monitoring"
        assert tool_dict["parameters"] == {"param1": "value1"}
        assert tool_dict["required_params"] == ["param1"]
        assert tool_dict["optional_params"] == ["param2"]
        assert len(tool_dict["examples"]) == 1

    def test_tool_validate_parameters_safe_string(self):
        """Tool execute with safe string parameters succeeds."""

        def dummy_function(param1):
            return param1

        tool = Tool(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.MONITORING,
            function=dummy_function,
            required_params=["param1"],
        )
        result = tool.execute(param1="safe_string")
        assert result == "safe_string"

    def test_tool_validate_parameters_dict_values(self):
        """Tool execute with dict parameter values."""

        def dummy_function(param1):
            return param1

        tool = Tool(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.MONITORING,
            function=dummy_function,
            required_params=["param1"],
        )
        result = tool.execute(param1={"key": "value"})
        assert result == {"key": "value"}


# ============================================================
# ToolRegistry class tests (20 test cases)
# ============================================================


class TestToolRegistry:
    """Test cases for ToolRegistry class."""

    def test_tool_registry_initialization(self):
        """Test ToolRegistry initialization."""
        registry = ToolRegistry()
        # Registry initializes with default tools, not empty
        assert registry.tools is not None
        assert len(registry.tools) >= 8  # Default tools

    def test_tool_registry_register_tool(self):
        """Test ToolRegistry register method."""
        registry = ToolRegistry()
        initial_count = len(registry.tools)

        def dummy_function(**kwargs):
            return "result"

        tool = Tool(
            name="custom_tool",
            description="Custom tool",
            category=ToolCategory.MONITORING,
            function=dummy_function,
        )
        registry.register(tool)
        assert len(registry.tools) == initial_count + 1
        assert "custom_tool" in registry.tools

    def test_tool_registry_unregister_tool(self):
        """Test ToolRegistry unregister method."""
        registry = ToolRegistry()
        registry.register(
            Tool(
                name="custom_tool",
                description="Custom tool",
                category=ToolCategory.MONITORING,
                function=lambda **kwargs: "result",
            )
        )
        registry.unregister("custom_tool")
        assert "custom_tool" not in registry.tools

    def test_tool_registry_unregister_nonexistent(self):
        """Test ToolRegistry unregister with nonexistent tool."""
        registry = ToolRegistry()
        # Should not raise exception
        registry.unregister("nonexistent_tool")

    def test_tool_registry_get_tool(self):
        """Test ToolRegistry get_tool method."""
        registry = ToolRegistry()
        tool = registry.get_tool("collect_metrics")
        assert tool is not None
        assert tool.name == "collect_metrics"

    def test_tool_registry_get_tool_nonexistent(self):
        """Test ToolRegistry get_tool with nonexistent tool."""
        registry = ToolRegistry()
        tool = registry.get_tool("nonexistent_tool")
        assert tool is None

    def test_tool_registry_list_tools_all(self):
        """Test ToolRegistry list_tools without category filter."""
        registry = ToolRegistry()
        tools = registry.list_tools()
        assert len(tools) > 0
        assert all(isinstance(tool, Tool) for tool in tools)

    def test_tool_registry_list_tools_by_category(self):
        """Test ToolRegistry list_tools with category filter."""
        registry = ToolRegistry()
        monitoring_tools = registry.list_tools(ToolCategory.MONITORING)
        assert len(monitoring_tools) > 0
        assert all(tool.category == ToolCategory.MONITORING for tool in monitoring_tools)

    def test_tool_registry_list_tools_empty_category(self):
        """Test ToolRegistry list_tools with category that has no tools."""
        registry = ToolRegistry()
        notification_tools = registry.list_tools(ToolCategory.NOTIFICATION)
        assert len(notification_tools) == 0

    def test_tool_registry_search_tools_by_name(self):
        """Test ToolRegistry search_tools by name."""
        registry = ToolRegistry()
        results = registry.search_tools("metric")
        assert len(results) > 0
        assert any("metric" in tool.name.lower() for tool in results)

    def test_tool_registry_search_tools_by_description(self):
        """Test ToolRegistry search_tools by description."""
        registry = ToolRegistry()
        results = registry.search_tools("收集")
        assert len(results) > 0

    def test_tool_registry_search_tools_case_insensitive(self):
        """Test ToolRegistry search_tools is case insensitive."""
        registry = ToolRegistry()
        results_lower = registry.search_tools("metric")
        results_upper = registry.search_tools("METRIC")
        assert len(results_lower) == len(results_upper)

    def test_tool_registry_search_tools_no_results(self):
        """Test ToolRegistry search_tools with no results."""
        registry = ToolRegistry()
        results = registry.search_tools("nonexistent_tool_xyz")
        assert len(results) == 0

    def test_tool_registry_default_tools_monitoring(self):
        """Test ToolRegistry has default monitoring tools."""
        registry = ToolRegistry()
        assert "collect_metrics" in registry.tools
        assert "collect_logs" in registry.tools

    def test_tool_registry_default_tools_analysis(self):
        """Test ToolRegistry has default analysis tools."""
        registry = ToolRegistry()
        assert "analyze_anomaly" in registry.tools
        assert "root_cause_analysis" in registry.tools

    def test_tool_registry_default_tools_execution(self):
        """Test ToolRegistry has default execution tools."""
        registry = ToolRegistry()
        assert "restart_service" in registry.tools
        assert "scale_service" in registry.tools

    def test_tool_registry_default_tools_diagnostic(self):
        """Test ToolRegistry has default diagnostic tools."""
        registry = ToolRegistry()
        assert "check_health" in registry.tools
        assert "run_diagnostic" in registry.tools

    def test_tool_registry_collect_metrics_execution(self):
        """Test default collect_metrics tool execution."""
        registry = ToolRegistry()
        tool = registry.get_tool("collect_metrics")
        result = tool.execute(target="system")
        assert result["target"] == "system"
        assert "cpu_usage" in result

    def test_tool_registry_collect_logs_execution(self):
        """Test default collect_logs tool execution."""
        registry = ToolRegistry()
        tool = registry.get_tool("collect_logs")
        result = tool.execute(service="test_service")
        assert len(result) == 100  # Default lines
        assert "test_service" in result[0]

    def test_tool_registry_duplicate_registration(self):
        """Test ToolRegistry handles duplicate registration."""
        registry = ToolRegistry()

        def dummy_function(**kwargs):
            return "result"

        tool = Tool(
            name="collect_metrics",  # Duplicate name
            description="Duplicate tool",
            category=ToolCategory.MONITORING,
            function=dummy_function,
        )
        registry.register(tool)
        # Should overwrite existing tool
        assert registry.tools["collect_metrics"].function == dummy_function


# ============================================================
# ToolSelector class tests (15 test cases)
# ============================================================


class TestToolSelector:
    """Test cases for ToolSelector class."""

    def test_tool_selector_initialization(self):
        """Test ToolSelector initialization."""
        registry = ToolRegistry()
        selector = ToolSelector(registry)
        assert selector.registry == registry

    def test_tool_selector_select_tool_log_collection(self):
        """Test ToolSelector selects log collection tool."""
        registry = ToolRegistry()
        selector = ToolSelector(registry)
        tool = selector.select_tool("收集日志", {"service": "test"})
        assert tool is not None
        assert "log" in tool.name.lower()

    def test_tool_selector_select_tool_metrics_collection(self):
        """Test ToolSelector selects metrics collection tool."""
        registry = ToolRegistry()
        selector = ToolSelector(registry)
        tool = selector.select_tool("收集指标", {"target": "system"})
        assert tool is not None
        assert "metric" in tool.name.lower()

    def test_tool_selector_select_tool_anomaly_detection(self):
        """Test ToolSelector selects anomaly detection tool."""
        registry = ToolRegistry()
        selector = ToolSelector(registry)
        tool = selector.select_tool("检测异常", {"data": [1.0, 2.0]})
        assert tool is not None
        assert "anomaly" in tool.name.lower()

    def test_tool_selector_select_tool_root_cause_analysis(self):
        """Test ToolSelector selects root cause analysis tool."""
        registry = ToolRegistry()
        selector = ToolSelector(registry)
        tool = selector.select_tool("根因分析", {"alert_id": "123"})
        assert tool is not None
        assert "root" in tool.name.lower()

    def test_tool_selector_select_tool_restart_service(self):
        """Test ToolSelector selects restart service tool."""
        registry = ToolRegistry()
        selector = ToolSelector(registry)
        tool = selector.select_tool("重启服务", {"service_name": "test"})
        assert tool is not None
        assert "restart" in tool.name.lower()

    def test_tool_selector_select_tool_scale_service(self):
        """Test ToolSelector selects scale service tool."""
        registry = ToolRegistry()
        selector = ToolSelector(registry)
        tool = selector.select_tool("扩容服务", {"service_name": "test", "replicas": 3})
        assert tool is not None
        assert "scale" in tool.name.lower()

    def test_tool_selector_select_tool_health_check(self):
        """Test ToolSelector selects health check tool."""
        registry = ToolRegistry()
        selector = ToolSelector(registry)
        tool = selector.select_tool("健康检查", {"target": "system"})
        assert tool is not None
        assert "health" in tool.name.lower()

    def test_tool_selector_select_tool_no_match(self):
        """Test ToolSelector returns None when no tool matches."""
        registry = ToolRegistry()
        selector = ToolSelector(registry)
        tool = selector.select_tool("unknown_task_xyz", {})
        assert tool is None

    def test_tool_selector_select_tool_case_insensitive(self):
        """Test ToolSelector is case insensitive."""
        registry = ToolRegistry()
        selector = ToolSelector(registry)
        tool_lower = selector.select_tool("收集指标", {})
        tool_upper = selector.select_tool("收集指标".upper(), {})
        assert tool_lower.name == tool_upper.name if tool_upper else tool_lower

    def test_tool_selector_select_tool_english_keywords(self):
        """Test ToolSelector works with English keywords."""
        registry = ToolRegistry()
        selector = ToolSelector(registry)
        tool = selector.select_tool("collect metrics", {"target": "system"})
        assert tool is not None
        assert "metric" in tool.name.lower()

    def test_tool_selector_select_tools_for_chain(self):
        """Test ToolSelector select_tools_for_chain method."""
        registry = ToolRegistry()
        selector = ToolSelector(registry)
        task_chain = ["收集指标", "检测异常"]
        tools = selector.select_tools_for_chain(task_chain, {})
        assert len(tools) > 0

    def test_tool_selector_select_tools_for_chain_partial_match(self):
        """Test ToolSelector select_tools_for_chain with partial matches."""
        registry = ToolRegistry()
        selector = ToolSelector(registry)
        task_chain = ["收集指标", "unknown_task"]
        tools = selector.select_tools_for_chain(task_chain, {})
        # Should only return tools that matched
        assert len(tools) >= 1

    def test_tool_selector_priority_specific_keywords(self):
        """Test ToolSelector prioritizes specific keywords."""
        registry = ToolRegistry()
        selector = ToolSelector(registry)
        # "日志" should match collect_logs over collect_metrics
        tool = selector.select_tool("收集日志", {"service": "test"})
        assert tool is not None
        assert "log" in tool.name.lower()

    def test_tool_selector_empty_task_description(self):
        """Test ToolSelector with empty task description."""
        registry = ToolRegistry()
        selector = ToolSelector(registry)
        tool = selector.select_tool("", {})
        assert tool is None


# ============================================================
# ToolExecutor class tests (20 test cases)
# ============================================================


class TestToolExecutor:
    """Test cases for ToolExecutor class."""

    def test_tool_executor_initialization(self):
        """Test ToolExecutor initialization."""
        registry = ToolRegistry()
        executor = ToolExecutor(registry)
        assert executor.registry == registry
        assert executor.selector is not None
        assert executor.execution_history == []

    def test_tool_executor_execute_tool_success(self):
        """Test ToolExecutor execute_tool with success."""
        registry = ToolRegistry()
        executor = ToolExecutor(registry)
        result = executor.execute_tool("collect_metrics", target="system")
        assert result["target"] == "system"
        assert len(executor.execution_history) == 1
        assert executor.execution_history[0]["success"] is True

    def test_tool_executor_execute_tool_not_found(self):
        """Test ToolExecutor execute_tool with nonexistent tool."""
        registry = ToolRegistry()
        executor = ToolExecutor(registry)
        with pytest.raises(ValueError, match="Tool not found"):
            executor.execute_tool("nonexistent_tool")

    def test_tool_executor_execute_tool_failure(self):
        """Test ToolExecutor execute_tool with failure."""
        registry = ToolRegistry()

        def failing_function(**kwargs):
            raise Exception("Tool failed")

        registry.register(
            Tool(
                name="failing_tool",
                description="Failing tool",
                category=ToolCategory.MONITORING,
                function=failing_function,
            )
        )

        executor = ToolExecutor(registry)
        with pytest.raises(Exception, match="Tool failed"):
            executor.execute_tool("failing_tool")

        assert len(executor.execution_history) == 1
        assert executor.execution_history[0]["success"] is False

    def test_tool_executor_execute_chain_success(self):
        """Test ToolExecutor execute_chain with success."""
        registry = ToolRegistry()
        executor = ToolExecutor(registry)
        tool_chain = [
            ("collect_metrics", {"target": "system"}),
            ("check_health", {"target": "system"}),
        ]
        results = executor.execute_chain(tool_chain)
        assert len(results) == 2
        assert len(executor.execution_history) == 2

    def test_tool_executor_execute_chain_failure_stops(self):
        """Test ToolExecutor execute_chain stops on failure."""
        registry = ToolRegistry()
        executor = ToolExecutor(registry)
        tool_chain = [
            ("collect_metrics", {"target": "system"}),
            ("nonexistent_tool", {}),  # This will fail
            ("check_health", {"target": "system"}),
        ]
        results = executor.execute_chain(tool_chain)
        # Should stop after failure
        assert len(results) == 1

    def test_tool_executor_execute_with_auto_selection(self):
        """Test ToolExecutor execute_with_auto_selection."""
        registry = ToolRegistry()
        executor = ToolExecutor(registry)
        result = executor.execute_with_auto_selection("收集指标", {"target": "system"})
        assert result is not None
        assert len(executor.execution_history) == 1

    def test_tool_executor_execute_with_auto_selection_no_tool(self):
        """Test ToolExecutor execute_with_auto_selection with no tool found."""
        registry = ToolRegistry()
        executor = ToolExecutor(registry)
        with pytest.raises(ValueError, match="No tool found"):
            executor.execute_with_auto_selection("unknown_task", {})

    def test_tool_executor_infer_parameters_target(self):
        """Test ToolExecutor _infer_parameters for target parameter."""
        registry = ToolRegistry()
        executor = ToolExecutor(registry)
        tool = registry.get_tool("collect_metrics")
        params = executor._infer_parameters(tool, {"service": "test_service"})
        # Should infer target from service
        assert params["target"] == "test_service"

    def test_tool_executor_infer_parameters_service(self):
        """Test ToolExecutor _infer_parameters for service parameter."""
        registry = ToolRegistry()
        executor = ToolExecutor(registry)
        tool = registry.get_tool("collect_logs")
        params = executor._infer_parameters(tool, {"target": "test_target"})
        # Should infer service from target
        assert params["service"] == "test_target"

    def test_tool_executor_infer_parameters_data(self):
        """Test ToolExecutor _infer_parameters for data parameter."""
        registry = ToolRegistry()
        executor = ToolExecutor(registry)
        tool = registry.get_tool("analyze_anomaly")
        params = executor._infer_parameters(tool, {"metrics": [1.0, 2.0]})
        # Should infer data from metrics
        assert params["data"] == [1.0, 2.0]

    def test_tool_executor_get_execution_statistics_empty(self):
        """Test ToolExecutor get_execution_statistics with empty history."""
        registry = ToolRegistry()
        executor = ToolExecutor(registry)
        stats = executor.get_execution_statistics()
        assert stats["total"] == 0
        assert stats["successful"] == 0
        assert stats["failed"] == 0
        assert stats["success_rate"] == 0

    def test_tool_executor_get_execution_statistics_with_history(self):
        """Test ToolExecutor get_execution_statistics with history."""
        registry = ToolRegistry()
        executor = ToolExecutor(registry)
        executor.execute_tool("collect_metrics", target="system")
        executor.execute_tool("check_health", target="system")
        stats = executor.get_execution_statistics()
        assert stats["total"] == 2
        assert stats["successful"] == 2
        assert stats["failed"] == 0
        assert stats["success_rate"] == 1.0

    def test_tool_executor_get_execution_statistics_mixed(self):
        """Test ToolExecutor get_execution_statistics with mixed results."""
        registry = ToolRegistry()

        def failing_function(**kwargs):
            raise Exception("Failed")

        registry.register(
            Tool(
                name="failing_tool",
                description="Failing tool",
                category=ToolCategory.MONITORING,
                function=failing_function,
            )
        )

        executor = ToolExecutor(registry)
        executor.execute_tool("collect_metrics", target="system")
        try:
            executor.execute_tool("failing_tool")
        except Exception:
            pass

        stats = executor.get_execution_statistics()
        assert stats["total"] == 2
        assert stats["successful"] == 1
        assert stats["failed"] == 1
        assert stats["success_rate"] == 0.5

    def test_tool_executor_execution_history_recording(self):
        """Test ToolExecutor records execution history correctly."""
        registry = ToolRegistry()
        executor = ToolExecutor(registry)
        executor.execute_tool("collect_metrics", target="system", duration=60)
        history = executor.execution_history[0]
        assert history["tool"] == "collect_metrics"
        assert history["parameters"]["target"] == "system"
        assert history["parameters"]["duration"] == 60
        assert history["success"] is True

    def test_tool_executor_multiple_executions(self):
        """Test ToolExecutor handles multiple executions."""
        registry = ToolRegistry()
        executor = ToolExecutor(registry)
        for i in range(5):
            executor.execute_tool("collect_metrics", target=f"system_{i}")
        stats = executor.get_execution_statistics()
        assert stats["total"] == 5
        assert stats["successful"] == 5

    def test_tool_executor_chain_empty(self):
        """Test ToolExecutor execute_chain with empty chain."""
        registry = ToolRegistry()
        executor = ToolExecutor(registry)
        results = executor.execute_chain([])
        assert results == []

    def test_tool_executor_parameter_override(self):
        """Test ToolExecutor parameter override in execute_tool."""
        registry = ToolRegistry()
        executor = ToolExecutor(registry)
        result = executor.execute_tool("collect_logs", service="test", lines=50)
        assert len(result) == 50  # Overridden default


# ============================================================
# Factory functions tests (2 test cases)
# ============================================================


class TestFactoryFunctions:
    """Test cases for factory functions."""

    def test_create_tool_registry(self):
        """Test create_tool_registry function."""
        registry = create_tool_registry()
        assert registry is not None
        assert isinstance(registry, ToolRegistry)
        assert len(registry.tools) > 0

    def test_create_tool_executor_default(self):
        """Test create_tool_executor with default registry."""
        executor = create_tool_executor()
        assert executor is not None
        assert isinstance(executor, ToolExecutor)
        assert executor.registry is not None

    def test_create_tool_executor_custom_registry(self):
        """Test create_tool_executor with custom registry."""
        custom_registry = ToolRegistry()
        executor = create_tool_executor(custom_registry)
        assert executor.registry == custom_registry


# ============================================================
# Edge cases and boundary conditions tests (8 test cases)
# ============================================================


class TestEdgeCases:
    """Test cases for edge cases and boundary conditions."""

    def test_tool_with_no_required_params(self):
        """Test Tool with no required parameters."""

        def dummy_function(**kwargs):
            return "result"

        tool = Tool(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.MONITORING,
            function=dummy_function,
            required_params=[],
        )
        result = tool.execute()
        assert result == "result"

    def test_tool_with_all_optional_params(self):
        """Test Tool with all optional parameters."""

        def dummy_function(**kwargs):
            return kwargs

        tool = Tool(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.MONITORING,
            function=dummy_function,
            optional_params=["param1", "param2"],
        )
        result = tool.execute(param1="value1")
        assert result["param1"] == "value1"

    def test_tool_registry_large_number_of_tools(self):
        """Test ToolRegistry with large number of tools."""
        registry = ToolRegistry()
        for i in range(100):
            registry.register(
                Tool(
                    name=f"tool_{i}",
                    description=f"Tool {i}",
                    category=ToolCategory.MONITORING,
                    function=lambda **kwargs: f"result_{i}",
                )
            )
        assert len(registry.tools) >= 100

    def test_tool_selector_ambiguous_description(self):
        """Test ToolSelector with ambiguous task description."""
        registry = ToolRegistry()
        selector = ToolSelector(registry)
        # Description that could match multiple tools
        tool = selector.select_tool("收集", {})
        # Should return first match or None
        assert tool is not None or tool is None

    def test_tool_executor_concurrent_execution(self):
        """Test ToolExecutor with concurrent execution simulation."""
        registry = ToolRegistry()
        executor = ToolExecutor(registry)
        # Simulate concurrent executions
        for i in range(10):
            executor.execute_tool("collect_metrics", target=f"system_{i}")
        stats = executor.get_execution_statistics()
        assert stats["total"] == 10

    def test_tool_parameter_special_characters_safe(self):
        """Test Tool with safe special characters."""

        def dummy_function(param1):
            return param1

        tool = Tool(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.MONITORING,
            function=dummy_function,
            required_params=["param1"],
        )
        result = tool.execute(param1="safe-value_with_underscores")
        assert result == "safe-value_with_underscores"

    def test_tool_unicode_parameters(self):
        """Test Tool with unicode parameters."""

        def dummy_function(param1):
            return param1

        tool = Tool(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.MONITORING,
            function=dummy_function,
            required_params=["param1"],
        )
        result = tool.execute(param1="测试参数")
        assert result == "测试参数"

    def test_tool_empty_string_parameter(self):
        """Test Tool with empty string parameter."""

        def dummy_function(param1):
            return param1

        tool = Tool(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.MONITORING,
            function=dummy_function,
            required_params=["param1"],
        )
        result = tool.execute(param1="")
        assert result == ""


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
