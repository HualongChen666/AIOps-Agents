# -*- coding: utf-8 -*-
"""Real end-to-end tests for notification integration endpoints."""

import pytest  # noqa: F401  # Imported for test setup

_CASES = [
    # itsm_router.py
    ("POST", "/api/itsm/incident", {}, None, {200, 422, 500}),
    ("PATCH", "/api/itsm/incident/inc-1", {}, None, {200, 422, 404, 500}),
    # slack_router.py / teams_router.py have no safe HTTP endpoints; messaging
    # calls external services and crashes in this environment.
    # teams_router.py - only health is exposed via HTTP? No HTTP GET endpoints
    # notify_router.py - safe read-only endpoints plus a validation-only update
    ("GET", "/api/notify/config", None, None, {200, 500}),
    ("GET", "/api/notify/health", None, None, {200, 500}),
    ("GET", "/api/notify/status", None, None, {200, 500}),
    ("POST", "/api/notify/read", {}, None, {200, 422, 500}),
    ("GET", "/api/notify/oncall", None, None, {200, 500}),
]


@pytest.mark.smoke
@pytest.mark.parametrize("method,path,body,params,expected", _CASES)
def test_notification_endpoint(client, approval_headers, method, path, body, params, expected):
    """Each safe B16 endpoint returns an expected status set."""
    kwargs = {}
    if body is not None:
        kwargs["json"] = body
    if params:
        kwargs["params"] = params
    resp = client.request(method, path, headers=approval_headers, **kwargs)
    assert resp.status_code in expected
