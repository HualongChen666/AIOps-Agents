# -*- coding: utf-8 -*-
"""
L1 Collection Layer - OpenTelemetry Enhanced Collection
Provides enhanced collectors with automatic OpenTelemetry and L4 Storage integration
"""

from .otel_collector import OTELEnhancedCollector, SystemMetricsCollector

__all__ = [
    "OTELEnhancedCollector",
    "SystemMetricsCollector",
]
