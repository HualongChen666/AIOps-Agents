# -*- coding: utf-8 -*-
"""Core service logic for the Datacenter Visualization microservice."""

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
    "design_physical_model",
    "three_d_visualization",
    "rack_u_management",
    "real_time_status_monitoring",
    "data_statistics_analysis",
    "access_control",
    "testing_and_optimization",
]


class DatacenterVisualizationService(BaseObservabilityService):
    """Domain service for Datacenter Visualization."""

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


Service = DatacenterVisualizationService
