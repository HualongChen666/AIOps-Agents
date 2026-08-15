# -*- coding: utf-8 -*-
"""Core service logic for the Log Aggregation microservice."""

from __future__ import annotations

from typing import Any, List, Optional

from .cache import CacheManager
from .config import settings
from .metrics import MetricsCollector
from .retry import RetryEngine
from ...engines.monitoring_provider import BaseObservabilityService

BASE_METHODS: List[str] = [
    "get_state",
    "backup_state",
    "restore_state",
    "get_stats",
    "list_methods",
]

OPERATIONS: List[str] = [
    "collect_logs_fluentd",
    "parse_logs",
    "filter_logs",
    "index_logs",
    "search_logs",
    "analyze_logs",
    "visualize_logs",
    "alert_on_logs",
    "write_log_docs",
    "test_and_optimize_log_aggregation",
]


class LogAggregationService(BaseObservabilityService):
    """Domain service for Log Aggregation."""

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


Service = LogAggregationService
