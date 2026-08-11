# -*- coding: utf-8 -*-
"""Tests for core/agent/executor.py."""

from core.agent.executor import (
    RiskAssessor,
    RollbackMechanism,
    SafetyBoundary,
    TrustMechanism,
    ValidationMechanism,
)
from core.command_guard import RiskLevel


def test_safety_boundary_allow_and_forbid():
    boundary = SafetyBoundary(
        allowed_operations=["check", "collect"],
        forbidden_operations=["delete"],
        require_approval_for=["restart"],
    )
    assert boundary.is_operation_allowed("check") is True
    assert boundary.is_operation_allowed("delete") is False
    assert boundary.is_operation_allowed("unknown") is False
    assert boundary.requires_approval("restart") is True
    assert boundary.requires_approval("check") is False


def test_risk_assessor_levels():
    boundary = SafetyBoundary(forbidden_operations=["rm -rf"])
    assessor = RiskAssessor(boundary)

    assert assessor.assess_risk("rm -rf", {}) == (
        RiskLevel.CRITICAL,
        "Operation rm -rf is forbidden",
    )
    assert assessor.assess_risk("delete data", {})[0] == RiskLevel.CRITICAL
    assert assessor.assess_risk("stop service", {})[0] == RiskLevel.HIGH
    assert assessor.assess_risk("restart pod", {})[0] == RiskLevel.MEDIUM
    assert assessor.assess_risk("check cpu", {})[0] == RiskLevel.LOW
    assert assessor.assess_risk("unknown", {})[0] == RiskLevel.MEDIUM


def test_risk_assessor_history():
    assessor = RiskAssessor(SafetyBoundary())
    assert assessor.check_historical_risk("op1") == 1.0
    assessor.record_execution("op1", True)
    assessor.record_execution("op1", False)
    assert assessor.check_historical_risk("op1") == 0.5


def test_trust_mechanism():
    trust = TrustMechanism(initial_trust=0.5, learning_rate=0.1)
    assert trust.get_trust_score("op1") == 0.5
    trust.update_trust("op1", True)
    assert trust.get_trust_score("op1") > 0.5
    trust.update_trust("op1", False)
    assert trust.get_trust_score("op1") < 1.0

    assert trust.can_auto_execute("op1", RiskLevel.LOW) is True
    assert trust.can_auto_execute("op1", RiskLevel.CRITICAL) is False


def test_rollback_mechanism():
    rb = RollbackMechanism()
    called = {"value": False}

    def action():
        called["value"] = True

    rb.register_rollback("op1", action)
    assert rb.execute_rollback("op1") is True
    assert called["value"] is True
    assert rb.execute_rollback("missing") is False


def test_validation_mechanism():
    validator = ValidationMechanism()
    assert validator.validate("op1", "result", {}) == (True, "No validation rules")

    def rule(result, context):
        return result == "ok", "result must be ok"

    validator.register_validation("op1", rule)
    assert validator.validate("op1", "ok", {}) == (True, "All validations passed")
    assert validator.validate("op1", "bad", {}) == (False, "result must be ok")
