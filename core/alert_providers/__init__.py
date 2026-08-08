# -*- coding: utf-8 -*-
"""Alert provider adapters for normalizing external monitoring payloads."""

from __future__ import annotations

from .base import (
    AlertProvider,
    get_alert_provider,
    list_alert_providers,
    register_alert_provider,
)
from .cloudwatch import CloudWatchAlertProvider
from .datadog import DatadogAlertProvider
from .grafana import GrafanaAlertProvider
from .pagerduty import PagerDutyAlertProvider
from .prometheus import PrometheusAlertProvider
from .zabbix import ZabbixAlertProvider

__all__ = [
    "AlertProvider",
    "get_alert_provider",
    "list_alert_providers",
    "register_alert_provider",
    "PrometheusAlertProvider",
    "GrafanaAlertProvider",
    "DatadogAlertProvider",
    "ZabbixAlertProvider",
    "CloudWatchAlertProvider",
    "PagerDutyAlertProvider",
]
