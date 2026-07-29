# -*- coding: utf-8 -*-
"""Real-time topology updates over WebSocket."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Set, cast

from loguru import logger

from services.topology_service.metrics import TOPOLOGY_REALTIME_MESSAGES


class RealtimeTopologyManager:
    """Manage WebSocket connections and broadcast topology updates."""

    def __init__(self) -> None:
        self._connections: Set[asyncio.Queue] = set()
        self._topology_cache: Dict[str, Any] = {}

    async def connect(self) -> asyncio.Queue:
        """Register a new WebSocket connection queue."""
        queue: asyncio.Queue = asyncio.Queue()
        self._connections.add(queue)
        TOPOLOGY_REALTIME_MESSAGES.labels(event_type="connect").inc()
        logger.info(f"WebSocket connected; total={len(self._connections)}")
        return queue

    async def disconnect(self, queue: asyncio.Queue) -> None:
        """Remove a WebSocket connection queue."""
        if queue in self._connections:
            self._connections.discard(queue)
            TOPOLOGY_REALTIME_MESSAGES.labels(event_type="disconnect").inc()
        logger.info(f"WebSocket disconnected; total={len(self._connections)}")

    async def broadcast(self, message: Dict[str, Any]) -> None:
        """Broadcast an update to all connected clients."""
        event_type = message.get("type", "update")
        TOPOLOGY_REALTIME_MESSAGES.labels(event_type=event_type).inc()
        dead: List[asyncio.Queue] = []
        for queue in self._connections:
            try:
                queue.put_nowait(message)
            except asyncio.QueueFull:
                dead.append(queue)
        for queue in dead:
            await self.disconnect(queue)

    async def update_topology(
        self,
        topology_id: str,
        update: Dict[str, Any],
    ) -> None:
        """Update cached topology and broadcast the change."""
        self._topology_cache.setdefault(topology_id, {}).update(update)
        message = {
            "type": "topology_update",
            "topology_id": topology_id,
            "update": update,
            "timestamp": datetime.utcnow().isoformat(),
        }
        await self.broadcast(message)

    async def send_heartbeat(self) -> None:
        """Send periodic heartbeat to keep connections alive."""
        await self.broadcast({"type": "heartbeat", "timestamp": datetime.utcnow().isoformat()})

    def get_cache(self, topology_id: str) -> Dict[str, Any]:
        return cast(Dict[str, Any], self._topology_cache.get(topology_id, {}))
