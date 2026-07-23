# -*- coding: utf-8 -*-
"""Alert escalation based on time thresholds and severity."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict, List, Optional

from services.alert_service.schemas import Alert, AlertSeverity, EscalationRule


@dataclass
class _PendingAlert:
    first_seen: float
    alert_id: str


class Escalator:
    """Escalate alerts that remain pending beyond configured time thresholds."""

    def __init__(self) -> None:
        self._rules: List[EscalationRule] = []
        self._pending: Dict[str, _PendingAlert] = {}

    def add_rule(self, rule: EscalationRule) -> None:
        self._rules.append(rule)

    def list_rules(self) -> List[EscalationRule]:
        return list(self._rules)

    def track(self, alert: Alert) -> None:
        if alert.id not in self._pending:
            self._pending[alert.id] = _PendingAlert(time.time(), alert.id)

    def should_escalate(self, alert: Alert) -> Optional[str]:
        severity_weight = self._severity_weight(alert.level)
        pending = self._pending.get(alert.id)
        if not pending:
            return None

        elapsed = time.time() - pending.first_seen
        for rule in self._rules:
            if not rule.enabled:
                continue
            if severity_weight >= self._severity_weight(rule.level_threshold):
                if elapsed >= rule.time_threshold_seconds:
                    alert.status = "escalated"  # type: ignore[assignment]
                    return rule.escalation_target
        return None

    def resolve(self, alert_id: str) -> bool:
        return bool(self._pending.pop(alert_id, None))

    @staticmethod
    def _severity_weight(level: AlertSeverity) -> int:
        weights = {
            AlertSeverity.INFO: 0,
            AlertSeverity.WARNING: 1,
            AlertSeverity.HIGH: 2,
            AlertSeverity.CRITICAL: 3,
            AlertSeverity.FATAL: 4,
        }
        return weights.get(level, 0)

    def clear(self) -> int:
        count = len(self._pending)
        self._pending.clear()
        return count
