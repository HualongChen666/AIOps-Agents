# -*- coding: utf-8 -*-
"""
Performance Optimization Module
==============================

Comprehensive performance optimization for AIOps Agent including:
- Performance bottleneck identification
- Cache strategy optimization
- Database query optimization
- Async operation and concurrency optimization
- Memory usage optimization
- Performance monitoring and alerting
"""

import asyncio
import functools
import os
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, TypedDict

import psutil
from loguru import logger

# Try to import caching libraries
try:
    from cachetools import TTLCache

    CACHING_AVAILABLE = True
except ImportError:
    CACHING_AVAILABLE = False
    logger.warning("Caching library not available, using simple cache")


class PerformanceMetric(Enum):
    """Types of performance metrics"""

    RESPONSE_TIME = "response_time"
    MEMORY_USAGE = "memory_usage"
    CPU_USAGE = "cpu_usage"
    DATABASE_QUERY_TIME = "database_query_time"
    CACHE_HIT_RATE = "cache_hit_rate"
    THROUGHPUT = "throughput"
    ERROR_RATE = "error_rate"


class DetectionDict(TypedDict):
    """Type definition for detection dictionary"""

    metric: str
    severity: str
    value: float
    threshold: float


@dataclass
class PerformanceBottleneck:
    """Identified performance bottleneck"""

    bottleneck_id: str
    component: str
    metric: PerformanceMetric
    severity: str  # low, medium, high, critical
    current_value: float
    threshold_value: float
    description: str
    detected_at: datetime = field(default_factory=datetime.now)
    suggestions: List[str] = field(default_factory=list)


@dataclass
class CacheStats:
    """Cache statistics"""

    cache_name: str
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    size: int = 0
    max_size: int = 0

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate"""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0


class PerformanceOptimizer:
    """
    Comprehensive performance optimizer
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize performance optimizer

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}

        # Performance monitoring
        self.metrics_history: Dict[str, List[Tuple[datetime, float]]] = defaultdict(list)
        self.bottlenecks: List[PerformanceBottleneck] = []
        self.thresholds = self._initialize_thresholds()

        # Caching
        self.caches: Dict[str, Any] = {}
        self.cache_stats: Dict[str, CacheStats] = {}
        self.cache_strategies = self._initialize_cache_strategies()

        # Database optimization
        self.query_stats: Dict[str, List[float]] = defaultdict(list)
        self.slow_queries: List[Dict[str, Any]] = []

        # Async optimization
        self.async_pools: Dict[str, asyncio.Semaphore] = {}
        self.concurrent_limits = self._initialize_concurrent_limits()

        # Memory optimization
        self.memory_pools: Dict[str, List] = defaultdict(list)
        self.memory_monitor = self._initialize_memory_monitor()

        # Performance alerts
        self.alert_thresholds = self._initialize_alert_thresholds()
        self.performance_alerts: List[Dict[str, Any]] = []

        # Initialize components
        self._initialize_caches()
        self._initialize_async_pools()
        self._start_background_monitoring()

        logger.info("Performance Optimizer initialized")

    def _initialize_thresholds(self) -> Dict[str, float]:
        """Initialize performance thresholds"""
        return {
            "response_time_warning": 1.0,  # seconds
            "response_time_critical": 5.0,
            "memory_usage_warning": 80.0,  # percentage
            "memory_usage_critical": 95.0,
            "cpu_usage_warning": 70.0,  # percentage
            "cpu_usage_critical": 90.0,
            "cache_hit_rate_warning": 0.5,  # 50%
            "error_rate_warning": 0.05,  # 5%
            "error_rate_critical": 0.15,  # 15%
        }

    def _initialize_cache_strategies(self) -> Dict[str, Dict[str, Any]]:
        """Initialize cache strategies"""
        return {
            "metrics": {"ttl": 60, "max_size": 1000, "strategy": "lru"},  # seconds
            "alerts": {"ttl": 300, "max_size": 500, "strategy": "lru"},
            "topology": {"ttl": 600, "max_size": 200, "strategy": "lru"},
            "user_sessions": {"ttl": 3600, "max_size": 100, "strategy": "lru"},
        }

    def _initialize_concurrent_limits(self) -> Dict[str, int]:
        """Initialize concurrent operation limits"""
        return {
            "api_requests": 100,
            "database_queries": 50,
            "external_api_calls": 20,
            "file_operations": 10,
        }

    def _initialize_memory_monitor(self) -> bool:
        """Initialize memory monitoring"""
        try:
            self.memory_monitor = psutil.virtual_memory()
            return True
        except Exception as e:
            logger.warning(f"Memory monitoring not available: {e}")
            return False

    def _initialize_alert_thresholds(self) -> Dict[str, float]:
        """Initialize performance alert thresholds"""
        return {
            "response_time_alert": 3.0,
            "memory_alert": 85.0,
            "cpu_alert": 80.0,
            "error_rate_alert": 0.10,
        }

    def _initialize_caches(self):
        """Initialize caches"""
        if CACHING_AVAILABLE:
            for cache_name, strategy in self.cache_strategies.items():
                try:
                    self.caches[cache_name] = TTLCache(
                        maxsize=strategy["max_size"], ttl=strategy["ttl"]
                    )
                    logger.info(f"Initialized cache: {cache_name}")
                except Exception as e:
                    logger.error(f"Failed to initialize cache {cache_name}: {e}")
        else:
            logger.warning("Caching not available, using simple dict cache")
            # Simple dict-based cache as fallback
            for cache_name, strategy in self.cache_strategies.items():
                self.caches[cache_name] = {}

    def _initialize_async_pools(self):
        """Initialize async semaphore pools"""
        for pool_name, limit in self.concurrent_limits.items():
            self.async_pools[pool_name] = asyncio.Semaphore(limit)
            logger.info(f"Initialized async pool: {pool_name} with limit {limit}")

    def _start_background_monitoring(self):
        """Start background performance monitoring"""
        # Skip background monitoring during tests
        if os.environ.get("PERFORMANCE_OPTIMIZER_DISABLED") == "true":
            logger.info("Background performance monitoring disabled for tests")
            return

        # Start background thread for monitoring
        monitor_thread = threading.Thread(target=self._background_monitoring_loop, daemon=True)
        monitor_thread.start()
        logger.info("Background performance monitoring started")

    def _background_monitoring_loop(self):
        """Background monitoring loop"""
        while True:
            try:
                self._collect_metrics()
                self._detect_bottlenecks()
                self._check_alerts()
                self._cleanup_old_metrics()
                time.sleep(30)  # Monitor every 30 seconds
            except Exception as e:
                logger.error(f"Background monitoring error: {e}")
                time.sleep(30)

    def _collect_metrics(self):
        """Collect performance metrics"""
        timestamp = datetime.now()

        # CPU usage
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            self.metrics_history["cpu_usage"].append((timestamp, cpu_percent))
        except Exception as e:
            logger.error(f"Failed to collect CPU metrics: {e}")

        # Memory usage
        try:
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            self.metrics_history["memory_usage"].append((timestamp, memory_percent))
        except Exception as e:
            logger.error(f"Failed to collect memory metrics: {e}")

        # Cache hit rates
        for cache_name, stats in self.cache_stats.items():
            if stats.hits + stats.misses > 0:
                hit_rate = stats.hits / (stats.hits + stats.misses)
                self.metrics_history[f"cache_hit_rate_{cache_name}"].append((timestamp, hit_rate))

    def _detect_bottlenecks(self) -> Dict[str, Any]:
        """Detect performance bottlenecks"""
        detected: List[DetectionDict] = []

        # Check response times
        if "response_time" in self.metrics_history:
            recent_times = [v for _, v in self.metrics_history["response_time"][-10:]]
            if recent_times:
                avg_time = sum(recent_times) / len(recent_times)
                if avg_time > self.thresholds["response_time_critical"]:
                    detected.append(
                        DetectionDict(
                            metric="response_time",
                            severity="critical",
                            value=avg_time,
                            threshold=self.thresholds["response_time_critical"],
                        )
                    )

        # Check memory usage
        if "memory_usage" in self.metrics_history:
            recent_memory = [v for _, v in self.metrics_history["memory_usage"][-5:]]
            if recent_memory:
                avg_memory = sum(recent_memory) / len(recent_memory)
                if avg_memory > self.thresholds["memory_usage_critical"]:
                    detected.append(
                        DetectionDict(
                            metric="memory_usage",
                            severity="critical",
                            value=avg_memory,
                            threshold=self.thresholds["memory_usage_critical"],
                        )
                    )

        # Check CPU usage
        if "cpu_usage" in self.metrics_history:
            recent_cpu = [v for _, v in self.metrics_history["cpu_usage"][-5:]]
            if recent_cpu:
                avg_cpu = sum(recent_cpu) / len(recent_cpu)
                if avg_cpu > self.thresholds["cpu_usage_critical"]:
                    detected.append(
                        DetectionDict(
                            metric="cpu_usage",
                            severity="critical",
                            value=avg_cpu,
                            threshold=self.thresholds["cpu_usage_critical"],
                        )
                    )

        # Store detected bottlenecks
        for detection in detected:
            bottleneck = PerformanceBottleneck(
                bottleneck_id=f"bottleneck_{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
                component="system",
                metric=PerformanceMetric(detection["metric"]),
                severity=detection["severity"],
                current_value=detection["value"],
                threshold_value=detection["threshold"],
                description=f"High {detection['metric']} detected",
            )
            self.bottlenecks.append(bottleneck)

        return {"detected_count": len(detected), "bottlenecks": detected}

    def _check_alerts(self):
        """Check if performance thresholds are exceeded"""
        for metric_name, metric_history in self.metrics_history.items():
            if not metric_history:
                continue

            recent_values = [v for _, v in metric_history[-10:]]
            if not recent_values:
                continue

            avg_value = sum(recent_values) / len(recent_values)

            # Check against alert thresholds
            for threshold_name, threshold_value in self.alert_thresholds.items():
                if threshold_name in metric_name and avg_value > threshold_value:
                    alert = {
                        "alert_id": f"alert_{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
                        "metric": metric_name,
                        "current_value": avg_value,
                        "threshold": threshold_value,
                        "timestamp": datetime.now().isoformat(),
                    }
                    self.performance_alerts.append(alert)
                    logger.warning(
                        f"Performance alert: {metric_name} = {avg_value:.2f} > {threshold_value}"
                    )

    def _cleanup_old_metrics(self):
        """Clean up old metrics data"""
        cutoff_time = datetime.now() - timedelta(hours=24)

        for metric_name in list(self.metrics_history.keys()):
            self.metrics_history[metric_name] = [
                (ts, val) for ts, val in self.metrics_history[metric_name] if ts > cutoff_time
            ]

        # Clean up old bottlenecks
        cutoff_bottleneck = datetime.now() - timedelta(hours=1)
        self.bottlenecks = [b for b in self.bottlenecks if b.detected_at > cutoff_bottleneck]

        # Clean up old alerts
        cutoff_alert = datetime.now() - timedelta(hours=6)
        self.performance_alerts = [
            a
            for a in self.performance_alerts
            if datetime.fromisoformat(a["timestamp"]) > cutoff_alert
        ]

    def cache_get(self, cache_name: str, key: str) -> Optional[Any]:
        """
        Get value from cache

        Args:
            cache_name: Name of the cache
            key: Cache key

        Returns:
            Cached value or None
        """
        if cache_name not in self.caches:
            return None

        cache = self.caches[cache_name]

        if CACHING_AVAILABLE:
            try:
                value = cache.get(key)
                if value is not None:
                    if cache_name not in self.cache_stats:
                        self.cache_stats[cache_name] = CacheStats(cache_name=cache_name)
                    self.cache_stats[cache_name].hits += 1
                    return value
                else:
                    if cache_name not in self.cache_stats:
                        self.cache_stats[cache_name] = CacheStats(cache_name=cache_name)
                    self.cache_stats[cache_name].misses += 1
                    return None
            except Exception as e:
                logger.error(f"Cache get error: {e}")
                return None
        else:
            # Simple dict cache
            if key in cache:
                if cache_name not in self.cache_stats:
                    self.cache_stats[cache_name] = CacheStats(cache_name=cache_name)
                self.cache_stats[cache_name].hits += 1
                return cache[key]
            else:
                if cache_name not in self.cache_stats:
                    self.cache_stats[cache_name] = CacheStats(cache_name=cache_name)
                self.cache_stats[cache_name].misses += 1
                return None

    def cache_set(self, cache_name: str, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Set value in cache

        Args:
            cache_name: Name of the cache
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
        """
        if cache_name not in self.caches:
            return

        cache = self.caches[cache_name]

        if CACHING_AVAILABLE:
            try:
                cache[key] = value
            except Exception as e:
                logger.error(f"Cache set error: {e}")
        else:
            cache[key] = value

    def cache_delete(self, cache_name: str, key: str) -> bool:
        """
        Delete value from cache

        Args:
            cache_name: Name of the cache
            key: Cache key

        Returns:
            True if deleted
        """
        if cache_name not in self.caches:
            return False

        cache = self.caches[cache_name]

        if CACHING_AVAILABLE:
            try:
                if key in cache:
                    del cache[key]
                    return True
            except Exception as e:
                logger.error(f"Cache delete error: {e}")
        else:
            if key in cache:
                del cache[key]
                return True

        return False

    def cache_clear(self, cache_name: str) -> int:
        """
        Clear all values from cache

        Args:
            cache_name: Name of the cache

        Returns:
            Number of items cleared
        """
        if cache_name not in self.caches:
            return 0

        cache = self.caches[cache_name]

        if CACHING_AVAILABLE:
            try:
                size = len(cache)
                cache.clear()
                return size
            except Exception as e:
                logger.error(f"Cache clear error: {e}")
                return 0
        else:
            size = len(cache)
            cache.clear()
            return size

    async def with_semaphore(self, pool_name: str, func: Callable, *args, **kwargs):
        """
        Execute function with semaphore-based concurrency control

        Args:
            pool_name: Name of the semaphore pool
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result
        """
        if pool_name not in self.async_pools:
            return await func(*args, **kwargs)

        semaphore = self.async_pools[pool_name]

        async with semaphore:
            return await func(*args, **kwargs)

    def optimize_database_query(self, query_func: Callable) -> Callable:
        """
        Decorator to optimize database query performance

        Args:
            query_func: Database query function

        Returns:
            Wrapped function
        """

        @functools.wraps(query_func)
        def wrapper(*args, **kwargs):
            start_time = time.time()

            try:
                result = query_func(*args, **kwargs)
                execution_time = time.time() - start_time

                # Track query statistics
                func_name = query_func.__name__
                self.query_stats[func_name].append(execution_time)

                # Log slow queries
                if execution_time > 1.0:  # 1 second threshold
                    logger.warning(f"Slow query detected: {func_name} took {execution_time:.2f}s")
                    self.slow_queries.append(
                        {
                            "function": func_name,
                            "execution_time": execution_time,
                            "timestamp": datetime.now().isoformat(),
                        }
                    )

                return result
            except Exception as e:
                logger.error(f"Query execution error: {e}")
                raise

        return wrapper

    def monitor_performance(self, component: str, metric: PerformanceMetric, value: float) -> None:
        """
        Record performance metric

        Args:
            component: Component name
            metric: Performance metric type
            value: Metric value
        """
        metric_key = f"{component}_{metric.value}"
        self.metrics_history[metric_key].append((datetime.now(), value))

        # Check against thresholds
        if metric == PerformanceMetric.RESPONSE_TIME:
            if value > self.thresholds["response_time_critical"]:
                bottleneck = PerformanceBottleneck(
                    bottleneck_id=f"perf_{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
                    component=component,
                    metric=metric,
                    severity="critical",
                    current_value=value,
                    threshold_value=self.thresholds["response_time_critical"],
                    description=f"Critical response time detected in {component}",
                )
                self.bottlenecks.append(bottleneck)

    def optimize_memory_usage(self):
        """
        Optimize memory usage by cleaning up unused resources
        """
        logger.info("Optimizing memory usage...")

        # Clear old cache entries
        for cache_name in list(self.caches.keys()):
            try:
                cleared = self.cache_clear(cache_name)
                logger.info(f"Cleared {cleared} items from cache {cache_name}")
            except Exception as e:
                logger.error(f"Failed to clear cache {cache_name}: {e}")

        # Clean up old metrics
        self._cleanup_old_metrics()

        # Trigger garbage collection
        import gc

        collected = gc.collect()
        logger.info(f"Garbage collection freed {collected} objects")

    def get_performance_report(self) -> Dict[str, Any]:
        """
        Get comprehensive performance report

        Returns:
            Performance report
        """
        return {
            "timestamp": datetime.now().isoformat(),
            "bottlenecks": [
                {
                    "bottleneck_id": b.bottleneck_id,
                    "component": b.component,
                    "metric": b.metric.value,
                    "severity": b.severity,
                    "current_value": b.current_value,
                    "threshold_value": b.threshold_value,
                    "detected_at": b.detected_at.isoformat(),
                    "suggestions": b.suggestions,
                }
                for b in self.bottlenecks[-10:]  # Last 10 bottlenecks
            ],
            "cache_stats": {
                name: {
                    "hits": stats.hits,
                    "misses": stats.misses,
                    "hit_rate": stats.hit_rate,
                    "size": stats.size,
                    "max_size": stats.max_size,
                }
                for name, stats in self.cache_stats.items()
            },
            "query_stats": {
                func_name: {
                    "avg_time": sum(times) / len(times) if times else 0,
                    "max_time": max(times) if times else 0,
                    "call_count": len(times),
                }
                for func_name, times in self.query_stats.items()
            },
            "slow_queries": self.slow_queries[-20:],  # Last 20 slow queries
            "performance_alerts": self.performance_alerts[-10:],  # Last 10 alerts
            "metrics_summary": {
                metric_name: {
                    "current": values[-1][1] if values else 0,
                    "average": sum(v for _, v in values) / len(values) if values else 0,
                    "sample_count": len(values),
                }
                for metric_name, values in self.metrics_history.items()
            },
        }


# Global instance
performance_optimizer = PerformanceOptimizer()


def get_performance_optimizer(config: Optional[Dict[str, Any]] = None) -> PerformanceOptimizer:
    """
    Get the global performance optimizer instance

    Args:
        config: Optional configuration to reinitialize the optimizer

    Returns:
        PerformanceOptimizer instance
    """
    global performance_optimizer
    if config is not None and performance_optimizer is None:
        performance_optimizer = PerformanceOptimizer(config)
    return performance_optimizer
