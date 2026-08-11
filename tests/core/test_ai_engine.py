# -*- coding: utf-8 -*-
"""Unit tests for core/ai_engine.py."""

import pytest

from core.ai_engine import (
    IntelligentRecommendationEngine,
    LLMAnalysisService,
    NaturalLanguageInteraction,
    PredictiveAnalysisEngine,
    RootCauseAnalysisResponse,
    _build_rich_user_message,
    _compute_prompt_token_budget,
    _redact_text,
    _redact_value,
    _rule_based_analysis,
    _validate_root_cause_output,
)


def test_compute_prompt_token_budget():
    budget = _compute_prompt_token_budget("system prompt")
    assert isinstance(budget, int)
    assert budget > 0


def test_validate_root_cause_output_valid():
    data = (
        '{"data_assessment": {"reliability_score": 0.9}, '
        '"candidates": [], "escalation_recommended": false, '
        '"recommended_action": "restart"}'
    )
    assert _validate_root_cause_output(data) is not None


def test_validate_root_cause_output_invalid():
    assert _validate_root_cause_output("not json") is None


def test_redact_text_and_value():
    assert isinstance(_redact_text("hello"), str)
    assert _redact_value(["a"]) == ["a"]


def test_build_rich_user_message():
    msg = _build_rich_user_message("query", "cpu 90", "windows", {})
    assert isinstance(msg, str)
    assert "query" in msg


def test_rule_based_analysis():
    result = _rule_based_analysis("cpu high", "cpu 90", "windows")
    assert isinstance(result, str)
    assert len(result) > 0


def test_root_cause_response_model():
    resp = RootCauseAnalysisResponse(
        data_assessment={"reliability_score": 0.9},
        candidates=[],
        escalation_recommended=False,
        recommended_action="restart",
    )
    assert resp.recommended_action == "restart"


@pytest.mark.asyncio
async def test_llm_analysis_service_health_and_search():
    service = LLMAnalysisService()
    health = await service.get_health_status()
    assert "status" in health
    result = await service.search_similar("cpu high", limit=5)
    assert isinstance(result, list)


@pytest.mark.asyncio
async def test_predictive_analysis_engine():
    engine = PredictiveAnalysisEngine()
    result = await engine.predict_system_anomalies(
        {"cpu": {"usage_percent": 85}, "memory": {"usage_percent": 90}}
    )
    assert "predicted_anomalies" in result
    assert result["confidence"] > 0


@pytest.mark.asyncio
async def test_intelligent_recommendation_engine():
    engine = IntelligentRecommendationEngine()
    recs = await engine.generate_recommendations({"type": "cpu_high", "severity": "critical"})
    assert isinstance(recs, list)
    assert len(recs) > 0


@pytest.mark.asyncio
async def test_natural_language_interaction():
    nli = NaturalLanguageInteraction()
    result = await nli.process_natural_language_query("What is the cpu status?")
    assert result["intent"] == "status_query"
    assert result["entities"].get("metric") == "cpu"
    assert isinstance(result["response"], str)
    conv = await nli.maintain_conversation("user1", "cpu high")
    assert "response" in conv
