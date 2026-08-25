# -*- coding: utf-8 -*-
"""HTTP RPC client for inter-service communication."""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

import httpx


class KnowledgeGraphRPCClient:
    """Simple HTTP client for knowledge graph service RPC."""

    def __init__(self, base_url: str = "http://localhost:9409") -> None:
        self.base_url = base_url

    async def call(self, method: str, payload: Optional[Dict[str, Any]] = None) -> Any:
        """Call an RPC method via HTTP."""
        # Use environment variable to control SSL verification (default: True for security)
        ssl_verify = os.environ.get("KNOWLEDGE_GRAPH_SERVICE_SSL_VERIFY", "true").lower() == "true"
        if not ssl_verify:
            import logging
            logging.warning("SSL verification is disabled in knowledge_graph_service client - this is a security risk!")
        async with httpx.AsyncClient(verify=ssl_verify) as client:
            response = await client.post(f"{self.base_url}/rpc/{method}", json=payload or {})
            response.raise_for_status()
            return response.json()
