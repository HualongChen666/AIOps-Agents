# -*- coding: utf-8 -*-
"""Audit event router (task 28.3)."""

from __future__ import annotations

from typing import Any, Dict, List

from services.audit_service.schemas import AuditEvent, AuditEventSeverity


class AuditEventRouter:
    """Routes audit events to appropriate queues."""

    def __init__(self) -> None:
        self._queues: Dict[str, List[Dict[str, Any]]] = {
            "standard": [],
            "priority": [],
            "analytics": [],
        }

    async def route(self, event: AuditEvent) -> str:
        if event.severity in (AuditEventSeverity.HIGH, AuditEventSeverity.CRITICAL):
            queue = "priority"
        elif event.action.startswith("read"):
            queue = "analytics"
        else:
            queue = "standard"
        self._queues[queue].append(event.model_dump())
        return queue

    async def batch_route(self, events: List[AuditEvent]) -> Dict[str, Any]:
        result = {"standard": 0, "priority": 0, "analytics": 0}
        for event in events:
            queue = await self.route(event)
            result[queue] += 1
        return result
