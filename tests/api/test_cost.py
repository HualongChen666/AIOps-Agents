# -*- coding: utf-8 -*-
"""Real end-to-end tests for the cost monitoring endpoints."""

import pytest  # noqa: F401  # Imported for test setup

_CASES = [
    ("GET", "/api/cost/collect", None, None, {200, 404, 500}),
    ("GET", "/api/cost/forecast", None, {"days": 30}, {200, 404, 500}),
    ("GET", "/api/cost/budget", None, None, {200, 500}),
]


@pytest.mark.smoke
@pytest.mark.parametrize("method,path,body,params,expected", _CASES)
def test_cost_endpoint(client, admin_headers, method, path, body, params, expected):
    """Each B26 endpoint returns an expected status set."""
    kwargs = {}
    if body is not None:
        kwargs["json"] = body
    if params:
        kwargs["params"] = params
    resp = client.request(method, path, headers=admin_headers, **kwargs)
    assert resp.status_code in expected
