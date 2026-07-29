# -*- coding: utf-8 -*-
"""Alert classification based on configurable rules and keyword heuristics."""

from __future__ import annotations

from typing import Any, Dict, List

from services.alert_service.schemas import Alert, AlertSeverity, ClassificationRule


class Classifier:
    """Classify alerts using rules and fallback keyword inference."""

    def __init__(self, default_category: str = "system", default_priority: str = "P3") -> None:
        self.default_category = default_category
        self.default_priority = default_priority
        self._rules: List[ClassificationRule] = []

    def add_rule(self, rule: ClassificationRule) -> None:
        self._rules.append(rule)

    def list_rules(self) -> List[ClassificationRule]:
        return list(self._rules)

    def classify(self, alert: Alert) -> Alert:
        for rule in self._rules:
            if not rule.enabled:
                continue
            if self._match(alert, rule.conditions):
                alert.category = rule.category
                alert.priority = rule.priority
                alert.tags["classification_rule"] = rule.name
                return alert

        # Fallback keyword classification
        category, priority = self._keyword_classify(alert.title + " " + alert.description)
        alert.category = category
        alert.priority = priority

        # Critical business-impact override: ensure CRITICAL severity on high-impact
        # categories jumps to the front of the priority queue without over-classifying
        # lower-severity alerts.
        if (
            alert.level == AlertSeverity.CRITICAL
            and alert.category in ("database", "payment", "auth", "security")
            and alert.priority != "P0"
        ):
            alert.priority = "P0"
            alert.tags["priority_override"] = "critical_business_impact"

        return alert

    def _match(self, alert: Alert, conditions: Dict[str, Any]) -> bool:
        flat = alert.model_dump()
        flat.update(alert.tags)
        for key, expected in conditions.items():
            if key.startswith("tags."):
                actual = alert.tags.get(key.split(".", 1)[1])
            else:
                actual = flat.get(key)
            if actual != expected:
                return False
        return True

    @staticmethod
    def _keyword_classify(text: str) -> tuple:
        lower = text.lower()
        if any(k in lower for k in ("ssh", "brute", "unauthorized", "attack")):
            return "security", "P1"
        if any(k in lower for k in ("cpu", "memory", "disk", "load")):
            return "performance", "P3"
        if any(k in lower for k in ("database", "db", "postgres", "sql")):
            return "database", "P1"
        if any(k in lower for k in ("network", "dns", "ping", "latency")):
            return "network", "P2"
        return "system", "P3"
