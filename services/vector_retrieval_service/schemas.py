# -*- coding: utf-8 -*-
"""Pydantic schemas for the vector retrieval microservice."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ServiceHealth(BaseModel):
    """Service health response."""

    status: str
    service: str
    uptime_seconds: int = 0
    index_size: int = 0


class StatsResponse(BaseModel):
    """Service statistics response."""

    total_requests: int
    cache_hits: int
    cache_misses: int
    operations: Dict[str, int] = Field(default_factory=dict)
    index_size: int


class SimilarityMetric(str, Enum):
    """Supported similarity metrics."""

    COSINE = "cosine"
    DOT = "dot"
    EUCLIDEAN = "euclidean"


class VectorStoreRequest(BaseModel):
    """Store a single vector."""

    collection: str = "default"
    id: str
    vector: List[float]
    payload: Dict[str, Any] = Field(default_factory=dict)


class VectorBatchStoreRequest(BaseModel):
    """Store a batch of vectors."""

    collection: str = "default"
    vectors: List[VectorStoreRequest]


class VectorSearchRequest(BaseModel):
    """Search vectors by similarity."""

    collection: str = "default"
    query_vector: List[float]
    top_k: int = 5
    metric: SimilarityMetric = SimilarityMetric.COSINE
    filters: Dict[str, Any] = Field(default_factory=dict)


class VectorResult(BaseModel):
    """Single search result."""

    id: str
    score: float
    payload: Dict[str, Any]
    vector: Optional[List[float]] = None


class VectorSearchResponse(BaseModel):
    """Search response."""

    collection: str
    total: int
    results: List[VectorResult]
    metric: str


class IndexRequest(BaseModel):
    """Create or update a vector index."""

    collection: str = "default"
    dimension: int = 128
    metric: SimilarityMetric = SimilarityMetric.COSINE
    params: Dict[str, Any] = Field(default_factory=dict)


class IndexResponse(BaseModel):
    """Index creation response."""

    collection: str
    dimension: int
    metric: str
    indexed_count: int


class ClusterRequest(BaseModel):
    """Cluster vectors in a collection."""

    collection: str = "default"
    n_clusters: int = 3
    max_iter: int = 20


class ClusterResponse(BaseModel):
    """Clustering response."""

    collection: str
    n_clusters: int
    labels: Dict[str, int]
    centroids: List[List[float]]


class HybridSearchRequest(BaseModel):
    """Hybrid search using vector similarity and keyword matching."""

    collection: str = "default"
    query_vector: List[float]
    query_text: str
    top_k: int = 5
    alpha: float = 0.7
    metric: SimilarityMetric = SimilarityMetric.COSINE


class MultiVectorSearchRequest(BaseModel):
    """Search with multiple query vectors."""

    collection: str = "default"
    query_vectors: List[List[float]]
    weights: Optional[List[float]] = None
    top_k: int = 5
    metric: SimilarityMetric = SimilarityMetric.COSINE


class RpcRequest(BaseModel):
    """RPC request wrapper."""

    payload: Optional[Dict[str, Any]] = None
