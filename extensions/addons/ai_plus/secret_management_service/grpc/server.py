# -*- coding: utf-8 -*-
"""gRPC server for Secret Management Service."""

import asyncio
import logging
from typing import Any, Callable, Dict, Optional

try:
    from ..config import Config
except ImportError:
    from config import Config
from loguru import logger


class SecretManagementRPCServer:
    """Simple in-memory RPC server for secret management service."""

    def __init__(self) -> None:
        """Initialize the RPC server."""
        self._handlers: Dict[str, Callable[..., Any]] = {}
        self._running = False

    def register(self, name: str, handler: Callable[..., Any]) -> None:
        """Register a handler.

        Args:
            name: Name of the RPC method
            handler: Handler function
        """
        self._handlers[name] = handler
        logger.debug(f"Registered RPC handler: {name}")

    def list_methods(self) -> list:
        """List registered methods.

        Returns:
            List of method names
        """
        return list(self._handlers.keys())

    async def call(self, method: str, payload: Optional[Dict[str, Any]] = None) -> Any:
        """Call a registered method.

        Args:
            method: Name of the method to call
            payload: Arguments to pass to the handler as a dict

        Returns:
            Result from the handler

        Raises:
            ValueError: If method is not found
        """
        if method not in self._handlers:
            raise ValueError(f"Unknown RPC method: {method}")

        handler = self._handlers[method]

        try:
            if asyncio.iscoroutinefunction(handler):
                return await handler(payload or {})
            return handler(payload or {})
        except Exception as e:
            logger.error(f"RPC method {method} failed: {e}", exc_info=True)
            raise

    async def start(self, host: str = "127.0.0.1", port: int = 50055) -> None:
        """Start the RPC server.

        Args:
            host: Host to bind to
            port: Port to bind to
        """
        self._running = True
        logger.info(f"RPC server started on {host}:{port}")

        # In a real implementation, this would start a gRPC server
        # For now, we just mark it as running
        # The actual gRPC server would use grpc.aio.server()

    async def stop(self) -> None:
        """Stop the RPC server."""
        self._running = False
        logger.info("RPC server stopped")

    def is_running(self) -> bool:
        """Check if the server is running.

        Returns:
            True if running, False otherwise
        """
        return self._running
