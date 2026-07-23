# -*- coding: utf-8 -*-
"""
Conditional Approval
Implements conditional approval rules
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List

from loguru import logger


class RuleOperator(Enum):
    """Rule operator"""

    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    CONTAINS = "contains"
    IN = "in"


@dataclass
class ApprovalRule:
    """
    Approval rule

    Attributes:
        rule_id: Rule identifier
        name: Rule name
        field: Field to check
        operator: Comparison operator
        value: Expected value
        action: Action to take if rule matches
    """

    rule_id: str
    name: str
    field: str
    operator: RuleOperator
    value: Any
    action: str  # "require_approval", "auto_approve", "auto_reject"

    def evaluate(self, context: Dict[str, Any]) -> bool:
        """
        Evaluate rule against context

        Args:
            context: Context data

        Returns:
            True if rule matches
        """
        field_value = context.get(self.field)

        if self.operator == RuleOperator.EQUALS:
            return bool(field_value == self.value)
        elif self.operator == RuleOperator.NOT_EQUALS:
            return bool(field_value != self.value)
        elif self.operator == RuleOperator.GREATER_THAN:
            return bool(field_value > self.value)
        elif self.operator == RuleOperator.LESS_THAN:
            return bool(field_value < self.value)
        elif self.operator == RuleOperator.CONTAINS:
            return self.value in str(field_value)
        elif self.operator == RuleOperator.IN:
            return field_value in self.value if isinstance(self.value, list) else False

        return False


class ConditionalApproval:
    """
    Conditional approval manager

    Applies rules to determine if approval is required
    """

    def __init__(self):
        """Initialize conditional approval"""
        self.rules: List[ApprovalRule] = []

    def add_rule(self, rule: ApprovalRule) -> None:
        """
        Add approval rule

        Args:
            rule: Approval rule
        """
        self.rules.append(rule)
        logger.info(f"Added approval rule: {rule.name}")

    def evaluate_rules(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate all rules against context

        Args:
            context: Context data

        Returns:
            Evaluation result
        """
        matched_rules = []

        for rule in self.rules:
            if rule.evaluate(context):
                matched_rules.append(rule)

        # Determine action based on matched rules
        if not matched_rules:
            return {"requires_approval": True, "action": "default", "matched_rules": []}

        # Check for auto-approve or auto-reject
        for rule in matched_rules:
            if rule.action == "auto_approve":
                return {
                    "requires_approval": False,
                    "action": "auto_approve",
                    "matched_rules": [r.rule_id for r in matched_rules],
                }
            elif rule.action == "auto_reject":
                return {
                    "requires_approval": False,
                    "action": "auto_reject",
                    "matched_rules": [r.rule_id for r in matched_rules],
                }

        # Default to require approval
        return {
            "requires_approval": True,
            "action": "require_approval",
            "matched_rules": [r.rule_id for r in matched_rules],
        }

    def add_default_rules(self) -> None:
        """Add default approval rules"""
        default_rules = [
            ApprovalRule(
                rule_id="low_risk_auto_approve",
                name="Low Risk Auto-Approve",
                field="risk_level",
                operator=RuleOperator.EQUALS,
                value="low",
                action="auto_approve",
            ),
            ApprovalRule(
                rule_id="high_risk_require_approval",
                name="High Risk Require Approval",
                field="risk_level",
                operator=RuleOperator.EQUALS,
                value="high",
                action="require_approval",
            ),
            ApprovalRule(
                rule_id="small_change_auto_approve",
                name="Small Change Auto-Approve",
                field="change_size",
                operator=RuleOperator.LESS_THAN,
                value=100,
                action="auto_approve",
            ),
            ApprovalRule(
                rule_id="large_change_require_approval",
                name="Large Change Require Approval",
                field="change_size",
                operator=RuleOperator.GREATER_THAN,
                value=1000,
                action="require_approval",
            ),
        ]

        for rule in default_rules:
            self.add_rule(rule)
