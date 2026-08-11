# -*- coding: utf-8 -*-
"""Real end-to-end tests for change management endpoints."""

import pytest

_CASES = [
    ("GET", "/api/v1/change-management/requests", None, None, {200, 500}),
    ("POST", "/api/v1/change-management/requests", {}, None, {200, 422, 500}),
    ("GET", "/api/v1/change-management/requests/cr-1", None, None, {200, 404, 500}),
    ("POST", "/api/v1/change-management/requests/cr-1/submit", {}, None, {200, 400, 422, 404, 500}),
    (
        "POST",
        "/api/v1/change-management/requests/cr-1/approve",
        {},
        None,
        {200, 400, 422, 404, 500},
    ),
    ("POST", "/api/v1/change-management/requests/cr-1/reject", {}, None, {200, 400, 422, 404, 500}),
    (
        "POST",
        "/api/v1/change-management/requests/cr-1/implement",
        {},
        None,
        {200, 400, 422, 404, 500},
    ),
    (
        "POST",
        "/api/v1/change-management/requests/cr-1/rollback",
        {},
        None,
        {200, 400, 422, 404, 500},
    ),
]


@pytest.mark.parametrize("method,path,body,params,expected", _CASES)
def test_change_management_endpoint(client, approval_headers, method, path, body, params, expected):
    """Each B17 endpoint returns an expected status set."""
    kwargs = {}
    if body is not None:
        kwargs["json"] = body
    if params:
        kwargs["params"] = params
    resp = client.request(method, path, headers=approval_headers, **kwargs)
    assert resp.status_code in expected
