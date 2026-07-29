# -*- coding: utf-8 -*-
"""Alert escalation based on time thresholds and severity."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from services.alert_service.schemas import Alert, AlertSeverity, EscalationRule


@dataclass
class _PendingAlert:
    first_seen: float
    alert_id: str


@dataclass
class EscalationChain:
    """Multi-level escalation chain with ordered fallback channels."""

    levels: List[str] = field(default_factory=lambda: ["oncall", "second_line", "manager"])
    fallback_channels: List[str] = field(
        default_factory=lambda: ["wecom", "dingtalk", "feishu", "email"]
    )

    def next_level(self, current: str) -> Optional[str]:
        """Return the next escalation level, or None if already at the end."""
        try:
            idx = self.levels.index(current)
        except ValueError:
            return None
        if idx + 1 < len(self.levels):
            return self.levels[idx + 1]
        return None


class Escalator:
    """Escalate alerts that remain pending beyond configured time thresholds."""

    def __init__(
        self,
        chain: Optional[EscalationChain] = None,
        fallback_channels: Optional[List[str]] = None,
    ) -> None:
        self._rules: List[EscalationRule] = []
        self._pending: Dict[str, _PendingAlert] = {}
        self.chain = chain or EscalationChain()
        self.fallback_channels = fallback_channels or self.chain.fallback_channels

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

    def escalate(
        self,
        alert: Alert,
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Build a rich escalation payload when ``should_escalate`` returns a target.

        Returns:
            Dict with escalation target, next levels, fallback channels, and
            full context, or None if the alert does not currently need escalation.
        """
        target = self.should_escalate(alert)
        if not target:
            return None

        ctx = context or {}
        payload = {
            "alert": alert.model_dump(mode="json") if hasattr(alert, "model_dump") else dict(alert),
            "escalation_target": target,
            "next_levels": self.chain.levels,
            "fallback_channels": self.fallback_channels,
            "context": {
                "original_alert": (
                    ctx.get("alert") or alert.model_dump(mode="json")
                    if hasattr(alert, "model_dump")
                    else dict(alert)
                ),
                "investigation_summary": ctx.get("investigation_summary")
                or ctx.get("diagnosis")
                or ctx.get("root_cause"),
                "excluded_causes": ctx.get("excluded_causes"),
                "current_hypothesis": ctx.get("hypothesis") or ctx.get("current_hypothesis"),
                "confidence": ctx.get("confidence"),
                "actions_taken": ctx.get("actions_taken") or ctx.get("executed_commands"),
                "links": {
                    k: v
                    for k, v in (ctx or {}).items()
                    if isinstance(v, str)
                    and any(keyword in k for keyword in ("dashboard", "log", "trace", "url"))
                },
                "severity": (
                    alert.level.value if hasattr(alert.level, "value") else str(alert.level)
                ),
                "elapsed_seconds": time.time()
                - self._pending.get(alert.id, _PendingAlert(time.time(), alert.id)).first_seen,
            },
            "timestamp": time.time(),
        }
        payload["context"]["next_escalation_level"] = self.chain.next_level(target)
        return payload
