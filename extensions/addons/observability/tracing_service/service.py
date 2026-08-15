# -*- coding: utf-8 -*-
"""Core service logic for the Tracing microservice."""

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
    "evaluate_tracing_backend",
    "select_tracing_backend",
    "install_jaeger",
    "install_zipkin",
    "install_skywalking",
    "configure_collector",
    "configure_storage",
    "install_opentelemetry_sdk",
    "configure_automatic_tracing",
    "configure_manual_tracing",
    "propagate_context",
    "add_span_tags",
    "add_baggage",
    "configure_sampling",
    "configure_span_filtering",
    "integrate_tracing_dashboard",
    "test_and_optimize_tracing",
]


class TracingService(BaseObservabilityService):
    """Domain service for Tracing."""

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


Service = TracingService
