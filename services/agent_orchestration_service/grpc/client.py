# -*- coding: utf-8 -*-
"""gRPC-like client for the Agent Orchestration microservice."""

from __future__ import annotations

from typing import Any, Dict, Optional

import httpx


class AgentRPCClient:
    """HTTP-based RPC client for the agent orchestration service."""

    def __init__(self, base_url: str = "http://localhost:9407") -> None:
        self.base_url = base_url

    async def call(self, method: str, payload: Optional[Dict[str, Any]] = None) -> Any:
        """Call an RPC method on the agent orchestration service."""
        if payload is None:
            payload = {}
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{self.base_url}/rpc/{method}", json=payload)
            response.raise_for_status()
            return response.json()
