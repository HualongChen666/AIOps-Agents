# -*- coding: utf-8 -*-
"""
L4 Storage Layer - VictoriaMetrics Adapter
Provides metrics storage backend using VictoriaMetrics (Prometheus-compatible)
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, cast

import httpx
from loguru import logger

from core.base.storage import BaseStorage
from core.observability_query import (
    DEFAULT_MAX_PROMQL_SAMPLES,
    QueryCache,
    align_time_window,
    cached_query,
    limit_range_samples,
    make_cache_key,
    parse_duration_to_seconds,
    validate_promql,
    with_query_timeout,
)


class VictoriaMetricsStorage(BaseStorage):
    """
    VictoriaMetrics storage adapter for time-series metrics

    VictoriaMetrics is a high-performance metrics storage solution that is
    Prometheus-compatible and provides better compression and performance.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        config = config or {}
        super().__init__("victoriametrics", config)

        self.base_url = config.get("base_url", "http://localhost:8428")
        self.timeout = config.get("timeout", 30)
        self.max_samples = config.get("max_samples", DEFAULT_MAX_PROMQL_SAMPLES)
        self.read_only = config.get("read_only")
        self._client: Optional[httpx.AsyncClient] = None
        self._query_cache = QueryCache()
        if self.read_only is None:
            logger.warning(
                "VictoriaMetrics storage created without explicit read_only flag; "
                "set read_only=True in production to enforce read-only credentials."
            )

    def initialize(self) -> bool:
        """Initialize VictoriaMetrics client"""
        try:
            self._client = httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout)
            self._is_initialized = True
            logger.info(f"VictoriaMetrics storage initialized: {self.base_url}")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize VictoriaMetrics: {e}")
            return False

    def _build_metric_line(self, key: str, value: Any, metadata: Optional[Dict[str, Any]]) -> str:
        """Build Prometheus metric line format"""
        if metadata is None:
            metadata = {}
        timestamp = metadata.get("timestamp", int(datetime.now().timestamp()))
        labels = metadata.get("labels", {})
        label_str = ",".join([f'{k}="{v}"' for k, v in labels.items()])
        return f"{key}{{{label_str}}} {value} {timestamp}\n"

    async def _send_to_victoriametrics(self, metric_line: str) -> bool:
        """Send metric line to VictoriaMetrics API"""
        if self._client is None:
            return False
        response = await self._client.post(
            "/api/v1/import/prometheus",
            content=metric_line,
            headers={"Content-Type": "application/json"},
        )

        if response.status_code in [200, 204]:
            return True
        else:
            logger.error(f"VictoriaMetrics store failed: {response.status_code} - {response.text}")
            return False

    async def store(self, key: str, value: Any, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Store metrics in VictoriaMetrics using Prometheus remote_write protocol

        Args:
            key: Metric name
            value: Metric value
            metadata: Labels and timestamp metadata

        Returns:
            True if successful
        """
        if self.read_only is True:
            logger.warning("VictoriaMetrics write rejected: storage is configured as read_only")
            return False

        if not self._is_initialized or not self._client:
            logger.warning("VictoriaMetrics not initialized")
            return False

        try:
            metric_line = self._build_metric_line(key, value, metadata)
            return await self._send_to_victoriametrics(metric_line)

        except Exception as e:
            logger.error(f"Error storing to VictoriaMetrics: {e}")
            return False

    def _parse_metric_query(self, key: str) -> str:
        """Parse metric name and labels from key"""
        metric_name = key.split("{")[0] if "{" in key else key
        return key if "{" in key else metric_name

    def _build_query_params(self, query: str) -> Dict[str, Any]:
        """Build query parameters for VictoriaMetrics API"""
        return {"query": query, "time": int(datetime.now().timestamp())}

    async def _execute_query(self, params: Dict[str, Any]) -> Optional[float]:
        """Execute query and parse result"""
        if self._client is None:
            return None
        response = await self._client.get("/api/v1/query", params=params)

        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "success" and data.get("data", {}).get("result"):
                return float(data["data"]["result"][0]["value"][1])

        return None

    async def _safe_query_key(self, query: Dict[str, Any]) -> str:
        """Build a cache-safe query key that is stable within a time bucket."""
        base = dict(query)
        base.pop("time", None)
        return make_cache_key("vm", self.base_url, base)

    async def retrieve(self, key: str) -> Optional[Any]:
        """
        Retrieve latest metric value from VictoriaMetrics

        Args:
            key: Metric name with optional label selectors (e.g., metric_name{label="value"})

        Returns:
            Latest metric value or None
        """
        if not self._is_initialized or not self._client:
            logger.warning("VictoriaMetrics not initialized")
            return None

        try:
            query = self._parse_metric_query(key)
            validate_promql(query)
            params = self._build_query_params(query)
            cache_key = make_cache_key("vm_retrieve", self.base_url, key, params["time"] // 60)
            return await cached_query(
                self._query_cache,
                cache_key,
                with_query_timeout(self._execute_query(params)),
            )

        except Exception as e:
            logger.error(f"Error retrieving from VictoriaMetrics: {e}")
            return None

    async def delete(self, key: str) -> bool:
        """
        Delete metrics from VictoriaMetrics
        Note: VictoriaMetrics doesn't support direct deletion via API
        This is a no-op that logs a warning

        Returns:
            False (not supported)
        """
        logger.warning("VictoriaMetrics doesn't support direct deletion via API")
        return False

    def _is_range_query(self, query: Dict[str, Any]) -> bool:
        """Check if query is a range query"""
        return "start" in query and "end" in query

    def _build_range_query_params(self, promql_query: str, query: Dict[str, Any]) -> tuple:
        """Build parameters for range query and enforce max samples."""
        start = query.get("start")
        end = query.get("end")
        step = query.get("step", "60")

        if isinstance(start, datetime):
            start_dt = start
        elif start is not None:
            start_dt = datetime.fromtimestamp(int(start), tz=timezone.utc)
        else:
            start_dt = datetime.now(timezone.utc) - timedelta(minutes=5)

        if isinstance(end, datetime):
            end_dt = end
        elif end is not None:
            end_dt = datetime.fromtimestamp(int(end), tz=timezone.utc)
        else:
            end_dt = datetime.now(timezone.utc)

        step_seconds = limit_range_samples(
            start_dt,
            end_dt,
            parse_duration_to_seconds(step),
            self.max_samples,
        )

        params = {
            "query": promql_query,
            "start": int(start_dt.timestamp()),
            "end": int(end_dt.timestamp()),
            "step": step_seconds,
        }
        return params, "/api/v1/query_range"

    def _build_instant_query_params(self, promql_query: str, query: Dict[str, Any]) -> tuple:
        """Build parameters for instant query"""
        params = {"query": promql_query, "time": query.get("time", int(datetime.now().timestamp()))}
        return params, "/api/v1/query"

    async def _execute_promql_query(
        self, endpoint: str, params: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Execute PromQL query and parse response"""
        if self._client is None:
            return []
        response = await self._client.get(endpoint, params=params)

        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "success":
                return cast(List[Dict[str, Any]], data.get("data", {}).get("result", []))

        return []

    async def query(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Execute PromQL query against VictoriaMetrics

        Args:
            query: Dictionary with query parameters
                - query: PromQL query string
                - start: Start timestamp (optional)
                - end: End timestamp (optional)
                - step: Step interval (optional)

        Returns:
            List of query results
        """
        if not self._is_initialized or not self._client:
            logger.warning("VictoriaMetrics not initialized")
            return []

        promql_query = query.get("query", "")
        if not promql_query:
            return []

        try:
            validate_promql(promql_query)
        except ValueError as exc:
            logger.warning("Invalid PromQL query rejected: %s", exc)
            return []

        try:
            cache_key = await self._safe_query_key(query)

            if self._is_range_query(query):
                params, endpoint = self._build_range_query_params(promql_query, query)
            else:
                params, endpoint = self._build_instant_query_params(promql_query, query)

            return cast(List[Dict[str, Any]], await cached_query(
                self._query_cache,
                cache_key,
                with_query_timeout(self._execute_promql_query(endpoint, params)),
            ))

        except Exception as e:
            logger.error(f"Error querying VictoriaMetrics: {e}")
            return []

    async def query_range(
        self, query: str, start: datetime, end: datetime, step: int = 60
    ) -> List[Dict[str, Any]]:
        """
        Execute range query for time series data

        Args:
            query: PromQL query
            start: Start time
            end: End time
            step: Step interval in seconds

        Returns:
            List of time series results
        """
        try:
            validate_promql(query)
        except ValueError as exc:
            logger.warning("Invalid PromQL query rejected: %s", exc)
            return []

        start, end = align_time_window(end=end, duration_seconds=(end - start).total_seconds())
        step = int(limit_range_samples(start, end, step, self.max_samples))

        query_params = {
            "query": query,
            "start": int(start.timestamp()),
            "end": int(end.timestamp()),
            "step": step,
        }
        return await self.query(query_params)

    def close(self) -> None:
        """Close VictoriaMetrics client"""
        if self._client:
            import asyncio

            try:
                asyncio.create_task(self._client.aclose())
            except Exception as e:
                logger.error(f"Error closing VictoriaMetrics client: {e}")
        self._is_initialized = False
        logger.info("VictoriaMetrics storage closed")
        logger.info("VictoriaMetrics storage closed")
