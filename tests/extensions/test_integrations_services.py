# -*- coding: utf-8 -*-
"""Happy-path tests for integration addon Service.execute_operation methods."""

from unittest.mock import MagicMock

import pytest

from extensions.addons.integrations.datadog_integration_service.service import (
    Service as DatadogService,
)
from extensions.addons.integrations.elasticsearch_audit_service.service import (
    Service as ElasticsearchAuditService,
)
from extensions.addons.integrations.elk_stack_service.service import Service as ElkStackService
from extensions.addons.integrations.github_repository_service.service import (
    Service as GitHubRepositoryService,
)
from extensions.addons.integrations.grafana_integration_service.service import (
    Service as GrafanaIntegrationService,
)
from extensions.addons.integrations.kafka_event_service.service import Service as KafkaEventService
from extensions.addons.integrations.message_queue_service.service import (
    Service as MessageQueueService,
)
from extensions.addons.integrations.prometheus_integration_service.service import (
    Service as PrometheusIntegrationService,
)


@pytest.fixture(autouse=True)
def _disable_real_execution(monkeypatch):
    """Ensure all integrations stay in dry-run mode."""
    monkeypatch.setenv("INFRA_EXECUTE_ENABLED", "false")


def _observability_service(service_cls):
    """Instantiate an observability addon service without real Redis/DB."""
    return service_cls(metrics=MagicMock(), cache=MagicMock())


def _assert_base_result(result, name):
    assert isinstance(result, dict)
    assert result.get("success") is True
    assert result.get("status") == "ok"
    assert result.get("feature") == name
    assert "result" in result
    assert result["result"] is not None


def test_datadog_integration_service_execute_operation():
    service = _observability_service(DatadogService)
    result = service.execute_operation(
        "query_metrics",
        {"target": "https://api.datadoghq.com", "metric": "system.cpu.user"},
    )
    _assert_base_result(result, "query_metrics")
    assert isinstance(result["result"], dict)


def test_elasticsearch_audit_service_execute_operation():
    service = _observability_service(ElasticsearchAuditService)
    result = service.execute_operation(
        "audit_log_search",
        {"query": "error", "limit": 10},
    )
    _assert_base_result(result, "audit_log_search")
    assert isinstance(result["result"], dict)


def test_elk_stack_service_execute_operation():
    service = ElkStackService()
    result = service.execute_operation(
        "search_query",
        {
            "dry_run": True,
            "url": "https://elk.example.com/_search",
            "payload": {"query": {"match_all": {}}},
        },
    )
    assert isinstance(result, dict)
    assert result.get("success") is True
    assert result.get("status") == "dry_run"
    assert result.get("action") == "webhook_send"


def test_github_repository_service_execute_operation():
    service = GitHubRepositoryService()
    result = service.execute_operation(
        "configure_github_releases",
        {
            "dry_run": True,
            "owner": "example-org",
            "repo": "example-repo",
            "endpoint": "releases",
        },
    )
    assert isinstance(result, dict)
    assert result.get("success") is True
    assert result.get("status") == "dry_run"
    assert result.get("action") == "github_request"


def test_grafana_integration_service_execute_operation():
    service = _observability_service(GrafanaIntegrationService)
    result = service.execute_operation(
        "query_data",
        {"target": "http://grafana:3000", "metric": "up"},
    )
    _assert_base_result(result, "query_data")
    assert isinstance(result["result"], dict)


def test_kafka_event_service_execute_operation():
    service = KafkaEventService()
    result = service.execute_operation(
        "implement_kafka_producer",
        {
            "dry_run": True,
            "topic": "test-topic",
            "message": {"event": "test"},
            "bus": "kafka",
        },
    )
    assert isinstance(result, dict)
    assert result.get("success") is True
    assert result.get("status") == "dry_run"
    assert result.get("action") == "produce"


def test_message_queue_service_execute_operation():
    service = MessageQueueService()
    result = service.execute_operation(
        "implement_message_producer",
        {
            "dry_run": True,
            "queue": "test-queue",
            "message": {"payload": "hello"},
        },
    )
    assert isinstance(result, dict)
    assert result.get("success") is True
    assert result.get("status") == "dry_run"
    assert result.get("action") == "publish_queue"


def test_prometheus_integration_service_execute_operation():
    service = _observability_service(PrometheusIntegrationService)
    result = service.execute_operation(
        "service_discovery",
        {"source": "http://prometheus:9090"},
    )
    _assert_base_result(result, "service_discovery")
    assert isinstance(result["result"], dict)
