# -*- coding: utf-8 -*-
"""
API Response Time Optimization
Enterprise-grade API response time optimization with caching and async processing
"""

import asyncio
import hashlib
import json
import statistics
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, List, Optional, cast

from loguru import logger


class OptimizationLevel(Enum):
    """Optimization level"""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class CacheStrategy(Enum):
    """Cache strategy"""

    MEMORY = "memory"
    REDIS = "redis"
    MEMCACHED = "memcached"
    HYBRID = "hybrid"


@dataclass
class APIResponse:
    """API response data"""

    endpoint: str
    method: str
    response_time_ms: float
    status_code: int
    response_size_bytes: int
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ResponseTimeMetrics:
    """Response time metrics"""

    endpoint: str
    method: str
    total_requests: int = 0
    avg_response_time_ms: float = 0.0
    min_response_time_ms: float = float("inf")
    max_response_time_ms: float = 0.0
    p50_response_time_ms: float = 0.0
    p95_response_time_ms: float = 0.0
    p99_response_time_ms: float = 0.0
    error_count: int = 0
    error_rate: float = 0.0
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class OptimizationRecommendation:
    """Optimization recommendation"""

    recommendation_id: str
    endpoint: str
    method: str
    optimization_type: str
    level: OptimizationLevel
    current_performance: Dict[str, float]
    expected_improvement: float
    implementation_effort: str
    description: str
    steps: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class APIResponseTimeOptimizer:
    """Enterprise-grade API response time optimizer"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize API response time optimizer

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}

        # Response history
        self.response_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=10000))

        # Response metrics
        self.response_metrics: Dict[str, ResponseTimeMetrics] = {}

        # API cache
        self.api_cache: Dict[str, Dict[str, Any]] = {}

        # Async task queue
        self.async_task_queue: asyncio.Queue = asyncio.Queue()

        # Optimization recommendations
        self.recommendations: List[OptimizationRecommendation] = []

        # Configuration
        self.slow_response_threshold_ms = self.config.get("slow_response_threshold_ms", 1000)
        self.cache_ttl_seconds = self.config.get("cache_ttl_seconds", 300)
        self.max_cache_size = self.config.get("max_cache_size", 1000)

        # Statistics
        self.total_requests_tracked = 0
        self.total_cache_hits = 0
        self.total_cache_misses = 0

        logger.info("API response time optimizer initialized")

    def track_response(
        self,
        endpoint: str,
        method: str,
        response_time_ms: float,
        status_code: int,
        response_size_bytes: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Track API response

        Args:
            endpoint: API endpoint
            method: HTTP method
            response_time_ms: Response time in milliseconds
            status_code: HTTP status code
            response_size_bytes: Response size in bytes
            metadata: Additional metadata
        """
        key = f"{method}:{endpoint}"

        response = APIResponse(
            endpoint=endpoint,
            method=method,
            response_time_ms=response_time_ms,
            status_code=status_code,
            response_size_bytes=response_size_bytes,
            metadata=metadata or {},
        )

        self.response_history[key].append(response)
        self.total_requests_tracked += 1

        # Update metrics
        self._update_metrics(key)

        logger.debug(f"Tracked response: {key}, time: {response_time_ms}ms")

    def _update_metrics(self, key: str) -> None:
        """
        Update response metrics

        Args:
            key: Endpoint key (method:endpoint)
        """
        history = self.response_history[key]

        if key not in self.response_metrics:
            method, endpoint = key.split(":", 1)
            self.response_metrics[key] = ResponseTimeMetrics(endpoint=endpoint, method=method)

        metrics = self.response_metrics[key]
        metrics.total_requests = len(history)

        response_times = [r.response_time_ms for r in history]
        metrics.avg_response_time_ms = statistics.mean(response_times)
        metrics.min_response_time_ms = min(response_times)
        metrics.max_response_time_ms = max(response_times)

        # Calculate percentiles
        sorted_times = sorted(response_times)
        metrics.p50_response_time_ms = statistics.median(sorted_times)
        if len(sorted_times) >= 20:
            metrics.p95_response_time_ms = statistics.quantiles(sorted_times, n=20)[18]
        if len(sorted_times) >= 100:
            metrics.p99_response_time_ms = statistics.quantiles(sorted_times, n=100)[98]

        # Calculate error rate
        error_count = sum(1 for r in history if r.status_code >= 400)
        metrics.error_count = error_count
        metrics.error_rate = error_count / len(history) if history else 0

        metrics.last_updated = datetime.now(timezone.utc)

    def analyze_slow_endpoints(self) -> List[Dict[str, Any]]:
        """
        Analyze slow endpoints

        Returns:
            List of slow endpoints sorted by impact
        """
        slow_endpoints = []

        for key, metrics in self.response_metrics.items():
            if metrics.p95_response_time_ms > self.slow_response_threshold_ms:
                method, endpoint = key.split(":", 1)
                slow_endpoints.append(
                    {
                        "endpoint": endpoint,
                        "method": method,
                        "avg_response_time_ms": metrics.avg_response_time_ms,
                        "p95_response_time_ms": metrics.p95_response_time_ms,
                        "p99_response_time_ms": metrics.p99_response_time_ms,
                        "total_requests": metrics.total_requests,
                        "error_rate": metrics.error_rate,
                        "impact_score": metrics.p95_response_time_ms * metrics.total_requests,
                    }
                )

        # Sort by impact score
        slow_endpoints.sort(key=lambda x: cast(float, x["impact_score"]), reverse=True)

        logger.info(f"Analyzed {len(slow_endpoints)} slow endpoints")

        return slow_endpoints

    def generate_optimizations(self) -> List[OptimizationRecommendation]:
        """
        Generate optimization recommendations

        Returns:
            List of optimization recommendations
        """
        self.recommendations = []

        slow_endpoints = self.analyze_slow_endpoints()

        for endpoint_data in slow_endpoints:
            endpoint = endpoint_data["endpoint"]
            method = endpoint_data["method"]
            key = f"{method}:{endpoint}"

            # Determine optimization type
            if endpoint_data["p95_response_time_ms"] > 5000:
                optimization_type = "async_processing"
                level = OptimizationLevel.CRITICAL
                expected_improvement = 70.0
            elif endpoint_data["p95_response_time_ms"] > 2000:
                optimization_type = "response_caching"
                level = OptimizationLevel.HIGH
                expected_improvement = 50.0
            elif endpoint_data["p95_response_time_ms"] > 1000:
                optimization_type = "query_optimization"
                level = OptimizationLevel.MEDIUM
                expected_improvement = 30.0
            else:
                optimization_type = "general_optimization"
                level = OptimizationLevel.LOW
                expected_improvement = 15.0

            recommendation = OptimizationRecommendation(
                recommendation_id=(
                    f"opt_{key.replace('/', '_')}_"
                    f"{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
                ),
                endpoint=endpoint,
                method=method,
                optimization_type=optimization_type,
                level=level,
                current_performance={
                    "avg_response_time_ms": endpoint_data["avg_response_time_ms"],
                    "p95_response_time_ms": endpoint_data["p95_response_time_ms"],
                    "error_rate": endpoint_data["error_rate"],
                },
                expected_improvement=expected_improvement,
                implementation_effort="medium",
                description=f"Optimize {method} {endpoint} for better response time",
                steps=self._generate_optimization_steps(optimization_type, endpoint, method),
            )

            self.recommendations.append(recommendation)

        logger.info(f"Generated {len(self.recommendations)} optimization recommendations")

        return self.recommendations

    def _generate_optimization_steps(
        self, optimization_type: str, endpoint: str, method: str
    ) -> List[str]:
        """
        Generate optimization steps

        Args:
            optimization_type: Optimization type
            endpoint: API endpoint
            method: HTTP method

        Returns:
            List of optimization steps
        """
        steps = []

        if optimization_type == "async_processing":
            steps = [
                "Convert endpoint to async processing",
                "Implement task queue for long-running operations",
                "Add WebSocket or SSE for progress updates",
                "Implement result caching",
            ]
        elif optimization_type == "response_caching":
            steps = [
                "Implement response caching",
                "Configure cache TTL based on data freshness",
                "Add cache invalidation strategy",
                "Monitor cache hit rate",
            ]
        elif optimization_type == "query_optimization":
            steps = [
                "Analyze database queries",
                "Add appropriate indexes",
                "Optimize query structure",
                "Implement query result caching",
            ]
        else:
            steps = [
                "Profile endpoint performance",
                "Identify bottlenecks",
                "Optimize critical path",
                "Implement monitoring",
            ]

        return steps

    def enable_response_caching(
        self, endpoint: str, method: str, ttl_seconds: Optional[float] = None
    ) -> None:
        """
        Enable response caching for endpoint

        Args:
            endpoint: API endpoint
            method: HTTP method
            ttl_seconds: Cache TTL in seconds
        """
        key = f"{method}:{endpoint}"

        self.api_cache[key] = {
            "enabled": True,
            "ttl_seconds": ttl_seconds or self.cache_ttl_seconds,
            "created_at": datetime.now(timezone.utc),
        }

        logger.info(f"Enabled response caching for: {key}")

    def get_cached_response(
        self, endpoint: str, method: str, cache_key: Optional[str] = None
    ) -> Optional[Any]:
        """
        Get cached response

        Args:
            endpoint: API endpoint
            method: HTTP method
            cache_key: Optional cache key

        Returns:
            Cached response or None
        """
        key = f"{method}:{endpoint}"

        if key not in self.api_cache or not self.api_cache[key]["enabled"]:
            return None

        cache_data = self.api_cache[key]

        if cache_key and cache_key in cache_data.get("responses", {}):
            cached_response = cache_data["responses"][cache_key]

            # Check TTL
            if (
                datetime.now(timezone.utc) - cached_response["cached_at"]
            ).total_seconds() < cache_data["ttl_seconds"]:
                self.total_cache_hits += 1
                logger.debug(f"Cache hit: {key}")
                return cached_response["data"]
            else:
                # Remove expired cache
                del cache_data["responses"][cache_key]
                self.total_cache_misses += 1
                return None

        self.total_cache_misses += 1
        return None

    def cache_response(
        self, endpoint: str, method: str, data: Any, cache_key: Optional[str] = None
    ) -> None:
        """
        Cache response

        Args:
            endpoint: API endpoint
            method: HTTP method
            data: Response data
            cache_key: Optional cache key
        """
        key = f"{method}:{endpoint}"

        if key not in self.api_cache or not self.api_cache[key]["enabled"]:
            return

        cache_data = self.api_cache[key]

        if "responses" not in cache_data:
            cache_data["responses"] = {}

        # Generate cache key if not provided
        if not cache_key:
            cache_key = hashlib.md5(
                json.dumps(data, default=str).encode(), usedforsecurity=False
            ).hexdigest()

        # Check cache size
        if len(cache_data["responses"]) >= self.max_cache_size:
            # Remove oldest entry
            oldest_key = min(cache_data["responses"].items(), key=lambda x: x[1]["cached_at"])[0]
            del cache_data["responses"][oldest_key]

        cache_data["responses"][cache_key] = {"data": data, "cached_at": datetime.now(timezone.utc)}

        logger.debug(f"Cached response: {key}")

    async def process_async_task(
        self, task_func: Callable[..., Awaitable[Any]], *args, **kwargs
    ) -> Any:
        """
        Process task asynchronously

        Args:
            task_func: Async function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Task result
        """
        try:
            result = await task_func(*args, **kwargs)
            return result
        except Exception as e:
            logger.error(f"Async task failed: {e}")
            raise

    def get_response_metrics(self, endpoint: str, method: str) -> Optional[ResponseTimeMetrics]:
        """
        Get response metrics for endpoint

        Args:
            endpoint: API endpoint
            method: HTTP method

        Returns:
            Response metrics or None
        """
        key = f"{method}:{endpoint}"
        return self.response_metrics.get(key)

    def get_all_metrics(self) -> Dict[str, ResponseTimeMetrics]:
        """Get all response metrics"""
        return self.response_metrics.copy()

    def get_statistics(self) -> Dict[str, Any]:
        """Get optimizer statistics"""
        return {
            "total_requests_tracked": self.total_requests_tracked,
            "total_endpoints": len(self.response_metrics),
            "total_cache_hits": self.total_cache_hits,
            "total_cache_misses": self.total_cache_misses,
            "cache_hit_rate": (
                self.total_cache_hits / (self.total_cache_hits + self.total_cache_misses)
                if (self.total_cache_hits + self.total_cache_misses) > 0
                else 0
            ),
            "optimizations_generated": len(self.recommendations),
        }


def get_api_response_time_optimizer(
    config: Optional[Dict[str, Any]] = None,
) -> APIResponseTimeOptimizer:
    """
    Factory function to get API response time optimizer instance

    Args:
        config: Optional configuration dictionary

    Returns:
        APIResponseTimeOptimizer: Optimizer instance
    """
    return APIResponseTimeOptimizer(config)
