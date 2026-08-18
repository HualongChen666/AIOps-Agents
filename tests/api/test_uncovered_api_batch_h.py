# -*- coding: utf-8 -*-
"""Batch H API coverage tests."""

import datetime
import sys  # noqa: F401  # Imported for test setup
from dataclasses import dataclass
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest  # noqa: F401  # Imported for test setup

pytestmark = [pytest.mark.api]


# ---------------------------------------------------------------------------
# Shared fake helpers
# ---------------------------------------------------------------------------
class _FakePredictionType:
    VALID = {"time_series", "anomaly", "classification", "regression"}

    def __init__(self, value):
        if value not in self.VALID:
            raise ValueError(value)
        self.value = value

    def __eq__(self, other):
        if isinstance(other, _FakePredictionType):
            return self.value == other.value
        return self.value == other

    def __hash__(self):
        return hash(self.value)


class _FakeLearningMode:
    VALID = {"online", "batch", "reinforcement"}

    def __init__(self, value):
        if value not in self.VALID:
            raise ValueError(value)
        self.value = value


class _FakeAdvancedAI:
    def __init__(self):
        self.learning_updates = [
            SimpleNamespace(
                update_id="u1",
                learning_mode=_FakeLearningMode("online"),
                performance_improvement=0.1,
                new_samples=10,
                model_version="v1",
                update_timestamp=datetime.datetime.now(),
            )
        ]
        self.prediction_history = [
            SimpleNamespace(
                prediction_type=_FakePredictionType("time_series"),
                confidence=0.9,
                model_used="test",
                prediction_timestamp=datetime.datetime.now(),
                metadata={},
            )
        ]
        self.knowledge_base = {  # noqa: F841  # Variable for test verification
            "ops": [
                {"timestamp": "2026-01-01T00:00:00Z", "content": "x"},
                {"timestamp": "2026-01-02T00:00:00Z", "content": "y"},
            ]
        }
        self.conversation_contexts = {
            "c1": SimpleNamespace(
                conversation_id="c1",
                user_id="u1",
                current_intent="test",
                messages=[{"role": "user", "content": "hi"}],
                started_at=datetime.datetime.now(),
                last_activity=datetime.datetime.now(),
                context_variables={},
            )
        }

    async def predict_time_series(self, *args, **kwargs):
        return SimpleNamespace(
            prediction_type=_FakePredictionType("time_series"),
            predicted_values=[1.0, 2.0],
            confidence=0.95,
            model_used="test",
            prediction_timestamp=datetime.datetime.now(),
            metadata={"horizon": 24},
        )

    async def predict_anomalies(self, *args, **kwargs):
        return SimpleNamespace(
            prediction_type=_FakePredictionType("anomaly"),
            predicted_values=[],
            confidence=0.9,
            model_used="test",
            prediction_timestamp=datetime.datetime.now(),
            metadata={
                "anomalies": [{"metric": "cpu"}],
                "anomaly_scores": {"cpu": 2.5},
                "total_metrics": 1,
            },
        )

    async def adaptive_learning_update(self, *args, **kwargs):
        return SimpleNamespace(
            update_id="u1",
            learning_mode=_FakeLearningMode("online"),
            performance_improvement=0.1,
            new_samples=10,
            model_version="v1",
            update_timestamp=datetime.datetime.now(),
            metadata={},
        )

    async def natural_language_interaction(self, *args, **kwargs):
        return {
            "conversation_id": "c1",
            "user_message": "hi",
            "ai_response": "ok",
            "intent": "test",
        }

    async def explain_decision(self, *args, **kwargs):
        return SimpleNamespace(
            decision_id="d1",
            decision="restart",
            confidence=0.8,
            reasoning=["cpu high"],
            feature_importance={"cpu": 0.8},
            alternative_options=[{"name": "scale"}],
            decision_timestamp=datetime.datetime.now(),
        )

    async def continuous_knowledge_learning(self, *args, **kwargs):
        return {"knowledge_id": "k1", "experience_type": "repair"}

    def get_capabilities_summary(self):
        return {"total": 1}


def _ten_ts_points():
    base = datetime.datetime(2026, 1, 1, 0, 0, 0)  # noqa: F841  # Variable for test verification
    return [
        {
            "timestamp": (base + datetime.timedelta(hours=i)).isoformat() + "Z",
            "value": float(i),
        }
        for i in range(10)
    ]


# ---------------------------------------------------------------------------
# Docker router
# ---------------------------------------------------------------------------
def test_docker_metrics_and_repair(client, admin_headers, monkeypatch):
    import api.docker_router as mod

    monkeypatch.setattr(mod, "DOCKER_HOSTS", [{"host": "h1"}])
    monkeypatch.setattr(mod, "collect_docker", lambda cfg: {"host": cfg["host"], "containers": []})
    monkeypatch.setattr(
        mod, "execute_repair_sync", AsyncMock(return_value={"success": True, "output": "ok"})
    )

    r = client.get("/api/v1/platforms/docker/metrics", headers=admin_headers)
    assert r.status_code == 200
    assert r.json() == [{"host": "h1", "containers": []}]

    r = client.post(
        "/api/v1/platforms/docker/repair",
        headers=admin_headers,
        json={"host": "h1", "script_name": "ps", "args": {}},
    )
    assert r.status_code == 200
    assert r.json()["success"] is True


def test_docker_metrics_empty_hosts(client, admin_headers, monkeypatch):
    import api.docker_router as mod

    monkeypatch.setattr(mod, "DOCKER_HOSTS", [])
    r = client.get("/api/v1/platforms/docker/metrics", headers=admin_headers)
    assert r.status_code == 400


def test_docker_repair_404_and_500(client, admin_headers, monkeypatch):
    import api.docker_router as mod

    monkeypatch.setattr(mod, "DOCKER_HOSTS", [{"host": "h2"}])
    r = client.post(
        "/api/v1/platforms/docker/repair",
        headers=admin_headers,
        json={"host": "h1", "script_name": "ps", "args": {}},
    )
    assert r.status_code == 404

    monkeypatch.setattr(mod, "DOCKER_HOSTS", [{"host": "h1"}])
    monkeypatch.setattr(mod, "execute_repair_sync", AsyncMock(side_effect=RuntimeError("boom")))
    r = client.post(
        "/api/v1/platforms/docker/repair",
        headers=admin_headers,
        json={"host": "h1", "script_name": "ps", "args": {}},
    )
    assert r.status_code == 500


# ---------------------------------------------------------------------------
# Business impact router
# ---------------------------------------------------------------------------
def test_business_impact_happy(client, admin_headers, monkeypatch):
    import api.business_impact_router as mod

    monkeypatch.setattr(
        mod, "list_business_impact_services", AsyncMock(return_value=[{"id": "SVC-1"}])
    )
    monkeypatch.setattr(
        mod, "list_business_impact_ux_metrics", AsyncMock(return_value=[{"id": "UX-1"}])
    )
    monkeypatch.setattr(mod, "assess_business_impact", AsyncMock(return_value={"name": "svc"}))

    r = client.get("/api/v1/business-impact/services", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["status"] == "success"

    r = client.get("/api/v1/business-impact/ux-metrics", headers=admin_headers)
    assert r.status_code == 200

    r = client.get("/api/v1/business-impact/assess/payment-service", headers=admin_headers)
    assert r.status_code == 200


def test_business_impact_errors(client, admin_headers, monkeypatch):
    import api.business_impact_router as mod

    monkeypatch.setattr(
        mod, "list_business_impact_services", AsyncMock(side_effect=RuntimeError("boom"))
    )
    r = client.get("/api/v1/business-impact/services", headers=admin_headers)
    assert r.status_code == 500

    r = client.get("/api/v1/business-impact/assess/payment+service", headers=admin_headers)
    assert r.status_code == 422

    monkeypatch.setattr(mod, "assess_business_impact", AsyncMock(side_effect=RuntimeError("boom")))
    r = client.get("/api/v1/business-impact/assess/payment-service", headers=admin_headers)
    assert r.status_code == 500


# ---------------------------------------------------------------------------
# Tenant router (uses real in-memory engine)
# ---------------------------------------------------------------------------
def test_tenant_crud(client, admin_headers):
    r = client.post(
        "/api/v1/tenants/",
        headers=admin_headers,
        json={"name": "BatchH Test Tenant", "plan": "basic", "status": "active"},
    )
    assert r.status_code == 201
    data = r.json()
    tenant_id = data["id"]
    assert data["name"] == "BatchH Test Tenant"

    r = client.get("/api/v1/tenants/", headers=admin_headers)
    assert r.status_code == 200

    r = client.get(f"/api/v1/tenants/{tenant_id}", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["id"] == tenant_id

    r = client.put(
        f"/api/v1/tenants/{tenant_id}",
        headers=admin_headers,
        json={"name": "Updated"},
    )
    assert r.status_code == 200
    assert r.json()["name"] == "Updated"

    r = client.delete(f"/api/v1/tenants/{tenant_id}", headers=admin_headers)
    assert r.status_code == 204


def test_tenant_errors(client, admin_headers):
    r = client.get("/api/v1/tenants/nonexistent", headers=admin_headers)
    assert r.status_code == 404

    r = client.delete("/api/v1/tenants/nonexistent", headers=admin_headers)
    assert r.status_code == 404

    r = client.post("/api/v1/tenants/", headers=admin_headers, json={"name": ""})
    assert r.status_code == 422

    r = client.put(
        "/api/v1/tenants/nonexistent",
        headers=admin_headers,
        json={"plan": "super"},
    )
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# Anomaly router
# ---------------------------------------------------------------------------
def test_anomaly_endpoints(client, admin_headers, monkeypatch):
    import api.anomaly_router as mod

    monkeypatch.setattr(mod, "detect_all_anomalies", lambda history: [{"id": "a1"}])
    monkeypatch.setattr(mod, "detect_anomalies", lambda history, metric: [{"id": f"{metric}-a"}])

    r = client.get("/api/v1/anomaly/records", headers=admin_headers)
    assert r.status_code == 200
    assert r.json() == [{"id": "a1"}]

    r = client.get("/api/v1/anomaly/statistics", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["total"] == 3

    r = client.post(
        "/api/v1/anomaly/detect",
        headers=admin_headers,
        json={"metric": "cpu", "values": [1, 2, 3]},
    )
    assert r.status_code == 200
    assert r.json()["count"] == 1

    r = client.post(
        "/api/v1/anomaly/detect",
        headers=admin_headers,
        json={},
    )
    assert r.status_code == 200
    assert r.json()["count"] == 1


def test_anomaly_errors(client, admin_headers, monkeypatch):
    import api.anomaly_router as mod

    monkeypatch.setattr(
        mod, "detect_all_anomalies", lambda history: (_ for _ in ()).throw(RuntimeError("boom"))
    )
    r = client.get("/api/v1/anomaly/records", headers=admin_headers)
    assert r.status_code == 500

    monkeypatch.setattr(mod, "detect_all_anomalies", lambda history: [])
    r = client.post(
        "/api/v1/anomaly/detect",
        headers=admin_headers,
        json={"metric": "cpu", "values": "not-a-list"},
    )
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# ITSM router
# ---------------------------------------------------------------------------
def test_itsm_create_and_resolve(client, admin_headers, monkeypatch):
    import api.itsm_router as mod

    monkeypatch.setattr(mod, "SERVICE_NOW_URL", "http://snow.example")
    monkeypatch.setattr(mod, "SERVICE_NOW_TOKEN", "tok")
    monkeypatch.setattr(mod, "JIRA_URL", "http://jira.example")
    monkeypatch.setattr(mod, "JIRA_TOKEN", "tok")
    monkeypatch.setitem(sys.modules, "httpx", None)

    r = client.post(
        "/api/itsm/incident?provider=servicenow",
        headers=admin_headers,
        json={"summary": "s", "description": "d"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "created"

    r = client.post(
        "/api/itsm/incident?provider=jira",
        headers=admin_headers,
        json={"summary": "s"},
    )
    assert r.status_code == 200

    r = client.patch(
        "/api/itsm/incident/123?provider=servicenow",
        headers=admin_headers,
    )
    assert r.status_code == 200
    assert r.json()["status"] == "resolved"


def test_itsm_errors(client, admin_headers, monkeypatch):
    import api.itsm_router as mod

    monkeypatch.setattr(mod, "SERVICE_NOW_URL", "")
    monkeypatch.setattr(mod, "SERVICE_NOW_TOKEN", "")
    r = client.post(
        "/api/itsm/incident?provider=servicenow",
        headers=admin_headers,
        json={},
    )
    assert r.status_code == 500

    r = client.post(
        "/api/itsm/incident?provider=unknown",
        headers=admin_headers,
        json={},
    )
    assert r.status_code == 400


# ---------------------------------------------------------------------------
# Advanced AI router
# ---------------------------------------------------------------------------
def _patch_advanced_ai(monkeypatch):
    import api.advanced_ai_router as mod

    monkeypatch.setattr(mod, "ADVANCED_AI_AVAILABLE", True)
    monkeypatch.setattr(mod, "advanced_ai_capabilities", _FakeAdvancedAI())
    monkeypatch.setattr(mod, "LearningMode", _FakeLearningMode)
    monkeypatch.setattr(mod, "PredictionType", _FakePredictionType)


def test_advanced_ai_predictions(client, admin_headers, monkeypatch):
    _patch_advanced_ai(monkeypatch)

    r = client.post(
        "/api/v1/ai-advanced/predict/time-series",
        headers=admin_headers,
        json={"historical_data": _ten_ts_points(), "prediction_horizon": 5},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "success"

    r = client.post(
        "/api/v1/ai-advanced/predict/anomalies",
        headers=admin_headers,
        json={"current_data": {"cpu": 95.0}, "historical_baseline": {"cpu": [1, 2, 3]}},
    )
    assert r.status_code == 200

    r = client.post(
        "/api/v1/ai-advanced/learning/update",
        headers=admin_headers,
        json={"new_data": {"x": 1}, "feedback": {"x": 0.5}, "learning_mode": "online"},
    )
    assert r.status_code == 200

    r = client.post(
        "/api/v1/ai-advanced/learning/update",
        headers=admin_headers,
        json={"new_data": {}, "feedback": {}, "learning_mode": "invalid"},
    )
    assert r.status_code == 400

    r = client.post(
        "/api/v1/ai-advanced/predict/time-series",
        headers=admin_headers,
        json={"historical_data": [{"timestamp": "2026-01-01T00:00:00Z", "value": 1}]},
    )
    assert r.status_code == 400


def test_advanced_ai_conversation_and_explain(client, admin_headers, monkeypatch):
    _patch_advanced_ai(monkeypatch)

    r = client.post(
        "/api/v1/ai-advanced/conversation",
        headers=admin_headers,
        json={"user_input": "hi", "conversation_id": "c1", "user_id": "u1"},
    )
    assert r.status_code == 200

    r = client.get("/api/v1/ai-advanced/conversation/c1", headers=admin_headers)
    assert r.status_code == 200

    r = client.get("/api/v1/ai-advanced/conversation/missing", headers=admin_headers)
    assert r.status_code == 404

    r = client.post(
        "/api/v1/ai-advanced/explain",
        headers=admin_headers,
        json={"decision": "restart", "decision_context": {"cpu": 90}},
    )
    assert r.status_code == 200

    r = client.post(
        "/api/v1/ai-advanced/knowledge/learn",
        headers=admin_headers,
        json={"experience_data": {"x": 1}, "outcome": "success"},
    )
    assert r.status_code == 200

    r = client.delete("/api/v1/ai-advanced/conversation/c1", headers=admin_headers)
    assert r.status_code == 200

    r = client.delete("/api/v1/ai-advanced/conversation/missing", headers=admin_headers)
    assert r.status_code == 404


def test_advanced_ai_knowledge_and_history(client, admin_headers, monkeypatch):
    _patch_advanced_ai(monkeypatch)

    r = client.get("/api/v1/ai-advanced/knowledge", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["items_count"] == 2

    r = client.get("/api/v1/ai-advanced/knowledge?category=ops", headers=admin_headers)
    assert r.status_code == 200

    r = client.get("/api/v1/ai-advanced/knowledge?category=missing", headers=admin_headers)
    assert r.status_code == 404

    r = client.get("/api/v1/ai-advanced/statistics", headers=admin_headers)
    assert r.status_code == 200

    r = client.get("/api/v1/ai-advanced/learning/history", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["total_updates"] == 1

    r = client.get("/api/v1/ai-advanced/predictions/history", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["total_predictions"] == 1

    r = client.get(
        "/api/v1/ai-advanced/predictions/history?prediction_type=time_series",
        headers=admin_headers,
    )
    assert r.status_code == 200

    r = client.get(
        "/api/v1/ai-advanced/predictions/history?prediction_type=invalid",
        headers=admin_headers,
    )
    assert r.status_code == 400


def test_advanced_ai_unavailable(client, admin_headers, monkeypatch):
    import api.advanced_ai_router as mod

    monkeypatch.setattr(mod, "ADVANCED_AI_AVAILABLE", False)
    r = client.post(
        "/api/v1/ai-advanced/predict/time-series",
        headers=admin_headers,
        json={"historical_data": _ten_ts_points()},
    )
    assert r.status_code == 503


def test_advanced_ai_invalid_data_points(client, admin_headers, monkeypatch):
    """
    Test coverage for lines 179-180: Invalid historical data point handling
    when ValueError or KeyError occurs during data parsing
    """
    _patch_advanced_ai(monkeypatch)

    # Create data with some invalid entries mixed with valid ones
    # Start with 13 valid points, then make 3 invalid to leave 10 valid
    base = datetime.datetime(2026, 1, 1, 0, 0, 0)
    historical_data = [
        {
            "timestamp": (base + datetime.timedelta(hours=i)).isoformat() + "Z",
            "value": float(i),
        }
        for i in range(13)
    ]
    # Add invalid data points that will trigger ValueError or KeyError
    historical_data[3] = {"timestamp": "invalid-timestamp", "value": 3.0}  # Invalid timestamp
    historical_data[7] = {"value": 7.0}  # Missing timestamp key
    historical_data[10] = {"timestamp": "2026-01-01T10:00:00Z", "value": "not-a-number"}  # Invalid value

    r = client.post(
        "/api/v1/ai-advanced/predict/time-series",
        headers=admin_headers,
        json={"historical_data": historical_data, "prediction_horizon": 5},
    )
    # Should succeed because after skipping invalid points, we still have >= 10 valid points
    assert r.status_code == 200
    assert r.json()["status"] == "success"


def test_advanced_ai_all_invalid_data(client, admin_headers, monkeypatch):
    """
    Test when all historical data points are invalid, resulting in insufficient data
    """
    _patch_advanced_ai(monkeypatch)

    # All data points are invalid
    historical_data = [
        {"timestamp": "invalid", "value": 1.0},
        {"value": 2.0},  # Missing timestamp
        {"timestamp": "2026-01-01T00:00:00Z", "value": "invalid"},
    ]

    r = client.post(
        "/api/v1/ai-advanced/predict/time-series",
        headers=admin_headers,
        json={"historical_data": historical_data, "prediction_horizon": 5},
    )
    # Should fail because after skipping all invalid points, we have < 10 valid points
    assert r.status_code == 400
    # The error message is in the response body, check for the Chinese error message
    response_data = r.json()
    assert "历史数据不足" in str(response_data) or "Insufficient" in str(response_data)


def test_advanced_ai_all_endpoints_unavailable(client, admin_headers, monkeypatch):
    """
    Comprehensive test for all ADVANCED_AI_AVAILABLE=False scenarios
    This ensures all 503 error paths are covered (lines 242, 315, 378, 429, 490, 550, 599, 640, 671, 732, 787)
    """
    import api.advanced_ai_router as mod

    monkeypatch.setattr(mod, "ADVANCED_AI_AVAILABLE", False)

    endpoints = [
        ("POST", "/api/v1/ai-advanced/predict/anomalies", {"current_data": {"cpu": 95.0}, "historical_baseline": {"cpu": [1, 2, 3]}}),
        ("POST", "/api/v1/ai-advanced/learning/update", {"new_data": {"x": 1}, "feedback": {"x": 0.5}, "learning_mode": "online"}),
        ("POST", "/api/v1/ai-advanced/conversation", {"user_input": "hi", "conversation_id": "c1", "user_id": "u1"}),
        ("GET", "/api/v1/ai-advanced/conversation/c1", None),
        ("POST", "/api/v1/ai-advanced/explain", {"decision": "restart", "decision_context": {"cpu": 90}}),
        ("POST", "/api/v1/ai-advanced/knowledge/learn", {"experience_data": {"x": 1}, "outcome": "success"}),
        ("GET", "/api/v1/ai-advanced/knowledge", None),
        ("GET", "/api/v1/ai-advanced/statistics", None),
        ("GET", "/api/v1/ai-advanced/learning/history", None),
        ("GET", "/api/v1/ai-advanced/predictions/history", None),
        ("DELETE", "/api/v1/ai-advanced/conversation/c1", None),
    ]

    for method, endpoint, data in endpoints:
        if method == "POST":
            r = client.post(endpoint, headers=admin_headers, json=data)
        elif method == "GET":
            r = client.get(endpoint, headers=admin_headers)
        elif method == "DELETE":
            r = client.delete(endpoint, headers=admin_headers)

        assert r.status_code == 503
        # Check for the error message in the response (may be in different format)
        response_data = r.json()
        assert "高级AI能力不可用" in str(response_data) or "not available" in str(response_data).lower()


# ---------------------------------------------------------------------------
# Plugin SDK router
# ---------------------------------------------------------------------------
def _patch_plugin_sdk(monkeypatch):
    import core.plugin_system_manager as psm

    class FakeManager:
        def get_system_summary(self):
            return {"total_plugins": 1}

        def define_plugin_interface(self, **kwargs):
            return SimpleNamespace(
                interface_id="i1",
                interface_name="I",
                methods=[],
                events=[],
                configuration={},
            )

        def generate_plugin_interface_spec(self, interface_type):
            return {"type": interface_type}

        def register_plugin(self, plugin_id, metadata):
            return True

        def enable_plugin(self, plugin_id):
            return True

        def disable_plugin(self, plugin_id):
            return True

        def list_plugins(self, *args, **kwargs):
            return [{"plugin_id": "p1"}]

        def get_plugin_info(self, plugin_id):
            return None if plugin_id == "missing" else {"plugin_id": plugin_id, "name": "P"}

    monkeypatch.setattr(psm, "get_plugin_system_manager", lambda: FakeManager())


def test_plugin_sdk_happy(client, admin_headers, monkeypatch):
    _patch_plugin_sdk(monkeypatch)

    r = client.get("/api/plugin-system/status", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["status"] == "success"

    r = client.post(
        "/api/plugin-system/interface/define?interface_id=i1&interface_name=I",
        headers=admin_headers,
        json={},
    )
    assert r.status_code == 200

    r = client.get("/api/plugin-system/interface/spec/monitoring", headers=admin_headers)
    assert r.status_code == 200

    r = client.post(
        "/api/plugin-system/plugin/register?plugin_id=p1&name=P&version=1.0.0&description=d&author=a&plugin_type=monitoring",  # noqa: E501  # Line too long (intentional)
        headers=admin_headers,
    )
    assert r.status_code == 200

    r = client.post("/api/plugin-system/plugin/p1/enable", headers=admin_headers)
    assert r.status_code == 200

    r = client.post("/api/plugin-system/plugin/p1/disable", headers=admin_headers)
    assert r.status_code == 200

    r = client.get("/api/plugin-system/plugins", headers=admin_headers)
    assert r.status_code == 200

    r = client.get("/api/plugin-system/plugin/p1", headers=admin_headers)
    assert r.status_code == 200

    r = client.get("/api/plugin-system/plugin/missing", headers=admin_headers)
    assert r.status_code == 404


def test_plugin_sdk_errors(client, admin_headers, monkeypatch):
    _patch_plugin_sdk(monkeypatch)
    import core.plugin_system_manager as psm

    class BoomManager:
        def get_system_summary(self):
            raise RuntimeError("boom")

    monkeypatch.setattr(psm, "get_plugin_system_manager", lambda: BoomManager())
    r = client.get("/api/plugin-system/status", headers=admin_headers)
    assert r.status_code == 500


# ---------------------------------------------------------------------------
# Notify router
# ---------------------------------------------------------------------------
def _patch_notify(monkeypatch, enabled=True):
    import api.notify_router as mod

    cfg = {
        "enabled": enabled,
        "min_level": "critical",
        "wecom_webhook": "http://w",
        "dingtalk_webhook": "http://d",
        "feishu_webhook": "http://f",
        "email_webhook": "http://e",
    }
    monkeypatch.setattr(mod._notify_engine, "NOTIFY_CONFIG", cfg)
    monkeypatch.setattr(
        mod,
        "send_alert_notification",
        AsyncMock(return_value={"wecom": True, "dingtalk": True, "feishu": True}),
    )
    monkeypatch.setattr(mod, "reload_notify_config", lambda: cfg)
    monkeypatch.setattr(mod._notify_engine, "get_notification_status", lambda **k: [{"id": "1"}])
    monkeypatch.setattr(mod._notify_engine, "mark_notification_read", lambda mid, ch: True)

    class FakeAdapter:
        async def lookup_async(self, **kwargs):
            return [
                SimpleNamespace(
                    name="a", email="", phone="", channel="wecom", team="ops", role="oncall"
                )
            ]

    monkeypatch.setattr(mod, "get_oncall_adapter", lambda: FakeAdapter())


def test_notify_happy(client, admin_headers, monkeypatch):
    _patch_notify(monkeypatch, enabled=True)

    r = client.get("/api/notify/config", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["enabled"] is True

    r = client.post(
        "/api/notify/test",
        headers=admin_headers,
        json={"level": "critical", "title": "t", "desc": "d"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

    r = client.post(
        "/api/notify/send",
        headers=admin_headers,
        json={"level": "critical", "title": "t", "desc": "d"},
    )
    assert r.status_code == 200

    r = client.post("/api/notify/reload", headers=admin_headers)
    assert r.status_code == 200

    r = client.get("/api/notify/health", headers=admin_headers)
    assert r.status_code == 200

    r = client.get("/api/notify/status", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["count"] == 1

    r = client.post(
        "/api/notify/read", headers=admin_headers, json={"message_id": "m1", "channel": "wecom"}
    )
    assert r.status_code == 200
    assert r.json()["updated"] is True

    r = client.get("/api/notify/oncall", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["count"] == 1


def test_notify_disabled_and_invalid(client, admin_headers, monkeypatch):
    _patch_notify(monkeypatch, enabled=False)
    r = client.post(
        "/api/notify/test",
        headers=admin_headers,
        json={"level": "critical", "title": "t", "desc": "d"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "skipped"

    r = client.post(
        "/api/notify/send",
        headers=admin_headers,
        json={"level": "critical", "title": "t"},
    )
    assert r.status_code == 422

    r = client.post(
        "/api/notify/send",
        headers=admin_headers,
        json={"level": "foo", "title": "t", "desc": "d"},
    )
    assert r.status_code == 422


def test_notify_errors(client, admin_headers, monkeypatch):
    import api.notify_router as mod

    _patch_notify(monkeypatch, enabled=True)
    monkeypatch.setattr(mod, "send_alert_notification", AsyncMock(side_effect=RuntimeError("boom")))
    r = client.post(
        "/api/notify/test",
        headers=admin_headers,
        json={"level": "critical", "title": "t", "desc": "d"},
    )
    assert r.status_code == 500

    monkeypatch.setattr(
        mod, "reload_notify_config", lambda: (_ for _ in ()).throw(RuntimeError("boom"))
    )
    r = client.post("/api/notify/reload", headers=admin_headers)
    assert r.status_code == 500

    monkeypatch.setattr(
        mod._notify_engine,
        "get_notification_status",
        lambda **k: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    r = client.get("/api/notify/status", headers=admin_headers)
    assert r.status_code == 500

    class BadAdapter:
        async def lookup_async(self, **kwargs):
            raise RuntimeError("boom")

    monkeypatch.setattr(mod, "get_oncall_adapter", lambda: BadAdapter())
    r = client.get("/api/notify/oncall", headers=admin_headers)
    assert r.status_code == 500

    monkeypatch.setattr(mod._notify_engine, "mark_notification_read", lambda mid, ch: False)
    r = client.post(
        "/api/notify/read", headers=admin_headers, json={"message_id": "m1", "channel": "wecom"}
    )
    assert r.status_code == 200
    assert r.json()["status"] == "not_found"


# ---------------------------------------------------------------------------
# Collaboration router
# ---------------------------------------------------------------------------
def _patch_collaboration(monkeypatch):
    import api.collaboration_router as mod

    monkeypatch.setattr(mod, "engine_list_workspaces", lambda *a, **k: [{"id": "ws1"}])
    monkeypatch.setattr(
        mod,
        "engine_get_workspace",
        lambda wid: None if wid == "missing" else {"id": wid, "name": "x"},
    )
    monkeypatch.setattr(mod, "engine_create_workspace", lambda **k: {"id": "new"})
    monkeypatch.setattr(mod, "engine_post_message", lambda *a, **k: {"message": "ok"})
    monkeypatch.setattr(mod, "engine_add_task", lambda *a, **k: {"task": "ok"})
    monkeypatch.setattr(mod, "engine_assign_task", lambda *a, **k: {"task": "ok"})
    monkeypatch.setattr(
        mod, "engine_resolve_workspace", lambda wid: {"id": wid, "status": "resolved"}
    )
    monkeypatch.setattr(mod, "engine_get_active_context", lambda: {"alerts": []})


def test_collaboration_happy(client, admin_headers, monkeypatch):
    _patch_collaboration(monkeypatch)

    r = client.get("/api/v1/collaboration/workspaces", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["workspaces"]

    r = client.get("/api/v1/collaboration/workspaces/ws1", headers=admin_headers)
    assert r.status_code == 200

    r = client.post(
        "/api/v1/collaboration/workspaces",
        headers=admin_headers,
        json={"name": "x"},
    )
    assert r.status_code == 201

    r = client.post(
        "/api/v1/collaboration/workspaces/ws1/messages",
        headers=admin_headers,
        json={"user": "u", "content": "c"},
    )
    assert r.status_code == 200

    r = client.post(
        "/api/v1/collaboration/workspaces/ws1/tasks",
        headers=admin_headers,
        json={"title": "t"},
    )
    assert r.status_code == 200

    r = client.patch(
        "/api/v1/collaboration/workspaces/ws1/tasks/t1",
        headers=admin_headers,
        json={"status": "done"},
    )
    assert r.status_code == 200

    r = client.post("/api/v1/collaboration/workspaces/ws1/resolve", headers=admin_headers)
    assert r.status_code == 200

    r = client.get("/api/v1/collaboration/active-context", headers=admin_headers)
    assert r.status_code == 200


def test_collaboration_errors(client, admin_headers, monkeypatch):
    import api.collaboration_router as mod

    _patch_collaboration(monkeypatch)

    r = client.get("/api/v1/collaboration/workspaces/missing", headers=admin_headers)
    assert r.status_code == 404

    monkeypatch.setattr(
        mod, "engine_create_workspace", lambda **k: (_ for _ in ()).throw(ValueError("bad"))
    )
    r = client.post("/api/v1/collaboration/workspaces", headers=admin_headers, json={"name": "x"})
    assert r.status_code == 400

    monkeypatch.setattr(
        mod, "engine_post_message", lambda *a, **k: (_ for _ in ()).throw(ValueError("missing"))
    )
    r = client.post(
        "/api/v1/collaboration/workspaces/ws1/messages",
        headers=admin_headers,
        json={"user": "u", "content": "c"},
    )
    assert r.status_code == 404

    monkeypatch.setattr(
        mod, "engine_list_workspaces", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom"))
    )
    r = client.get("/api/v1/collaboration/workspaces", headers=admin_headers)
    assert r.status_code == 500

    # Test get_workspace with RuntimeError (lines 117-119)
    monkeypatch.setattr(
        mod, "engine_get_workspace", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("get error"))
    )
    r = client.get("/api/v1/collaboration/workspaces/ws1", headers=admin_headers)
    assert r.status_code == 500

    # Test create_workspace with RuntimeError (lines 146-148)
    monkeypatch.setattr(
        mod, "engine_create_workspace", lambda **k: (_ for _ in ()).throw(RuntimeError("create error"))
    )
    r = client.post("/api/v1/collaboration/workspaces", headers=admin_headers, json={"name": "x"})
    assert r.status_code == 500

    # Test post_message with RuntimeError (lines 166-168)
    monkeypatch.setattr(
        mod, "engine_post_message", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("post error"))
    )
    r = client.post(
        "/api/v1/collaboration/workspaces/ws1/messages",
        headers=admin_headers,
        json={"user": "u", "content": "c"},
    )
    assert r.status_code == 500

    # Test add_task with ValueError (lines 184-185)
    monkeypatch.setattr(
        mod, "engine_add_task", lambda *a, **k: (_ for _ in ()).throw(ValueError("task not found"))
    )
    r = client.post(
        "/api/v1/collaboration/workspaces/ws1/tasks",
        headers=admin_headers,
        json={"title": "t"},
    )
    assert r.status_code == 404

    # Test add_task with RuntimeError (lines 186-188)
    monkeypatch.setattr(
        mod, "engine_add_task", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("add task error"))
    )
    r = client.post(
        "/api/v1/collaboration/workspaces/ws1/tasks",
        headers=admin_headers,
        json={"title": "t"},
    )
    assert r.status_code == 500

    # Test update_task with ValueError (lines 206-207)
    monkeypatch.setattr(
        mod, "engine_assign_task", lambda *a, **k: (_ for _ in ()).throw(ValueError("task not found"))
    )
    r = client.patch(
        "/api/v1/collaboration/workspaces/ws1/tasks/t1",
        headers=admin_headers,
        json={"status": "done"},
    )
    assert r.status_code == 404

    # Test update_task with RuntimeError (lines 208-210)
    monkeypatch.setattr(
        mod, "engine_assign_task", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("update error"))
    )
    r = client.patch(
        "/api/v1/collaboration/workspaces/ws1/tasks/t1",
        headers=admin_headers,
        json={"status": "done"},
    )
    assert r.status_code == 500

    # Test resolve_workspace with ValueError (lines 226-227)
    monkeypatch.setattr(
        mod, "engine_resolve_workspace", lambda *a, **k: (_ for _ in ()).throw(ValueError("workspace not found"))
    )
    r = client.post("/api/v1/collaboration/workspaces/ws1/resolve", headers=admin_headers)
    assert r.status_code == 404

    # Test resolve_workspace with RuntimeError (lines 228-230)
    monkeypatch.setattr(
        mod, "engine_resolve_workspace", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("resolve error"))
    )
    r = client.post("/api/v1/collaboration/workspaces/ws1/resolve", headers=admin_headers)
    assert r.status_code == 500

    # Test get_active_context with RuntimeError (lines 247-249)
    monkeypatch.setattr(
        mod, "engine_get_active_context", lambda: (_ for _ in ()).throw(RuntimeError("context error"))
    )
    r = client.get("/api/v1/collaboration/active-context", headers=admin_headers)
    assert r.status_code == 500


# ---------------------------------------------------------------------------
# Change management router
# ---------------------------------------------------------------------------
def _change_req():
    return {
        "id": "cr1",
        "title": "t",
        "requester": "r",
        "status": "draft",
        "risk_level": "low",
        "affected_services": [],
        "implementation_plan": "",
        "rollback_plan": "",
        "schedule": "",
        "approver": "",
        "description": "",
        "audit_log": [],
    }


def _patch_change(monkeypatch):
    import api.change_management_router as mod

    monkeypatch.setattr(mod, "list_requests", AsyncMock(return_value=[_change_req()]))
    monkeypatch.setattr(mod, "create_request", AsyncMock(return_value=_change_req()))
    monkeypatch.setattr(mod, "get_request", AsyncMock(return_value=_change_req()))
    monkeypatch.setattr(mod, "submit_request", AsyncMock(return_value=_change_req()))
    monkeypatch.setattr(mod, "approve_request", AsyncMock(return_value=_change_req()))
    monkeypatch.setattr(mod, "reject_request", AsyncMock(return_value=_change_req()))
    monkeypatch.setattr(mod, "implement_request", AsyncMock(return_value=_change_req()))
    monkeypatch.setattr(mod, "rollback_request", AsyncMock(return_value=_change_req()))
    monkeypatch.setattr(mod, "record_audit", lambda **kwargs: None)


def test_change_management_happy(client, admin_headers, monkeypatch):
    _patch_change(monkeypatch)

    r = client.get("/api/v1/change-management/requests", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()

    r = client.post(
        "/api/v1/change-management/requests",
        headers=admin_headers,
        json={"title": "t", "requester": "r"},
    )
    assert r.status_code == 201

    r = client.get("/api/v1/change-management/requests/cr1", headers=admin_headers)
    assert r.status_code == 200

    r = client.post("/api/v1/change-management/requests/cr1/submit", headers=admin_headers)
    assert r.status_code == 200

    r = client.post("/api/v1/change-management/requests/cr1/approve", headers=admin_headers)
    assert r.status_code == 200

    r = client.post("/api/v1/change-management/requests/cr1/reject", headers=admin_headers)
    assert r.status_code == 200

    r = client.post("/api/v1/change-management/requests/cr1/implement", headers=admin_headers)
    assert r.status_code == 200

    r = client.post("/api/v1/change-management/requests/cr1/rollback", headers=admin_headers)
    assert r.status_code == 200


def test_change_management_errors(client, admin_headers, monkeypatch):
    import api.change_management_router as mod

    _patch_change(monkeypatch)

    monkeypatch.setattr(mod, "list_requests", AsyncMock(side_effect=RuntimeError("boom")))
    r = client.get("/api/v1/change-management/requests", headers=admin_headers)
    assert r.status_code == 500

    monkeypatch.setattr(
        mod, "create_request", AsyncMock(side_effect=mod.ChangeManagementError("bad"))
    )
    r = client.post(
        "/api/v1/change-management/requests",
        headers=admin_headers,
        json={"title": "t", "requester": "r"},
    )
    assert r.status_code == 400

    monkeypatch.setattr(
        mod, "get_request", AsyncMock(side_effect=mod.ChangeManagementError("missing"))
    )
    r = client.get("/api/v1/change-management/requests/cr1", headers=admin_headers)
    assert r.status_code == 404

    monkeypatch.setattr(mod, "submit_request", AsyncMock(side_effect=RuntimeError("boom")))
    r = client.post("/api/v1/change-management/requests/cr1/submit", headers=admin_headers)
    assert r.status_code == 500


# ---------------------------------------------------------------------------
# AI router
# ---------------------------------------------------------------------------
def test_ai_analyze(client, admin_headers, monkeypatch):
    import api.ai_router as mod

    monkeypatch.setattr(
        mod, "analyze", AsyncMock(return_value={"analysis": "ok", "confidence": 0.9})
    )

    r = client.post(
        "/api/ai/analyze",
        headers=admin_headers,
        json={"query": "cpu high", "include_metrics": False, "include_rich_context": False},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_ai_analyze_errors(client, admin_headers, monkeypatch):
    import api.ai_router as mod

    r = client.post(
        "/api/ai/analyze",
        headers=admin_headers,
        json={"query": "  "},
    )
    assert r.status_code == 422

    monkeypatch.setattr(mod, "analyze", AsyncMock(side_effect=RuntimeError("boom")))
    r = client.post(
        "/api/ai/analyze",
        headers=admin_headers,
        json={"query": "cpu high", "include_metrics": False, "include_rich_context": False},
    )
    assert r.status_code == 500


# ---------------------------------------------------------------------------
# Infrastructure router
# ---------------------------------------------------------------------------
def _patch_infrastructure(monkeypatch):
    import api.infrastructure_router as mod

    class _JobTypeMeta(type):
        def __iter__(cls):
            yield getattr(cls, "METRICS_AGGREGATION")
            yield getattr(cls, "STREAMING")

    class JobType(metaclass=_JobTypeMeta):
        METRICS_AGGREGATION = SimpleNamespace(value="metrics_aggregation")
        STREAMING = SimpleNamespace(value="streaming")

    @dataclass
    class FlinkJobConfig:
        job_name: str
        job_type: object
        parallelism: int

    class Job:
        def __init__(self, config):
            self.config = config

    class KafkaProc:
        producer = None

        def send_message(self, **kwargs):
            return True

        def get_cached_messages(self):
            return [SimpleNamespace(topic="t1"), SimpleNamespace(topic="t2")]

    class FlinkMan:
        _initialized = True
        jobs = {"j1": Job(FlinkJobConfig("j1", JobType.METRICS_AGGREGATION, 2))}

        def create_job(self, config):
            return Job(config)

        def get_job_status(self, name):
            job = self.jobs[name]
            return {
                "job_name": job.config.job_name,
                "job_type": job.config.job_type.value,
                "status": "running",
            }

    class StorageMan:
        _initialized = True

        def get_read_connection_info(self):
            return {}

        def get_write_connection_info(self):
            return {}

        def health_check(self):
            return {}

    class ConfigCenter:
        _initialized = True

        def set_config(self, **kwargs):
            return True

        def get_config_item(self, key):
            return SimpleNamespace(version=1)

        def get_config(self, key):
            return "v"

        def get_all_configs(self):
            return {"k": "v"}

    class MetricsCollector:
        _initialized = True

        def increment_counter(self, name):
            pass

    class MonitoringInfra:
        metrics_collector = MetricsCollector()

        def get_monitoring_status(self):
            return {"status": "ok"}

    class DataFlow:
        _initialized = True

        def get_data_flow_stats(self):
            return {
                "total_processed": 1,
                "total_analyzed": 1,
                "total_errors": 0,
                "avg_processing_time_ms": 1.0,
                "error_rate": 0.0,
                "analysis_rate": 1.0,
            }

        def start_data_flow(self):
            return True

        def stop_data_flow(self):
            return True

    class MonitoringSys:
        _initialized = True

        def get_monitoring_summary(self):
            return {
                "total_alerts": 1,
                "active_alerts": 1,
                "critical_alerts": 0,
                "error_alerts": 0,
                "warning_alerts": 0,
                "total_dashboards": 1,
            }

        def get_active_alerts(self):
            return []

        def resolve_alert(self, alert_id):
            pass

    monkeypatch.setattr(mod, "FlinkJobType", JobType)
    monkeypatch.setattr(mod, "FlinkJobConfig", FlinkJobConfig)
    monkeypatch.setattr(mod, "get_kafka_processor", lambda: KafkaProc())
    monkeypatch.setattr(mod, "get_flink_job_manager", lambda: FlinkMan())
    monkeypatch.setattr(mod, "get_distributed_storage_manager", lambda: StorageMan())
    monkeypatch.setattr(mod, "get_config_center", lambda: ConfigCenter())
    monkeypatch.setattr(mod, "get_monitoring_infrastructure", lambda: MonitoringInfra())
    monkeypatch.setattr(mod, "get_l1l2_data_flow_integrator", lambda: DataFlow())
    monkeypatch.setattr(mod, "get_monitoring_system_integrator", lambda: MonitoringSys())


def test_infrastructure_happy(client, admin_headers, monkeypatch):
    _patch_infrastructure(monkeypatch)

    r = client.post(
        "/api/v1/infrastructure/kafka/send",
        headers=admin_headers,
        json={"topic": "t", "key": "k", "value": {"x": 1}},
    )
    assert r.status_code == 200
    assert r.json()["success"] is True

    r = client.get("/api/v1/infrastructure/kafka/status", headers=admin_headers)
    assert r.status_code == 200
    assert "topics" in r.json()

    r = client.post(
        "/api/v1/infrastructure/flink/job",
        headers=admin_headers,
        json={"job_name": "j1", "job_type": "metrics_aggregation", "parallelism": 2},
    )
    assert r.status_code == 200

    r = client.get("/api/v1/infrastructure/flink/jobs", headers=admin_headers)
    assert r.status_code == 200

    r = client.get("/api/v1/infrastructure/storage/read-connection", headers=admin_headers)
    assert r.status_code == 200

    r = client.get("/api/v1/infrastructure/storage/write-connection", headers=admin_headers)
    assert r.status_code == 200

    r = client.get("/api/v1/infrastructure/storage/health", headers=admin_headers)
    assert r.status_code == 200

    r = client.post(
        "/api/v1/infrastructure/config",
        headers=admin_headers,
        json={"key": "k", "value": "v"},
    )
    assert r.status_code == 200

    r = client.get("/api/v1/infrastructure/config/k", headers=admin_headers)
    assert r.status_code == 200

    r = client.get("/api/v1/infrastructure/config", headers=admin_headers)
    assert r.status_code == 200

    r = client.get("/api/v1/infrastructure/monitoring/status", headers=admin_headers)
    assert r.status_code == 200

    r = client.post("/api/v1/infrastructure/monitoring/metrics", headers=admin_headers)
    assert r.status_code == 200

    r = client.get("/api/v1/infrastructure/data-flow/stats", headers=admin_headers)
    assert r.status_code == 200

    r = client.post("/api/v1/infrastructure/data-flow/start", headers=admin_headers)
    assert r.status_code == 200

    r = client.post("/api/v1/infrastructure/data-flow/stop", headers=admin_headers)
    assert r.status_code == 200

    r = client.get("/api/v1/infrastructure/monitoring/summary", headers=admin_headers)
    assert r.status_code == 200

    r = client.get("/api/v1/infrastructure/alerts", headers=admin_headers)
    assert r.status_code == 200

    r = client.post("/api/v1/infrastructure/alerts/1/resolve", headers=admin_headers)
    assert r.status_code == 200

    r = client.get("/api/v1/infrastructure/health", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["kafka"] is True


def test_infrastructure_errors(client, admin_headers, monkeypatch):
    import api.infrastructure_router as mod

    _patch_infrastructure(monkeypatch)

    def boom():
        raise RuntimeError("boom")

    monkeypatch.setattr(mod, "get_kafka_processor", boom)
    r = client.post(
        "/api/v1/infrastructure/kafka/send",
        headers=admin_headers,
        json={"topic": "t", "key": "k", "value": {"x": 1}},
    )
    assert r.status_code == 500

    monkeypatch.setattr(mod, "get_monitoring_infrastructure", boom)
    r = client.get("/api/v1/infrastructure/monitoring/status", headers=admin_headers)
    assert r.status_code == 500

    monkeypatch.setattr(mod, "get_l1l2_data_flow_integrator", boom)
    r = client.get("/api/v1/infrastructure/data-flow/stats", headers=admin_headers)
    assert r.status_code == 500
