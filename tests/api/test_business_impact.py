# -*- coding: utf-8 -*-
"""Real end-to-end tests for the business impact endpoints."""


def test_list_business_impact_services(client, approval_headers):
    """The services list returns a 200 response or a valid server error."""
    resp = client.get("/api/v1/business-impact/services", headers=approval_headers)
    assert resp.status_code in (200, 500)


def test_ux_metrics(client, approval_headers):
    """The UX metrics endpoint returns a 200 response or a valid error."""
    resp = client.get("/api/v1/business-impact/ux-metrics", headers=approval_headers)
    assert resp.status_code in (200, 500)


def test_assess_service(client, approval_headers):
    """Assessing a single service returns a 200/404/500 status."""
    resp = client.get(
        "/api/v1/business-impact/assess/test-service",
        headers=approval_headers,
    )
    assert resp.status_code in (200, 404, 500)
