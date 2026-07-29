# -*- coding: utf-8 -*-
"""gRPC-like server for user microservice (task 29.9)."""

from __future__ import annotations

from typing import Any, Awaitable, Callable, Dict

from loguru import logger


class UserRPCServer:
    """Lightweight in-memory RPC server for user services."""

    def __init__(self) -> None:
        self._handlers: Dict[str, Callable[..., Awaitable[Any]]] = {}

    def register(
        self,
        method: str,
        handler: Callable[..., Awaitable[Any]],
    ) -> None:
        self._handlers[method] = handler
        logger.info(f"Registered RPC method: {method}")

    async def call(self, method: str, **kwargs: Any) -> Any:
        handler = self._handlers.get(method)
        if not handler:
            raise ValueError(f"Unknown RPC method: {method}")
        result = handler(**kwargs)
        if hasattr(result, "__await__"):
            return await result
        return result

    def list_methods(self) -> list[str]:
        return list(self._handlers.keys())
