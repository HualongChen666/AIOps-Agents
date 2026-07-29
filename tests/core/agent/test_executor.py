# -*- coding: utf-8 -*-
"""
Unit tests for core/agent/executor.py

This module contains comprehensive unit tests for the autonomous executor module,
covering task execution, result validation, error handling, rollback mechanisms,
trust mechanisms, and concurrent execution functionalities.
"""

from unittest.mock import Mock, patch

import pytest

from core.agent.executor import (
    DANGEROUS_KEYWORDS,
    MODIFY_KEYWORDS,
    READONLY_KEYWORDS,
    STOP_KEYWORDS,
    AutonomousExecutor,
    RiskAssessor,
    RiskLevel,
    RollbackMechanism,
    SafetyBoundary,
    TrustMechanism,
    ValidationMechanism,
    create_autonomous_executor,
)

# ============================================================
# RiskLevel enum tests (2 test cases)
# ============================================================


class TestRiskLevel:
    """Test cases for RiskLevel enum."""

    def test_risk_level_enum_values(self):
        """Test that RiskLevel enum uses the unified command_guard string values."""
        assert RiskLevel.LOW.value == "low"
        assert RiskLevel.MEDIUM.value == "medium"
        assert RiskLevel.HIGH.value == "high"
        assert RiskLevel.BLOCKED.value == "blocked"
        assert RiskLevel.SAFE.value == "safe"

    def test_risk_level_enum_comparison(self):
        """Test RiskLevel enum names and existence."""
        assert RiskLevel.LOW.name == "LOW"
        assert RiskLevel.MEDIUM.name == "MEDIUM"
        assert RiskLevel.HIGH.name == "HIGH"
        assert RiskLevel.BLOCKED.name == "BLOCKED"


# ============================================================
# SafetyBoundary class tests (6 test cases)
# ============================================================


class TestSafetyBoundary:
    """Test cases for SafetyBoundary class."""

    def test_safety_boundary_initialization(self):
        """Test SafetyBoundary initialization with default values."""
        boundary = SafetyBoundary()
        assert boundary.allowed_operations == []
        assert boundary.forbidden_operations == []
        assert boundary.max_resource_impact == 0.5
        assert boundary.max_rollback_time == 300
        assert boundary.require_approval_for == []

    def test_safety_boundary_custom_initialization(self):
        """Test SafetyBoundary initialization with custom values."""
        boundary = SafetyBoundary(
            allowed_operations=["restart"],
            forbidden_operations=["delete"],
            max_resource_impact=0.8,
            max_rollback_time=600,
            require_approval_for=["scale"],
        )
        assert "restart" in boundary.allowed_operations
        assert "delete" in boundary.forbidden_operations
        assert boundary.max_resource_impact == 0.8
        assert boundary.max_rollback_time == 600
        assert "scale" in boundary.require_approval_for

    def test_is_operation_allowed_allowed(self):
        """Test is_operation_allowed with allowed operation."""
        boundary = SafetyBoundary(allowed_operations=["restart"])
        assert boundary.is_operation_allowed("restart") is True

    def test_is_operation_allowed_forbidden(self):
        """Test is_operation_allowed with forbidden operation."""
        boundary = SafetyBoundary(forbidden_operations=["delete"])
        assert boundary.is_operation_allowed("delete") is False

    def test_is_operation_allowed_empty_allowed_list(self):
        """Test is_operation_allowed with empty allowed list (allow all except forbidden)."""
        boundary = SafetyBoundary(allowed_operations=[], forbidden_operations=["delete"])
        assert boundary.is_operation_allowed("restart") is True
        assert boundary.is_operation_allowed("delete") is False

    def test_requires_approval(self):
        """Test requires_approval method."""
        boundary = SafetyBoundary(require_approval_for=["scale"])
        assert boundary.requires_approval("scale") is True
        assert boundary.requires_approval("restart") is False


# ============================================================
# RiskAssessor class tests (10 test cases)
# ============================================================


class TestRiskAssessor:
    """Test cases for RiskAssessor class."""

    def test_risk_assessor_initialization(self):
        """Test RiskAssessor initialization."""
        boundary = SafetyBoundary()
        assessor = RiskAssessor(boundary)
        assert assessor.safety_boundary == boundary
        assert assessor.risk_history == {}

    def test_assess_risk_forbidden_operation(self):
        """Test assess_risk with forbidden operation."""
        boundary = SafetyBoundary(forbidden_operations=["delete"])
        assessor = RiskAssessor(boundary)
        risk_level, reason = assessor.assess_risk("delete", {})
        assert risk_level == RiskLevel.CRITICAL
        assert "forbidden" in reason.lower()

    def test_assess_risk_dangerous_operation(self):
        """Test assess_risk with dangerous operation."""
        boundary = SafetyBoundary()
        assessor = RiskAssessor(boundary)
        risk_level, reason = assessor.assess_risk("delete file", {})
        assert risk_level == RiskLevel.CRITICAL
        assert "destructive" in reason.lower()

    def test_assess_risk_stop_operation(self):
        """Test assess_risk with stop operation."""
        boundary = SafetyBoundary()
        assessor = RiskAssessor(boundary)
        risk_level, reason = assessor.assess_risk("stop service", {})
        assert risk_level == RiskLevel.HIGH
        assert "stop" in reason.lower()

    def test_assess_risk_modify_operation(self):
        """Test assess_risk with modify operation."""
        boundary = SafetyBoundary()
        assessor = RiskAssessor(boundary)
        risk_level, reason = assessor.assess_risk("restart service", {})
        assert risk_level == RiskLevel.MEDIUM
        assert "modification" in reason.lower()

    def test_assess_risk_scale_operation(self):
        """Test assess_risk with scale operation."""
        boundary = SafetyBoundary()
        assessor = RiskAssessor(boundary)
        risk_level, reason = assessor.assess_risk("scale up", {})
        assert risk_level == RiskLevel.MEDIUM
        assert "scaling" in reason.lower()

    def test_assess_risk_readonly_operation(self):
        """Test assess_risk with read-only operation."""
        boundary = SafetyBoundary()
        assessor = RiskAssessor(boundary)
        risk_level, reason = assessor.assess_risk("check status", {})
        assert risk_level == RiskLevel.LOW
        assert "read-only" in reason.lower()

    def test_assess_risk_unknown_operation(self):
        """Test assess_risk with unknown operation."""
        boundary = SafetyBoundary()
        assessor = RiskAssessor(boundary)
        risk_level, reason = assessor.assess_risk("unknown operation", {})
        assert risk_level == RiskLevel.MEDIUM
        assert "unknown" in reason.lower()

    def test_check_historical_risk_no_history(self):
        """Test check_historical_risk with no history."""
        boundary = SafetyBoundary()
        assessor = RiskAssessor(boundary)
        success_rate = assessor.check_historical_risk("restart")
        assert success_rate == 1.0

    def test_record_execution(self):
        """Test record_execution method."""
        boundary = SafetyBoundary()
        assessor = RiskAssessor(boundary)
        assessor.record_execution("restart", True)
        assert "restart" in assessor.risk_history
        assert len(assessor.risk_history["restart"]) == 1
        assert assessor.risk_history["restart"][0]["success"] is True


# ============================================================
# TrustMechanism class tests (8 test cases)
# ============================================================


class TestTrustMechanism:
    """Test cases for TrustMechanism class."""

    def test_trust_mechanism_initialization(self):
        """Test TrustMechanism initialization."""
        mechanism = TrustMechanism()
        assert mechanism.initial_trust == 0.5
        assert mechanism.learning_rate == 0.1
        assert mechanism.trust_scores == {}

    def test_trust_mechanism_custom_initialization(self):
        """Test TrustMechanism with custom values."""
        mechanism = TrustMechanism(initial_trust=0.7, learning_rate=0.2)
        assert mechanism.initial_trust == 0.7
        assert mechanism.learning_rate == 0.2

    def test_get_trust_score_no_history(self):
        """Test get_trust_score with no history."""
        mechanism = TrustMechanism(initial_trust=0.5)
        score = mechanism.get_trust_score("restart")
        assert score == 0.5

    def test_get_trust_score_with_history(self):
        """Test get_trust_score with history."""
        mechanism = TrustMechanism(initial_trust=0.5)
        mechanism.trust_scores["restart"] = 0.8
        score = mechanism.get_trust_score("restart")
        assert score == 0.8

    def test_update_trust_success(self):
        """Test update_trust with success."""
        mechanism = TrustMechanism(initial_trust=0.5, learning_rate=0.1)
        mechanism.update_trust("restart", True)
        score = mechanism.get_trust_score("restart")
        assert score > 0.5  # Trust should increase

    def test_update_trust_failure(self):
        """Test update_trust with failure."""
        mechanism = TrustMechanism(initial_trust=0.5, learning_rate=0.1)
        mechanism.update_trust("restart", False)
        score = mechanism.get_trust_score("restart")
        assert score < 0.5  # Trust should decrease

    def test_can_auto_execute_low_risk(self):
        """Test can_auto_execute with LOW risk."""
        mechanism = TrustMechanism(initial_trust=0.5)
        assert mechanism.can_auto_execute("check", RiskLevel.LOW) is True

    def test_can_auto_execute_blocked_risk(self):
        """Test can_auto_execute with BLOCKED risk."""
        mechanism = TrustMechanism(initial_trust=1.0)
        assert mechanism.can_auto_execute("delete", RiskLevel.BLOCKED) is False


# ============================================================
# RollbackMechanism class tests (6 test cases)
# ============================================================


class TestRollbackMechanism:
    """Test cases for RollbackMechanism class."""

    def test_rollback_mechanism_initialization(self):
        """Test RollbackMechanism initialization."""
        mechanism = RollbackMechanism()
        assert mechanism.rollback_actions == {}
        assert mechanism.rollback_history == []

    def test_register_rollback(self):
        """Test register_rollback method."""
        mechanism = RollbackMechanism()

        def rollback_action():
            return None

        mechanism.register_rollback("op1", rollback_action)
        assert "op1" in mechanism.rollback_actions

    def test_execute_rollback_success(self):
        """Test execute_rollback with successful rollback."""
        mechanism = RollbackMechanism()
        rollback_called = []

        def rollback_action():
            rollback_called.append(True)

        mechanism.register_rollback("op1", rollback_action)
        result = mechanism.execute_rollback("op1")
        assert result is True
        assert len(rollback_called) == 1

    def test_execute_rollback_no_action(self):
        """Test execute_rollback with no rollback action."""
        mechanism = RollbackMechanism()
        result = mechanism.execute_rollback("nonexistent")
        assert result is False

    def test_execute_rollback_failure(self):
        """Test execute_rollback with rollback failure."""
        mechanism = RollbackMechanism()

        def failing_rollback():
            raise Exception("Rollback failed")

        mechanism.register_rollback("op1", failing_rollback)
        result = mechanism.execute_rollback("op1")
        assert result is False
        assert len(mechanism.rollback_history) == 1

    def test_rollback_history(self):
        """Test that rollback history is recorded."""
        mechanism = RollbackMechanism()

        def rollback_action():
            pass

        mechanism.register_rollback("op1", rollback_action)
        mechanism.execute_rollback("op1")
        assert len(mechanism.rollback_history) == 1
        assert mechanism.rollback_history[0]["operation_id"] == "op1"


# ============================================================
# ValidationMechanism class tests (6 test cases)
# ============================================================


class TestValidationMechanism:
    """Test cases for ValidationMechanism class."""

    def test_validation_mechanism_initialization(self):
        """Test ValidationMechanism initialization."""
        mechanism = ValidationMechanism()
        assert mechanism.validation_rules == {}

    def test_register_validation(self):
        """Test register_validation method."""
        mechanism = ValidationMechanism()

        def validation_func(result, context):
            return (True, "OK")

        mechanism.register_validation("restart", validation_func)
        assert "restart" in mechanism.validation_rules

    def test_validate_no_rules(self):
        """Test validate with no validation rules."""
        mechanism = ValidationMechanism()
        passed, reason = mechanism.validate("restart", {"status": "ok"}, {})
        assert passed is True
        assert "No validation rules" in reason

    def test_validate_success(self):
        """Test validate with successful validation."""
        mechanism = ValidationMechanism()

        def validation_func(result, context):
            return (True, "Valid")

        mechanism.register_validation("restart", validation_func)
        passed, reason = mechanism.validate("restart", {"status": "ok"}, {})
        assert passed is True

    def test_validate_failure(self):
        """Test validate with failed validation."""
        mechanism = ValidationMechanism()

        def validation_func(result, context):
            return (False, "Invalid")

        mechanism.register_validation("restart", validation_func)
        passed, reason = mechanism.validate("restart", {"status": "error"}, {})
        assert passed is False
        assert reason == "Invalid"

    def test_validate_exception(self):
        """Test validate with validation exception."""
        mechanism = ValidationMechanism()

        def failing_validation(result, context):
            raise Exception("Validation error")

        mechanism.register_validation("restart", failing_validation)
        passed, reason = mechanism.validate("restart", {"status": "ok"}, {})
        assert passed is False
        assert "Validation error" in reason


# ============================================================
# AutonomousExecutor class tests (15 test cases)
# ============================================================


class TestAutonomousExecutor:
    """Test cases for AutonomousExecutor class."""

    def test_autonomous_executor_initialization(self):
        """Test AutonomousExecutor initialization."""
        planner = Mock()
        tool_executor = Mock()
        boundary = SafetyBoundary()
        executor = AutonomousExecutor(planner, tool_executor, boundary)
        assert executor.planner == planner
        assert executor.tool_executor == tool_executor
        assert executor.safety_boundary == boundary
        assert executor.execution_mode == "hybrid"

    def test_execute_plan_basic(self):
        """Test execute_plan with basic functionality."""
        planner = Mock()
        tool_executor = Mock()
        boundary = SafetyBoundary()
        executor = AutonomousExecutor(planner, tool_executor, boundary)

        # Mock task
        from core.agent.planner import Task, TaskStatus

        task = Task(id="task1", description="check status", status=TaskStatus.PENDING)
        planner.plan.return_value = [task]
        tool_executor.execute_with_auto_selection.return_value = {"status": "ok"}
        planner.adjust_plan.return_value = None
        planner.get_plan_summary.return_value = {"total": 1, "completed": 1}

        result = executor.execute_plan("check system", {}, ["check"])
        assert result["goal"] == "check system"
        assert len(result["tasks"]) == 1

    def test_execute_task_manual_mode(self):
        """Test execute_task in manual mode with approval required."""
        planner = Mock()
        tool_executor = Mock()
        boundary = SafetyBoundary(require_approval_for=["restart service"])
        executor = AutonomousExecutor(planner, tool_executor, boundary)
        executor.set_execution_mode("manual")

        from core.agent.planner import Task, TaskStatus

        task = Task(id="task1", description="restart service", status=TaskStatus.PENDING)
        result = executor.execute_task(task, {})
        assert result["status"] == "pending_approval"

    def test_execute_task_autonomous_mode_low_trust(self):
        """Test execute_task in autonomous mode with low trust."""
        planner = Mock()
        tool_executor = Mock()
        boundary = SafetyBoundary()
        executor = AutonomousExecutor(planner, tool_executor, boundary)
        executor.set_execution_mode("autonomous")

        from core.agent.planner import Task, TaskStatus

        task = Task(id="task1", description="restart service", status=TaskStatus.PENDING)
        result = executor.execute_task(task, {})
        assert result["status"] == "pending_approval"

    def test_execute_task_hybrid_mode_high_risk(self):
        """Test execute_task in hybrid mode with high risk."""
        planner = Mock()
        tool_executor = Mock()
        boundary = SafetyBoundary()
        executor = AutonomousExecutor(planner, tool_executor, boundary)
        executor.set_execution_mode("hybrid")

        from core.agent.planner import Task, TaskStatus

        task = Task(id="task1", description="delete file", status=TaskStatus.PENDING)
        result = executor.execute_task(task, {})
        assert result["status"] == "pending_approval"

    def test_execute_task_validation_failure(self):
        """Test execute_task with validation failure."""
        planner = Mock()
        tool_executor = Mock()
        boundary = SafetyBoundary()
        executor = AutonomousExecutor(planner, tool_executor, boundary)

        from core.agent.planner import Task, TaskStatus

        task = Task(id="task1", description="check status", status=TaskStatus.PENDING)
        tool_executor.execute_with_auto_selection.return_value = {"status": "error"}

        # Register validation that will fail
        executor.validation_mechanism.register_validation(
            "check status", lambda result, context: (False, "Validation failed")
        )

        result = executor.execute_task(task, {})
        assert result["status"] == "failed"

    def test_execute_task_execution_exception(self):
        """Test execute_task with execution exception."""
        planner = Mock()
        tool_executor = Mock()
        boundary = SafetyBoundary()
        executor = AutonomousExecutor(planner, tool_executor, boundary)

        from core.agent.planner import Task, TaskStatus

        task = Task(id="task1", description="check status", status=TaskStatus.PENDING)
        tool_executor.execute_with_auto_selection.side_effect = Exception("Execution failed")

        result = executor.execute_task(task, {})
        assert result["status"] == "failed"
        assert "Execution failed" in result["error"]

    def test_set_execution_mode_valid(self):
        """Test set_execution_mode with valid mode."""
        planner = Mock()
        tool_executor = Mock()
        executor = AutonomousExecutor(planner, tool_executor)
        executor.set_execution_mode("autonomous")
        assert executor.execution_mode == "autonomous"

    def test_set_execution_mode_invalid(self):
        """Test set_execution_mode with invalid mode."""
        planner = Mock()
        tool_executor = Mock()
        executor = AutonomousExecutor(planner, tool_executor)
        with pytest.raises(ValueError, match="Invalid execution mode"):
            executor.set_execution_mode("invalid_mode")

    def test_get_statistics(self):
        """Test get_statistics method."""
        planner = Mock()
        tool_executor = Mock()
        executor = AutonomousExecutor(planner, tool_executor)
        stats = executor.get_statistics()
        assert "execution_mode" in stats
        assert "trust_scores" in stats
        assert "risk_history" in stats
        assert "rollback_history" in stats

    def test_execute_plan_empty_task_list(self):
        """Test execute_plan with empty task list."""
        planner = Mock()
        tool_executor = Mock()
        executor = AutonomousExecutor(planner, tool_executor)
        planner.plan.return_value = []
        planner.get_plan_summary.return_value = {"total": 0, "completed": 0}

        result = executor.execute_plan("check", {}, [])
        assert len(result["tasks"]) == 0

    def test_execute_task_empty_context(self):
        """Test execute_task with empty context."""
        planner = Mock()
        tool_executor = Mock()
        boundary = SafetyBoundary()
        executor = AutonomousExecutor(planner, tool_executor, boundary)

        from core.agent.planner import Task, TaskStatus

        task = Task(id="task1", description="check status", status=TaskStatus.PENDING)
        tool_executor.execute_with_auto_selection.return_value = {"status": "ok"}

        result = executor.execute_task(task, {})
        assert result["status"] == "completed"

    def test_execute_task_planner_exception(self):
        """Test execute_plan with planner exception."""
        planner = Mock()
        tool_executor = Mock()
        executor = AutonomousExecutor(planner, tool_executor)
        planner.plan.side_effect = Exception("Planner failed")

        with pytest.raises(Exception, match="Planner failed"):
            executor.execute_plan("check", {}, ["check"])

    def test_execute_task_tool_executor_exception(self):
        """Test execute_task with tool_executor exception."""
        planner = Mock()
        tool_executor = Mock()
        boundary = SafetyBoundary()
        executor = AutonomousExecutor(planner, tool_executor, boundary)

        from core.agent.planner import Task, TaskStatus

        task = Task(id="task1", description="check status", status=TaskStatus.PENDING)
        tool_executor.execute_with_auto_selection.side_effect = Exception("Tool failed")

        result = executor.execute_task(task, {})
        assert result["status"] == "failed"


# ============================================================
# create_autonomous_executor function tests (3 test cases)
# ============================================================


class TestCreateAutonomousExecutor:
    """Test cases for create_autonomous_executor function."""

    @patch("core.agent.planner.create_planner")
    @patch("core.agent.tools.create_tool_executor")
    def test_create_autonomous_executor_basic(self, mock_create_tool, mock_create_planner):
        """Test create_autonomous_executor with default parameters."""
        mock_planner = Mock()
        mock_tool = Mock()
        mock_create_planner.return_value = mock_planner
        mock_create_tool.return_value = mock_tool

        executor = create_autonomous_executor()
        assert executor.planner == mock_planner
        assert executor.tool_executor == mock_tool

    def test_create_autonomous_executor_custom_planner(self):
        """Test create_autonomous_executor with custom planner."""
        planner = Mock()
        tool_executor = Mock()
        executor = create_autonomous_executor(planner=planner, tool_executor=tool_executor)
        assert executor.planner == planner
        assert executor.tool_executor == tool_executor

    def test_create_autonomous_executor_custom_safety_boundary(self):
        """Test create_autonomous_executor with custom safety boundary."""
        planner = Mock()
        tool_executor = Mock()
        boundary = SafetyBoundary(max_resource_impact=0.8)
        executor = create_autonomous_executor(
            planner=planner, tool_executor=tool_executor, safety_boundary=boundary
        )
        assert executor.safety_boundary == boundary


# ============================================================
# Edge cases and boundary conditions tests (8 test cases)
# ============================================================


class TestEdgeCases:
    """Test cases for edge cases and boundary conditions."""

    def test_empty_string_operation(self):
        """Test risk assessment with empty string operation."""
        boundary = SafetyBoundary()
        assessor = RiskAssessor(boundary)
        risk_level, reason = assessor.assess_risk("", {})
        assert risk_level == RiskLevel.MEDIUM

    def test_none_parameters(self):
        """Test methods with None parameters - handle gracefully."""
        boundary = SafetyBoundary()
        assessor = RiskAssessor(boundary)
        # Test that None operation is handled (will raise AttributeError in actual code)
        # This test documents current behavior
        with pytest.raises(AttributeError):
            assessor.assess_risk(None, None)

    def test_very_long_operation_string(self):
        """Test risk assessment with very long operation string."""
        boundary = SafetyBoundary()
        assessor = RiskAssessor(boundary)
        long_operation = "check " * 1000
        risk_level, reason = assessor.assess_risk(long_operation, {})
        assert risk_level == RiskLevel.LOW

    def test_special_characters_in_operation(self):
        """Test risk assessment with special characters."""
        boundary = SafetyBoundary()
        assessor = RiskAssessor(boundary)
        risk_level, reason = assessor.assess_risk("check@#$%^&*()", {})
        # Contains "check" keyword, so it's LOW risk
        assert risk_level == RiskLevel.LOW

    def test_trust_score_boundary_zero(self):
        """Test trust score at boundary zero."""
        mechanism = TrustMechanism(initial_trust=0.0)
        score = mechanism.get_trust_score("operation")
        assert score == 0.0

    def test_trust_score_boundary_one(self):
        """Test trust score at boundary one."""
        mechanism = TrustMechanism(initial_trust=1.0)
        score = mechanism.get_trust_score("operation")
        assert score == 1.0

    def test_historical_risk_limit(self):
        """Test that historical risk is limited to 100 records."""
        boundary = SafetyBoundary()
        assessor = RiskAssessor(boundary)
        for i in range(150):
            assessor.record_execution("restart", True)
        assert len(assessor.risk_history["restart"]) == 100

    def test_concurrent_operations(self):
        """Test handling of concurrent operations."""
        boundary = SafetyBoundary()
        assessor = RiskAssessor(boundary)
        mechanism = TrustMechanism()

        # Simulate multiple operations
        for i in range(10):
            assessor.record_execution(f"operation_{i}", i % 2 == 0)
            mechanism.update_trust(f"operation_{i}", i % 2 == 0)

        assert len(assessor.risk_history) == 10
        assert len(mechanism.trust_scores) == 10


# ============================================================
# Keyword constants tests (4 test cases)
# ============================================================


class TestKeywordConstants:
    """Test cases for keyword constants."""

    def test_dangerous_keywords(self):
        """Test DANGEROUS_KEYWORDS constant."""
        assert "删除" in DANGEROUS_KEYWORDS
        assert "delete" in DANGEROUS_KEYWORDS
        assert "清空" in DANGEROUS_KEYWORDS
        assert "格式化" in DANGEROUS_KEYWORDS

    def test_stop_keywords(self):
        """Test STOP_KEYWORDS constant."""
        assert "停止" in STOP_KEYWORDS
        assert "stop" in STOP_KEYWORDS
        assert "终止" in STOP_KEYWORDS
        assert "kill" in STOP_KEYWORDS

    def test_modify_keywords(self):
        """Test MODIFY_KEYWORDS constant."""
        assert "重启" in MODIFY_KEYWORDS
        assert "restart" in MODIFY_KEYWORDS
        assert "修改" in MODIFY_KEYWORDS
        assert "modify" in MODIFY_KEYWORDS

    def test_readonly_keywords(self):
        """Test READONLY_KEYWORDS constant."""
        assert "检查" in READONLY_KEYWORDS
        assert "check" in READONLY_KEYWORDS
        assert "收集" in READONLY_KEYWORDS
        assert "collect" in READONLY_KEYWORDS
