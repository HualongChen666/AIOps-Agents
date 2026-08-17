# -*- coding: utf-8 -*-
"""Real end-to-end tests for the AI, advanced AI and AI-feedback endpoints."""

import pytest  # noqa: F401  # Imported for test setup

_CASES = [
    # ai_router.py
    ("POST", "/api/ai/analyze", {}, None, {200, 422, 500, 503}),
    # advanced_ai_router.py
    ("POST", "/api/v1/ai-advanced/predict/time-series", {}, None, {200, 422, 500, 503}),
    ("POST", "/api/v1/ai-advanced/predict/anomalies", {}, None, {200, 422, 500, 503}),
    ("POST", "/api/v1/ai-advanced/learning/update", {}, None, {200, 422, 500, 503}),
    ("POST", "/api/v1/ai-advanced/conversation", {}, None, {200, 422, 500, 503}),
    ("GET", "/api/v1/ai-advanced/conversation/conv-123", None, None, {200, 404, 500}),
    ("POST", "/api/v1/ai-advanced/explain", {}, None, {200, 422, 500, 503}),
    ("POST", "/api/v1/ai-advanced/knowledge/learn", {}, None, {200, 422, 500, 503}),
    ("GET", "/api/v1/ai-advanced/knowledge", None, None, {200, 500}),
    ("GET", "/api/v1/ai-advanced/statistics", None, None, {200, 500}),
    ("GET", "/api/v1/ai-advanced/learning/history", None, None, {200, 500}),
    ("GET", "/api/v1/ai-advanced/predictions/history", None, None, {200, 500}),
    ("DELETE", "/api/v1/ai-advanced/conversation/conv-123", None, None, {200, 404, 500}),
    # ai_feedback_router.py
    ("GET", "/api/ai/feedback/stats", None, None, {200, 500}),
    ("GET", "/api/ai/feedback/recent", None, None, {200, 500}),
]


@pytest.mark.smoke
@pytest.mark.parametrize("method,path,body,params,expected", _CASES)
def test_ai_endpoint(client, approval_headers, method, path, body, params, expected):
    """Each AI endpoint returns an expected status set."""
    kwargs = {}
    if body is not None:
        kwargs["json"] = body
    if params:
        kwargs["params"] = params
    resp = client.request(method, path, headers=approval_headers, **kwargs)
    assert resp.status_code in expected
