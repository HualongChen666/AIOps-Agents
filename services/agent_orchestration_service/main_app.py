# -*- coding: utf-8 -*-
"""FastAPI application for the Agent Orchestration microservice."""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

from fastapi import Body, FastAPI, HTTPException
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.responses import Response

from .config import settings
from .health_check import HealthCheckEngine
from .orchestrator import AgentOrchestrator
from .schemas import (
    AgentRequest,
    AgentResponse,
    AggregateRequest,
    AggregateResponse,
    CollaborateRequest,
    CollaborateResponse,
    CoordinateRequest,
    CoordinateResponse,
    DecomposeRequest,
    DecomposeResponse,
    ErrorHandleRequest,
    ErrorHandleResponse,
    HealthResponse,
    StatsResponse,
)

app = FastAPI(title=settings.service_name, version="1.0.0")
_orchestrator: Optional[AgentOrchestrator] = None


def get_orchestrator() -> AgentOrchestrator:
    """Return a shared orchestrator instance."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = AgentOrchestrator()
    return _orchestrator


@app.on_event("startup")
async def startup() -> None:
    get_orchestrator()


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return await HealthCheckEngine().check()


@app.get("/metrics")
async def metrics() -> Response:
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )


@app.get("/stats", response_model=StatsResponse)
async def stats() -> StatsResponse:
    return await get_orchestrator().get_stats()


@app.get("/agents")
async def list_agents() -> List[str]:
    from .schemas import AgentType

    return [t.value for t in AgentType]


@app.post("/decompose", response_model=DecomposeResponse)
async def decompose(request: DecomposeRequest) -> DecomposeResponse:
    try:
        return await get_orchestrator().decompose_task(request)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/run/{agent_type}", response_model=AgentResponse)
async def run_agent(agent_type: str, request: AgentRequest) -> AgentResponse:
    try:
        return await get_orchestrator().run_agent(request)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/coordinate", response_model=CoordinateResponse)
async def coordinate(request: CoordinateRequest) -> CoordinateResponse:
    try:
        return await get_orchestrator().coordinate(request)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/collaborate", response_model=CollaborateResponse)
async def collaborate(request: CollaborateRequest) -> CollaborateResponse:
    try:
        return await get_orchestrator().collaborate(request)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/aggregate", response_model=AggregateResponse)
async def aggregate(request: AggregateRequest) -> AggregateResponse:
    try:
        return await get_orchestrator().aggregate(request)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/handle-error", response_model=ErrorHandleResponse)
async def handle_error(request: ErrorHandleRequest) -> ErrorHandleResponse:
    try:
        return await get_orchestrator().handle_error(request)
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
            "decompose_task": DecomposeRequest,
            "run_agent": AgentRequest,
            "coordinate": CoordinateRequest,
            "collaborate": CollaborateRequest,
            "aggregate": AggregateRequest,
            "handle_error": ErrorHandleRequest,
        }
        request_type = request_types.get(method)
        if request_type is not None and payload:
            result = await fn(request_type(**payload))
        else:
            result = await fn(**payload) if asyncio.iscoroutinefunction(fn) else fn(**payload)
        if isinstance(result, BaseModel):
            return result.model_dump()
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
