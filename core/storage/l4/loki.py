# -*- coding: utf-8 -*-
"""
L4 Storage Layer - Loki Adapter
Provides log storage backend using Grafana Loki
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
from loguru import logger

from core.base.storage import BaseStorage


class LokiStorage(BaseStorage):
    """
    Loki storage adapter for log aggregation

    Loki is a horizontally-scalable, highly-available log aggregation system
    inspired by Prometheus.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        config = config or {}
        super().__init__("loki", config)

        self.base_url = config.get("base_url", "http://localhost:3100")
        self.timeout = config.get("timeout", 30)
        self._client: Optional[httpx.AsyncClient] = None

    def initialize(self) -> bool:
        """Initialize Loki client"""
        try:
            self._client = httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout)
            self._is_initialized = True
            logger.info(f"Loki storage initialized: {self.base_url}")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Loki: {e}")
            return False

    def _build_loki_stream(
        self, key: str, value: Any, metadata: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Build Loki stream structure from key, value, and metadata"""
        if metadata is None:
            metadata = {}
        timestamp = metadata.get("timestamp", int(datetime.now().timestamp() * 1e9))  # nanoseconds
        labels = metadata.get("labels", {})

        # Add key as a label
        if key:
            labels["stream"] = key

        return {"stream": labels, "values": [[str(timestamp), str(value)]]}

    async def _send_to_loki(self, payload: Dict[str, Any]) -> bool:
        """Send payload to Loki API"""
        if self._client is None:
            logger.warning("Loki client not initialized")
            return False
        response = await self._client.post(
            "/loki/api/v1/push", json=payload, headers={"Content-Type": "application/json"}
        )

        if response.status_code in [200, 204]:
            return True
        else:
            logger.error(f"Loki store failed: {response.status_code} - {response.text}")
            return False

    async def store(self, key: str, value: Any, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Store log entry in Loki

        Args:
            key: Stream identifier (used as part of labels)
            value: Log message
            metadata: Labels and timestamp metadata

        Returns:
            True if successful
        """
        if not self._is_initialized or not self._client:
            logger.warning("Loki not initialized")
            return False

        try:
            # Build Loki stream structure
            stream = self._build_loki_stream(key, value, metadata)

            payload = {"streams": [stream]}

            return await self._send_to_loki(payload)

        except Exception as e:
            logger.error(f"Error storing to Loki: {e}")
            return False

    async def retrieve(self, key: str) -> Optional[Any]:
        """
        Retrieve log entries from Loki by stream label

        Args:
            key: Stream label value

        Returns:
            List of log entries or None
        """
        if not self._is_initialized or not self._client:
            logger.warning("Loki not initialized")
            return None

        try:
            query = f'{{stream="{key}"}}'
            params: Dict[str, str | int] = {
                "query": query,
                "limit": 100,
                "time": int(datetime.now().timestamp() * 1e9),
            }

            response = await self._client.get("/loki/api/v1/query", params=params)

            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success":
                    return data.get("data", {}).get("result", [])

            return None

        except Exception as e:
            logger.error(f"Error retrieving from Loki: {e}")
            return None

    async def delete(self, key: str) -> bool:
        """
        Delete log entries from Loki by stream label
        Note: Loki doesn't support direct deletion via API
        This is a no-op that logs a warning

        Returns:
            False (not supported)
        """
        logger.warning("Loki doesn't support direct deletion via API")
        return False

    def _build_query_params(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Build query parameters for Loki API"""
        logql_query = query.get("query", "")
        if not logql_query:
            return {}

        params = {"query": logql_query, "limit": query.get("limit", 100)}

        if "start" in query:
            params["start"] = query["start"]
        if "end" in query:
            params["end"] = query["end"]

        return params

    async def _execute_loki_query(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute Loki query and parse response"""
        if self._client is None:
            logger.warning("Loki client not initialized")
            return []
        response = await self._client.get("/loki/api/v1/query", params=params)

        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "success":
                result = data.get("data", {}).get("result", [])
                return result if isinstance(result, list) else []

        return []

    async def query(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Execute LogQL query against Loki

        Args:
            query: Dictionary with query parameters
                - query: LogQL query string
                - start: Start timestamp (nanoseconds, optional)
                - end: End timestamp (nanoseconds, optional)
                - limit: Result limit (optional)

        Returns:
            List of query results
        """
        if not self._is_initialized or not self._client:
            logger.warning("Loki not initialized")
            return []

        try:
            params = self._build_query_params(query)
            if not params:
                return []

            return await self._execute_loki_query(params)

        except Exception as e:
            logger.error(f"Error querying Loki: {e}")
            return []

    async def query_range(
        self, query: str, start: datetime, end: datetime, limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        Execute range query for log data

        Args:
            query: LogQL query
            start: Start time
            end: End time
            limit: Maximum number of results

        Returns:
            List of log entries
        """
        query_params = {
            "query": query,
            "start": int(start.timestamp() * 1e9),
            "end": int(end.timestamp() * 1e9),
            "limit": limit,
        }
        return await self.query(query_params)

    def _build_labels_params(self, stream: Optional[str] = None) -> Dict[str, Any]:
        """Build parameters for labels API call"""
        params = {}
        if stream:
            params["stream"] = stream
        return params

    async def _fetch_labels(self, params: Dict[str, Any]) -> List[str]:
        """Fetch labels from Loki API"""
        if self._client is None:
            logger.warning("Loki client not initialized")
            return []
        response = await self._client.get("/loki/api/v1/labels", params=params)

        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "success":
                result = data.get("data", [])
                return result if isinstance(result, list) else []

        return []

    async def get_labels(self, stream: Optional[str] = None) -> List[str]:
        """
        Get available labels from Loki

        Args:
            stream: Optional stream filter

        Returns:
            List of label names
        """
        if not self._is_initialized or not self._client:
            logger.warning("Loki not initialized")
            return []

        try:
            params = self._build_labels_params(stream)
            return await self._fetch_labels(params)

        except Exception as e:
            logger.error(f"Error getting labels from Loki: {e}")
            return []

    def close(self) -> None:
        """Close Loki client"""
        if self._client:
            import asyncio

            try:
                asyncio.create_task(self._client.aclose())
            except Exception as e:
                logger.error(f"Error closing Loki client: {e}")
        self._is_initialized = False
        logger.info("Loki storage closed")
