# -*- coding: utf-8 -*-
"""WebSocket-based hot update (task 30.4)."""

from __future__ import annotations

from typing import Any, Dict, List

from services.config_service.schemas import ConfigUpdateEvent


class HotUpdateManager:
    """Manages WebSocket subscriptions and hot updates."""

    def __init__(self) -> None:
        self._subscribers: Dict[str, List[Any]] = {}

    async def subscribe(self, namespace: str, connection: Any) -> None:
        self._subscribers.setdefault(namespace, []).append(connection)

    async def publish(self, event: ConfigUpdateEvent) -> int:
        subscribers = self._subscribers.get(event.namespace, [])
        for connection in subscribers:
            if hasattr(connection, "send_json"):
                await connection.send_json(event.model_dump())
        return len(subscribers)

    async def broadcast(self, namespace: str, message: Dict[str, Any]) -> int:
        subscribers = self._subscribers.get(namespace, [])
        for connection in subscribers:
            if hasattr(connection, "send_json"):
                await connection.send_json(message)
        return len(subscribers)
