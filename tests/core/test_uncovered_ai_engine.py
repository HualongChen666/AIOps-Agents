# -*- coding: utf-8 -*-
"""Coverage tests for core/ai_engine.py public classes and helpers."""

import asyncio  # noqa: F401  # Imported for test setup
import json  # noqa: F401  # Imported for test setup
import sys  # noqa: F401  # Imported for test setup
import types
from unittest.mock import AsyncMock

import pytest  # noqa: F401  # Imported for test setup

# Stub the optional core.ai.rag submodules before core.ai_engine is imported so that
# heavy sentence-transformer model loading is avoided during the test run.
if "core.ai.rag" not in sys.modules:
    _rag = types.ModuleType("core.ai.rag")
    _rag.KnowledgeBase = type("KnowledgeBase", (), {})
    _rag.RAGPipeline = type(
        "RAGPipeline",
        (),
        {
            "__init__": lambda self, *a, **k: None,
            "retrieve_and_generate": staticmethod(lambda **k: ""),
        },
    )
    sys.modules["core.ai.rag"] = _rag

    _fusion = types.ModuleType("core.ai.rag.fusion")
    _fusion.ConcatenationFusion = type("ConcatenationFusion", (), {"__init__": lambda self: None})
    sys.modules["core.ai.rag.fusion"] = _fusion

    _retriever = types.ModuleType("core.ai.rag.retriever")
    _retriever.Retriever = type("Retriever", (), {"__init__": lambda self, *a, **k: None})
    _retriever.VectorStoreRetrieval = type(
        "VectorStoreRetrieval", (), {"__init__": lambda self, *a, **k: None}
    )
    sys.modules["core.ai.rag.retriever"] = _retriever

    _vectorizer = types.ModuleType("core.ai.rag.vectorizer")
    _vectorizer.SentenceTransformerEmbedding = type(  # noqa: F841  # Variable for test verification
        "SentenceTransformerEmbedding", (), {"__init__": lambda self, **k: None}
    )
    sys.modules["core.ai.rag.vectorizer"] = _vectorizer

import core.ai_engine as ai_engine  # noqa: E402

pytestmark = [pytest.mark.core]


class _FakeLLMRouter:
    def __init__(self, content="fake ai response"):
        self.content = content

    async def generate(self, **kwargs):
        return {
            "content": self.content,
            "model": "fake-model",
            "usage": {
                "total_tokens": 10,
                "prompt_tokens": 7,
                "completion_tokens": 3,
            },
        }


def _stub_llm(monkeypatch, content="fake ai response"):
    """Replace LLM/cost/RAG paths with lightweight fakes."""
    router = _FakeLLMRouter(content)
    monkeypatch.setattr(ai_engine, "get_llm_router", lambda: router)
    monkeypatch.setattr(ai_engine, "get_llm_cost_monitor", None)
    monkeypatch.setattr(ai_engine, "get_session_budget", None)
    monkeypatch.setattr(ai_engine, "CONTENT_MODERATION_AVAILABLE", False)
    monkeypatch.setattr(ai_engine, "_langfuse_available", False)
    monkeypatch.setattr(ai_engine, "_rag_pipeline", None)
    monkeypatch.setattr(ai_engine, "_rate_limit_wait", AsyncMock())
    monkeypatch.setattr(
        ai_engine,
        "AI_CONFIG",
        {
            "is_enabled": True,
            "api_key": "test-key",
            "base_url": "http://test",
            "model": "fake",
            "timeout": 10,
            "max_retries": 1,
        },
    )
    return router


async def test_llm_analysis_service_analyze(monkeypatch):
    _stub_llm(monkeypatch, content="analyzed")
    service = ai_engine.LLMAnalysisService()
    result = await service.analyze(  # noqa: F841  # Variable for test verification
        context={"query": "cpu high", "metrics_snapshot": "cpu=90", "platform": "linux"}
    )
    assert isinstance(result, dict)
    assert "result" in result
    assert "timestamp" in result
    assert result["platform"] == "linux"


async def test_llm_analysis_service_observe(monkeypatch):
    _stub_llm(monkeypatch, content="observed")
    service = ai_engine.LLMAnalysisService()
    result = await service.observe({"query": "service down"})  # noqa: F841  # Variable for test verification
    assert isinstance(result, dict)
    assert "result" in result


async def test_llm_analysis_service_generate_runbook(monkeypatch):
    _stub_llm(monkeypatch, content="runbook text")
    service = ai_engine.LLMAnalysisService()
    result = await service.generate_runbook(  # noqa: F841  # Variable for test verification
        {"id": "a1", "title": "CPU high", "desc": "cpu usage high"},
        {"platform": "linux"},
    )
    assert isinstance(result, dict)
    assert "runbook" in result
    assert result["alert_id"] == "a1"


def test_llm_analysis_service_get_health_status():
    service = ai_engine.LLMAnalysisService()
    status = asyncio.run(service.get_health_status())
    assert isinstance(status, dict)
    assert "available" in status
    assert "langfuse_available" in status
    assert "timestamp" in status


async def test_llm_analysis_service_search_similar():
    service = ai_engine.LLMAnalysisService()
    result = await service.search_similar("cpu spike", limit=5)  # noqa: F841  # Variable for test verification
    assert isinstance(result, list)
    assert len(result) == 0


async def test_analyze_returns_rule_fallback_when_disabled(monkeypatch):
    monkeypatch.setattr(ai_engine, "_rate_limit_wait", AsyncMock())
    monkeypatch.setattr(
        ai_engine,
        "AI_CONFIG",
        {
            "is_enabled": False,
            "api_key": "",
            "base_url": "",
            "model": "",
            "timeout": 10,
            "max_retries": 1,
        },
    )
    result = await ai_engine.analyze(query="cpu high", platform="linux")  # noqa: F841  # Variable for test verification
    assert isinstance(result, str)
    assert "规则降级" in result
    assert "linux" in result


async def test_analyze_with_json_validation(monkeypatch):
    payload = {
        "data_assessment": {
            "reliability_score": 0.8,
            "reliability_concerns": [],
        },
        "candidates": [
            {
                "rank": 1,
                "root_cause": "cpu overload",
                "confidence": 0.85,
                "expected_observations_if_true": [],
                "missing_data": [],
                "is_verifiable": True,
                "evidence": [],
            }
        ],
        "multi_root_cause_note": "",
        "escalation_recommended": False,
        "escalation_reason": "",
        "recommended_action": "check process",
    }
    _stub_llm(monkeypatch, content=json.dumps(payload, ensure_ascii=False))
    result = await ai_engine.analyze(query="cpu high", validate_json=True)  # noqa: F841  # Variable for test verification
    assert isinstance(result, str)
    parsed = json.loads(result)
    assert "data_assessment" in parsed
    assert parsed["escalation_recommended"] is False


def test_validate_root_cause_output_valid():
    raw = json.dumps(
        {
            "data_assessment": {
                "reliability_score": 0.9,
                "reliability_concerns": [],
            },
            "candidates": [
                {
                    "rank": 1,
                    "root_cause": "test",
                    "confidence": 0.8,
                    "expected_observations_if_true": [],
                    "missing_data": [],
                    "is_verifiable": True,
                    "evidence": [],
                }
            ],
            "multi_root_cause_note": "",
            "escalation_recommended": False,
            "escalation_reason": "",
            "recommended_action": "",
        },
        ensure_ascii=False,
    )
    validated = ai_engine._validate_root_cause_output(raw)
    assert validated is not None
    assert "data_assessment" in validated


def test_validate_root_cause_output_invalid():
    assert ai_engine._validate_root_cause_output("not json") is None
    assert ai_engine._validate_root_cause_output("") is None
    assert ai_engine._validate_root_cause_output("{}") is None


def test_fallback_schema_error_json():
    s = ai_engine._fallback_schema_error_json("schema mismatch")
    assert isinstance(s, str)
    data = json.loads(s)
    assert data["escalation_recommended"] is True
    assert "schema mismatch" in data["data_assessment"]["reliability_concerns"][0]


async def test_predictive_analysis_engine_predict_system_anomalies():
    engine = ai_engine.PredictiveAnalysisEngine()
    metrics = {
        "cpu": {"usage_percent": 95},
        "memory": {"usage_percent": 90},
        "disk": [{"usage_percent": 95, "mount_point": "/"}],
    }
    result = await engine.predict_system_anomalies(metrics, prediction_horizon_hours=24)  # noqa: F841  # Variable for test verification
    assert isinstance(result, dict)
    assert "predicted_anomalies" in result
    assert len(result["predicted_anomalies"]) == 3
    assert result["confidence"] == 0.95


async def test_predictive_analysis_engine_predict_capacity_needs():
    engine = ai_engine.PredictiveAnalysisEngine()
    metrics = {
        "cpu": {"usage_percent": 80},
        "memory": {"usage_percent": 70},
    }
    result = await engine.predict_capacity_needs(metrics, growth_rate=0.1)  # noqa: F841  # Variable for test verification
    assert "predictions_3_months" in result
    assert "predictions_6_months" in result
    assert result["predictions_3_months"]["cpu"] == 80 * 1.3
    assert result["predictions_6_months"]["memory"] == 70 * 1.6


async def test_intelligent_recommendation_engine_generate_recommendations():
    engine = ai_engine.IntelligentRecommendationEngine()
    recs = await engine.generate_recommendations(
        {"id": "1", "type": "cpu_high", "severity": "critical"}
    )
    assert isinstance(recs, list)
    assert len(recs) == 3
    assert all("action" in r for r in recs)
    assert any(r["type"] == "escalation" for r in recs)


async def test_intelligent_recommendation_engine_get_personalized_recommendations():
    engine = ai_engine.IntelligentRecommendationEngine()
    recs = await engine.get_personalized_recommendations(
        "u1", [{"type": "optimization"}, {"type": "optimization"}]
    )
    assert isinstance(recs, list)
    assert len(recs) == 1
    assert recs[0]["type"] == "optimization"


async def test_natural_language_interaction_process_query():
    nli = ai_engine.NaturalLanguageInteraction()
    result = await nli.process_natural_language_query(  # noqa: F841  # Variable for test verification
        "what is the cpu status?",
        context={"metrics": {"cpu": "80%"}},
    )
    assert result["intent"] == "status_query"
    assert result["entities"]["metric"] == "cpu"
    assert "response" in result


async def test_natural_language_interaction_maintain_conversation():
    nli = ai_engine.NaturalLanguageInteraction()
    result = await nli.maintain_conversation("u1", "predict memory trends")  # noqa: F841  # Variable for test verification
    assert "conversation_history" in result
    assert len(nli.conversation_history["u1"]) == 2

    # Truncation to 10 messages is exercised by adding more turns.
    for i in range(10):
        await nli.maintain_conversation("u1", f"query {i}")
    assert len(nli.conversation_history["u1"]) == 10
