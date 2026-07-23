# -*- coding: utf-8 -*-
"""
Tests for core/ai/rag/fusion.py.
"""

from unittest.mock import AsyncMock

import pytest

from core.ai.rag.fusion import (
    ConcatenationFusion,
    FusionStrategy,
    RAGPipeline,
    RelevanceFusion,
)
from core.ai.rag.retriever import RetrievalResult
from core.ai.rag.vectorizer import DocumentChunk


@pytest.fixture
def retrieval_results():
    chunks = [
        DocumentChunk(
            id="c1", document_id="d1", content="First chunk content", chunk_index=0, metadata={}
        ),
        DocumentChunk(
            id="c2", document_id="d1", content="Second chunk", chunk_index=1, metadata={}
        ),
    ]
    return [
        RetrievalResult(chunk=chunks[0], score=0.9, metadata={}),
        RetrievalResult(chunk=chunks[1], score=0.5, metadata={}),
    ]


class TestFusionStrategy:
    def test_abstract_fuse(self, retrieval_results):
        strategy = FusionStrategy()
        with pytest.raises(NotImplementedError):
            strategy.fuse("query", retrieval_results)


class TestConcatenationFusion:
    def test_concatenation(self, retrieval_results):
        strategy = ConcatenationFusion()
        context = strategy.fuse("query", retrieval_results)
        assert "First chunk content" in context
        assert "Second chunk" in context

    def test_max_length(self, retrieval_results):
        strategy = ConcatenationFusion()
        context = strategy.fuse("query", retrieval_results, max_context_length=10)
        assert len(context) <= 10

    def test_empty_results(self):
        strategy = ConcatenationFusion()
        context = strategy.fuse("query", [])
        assert context == ""


class TestRelevanceFusion:
    def test_relevance_ordering(self, retrieval_results):
        strategy = RelevanceFusion()
        context = strategy.fuse("query", retrieval_results)
        # Results sorted by score descending, first should be high score chunk
        assert "First chunk content" in context
        assert "0.90" in context or "0.9" in context

    def test_max_length(self, retrieval_results):
        strategy = RelevanceFusion()
        context = strategy.fuse("query", retrieval_results, max_context_length=5)
        assert len(context) <= 5

    def test_empty_results(self):
        strategy = RelevanceFusion()
        context = strategy.fuse("query", [])
        assert context == ""


class TestRAGPipeline:
    @pytest.fixture
    def mock_retriever(self, retrieval_results):
        retriever = AsyncMock()
        retriever.retrieve.return_value = retrieval_results
        return retriever

    @pytest.fixture
    def mock_reranker(self, retrieval_results):
        reranker = AsyncMock()
        reranker.rerank.return_value = retrieval_results
        return reranker

    @pytest.mark.asyncio
    async def test_query_without_rerank(self, mock_retriever):
        pipeline = RAGPipeline(mock_retriever)
        result = await pipeline.query("test", top_k=2, rerank=False)
        assert result["query"] == "test"
        assert "context" in result
        assert "sources" in result
        assert len(result["sources"]) == 2

    @pytest.mark.asyncio
    async def test_query_with_rerank(self, mock_retriever, mock_reranker):
        pipeline = RAGPipeline(mock_retriever, reranker=mock_reranker)
        result = await pipeline.query("test", top_k=2, rerank=True)
        assert result["query"] == "test"
        mock_reranker.rerank.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_query_empty_results(self, mock_retriever):
        mock_retriever.retrieve.return_value = []
        pipeline = RAGPipeline(mock_retriever)
        result = await pipeline.query("test")
        assert result["context"] == ""
        assert result["sources"] == []

    @pytest.mark.asyncio
    async def test_query_custom_max_length(self, mock_retriever):
        pipeline = RAGPipeline(mock_retriever)
        result = await pipeline.query("test", max_context_length=10)
        assert len(result["context"]) <= 10
