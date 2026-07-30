# -*- coding: utf-8 -*-
"""Alert routing using configurable rules and oncall/team integration."""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from services.alert_service.schemas import Alert, RoutingRule

try:
    from core.oncall_adapter import get_oncall_adapter
except Exception as e:
    logging.exception("Unexpected exception: %s", e)
    get_oncall_adapter = None  # type: ignore[assignment]


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

        # 严重告警且未命中自定义规则时,根据团队/oncall 排班解析目标
        if alert.level.value.lower() in ("critical", "fatal", "high"):
            destination = self._resolve_team_route(alert)
        else:
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

    def _resolve_team_route(self, alert: Alert) -> str:
        """根据告警类别/团队/oncall 排班解析目标团队路由"""
        team = str(alert.tags.get("team", alert.tags.get("owner_team", ""))).lower()
        if team:
            return f"team:{team}"
        category = alert.category.lower()
        if callable(get_oncall_adapter):
            try:
                adapter = get_oncall_adapter()
                contacts = adapter.lookup(
                    category=category,
                    service=str(alert.tags.get("service", alert.host or "")),
                    alert_type=alert.alert_type.lower(),
                    team=team,
                )
                if contacts:
                    return f"oncall:{contacts[0].team or category}"
            except Exception as e:
                logging.exception("Unexpected exception: %s", e)
                logging.warning("Suppressed exception", exc_info=True)
                pass
        if category == "security":
            return "team:security"
        if category in ("database", "network"):
            return "team:infrastructure"
        if category in ("frontend", "backend"):
            return f"team:{category}"
        return "default"

    @staticmethod
    def _default_route(alert: Alert) -> str:
        level = alert.level.value.lower()
        category = alert.category.lower()
        if level in ("critical", "fatal"):
            return "immediate"
        if category == "security":
            return "team:security"
        if category in ("database", "network"):
            return "team:infrastructure"
        if category in ("frontend", "backend"):
            return f"team:{category}"
        return "default"
