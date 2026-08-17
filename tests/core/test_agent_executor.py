# -*- coding: utf-8 -*-
"""Unit tests for core/agent/executor.py."""

import pytest  # noqa: F401  # Imported for test setup

from core.agent.executor import (
    RiskAssessor,
    RollbackMechanism,
    SafetyBoundary,
    TrustMechanism,
    ValidationMechanism,
    create_autonomous_executor,
)
from core.command_guard import RiskLevel


def test_safety_boundary():
    boundary = SafetyBoundary(
        allowed_operations=["read"],
        forbidden_operations=["delete"],
        require_approval_for=["write"],
    )
    assert boundary.is_operation_allowed("read") is True
    assert boundary.is_operation_allowed("delete") is False
    assert boundary.is_operation_allowed("unknown") is False
    assert boundary.requires_approval("write") is True
    assert boundary.requires_approval("read") is False


def test_risk_assessor():
    boundary = SafetyBoundary(forbidden_operations=["rm -rf"])
    assessor = RiskAssessor(boundary)
    level, reason = assessor.assess_risk("collect_metrics", {})
    assert reason
    assert assessor.check_historical_risk("collect_metrics") == 1.0
    assert assessor.check_historical_risk("unknown") == 1.0


def test_trust_mechanism():
    trust = TrustMechanism(initial_trust=0.5, learning_rate=0.1)
    assert trust.get_trust_score("op") == 0.5
    trust.update_trust("op", True)
    assert trust.get_trust_score("op") > 0.5
    assert trust.can_auto_execute("op", RiskLevel.LOW) is True
    assert trust.can_auto_execute("op", RiskLevel.CRITICAL) is False


def test_rollback_mechanism():
    rollback = RollbackMechanism()
    called = []
    rollback.register_rollback("op1", lambda: called.append(1))
    assert rollback.execute_rollback("op1") is True
    assert called == [1]
    assert rollback.execute_rollback("missing") is False


def test_validation_mechanism():
    validator = ValidationMechanism()
    assert validator.validate("op", None, {}) == (True, "No validation rules")
    validator.register_validation("op", lambda r, c: (True, "ok"))
    assert validator.validate("op", None, {}) == (True, "All validations passed")
    validator.register_validation("op", lambda r, c: (False, "bad"))
    assert validator.validate("op", None, {}) == (False, "bad")


@pytest.mark.timeout(120)
def test_autonomous_executor_plan_dry_run():
    executor = create_autonomous_executor()
    executor.tool_executor.dry_run = True
    executor.set_execution_mode("hybrid")
    result = executor.execute_plan(  # noqa: F841  # Variable for test verification
        goal="collect cpu metrics",
        context={"target": "system"},
        available_tools=["collect_metrics", "collect_logs"],
    )
    assert "tasks" in result
    assert "results" in result
    stats = executor.get_statistics()
    assert isinstance(stats, dict)
