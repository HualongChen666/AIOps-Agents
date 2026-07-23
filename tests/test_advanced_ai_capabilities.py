# -*- coding: utf-8 -*-
"""
Unit Tests for Advanced AI Capabilities
========================================

Comprehensive unit tests for the advanced AI capabilities module.
"""

import asyncio  # noqa: F401
from datetime import datetime, timedelta
from typing import Any, Dict  # noqa: F401

import pytest

try:
    from core.advanced_ai_capabilities import (  # noqa: F401
        AdvancedAICapabilities,
        ConversationContext,
        ExplainableDecision,
        LearningMode,
        PredictionType,
    )

    ADVANCED_AI_AVAILABLE = True
except ImportError:
    ADVANCED_AI_AVAILABLE = False


@pytest.mark.skipif(not ADVANCED_AI_AVAILABLE, reason="Advanced AI capabilities not available")
class TestAdvancedAICapabilities:
    """Test suite for AdvancedAICapabilities"""

    @pytest.fixture
    def ai_capabilities(self):
        """Fixture for AdvancedAICapabilities instance"""
        return AdvancedAICapabilities()

    @pytest.fixture
    def sample_historical_data(self):
        """Fixture for sample historical time series data"""
        base_time = datetime.now()
        return [(base_time - timedelta(hours=i), 50 + i * 2 + (i % 5)) for i in range(24, 0, -1)]

    def test_initialization(self, ai_capabilities):
        """Test that AdvancedAICapabilities initializes correctly"""
        assert ai_capabilities is not None
        assert hasattr(ai_capabilities, "prediction_models")
        assert hasattr(ai_capabilities, "learning_models")
        assert hasattr(ai_capabilities, "conversation_contexts")

    @pytest.mark.asyncio
    async def test_predict_time_series(self, ai_capabilities, sample_historical_data):
        """Test time series prediction"""
        result = await ai_capabilities.predict_time_series(
            sample_historical_data, prediction_horizon=5
        )

        assert result is not None
        assert result.prediction_type == PredictionType.TIME_SERIES
        assert len(result.predicted_values) == 5
        assert result.confidence >= 0
        assert result.model_used is not None

    @pytest.mark.asyncio
    async def test_predict_time_series_insufficient_data(self, ai_capabilities):
        """Test time series prediction with insufficient data"""
        insufficient_data = [(datetime.now(), 50), (datetime.now(), 51)]

        result = await ai_capabilities.predict_time_series(insufficient_data, prediction_horizon=5)

        assert result is not None
        assert result.model_used == "insufficient_data"

    @pytest.mark.asyncio
    async def test_predict_anomalies(self, ai_capabilities):
        """Test anomaly prediction"""
        current_data = {"cpu_usage": 95.0, "memory_usage": 80.0, "disk_usage": 60.0}

        historical_baseline = {
            "cpu_usage": [50.0, 52.0, 48.0, 51.0, 49.0],
            "memory_usage": [60.0, 62.0, 58.0, 61.0, 59.0],
            "disk_usage": [40.0, 41.0, 39.0, 40.0, 41.0],
        }

        result = await ai_capabilities.predict_anomalies(
            current_data, historical_baseline, threshold_std=2.0
        )

        assert result is not None
        assert result.prediction_type == PredictionType.ANOMALY
        assert result.model_used == "statistical_z_score"
        assert "anomalies" in result.metadata

    @pytest.mark.asyncio
    async def test_adaptive_learning_update(self, ai_capabilities):
        """Test adaptive learning update"""
        new_data = {"feature1": 1.0, "feature2": 2.0, "feature3": 3.0}

        feedback = {"metric1": 0.8, "metric2": 0.9}

        result = await ai_capabilities.adaptive_learning_update(
            new_data, feedback, LearningMode.ONLINE
        )

        assert result is not None
        assert result.learning_mode == LearningMode.ONLINE
        assert result.update_id is not None
        assert result.performance_improvement >= 0

    @pytest.mark.asyncio
    async def test_natural_language_interaction(self, ai_capabilities):
        """Test natural language interaction"""
        response = await ai_capabilities.natural_language_interaction(
            user_input="检查系统状态", conversation_id="test_conv_1", user_id="test_user"
        )

        assert response is not None
        assert "response" in response
        assert "intent" in response
        assert "confidence" in response

    @pytest.mark.asyncio
    async def test_conversation_context_persistence(self, ai_capabilities):
        """Test that conversation context persists across messages"""
        conversation_id = "test_conv_persistence"

        # First message
        await ai_capabilities.natural_language_interaction(
            user_input="你好", conversation_id=conversation_id, user_id="test_user"
        )

        # Second message
        await ai_capabilities.natural_language_interaction(
            user_input="系统状态如何", conversation_id=conversation_id, user_id="test_user"
        )

        # Check that context exists
        assert conversation_id in ai_capabilities.conversation_contexts
        context = ai_capabilities.conversation_contexts[conversation_id]
        assert len(context.messages) == 2

    @pytest.mark.asyncio
    async def test_explain_decision(self, ai_capabilities):
        """Test decision explanation"""
        decision = "Route alert to team A"
        decision_context = {"severity": 0.8, "priority": 0.7, "team_availability": 0.9}

        explanation = await ai_capabilities.explain_decision(
            decision=decision, decision_context=decision_context, decision_type="alert_routing"
        )

        assert explanation is not None
        assert explanation.decision == decision
        assert explanation.confidence >= 0
        assert len(explanation.reasoning) > 0
        assert len(explanation.feature_importance) > 0

    @pytest.mark.asyncio
    async def test_continuous_knowledge_learning(self, ai_capabilities):
        """Test continuous knowledge learning"""
        experience_data = {"metric1": 100, "metric2": 200, "pattern": "test_pattern"}

        result = await ai_capabilities.continuous_knowledge_learning(
            experience_data, outcome="success"
        )

        assert result is not None
        assert result["status"] == "success"
        assert result["knowledge_extracted"] > 0

    def test_get_capabilities_summary(self, ai_capabilities):
        """Test getting capabilities summary"""
        summary = ai_capabilities.get_capabilities_summary()

        assert summary is not None
        assert "predictive_analysis" in summary
        assert "adaptive_learning" in summary
        assert "natural_language_interaction" in summary
        assert "knowledge_base" in summary
        assert "explainable_ai" in summary


@pytest.mark.skipif(not ADVANCED_AI_AVAILABLE, reason="Advanced AI capabilities not available")
class TestPredictionResult:
    """Test suite for PredictionResult dataclass"""

    def test_prediction_result_creation(self):
        """Test PredictionResult creation"""
        from core.advanced_ai_capabilities import PredictionResult

        result = PredictionResult(
            prediction_type=PredictionType.TIME_SERIES,
            predicted_values=[1.0, 2.0, 3.0],
            confidence=0.8,
            model_used="test_model",
        )

        assert result.prediction_type == PredictionType.TIME_SERIES
        assert len(result.predicted_values) == 3
        assert result.confidence == 0.8
        assert result.model_used == "test_model"


@pytest.mark.skipif(not ADVANCED_AI_AVAILABLE, reason="Advanced AI capabilities not available")
class TestLearningUpdate:
    """Test suite for LearningUpdate dataclass"""

    def test_learning_update_creation(self):
        """Test LearningUpdate creation"""
        from core.advanced_ai_capabilities import LearningUpdate

        update = LearningUpdate(
            update_id="update_1",
            learning_mode=LearningMode.ONLINE,
            performance_improvement=0.1,
            new_samples=100,
            model_version="v1.0",
        )

        assert update.update_id == "update_1"
        assert update.learning_mode == LearningMode.ONLINE
        assert update.performance_improvement == 0.1
        assert update.new_samples == 100
