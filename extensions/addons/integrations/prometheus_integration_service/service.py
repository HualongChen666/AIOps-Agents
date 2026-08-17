# -*- coding: utf-8 -*-
"""Core service logic for the Prometheus Integration microservice."""

from __future__ import annotations

from typing import Any, List, Optional

from ...engines.monitoring_provider import BaseObservabilityService
from .cache import CacheManager
from .config import settings
from .lock import IdempotencyManager, LockManager
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
    "collect_prometheus_data",
    "promql_query",
    "rule_management",
    "alert_management",
    "service_discovery",
    "target_management",
    "integrate_monitoring_layer",
    "test_and_optimize_prometheus",
    "write_integration_docs",
    "implement_error_handling",
]


class PrometheusIntegrationService(BaseObservabilityService):
    """Domain service for Prometheus Integration."""

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


Service = PrometheusIntegrationService
