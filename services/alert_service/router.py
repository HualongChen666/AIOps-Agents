# -*- coding: utf-8 -*-
"""Alert routing using configurable rules."""

from __future__ import annotations

from typing import Any, Dict, List

from services.alert_service.schemas import Alert, RoutingRule


class Router:
    """Route alerts to destinations based on rules and default severity logic."""

    def __init__(self) -> None:
        self._rules: List[RoutingRule] = []

    def add_rule(self, rule: RoutingRule) -> None:
        self._rules.append(rule)
        # Higher priority first
        self._rules.sort(key=lambda r: r.priority, reverse=True)

    def list_rules(self) -> List[RoutingRule]:
        return list(self._rules)

    def route(self, alert: Alert) -> str:
        for rule in self._rules:
            if not rule.enabled:
                continue
            if self._match(alert, rule.conditions):
                alert.routed_to = rule.destination
                return rule.destination

        destination = self._default_route(alert)
        alert.routed_to = destination
        return destination

    def _match(self, alert: Alert, conditions: Dict[str, Any]) -> bool:
        flat = alert.model_dump()
        flat.update(alert.tags)
        for key, expected in conditions.items():
            if key.startswith("tags."):
                actual = flat.get(key)
            else:
                actual = flat.get(key)
            if actual != expected:
                return False
        return True

    @staticmethod
    def _default_route(alert: Alert) -> str:
        level = alert.level.value.lower()
        category = alert.category.lower()
        if level in ("critical", "fatal"):
            return "immediate"
        if category == "security":
            return "security_team"
        if category in ("database", "network"):
            return "infrastructure_team"
        return "default"
