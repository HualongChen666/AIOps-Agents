# -*- coding: utf-8 -*-
"""
Knowledge Base Router
Provides API endpoints for knowledge base document management
"""

import os
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from loguru import logger

from core.ai.rag.knowledge_base import KnowledgeBase
from core.ai.rag.vectorizer import (
    VectorizationPipeline,
    FixedSizeChunking,
    SentenceTransformerEmbedding,
)
from core.authentication import get_current_active_user
from core.rag_engine import search_similar

router = APIRouter(prefix="/api/v1/knowledge-base", tags=["Knowledge Base"])

# Rate limiting configuration
BATCH_SIZE_LIMIT = int(os.environ.get("KNOWLEDGE_BASE_BATCH_SIZE_LIMIT", "100"))
RATE_LIMIT_PER_MINUTE = int(os.environ.get("KNOWLEDGE_BASE_RATE_LIMIT", "60"))

# Global knowledge base instance (lazy initialization)
_knowledge_base: Optional[KnowledgeBase] = None
_vectorization_pipeline: Optional[VectorizationPipeline] = None


def get_knowledge_base() -> KnowledgeBase:
    """Get or create knowledge base instance"""
    global _knowledge_base, _vectorization_pipeline
    if _knowledge_base is None:
        if _vectorization_pipeline is None:
            chunking_strategy = FixedSizeChunking(chunk_size=500, overlap=50)
            embedding_model = SentenceTransformerEmbedding(
                model_name=os.environ.get("AIOPS_EMBEDDING_MODEL", "BAAI/bge-large-zh-v1.5")
            )
            _vectorization_pipeline = VectorizationPipeline(
                chunking_strategy=chunking_strategy,
                embedding_model=embedding_model,
                batch_size=32,
            )
        _knowledge_base = KnowledgeBase(
            name="default",
            vectorization_pipeline=_vectorization_pipeline,
        )
        logger.info("Knowledge base initialized")
    return _knowledge_base


# Pydantic models for request/response
class DocumentCreateRequest(BaseModel):
    """Request model for creating a document"""
    document_id: str = Field(..., description="Unique document identifier")
    content: str = Field(..., description="Document content")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Document metadata")

    model_config = {
        "json_schema_extra": {
            "example": {
                "document_id": "doc_001",
                "content": "This is a sample document content.",
                "metadata": {"category": "operations", "tags": ["incident", "resolution"]},
            }
        }
    }


class DocumentResponse(BaseModel):
    """Response model for document"""
    document_id: str
    content: str
    metadata: Dict[str, Any]
    chunk_count: Optional[int] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "document_id": "doc_001",
                "content": "This is a sample document content.",
                "metadata": {"category": "operations"},
                "chunk_count": 3,
            }
        }
    }


class BatchDocumentCreateRequest(BaseModel):
    """Request model for batch document creation"""
    documents: List[DocumentCreateRequest] = Field(..., description="List of documents to create")

    model_config = {
        "json_schema_extra": {
            "example": {
                "documents": [
                    {
                        "document_id": "doc_001",
                        "content": "First document",
                        "metadata": {"category": "ops"},
                    },
                    {
                        "document_id": "doc_002",
                        "content": "Second document",
                        "metadata": {"category": "ops"},
                    },
                ]
            }
        }
    }


class BatchDocumentResponse(BaseModel):
    """Response model for batch document creation"""
    success_count: int
    failed_count: int
    results: List[Dict[str, Any]]

    model_config = {
        "json_schema_extra": {
            "example": {
                "success_count": 2,
                "failed_count": 0,
                "results": [
                    {"document_id": "doc_001", "status": "success"},
                    {"document_id": "doc_002", "status": "success"},
                ],
            }
        }
    }


class SearchRequest(BaseModel):
    """Request model for document search"""
    query: str = Field(..., description="Search query")
    top_k: int = Field(default=5, ge=1, le=100, description="Number of results to return")
    score_threshold: float = Field(default=0.55, ge=0.0, le=1.0, description="Minimum similarity score")

    model_config = {
        "json_schema_extra": {
            "example": {"query": "service restart procedure", "top_k": 5, "score_threshold": 0.55}
        }
    }


class SearchResponse(BaseModel):
    """Response model for document search"""
    query: str
    results: List[Dict[str, Any]]
    total_count: int

    model_config = {
        "json_schema_extra": {
            "example": {
                "query": "service restart",
                "results": [
                    {
                        "score": 0.85,
                        "payload": {"text": "Service restart procedure..."},
                    }
                ],
                "total_count": 1,
            }
        }
    }


class DocumentListResponse(BaseModel):
    """Response model for document list"""
    document_ids: List[str]
    total_count: int

    model_config = {
        "json_schema_extra": {
            "example": {"document_ids": ["doc_001", "doc_002"], "total_count": 2}
        }
    }


class DeleteResponse(BaseModel):
    """Response model for document deletion"""
    document_id: str
    deleted: bool
    message: str

    model_config = {
        "json_schema_extra": {
            "example": {"document_id": "doc_001", "deleted": True, "message": "Document deleted successfully"}
        }
    }


@router.post(
    "/documents",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add document to knowledge base",
    description="Add a single document to the knowledge base with vectorization",
    responses={
        201: {"description": "Document created successfully"},
        400: {"description": "Invalid request"},
        401: {"description": "Unauthorized"},
        429: {"description": "Rate limit exceeded"},
    },
)
async def add_document(
    req: DocumentCreateRequest,
    current_user: Any = Depends(get_current_active_user),
) -> DocumentResponse:
    """
    Add a document to the knowledge base

    - **document_id**: Unique identifier for the document
    - **content**: Document text content
    - **metadata**: Optional metadata dictionary
    """
    try:
        kb = get_knowledge_base()
        document = await kb.add_document(req.document_id, req.content, req.metadata)

        logger.info(
            f"User {current_user.username} added document {req.document_id} to knowledge base"
        )

        return DocumentResponse(
            document_id=document.id,
            content=document.content,
            metadata=document.metadata,
            chunk_count=len(document.chunks) if document.chunks else 0,
        )
    except Exception as e:
        logger.error(f"Failed to add document {req.document_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get(
    "/documents/{document_id}",
    response_model=DocumentResponse,
    summary="Get document by ID",
    description="Retrieve a specific document from the knowledge base",
    responses={
        200: {"description": "Document retrieved successfully"},
        401: {"description": "Unauthorized"},
        404: {"description": "Document not found"},
    },
)
async def get_document(
    document_id: str,
    current_user: Any = Depends(get_current_active_user),
) -> DocumentResponse:
    """
    Get a document by its ID

    - **document_id**: Unique identifier for the document
    """
    try:
        kb = get_knowledge_base()
        document = kb.get_document(document_id)

        if document is None:
            logger.warning(f"Document {document_id} not found requested by {current_user.username}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Document {document_id} not found"
            )

        logger.info(f"User {current_user.username} retrieved document {document_id}")

        return DocumentResponse(
            document_id=document.id,
            content=document.content,
            metadata=document.metadata,
            chunk_count=len(document.chunks) if document.chunks else 0,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get document {document_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.delete(
    "/documents/{document_id}",
    response_model=DeleteResponse,
    summary="Delete document",
    description="Delete a document from the knowledge base",
    responses={
        200: {"description": "Document deleted successfully"},
        401: {"description": "Unauthorized"},
        404: {"description": "Document not found"},
    },
)
async def delete_document(
    document_id: str,
    current_user: Any = Depends(get_current_active_user),
) -> DeleteResponse:
    """
    Delete a document by its ID

    - **document_id**: Unique identifier for the document
    """
    try:
        kb = get_knowledge_base()
        deleted = await kb.delete_document(document_id)

        if not deleted:
            logger.warning(f"Document {document_id} not found for deletion by {current_user.username}")
            return DeleteResponse(
                document_id=document_id,
                deleted=False,
                message=f"Document {document_id} not found",
            )

        logger.info(f"User {current_user.username} deleted document {document_id}")

        return DeleteResponse(
            document_id=document_id,
            deleted=True,
            message="Document deleted successfully",
        )
    except Exception as e:
        logger.error(f"Failed to delete document {document_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get(
    "/documents",
    response_model=DocumentListResponse,
    summary="List all documents",
    description="List all document IDs in the knowledge base",
    responses={
        200: {"description": "Document list retrieved successfully"},
        401: {"description": "Unauthorized"},
    },
)
async def list_documents(
    current_user: Any = Depends(get_current_active_user),
) -> DocumentListResponse:
    """
    List all documents in the knowledge base

    Returns a list of document IDs
    """
    try:
        kb = get_knowledge_base()
        document_ids = kb.list_documents()

        logger.info(f"User {current_user.username} listed {len(document_ids)} documents")

        return DocumentListResponse(document_ids=document_ids, total_count=len(document_ids))
    except Exception as e:
        logger.error(f"Failed to list documents: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post(
    "/documents/batch",
    response_model=BatchDocumentResponse,
    summary="Batch add documents",
    description="Add multiple documents to the knowledge base in a single request",
    responses={
        200: {"description": "Documents processed"},
        400: {"description": "Invalid request or batch size exceeds limit"},
        401: {"description": "Unauthorized"},
        429: {"description": "Rate limit exceeded"},
    },
)
async def add_documents_batch(
    req: BatchDocumentCreateRequest,
    current_user: Any = Depends(get_current_active_user),
) -> BatchDocumentResponse:
    """
    Add multiple documents to the knowledge base

    - **documents**: List of documents to add
    - Maximum batch size is controlled by KNOWLEDGE_BASE_BATCH_SIZE_LIMIT environment variable
    """
    try:
        # Validate batch size
        if len(req.documents) > BATCH_SIZE_LIMIT:
            logger.warning(
                f"Batch size {len(req.documents)} exceeds limit {BATCH_SIZE_LIMIT} "
                f"requested by {current_user.username}"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Batch size exceeds limit of {BATCH_SIZE_LIMIT}",
            )

        kb = get_knowledge_base()
        documents_data = [
            {"id": doc.document_id, "content": doc.content, "metadata": doc.metadata}
            for doc in req.documents
        ]

        # Process in batches to avoid rate limiting
        results = []
        success_count = 0
        failed_count = 0

        for doc_data in documents_data:
            try:
                await kb.add_document(doc_data["id"], doc_data["content"], doc_data.get("metadata"))
                results.append({"document_id": doc_data["id"], "status": "success"})
                success_count += 1
            except Exception as e:
                logger.error(f"Failed to add document {doc_data['id']}: {e}")
                results.append({"document_id": doc_data["id"], "status": "failed", "error": str(e)})
                failed_count += 1

        logger.info(
            f"User {current_user.username} batch added {success_count} documents, "
            f"{failed_count} failed"
        )

        return BatchDocumentResponse(
            success_count=success_count,
            failed_count=failed_count,
            results=results,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to batch add documents: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post(
    "/search",
    response_model=SearchResponse,
    summary="Search documents",
    description="Search for documents using semantic similarity",
    responses={
        200: {"description": "Search results returned"},
        400: {"description": "Invalid search query"},
        401: {"description": "Unauthorized"},
    },
)
async def search_documents(
    req: SearchRequest,
    current_user: Any = Depends(get_current_active_user),
) -> SearchResponse:
    """
    Search for documents using semantic similarity

    - **query**: Search query text
    - **top_k**: Number of results to return (1-100)
    - **score_threshold**: Minimum similarity score (0.0-1.0)
    """
    try:
        if not req.query.strip():
            logger.warning(f"Empty search query by {current_user.username}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Query cannot be empty")

        results = search_similar(req.query, top_k=req.top_k, score_threshold=req.score_threshold)

        logger.info(
            f"User {current_user.username} searched for '{req.query}', "
            f"found {len(results)} results"
        )

        return SearchResponse(query=req.query, results=results, total_count=len(results))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to search documents: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get(
    "/health",
    summary="Knowledge base health check",
    description="Check if the knowledge base service is operational",
    responses={
        200: {"description": "Service is healthy"},
        503: {"description": "Service is unavailable"},
    },
)
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint for knowledge base service

    Returns service status and configuration information
    """
    try:
        kb = get_knowledge_base()
        doc_count = len(kb.list_documents())

        return {
            "status": "healthy",
            "document_count": doc_count,
            "batch_size_limit": BATCH_SIZE_LIMIT,
            "rate_limit_per_minute": RATE_LIMIT_PER_MINUTE,
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
        }
