# -*- coding: utf-8 -*-
"""
API Performance Optimizer
Enterprise-grade API performance optimization with response time analysis and caching
"""

import functools
import statistics
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from loguru import logger


class OptimizationStrategy(Enum):
    """API optimization strategy"""

    RESPONSE_CACHE = "response_cache"
    ASYNC_PROCESSING = "async_processing"
    BATCH_PROCESSING = "batch_processing"
    COMPRESSION = "compression"
    CONNECTION_POOLING = "connection_pooling"


class PriorityLevel(Enum):
    """Priority level for API optimization"""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class APIPerformanceMetric:
    """API performance metric"""

    endpoint: str
    method: str
    response_time_ms: float
    timestamp: datetime
    status_code: int
    cache_hit: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class APIOptimization:
    """API optimization recommendation"""

    optimization_id: str
    endpoint: str
    strategy: OptimizationStrategy
    priority: PriorityLevel
    current_performance: Dict[str, float]
    expected_improvement: float
    description: str
    implementation_complexity: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class APIPerformanceOptimizer:
    """
    Enterprise-grade API performance optimizer
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize API performance optimizer

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}

        # Performance metrics storage
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=10000))
        self.endpoint_stats: Dict[str, Dict[str, Any]] = {}

        # Optimization recommendations
        self.optimizations: Dict[str, APIOptimization] = {}

        # Response cache
        self.response_cache: Dict[str, Any] = {}
        self.cache_ttl: Dict[str, datetime] = {}

        # Rate limiting configuration
        self.rate_limits: Dict[str, Dict[str, Any]] = {}
        self.request_counts: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))

        # Resource monitoring
        self.resource_usage: Dict[str, Any] = {
            "memory_mb": 0.0,
            "cpu_percent": 0.0,
            "active_connections": 0,
        }

        # Configuration
        self.slow_api_threshold_ms = self.config.get("slow_api_threshold_ms", 1000)
        self.cache_enabled = self.config.get("cache_enabled", True)
        self.default_cache_ttl_seconds = self.config.get("default_cache_ttl_seconds", 300)
        self.default_rate_limit = self.config.get("default_rate_limit", 100)  # requests per minute

        # Statistics
        self.total_requests = 0
        self.cache_hits = 0
        self.cache_misses = 0
        self.total_optimizations = 0
        self.rate_limited_requests = 0

        logger.info("API performance optimizer initialized")

    def record_api_call(
        self,
        endpoint: str,
        method: str,
        response_time_ms: float,
        status_code: int,
        cache_hit: bool = False,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Record API call performance metric

        Args:
            endpoint: API endpoint
            method: HTTP method
            response_time_ms: Response time in milliseconds
            status_code: HTTP status code
            cache_hit: Whether response was served from cache
            metadata: Additional metadata
        """
        metric = APIPerformanceMetric(
            endpoint=endpoint,
            method=method,
            response_time_ms=response_time_ms,
            timestamp=datetime.now(timezone.utc),
            status_code=status_code,
            cache_hit=cache_hit,
            metadata=metadata or {},
        )

        # Store metric
        self.metrics[endpoint].append(metric)

        # Update endpoint statistics
        if endpoint not in self.endpoint_stats:
            self.endpoint_stats[endpoint] = {
                "total_calls": 0,
                "total_response_time_ms": 0.0,
                "max_response_time_ms": 0.0,
                "min_response_time_ms": float("inf"),
                "error_count": 0,
                "cache_hits": 0,
                "cache_misses": 0,
            }

        stats = self.endpoint_stats[endpoint]
        stats["total_calls"] += 1
        stats["total_response_time_ms"] += response_time_ms
        stats["max_response_time_ms"] = max(stats["max_response_time_ms"], response_time_ms)
        stats["min_response_time_ms"] = min(stats["min_response_time_ms"], response_time_ms)

        if status_code >= 400:
            stats["error_count"] += 1

        if cache_hit:
            stats["cache_hits"] += 1
            self.cache_hits += 1
        else:
            stats["cache_misses"] += 1
            self.cache_misses += 1

        self.total_requests += 1

        logger.debug(f"Recorded API call: {endpoint}, response_time: {response_time_ms}ms")

    def analyze_response_times(self) -> Dict[str, Any]:
        """
        Analyze API response time distribution

        Returns:
            Response time analysis
        """
        analysis = {}

        for endpoint, metrics in self.metrics.items():
            if not metrics:
                continue

            response_times = [m.response_time_ms for m in metrics]

            analysis[endpoint] = {
                "count": len(response_times),
                "avg_ms": statistics.mean(response_times),
                "median_ms": statistics.median(response_times),
                "p95_ms": self._calculate_percentile(response_times, 95),
                "p99_ms": self._calculate_percentile(response_times, 99),
                "max_ms": max(response_times),
                "min_ms": min(response_times),
                "std_dev_ms": statistics.stdev(response_times) if len(response_times) > 1 else 0.0,
            }

        return analysis

    def identify_slow_apis(self) -> List[Dict[str, Any]]:
        """
        Identify slow APIs based on threshold

        Returns:
            List of slow APIs sorted by impact
        """
        slow_apis = []

        for endpoint, stats in self.endpoint_stats.items():
            avg_response_time = stats["total_response_time_ms"] / stats["total_calls"]

            if avg_response_time > self.slow_api_threshold_ms:
                slow_apis.append(
                    {
                        "endpoint": endpoint,
                        "avg_response_time_ms": avg_response_time,
                        "max_response_time_ms": stats["max_response_time_ms"],
                        "total_calls": stats["total_calls"],
                        "error_rate": stats["error_count"] / stats["total_calls"],
                        "impact_score": avg_response_time * stats["total_calls"],
                    }
                )

        # Sort by impact score
        slow_apis.sort(key=lambda x: x["impact_score"], reverse=True)

        return slow_apis

    def generate_optimizations(self) -> List[APIOptimization]:
        """
        Generate API optimization recommendations

        Returns:
            List of optimization recommendations
        """
        optimizations = []

        # Analyze slow APIs
        slow_apis = self.identify_slow_apis()

        for api in slow_apis:
            # Generate optimization based on API characteristics
            optimization = self._generate_api_optimization(api)
            if optimization:
                optimizations.append(optimization)
                self.optimizations[optimization.optimization_id] = optimization
                self.total_optimizations += 1

        logger.info(f"Generated {len(optimizations)} API optimizations")

        return optimizations

    def _generate_api_optimization(self, api_info: Dict[str, Any]) -> Optional[APIOptimization]:
        """
        Generate optimization for a specific API

        Args:
            api_info: API information

        Returns:
            Optimization recommendation
        """
        endpoint = api_info["endpoint"]
        avg_response_time = api_info["avg_response_time_ms"]
        total_calls = api_info["total_calls"]

        # Determine optimization strategy based on characteristics
        if avg_response_time > 5000:  # Very slow
            strategy = OptimizationStrategy.ASYNC_PROCESSING
            priority = PriorityLevel.CRITICAL
            expected_improvement = 0.7  # 70% improvement
            description = (
                f"API {endpoint} is very slow ({avg_response_time:.0f}ms). "
                "Implement async processing."
            )
        elif avg_response_time > 2000:  # Slow
            strategy = OptimizationStrategy.RESPONSE_CACHE
            priority = PriorityLevel.HIGH
            expected_improvement = 0.5  # 50% improvement
            description = (
                f"API {endpoint} is slow ({avg_response_time:.0f}ms). Implement response caching."
            )
        elif avg_response_time > 1000:  # Moderately slow
            strategy = OptimizationStrategy.BATCH_PROCESSING
            priority = PriorityLevel.MEDIUM
            expected_improvement = 0.3  # 30% improvement
            description = (
                f"API {endpoint} is moderately slow ({avg_response_time:.0f}ms). "
                "Consider batch processing."
            )
        else:
            return None

        return APIOptimization(
            optimization_id=f"opt_{hash(endpoint)}",
            endpoint=endpoint,
            strategy=strategy,
            priority=priority,
            current_performance={
                "avg_response_time_ms": avg_response_time,
                "total_calls": total_calls,
            },
            expected_improvement=expected_improvement,
            description=description,
            implementation_complexity=(
                "medium" if strategy == OptimizationStrategy.ASYNC_PROCESSING else "low"
            ),
        )

    def setup_response_cache(self, endpoint: str, ttl_seconds: Optional[int] = None) -> None:
        """
        Setup response cache for an endpoint

        Args:
            endpoint: API endpoint
            ttl_seconds: Cache TTL in seconds
        """
        ttl_seconds = ttl_seconds or self.default_cache_ttl_seconds
        self.response_cache[endpoint] = {}  # Initialize cache for endpoint
        logger.info(f"Setup response cache for {endpoint} with TTL {ttl_seconds}s")

    def get_cached_response(self, endpoint: str, cache_key: str) -> Optional[Any]:
        """
        Get cached response if available and not expired

        Args:
            endpoint: API endpoint
            cache_key: Cache key

        Returns:
            Cached response or None
        """
        if not self.cache_enabled:
            return None

        full_key = f"{endpoint}:{cache_key}"

        if full_key in self.response_cache:
            # Check TTL
            if full_key in self.cache_ttl:
                if datetime.now(timezone.utc) < self.cache_ttl[full_key]:
                    return self.response_cache[full_key]
                else:
                    # Expired, remove from cache
                    del self.response_cache[full_key]
                    del self.cache_ttl[full_key]
            else:
                return self.response_cache[full_key]

        return None

    def set_cached_response(
        self, endpoint: str, cache_key: str, response: Any, ttl_seconds: Optional[int] = None
    ) -> None:
        """
        Cache response

        Args:
            endpoint: API endpoint
            cache_key: Cache key
            response: Response to cache
            ttl_seconds: Cache TTL in seconds
        """
        if not self.cache_enabled:
            return

        ttl_seconds = ttl_seconds or self.default_cache_ttl_seconds
        full_key = f"{endpoint}:{cache_key}"

        self.response_cache[full_key] = response
        self.cache_ttl[full_key] = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)

    def invalidate_cache(self, endpoint: Optional[str] = None) -> None:
        """
        Invalidate cache

        Args:
            endpoint: Specific endpoint to invalidate, or None for all
        """
        if endpoint:
            keys_to_remove = [
                key for key in self.response_cache.keys() if key.startswith(f"{endpoint}:")
            ]
            for key in keys_to_remove:
                del self.response_cache[key]
                if key in self.cache_ttl:
                    del self.cache_ttl[key]
            logger.info(f"Invalidated cache for endpoint: {endpoint}")
        else:
            self.response_cache.clear()
            self.cache_ttl.clear()
            logger.info("Invalidated all cache")

    def get_performance_summary(self) -> Dict[str, Any]:
        """
        Get performance summary

        Returns:
            Performance summary
        """
        return {
            "total_requests": self.total_requests,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "cache_hit_rate": (
                self.cache_hits / self.total_requests if self.total_requests > 0 else 0.0
            ),
            "total_optimizations": self.total_optimizations,
            "endpoints_monitored": len(self.endpoint_stats),
            "slow_apis_count": len(self.identify_slow_apis()),
        }

    def _calculate_percentile(self, data: List[float], percentile: float) -> float:
        """
        Calculate percentile of data

        Args:
            data: Data points
            percentile: Percentile to calculate (0-100)

        Returns:
            Percentile value
        """
        if not data:
            return 0.0

        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]

    def setup_rate_limit(
        self, endpoint: str, requests_per_minute: int, burst_size: Optional[int] = None
    ) -> None:
        """
        Setup rate limit for an endpoint

        Args:
            endpoint: API endpoint
            requests_per_minute: Maximum requests per minute
            burst_size: Burst size (optional)
        """
        burst_size = burst_size or requests_per_minute // 2

        self.rate_limits[endpoint] = {
            "requests_per_minute": requests_per_minute,
            "burst_size": burst_size,
            "created_at": datetime.now(timezone.utc),
        }

        logger.info(f"Setup rate limit for {endpoint}: {requests_per_minute} req/min")

    def check_rate_limit(self, endpoint: str) -> bool:
        """
        Check if request is within rate limit

        Args:
            endpoint: API endpoint

        Returns:
            True if request is allowed, False otherwise
        """
        if endpoint not in self.rate_limits:
            return True  # No rate limit configured

        rate_limit = self.rate_limits[endpoint]
        now = datetime.now(timezone.utc)

        # Clean old request records (older than 1 minute)
        cutoff = now - timedelta(minutes=1)
        self.request_counts[endpoint] = deque(
            [ts for ts in self.request_counts[endpoint] if ts > cutoff]
        )

        # Check rate limit
        current_count = len(self.request_counts[endpoint])
        if current_count >= rate_limit["requests_per_minute"]:
            self.rate_limited_requests += 1
            return False

        # Add current request
        self.request_counts[endpoint].append(now)
        return True

    def get_throughput_metrics(self) -> Dict[str, Any]:
        """
        Get throughput metrics

        Returns:
            Throughput metrics
        """
        now = datetime.now(timezone.utc)
        one_minute_ago = now - timedelta(minutes=1)
        one_hour_ago = now - timedelta(hours=1)

        requests_per_minute = 0
        requests_per_hour = 0

        for endpoint_metrics in self.metrics.values():
            for metric in endpoint_metrics:
                if metric.timestamp > one_minute_ago:
                    requests_per_minute += 1
                if metric.timestamp > one_hour_ago:
                    requests_per_hour += 1

        return {
            "requests_per_minute": requests_per_minute,
            "requests_per_hour": requests_per_hour,
            "rate_limited_requests": self.rate_limited_requests,
            "rate_limiting_enabled": len(self.rate_limits) > 0,
            "endpoints_with_rate_limits": list(self.rate_limits.keys()),
        }

    def monitor_resource_usage(self) -> Dict[str, Any]:
        """
        Monitor resource usage using psutil when available, otherwise fallback values.

        Returns:
            Resource usage metrics
        """
        try:
            import psutil

            memory = psutil.virtual_memory()
            self.resource_usage = {
                "memory_mb": memory.used / (1024 * 1024),
                "cpu_percent": psutil.cpu_percent(interval=None),
                "active_connections": sum(len(q) for q in self.request_counts.values()),
            }
        except Exception as e:
            logger.warning(f"Failed to monitor resource usage: {e}")
        return self.resource_usage

    def setup_resource_limits(
        self, max_memory_mb: float, max_cpu_percent: float, max_connections: int
    ) -> None:
        """
        Setup resource limits

        Args:
            max_memory_mb: Maximum memory usage in MB
            max_cpu_percent: Maximum CPU usage percentage
            max_connections: Maximum active connections
        """
        self.resource_limits = {
            "max_memory_mb": max_memory_mb,
            "max_cpu_percent": max_cpu_percent,
            "max_connections": max_connections,
        }

        logger.info(
            f"Setup resource limits: memory={max_memory_mb}MB, "
            f"cpu={max_cpu_percent}%, connections={max_connections}"
        )

    def check_resource_limits(self) -> Dict[str, bool]:
        """
        Check if current resource usage is within limits

        Returns:
            Dictionary with limit check results
        """
        current_usage = self.monitor_resource_usage()

        if not hasattr(self, "resource_limits"):
            return {"memory_ok": True, "cpu_ok": True, "connections_ok": True}

        return {
            "memory_ok": current_usage["memory_mb"] <= self.resource_limits["max_memory_mb"],
            "cpu_ok": current_usage["cpu_percent"] <= self.resource_limits["max_cpu_percent"],
            "connections_ok": (
                current_usage["active_connections"] <= self.resource_limits["max_connections"]
            ),
        }


# Global instance
_api_optimizer: Optional[APIPerformanceOptimizer] = None


def get_api_performance_optimizer() -> APIPerformanceOptimizer:
    """
    Get the global API performance optimizer instance

    Returns:
        APIPerformanceOptimizer instance
    """
    global _api_optimizer
    if _api_optimizer is None:
        _api_optimizer = APIPerformanceOptimizer()
    return _api_optimizer


def cache_response(ttl_seconds: int = 300):
    """
    Decorator to cache API responses

    Args:
        ttl_seconds: Cache TTL in seconds

    Returns:
        Decorator function
    """

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            optimizer = get_api_performance_optimizer()

            # Generate cache key from function arguments
            cache_key = f"{func.__name__}:{hash(str(args) + str(kwargs))}"

            # Try to get cached response
            cached_response = optimizer.get_cached_response(func.__name__, cache_key)
            if cached_response is not None:
                return cached_response

            # Execute function
            result = await func(*args, **kwargs)

            # Cache response
            optimizer.set_cached_response(func.__name__, cache_key, result, ttl_seconds)

            return result

        return wrapper

    return decorator
