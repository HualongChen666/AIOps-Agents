# -*- coding: utf-8 -*-
"""Core service logic for the Performance Monitoring microservice."""

from __future__ import annotations

from typing import Any, List, Optional

from ...engines.monitoring_provider import BaseObservabilityService
from .cache import CacheManager
from .config import settings
from .metrics import MetricsCollector
from .retry import RetryEngine

BASE_METHODS: List[str] = [
    "get_state",
    "backup_state",
    "restore_state",
    "get_stats",
    "list_methods",
]

OPERATIONS: List[str] = [
    "design_apm_framework",
    "integrate_skywalking",
    "collect_performance_metrics",
    "analyze_performance",
    "identify_bottlenecks",
    "generate_optimization_suggestions",
    "run_benchmark_tests",
    "detect_regressions",
    "write_performance_reports",
    "test_and_optimize_performance_monitoring",
]


class PerformanceMonitoringService(BaseObservabilityService):
    """Domain service for Performance Monitoring."""

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


Service = PerformanceMonitoringService
