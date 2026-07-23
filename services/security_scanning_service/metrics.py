# -*- coding: utf-8 -*-
"""Prometheus metrics collector."""

from __future__ import annotations

import time
from typing import Optional

from prometheus_client import Counter, Gauge, Histogram


class MetricsCollector:
    """Collects Prometheus metrics for the service.

    The collector caches instances by normalized service name to avoid
    duplicate Prometheus metric registration across tests or restarts.
    """

    _instances: dict[str, "MetricsCollector"] = {}

    def __new__(cls, service_name: str) -> "MetricsCollector":
        prefix = service_name.replace("-", "_")
        existing = cls._instances.get(prefix)
        if existing is not None:
            return existing
        instance = super().__new__(cls)
        cls._instances[prefix] = instance
        return instance

    def __init__(self, service_name: str) -> None:
        if getattr(self, "_initialized", False):
            return
        self._initialized = True
        prefix = service_name.replace("-", "_")
        self.request_count = 0
        self.cache_hits_count = 0
        self.cache_misses_count = 0
        self.requests = Counter(
            f"{prefix}_requests_total",
            "Total number of requests",
            ["operation"],
        )
        self.failures = Counter(
            f"{prefix}_request_failures_total",
            "Total number of request failures",
            ["operation", "error"],
        )
        self.latency = Histogram(
            f"{prefix}_request_latency_seconds",
            "Request latency",
            ["operation"],
        )
        self.cache_hits = Counter(
            f"{prefix}_cache_hits_total",
            "Cache hits",
            [],
        )
        self.cache_misses = Counter(
            f"{prefix}_cache_misses_total",
            "Cache misses",
            [],
        )
        self.index_size = Gauge(
            f"{prefix}_index_size",
            "Current index size",
            [],
        )
        self.batch_size = Histogram(
            f"{prefix}_batch_size",
            "Batch request size",
            ["operation"],
        )
        self.operation_count = Counter(
            f"{prefix}_operations_total",
            "Total number of internal operations",
            ["operation"],
        )

    def inc_request(self, operation: str) -> None:
        self.request_count += 1
        self.requests.labels(operation=operation).inc()

    def inc_failure(self, operation: str, error: Optional[str] = None) -> None:
        self.failures.labels(operation=operation, error=error or "unknown").inc()

    def observe_latency(self, operation: str, duration: float) -> None:
        self.latency.labels(operation=operation).observe(duration)

    def time_operation(self, operation: str):
        import contextlib

        @contextlib.contextmanager
        def _timer():
            start = time.time()
            try:
                yield
            finally:
                self.observe_latency(operation, time.time() - start)

        return _timer()

    def inc_cache_hit(self) -> None:
        self.cache_hits_count += 1
        self.cache_hits.inc()

    def inc_cache_miss(self) -> None:
        self.cache_misses_count += 1
        self.cache_misses.inc()

    def set_index_size(self, size: int) -> None:
        self.index_size.set(size)

    def observe_batch_size(self, operation: str, size: int) -> None:
        self.batch_size.labels(operation=operation).observe(size)

    def inc_operation(self, operation: str) -> None:
        self.operation_count.labels(operation=operation).inc()
