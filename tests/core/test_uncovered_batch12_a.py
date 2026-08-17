# -*- coding: utf-8 -*-
"""Coverage tests for batch 12-a core modules."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import numpy as np
import pytest

pytestmark = [pytest.mark.core]


import config

# ---------------------------------------------------------------------------
# core.analysis.l2.model_router
# ---------------------------------------------------------------------------
import core.analysis.l2.model_router as mr


@pytest.fixture
def router_cfg():
    return {
        "models": [
            {
                "provider": "openai",
                "model": "gpt-3.5-turbo",
                "cost_per_1k": 0.002,
                "max_tokens": 4096,
            },
            {"provider": "openai", "model": "gpt-4", "cost_per_1k": 0.03, "max_tokens": 8192},
        ],
        "token_cost_threshold": 10,
    }


@pytest.fixture(autouse=True)
def disable_enhanced_router(monkeypatch):
    monkeypatch.setattr(mr, "ENHANCED_ROUTER_AVAILABLE", False)


def test_model_router_init(router_cfg):
    router = mr.MultiModelRouter(router_cfg)
    assert router._is_initialized
    assert router.models[0]["model"] == "gpt-3.5-turbo"
    assert router.get_status()["initialized"] is True
    assert router.get_model_stats()["total_models"] == 2


def test_model_router_init_no_models():
    router = mr.MultiModelRouter({})
    assert not router._is_initialized


def test_estimate_tokens():
    router = mr.MultiModelRouter({"models": []})
    assert router.estimate_tokens("abcd") == 1


@pytest.mark.asyncio
async def test_select_model_force_found(router_cfg):
    router = mr.MultiModelRouter(router_cfg)
    model = await router.select_model("test", force_model="gpt-4")
    assert model["model"] == "gpt-4"


@pytest.mark.asyncio
async def test_select_model_force_missing_uses_cheapest(router_cfg):
    router = mr.MultiModelRouter(router_cfg)
    model = await router.select_model("small")
    assert model["model"] == "gpt-3.5-turbo"


@pytest.mark.asyncio
async def test_select_model_token_threshold(router_cfg):
    router = mr.MultiModelRouter(router_cfg)
    model = await router.select_model("x" * 100)
    assert model["model"] == "gpt-4"


@pytest.mark.asyncio
async def test_select_model_no_cheap_fit_falls_back(router_cfg, monkeypatch):
    # Force gpt-3.5 to report tiny max_tokens so no model fits the cheap path.
    router = mr.MultiModelRouter(router_cfg)
    for m in router.models:
        m["max_tokens"] = 1
    model = await router.select_model("small")
    assert model is not None


def test_get_next_model(router_cfg):
    router = mr.MultiModelRouter(router_cfg)
    first = router.models[0]
    second = router._get_next_model(first)
    assert second == router.models[1]
    assert router._get_next_model(second) is None
    assert router._get_next_model({"model": "ghost"}) is None


def test_build_prompt_no_context(router_cfg):
    router = mr.MultiModelRouter(router_cfg)
    assert router._build_prompt("hello", None) == "hello"


def test_build_prompt_full_context(router_cfg):
    router = mr.MultiModelRouter(router_cfg)
    ctx = {
        "rag_enabled": True,
        "rag_knowledge": [{"text": "known issue"}],
        "metrics": "cpu 90%",
        "logs": "oom",
    }
    full = router._build_prompt("check", ctx)
    assert "known issue" in full
    assert "cpu 90%" in full
    assert "oom" in full


@pytest.mark.asyncio
async def test_route_analysis_success(router_cfg, monkeypatch):
    router = mr.MultiModelRouter(router_cfg)
    monkeypatch.setattr(config, "AI_CONFIG", {"api_key": "ak", "model": "gpt-4"})
    monkeypatch.setattr("core.ai_engine.analyze", MagicMock(return_value={"result": "ok"}))
    result = await router.route_analysis(
        "prompt", {"rag_enabled": True, "rag_knowledge": [{"text": "k"}]}
    )
    assert result["routing_metadata"]["model"] == "gpt-3.5-turbo"
    assert result["result"] == "ok"


@pytest.mark.asyncio
async def test_route_analysis_error_no_fallback(router_cfg, monkeypatch):
    router = mr.MultiModelRouter({"models": [router_cfg["models"][0]], "token_cost_threshold": 10})
    monkeypatch.setattr("core.ai_engine.analyze", MagicMock(side_effect=Exception("boom")))
    result = await router.route_analysis("prompt")
    assert "error" in result


@pytest.mark.asyncio
async def test_route_analysis_fallback(router_cfg, monkeypatch):
    router = mr.MultiModelRouter(router_cfg)
    monkeypatch.setattr(
        "core.ai_engine.analyze", MagicMock(side_effect=[Exception("boom"), {"result": "ok"}])
    )
    result = await router.route_analysis("prompt")
    assert result["result"] == "ok"


def test_init_and_get_model_router(monkeypatch):
    monkeypatch.setattr(mr, "_model_router", None)
    inst = mr.init_model_router({"models": []})
    assert inst is not None
    assert mr.get_model_router() is inst


# ---------------------------------------------------------------------------
# core.alert_providers.datadog
# ---------------------------------------------------------------------------
from core.alert_providers.datadog import DatadogAlertProvider, _safe_float


def test_safe_float():
    assert _safe_float("1.5") == 1.5
    assert _safe_float(None) == 0.0
    assert _safe_float("bad") == 0.0
    assert _safe_float(42) == 42.0


def test_datadog_normalize_list():
    prov = DatadogAlertProvider()
    raw = [
        {
            "title": "t",
            "text": "m",
            "hostname": "h1",
            "alert_metric": "cpu",
            "metric_snapshot": {"cpu": 90},
        },
        {"title": "t2", "message": "m2", "host": "h2", "event_type": "recovery"},
    ]
    out = prov.normalize(raw)
    assert len(out) == 2
    assert out[0]["source"] == "datadog"
    assert out[1]["status"] == "resolved"


def test_datadog_normalize_dict():
    prov = DatadogAlertProvider()
    raw = {"title": "t", "body": "b", "tags": ["service:web", "platform:linux"]}
    out = prov.normalize(raw)
    assert len(out) == 1
    assert out[0]["service"] == "web"
    assert out[0]["platform"] == "linux"
    assert out[0]["labels"]["service"] == "web"


def test_datadog_normalize_invalid():
    prov = DatadogAlertProvider()
    assert prov.normalize("not a payload") == []
    assert prov.normalize([1, 2, 3]) == []


def test_datadog_severity_and_priority():
    prov = DatadogAlertProvider()
    for key, sev in [
        ("1", "info"),
        ("2", "low"),
        ("3", "warning"),
        ("4", "high"),
        ("5", "critical"),
        ("p1", "info"),
        ("p5", "critical"),
    ]:
        out = prov.normalize({"priority": key})[0]
        assert out["severity"] == sev
    out = prov.normalize({"priority": "unknown"})[0]
    assert out["severity"] == "unknown"


def test_datadog_labels_from_dict():
    prov = DatadogAlertProvider()
    out = prov.normalize({"tags": {"team": "sre"}})[0]
    assert out["labels"]["team"] == "sre"


def test_datadog_metric_snapshot():
    prov = DatadogAlertProvider()
    out = prov.normalize({"metric_snapshot": {"mem": 85.5}})[0]
    assert out["metric"] == "mem"
    assert out["value"] == 85.5


import core.db_engine as db_engine
import core.heal_graph as heal_graph

# ---------------------------------------------------------------------------
# core.mcp_tools
# ---------------------------------------------------------------------------
import core.mcp_tools as mcp
import core.rag_engine as rag_engine_mod


def test_validate_str():
    assert mcp._validate_str("ok", "name") == "ok"
    with pytest.raises(ValueError):
        mcp._validate_str(123, "name")
    with pytest.raises(ValueError):
        mcp._validate_str("", "name")
    with pytest.raises(ValueError):
        mcp._validate_str("bad\x00", "name")
    with pytest.raises(ValueError):
        mcp._validate_str("x" * 1000, "name")


def test_validate_bool():
    assert mcp._validate_bool(True, "b") is True
    with pytest.raises(ValueError):
        mcp._validate_bool("true", "b")


def test_validate_int():
    assert mcp._validate_int(5, "i", 1, 10) == 5
    with pytest.raises(ValueError):
        mcp._validate_int(True, "i", 1, 10)
    with pytest.raises(ValueError):
        mcp._validate_int(5.0, "i", 1, 10)
    with pytest.raises(ValueError):
        mcp._validate_int(15, "i", 1, 10)


@pytest.mark.asyncio
async def test_trigger_repair_success(monkeypatch):
    state = MagicMock(fix_applied=True, verification="ok", error=None)
    monkeypatch.setattr(heal_graph, "HealState", MagicMock(return_value=state))
    monkeypatch.setattr(heal_graph, "run_heal", AsyncMock(return_value=state))
    result = await mcp.trigger_repair("A1", "user", "fix it")
    assert result["success"] is True
    assert result["status"] == "completed"
    assert result["fix_applied"] is True


@pytest.mark.asyncio
async def test_trigger_repair_pending(monkeypatch):
    state = MagicMock(fix_applied=False, verification=None, error=None)
    monkeypatch.setattr(heal_graph, "HealState", MagicMock(return_value=state))
    monkeypatch.setattr(heal_graph, "run_heal", AsyncMock(return_value=state))
    result = await mcp.trigger_repair("A2", "user")
    assert result["success"] is False
    assert result["status"] == "pending"


@pytest.mark.asyncio
async def test_trigger_repair_error(monkeypatch):
    monkeypatch.setattr(heal_graph, "run_heal", AsyncMock(side_effect=RuntimeError("heal failed")))
    result = await mcp.trigger_repair("A3", "user")
    assert result["success"] is False
    assert result["status"] == "error"
    assert "heal failed" in result["error"]


@pytest.mark.asyncio
async def test_get_host_health_no_data(monkeypatch):
    monkeypatch.setattr(mcp, "get_cached_snapshot", MagicMock(return_value=None))
    result = await mcp.get_host_health("host-1")
    assert result == {}


@pytest.mark.asyncio
async def test_get_host_health_with_data(monkeypatch):
    snapshot = {"cpu": 0.5, "mem": 0.8}
    monkeypatch.setattr(mcp, "get_cached_snapshot", MagicMock(return_value=snapshot))
    result = await mcp.get_host_health("host-1")
    assert result == snapshot


@pytest.mark.asyncio
async def test_get_metrics(monkeypatch):
    monkeypatch.setattr(
        mcp, "get_cached_snapshot", MagicMock(return_value={"cpu": 0.5, "mem": 0.8})
    )
    result = await mcp.get_metrics("host-1", ["cpu", "disk"])
    assert result["cpu"] == 0.5
    assert result["disk"] is None

    monkeypatch.setattr(mcp, "get_cached_snapshot", MagicMock(return_value=None))
    result = await mcp.get_metrics("host-1", ["cpu"])
    assert result["cpu"] is None


def test_get_metrics_validation():
    with pytest.raises(ValueError):
        asyncio.run(mcp.get_metrics("h", 123))


@pytest.mark.asyncio
async def test_approve_repair(monkeypatch):
    db = MagicMock()
    db.get_repair_record.return_value = None
    monkeypatch.setattr(db_engine, "db", db)
    result = await mcp.approve_repair("R1", True)
    assert result["status"] == "approved"
    assert db.update_repair_status.called

    db.reset_mock()
    db.get_repair_record.return_value = {"id": "R1"}
    result = await mcp.approve_repair("R1", False, "rejected by user")
    assert result["status"] == "rejected"


@pytest.mark.asyncio
async def test_trigger_repair_with_hitl(monkeypatch):
    state = MagicMock(fix_applied=True, verification="ok", error=None)
    monkeypatch.setattr(heal_graph, "HealState", MagicMock(return_value=state))
    monkeypatch.setattr(heal_graph, "run_heal", AsyncMock(return_value=state))
    result = await mcp.trigger_repair_with_hitl("A4", "admin", "go")
    assert result["success"] is True


# ---------------------------------------------------------------------------
# core.analysis.l2.rag_engine
# ---------------------------------------------------------------------------
import core.analysis.l2.rag_engine as rag_engine
from core.analysis.l2.rag_engine import RAGEngine


@pytest.fixture
def qdrant_enabled(monkeypatch):
    monkeypatch.setattr(rag_engine, "QDRANT_AVAILABLE", True)
    monkeypatch.setattr(rag_engine, "SENTENCE_TRANSFORMERS_AVAILABLE", False)
    client = MagicMock()
    client.get_collections.return_value = MagicMock(collections=[])
    client.search.return_value = []
    client.upsert.return_value = None
    client.delete.return_value = None
    monkeypatch.setattr(rag_engine, "QdrantClient", MagicMock(return_value=client))
    monkeypatch.setattr(rag_engine, "VectorParams", MagicMock())
    monkeypatch.setattr(rag_engine, "Distance", MagicMock())
    monkeypatch.setattr(rag_engine, "PointStruct", MagicMock())
    monkeypatch.setattr(rag_engine, "Filter", MagicMock())
    monkeypatch.setattr(rag_engine, "FieldCondition", MagicMock())
    monkeypatch.setattr(rag_engine, "MatchValue", MagicMock())
    return client


def test_rag_engine_init_success(qdrant_enabled):
    engine = RAGEngine({"qdrant_host": "localhost", "qdrant_port": 6333})
    assert engine._is_initialized
    assert engine.get_status()["qdrant_available"] is True


def test_rag_engine_init_qdrant_failure(monkeypatch):
    monkeypatch.setattr(rag_engine, "QDRANT_AVAILABLE", True)
    monkeypatch.setattr(
        rag_engine, "QdrantClient", MagicMock(side_effect=Exception("conn refused"))
    )
    engine = RAGEngine({})
    assert not engine._is_initialized


def test_rag_engine_embed_zero():
    engine = RAGEngine({})
    vec = engine.embed_text("hello")
    assert vec == [0.0] * 384


def test_rag_engine_load_and_embed_text(monkeypatch):
    emb = MagicMock(
        encode=MagicMock(return_value=MagicMock(tolist=MagicMock(return_value=[0.5] * 384)))
    )
    monkeypatch.setattr(rag_engine, "SENTENCE_TRANSFORMERS_AVAILABLE", True)
    monkeypatch.setattr(rag_engine, "SentenceTransformer", MagicMock(return_value=emb))
    engine = RAGEngine({})
    engine._load_embedding_model()
    assert engine.embedding_model_instance is emb
    vec = engine.embed_text("hello")
    assert vec == [0.5] * 384


def test_rag_engine_embed_exception(monkeypatch):
    emb = MagicMock(encode=MagicMock(side_effect=Exception("encode fail")))
    monkeypatch.setattr(rag_engine, "SENTENCE_TRANSFORMERS_AVAILABLE", True)
    monkeypatch.setattr(rag_engine, "SentenceTransformer", MagicMock(return_value=emb))
    engine = RAGEngine({})
    engine._load_embedding_model()
    vec = engine.embed_text("hello")
    assert vec == [0.0] * 384


@pytest.mark.asyncio
async def test_rag_add_knowledge(qdrant_enabled):
    engine = RAGEngine({})
    assert await engine.add_knowledge("knowledge", {"tag": "x"}, "id1") is True


@pytest.mark.asyncio
async def test_rag_add_knowledge_not_initialized():
    engine = RAGEngine({})
    engine._is_initialized = False
    assert await engine.add_knowledge("x") is False


@pytest.mark.asyncio
async def test_rag_retrieve_knowledge(qdrant_enabled):
    hit = MagicMock()
    hit.score = 0.95
    hit.payload = {"text": "answer", "timestamp": "2024-01-01", "source": "runbook"}
    qdrant_enabled.search.return_value = [hit]
    engine = RAGEngine({})
    results = await engine.retrieve_knowledge("query")
    assert len(results) == 1
    assert results[0]["text"] == "answer"
    assert results[0]["metadata"]["source"] == "runbook"


@pytest.mark.asyncio
async def test_rag_search_similar_with_filters(qdrant_enabled):
    hit = MagicMock(score=0.8, payload={"text": "res", "timestamp": "t"})
    qdrant_enabled.search.return_value = [hit]
    engine = RAGEngine({})
    results = await engine.search_similar("q", 5, filters={"source": "runbook"})
    assert len(results) == 1
    assert rag_engine.Filter.called


@pytest.mark.asyncio
async def test_rag_augment_context_with_knowledge(qdrant_enabled):
    hit = MagicMock(score=0.9, payload={"text": "tip", "timestamp": "t"})
    qdrant_enabled.search.return_value = [hit]
    engine = RAGEngine({})
    ctx = await engine.augment_context("q", base_context={"host": "h1"}, limit=1)
    assert ctx["rag_enabled"] is True
    assert ctx["rag_count"] == 1
    assert ctx["host"] == "h1"


@pytest.mark.asyncio
async def test_rag_augment_context_no_knowledge(qdrant_enabled):
    qdrant_enabled.search.return_value = []
    engine = RAGEngine({})
    ctx = await engine.augment_context("q")
    assert ctx["rag_enabled"] is False
    assert ctx["rag_count"] == 0


@pytest.mark.asyncio
async def test_rag_delete_knowledge(qdrant_enabled):
    engine = RAGEngine({})
    assert await engine.delete_knowledge("id1") is True


@pytest.mark.asyncio
async def test_rag_delete_knowledge_error(qdrant_enabled):
    qdrant_enabled.delete.side_effect = Exception("boom")
    engine = RAGEngine({})
    assert await engine.delete_knowledge("id1") is False


def test_rag_close(qdrant_enabled):
    engine = RAGEngine({})
    engine.close()
    assert not engine._is_initialized
    qdrant_enabled.close.assert_called_once()


def test_init_and_get_rag_engine(monkeypatch):
    monkeypatch.setattr(rag_engine, "_rag_engine", None)
    inst = rag_engine.init_rag_engine({})
    assert inst is not None
    assert rag_engine.get_rag_engine() is inst


# ---------------------------------------------------------------------------
# core.causal.algorithms
# ---------------------------------------------------------------------------
from core.causal.algorithms import ConditionalIndependenceTest, GESAlgorithm, PCAlgorithm
from core.causal.graph import CausalEdge, CausalGraph, CausalStrength


def test_conditional_independence_test():
    result = ConditionalIndependenceTest(True, 0.1, 0.05)
    assert result.independent is True


def test_pc_algorithm_discovers_graph():
    np.random.seed(0)
    data = np.random.randn(50, 3)
    pc = PCAlgorithm(alpha=0.05)
    graph = pc.discover(data, ["a", "b", "c"])
    assert "a" in graph.nodes
    assert "b" in graph.nodes
    assert "c" in graph.nodes


def test_pc_test_independence_conditioning_set():
    data = np.random.randn(30, 3)
    pc = PCAlgorithm(alpha=0.05)
    result = pc._test_independence(data, 0, 1, {2})
    assert result.independent in (True, False)
    assert isinstance(result.p_value, float)


def test_ges_algorithm_discovers_graph():
    np.random.seed(1)
    data = np.random.randn(50, 3)
    ges = GESAlgorithm(scoring_metric="bic")
    graph = ges.discover(data, ["x", "y", "z"])
    assert len(graph.nodes) == 3


def test_ges_empty_variables():
    data = np.zeros((10, 0))
    ges = GESAlgorithm()
    graph = ges.discover(data, [])
    assert len(graph.nodes) == 0


def test_ges_score_graph_aic():
    data = np.random.randn(20, 2)
    graph = CausalGraph("test")
    graph.add_node("x")
    graph.add_node("y")
    graph.add_edge(CausalEdge("x", "y", strength=CausalStrength.MODERATE))
    ges = GESAlgorithm(scoring_metric="aic")
    score = ges._score_graph(data, graph)
    assert isinstance(score, float)
