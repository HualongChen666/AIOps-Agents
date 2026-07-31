# -*- coding: utf-8 -*-
"""
Tests for core/ai/rag/reranker.py.
"""

import pytest

pytestmark = pytest.mark.smoke
from core.ai.rag.reranker import CrossEncoderReranker, MMRReranker, Reranker, RerankingPipeline
from core.ai.rag.retriever import RetrievalResult
from core.ai.rag.vectorizer import DocumentChunk


@pytest.fixture
def retrieval_results():
    chunks = [
        DocumentChunk(id="c1", document_id="d1", content="First chunk", chunk_index=0, metadata={}),
        DocumentChunk(
            id="c2", document_id="d1", content="Second chunk", chunk_index=1, metadata={}
        ),
    ]
    return [
        RetrievalResult(chunk=chunks[0], score=0.5, metadata={}),
        RetrievalResult(chunk=chunks[1], score=0.9, metadata={}),
    ]


class TestReranker:
    @pytest.mark.asyncio
    async def test_abstract_rerank(self):
        reranker = Reranker()
        with pytest.raises(NotImplementedError):
            await reranker.rerank("query", [], 1)


class TestCrossEncoderReranker:
    @pytest.fixture
    def mock_cross_encoder(self):
        class MockCrossEncoder:
            def predict(self, pairs):
                return [0.9, 0.1]

        return MockCrossEncoder()

    @pytest.mark.asyncio
    async def test_rerank_with_model(self, retrieval_results, mock_cross_encoder):
        reranker = CrossEncoderReranker()
        reranker._model = mock_cross_encoder
        results = await reranker.rerank("query", retrieval_results, top_k=2)
        assert len(results) == 2
        # First result should now have the highest score
        assert results[0].score == pytest.approx(0.9, abs=0.01)

    @pytest.mark.asyncio
    async def test_rerank_empty_results(self):
        reranker = CrossEncoderReranker()
        results = await reranker.rerank("query", [], top_k=2)
        assert results == []

    @pytest.mark.asyncio
    async def test_rerank_model_unavailable(self, retrieval_results, monkeypatch):
        # Ensure CrossEncoder raises ImportError
        try:
            import sentence_transformers
        except ImportError:
            pass
        else:

            class _Failing:
                def __init__(self, *args, **kwargs):
                    raise ImportError("not available")

            monkeypatch.setattr(sentence_transformers, "CrossEncoder", _Failing)

        reranker = CrossEncoderReranker()
        results = await reranker.rerank("query", retrieval_results, top_k=2)
        assert len(results) == 2

    def test_initialization(self):
        reranker = CrossEncoderReranker("cross-encoder/test", "cpu")
        assert reranker.model_name == "cross-encoder/test"
        assert reranker.device == "cpu"
        assert reranker._model is None


class TestMMRReranker:
    @pytest.fixture
    def mmr_results(self):
        chunks = [
            DocumentChunk(id="c1", document_id="d1", content="A", chunk_index=0, metadata={}),
            DocumentChunk(id="c2", document_id="d1", content="B", chunk_index=1, metadata={}),
            DocumentChunk(id="c3", document_id="d1", content="C", chunk_index=2, metadata={}),
        ]
        return [
            RetrievalResult(chunk=chunks[0], score=0.9, metadata={}),
            RetrievalResult(chunk=chunks[1], score=0.8, metadata={}),
            RetrievalResult(chunk=chunks[2], score=0.7, metadata={}),
        ]

    @pytest.mark.asyncio
    async def test_mmr_rerank(self, mmr_results):
        reranker = MMRReranker(lambda_param=0.5)
        results = await reranker.rerank("query", mmr_results, top_k=2)
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_mmr_empty_results(self):
        reranker = MMRReranker()
        results = await reranker.rerank("query", [], top_k=2)
        assert results == []

    @pytest.mark.asyncio
    async def test_mmr_top_k_one(self, mmr_results):
        reranker = MMRReranker(lambda_param=1.0)
        results = await reranker.rerank("query", mmr_results, top_k=1)
        assert len(results) == 1
        assert results[0].score == pytest.approx(0.9, abs=0.01)

    def test_compute_similarity_with_embeddings(self):
        chunk1 = DocumentChunk(
            id="c1",
            document_id="d1",
            content="A",
            chunk_index=0,
            metadata={},
            embedding=[1.0, 0.0, 0.0],
        )
        chunk2 = DocumentChunk(
            id="c2",
            document_id="d1",
            content="B",
            chunk_index=1,
            metadata={},
            embedding=[0.0, 1.0, 0.0],
        )
        reranker = MMRReranker()
        similarity = reranker._compute_similarity(chunk1, chunk2)
        assert similarity == pytest.approx(0.0, abs=0.01)

    def test_compute_similarity_without_embeddings(self):
        chunk1 = DocumentChunk(id="c1", document_id="d1", content="A", chunk_index=0, metadata={})
        chunk2 = DocumentChunk(id="c2", document_id="d1", content="B", chunk_index=1, metadata={})
        reranker = MMRReranker()
        assert reranker._compute_similarity(chunk1, chunk2) == 0.0


class TestRerankingPipeline:
    @pytest.mark.asyncio
    async def test_pipeline(self, retrieval_results):
        reranker1 = MMRReranker()
        reranker2 = MMRReranker()
        pipeline = RerankingPipeline([reranker1, reranker2])
        results = await pipeline.rerank("query", retrieval_results, top_k=2)
        assert len(results) <= 2

    @pytest.mark.asyncio
    async def test_pipeline_empty_rerankers(self, retrieval_results):
        pipeline = RerankingPipeline([])
        results = await pipeline.rerank("query", retrieval_results, top_k=2)
        assert len(results) == 2
