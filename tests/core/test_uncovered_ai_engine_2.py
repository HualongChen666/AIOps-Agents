# -*- coding: utf-8 -*-
"""Coverage tests for core/ai_engine.py (additional uncovered branches)."""

import asyncio
import json
import sys
import types
from unittest.mock import AsyncMock, MagicMock

import pytest

# Stub heavy RAG submodules before importing core.ai_engine
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
    _vectorizer.SentenceTransformerEmbedding = type(
        "SentenceTransformerEmbedding", (), {"__init__": lambda self, **k: None}
    )
    sys.modules["core.ai.rag.vectorizer"] = _vectorizer

import core.ai_engine as ai_engine  # noqa: E402

pytestmark = [pytest.mark.core]


class _FakeLLMRouter:
    def __init__(self, content="fake response"):
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


class _FakeCostMonitor:
    def __init__(self, budget_ok=True, session_ok=True):
        self.budget_ok = budget_ok
        self.session_ok = session_ok
        self.model_configs = [{"max_tokens": 8000, "cost_per_1k": 0.002}]

    def estimate_tokens(self, text):
        return len(text) // 4

    def check_budget(self, cost):
        return self.budget_ok

    def get_cost_per_1k(self, model, default=0.001):
        return 0.002

    def record_cost(self, cost):
        pass


class _FakeSessionBudget:
    def __init__(self, ok=True):
        self.ok = ok

    def check_and_record(self, tokens, cost):
        return self.ok

    def record_cost(self, cost):
        pass


class _FakeSessionBudgetFail:
    def check_and_record(self, tokens, cost):
        return False

    def record_cost(self, cost):
        pass


def _stub_base(monkeypatch, router=None):
    monkeypatch.setattr(ai_engine, "get_llm_router", lambda: router if router is not None else _FakeLLMRouter())
    monkeypatch.setattr(ai_engine, "CONTENT_MODERATION_AVAILABLE", False)
    monkeypatch.setattr(ai_engine, "_rag_pipeline", None)
    monkeypatch.setattr(ai_engine, "_langfuse_available", False)
    monkeypatch.setattr(ai_engine, "_rate_limit_wait", AsyncMock())
    monkeypatch.setattr(
        ai_engine,
        "AI_CONFIG",
        {
            "is_enabled": True,
            "api_key": "test",
            "base_url": "http://test",
            "model": "fake",
            "timeout": 10,
            "max_retries": 1,
        },
    )


def test_compute_prompt_token_budget(monkeypatch):
    # Without cost monitor, default 7000 is returned.
    monkeypatch.setattr(ai_engine, "get_llm_cost_monitor", None)
    budget = ai_engine._compute_prompt_token_budget(ai_engine.SYSTEM_PROMPT)
    assert budget == 7000

    # With cost monitor
    monkeypatch.setattr(ai_engine, "get_llm_cost_monitor", lambda: _FakeCostMonitor())
    budget = ai_engine._compute_prompt_token_budget(ai_engine.SYSTEM_PROMPT)
    assert budget > 0


def test_validate_root_cause_output_markdown_and_invalid():
    raw = "```json\n" + json.dumps({
        "data_assessment": {"reliability_score": 0.8, "reliability_concerns": []},
        "candidates": [{
            "rank": 1,
            "root_cause": "x",
            "confidence": 0.8,
            "expected_observations_if_true": [],
            "missing_data": [],
            "is_verifiable": True,
            "evidence": [],
        }],
        "multi_root_cause_note": "",
        "escalation_recommended": False,
        "escalation_reason": "",
        "recommended_action": "",
    }) + "\n```"
    assert ai_engine._validate_root_cause_output(raw) is not None

    # Invalid rank type should be caught by validator and return None
    invalid = json.dumps({
        "data_assessment": {"reliability_score": 0.8, "reliability_concerns": []},
        "candidates": [{
            "rank": "abc",
            "root_cause": "x",
            "confidence": 0.8,
            "expected_observations_if_true": [],
            "missing_data": [],
            "is_verifiable": True,
            "evidence": [],
        }],
        "multi_root_cause_note": "",
        "escalation_recommended": False,
        "escalation_reason": "",
        "recommended_action": "",
    })
    assert ai_engine._validate_root_cause_output(invalid) is None


def test_fallback_schema_error_json():
    s = ai_engine._fallback_schema_error_json("bad")
    assert "bad" in s


async def test_analyze_invalid_platform(monkeypatch):
    _stub_base(monkeypatch)
    result = await ai_engine.analyze(query="q", platform="unknown")
    assert isinstance(result, str)
    assert "unknown" not in result


async def test_analyze_disabled(monkeypatch):
    monkeypatch.setattr(ai_engine, "_rate_limit_wait", AsyncMock())
    monkeypatch.setattr(
        ai_engine, "AI_CONFIG", {"is_enabled": False}
    )
    result = await ai_engine.analyze(query="q", platform="linux")
    assert "规则降级" in result
    assert "linux" in result


async def test_analyze_rich_context(monkeypatch):
    _stub_base(monkeypatch, _FakeLLMRouter("analysis"))
    rich = {
        "top_processes": [{"pid": 1, "name": "a"}],
        "recent_alerts": [{"level": "warning", "title": "t", "desc": "d"}],
        "recent_repairs": [{"script_key": "r", "success": True}],
        "stats": {"alerts": 5},
        "service_metrics": {"qps": 10},
        "dependencies": {"svc": ["db"]},
        "upstream_callers": {"api": {"qps": 1}},
        "downstream_dependencies": {"api": {"db": 1}},
        "infrastructure_metrics": {"cpu": 0.5},
        "change_events": [{"timestamp": "t", "type": "deploy", "target": "svc", "description": "d"}],
        "correlated_alerts": [{"level": "critical", "title": "t", "source": "s", "desc": "d"}],
    }
    result = await ai_engine.analyze(query="cpu high", platform="linux", rich_context=rich)
    assert isinstance(result, str)
    assert "analysis" in result


async def test_analyze_rag_context(monkeypatch):
    _stub_base(monkeypatch, _FakeLLMRouter("rag response"))
    rag = AsyncMock(return_value="rag knowledge")
    monkeypatch.setattr(ai_engine, "_rag_pipeline", type("RAG", (), {"retrieve_and_generate": rag})())
    result = await ai_engine.analyze(query="cpu", platform="linux")
    assert isinstance(result, str)
    rag.assert_awaited_once()


async def test_analyze_rag_exception(monkeypatch):
    _stub_base(monkeypatch, _FakeLLMRouter("ok"))
    rag = AsyncMock(side_effect=RuntimeError("rag fail"))
    monkeypatch.setattr(ai_engine, "_rag_pipeline", type("RAG", (), {"retrieve_and_generate": rag})())
    result = await ai_engine.analyze(query="cpu", platform="linux")
    assert "ok" in result


async def test_analyze_content_moderation_blocks(monkeypatch):
    _stub_base(monkeypatch)
    monkeypatch.setattr(ai_engine, "CONTENT_MODERATION_AVAILABLE", True)
    monkeypatch.setattr(ai_engine, "moderate_content", lambda texts: (False, ["injection"]))
    from fastapi import HTTPException
    with pytest.raises(HTTPException):
        await ai_engine.analyze(query="bad", platform="linux")


async def test_analyze_cost_budget_exhausted(monkeypatch):
    _stub_base(monkeypatch)
    monkeypatch.setattr(ai_engine, "get_llm_cost_monitor", lambda: _FakeCostMonitor(budget_ok=False))
    result = await ai_engine.analyze(query="cpu", platform="linux")
    assert "规则降级" in result


async def test_analyze_session_budget_exhausted(monkeypatch):
    _stub_base(monkeypatch)
    monkeypatch.setattr(ai_engine, "get_llm_cost_monitor", lambda: _FakeCostMonitor(budget_ok=True))
    monkeypatch.setattr(ai_engine, "get_session_budget", lambda sid: _FakeSessionBudgetFail())
    result = await ai_engine.analyze(
        query="cpu", platform="linux", rich_context={"session_id": "s1"}
    )
    assert "规则降级" in result


async def test_analyze_llm_router_exception(monkeypatch):
    _stub_base(monkeypatch)
    bad_router = type("BadRouter", (), {})()
    bad_router.generate = AsyncMock(side_effect=RuntimeError("llm down"))
    monkeypatch.setattr(ai_engine, "get_llm_router", lambda: bad_router)
    result = await ai_engine.analyze(query="cpu", platform="linux")
    assert "规则降级" in result


async def test_analyze_llm_empty_content(monkeypatch):
    _stub_base(monkeypatch, _FakeLLMRouter(""))
    result = await ai_engine.analyze(query="cpu", platform="linux")
    assert "规则降级" in result


async def test_analyze_validate_json_valid(monkeypatch):
    payload = {
        "data_assessment": {"reliability_score": 0.8, "reliability_concerns": []},
        "candidates": [{
            "rank": 1,
            "root_cause": "cpu",
            "confidence": 0.85,
            "expected_observations_if_true": [],
            "missing_data": [],
            "is_verifiable": True,
            "evidence": [],
        }],
        "multi_root_cause_note": "",
        "escalation_recommended": False,
        "escalation_reason": "",
        "recommended_action": "check",
    }
    _stub_base(monkeypatch, _FakeLLMRouter(json.dumps(payload, ensure_ascii=False)))
    result = await ai_engine.analyze(query="cpu", platform="linux", validate_json=True)
    parsed = json.loads(result)
    assert parsed["escalation_recommended"] is False


async def test_analyze_validate_json_invalid_fallback(monkeypatch):
    _stub_base(monkeypatch, _FakeLLMRouter("not json"))
    result = await ai_engine.analyze(query="cpu", platform="linux", validate_json=True)
    assert "escalation_recommended" in result


def test_http_client_and_close(monkeypatch):
    monkeypatch.setenv("HTTPX_SSL_VERIFY", "false")
    ai_engine._http_client = None
    ai_engine._http_client_lock = None
    client = ai_engine._get_http_client()
    assert client is not None
    assert client is ai_engine._get_http_client()

    async def close():
        await ai_engine.close_http_client()

    asyncio.run(close())
    assert ai_engine._http_client is None


async def test_close_langfuse_client(monkeypatch):
    mock_client = MagicMock()
    ai_engine._langfuse_client = mock_client
    monkeypatch.setattr(ai_engine.asyncio, "sleep", AsyncMock())
    await ai_engine.close_langfuse_client()
    mock_client.flush.assert_called_once()
    assert ai_engine._langfuse_client is None


async def test_rate_limit_wait(monkeypatch):
    import time as _time
    base = _time.monotonic()
    monkeypatch.setattr(ai_engine.time, "monotonic", lambda: base + 10)
    monkeypatch.setattr(ai_engine, "_next_available_time", base + 13)
    monkeypatch.setattr(ai_engine.asyncio, "sleep", AsyncMock())
    await ai_engine._rate_limit_wait()
    # If already past the slot, no sleep branch
    monkeypatch.setattr(ai_engine, "_next_available_time", 0.0)
    await ai_engine._rate_limit_wait()


async def test_llm_analysis_service_runbook(monkeypatch):
    _stub_base(monkeypatch, _FakeLLMRouter("runbook"))
    service = ai_engine.LLMAnalysisService()
    result = await service.generate_runbook(
        {"id": "a1", "title": "CPU", "desc": "high"},
        {"platform": "linux"},
    )
    assert "runbook" in result
    assert result["alert_id"] == "a1"


async def test_llm_analysis_service_search_similar_success(monkeypatch):
    monkeypatch.setitem(
        sys.modules,
        "core.rag_engine",
        types.SimpleNamespace(search_similar=lambda query, limit: [{"id": "1"}]),
    )
    monkeypatch.setattr(ai_engine, "AUDIT_LOGGER_AVAILABLE", True)
    monkeypatch.setattr(ai_engine, "log_audit_event", MagicMock())
    service = ai_engine.LLMAnalysisService()
    result = await service.search_similar("cpu", limit=5)
    assert len(result) == 1
    assert result[0]["id"] == "1"


async def test_llm_analysis_service_search_similar_failure(monkeypatch):
    monkeypatch.setitem(
        sys.modules,
        "core.rag_engine",
        types.SimpleNamespace(
            search_similar=lambda query, limit: (_ for _ in ()).throw(RuntimeError("fail"))
        ),
    )
    monkeypatch.setattr(ai_engine, "AUDIT_LOGGER_AVAILABLE", True)
    monkeypatch.setattr(ai_engine, "log_audit_event", MagicMock(side_effect=RuntimeError("audit fail")))
    service = ai_engine.LLMAnalysisService()
    result = await service.search_similar("cpu", limit=5)
    assert result == []


def test_predictive_engine_empty():
    engine = ai_engine.PredictiveAnalysisEngine()
    result = asyncio.run(engine.predict_system_anomalies({"cpu": {"usage_percent": 10}}, 12))
    assert result["predicted_anomalies"] == []
    assert result["confidence"] == 0.0


def test_intelligent_recommendation_scaling():
    engine = ai_engine.IntelligentRecommendationEngine()
    result = asyncio.run(engine.get_personalized_recommendations("u1", [{"type": "scaling"}, {"type": "scaling"}]))
    assert any(r["type"] == "scaling" for r in result)


def test_intelligent_recommendation_disk(monkeypatch):
    _stub_base(monkeypatch)
    engine = ai_engine.IntelligentRecommendationEngine()
    result = asyncio.run(engine.generate_recommendations({"id": "2", "type": "disk_high", "severity": "critical"}))
    assert any("disk" in r["action"].lower() or "Clean" in r["action"] for r in result)


def test_natural_language_interaction_branches():
    nli = ai_engine.NaturalLanguageInteraction()
    cases = [
        ("what is the cpu status last hour?", "status_query", "cpu", "1h"),
        ("why is memory high today?", "root_cause_query", "memory", "24h"),
        ("how to fix disk issue?", "repair_query", "disk", None),
        ("predict trends this week", "prediction_query", None, "7d"),
        ("recommend optimizations", "recommendation_query", None, None),
        ("hello", "general_query", None, None),
    ]
    for query, expected_intent, expected_metric, expected_time in cases:
        result = asyncio.run(nli.process_natural_language_query(query, {"metrics": {"cpu": "80%"}}))
        assert result["intent"] == expected_intent
        if expected_metric:
            assert result["entities"].get("metric") == expected_metric
        if expected_time:
            assert result["entities"].get("time_range") == expected_time


def test_natural_language_conversation_truncation():
    nli = ai_engine.NaturalLanguageInteraction()
    for i in range(12):
        asyncio.run(nli.maintain_conversation("u1", f"msg {i}"))
    assert len(nli.conversation_history["u1"]) == 10
