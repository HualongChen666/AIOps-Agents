# -*- coding: utf-8 -*-
"""Audit log analyzer (task 28.2)."""

from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List

from services.audit_service.repository import AuditRepository


class AuditAnalyzer:
    """Analyzes audit event streams."""

    def __init__(self, repo: AuditRepository) -> None:
        self.repo = repo

    async def analyze(self, tenant_id: str) -> Dict[str, Any]:
        events = await self.repo.list_events(tenant_id=tenant_id, limit=10000)
        actions = [e.action for e in events]
        severities = [e.severity for e in events]
        return {
            "tenant_id": tenant_id,
            "total": len(events),
            "top_actions": dict(Counter(actions).most_common(10)),
            "severity_distribution": dict(Counter(severities)),
            "high_severity_count": sum(1 for e in events if e.severity in ("high", "critical")),
        }

    async def detect_anomalies(self, tenant_id: str) -> List[Dict[str, Any]]:
        analysis = await self.analyze(tenant_id)
        alerts = []
        if analysis["high_severity_count"] > 0:
            alerts.append(
                {
                    "type": "high_severity_events",
                    "count": analysis["high_severity_count"],
                    "severity": "high",
                }
            )
        return alerts
