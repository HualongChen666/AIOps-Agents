# -*- coding: utf-8 -*-
"""Audit query utilities (task 28.2)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from services.audit_service.repository import AuditRepository
from services.audit_service.schemas import AuditEvent


class AuditQuery:
    """Query interface for audit events."""

    def __init__(self, repo: AuditRepository) -> None:
        self.repo = repo

    async def search(
        self,
        tenant_id: Optional[str] = None,
        action: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 100,
    ) -> List[AuditEvent]:
        events = await self.repo.list_events(tenant_id=tenant_id, limit=limit)
        if action:
            events = [e for e in events if e.action == action]
        if severity:
            events = [e for e in events if e.severity == severity]
        return events

    async def analyze(self, tenant_id: str) -> Dict[str, Any]:
        events = await self.repo.list_events(tenant_id=tenant_id, limit=10000)
        return {
            "tenant_id": tenant_id,
            "total": len(events),
            "by_action": self._group_count(events, "action"),
            "by_severity": self._group_count(events, "severity"),
        }

    @staticmethod
    def _group_count(events: List[AuditEvent], field: str) -> Dict[str, int]:
        result: Dict[str, int] = {}
        for event in events:
            value = getattr(event, field)
            result[value] = result.get(value, 0) + 1
        return result
