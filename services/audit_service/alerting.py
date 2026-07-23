# -*- coding: utf-8 -*-
"""Audit alerting based on rules (task 28.8)."""

from __future__ import annotations

from typing import Dict, List

from services.audit_service.repository import AuditRepository
from services.audit_service.schemas import AlertRule, AuditEvent, AuditEventSeverity


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
            return bool(eval(rule.condition, {"__builtins__": {}}, local_ctx))  # noqa: S307
        except Exception:
            return False

    async def add_rule(self, rule: AlertRule) -> None:
        self.rules[rule.rule_id] = rule
