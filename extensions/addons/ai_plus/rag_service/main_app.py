# -*- coding: utf-8 -*-
"""FastAPI application for the RAG microservice."""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

from fastapi import Body, FastAPI, HTTPException
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.responses import Response

from .config import settings
from .health_check import HealthCheckEngine
from .orchestrator import RAGOrchestrator
from .schemas import (
    BatchSearchRequest,
    BatchVectorizeRequest,
    ContextRequest,
    ContextResponse,
    DeleteRequest,
    GenerateRequest,
    GenerateResponse,
    HybridRequest,
    IndexRequest,
    IndexResponse,
    KnowledgeGraphLinkageRequest,
    MarkStaleRequest,
    RebuildIndexRequest,
    RecallRequest,
    RecallResponse,
    RerankRequest,
    RetrieveRequest,
    RetrieveResponse,
    SearchRequest,
    SearchResponse,
    ServiceHealth,
    StatsResponse,
    VectorizeRequest,
    VectorizeResponse,
)

_orchestrator: Optional[RAGOrchestrator] = None


def get_orchestrator() -> RAGOrchestrator:
    """Return a singleton RAG orchestrator."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = RAGOrchestrator()
    return _orchestrator


app = FastAPI(
    title="RAG Service",
    description="Retrieval-Augmented Generation microservice with multi-strategy retrieval.",
    version="0.1.0",
)


@app.get("/health", response_model=ServiceHealth)
async def health() -> ServiceHealth:
    """Health check endpoint."""
    orchestrator = get_orchestrator()
    return await HealthCheckEngine().check(settings.service_name, len(orchestrator._index))


@app.get("/metrics")
async def metrics() -> Response:
    """Prometheus metrics endpoint."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/stats")
async def stats() -> StatsResponse:
    """Service statistics endpoint."""
    data = get_orchestrator().get_stats()
    return StatsResponse(
        index_size=data["index_size"],
        cache_hits=data["cache_hits"],
        cache_misses=data["cache_misses"],
        total_requests=sum(data["request_counts"].values()),
        operations=data["request_counts"],
    )


@app.post("/vectorize", response_model=VectorizeResponse)
async def vectorize(request: VectorizeRequest) -> VectorizeResponse:
    """Vectorize a document into chunks and embeddings."""
    try:
        return await get_orchestrator().vectorize_document(request)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/index", response_model=IndexResponse)
async def index(request: IndexRequest) -> IndexResponse:
    """Index a document into the knowledge base."""
    try:
        return await get_orchestrator().index_document(request)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest) -> SearchResponse:
    """Semantic search over the knowledge base."""
    try:
        return await get_orchestrator().semantic_search(request)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/retrieve", response_model=RetrieveResponse)
async def retrieve(request: RetrieveRequest) -> RetrieveResponse:
    """Retrieve chunks from the knowledge base."""
    try:
        return await get_orchestrator().retrieve(request)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/context", response_model=ContextResponse)
async def context(request: ContextRequest) -> ContextResponse:
    """Build a context string from retrieved results."""
    try:
        return await get_orchestrator().build_context(request)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/generate", response_model=GenerateResponse)
async def generate(request: GenerateRequest) -> GenerateResponse:
    """Generate an answer for a query using retrieved context."""
    try:
        return await get_orchestrator().generate_answer(request)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/hybrid", response_model=SearchResponse)
async def hybrid(request: HybridRequest) -> SearchResponse:
    """Hybrid semantic + keyword search."""
    try:
        return await get_orchestrator().hybrid_search(request)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/rerank", response_model=SearchResponse)
async def rerank(request: RerankRequest) -> SearchResponse:
    """Rerank candidates for a query."""
    try:
        return await get_orchestrator().rerank(request)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/recall", response_model=RecallResponse)
async def recall(request: RecallRequest) -> RecallResponse:
    """Multi-way recall over multiple retrieval strategies."""
    try:
        return await get_orchestrator().multi_recall(request)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/batch/vectorize", response_model=List[VectorizeResponse])
async def batch_vectorize(request: BatchVectorizeRequest) -> List[VectorizeResponse]:
    """Vectorize multiple documents in parallel."""
    try:
        return await get_orchestrator().batch_vectorize(request)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/batch/search", response_model=List[SearchResponse])
async def batch_search(request: BatchSearchRequest) -> List[SearchResponse]:
    """Search multiple queries in parallel."""
    try:
        return await get_orchestrator().batch_search(request)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/batch/index", response_model=List[IndexResponse])
async def batch_index(documents: List[IndexRequest]) -> List[IndexResponse]:
    """Index multiple documents in parallel."""
    try:
        return await get_orchestrator().batch_index(documents)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/document/delete", response_model=IndexResponse)
async def delete_document(request: DeleteRequest) -> IndexResponse:
    """Delete a document from the knowledge base."""
    try:
        return await get_orchestrator().delete_document(request)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/document/stale", response_model=IndexResponse)
async def mark_document_stale(request: MarkStaleRequest) -> IndexResponse:
    """Mark a document as stale/outdated."""
    try:
        return await get_orchestrator().mark_document_stale(request)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/index/rebuild", response_model=IndexResponse)
async def rebuild_index(request: RebuildIndexRequest) -> IndexResponse:
    """Rebuild embeddings for all or selected documents."""
    try:
        return await get_orchestrator().rebuild_index(request)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/document/link-graph")
async def link_to_knowledge_graph(request: KnowledgeGraphLinkageRequest) -> Dict[str, Any]:
    """Link a knowledge base document to the knowledge graph."""
    try:
        return await get_orchestrator().link_to_knowledge_graph(request)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/rpc/{method}")
async def rpc(method: str, payload: Optional[Dict[str, Any]] = Body(default=None)) -> Any:
    """Simple RPC dispatcher for inter-service calls."""
    if payload is None:
        payload = {}
    orchestrator = get_orchestrator()
    if method == "list_methods":
        return orchestrator.list_methods()
    if method == "stats":
        return orchestrator.get_stats()
    if method not in orchestrator.list_methods():
        raise HTTPException(status_code=404, detail=f"Unknown RPC method: {method}")
    try:
        fn = getattr(orchestrator, method)
        from .schemas import BaseModel

        request_types: Dict[str, Any] = {
            "vectorize_document": VectorizeRequest,
            "index_document": IndexRequest,
            "semantic_search": SearchRequest,
            "retrieve": RetrieveRequest,
            "build_context": ContextRequest,
            "generate_answer": GenerateRequest,
            "hybrid_search": HybridRequest,
            "rerank": RerankRequest,
            "multi_recall": RecallRequest,
        }
        request_type = request_types.get(method)
        if request_type is not None and payload:
            result = await fn(request_type(**payload))
        else:
            result = await fn(**payload) if asyncio.iscoroutinefunction(fn) else fn(**payload)
        if isinstance(result, BaseModel):
            return result.model_dump()
        if isinstance(result, list) and result and isinstance(result[0], BaseModel):
            return [r.model_dump() for r in result]
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
