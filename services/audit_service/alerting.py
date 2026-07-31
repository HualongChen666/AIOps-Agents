# -*- coding: utf-8 -*-
"""Audit alerting based on rules (task 28.8)."""

from __future__ import annotations

import ast
import logging
from typing import Any, Dict, List

from services.audit_service.repository import AuditRepository
from services.audit_service.schemas import AlertRule, AuditEvent, AuditEventSeverity


def _safe_eval_condition(condition: str, ctx: Dict[str, Any]) -> bool:
    """Evaluate a restricted audit alert condition without using eval()."""
    allowed_calls = ("startswith", "endswith")
    allowed_ops = {
        ast.Eq: lambda a, b: a == b,
        ast.NotEq: lambda a, b: a != b,
        ast.Lt: lambda a, b: a < b,
        ast.LtE: lambda a, b: a <= b,
        ast.Gt: lambda a, b: a > b,
        ast.GtE: lambda a, b: a >= b,
        ast.In: lambda a, b: a in b,
        ast.NotIn: lambda a, b: a not in b,
    }

    def _eval(node: ast.AST) -> Any:
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Name):
            if node.id not in ctx:
                raise NameError(node.id)
            return ctx[node.id]
        if isinstance(node, ast.Compare):
            left = _eval(node.left)
            for op, comparator in zip(node.ops, node.comparators):
                right = _eval(comparator)
                handler = allowed_ops.get(type(op))
                if handler is None:
                    raise ValueError(f"Disallowed operator: {op}")
                if not handler(left, right):
                    return False
                left = right
            return True
        if isinstance(node, ast.BoolOp):
            if isinstance(node.op, ast.And):
                return all(_eval(v) for v in node.values)
            if isinstance(node.op, ast.Or):
                return any(_eval(v) for v in node.values)
            raise ValueError(f"Disallowed bool op: {node.op}")
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            return not _eval(node.operand)
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Attribute):
                raise ValueError("Only attribute calls are allowed")
            if node.func.attr not in allowed_calls or node.keywords:
                raise ValueError(f"Disallowed call: {node.func.attr}")
            obj = _eval(node.func.value)
            args = [_eval(a) for a in node.args]
            return getattr(obj, node.func.attr)(*args)
        raise ValueError(f"Disallowed expression: {node}")

    return bool(_eval(ast.parse(condition, mode="eval").body))


class AlertingEngine:
    """Rule-based alerting engine for audit events."""

    DEFAULT_RULES: List[AlertRule] = [
        AlertRule(
            rule_id="r1",
            name="critical_event",
            condition="severity == 'critical'",
            severity=AuditEventSeverity.CRITICAL,
            action="notify",
        ),
        AlertRule(
            rule_id="r2",
            name="high_event",
            condition="severity == 'high'",
            severity=AuditEventSeverity.HIGH,
            action="notify",
        ),
        AlertRule(
            rule_id="r3",
            name="unauthorized_access",
            condition="action == 'unauthorized_access'",
            severity=AuditEventSeverity.HIGH,
            action="block",
        ),
        AlertRule(
            rule_id="r4",
            name="admin_action",
            condition="action.startswith('admin')",
            severity=AuditEventSeverity.MEDIUM,
            action="log",
        ),
        AlertRule(
            rule_id="r5",
            name="data_export",
            condition="action == 'export'",
            severity=AuditEventSeverity.MEDIUM,
            action="log",
        ),
        AlertRule(
            rule_id="r6",
            name="login_failure",
            condition="action == 'login_failure'",
            severity=AuditEventSeverity.LOW,
            action="log",
        ),
        AlertRule(
            rule_id="r7",
            name="permission_change",
            condition="action == 'permission_change'",
            severity=AuditEventSeverity.HIGH,
            action="notify",
        ),
        AlertRule(
            rule_id="r8",
            name="delete_attempt",
            condition="action == 'delete'",
            severity=AuditEventSeverity.MEDIUM,
            action="log",
        ),
        AlertRule(
            rule_id="r9",
            name="config_change",
            condition="action == 'config_change'",
            severity=AuditEventSeverity.HIGH,
            action="notify",
        ),
        AlertRule(
            rule_id="r10",
            name="after_hours",
            condition="action == 'after_hours_access'",
            severity=AuditEventSeverity.LOW,
            action="log",
        ),
    ]

    def __init__(self, repo: AuditRepository) -> None:
        self.repo = repo
        self.rules: Dict[str, AlertRule] = {r.rule_id: r for r in self.DEFAULT_RULES}

    async def evaluate(self, event: AuditEvent) -> List[AlertRule]:
        triggered = []
        for rule in self.rules.values():
            if self._match(rule, event):
                triggered.append(rule)
        return triggered

    def _match(self, rule: AlertRule, event: AuditEvent) -> bool:
        if not rule.enabled:
            return False
        local_ctx = {"severity": event.severity, "action": event.action}
        try:
            return _safe_eval_condition(rule.condition, local_ctx)
        except Exception as e:
            logging.exception("Unexpected exception: %s", e)
            return False

    async def add_rule(self, rule: AlertRule) -> None:
        self.rules[rule.rule_id] = rule
