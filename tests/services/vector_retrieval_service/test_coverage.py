# -*- coding: utf-8 -*-
"""补充 vector_retrieval_service 核心分支覆盖率测试。"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any, Dict, List
from unittest import mock

import pytest

import services.vector_retrieval_service.cache as cache_module
import services.vector_retrieval_service.retry as retry_module
import services.vector_retrieval_service.service as service_module
from services.vector_retrieval_service.metrics import MetricsCollector
from services.vector_retrieval_service.schemas import (
    ClusterRequest,
    HybridSearchRequest,
    IndexRequest,
    MultiVectorSearchRequest,
    SimilarityMetric,
    VectorSearchRequest,
    VectorStoreRequest,
)


class _FakeRedis:
    def __init__(self, fail: bool = False) -> None:
        self._data: dict[str, str] = {}
        self._fail = fail

    async def get(self, key: str) -> str | None:
        if self._fail:
            raise ConnectionError("redis down")
        return self._data.get(key)

    async def setex(self, key: str, ttl: int, value: str) -> None:
        if self._fail:
            raise ConnectionError("redis down")
        self._data[key] = value

    async def delete(self, key: str) -> None:
        if self._fail:
            raise ConnectionError("redis down")
        self._data.pop(key, None)

    async def flushdb(self) -> None:
        if self._fail:
            raise ConnectionError("redis down")
        self._data.clear()


class _FakeAioredis:
    @staticmethod
    def from_url(url: str, *, decode_responses: bool = True) -> _FakeRedis:
        return _FakeRedis()


class _FakeQdrant:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.recreate_collection = mock.MagicMock()
        self.upsert = mock.MagicMock()


@dataclass
class _FakeVectorParams:
    size: int
    distance: str


@dataclass
class _FakePointStruct:
    id: str
    vector: List[float]
    payload: Dict[str, Any]


class _FakeDistance:
    COSINE = "Cosine"
    DOT = "Dot"
    EUCLID = "Euclid"


class _FakeQdrantFail:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        pass

    def recreate_collection(self, **kwargs: Any) -> None:
        raise ConnectionError("qdrant down")

    def upsert(self, **kwargs: Any) -> None:
        raise ConnectionError("qdrant down")


class _FakeQdrantInitFail:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        raise ConnectionError("init fail")


@pytest.mark.asyncio
async def test_cache_manager_redis_paths() -> None:
    metrics = MetricsCollector(f"vec-redis-{uuid.uuid4().hex[:6]}")
    with mock.patch.object(cache_module, "aioredis", _FakeAioredis()):
        cache = cache_module.CacheManager(redis_url="redis://fake", metrics=metrics)
        assert cache._redis is not None
        assert cache._key("a", 1) == "a:1"

        await cache.set("k", {"x": 1})
        assert await cache.get("k") == {"x": 1}

        await cache.delete("k")
        assert await cache.get("k") is None

        await cache.set("k2", {"y": 2})
        await cache.clear()
        assert await cache.get("k2") is None

        cache._memory["k3"] = {"z": 3}
        assert await cache.get("k3") == {"z": 3}


@pytest.mark.asyncio
async def test_cache_manager_redis_failures() -> None:
    metrics = MetricsCollector(f"vec-fail-{uuid.uuid4().hex[:6]}")
    with mock.patch.object(cache_module, "aioredis", _FakeAioredis()):
        cache = cache_module.CacheManager(redis_url="redis://fake", metrics=metrics)
        cache._redis._fail = True

        await cache.set("k", {"x": 1})
        assert await cache.get("k") == {"x": 1}

        await cache.delete("k")
        assert await cache.get("k") is None

        await cache.set("k2", {"y": 2})
        await cache.clear()
        assert await cache.get("k2") is None


@pytest.mark.asyncio
async def test_retry_engine_coverage() -> None:
    metrics = MetricsCollector(f"vec-retry-{uuid.uuid4().hex[:6]}")
    engine = retry_module.RetryEngine("exponential_fast", metrics=metrics)

    custom = retry_module.RetryPolicy(name="custom", max_retries=1)
    engine.add_policy(custom)
    assert "custom" in engine.list_policies()

    fn = mock.AsyncMock(side_effect=Exception("fatal error"))
    with pytest.raises(Exception, match="fatal error"):
        await engine.execute(fn, operation="op")
    assert fn.await_count == 1

    fn = mock.AsyncMock(side_effect=[Exception("retryable"), "ok"])
    with mock.patch("asyncio.sleep", new_callable=mock.AsyncMock):
        result = await engine.execute(fn, policy_name="exponential_fast", operation="op")
    assert result == "ok"
    assert fn.await_count == 2

    fn = mock.AsyncMock(side_effect=Exception("retryable"))
    with pytest.raises(Exception, match="retryable"):
        await engine.execute(fn, policy_name="no_retry")
    assert fn.await_count == 1

    engine.add_policy(
        retry_module.RetryPolicy(
            name="all", max_retries=1, base_delay_seconds=0, retryable_errors=[]
        )
    )
    fn = mock.AsyncMock(side_effect=[Exception("fatal"), "ok"])
    with mock.patch("asyncio.sleep", new_callable=mock.AsyncMock):
        result = await engine.execute(fn, policy_name="all", operation="op")
    assert result == "ok"
    assert fn.await_count == 2

    engine.add_policy(
        retry_module.RetryPolicy(
            name="jitter",
            max_retries=1,
            base_delay_seconds=1,
            max_delay_seconds=60,
            exponential_base=2.0,
        )
    )
    fn = mock.AsyncMock(side_effect=[Exception("retryable"), "ok"])
    sleep_mock = mock.AsyncMock()
    with mock.patch("asyncio.sleep", new=sleep_mock):
        with mock.patch.object(retry_module, "secrets") as mock_secrets:
            mock_secrets.SystemRandom.return_value.random.return_value = 0.5
            result = await engine.execute(fn, policy_name="jitter", operation="op")
    assert result == "ok"
    assert fn.await_count == 2
    sleep_mock.assert_awaited_once()
    args = sleep_mock.call_args[0]
    assert 0.5 <= args[0] <= 60.0


@pytest.mark.asyncio
async def test_vector_service_numpy_fallback() -> None:
    metrics = MetricsCollector(f"vec-np-{uuid.uuid4().hex[:6]}")
    with mock.patch.multiple(service_module, np=None, QdrantClient=None):
        service = service_module.VectorRetrievalService(metrics=metrics)

        await service.create_index(
            IndexRequest(collection="test", dimension=3, metric=SimilarityMetric.DOT)
        )

        await service.store(
            VectorStoreRequest(
                id="a", collection="test", vector=[1.0, 0.0, 0.0], payload={"tag": "ok"}
            )
        )
        await service.store(
            VectorStoreRequest(
                id="b", collection="test", vector=[0.0, 1.0, 0.0], payload={"tag": "bad"}
            )
        )

        res = await service.search(
            VectorSearchRequest(
                collection="test",
                query_vector=[1.0, 0.0, 0.0],
                top_k=2,
                metric=SimilarityMetric.DOT,
                filters={"tag": "ok"},
            )
        )
        assert len(res.results) == 1
        assert res.results[0].id == "a"

        res = await service.exact_search(
            VectorSearchRequest(
                collection="test",
                query_vector=[1.0, 0.0, 0.0],
                top_k=2,
                metric=SimilarityMetric.EUCLIDEAN,
            )
        )
        assert res.results[0].id == "a"

        res = await service.ann_search(
            VectorSearchRequest(
                collection="test",
                query_vector=[0.0, 0.0, 0.0],
                top_k=2,
                metric=SimilarityMetric.COSINE,
            )
        )
        assert len(res.results) == 2

        res = await service.hybrid_search(
            HybridSearchRequest(
                collection="test",
                query_vector=[1.0, 0.0, 0.0],
                query_text="ok",
                top_k=2,
                metric=SimilarityMetric.DOT,
                alpha=0.5,
            )
        )
        assert res.results[0].id == "a"

        res = await service.multi_vector_search(
            MultiVectorSearchRequest(
                collection="test",
                query_vectors=[[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]],
                weights=[0.5, 0.5],
                top_k=2,
                metric=SimilarityMetric.DOT,
            )
        )
        assert len(res.results) == 2

        res = await service.cluster_vectors(ClusterRequest(collection="test", n_clusters=2))
        assert res.n_clusters == 2
        assert len(res.labels) == 2

        stats = await service.call("get_stats")
        assert "total_requests" in stats

        with pytest.raises(ValueError, match="Unknown method"):
            await service.call("unknown")


@pytest.mark.asyncio
async def test_vector_service_qdrant_success() -> None:
    metrics = MetricsCollector(f"vec-qdrant-ok-{uuid.uuid4().hex[:6]}")
    with mock.patch.multiple(
        service_module,
        QdrantClient=_FakeQdrant,
        Distance=_FakeDistance,
        VectorParams=_FakeVectorParams,
        PointStruct=_FakePointStruct,
    ):
        service = service_module.VectorRetrievalService(metrics=metrics)
        assert service._qdrant is not None

        await service.create_index(
            IndexRequest(collection="qdrant", dimension=3, metric=SimilarityMetric.DOT)
        )
        assert service._qdrant.recreate_collection.call_count == 1

        await service.store(VectorStoreRequest(id="x", collection="qdrant", vector=[1.0, 0.0, 0.0]))
        assert service._qdrant.upsert.call_count == 1


@pytest.mark.asyncio
async def test_vector_service_qdrant_failure() -> None:
    metrics = MetricsCollector(f"vec-qdrant-fail-{uuid.uuid4().hex[:6]}")
    with mock.patch.multiple(
        service_module,
        QdrantClient=_FakeQdrantFail,
        Distance=_FakeDistance,
        VectorParams=_FakeVectorParams,
        PointStruct=_FakePointStruct,
    ):
        service = service_module.VectorRetrievalService(metrics=metrics)
        assert service._qdrant is not None

        await service.create_index(
            IndexRequest(collection="qfail", dimension=3, metric=SimilarityMetric.COSINE)
        )
        await service.store(VectorStoreRequest(id="y", collection="qfail", vector=[1.0, 0.0, 0.0]))


@pytest.mark.asyncio
async def test_vector_service_qdrant_init_failure() -> None:
    metrics = MetricsCollector(f"vec-qdrant-init-{uuid.uuid4().hex[:6]}")
    with mock.patch.object(service_module, "QdrantClient", _FakeQdrantInitFail):
        service = service_module.VectorRetrievalService(metrics=metrics)
        assert service._qdrant is None
