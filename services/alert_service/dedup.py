# -*- coding: utf-8 -*-
"""Alert deduplication based on fingerprint and time window."""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from typing import Dict

from loguru import logger

from services.alert_service.schemas import Alert


@dataclass
class _DedupEntry:
    first_seen: float
    last_seen: float
    repeat_count: int = 0
    alert_id: str = ""


class Deduplicator:
    """Deduplicate alerts by fingerprint within a sliding time window."""

    def __init__(self, window_seconds: int = 300, max_entries: int = 5000) -> None:
        self.window_seconds = window_seconds
        self.max_entries = max_entries
        self._cache: Dict[str, _DedupEntry] = {}

    def fingerprint(self, alert: Alert) -> str:
        """Public accessor to compute and assign the stable fingerprint."""
        fp = alert.fingerprint or self._fingerprint(alert)
        alert.fingerprint = fp
        return fp

    def _fingerprint(self, alert: Alert) -> str:
        """按（服务/主机 + 告警类型 + 指标 + 标题）生成去重 key。

        同主机同类型的重复告警会被抑制；不同主机的同类告警保留，
        交由聚合器按根因维度进一步合并。
        """
        keys = ("category", "alert_type", "host", "metric", "title")
        data = {k: getattr(alert, k, "") or "" for k in keys}
        data["level"] = str(alert.level.value) if alert.level else ""
        data["tags"] = alert.tags
        payload = json.dumps(data, sort_keys=True, ensure_ascii=False, default=str)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32]

    def is_duplicate(self, alert: Alert) -> bool:
        """滑动窗口去重：以上一次出现时间为基准，持续相同则抑制。"""
        now = time.time()
        fp = alert.fingerprint or self._fingerprint(alert)
        alert.fingerprint = fp

        self._evict(now)

        if fp in self._cache:
            entry = self._cache[fp]
            elapsed = now - entry.last_seen
            if elapsed < self.window_seconds:
                alert.prev_suppressed = entry.repeat_count
                entry.repeat_count += 1
                entry.last_seen = now
                entry.last_alert = alert
                logger.debug(f"Deduplicated alert {alert.id} (count={entry.repeat_count})")
                return True

        prev_count = self._cache[fp].repeat_count if fp in self._cache else 0
        self._cache[fp] = _DedupEntry(now, now, repeat_count=0, alert_id=alert.id)
        if prev_count:
            alert.prev_suppressed = prev_count
        return False

    def _evict(self, now: float) -> None:
        cutoff = now - self.window_seconds
        expired = [fp for fp, e in self._cache.items() if e.last_seen < cutoff]
        for fp in expired:
            del self._cache[fp]
        if len(self._cache) > self.max_entries:
            sorted_items = sorted(self._cache.items(), key=lambda kv: kv[1].last_seen)
            excess = len(self._cache) - self.max_entries
            for fp, _ in sorted_items[:excess]:
                del self._cache[fp]

    def get_stats(self) -> Dict[str, int]:
        return {
            "cache_size": len(self._cache),
            "total_suppressed": sum(e.repeat_count for e in self._cache.values()),
        }
