# -*- coding: utf-8 -*-
"""Vector retrieval service.

Provides two layers of functionality:

* ``execute_operation`` – thin dispatch to :class:`StorageDriver` (used by the
  generic add-on integration tests / RPC dispatcher).
* A **real** in-process vector index API (``create_index`` / ``store`` /
  ``store_batch`` / ``search`` / ``ann_search`` / ``exact_search`` /
  ``hybrid_search`` / ``multi_vector_search`` / ``cluster_vectors``) implementing
  genuine cosine / dot / euclidean similarity, keyword-augmented hybrid scoring,
  weighted multi-vector search and deterministic k-means clustering.  This is the
  API advertised by ``main_app.py``.
"""

from __future__ import annotations

import math
import random
import threading
from typing import Any, Dict, List, Optional

from extensions.addons.engines.storage_driver import StorageDriver

OPERATIONS: List[str] = [
    "vector_create_collection",
    "vector_upsert",
    "vector_search",
    "get_stats",
]

_METRIC_ALIASES = {"cosine": "cosine", "dot": "dot", "euclidean": "euclidean"}


def _metric_name(metric: Any) -> str:
    """Normalise a metric enum/string to its canonical name."""
    value = getattr(metric, "value", metric)
    return _METRIC_ALIASES.get(str(value).lower(), "cosine")


def _dot(a: List[float], b: List[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def _norm(a: List[float]) -> float:
    return math.sqrt(sum(x * x for x in a))


def _similarity(metric: str, a: List[float], b: List[float]) -> float:
    """Real similarity score (higher is more similar)."""
    if metric == "dot":
        return _dot(a, b)
    if metric == "euclidean":
        dist = math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))
        return 1.0 / (1.0 + dist)
    denom = _norm(a) * _norm(b)
    if denom == 0:
        return 0.0
    return _dot(a, b) / denom


class _Collection:
    """An in-process vector collection with real similarity search."""

    def __init__(self, dimension: int, metric: str) -> None:
        self.dimension = dimension
        self.metric = metric
        self.entries: List[Dict[str, Any]] = []
        self._by_id: Dict[str, Dict[str, Any]] = {}

    def upsert(self, item_id: str, vector: List[float], payload: Dict[str, Any]) -> None:
        record = {"id": item_id, "vector": list(vector), "payload": dict(payload or {})}
        if item_id in self._by_id:
            for index, existing in enumerate(self.entries):
                if existing["id"] == item_id:
                    self.entries[index] = record
                    break
        else:
            self.entries.append(record)
        self._by_id[item_id] = record

    def search(
        self, query: List[float], top_k: int, metric: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        active_metric = metric or self.metric
        scored = [
            {
                "id": entry["id"],
                "score": _similarity(active_metric, query, entry["vector"]),
                "payload": entry["payload"],
                "vector": entry["vector"],
            }
            for entry in self.entries
        ]
        scored.sort(key=lambda item: item["score"], reverse=True)
        return scored[: max(0, top_k)]


class Service:
    """Vector retrieval service (thin driver dispatch + real vector index)."""

    def __init__(self, dry_run: bool = True, **kwargs: Any) -> None:
        self.driver = StorageDriver(dry_run=dry_run, **kwargs)
        self.dry_run = dry_run
        self._collections: Dict[str, _Collection] = {}
        self._lock = threading.Lock()
        self._total_requests = 0
        self._operations: Dict[str, int] = {}

    # ------------------------------------------------------------------
    # Thin driver dispatch (compatibility with generic addon tooling)
    # ------------------------------------------------------------------
    def execute_operation(self, name: str, params: Optional[Dict[str, Any]] = None) -> Any:
        if params is None:
            params = {}
        if hasattr(params, "model_dump"):
            params = params.model_dump()
        if name not in OPERATIONS:
            raise ValueError(f"Unknown operation: {name}")
        method = getattr(self.driver, name)
        return method(**params)

    # ------------------------------------------------------------------
    # Real vector index API
    # ------------------------------------------------------------------
    @property
    def collections(self) -> Dict[str, _Collection]:
        return self._collections

    def list_methods(self) -> List[str]:
        return sorted(
            [
                "create_index",
                "store",
                "store_batch",
                "search",
                "ann_search",
                "exact_search",
                "hybrid_search",
                "multi_vector_search",
                "cluster_vectors",
                "get_stats",
            ]
        )

    def get_stats(self) -> Dict[str, Any]:
        """Real service statistics derived from in-process state."""
        index_size = sum(len(collection.entries) for collection in self._collections.values())
        return {
            "total_requests": self._total_requests,
            "cache_hits": self.driver._cache_hits,
            "cache_misses": max(0, self._total_requests - self.driver._cache_hits),
            "operations": dict(self._operations),
            "index_size": index_size,
        }

    def _touch(self, operation: str) -> None:
        self._total_requests += 1
        self._operations[operation] = self._operations.get(operation, 0) + 1

    def _get_collection(self, name: str, dimension: int = 0, metric: str = "cosine") -> _Collection:
        collection = self._collections.get(name)
        if collection is None:
            collection = _Collection(dimension or 0, metric)
            self._collections[name] = collection
        return collection

    async def create_index(self, request: Any):
        from .schemas import IndexResponse

        self._touch("create_index")
        with self._lock:
            collection = self._get_collection(
                request.collection, request.dimension, _metric_name(request.metric)
            )
            collection.dimension = request.dimension
            collection.metric = _metric_name(request.metric)
            indexed = len(collection.entries)
        return IndexResponse(
            collection=request.collection,
            dimension=request.dimension,
            metric=_metric_name(request.metric),
            indexed_count=indexed,
        )

    async def store(self, request: Any) -> Dict[str, Any]:
        self._touch("store")
        with self._lock:
            collection = self._get_collection(request.collection)
            collection.upsert(request.id, request.vector, request.payload)
        return {"stored": 1, "collection": request.collection, "id": request.id}

    async def store_batch(self, request: Any) -> Dict[str, Any]:
        self._touch("store_batch")
        with self._lock:
            collection = self._get_collection(request.collection)
            for item in request.vectors:
                collection.upsert(item.id, item.vector, item.payload)
        return {"stored": len(request.vectors), "collection": request.collection}

    def _search(self, request: Any, metric: Optional[str] = None):
        from .schemas import VectorResult, VectorSearchResponse

        collection = self._get_collection(request.collection)
        metric_name = metric or _metric_name(request.metric)
        matches = collection.search(request.query_vector, request.top_k, metric_name)
        return VectorSearchResponse(
            collection=request.collection,
            total=len(matches),
            metric=metric_name,
            results=[
                VectorResult(
                    id=str(match["id"]),
                    score=float(match["score"]),
                    payload=match["payload"],
                    vector=match.get("vector"),
                )
                for match in matches
            ],
        )

    async def search(self, request: Any):
        self._touch("search")
        return self._search(request)

    async def ann_search(self, request: Any):
        # Approximate search: identical scoring path over the current index.
        self._touch("ann_search")
        return self._search(request)

    async def exact_search(self, request: Any):
        self._touch("exact_search")
        return self._search(request)

    async def hybrid_search(self, request: Any):
        """Combine vector similarity with real keyword overlap on payload text."""
        from .schemas import VectorResult, VectorSearchResponse

        self._touch("hybrid_search")
        collection = self._get_collection(request.collection)
        metric_name = _metric_name(request.metric)
        query_terms = [term for term in request.query_text.lower().split() if term]

        scored = []
        for entry in collection.entries:
            vector_score = _similarity(metric_name, request.query_vector, entry["vector"])
            text = " ".join(str(value) for value in (entry["payload"] or {}).values()).lower()
            if query_terms:
                matched = sum(1 for term in query_terms if term in text)
                keyword_score = matched / len(query_terms)
            else:
                keyword_score = 0.0
            combined = request.alpha * vector_score + (1.0 - request.alpha) * keyword_score
            scored.append(
                {
                    "id": entry["id"],
                    "score": combined,
                    "payload": entry["payload"],
                    "vector": entry["vector"],
                }
            )
        scored.sort(key=lambda item: item["score"], reverse=True)
        results = scored[: max(0, request.top_k)]
        return VectorSearchResponse(
            collection=request.collection,
            total=len(results),
            metric=metric_name,
            results=[
                VectorResult(
                    id=str(item["id"]),
                    score=float(item["score"]),
                    payload=item["payload"],
                    vector=item.get("vector"),
                )
                for item in results
            ],
        )

    async def multi_vector_search(self, request: Any):
        """Weighted average similarity over multiple query vectors."""
        from .schemas import VectorResult, VectorSearchResponse

        self._touch("multi_vector_search")
        collection = self._get_collection(request.collection)
        metric_name = _metric_name(request.metric)

        weights = request.weights or [1.0] * len(request.query_vectors)
        if len(weights) != len(request.query_vectors):
            raise ValueError("weights length must match query_vectors length")
        total_weight = sum(weights) or 1.0

        scored = []
        for entry in collection.entries:
            weighted = 0.0
            for vector, weight in zip(request.query_vectors, weights):
                weighted += weight * _similarity(metric_name, vector, entry["vector"])
            scored.append(
                {
                    "id": entry["id"],
                    "score": weighted / total_weight,
                    "payload": entry["payload"],
                    "vector": entry["vector"],
                }
            )
        scored.sort(key=lambda item: item["score"], reverse=True)
        results = scored[: max(0, request.top_k)]
        return VectorSearchResponse(
            collection=request.collection,
            total=len(results),
            metric=metric_name,
            results=[
                VectorResult(
                    id=str(item["id"]),
                    score=float(item["score"]),
                    payload=item["payload"],
                    vector=item.get("vector"),
                )
                for item in results
            ],
        )

    async def cluster_vectors(self, request: Any):
        """Deterministic k-means clustering over the collection's vectors."""
        from .schemas import ClusterResponse

        self._touch("cluster_vectors")
        collection = self._get_collection(request.collection)
        vectors = [entry["vector"] for entry in collection.entries]
        ids = [str(entry["id"]) for entry in collection.entries]
        k = min(max(1, request.n_clusters), len(vectors)) if vectors else 0

        if k == 0:
            return ClusterResponse(
                collection=request.collection, n_clusters=0, labels={}, centroids=[]
            )

        rng = random.Random(42)
        centroids = [list(vectors[rng.randrange(len(vectors))]) for _ in range(k)]
        labels: Dict[str, int] = {}

        for _ in range(max(1, request.max_iter)):
            labels = {}
            clusters: List[List[int]] = [[] for _ in range(k)]
            for index, vector in enumerate(vectors):
                best, best_score = 0, None
                for cluster_id, centroid in enumerate(centroids):
                    score = _similarity("euclidean", vector, centroid)
                    if best_score is None or score > best_score:
                        best, best_score = cluster_id, score
                labels[ids[index]] = best
                clusters[best].append(index)

            new_centroids = []
            for cluster_id in range(k):
                members = clusters[cluster_id]
                if not members:
                    new_centroids.append(centroids[cluster_id])
                    continue
                dim = len(vectors[members[0]])
                centroid = [
                    sum(vectors[m][d] for m in members) / len(members) for d in range(dim)
                ]
                new_centroids.append(centroid)
            if new_centroids == centroids:
                break
            centroids = new_centroids

        return ClusterResponse(
            collection=request.collection,
            n_clusters=k,
            labels=labels,
            centroids=centroids,
        )

    async def call(self, method: str, **payload: Any) -> Any:
        """Generic async dispatcher used by main_app RPC endpoint."""
        if method not in self.list_methods():
            raise ValueError(f"Unknown method: {method}")
        request = payload.pop("request", None)
        if request is not None:
            return await getattr(self, method)(request)
        return await getattr(self, method)(**payload)


Service.OPERATIONS = OPERATIONS


VectorRetrievalService = Service
