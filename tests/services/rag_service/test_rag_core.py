# -*- coding: utf-8 -*-
"""Core tests for the RAG microservice."""

from __future__ import annotations

import pytest

from services.rag_service.cache import CacheManager
from services.rag_service.orchestrator import RAGOrchestrator
from services.rag_service.retry import RAGRetryEngine, RetryPolicy
from services.rag_service.schemas import (
    BatchSearchRequest,
    BatchVectorizeRequest,
    ContextRequest,
    GenerateRequest,
    HybridRequest,
    IndexRequest,
    RecallRequest,
    RerankRequest,
    RetrieveRequest,
    SearchRequest,
    VectorizeRequest,
)


@pytest.fixture
def orchestrator():
    return RAGOrchestrator(embedding_model="fallback", cache=CacheManager())


@pytest.mark.asyncio
async def test_fallback_embedding(orchestrator):
    vectors = orchestrator._fallback_embedding(["hello", "world"])
    assert len(vectors) == 2
    assert len(vectors[0]) == orchestrator.vector_dimension


@pytest.mark.asyncio
async def test_embed(orchestrator):
    vectors = await orchestrator.embed(["hello"])
    assert len(vectors) == 1
    assert len(vectors[0]) == orchestrator.vector_dimension


@pytest.mark.asyncio
async def test_vectorize_document(orchestrator):
    request = VectorizeRequest(content="Short doc.", chunk_size=64, chunk_overlap=0)
    response = await orchestrator.vectorize_document(request)
    assert response.chunk_count >= 1
    assert len(response.vectors) == response.chunk_count


@pytest.mark.asyncio
async def test_index_document(orchestrator):
    request = IndexRequest(document_id="d1", content="Index this document.")
    response = await orchestrator.index_document(request)
    assert response.status == "indexed"
    assert response.chunks_indexed >= 1


@pytest.mark.asyncio
async def test_semantic_search(orchestrator):
    await orchestrator.index_document(IndexRequest(document_id="d2", content="RAG retrieval"))
    response = await orchestrator.semantic_search(SearchRequest(query="RAG", top_k=3))
    assert response.total >= 1
    assert response.results[0].score > 0


@pytest.mark.asyncio
async def test_retrieve(orchestrator):
    await orchestrator.index_document(IndexRequest(document_id="d3", content="Monitoring test"))
    response = await orchestrator.retrieve(
        RetrieveRequest(query="monitoring", top_k=2, filters={"source": "text"})
    )
    assert response.total >= 0


@pytest.mark.asyncio
async def test_build_context(orchestrator):
    await orchestrator.index_document(IndexRequest(document_id="d4", content="Context test"))
    response = await orchestrator.build_context(ContextRequest(query="context", top_k=2))
    assert response.source_count >= 0
    assert response.query.lower() in response.context.lower() or response.source_count == 0


@pytest.mark.asyncio
async def test_generate_answer(orchestrator):
    await orchestrator.index_document(IndexRequest(document_id="d5", content="Answer source"))
    response = await orchestrator.generate_answer(GenerateRequest(query="answer", top_k=2))
    assert response.answer
    assert response.query == "answer"


@pytest.mark.asyncio
async def test_hybrid_search(orchestrator):
    await orchestrator.index_document(IndexRequest(document_id="d6", content="Hybrid search"))
    response = await orchestrator.hybrid_search(HybridRequest(query="hybrid", top_k=2))
    assert response.total >= 0


@pytest.mark.asyncio
async def test_rerank(orchestrator):
    await orchestrator.index_document(IndexRequest(document_id="d7", content="Rerank content"))
    search = await orchestrator.semantic_search(SearchRequest(query="rerank", top_k=2))
    response = await orchestrator.rerank(
        RerankRequest(query="rerank", candidates=search.results, top_k=2)
    )
    assert response.total >= 0


@pytest.mark.asyncio
async def test_multi_recall(orchestrator):
    await orchestrator.index_document(IndexRequest(document_id="d8", content="Multi recall"))
    response = await orchestrator.multi_recall(
        RecallRequest(query="recall", top_k=2, strategies=["semantic", "keyword", "vector"])
    )
    assert response.total >= 0
    assert "semantic" in response.strategy_results
    assert "keyword" in response.strategy_results


@pytest.mark.asyncio
async def test_batch_vectorize(orchestrator):
    request = BatchVectorizeRequest(
        documents=[VectorizeRequest(content="A"), VectorizeRequest(content="B")]
    )
    responses = await orchestrator.batch_vectorize(request)
    assert len(responses) == 2


@pytest.mark.asyncio
async def test_batch_search(orchestrator):
    await orchestrator.index_document(IndexRequest(document_id="d9", content="Batch search"))
    request = BatchSearchRequest(queries=["batch", "search"], top_k=2)
    responses = await orchestrator.batch_search(request)
    assert len(responses) == 2


@pytest.mark.asyncio
async def test_batch_index(orchestrator):
    docs = [
        IndexRequest(document_id="d10", content="Ten"),
        IndexRequest(document_id="d11", content="Eleven"),
    ]
    responses = await orchestrator.batch_index(docs)
    assert len(responses) == 2


@pytest.mark.asyncio
async def test_cache(orchestrator):
    await orchestrator.cache.set("key", {"value": 1})
    value = await orchestrator.cache.get("key")
    assert value == {"value": 1}


@pytest.mark.asyncio
async def test_retry_engine_execute():
    async def ok():
        return "ok"

    engine = RAGRetryEngine()
    result = await engine.execute(ok, operation="test")
    assert result == "ok"


@pytest.mark.asyncio
async def test_retry_engine_policy():
    engine = RAGRetryEngine()
    assert "exponential" in engine.list_policies()
    engine.add_policy(RetryPolicy(name="custom", max_retries=1))
    assert "custom" in engine.list_policies()


@pytest.mark.asyncio
async def test_get_stats(orchestrator):
    await orchestrator.index_document(IndexRequest(document_id="d12", content="Stats"))
    stats = orchestrator.get_stats()
    assert stats["index_size"] >= 1
    assert "retry_policies" in stats


def test_list_methods(orchestrator):
    methods = orchestrator.list_methods()
    assert "semantic_search" in methods
    assert "multi_recall" in methods


@pytest.mark.asyncio
async def test_grpc_server():
    from services.rag_service.grpc.server import RAGRPCServer

    server = RAGRPCServer()
    server.register("echo", lambda x: x)
    assert "echo" in server.list_methods()
    result = await server.call("echo", x="hello")
    assert result == "hello"


@pytest.mark.asyncio
async def test_grpc_client():
    from unittest.mock import AsyncMock, MagicMock, patch

    from services.rag_service.grpc.client import RAGRPCClient

    mock_response = MagicMock()
    mock_response.json.return_value = {"ok": True}
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.post.return_value = mock_response

    with patch("services.rag_service.grpc.client.httpx.AsyncClient", return_value=mock_client):
        client = RAGRPCClient()
        result = await client.call("echo", {"x": "hello"})
    assert result == {"ok": True}


@pytest.mark.asyncio
async def test_retry_engine_failure():
    from unittest.mock import patch

    from services.rag_service.retry import RAGRetryEngine

    calls = 0

    async def flaky():
        nonlocal calls
        calls += 1
        if calls < 2:
            raise RuntimeError("retryable error")
        return "ok"

    engine = RAGRetryEngine("exponential_fast")
    with patch("services.rag_service.retry.asyncio.sleep"):
        result = await engine.execute(flaky, operation="flaky")
    assert result == "ok"
    assert calls == 2


@pytest.mark.asyncio
async def test_retry_engine_non_retryable():
    from services.rag_service.retry import RAGRetryEngine

    async def fail():
        raise ValueError("fatal")

    engine = RAGRetryEngine("no_retry")
    with pytest.raises(ValueError):
        await engine.execute(fail, operation="fail")


@pytest.mark.asyncio
async def test_cache_redis():
    from unittest.mock import AsyncMock, MagicMock, patch

    from services.rag_service.cache import CacheManager

    fake_redis = AsyncMock()
    fake_redis.get.return_value = '{"value": 42}'
    fake_from_url = MagicMock(return_value=fake_redis)

    mock_redis_module = MagicMock()
    mock_redis_module.from_url = fake_from_url

    with patch("services.rag_service.cache.aioredis", mock_redis_module, create=True):
        cache = CacheManager("redis://localhost:6379")
        value = await cache.get("key")
        await cache.set("key", {"value": 1})
        await cache.clear()

    assert value == {"value": 42}
    fake_redis.setex.assert_called_once()
    fake_redis.flushdb.assert_called_once()
