# -*- coding: utf-8 -*-
"""FastAPI application for the Kubernetes Orchestration microservice."""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import Body, FastAPI, HTTPException
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.responses import Response

from .cache import CacheManager
from .config import settings
from .health_check import HealthCheckEngine
from .metrics import MetricsCollector
from .schemas import FeatureRequest, FeatureResponse, ServiceHealth, StatsResponse
from .service import BASE_METHODS, OPERATIONS
from .service import KubernetesOrchestrationService as ServiceClass

URL_PREFIX = "kubernetes-orchestration"

_service: Optional[ServiceClass] = None
_metrics = MetricsCollector(settings.service_name)
_allowed_methods = set(OPERATIONS) | set(BASE_METHODS)


def get_service() -> ServiceClass:
    """Return the service singleton."""
    global _service
    if _service is None:
        _service = ServiceClass(
            redis_url=settings.redis_url,
            metrics=_metrics,
            cache=CacheManager(settings.redis_url, _metrics),
        )
    return _service


app = FastAPI(
    title="Kubernetes Orchestration Service",
    description="FastAPI microservice for Kubernetes Orchestration.",
    version="0.1.0",
)


@app.get("/health", response_model=ServiceHealth)
async def health() -> ServiceHealth:
    """Health check endpoint."""
    service = get_service()
    return await HealthCheckEngine().check(settings.service_name, len(service._state))


@app.get("/metrics")
async def metrics() -> Response:
    """Prometheus metrics endpoint."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/stats", response_model=StatsResponse)
async def stats() -> StatsResponse:
    """Service statistics."""
    data = await get_service().get_stats()
    result = data.get("result", {})
    return StatsResponse(**result)


@app.post("/kubernetes-orchestration/{path}", response_model=FeatureResponse)
async def dispatch(path: str, request: FeatureRequest) -> FeatureResponse:
    """Dispatch any feature endpoint to the service."""
    method = path.replace("-", "_")
    if method not in _allowed_methods:
        raise HTTPException(status_code=404, detail=f"Unknown endpoint: {path}")
    service = get_service()
    handler = getattr(service, method)
    data = await handler(request)
    return FeatureResponse(**data)


@app.post("/rpc/{method}")
async def rpc(method: str, payload: Optional[Dict[str, Any]] = Body(default=None)) -> Any:
    """Generic RPC dispatcher."""
    payload = payload or {}
    service = get_service()
    if method == "list_methods":
        return (await service.list_methods()).get("result", {}).get("methods", [])
    if method == "stats":
        return (await service.get_stats()).get("result", {})
    try:
        result = await service.call(method, request=payload)
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
