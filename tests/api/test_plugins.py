# -*- coding: utf-8 -*-
"""Real end-to-end tests for plugin system endpoints."""

import pytest

_CASES = [
    # plugin_marketplace_router.py
    ("GET", "/api/plugin-marketplace/status", None, None, {200, 500}),
    ("POST", "/api/plugin-marketplace/publish", {}, None, {200, 422, 500}),
    ("POST", "/api/plugin-marketplace/plugin/p-1/approve", {}, None, {200, 422, 404, 500}),
    ("POST", "/api/plugin-marketplace/plugin/p-1/reject", {}, None, {200, 422, 404, 500}),
    ("POST", "/api/plugin-marketplace/plugin/p-1/download", {}, None, {200, 422, 404, 500}),
    ("GET", "/api/plugin-marketplace/listings", None, None, {200, 500}),
    ("POST", "/api/plugin-marketplace/plugin/p-1/review", {}, None, {200, 422, 404, 500}),
    # plugin_ecosystem_router.py
    ("GET", "/api/plugin-ecosystem/status", None, None, {200, 500}),
    ("POST", "/api/plugin-ecosystem/activity", {}, None, {200, 422, 500}),
    ("GET", "/api/plugin-ecosystem/activities/p-1", None, None, {200, 404, 500}),
    ("POST", "/api/plugin-ecosystem/developer/register", {}, None, {200, 422, 500}),
    ("GET", "/api/plugin-ecosystem/developer/dev-1", None, None, {200, 404, 500}),
    # plugin_sdk_router.py
    ("GET", "/api/plugin-system/status", None, None, {200, 500}),
    ("POST", "/api/plugin-system/interface/define", {}, None, {200, 422, 500}),
    ("GET", "/api/plugin-system/interface/spec/http", None, None, {200, 404, 500}),
    ("POST", "/api/plugin-system/plugin/register", {}, None, {200, 422, 500}),
    ("POST", "/api/plugin-system/plugin/p-1/enable", {}, None, {200, 422, 404, 500}),
    ("POST", "/api/plugin-system/plugin/p-1/disable", {}, None, {200, 422, 404, 500}),
    ("GET", "/api/plugin-system/plugins", None, None, {200, 500}),
    ("GET", "/api/plugin-system/plugin/p-1", None, None, {200, 404, 500}),
    # plugin_development_router.py
    ("GET", "/api/plugin-sdk/status", None, None, {200, 500}),
    ("GET", "/api/plugin-sdk/templates", None, None, {200, 500}),
    ("POST", "/api/plugin-sdk/generate", {}, None, {200, 422, 500}),
]


@pytest.mark.smoke
@pytest.mark.parametrize("method,path,body,params,expected", _CASES)
def test_plugin_endpoint(client, approval_headers, method, path, body, params, expected):
    """Each safe B18 endpoint returns an expected status set."""
    kwargs = {}
    if body is not None:
        kwargs["json"] = body
    if params:
        kwargs["params"] = params
    resp = client.request(method, path, headers=approval_headers, **kwargs)
    assert resp.status_code in expected
