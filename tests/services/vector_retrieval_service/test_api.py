# -*- coding: utf-8 -*-
"""API tests for the vector retrieval microservice."""

from __future__ import annotations

import httpx
import pytest

from services.vector_retrieval_service import main_app as main_module
from services.vector_retrieval_service.main_app import app
from services.vector_retrieval_service.metrics import MetricsCollector
from services.vector_retrieval_service.service import VectorRetrievalService


@pytest.fixture(autouse=True)
async def reset_service():
    from services.vector_retrieval_service import config

    config.settings.redis_url = ""
    config.settings.qdrant_url = ""
    metrics = MetricsCollector("vector_api_test")
    service = VectorRetrievalService(
        redis_url="",
        qdrant_url="",
        metrics=metrics,
    )
    main_module._service = service
    yield


@pytest.mark.asyncio
async def test_health():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_metrics():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/metrics")
    assert response.status_code == 200
    assert "vector" in response.text


@pytest.mark.asyncio
async def test_index_and_store():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        index_resp = await client.post(
            "/vectors/index",
            json={"collection": "api", "dimension": 2, "metric": "cosine"},
        )
        assert index_resp.status_code == 200
        store_resp = await client.post(
            "/vectors/store",
            json={"collection": "api", "id": "v1", "vector": [1.0, 0.0], "payload": {"tag": "a"}},
        )
    assert store_resp.status_code == 200
    assert store_resp.json()["stored"] is True


@pytest.mark.asyncio
async def test_search():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        await client.post(
            "/vectors/store",
            json={"collection": "search", "id": "s1", "vector": [1.0, 0.0], "payload": {}},
        )
        await client.post(
            "/vectors/store",
            json={"collection": "search", "id": "s2", "vector": [0.0, 1.0], "payload": {}},
        )
        response = await client.post(
            "/vectors/search",
            json={"collection": "search", "query_vector": [1.0, 0.0], "top_k": 1},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert data["results"][0]["id"] == "s1"


@pytest.mark.asyncio
async def test_hybrid():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        await client.post(
            "/vectors/store",
            json={
                "collection": "hybrid",
                "id": "h1",
                "vector": [1.0, 0.0],
                "payload": {"text": "red apple"},
            },
        )
        response = await client.post(
            "/vectors/hybrid",
            json={
                "collection": "hybrid",
                "query_vector": [1.0, 0.0],
                "query_text": "apple",
                "top_k": 1,
                "alpha": 0.9,
            },
        )
    assert response.status_code == 200
    assert response.json()["results"][0]["id"] == "h1"


@pytest.mark.asyncio
async def test_multi():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        await client.post(
            "/vectors/store",
            json={"collection": "multi", "id": "m1", "vector": [1.0, 0.0], "payload": {}},
        )
        response = await client.post(
            "/vectors/multi",
            json={
                "collection": "multi",
                "query_vectors": [[1.0, 0.0], [0.5, 0.5]],
                "weights": [0.8, 0.2],
                "top_k": 1,
            },
        )
    assert response.status_code == 200
    assert len(response.json()["results"]) == 1


@pytest.mark.asyncio
async def test_cluster():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        for i, vec in enumerate([[0.0, 0.0], [0.1, 0.1], [10.0, 10.0]]):
            await client.post(
                "/vectors/store",
                json={"collection": "cluster", "id": f"c{i}", "vector": vec, "payload": {}},
            )
        response = await client.post(
            "/vectors/cluster",
            json={"collection": "cluster", "n_clusters": 2},
        )
    assert response.status_code == 200
    data = response.json()
    assert len(data["labels"]) == 3
    assert len(data["centroids"]) == 2


@pytest.mark.asyncio
async def test_stats_and_rpc():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        stats = await client.get("/stats")
        assert stats.status_code == 200
        rpc_list = await client.post("/rpc/list_methods", json={})
        assert rpc_list.status_code == 200
        assert "hybrid_search" in rpc_list.json()


@pytest.mark.asyncio
async def test_ann_and_exact():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        await client.post(
            "/vectors/index",
            json={"collection": "ann", "dimension": 2, "metric": "cosine"},
        )
        for i, vec in enumerate([[1.0, 0.0], [0.0, 1.0]]):
            await client.post(
                "/vectors/store",
                json={"collection": "ann", "id": f"a{i}", "vector": vec, "payload": {}},
            )
        ann = await client.post(
            "/vectors/ann",
            json={"collection": "ann", "query_vector": [1.0, 0.0], "top_k": 1},
        )
        exact = await client.post(
            "/vectors/exact",
            json={"collection": "ann", "query_vector": [1.0, 0.0], "top_k": 1},
        )
    assert ann.status_code == 200
    assert exact.status_code == 200


@pytest.mark.asyncio
async def test_store_batch():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/vectors/store/batch",
            json={
                "collection": "batch",
                "vectors": [
                    {"id": "b1", "vector": [1.0, 0.0], "payload": {}},
                    {"id": "b2", "vector": [0.0, 1.0], "payload": {}},
                ],
            },
        )
    assert response.status_code == 200
    assert response.json()["stored_count"] == 2


@pytest.mark.asyncio
async def test_rpc_method():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        rpc_resp = await client.post(
            "/rpc/search",
            json={
                "collection": "rpc-search",
                "query_vector": [1.0, 0.0],
                "top_k": 3,
            },
        )
    assert rpc_resp.status_code == 200
    assert "results" in rpc_resp.json()
