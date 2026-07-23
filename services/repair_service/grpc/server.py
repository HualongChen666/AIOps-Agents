# -*- coding: utf-8 -*-
"""gRPC-like server for repair microservice."""

from __future__ import annotations

from typing import Any, Awaitable, Callable, Dict

from loguru import logger


class RPCServer:
    """Lightweight in-memory RPC server; can be backed by grpcio if available."""

    def __init__(self) -> None:
        self._handlers: Dict[str, Callable[..., Awaitable[Any]]] = {}

    def register(
        self,
        method: str,
        handler: Callable[..., Awaitable[Any]],
    ) -> None:
        self._handlers[method] = handler
        logger.info(f"Registered gRPC method: {method}")

    async def call(self, method: str, **kwargs: Any) -> Any:
        handler = self._handlers.get(method)
        if not handler:
            raise ValueError(f"Unknown RPC method: {method}")
        return await handler(**kwargs)

    def list_methods(self) -> list[str]:
        return list(self._handlers.keys())
