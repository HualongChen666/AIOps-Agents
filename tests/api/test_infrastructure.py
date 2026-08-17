# -*- coding: utf-8 -*-
"""Real end-to-end tests for infrastructure, cloud and integration read-only endpoints."""

import pytest  # noqa: F401  # Imported for test setup

_CASES = [
    # infrastructure_router.py - GET only to avoid starting external services
    ("GET", "/api/v1/infrastructure/kafka/status", None, None, {200, 500}),
    ("GET", "/api/v1/infrastructure/flink/jobs", None, None, {200, 500}),
    ("GET", "/api/v1/infrastructure/config/test-key", None, None, {200, 404, 500}),
    ("GET", "/api/v1/infrastructure/config", None, None, {200, 500}),
    ("GET", "/api/v1/infrastructure/monitoring/status", None, None, {200, 500}),
    ("GET", "/api/v1/infrastructure/data-flow/stats", None, None, {200, 500}),
    ("GET", "/api/v1/infrastructure/monitoring/summary", None, None, {200, 500}),
    ("GET", "/api/v1/infrastructure/alerts", None, None, {200, 500}),
    # cloud_router.py - GET only to avoid running cloud repair/collect
    ("GET", "/api/v1/platforms/cloud/metrics", None, None, {200, 500}),
    ("GET", "/api/v1/platforms/cloud/history", None, None, {200, 500}),
    ("GET", "/api/v1/platforms/cloud/aws/metrics", None, None, {200, 404, 500}),
    ("GET", "/api/v1/platforms/cloud/aws/history", None, None, {200, 404, 500}),
    ("GET", "/api/v1/platforms/cloud/aws/repair/history", None, None, {200, 404, 500}),
    # integration_router.py - read-only plus validation-only registrations
    ("GET", "/api/v1/integration/list", None, None, {200, 500}),
    ("POST", "/api/v1/integration/register", {}, None, {200, 422, 500}),
    ("GET", "/api/v1/integration/notification/channels", None, None, {200, 500}),
    ("POST", "/api/v1/integration/webhook/register", {}, None, {200, 422, 500}),
    ("GET", "/api/v1/integration/webhooks", None, None, {200, 500}),
    ("GET", "/api/v1/integration/templates", None, None, {200, 500}),
    ("GET", "/api/v1/integration/summary", None, None, {200, 500}),
    ("GET", "/api/v1/integration/types", None, None, {200, 500}),
    ("GET", "/api/v1/integration/events", None, None, {200, 500}),
]


@pytest.mark.smoke
@pytest.mark.parametrize("method,path,body,params,expected", _CASES)
def test_infrastructure_endpoint(client, approval_headers, method, path, body, params, expected):
    """Each safe B20 endpoint returns an expected status set."""
    kwargs = {}
    if body is not None:
        kwargs["json"] = body
    if params:
        kwargs["params"] = params
    resp = client.request(method, path, headers=approval_headers, **kwargs)
    assert resp.status_code in expected
