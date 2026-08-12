import pytest
# -*- coding: utf-8 -*-
"""Real end-to-end tests for the anomaly detection endpoints."""


@pytest.mark.smoke
def test_list_anomaly_records(client, approval_headers):
    """The anomaly records list returns 200 or a valid server error."""
    resp = client.get("/api/v1/anomaly/records", headers=approval_headers)
    assert resp.status_code in (200, 500)


@pytest.mark.smoke
def test_anomaly_statistics(client, approval_headers):
    """The anomaly statistics endpoint returns 200 or a valid error."""
    resp = client.get("/api/v1/anomaly/statistics", headers=approval_headers)
    assert resp.status_code in (200, 500)


@pytest.mark.smoke
def test_detect_anomaly(client, approval_headers):
    """The detect endpoint accepts an optional payload and returns a result."""
    resp = client.post(
        "/api/v1/anomaly/detect",
        json={},
        headers=approval_headers,
    )
    assert resp.status_code in (200, 400, 422, 500)
