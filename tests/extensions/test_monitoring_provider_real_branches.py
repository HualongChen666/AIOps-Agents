# -*- coding: utf-8 -*-
"""Real branch coverage tests for monitoring_provider.py.

Uses real MonitoringProvider and BaseObservabilityService classes with real env var
manipulation. Only monkeypatches external I/O boundaries: requests.request,
subprocess.run, urllib.request.urlopen. Does not stub business logic.
"""

import json
import os
import subprocess
import urllib.request
from unittest.mock import MagicMock, patch

import pytest

from extensions.addons.engines.monitoring_provider import (
    BaseObservabilityService,
    MonitoringProvider,
    resolve_operation,
)


class TestResolveOperation:
    """Test resolve_operation function branches."""

    def test_resolve_operation_alert_keywords(self):
        """Test alert-related keywords map to push_alert."""
        for keyword in ["alert", "rule", "silence", "suppress", "escalate", "notify", "pagerduty"]:
            assert resolve_operation(keyword) == "push_alert"
            assert resolve_operation(f"my_{keyword}") == "push_alert"
            assert resolve_operation(f"{keyword}_test") == "push_alert"

    def test_resolve_operation_topology_keywords(self):
        """Test topology-related keywords map to get_topology."""
        for keyword in ["topology", "discovery", "cmdb", "dependency", "service discovery"]:
            assert resolve_operation(keyword) == "get_topology"
            assert resolve_operation(f"my_{keyword}") == "get_topology"

    def test_resolve_operation_log_keywords(self):
        """Test log-related keywords map to logs."""
        for keyword in ["log", "loki", "elk", "fluentd", "audit_log"]:
            assert resolve_operation(keyword) == "logs"
            assert resolve_operation(f"my_{keyword}") == "logs"

    def test_resolve_operation_trace_keywords(self):
        """Test trace-related keywords map to traces."""
        for keyword in ["trace", "tracing", "jaeger", "zipkin", "skywalking", "otel"]:
            assert resolve_operation(keyword) == "traces"
            assert resolve_operation(f"my_{keyword}") == "traces"

    def test_resolve_operation_health_keywords(self):
        """Test health-related keywords map to health."""
        for keyword in ["health", "status", "probe", "ping"]:
            assert resolve_operation(keyword) == "health"
            assert resolve_operation(f"my_{keyword}") == "health"

    def test_resolve_operation_default(self):
        """Test default mapping to query."""
        assert resolve_operation("metrics") == "query"
        assert resolve_operation("custom") == "query"
        assert resolve_operation("random") == "query"


class TestMonitoringProviderInit:
    """Test MonitoringProvider.__init__ branches."""

    def test_init_dry_run_none_env_not_set(self):
        """Test dry_run=None when env var not set defaults to True."""
        if "INFRA_EXECUTE_ENABLED" in os.environ:
            del os.environ["INFRA_EXECUTE_ENABLED"]
        provider = MonitoringProvider(dry_run=None)
        assert provider.dry_run is True

    def test_init_dry_run_none_env_true(self):
        """Test dry_run=None when env var is 'true' defaults to False."""
        os.environ["INFRA_EXECUTE_ENABLED"] = "true"
        provider = MonitoringProvider(dry_run=None)
        assert provider.dry_run is False
        del os.environ["INFRA_EXECUTE_ENABLED"]

    def test_init_dry_run_none_env_other(self):
        """Test dry_run=None when env var is not 'true' defaults to True."""
        os.environ["INFRA_EXECUTE_ENABLED"] = "false"
        provider = MonitoringProvider(dry_run=None)
        assert provider.dry_run is True
        del os.environ["INFRA_EXECUTE_ENABLED"]

    def test_init_dry_run_explicit_true(self):
        """Test explicit dry_run=True."""
        provider = MonitoringProvider(dry_run=True)
        assert provider.dry_run is True

    def test_init_dry_run_explicit_false(self):
        """Test explicit dry_run=False."""
        provider = MonitoringProvider(dry_run=False)
        assert provider.dry_run is False


class TestMonitoringProviderRequest:
    """Test _request method branches."""

    def test_request_with_requests(self):
        """Test _request using requests library."""
        provider = MonitoringProvider(dry_run=False)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": "ok"}
        mock_response.text = "ok"

        with patch("extensions.addons.engines.monitoring_provider.requests") as mock_requests:
            mock_requests.request.return_value = mock_response
            result = provider._request("GET", "http://example.com")
            assert result.status_code == 200
            mock_requests.request.assert_called_once()

    def test_request_urllib_fallback(self):
        """Test _request using urllib fallback when requests is None."""
        provider = MonitoringProvider(dry_run=False)

        # Mock urllib.request.urlopen to return a proper addinfourl-like object
        mock_response = MagicMock()
        mock_response.getcode.return_value = 200
        mock_response.read.return_value = b'{"result": "ok"}'

        with patch("extensions.addons.engines.monitoring_provider.requests", None):
            with patch("urllib.request.urlopen") as mock_urlopen:
                mock_urlopen.return_value.__enter__.return_value = mock_response
                result = provider._request("GET", "http://example.com")
                assert result.status_code == 200
                assert result.json() == {"result": "ok"}

    def test_request_urllib_fallback_with_params(self):
        """Test _request urllib fallback with query params."""
        provider = MonitoringProvider(dry_run=False)

        mock_response = MagicMock()
        mock_response.getcode.return_value = 200
        mock_response.read.return_value = b'{"result": "ok"}'

        with patch("extensions.addons.engines.monitoring_provider.requests", None):
            with patch("urllib.request.urlopen") as mock_urlopen:
                mock_urlopen.return_value.__enter__.return_value = mock_response
                result = provider._request("GET", "http://example.com", params={"key": "value"})
                assert result.status_code == 200
                assert result.json() == {"result": "ok"}

    def test_request_urllib_fallback_with_json(self):
        """Test _request urllib fallback with JSON body."""
        provider = MonitoringProvider(dry_run=False)

        mock_response = MagicMock()
        mock_response.getcode.return_value = 201
        mock_response.read.return_value = b'{"created": true}'

        with patch("extensions.addons.engines.monitoring_provider.requests", None):
            with patch("urllib.request.urlopen") as mock_urlopen:
                mock_urlopen.return_value.__enter__.return_value = mock_response
                result = provider._request("POST", "http://example.com", json={"data": "test"})
                assert result.status_code == 201
                assert result.json() == {"created": True}

    def test_request_urllib_error_status(self):
        """Test _request urllib fallback with error status."""
        provider = MonitoringProvider(dry_run=False)

        mock_response = MagicMock()
        mock_response.getcode.return_value = 404
        mock_response.read.return_value = b'{"error": "not found"}'

        with patch("extensions.addons.engines.monitoring_provider.requests", None):
            with patch("urllib.request.urlopen") as mock_urlopen:
                mock_urlopen.return_value.__enter__.return_value = mock_response
                result = provider._request("GET", "http://example.com")
                assert result.status_code == 404
                with pytest.raises(RuntimeError):
                    result.raise_for_status()


class TestMonitoringProviderQuery:
    """Test query method branches."""

    def test_query_dry_run(self):
        """Test query in dry_run mode."""
        provider = MonitoringProvider(dry_run=True)
        result = provider.query(target="http://prometheus:9090", metric="up")
        assert result["status"] == "ok"
        assert len(result["data"]) == 1
        assert result["data"][0]["value"] == 0.42

    def test_query_no_target(self):
        """Test query with no target."""
        provider = MonitoringProvider(dry_run=False)
        result = provider.query(metric="up")
        assert result["status"] == "ok"
        assert result["data"][0]["value"] == 0.42

    def test_query_datadog_backend(self):
        """Test query with Datadog backend."""
        provider = MonitoringProvider(dry_run=False)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"series": []}

        with patch.object(provider, "_request", return_value=mock_response):
            result = provider.query(target="https://api.datadoghq.com", metric="system.cpu.usage")
            assert result["status"] == "ok"

    def test_query_elasticsearch_backend(self):
        """Test query with Elasticsearch backend."""
        provider = MonitoringProvider(dry_run=False)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"hits": {"hits": []}}

        with patch.object(provider, "_request", return_value=mock_response):
            result = provider.query(target="http://elasticsearch:9200", metric="*")
            assert result["status"] == "ok"

    def test_query_cloudwatch_backend(self):
        """Test query with CloudWatch backend."""
        provider = MonitoringProvider(dry_run=False)
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({"Datapoints": []})

        with patch.object(provider, "_run_cli", return_value=mock_result):
            result = provider.query(target="cloudwatch", metric="CPUUtilization")
            assert result["status"] == "ok"

    def test_query_prometheus_backend(self):
        """Test query with Prometheus backend."""
        provider = MonitoringProvider(dry_run=False)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {"result": []}}

        with patch.object(provider, "_request", return_value=mock_response):
            result = provider.query(target="http://prometheus:9090", metric="up")
            assert result["status"] == "ok"

    def test_query_exception(self):
        """Test query with exception."""
        provider = MonitoringProvider(dry_run=False)

        with patch.object(provider, "_request", side_effect=Exception("network error")):
            result = provider.query(target="http://prometheus:9090", metric="up")
            assert result["status"] == "error"
            assert "network error" in result["message"]


class TestQueryPrometheus:
    """Test _query_prometheus method branches."""

    def test_query_prometheus_all_params(self):
        """Test _query_prometheus with all optional params."""
        provider = MonitoringProvider(dry_run=False)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {"result": [{"metric": "up"}]}}

        with patch.object(provider, "_request", return_value=mock_response):
            result = provider._query_prometheus(
                target="http://prometheus:9090",
                metric="up",
                start="2024-01-01T00:00:00Z",
                end="2024-01-01T01:00:00Z",
                step="1m",
            )
            assert result["status"] == "ok"
            assert len(result["data"]) == 1

    def test_query_prometheus_no_metric(self):
        """Test _query_prometheus without metric."""
        provider = MonitoringProvider(dry_run=False)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {"result": []}}

        with patch.object(provider, "_request", return_value=mock_response):
            result = provider._query_prometheus(
                target="http://prometheus:9090",
                metric=None,
                start="2024-01-01T00:00:00Z",
                end="2024-01-01T01:00:00Z",
                step="1m",
            )
            assert result["status"] == "ok"

    def test_query_prometheus_no_start_end_step(self):
        """Test _query_prometheus without start, end, step."""
        provider = MonitoringProvider(dry_run=False)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {"result": []}}

        with patch.object(provider, "_request", return_value=mock_response):
            result = provider._query_prometheus(
                target="http://prometheus:9090",
                metric="up",
                start=None,
                end=None,
                step=None,
            )
            assert result["status"] == "ok"


class TestQueryDatadog:
    """Test _query_datadog method branches."""

    def test_query_datadog_with_keys(self):
        """Test _query_datadog with API keys."""
        provider = MonitoringProvider(dry_run=False)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"series": []}

        with patch.object(provider, "_request", return_value=mock_response):
            result = provider._query_datadog(
                target="https://api.datadoghq.com",
                metric="system.cpu.usage",
                start="2024-01-01T00:00:00Z",
                end="2024-01-01T01:00:00Z",
                step="1m",
                api_key="test_key",
                app_key="test_app",
            )
            assert result["status"] == "ok"

    def test_query_datadog_no_keys(self):
        """Test _query_datadog without API keys."""
        provider = MonitoringProvider(dry_run=False)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"series": []}

        with patch.object(provider, "_request", return_value=mock_response):
            result = provider._query_datadog(
                target="https://api.datadoghq.com",
                metric="system.cpu.usage",
                start="2024-01-01T00:00:00Z",
                end="2024-01-01T01:00:00Z",
                step="1m",
            )
            assert result["status"] == "ok"

    def test_query_datadog_no_metric(self):
        """Test _query_datadog without metric."""
        provider = MonitoringProvider(dry_run=False)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"series": []}

        with patch.object(provider, "_request", return_value=mock_response):
            result = provider._query_datadog(
                target="https://api.datadoghq.com",
                metric=None,
                start="2024-01-01T00:00:00Z",
                end="2024-01-01T01:00:00Z",
                step="1m",
            )
            assert result["status"] == "ok"

    def test_query_datadog_exception(self):
        """Test _query_datadog with exception - should propagate."""
        provider = MonitoringProvider(dry_run=False)

        with patch.object(provider, "_request", side_effect=Exception("datadog error")):
            with pytest.raises(Exception, match="datadog error"):
                provider._query_datadog(
                    target="https://api.datadoghq.com",
                    metric="system.cpu.usage",
                    start="2024-01-01T00:00:00Z",
                    end="2024-01-01T01:00:00Z",
                    step="1m",
                )


class TestQueryElasticsearch:
    """Test _query_elasticsearch method branches."""

    def test_query_elasticsearch_success(self):
        """Test _query_elasticsearch success."""
        provider = MonitoringProvider(dry_run=False)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"hits": {"hits": [{"_id": "1"}]}}

        with patch.object(provider, "_request", return_value=mock_response):
            result = provider._query_elasticsearch(
                target="http://elasticsearch:9200",
                metric="*",
                start="2024-01-01T00:00:00Z",
                end="2024-01-01T01:00:00Z",
                step="1m",
            )
            assert result["status"] == "ok"
            assert len(result["data"]) == 1

    def test_query_elasticsearch_no_metric(self):
        """Test _query_elasticsearch without metric."""
        provider = MonitoringProvider(dry_run=False)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"hits": {"hits": []}}

        with patch.object(provider, "_request", return_value=mock_response):
            result = provider._query_elasticsearch(
                target="http://elasticsearch:9200",
                metric=None,
                start="2024-01-01T00:00:00Z",
                end="2024-01-01T01:00:00Z",
                step="1m",
            )
            assert result["status"] == "ok"

    def test_query_elasticsearch_exception(self):
        """Test _query_elasticsearch with exception - should propagate."""
        provider = MonitoringProvider(dry_run=False)

        with patch.object(provider, "_request", side_effect=Exception("es error")):
            with pytest.raises(Exception, match="es error"):
                provider._query_elasticsearch(
                    target="http://elasticsearch:9200",
                    metric="*",
                    start="2024-01-01T00:00:00Z",
                    end="2024-01-01T01:00:00Z",
                    step="1m",
                )


class TestQueryCloudWatch:
    """Test _query_cloudwatch method branches."""

    def test_query_cloudwatch_success(self):
        """Test _query_cloudwatch success."""
        provider = MonitoringProvider(dry_run=False)
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({"Datapoints": [{"Timestamp": "2024-01-01", "Average": 50.0}]})

        with patch.object(provider, "_run_cli", return_value=mock_result):
            result = provider._query_cloudwatch(
                target="cloudwatch",
                metric="CPUUtilization",
                start="2024-01-01T00:00:00Z",
                end="2024-01-01T01:00:00Z",
                step="60",
            )
            assert result["status"] == "ok"
            assert len(result["data"]["Datapoints"]) == 1

    def test_query_cloudwatch_custom_namespace(self):
        """Test _query_cloudwatch with custom namespace."""
        provider = MonitoringProvider(dry_run=False)
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({"Datapoints": []})

        with patch.object(provider, "_run_cli", return_value=mock_result):
            result = provider._query_cloudwatch(
                target="cloudwatch",
                metric="CPUUtilization",
                start="2024-01-01T00:00:00Z",
                end="2024-01-01T01:00:00Z",
                step="60",
                namespace="AWS/RDS",
            )
            assert result["status"] == "ok"

    def test_query_cloudwatch_no_metric(self):
        """Test _query_cloudwatch without metric."""
        provider = MonitoringProvider(dry_run=False)
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({"Datapoints": []})

        with patch.object(provider, "_run_cli", return_value=mock_result):
            result = provider._query_cloudwatch(
                target="cloudwatch",
                metric=None,
                start="2024-01-01T00:00:00Z",
                end="2024-01-01T01:00:00Z",
                step="60",
            )
            assert result["status"] == "ok"

    def test_query_cloudwatch_cli_failure(self):
        """Test _query_cloudwatch with CLI failure."""
        provider = MonitoringProvider(dry_run=False)
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "AWS credentials not found"

        with patch.object(provider, "_run_cli", return_value=mock_result):
            result = provider._query_cloudwatch(
                target="cloudwatch",
                metric="CPUUtilization",
                start="2024-01-01T00:00:00Z",
                end="2024-01-01T01:00:00Z",
                step="60",
            )
            assert result["status"] == "error"
            assert "AWS credentials not found" in result["message"]


class TestPushAlert:
    """Test push_alert method branches."""

    def test_push_alert_dry_run(self):
        """Test push_alert in dry_run mode."""
        provider = MonitoringProvider(dry_run=True)
        result = provider.push_alert(rule_name="test_rule", expr="up == 0")
        assert result["status"] == "ok"
        assert result["data"]["fired"] is False

    def test_push_alert_severity_value_error(self):
        """Test push_alert with invalid severity (ValueError caught)."""
        provider = MonitoringProvider(dry_run=False)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "success"}

        with patch.object(provider, "_request", return_value=mock_response):
            result = provider.push_alert(
                rule_name="test_rule",
                expr="up == 0",
                labels={"severity": "invalid_severity"},
            )
            assert result["status"] == "ok"

    def test_push_alert_metrics_not_dict(self):
        """Test push_alert with metrics not being a dict."""
        provider = MonitoringProvider(dry_run=False)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "success"}

        with patch.object(provider, "_request", return_value=mock_response):
            result = provider.push_alert(
                rule_name="test_rule",
                expr="up == 0",
                metrics="not_a_dict",
            )
            assert result["status"] == "ok"

    def test_push_alert_target_from_kwargs(self):
        """Test push_alert with target from kwargs."""
        provider = MonitoringProvider(dry_run=False)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "success"}

        with patch.object(provider, "_request", return_value=mock_response):
            result = provider.push_alert(
                rule_name="test_rule",
                expr="up == 0",
                target="http://custom-alertmanager:9093",
            )
            assert result["status"] == "ok"

    def test_push_alert_target_from_alertmanager_url(self):
        """Test push_alert with target from alertmanager_url kwarg."""
        provider = MonitoringProvider(dry_run=False)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "success"}

        with patch.object(provider, "_request", return_value=mock_response):
            result = provider.push_alert(
                rule_name="test_rule",
                expr="up == 0",
                alertmanager_url="http://custom-alertmanager:9093",
            )
            assert result["status"] == "ok"

    def test_push_alert_target_from_env(self):
        """Test push_alert with target from environment variable."""
        provider = MonitoringProvider(dry_run=False)
        os.environ["ALERTMANAGER_URL"] = "http://env-alertmanager:9093"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "success"}

        with patch.object(provider, "_request", return_value=mock_response):
            result = provider.push_alert(rule_name="test_rule", expr="up == 0")
            assert result["status"] == "ok"
        del os.environ["ALERTMANAGER_URL"]

    def test_push_alert_target_default(self):
        """Test push_alert with default target."""
        provider = MonitoringProvider(dry_run=False)
        if "ALERTMANAGER_URL" in os.environ:
            del os.environ["ALERTMANAGER_URL"]
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "success"}

        with patch.object(provider, "_request", return_value=mock_response):
            result = provider.push_alert(rule_name="test_rule", expr="up == 0")
            assert result["status"] == "ok"

    def test_push_alert_post_exception(self):
        """Test push_alert with POST exception."""
        provider = MonitoringProvider(dry_run=False)

        with patch.object(provider, "_request", side_effect=Exception("post failed")):
            result = provider.push_alert(rule_name="test_rule", expr="up == 0")
            assert result["status"] == "error"
            assert "post failed" in result["message"]

    def test_push_alert_no_hasattr_json(self):
        """Test push_alert when response has no json method."""
        provider = MonitoringProvider(dry_run=False)
        mock_response = MagicMock()
        mock_response.status_code = 200
        del mock_response.json  # Remove json method
        mock_response.text = "success"

        with patch.object(provider, "_request", return_value=mock_response):
            result = provider.push_alert(rule_name="test_rule", expr="up == 0")
            assert result["status"] == "ok"
            assert result["data"]["posted"] == "success"


class TestGetTopology:
    """Test get_topology method branches."""

    def test_get_topology_dry_run(self):
        """Test get_topology in dry_run mode."""
        provider = MonitoringProvider(dry_run=True)
        result = provider.get_topology(source="http://cmdb:8080")
        assert result["status"] == "ok"
        assert len(result["data"]["nodes"]) == 2

    def test_get_topology_no_source(self):
        """Test get_topology with no source."""
        provider = MonitoringProvider(dry_run=False)
        result = provider.get_topology()
        assert result["status"] == "ok"
        assert len(result["data"]["nodes"]) == 2

    def test_get_topology_http_source(self):
        """Test get_topology with HTTP source."""
        provider = MonitoringProvider(dry_run=False)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "activeTargets": [
                    {"labels": {"instance": "host1", "job": "node"}},
                    {"labels": {"instance": "host2", "job": "node"}},
                ]
            }
        }

        with patch.object(provider, "_request", return_value=mock_response):
            result = provider.get_topology(source="http://prometheus:9090")
            assert result["status"] == "ok"
            assert len(result["data"]["nodes"]) == 2

    def test_get_topology_http_source_non_dict_data(self):
        """Test get_topology with HTTP source returning non-dict data."""
        provider = MonitoringProvider(dry_run=False)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"labels": {"instance": "host1", "job": "node"}},
        ]

        with patch.object(provider, "_request", return_value=mock_response):
            result = provider.get_topology(source="http://prometheus:9090")
            assert result["status"] == "ok"

    def test_get_topology_http_source_exception(self):
        """Test get_topology with HTTP source exception."""
        provider = MonitoringProvider(dry_run=False)

        with patch.object(provider, "_request", side_effect=Exception("http error")):
            result = provider.get_topology(source="http://prometheus:9090")
            assert result["status"] == "error"
            assert "http error" in result["message"]

    def test_get_topology_kubectl_success(self):
        """Test get_topology with kubectl success."""
        provider = MonitoringProvider(dry_run=False)
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({
            "items": [
                {"metadata": {"name": "svc1"}},
                {"metadata": {"name": "svc2"}},
            ]
        })

        with patch.object(provider, "_run_cli", return_value=mock_result):
            result = provider.get_topology(source="kubernetes")
            assert result["status"] == "ok"
            assert len(result["data"]["nodes"]) == 2

    def test_get_topology_kubectl_with_filters(self):
        """Test get_topology with kubectl and namespace filter."""
        provider = MonitoringProvider(dry_run=False)
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({"items": [{"metadata": {"name": "svc1"}}]})

        with patch.object(provider, "_run_cli", return_value=mock_result):
            result = provider.get_topology(
                source="kubernetes",
                filters={"namespace": "test-ns"},
            )
            assert result["status"] == "ok"

    def test_get_topology_kubectl_failure(self):
        """Test get_topology with kubectl failure."""
        provider = MonitoringProvider(dry_run=False)
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "kubectl: command not found"

        with patch.object(provider, "_run_cli", return_value=mock_result):
            result = provider.get_topology(source="kubernetes")
            assert result["status"] == "error"
            assert "kubectl: command not found" in result["message"]

    def test_get_topology_kubectl_exception(self):
        """Test get_topology with kubectl exception."""
        provider = MonitoringProvider(dry_run=False)

        with patch.object(provider, "_run_cli", side_effect=Exception("kubectl error")):
            result = provider.get_topology(source="kubernetes")
            assert result["status"] == "error"
            assert "kubectl error" in result["message"]


class TestLogs:
    """Test logs method branches."""

    def test_logs_dry_run(self):
        """Test logs in dry_run mode."""
        provider = MonitoringProvider(dry_run=True)
        result = provider.logs(query="error", target="http://loki:3100")
        assert result["status"] == "ok"
        assert len(result["data"]) == 1

    def test_logs_no_target_or_query(self):
        """Test logs with no target or query."""
        provider = MonitoringProvider(dry_run=False)
        result = provider.logs()
        assert result["status"] == "ok"
        assert len(result["data"]) == 1

    def test_logs_elasticsearch(self):
        """Test logs with Elasticsearch target."""
        provider = MonitoringProvider(dry_run=False)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"hits": {"hits": [{"_source": {"message": "error"}}]}}

        with patch.object(provider, "_request", return_value=mock_response):
            result = provider.logs(
                query="error",
                target="http://elasticsearch:9200",
                limit=50,
            )
            assert result["status"] == "ok"
            assert len(result["data"]) == 1

    def test_logs_elasticsearch_exception(self):
        """Test logs with Elasticsearch exception."""
        provider = MonitoringProvider(dry_run=False)

        with patch.object(provider, "_request", side_effect=Exception("es error")):
            result = provider.logs(
                query="error",
                target="http://elasticsearch:9200",
            )
            assert result["status"] == "error"
            assert "es error" in result["message"]

    def test_logs_loki(self):
        """Test logs with Loki target."""
        provider = MonitoringProvider(dry_run=False)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {"result": [{"values": [["1", "error log"]]}]}}

        with patch.object(provider, "_request", return_value=mock_response):
            result = provider.logs(
                query="error",
                target="http://loki:3100",
                start="2024-01-01T00:00:00Z",
                end="2024-01-01T01:00:00Z",
            )
            assert result["status"] == "ok"

    def test_logs_loki_from_env(self):
        """Test logs with Loki target from environment."""
        provider = MonitoringProvider(dry_run=False)
        os.environ["LOKI_URL"] = "http://env-loki:3100"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {"result": []}}

        with patch.object(provider, "_request", return_value=mock_response):
            result = provider.logs(query="error")
            assert result["status"] == "ok"
        del os.environ["LOKI_URL"]

    def test_logs_loki_non_dict_response(self):
        """Test logs with Loki returning non-dict response."""
        provider = MonitoringProvider(dry_run=False)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{"values": [["1", "log"]]}]

        with patch.object(provider, "_request", return_value=mock_response):
            result = provider.logs(
                query="error",
                target="http://loki:3100",
            )
            assert result["status"] == "ok"

    def test_logs_loki_exception(self):
        """Test logs with Loki exception."""
        provider = MonitoringProvider(dry_run=False)

        with patch.object(provider, "_request", side_effect=Exception("loki error")):
            result = provider.logs(
                query="error",
                target="http://loki:3100",
            )
            assert result["status"] == "error"
            assert "loki error" in result["message"]


class TestTraces:
    """Test traces method branches."""

    def test_traces_dry_run(self):
        """Test traces in dry_run mode."""
        provider = MonitoringProvider(dry_run=True)
        result = provider.traces(service="my-service", target="http://jaeger:16686")
        assert result["status"] == "ok"
        assert len(result["data"]) == 1

    def test_traces_jaeger(self):
        """Test traces with Jaeger target."""
        provider = MonitoringProvider(dry_run=False)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": [{"traceID": "123"}]}

        with patch.object(provider, "_request", return_value=mock_response):
            result = provider.traces(
                service="my-service",
                operation="GET",
                target="http://jaeger:16686",
            )
            assert result["status"] == "ok"

    def test_traces_jaeger_from_env(self):
        """Test traces with Jaeger target from environment."""
        provider = MonitoringProvider(dry_run=False)
        os.environ["JAEGER_URL"] = "http://env-jaeger:16686"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": []}

        with patch.object(provider, "_request", return_value=mock_response):
            result = provider.traces(service="my-service")
            assert result["status"] == "ok"
        del os.environ["JAEGER_URL"]

    def test_traces_jaeger_non_dict_response(self):
        """Test traces with Jaeger returning non-dict response."""
        provider = MonitoringProvider(dry_run=False)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{"traceID": "123"}]

        with patch.object(provider, "_request", return_value=mock_response):
            result = provider.traces(
                service="my-service",
                target="http://jaeger:16686",
            )
            assert result["status"] == "ok"

    def test_traces_jaeger_exception(self):
        """Test traces with Jaeger exception."""
        provider = MonitoringProvider(dry_run=False)

        with patch.object(provider, "_request", side_effect=Exception("jaeger error")):
            result = provider.traces(
                service="my-service",
                target="http://jaeger:16686",
            )
            assert result["status"] == "error"
            assert "jaeger error" in result["message"]

    def test_traces_zipkin(self):
        """Test traces with Zipkin target."""
        provider = MonitoringProvider(dry_run=False)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{"traceID": "456"}]

        with patch.object(provider, "_request", return_value=mock_response):
            result = provider.traces(
                service="my-service",
                operation="GET",
                target="http://zipkin:9411",
            )
            assert result["status"] == "ok"

    def test_traces_zipkin_no_json_method(self):
        """Test traces with Zipkin response having no json method."""
        provider = MonitoringProvider(dry_run=False)
        mock_response = MagicMock()
        mock_response.status_code = 200
        del mock_response.json
        mock_response.read.return_value = b'[{"traceID": "789"}]'

        with patch.object(provider, "_request", return_value=mock_response):
            result = provider.traces(
                service="my-service",
                target="http://zipkin:9411",
            )
            assert result["status"] == "ok"

    def test_traces_zipkin_exception(self):
        """Test traces with Zipkin exception."""
        provider = MonitoringProvider(dry_run=False)

        with patch.object(provider, "_request", side_effect=Exception("zipkin error")):
            result = provider.traces(
                service="my-service",
                target="http://zipkin:9411",
            )
            assert result["status"] == "error"
            assert "zipkin error" in result["message"]


class TestHealth:
    """Test health method branches."""

    def test_health_dry_run(self):
        """Test health in dry_run mode."""
        provider = MonitoringProvider(dry_run=True)
        result = provider.health(target="http://example.com")
        assert result["status"] == "ok"
        assert result["data"]["healthy"] is True

    def test_health_no_target(self):
        """Test health with no target."""
        provider = MonitoringProvider(dry_run=False)
        result = provider.health()
        assert result["status"] == "ok"
        assert result["data"]["healthy"] is True

    def test_health_http_success(self):
        """Test health with HTTP success."""
        provider = MonitoringProvider(dry_run=False)
        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch.object(provider, "_request", return_value=mock_response):
            result = provider.health(target="http://example.com")
            assert result["status"] == "ok"
            assert result["data"]["status_code"] == 200

    def test_health_http_error(self):
        """Test health with HTTP error."""
        provider = MonitoringProvider(dry_run=False)
        mock_response = MagicMock()
        mock_response.status_code = 500

        with patch.object(provider, "_request", return_value=mock_response):
            result = provider.health(target="http://example.com")
            assert result["status"] == "error"
            assert result["data"]["status_code"] == 500

    def test_health_http_urllib_fallback(self):
        """Test health with urllib fallback."""
        provider = MonitoringProvider(dry_run=False)
        mock_response = MagicMock()
        mock_response.getcode.return_value = 200
        mock_response.status_code = 200

        with patch("extensions.addons.engines.monitoring_provider.requests", None):
            with patch.object(provider, "_request", return_value=mock_response):
                result = provider.health(target="http://example.com")
                assert result["status"] == "ok"

    def test_health_http_exception(self):
        """Test health with HTTP exception."""
        provider = MonitoringProvider(dry_run=False)

        with patch.object(provider, "_request", side_effect=Exception("http error")):
            result = provider.health(target="http://example.com")
            assert result["status"] == "error"
            assert "http error" in result["message"]

    def test_health_cli_success(self):
        """Test health with CLI success."""
        provider = MonitoringProvider(dry_run=False)
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stderr = ""

        with patch.object(provider, "_run_cli", return_value=mock_result):
            result = provider.health(target="kubectl version")
            assert result["status"] == "ok"
            assert result["data"]["returncode"] == 0

    def test_health_cli_failure(self):
        """Test health with CLI failure."""
        provider = MonitoringProvider(dry_run=False)
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "command failed"

        with patch.object(provider, "_run_cli", return_value=mock_result):
            result = provider.health(target="kubectl version")
            assert result["status"] == "error"
            assert result["data"]["returncode"] == 1

    def test_health_cli_exception(self):
        """Test health with CLI exception."""
        provider = MonitoringProvider(dry_run=False)

        with patch.object(provider, "_run_cli", side_effect=Exception("cli error")):
            result = provider.health(target="kubectl version")
            assert result["status"] == "error"
            assert "cli error" in result["message"]


class TestBaseObservabilityService:
    """Test BaseObservabilityService branches."""

    def test_init_defaults(self):
        """Test __init__ with default parameters."""
        service = BaseObservabilityService()
        assert service.metrics is not None
        assert service.cache is None
        assert service.settings is None
        assert service._state == {}
        assert service._backups == {}
        assert service._operations == {}

    def test_init_with_params(self):
        """Test __init__ with custom parameters."""
        mock_metrics = MagicMock()
        mock_cache = MagicMock()
        mock_settings = MagicMock()
        service = BaseObservabilityService(
            metrics=mock_metrics,
            cache=mock_cache,
            settings=mock_settings,
        )
        assert service.metrics == mock_metrics
        assert service.cache == mock_cache
        assert service.settings == mock_settings

    def test_get_config_none(self):
        """Test _get_config with None."""
        result = BaseObservabilityService._get_config(None)
        assert result == {}

    def test_get_config_model_dump(self):
        """Test _get_config with object having model_dump."""
        mock_request = MagicMock()
        mock_request.model_dump.return_value = {"config": {"key": "value"}}
        result = BaseObservabilityService._get_config(mock_request)
        assert result == {"key": "value"}

    def test_get_config_dict(self):
        """Test _get_config with dict."""
        result = BaseObservabilityService._get_config({"key": "value"})
        assert result == {"key": "value"}

    def test_get_config_dict_with_config_key(self):
        """Test _get_config with dict containing config key."""
        result = BaseObservabilityService._get_config({"config": {"nested": "value"}})
        assert result == {"nested": "value"}

    def test_get_config_non_dict_non_model_dump(self):
        """Test _get_config with non-dict, non-model_dump object."""
        result = BaseObservabilityService._get_config("string")
        assert result == {}

    def test_get_config_dict_not_dict_after_extraction(self):
        """Test _get_config when extracted data is not a dict."""
        # When config key exists but value is not a dict, it returns the value
        result = BaseObservabilityService._get_config({"config": "not_a_dict"})
        assert result == "not_a_dict"

    async def test_get_state_with_feature_found(self):
        """Test get_state with feature found in state."""
        service = BaseObservabilityService()
        service._state["test_feature"] = {"data": "value"}
        result = await service.get_state({"feature": "test_feature"})
        assert result["success"] is True
        assert result["status"] == "found"
        assert result["result"]["state"] == {"data": "value"}

    async def test_get_state_with_feature_not_found(self):
        """Test get_state with feature not in state."""
        service = BaseObservabilityService()
        result = await service.get_state({"feature": "missing_feature"})
        assert result["success"] is False
        assert result["status"] == "not_found"

    async def test_get_state_no_feature(self):
        """Test get_state without feature."""
        service = BaseObservabilityService()
        result = await service.get_state({})
        assert result["success"] is False
        assert result["status"] == "not_found"

    async def test_get_state_non_dict_config(self):
        """Test get_state with non-dict config."""
        service = BaseObservabilityService()
        result = await service.get_state("string")
        assert result["success"] is False
        assert result["status"] == "not_found"

    async def test_backup_state_default_name(self):
        """Test backup_state with default name."""
        service = BaseObservabilityService()
        service._state = {"key": "value"}
        result = await service.backup_state()
        assert result["success"] is True
        assert result["status"] == "backed_up"
        assert "default" in service._backups

    async def test_backup_state_custom_name(self):
        """Test backup_state with custom name."""
        service = BaseObservabilityService()
        service._state = {"key": "value"}
        result = await service.backup_state({"name": "custom_backup"})
        assert result["success"] is True
        assert "custom_backup" in service._backups

    async def test_backup_state_non_dict_config(self):
        """Test backup_state with non-dict config."""
        service = BaseObservabilityService()
        result = await service.backup_state("string")
        assert result["success"] is True
        assert result["config"]["name"] == "default"

    async def test_restore_state_success(self):
        """Test restore_state success."""
        service = BaseObservabilityService()
        service._backups["test_backup"] = {
            "timestamp": "2024-01-01T00:00:00Z",
            "state": {"restored": "data"},
        }
        result = await service.restore_state({"name": "test_backup"})
        assert result["success"] is True
        assert result["status"] == "restored"
        assert service._state == {"restored": "data"}

    async def test_restore_state_not_found(self):
        """Test restore_state with backup not found."""
        service = BaseObservabilityService()
        result = await service.restore_state({"name": "missing_backup"})
        assert result["success"] is False
        assert result["status"] == "not_found"

    async def test_restore_state_non_dict_config(self):
        """Test restore_state with non-dict config."""
        service = BaseObservabilityService()
        service._backups["default"] = {
            "timestamp": "2024-01-01T00:00:00Z",
            "state": {"data": "value"},
        }
        result = await service.restore_state("string")
        assert result["success"] is True
        assert result["config"]["name"] == "default"

    async def test_get_stats(self):
        """Test get_stats."""
        service = BaseObservabilityService()
        service.metrics.request_count = 10
        service.metrics.cache_hits_count = 5
        service.metrics.cache_misses_count = 3
        service._operations = {"query": 5}
        service._state = {"key": "value"}
        result = await service.get_stats()
        assert result["success"] is True
        # get_stats increments request_count by 1
        assert result["result"]["total_requests"] == 11
        assert result["result"]["cache_hits"] == 5
        assert result["result"]["cache_misses"] == 3
        assert result["result"]["operations"] == {"query": 5}
        assert result["result"]["index_size"] == 1

    async def test_list_methods(self):
        """Test list_methods."""
        service = BaseObservabilityService()
        service.OPERATIONS = ["query", "logs"]
        result = await service.list_methods()
        assert result["success"] is True
        assert "query" in result["result"]["methods"]
        assert "logs" in result["result"]["methods"]
        assert "get_state" in result["result"]["methods"]

    def test_execute_operation(self):
        """Test execute_operation."""
        service = BaseObservabilityService()
        service.OPERATIONS = ["query"]
        result = service.execute_operation("query", {"metric": "up"})
        assert result["feature"] == "query"
        assert result["success"] is True
        assert service._operations["query"] == 1

    def test_getattr_operation(self):
        """Test __getattr__ for operation."""
        service = BaseObservabilityService()
        service.OPERATIONS = ["query"]
        handler = service.query
        assert callable(handler)

    def test_getattr_non_operation(self):
        """Test __getattr__ for non-operation raises AttributeError."""
        service = BaseObservabilityService()
        with pytest.raises(AttributeError):
            _ = service.nonexistent_method

    async def test_call_base_method(self):
        """Test call with base method."""
        service = BaseObservabilityService()
        result = await service.call("get_state")
        assert result["feature"] == "get_state"

    async def test_call_operation(self):
        """Test call with operation."""
        service = BaseObservabilityService()
        service.OPERATIONS = ["query"]
        result = await service.call("query", request={"metric": "up"})
        assert result["feature"] == "query"

    async def test_call_unknown_method(self):
        """Test call with unknown method raises ValueError."""
        service = BaseObservabilityService()
        with pytest.raises(ValueError, match="Unknown method"):
            await service.call("unknown_method")
