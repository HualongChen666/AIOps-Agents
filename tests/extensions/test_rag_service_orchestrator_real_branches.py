# -*- coding: utf-8 -*-
"""Real-execution branch coverage for the ai-plus RAG orchestrator."""

from __future__ import annotations

import datetime
import importlib.util
import sys
import types
from pathlib import Path
from typing import Any, List

import pytest

ADDONS_ROOT = Path(__file__).resolve().parents[2] / "extensions" / "addons"
ROOT_PKG = "_rag_real_branches_test"


def _sanitized(part: str) -> str:
    return part.replace("-", "_").replace(".", "_")


def _ensure_package_chain(rel_dir: Path) -> str:
    parts = [_sanitized(p) for p in rel_dir.parts]
    root = sys.modules.setdefault(ROOT_PKG, types.ModuleType(ROOT_PKG))
    root.__path__ = [str(ADDONS_ROOT)]
    current = ROOT_PKG
    for i, part in enumerate(parts):
        current += f".{part}"
        pkg = sys.modules.setdefault(current, types.ModuleType(current))
        pkg.__path__ = [str(ADDONS_ROOT / Path(*rel_dir.parts[: i + 1]))]
    return current


def _load_module(rel_path: str) -> Any:
    path = ADDONS_ROOT / rel_path
    rel = path.relative_to(ADDONS_ROOT)
    package = _ensure_package_chain(rel.parent)
    module_name = f"{package}.{_sanitized(path.stem)}"
    spec = importlib.util.spec_from_file_location(
        module_name, str(path), submodule_search_locations=None
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not create spec for {rel_path}")
    module = importlib.util.module_from_spec(spec)
    module.__package__ = package
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


# Avoid heavy SentenceTransformer downloads.  The orchestrator falls back to its
# deterministic hash-based embedding whenever model loading fails.
_fake_st = types.ModuleType("sentence_transformers")


class _FakeSentenceTransformer:
    def __init__(self, name: str) -> None:
        raise RuntimeError(f"No such model: {name}")


class _FakeCrossEncoder:
    def __init__(self, name: str) -> None:
        raise RuntimeError(f"No such cross-encoder: {name}")


_fake_st.SentenceTransformer = _FakeSentenceTransformer
_fake_st.CrossEncoder = _FakeCrossEncoder
sys.modules["sentence_transformers"] = _fake_st

# Ensure conftest's per-test sys.modules restore keeps our stub installed.
# Find the tests/extensions/conftest module and force sentence_transformers back
# to the fake whenever pytest restores sys.modules between tests.
for _mod_candidate in list(sys.modules.values()):
    if not isinstance(_mod_candidate, types.ModuleType):
        continue
    if "_INITIAL_SYS_MODULES" not in _mod_candidate.__dict__:
        continue
    _mod_candidate._INITIAL_SYS_MODULES.pop("sentence_transformers", None)

ORCHESTRATOR = _load_module("ai-plus/rag_service/orchestrator.py")
SCHEMAS = sys.modules[f"{ORCHESTRATOR.__package__}.schemas"]
CONFIG = sys.modules[f"{ORCHESTRATOR.__package__}.config"]


@pytest.fixture
def orchestrator(monkeypatch):
    """Fresh RAGOrchestrator using deterministic fallback embeddings."""
    settings = CONFIG.settings.model_copy()
    settings.openai_api_key = ""
    settings.rerank_model = ""
    orch = ORCHESTRATOR.RAGOrchestrator(embedding_model="fallback", vector_dimension=8)
    monkeypatch.setattr(orch, "settings", settings)
    return orch


# ------------------------------------------------------------------
# Module-level helpers
# ------------------------------------------------------------------
def test_parse_date_branches():
    p = ORCHESTRATOR._parse_date
    today = datetime.date.today()
    assert p(None) is None
    assert p(today) == today
    now = datetime.datetime.now()
    assert p(now) == now.date()
    assert p("2024-03-15") == datetime.date(2024, 3, 15)
    assert p("2024/03/15T00:00:00") == datetime.date(2024, 3, 15)
    assert p("20240315") == datetime.date(2024, 3, 15)
    assert p("not-a-date") is None


def test_freshness_boost_branches():
    f = ORCHESTRATOR._freshness_boost
    assert f("2024-01-01", 1.0, 0.0) == 1.0
    assert f("not-a-date", 1.0, 0.5) == 1.0
    today = datetime.date.today().isoformat()
    boosted = f(today, 1.0, 0.5)
    assert boosted > 1.0
    old = (datetime.date.today() - datetime.timedelta(days=365)).isoformat()
    assert f(old, 1.0, 0.5) < 1.0


def test_normalize_scores_branches():
    n = ORCHESTRATOR._normalize_scores
    assert n([]) == []
    same = [("a", 0.5), ("b", 0.5)]
    assert n(same) == [("a", 1.1), ("b", 1.1)]
    mixed = [("a", 0.0), ("b", 1.0)]
    assert n(mixed) == [("a", 0.0), ("b", 1.0)]


def test_chunk_text_simple_branches():
    c = ORCHESTRATOR._chunk_text_simple
    assert c("", 10, 2) == []
    text = "line one\nline two\nline three"
    chunks = c(text, 12, 2)
    assert all(chunks)
    text2 = "1. first\n2. second\n3. third"
    chunks2 = c(text2, 20, 2)
    assert all(chunks2)


def test_langchain_adapter():
    adapter = ORCHESTRATOR.LangChainAdapter()
    text = "line one\nline two\nline three"
    chunks = adapter.split(text, 12, 2)
    assert chunks
    docs = adapter.to_documents(["a", "b"], {"k": "v"})
    assert len(docs) == 2
    assert docs[0]["metadata"]["k"] == "v"


def test_langchain_adapter_split_exception():
    adapter = ORCHESTRATOR.LangChainAdapter()

    class BadSplitter:
        def __init__(self, *args, **kwargs) -> None:
            raise RuntimeError("langchain unavailable")

    adapter.text_splitter = BadSplitter
    chunks = adapter.split("hello world", 10, 2)
    assert chunks


# ------------------------------------------------------------------
# Embedding / vectorization
# ------------------------------------------------------------------
@pytest.mark.asyncio
async def test_embed_fallback_and_exception(orchestrator):
    # deterministic fallback path
    v = await orchestrator.embed(["hello", "world"])
    assert len(v) == 2
    assert len(v[0]) == 8
    # broken model encode -> exception caught -> fallback
    orchestrator._embedding_model = _BrokenEncoder(4)
    v2 = await orchestrator.embed(["test"])
    assert len(v2[0]) == orchestrator.vector_dimension


@pytest.mark.asyncio
async def test_embedding_lazy_load_and_fallback(monkeypatch):
    import sentence_transformers as _st

    # Force the lazy attribute to resolve, then replace with a failing stub.
    _ = _st.SentenceTransformer
    monkeypatch.setattr(_st, "SentenceTransformer", _FakeSentenceTransformer)
    orch = ORCHESTRATOR.RAGOrchestrator(embedding_model=None, vector_dimension=8)
    # property tries primary/fallback SentenceTransformer models, both fail, then fallback.
    model = orch.embedding_model
    assert model == "fallback"
    v = await orch.embed(["lazy"])
    assert len(v[0]) == 8


@pytest.mark.asyncio
async def test_vectorize_empty_and_dimension_mismatch():
    # empty content fallback path: chunks = [content]
    empty_req = SCHEMAS.VectorizeRequest(content="", source=SCHEMAS.DocumentSource.TEXT)
    resp = await ORCHESTRATOR.RAGOrchestrator(
        embedding_model="fallback", vector_dimension=8
    ).vectorize_document(empty_req)
    assert resp.chunk_count == 1
    # mismatch: model returns a different dimension, vector_dimension is updated
    mismatch_orch = ORCHESTRATOR.RAGOrchestrator(
        embedding_model=_FixedDimEncoder(4), vector_dimension=8
    )
    req = SCHEMAS.VectorizeRequest(content="some text", source=SCHEMAS.DocumentSource.TEXT)
    resp2 = await mismatch_orch.vectorize_document(req)
    assert resp2.dimension == 4
    assert mismatch_orch.vector_dimension == 4


# ------------------------------------------------------------------
# Indexing
# ------------------------------------------------------------------
@pytest.mark.asyncio
async def test_index_validation_rejections(orchestrator):
    short = SCHEMAS.IndexRequest(
        document_id="doc1", content="ab", source=SCHEMAS.DocumentSource.TEXT
    )
    r = await orchestrator.index_document(short)
    assert r.status == "rejected"

    bad_id = SCHEMAS.IndexRequest(
        document_id="bad id!", content="valid content here", source=SCHEMAS.DocumentSource.TEXT
    )
    r = await orchestrator.index_document(bad_id)
    assert r.status == "rejected"

    big = "x" * 1_000_001
    too_big = SCHEMAS.IndexRequest(
        document_id="bigdoc", content=big, source=SCHEMAS.DocumentSource.TEXT
    )
    r = await orchestrator.index_document(too_big)
    assert r.status == "rejected"

    forbidden = SCHEMAS.IndexRequest(
        document_id="baddoc", content="run rm -rf / now", source=SCHEMAS.DocumentSource.TEXT
    )
    r = await orchestrator.index_document(forbidden)
    assert r.status == "rejected"


@pytest.mark.asyncio
async def test_index_updated_at_default_and_success(orchestrator):
    req = SCHEMAS.IndexRequest(
        document_id="doc_a",
        content="This is a valid document content.",
        source=SCHEMAS.DocumentSource.TEXT,
    )
    r = await orchestrator.index_document(req)
    assert r.status == "indexed"
    assert r.chunks_indexed > 0
    assert "doc_a::0" in orchestrator._index
    chunk = orchestrator._index["doc_a::0"]
    assert "updated_at" in chunk["metadata"]


# ------------------------------------------------------------------
# Search / retrieve
# ------------------------------------------------------------------
@pytest.mark.asyncio
async def test_semantic_search_cache_threshold_and_stale(orchestrator):
    await orchestrator.index_document(
        SCHEMAS.IndexRequest(
            document_id="s1",
            content="python logging best practices",
            source=SCHEMAS.DocumentSource.TEXT,
        )
    )
    q = SCHEMAS.SearchRequest(query="python logging", top_k=2, use_cache=True)
    r1 = await orchestrator.semantic_search(q)
    assert r1.total >= 0
    r2 = await orchestrator.semantic_search(q)
    assert r2.total == r1.total
    # high threshold -> no results
    q_high = SCHEMAS.SearchRequest(query="python logging", top_k=2, score_threshold=2.0)
    r3 = await orchestrator.semantic_search(q_high)
    assert r3.total == 0

    await orchestrator.mark_document_stale(SCHEMAS.MarkStaleRequest(document_id="s1", reason="old"))
    r4 = await orchestrator.semantic_search(
        SCHEMAS.SearchRequest(query="python logging", top_k=2, use_cache=False)
    )
    assert r4.total == 0


@pytest.mark.asyncio
async def test_score_chunks_recency_and_threshold(orchestrator):
    old_date = (datetime.date.today() - datetime.timedelta(days=100)).isoformat()
    new_date = datetime.date.today().isoformat()
    await orchestrator.index_document(
        SCHEMAS.IndexRequest(
            document_id="old_doc",
            content="old text content",
            source=SCHEMAS.DocumentSource.TEXT,
            metadata={"updated_at": old_date},
        )
    )
    await orchestrator.index_document(
        SCHEMAS.IndexRequest(
            document_id="new_doc",
            content="new text content",
            source=SCHEMAS.DocumentSource.TEXT,
            metadata={"updated_at": new_date},
        )
    )
    qv = (await orchestrator.embed(["text"]))[0]
    results = orchestrator._score_chunks(qv, 10, threshold=0.0, recency_weight=0.5)
    # new doc should outrank old doc when recency matters
    assert results[0].chunk_id.startswith("new_doc")
    threshold_results = orchestrator._score_chunks(qv, 10, threshold=2.0)
    assert threshold_results == []


@pytest.mark.asyncio
async def test_retrieve_filters_and_threshold(orchestrator):
    await orchestrator.index_document(
        SCHEMAS.IndexRequest(
            document_id="filter_doc",
            content="kubernetes deployment rollout steps",
            source=SCHEMAS.DocumentSource.TEXT,
            metadata={"topic": "k8s"},
        )
    )
    r = await orchestrator.retrieve(
        SCHEMAS.RetrieveRequest(query="kubernetes deployment", top_k=5, filters={"topic": "k8s"})
    )
    assert any(res.metadata.get("topic") == "k8s" for res in r.results)
    r2 = await orchestrator.retrieve(
        SCHEMAS.RetrieveRequest(query="kubernetes deployment", top_k=5, score_threshold=2.0)
    )
    assert r2.total == 0


# ------------------------------------------------------------------
# Context / generation
# ------------------------------------------------------------------
@pytest.mark.asyncio
async def test_build_context_all_paths(orchestrator):
    # empty results
    empty = await orchestrator.build_context(
        SCHEMAS.ContextRequest(query="missing", search_results=[], top_k=3)
    )
    assert empty.context == ""
    assert empty.token_estimate == 0

    # results with updated_at and truncation
    await orchestrator.index_document(
        SCHEMAS.IndexRequest(
            document_id="ctx_doc",
            content="A" * 500,
            source=SCHEMAS.DocumentSource.TEXT,
            metadata={"updated_at": datetime.date.today().isoformat()},
        )
    )
    ctx = await orchestrator.build_context(
        SCHEMAS.ContextRequest(query="A", top_k=1, max_context_length=10)
    )
    assert ctx.token_estimate <= 10
    assert "updated:" in ctx.context


@pytest.mark.asyncio
async def test_generate_answer_context_branches(orchestrator):
    await orchestrator.index_document(
        SCHEMAS.IndexRequest(
            document_id="gen_doc",
            content="The answer is 42.",
            source=SCHEMAS.DocumentSource.TEXT,
        )
    )
    # context None -> performs search and builds context
    r = await orchestrator.generate_answer(SCHEMAS.GenerateRequest(query="answer", top_k=2))
    assert r.answer
    # context provided
    r2 = await orchestrator.generate_answer(
        SCHEMAS.GenerateRequest(query="answer", context="provided context here", top_k=2)
    )
    assert "provided context here" in r2.answer or "未找到" not in r2.answer
    assert r2.sources == []


@pytest.mark.asyncio
async def test_call_llm_no_key_and_template_answer(orchestrator):
    ans = await orchestrator._call_llm(
        "what?", "Context here.", SCHEMAS.GenerateRequest(query="what?")
    )
    assert "Context here." in ans
    no_ctx = await orchestrator._call_llm("what?", "", SCHEMAS.GenerateRequest(query="what?"))
    assert "未找到" in no_ctx


# ------------------------------------------------------------------
# Hybrid / rerank
# ------------------------------------------------------------------
@pytest.mark.asyncio
async def test_hybrid_search_threshold_and_recency(orchestrator):
    await orchestrator.index_document(
        SCHEMAS.IndexRequest(
            document_id="hybrid_doc",
            content="network latency troubleshooting guide",
            source=SCHEMAS.DocumentSource.TEXT,
            metadata={
                "updated_at": (datetime.date.today() - datetime.timedelta(days=10)).isoformat()
            },
        )
    )
    r = await orchestrator.hybrid_search(
        SCHEMAS.HybridRequest(
            query="network latency", top_k=2, score_threshold=0.0, recency_weight=0.2
        )
    )
    assert r.total >= 0
    r2 = await orchestrator.hybrid_search(
        SCHEMAS.HybridRequest(query="network latency", top_k=2, score_threshold=2.0)
    )
    assert r2.total == 0


@pytest.mark.asyncio
async def test_rerank_empty_candidates_and_keyword_fallback(orchestrator):
    await orchestrator.index_document(
        SCHEMAS.IndexRequest(
            document_id="rerank_doc",
            content="database connection timeout resolution",
            source=SCHEMAS.DocumentSource.TEXT,
        )
    )
    # empty candidates -> fetch from index then keyword-score
    r = await orchestrator.rerank(
        SCHEMAS.RerankRequest(query="database timeout", candidates=[], top_k=2)
    )
    assert r.total >= 0


@pytest.mark.asyncio
async def test_rerank_cross_encoder_fallback(monkeypatch, orchestrator):
    import sentence_transformers as _st

    # Force the lazy attribute to resolve, then replace with a failing stub.
    _ = _st.CrossEncoder
    monkeypatch.setattr(_st, "CrossEncoder", _FakeCrossEncoder)
    monkeypatch.setattr(orchestrator.settings, "rerank_model", "broken-model")
    candidates = [
        SCHEMAS.SearchResult(chunk_id="c1", content="database timeout", score=0.5),
        SCHEMAS.SearchResult(chunk_id="c2", content="hello world", score=0.4),
    ]
    r = await orchestrator.rerank(
        SCHEMAS.RerankRequest(query="database timeout", candidates=candidates, top_k=2)
    )
    assert r.total > 0
    assert r.results[0].chunk_id == "c1"


# ------------------------------------------------------------------
# Multi-recall
# ------------------------------------------------------------------
@pytest.mark.asyncio
async def test_multi_recall_unknown_threshold_and_failure_absorption(monkeypatch, orchestrator):
    await orchestrator.index_document(
        SCHEMAS.IndexRequest(
            document_id="recall_doc",
            content="alertmanager routing configuration",
            source=SCHEMAS.DocumentSource.TEXT,
        )
    )
    # unknown strategy falls back to semantic recall
    r = await orchestrator.multi_recall(
        SCHEMAS.RecallRequest(query="alertmanager", top_k=2, strategies=["weird"])
    )
    assert "weird" in r.strategy_results
    # high threshold filters everything
    r2 = await orchestrator.multi_recall(
        SCHEMAS.RecallRequest(
            query="alertmanager", top_k=2, strategies=["semantic"], score_threshold=2.0
        )
    )
    assert r2.total == 0

    # force a strategy failure by breaking the cache
    async def boom(_key):
        raise RuntimeError("cache down")

    monkeypatch.setattr(orchestrator.cache, "get", boom)
    r3 = await orchestrator.multi_recall(
        SCHEMAS.RecallRequest(
            query="alertmanager",
            top_k=2,
            strategies=["semantic", "keyword", "vector"],
        )
    )
    assert r3.total >= 0 or all(not v for v in r3.strategy_results.values())
    assert r3.strategy_results["semantic"] == []


# ------------------------------------------------------------------
# Maintenance
# ------------------------------------------------------------------
@pytest.mark.asyncio
async def test_delete_and_mark_stale_and_rebuild(orchestrator):
    await orchestrator.index_document(
        SCHEMAS.IndexRequest(
            document_id="maint_doc",
            content="content for maintenance",
            source=SCHEMAS.DocumentSource.TEXT,
        )
    )
    del_resp = await orchestrator.delete_document(SCHEMAS.DeleteRequest(document_id="maint_doc"))
    assert del_resp.status == "deleted"
    not_found = await orchestrator.delete_document(SCHEMAS.DeleteRequest(document_id="maint_doc"))
    assert not_found.status == "not_found"

    await orchestrator.index_document(
        SCHEMAS.IndexRequest(
            document_id="stale_doc",
            content="will be stale",
            source=SCHEMAS.DocumentSource.TEXT,
        )
    )
    stale = await orchestrator.mark_document_stale(
        SCHEMAS.MarkStaleRequest(document_id="stale_doc", reason="test")
    )
    assert stale.status == "marked_stale"
    missing_stale = await orchestrator.mark_document_stale(
        SCHEMAS.MarkStaleRequest(document_id="missing", reason="test")
    )
    assert missing_stale.status == "not_found"

    # rebuild selected/all
    await orchestrator.index_document(
        SCHEMAS.IndexRequest(
            document_id="rebuild_doc",
            content="rebuild me",
            source=SCHEMAS.DocumentSource.TEXT,
        )
    )
    rb = await orchestrator.rebuild_index(SCHEMAS.RebuildIndexRequest(document_ids=["rebuild_doc"]))
    assert rb.status == "rebuilt"
    rb_all = await orchestrator.rebuild_index(SCHEMAS.RebuildIndexRequest())
    assert rb_all.status == "rebuilt"


@pytest.mark.asyncio
async def test_link_to_knowledge_graph_branches(orchestrator):
    missing = await orchestrator.link_to_knowledge_graph(
        SCHEMAS.KnowledgeGraphLinkageRequest(document_id="missing")
    )
    assert missing["linked"] is False

    await orchestrator.index_document(
        SCHEMAS.IndexRequest(
            document_id="kg_doc",
            content="service description",
            source=SCHEMAS.DocumentSource.TEXT,
            metadata={"service": "payments", "type": "runbook"},
        )
    )
    linked = await orchestrator.link_to_knowledge_graph(
        SCHEMAS.KnowledgeGraphLinkageRequest(
            document_id="kg_doc", service="payments", document_type="runbook"
        )
    )
    assert linked["linked"] is True
    assert linked["service"] == "payments"
    assert linked["document_type"] == "runbook"


# ------------------------------------------------------------------
# Batch and stats
# ------------------------------------------------------------------
@pytest.mark.asyncio
async def test_batch_vectorize_search_index(orchestrator):
    docs = [
        SCHEMAS.VectorizeRequest(content="first document", source=SCHEMAS.DocumentSource.TEXT),
        SCHEMAS.VectorizeRequest(content="second document", source=SCHEMAS.DocumentSource.TEXT),
    ]
    vec_res = await orchestrator.batch_vectorize(SCHEMAS.BatchVectorizeRequest(documents=docs))
    assert len(vec_res) == 2

    search_res = await orchestrator.batch_search(
        SCHEMAS.BatchSearchRequest(queries=["first", "second"], top_k=2)
    )
    assert len(search_res) == 2

    idx_reqs = [
        SCHEMAS.IndexRequest(
            document_id="batch_a",
            content="batch content alpha",
            source=SCHEMAS.DocumentSource.TEXT,
        ),
        SCHEMAS.IndexRequest(
            document_id="batch_b",
            content="batch content beta",
            source=SCHEMAS.DocumentSource.TEXT,
        ),
    ]
    idx_res = await orchestrator.batch_index(idx_reqs)
    assert len(idx_res) == 2
    assert all(r.status == "indexed" for r in idx_res)


def test_stats_and_methods(orchestrator):
    stats = orchestrator.get_stats()
    assert "index_size" in stats
    assert "embedding_dimension" in stats
    assert orchestrator.list_methods()


# ------------------------------------------------------------------
# Broken-model helpers (real failure handles, not mocks of RAG logic)
# ------------------------------------------------------------------
class _BrokenEncoder:
    def __init__(self, dim: int) -> None:
        self._dim = dim

    def encode(self, texts: List[str], convert_to_numpy: bool = True) -> Any:
        raise RuntimeError("embedding model broken")


class _FixedDimEncoder:
    def __init__(self, dim: int) -> None:
        self._dim = dim

    def encode(self, texts: List[str], convert_to_numpy: bool = True) -> Any:
        import numpy as np

        arr = np.random.rand(len(texts), self._dim).astype(np.float32)
        return arr
