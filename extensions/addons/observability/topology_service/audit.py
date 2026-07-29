# -*- coding: utf-8 -*-
"""Topology change audit logging."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict

from loguru import logger

from services.topology_service.metrics import TOPOLOGY_AUDIT_EVENTS
from services.topology_service.repository import InMemoryAuditRepository
from services.topology_service.schemas import TopologyAuditEvent


class TopologyAuditStore:
    """Store and query topology audit events."""

    def __init__(self, repository: Any = None) -> None:
        self.repository = repository or InMemoryAuditRepository()

    async def record(
        self,
        topology_id: str,
        event_type: str,
        actor: str,
        details: Dict[str, Any],
    ) -> TopologyAuditEvent:
        """Record a topology change audit event."""
        event = TopologyAuditEvent(
            event_id=f"EV-{uuid.uuid4().hex[:16].upper()}",
            topology_id=topology_id,
            event_type=event_type,
            actor=actor,
            details=details,
            timestamp=datetime.utcnow(),
        )
        await self.repository.save(event)
        TOPOLOGY_AUDIT_EVENTS.labels(event_type=event_type).inc()
        logger.info(f"Audit event {event.event_id} for topology {topology_id}: {event_type}")
        return event

    async def get_events(
        self,
        topology_id: str,
        limit: int = 100,
    ) -> list:
        """Query audit events for a topology."""
        return await self.repository.list(topology_id, limit=limit)
