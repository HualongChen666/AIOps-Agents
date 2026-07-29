# -*- coding: utf-8 -*-
"""Core service logic for the vector retrieval microservice."""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional, Tuple, cast

from loguru import logger

from .cache import CacheManager
from .metrics import MetricsCollector
from .retry import RetryEngine
from .schemas import (
    ClusterRequest,
    ClusterResponse,
    HybridSearchRequest,
    IndexRequest,
    IndexResponse,
    MultiVectorSearchRequest,
    SimilarityMetric,
    VectorBatchStoreRequest,
    VectorResult,
    VectorSearchRequest,
    VectorSearchResponse,
    VectorStoreRequest,
)

try:
    import numpy as np
except ImportError:  # pragma: no cover
    np = None  # type: ignore[assignment]

try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, PointStruct, VectorParams
except ImportError:  # pragma: no cover
    QdrantClient = None  # type: ignore[assignment, misc]
    Distance = None  # type: ignore[assignment, misc]
    PointStruct = None  # type: ignore[assignment, misc]
    VectorParams = None  # type: ignore[assignment, misc]


class VectorStoreEntry:
    """In-memory vector store entry."""

    def __init__(self, entry_id: str, vector: List[float], payload: Dict[str, Any]) -> None:
        self.id = entry_id
        self.vector = vector
        self.payload = payload


class VectorCollection:
    """In-memory vector collection with index metadata."""

    def __init__(self, name: str, dimension: int, metric: SimilarityMetric) -> None:
        self.name = name
        self.dimension = dimension
        self.metric = metric
        self.entries: Dict[str, VectorStoreEntry] = {}


class VectorRetrievalService:
    """Vector retrieval service implementing storage, search and clustering."""

    def __init__(
        self,
        redis_url: str = "",
        qdrant_url: str = "",
        metrics: Optional[MetricsCollector] = None,
        retry_engine: Optional[RetryEngine] = None,
        cache: Optional[CacheManager] = None,
    ) -> None:
        self.metrics = metrics or MetricsCollector("vector_retrieval")
        self.retry_engine = retry_engine or RetryEngine("exponential_fast", self.metrics)
        self.cache = cache or CacheManager(redis_url, self.metrics)
        self.collections: Dict[str, VectorCollection] = {}
        self.qdrant_url = qdrant_url
        self._qdrant: Any = None
        self._init_qdrant()

    def _init_qdrant(self) -> None:
        if QdrantClient is None:
            return
        try:
            if self.qdrant_url:
                self._qdrant = QdrantClient(url=self.qdrant_url)
            else:
                self._qdrant = QdrantClient(":memory:")
            logger.info("Qdrant client initialized")
        except Exception as exc:
            logger.warning(f"Qdrant client unavailable: {exc}")
            self._qdrant = None

    def _get_collection(self, name: str) -> VectorCollection:
        if name not in self.collections:
            self.collections[name] = VectorCollection(name, 128, SimilarityMetric.COSINE)
        return self.collections[name]

    def _normalize(self, vector: List[float]) -> List[float]:
        if np is None:
            norm = sum(v * v for v in vector) ** 0.5
            if norm == 0:
                return vector[:]
            return [v / norm for v in vector]
        arr = np.array(vector, dtype=float)
        norm = np.linalg.norm(arr)
        if norm == 0:
            return cast(List[float], arr.tolist())
        return cast(List[float], (arr / norm).tolist())

    def _score(
        self, query: List[float], entry: VectorStoreEntry, metric: SimilarityMetric
    ) -> float:
        q: Any = np.array(query, dtype=float) if np is not None else query
        v: Any = np.array(entry.vector, dtype=float) if np is not None else entry.vector
        if metric == SimilarityMetric.COSINE:
            q = self._normalize(q if isinstance(q, list) else q.tolist())
            v = self._normalize(v if isinstance(v, list) else v.tolist())
            if np is not None:
                return float(np.dot(np.array(q), np.array(v)))
            return sum(a * b for a, b in zip(q, v))
        if metric == SimilarityMetric.DOT:
            if np is not None:
                return float(np.dot(np.array(query, dtype=float), v))
            return sum(a * b for a, b in zip(query, entry.vector))
        # euclidean
        if np is not None:
            return float(-np.linalg.norm(np.array(query, dtype=float) - v))
        return -sum((a - b) ** 2 for a, b in zip(query, entry.vector)) ** 0.5

    def _filter_matches(self, entry: VectorStoreEntry, filters: Dict[str, Any]) -> bool:
        for key, value in filters.items():
            if entry.payload.get(key) != value:
                return False
        return True

    async def create_index(self, request: IndexRequest) -> IndexResponse:
        self.metrics.inc_request("create_index")
        collection = VectorCollection(request.collection, request.dimension, request.metric)
        self.collections[request.collection] = collection
        if self._qdrant is not None:
            try:
                distance = (
                    Distance.COSINE
                    if request.metric == SimilarityMetric.COSINE
                    else Distance.DOT if request.metric == SimilarityMetric.DOT else Distance.EUCLID
                )
                self._qdrant.recreate_collection(
                    collection_name=request.collection,
                    vectors_config=VectorParams(size=request.dimension, distance=distance),
                )
            except Exception as exc:
                logger.warning(f"Qdrant index creation failed: {exc}")
        self.metrics.set_index_size(len(collection.entries))
        self.metrics.inc_operation("index_created")
        return IndexResponse(
            collection=request.collection,
            dimension=request.dimension,
            metric=request.metric.value,
            indexed_count=0,
        )

    async def store(self, request: VectorStoreRequest) -> Dict[str, Any]:
        self.metrics.inc_request("store")
        collection = self._get_collection(request.collection)
        if len(request.vector) != collection.dimension and collection.dimension != 128:
            collection.dimension = len(request.vector)
        collection.entries[request.id] = VectorStoreEntry(
            request.id, request.vector[:], request.payload
        )
        self.metrics.set_index_size(len(collection.entries))
        self.metrics.inc_operation("vector_stored")

        if self._qdrant is not None:
            try:
                self._qdrant.upsert(
                    collection_name=request.collection,
                    points=[
                        PointStruct(
                            id=request.id,
                            vector=request.vector,
                            payload=request.payload,
                        )
                    ],
                )
            except Exception as exc:
                logger.warning(f"Qdrant upsert failed: {exc}")
        return {"id": request.id, "stored": True}

    async def store_batch(self, request: VectorBatchStoreRequest) -> Dict[str, Any]:
        self.metrics.inc_request("store_batch")
        for item in request.vectors:
            item.collection = request.collection
            await self.store(item)
        self.metrics.observe_batch_size("store_batch", len(request.vectors))
        return {"stored_count": len(request.vectors)}

    async def search(self, request: VectorSearchRequest) -> VectorSearchResponse:
        self.metrics.inc_request("search")
        collection = self._get_collection(request.collection)
        candidates = [
            entry
            for entry in collection.entries.values()
            if self._filter_matches(entry, request.filters)
        ]
        scored: List[Tuple[float, VectorStoreEntry]] = []
        for entry in candidates:
            score = self._score(request.query_vector, entry, request.metric)
            scored.append((score, entry))
        scored.sort(key=lambda x: x[0], reverse=True)
        top = scored[: request.top_k]
        results = [
            VectorResult(
                id=entry.id,
                score=score,
                payload=entry.payload,
                vector=entry.vector,
            )
            for score, entry in top
        ]
        self.metrics.inc_operation("search")
        return VectorSearchResponse(
            collection=request.collection,
            total=len(candidates),
            results=results,
            metric=request.metric.value,
        )

    async def exact_search(self, request: VectorSearchRequest) -> VectorSearchResponse:
        """Exact (exhaustive) nearest neighbor search."""
        self.metrics.inc_request("exact_search")
        return await self.search(request)

    async def ann_search(self, request: VectorSearchRequest) -> VectorSearchResponse:
        """Approximate nearest neighbor search (default_value using flat index)."""
        self.metrics.inc_request("ann_search")
        self.metrics.inc_operation("ann_search")
        return await self.search(request)

    async def hybrid_search(self, request: HybridSearchRequest) -> VectorSearchResponse:
        """Combine vector similarity with keyword matching in payloads."""
        self.metrics.inc_request("hybrid_search")
        collection = self._get_collection(request.collection)
        query_words = set(request.query_text.lower().split())
        candidates = list(collection.entries.values())
        scored: List[Tuple[float, VectorStoreEntry]] = []
        for entry in candidates:
            vec_score = self._score(request.query_vector, entry, request.metric)
            text = " ".join(str(v) for v in entry.payload.values()).lower()
            text_score = sum(1 for w in query_words if w in text) / max(1, len(query_words))
            combined = request.alpha * vec_score + (1 - request.alpha) * text_score
            scored.append((combined, entry))
        scored.sort(key=lambda x: x[0], reverse=True)
        top = scored[: request.top_k]
        results = [
            VectorResult(id=entry.id, score=score, payload=entry.payload, vector=entry.vector)
            for score, entry in top
        ]
        self.metrics.inc_operation("hybrid_search")
        return VectorSearchResponse(
            collection=request.collection,
            total=len(candidates),
            results=results,
            metric=request.metric.value,
        )

    async def multi_vector_search(self, request: MultiVectorSearchRequest) -> VectorSearchResponse:
        """Search using multiple query vectors combined with weights."""
        self.metrics.inc_request("multi_vector_search")
        weights = request.weights or [1.0] * len(request.query_vectors)
        weights = [float(w) for w in weights]
        if np is not None:
            query = np.average(
                np.array(request.query_vectors, dtype=float),
                axis=0,
                weights=weights,
            ).tolist()
        else:
            dim = len(request.query_vectors[0])
            query = [0.0] * dim
            total_weight = sum(weights)
            for vec, weight in zip(request.query_vectors, weights):
                for i, v in enumerate(vec):
                    query[i] += v * weight / total_weight
        search_req = VectorSearchRequest(
            collection=request.collection,
            query_vector=query,
            top_k=request.top_k,
            metric=request.metric,
        )
        self.metrics.inc_operation("multi_vector_search")
        return await self.search(search_req)

    async def cluster_vectors(self, request: ClusterRequest) -> ClusterResponse:
        """Run k-means clustering over vectors in a collection."""
        self.metrics.inc_request("cluster_vectors")
        collection = self._get_collection(request.collection)
        vectors = [entry.vector for entry in collection.entries.values()]
        ids = list(collection.entries.keys())
        if len(vectors) < request.n_clusters:
            labels = {entry_id: 0 for entry_id in ids}
            centroids = [vectors[0] if vectors else [0.0] * collection.dimension]
            return ClusterResponse(
                collection=request.collection,
                n_clusters=request.n_clusters,
                labels=labels,
                centroids=centroids,
            )
        centroids, assignments = self._kmeans(vectors, request.n_clusters, request.max_iter)
        labels = {entry_id: int(assignments[i]) for i, entry_id in enumerate(ids)}
        self.metrics.inc_operation("clustering")
        return ClusterResponse(
            collection=request.collection,
            n_clusters=request.n_clusters,
            labels=labels,
            centroids=[c.tolist() if hasattr(c, "tolist") else list(c) for c in centroids],
        )

    def _kmeans(
        self, vectors: List[List[float]], k: int, max_iter: int
    ) -> Tuple[List[Any], List[int]]:
        if np is None:
            # Pure-python fallback: assign all to first centroid.
            return [vectors[0][:]], [0] * len(vectors)
        data = np.array(vectors, dtype=float)
        rng = np.random.default_rng(42)
        indices = rng.choice(len(data), size=k, replace=False)
        centroids = data[indices].copy()
        for _ in range(max_iter):
            distances = np.linalg.norm(data[:, np.newaxis] - centroids, axis=2)
            assignments = distances.argmin(axis=1)
            new_centroids = np.array(
                [
                    (
                        data[assignments == i].mean(axis=0)
                        if np.any(assignments == i)
                        else centroids[i]
                    )
                    for i in range(k)
                ]
            )
            if np.allclose(centroids, new_centroids):
                break
            centroids = new_centroids
        return centroids.tolist(), assignments.tolist()

    def get_stats(self) -> Dict[str, Any]:
        total = sum(len(c.entries) for c in self.collections.values())
        return {
            "total_requests": self.metrics.request_count,
            "cache_hits": self.metrics.cache_hits_count,
            "cache_misses": self.metrics.cache_misses_count,
            "operations": {},
            "index_size": total,
        }

    def list_methods(self) -> List[str]:
        return [
            "create_index",
            "store",
            "store_batch",
            "search",
            "exact_search",
            "ann_search",
            "hybrid_search",
            "multi_vector_search",
            "cluster_vectors",
            "get_stats",
        ]

    async def call(self, method: str, **kwargs: Any) -> Any:
        fn = getattr(self, method, None)
        if not fn:
            raise ValueError(f"Unknown method: {method}")
        if asyncio.iscoroutinefunction(fn):
            return await fn(**kwargs)
        return fn(**kwargs)
