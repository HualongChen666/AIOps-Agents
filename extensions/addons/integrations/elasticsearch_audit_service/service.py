# -*- coding: utf-8 -*-
"""Core service logic for the Elasticsearch Audit microservice."""

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
    "audit_log_storage",
    "audit_log_search",
    "audit_log_analysis",
    "audit_log_visualization",
    "audit_log_retention",
    "audit_log_export",
    "audit_log_encryption",
    "compliance_reporting",
    "integrate_audit_service",
    "test_and_optimize_elasticsearch_audit",
]


class ElasticsearchAuditService(BaseObservabilityService):
    """Domain service for Elasticsearch Audit."""

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


Service = ElasticsearchAuditService
