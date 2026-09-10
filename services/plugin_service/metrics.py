# -*- coding: utf-8 -*-
"""Prometheus metrics for the plugin microservice."""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

PLUGINS_CREATED = Counter(
    "plugin_service_plugins_created_total",
    "Total number of plugins created",
    ["plugin_type"],
)
PLUGINS_UPDATED = Counter(
    "plugin_service_plugins_updated_total",
    "Total number of plugin updates",
)
PLUGINS_DELETED = Counter(
    "plugin_service_plugins_deleted_total",
    "Total number of plugins deleted",
)
PLUGINS_REGISTERED = Gauge(
    "plugin_service_plugins_registered",
    "Number of plugins currently registered",
    ["status"],
)
PLUGIN_EXECUTIONS = Counter(
    "plugin_service_executions_total",
    "Total number of plugin executions",
    ["plugin", "outcome"],
)
PLUGIN_EXECUTION_DURATION = Histogram(
    "plugin_service_execution_duration_seconds",
    "Wall-clock duration of plugin executions",
    ["plugin"],
)
PLUGIN_CONFIG_MUTATIONS = Counter(
    "plugin_service_config_mutations_total",
    "Total number of plugin configuration mutations",
    ["operation"],
)
