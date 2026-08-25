# -*- coding: utf-8 -*-
"""gRPC-like client for the RAG microservice."""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

import httpx


class RAGRPCClient:
    """HTTP-based RPC client for the RAG microservice."""

    def __init__(self, base_url: str = "http://localhost:9406") -> None:
        self.base_url = base_url

    async def call(self, method: str, payload: Optional[Dict[str, Any]] = None) -> Any:
        """Call an RPC method on the RAG service."""
        if payload is None:
            payload = {}
        # Use environment variable to control SSL verification (default: True for security)
        ssl_verify = os.environ.get("RAG_SERVICE_SSL_VERIFY", "true").lower() == "true"
        if not ssl_verify:
            import logging
            logging.warning("SSL verification is disabled in RAG service client - this is a security risk!")
        async with httpx.AsyncClient(verify=ssl_verify) as client:
            response = await client.post(f"{self.base_url}/rpc/{method}", json=payload)
            response.raise_for_status()
            return response.json()
