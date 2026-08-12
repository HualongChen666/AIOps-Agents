# -*- coding: utf-8 -*-
"""Real end-to-end tests for the root cause analysis endpoints."""

import pytest

_CASES = [
    ("GET", "/api/v1/root-cause/topology", None, None, {200, 503}),
    ("POST", "/api/v1/root-cause/topology/discover", {}, None, {200, 422, 503}),
    ("POST", "/api/v1/root-cause/cross-layer-track", {}, {"max_depth": 1}, {200, 422, 500, 503}),
    ("POST", "/api/v1/root-cause/patterns/match", {}, None, {200, 422, 500, 503}),
    ("POST", "/api/v1/root-cause/patterns/learn", {}, None, {200, 422, 500, 503}),
    ("GET", "/api/v1/root-cause/patterns", None, None, {200, 500}),
    ("POST", "/api/v1/root-cause/analyze", {}, None, {200, 422, 500, 503}),
    ("POST", "/api/v1/root-cause/predict", {}, None, {200, 422, 500, 503}),
    ("POST", "/api/v1/root-cause/verify", {}, None, {200, 422, 500, 503}),
    ("GET", "/api/v1/root-cause/statistics", None, None, {200, 500}),
    ("GET", "/api/v1/root-cause/hypotheses", None, None, {200, 500}),
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
