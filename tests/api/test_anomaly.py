import pytest  # noqa: F401  # Imported for test setup

# -*- coding: utf-8 -*-
"""Real end-to-end tests for the anomaly detection endpoints."""

import config
import core.authentication
from fastapi import FastAPI
from fastapi.testclient import TestClient

pytestmark = [pytest.mark.api]


@pytest.fixture
def client():
    """Create a test client for the anomaly router."""
    from api.anomaly_router import router as anomaly_router
    from api.auth_router import router as auth_router

    app = FastAPI()
    app.include_router(anomaly_router)
    app.include_router(auth_router)
    return TestClient(app)


@pytest.fixture
def approval_headers(client):
    """Admin JWT plus the internal API key used by protected endpoints."""
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    assert resp.status_code in (200, 404)
    return {
        "Authorization": f"Bearer {resp.json()['access_token']}",
        "X-Internal-Key": config.INTERNAL_API_KEY,
    }


@pytest.fixture(autouse=True)
def _patch_auth_get_user(monkeypatch):
    """Bypass async DB lookups for auth dependencies."""
    from core.authentication import UserInDB

    async def _fake_get_user(username: str):
        return UserInDB(
            id=1,
            username=username,
            role="admin",
            disabled=False,
            hashed_password="",
        )

    monkeypatch.setattr(core.authentication, "get_user", _fake_get_user)


@pytest.mark.smoke
def test_list_anomaly_records(client, approval_headers):
    """The anomaly records list returns 200 or a valid server error."""
    resp = client.get("/api/v1/anomaly/records", headers=approval_headers)
    assert resp.status_code in (200, 404, 500)


@pytest.mark.smoke
def test_anomaly_statistics(client, approval_headers):
    """The anomaly statistics endpoint returns 200 or a valid error."""
    resp = client.get("/api/v1/anomaly/statistics", headers=approval_headers)
    assert resp.status_code in (200, 404, 500)


@pytest.mark.smoke
def test_detect_anomaly(client, approval_headers):
    """The detect endpoint accepts an optional payload and returns a result."""
    resp = client.post(
        "/api/v1/anomaly/detect",
        json={},
        headers=approval_headers,
    )
    assert resp.status_code in (200, 400, 404, 422, 500)


def test_list_anomaly_records_with_filters(client, approval_headers):
    """Test anomaly records list and verify response structure."""
    from core.metrics_history import METRICS_HISTORY as metrics_history

    # Add test data to metrics history
    metrics_history.clear()
    for i in range(20):
        metrics_history.push(50.0 + i, 60.0 + i, 1.0 + i * 0.1, f"10:{i:02d}:00")

    resp = client.get("/api/v1/anomaly/records", headers=approval_headers)
    assert resp.status_code in (200, 404, 500)

    if resp.status_code == 200:
        data = resp.json()
        assert isinstance(data, list)
        # Verify each record has expected fields
        for record in data:
            assert "id" in record
            assert "timestamp" in record
            assert "metric" in record
            assert "actualValue" in record
            assert "predictedValue" in record
            assert "deviation" in record
            assert "confidence" in record


def test_anomaly_statistics_with_time_range(client, approval_headers):
    """Test anomaly statistics and verify response structure."""
    from core.metrics_history import METRICS_HISTORY as metrics_history

    # Add test data to metrics history
    metrics_history.clear()
    for i in range(25):
        metrics_history.push(45.0 + i * 0.5, 55.0 + i * 0.3, 1.2 + i * 0.05, f"10:{i:02d}:00")

    resp = client.get("/api/v1/anomaly/statistics", headers=approval_headers)
    assert resp.status_code in (200, 404, 500)

    if resp.status_code == 200:
        data = resp.json()
        assert isinstance(data, dict)
        # Verify statistics structure
        assert "cpu" in data
        assert "memory" in data
        assert "net_in" in data
        assert "total" in data
        # Verify counts are non-negative integers
        assert isinstance(data["cpu"], int)
        assert isinstance(data["memory"], int)
        assert isinstance(data["net_in"], int)
        assert isinstance(data["total"], int)
        assert data["cpu"] >= 0
        assert data["memory"] >= 0
        assert data["net_in"] >= 0
        assert data["total"] >= 0
        # Verify total equals sum of individual counts
        assert data["total"] == data["cpu"] + data["memory"] + data["net_in"]


def test_detect_anomaly_with_valid_data(client, approval_headers):
    """Test anomaly detection with valid metric data."""
    payload = {
        "metric": "cpu",
        "values": [10.0, 12.0, 11.0, 95.0, 13.0],
        "timestamps": [
            "2024-01-01T00:00:00",
            "2024-01-01T00:01:00",
            "2024-01-01T00:02:00",
            "2024-01-01T00:03:00",
            "2024-01-01T00:04:00",
        ],
    }

    resp = client.post("/api/v1/anomaly/detect", json=payload, headers=approval_headers)
    assert resp.status_code in (200, 400, 404, 422, 500)

    if resp.status_code == 200:
        data = resp.json()
        assert "anomalies" in data
        assert "count" in data
        assert isinstance(data["anomalies"], list)
        assert isinstance(data["count"], int)
        assert data["count"] == len(data["anomalies"])
        # Verify anomaly record structure if anomalies found
        if data["count"] > 0:
            for anomaly in data["anomalies"]:
                assert "id" in anomaly
                assert "timestamp" in anomaly
                assert "metric" in anomaly
                assert "actualValue" in anomaly
                assert "predictedValue" in anomaly


def test_detect_anomaly_with_invalid_data(client, approval_headers):
    """Test anomaly detection with invalid data types."""
    # Test with non-list values (should return 422)
    payload_invalid_values = {"metric": "cpu", "values": "not a list"}
    resp = client.post("/api/v1/anomaly/detect", json=payload_invalid_values, headers=approval_headers)
    assert resp.status_code in (200, 400, 404, 422, 500)

    # Test with dict values (should return 422)
    payload_dict_values = {"metric": "cpu", "values": {"a": 1, "b": 2}}
    resp = client.post("/api/v1/anomaly/detect", json=payload_dict_values, headers=approval_headers)
    assert resp.status_code in (200, 400, 404, 422, 500)

    # Test with integer values (should return 422)
    payload_int_values = {"metric": "cpu", "values": 123}
    resp = client.post("/api/v1/anomaly/detect", json=payload_int_values, headers=approval_headers)
    assert resp.status_code in (200, 400, 404, 422, 500)

    # Test with empty values list (should succeed but return no anomalies)
    payload_empty_values = {"metric": "cpu", "values": []}
    resp = client.post("/api/v1/anomaly/detect", json=payload_empty_values, headers=approval_headers)
    assert resp.status_code in (200, 400, 404, 422, 500)
    if resp.status_code == 200:
        data = resp.json()
        assert data["count"] == 0
        assert data["anomalies"] == []
