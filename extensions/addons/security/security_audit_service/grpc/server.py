# -*- coding: utf-8 -*-
"""gRPC-like in-memory server for the Security Audit microservice."""

from __future__ import annotations

from typing import Any, Awaitable, Callable, Dict

from loguru import logger


class SecurityAuditServiceRPCServer:
    """Lightweight in-memory RPC server."""

    def __init__(self) -> None:
        self._handlers: Dict[str, Callable[..., Awaitable[Any]]] = {}

    def register(self, method: str, handler: Callable[..., Awaitable[Any]]) -> None:
        """Register an RPC handler."""
        self._handlers[method] = handler
        logger.info(f"Registered RPC method: {method}")

    def list_methods(self) -> list[str]:
        """List registered methods."""
        return list(self._handlers.keys())

    async def call(self, method: str, **kwargs: Any) -> Any:
        """Call a registered handler."""
        handler = self._handlers.get(method)
        if not handler:
            raise ValueError(f"Unknown RPC method: {method}")
        result = handler(**kwargs)
        if hasattr(result, "__await__"):
            return await result
        return result
