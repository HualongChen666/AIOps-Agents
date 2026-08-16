# -*- coding: utf-8 -*-
"""Real branch-coverage tests for api/advanced_ai_router.py.

These tests use TestClient against the real main.app with the advanced AI
add-on router mounted (ENABLE_ADDONS=true, LLM_ROUTER_ENABLED=true).  No
mocks or stubs are used; all calls exercise the real router and the real
core/advanced_ai_capabilities implementation behind it.
"""

import importlib
import os
import uuid

import pytest
from fastapi.testclient import TestClient

# Force the real add-on AI router to be mounted.
os.environ["ENABLE_ADDONS"] = "true"
os.environ["LLM_ROUTER_ENABLED"] = "true"
os.environ["AIOPS_DISABLE_SECURITY_SCAN"] = "1"

import config  # noqa: E402

importlib.reload(config)
import main  # noqa: E402

importlib.reload(main)
from main import app  # noqa: E402


@pytest.fixture(scope="module")
def advanced_ai_client():
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client


@pytest.fixture
def admin_headers(advanced_ai_client):
    resp = advanced_ai_client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    assert resp.status_code == 200, f"login failed: {resp.text}"
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _ts_point(n, value):
    return {
        "timestamp": f"2026-08-01T{n:02d}:00:00Z",
        "value": value,
    }


def test_predict_time_series_valid(advanced_ai_client, admin_headers):
    data = [_ts_point(i, 10.0 + i) for i in range(11)]
    # Include one invalid data point to exercise the try/except parsing branch.
    data.insert(3, {"timestamp": "not-a-timestamp"})
    r = advanced_ai_client.post(
        "/api/v1/ai-advanced/predict/time-series",
        json={"historical_data": data, "prediction_horizon": 5},
        headers=admin_headers,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "success"
    assert "prediction" in body


def test_predict_time_series_insufficient_data(advanced_ai_client, admin_headers):
    r = advanced_ai_client.post(
        "/api/v1/ai-advanced/predict/time-series",
        json={"historical_data": [{"timestamp": "2026-08-01T00:00:00Z", "value": 1.0}]},
        headers=admin_headers,
    )
    assert r.status_code == 400


def test_predict_anomalies(advanced_ai_client, admin_headers):
    baseline = [50.0 + i for i in range(15)]
    r = advanced_ai_client.post(
        "/api/v1/ai-advanced/predict/anomalies",
        json={
            "current_data": {"cpu_usage": 95.5},
            "historical_baseline": {"cpu_usage": baseline},
            "threshold_std": 1.5,
        },
        headers=admin_headers,
    )
    assert r.status_code == 200
    assert r.json()["status"] == "success"


def test_adaptive_learning_update_valid_and_invalid(advanced_ai_client, admin_headers):
    r = advanced_ai_client.post(
        "/api/v1/ai-advanced/learning/update",
        json={
            "new_data": {"feature_a": 1.0, "feature_b": 2.0},
            "feedback": {"score": 0.9},
            "learning_mode": "online",
        },
        headers=admin_headers,
    )
    assert r.status_code == 200

    r2 = advanced_ai_client.post(
        "/api/v1/ai-advanced/learning/update",
        json={
            "new_data": {},
            "feedback": {},
            "learning_mode": "not-a-mode",
        },
        headers=admin_headers,
    )
    assert r2.status_code == 400


def test_natural_language_interaction_and_context(advanced_ai_client, admin_headers):
    conversation_id = f"conv-{uuid.uuid4().hex[:8]}"
    r = advanced_ai_client.post(
        "/api/v1/ai-advanced/conversation",
        json={
            "user_input": "check system status",
            "conversation_id": conversation_id,
            "user_id": "test-user",
        },
        headers=admin_headers,
    )
    assert r.status_code == 200
    assert r.json()["status"] == "success"

    r2 = advanced_ai_client.get(
        f"/api/v1/ai-advanced/conversation/{conversation_id}",
        headers=admin_headers,
    )
    assert r2.status_code == 200
    assert r2.json()["status"] == "success"


def test_get_conversation_context_not_found(advanced_ai_client, admin_headers):
    r = advanced_ai_client.get(
        f"/api/v1/ai-advanced/conversation/missing-{uuid.uuid4().hex[:8]}",
        headers=admin_headers,
    )
    assert r.status_code == 404


def test_explain_decision(advanced_ai_client, admin_headers):
    r = advanced_ai_client.post(
        "/api/v1/ai-advanced/explain",
        json={
            "decision": "restart_service",
            "decision_context": {"cpu": 0.95, "memory": 0.88},
            "decision_type": "auto_heal",
        },
        headers=admin_headers,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "success"
    assert "explanation" in body


def test_continuous_knowledge_learning_and_knowledge_base(advanced_ai_client, admin_headers):
    r = advanced_ai_client.post(
        "/api/v1/ai-advanced/knowledge/learn",
        json={
            "experience_data": {"cpu": 95.0, "action": "restart"},
            "outcome": "success",
        },
        headers=admin_headers,
    )
    assert r.status_code == 200
    assert r.json()["status"] == "success"

    # List whole knowledge base (no category filter).
    r2 = advanced_ai_client.get("/api/v1/ai-advanced/knowledge", headers=admin_headers)
    assert r2.status_code == 200
    assert r2.json()["status"] == "success"

    # Filter by a known category produced by _extract_knowledge.
    r3 = advanced_ai_client.get(
        "/api/v1/ai-advanced/knowledge?category=cpu_value&limit=5",
        headers=admin_headers,
    )
    assert r3.status_code == 200
    assert r3.json()["status"] == "success"

    # Unknown category should return 404.
    r4 = advanced_ai_client.get(
        "/api/v1/ai-advanced/knowledge?category=nonexistent",
        headers=admin_headers,
    )
    assert r4.status_code == 404


def test_get_ai_statistics(advanced_ai_client, admin_headers):
    r = advanced_ai_client.get("/api/v1/ai-advanced/statistics", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["status"] == "success"


def test_get_learning_history(advanced_ai_client, admin_headers):
    r = advanced_ai_client.get(
        "/api/v1/ai-advanced/learning/history?limit=10",
        headers=admin_headers,
    )
    assert r.status_code == 200
    assert r.json()["status"] == "success"


def test_get_prediction_history(advanced_ai_client, admin_headers):
    # No filter.
    r1 = advanced_ai_client.get(
        "/api/v1/ai-advanced/predictions/history?limit=10",
        headers=admin_headers,
    )
    assert r1.status_code == 200
    assert r1.json()["status"] == "success"

    # Valid prediction type filter.
    r2 = advanced_ai_client.get(
        "/api/v1/ai-advanced/predictions/history?prediction_type=time_series&limit=5",
        headers=admin_headers,
    )
    assert r2.status_code == 200
    assert r2.json()["status"] == "success"

    # Invalid prediction type should return 400.
    r3 = advanced_ai_client.get(
        "/api/v1/ai-advanced/predictions/history?prediction_type=invalid_type",
        headers=admin_headers,
    )
    assert r3.status_code == 400


def test_delete_conversation_found_and_not_found(advanced_ai_client, admin_headers):
    # Not-found first.
    r = advanced_ai_client.delete(
        f"/api/v1/ai-advanced/conversation/missing-{uuid.uuid4().hex[:8]}",
        headers=admin_headers,
    )
    assert r.status_code == 404

    # Create and then delete.
    conversation_id = f"conv-{uuid.uuid4().hex[:8]}"
    advanced_ai_client.post(
        "/api/v1/ai-advanced/conversation",
        json={
            "user_input": "restart the database",
            "conversation_id": conversation_id,
            "user_id": "test-user",
        },
        headers=admin_headers,
    )
    r2 = advanced_ai_client.delete(
        f"/api/v1/ai-advanced/conversation/{conversation_id}",
        headers=admin_headers,
    )
    assert r2.status_code == 200
    assert r2.json()["status"] == "success"
