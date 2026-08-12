import pytest
# -*- coding: utf-8 -*-
"""Real end-to-end tests for the health endpoints."""


def test_health_liveness(client):
    """The liveness probe must return 200."""
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert "timestamp" in data


def test_health_ping_with_auth(client, admin_headers):
    """The ping endpoint returns alive for an authorized request."""
    resp = client.get("/api/v1/health/ping", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "alive"


@pytest.mark.smoke
def test_ready_endpoint_responds(client, admin_headers):
    """The readiness endpoint returns either 200 or 503 depending on deps."""
    resp = client.get("/ready", headers=admin_headers)
    assert resp.status_code in (200, 503)


@pytest.mark.smoke
def test_detailed_health_endpoint_responds(client, admin_headers):
    """Detailed health returns either 200 (all healthy) or 503 (some failing)."""
    resp = client.get("/api/v1/health/detailed", headers=admin_headers)
    assert resp.status_code in (200, 503)
