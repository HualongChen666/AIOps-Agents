# -*- coding: utf-8 -*-
"""Core service logic for the Distributed Tracing microservice."""

from __future__ import annotations

from typing import Any, List, Optional


from ...engines.monitoring_provider import BaseObservabilityService
from .cache import CacheManager
from .config import settings
from .metrics import MetricsCollector

BASE_METHODS: List[str] = [
    "get_state",
    "backup_state",
    "restore_state",
    "get_stats",
    "list_methods",
]

OPERATIONS: List[str] = [
    "collect_traces_jaeger",
    "store_traces",
    "analyze_traces",
    "visualize_traces",
    "search_traces",
    "alert_on_traces",
    "analyze_trace_performance",
    "identify_trace_bottlenecks",
    "write_tracing_docs",
    "test_and_optimize_distributed_tracing",
]


class DistributedTracingService(BaseObservabilityService):
    """Domain service for Distributed Tracing."""

    OPERATIONS = OPERATIONS
    BASE_METHODS = BASE_METHODS

    def __init__(
        self,
        redis_url: Optional[str] = None,
        metrics: Optional[MetricsCollector] = None,
        cache: Optional[CacheManager] = None,
    ) -> None:
        metrics = metrics or MetricsCollector(settings.service_name)
        cache = cache or CacheManager(redis_url or settings.redis_url, metrics)
        super().__init__(metrics=metrics, cache=cache, settings=settings)


Service = DistributedTracingService
