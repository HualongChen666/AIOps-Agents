# -*- coding: utf-8 -*-
"""FastAPI application for the Knowledge Graph microservice."""

from __future__ import annotations

import asyncio
from typing import Any, Dict, Optional

from fastapi import Body, FastAPI, HTTPException
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.responses import Response

from .config import settings
from .health_check import HealthCheckEngine
from .orchestrator import KnowledgeGraphOrchestrator
from .schemas import (
    EntityModelingRequest,
    EntityModelingResponse,
    FaultPropagationGraphRequest,
    FaultPropagationGraphResponse,
    GraphBuildRequest,
    GraphBuildResponse,
    GraphQueryRequest,
    GraphQueryResponse,
    GraphReasonRequest,
    GraphReasonResponse,
    GraphVisualizationRequest,
    GraphVisualizationResponse,
    HealthResponse,
    InfrastructureGraphRequest,
    InfrastructureGraphResponse,
    RelationModelingRequest,
    RelationModelingResponse,
    ServiceDependencyGraphRequest,
    ServiceDependencyGraphResponse,
    StatsResponse,
)

app = FastAPI(title=settings.service_name, version="1.0.0")
_orchestrator: Optional[KnowledgeGraphOrchestrator] = None


def get_orchestrator() -> KnowledgeGraphOrchestrator:
    """Return a shared orchestrator instance."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = KnowledgeGraphOrchestrator()
    return _orchestrator


@app.on_event("startup")
async def startup() -> None:
    orchestrator = get_orchestrator()
    await orchestrator.cache.connect()
    await orchestrator.store.connect()


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    data = await HealthCheckEngine().check()
    return HealthResponse(**data)


@app.get("/metrics")
async def metrics() -> Response:
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )


@app.get("/stats", response_model=StatsResponse)
async def stats() -> StatsResponse:
    return await get_orchestrator().get_stats()


@app.post("/entity/model", response_model=EntityModelingResponse)
async def model_entity(request: EntityModelingRequest) -> EntityModelingResponse:
    try:
        return await get_orchestrator().model_entity(request)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/relation/model", response_model=RelationModelingResponse)
async def model_relation(request: RelationModelingRequest) -> RelationModelingResponse:
    try:
        return await get_orchestrator().model_relation(request)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/graph/build", response_model=GraphBuildResponse)
async def build_graph(request: GraphBuildRequest) -> GraphBuildResponse:
    try:
        return await get_orchestrator().build_graph(request)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/graph/query", response_model=GraphQueryResponse)
async def query_graph(request: GraphQueryRequest) -> GraphQueryResponse:
    try:
        return await get_orchestrator().query_graph(request)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/graph/reason", response_model=GraphReasonResponse)
async def reason_graph(request: GraphReasonRequest) -> GraphReasonResponse:
    try:
        return await get_orchestrator().infer_graph(request)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/graph/visualize", response_model=GraphVisualizationResponse)
async def visualize_graph(request: GraphVisualizationRequest) -> GraphVisualizationResponse:
    try:
        return await get_orchestrator().visualize_graph(request)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/service-dependency/build", response_model=ServiceDependencyGraphResponse)
async def build_service_dependency_graph(
    request: ServiceDependencyGraphRequest,
) -> ServiceDependencyGraphResponse:
    try:
        return await get_orchestrator().build_service_dependency_graph(request)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/infrastructure/build", response_model=InfrastructureGraphResponse)
async def build_infrastructure_graph(
    request: InfrastructureGraphRequest,
) -> InfrastructureGraphResponse:
    try:
        return await get_orchestrator().build_infrastructure_graph(request)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/fault-propagation/build", response_model=FaultPropagationGraphResponse)
async def build_fault_propagation_graph(
    request: FaultPropagationGraphRequest,
) -> FaultPropagationGraphResponse:
    try:
        return await get_orchestrator().build_fault_propagation_graph(request)
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
        return await orchestrator.get_stats()
    if method not in orchestrator.list_methods():
        raise HTTPException(status_code=404, detail=f"Unknown RPC method: {method}")
    try:
        fn = getattr(orchestrator, method)
        request_types: Dict[str, Any] = {
            "model_entity": EntityModelingRequest,
            "model_relation": RelationModelingRequest,
            "build_graph": GraphBuildRequest,
            "query_graph": GraphQueryRequest,
            "infer_graph": GraphReasonRequest,
            "visualize_graph": GraphVisualizationRequest,
            "build_service_dependency_graph": ServiceDependencyGraphRequest,
            "build_infrastructure_graph": InfrastructureGraphRequest,
            "build_fault_propagation_graph": FaultPropagationGraphRequest,
        }
        request_type = request_types.get(method)
        if request_type is not None and payload:
            result = await fn(request_type(**payload))
        else:
            result = await fn(**payload) if asyncio.iscoroutinefunction(fn) else fn(**payload)
        from .schemas import BaseModel

        if isinstance(result, BaseModel):
            return result.model_dump()
        return result
    except HTTPException:
        raise
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
