# -*- coding: utf-8 -*-
"""Core service logic for the Metrics Monitoring microservice."""

from __future__ import annotations

from typing import List, Optional


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
    "collect_metrics_prometheus",
    "aggregate_metrics",
    "analyze_metrics",
    "visualize_metrics",
    "alert_on_metrics",
    "monitor_sli_slo",
    "monitor_performance",
    "monitor_resources",
    "write_metrics_docs",
    "test_and_optimize_metrics_monitoring",
]


class MetricsMonitoringService(BaseObservabilityService):
    """Domain service for Metrics Monitoring."""

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


Service = MetricsMonitoringService
