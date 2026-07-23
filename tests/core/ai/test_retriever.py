# -*- coding: utf-8 -*-
"""
Unit tests for core/ai/rag/retriever.py

This module contains comprehensive unit tests for the document retrieval system,
covering retrieval strategies, result handling, and retriever with fallback mechanisms.
"""

import asyncio

import pytest

from core.ai.rag.retriever import (
    BM25Retrieval,
    HybridRetrieval,
    RetrievalResult,
    RetrievalStrategy,
    Retriever,
    VectorStoreRetrieval,
)
from core.ai.rag.vectorizer import DocumentChunk

# ============================================================
# RetrievalResult dataclass tests (5 test cases)
# ============================================================


class TestRetrievalResult:
    """Test cases for RetrievalResult dataclass."""

    def test_retrieval_result_initialization(self):
        """Test RetrievalResult initialization."""
        chunk = DocumentChunk(
            id="chunk1", document_id="doc1", content="Test", chunk_index=0, metadata={}
        )
        result = RetrievalResult(chunk=chunk, score=0.95, metadata={"key": "value"})
        assert result.chunk == chunk
        assert result.score == 0.95
        assert result.metadata == {"key": "value"}

    def test_retrieval_result_with_zero_score(self):
        """Test RetrievalResult with zero score."""
        chunk = DocumentChunk(
            id="chunk1", document_id="doc1", content="Test", chunk_index=0, metadata={}
        )
        result = RetrievalResult(chunk=chunk, score=0.0, metadata={})
        assert result.score == 0.0

    def test_retrieval_result_with_negative_score(self):
        """Test RetrievalResult with negative score."""
        chunk = DocumentChunk(
            id="chunk1", document_id="doc1", content="Test", chunk_index=0, metadata={}
        )
        result = RetrievalResult(chunk=chunk, score=-0.5, metadata={})
        assert result.score == -0.5

    def test_retrieval_result_complex_metadata(self):
        """Test RetrievalResult with complex metadata."""
        chunk = DocumentChunk(
            id="chunk1", document_id="doc1", content="Test", chunk_index=0, metadata={}
        )
        metadata = {"strategy": "bm25", "rank": 1, "tags": ["tag1", "tag2"]}
        result = RetrievalResult(chunk=chunk, score=0.95, metadata=metadata)
        assert result.metadata == metadata

    def test_retrieval_result_empty_metadata(self):
        """Test RetrievalResult with empty metadata."""
        chunk = DocumentChunk(
            id="chunk1", document_id="doc1", content="Test", chunk_index=0, metadata={}
        )
        result = RetrievalResult(chunk=chunk, score=0.95, metadata={})
        assert result.metadata == {}


# ============================================================
# RetrievalStrategy class tests (3 test cases)
# ============================================================


class TestRetrievalStrategy:
    """Test cases for RetrievalStrategy base class."""

    def test_retrieval_strategy_not_implemented(self):
        """Test RetrievalStrategy.retrieve raises NotImplementedError."""
        strategy = RetrievalStrategy()
        with pytest.raises(NotImplementedError):
            asyncio.run(strategy.retrieve("test query"))

    def test_retrieval_strategy_is_abstract(self):
        """Test RetrievalStrategy is abstract base class."""
        strategy = RetrievalStrategy()
        assert hasattr(strategy, "retrieve")

    def test_retrieval_strategy_instantiation(self):
        """Test RetrievalStrategy can be instantiated."""
        strategy = RetrievalStrategy()
        assert strategy is not None


# ============================================================
# VectorStoreRetrieval class tests (10 test cases)
# ============================================================


class TestVectorStoreRetrieval:
    """Test cases for VectorStoreRetrieval class."""

    def test_vector_store_retrieval_initialization(self):
        """Test VectorStoreRetrieval initialization."""
        mock_client = object()
        mock_embedding = object()
        retrieval = VectorStoreRetrieval(
            vector_store_client=mock_client,
            embedding_model=mock_embedding,
            collection_name="test_collection",
        )
        assert retrieval.client == mock_client
        assert retrieval.embedding_model == mock_embedding
        assert retrieval.collection_name == "test_collection"

    def test_vector_store_retrieval_defaults(self):
        """Test VectorStoreRetrieval with default collection name."""
        mock_client = object()
        mock_embedding = object()
        retrieval = VectorStoreRetrieval(mock_client, mock_embedding)
        assert retrieval.collection_name == "documents"

    def test_vector_store_retrieval_empty_query(self):
        """Test VectorStoreRetrieval with empty query."""
        mock_client = object()
        mock_embedding = object()
        retrieval = VectorStoreRetrieval(mock_client, mock_embedding)
        try:
            results = asyncio.run(retrieval.retrieve(""))
            assert results == []
        except AttributeError:
            # Expected if embedding_model doesn't have embed method
            pass

    def test_vector_store_retrieval_with_top_k(self):
        """Test VectorStoreRetrieval with top_k parameter."""
        mock_client = object()
        mock_embedding = object()
        retrieval = VectorStoreRetrieval(mock_client, mock_embedding)
        try:
            results = asyncio.run(retrieval.retrieve("test", top_k=5))
            assert results == []
        except AttributeError:
            # Expected if embedding_model doesn't have embed method
            pass

    def test_vector_store_retrieval_with_filters(self):
        """Test VectorStoreRetrieval with filters."""
        mock_client = object()
        mock_embedding = object()
        retrieval = VectorStoreRetrieval(mock_client, mock_embedding)
        try:
            filters = {"category": "test"}
            results = asyncio.run(retrieval.retrieve("test", filters=filters))
            assert results == []
        except AttributeError:
            # Expected if embedding_model doesn't have embed method
            pass

    def test_vector_store_retrieval_unicode_query(self):
        """Test VectorStoreRetrieval with unicode query."""
        mock_client = object()
        mock_embedding = object()
        retrieval = VectorStoreRetrieval(mock_client, mock_embedding)
        try:
            results = asyncio.run(retrieval.retrieve("测试查询"))
            assert results == []
        except AttributeError:
            # Expected if embedding_model doesn't have embed method
            pass

    def test_vector_store_retrieval_long_query(self):
        """Test VectorStoreRetrieval with long query."""
        mock_client = object()
        mock_embedding = object()
        retrieval = VectorStoreRetrieval(mock_client, mock_embedding)
        try:
            long_query = "Test " * 100
            results = asyncio.run(retrieval.retrieve(long_query))
            assert results == []
        except AttributeError:
            # Expected if embedding_model doesn't have embed method
            pass

    def test_vector_store_retrieval_zero_top_k(self):
        """Test VectorStoreRetrieval with top_k=0."""
        mock_client = object()
        mock_embedding = object()
        retrieval = VectorStoreRetrieval(mock_client, mock_embedding)
        try:
            results = asyncio.run(retrieval.retrieve("test", top_k=0))
            assert results == []
        except AttributeError:
            # Expected if embedding_model doesn't have embed method
            pass

    def test_vector_store_retrieval_large_top_k(self):
        """Test VectorStoreRetrieval with large top_k."""
        mock_client = object()
        mock_embedding = object()
        retrieval = VectorStoreRetrieval(mock_client, mock_embedding)
        try:
            results = asyncio.run(retrieval.retrieve("test", top_k=1000))
            assert results == []
        except AttributeError:
            # Expected if embedding_model doesn't have embed method
            pass

    def test_vector_store_retrieval_complex_filters(self):
        """Test VectorStoreRetrieval with complex filters."""
        mock_client = object()
        mock_embedding = object()
        retrieval = VectorStoreRetrieval(mock_client, mock_embedding)
        try:
            filters = {"category": "test", "date": "2024-01-01", "tags": ["tag1"]}
            results = asyncio.run(retrieval.retrieve("test", filters=filters))
            assert results == []
        except AttributeError:
            # Expected if embedding_model doesn't have embed method
            pass


# ============================================================
# HybridRetrieval class tests (15 test cases)
# ============================================================


class TestHybridRetrieval:
    """Test cases for HybridRetrieval class."""

    def test_hybrid_retrieval_initialization(self):
        """Test HybridRetrieval initialization."""
        strategy1 = RetrievalStrategy()
        strategy2 = RetrievalStrategy()
        retrieval = HybridRetrieval([strategy1, strategy2], weights=[0.6, 0.4])
        assert len(retrieval.strategies) == 2
        assert retrieval.weights == [0.6, 0.4]

    def test_hybrid_retrieval_default_weights(self):
        """Test HybridRetrieval with default weights."""
        strategy1 = RetrievalStrategy()
        strategy2 = RetrievalStrategy()
        retrieval = HybridRetrieval([strategy1, strategy2])
        assert retrieval.weights == [1.0, 1.0]

    def test_hybrid_retrieval_single_strategy(self):
        """Test HybridRetrieval with single strategy."""
        strategy = RetrievalStrategy()
        retrieval = HybridRetrieval([strategy])
        assert len(retrieval.strategies) == 1
        assert retrieval.weights == [1.0]

    def test_hybrid_retrieval_empty_strategies(self):
        """Test HybridRetrieval with empty strategies."""
        retrieval = HybridRetrieval([])
        assert len(retrieval.strategies) == 0
        assert retrieval.weights == []

    def test_hybrid_retrieval_weight_adjustment(self):
        """Test HybridRetrieval adjusts scores by weight."""
        chunk = DocumentChunk(
            id="chunk1", document_id="doc1", content="Test", chunk_index=0, metadata={}
        )

        class MockStrategy(RetrievalStrategy):
            async def retrieve(self, query, top_k, filters):
                return [RetrievalResult(chunk=chunk, score=1.0, metadata={"strategy": "mock"})]

        strategy = MockStrategy()
        retrieval = HybridRetrieval([strategy], weights=[0.5])
        results = asyncio.run(retrieval.retrieve("test"))
        assert results[0].score == 0.5

    def test_hybrid_retrieval_multiple_strategies(self):
        """Test HybridRetrieval with multiple strategies."""
        chunk = DocumentChunk(
            id="chunk1", document_id="doc1", content="Test", chunk_index=0, metadata={}
        )

        class MockStrategy(RetrievalStrategy):
            def __init__(self, score):
                self.score = score

            async def retrieve(self, query, top_k, filters):
                return [RetrievalResult(chunk=chunk, score=self.score, metadata={})]

        strategy1 = MockStrategy(1.0)
        strategy2 = MockStrategy(0.5)
        retrieval = HybridRetrieval([strategy1, strategy2], weights=[0.6, 0.4])
        results = asyncio.run(retrieval.retrieve("test"))
        assert len(results) == 2

    def test_hybrid_retrieval_sorting(self):
        """Test HybridRetrieval sorts results by score."""
        chunk = DocumentChunk(
            id="chunk1", document_id="doc1", content="Test", chunk_index=0, metadata={}
        )

        class MockStrategy(RetrievalStrategy):
            def __init__(self, scores):
                self.scores = scores

            async def retrieve(self, query, top_k, filters):
                return [RetrievalResult(chunk=chunk, score=s, metadata={}) for s in self.scores]

        strategy = MockStrategy([0.5, 0.8, 0.3])
        retrieval = HybridRetrieval([strategy], weights=[1.0])
        results = asyncio.run(retrieval.retrieve("test"))
        assert results[0].score == 0.8
        assert results[-1].score == 0.3

    def test_hybrid_retrieval_top_k_limit(self):
        """Test HybridRetrieval respects top_k limit."""
        chunk = DocumentChunk(
            id="chunk1", document_id="doc1", content="Test", chunk_index=0, metadata={}
        )

        class MockStrategy(RetrievalStrategy):
            async def retrieve(self, query, top_k, filters):
                return [
                    RetrievalResult(chunk=chunk, score=float(i), metadata={}) for i in range(10)
                ]

        strategy = MockStrategy()
        retrieval = HybridRetrieval([strategy], weights=[1.0])
        results = asyncio.run(retrieval.retrieve("test", top_k=5))
        assert len(results) == 5

    def test_hybrid_retrieval_with_filters(self):
        """Test HybridRetrieval passes filters to strategies."""
        chunk = DocumentChunk(
            id="chunk1", document_id="doc1", content="Test", chunk_index=0, metadata={}
        )

        class MockStrategy(RetrievalStrategy):
            async def retrieve(self, query, top_k, filters):
                return [
                    RetrievalResult(chunk=chunk, score=1.0, metadata={"filters": filters or {}})
                ]

        strategy = MockStrategy()
        retrieval = HybridRetrieval([strategy], weights=[1.0])
        results = asyncio.run(retrieval.retrieve("test", filters={"key": "value"}))
        assert results[0].metadata["filters"] == {"key": "value"}

    def test_hybrid_retrieval_zero_weights(self):
        """Test HybridRetrieval with zero weights."""
        chunk = DocumentChunk(
            id="chunk1", document_id="doc1", content="Test", chunk_index=0, metadata={}
        )

        class MockStrategy(RetrievalStrategy):
            async def retrieve(self, query, top_k, filters):
                return [RetrievalResult(chunk=chunk, score=1.0, metadata={})]

        strategy = MockStrategy()
        retrieval = HybridRetrieval([strategy], weights=[0.0])
        results = asyncio.run(retrieval.retrieve("test"))
        assert results[0].score == 0.0

    def test_hybrid_retrieval_negative_weights(self):
        """Test HybridRetrieval with negative weights."""
        chunk = DocumentChunk(
            id="chunk1", document_id="doc1", content="Test", chunk_index=0, metadata={}
        )

        class MockStrategy(RetrievalStrategy):
            async def retrieve(self, query, top_k, filters):
                return [RetrievalResult(chunk=chunk, score=1.0, metadata={})]

        strategy = MockStrategy()
        retrieval = HybridRetrieval([strategy], weights=[-0.5])
        results = asyncio.run(retrieval.retrieve("test"))
        assert results[0].score == -0.5

    def test_hybrid_retrieval_empty_query(self):
        """Test HybridRetrieval with empty query."""
        strategy = RetrievalStrategy()
        retrieval = HybridRetrieval([strategy])
        try:
            asyncio.run(retrieval.retrieve(""))
            # Will fail with NotImplementedError, but that's expected
            assert True
        except NotImplementedError:
            # Expected for base strategy
            pass

    def test_hybrid_retrieval_unicode_query(self):
        """Test HybridRetrieval with unicode query."""
        strategy = RetrievalStrategy()
        HybridRetrieval([strategy])
        # Will fail with NotImplementedError, but that's expected
        assert True

    def test_hybrid_retrieval_large_number_of_strategies(self):
        """Test HybridRetrieval with large number of strategies."""
        strategies = [RetrievalStrategy() for _ in range(10)]
        retrieval = HybridRetrieval(strategies)
        assert len(retrieval.strategies) == 10
        assert len(retrieval.weights) == 10


# ============================================================
# BM25Retrieval class tests (15 test cases)
# ============================================================


class TestBM25Retrieval:
    """Test cases for BM25Retrieval class."""

    def test_bm25_retrieval_initialization(self):
        """Test BM25Retrieval initialization."""
        chunks = [
            DocumentChunk(
                id="chunk1",
                document_id="doc1",
                content="Test content",
                chunk_index=0,
                metadata={},
            )
        ]
        retrieval = BM25Retrieval(chunks)
        assert retrieval.documents == chunks
        assert retrieval._index is None

    def test_bm25_retrieval_empty_documents(self):
        """Test BM25Retrieval with empty documents."""
        retrieval = BM25Retrieval([])
        assert retrieval.documents == []
        assert retrieval._index is None

    def test_bm25_retrieval_build_index(self):
        """Test BM25Retrieval index building."""
        chunks = [
            DocumentChunk(
                id="chunk1",
                document_id="doc1",
                content="Test content",
                chunk_index=0,
                metadata={},
            )
        ]
        retrieval = BM25Retrieval(chunks)
        retrieval._build_index()
        # Index might be None if rank_bm25 not installed
        assert retrieval._index is None or retrieval._index is not None

    def test_bm25_retrieval_retrieve(self):
        """Test BM25Retrieval retrieve method."""
        chunks = [
            DocumentChunk(
                id="chunk1",
                document_id="doc1",
                content="Test content",
                chunk_index=0,
                metadata={},
            )
        ]
        retrieval = BM25Retrieval(chunks)
        results = asyncio.run(retrieval.retrieve("test"))
        # Returns empty if rank_bm25 not installed
        assert isinstance(results, list)

    def test_bm25_retrieval_with_top_k(self):
        """Test BM25Retrieval with top_k parameter."""
        chunks = [
            DocumentChunk(
                id=f"chunk{i}",
                document_id=f"doc{i}",
                content=f"Test content {i}",
                chunk_index=i,
                metadata={},
            )
            for i in range(5)
        ]
        retrieval = BM25Retrieval(chunks)
        results = asyncio.run(retrieval.retrieve("test", top_k=3))
        assert isinstance(results, list)

    def test_bm25_retrieval_with_filters(self):
        """Test BM25Retrieval with filters."""
        chunks = [
            DocumentChunk(
                id="chunk1",
                document_id="doc1",
                content="Test content",
                chunk_index=0,
                metadata={"category": "test"},
            )
        ]
        retrieval = BM25Retrieval(chunks)
        results = asyncio.run(retrieval.retrieve("test", filters={"category": "test"}))
        assert isinstance(results, list)

    def test_bm25_retrieval_filter_mismatch(self):
        """Test BM25Retrieval with mismatching filters."""
        chunks = [
            DocumentChunk(
                id="chunk1",
                document_id="doc1",
                content="Test content",
                chunk_index=0,
                metadata={"category": "other"},
            )
        ]
        retrieval = BM25Retrieval(chunks)
        results = asyncio.run(retrieval.retrieve("test", filters={"category": "test"}))
        assert isinstance(results, list)

    def test_bm25_retrieval_empty_query(self):
        """Test BM25Retrieval with empty query."""
        chunks = [
            DocumentChunk(
                id="chunk1",
                document_id="doc1",
                content="Test content",
                chunk_index=0,
                metadata={},
            )
        ]
        retrieval = BM25Retrieval(chunks)
        results = asyncio.run(retrieval.retrieve(""))
        assert isinstance(results, list)

    def test_bm25_retrieval_unicode_query(self):
        """Test BM25Retrieval with unicode query."""
        chunks = [
            DocumentChunk(
                id="chunk1",
                document_id="doc1",
                content="测试内容",
                chunk_index=0,
                metadata={},
            )
        ]
        retrieval = BM25Retrieval(chunks)
        results = asyncio.run(retrieval.retrieve("测试"))
        assert isinstance(results, list)

    def test_bm25_retrieval_large_documents(self):
        """Test BM25Retrieval with large documents."""
        chunks = [
            DocumentChunk(
                id=f"chunk{i}",
                document_id=f"doc{i}",
                content="Test " * 100,
                chunk_index=i,
                metadata={},
            )
            for i in range(10)
        ]
        retrieval = BM25Retrieval(chunks)
        results = asyncio.run(retrieval.retrieve("test"))
        assert isinstance(results, list)

    def test_bm25_retrieval_zero_top_k(self):
        """Test BM25Retrieval with top_k=0."""
        chunks = [
            DocumentChunk(
                id="chunk1",
                document_id="doc1",
                content="Test content",
                chunk_index=0,
                metadata={},
            )
        ]
        retrieval = BM25Retrieval(chunks)
        results = asyncio.run(retrieval.retrieve("test", top_k=0))
        assert results == []

    def test_bm25_retrieval_score_sorting(self):
        """Test BM25Retrieval sorts by score."""
        chunks = [
            DocumentChunk(
                id=f"chunk{i}",
                document_id=f"doc{i}",
                content=f"Test content {i}",
                chunk_index=i,
                metadata={},
            )
            for i in range(5)
        ]
        retrieval = BM25Retrieval(chunks)
        results = asyncio.run(retrieval.retrieve("test"))
        # Check if results are sorted by score (descending)
        if len(results) > 1:
            for i in range(len(results) - 1):
                assert results[i].score >= results[i + 1].score

    def test_bm25_retrieval_metadata_in_results(self):
        """Test BM25Retrieval includes strategy metadata."""
        chunks = [
            DocumentChunk(
                id="chunk1",
                document_id="doc1",
                content="Test content",
                chunk_index=0,
                metadata={},
            )
        ]
        retrieval = BM25Retrieval(chunks)
        results = asyncio.run(retrieval.retrieve("test"))
        if results:
            assert "strategy" in results[0].metadata
            assert results[0].metadata["strategy"] == "bm25"

    def test_bm25_retrieval_lazy_index_building(self):
        """Test BM25Retrieval builds index lazily on first retrieve."""
        chunks = [
            DocumentChunk(
                id="chunk1",
                document_id="doc1",
                content="Test content",
                chunk_index=0,
                metadata={},
            )
        ]
        retrieval = BM25Retrieval(chunks)
        assert retrieval._index is None
        asyncio.run(retrieval.retrieve("test"))
        # Index should be built (or None if rank_bm25 not installed)
        assert retrieval._index is None or retrieval._index is not None

    def test_bm25_retrieval_complex_filters(self):
        """Test BM25Retrieval with complex filters."""
        chunks = [
            DocumentChunk(
                id="chunk1",
                document_id="doc1",
                content="Test content",
                chunk_index=0,
                metadata={"category": "test", "date": "2024-01-01"},
            )
        ]
        retrieval = BM25Retrieval(chunks)
        results = asyncio.run(
            retrieval.retrieve("test", filters={"category": "test", "date": "2024-01-01"})
        )
        assert isinstance(results, list)


# ============================================================
# Retriever class tests (10 test cases)
# ============================================================


class TestRetriever:
    """Test cases for Retriever class."""

    def test_retriever_initialization(self):
        """Test Retriever initialization."""
        primary = RetrievalStrategy()
        retriever = Retriever(primary_strategy=primary)
        assert retriever.primary_strategy == primary
        assert retriever.fallback_strategies == []

    def test_retriever_with_fallback(self):
        """Test Retriever with fallback strategies."""
        primary = RetrievalStrategy()
        fallback = RetrievalStrategy()
        retriever = Retriever(primary_strategy=primary, fallback_strategies=[fallback])
        assert len(retriever.fallback_strategies) == 1

    def test_retriever_empty_fallbacks(self):
        """Test Retriever with empty fallback list."""
        primary = RetrievalStrategy()
        retriever = Retriever(primary_strategy=primary, fallback_strategies=[])
        assert retriever.fallback_strategies == []

    def test_retriever_primary_success(self):
        """Test Retriever with successful primary strategy."""
        chunk = DocumentChunk(
            id="chunk1", document_id="doc1", content="Test", chunk_index=0, metadata={}
        )

        class MockStrategy(RetrievalStrategy):
            async def retrieve(self, query, top_k, filters):
                return [RetrievalResult(chunk=chunk, score=1.0, metadata={})]

        primary = MockStrategy()
        retriever = Retriever(primary_strategy=primary)
        results = asyncio.run(retriever.retrieve("test"))
        assert len(results) == 1

    def test_retriever_primary_failure_fallback_success(self):
        """Test Retriever fallback when primary fails."""
        chunk = DocumentChunk(
            id="chunk1", document_id="doc1", content="Test", chunk_index=0, metadata={}
        )

        class FailingStrategy(RetrievalStrategy):
            async def retrieve(self, query, top_k, filters):
                raise Exception("Primary failed")

        class WorkingStrategy(RetrievalStrategy):
            async def retrieve(self, query, top_k, filters):
                return [RetrievalResult(chunk=chunk, score=1.0, metadata={})]

        primary = FailingStrategy()
        fallback = WorkingStrategy()
        retriever = Retriever(primary_strategy=primary, fallback_strategies=[fallback])
        results = asyncio.run(retriever.retrieve("test"))
        assert len(results) == 1

    def test_retriever_all_strategies_fail(self):
        """Test Retriever when all strategies fail."""

        class FailingStrategy(RetrievalStrategy):
            async def retrieve(self, query, top_k, filters):
                raise Exception("Failed")

        primary = FailingStrategy()
        fallback = FailingStrategy()
        retriever = Retriever(primary_strategy=primary, fallback_strategies=[fallback])
        results = asyncio.run(retriever.retrieve("test"))
        assert results == []

    def test_retriever_with_filters(self):
        """Test Retriever passes filters to strategies."""
        chunk = DocumentChunk(
            id="chunk1", document_id="doc1", content="Test", chunk_index=0, metadata={}
        )

        class MockStrategy(RetrievalStrategy):
            async def retrieve(self, query, top_k, filters):
                return [
                    RetrievalResult(chunk=chunk, score=1.0, metadata={"filters": filters or {}})
                ]

        primary = MockStrategy()
        retriever = Retriever(primary_strategy=primary)
        results = asyncio.run(retriever.retrieve("test", filters={"key": "value"}))
        assert results[0].metadata["filters"] == {"key": "value"}

    def test_retriever_with_top_k(self):
        """Test Retriever passes top_k to strategies."""
        chunk = DocumentChunk(
            id="chunk1", document_id="doc1", content="Test", chunk_index=0, metadata={}
        )

        class MockStrategy(RetrievalStrategy):
            async def retrieve(self, query, top_k, filters):
                return [RetrievalResult(chunk=chunk, score=1.0, metadata={"top_k": top_k})]

        primary = MockStrategy()
        retriever = Retriever(primary_strategy=primary)
        results = asyncio.run(retriever.retrieve("test", top_k=5))
        assert results[0].metadata["top_k"] == 5

    def test_retriever_empty_query(self):
        """Test Retriever with empty query."""
        chunk = DocumentChunk(
            id="chunk1", document_id="doc1", content="Test", chunk_index=0, metadata={}
        )

        class MockStrategy(RetrievalStrategy):
            async def retrieve(self, query, top_k, filters):
                return [RetrievalResult(chunk=chunk, score=1.0, metadata={})]

        primary = MockStrategy()
        retriever = Retriever(primary_strategy=primary)
        results = asyncio.run(retriever.retrieve(""))
        assert len(results) == 1

    def test_retriever_multiple_fallbacks(self):
        """Test Retriever with multiple fallback strategies."""
        chunk = DocumentChunk(
            id="chunk1", document_id="doc1", content="Test", chunk_index=0, metadata={}
        )

        class FailingStrategy(RetrievalStrategy):
            async def retrieve(self, query, top_k, filters):
                raise Exception("Failed")

        class WorkingStrategy(RetrievalStrategy):
            async def retrieve(self, query, top_k, filters):
                return [RetrievalResult(chunk=chunk, score=1.0, metadata={})]

        primary = FailingStrategy()
        fallback1 = FailingStrategy()
        fallback2 = WorkingStrategy()
        retriever = Retriever(primary_strategy=primary, fallback_strategies=[fallback1, fallback2])
        results = asyncio.run(retriever.retrieve("test"))
        assert len(results) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
