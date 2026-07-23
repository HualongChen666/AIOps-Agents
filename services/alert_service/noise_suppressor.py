# -*- coding: utf-8 -*-
"""Noise suppression using configurable rules and pattern frequency."""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from typing import Dict, List

from services.alert_service.schemas import Alert, AlertSeverity, SuppressionRule


@dataclass
class _PatternStat:
    count: int
    first_seen: float
    last_seen: float


class NoiseSuppressor:
    """Suppress noisy alerts by rule and auto-detected high-frequency patterns."""

    def __init__(
        self,
        window_seconds: int = 300,
        min_noise_count: int = 10,
        max_entries: int = 5000,
    ) -> None:
        self.window_seconds = window_seconds
        self.min_noise_count = min_noise_count
        self.max_entries = max_entries
        self._rules: List[SuppressionRule] = []
        self._stats: Dict[str, _PatternStat] = {}

    def add_rule(self, rule: SuppressionRule) -> None:
        self._rules.append(rule)

    def list_rules(self) -> List[SuppressionRule]:
        return list(self._rules)

    def is_noise(self, alert: Alert) -> bool:
        fp = alert.fingerprint or self._fingerprint(alert)
        alert.fingerprint = fp

        for rule in self._rules:
            if not rule.enabled:
                continue
            if self._rule_matches(rule, alert):
                alert.suppressed = True
                alert.suppression_reason = rule.reason or f"matched rule {rule.name}"
                return True

        self._update_stats(fp)
        stat = self._stats.get(fp)
        if stat and stat.count >= self.min_noise_count and self._severity_weight(alert.level) <= 1:
            alert.suppressed = True
            alert.suppression_reason = "auto-detected noise pattern"
            return True

        return False

    def _rule_matches(self, rule: SuppressionRule, alert: Alert) -> bool:
        if rule.pattern in (alert.fingerprint or ""):
            return True
        text = f"{alert.title} {alert.description}".lower()
        return rule.pattern.lower() in text

    def _update_stats(self, fp: str) -> None:
        now = time.time()
        self._evict(now)
        if fp in self._stats:
            self._stats[fp].count += 1
            self._stats[fp].last_seen = now
        else:
            self._stats[fp] = _PatternStat(1, now, now)

    def _fingerprint(self, alert: Alert) -> str:
        data = {
            "level": alert.level,
            "category": alert.category,
            "title": alert.title,
            "tags": alert.tags,
        }
        payload = json.dumps(data, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32]

    def _evict(self, now: float) -> None:
        cutoff = now - self.window_seconds
        expired = [fp for fp, s in self._stats.items() if s.last_seen < cutoff]
        for fp in expired:
            del self._stats[fp]
        if len(self._stats) > self.max_entries:
            sorted_items = sorted(self._stats.items(), key=lambda kv: kv[1].last_seen)
            excess = len(self._stats) - self.max_entries
            for fp, _ in sorted_items[:excess]:
                del self._stats[fp]

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

    def get_stats(self) -> Dict[str, int]:
        return {
            "pattern_count": len(self._stats),
            "noise_patterns": sum(
                1 for s in self._stats.values() if s.count >= self.min_noise_count
            ),
        }
