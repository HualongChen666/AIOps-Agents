# -*- coding: utf-8 -*-
"""Advanced AI Router Tests"""

import datetime
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import api.advanced_ai_router as advanced_ai_router

sys.modules["core.advanced_ai_capabilities"] = MagicMock()
sys.modules["core.advanced_ai_capabilities"].ADVANCED_AI_AVAILABLE = True
sys.modules["core.advanced_ai_capabilities"].advanced_ai_capabilities = MagicMock()


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(advanced_ai_router.router)
    return TestClient(app)


class TestAdvancedAIRouter:
    def test_advanced_ai_health(self, client):
        response = client.get("/api/v1/ai-advanced/")
        assert response.status_code in [200, 404]

    def test_predict_time_series_unavailable(self, client):
        """测试时序预测（不可用）"""
        with patch("api.advanced_ai_router.ADVANCED_AI_AVAILABLE", False):
            response = client.post(
                "/api/v1/ai-advanced/predict/time-series",
                json={
                    "historical_data": [{"timestamp": "2026-07-03T00:00:00Z", "value": 10.0}],
                    "prediction_horizon": 24,
                },
            )
            assert response.status_code in [200, 503, 500]

    def test_predict_anomalies_unavailable(self, client):
        """测试异常预测（不可用）"""
        with patch("api.advanced_ai_router.ADVANCED_AI_AVAILABLE", False):
            response = client.post(
                "/api/v1/ai-advanced/predict/anomalies",
                json={
                    "current_data": {"cpu_usage": 80.0},
                    "historical_baseline": {"cpu_usage": [50.0, 60.0, 70.0]},
                },
            )
            assert response.status_code in [200, 503, 500]

    def test_adaptive_learning_update_unavailable(self, client):
        """测试自适应学习更新（不可用）"""
        with patch("api.advanced_ai_router.ADVANCED_AI_AVAILABLE", False):
            response = client.post(
                "/api/v1/ai-advanced/learning/update",
                json={
                    "new_data": {"metric": "cpu_usage"},
                    "feedback": {"accuracy": 0.9},
                    "learning_mode": "online",
                },
            )
            assert response.status_code in [200, 503, 500]

    def test_natural_language_interaction_unavailable(self, client):
        """测试自然语言交互（不可用）"""
        with patch("api.advanced_ai_router.ADVANCED_AI_AVAILABLE", False):
            response = client.post(
                "/api/v1/ai-advanced/conversation",
                json={
                    "user_input": "系统状态如何？",
                    "conversation_id": "conv-123",
                    "user_id": "user-456",
                },
            )
            assert response.status_code in [200, 503, 500]


class _FakeLearningMode:
    """用于验证学习模式的分支"""

    def __init__(self, value: str):
        if value not in {"online", "batch"}:
            raise ValueError(f"Invalid learning mode: {value}")
        self.value = value

    def __eq__(self, other):
        return isinstance(other, _FakeLearningMode) and self.value == other.value


class _FakePredictionType:
    """用于验证预测类型的分支"""

    def __init__(self, value: str):
        if value not in {"time_series", "anomaly"}:
            raise ValueError(f"Invalid prediction type: {value}")
        self.value = value

    def __eq__(self, other):
        return isinstance(other, _FakePredictionType) and self.value == other.value


def _prediction_result(values=None):
    return SimpleNamespace(
        prediction_type=SimpleNamespace(value="time_series"),
        predicted_values=values if values is not None else [1.0, 2.0],
        confidence=0.9,
        model_used="prophet",
        prediction_timestamp=datetime.datetime(2026, 7, 4, 0, 0, 0),
        metadata={},
    )


def _learning_update(mode="online"):
    return SimpleNamespace(
        update_id="update-123",
        learning_mode=SimpleNamespace(value=mode),
        performance_improvement=0.15,
        new_samples=100,
        model_version="v2.1",
        update_timestamp=datetime.datetime(2026, 7, 4, 0, 0, 0),
        metadata={},
    )


def _explanation_result():
    return SimpleNamespace(
        decision_id="decision-123",
        decision="restart_service",
        confidence=0.88,
        reasoning="high response time",
        feature_importance={"response_time": 0.6},
        alternative_options=["scale_up"],
        decision_timestamp=datetime.datetime(2026, 7, 4, 0, 0, 0),
    )


def _conversation_context(cid="conv-123", uid="user-456"):
    return SimpleNamespace(
        conversation_id=cid,
        user_id=uid,
        current_intent="status_query",
        messages=[],
        started_at=datetime.datetime(2026, 7, 4, 0, 0, 0),
        last_activity=datetime.datetime(2026, 7, 4, 0, 0, 0),
        context_variables={},
    )


def _learning_update_entry(mode="online"):
    return SimpleNamespace(
        update_id="update-1",
        learning_mode=SimpleNamespace(value=mode),
        performance_improvement=0.1,
        new_samples=10,
        model_version="v1",
        update_timestamp=datetime.datetime(2026, 7, 4, 0, 0, 0),
    )


def _prediction_entry(ptype="time_series"):
    return SimpleNamespace(
        prediction_type=SimpleNamespace(value=ptype),
        confidence=0.9,
        model_used="prophet",
        prediction_timestamp=datetime.datetime(2026, 7, 4, 0, 0, 0),
        metadata={},
    )


class TestAdvancedAIRouterSuccess:
    """高级 AI 路由器成功与异常分支测试"""

    def test_predict_time_series_success(self, client):
        mock = advanced_ai_router.advanced_ai_capabilities
        mock.predict_time_series = AsyncMock(
            return_value=_prediction_result(values=[1.0, 2.0, 3.0])
        )
        historical = [{"timestamp": "2026-07-03T00:00:00Z", "value": float(i)} for i in range(10)]
        response = client.post(
            "/api/v1/ai-advanced/predict/time-series",
            json={"historical_data": historical, "prediction_horizon": 3},
        )
        assert response.status_code == 200

    def test_predict_time_series_insufficient_data(self, client):
        response = client.post(
            "/api/v1/ai-advanced/predict/time-series",
            json={
                "historical_data": [{"timestamp": "2026-07-03T00:00:00Z", "value": 1.0}],
                "prediction_horizon": 3,
            },
        )
        assert response.status_code == 400

    def test_predict_time_series_invalid_data_skipped(self, client):
        mock = advanced_ai_router.advanced_ai_capabilities
        mock.predict_time_series = AsyncMock(return_value=_prediction_result(values=[1.0]))
        historical = [
            {"timestamp": "bad", "value": 1.0},
            *[{"timestamp": "2026-07-03T00:00:00Z", "value": float(i)} for i in range(10)],
        ]
        response = client.post(
            "/api/v1/ai-advanced/predict/time-series",
            json={"historical_data": historical, "prediction_horizon": 1},
        )
        assert response.status_code == 200

    def test_predict_anomalies_success(self, client):
        mock = advanced_ai_router.advanced_ai_capabilities
        mock.predict_anomalies = AsyncMock(
            return_value=SimpleNamespace(
                prediction_type=SimpleNamespace(value="anomaly"),
                predicted_values=[],
                confidence=0.92,
                model_used="statistical_z_score",
                prediction_timestamp=datetime.datetime(2026, 7, 4, 0, 0, 0),
                metadata={"anomalies": [], "anomaly_scores": {}, "total_metrics": 0},
            )
        )
        response = client.post(
            "/api/v1/ai-advanced/predict/anomalies",
            json={
                "current_data": {"cpu_usage": 80.0},
                "historical_baseline": {"cpu_usage": [50.0, 60.0, 70.0]},
            },
        )
        assert response.status_code == 200

    def test_adaptive_learning_update_success(self, client):
        mock = advanced_ai_router.advanced_ai_capabilities
        mock.adaptive_learning_update = AsyncMock(return_value=_learning_update())
        response = client.post(
            "/api/v1/ai-advanced/learning/update",
            json={
                "new_data": {"metric": "cpu_usage"},
                "feedback": {"accuracy": 0.9},
                "learning_mode": "online",
            },
        )
        assert response.status_code == 200

    def test_adaptive_learning_update_invalid_mode(self, client):
        with patch.object(advanced_ai_router, "LearningMode", _FakeLearningMode):
            response = client.post(
                "/api/v1/ai-advanced/learning/update",
                json={
                    "new_data": {"metric": "cpu_usage"},
                    "feedback": {"accuracy": 0.9},
                    "learning_mode": "invalid",
                },
            )
        assert response.status_code == 400

    def test_natural_language_interaction_success(self, client):
        mock = advanced_ai_router.advanced_ai_capabilities
        mock.natural_language_interaction = AsyncMock(
            return_value={
                "conversation_id": "conv-123",
                "user_message": "系统状态如何？",
                "ai_response": "系统运行正常",
                "intent": "status_query",
            }
        )
        response = client.post(
            "/api/v1/ai-advanced/conversation",
            json={
                "user_input": "系统状态如何？",
                "conversation_id": "conv-123",
                "user_id": "user-456",
            },
        )
        assert response.status_code == 200

    def test_get_conversation_context_success(self, client):
        mock = advanced_ai_router.advanced_ai_capabilities
        mock.conversation_contexts = {"conv-123": _conversation_context()}
        response = client.get("/api/v1/ai-advanced/conversation/conv-123")
        assert response.status_code == 200

    def test_get_conversation_context_not_found(self, client):
        mock = advanced_ai_router.advanced_ai_capabilities
        mock.conversation_contexts = {}
        response = client.get("/api/v1/ai-advanced/conversation/conv-404")
        assert response.status_code == 404

    def test_explain_decision_success(self, client):
        mock = advanced_ai_router.advanced_ai_capabilities
        mock.explain_decision = AsyncMock(return_value=_explanation_result())
        response = client.post(
            "/api/v1/ai-advanced/explain",
            json={
                "decision": "restart_service",
                "decision_context": {"response_time": 2.5},
                "decision_type": "default",
            },
        )
        assert response.status_code == 200

    def test_continuous_knowledge_learning_success(self, client):
        mock = advanced_ai_router.advanced_ai_capabilities
        mock.continuous_knowledge_learning = AsyncMock(
            return_value={
                "status": "success",
                "knowledge_extracted": 1,
                "total_knowledge_items": 1,
            }
        )
        response = client.post(
            "/api/v1/ai-advanced/knowledge/learn",
            json={
                "experience_data": {"issue": "slow_response", "fix": "restart"},
                "outcome": "success",
            },
        )
        assert response.status_code == 200

    def test_get_knowledge_base_with_category(self, client):
        mock = advanced_ai_router.advanced_ai_capabilities
        mock.knowledge_base = {
            "category1": [
                {
                    "value": "v1",
                    "timestamp": datetime.datetime(2026, 7, 4, 0, 0, 0),
                }
            ]
        }
        response = client.get("/api/v1/ai-advanced/knowledge?category=category1&limit=10")
        assert response.status_code == 200

    def test_get_knowledge_base_not_found(self, client):
        mock = advanced_ai_router.advanced_ai_capabilities
        mock.knowledge_base = {}
        response = client.get("/api/v1/ai-advanced/knowledge?category=missing")
        assert response.status_code == 404

    def test_get_knowledge_base_all(self, client):
        mock = advanced_ai_router.advanced_ai_capabilities
        mock.knowledge_base = {
            "category1": [
                {
                    "value": "v1",
                    "timestamp": datetime.datetime(2026, 7, 4, 0, 0, 0),
                }
            ]
        }
        response = client.get("/api/v1/ai-advanced/knowledge")
        assert response.status_code == 200

    def test_get_ai_statistics_success(self, client):
        mock = advanced_ai_router.advanced_ai_capabilities
        mock.get_capabilities_summary = MagicMock(return_value={"models": 5})
        response = client.get("/api/v1/ai-advanced/statistics")
        assert response.status_code == 200

    def test_get_learning_history_success(self, client):
        mock = advanced_ai_router.advanced_ai_capabilities
        mock.learning_updates = [_learning_update_entry()]
        response = client.get("/api/v1/ai-advanced/learning/history")
        assert response.status_code == 200

    def test_get_prediction_history_success(self, client):
        mock = advanced_ai_router.advanced_ai_capabilities
        mock.prediction_history = [_prediction_entry()]
        response = client.get("/api/v1/ai-advanced/predictions/history")
        assert response.status_code == 200

    def test_get_prediction_history_invalid_type(self, client):
        with patch.object(advanced_ai_router, "PredictionType", _FakePredictionType):
            response = client.get("/api/v1/ai-advanced/predictions/history?prediction_type=invalid")
        assert response.status_code == 400

    def test_delete_conversation_success(self, client):
        mock = advanced_ai_router.advanced_ai_capabilities
        mock.conversation_contexts = {"conv-123": _conversation_context()}
        response = client.delete("/api/v1/ai-advanced/conversation/conv-123")
        assert response.status_code == 200

    def test_delete_conversation_not_found(self, client):
        mock = advanced_ai_router.advanced_ai_capabilities
        mock.conversation_contexts = {}
        response = client.delete("/api/v1/ai-advanced/conversation/conv-404")
        assert response.status_code == 404


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
