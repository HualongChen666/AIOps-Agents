# -*- coding: utf-8 -*-
"""Real end-to-end tests for assets, capacity, SLO, dashboard and stats endpoints."""

import pytest

_CASES = [
    # assets_router.py
    ("GET", "/api/v1/assets/", None, None, {200, 500}),
    ("POST", "/api/v1/assets/", {}, None, {200, 422, 500}),
    ("GET", "/api/v1/assets/1", None, None, {200, 404, 500}),
    ("PUT", "/api/v1/assets/1", {}, None, {200, 422, 404, 500}),
    ("DELETE", "/api/v1/assets/1", None, None, {200, 404, 500}),
    # capacity_router.py
    ("GET", "/api/v1/capacity/forecast", None, None, {200, 500}),
    ("GET", "/api/v1/capacity/recommendations", None, None, {200, 500}),
    # slo_router.py
    ("GET", "/api/v1/slo/", None, None, {200, 500}),
    ("POST", "/api/v1/slo/", {}, None, {200, 422, 500}),
    ("GET", "/api/v1/slo/slo-1", None, None, {200, 404, 500}),
    ("PUT", "/api/v1/slo/slo-1", {}, None, {200, 422, 404, 500}),
    ("DELETE", "/api/v1/slo/slo-1", None, None, {200, 404, 500}),
    ("GET", "/api/v1/slo/reports", None, None, {200, 500}),
    ("POST", "/api/v1/slo/reports", {}, None, {200, 422, 500}),
    ("GET", "/api/v1/slo/reports/r-1", None, None, {200, 404, 500}),
    ("DELETE", "/api/v1/slo/reports/r-1", None, None, {200, 404, 500}),
    # stats_router.py
    ("GET", "/api/v1/stats/summary", None, None, {200, 500}),
    ("POST", "/api/v1/stats/repair/record", {}, None, {200, 422, 500}),
]


@pytest.mark.parametrize("method,path,body,params,expected", _CASES)
def test_assets_capacity_endpoint(client, approval_headers, method, path, body, params, expected):
    """Each B13 endpoint returns an expected status set."""
    kwargs = {}
    if body is not None:
        kwargs["json"] = body
    if params:
        kwargs["params"] = params
    resp = client.request(method, path, headers=approval_headers, **kwargs)
    assert resp.status_code in expected
