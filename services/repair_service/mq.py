# -*- coding: utf-8 -*-
"""Lightweight in-memory message queue for repair microservice communication."""

from __future__ import annotations

import asyncio
from typing import Any, ClassVar, Dict, Optional

from loguru import logger


class InMemoryMessageQueue:
    """Async in-memory message queue with named channels."""

    _instance: ClassVar[Optional["InMemoryMessageQueue"]] = None
    _queues: Dict[str, asyncio.Queue[Dict[str, Any]]]

    def __new__(cls) -> "InMemoryMessageQueue":
        if cls._instance is None:
            instance = super().__new__(cls)
            instance._queues = {}
            cls._instance = instance
        assert cls._instance is not None
        return cls._instance

    def _get_queue(self, channel: str) -> asyncio.Queue[Dict[str, Any]]:
        if channel not in self._queues:
            self._queues[channel] = asyncio.Queue()
        return self._queues[channel]

    async def publish(self, channel: str, payload: Dict[str, Any]) -> None:
        queue = self._get_queue(channel)
        await queue.put(payload)
        logger.debug(f"Published to {channel}: {payload.get('type', 'message')}")

    async def consume(self, channel: str) -> Dict[str, Any]:
        queue = self._get_queue(channel)
        return await queue.get()

    def get_queue(self, channel: str) -> asyncio.Queue[Dict[str, Any]]:
        return self._get_queue(channel)

    def reset(self) -> None:
        """Clear all queues (useful for tests)."""
        self._queues.clear()


message_queue = InMemoryMessageQueue()
