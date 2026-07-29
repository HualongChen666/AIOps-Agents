# -*- coding: utf-8 -*-
"""Lightweight in-memory priority message queue for microservice communication."""

from __future__ import annotations

import asyncio
import itertools
from typing import Any, ClassVar, Dict, Optional, Tuple

from loguru import logger


class InMemoryMessageQueue:
    """Async in-memory priority message queue with named channels.

    Lower ``priority`` values are consumed first. Within the same priority,
    messages are consumed in FIFO order.
    """

    _instance: ClassVar[Optional["InMemoryMessageQueue"]] = None
    _queues: Dict[str, asyncio.PriorityQueue[Tuple[int, int, Dict[str, Any]]]]
    _counter: ClassVar[itertools.count] = itertools.count()

    def __new__(cls) -> "InMemoryMessageQueue":
        instance = cls._instance
        if instance is None:
            instance = super().__new__(cls)
            instance._queues = {}
            cls._instance = instance
        return instance

    def _get_queue(self, channel: str) -> asyncio.PriorityQueue[Tuple[int, int, Dict[str, Any]]]:
        if channel not in self._queues:
            self._queues[channel] = asyncio.PriorityQueue()
        return self._queues[channel]

    async def publish(
        self,
        channel: str,
        payload: Dict[str, Any],
        priority: int = 0,
    ) -> None:
        queue = self._get_queue(channel)
        queue.put_nowait((priority, next(self._counter), payload))
        logger.debug(f"Published to {channel}: {payload.get('type', 'message')}")

    async def consume(self, channel: str) -> Dict[str, Any]:
        queue = self._get_queue(channel)
        _, _, payload = await queue.get()
        return payload

    def qsize(self, channel: str) -> int:
        return self._get_queue(channel).qsize()

    def get_queue(self, channel: str) -> asyncio.PriorityQueue[Tuple[int, int, Dict[str, Any]]]:
        return self._get_queue(channel)

    def reset(self) -> None:
        """Clear all queues (useful for tests)."""
        self._queues.clear()


message_queue = InMemoryMessageQueue()
