# -*- coding: utf-8 -*-
"""Prometheus metrics for the RAG microservice."""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

RAG_REQUESTS_TOTAL = Counter(
    "rag_requests_total",
    "Total number of RAG requests",
    ["operation"],
)
RAG_REQUEST_FAILURES_TOTAL = Counter(
    "rag_request_failures_total",
    "Total number of RAG request failures",
    ["operation", "error"],
)
RAG_LATENCY = Histogram(
    "rag_request_latency_seconds",
    "RAG request latency",
    ["operation"],
)
RAG_DOCUMENTS_INDEXED = Counter(
    "rag_documents_indexed_total",
    "Total number of documents indexed",
    ["source"],
)
RAG_QUERIES_TOTAL = Counter(
    "rag_queries_total",
    "Total number of search/retrieve queries",
    ["operation"],
)
RAG_CACHE_HITS = Counter(
    "rag_cache_hits_total",
    "Cache hits",
    [],
)
RAG_CACHE_MISSES = Counter(
    "rag_cache_misses_total",
    "Cache misses",
    [],
)
RAG_BATCH_SIZE = Histogram(
    "rag_batch_size",
    "Batch request size",
    ["operation"],
)
RAG_EMBEDDING_DIMENSION = Gauge(
    "rag_embedding_dimension",
    "Configured embedding dimension",
    [],
)
RAG_TOP_K_RESULTS = Histogram(
    "rag_top_k_results",
    "Number of results returned",
    ["operation"],
)
RAG_RETRIEVER_SCORE = Histogram(
    "rag_retriever_score",
    "Similarity score for retrieved chunks",
    ["operation"],
)
