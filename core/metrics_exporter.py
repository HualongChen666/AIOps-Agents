# -*- coding: utf-8 -*-
"""
Backwards-compatibility shim for the former ``MetricsExporter``.

The two home-grown exporters were merged into :mod:`core.prometheus_metrics`
(which now owns every ``aiops_*`` metric on the process default registry) so
that a single registry both receives production writes and is exposed over
HTTP.  This module is kept only so that existing imports keep working; it does
**not** define any metric of its own.
"""

from __future__ import annotations

from core.prometheus_metrics import PrometheusMetricsExporter as MetricsExporter
from core.prometheus_metrics import get_metrics_exporter

__all__ = ["MetricsExporter", "get_metrics_exporter"]
