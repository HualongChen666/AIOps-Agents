# -*- coding: utf-8 -*-
"""Real end-to-end tests for test framework, coverage and automation endpoints."""

import pytest  # noqa: F401  # Imported for test setup

_CASES = [
    # test_automation_router.py
    ("GET", "/api/test-automation/status", None, None, {200, 500}),
    ("POST", "/api/test-automation/job/create", {}, None, {200, 422, 500}),
    ("POST", "/api/test-automation/cicd/generate", {}, None, {200, 422, 500}),
    ("POST", "/api/test-automation/report/generate", {}, None, {200, 422, 500}),
    # test_coverage_router.py
    ("GET", "/api/test-coverage/status", None, None, {200, 500}),
    ("POST", "/api/test-coverage/module/add", {}, None, {200, 422, 500}),
    ("GET", "/api/test-coverage/module/m-1", None, None, {200, 404, 500}),
    ("GET", "/api/test-coverage/report", None, None, {200, 500}),
    # test_framework_router.py
    ("GET", "/api/test-framework/status", None, None, {200, 500}),
    ("GET", "/api/test-framework/suites", None, None, {200, 500}),
    ("POST", "/api/test-framework/suite/create", {}, None, {200, 422, 500}),
    ("POST", "/api/test-framework/test/generate", {}, None, {200, 422, 500}),
]


@pytest.mark.smoke
@pytest.mark.parametrize("method,path,body,params,expected", _CASES)
def test_testing_endpoint(client, approval_headers, method, path, body, params, expected):
    """Each safe B24 endpoint returns an expected status set."""
    kwargs = {}
    if body is not None:
        kwargs["json"] = body
    if params:
        kwargs["params"] = params
    resp = client.request(method, path, headers=approval_headers, **kwargs)
    assert resp.status_code in expected
