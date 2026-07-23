# -*- coding: utf-8 -*-
"""
L4 Storage Layer - Tempo Adapter
Provides distributed tracing storage backend using Grafana Tempo
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, cast

import httpx
from loguru import logger

from core.base.storage import BaseStorage


class TempoStorage(BaseStorage):
    """
    Tempo storage adapter for distributed tracing

    Tempo is a highly-scalable distributed tracing backend that is
    compatible with OpenTelemetry and Jaeger.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        config = config or {}
        super().__init__("tempo", config)

        self.base_url = config.get("base_url", "http://localhost:3200")
        self.timeout = config.get("timeout", 30)
        self._client: Optional[httpx.AsyncClient] = None

    def initialize(self) -> bool:
        """Initialize Tempo client"""
        try:
            self._client = httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout)
            self._is_initialized = True
            logger.info(f"Tempo storage initialized: {self.base_url}")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Tempo: {e}")
            return False

    async def store(self, key: str, value: Any, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Store trace span in Tempo
        Note: Tempo typically receives traces via OpenTelemetry OTLP protocol
        This method is for manual trace ingestion if needed

        Args:
            key: Trace ID
            value: Span data
            metadata: Additional trace metadata

        Returns:
            True if successful
        """
        if not self._is_initialized or not self._client:
            logger.warning("Tempo not initialized")
            return False

        try:
            # Tempo typically uses OTLP for trace ingestion
            # This is a fallback for manual ingestion
            logger.warning("Tempo traces should be sent via OpenTelemetry OTLP")
            return False

        except Exception as e:
            logger.error(f"Error storing to Tempo: {e}")
            return False

    async def retrieve(self, key: str) -> Optional[Any]:
        """
        Retrieve trace by trace ID from Tempo

        Args:
            key: Trace ID (hex string)

        Returns:
            Trace data or None
        """
        if not self._is_initialized or not self._client:
            logger.warning("Tempo not initialized")
            return None

        try:
            response = await self._client.get(f"/api/traces/{key}")

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                logger.debug(f"Trace not found: {key}")
                return None
            else:
                logger.error(f"Tempo retrieve failed: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Error retrieving from Tempo: {e}")
            return None

    async def delete(self, key: str) -> bool:
        """
        Delete trace from Tempo
        Note: Tempo doesn't support direct deletion via API
        This is a no-op that logs a warning

        Returns:
            False (not supported)
        """
        logger.warning("Tempo doesn't support direct deletion via API")
        return False

    def _build_tempo_query_params(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Build query parameters for Tempo API"""
        tempo_query = query.get("query", "")
        if not tempo_query:
            return {}

        params = {"query": tempo_query, "limit": query.get("limit", 20)}

        if "start" in query:
            params["start"] = query["start"]
        if "end" in query:
            params["end"] = query["end"]

        return params

    async def _execute_tempo_query(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute Tempo query and parse response"""
        if not self._client:
            logger.warning("Tempo client not initialized")
            return []

        if self._client is None:
            return []
        response = await self._client.get("/api/search", params=params)

        if response.status_code == 200:
            data = response.json()
            traces = cast(List[Dict[str, Any]], data.get("traces", []))
            return traces if isinstance(traces, list) else []

        return []

    async def query(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Execute TempoQL query against Tempo

        Args:
            query: Dictionary with query parameters
                - query: TempoQL query string
                - start: Start timestamp (optional)
                - end: End timestamp (optional)
                - limit: Result limit (optional)

        Returns:
            List of matching traces
        """
        if not self._is_initialized or not self._client:
            logger.warning("Tempo not initialized")
            return []

        try:
            params = self._build_tempo_query_params(query)
            if not params:
                return []

            return await self._execute_tempo_query(params)

        except Exception as e:
            logger.error(f"Error querying Tempo: {e}")
            return []

    def _build_search_query(
        self,
        service_name: Optional[str] = None,
        operation: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
        min_duration: Optional[float] = None,
        max_duration: Optional[float] = None,
    ) -> str:
        """Build TempoQL search query from filters"""
        query_parts = []

        if service_name:
            query_parts.append(f'service.name="{service_name}"')
        if operation:
            query_parts.append(f'name="{operation}"')
        if tags:
            for k, v in tags.items():
                query_parts.append(f'{k}="{v}"')
        if min_duration:
            query_parts.append(f"duration>={min_duration}s")
        if max_duration:
            query_parts.append(f"duration<={max_duration}s")

        return "{" + " AND ".join(query_parts) + "}" if query_parts else "{}"

    def _build_search_params(
        self,
        query: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        limit: int = 20,
    ) -> Dict[str, Any]:
        """Build query parameters for search"""
        query_params = {"query": query, "limit": limit}

        if start:
            query_params["start"] = int(start.timestamp() * 1e9)
        if end:
            query_params["end"] = int(end.timestamp() * 1e9)

        return query_params

    async def search_traces(
        self,
        service_name: Optional[str] = None,
        operation: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
        min_duration: Optional[float] = None,
        max_duration: Optional[float] = None,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Search traces with filters

        Args:
            service_name: Filter by service name
            operation: Filter by operation name
            tags: Filter by tag key-value pairs
            min_duration: Minimum duration in seconds
            max_duration: Maximum duration in seconds
            start: Start time
            end: End time
            limit: Maximum number of results

        Returns:
            List of matching traces
        """
        query = self._build_search_query(service_name, operation, tags, min_duration, max_duration)
        query_params = self._build_search_params(query, start, end, limit)

        return await self.query(query_params)

    async def get_services(self) -> List[str]:
        """
        Get list of services from Tempo

        Returns:
            List of service names
        """
        if not self._is_initialized or not self._client:
            logger.warning("Tempo not initialized")
            return []

        try:
            response = await self._client.get("/api/services")

            if response.status_code == 200:
                data = response.json()
                services = cast(List[str], data.get("data", []))
                return services if isinstance(services, list) else []

            return []

        except Exception as e:
            logger.error(f"Error getting services from Tempo: {e}")
            return []

    async def get_operations(self, service_name: str) -> List[str]:
        """
        Get list of operations for a service from Tempo

        Args:
            service_name: Service name

        Returns:
            List of operation names
        """
        if not self._is_initialized or not self._client:
            logger.warning("Tempo not initialized")
            return []

        try:
            response = await self._client.get(f"/api/services/{service_name}/operations")

            if response.status_code == 200:
                data = response.json()
                operations = cast(List[str], data.get("data", []))
                return operations if isinstance(operations, list) else []

            return []

        except Exception as e:
            logger.error(f"Error getting operations from Tempo: {e}")
            return []

    def close(self) -> None:
        """Close Tempo client"""
        if self._client:
            import asyncio

            try:
                asyncio.create_task(self._client.aclose())
            except Exception as e:
                logger.error(f"Error closing Tempo client: {e}")
        self._is_initialized = False
        logger.info("Tempo storage closed")
