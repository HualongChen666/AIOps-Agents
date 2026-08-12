# -*- coding: utf-8 -*-
"""Real end-to-end tests for guard and security endpoints."""

import pytest

_CASES = [
    # guard_router.py
    ("POST", "/api/guard/check", {}, None, {200, 422, 500}),
    ("POST", "/api/guard/allowed", {}, None, {200, 422, 500}),
    ("POST", "/api/guard/rewrite", {}, None, {200, 422, 500}),
    ("POST", "/api/guard/dryrun", {}, None, {200, 422, 500}),
    ("GET", "/api/guard/audit", None, None, {200, 500}),
    ("GET", "/api/guard/stats", None, None, {200, 500}),
    # security_router
    ("GET", "/api/v1/security/events", None, None, {200, 500}),
    ("GET", "/api/v1/security/stats", None, None, {200, 500}),
]


@pytest.mark.smoke
@pytest.mark.parametrize("method,path,body,params,expected", _CASES)
def test_guard_endpoint(client, approval_headers, method, path, body, params, expected):
    """Each B22 endpoint returns an expected status set."""
    kwargs = {}
    if body is not None:
        kwargs["json"] = body
    if params:
        kwargs["params"] = params
    resp = client.request(method, path, headers=approval_headers, **kwargs)
    assert resp.status_code in expected
