# -*- coding: utf-8 -*-
"""FastAPI application for the vector retrieval microservice."""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import Body, FastAPI, HTTPException
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.responses import Response

from .cache import CacheManager
from .config import settings
from .health_check import HealthCheckEngine
from .metrics import MetricsCollector
from .retry import RetryEngine
from .schemas import (
    ClusterRequest,
    HybridSearchRequest,
    IndexRequest,
    IndexResponse,
    MultiVectorSearchRequest,
    ServiceHealth,
    StatsResponse,
    VectorBatchStoreRequest,
    VectorSearchRequest,
    VectorSearchResponse,
    VectorStoreRequest,
)
from .service import VectorRetrievalService

_service: Optional[VectorRetrievalService] = None
_metrics = MetricsCollector(settings.service_name)


def get_service() -> VectorRetrievalService:
    """Return the vector retrieval service singleton."""
    global _service
    if _service is None:
        _service = VectorRetrievalService(
            redis_url=settings.redis_url,
            qdrant_url=settings.qdrant_url,
            metrics=_metrics,
            retry_engine=RetryEngine("exponential_fast", _metrics),
            cache=CacheManager(settings.redis_url, _metrics),
        )
    return _service


app = FastAPI(
    title="Vector Retrieval Service",
    description="Vector storage, indexing, search and retrieval microservice.",
    version="0.1.0",
)


@app.get("/health", response_model=ServiceHealth)
async def health() -> ServiceHealth:
    """Health check endpoint."""
    service = get_service()
    total = sum(len(c.entries) for c in service.collections.values())
    return await HealthCheckEngine().check(settings.service_name, total)


@app.get("/metrics")
async def metrics() -> Response:
    """Prometheus metrics endpoint."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/stats", response_model=StatsResponse)
async def stats() -> StatsResponse:
    """Service statistics."""
    data = get_service().get_stats()
    return StatsResponse(**data)


@app.post("/vectors/index", response_model=IndexResponse)
async def create_index(request: IndexRequest) -> IndexResponse:
    """Create a vector collection/index."""
    return await get_service().create_index(request)


@app.post("/vectors/store")
async def store_vector(request: VectorStoreRequest) -> Dict[str, Any]:
    """Store a single vector."""
    return await get_service().store(request)


@app.post("/vectors/store/batch")
async def store_vectors_batch(request: VectorBatchStoreRequest) -> Dict[str, Any]:
    """Store a batch of vectors."""
    return await get_service().store_batch(request)


@app.post("/vectors/search", response_model=VectorSearchResponse)
async def search_vectors(request: VectorSearchRequest) -> VectorSearchResponse:
    """Search vectors by similarity."""
    return await get_service().search(request)


@app.post("/vectors/ann", response_model=VectorSearchResponse)
async def ann_search(request: VectorSearchRequest) -> VectorSearchResponse:
    """Approximate nearest neighbor search."""
    return await get_service().ann_search(request)


@app.post("/vectors/exact", response_model=VectorSearchResponse)
async def exact_search(request: VectorSearchRequest) -> VectorSearchResponse:
    """Exact nearest neighbor search."""
    return await get_service().exact_search(request)


@app.post("/vectors/hybrid", response_model=VectorSearchResponse)
async def hybrid_search(request: HybridSearchRequest) -> VectorSearchResponse:
    """Hybrid vector + keyword search."""
    return await get_service().hybrid_search(request)


@app.post("/vectors/multi", response_model=VectorSearchResponse)
async def multi_vector_search(request: MultiVectorSearchRequest) -> VectorSearchResponse:
    """Search with multiple query vectors."""
    return await get_service().multi_vector_search(request)


@app.post("/vectors/cluster")
async def cluster_vectors(request: ClusterRequest) -> Dict[str, Any]:
    """Cluster vectors in a collection."""
    result = await get_service().cluster_vectors(request)
    return result.model_dump()


@app.post("/rpc/{method}")
async def rpc(method: str, payload: Optional[Dict[str, Any]] = Body(default=None)) -> Any:
    """Generic RPC dispatcher."""
    if payload is None:
        payload = {}
    service = get_service()
    if method == "list_methods":
        return service.list_methods()
    if method == "stats":
        return service.get_stats()
    if method not in service.list_methods():
        raise HTTPException(status_code=404, detail=f"Unknown RPC method: {method}")
    request_types: Dict[str, Any] = {
        "create_index": IndexRequest,
        "store": VectorStoreRequest,
        "store_batch": VectorBatchStoreRequest,
        "search": VectorSearchRequest,
        "exact_search": VectorSearchRequest,
        "ann_search": VectorSearchRequest,
        "hybrid_search": HybridSearchRequest,
        "multi_vector_search": MultiVectorSearchRequest,
        "cluster_vectors": ClusterRequest,
    }
    try:
        request_type = request_types.get(method)
        if request_type is not None and payload:
            filtered = {k: v for k, v in payload.items() if k in request_type.model_fields}
            result = await service.call(method, request=request_type(**filtered))
        else:
            result = await service.call(method, **payload)
        if hasattr(result, "model_dump"):
            return result.model_dump()
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
