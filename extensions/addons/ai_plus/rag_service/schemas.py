# -*- coding: utf-8 -*-
"""Pydantic schemas for the RAG microservice."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class DocumentSource(str, Enum):
    """Document source types."""

    TEXT = "text"
    FILE = "file"
    URL = "url"


class VectorizeRequest(BaseModel):
    """Document vectorization request."""

    content: str
    source: DocumentSource = DocumentSource.TEXT
    metadata: Dict[str, Any] = Field(default_factory=dict)
    chunk_size: int = 512
    chunk_overlap: int = 64


class VectorizeResponse(BaseModel):
    """Document vectorization response."""

    chunks: List[str]
    vectors: List[List[float]]
    dimension: int
    chunk_count: int
    latency_ms: float


class IndexRequest(BaseModel):
    """Knowledge base index request."""

    document_id: str
    content: str
    source: DocumentSource = DocumentSource.TEXT
    metadata: Dict[str, Any] = Field(default_factory=dict)


class IndexResponse(BaseModel):
    """Knowledge base index response."""

    document_id: str
    chunks_indexed: int
    status: str
    reason: Optional[str] = None
    stale: bool = False


class SearchRequest(BaseModel):
    """Semantic search request."""

    query: str
    top_k: int = 5
    score_threshold: Optional[float] = None
    use_cache: bool = True


class SearchResult(BaseModel):
    """Search result item."""

    chunk_id: str
    content: str
    score: float
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SearchResponse(BaseModel):
    """Semantic search response."""

    query: str
    results: List[SearchResult]
    total: int
    latency_ms: float


class RetrieveRequest(BaseModel):
    """Knowledge base retrieve request."""

    query: str
    top_k: int = 5
    score_threshold: Optional[float] = None
    filters: Dict[str, Any] = Field(default_factory=dict)


class RetrieveResponse(BaseModel):
    """Knowledge base retrieve response."""

    query: str
    results: List[SearchResult]
    total: int


class ContextRequest(BaseModel):
    """Context build request."""

    query: str
    search_results: Optional[List[SearchResult]] = None
    top_k: int = 5
    max_context_length: int = 4096


class ContextResponse(BaseModel):
    """Context build response."""

    query: str
    context: str
    source_count: int
    token_estimate: int


class GenerateRequest(BaseModel):
    """Answer generation request."""

    query: str
    context: Optional[str] = None
    top_k: int = 5
    score_threshold: Optional[float] = None
    max_tokens: int = 1024
    temperature: float = 0.7


class GenerateResponse(BaseModel):
    """Answer generation response."""

    query: str
    answer: str
    sources: List[SearchResult]
    latency_ms: float


class HybridRequest(BaseModel):
    """Hybrid retrieval request."""

    query: str
    top_k: int = 5
    semantic_weight: float = 0.7
    keyword_weight: float = 0.3
    score_threshold: Optional[float] = None
    recency_weight: float = 0.15


class RerankRequest(BaseModel):
    """Rerank request."""

    query: str
    candidates: List[SearchResult]
    top_k: int = 5


class RecallRequest(BaseModel):
    """Multi-way recall request."""

    query: str
    top_k: int = 5
    strategies: List[str] = Field(default_factory=lambda: ["semantic", "keyword", "vector"])
    score_threshold: Optional[float] = None
    recency_weight: float = 0.15


class RecallResponse(BaseModel):
    """Multi-way recall response."""

    query: str
    strategy_results: Dict[str, List[SearchResult]]
    fused_results: List[SearchResult]
    total: int


class BatchVectorizeRequest(BaseModel):
    """Batch vectorization request."""

    documents: List[VectorizeRequest]


class BatchSearchRequest(BaseModel):
    """Batch search request."""

    queries: List[str]
    top_k: int = 5


class DeleteRequest(BaseModel):
    """Delete document request."""

    document_id: str


class MarkStaleRequest(BaseModel):
    """Mark a document as stale/outdated."""

    document_id: str
    reason: str = "deprecated"


class RebuildIndexRequest(BaseModel):
    """Rebuild embeddings for the whole index or a subset."""

    document_ids: Optional[List[str]] = None
    force: bool = False


class KnowledgeGraphLinkageRequest(BaseModel):
    """Link a knowledge base document into the knowledge graph."""

    document_id: str
    service: Optional[str] = None
    document_type: Optional[str] = None


class ServiceHealth(BaseModel):
    """Service health response."""

    status: str
    service: str
    uptime_seconds: int = 0
    index_size: int = 0


class StatsResponse(BaseModel):
    """Service statistics response."""

    index_size: int
    cache_hits: int
    cache_misses: int
    total_requests: int
    operations: Dict[str, int] = Field(default_factory=dict)
