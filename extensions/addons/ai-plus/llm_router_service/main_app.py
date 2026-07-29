# -*- coding: utf-8 -*-
"""FastAPI application for the LLM router microservice."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import Body, FastAPI, HTTPException
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.responses import Response

from .config import settings
from .grpc.server import LLMRouterRPCServer
from .health_check import HealthCheckEngine
from .orchestrator import LLMRouterOrchestrator
from .schemas import GenerateRequest, LiteLLMRequest, RouteRequest, ServiceHealth

_orchestrator: Optional[LLMRouterOrchestrator] = None
_rpc_server: Optional[LLMRouterRPCServer] = None


def get_orchestrator() -> LLMRouterOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = LLMRouterOrchestrator()
    return _orchestrator


def get_rpc_server() -> LLMRouterRPCServer:
    global _rpc_server
    if _rpc_server is None:
        orchestrator = get_orchestrator()
        server = LLMRouterRPCServer()
        server.register("route", lambda **kwargs: orchestrator.route(RouteRequest(**kwargs)))
        server.register(
            "generate",
            lambda **kwargs: orchestrator.generate(GenerateRequest(**kwargs)),
        )
        server.register("list_models", orchestrator.list_models)
        server.register("get_stats", orchestrator.get_stats)
        server.register("get_cost_report", orchestrator.get_cost_report)
        server.register("get_performance_report", orchestrator.get_performance_report)
        server.register(
            "health",
            lambda: HealthCheckEngine().check(
                settings.service_name, len(orchestrator.list_models())
            ),
        )
        _rpc_server = server
    return _rpc_server


app = FastAPI(
    title="LLM Router Service",
    description="LLM routing microservice with multi-model support.",
    version="0.1.0",
)


@app.get("/health", response_model=ServiceHealth)
async def health() -> ServiceHealth:
    orchestrator = get_orchestrator()
    return await HealthCheckEngine().check(settings.service_name, len(orchestrator.list_models()))


@app.get("/metrics")
async def metrics() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/models")
async def list_models() -> Dict[str, Any]:
    orchestrator = get_orchestrator()
    items = [m.model_dump() for m in orchestrator.list_models()]
    return {"total": len(items), "items": items}


@app.post("/route")
async def route(request: RouteRequest) -> Dict[str, Any]:
    response = await get_orchestrator().route(request)
    return response.model_dump()


@app.post("/generate")
async def generate(request: RouteRequest) -> Dict[str, Any]:
    response = await get_orchestrator().route_and_generate(request)
    return response.model_dump()


@app.post("/completions")
async def completions(request: LiteLLMRequest) -> Dict[str, Any]:
    response = await get_orchestrator().completion(request)
    return response.model_dump()


@app.get("/stats")
async def stats() -> Dict[str, Any]:
    return get_orchestrator().get_stats()


@app.get("/cost")
async def cost() -> Dict[str, Any]:
    report = await get_orchestrator().get_cost_report()
    return report.model_dump()


@app.get("/performance")
async def performance() -> Dict[str, Any]:
    report = await get_orchestrator().get_performance_report()
    return report.model_dump()


@app.get("/strategies")
async def strategies() -> Dict[str, List[str]]:
    return {"strategies": ["cost_optimized", "capability_first", "balanced"]}


@app.get("/retry-policies")
async def retry_policies() -> Dict[str, List[str]]:
    return {"policies": get_orchestrator().retry_engine.list_policies()}


@app.get("/circuit-states")
async def circuit_states() -> Dict[str, Any]:
    orchestrator = get_orchestrator()
    states = orchestrator.router.load_balancer.get_circuit_states()
    return {"states": {name: state.value for name, state in states.items()}}


@app.post("/batch/route")
async def batch_route(requests: List[RouteRequest]) -> List[Dict[str, Any]]:
    responses = await get_orchestrator().route_batch(requests)
    return [r.model_dump() for r in responses]


@app.post("/batch/generate")
async def batch_generate(requests: List[GenerateRequest]) -> List[Dict[str, Any]]:
    responses = await get_orchestrator().generate_batch(requests)
    return [r.model_dump() for r in responses]


@app.post("/rpc/{method}")
async def rpc(method: str, payload: Optional[Dict[str, Any]] = Body(default=None)) -> Any:
    if payload is None:
        payload = {}
    server = get_rpc_server()
    try:
        result = await server.call(method, **payload)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
