# -*- coding: utf-8 -*-
"""
Tests for core/ai/rag/knowledge_base.py.
"""

from unittest.mock import AsyncMock

import pytest

from core.ai.rag.knowledge_base import KnowledgeBase
from core.ai.rag.vectorizer import DocumentChunk


@pytest.fixture
def mock_pipeline():
    pipeline = AsyncMock()

    async def vectorize(doc):
        doc.chunks = [
            DocumentChunk(
                id=f"{doc.id}_chunk_0",
                document_id=doc.id,
                content=doc.content,
                chunk_index=0,
                metadata={},
            )
        ]
        return doc

    pipeline.vectorize.side_effect = vectorize
    return pipeline


@pytest.fixture
def mock_vector_store():
    return AsyncMock()


class TestKnowledgeBase:
    @pytest.mark.asyncio
    async def test_initialization(self, mock_pipeline):
        kb = KnowledgeBase("test_kb", mock_pipeline)
        assert kb.name == "test_kb"
        assert kb.documents == {}

    @pytest.mark.asyncio
    async def test_add_document(self, mock_pipeline):
        kb = KnowledgeBase("test_kb", mock_pipeline)
        doc = await kb.add_document("doc1", "Hello world", {"source": "test"})
        assert doc.id == "doc1"
        assert "doc1" in kb.documents
        assert kb.documents["doc1"].chunks is not None

    @pytest.mark.asyncio
    async def test_add_document_with_vector_store(self, mock_pipeline, mock_vector_store):
        kb = KnowledgeBase("test_kb", mock_pipeline, vector_store_client=mock_vector_store)
        doc = await kb.add_document("doc1", "Hello world")
        assert doc.id == "doc1"
        mock_vector_store.upsert.assert_not_called()  # placeholder does not call upsert

    @pytest.mark.asyncio
    async def test_delete_document(self, mock_pipeline):
        kb = KnowledgeBase("test_kb", mock_pipeline)
        await kb.add_document("doc1", "Hello world")
        assert (await kb.delete_document("doc1")) is True
        assert (await kb.delete_document("doc1")) is False

    @pytest.mark.asyncio
    async def test_get_document(self, mock_pipeline):
        kb = KnowledgeBase("test_kb", mock_pipeline)
        await kb.add_document("doc1", "Hello world")
        assert kb.get_document("doc1") is not None
        assert kb.get_document("missing") is None

    @pytest.mark.asyncio
    async def test_list_documents(self, mock_pipeline):
        kb = KnowledgeBase("test_kb", mock_pipeline)
        await kb.add_document("doc1", "Hello world")
        await kb.add_document("doc2", "Hello again")
        docs = kb.list_documents()
        assert "doc1" in docs
        assert "doc2" in docs

    @pytest.mark.asyncio
    async def test_add_documents_batch(self, mock_pipeline):
        kb = KnowledgeBase("test_kb", mock_pipeline)
        documents = [
            {"id": "doc1", "content": "Hello world", "metadata": {"source": "test"}},
            {"id": "doc2", "content": "Hello again", "metadata": {"source": "test"}},
        ]
        results = await kb.add_documents_batch(documents)
        assert len(results) == 2
        assert "doc1" in kb.documents
        assert "doc2" in kb.documents

    @pytest.mark.asyncio
    async def test_add_documents_batch_without_metadata(self, mock_pipeline):
        kb = KnowledgeBase("test_kb", mock_pipeline)
        documents = [
            {"id": "doc1", "content": "Hello world"},
        ]
        results = await kb.add_documents_batch(documents)
        assert len(results) == 1
        assert results[0].metadata == {}
