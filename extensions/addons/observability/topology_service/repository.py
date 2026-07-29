# -*- coding: utf-8 -*-
"""Topology repository abstraction."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger

from services.topology_service.schemas import (
    ServiceTopology,
    TopologyAuditEvent,
)


class TopologyRepository(ABC):
    """Abstract topology repository."""

    @abstractmethod
    async def save(self, topology: ServiceTopology) -> str: ...

    @abstractmethod
    async def get(self, topology_id: str) -> Optional[ServiceTopology]: ...

    @abstractmethod
    async def list(self, limit: int = 100) -> List[ServiceTopology]: ...

    @abstractmethod
    async def update(self, topology_id: str, data: Dict[str, Any]) -> bool: ...

    @abstractmethod
    async def delete(self, topology_id: str) -> bool: ...

    @abstractmethod
    async def count(self) -> int: ...


class InMemoryTopologyRepository(TopologyRepository):
    """In-memory repository for tests and local dev."""

    def __init__(self) -> None:
        self._topologies: Dict[str, ServiceTopology] = {}

    async def save(self, topology: ServiceTopology) -> str:
        if not topology.topology_id:
            raise ValueError("topology_id is required")
        topology.updated_at = datetime.utcnow()
        self._topologies[topology.topology_id] = topology
        logger.debug(f"Repository saved topology {topology.topology_id}")
        return topology.topology_id

    async def get(self, topology_id: str) -> Optional[ServiceTopology]:
        return self._topologies.get(topology_id)

    async def list(self, limit: int = 100) -> List[ServiceTopology]:
        topologies = sorted(
            self._topologies.values(),
            key=lambda t: t.updated_at,
            reverse=True,
        )
        return topologies[:limit]

    async def update(self, topology_id: str, data: Dict[str, Any]) -> bool:
        topology = self._topologies.get(topology_id)
        if not topology:
            return False
        merged = topology.model_dump() | data
        self._topologies[topology_id] = ServiceTopology.model_validate(merged)
        self._topologies[topology_id].updated_at = datetime.utcnow()
        return True

    async def delete(self, topology_id: str) -> bool:
        if topology_id in self._topologies:
            del self._topologies[topology_id]
            return True
        return False

    async def count(self) -> int:
        return len(self._topologies)


async def get_repository(use_in_memory: bool = True) -> TopologyRepository:
    """Return repository instance based on configuration."""
    return InMemoryTopologyRepository()


class AuditRepository(ABC):
    """Abstract audit repository."""

    @abstractmethod
    async def save(self, event: TopologyAuditEvent) -> str: ...

    @abstractmethod
    async def list(self, topology_id: str, limit: int = 100) -> List[TopologyAuditEvent]: ...


class InMemoryAuditRepository(AuditRepository):
    """In-memory audit repository."""

    def __init__(self) -> None:
        self._events: Dict[str, List[TopologyAuditEvent]] = {}

    async def save(self, event: TopologyAuditEvent) -> str:
        self._events.setdefault(event.topology_id, []).append(event)
        return event.event_id

    async def list(self, topology_id: str, limit: int = 100) -> List[TopologyAuditEvent]:
        events = self._events.get(topology_id, [])
        return events[-limit:]
