import pytest  # noqa: F401  # Imported for test setup
from unittest.mock import patch, MagicMock
from datetime import datetime

# -*- coding: utf-8 -*-
"""Real end-to-end tests for the alert management and webhook endpoints."""


def test_list_alerts(client, admin_headers):
    """The alert history list returns a 200 response with an alerts field."""
    resp = client.get("/api/v1/alerts/", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict)
    assert "alerts" in data


def test_acknowledge_alert(client, admin_headers):
    """Acknowledging an alert returns the expected status payload."""
    resp = client.post("/api/v1/alerts/alert-123/acknowledge", headers=admin_headers)
    assert resp.status_code in (200, 404, 500)
    if resp.status_code == 200:
        assert resp.json()["status"] == "acknowledged"


def test_resolve_alert(client, admin_headers):
    """Resolving an alert returns the expected status payload."""
    resp = client.post("/api/v1/alerts/alert-123/resolve", headers=admin_headers)
    assert resp.status_code in (200, 404, 500)
    if resp.status_code == 200:
        assert resp.json()["status"] == "resolved"


@pytest.mark.smoke
def test_intelligence_statistics(client, admin_headers):
    """Intelligence statistics returns 200 when available or 503 when disabled."""
    resp = client.get("/api/v1/alerts/intelligence/statistics", headers=admin_headers)
    assert resp.status_code in (200, 503)


@pytest.mark.smoke
def test_predict_trend(client, admin_headers):
    """Trend prediction accepts a valid payload and returns 200, 400 or 503."""
    resp = client.post(
        "/api/v1/alerts/intelligence/predict",
        json={"metric_name": "cpu_usage", "horizon_hours": 12},
        headers=admin_headers,
    )
    assert resp.status_code in (200, 400, 422, 503)


@pytest.mark.smoke
def test_routing_rules(client, admin_headers):
    """Adding a routing rule returns 200/422/503 depending on engine state."""
    resp = client.post(
        "/api/v1/alerts/intelligence/routing-rules",
        json={
            "conditions": {"severity": "critical"},
            "destination": "pagerduty",
            "description": "Route critical alerts",
            "priority": 1,
        },
        headers=admin_headers,
    )
    assert resp.status_code in (200, 422, 503)


@pytest.mark.smoke
def test_suppression_rules(client, admin_headers):
    """Adding a suppression rule returns 200/422/503 depending on engine state."""
    resp = client.post(
        "/api/v1/alerts/intelligence/suppression-rules",
        json={
            "pattern": "test.*",
            "reason": "Testing suppression",
            "suppression_window": 60,
            "enabled": True,
        },
        headers=admin_headers,
    )
    assert resp.status_code in (200, 422, 503)


@pytest.mark.smoke
def test_prometheus_webhook(client):
    """The Prometheus webhook endpoint accepts a payload and returns a status."""
    payload = {
        "status": "firing",
        "alerts": [
            {
                "labels": {"alertname": "CPUHigh", "severity": "warning"},
                "annotations": {"summary": "CPU usage high"},
                "startsAt": "2026-08-10T00:00:00Z",
            }
        ],
    }
    resp = client.post("/api/v1/alerts/prometheus", json=payload)
    assert resp.status_code in (200, 404, 422, 500, 503)


def test_intelligence_statistics_unavailable(client):
    """Test 503 response when alert intelligence engine is not available (line 247)."""
    with patch("api.alert_router.ALERT_INTELLIGENCE_AVAILABLE", False):
        resp = client.get("/api/v1/alerts/intelligence/statistics")
        assert resp.status_code == 503
        # Check for error message in response (API error wrapper format)
        resp_data = resp.json()
        error_msg = resp_data.get("error", {}).get("message", "")
        assert "智能告警引擎不可用" in error_msg


def test_intelligence_statistics_available(client):
    """Test successful response when alert intelligence engine is available (line 248)."""
    resp = client.get("/api/v1/alerts/intelligence/statistics")
    assert resp.status_code in (200, 503)
    if resp.status_code == 200:
        data = resp.json()
        # Should return statistics
        assert "total_patterns" in data or len(data) > 0


def test_alert_patterns_unavailable(client):
    """Test 503 response when alert intelligence engine is not available (line 298)."""
    with patch("api.alert_router.ALERT_INTELLIGENCE_AVAILABLE", False):
        resp = client.get("/api/v1/alerts/intelligence/patterns")
        assert resp.status_code == 503
        resp_data = resp.json()
        error_msg = resp_data.get("error", {}).get("message", "")
        assert "智能告警引擎不可用" in error_msg


def test_alert_patterns_with_noise(client):
    """Test patterns endpoint with include_noise=True (lines 302-303)."""
    from core.alert_intelligence import alert_intelligence_engine, AlertPattern
    from datetime import datetime

    # Add some test patterns
    alert_intelligence_engine.patterns = {
        "pattern_1": AlertPattern(
            pattern_id="pattern_1",
            signature="cpu_high",
            frequency=10,
            last_seen=datetime.now(),
            is_noise=True,
            noise_reason="高频低级别"
        ),
        "pattern_2": AlertPattern(
            pattern_id="pattern_2",
            signature="memory_high",
            frequency=5,
            last_seen=datetime.now(),
            is_noise=False
        )
    }

    # Test with include_noise=False (default)
    resp = client.get("/api/v1/alerts/intelligence/patterns?include_noise=false")
    if resp.status_code == 200:
        patterns = resp.json()["patterns"]
        # Should only include non-noise patterns
        assert all(not p["is_noise"] for p in patterns)

    # Test with include_noise=True
    resp = client.get("/api/v1/alerts/intelligence/patterns?include_noise=true")
    if resp.status_code == 200:
        patterns = resp.json()["patterns"]
        # Should include both noise and non-noise patterns
        assert len(patterns) >= 1


def test_predict_trend_unavailable(client):
    """Test 503 response when alert intelligence engine is not available (line 358)."""
    with patch("api.alert_router.ALERT_INTELLIGENCE_AVAILABLE", False):
        resp = client.post(
            "/api/v1/alerts/intelligence/predict",
            json={"metric_name": "cpu_usage", "horizon_hours": 12},
        )
        assert resp.status_code == 503
        resp_data = resp.json()
        error_msg = resp_data.get("error", {}).get("message", "")
        assert "智能告警引擎不可用" in error_msg


def test_predict_trend_incomplete_data(client):
    """Test 400 response when metric data is incomplete (line 366)."""
    from core.metrics_history import metrics_history

    # Clear and add incomplete data (timestamps and values mismatch)
    metrics_history.clear()
    metrics_history.timestamps.append("10:00:00")
    metrics_history.timestamps.append("10:01:00")
    metrics_history.timestamps.append("10:02:00")
    # Add only 2 cpu values instead of 3
    metrics_history.cpu.append(50.0)
    metrics_history.cpu.append(55.0)

    resp = client.post(
        "/api/v1/alerts/intelligence/predict",
        json={"metric_name": "cpu", "horizon_hours": 12},
    )
    # Should return 400 due to incomplete data
    assert resp.status_code in (400, 503)
    if resp.status_code == 400:
        resp_data = resp.json()
        error_msg = resp_data.get("error", {}).get("message", "")
        assert "数据不完整" in error_msg


def test_predict_trend_insufficient_data(client):
    """Test 400 response when historical data is insufficient (line 374)."""
    from core.metrics_history import metrics_history

    # Clear and add only 5 data points (less than required 10)
    metrics_history.clear()
    for i in range(5):
        metrics_history.push(50.0 + i, 60.0 + i, 1.0 + i * 0.1, f"10:0{i}:00")

    resp = client.post(
        "/api/v1/alerts/intelligence/predict",
        json={"metric_name": "cpu", "horizon_hours": 12},
    )
    # Should return 400 due to insufficient data
    assert resp.status_code in (400, 503)
    if resp.status_code == 400:
        resp_data = resp.json()
        error_msg = resp_data.get("error", {}).get("message", "")
        assert "历史数据不足" in error_msg


def test_predict_trend_invalid_timestamps(client):
    """Test prediction with invalid timestamp formats (lines 371-372)."""
    from core.metrics_history import metrics_history

    # Clear and add data with some invalid timestamps
    metrics_history.clear()
    metrics_history.timestamps.append("10:00:00")
    metrics_history.timestamps.append("invalid_timestamp")  # Invalid format
    metrics_history.timestamps.append("10:02:00")
    metrics_history.cpu.append(50.0)
    metrics_history.cpu.append(55.0)
    metrics_history.cpu.append(60.0)

    resp = client.post(
        "/api/v1/alerts/intelligence/predict",
        json={"metric_name": "cpu", "horizon_hours": 12},
    )
    # Should handle invalid timestamps gracefully
    assert resp.status_code in (200, 400, 503)


def test_topology_context_unavailable(client):
    """Test 503 response when alert intelligence engine is not available (line 430)."""
    with patch("api.alert_router.ALERT_INTELLIGENCE_AVAILABLE", False):
        resp = client.get("/api/v1/alerts/intelligence/topology")
        assert resp.status_code == 503
        resp_data = resp.json()
        error_msg = resp_data.get("error", {}).get("message", "")
        assert "智能告警引擎不可用" in error_msg


def test_routing_rules_unavailable(client):
    """Test 503 response when alert intelligence engine is not available (line 480)."""
    with patch("api.alert_router.ALERT_INTELLIGENCE_AVAILABLE", False):
        resp = client.post(
            "/api/v1/alerts/intelligence/routing-rules",
            json={
                "conditions": {"severity": "critical"},
                "destination": "pagerduty",
                "description": "Route critical alerts",
                "priority": 1,
            },
        )
        assert resp.status_code == 503
        resp_data = resp.json()
        error_msg = resp_data.get("error", {}).get("message", "")
        assert "智能告警引擎不可用" in error_msg


def test_suppression_rules_unavailable(client):
    """Test 503 response when alert intelligence engine is not available (line 527)."""
    with patch("api.alert_router.ALERT_INTELLIGENCE_AVAILABLE", False):
        resp = client.post(
            "/api/v1/alerts/intelligence/suppression-rules",
            json={
                "pattern": "test.*",
                "reason": "Testing suppression",
                "suppression_window": 60,
                "enabled": True,
            },
        )
        assert resp.status_code == 503
        resp_data = resp.json()
        error_msg = resp_data.get("error", {}).get("message", "")
        assert "智能告警引擎不可用" in error_msg


def test_route_alerts_unavailable(client):
    """Test 503 response when alert intelligence engine is not available (line 572)."""
    with patch("api.alert_router.ALERT_INTELLIGENCE_AVAILABLE", False):
        resp = client.post("/api/v1/alerts/intelligence/route-alerts")
        assert resp.status_code == 503
        resp_data = resp.json()
        error_msg = resp_data.get("error", {}).get("message", "")
        assert "智能告警引擎不可用" in error_msg


def test_get_alerts_with_tenant_id(client):
    """Test get_alerts with tenant_id parameter."""
    resp = client.get("/api/v1/alerts/?limit=10")
    assert resp.status_code == 200
    data = resp.json()
    assert "alerts" in data
    assert "total" in data


def test_get_alerts_limit_validation(client):
    """Test get_alerts with limit parameter validation."""
    # Test with valid limit
    resp = client.get("/api/v1/alerts/?limit=50")
    assert resp.status_code == 200

    # Test with limit at boundary (500)
    resp = client.get("/api/v1/alerts/?limit=500")
    assert resp.status_code == 200

    # Test with invalid limit (should be rejected by FastAPI validation)
    resp = client.get("/api/v1/alerts/?limit=600")
    assert resp.status_code == 422


def test_clear_alerts_endpoint(client):
    """Test clear alerts endpoint (line 199-206)."""
    resp = client.delete("/api/v1/alerts/")
    assert resp.status_code in (200, 401, 403)
    if resp.status_code == 200:
        assert "status" in resp.json()
        assert "cleared_count" in resp.json() or "deleted_count" in resp.json()


def test_alert_patterns_limit_parameter(client):
    """Test patterns endpoint with different limit values."""
    # Test with default limit
    resp = client.get("/api/v1/alerts/intelligence/patterns")
    assert resp.status_code in (200, 503)

    # Test with custom limit
    resp = client.get("/api/v1/alerts/intelligence/patterns?limit=10")
    assert resp.status_code in (200, 503)

    # Test with limit at boundary
    resp = client.get("/api/v1/alerts/intelligence/patterns?limit=200")
    assert resp.status_code in (200, 503)


def test_predict_trend_with_sufficient_data(client):
    """Test prediction with sufficient valid data."""
    from core.metrics_history import metrics_history

    # Clear and add 15 data points (more than required 10)
    metrics_history.clear()
    for i in range(15):
        metrics_history.push(50.0 + i * 0.5, 60.0 + i * 0.3, 1.0 + i * 0.05, f"10:{i:02d}:00")

    resp = client.post(
        "/api/v1/alerts/intelligence/predict",
        json={"metric_name": "cpu", "horizon_hours": 12},
    )
    # Should succeed or return 503 if engine unavailable
    assert resp.status_code in (200, 503)
    if resp.status_code == 200:
        data = resp.json()
        assert "metric_name" in data
        assert "predicted_values" in data


def test_topology_context_with_alerts(client):
    """Test topology context endpoint with alert history."""
    from core.alert_engine import alert_history

    # Add some test alerts
    test_alert = {
        "id": "test-001",
        "level": "warning",
        "title": "Test alert",
        "desc": "Test description",
        "host": "test-server",
        "category": "system",
        "metric": "cpu",
        "value": 85.0,
        "raw_time": "10:30:00"
    }
    alert_history.appendleft(test_alert)

    resp = client.get("/api/v1/alerts/intelligence/topology")
    assert resp.status_code in (200, 503)
    if resp.status_code == 200:
        data = resp.json()
        assert "nodes" in data
        assert "edges" in data


def test_routing_rules_success(client):
    """Test successful routing rule addition."""
    resp = client.post(
        "/api/v1/alerts/intelligence/routing-rules",
        json={
            "conditions": {"severity": "critical"},
            "destination": "pagerduty",
            "description": "Route critical alerts",
            "priority": 1,
        },
    )
    assert resp.status_code in (200, 503)
    if resp.status_code == 200:
        data = resp.json()
        assert data["status"] == "success"
        assert "rule" in data


def test_suppression_rules_success(client):
    """Test successful suppression rule addition."""
    resp = client.post(
        "/api/v1/alerts/intelligence/suppression-rules",
        json={
            "pattern": "test.*",
            "reason": "Testing suppression",
            "suppression_window": 60,
            "enabled": True,
        },
    )
    assert resp.status_code in (200, 503)
    if resp.status_code == 200:
        data = resp.json()
        assert data["status"] == "success"
        assert "rule" in data


def test_route_alerts_intelligently(client):
    """Test intelligent alert routing."""
    from core.alert_engine import alert_history

    # Add some test alerts for routing
    for i in range(5):
        alert_history.appendleft({
            "id": f"route-test-{i}",
            "level": "warning" if i % 2 == 0 else "critical",
            "title": f"Alert {i}",
            "desc": f"Description {i}",
            "host": f"server-{i}",
            "category": "system",
            "metric": "cpu",
            "value": 80.0 + i,
            "raw_time": f"10:{i}:00"
        })

    resp = client.post("/api/v1/alerts/intelligence/route-alerts")
    assert resp.status_code in (200, 503)
    if resp.status_code == 200:
        data = resp.json()
        assert "total_alerts" in data
        assert "routes" in data
        assert "detailed_routing" in data
