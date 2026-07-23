# -*- coding: utf-8 -*-
"""FastAPI application for the shard cluster microservice."""

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
    BackupRequest,
    BackupResponse,
    ConfigureClusterRequest,
    ConfigureClusterResponse,
    CrossShardQueryRequest,
    CrossShardQueryResponse,
    FailoverRequest,
    FailoverResponse,
    HARequest,
    HAResponse,
    MetricsResponse,
    PerformanceRequest,
    PerformanceResponse,
    RebalanceRequest,
    RebalanceResponse,
    ReplicationRequest,
    ReplicationResponse,
    RestoreRequest,
    RestoreResponse,
    RouteRequest,
    RouteResponse,
    ServiceHealth,
    StatsResponse,
)
from .service import ShardClusterService

_service: Optional[ShardClusterService] = None
_metrics = MetricsCollector(settings.service_name)


def get_service() -> ShardClusterService:
    """Return the shard cluster service singleton."""
    global _service
    if _service is None:
        _service = ShardClusterService(
            backend=settings.backend,
            redis_url=settings.redis_url,
            database_url=settings.database_url,
            qdrant_url=settings.qdrant_url,
            metrics=_metrics,
            retry_engine=RetryEngine("exponential_fast", _metrics),
            cache=CacheManager(settings.redis_url, _metrics),
        )
    return _service


app = FastAPI(
    title="Qdrant Shard Cluster Service",
    description="Sharded cluster microservice for Qdrant.",
    version="0.1.0",
)


@app.get("/health", response_model=ServiceHealth)
async def health() -> ServiceHealth:
    """Health check endpoint."""
    service = get_service()
    return await HealthCheckEngine().check(settings.service_name, len(service.shards))


@app.get("/metrics")
async def metrics() -> Response:
    """Prometheus metrics endpoint."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/stats", response_model=StatsResponse)
async def stats() -> StatsResponse:
    """Service statistics."""
    return StatsResponse(**get_service().get_stats())


@app.post("/shards/configure", response_model=ConfigureClusterResponse)
async def configure_cluster(request: ConfigureClusterRequest) -> ConfigureClusterResponse:
    """Configure the sharded cluster."""
    data = await get_service().configure_cluster(request)
    return ConfigureClusterResponse(**data)


@app.post("/shards/route", response_model=RouteResponse)
async def route_key(request: RouteRequest) -> RouteResponse:
    """Route a key to its shard and node."""
    data = await get_service().route_key(request)
    return RouteResponse(**data)


@app.post("/shards/route/read", response_model=RouteResponse)
async def route_read(request: RouteRequest) -> RouteResponse:
    """Route a read to a replica or primary."""
    data = await get_service().route_read(request)
    return RouteResponse(**data)


@app.post("/shards/route/write", response_model=RouteResponse)
async def route_write(request: RouteRequest) -> RouteResponse:
    """Route a write to the primary."""
    data = await get_service().route_write(request)
    return RouteResponse(**data)


@app.post("/shards/rebalance", response_model=RebalanceResponse)
async def rebalance_cluster(request: RebalanceRequest) -> RebalanceResponse:
    """Rebalance shards/slots/ring."""
    data = await get_service().rebalance_cluster(request)
    return RebalanceResponse(**data)


@app.post("/replication/configure", response_model=ReplicationResponse)
async def configure_replication(request: ReplicationRequest) -> ReplicationResponse:
    """Configure master-replica replication."""
    data = await get_service().configure_replication(request)
    return ReplicationResponse(**data)


@app.post("/ha/configure", response_model=HAResponse)
async def configure_ha(request: HARequest) -> HAResponse:
    """Configure high availability (Patroni/Sentinel/Raft)."""
    data = await get_service().configure_ha(request)
    return HAResponse(**data)


@app.post("/failover", response_model=FailoverResponse)
async def failover(request: FailoverRequest) -> FailoverResponse:
    """Trigger a failover."""
    data = await get_service().failover(request)
    return FailoverResponse(**data)


@app.post("/cross_shard/query", response_model=CrossShardQueryResponse)
async def cross_shard_query(request: CrossShardQueryRequest) -> CrossShardQueryResponse:
    """Execute a cross-shard scatter/gather query."""
    data = await get_service().cross_shard_query(request)
    return CrossShardQueryResponse(**data)


@app.get("/monitor", response_model=MetricsResponse)
async def get_monitor() -> MetricsResponse:
    """Get current cluster metrics."""
    data = await get_service().get_metrics()
    return MetricsResponse(**data)


@app.post("/backup", response_model=BackupResponse)
async def backup(request: BackupRequest) -> BackupResponse:
    """Create a metadata snapshot."""
    data = await get_service().backup(request)
    return BackupResponse(**data)


@app.post("/restore", response_model=RestoreResponse)
async def restore(request: RestoreRequest) -> RestoreResponse:
    """Restore from a metadata snapshot."""
    data = await get_service().restore(request)
    return RestoreResponse(**data)


@app.post("/performance", response_model=PerformanceResponse)
async def test_performance(request: PerformanceRequest) -> PerformanceResponse:
    """Run a performance smoke test."""
    data = await get_service().test_performance(request)
    return PerformanceResponse(**data)


@app.post("/rpc/{method}")
async def rpc(method: str, payload: Optional[Dict[str, Any]] = Body(default=None)) -> Any:
    """Generic RPC dispatcher."""
    payload = payload or {}
    service = get_service()
    if method == "list_methods":
        return service.list_methods()
    if method == "stats":
        return service.get_stats()
    if method not in service.list_methods():
        raise HTTPException(status_code=404, detail=f"Unknown RPC method: {method}")
    try:
        result = await service.call(method, request=payload)
        if hasattr(result, "model_dump"):
            return result.model_dump()
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
