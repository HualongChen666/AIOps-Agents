# -*- coding: utf-8 -*-
"""gRPC-like server for the LLM router microservice."""

from __future__ import annotations

from typing import Any, Callable, Dict

from loguru import logger


class LLMRouterRPCServer:
    """Lightweight in-memory RPC server for LLM router services."""

    def __init__(self) -> None:
        self._handlers: Dict[str, Callable[..., Any]] = {}

    def register(self, method: str, handler: Callable[..., Any]) -> None:
        self._handlers[method] = handler
        logger.info(f"Registered RPC method: {method}")

    def list_methods(self) -> list[str]:
        return list(self._handlers.keys())

    async def call(self, method: str, **kwargs: Any) -> Any:
        handler = self._handlers.get(method)
        if not handler:
            raise ValueError(f"Unknown RPC method: {method}")
        result = handler(**kwargs)
        if hasattr(result, "__await__"):
            return await result
        return result
