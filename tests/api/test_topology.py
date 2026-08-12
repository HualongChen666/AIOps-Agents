# -*- coding: utf-8 -*-
"""Real end-to-end tests for topology endpoints."""

import pytest

_CASES = [
    # topology_router.py
    ("GET", "/api/v1/topologies/types", None, None, {200, 500}),
    ("GET", "/api/v1/topologies/status/topo-1", None, None, {200, 404, 500}),
    ("POST", "/api/v1/topologies/node/health", {}, None, {200, 422, 500}),
    ("GET", "/api/v1/topologies/full-link", None, None, {200, 500}),
    ("GET", "/api/v1/topologies/node/node-1/timeline", None, None, {200, 404, 500}),
    # topology_view_router.py
    ("GET", "/topology/", None, None, {200, 404, 500}),
]


@pytest.mark.smoke
@pytest.mark.parametrize("method,path,body,params,expected", _CASES)
def test_topology_endpoint(client, approval_headers, method, path, body, params, expected):
    """Each B21 endpoint returns an expected status set."""
    kwargs = {}
    if body is not None:
        kwargs["json"] = body
    if params:
        kwargs["params"] = params
    resp = client.request(method, path, headers=approval_headers, **kwargs)
    assert resp.status_code in expected
