# -*- coding: utf-8 -*-
"""Repair audit log with event sourcing."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger

from services.repair_service.metrics import REPAIR_AUDIT_EVENTS
from services.repair_service.schemas import AuditEvent


class AuditStore:
    """In-memory event sourcing store for repair audit logs."""

    def __init__(self) -> None:
        self._events: List[AuditEvent] = []

    async def record(
        self,
        task_id: str,
        event_type: str,
        actor: str = "system",
        payload: Optional[Dict[str, Any]] = None,
    ) -> AuditEvent:
        event = AuditEvent(
            event_id=str(uuid.uuid4()),
            task_id=task_id,
            event_type=event_type,
            actor=actor,
            payload=payload or {},
        )
        self._events.append(event)
        REPAIR_AUDIT_EVENTS.labels(event_type=event_type).inc()
        logger.info(f"Audit event {event_type} for task {task_id}")
        return event

    async def get_events(
        self,
        task_id: str,
    ) -> List[AuditEvent]:
        return [e for e in self._events if e.task_id == task_id]

    async def query(
        self,
        event_type: Optional[str] = None,
        limit: int = 100,
    ) -> List[AuditEvent]:
        events = self._events
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        return sorted(events, key=lambda e: e.timestamp, reverse=True)[:limit]

    async def analyze(self, task_id: str) -> Dict[str, Any]:
        events = await self.get_events(task_id)
        types: Dict[str, int] = {}
        for e in events:
            types[e.event_type] = types.get(e.event_type, 0) + 1
        return {
            "task_id": task_id,
            "total_events": len(events),
            "event_types": types,
            "first_event": events[0].timestamp.isoformat() if events else None,
            "last_event": events[-1].timestamp.isoformat() if events else None,
        }

    async def snapshot(self, task_id: str, state: Dict[str, Any]) -> None:
        await self.record(
            task_id=task_id,
            event_type="snapshot",
            payload={"state": state, "timestamp": datetime.utcnow().isoformat()},
        )
