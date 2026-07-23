# -*- coding: utf-8 -*-
"""FastAPI application for the cache microservice."""

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
    AvalancheProtectRequest,
    AvalancheProtectResponse,
    BreakdownProtectRequest,
    BreakdownProtectResponse,
    CacheGetRequest,
    CachePreheatRequest,
    CachePreheatResponse,
    CacheSetRequest,
    CacheStatsResponse,
    CacheStrategyRequest,
    CacheStrategyResponse,
    ServiceHealth,
    StatsResponse,
)
from .service import CacheService

_service: Optional[CacheService] = None
_metrics = MetricsCollector(settings.service_name)


def get_service() -> CacheService:
    """Return the cache service singleton."""
    global _service
    if _service is None:
        _service = CacheService(
            redis_url=settings.redis_url,
            metrics=_metrics,
            retry_engine=RetryEngine("exponential_fast", _metrics),
            cache=CacheManager(settings.redis_url, _metrics),
        )
    return _service


app = FastAPI(
    title="Cache Service",
    description="Distributed caching microservice with strategies and protections.",
    version="0.1.0",
)


@app.get("/health", response_model=ServiceHealth)
async def health() -> ServiceHealth:
    """Health check endpoint."""
    return await HealthCheckEngine().check(settings.service_name)


@app.get("/metrics")
async def metrics() -> Response:
    """Prometheus metrics endpoint."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/stats", response_model=StatsResponse)
async def stats() -> StatsResponse:
    """Service statistics."""
    data = get_service().get_stats()
    return StatsResponse(**data)


@app.post("/cache/get")
async def cache_get(request: CacheGetRequest) -> Dict[str, Any]:
    """Get a value from cache."""
    result = await get_service().get(request)
    return result.model_dump()


@app.post("/cache/set")
async def cache_set(request: CacheSetRequest) -> Dict[str, Any]:
    """Set a value in cache."""
    return await get_service().set(request)


@app.post("/cache/delete")
async def cache_delete(request: CacheGetRequest) -> Dict[str, bool]:
    """Delete a key from cache."""
    return await get_service().delete(request)


@app.post("/cache/clear")
async def cache_clear() -> Dict[str, bool]:
    """Clear all cached values."""
    return await get_service().clear()


@app.post("/cache/preheat", response_model=CachePreheatResponse)
async def cache_preheat(request: CachePreheatRequest) -> CachePreheatResponse:
    """Preheat cache with key-value pairs."""
    return await get_service().preheat(request)


@app.post("/cache/breakdown/protect", response_model=BreakdownProtectResponse)
async def cache_breakdown_protect(request: BreakdownProtectRequest) -> BreakdownProtectResponse:
    """Protect against cache breakdown using a per-key mutex."""
    return await get_service().protect_breakdown(request)


@app.post("/cache/avalanche/protect", response_model=AvalancheProtectResponse)
async def cache_avalanche_protect(request: AvalancheProtectRequest) -> AvalancheProtectResponse:
    """Protect against cache avalanche with randomized TTL."""
    return await get_service().protect_avalanche(request)


@app.post("/cache/strategy", response_model=CacheStrategyResponse)
async def cache_strategy(request: CacheStrategyRequest) -> CacheStrategyResponse:
    """Execute a caching strategy."""
    return await get_service().execute_strategy(request)


@app.get("/cache/stats", response_model=CacheStatsResponse)
async def cache_stats() -> CacheStatsResponse:
    """Cache statistics."""
    return get_service().get_cache_stats()


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
        "get": CacheGetRequest,
        "set": CacheSetRequest,
        "delete": CacheGetRequest,
        "preheat": CachePreheatRequest,
        "protect_breakdown": BreakdownProtectRequest,
        "protect_avalanche": AvalancheProtectRequest,
        "execute_strategy": CacheStrategyRequest,
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
