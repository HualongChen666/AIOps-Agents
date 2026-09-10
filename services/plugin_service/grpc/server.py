# -*- coding: utf-8 -*-
"""gRPC-like in-process RPC server for the plugin microservice.

Mirrors ``services/audit_service/grpc/server.py``: handlers are registered by
name and dispatched through :meth:`call`, which supports both coroutine and
plain callables.
"""

from __future__ import annotations

from typing import Any, Awaitable, Callable, Dict

from loguru import logger


class PluginRPCServer:
    """Lightweight in-memory RPC server for plugin operations."""

    def __init__(self) -> None:
        self._handlers: Dict[str, Callable[..., Awaitable[Any]]] = {}

    def register(
        self,
        method: str,
        handler: Callable[..., Awaitable[Any]],
    ) -> None:
        """Register ``handler`` under ``method``."""
        self._handlers[method] = handler
        logger.info(f"Registered RPC method: {method}")

    async def call(self, method: str, **kwargs: Any) -> Any:
        """Invoke a registered method, awaiting the result when needed."""
        handler = self._handlers.get(method)
        if not handler:
            raise ValueError(f"Unknown RPC method: {method}")
        result = handler(**kwargs)
        if hasattr(result, "__await__"):
            return await result
        return result

    def list_methods(self) -> list[str]:
        """Return the registered method names."""
        return list(self._handlers.keys())
