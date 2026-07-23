# -*- coding: utf-8 -*-
"""Core tests for the vector retrieval microservice."""

from __future__ import annotations

import pytest

from services.vector_retrieval_service.grpc.client import (
    VectorRetrievalServiceRPCClient,
)
from services.vector_retrieval_service.grpc.server import (
    VectorRetrievalServiceRPCServer,
)
from services.vector_retrieval_service.metrics import MetricsCollector
from services.vector_retrieval_service.schemas import (
    ClusterRequest,
    HybridSearchRequest,
    IndexRequest,
    MultiVectorSearchRequest,
    SimilarityMetric,
    VectorBatchStoreRequest,
    VectorSearchRequest,
    VectorStoreRequest,
)
from services.vector_retrieval_service.service import VectorRetrievalService


@pytest.fixture
async def service():
    svc = VectorRetrievalService()
    yield svc


@pytest.mark.asyncio
async def test_create_index(service: VectorRetrievalService):
    req = IndexRequest(collection="test", dimension=4, metric=SimilarityMetric.COSINE)
    resp = await service.create_index(req)
    assert resp.collection == "test"
    assert resp.dimension == 4


@pytest.mark.asyncio
async def test_store_and_search(service: VectorRetrievalService):
    await service.create_index(
        IndexRequest(collection="c1", dimension=3, metric=SimilarityMetric.COSINE)
    )
    await service.store(
        VectorStoreRequest(
            collection="c1", id="a", vector=[1.0, 0.0, 0.0], payload={"text": "apple"}
        )
    )
    await service.store(
        VectorStoreRequest(
            collection="c1", id="b", vector=[0.0, 1.0, 0.0], payload={"text": "banana"}
        )
    )
    result = await service.search(
        VectorSearchRequest(collection="c1", query_vector=[1.0, 0.0, 0.0], top_k=1)
    )
    assert result.total == 2
    assert result.results[0].id == "a"


@pytest.mark.asyncio
async def test_store_batch(service: VectorRetrievalService):
    req = VectorBatchStoreRequest(
        collection="c2",
        vectors=[
            VectorStoreRequest(id="1", vector=[1.0, 0.0], payload={}),
            VectorStoreRequest(id="2", vector=[0.0, 1.0], payload={}),
        ],
    )
    resp = await service.store_batch(req)
    assert resp["stored_count"] == 2


@pytest.mark.asyncio
async def test_exact_and_ann(service: VectorRetrievalService):
    await service.create_index(
        IndexRequest(collection="c3", dimension=2, metric=SimilarityMetric.DOT)
    )
    await service.store(VectorStoreRequest(collection="c3", id="x", vector=[1.0, 1.0], payload={}))
    exact = await service.exact_search(
        VectorSearchRequest(collection="c3", query_vector=[1.0, 1.0], top_k=1)
    )
    ann = await service.ann_search(
        VectorSearchRequest(collection="c3", query_vector=[1.0, 1.0], top_k=1)
    )
    assert exact.results[0].id == ann.results[0].id == "x"


@pytest.mark.asyncio
async def test_hybrid_search(service: VectorRetrievalService):
    await service.create_index(
        IndexRequest(collection="c4", dimension=2, metric=SimilarityMetric.COSINE)
    )
    await service.store(
        VectorStoreRequest(
            collection="c4", id="h1", vector=[1.0, 0.0], payload={"text": "red apple"}
        )
    )
    await service.store(
        VectorStoreRequest(
            collection="c4", id="h2", vector=[0.0, 1.0], payload={"text": "green banana"}
        )
    )
    result = await service.hybrid_search(
        HybridSearchRequest(
            collection="c4",
            query_vector=[1.0, 0.0],
            query_text="apple",
            top_k=2,
            alpha=0.9,
        )
    )
    assert result.total == 2
    assert result.results[0].id == "h1"


@pytest.mark.asyncio
async def test_multi_vector_search(service: VectorRetrievalService):
    await service.create_index(
        IndexRequest(collection="c5", dimension=2, metric=SimilarityMetric.DOT)
    )
    await service.store(VectorStoreRequest(collection="c5", id="m1", vector=[1.0, 0.0], payload={}))
    await service.store(VectorStoreRequest(collection="c5", id="m2", vector=[0.0, 1.0], payload={}))
    result = await service.multi_vector_search(
        MultiVectorSearchRequest(
            collection="c5",
            query_vectors=[[1.0, 0.0], [0.5, 0.5]],
            weights=[0.8, 0.2],
            top_k=1,
        )
    )
    assert len(result.results) == 1


@pytest.mark.asyncio
async def test_cluster_vectors(service: VectorRetrievalService):
    await service.create_index(
        IndexRequest(collection="c6", dimension=2, metric=SimilarityMetric.EUCLIDEAN)
    )
    await service.store(VectorStoreRequest(collection="c6", id="p1", vector=[0.0, 0.0], payload={}))
    await service.store(VectorStoreRequest(collection="c6", id="p2", vector=[0.1, 0.1], payload={}))
    await service.store(
        VectorStoreRequest(collection="c6", id="p3", vector=[10.0, 10.0], payload={})
    )
    result = await service.cluster_vectors(ClusterRequest(collection="c6", n_clusters=2))
    assert result.n_clusters == 2
    assert len(result.labels) == 3
    assert len(result.centroids) == 2


@pytest.mark.asyncio
async def test_get_stats(service: VectorRetrievalService):
    service.get_stats()
    assert "total_requests" in service.get_stats()


@pytest.mark.asyncio
async def test_list_methods(service: VectorRetrievalService):
    assert "hybrid_search" in service.list_methods()
    assert "cluster_vectors" in service.list_methods()


@pytest.mark.asyncio
async def test_rpc_server():
    server = VectorRetrievalServiceRPCServer()
    server.register("echo", lambda x: x)
    assert "echo" in server.list_methods()
    assert await server.call("echo", x="hi") == "hi"


@pytest.mark.asyncio
async def test_rpc_client():
    from unittest.mock import AsyncMock, MagicMock, patch

    response = MagicMock()
    response.json.return_value = {"ok": True}
    response.raise_for_status.return_value = None
    client_mock = MagicMock()
    client_mock.__aenter__ = AsyncMock(return_value=client_mock)
    client_mock.__aexit__ = AsyncMock(return_value=None)
    client_mock.post = AsyncMock(return_value=response)

    with patch(
        "services.vector_retrieval_service.grpc.client.httpx.AsyncClient", return_value=client_mock
    ):
        client = VectorRetrievalServiceRPCClient(base_url="http://test")
        result = await client.call("stats")
    assert result["ok"] is True


def test_metrics_collector():
    metrics = MetricsCollector("vector_metrics_test")
    metrics.inc_request("search")
    metrics.inc_cache_hit()
    metrics.inc_cache_miss()
    metrics.inc_failure("search", "err")
    metrics.observe_batch_size("store", 3)
    with metrics.time_operation("op"):
        pass
    assert metrics.request_count == 1


@pytest.mark.asyncio
async def test_cache_manager():
    from services.vector_retrieval_service.cache import CacheManager

    metrics = MetricsCollector("vector_cache_test")
    cache = CacheManager(metrics=metrics)
    assert await cache.get("missing") is None
    assert metrics.cache_misses_count == 1
    await cache.set("k", {"v": 1}, ttl=60)
    assert await cache.get("k") == {"v": 1}
    assert metrics.cache_hits_count == 1
    await cache.delete("k")
    assert await cache.get("k") is None
    await cache.set("a", 1)
    await cache.clear()
    assert await cache.get("a") is None


@pytest.mark.asyncio
async def test_retry_engine():
    from unittest.mock import AsyncMock

    from services.vector_retrieval_service.retry import RetryEngine

    engine = RetryEngine("exponential_fast")
    fn = AsyncMock(side_effect=[Exception("retryable"), "ok"])
    result = await engine.execute(fn, operation="test")
    assert result == "ok"
    assert fn.await_count == 2


@pytest.mark.asyncio
async def test_filter_and_empty_search(service: VectorRetrievalService):
    await service.create_index(
        IndexRequest(collection="filter", dimension=2, metric=SimilarityMetric.COSINE)
    )
    await service.store(
        VectorStoreRequest(collection="filter", id="f1", vector=[1.0, 0.0], payload={"tag": "a"})
    )
    result = await service.search(
        VectorSearchRequest(
            collection="filter", query_vector=[1.0, 0.0], top_k=5, filters={"tag": "b"}
        )
    )
    assert result.total == 0


@pytest.mark.asyncio
async def test_store_dimension_update(service: VectorRetrievalService):
    await service.create_index(
        IndexRequest(collection="dim", dimension=2, metric=SimilarityMetric.COSINE)
    )
    await service.store(
        VectorStoreRequest(collection="dim", id="d1", vector=[1.0, 0.0, 0.0], payload={})
    )
    assert service.collections["dim"].dimension == 3


@pytest.mark.asyncio
async def test_cluster_small(service: VectorRetrievalService):
    await service.create_index(
        IndexRequest(collection="small", dimension=2, metric=SimilarityMetric.COSINE)
    )
    await service.store(
        VectorStoreRequest(collection="small", id="s1", vector=[1.0, 0.0], payload={})
    )
    result = await service.cluster_vectors(ClusterRequest(collection="small", n_clusters=3))
    assert result.n_clusters == 3
    assert len(result.labels) == 1
