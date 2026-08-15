# -*- coding: utf-8 -*-
"""Happy-path tests for observability addon ``Service.execute_operation``."""

from types import SimpleNamespace

import pytest

from extensions.addons.observability.distributed_tracing_service.service import Service as DistributedTracingService
from extensions.addons.observability.log_aggregation_service.service import Service as LogAggregationService
from extensions.addons.observability.metrics_monitoring_service.service import Service as MetricsMonitoringService
from extensions.addons.observability.topology_service.service import Service as TopologyService
from extensions.addons.observability.tracing_service.service import Service as TracingService


class _FakeMetrics:
    """Minimal metrics collector that avoids real side effects."""

    request_count = 0
    cache_hits_count = 0
    cache_misses_count = 0

    def inc_request(self, operation: str) -> None:
        self.request_count += 1

    def inc_operation(self, operation: str) -> None:
        pass

    def inc_cache_hit(self) -> None:
        self.cache_hits_count += 1

    def inc_cache_miss(self) -> None:
        self.cache_misses_count += 1


_FAKE_METRICS = _FakeMetrics()
_FAKE_CACHE = SimpleNamespace()


class _FakeMonitoringProvider:
    """Stub monitoring provider used to avoid any real network/CLI calls."""

    def __init__(self, dry_run: bool = True) -> None:
        self.dry_run = dry_run

    def __getattr__(self, name: str):
        def _handler(**kwargs):
            return {"status": "ok", "data": kwargs or {}}

        return _handler


@pytest.fixture
def fake_monitoring_provider(monkeypatch):
    """Replace the real monitoring engine with a stub for the duration of a test."""
    monkeypatch.setenv("INFRA_EXECUTE_ENABLED", "false")
    monkeypatch.setattr(
        "extensions.addons.engines.monitoring_provider.MonitoringProvider",
        _FakeMonitoringProvider,
    )


def _make_service(cls):
    """Instantiate an observability service with fake metrics/cache."""
    return cls(metrics=_FAKE_METRICS, cache=_FAKE_CACHE)


def _assert_valid_result(result, feature):
    assert result is not None
    assert isinstance(result, dict)
    for key in ("success", "result", "status", "feature", "config", "message"):
        assert key in result
    assert result["success"] is True
    assert result["status"] == "ok"
    assert result["feature"] == feature
    assert result["result"] is not None
    assert isinstance(result["result"], (dict, list))


def test_distributed_tracing_collect_traces_jaeger(fake_monitoring_provider):
    service = _make_service(DistributedTracingService)
    result = service.execute_operation(
        "collect_traces_jaeger",
        {"service": "api", "limit": 10},
    )
    _assert_valid_result(result, "collect_traces_jaeger")


def test_log_aggregation_collect_logs_fluentd(fake_monitoring_provider):
    service = _make_service(LogAggregationService)
    result = service.execute_operation(
        "collect_logs_fluentd",
        {"query": "*"},
    )
    _assert_valid_result(result, "collect_logs_fluentd")


def test_metrics_monitoring_collect_metrics_prometheus(fake_monitoring_provider):
    service = _make_service(MetricsMonitoringService)
    result = service.execute_operation(
        "collect_metrics_prometheus",
        {"target": "http://prometheus:9090", "metric": "up"},
    )
    _assert_valid_result(result, "collect_metrics_prometheus")


def test_topology_discover_topology(fake_monitoring_provider):
    service = _make_service(TopologyService)
    result = service.execute_operation(
        "discover_topology",
        {"source": "cmdb"},
    )
    _assert_valid_result(result, "discover_topology")


def test_tracing_install_jaeger(fake_monitoring_provider):
    service = _make_service(TracingService)
    result = service.execute_operation(
        "install_jaeger",
        {"service": "api"},
    )
    _assert_valid_result(result, "install_jaeger")
