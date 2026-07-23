# -*- coding: utf-8 -*-
"""API tests for the RAG microservice."""

from __future__ import annotations

import httpx
import pytest

from services.rag_service.cache import CacheManager
from services.rag_service.main_app import app
from services.rag_service.orchestrator import RAGOrchestrator


@pytest.fixture(autouse=True)
def reset_orchestrator():
    """Reset the RAG orchestrator to a deterministic fallback for tests."""
    from services.rag_service import config, main_app

    config.settings.redis_url = ""
    main_app._orchestrator = RAGOrchestrator(
        embedding_model="fallback",
        cache=CacheManager(),
    )
    yield


@pytest.mark.asyncio
async def test_health():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "rag-service"


@pytest.mark.asyncio
async def test_metrics():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/metrics")
    assert response.status_code == 200
    assert "rag_" in response.text


@pytest.mark.asyncio
async def test_stats():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/stats")
    assert response.status_code == 200
    data = response.json()
    assert "index_size" in data


@pytest.mark.asyncio
async def test_vectorize():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/vectorize",
            json={"content": "The quick brown fox jumps over the lazy dog."},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["chunk_count"] >= 1
    assert data["dimension"] > 0


@pytest.mark.asyncio
async def test_index_and_search():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        await client.post(
            "/index",
            json={
                "document_id": "doc-1",
                "content": "RAG combines retrieval with generation.",
                "metadata": {"source": "test"},
            },
        )
        response = await client.post("/search", json={"query": "RAG retrieval", "top_k": 3})
    data = response.json()
    assert response.status_code == 200
    assert data["total"] >= 1
    assert any("RAG" in r["content"] for r in data["results"])


@pytest.mark.asyncio
async def test_retrieve():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        await client.post(
            "/index",
            json={"document_id": "doc-2", "content": "Monitoring keeps systems reliable."},
        )
        response = await client.post(
            "/retrieve",
            json={"query": "monitoring", "top_k": 2, "filters": {"source": "text"}},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 0


@pytest.mark.asyncio
async def test_context():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        await client.post(
            "/index",
            json={"document_id": "doc-3", "content": "Context is built from search results."},
        )
        response = await client.post("/context", json={"query": "context", "top_k": 2})
    assert response.status_code == 200
    data = response.json()
    assert "context" in data
    assert data["source_count"] >= 0


@pytest.mark.asyncio
async def test_generate():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        await client.post(
            "/index",
            json={"document_id": "doc-4", "content": "The answer is derived from context."},
        )
        response = await client.post("/generate", json={"query": "answer", "top_k": 2})
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data


@pytest.mark.asyncio
async def test_hybrid():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        await client.post(
            "/index",
            json={"document_id": "doc-5", "content": "Hybrid search combines signals."},
        )
        response = await client.post("/hybrid", json={"query": "hybrid search", "top_k": 2})
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 0


@pytest.mark.asyncio
async def test_rerank():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        await client.post(
            "/index",
            json={"document_id": "doc-6", "content": "Reranking improves result quality."},
        )
        search = await client.post("/search", json={"query": "reranking", "top_k": 2})
        candidates = search.json()["results"]
        response = await client.post(
            "/rerank",
            json={"query": "reranking", "candidates": candidates, "top_k": 2},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 0


@pytest.mark.asyncio
async def test_recall():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        await client.post(
            "/index",
            json={"document_id": "doc-7", "content": "Multi-way recall uses several strategies."},
        )
        response = await client.post(
            "/recall",
            json={"query": "multi-way recall", "top_k": 2, "strategies": ["semantic", "keyword"]},
        )
    assert response.status_code == 200
    data = response.json()
    assert "fused_results" in data
    assert "strategy_results" in data


@pytest.mark.asyncio
async def test_batch_vectorize():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/batch/vectorize",
            json={
                "documents": [
                    {"content": "First document."},
                    {"content": "Second document."},
                ]
            },
        )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


@pytest.mark.asyncio
async def test_batch_search():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        await client.post(
            "/index",
            json={"document_id": "doc-8", "content": "Batch search is efficient."},
        )
        response = await client.post(
            "/batch/search",
            json={"queries": ["batch", "efficient"], "top_k": 2},
        )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


@pytest.mark.asyncio
async def test_batch_index():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/batch/index",
            json=[
                {"document_id": "doc-9", "content": "Document nine."},
                {"document_id": "doc-10", "content": "Document ten."},
            ],
        )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


@pytest.mark.asyncio
async def test_rpc_methods():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/rpc/list_methods", json={})
    assert response.status_code == 200
    methods = response.json()
    assert "vectorize_document" in methods


@pytest.mark.asyncio
async def test_rpc_vectorize():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/rpc/vectorize_document",
            json={"content": "RPC vectorization test."},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["chunk_count"] >= 1


@pytest.mark.asyncio
async def test_rpc_unknown():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/rpc/unknown", json={})
    assert response.status_code == 404
