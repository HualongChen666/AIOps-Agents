# -*- coding: utf-8 -*-
"""Audit event tracker based on message queues (task 28.3)."""

from __future__ import annotations

from typing import Any, Dict, List

from services.audit_service.repository import AuditRepository
from services.audit_service.schemas import AuditEvent, AuditEventStatus


class AuditEventTracker:
    """Tracks audit events with routing and caching."""

    def __init__(self, repo: AuditRepository) -> None:
        self.repo = repo
        self._routes: Dict[str, str] = {}

    async def track(self, event: AuditEvent) -> str:
        event.status = AuditEventStatus.ROUTED
        await self.repo.save_event(event)
        route = self._route(event)
        self._routes[event.event_id] = route
        return route

    def _route(self, event: AuditEvent) -> str:
        if event.severity in ("high", "critical"):
            return "priority-queue"
        return "standard-queue"

    async def batch_track(self, events: List[AuditEvent]) -> Dict[str, Any]:
        routes: Dict[str, int] = {}
        for event in events:
            route = await self.track(event)
            routes[route] = routes.get(route, 0) + 1
        return {"tracked": len(events), "routes": routes}
