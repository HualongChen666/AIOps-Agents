# -*- coding: utf-8 -*-
"""Tests for the observability addon service wrappers."""

from unittest.mock import patch

import pytest

from extensions.addons.observability.metrics_monitoring_service.service import (
    Service as MetricsMonitoringService,
)
from extensions.addons.infrastructure.alert_rule_service.service import (
    Service as AlertRuleService,
)
from extensions.addons.infrastructure.performance_monitoring_service.service import (
    Service as PerformanceMonitoringService,
)
from extensions.addons.infrastructure.cloud_monitoring_service.service import (
    Service as CloudMonitoringService,
)
from extensions.addons.observability.log_aggregation_service.service import (
    Service as LogAggregationService,
)
from extensions.addons.observability.tracing_service.service import (
    Service as TracingService,
)
from extensions.addons.observability.distributed_tracing_service.service import (
    Service as DistributedTracingService,
)
from extensions.addons.observability.topology_service.service import (
    Service as TopologyService,
)
from extensions.addons.infrastructure.datacenter_visualization_service.service import (
    Service as DatacenterVisualizationService,
)
from extensions.addons.integrations.prometheus_integration_service.service import (
    Service as PrometheusIntegrationService,
)
from extensions.addons.integrations.grafana_integration_service.service import (
    Service as GrafanaIntegrationService,
)
from extensions.addons.integrations.datadog_integration_service.service import (
    Service as DatadogIntegrationService,
)
from extensions.addons.integrations.elasticsearch_audit_service.service import (
    Service as ElasticsearchAuditService,
)

ADDONS = [
    (
        MetricsMonitoringService,
        "collect_metrics_prometheus",
        {
            "target": "http://prometheus:9090",
            "metric": "up",
            "start": "2024-01-01T00:00:00Z",
            "end": "2024-01-01T01:00:00Z",
            "step": "15s",
        },
    ),
    (
        AlertRuleService,
        "configure_prometheus_alert_rules",
        {
            "rule_name": "HighCPU",
            "expr": "cpu > 80",
            "labels": {"severity": "warning"},
            "annotations": {"summary": "CPU high"},
        },
    ),
    (
        PerformanceMonitoringService,
        "collect_performance_metrics",
        {
            "target": "http://prometheus:9090",
            "metric": "avg(system_cpu)",
            "start": "2024-01-01T00:00:00Z",
            "end": "2024-01-01T01:00:00Z",
            "step": "15s",
        },
    ),
    (
        CloudMonitoringService,
        "unify_log_collection",
        {
            "query": "error",
            "start": "2024-01-01T00:00:00Z",
            "end": "2024-01-01T01:00:00Z",
            "limit": 10,
            "target": "http://loki:3100",
        },
    ),
    (
        LogAggregationService,
        "search_logs",
        {
            "query": "error",
            "start": "2024-01-01T00:00:00Z",
            "end": "2024-01-01T01:00:00Z",
            "limit": 10,
            "target": "http://loki:3100",
        },
    ),
    (
        TracingService,
        "configure_automatic_tracing",
        {
            "service": "frontend",
            "operation": "GET /",
            "start": "2024-01-01T00:00:00Z",
            "end": "2024-01-01T01:00:00Z",
            "limit": 10,
            "target": "http://jaeger:16686",
        },
    ),
    (
        DistributedTracingService,
        "collect_traces_jaeger",
        {
            "service": "frontend",
            "operation": "GET /",
            "start": "2024-01-01T00:00:00Z",
            "end": "2024-01-01T01:00:00Z",
            "limit": 10,
            "target": "http://jaeger:16686",
        },
    ),
    (
        TopologyService,
        "discover_topology",
        {
            "source": "http://prometheus:9090",
            "filters": {"namespace": "default"},
        },
    ),
    (
        DatacenterVisualizationService,
        "real_time_status_monitoring",
        {
            "target": "http://localhost:8080",
        },
    ),
    (
        PrometheusIntegrationService,
        "promql_query",
        {
            "target": "http://prometheus:9090",
            "metric": "up",
            "start": "2024-01-01T00:00:00Z",
            "end": "2024-01-01T01:00:00Z",
            "step": "15s",
        },
    ),
    (
        GrafanaIntegrationService,
        "query_data",
        {
            "target": "http://grafana:3000",
            "metric": "up",
            "start": "2024-01-01T00:00:00Z",
            "end": "2024-01-01T01:00:00Z",
            "step": "15s",
        },
    ),
    (
        DatadogIntegrationService,
        "query_metrics",
        {
            "target": "https://api.datadoghq.com",
            "metric": "avg:system.cpu{*}",
            "start": "1704067200",
            "end": "1704070800",
            "api_key": "test-key",
            "app_key": "test-app-key",
        },
    ),
    (
        ElasticsearchAuditService,
        "audit_log_search",
        {
            "query": "login",
            "start": "2024-01-01T00:00:00Z",
            "end": "2024-01-01T01:00:00Z",
            "limit": 10,
            "target": "http://elasticsearch:9200",
        },
    ),
]


@patch("extensions.addons.engines.monitoring_provider.subprocess.run")
@patch("extensions.addons.engines.monitoring_provider.requests.request")
def test_observability_addons_execute_operation(mock_request, mock_subprocess):
    """Each addon service can execute one operation and return a shaped response."""
    for cls, op, params in ADDONS:
        service = cls()
        result = service.execute_operation(op, params)
        assert isinstance(result, dict), f"{cls.__name__} must return a dict"
        assert "status" in result, f"{cls.__name__} result missing 'status'"
        assert result["status"] in ("ok", "error"), f"{cls.__name__} unexpected status"
        assert result.get("success") in (True, False)
        assert "result" in result

    # Default dry-run must not touch network or CLI.
    mock_request.assert_not_called()
    mock_subprocess.assert_not_called()
