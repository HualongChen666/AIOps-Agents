# -*- coding: utf-8 -*-
"""Alert provider adapters for normalizing external monitoring payloads."""

from __future__ import annotations

from .base import (
    AlertProvider,
    get_alert_provider,
    list_alert_providers,
    register_alert_provider,
)
from .prometheus import PrometheusAlertProvider

__all__ = [
    "AlertProvider",
    "get_alert_provider",
    "list_alert_providers",
    "register_alert_provider",
    "PrometheusAlertProvider",
]
