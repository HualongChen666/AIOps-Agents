# -*- coding: utf-8 -*-
"""FastAPI application for the data access microservice."""

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
    DbRouteRequest,
    DbRouteResponse,
    ItemCreate,
    ItemResponse,
    ItemUpdate,
    OptimizeRequest,
    OptimizeResponse,
    PoolStatus,
    QueryRequest,
    QueryResponse,
    RouteRequest,
    RouteResponse,
    ServiceHealth,
    ShardRequest,
    ShardResponse,
    SlowQueryReport,
    StatsResponse,
    TransactionRequest,
    TransactionResponse,
)
from .service import DataAccessService

_service: Optional[DataAccessService] = None
_metrics = MetricsCollector(settings.service_name)


def get_service() -> DataAccessService:
    """Return the data access service singleton."""
    global _service
    if _service is None:
        _service = DataAccessService(
            database_url=settings.database_url,
            redis_url=settings.redis_url,
            metrics=_metrics,
            retry_engine=RetryEngine("exponential_fast", _metrics),
            cache=CacheManager(settings.redis_url, _metrics),
        )
    return _service


app = FastAPI(
    title="Data Access Service",
    description="Data access microservice with ORM, pooling, routing and optimization.",
    version="0.1.0",
)


@app.get("/health", response_model=ServiceHealth)
async def health() -> ServiceHealth:
    """Health check endpoint."""
    service = get_service()
    return await HealthCheckEngine().check(settings.service_name, await service.count_items())


@app.get("/metrics")
async def metrics() -> Response:
    """Prometheus metrics endpoint."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/stats", response_model=StatsResponse)
async def stats() -> StatsResponse:
    """Service statistics."""
    data = get_service().get_stats()
    return StatsResponse(
        total_requests=data["total_requests"],
        cache_hits=data["cache_hits"],
        cache_misses=data["cache_misses"],
        operations=data.get("operations", {}),
        index_size=data["index_size"],
    )


@app.post("/items", response_model=ItemResponse)
async def create_item(request: ItemCreate) -> ItemResponse:
    """Create a new item."""
    try:
        return await get_service().create_item(request)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/items")
async def list_items(
    name: Optional[str] = None,
    value: Optional[str] = None,
    sort_by: str = "id",
    sort_order: str = "asc",
    page: int = 1,
    page_size: int = 10,
) -> Dict[str, Any]:
    """List items with optional filters and pagination."""
    filters: Dict[str, Any] = {}
    if name is not None:
        filters["name"] = name
    if value is not None:
        filters["value"] = value
    return await get_service().list_items(
        filters=filters,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
    )


@app.get("/items/{item_id}", response_model=ItemResponse)
async def get_item(item_id: int) -> ItemResponse:
    """Get an item by ID."""
    result = await get_service().get_item(item_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Item {item_id} not found")
    return result


@app.put("/items/{item_id}", response_model=ItemResponse)
async def update_item(item_id: int, request: ItemUpdate) -> ItemResponse:
    """Update an item by ID."""
    result = await get_service().update_item(item_id, request)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Item {item_id} not found")
    return result


@app.delete("/items/{item_id}")
async def delete_item(item_id: int) -> Dict[str, bool]:
    """Delete an item by ID."""
    success = await get_service().delete_item(item_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Item {item_id} not found")
    return {"deleted": True}


@app.post("/query/build", response_model=QueryResponse)
async def build_query(request: QueryRequest) -> QueryResponse:
    """Build a SQL query."""
    return get_service().build_query(request)


@app.post("/transaction", response_model=TransactionResponse)
async def execute_transaction(request: TransactionRequest) -> TransactionResponse:
    """Execute a transaction."""
    return await get_service().execute_transaction(request)


@app.get("/pool/status", response_model=PoolStatus)
async def pool_status() -> PoolStatus:
    """Connection pool status."""
    return get_service().pool_status()


@app.post("/monitor/slow")
async def record_slow_query(query: str, elapsed_ms: float) -> SlowQueryReport:
    """Record a slow query."""
    service = get_service()
    service.record_slow_query(query, elapsed_ms)
    return service.get_slow_queries()


@app.get("/monitor/slow", response_model=SlowQueryReport)
async def get_slow_queries() -> SlowQueryReport:
    """Get slow query alerts."""
    return get_service().get_slow_queries()


@app.get("/route/read", response_model=RouteResponse)
async def route_read(operation: Optional[str] = None) -> RouteResponse:
    """Route a read operation."""
    return get_service().route_read(RouteRequest(operation=operation or "read"))


@app.get("/route/write", response_model=RouteResponse)
async def route_write(operation: Optional[str] = None) -> RouteResponse:
    """Route a write operation."""
    return get_service().route_write(RouteRequest(operation=operation or "write"))


@app.post("/route/shard", response_model=ShardResponse)
async def route_shard(request: ShardRequest) -> ShardResponse:
    """Route to a shard."""
    return get_service().route_shard(request)


@app.post("/route/database", response_model=DbRouteResponse)
async def route_database(request: DbRouteRequest) -> DbRouteResponse:
    """Route to a database."""
    return get_service().route_database(request)


@app.post("/optimize", response_model=OptimizeResponse)
async def optimize_query(request: OptimizeRequest) -> OptimizeResponse:
    """Optimize a query."""
    return get_service().optimize_query(request)


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
        "create_item": ItemCreate,
        "build_query": QueryRequest,
        "execute_transaction": TransactionRequest,
        "route_read": RouteRequest,
        "route_write": RouteRequest,
        "route_shard": ShardRequest,
        "route_database": DbRouteRequest,
        "optimize_query": OptimizeRequest,
    }
    try:
        request_type = request_types.get(method)
        if request_type is not None and payload:
            filtered = {k: v for k, v in payload.items() if k in request_type.model_fields}
            result = await service.call(method, request=request_type(**filtered))
        else:
            result = await service.call(method, **payload)
        if isinstance(result, list):
            return [r.model_dump() if hasattr(r, "model_dump") else r for r in result]
        if hasattr(result, "model_dump"):
            return result.model_dump()
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
