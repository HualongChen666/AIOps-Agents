# -*- coding: utf-8 -*-
"""
L2 Analysis Layer - RAG (Retrieval-Augmented Generation) Engine
Provides knowledge retrieval and context-aware analysis using vector database
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger

# Qdrant client for vector storage
try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import (
        Distance,
        FieldCondition,
        Filter,
        MatchValue,
        PointStruct,
        VectorParams,
    )

    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False
    logger.warning("Qdrant client not available - RAG will use fallback")

# Sentence transformers for embeddings
try:
    from sentence_transformers import SentenceTransformer

    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logger.warning("Sentence transformers not available - RAG will use fallback")


class RAGEngine:
    """
    RAG engine for knowledge retrieval and context-aware analysis

    This engine provides:
    - Vector-based knowledge retrieval from Qdrant
    - Semantic search using sentence transformers
    - Context augmentation for AI analysis
    - Knowledge base management
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        config = config or {}
        self.config = config

        self.qdrant_host = config.get("qdrant_host", "localhost")
        self.qdrant_port = config.get("qdrant_port", 6333)
        self.collection_name = config.get("collection_name", "aiops_knowledge")
        self.embedding_model = config.get("embedding_model", "all-MiniLM-L6-v2")

        self.qdrant_client: Optional[QdrantClient] = None
        self.embedding_model_instance: Optional[SentenceTransformer] = None
        self._is_initialized = False

        self._initialize()

    def _initialize(self) -> None:
        """Initialize RAG engine components (embedding model is loaded lazily)."""
        try:
            # Initialize Qdrant client - make it optional
            if QDRANT_AVAILABLE:
                try:
                    self.qdrant_client = QdrantClient(host=self.qdrant_host, port=self.qdrant_port)
                    logger.info(f"Qdrant client initialized: {self.qdrant_host}:{self.qdrant_port}")
                except Exception as e:
                    logger.warning(f"Failed to initialize Qdrant client: {e}")
                    self.qdrant_client = None

            # Embedding model is loaded on first use so that startup does not block
            # on network downloads when the model is not cached locally.
            if SENTENCE_TRANSFORMERS_AVAILABLE:
                try:
                    self._load_embedding_model()
                except Exception as e:
                    logger.warning(f"Failed to load embedding model: {e}")
                    self.embedding_model_instance = None

            # Create collection if it doesn't exist - make it optional
            if self.qdrant_client:
                try:
                    self._ensure_collection()
                except Exception as e:
                    logger.warning(f"Failed to ensure Qdrant collection: {e}")
                    self.qdrant_client = None

            self._is_initialized = True
            logger.info("RAG engine initialized successfully")

        except Exception as e:
            logger.warning(f"Failed to initialize RAG engine: {e}")
            self._is_initialized = False

    def _load_embedding_model(self) -> None:
        """Load the sentence transformer embedding model lazily.

        Uses ``local_files_only=True`` to avoid blocking startup with network
        downloads; falls back to a disabled embedding model if not cached.
        """
        if self.embedding_model_instance is not None:
            return
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            logger.warning("sentence-transformers not available; embeddings disabled")
            return
        try:
            self.embedding_model_instance = SentenceTransformer(
                self.embedding_model, local_files_only=True
            )
            logger.info(f"Embedding model loaded: {self.embedding_model}")
        except Exception as e:
            logger.warning(f"Embedding model not cached locally; disabling RAG embeddings: {e}")
            self.embedding_model_instance = None

    def _ensure_collection(self) -> None:
        """Ensure Qdrant collection exists"""
        try:
            if self.qdrant_client is None:
                logger.warning("Qdrant client not initialized")
                return

            collections = self.qdrant_client.get_collections().collections
            collection_names = [c.name for c in collections]

            if self.collection_name not in collection_names:
                logger.info(f"Creating collection: {self.collection_name}")
                self.qdrant_client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=384,  # all-MiniLM-L6-v2 produces 384-dimensional vectors
                        distance=Distance.COSINE,
                    ),
                )
                logger.info(f"Collection created: {self.collection_name}")

        except Exception as e:
            logger.warning(f"Failed to ensure collection: {e}")
            # Don't fail the entire initialization if Qdrant is not available
            self._is_initialized = False

    def embed_text(self, text: str) -> List[float]:
        """
        Convert text to embedding vector

        Args:
            text: Input text

        Returns:
            Embedding vector
        """
        if not self.embedding_model_instance:
            logger.warning("Embedding model not available, returning zero vector")
            return [0.0] * 384

        try:
            embedding = self.embedding_model_instance.encode(text)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Failed to embed text: {e}")
            return [0.0] * 384

    async def add_knowledge(
        self, text: str, metadata: Optional[Dict[str, Any]] = None, id: Optional[str] = None
    ) -> bool:
        """
        Add knowledge to the vector database

        Args:
            text: Knowledge text
            metadata: Optional metadata
            id: Optional unique ID

        Returns:
            True if successful
        """
        if not self._is_initialized or not self.qdrant_client:
            logger.warning("RAG engine not initialized")
            return False

        try:
            # Generate embedding
            embedding = self.embed_text(text)

            # Create point
            point_id = id or str(datetime.now().timestamp())
            point = PointStruct(
                id=point_id,
                vector=embedding,
                payload={"text": text, "timestamp": datetime.now().isoformat(), **(metadata or {})},
            )

            # Upsert to Qdrant
            self.qdrant_client.upsert(collection_name=self.collection_name, points=[point])

            logger.info(f"Knowledge added: {point_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to add knowledge: {e}")
            return False

    async def retrieve_knowledge(
        self, query: str, limit: int = 5, score_threshold: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant knowledge for a query

        Args:
            query: Query text
            limit: Maximum number of results
            score_threshold: Minimum similarity score

        Returns:
            List of relevant knowledge items
        """
        if not self._is_initialized or not self.qdrant_client:
            logger.warning("RAG engine not initialized")
            return []

        try:
            # Generate query embedding
            query_embedding = self.embed_text(query)

            # Search in Qdrant
            search_results = self.qdrant_client.search(  # type: ignore[attr-defined]
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=limit,
                score_threshold=score_threshold,
            )

            # Format results
            results = []
            for result in search_results:
                results.append(
                    {
                        "text": result.payload.get("text", ""),
                        "score": result.score,
                        "metadata": {
                            k: v
                            for k, v in result.payload.items()
                            if k not in ["text", "timestamp"]
                        },
                        "timestamp": result.payload.get("timestamp"),
                    }
                )

            logger.info(f"Retrieved {len(results)} knowledge items")
            return results

        except Exception as e:
            logger.error(f"Failed to retrieve knowledge: {e}")
            return []

    async def augment_context(
        self, query: str, base_context: Optional[Dict[str, Any]] = None, limit: int = 3
    ) -> Dict[str, Any]:
        """
        Augment context with retrieved knowledge

        Args:
            query: Query text
            base_context: Base context to augment
            limit: Number of knowledge items to retrieve

        Returns:
            Augmented context
        """
        # Retrieve relevant knowledge
        knowledge = await self.retrieve_knowledge(query, limit=limit)

        # Build augmented context
        augmented = base_context or {}

        if knowledge:
            augmented["rag_knowledge"] = [
                {"text": k["text"], "score": k["score"], "metadata": k["metadata"]}
                for k in knowledge
            ]
            augmented["rag_enabled"] = True
            augmented["rag_count"] = len(knowledge)
        else:
            augmented["rag_enabled"] = False
            augmented["rag_count"] = 0

        return augmented

    async def search_similar(
        self, text: str, limit: int = 10, filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar knowledge items

        Args:
            text: Search text
            limit: Maximum number of results
            filters: Optional metadata filters

        Returns:
            List of similar items
        """
        if not self._is_initialized or not self.qdrant_client:
            logger.warning("RAG engine not initialized")
            return []

        try:
            # Generate query embedding
            query_embedding = self.embed_text(text)

            # Build filter if provided
            query_filter = None
            if filters:
                conditions = [
                    FieldCondition(key=k, match=MatchValue(value=v)) for k, v in filters.items()
                ]
                query_filter = Filter(must=conditions)  # type: ignore[arg-type]

            # Search in Qdrant
            search_results = self.qdrant_client.search(  # type: ignore[attr-defined]
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=limit,
                query_filter=query_filter,
            )

            # Format results
            results = []
            for result in search_results:
                results.append(
                    {
                        "text": result.payload.get("text", ""),
                        "score": result.score,
                        "metadata": {
                            k: v
                            for k, v in result.payload.items()
                            if k not in ["text", "timestamp"]
                        },
                        "timestamp": result.payload.get("timestamp"),
                    }
                )

            return results

        except Exception as e:
            logger.error(f"Failed to search similar: {e}")
            return []

    async def delete_knowledge(self, id: str) -> bool:
        """
        Delete knowledge by ID

        Args:
            id: Knowledge ID

        Returns:
            True if successful
        """
        if not self._is_initialized or not self.qdrant_client:
            logger.warning("RAG engine not initialized")
            return False

        try:
            self.qdrant_client.delete(collection_name=self.collection_name, points_selector=[id])
            logger.info(f"Knowledge deleted: {id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete knowledge: {e}")
            return False

    def get_status(self) -> Dict[str, Any]:
        """Get RAG engine status"""
        return {
            "initialized": self._is_initialized,
            "qdrant_available": QDRANT_AVAILABLE,
            "sentence_transformers_available": SENTENCE_TRANSFORMERS_AVAILABLE,
            "collection_name": self.collection_name,
            "embedding_model": self.embedding_model,
        }

    def close(self) -> None:
        """Close RAG engine"""
        if self.qdrant_client:
            try:
                self.qdrant_client.close()
            except Exception as e:
                logger.error(f"Error closing Qdrant client: {e}")

        self._is_initialized = False
        logger.info("RAG engine closed")


# Global singleton instance
_rag_engine: Optional[RAGEngine] = None


def get_rag_engine() -> Optional[RAGEngine]:
    """Get global RAG engine instance"""
    return _rag_engine


def init_rag_engine(config: Dict[str, Any]) -> RAGEngine:
    """Initialize global RAG engine"""
    global _rag_engine
    _rag_engine = RAGEngine(config)
    return _rag_engine
