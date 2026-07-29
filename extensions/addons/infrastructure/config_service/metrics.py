# -*- coding: utf-8 -*-
"""Prometheus metrics for the configuration microservice."""

from __future__ import annotations

from prometheus_client import Counter, Gauge

CONFIGS_CREATED = Counter(
    "configs_created_total",
    "Total number of config values created",
    ["namespace"],
)
CONFIGS_UPDATED = Counter(
    "configs_updated_total",
    "Total number of config values updated",
    ["namespace"],
)
CONFIG_SNAPSHOTS = Counter(
    "config_snapshots_total",
    "Total number of config snapshots",
    ["namespace"],
)
CONFIG_HOT_UPDATES = Counter(
    "config_hot_updates_total",
    "Total number of config hot updates pushed",
    ["namespace"],
)
CONFIG_VERSIONS = Counter(
    "config_versions_total",
    "Total number of config version commits",
    ["namespace"],
)
CONFIG_SAGA_STATUS = Gauge(
    "config_saga_status",
    "Current saga transaction status (0=pending,1=success,2=failed,3=compensating)",
    ["saga_id"],
)
