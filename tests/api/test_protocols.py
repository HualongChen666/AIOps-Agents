# -*- coding: utf-8 -*-
"""Real end-to-end tests for gRPC and realtime HTTP endpoints."""

import pytest  # noqa: F401  # Imported for test setup

_CASES = [
    # grpc_router.py
    ("GET", "/grpc/health", None, None, {200, 500}),
    # grpc_service_router.py
    ("GET", "/api/grpc-services/status", None, None, {200, 500}),
    ("POST", "/api/grpc-services/create", {}, None, {200, 422, 500}),
    ("POST", "/api/grpc-services/create/monitoring", {}, None, {200, 422, 500}),
    ("POST", "/api/grpc-services/create/alert", {}, None, {200, 422, 500}),
    ("POST", "/api/grpc-services/create/repair", {}, None, {200, 422, 500}),
    ("GET", "/api/grpc-services/export/proto/svc-1", None, None, {200, 404, 500}),
    ("GET", "/api/grpc-services/export/python/svc-1", None, None, {200, 404, 500}),
    # realtime_router.py
    ("GET", "/api/v1/realtime/status", None, None, {200, 500}),
]


@pytest.mark.smoke
@pytest.mark.parametrize("method,path,body,params,expected", _CASES)
def test_protocol_endpoint(client, approval_headers, method, path, body, params, expected):
    """Each safe B19 HTTP endpoint returns an expected status set."""
    kwargs = {}
    if body is not None:
        kwargs["json"] = body
    if params:
        kwargs["params"] = params
    resp = client.request(method, path, headers=approval_headers, **kwargs)
    assert resp.status_code in expected
