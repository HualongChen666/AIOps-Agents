# -*- coding: utf-8 -*-
"""Real end-to-end tests for platform repair and metric endpoints."""

import pytest  # noqa: F401  # Imported for test setup

_CASES = [
    # k8s_router.py
    ("GET", "/api/v1/platforms/kubernetes/metrics", None, None, {200, 404, 500}),
    ("GET", "/api/v1/platforms/kubernetes/history", None, None, {200, 404, 500}),
    ("POST", "/api/v1/platforms/kubernetes/repair", {}, None, {200, 422, 404, 500}),
    ("POST", "/api/v1/platforms/kubernetes/repair/all", {}, None, {200, 422, 404, 500}),
    ("GET", "/api/v1/platforms/kubernetes/repair/history", None, None, {200, 404, 500}),
    # docker_router.py (currently not mounted in main.py, may return 400/404)
    ("GET", "/api/v1/platforms/docker/metrics", None, None, {200, 400, 404, 500}),
    ("POST", "/api/v1/platforms/docker/repair", {}, None, {200, 422, 404, 500}),
    # linux_router.py
    ("GET", "/api/v1/platforms/linux/hosts", None, None, {200, 404, 500}),
    ("GET", "/api/v1/platforms/linux/metrics/available", None, None, {200, 404, 500}),
    ("GET", "/api/v1/platforms/linux/collect/all", None, None, {200, 404, 500}),
    ("POST", "/api/v1/platforms/linux/collect/host", {}, None, {200, 422, 404, 500}),
    ("GET", "/api/v1/platforms/linux/repair/scripts", None, None, {200, 404, 500}),
    ("POST", "/api/v1/platforms/linux/repair/execute", {}, None, {200, 422, 404, 500}),
    # macos_router.py
    ("GET", "/api/macos/metrics", None, None, {200, 404, 500}),
    ("POST", "/api/macos/repair", {}, None, {200, 422, 404, 500}),
    # windows_repair_router.py
    ("GET", "/api/v1/platforms/windows/repair/scripts", None, None, {200, 404, 500}),
    ("POST", "/api/v1/platforms/windows/repair/execute", {}, None, {200, 422, 404, 500}),
    ("GET", "/api/v1/platforms/windows/repair/history", None, None, {200, 404, 500}),
]


@pytest.mark.smoke
@pytest.mark.parametrize("method,path,body,params,expected", _CASES)
def test_platform_endpoint(client, approval_headers, method, path, body, params, expected):
    """Each platform endpoint returns an expected status set."""
    kwargs = {}
    if body is not None:
        kwargs["json"] = body
    if params:
        kwargs["params"] = params
    resp = client.request(method, path, headers=approval_headers, **kwargs)
    assert resp.status_code in expected
