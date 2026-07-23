# -*- coding: utf-8 -*-
"""FastAPI application for the Scenario Memory microservice."""

from __future__ import annotations

import asyncio
from typing import Any, Dict, Optional

from fastapi import Body, FastAPI, HTTPException
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.responses import Response

from .config import settings
from .health_check import HealthCheckEngine
from .orchestrator import ScenarioMemoryOrchestrator
from .schemas import (
    AccumulateKnowledgeRequest,
    AccumulateKnowledgeResponse,
    HealthResponse,
    LearnExperienceRequest,
    LearnExperienceResponse,
    LongTermRequest,
    LongTermResponse,
    PatternRequest,
    PatternResponse,
    ProceduralRequest,
    ProceduralResponse,
    SemanticRequest,
    SemanticResponse,
    ShortTermRequest,
    ShortTermResponse,
    SimilarityQueryRequest,
    SimilarityQueryResponse,
    StatsResponse,
    StoreEventRequest,
    StoreEventResponse,
)

app = FastAPI(title=settings.service_name, version="1.0.0")
_orchestrator: Optional[ScenarioMemoryOrchestrator] = None


def get_orchestrator() -> ScenarioMemoryOrchestrator:
    """Return a shared orchestrator instance."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = ScenarioMemoryOrchestrator()
    return _orchestrator


@app.on_event("startup")
async def startup() -> None:
    orchestrator = get_orchestrator()
    await orchestrator.cache.connect()


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


@app.post("/store/event", response_model=StoreEventResponse)
async def store_event(request: StoreEventRequest) -> StoreEventResponse:
    try:
        return await get_orchestrator().store_event(request)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/search/similar", response_model=SimilarityQueryResponse)
async def search_similar(request: SimilarityQueryRequest) -> SimilarityQueryResponse:
    try:
        return await get_orchestrator().search_similar(request)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/learn/experience", response_model=LearnExperienceResponse)
async def learn_experience(request: LearnExperienceRequest) -> LearnExperienceResponse:
    try:
        return await get_orchestrator().learn_experience(request)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/accumulate/knowledge", response_model=AccumulateKnowledgeResponse)
async def accumulate_knowledge(
    request: AccumulateKnowledgeRequest,
) -> AccumulateKnowledgeResponse:
    try:
        return await get_orchestrator().accumulate_knowledge(request)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/recognize/pattern", response_model=PatternResponse)
async def recognize_pattern(request: PatternRequest) -> PatternResponse:
    try:
        return await get_orchestrator().recognize_pattern(request)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/memory/short-term/{key}", response_model=ShortTermResponse)
async def store_short_term(key: str, request: ShortTermRequest) -> ShortTermResponse:
    try:
        if request.key != key:
            request.key = key
        return await get_orchestrator().store_short_term(request)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/memory/short-term/{key}")
async def retrieve_short_term(key: str) -> Any:
    try:
        value = await get_orchestrator().retrieve_short_term(key)
        if value is None:
            raise HTTPException(status_code=404, detail="Short-term memory not found")
        return {"key": key, "value": value}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/memory/long-term/{key}", response_model=LongTermResponse)
async def store_long_term(key: str, request: LongTermRequest) -> LongTermResponse:
    try:
        if request.key != key:
            request.key = key
        return await get_orchestrator().store_long_term(request)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/memory/long-term/{key}")
async def retrieve_long_term(key: str) -> Any:
    try:
        value = await get_orchestrator().retrieve_long_term(key)
        if value is None:
            raise HTTPException(status_code=404, detail="Long-term memory not found")
        return {"key": key, "value": value}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/memory/semantic", response_model=SemanticResponse)
async def store_semantic(request: SemanticRequest) -> SemanticResponse:
    try:
        return await get_orchestrator().store_semantic(request)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/memory/semantic/{entity}")
async def retrieve_semantic(entity: str) -> dict:
    try:
        triples = await get_orchestrator().retrieve_semantic(entity)
        return {"entity": entity, "triples": [t.model_dump() for t in triples]}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/memory/procedural", response_model=ProceduralResponse)
async def store_procedural(request: ProceduralRequest) -> ProceduralResponse:
    try:
        return await get_orchestrator().store_procedural(request)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/memory/procedural/{key}")
async def retrieve_procedural(key: str) -> dict:
    try:
        proc = await get_orchestrator().retrieve_procedural(key)
        if proc is None:
            raise HTTPException(status_code=404, detail="Procedural memory not found")
        return {"key": key, "procedure": proc.model_dump()}
    except HTTPException:
        raise
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
            "store_event": StoreEventRequest,
            "search_similar": SimilarityQueryRequest,
            "learn_experience": LearnExperienceRequest,
            "accumulate_knowledge": AccumulateKnowledgeRequest,
            "recognize_pattern": PatternRequest,
            "store_short_term": ShortTermRequest,
            "store_long_term": LongTermRequest,
            "store_semantic": SemanticRequest,
            "store_procedural": ProceduralRequest,
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
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
