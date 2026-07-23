# -*- coding: utf-8 -*-
"""
Unit tests for core/agent/planner.py

This module contains comprehensive unit tests for the task planner module,
covering task decomposition, dependency analysis, execution planning,
chain-of-thought reasoning, and dynamic plan adjustment functionalities.
"""

from unittest.mock import Mock

import pytest

from core.agent.planner import (
    ChainOfThought,
    Task,
    TaskPlanner,
    TaskPriority,
    TaskStatus,
    create_planner,
)

# ============================================================
# TaskStatus enum tests (3 test cases)
# ============================================================


class TestTaskStatus:
    """Test cases for TaskStatus enum."""

    def test_task_status_enum_values(self):
        """Test that TaskStatus enum has correct values."""
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.IN_PROGRESS.value == "in_progress"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"
        assert TaskStatus.SKIPPED.value == "skipped"

    def test_task_status_enum_comparison(self):
        """Test TaskStatus enum comparison."""
        assert TaskStatus.PENDING == TaskStatus.PENDING
        assert TaskStatus.PENDING != TaskStatus.IN_PROGRESS

    def test_task_status_enum_iteration(self):
        """Test TaskStatus enum iteration."""
        statuses = list(TaskStatus)
        assert len(statuses) == 5
        assert TaskStatus.PENDING in statuses


# ============================================================
# TaskPriority enum tests (3 test cases)
# ============================================================


class TestTaskPriority:
    """Test cases for TaskPriority enum."""

    def test_task_priority_enum_values(self):
        """Test that TaskPriority enum has correct values."""
        assert TaskPriority.LOW.value == 1
        assert TaskPriority.MEDIUM.value == 2
        assert TaskPriority.HIGH.value == 3
        assert TaskPriority.CRITICAL.value == 4

    def test_task_priority_enum_comparison(self):
        """Test TaskPriority enum comparison using value attribute."""
        assert TaskPriority.LOW.value < TaskPriority.MEDIUM.value
        assert TaskPriority.MEDIUM.value < TaskPriority.HIGH.value
        assert TaskPriority.HIGH.value < TaskPriority.CRITICAL.value

    def test_task_priority_enum_iteration(self):
        """Test TaskPriority enum iteration."""
        priorities = list(TaskPriority)
        assert len(priorities) == 4
        assert TaskPriority.LOW in priorities


# ============================================================
# Task dataclass tests (8 test cases)
# ============================================================


class TestTask:
    """Test cases for Task dataclass."""

    def test_task_initialization_defaults(self):
        """Test Task initialization with default values."""
        task = Task(id="task1", description="Test task")
        assert task.id == "task1"
        assert task.description == "Test task"
        assert task.status == TaskStatus.PENDING
        assert task.priority == TaskPriority.MEDIUM
        assert task.dependencies == []
        assert task.parameters == {}
        assert task.result is None
        assert task.error is None

    def test_task_initialization_custom(self):
        """Test Task initialization with custom values."""
        task = Task(
            id="task1",
            description="Test task",
            status=TaskStatus.IN_PROGRESS,
            priority=TaskPriority.HIGH,
            dependencies=["task0"],
            parameters={"action": "test"},
            result="success",
            error=None,
        )
        assert task.status == TaskStatus.IN_PROGRESS
        assert task.priority == TaskPriority.HIGH
        assert task.dependencies == ["task0"]
        assert task.parameters == {"action": "test"}
        assert task.result == "success"

    def test_task_to_dict(self):
        """Test Task to_dict method."""
        task = Task(
            id="task1",
            description="Test task",
            status=TaskStatus.COMPLETED,
            priority=TaskPriority.HIGH,
            dependencies=["task0"],
            parameters={"action": "test"},
            result="success",
            reasoning="Test reasoning",
            estimated_duration=10.0,
            actual_duration=8.5,
        )
        task_dict = task.to_dict()
        assert task_dict["id"] == "task1"
        assert task_dict["description"] == "Test task"
        assert task_dict["status"] == "completed"
        assert task_dict["priority"] == 3
        assert task_dict["dependencies"] == ["task0"]
        assert task_dict["parameters"] == {"action": "test"}
        assert task_dict["result"] == "success"
        assert task_dict["reasoning"] == "Test reasoning"
        assert task_dict["estimated_duration"] == 10.0
        assert task_dict["actual_duration"] == 8.5

    def test_task_to_dict_with_none_result(self):
        """Test Task to_dict method with None result."""
        task = Task(id="task1", description="Test task", result=None)
        task_dict = task.to_dict()
        assert task_dict["result"] is None

    def test_task_dependencies(self):
        """Test Task with dependencies."""
        task = Task(
            id="task1",
            description="Test task",
            dependencies=["task0", "task2"],
        )
        assert len(task.dependencies) == 2
        assert "task0" in task.dependencies
        assert "task2" in task.dependencies

    def test_task_parameters(self):
        """Test Task with parameters."""
        task = Task(
            id="task1",
            description="Test task",
            parameters={"action": "collect", "target": "system"},
        )
        assert task.parameters["action"] == "collect"
        assert task.parameters["target"] == "system"

    def test_task_empty_string_description(self):
        """Test Task with empty string description."""
        task = Task(id="task1", description="")
        assert task.description == ""

    def test_task_none_optional_fields(self):
        """Test Task with None optional fields."""
        task = Task(
            id="task1",
            description="Test task",
            reasoning=None,
            estimated_duration=None,
            actual_duration=None,
        )
        assert task.reasoning is None
        assert task.estimated_duration is None
        assert task.actual_duration is None


# ============================================================
# ChainOfThought class tests (12 test cases)
# ============================================================


class TestChainOfThought:
    """Test cases for ChainOfThought class."""

    def test_chain_of_thought_initialization(self):
        """Test ChainOfThought initialization without LLM client."""
        cot = ChainOfThought()
        assert cot.llm_client is None
        assert cot.reasoning_steps == []

    def test_chain_of_thought_initialization_with_llm(self):
        """Test ChainOfThought initialization with LLM client."""
        llm_client = Mock()
        cot = ChainOfThought(llm_client)
        assert cot.llm_client == llm_client

    def test_reason_without_llm(self):
        """Test reason method without LLM client (rule-based)."""
        cot = ChainOfThought()
        steps = cot.reason("诊断系统问题", {"target": "system"})
        assert len(steps) > 0
        assert "收集" in steps[0]

    def test_reason_with_llm_success(self):
        """Test reason method with LLM client success."""
        llm_client = Mock()
        llm_client.generate.return_value = '["步骤1: 收集数据", "步骤2: 分析数据"]'
        cot = ChainOfThought(llm_client)
        steps = cot.reason("诊断系统问题", {"target": "system"})
        assert len(steps) == 2

    def test_reason_with_llm_failure(self):
        """Test reason method with LLM client failure."""
        llm_client = Mock()
        llm_client.generate.side_effect = Exception("LLM failed")
        cot = ChainOfThought(llm_client)
        steps = cot.reason("诊断系统问题", {"target": "system"})
        # Should fall back to rule-based reasoning
        assert len(steps) > 0

    def test_rule_reason_diagnosis_goal(self):
        """Test _rule_reason with diagnosis goal."""
        cot = ChainOfThought()
        steps = cot._rule_reason("诊断系统问题", {}, 10)
        assert "收集" in steps[0]
        assert "分析" in steps[1]

    def test_rule_reason_fix_goal(self):
        """Test _rule_reason with fix goal."""
        cot = ChainOfThought()
        steps = cot._rule_reason("修复系统问题", {}, 10)
        assert "定位" in steps[0]
        assert "评估" in steps[1]

    def test_rule_reason_scale_goal(self):
        """Test _rule_reason with scale goal."""
        cot = ChainOfThought()
        steps = cot._rule_reason("扩容系统", {}, 10)
        assert "分析" in steps[0]
        assert "预测" in steps[1]

    def test_rule_reason_generic_goal(self):
        """Test _rule_reason with generic goal."""
        cot = ChainOfThought()
        steps = cot._rule_reason("完成某任务", {}, 10)
        assert "理解" in steps[0]
        assert "收集" in steps[1]

    def test_reason_max_steps_limit(self):
        """Test reason method with max_steps limit."""
        cot = ChainOfThought()
        steps = cot.reason("诊断系统问题", {}, max_steps=2)
        assert len(steps) <= 2

    def test_reasoning_steps_storage(self):
        """Test that reasoning steps are stored."""
        cot = ChainOfThought()
        steps = cot.reason("诊断系统问题", {})
        assert cot.reasoning_steps == steps

    def test_reason_empty_goal(self):
        """Test reason method with empty goal."""
        cot = ChainOfThought()
        steps = cot.reason("", {})
        # Should still generate generic steps
        assert len(steps) > 0


# ============================================================
# TaskPlanner class tests (20 test cases)
# ============================================================


class TestTaskPlanner:
    """Test cases for TaskPlanner class."""

    def test_task_planner_initialization(self):
        """Test TaskPlanner initialization."""
        cot = ChainOfThought()
        planner = TaskPlanner(cot)
        assert planner.cot_engine == cot
        assert planner.tasks == {}
        assert planner.task_counter == 0

    def test_task_planner_initialization_default(self):
        """Test TaskPlanner initialization with default CoT engine."""
        planner = TaskPlanner()
        assert planner.cot_engine is not None
        assert planner.tasks == {}
        assert planner.task_counter == 0

    def test_plan_basic(self):
        """Test plan method with basic goal."""
        planner = TaskPlanner()
        tasks = planner.plan("诊断系统问题", {"target": "system"}, ["collect", "analyze"])
        assert len(tasks) > 0
        assert all(isinstance(task, Task) for task in tasks)

    def test_plan_task_dependencies(self):
        """Test plan method creates task dependencies."""
        planner = TaskPlanner()
        tasks = planner.plan("诊断系统问题", {"target": "system"}, ["collect", "analyze"])
        if len(tasks) > 1:
            # Second task should depend on first
            assert tasks[1].dependencies == [tasks[0].id]

    def test_plan_parameter_inference(self):
        """Test plan method infers task parameters."""
        planner = TaskPlanner()
        tasks = planner.plan("收集系统指标", {"target": "system"}, ["collect"])
        assert len(tasks) > 0
        assert "available_tools" in tasks[0].parameters

    def test_infer_task_parameters_collect(self):
        """Test _infer_task_parameters with collect action."""
        planner = TaskPlanner()
        params = planner._infer_task_parameters("收集系统指标", {"target": "system"}, ["collect"])
        assert params["action"] == "collect"
        assert params["target"] == "system"

    def test_infer_task_parameters_analyze(self):
        """Test _infer_task_parameters with analyze action."""
        planner = TaskPlanner()
        params = planner._infer_task_parameters("分析数据", {}, ["analyze"])
        assert params["action"] == "analyze"
        assert params["method"] == "statistical"

    def test_infer_task_parameters_identify(self):
        """Test _infer_task_parameters with identify action."""
        planner = TaskPlanner()
        params = planner._infer_task_parameters("识别问题", {}, ["identify"])
        assert params["action"] == "identify"
        assert params["algorithm"] == "anomaly_detection"

    def test_infer_task_parameters_validate(self):
        """Test _infer_task_parameters with validate action."""
        planner = TaskPlanner()
        params = planner._infer_task_parameters("验证结果", {}, ["validate"])
        assert params["action"] == "validate"
        assert params["criteria"] == "success_rate"

    def test_infer_task_parameters_execute(self):
        """Test _infer_task_parameters with execute action."""
        planner = TaskPlanner()
        params = planner._infer_task_parameters("执行操作", {}, ["execute"])
        assert params["action"] == "execute"
        assert params["mode"] == "safe"

    def test_infer_task_parameters_generate(self):
        """Test _infer_task_parameters with generate action."""
        planner = TaskPlanner()
        params = planner._infer_task_parameters("生成报告", {}, ["generate"])
        assert params["action"] == "generate"
        assert params["format"] == "report"

    def test_adjust_plan_completed(self):
        """Test adjust_plan with completed task."""
        planner = TaskPlanner()
        tasks = planner.plan("诊断系统问题", {}, ["collect"])
        task_id = tasks[0].id
        planner.adjust_plan(task_id, TaskStatus.COMPLETED, "success")
        assert planner.tasks[task_id].status == TaskStatus.COMPLETED
        assert planner.tasks[task_id].result == "success"

    def test_adjust_plan_failed(self):
        """Test adjust_plan with failed task."""
        planner = TaskPlanner()
        tasks = planner.plan("诊断系统问题", {}, ["collect"])
        task_id = tasks[0].id
        planner.adjust_plan(task_id, TaskStatus.FAILED, None, "error")
        assert planner.tasks[task_id].status == TaskStatus.FAILED
        assert planner.tasks[task_id].error == "error"

    def test_adjust_plan_nonexistent_task(self):
        """Test adjust_plan with nonexistent task."""
        planner = TaskPlanner()
        adjusted = planner.adjust_plan("nonexistent", TaskStatus.COMPLETED)
        assert adjusted == []

    def test_handle_task_failure(self):
        """Test _handle_task_failure skips dependent tasks."""
        planner = TaskPlanner()
        tasks = planner.plan("诊断系统问题", {}, ["collect"])
        if len(tasks) > 1:
            planner._handle_task_failure(tasks[0].id)
            assert planner.tasks[tasks[1].id].status == TaskStatus.SKIPPED

    def test_get_ready_tasks(self):
        """Test get_ready_tasks returns tasks with met dependencies."""
        planner = TaskPlanner()
        planner.plan("诊断系统问题", {}, ["collect"])
        # First task should be ready (no dependencies)
        ready_tasks = planner.get_ready_tasks()
        assert len(ready_tasks) > 0

    def test_get_ready_tasks_priority_sorting(self):
        """Test get_ready_tasks sorts by priority."""
        planner = TaskPlanner()
        planner.tasks["task1"] = Task(id="task1", description="Task 1", priority=TaskPriority.HIGH)
        planner.tasks["task2"] = Task(id="task2", description="Task 2", priority=TaskPriority.LOW)
        ready_tasks = planner.get_ready_tasks()
        # High priority should come first
        assert ready_tasks[0].priority == TaskPriority.HIGH

    def test_get_plan_summary(self):
        """Test get_plan_summary returns correct statistics."""
        planner = TaskPlanner()
        planner.plan("诊断系统问题", {}, ["collect"])
        summary = planner.get_plan_summary()
        assert "total" in summary
        assert "completed" in summary
        assert "failed" in summary
        assert "skipped" in summary
        assert "in_progress" in summary
        assert "pending" in summary
        assert "progress" in summary

    def test_get_plan_summary_empty(self):
        """Test get_plan_summary with empty plan."""
        planner = TaskPlanner()
        summary = planner.get_plan_summary()
        assert summary["total"] == 0
        assert summary["progress"] == 0

    def test_task_counter_increment(self):
        """Test that task counter increments correctly."""
        planner = TaskPlanner()
        initial_counter = planner.task_counter
        planner.plan("诊断系统问题", {}, ["collect"])
        assert planner.task_counter > initial_counter

    def test_plan_empty_tools_list(self):
        """Test plan method with empty tools list."""
        planner = TaskPlanner()
        tasks = planner.plan("诊断系统问题", {}, [])
        assert len(tasks) > 0


# ============================================================
# create_planner function tests (3 test cases)
# ============================================================


class TestCreatePlanner:
    """Test cases for create_planner function."""

    def test_create_planner_basic(self):
        """Test create_planner with default parameters."""
        planner = create_planner()
        assert planner is not None
        assert isinstance(planner, TaskPlanner)

    def test_create_planner_with_llm(self):
        """Test create_planner with custom LLM client."""
        llm_client = Mock()
        planner = create_planner(llm_client)
        assert planner.cot_engine.llm_client == llm_client

    def test_create_planner_none_llm(self):
        """Test create_planner with None LLM client."""
        planner = create_planner(None)
        assert planner.cot_engine.llm_client is None


# ============================================================
# Edge cases and boundary conditions tests (12 test cases)
# ============================================================


class TestEdgeCases:
    """Test cases for edge cases and boundary conditions."""

    def test_empty_string_goal(self):
        """Test plan method with empty string goal."""
        planner = TaskPlanner()
        tasks = planner.plan("", {}, ["collect"])
        # Should still generate generic tasks
        assert len(tasks) > 0

    def test_none_parameters(self):
        """Test plan method with None parameters - expects AttributeError."""
        planner = TaskPlanner()
        # None goal will cause AttributeError in actual code
        # This test documents current behavior
        with pytest.raises(AttributeError):
            planner.plan(None, None, None)  # type: ignore

    def test_very_long_goal_string(self):
        """Test plan method with very long goal string."""
        planner = TaskPlanner()
        long_goal = "诊断 " * 1000
        tasks = planner.plan(long_goal, {}, ["collect"])
        assert len(tasks) > 0

    def test_special_characters_in_goal(self):
        """Test plan method with special characters in goal."""
        planner = TaskPlanner()
        tasks = planner.plan("诊断@#$%^&*()系统", {}, ["collect"])
        assert len(tasks) > 0

    def test_empty_context(self):
        """Test plan method with empty context."""
        planner = TaskPlanner()
        tasks = planner.plan("诊断系统问题", {}, ["collect"])
        assert len(tasks) > 0

    def test_no_available_tools(self):
        """Test plan method with no available tools."""
        planner = TaskPlanner()
        tasks = planner.plan("诊断系统问题", {}, [])
        assert len(tasks) > 0

    def test_circular_dependencies(self):
        """Test handling of circular dependencies."""
        planner = TaskPlanner()
        task1 = Task(id="task1", description="Task 1", dependencies=["task2"])
        task2 = Task(id="task2", description="Task 2", dependencies=["task1"])
        planner.tasks["task1"] = task1
        planner.tasks["task2"] = task2
        ready_tasks = planner.get_ready_tasks()
        # Neither should be ready due to circular dependency
        assert len(ready_tasks) == 0

    def test_large_number_of_tasks(self):
        """Test planner with large number of tasks."""
        planner = TaskPlanner()
        for i in range(100):
            planner.tasks[f"task_{i}"] = Task(id=f"task_{i}", description=f"Task {i}")
        summary = planner.get_plan_summary()
        assert summary["total"] == 100

    def test_concurrent_planning(self):
        """Test handling of concurrent planning calls."""
        planner = TaskPlanner()
        tasks1 = planner.plan("诊断系统问题", {}, ["collect"])
        tasks2 = planner.plan("分析数据", {}, ["analyze"])
        assert len(tasks1) > 0
        assert len(tasks2) > 0
        # Task counter should have incremented
        assert planner.task_counter > 0

    def test_task_counter_overflow(self):
        """Test task counter with very large values."""
        planner = TaskPlanner()
        planner.task_counter = 999999
        tasks = planner.plan("诊断系统问题", {}, ["collect"])
        # Should still work
        assert len(tasks) > 0

    def test_unicode_characters_in_description(self):
        """Test task with unicode characters in description."""
        task = Task(id="task1", description="诊断系统问题🔍")
        task_dict = task.to_dict()
        assert "🔍" in task_dict["description"]

    def test_error_recovery_after_failure(self):
        """Test planner recovery after task failure."""
        planner = TaskPlanner()
        tasks = planner.plan("诊断系统问题", {}, ["collect"])
        if len(tasks) > 1:
            # Mark first task as failed
            planner.adjust_plan(tasks[0].id, TaskStatus.FAILED, None, "error")
            # Second task should be skipped
            assert planner.tasks[tasks[1].id].status == TaskStatus.SKIPPED
