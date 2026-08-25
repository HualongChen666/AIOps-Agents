# -*- coding: utf-8 -*-
"""Core service logic for the Cloud Monitoring microservice."""

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
    "integrate_aws_cloudwatch",
    "integrate_azure_monitor",
    "integrate_gcp_cloud_monitoring",
    "integrate_aliyun_monitoring",
    "integrate_tencent_cloud_monitoring",
    "unify_metric_collection",
    "unify_log_collection",
    "unify_alert_processing",
    "integrate_cloud_platform",
    "test_and_optimize_cloud_monitoring",
]


class CloudMonitoringService(BaseObservabilityService):
    """Domain service for Cloud Monitoring."""

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


Service = CloudMonitoringService
