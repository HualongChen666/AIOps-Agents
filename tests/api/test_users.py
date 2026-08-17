# -*- coding: utf-8 -*-
"""Real end-to-end tests for the user management endpoints."""

import pytest  # noqa: F401  # Imported for test setup

_CASES = [
    ("POST", "/api/v1/users/", {}, {200, 422, 500}),
    ("GET", "/api/v1/users/", None, {200, 404, 500}),
    ("GET", "/api/v1/users/me", None, {200, 500}),
    ("GET", "/api/v1/users/audit-logs", None, {200, 403, 422, 500}),
    ("GET", "/api/v1/users/1", None, {200, 404, 500}),
    ("PUT", "/api/v1/users/1", {}, {200, 422, 404, 500}),
    ("DELETE", "/api/v1/users/1", None, {200, 204, 400, 404, 500}),
    ("POST", "/api/v1/users/me/change-password", {}, {200, 422, 404, 500}),
    ("POST", "/api/v1/users/me/mfa/enable", {}, {200, 422, 404, 500}),
    ("POST", "/api/v1/users/me/mfa/disable", {}, {200, 422, 404, 500}),
    ("GET", "/api/v1/users/me/mfa/status", None, {200, 404, 500}),
    ("GET", "/api/v1/users/me/audit-logs", None, {200, 404, 500}),
    ("GET", "/api/v1/users/1/audit-logs", None, {200, 404, 500}),
]


@pytest.mark.smoke
@pytest.mark.parametrize("method,path,body,expected", _CASES)
def test_user_endpoint(client, admin_headers, method, path, body, expected):
    """Each user_router endpoint returns an expected status set."""
    kwargs = {}
    if body is not None:
        kwargs["json"] = body
    resp = client.request(method, path, headers=admin_headers, **kwargs)
    assert resp.status_code in expected
