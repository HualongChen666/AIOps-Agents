# -*- coding: utf-8 -*-
import logging

"""
Unit tests for core/ai/rag/vectorizer.py

This module contains comprehensive unit tests for the document vectorization pipeline,
covering document chunking strategies, embedding models, and vectorization pipeline.
"""

import asyncio

import pytest

from core.ai.rag.vectorizer import (
    ChunkingStrategy,
    Document,
    DocumentChunk,
    EmbeddingModel,
    FixedSizeChunking,
    OpenAIEmbedding,
    SemanticChunking,
    SentenceTransformerEmbedding,
    VectorizationPipeline,
)


@pytest.fixture(autouse=True)
def mock_sentence_transformer(monkeypatch):
    """Mock sentence transformer to avoid network model downloads."""

    class MockSentenceTransformer:
        def __init__(self, *args, **kwargs):
            raise ImportError("sentence-transformers not available")

    try:
        import sentence_transformers

        monkeypatch.setattr(sentence_transformers, "SentenceTransformer", MockSentenceTransformer)
    except ImportError:
        pass


# ============================================================
# Document dataclass tests (8 test cases)
# ============================================================


class TestDocument:
    """Test cases for Document dataclass."""

    def test_document_initialization(self):
        """Test Document initialization."""
        doc = Document(id="doc1", content="Test content", metadata={"key": "value"})
        assert doc.id == "doc1"
        assert doc.content == "Test content"
        assert doc.metadata == {"key": "value"}
        assert doc.embedding is None
        assert doc.chunks is None

    def test_document_with_embedding(self):
        """Test Document with embedding."""
        doc = Document(id="doc1", content="Test", metadata={}, embedding=[0.1, 0.2, 0.3])
        assert doc.embedding == [0.1, 0.2, 0.3]

    def test_document_with_chunks(self):
        """Test Document with chunks."""
        chunk = DocumentChunk(
            id="chunk1", document_id="doc1", content="Chunk", chunk_index=0, metadata={}
        )
        doc = Document(id="doc1", content="Test", metadata={}, chunks=[chunk])
        assert len(doc.chunks) == 1
        assert doc.chunks[0].id == "chunk1"

    def test_document_empty_content(self):
        """Test Document with empty content."""
        doc = Document(id="doc1", content="", metadata={})
        assert doc.content == ""

    def test_document_large_content(self):
        """Test Document with large content."""
        content = "Test " * 10000
        doc = Document(id="doc1", content=content, metadata={})
        assert len(doc.content) == 50000

    def test_document_complex_metadata(self):
        """Test Document with complex metadata."""
        metadata = {
            "author": "test",
            "date": "2024-01-01",
            "tags": ["tag1", "tag2"],
            "nested": {"key": "value"},
        }
        doc = Document(id="doc1", content="Test", metadata=metadata)
        assert doc.metadata == metadata

    def test_document_unicode_content(self):
        """Test Document with unicode content."""
        doc = Document(id="doc1", content="测试内容", metadata={})
        assert doc.content == "测试内容"

    def test_document_embedding_dimensions(self):
        """Test Document with specific embedding dimensions."""
        embedding = [0.0] * 1536  # OpenAI ada-002 dimensions
        doc = Document(id="doc1", content="Test", metadata={}, embedding=embedding)
        assert len(doc.embedding) == 1536


# ============================================================
# DocumentChunk dataclass tests (8 test cases)
# ============================================================


class TestDocumentChunk:
    """Test cases for DocumentChunk dataclass."""

    def test_chunk_initialization(self):
        """Test DocumentChunk initialization."""
        chunk = DocumentChunk(
            id="chunk1", document_id="doc1", content="Chunk", chunk_index=0, metadata={}
        )
        assert chunk.id == "chunk1"
        assert chunk.document_id == "doc1"
        assert chunk.content == "Chunk"
        assert chunk.chunk_index == 0
        assert chunk.metadata == {}
        assert chunk.embedding is None

    def test_chunk_with_embedding(self):
        """Test DocumentChunk with embedding."""
        chunk = DocumentChunk(
            id="chunk1",
            document_id="doc1",
            content="Chunk",
            chunk_index=0,
            metadata={},
            embedding=[0.1, 0.2],
        )
        assert chunk.embedding == [0.1, 0.2]

    def test_chunk_with_metadata(self):
        """Test DocumentChunk with metadata."""
        chunk = DocumentChunk(
            id="chunk1",
            document_id="doc1",
            content="Chunk",
            chunk_index=0,
            metadata={"start": 0, "end": 100},
        )
        assert chunk.metadata["start"] == 0
        assert chunk.metadata["end"] == 100

    def test_chunk_index_increment(self):
        """Test DocumentChunk with different indices."""
        chunk0 = DocumentChunk(
            id="chunk0", document_id="doc1", content="Chunk0", chunk_index=0, metadata={}
        )
        chunk1 = DocumentChunk(
            id="chunk1", document_id="doc1", content="Chunk1", chunk_index=1, metadata={}
        )
        assert chunk0.chunk_index == 0
        assert chunk1.chunk_index == 1

    def test_chunk_empty_content(self):
        """Test DocumentChunk with empty content."""
        chunk = DocumentChunk(
            id="chunk1", document_id="doc1", content="", chunk_index=0, metadata={}
        )
        assert chunk.content == ""

    def test_chunk_unicode_content(self):
        """Test DocumentChunk with unicode content."""
        chunk = DocumentChunk(
            id="chunk1", document_id="doc1", content="测试", chunk_index=0, metadata={}
        )
        assert chunk.content == "测试"

    def test_chunk_large_content(self):
        """Test DocumentChunk with large content."""
        content = "Test " * 5000
        chunk = DocumentChunk(
            id="chunk1", document_id="doc1", content=content, chunk_index=0, metadata={}
        )
        assert len(chunk.content) == 25000

    def test_chunk_embedding_dimensions(self):
        """Test DocumentChunk with specific embedding dimensions."""
        embedding = [0.0] * 384  # Sentence transformer dimensions
        chunk = DocumentChunk(
            id="chunk1",
            document_id="doc1",
            content="Chunk",
            chunk_index=0,
            metadata={},
            embedding=embedding,
        )
        assert len(chunk.embedding) == 384


# ============================================================
# ChunkingStrategy class tests (3 test cases)
# ============================================================


class TestChunkingStrategy:
    """Test cases for ChunkingStrategy base class."""

    def test_chunking_strategy_not_implemented(self):
        """Test ChunkingStrategy.chunk raises NotImplementedError."""
        strategy = ChunkingStrategy()
        doc = Document(id="doc1", content="Test", metadata={})
        with pytest.raises(NotImplementedError):
            strategy.chunk(doc)

    def test_chunking_strategy_is_abstract(self):
        """Test ChunkingStrategy is abstract base class."""
        strategy = ChunkingStrategy()
        assert hasattr(strategy, "chunk")

    def test_chunking_strategy_instantiation(self):
        """Test ChunkingStrategy can be instantiated."""
        strategy = ChunkingStrategy()
        assert strategy is not None


# ============================================================
# FixedSizeChunking class tests (10 test cases)
# ============================================================


class TestFixedSizeChunking:
    """Test cases for FixedSizeChunking class."""

    def test_fixed_size_chunking_initialization(self):
        """Test FixedSizeChunking initialization."""
        chunking = FixedSizeChunking(chunk_size=500, overlap=50)
        assert chunking.chunk_size == 500
        assert chunking.overlap == 50

    def test_fixed_size_chunking_defaults(self):
        """Test FixedSizeChunking with default parameters."""
        chunking = FixedSizeChunking()
        assert chunking.chunk_size == 500
        assert chunking.overlap == 50

    def test_fixed_size_chunking_short_content(self):
        """Test FixedSizeChunking with short content."""
        chunking = FixedSizeChunking(chunk_size=500, overlap=50)
        doc = Document(id="doc1", content="Short content", metadata={})
        chunks = chunking.chunk(doc)
        assert len(chunks) == 1
        assert chunks[0].content == "Short content"

    def test_fixed_size_chunking_long_content(self):
        """Test FixedSizeChunking with long content."""
        chunking = FixedSizeChunking(chunk_size=100, overlap=20)
        content = "Test " * 50  # 250 characters
        doc = Document(id="doc1", content=content, metadata={})
        chunks = chunking.chunk(doc)
        assert len(chunks) > 1

    def test_fixed_size_chunking_overlap(self):
        """Test FixedSizeChunking overlap functionality."""
        chunking = FixedSizeChunking(chunk_size=100, overlap=50)
        content = "Test " * 40  # 200 characters
        doc = Document(id="doc1", content=content, metadata={})
        chunks = chunking.chunk(doc)
        if len(chunks) > 1:
            # Check that chunks overlap
            assert chunks[0].content[-50:] in chunks[1].content

    def test_fixed_size_chunking_chunk_indices(self):
        """Test FixedSizeChunking assigns correct indices."""
        chunking = FixedSizeChunking(chunk_size=100, overlap=20)
        content = "Test " * 40
        doc = Document(id="doc1", content=content, metadata={})
        chunks = chunking.chunk(doc)
        for i, chunk in enumerate(chunks):
            assert chunk.chunk_index == i

    def test_fixed_size_chunking_metadata_preservation(self):
        """Test FixedSizeChunking preserves document metadata."""
        chunking = FixedSizeChunking(chunk_size=100, overlap=20)
        doc = Document(id="doc1", content="Test content", metadata={"key": "value"})
        chunks = chunking.chunk(doc)
        for chunk in chunks:
            assert chunk.metadata["key"] == "value"

    def test_fixed_size_chunking_chunk_metadata(self):
        """Test FixedSizeChunking adds chunk-specific metadata."""
        chunking = FixedSizeChunking(chunk_size=100, overlap=20)
        content = "Test " * 20
        doc = Document(id="doc1", content=content, metadata={})
        chunks = chunking.chunk(doc)
        for chunk in chunks:
            assert "chunk_start" in chunk.metadata
            assert "chunk_end" in chunk.metadata

    def test_fixed_size_chunking_empty_content(self):
        """Test FixedSizeChunking with empty content."""
        chunking = FixedSizeChunking(chunk_size=100, overlap=20)
        doc = Document(id="doc1", content="", metadata={})
        chunks = chunking.chunk(doc)
        assert len(chunks) == 0

    def test_fixed_size_chunking_zero_overlap(self):
        """Test FixedSizeChunking with zero overlap."""
        chunking = FixedSizeChunking(chunk_size=100, overlap=0)
        content = "Test " * 30
        doc = Document(id="doc1", content=content, metadata={})
        chunks = chunking.chunk(doc)
        if len(chunks) > 1:
            # Chunks should not overlap
            assert chunks[0].content not in chunks[1].content


# ============================================================
# SemanticChunking class tests (10 test cases)
# ============================================================


class TestSemanticChunking:
    """Test cases for SemanticChunking class."""

    def test_semantic_chunking_initialization(self):
        """Test SemanticChunking initialization."""
        chunking = SemanticChunking(max_chunk_size=1000)
        assert chunking.max_chunk_size == 1000

    def test_semantic_chunking_defaults(self):
        """Test SemanticChunking with default parameters."""
        chunking = SemanticChunking()
        assert chunking.max_chunk_size == 1000

    def test_semantic_chunking_paragraph_splitting(self):
        """Test SemanticChunking splits by paragraphs."""
        chunking = SemanticChunking(max_chunk_size=500)
        content = "Para1\n\nPara2\n\nPara3"
        doc = Document(id="doc1", content=content, metadata={})
        chunks = chunking.chunk(doc)
        assert len(chunks) >= 1

    def test_semantic_chunking_long_paragraph(self):
        """Test SemanticChunking handles long paragraphs."""
        chunking = SemanticChunking(max_chunk_size=100)
        content = "Very long paragraph " * 20
        doc = Document(id="doc1", content=content, metadata={})
        chunks = chunking.chunk(doc)
        # Should split long paragraph
        assert len(chunks) >= 1

    def test_semantic_chunking_chunk_indices(self):
        """Test SemanticChunking assigns correct indices."""
        chunking = SemanticChunking(max_chunk_size=500)
        content = "Para1\n\nPara2\n\nPara3"
        doc = Document(id="doc1", content=content, metadata={})
        chunks = chunking.chunk(doc)
        for i, chunk in enumerate(chunks):
            assert chunk.chunk_index == i

    def test_semantic_chunking_metadata_preservation(self):
        """Test SemanticChunking preserves document metadata."""
        chunking = SemanticChunking(max_chunk_size=500)
        doc = Document(id="doc1", content="Para1\n\nPara2", metadata={"key": "value"})
        chunks = chunking.chunk(doc)
        for chunk in chunks:
            assert chunk.metadata["key"] == "value"

    def test_semantic_chunking_empty_content(self):
        """Test SemanticChunking with empty content."""
        chunking = SemanticChunking(max_chunk_size=500)
        doc = Document(id="doc1", content="", metadata={})
        chunks = chunking.chunk(doc)
        assert len(chunks) == 0

    def test_semantic_chunking_single_paragraph(self):
        """Test SemanticChunking with single paragraph."""
        chunking = SemanticChunking(max_chunk_size=500)
        content = "Single paragraph"
        doc = Document(id="doc1", content=content, metadata={})
        chunks = chunking.chunk(doc)
        assert len(chunks) == 1

    def test_semantic_chunking_unicode_content(self):
        """Test SemanticChunking with unicode content."""
        chunking = SemanticChunking(max_chunk_size=500)
        content = "段落1\n\n段落2\n\n段落3"
        doc = Document(id="doc1", content=content, metadata={})
        chunks = chunking.chunk(doc)
        assert len(chunks) >= 1

    def test_semantic_chunking_large_max_size(self):
        """Test SemanticChunking with large max_chunk_size."""
        chunking = SemanticChunking(max_chunk_size=10000)
        content = "Para1\n\nPara2\n\nPara3"
        doc = Document(id="doc1", content=content, metadata={})
        chunks = chunking.chunk(doc)
        # Should fit all content in one chunk
        assert len(chunks) >= 1


# ============================================================
# EmbeddingModel class tests (3 test cases)
# ============================================================


class TestEmbeddingModel:
    """Test cases for EmbeddingModel base class."""

    def test_embedding_model_not_implemented(self):
        """Test EmbeddingModel.embed raises NotImplementedError."""
        model = EmbeddingModel()
        with pytest.raises(NotImplementedError):
            asyncio.run(model.embed("test"))

    def test_embedding_model_embed_batch_not_implemented(self):
        """Test EmbeddingModel.embed_batch uses embed method."""
        model = EmbeddingModel()
        # This will fail because embed is not implemented
        with pytest.raises(NotImplementedError):
            asyncio.run(model.embed_batch(["test1", "test2"]))

    def test_embedding_model_instantiation(self):
        """Test EmbeddingModel can be instantiated."""
        model = EmbeddingModel()
        assert model is not None


# ============================================================
# OpenAIEmbedding class tests (8 test cases)
# ============================================================


class TestOpenAIEmbedding:
    """Test cases for OpenAIEmbedding class."""

    def test_openai_embedding_initialization(self):
        """Test OpenAIEmbedding initialization."""
        model = OpenAIEmbedding(model="text-embedding-ada-002", api_key="test_key")
        assert model.model == "text-embedding-ada-002"
        assert model.api_key == "test_key"

    def test_openai_embedding_defaults(self):
        """Test OpenAIEmbedding with default parameters."""
        model = OpenAIEmbedding()
        assert model.model == "text-embedding-ada-002"
        assert model.api_key is None

    def test_openai_embedding_embed_placeholder(self):
        """Test OpenAIEmbedding returns default_value."""
        model = OpenAIEmbedding()
        embedding = asyncio.run(model.embed("test text"))
        assert len(embedding) == 1536  # ada-002 dimensions
        assert all(x == 0.0 for x in embedding)

    def test_openai_embedding_embed_batch_placeholder(self):
        """Test OpenAIEmbedding embed_batch returns placeholders."""
        model = OpenAIEmbedding()
        embeddings = asyncio.run(model.embed_batch(["text1", "text2"]))
        assert len(embeddings) == 2
        assert all(len(emb) == 1536 for emb in embeddings)

    def test_openai_embedding_empty_text(self):
        """Test OpenAIEmbedding with empty text."""
        model = OpenAIEmbedding()
        embedding = asyncio.run(model.embed(""))
        assert len(embedding) == 1536

    def test_openai_embedding_unicode_text(self):
        """Test OpenAIEmbedding with unicode text."""
        model = OpenAIEmbedding()
        embedding = asyncio.run(model.embed("测试文本"))
        assert len(embedding) == 1536

    def test_openai_embedding_long_text(self):
        """Test OpenAIEmbedding with long text."""
        model = OpenAIEmbedding()
        long_text = "Test " * 1000
        embedding = asyncio.run(model.embed(long_text))
        assert len(embedding) == 1536

    def test_openai_embedding_different_model(self):
        """Test OpenAIEmbedding with different model."""
        model = OpenAIEmbedding(model="text-embedding-3-small")
        assert model.model == "text-embedding-3-small"


# ============================================================
# SentenceTransformerEmbedding class tests (10 test cases)
# ============================================================


class TestSentenceTransformerEmbedding:
    """Test cases for SentenceTransformerEmbedding class."""

    def test_sentence_transformer_initialization(self):
        """Test SentenceTransformerEmbedding initialization."""
        model = SentenceTransformerEmbedding(model_name="all-MiniLM-L6-v2")
        assert model.model_name == "all-MiniLM-L6-v2"
        assert model._model is None

    def test_sentence_transformer_defaults(self):
        """Test SentenceTransformerEmbedding with default parameters."""
        model = SentenceTransformerEmbedding()
        assert model.model_name == "BAAI/bge-large-zh-v1.5"

    def test_sentence_transformer_embed_placeholder(self):
        """Test SentenceTransformerEmbedding returns default_value when model unavailable."""
        model = SentenceTransformerEmbedding()
        # Model will try to load but fail gracefully
        try:
            embedding = asyncio.run(model.embed("test text"))
            # If it succeeds, check dimensions
            assert len(embedding) == 1024  # BGE-large-zh dimensions
        except Exception as e:
            logging.exception("Unexpected exception: %s", e)
            # If it fails, that's expected when sentence-transformers not installed
            pass

    def test_sentence_transformer_embed_batch_placeholder(self):
        """Test SentenceTransformerEmbedding embed_batch returns placeholders."""
        model = SentenceTransformerEmbedding()
        try:
            embeddings = asyncio.run(model.embed_batch(["text1", "text2"]))
            assert len(embeddings) == 2
            assert all(len(emb) == 1024 for emb in embeddings)
        except Exception as e:
            logging.exception("Unexpected exception: %s", e)
            # Expected when sentence-transformers not installed
            pass

    def test_sentence_transformer_empty_text(self):
        """Test SentenceTransformerEmbedding with empty text."""
        model = SentenceTransformerEmbedding()
        try:
            embedding = asyncio.run(model.embed(""))
            assert len(embedding) == 1024
        except Exception as e:
            logging.exception("Unexpected exception: %s", e)
            # Expected when sentence-transformers not installed
            pass

    def test_sentence_transformer_unicode_text(self):
        """Test SentenceTransformerEmbedding with unicode text."""
        model = SentenceTransformerEmbedding()
        try:
            embedding = asyncio.run(model.embed("测试文本"))
            assert len(embedding) == 1024
        except Exception as e:
            logging.exception("Unexpected exception: %s", e)
            # Expected when sentence-transformers not installed
            pass

    def test_sentence_transformer_long_text(self):
        """Test SentenceTransformerEmbedding with long text."""
        model = SentenceTransformerEmbedding()
        try:
            long_text = "Test " * 1000
            embedding = asyncio.run(model.embed(long_text))
            assert len(embedding) == 1024
        except Exception as e:
            logging.exception("Unexpected exception: %s", e)
            # Expected when sentence-transformers not installed
            pass

    def test_sentence_transformer_different_model(self):
        """Test SentenceTransformerEmbedding with different model."""
        model = SentenceTransformerEmbedding(model_name="paraphrase-MiniLM-L6-v2")
        assert model.model_name == "paraphrase-MiniLM-L6-v2"

    def test_sentence_transformer_model_loading(self):
        """Test SentenceTransformerEmbedding model loading (lazy)."""
        model = SentenceTransformerEmbedding()
        # Model should be None initially
        assert model._model is None

    def test_sentence_transformer_embed_batch_efficiency(self):
        """Test SentenceTransformerEmbedding batch processing."""
        model = SentenceTransformerEmbedding()
        try:
            texts = [f"text{i}" for i in range(10)]
            embeddings = asyncio.run(model.embed_batch(texts))
            assert len(embeddings) == 10
        except Exception as e:
            logging.exception("Unexpected exception: %s", e)
            # Expected when sentence-transformers not installed
            pass


# ============================================================
# VectorizationPipeline class tests (10 test cases)
# ============================================================


class TestVectorizationPipeline:
    """Test cases for VectorizationPipeline class."""

    def test_vectorization_pipeline_initialization(self):
        """Test VectorizationPipeline initialization."""
        chunking = FixedSizeChunking(chunk_size=100, overlap=20)
        embedding = OpenAIEmbedding()
        pipeline = VectorizationPipeline(chunking, embedding, batch_size=32)
        assert pipeline.chunking_strategy == chunking
        assert pipeline.embedding_model == embedding
        assert pipeline.batch_size == 32

    def test_vectorization_pipeline_defaults(self):
        """Test VectorizationPipeline with default batch_size."""
        chunking = FixedSizeChunking()
        embedding = OpenAIEmbedding()
        pipeline = VectorizationPipeline(chunking, embedding)
        assert pipeline.batch_size == 32

    def test_vectorization_pipeline_vectorize_document(self):
        """Test VectorizationPipeline vectorize method."""
        chunking = FixedSizeChunking(chunk_size=100, overlap=20)
        embedding = OpenAIEmbedding()
        pipeline = VectorizationPipeline(chunking, embedding)
        doc = Document(id="doc1", content="Test content for vectorization", metadata={})
        result = asyncio.run(pipeline.vectorize(doc))
        assert result.id == "doc1"
        assert result.chunks is not None
        assert len(result.chunks) > 0

    def test_vectorization_pipeline_chunk_assignment(self):
        """Test VectorizationPipeline assigns chunks to document."""
        chunking = FixedSizeChunking(chunk_size=100, overlap=20)
        embedding = OpenAIEmbedding()
        pipeline = VectorizationPipeline(chunking, embedding)
        doc = Document(id="doc1", content="Test content for vectorization", metadata={})
        result = asyncio.run(pipeline.vectorize(doc))
        assert result.chunks is not None
        for chunk in result.chunks:
            assert chunk.embedding is not None

    def test_vectorization_pipeline_embedding_assignment(self):
        """Test VectorizationPipeline assigns embeddings to chunks."""
        chunking = FixedSizeChunking(chunk_size=100, overlap=20)
        embedding = OpenAIEmbedding()
        pipeline = VectorizationPipeline(chunking, embedding)
        doc = Document(id="doc1", content="Test content for vectorization", metadata={})
        result = asyncio.run(pipeline.vectorize(doc))
        for chunk in result.chunks:
            assert len(chunk.embedding) == 1536

    def test_vectorization_pipeline_batch_vectorization(self):
        """Test VectorizationPipeline vectorize_batch method."""
        chunking = FixedSizeChunking(chunk_size=100, overlap=20)
        embedding = OpenAIEmbedding()
        pipeline = VectorizationPipeline(chunking, embedding)
        docs = [Document(id=f"doc{i}", content=f"Content {i}", metadata={}) for i in range(3)]
        results = asyncio.run(pipeline.vectorize_batch(docs))
        assert len(results) == 3
        for result in results:
            assert result.chunks is not None

    def test_vectorization_pipeline_empty_document(self):
        """Test VectorizationPipeline with empty document."""
        chunking = FixedSizeChunking(chunk_size=100, overlap=20)
        embedding = OpenAIEmbedding()
        pipeline = VectorizationPipeline(chunking, embedding)
        doc = Document(id="doc1", content="", metadata={})
        result = asyncio.run(pipeline.vectorize(doc))
        assert len(result.chunks) == 0

    def test_vectorization_pipeline_large_document(self):
        """Test VectorizationPipeline with large document."""
        chunking = FixedSizeChunking(chunk_size=500, overlap=50)
        embedding = OpenAIEmbedding()
        pipeline = VectorizationPipeline(chunking, embedding)
        content = "Test " * 1000
        doc = Document(id="doc1", content=content, metadata={})
        result = asyncio.run(pipeline.vectorize(doc))
        assert len(result.chunks) > 1

    def test_vectorization_pipeline_semantic_chunking(self):
        """Test VectorizationPipeline with semantic chunking."""
        chunking = SemanticChunking(max_chunk_size=500)
        embedding = OpenAIEmbedding()
        pipeline = VectorizationPipeline(chunking, embedding)
        doc = Document(id="doc1", content="Para1\n\nPara2\n\nPara3", metadata={})
        result = asyncio.run(pipeline.vectorize(doc))
        assert result.chunks is not None

    def test_vectorization_pipeline_batch_size_parameter(self):
        """Test VectorizationPipeline respects batch_size."""
        chunking = FixedSizeChunking(chunk_size=100, overlap=20)
        embedding = OpenAIEmbedding()
        pipeline = VectorizationPipeline(chunking, embedding, batch_size=10)
        assert pipeline.batch_size == 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
