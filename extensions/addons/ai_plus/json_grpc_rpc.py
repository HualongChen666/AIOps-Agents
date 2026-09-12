# -*- coding: utf-8 -*-
"""Shared JSON-over-gRPC transport for the ai_plus microservices.

Several addon services expose a plain handler registry (method name -> callable)
and previously shipped a *simulated* client/server pair.  This module provides a
genuine gRPC transport for such registries using a JSON codec, so the registries
are reachable over real gRPC and the clients make real RPC round-trips.

It is import-name robust: the services live under packages literally named
``grpc`` which shadow the installed library when their directory is on
``sys.path``; :func:`_import_grpc_lib` temporarily strips such entries.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from typing import Any, Awaitable, Callable, Dict, Optional


def _import_grpc_lib():
    """Import the installed grpc library, avoiding sibling ``grpc`` shadowing."""

    def _is_shadow(p: str) -> bool:
        base = os.path.abspath(p or ".")
        gd = os.path.join(base, "grpc")
        return os.path.isfile(os.path.join(gd, "client.py")) and os.path.isfile(
            os.path.join(gd, "server.py")
        )

    saved = list(sys.path)
    sys.path = [p for p in sys.path if not _is_shadow(p)]
    try:
        import grpc as _grpc

        return _grpc
    finally:
        sys.path = saved


grpc = _import_grpc_lib()


def json_deserialize(payload: bytes) -> Dict[str, Any]:
    """Deserialize a byte payload into a JSON request dict."""
    if not payload:
        return {}
    return json.loads(payload.decode("utf-8"))


def json_serialize(message: Any) -> bytes:
    """Serialize a response object to JSON bytes."""
    return json.dumps(message, default=str).encode("utf-8")


def _make_behavior(handler: Callable[..., Any]) -> Callable[..., Awaitable[Any]]:
    """Wrap a registry handler (sync or async, single payload arg) as a gRPC behavior."""

    if asyncio.iscoroutinefunction(handler):

        async def _async_behavior(request: Dict[str, Any], context: Any) -> Any:
            return await handler(request or {})

        return _async_behavior

    async def _sync_behavior(request: Dict[str, Any], context: Any) -> Any:
        return handler(request or {})

    return _sync_behavior


class JsonRpcServer:
    """A real gRPC server exposing a method-name -> handler registry via JSON."""

    def __init__(self, service_fqn: str) -> None:
        self.service_fqn = service_fqn
        self._handlers: Dict[str, Callable[..., Any]] = {}
        self._server: Optional[Any] = None

    def register(self, name: str, handler: Callable[..., Any]) -> None:
        """Register an RPC handler under ``name``."""
        self._handlers[name] = handler

    def list_methods(self) -> list:
        """Return the registered method names."""
        return list(self._handlers.keys())

    async def call(self, method: str, payload: Optional[Dict[str, Any]] = None) -> Any:
        """Dispatch a method locally (used by the HTTP ``/rpc`` endpoint)."""
        if method not in self._handlers:
            raise ValueError(f"Unknown RPC method: {method}")
        handler = self._handlers[method]
        request = payload or {}
        if asyncio.iscoroutinefunction(handler):
            return await handler(request)
        return handler(request)

    def build_generic_handler(self) -> Any:
        """Build the gRPC generic handler from the registered methods."""
        method_handlers = {
            name: grpc.unary_unary_rpc_method_handler(
                _make_behavior(handler),
                request_deserializer=json_deserialize,
                response_serializer=json_serialize,
            )
            for name, handler in self._handlers.items()
        }
        return grpc.method_handlers_generic_handler(self.service_fqn, method_handlers)

    async def start(self, host: str, port: int) -> None:
        """Bind and start a real gRPC server on ``host:port``."""
        self._server = grpc.aio.server()
        self._server.add_generic_rpc_handlers((self.build_generic_handler(),))
        bound = self._server.add_insecure_port(f"{host}:{port}")
        if bound == 0:
            raise RuntimeError(f"Failed to bind gRPC server to {host}:{port}")
        await self._server.start()

    async def stop(self) -> None:
        """Stop the gRPC server if running."""
        if self._server is not None:
            await self._server.stop(0)
            self._server = None

    async def wait_for_termination(self) -> None:
        """Block until the (running) gRPC server terminates."""
        if self._server is not None:
            await self._server.wait_for_termination()

    def is_running(self) -> bool:
        """Return whether the gRPC server is currently bound."""
        return self._server is not None


class JsonRpcClient:
    """A real gRPC client for a :class:`JsonRpcServer` (JSON codec)."""

    def __init__(self, service_fqn: str, host: str, port: int) -> None:
        self.service_fqn = service_fqn
        self.host = host
        self.port = port
        self._channel: Optional[Any] = None

    async def connect(self, timeout: float = 5.0) -> None:
        """Open the channel and wait until it is ready."""
        self._channel = grpc.aio.insecure_channel(f"{self.host}:{self.port}")
        try:
            await asyncio.wait_for(self._channel.channel_ready(), timeout=timeout)
        except asyncio.TimeoutError as exc:
            raise ConnectionError(
                f"Cannot reach {self.service_fqn} at {self.host}:{self.port}"
            ) from exc

    async def disconnect(self) -> None:
        """Close the channel."""
        if self._channel is not None:
            await self._channel.close()
            self._channel = None

    async def call(self, method: str, payload: Optional[Dict[str, Any]] = None) -> Any:
        """Invoke ``method`` on the remote server and return the result."""
        if self._channel is None:
            raise ConnectionError("Not connected to RPC server")
        stub = self._channel.unary_unary(
            f"/{self.service_fqn}/{method}",
            request_serializer=json_serialize,
            response_deserializer=json_deserialize,
        )
        return await stub(payload or {})
