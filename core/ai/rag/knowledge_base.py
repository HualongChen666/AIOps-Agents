# -*- coding: utf-8 -*-
"""
Knowledge Base Management
Manages document storage and retrieval
"""

from typing import Any, Dict, List, Optional

from loguru import logger

from .vectorizer import Document, VectorizationPipeline


class KnowledgeBase:
    """
    Knowledge base for document management
    """

    def __init__(
        self,
        name: str,
        vectorization_pipeline: VectorizationPipeline,
        vector_store_client: Optional[Any] = None,
    ):
        """
        Initialize knowledge base

        Args:
            name: Knowledge base name
            vectorization_pipeline: Vectorization pipeline
            vector_store_client: Vector store client
        """
        self.name = name
        self.vectorization_pipeline = vectorization_pipeline
        self.vector_store_client = vector_store_client
        self.documents: Dict[str, Document] = {}

    async def add_document(
        self, document_id: str, content: str, metadata: Optional[Dict[str, Any]] = None
    ) -> Document:
        """
        Add document to knowledge base

        Args:
            document_id: Document ID
            content: Document content
            metadata: Document metadata

        Returns:
            Vectorized document
        """
        document = Document(id=document_id, content=content, metadata=metadata or {})

        # Vectorize
        vectorized = await self.vectorization_pipeline.vectorize(document)
        self.documents[document_id] = vectorized

        # Store in vector store if available
        if self.vector_store_client:
            await self._store_in_vector_store(vectorized)

        logger.info(f"Added document {document_id} to knowledge base {self.name}")
        return vectorized

    async def _store_in_vector_store(self, document: Document) -> None:
        """Store document in vector store"""
        try:
            # Placeholder - integrate with actual vector store
            # for chunk in document.chunks:
            #     self.vector_store_client.upsert(...)
            chunk_count = len(document.chunks) if document.chunks else 0
            logger.debug(f"Stored {chunk_count} chunks in vector store")
        except Exception as e:
            logger.error(f"Failed to store in vector store: {e}")

    async def delete_document(self, document_id: str) -> bool:
        """
        Delete document from knowledge base

        Args:
            document_id: Document ID

        Returns:
            True if deleted
        """
        if document_id not in self.documents:
            return False

        del self.documents[document_id]
        logger.info(f"Deleted document {document_id} from knowledge base {self.name}")
        return True

    def get_document(self, document_id: str) -> Optional[Document]:
        """Get document by ID"""
        return self.documents.get(document_id)

    def list_documents(self) -> List[str]:
        """List all document IDs"""
        return list(self.documents.keys())

    async def add_documents_batch(self, documents: List[Dict[str, Any]]) -> List[Document]:
        """
        Add multiple documents

        Args:
            documents: List of document dicts

        Returns:
            Vectorized documents
        """
        results = []
        for doc_data in documents:
            doc = await self.add_document(
                doc_data["id"], doc_data["content"], doc_data.get("metadata")
            )
            results.append(doc)
        return results
