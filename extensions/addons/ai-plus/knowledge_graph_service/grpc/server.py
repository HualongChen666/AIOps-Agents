# -*- coding: utf-8 -*-
"""In-memory RPC server for inter-service communication."""

from __future__ import annotations

import asyncio
from typing import Any, Callable, Dict


class KnowledgeGraphRPCServer:
    """Simple in-memory RPC server."""

    def __init__(self) -> None:
        self._handlers: Dict[str, Callable[..., Any]] = {}

    def register(self, name: str, handler: Callable[..., Any]) -> None:
        """Register a handler."""
        self._handlers[name] = handler

    def list_methods(self) -> list:
        """List registered methods."""
        return list(self._handlers.keys())

    async def call(self, method: str, **kwargs: Any) -> Any:
        """Call a registered method."""
        if method not in self._handlers:
            raise ValueError(f"Unknown method: {method}")
        handler = self._handlers[method]
        if asyncio.iscoroutinefunction(handler):
            return await handler(**kwargs)
        return handler(**kwargs)
