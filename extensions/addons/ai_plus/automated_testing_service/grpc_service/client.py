# -*- coding: utf-8 -*-
"""gRPC client for Automated Testing Service."""

import logging
from typing import Any, Dict, Optional

import httpx

from ..config import Config

logger = logging.getLogger(Config.SERVICE_NAME)


class AutomatedTestingRPCClient:
    """HTTP client for automated testing service RPC."""

    def __init__(self, base_url: Optional[str] = None) -> None:
        """Initialize the RPC client.

        Args:
            base_url: Base URL of the service. If None, uses default.
        """
        self.base_url = base_url or f"http://{Config.HOST}:{Config.PORT}"
        self.timeout = 30.0

    async def call(
        self, method: str, payload: Optional[Dict[str, Any]] = None
    ) -> Any:
        """Call an RPC method via HTTP.

        Args:
            method: Name of the RPC method
            payload: Optional payload to send

        Returns:
            Response data

        Raises:
            httpx.HTTPError: If the request fails
        """
        url = f"{self.base_url}/rpc/{method}"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload or {})
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            logger.error(f"RPC call to {method} failed: {e}")
            raise

    async def health_check(self) -> Dict[str, Any]:
        """Perform a health check on the service.

        Returns:
            Health check response
        """
        url = f"{self.base_url}/health"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.json()

    async def invoke(self, action: str, payload: Optional[Dict[str, Any]] = None) -> Any:
        """Invoke an action on the service.

        Args:
            action: Action to invoke
            payload: Optional payload

        Returns:
            Response data
        """
        url = f"{self.base_url}/invoke"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, json={"action": action, "payload": payload or {}})
            response.raise_for_status()
            return response.json()
