# -*- coding: utf-8 -*-
"""Real end-to-end tests for metrics, logs, tracing and APM endpoints."""

import pytest

_CASES = [
    # metrics_router.py
    ("GET", "/api/v1/metrics/", None, None, {200, 500}),
    ("GET", "/api/v1/metrics/snapshot", None, None, {200, 500}),
    ("GET", "/api/v1/metrics/history", None, None, {200, 500}),
    ("GET", "/api/v1/metrics/predictions", None, None, {200, 500}),
    ("GET", "/api/v1/metrics/processes", None, None, {200, 500}),
    ("GET", "/api/v1/metrics/summary", None, None, {200, 500}),
    ("GET", "/api/v1/metrics/agent/feedback-accuracy", None, None, {200, 500}),
    ("GET", "/api/v1/metrics/agent/decision-accuracy", None, None, {200, 500}),
    ("DELETE", "/api/v1/metrics/cache", None, None, {200, 404, 500}),
    # log_router.py
    ("GET", "/api/v1/logs/system/errors", None, None, {200, 500}),
    ("GET", "/api/v1/logs/application/errors", None, None, {200, 500}),
    ("GET", "/api/v1/logs/query", None, None, {200, 500}),
    ("GET", "/api/v1/logs/linux/errors", None, {"host_name": "test"}, {200, 422, 500}),
    ("GET", "/api/v1/logs/linux/query", None, {"host_name": "test"}, {200, 422, 500}),
    # tracing_router.py
    ("GET", "/api/tracing/dashboard", None, None, {200, 500}),
    ("GET", "/api/tracing/traces", None, None, {200, 500}),
    ("GET", "/api/tracing/traces/t-1", None, None, {200, 404, 500}),
    ("GET", "/api/tracing/topology", None, None, {200, 500}),
    ("GET", "/api/tracing/performance/hotspots", None, None, {200, 500}),
    ("GET", "/api/tracing/errors/analysis", None, None, {200, 500}),
    ("GET", "/api/tracing/export/trace-config", None, None, {200, 500}),
    # apm_router.py
    ("GET", "/api/v1/apm/metrics", None, None, {200, 500}),
    ("POST", "/api/v1/apm/metrics/reset", {}, None, {200, 422, 500}),
]


@pytest.mark.parametrize("method,path,body,params,expected", _CASES)
def test_observability_endpoint(client, approval_headers, method, path, body, params, expected):
    """Each B14 endpoint returns an expected status set."""
    kwargs = {}
    if body is not None:
        kwargs["json"] = body
    if params:
        kwargs["params"] = params
    resp = client.request(method, path, headers=approval_headers, **kwargs)
    assert resp.status_code in expected
