# -*- coding: utf-8 -*-
"""Core service logic for the Datadog Integration microservice."""

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
    "integrate_datadog_api",
    "collect_metrics",
    "query_metrics",
    "collect_logs",
    "integrate_apm",
    "integrate_alerts",
    "integrate_dashboards",
    "integrate_slo",
    "integrate_unified_monitoring",
    "test_and_optimize_datadog",
    "write_integration_docs",
]


class DatadogIntegrationService(BaseObservabilityService):
    """Domain service for Datadog Integration."""

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


Service = DatadogIntegrationService
