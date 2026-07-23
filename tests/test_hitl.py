# -*- coding: utf-8 -*-
"""
HITL Module Tests
"""

import pytest  # noqa: F401

from core.hitl import (  # noqa: F401
    ApprovalConfig,
    ApprovalHistory,
    ApprovalLevel,
    ApprovalNotifier,
    ApprovalRequest,
    ApprovalRule,
    ApprovalStatus,
    ApprovalStep,
    ApprovalWorkflow,
    ConditionalApproval,
    MultiLevelApprover,
    NotificationConfig,
    RuleOperator,
)


class TestApprovalWorkflow:
    """Test approval workflow"""

    def test_create_request(self):
        """Test creating approval request"""
        workflow = ApprovalWorkflow()

        steps = [ApprovalStep(step_id="step1", name="Step 1", approver="user1")]

        request = workflow.create_request(
            workflow_id="test_wf", title="Test Request", description="Test Description", steps=steps
        )

        assert request.request_id is not None
        assert len(request.steps) == 1

    def test_approve_step(self):
        """Test approving a step"""
        workflow = ApprovalWorkflow()

        steps = [ApprovalStep(step_id="step1", name="Step 1", approver="user1")]

        request = workflow.create_request(
            workflow_id="test_wf", title="Test Request", description="Test Description", steps=steps
        )

        result = workflow.approve_step(request.request_id, "step1", "user1", "Approved")

        assert result is True
        assert request.steps[0].status == ApprovalStatus.APPROVED

    def test_reject_step(self):
        """Test rejecting a step"""
        workflow = ApprovalWorkflow()

        steps = [ApprovalStep(step_id="step1", name="Step 1", approver="user1")]

        request = workflow.create_request(
            workflow_id="test_wf", title="Test Request", description="Test Description", steps=steps
        )

        result = workflow.reject_step(request.request_id, "step1", "user1", "Rejected")

        assert result is True
        assert request.status == ApprovalStatus.REJECTED


class TestMultiLevelApprover:
    """Test multi-level approver"""

    def test_configure_level(self):
        """Test configuring approval level"""
        workflow = ApprovalWorkflow()
        approver = MultiLevelApprover(workflow)

        config = ApprovalConfig(level=ApprovalLevel.L1, approvers=["user1", "user2"])

        approver.configure_level(config)

        assert ApprovalLevel.L1 in approver.level_configs

    def test_create_multi_level_request(self):
        """Test creating multi-level request"""
        workflow = ApprovalWorkflow()
        approver = MultiLevelApprover(workflow)

        approver.configure_level(ApprovalConfig(level=ApprovalLevel.L1, approvers=["user1"]))

        request = approver.create_multi_level_request(
            workflow_id="test_wf",
            title="Test Request",
            description="Test Description",
            min_level=ApprovalLevel.L1,
        )

        assert len(request.steps) == 1


class TestConditionalApproval:
    """Test conditional approval"""

    def test_add_rule(self):
        """Test adding approval rule"""
        conditional = ConditionalApproval()

        rule = ApprovalRule(
            rule_id="rule1",
            name="Test Rule",
            field="risk_level",
            operator=RuleOperator.EQUALS,
            value="low",
            action="auto_approve",
        )

        conditional.add_rule(rule)

        assert len(conditional.rules) == 1

    def test_evaluate_rules(self):
        """Test evaluating rules"""
        conditional = ConditionalApproval()

        conditional.add_rule(
            ApprovalRule(
                rule_id="auto_approve",
                name="Auto Approve",
                field="risk_level",
                operator=RuleOperator.EQUALS,
                value="low",
                action="auto_approve",
            )
        )

        context = {"risk_level": "low"}
        result = conditional.evaluate_rules(context)

        assert result["requires_approval"] is False
        assert result["action"] == "auto_approve"


class TestApprovalHistory:
    """Test approval history"""

    def test_record_action(self):
        """Test recording approval action"""
        history = ApprovalHistory()

        record = history.record_action(
            request_id="req1", workflow_id="wf1", action="approve", actor="user1"
        )

        assert record.record_id is not None
        assert len(history.records) == 1

    def test_get_history(self):
        """Test getting approval history"""
        history = ApprovalHistory()

        history.record_action(request_id="req1", workflow_id="wf1", action="approve", actor="user1")

        history.record_action(request_id="req2", workflow_id="wf1", action="reject", actor="user2")

        req1_history = history.get_history(request_id="req1")

        assert len(req1_history) == 1
