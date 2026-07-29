# -*- coding: utf-8 -*-
"""Time-window alert aggregation (sliding and tumbling)."""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional

from services.alert_service.schemas import AggregatedAlert, Alert, AlertSeverity


def _to_timestamp(dt: datetime) -> float:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc).timestamp()
    return dt.timestamp()


@dataclass
class _WindowEntry:
    ts: float
    alert: Alert


class TimeWindowAggregator:
    """Aggregate similar alerts using sliding or tumbling time windows."""

    def __init__(
        self,
        window_seconds: int = 300,
        mode: str = "tumbling",
        signature_fields: Optional[tuple] = None,
    ) -> None:
        self.window_seconds = window_seconds
        self.mode = mode
        # Root-cause aggregation: group by incident type, not by individual host.
        self.signature_fields = signature_fields or (
            "category",
            "alert_type",
            "metric",
        )
        self._sliding: Dict[str, List[_WindowEntry]] = {}
        self._tumbling: Dict[str, Dict[int, List[Alert]]] = {}

    def _signature(self, alert: Alert) -> str:
        return "|".join(str(getattr(alert, f, "") or "").lower() for f in self.signature_fields)

    def add(self, alert: Alert) -> List[Alert]:
        if self.mode == "tumbling":
            return self._add_tumbling(alert)
        return self._add_sliding(alert)

    def _add_sliding(self, alert: Alert) -> List[Alert]:
        ts = _to_timestamp(alert.detected_at)
        sig = self._signature(alert)
        entries = self._sliding.setdefault(sig, [])
        entries.append(_WindowEntry(ts, alert))

        cutoff = ts - self.window_seconds
        entries[:] = [e for e in entries if e.ts >= cutoff]

        if len(entries) > 1:
            aggregated = self._aggregate([e.alert for e in entries], sig)
            self._sliding[sig] = []
            return [aggregated]
        return []

    def _add_tumbling(self, alert: Alert) -> List[Alert]:
        ts = _to_timestamp(alert.detected_at)
        bucket = int(ts // self.window_seconds)
        sig = self._signature(alert)
        buckets = self._tumbling.setdefault(sig, {})

        flushed: List[Alert] = []
        for old_bucket in sorted(b for b in buckets if b < bucket):
            alerts = buckets.pop(old_bucket)
            flushed.append(self._aggregate(alerts, sig) if len(alerts) > 1 else alerts[0])

        buckets.setdefault(bucket, []).append(alert)
        return flushed

    def _aggregate(self, alerts: List[Alert], cluster_id: str) -> AggregatedAlert:
        base = max(
            alerts,
            key=lambda a: self._severity_weight(a.level),
        )
        return AggregatedAlert(
            **base.model_dump(
                exclude={"id", "title", "description", "aggregated_count", "aggregated_alerts"}
            ),
            id=f"AGG-{cluster_id}-{int(time.time() * 1000)}",
            title=f"[聚合] {base.title}",
            description=f"聚合了 {len(alerts)} 个相似告警",
            aggregated_count=len(alerts),
            aggregated_alerts=alerts,
            cluster_id=cluster_id,
        )

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

    def flush(self, force: bool = False) -> List[Alert]:
        if self.mode == "tumbling":
            return self._flush_tumbling(force=force)
        return self._flush_sliding(force=force)

    def _flush_sliding(self, force: bool = False) -> List[Alert]:
        now = time.time()
        cutoff = now - self.window_seconds
        results: List[Alert] = []
        for sig, entries in list(self._sliding.items()):
            expired = [e for e in entries if force or e.ts < cutoff]
            active = [e for e in entries if not force and e.ts >= cutoff]
            if expired:
                results.append(
                    self._aggregate([e.alert for e in expired], sig)
                    if len(expired) > 1
                    else expired[0].alert
                )
            if active:
                self._sliding[sig] = active
            else:
                self._sliding.pop(sig, None)
        return results

    def _flush_tumbling(self, force: bool = False) -> List[Alert]:
        results: List[Alert] = []
        for sig, buckets in list(self._tumbling.items()):
            for bucket, alerts in list(buckets.items()):
                results.append(
                    self._aggregate(alerts, f"{sig}-{bucket}") if len(alerts) > 1 else alerts[0]
                )
            self._tumbling.pop(sig, None)
        return results
