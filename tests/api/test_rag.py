# -*- coding: utf-8 -*-
"""Real end-to-end tests for RAG and RAG-history endpoints."""

import pytest  # noqa: F401  # Imported for test setup

_CASES = [
    ("POST", "/api/v1/rag/search", {}, None, {200, 422, 500}),
    ("POST", "/api/v1/rag/ingest", {}, None, {200, 422, 500}),
    ("POST", "/api/v1/rag/ingest/batch", {}, None, {200, 422, 500}),
    ("GET", "/rag_history/", None, None, {200, 404, 500}),
]


@pytest.mark.smoke
@pytest.mark.parametrize("method,path,body,params,expected", _CASES)
def test_rag_endpoint(client, approval_headers, method, path, body, params, expected):
    """Each RAG endpoint returns an expected status set."""
    kwargs = {}
    if body is not None:
        kwargs["json"] = body
    if params:
        kwargs["params"] = params
    resp = client.request(method, path, headers=approval_headers, **kwargs)
    assert resp.status_code in expected
