# -*- coding: utf-8 -*-
"""Core service logic for the Alert Rule microservice."""

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
    "design_alert_rule_system",
    "configure_system_resource_alerts",
    "configure_application_performance_alerts",
    "configure_business_metric_alerts",
    "configure_prometheus_alert_rules",
    "configure_alertmanager_routing",
    "configure_alert_suppression",
    "configure_alert_aggregation",
    "configure_slack_notifications",
    "configure_email_notifications",
    "configure_pagerduty_notifications",
    "configure_alert_escalation",
    "configure_alert_silencing",
    "validate_alert_rules",
    "test_alert_rules",
]


class AlertRuleService(BaseObservabilityService):
    """Domain service for Alert Rule."""

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


Service = AlertRuleService
