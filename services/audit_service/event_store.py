# -*- coding: utf-8 -*-
"""Event sourcing store for audit events (task 28.2)."""

from __future__ import annotations

from typing import Any, Dict, List

from loguru import logger

from services.audit_service.repository import AuditRepository
from services.audit_service.schemas import AuditEvent


class EventStore:
    """Append-only event store with projection support."""

    def __init__(self, repo: AuditRepository) -> None:
        self.repo = repo

    async def append(self, event: AuditEvent) -> str:
        await self.repo.save_event(event)
        logger.info(f"Appended audit event {event.event_id}")
        return event.event_id

    async def get_stream(
        self,
        tenant_id: str,
        limit: int = 100,
    ) -> List[AuditEvent]:
        return await self.repo.list_events(tenant_id=tenant_id, limit=limit)

    async def project(self, tenant_id: str) -> Dict[str, Any]:
        events = await self.get_stream(tenant_id)
        return {
            "tenant_id": tenant_id,
            "total": len(events),
            "by_severity": self._count(events, "severity"),
            "by_action": self._count(events, "action"),
        }

    @staticmethod
    def _count(events: List[AuditEvent], field: str) -> Dict[str, int]:
        result: Dict[str, int] = {}
        for event in events:
            value = getattr(event, field)
            result[value] = result.get(value, 0) + 1
        return result
