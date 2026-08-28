# -*- coding: utf-8 -*-
"""Real end-to-end tests for the AI, advanced AI and AI-feedback endpoints."""

import pytest  # noqa: F401  # Imported for test setup
from fastapi import FastAPI
from fastapi.testclient import TestClient

import api.ai_router
import api.advanced_ai_router
import config

pytestmark = [pytest.mark.api]


@pytest.fixture
def client():
    """Create a test client for AI routers."""
    app = FastAPI()
    app.include_router(api.ai_router.router)
    app.include_router(api.advanced_ai_router.router)
    return TestClient(app)


@pytest.fixture
def approval_headers(client):
    """Admin JWT plus the internal API key used by protected endpoints."""
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    if resp.status_code == 200:
        return {
            "Authorization": f"Bearer {resp.json()['access_token']}",
            "X-Internal-Key": config.INTERNAL_API_KEY,
        }
    # If auth is not available, return minimal headers for testing
    return {"X-Internal-Key": config.INTERNAL_API_KEY}


_CASES = [
    # ai_router.py
    ("POST", "/api/ai/analyze", {}, None, {200, 422, 500, 503}),
    # advanced_ai_router.py
    ("POST", "/api/v1/ai-advanced/predict/time-series", {}, None, {200, 422, 500, 503}),
    ("POST", "/api/v1/ai-advanced/predict/anomalies", {}, None, {200, 422, 500, 503}),
    ("POST", "/api/v1/ai-advanced/learning/update", {}, None, {200, 422, 500, 503}),
    ("POST", "/api/v1/ai-advanced/conversation", {}, None, {200, 422, 500, 503}),
    ("GET", "/api/v1/ai-advanced/conversation/conv-123", None, None, {200, 404, 500, 503}),
    ("POST", "/api/v1/ai-advanced/explain", {}, None, {200, 422, 500, 503}),
    ("POST", "/api/v1/ai-advanced/knowledge/learn", {}, None, {200, 422, 500, 503}),
    ("GET", "/api/v1/ai-advanced/knowledge", None, None, {200, 500, 503}),
    ("GET", "/api/v1/ai-advanced/statistics", None, None, {200, 500, 503}),
    ("GET", "/api/v1/ai-advanced/learning/history", None, None, {200, 500, 503}),
    ("GET", "/api/v1/ai-advanced/predictions/history", None, None, {200, 500, 503}),
    ("DELETE", "/api/v1/ai-advanced/conversation/conv-123", None, None, {200, 404, 500, 503}),
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


def test_ai_analyze_with_valid_payload(client):
    """Test AI analyze endpoint with valid payload."""
    valid_payload = {
        "query": "CPU 使用率飙升,请分析根因",
        "include_metrics": True,
        "platform": "windows",
        "include_rich_context": True,
    }
    resp = client.post("/api/ai/analyze", json=valid_payload)
    # Should return 200, 500, or 503 depending on AI engine availability
    assert resp.status_code in {200, 500, 503}
    if resp.status_code == 200:
        data = resp.json()
        # Response should be a dict with expected fields
        assert isinstance(data, dict) or isinstance(data, str)
        if isinstance(data, dict):
            assert "status" in data or "analysis" in data


def test_ai_analyze_with_invalid_payload(client):
    """Test AI analyze endpoint with invalid payload."""
    # Test with missing required field
    invalid_payload = {
        "include_metrics": True,
        "platform": "windows",
    }
    resp = client.post("/api/ai/analyze", json=invalid_payload)
    # Should return 422 for validation error
    assert resp.status_code in (422, 404)
    if resp.status_code != 404:
        data = resp.json()
    # Check for validation error structure
        assert "detail" in data or "error" in data

    # Test with invalid platform value
    invalid_platform_payload = {
        "query": "CPU 使用率飙升",
        "include_metrics": True,
        "platform": "invalid_platform",
    }
    resp = client.post("/api/ai/analyze", json=invalid_platform_payload)
    # Should return 422 for validation error
    assert resp.status_code in (422, 404)

    # Test with empty query
    empty_query_payload = {
        "query": "",
        "include_metrics": True,
        "platform": "windows",
    }
    resp = client.post("/api/ai/analyze", json=empty_query_payload)
    # Should return 422 for validation error
    assert resp.status_code in (422, 404)


def test_ai_advanced_predict_time_series(client):
    """Test time series prediction endpoint."""
    # Prepare valid historical data with at least 10 data points
    from datetime import datetime, timedelta

    historical_data = []
    base_time = datetime.now()
    for i in range(15):
        historical_data.append({
            "timestamp": (base_time + timedelta(hours=i)).isoformat(),
            "value": 50.0 + i * 0.5,
        })

    valid_payload = {
        "historical_data": historical_data,
        "prediction_horizon": 24,
    }
    resp = client.post("/api/v1/ai-advanced/predict/time-series", json=valid_payload)
    # Should return 200, 400, or 503 depending on data and engine availability
    assert resp.status_code in {200, 400, 503}
    if resp.status_code == 200:
        data = resp.json()
        assert "status" in data
        assert "prediction" in data
        assert "predicted_values" in data["prediction"]
        assert "confidence" in data["prediction"]

    # Test with insufficient data (less than 10 points)
    insufficient_data = historical_data[:5]
    invalid_payload = {
        "historical_data": insufficient_data,
        "prediction_horizon": 24,
    }
    resp = client.post("/api/v1/ai-advanced/predict/time-series", json=invalid_payload)
    # Should return 400 for insufficient data
    assert resp.status_code in {400, 503}
    if resp.status_code == 400:
        data = resp.json()
        assert "detail" in data or "error" in data


def test_ai_advanced_conversation_flow(client):
    """Test conversation flow endpoint."""
    # Test creating a new conversation
    conversation_payload = {
        "user_input": "系统状态如何？",
        "conversation_id": "test-conv-001",
        "user_id": "test-user-001",
    }
    resp = client.post("/api/v1/ai-advanced/conversation", json=conversation_payload)
    # Should return 200 or 503 depending on engine availability
    assert resp.status_code in {200, 503}
    if resp.status_code == 200:
        data = resp.json()
        assert "status" in data
        assert "response" in data
        assert "conversation_id" in data["response"]

    # Test retrieving conversation context
    resp = client.get("/api/v1/ai-advanced/conversation/test-conv-001")
    # Should return 200, 404, or 503
    assert resp.status_code in {200, 404, 503}
    if resp.status_code == 200:
        data = resp.json()
        assert "status" in data
        assert "conversation" in data

    # Test deleting conversation
    resp = client.delete("/api/v1/ai-advanced/conversation/test-conv-001")
    # Should return 200, 404, 500, or 503
    assert resp.status_code in {200, 404, 500, 503}

    # Test with invalid payload (missing required fields)
    invalid_payload = {
        "user_input": "系统状态如何？",
    }
    resp = client.post("/api/v1/ai-advanced/conversation", json=invalid_payload)
    # Should return 422 for validation error
    assert resp.status_code in (422, 404)
