# -*- coding: utf-8 -*-
"""Real (no-mock) branch coverage tests for core.agent.observability_client.

Tests exercise the client with a real local HTTP server, real environment
variables and real temporary files.  No ``unittest.mock`` or httpx fakes are
used.
"""

import json
import os
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

import core.agent.observability_client as oc


# ---------------------------------------------------------------------------
# Local HTTP server fixture
# ---------------------------------------------------------------------------
class _ObservabilityHandler(BaseHTTPRequestHandler):
    """A tiny real HTTP server that returns safe observability-shaped data."""

    def log_message(self, fmt, *args):  # noqa: D401
        pass

    def _send_json(self, body, status=200):
        payload = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _route(self, path):
        if path.startswith("/api/v1/query"):
            self._send_json(
                {"status": "success", "data": {"result": [{"value": [time.time(), "12.5"]}]}}
            )
        elif path.startswith("/api/v1/query_range"):
            self._send_json(
                {"status": "success", "data": {"result": [{"value": [time.time(), "12.5"]}]}}
            )
        elif path.startswith("/loki/api/v1/query_range"):
            self._send_json({"status": "success", "data": {"result": []}})
        elif path.startswith("/api/v1/events"):
            self._send_json(
                {
                    "items": [
                        {
                            "type": "Normal",
                            "reason": "Created",
                            "message": "Pod created",
                            "involvedObject": {"name": "pod-1", "kind": "Pod"},
                            "metadata": {"namespace": "default"},
                            "lastTimestamp": "2024-01-01T00:00:00Z",
                        }
                    ]
                }
            )
        elif path == "/api/v1/namespaces/default/pods/my-pod":
            self._send_json(
                {
                    "status": {
                        "phase": "Running",
                        "containerStatuses": [
                            {
                                "name": "app",
                                "lastState": {
                                    "terminated": {"exitCode": 137, "reason": "OOMKilled"}
                                },
                            }
                        ],
                    },
                    "spec": {"nodeName": "node-1"},
                }
            )
        elif path == "/api/v1/nodes/my-node":
            self._send_json(
                {
                    "status": {
                        "conditions": [{"type": "Ready", "status": "True"}],
                        "allocatable": {"memory": "32Gi", "cpu": "8"},
                    }
                }
            )
        elif path.startswith("/events"):
            if "target=invalid" in path:
                self._send_json({"status": "ok"})
            elif "target=list" in path:
                self._send_json([])
            else:
                self._send_json(
                    {"events": [{"timestamp": "2024-01-01T00:00:00Z", "target": "web"}]}
                )
        elif path == "/error":
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b"server error")
        elif path == "/invalid_json":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"not json at all")
        elif path == "/string_json":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            payload = b'"hello"'
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        else:
            self.send_response(404)
            self.end_headers()

    def do_GET(self):  # noqa: N802
        if self.path.startswith("/slow"):
            time.sleep(2)
            if self.path == "/slow":
                self._send_json({"ok": True})
            else:
                self._route(self.path[len("/slow") :])
        else:
            self._route(self.path)


@pytest.fixture(scope="module")
def obs_server():
    server = HTTPServer(("127.0.0.1", 0), _ObservabilityHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    # Ensure the server is accepting connections before yielding.
    for _ in range(50):
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                break
        except OSError:
            time.sleep(0.01)
    yield f"http://127.0.0.1:{port}"
    server.shutdown()
    server.server_close()


@pytest.fixture(autouse=True)
def _reset_http_client():
    """Close any shared httpx client so per-test env changes take effect."""
    client = getattr(oc, "_HTTP_CLIENT", None)
    if client is not None:
        try:
            client.close()
        except Exception:
            pass
    oc._HTTP_CLIENT = None
    yield
    client = getattr(oc, "_HTTP_CLIENT", None)
    if client is not None:
        try:
            client.close()
        except Exception:
            pass
    oc._HTTP_CLIENT = None


# ---------------------------------------------------------------------------
# Helpers and environment branches
# ---------------------------------------------------------------------------
def test_safe_label_and_helpers():
    assert oc._safe_label("web-frontend_v1:1.0") == "web-frontend_v1:1.0"
    with pytest.raises(ValueError):
        oc._safe_label("bad;value")
    with pytest.raises(ValueError):
        oc._safe_label("x" * 201)
    with pytest.raises(ValueError):
        oc._safe_label(123)  # type: ignore[arg-type]
    assert oc._sanitize_url_for_log("http://x") == "http://x"
    assert oc._read_file(__file__) is not None
    assert oc._read_file("/non/existent/file") is None


def test_env_getters(monkeypatch):
    monkeypatch.setenv("AIOPS_PROMETHEUS_URL", "http://prom")
    assert oc.get_prometheus_url() == "http://prom"
    monkeypatch.delenv("AIOPS_PROMETHEUS_URL", raising=False)
    assert oc.get_prometheus_url() is None

    monkeypatch.setenv("AIOPS_KUBERNETES_TOKEN", "tok")
    assert oc.get_kubernetes_token() == "tok"
    monkeypatch.delenv("AIOPS_KUBERNETES_TOKEN", raising=False)
    assert oc.get_kubernetes_token() in (None, "")

    monkeypatch.setenv("AIOPS_KUBERNETES_VERIFY", "false")
    assert oc._should_verify_ssl() is False
    monkeypatch.setenv("AIOPS_KUBERNETES_VERIFY", "yes")
    assert oc._should_verify_ssl() is True


def test_headers_and_verify(monkeypatch, tmp_path):
    monkeypatch.setenv("AIOPS_PROMETHEUS_TOKEN", "prom-token")
    headers = oc._prom_headers()
    assert headers.get("Authorization") == "Bearer prom-token"

    ca_file = tmp_path / "ca.crt"
    ca_file.write_text("fake-ca")
    monkeypatch.setenv("AIOPS_KUBERNETES_VERIFY", "true")
    monkeypatch.setenv("AIOPS_KUBERNETES_CA", str(ca_file))
    assert oc._k8s_verify() == str(ca_file)

    monkeypatch.setenv("AIOPS_KUBERNETES_VERIFY", "false")
    assert oc._k8s_verify() is False

    monkeypatch.setenv("AIOPS_KUBERNETES_TOKEN", "k8s-token")
    k8s_headers = oc._k8s_headers()
    assert k8s_headers["Accept"] == "application/json"
    assert k8s_headers["Authorization"] == "Bearer k8s-token"


def test_kubernetes_ca_default(monkeypatch):
    monkeypatch.delenv("AIOPS_KUBERNETES_CA", raising=False)
    assert oc.get_kubernetes_ca() is None

    # _k8s_verify falls back to True when no CA is available.
    monkeypatch.setenv("AIOPS_KUBERNETES_VERIFY", "true")
    assert oc._k8s_verify() is True


# ---------------------------------------------------------------------------
# HTTP client and query branches
# ---------------------------------------------------------------------------
def test_http_get_json_success(obs_server, monkeypatch):
    monkeypatch.setenv("AIOPS_PROMETHEUS_URL", obs_server)
    data, error = oc._http_get_json(f"{obs_server}/api/v1/query")
    assert data is not None
    assert error is None


def test_http_get_json_errors(obs_server, monkeypatch):
    monkeypatch.setenv("AIOPS_PROMETHEUS_URL", obs_server)

    # 500 from the server
    data, error = oc._http_get_json(f"{obs_server}/error")
    assert data is None
    assert (
        "500" in error or "Server error" in error or "Internal" in error or "error" in error.lower()
    )

    # Non-JSON body
    data, error = oc._http_get_json(f"{obs_server}/invalid_json")
    assert data is None
    assert error is not None

    # Response exceeds size limit
    orig_limit = oc._MAX_RESPONSE_BYTES
    try:
        oc._MAX_RESPONSE_BYTES = 5
        data, error = oc._http_get_json(f"{obs_server}/api/v1/query")
        assert data is None
        assert "too large" in error.lower() or "large" in error.lower()
    finally:
        oc._MAX_RESPONSE_BYTES = orig_limit


def test_http_get_json_non_dict_list(obs_server, monkeypatch):
    monkeypatch.setenv("AIOPS_PROMETHEUS_URL", obs_server)
    # A top-level JSON string covers the else branch in the finally logger.
    data, error = oc._http_get_json(f"{obs_server}/string_json")
    assert data == "hello"
    assert error is None


def test_http_get_json_timeout(obs_server, monkeypatch):
    monkeypatch.setenv("AIOPS_PROMETHEUS_URL", f"{obs_server}/slow")
    monkeypatch.setenv("AIOPS_OBSERVABILITY_TIMEOUT", "0.01")
    oc._HTTP_CLIENT = None
    data, error = oc._http_get_json(f"{obs_server}/slow")
    assert data is None
    assert error is not None


def test_query_prometheus_success(obs_server, monkeypatch):
    monkeypatch.setenv("AIOPS_PROMETHEUS_URL", obs_server)
    result = oc.query_prometheus("up")
    assert isinstance(result, dict)
    assert result.get("status") == "success"


def test_query_prometheus_missing_backend():
    # Ensure the environment variable is absent.
    os.environ.pop("AIOPS_PROMETHEUS_URL", None)
    oc._HTTP_CLIENT = None
    assert oc.query_prometheus("up") is None


def test_query_prometheus_invalid_promql(obs_server, monkeypatch):
    monkeypatch.setenv("AIOPS_PROMETHEUS_URL", obs_server)
    # Validation fails before any network call.
    result = oc.query_prometheus("up; drop")
    assert result is None


def test_query_prometheus_invalid_backend(monkeypatch):
    monkeypatch.setenv("AIOPS_PROMETHEUS_URL", "http://127.0.0.1:1")
    result = oc.query_prometheus("up")
    assert isinstance(result, dict)
    assert result.get("status") == "error"


def test_query_prometheus_range_success(obs_server, monkeypatch):
    monkeypatch.setenv("AIOPS_PROMETHEUS_URL", obs_server)
    end = time.time()
    start = end - 3600
    result = oc.query_prometheus_range("up", start, end, step="15s")
    assert isinstance(result, dict)
    assert result.get("status") == "success"


def test_query_prometheus_range_invalid(obs_server, monkeypatch):
    end = time.time()
    start = end - 3600

    # No backend configured.
    os.environ.pop("AIOPS_PROMETHEUS_URL", None)
    assert oc.query_prometheus_range("up", start, end) is None

    # Invalid PromQL raises validation failure before any network call.
    monkeypatch.setenv("AIOPS_PROMETHEUS_URL", obs_server)
    assert oc.query_prometheus_range("up; drop", start, end) is None

    # Valid PromQL but invalid backend returns an error-shaped dict.
    monkeypatch.setenv("AIOPS_PROMETHEUS_URL", "http://127.0.0.1:1")
    result = oc.query_prometheus_range("up", start, end)
    assert isinstance(result, dict)
    assert result.get("status") == "error"


# ---------------------------------------------------------------------------
# Service / network metrics (loops and scalar extraction)
# ---------------------------------------------------------------------------
def test_extract_scalar_value():
    assert oc._extract_prom_scalar_value(None) is None
    assert oc._extract_prom_scalar_value({}) is None
    assert oc._extract_prom_scalar_value({"data": {"result": []}}) is None
    assert oc._extract_prom_scalar_value({"data": {"result": [{"value": [1]}]}}) is None
    assert oc._extract_prom_scalar_value({"data": {"result": [{"value": [1, "abc"]}]}}) is None
    assert oc._extract_prom_scalar_value({"data": {"result": [{"value": [1, "12.5"]}]}}) == 12.5


def test_query_service_metrics_success(obs_server, monkeypatch):
    monkeypatch.setenv("AIOPS_PROMETHEUS_URL", obs_server)
    metrics = oc.query_service_metrics("web-frontend_v1")
    assert metrics["source"] == "prometheus"
    assert metrics["available"] is True
    for key in ("request_rate", "error_rate", "latency_p99", "latency_p95", "latency_p50"):
        assert key in metrics


def test_query_service_metrics_missing_backend():
    os.environ.pop("AIOPS_PROMETHEUS_URL", None)
    metrics = oc.query_service_metrics("web-frontend_v1")
    assert metrics["available"] is False


def test_query_network_metrics_success(obs_server, monkeypatch):
    monkeypatch.setenv("AIOPS_PROMETHEUS_URL", obs_server)
    metrics = oc.query_network_metrics("192.168.1.1")
    assert metrics["source"] == "prometheus"
    assert metrics["available"] is True


def test_query_network_metrics_missing_backend():
    os.environ.pop("AIOPS_PROMETHEUS_URL", None)
    metrics = oc.query_network_metrics("192.168.1.1")
    assert metrics["available"] is False


# ---------------------------------------------------------------------------
# Loki, Kubernetes and change events
# ---------------------------------------------------------------------------
def test_query_loki_success(obs_server, monkeypatch):
    monkeypatch.setenv("AIOPS_LOKI_URL", obs_server)
    result = oc.query_loki('{app="test"}')
    assert result is not None
    assert result.get("status") == "success"


def test_query_loki_missing_backend():
    os.environ.pop("AIOPS_LOKI_URL", None)
    assert oc.query_loki('{app="test"}') is None


def test_query_loki_invalid_logql(obs_server, monkeypatch):
    monkeypatch.setenv("AIOPS_LOKI_URL", obs_server)
    result = oc.query_loki("{")  # unbalanced braces
    assert isinstance(result, dict)
    assert "error" in result


def test_query_kubernetes_events_branches(obs_server, monkeypatch):
    monkeypatch.setenv("AIOPS_KUBERNETES_API_URL", obs_server)

    # No filters
    assert oc.query_kubernetes_events()
    # Namespace only
    assert oc.query_kubernetes_events(namespace="default")
    # Field selector only
    assert oc.query_kubernetes_events(field_selector="type=Normal")
    # Both filters
    assert oc.query_kubernetes_events(namespace="default", field_selector="type=Normal")


def test_query_kubernetes_events_missing_backend():
    os.environ.pop("AIOPS_KUBERNETES_API_URL", None)
    assert oc.query_kubernetes_events() == []


def test_query_kubernetes_events_invalid_backend(monkeypatch):
    monkeypatch.setenv("AIOPS_KUBERNETES_API_URL", "http://127.0.0.1:1")
    assert oc.query_kubernetes_events() == []


def test_query_kubernetes_pod_success(obs_server, monkeypatch):
    monkeypatch.setenv("AIOPS_KUBERNETES_API_URL", obs_server)
    result = oc.query_kubernetes_pod("my-pod")
    assert result["available"] is True
    assert result["phase"] == "Running"
    assert result["last_state"].get("exitCode") == 137


def test_query_kubernetes_pod_missing_and_error(monkeypatch):
    os.environ.pop("AIOPS_KUBERNETES_API_URL", None)
    result = oc.query_kubernetes_pod("my-pod")
    assert result["available"] is False

    monkeypatch.setenv("AIOPS_KUBERNETES_API_URL", "http://127.0.0.1:1")
    result = oc.query_kubernetes_pod("my-pod")
    assert result["available"] is False
    assert result["reason"] is not None


def test_query_kubernetes_node_success(obs_server, monkeypatch):
    monkeypatch.setenv("AIOPS_KUBERNETES_API_URL", obs_server)
    result = oc.query_kubernetes_node("my-node")
    assert result["available"] is True
    assert result["conditions"].get("Ready") == "True"
    assert result["allocatable_memory"] == "32Gi"


def test_query_kubernetes_node_missing_and_error(monkeypatch):
    os.environ.pop("AIOPS_KUBERNETES_API_URL", None)
    result = oc.query_kubernetes_node("my-node")
    assert result["available"] is False

    monkeypatch.setenv("AIOPS_KUBERNETES_API_URL", "http://127.0.0.1:1")
    result = oc.query_kubernetes_node("my-node")
    assert result["available"] is False
    assert result["reason"] is not None


def test_query_change_events_file_only(tmp_path, monkeypatch):
    events_file = tmp_path / "events.json"
    events_file.write_text(json.dumps([{"target": "web", "when": "2024-01-01T00:00:00Z"}]))
    monkeypatch.setenv("AIOPS_CHANGE_EVENTS_FILE", str(events_file))
    os.environ.pop("AIOPS_CHANGE_EVENTS_URL", None)

    events = oc.query_change_events("web")
    assert len(events) == 1
    assert events[0]["target"] == "web"

    # Non-list JSON file should be ignored.
    events_file.write_text(json.dumps({"not": "list"}))
    assert oc.query_change_events("web") == []

    # Malformed JSON is caught and ignored.
    events_file.write_text("not json")
    assert oc.query_change_events("web") == []

    # File too large is skipped.
    events_file.write_text(json.dumps([{"x": 1}]))
    orig_max = oc._MAX_CHANGE_EVENTS_FILE_BYTES
    try:
        oc._MAX_CHANGE_EVENTS_FILE_BYTES = 1
        assert oc.query_change_events("web") == []
    finally:
        oc._MAX_CHANGE_EVENTS_FILE_BYTES = orig_max


def test_query_change_events_api_branches(obs_server, monkeypatch):
    monkeypatch.setenv("AIOPS_CHANGE_EVENTS_URL", obs_server)
    os.environ.pop("AIOPS_CHANGE_EVENTS_FILE", None)

    # Dict with "events"
    events = oc.query_change_events("web")
    assert len(events) == 1

    # List response
    events = oc.query_change_events("list")
    assert events == []

    # Unexpected response shape
    events = oc.query_change_events("invalid")
    assert events == []


def test_query_change_events_timeout(obs_server, monkeypatch):
    monkeypatch.setenv("AIOPS_CHANGE_EVENTS_URL", f"{obs_server}/slow")
    oc._HTTP_CLIENT = None
    # query_change_events passes _DEFAULT_TIMEOUT to _http_get_json, so we lower
    # that module constant directly for this test.
    original = oc._DEFAULT_TIMEOUT
    try:
        oc._DEFAULT_TIMEOUT = 0.01
        # Should not raise; the timeout is caught and an empty list returned.
        events = oc.query_change_events("web")
        assert events == []
    finally:
        oc._DEFAULT_TIMEOUT = original


def test_query_change_events_invalid_hours(obs_server, monkeypatch):
    monkeypatch.setenv("AIOPS_CHANGE_EVENTS_URL", obs_server)
    events = oc.query_change_events("web", hours="not-a-number")
    assert events == []
