# -*- coding: utf-8 -*-
"""
Document Vectorization Pipeline
Handles document chunking and vector embedding generation
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from loguru import logger


@dataclass
class Document:
    """Document representation"""

    id: str
    content: str
    metadata: Dict[str, Any]
    embedding: Optional[List[float]] = None
    chunks: Optional[List["DocumentChunk"]] = None


@dataclass
class DocumentChunk:
    """Document chunk representation"""

    id: str
    document_id: str
    content: str
    chunk_index: int
    metadata: Dict[str, Any]
    embedding: Optional[List[float]] = None


class ChunkingStrategy:
    """Base class for chunking strategies"""

    def chunk(self, document: Document) -> List[DocumentChunk]:
        """Split document into chunks"""
        raise NotImplementedError


class FixedSizeChunking(ChunkingStrategy):
    """Fixed-size chunking strategy"""

    def __init__(self, chunk_size: int = 500, overlap: int = 50):
        """
        Initialize fixed-size chunking

        Args:
            chunk_size: Size of each chunk in characters
            overlap: Overlap between chunks in characters
        """
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, document: Document) -> List[DocumentChunk]:
        """Split document into fixed-size chunks"""
        chunks = []
        content = document.content
        start = 0

        chunk_index = 0
        while start < len(content):
            end = start + self.chunk_size
            chunk_content = content[start:end]

            chunk = DocumentChunk(
                id=f"{document.id}_chunk_{chunk_index}",
                document_id=document.id,
                content=chunk_content,
                chunk_index=chunk_index,
                metadata={**document.metadata, "chunk_start": start, "chunk_end": end},
            )
            chunks.append(chunk)

            start = end - self.overlap
            chunk_index += 1

        return chunks


class SemanticChunking(ChunkingStrategy):
    """Semantic-aware chunking strategy"""

    def __init__(self, max_chunk_size: int = 1000):
        """
        Initialize semantic chunking

        Args:
            max_chunk_size: Maximum chunk size
        """
        self.max_chunk_size = max_chunk_size

    def chunk(self, document: Document) -> List[DocumentChunk]:
        """Split document semantically (by paragraphs/sentences)"""
        chunks = []

        # Split by paragraphs first
        paragraphs = document.content.split("\n\n")

        current_chunk = ""
        chunk_index = 0

        for para in paragraphs:
            if len(current_chunk) + len(para) > self.max_chunk_size:
                if current_chunk:
                    chunk = DocumentChunk(
                        id=f"{document.id}_chunk_{chunk_index}",
                        document_id=document.id,
                        content=current_chunk.strip(),
                        chunk_index=chunk_index,
                        metadata={**document.metadata},
                    )
                    chunks.append(chunk)
                    chunk_index += 1
                    current_chunk = para
                else:
                    # Single paragraph exceeds max size, split it
                    current_chunk = para
            else:
                current_chunk += "\n\n" + para if current_chunk else para

        # Add final chunk
        if current_chunk:
            chunk = DocumentChunk(
                id=f"{document.id}_chunk_{chunk_index}",
                document_id=document.id,
                content=current_chunk.strip(),
                chunk_index=chunk_index,
                metadata={**document.metadata},
            )
            chunks.append(chunk)

        return chunks


class EmbeddingModel:
    """Base embedding model interface"""

    async def embed(self, text: str) -> List[float]:
        """Generate embedding for text"""
        raise NotImplementedError

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for batch of texts"""
        embeddings = []
        for text in texts:
            embedding = await self.embed(text)
            embeddings.append(embedding)
        return embeddings


class SentenceTransformerEmbedding(EmbeddingModel):
    """Sentence Transformer embedding model"""

    # Expected dimensions for common models; used as a fallback when the model is unavailable
    _DIMENSIONS: Dict[str, int] = {
        "BAAI/bge-large-zh-v1.5": 1024,
        "BAAI/bge-large-zh": 1024,
        "intfloat/multilingual-e5-large": 1024,
        "sentence-transformers/all-MiniLM-L6-v2": 384,
        "all-MiniLM-L6-v2": 384,
    }

    def __init__(self, model_name: str = "BAAI/bge-large-zh-v1.5"):
        """
        Initialize sentence transformer

        Args:
            model_name: Model name (defaults to Chinese/ops-oriented BGE model)
        """
        self.model_name = model_name
        self._model = None

    def _fallback_dimension(self) -> int:
        """Return the expected embedding dimension for the configured model."""
        return self._DIMENSIONS.get(self.model_name, 1024)

    def _load_model(self):
        """Load model lazily"""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer

                self._model = SentenceTransformer(self.model_name)
                logger.info(f"Loaded sentence transformer: {self.model_name}")
            except ImportError:
                logger.warning("sentence-transformers not available")

    async def embed(self, text: str) -> List[float]:
        """Generate embedding using sentence transformer"""
        try:
            self._load_model()
            if self._model is None:
                # Fallback to a zero vector matching the expected model dimension
                return [0.0] * self._fallback_dimension()

            embedding = self._model.encode(text)
            return embedding.tolist()

        except Exception as e:
            logger.error(f"Sentence transformer embedding failed: {e}")
            raise

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for batch"""
        try:
            self._load_model()
            if self._model is None:
                dim = self._fallback_dimension()
                return [[0.0] * dim for _ in texts]

            embeddings = self._model.encode(texts)
            return [emb.tolist() for emb in embeddings]

        except Exception as e:
            logger.error(f"Batch embedding failed: {e}")
            raise


class VectorizationPipeline:
    """
    Pipeline for vectorizing documents
    """

    def __init__(
        self,
        chunking_strategy: ChunkingStrategy,
        embedding_model: EmbeddingModel,
        batch_size: int = 32,
    ):
        """
        Initialize vectorization pipeline

        Args:
            chunking_strategy: Chunking strategy to use
            embedding_model: Embedding model
            batch_size: Batch size for embedding
        """
        self.chunking_strategy = chunking_strategy
        self.embedding_model = embedding_model
        self.batch_size = batch_size

    async def vectorize(self, document: Document) -> Document:
        """
        Vectorize a document

        Args:
            document: Document to vectorize

        Returns:
            Document with embeddings
        """
        # Chunk document
        chunks = self.chunking_strategy.chunk(document)
        document.chunks = chunks

        # Generate embeddings for chunks
        chunk_texts = [chunk.content for chunk in chunks]
        embeddings = await self.embedding_model.embed_batch(chunk_texts)

        # Assign embeddings to chunks
        for chunk, embedding in zip(chunks, embeddings):
            chunk.embedding = embedding

        logger.info(f"Vectorized document {document.id} into {len(chunks)} chunks")
        return document

    async def vectorize_batch(self, documents: List[Document]) -> List[Document]:
        """
        Vectorize batch of documents

        Args:
            documents: Documents to vectorize

        Returns:
            Vectorized documents
        """
        results = []
        for document in documents:
            vectorized = await self.vectorize(document)
            results.append(vectorized)
        return results
