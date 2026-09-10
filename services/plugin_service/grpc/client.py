# -*- coding: utf-8 -*-
"""gRPC-like client for the plugin microservice.

Talks to a :class:`services.plugin_service.grpc.server.PluginRPCServer`
instance in-process, or over HTTP when a remote base URL is configured.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import httpx

from services.plugin_service.grpc.server import PluginRPCServer


class PluginRPCClient:
    """Client for plugin RPC methods."""

    def __init__(
        self,
        server: Optional[PluginRPCServer] = None,
        base_url: Optional[str] = None,
        timeout: float = 10.0,
    ) -> None:
        if server is None and not base_url:
            raise ValueError("Either 'server' or 'base_url' must be provided")
        self._server = server
        self._base_url = base_url.rstrip("/") if base_url else None
        self._timeout = timeout

    async def call(self, method: str, **kwargs: Any) -> Dict[str, Any]:
        """Invoke ``method`` on the in-process server or the remote endpoint."""
        if self._server is not None:
            result = await self._server.call(method, **kwargs)
            return {"method": method, "result": result}
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(f"{self._base_url}/rpc/{method}", json=kwargs)
            response.raise_for_status()
            return response.json()
