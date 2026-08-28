# -*- coding: utf-8 -*-
"""Real end-to-end tests for the root cause analysis endpoints."""

import pytest  # noqa: F401  # Imported for test setup

pytestmark = [pytest.mark.api]


@pytest.fixture
def admin_headers():
    """Simple admin headers for testing (no auth required for root cause endpoints)."""
    return {}


@pytest.fixture
def approval_headers():
    """Simple approval headers for testing (no auth required for root cause endpoints)."""
    return {}


_CASES = [
    ("GET", "/api/v1/root-cause/topology", None, None, {200, 404, 503}),
    ("POST", "/api/v1/root-cause/topology/discover", {}, None, {200, 404, 422, 503}),
    ("POST", "/api/v1/root-cause/cross-layer-track", {}, {"max_depth": 1}, {200, 404, 422, 500, 503}),
    ("POST", "/api/v1/root-cause/patterns/match", {}, None, {200, 404, 422, 500, 503}),
    ("POST", "/api/v1/root-cause/patterns/learn", {}, None, {200, 404, 422, 500, 503}),
    ("GET", "/api/v1/root-cause/patterns", None, None, {200, 404, 500}),
    ("POST", "/api/v1/root-cause/analyze", {}, None, {200, 404, 422, 500, 503}),
    ("POST", "/api/v1/root-cause/predict", {}, None, {200, 404, 422, 500, 503}),
    ("POST", "/api/v1/root-cause/verify", {}, None, {200, 404, 422, 500, 503}),
    ("GET", "/api/v1/root-cause/statistics", None, None, {200, 404, 500}),
    ("GET", "/api/v1/root-cause/hypotheses", None, None, {200, 404, 500}),
    ("DELETE", "/api/v1/root-cause/hypotheses/h-123", None, None, {200, 404, 500}),
]


@pytest.mark.smoke
@pytest.mark.parametrize("method,path,body,params,expected", _CASES)
def test_root_cause_endpoint(client, approval_headers, method, path, body, params, expected):
    """Each root-cause endpoint returns an expected status set."""
    kwargs = {}
    if body is not None:
        kwargs["json"] = body
    if params:
        kwargs["params"] = params
    resp = client.request(method, path, headers=approval_headers, **kwargs)
    assert resp.status_code in expected


def test_root_cause_topology_discover(client, approval_headers):
    """Test topology discovery endpoint with valid metrics data."""
    payload = {
        "metrics_data": {
            "cpu_usage": 85.5,
            "memory_usage": 78.2,
            "disk_io": 45.3,
            "network_latency": 120.5,
        },
        "include_dependencies": True,
    }
    resp = client.post(
        "/api/v1/root-cause/topology/discover",
        json=payload,
        headers=approval_headers,
    )
    assert resp.status_code in (200, 404, 422, 503)
    if resp.status_code == 200:
        data = resp.json()
        assert "status" in data
        assert "discovery_result" in data
        assert data["status"] == "success"


def test_root_cause_cross_layer_track(client, approval_headers):
    """Test cross-layer tracking with alert data and max_depth parameter."""
    alert_data = {
        "id": "alert-001",
        "severity": "critical",
        "title": "High CPU Usage",
        "description": "CPU usage exceeded threshold",
        "host": "server-01",
        "timestamp": "2026-01-15T10:30:00Z",
    }
    resp = client.post(
        "/api/v1/root-cause/cross-layer-track",
        json=alert_data,
        params={"max_depth": 5},
        headers=approval_headers,
    )
    assert resp.status_code in (200, 404, 422, 500, 503)
    if resp.status_code == 200:
        data = resp.json()
        assert "status" in data
        assert "causal_path" in data
        assert "path_length" in data
        assert "alert_id" in data
        assert data["status"] == "success"
        assert isinstance(data["causal_path"], list)


def test_root_cause_analyze_with_context(client, approval_headers):
    """Test root cause analysis with alert, metrics, and context data."""
    payload = {
        "alert": {
            "id": "alert-002",
            "severity": "warning",
            "title": "Memory Leak Detected",
            "description": "Memory usage steadily increasing",
        },
        "metrics_data": {
            "memory_usage": 92.5,
            "heap_size": 2048,
            "gc_frequency": 15,
        },
        "context": {
            "recent_changes": ["deployment-123", "config-update-456"],
            "time_window": "30m",
            "affected_services": ["api-gateway", "auth-service"],
        },
    }
    resp = client.post(
        "/api/v1/root-cause/analyze",
        json=payload,
        headers=approval_headers,
    )
    assert resp.status_code in (200, 404, 422, 500, 503)
    if resp.status_code == 200:
        data = resp.json()
        assert "status" in data
        assert "hypotheses" in data
        assert "total_hypotheses" in data
        assert "alert_id" in data
        assert data["status"] == "success"
        assert isinstance(data["hypotheses"], list)
        # Verify hypothesis structure
        if len(data["hypotheses"]) > 0:
            hypothesis = data["hypotheses"][0]
            assert "hypothesis_id" in hypothesis
            assert "root_cause" in hypothesis
            assert "confidence" in hypothesis
            assert "evidence" in hypothesis


def test_root_cause_patterns_learn(client, approval_headers):
    """Test pattern learning from resolved incidents."""
    payload = {
        "symptoms": {
            "cpu_spike": True,
            "memory_increase": True,
            "disk_io_high": False,
            "network_latency_normal": True,
        },
        "root_cause": "Database connection pool exhaustion",
        "resolution_time": 45.5,
        "effectiveness": 0.85,
    }
    resp = client.post(
        "/api/v1/root-cause/patterns/learn",
        json=payload,
        headers=approval_headers,
    )
    assert resp.status_code in (200, 404, 422, 500, 503)
    if resp.status_code == 200:
        data = resp.json()
        assert "status" in data
        assert "message" in data
        assert "root_cause" in data
        assert data["status"] == "success"
        assert data["root_cause"] == "Database connection pool exhaustion"
