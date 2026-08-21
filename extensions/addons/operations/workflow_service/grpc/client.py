# -*- coding: utf-8 -*-
"""gRPC-like client for workflow microservice."""

from __future__ import annotations

from typing import Any, Optional

import httpx

from extensions.addons.operations.workflow_service.grpc.server import WorkflowRPCServer


class WorkflowRPCClient:
    """Lightweight RPC client with in-memory or HTTP transport."""

    def __init__(
        self,
        server: Optional[WorkflowRPCServer] = None,
        base_url: Optional[str] = None,
    ) -> None:
        self.server = server
        self.base_url = base_url
        self._http: Optional[httpx.AsyncClient] = None
        if base_url and base_url.strip():
            self._http = httpx.AsyncClient(base_url=base_url, timeout=30.0)

    async def call(self, method: str, **kwargs: Any) -> Any:
        if self.server:
            return await self.server.call(method, **kwargs)
        if self._http:
            response = await self._http.post(f"/rpc/{method}", json=kwargs)
            response.raise_for_status()
            return response.json()
        raise RuntimeError("RPCClient requires a server instance or base_url")

    async def close(self) -> None:
        if self._http:
            await self._http.aclose()
            self._http = None
