# -*- coding: utf-8 -*-
"""Database High-Availability API router.

Exposes the real database HA capabilities that already live in
:mod:`core.db_replication` and :mod:`core.db_read_write_router`:

* ``/api/v1/database/replication/*`` — configure master/replica replication,
  read the replication status and run real TCP health checks against the
  configured primary/replicas.
* ``/api/v1/database/failover/*`` — inspect failover readiness, trigger a
  failover to a healthy replica and read the durable failover history.
* ``/api/v1/database/read-write-routing/*`` — configure the read/write router,
  classify & route a SQL statement and read live routing statistics.

Nothing is simulated: replication status reflects the configured topology,
node health is the result of an actual TCP connect, the read/write decision is
computed by :class:`~core.db_read_write_router.ReadWriteRouter` and failover
history only records events that really happened.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from core import db_replication
from core.db_read_write_router import ReplicaState, get_read_write_router
from core.persistent_store import PersistentStore
from loguru import logger

router = APIRouter(prefix="/api/v1/database", tags=["Database HA"])

#: Durable failover history (only real, executed failovers are recorded).
_failover_events: PersistentStore = PersistentStore("db_ha", "failover_events")

#: Read/write router configuration + live instance.
_router_store: PersistentStore = PersistentStore("db_ha", "read_write_router")
_rw_router = None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_rw_router():
    global _rw_router
    if _rw_router is not None:
        return _rw_router
    config = _router_store.get("config")
    _rw_router = get_read_write_router(dict(config) if config else None)
    return _rw_router


# --------------------------------------------------------------------------- #
# Schemas
# --------------------------------------------------------------------------- #
class ReplicaConfig(BaseModel):
    """A replica endpoint."""

    host: str
    port: int = 5432
    database: Optional[str] = None
    username: Optional[str] = None


class PrimaryConfig(BaseModel):
    """The primary endpoint."""

    host: str
    port: int = 5432
    database: Optional[str] = None
    username: Optional[str] = None


class ReplicationConfigureRequest(BaseModel):
    """Configure replication."""

    primary: PrimaryConfig
    replicas: List[ReplicaConfig] = Field(default_factory=list)
    read_write_splitting: bool = False
    failover_enabled: bool = False


class PromoteRequest(BaseModel):
    """Promote a replica to primary by index."""

    replica_index: int = Field(0, ge=0)


class ReadWriteRouterConfigRequest(BaseModel):
    """Configure the read/write router."""

    primary_host: str = "localhost"
    primary_port: int = 5432
    replicas: List[ReplicaConfig] = Field(default_factory=list)
    read_write_splitting_enabled: bool = True
    lag_threshold: float = 5.0
    load_balancing_method: str = "round_robin"
    health_check_interval: int = 10


class RouteQueryRequest(BaseModel):
    """Route a SQL statement."""

    query: str


class SplittingRequest(BaseModel):
    """Toggle read/write splitting."""

    enabled: bool = True


class ReplicaStateRequest(BaseModel):
    """Update a replica's state/lag/connections."""

    state: str = "healthy"
    lag: Optional[float] = None
    connections: Optional[int] = None


# --------------------------------------------------------------------------- #
# Replication
# --------------------------------------------------------------------------- #
@router.get("/replication/status", summary="Replication status")
async def replication_status() -> Dict[str, Any]:
    status = db_replication.get_replication_status()
    status["current_primary"] = db_replication.get_current_primary()
    return status


@router.post("/replication/configure", summary="Configure replication")
async def configure_replication(request: ReplicationConfigureRequest) -> Dict[str, Any]:
    db_replication.configure_replication(
        primary_config=request.primary.model_dump(),
        replicas_config=[r.model_dump() for r in request.replicas],
        read_write_splitting=request.read_write_splitting,
        failover_enabled=request.failover_enabled,
    )
    return db_replication.get_replication_status()


@router.get("/replication/health", summary="Real health checks for primary + replicas")
async def replication_health() -> Dict[str, Any]:
    if not db_replication.is_replication_enabled():
        raise HTTPException(status_code=409, detail="replication is not configured")
    health = await db_replication.check_all_replicas_health()
    return {"health": health, "healthy_replicas": db_replication.get_healthy_replicas()}


# --------------------------------------------------------------------------- #
# Failover
# --------------------------------------------------------------------------- #
def _record_failover(event: Dict[str, Any]) -> None:
    events = list(_failover_events.values())
    _failover_events[f"failover-{len(events) + 1}"] = event


@router.get("/failover/status", summary="Failover readiness")
async def failover_status() -> Dict[str, Any]:
    status = db_replication.get_replication_status()
    return {
        "failover_enabled": status["failover_enabled"],
        "current_primary": status["current_primary"],
        "replica_count": status["replica_count"],
        "healthy_replicas": db_replication.get_healthy_replicas(),
        "health_status": status["health_status"],
        "ready": bool(status["failover_enabled"] and db_replication.get_healthy_replicas()),
    }


@router.post("/failover/execute", summary="Trigger failover to a healthy replica")
async def execute_failover() -> Dict[str, Any]:
    if not db_replication.is_replication_enabled():
        raise HTTPException(status_code=409, detail="replication is not configured")
    if not db_replication.is_failover_enabled():
        raise HTTPException(status_code=409, detail="failover is not enabled")

    # Refresh health first so the decision uses current data.
    await db_replication.check_all_replicas_health()
    previous = db_replication.get_current_primary()
    success = await db_replication.perform_failover()
    new_primary = db_replication.get_current_primary()
    event = {
        "timestamp": _now(),
        "success": success,
        "previous_primary": previous,
        "new_primary": new_primary if success else previous,
        "healthy_replicas": db_replication.get_healthy_replicas(),
    }
    _record_failover(event)
    if not success:
        raise HTTPException(
            status_code=409,
            detail={"message": "failover could not complete", "event": event},
        )
    return event


@router.post("/failover/promote", summary="Promote a replica to primary")
async def promote_replica(request: PromoteRequest) -> Dict[str, Any]:
    if not db_replication.is_replication_enabled():
        raise HTTPException(status_code=409, detail="replication is not configured")
    replicas = db_replication.get_replica_configs()
    if request.replica_index >= len(replicas):
        raise HTTPException(
            status_code=404, detail=f"replica index {request.replica_index} is not configured"
        )
    previous = db_replication.get_current_primary()
    success = await db_replication.promote_replica_to_primary(request.replica_index)
    event = {
        "timestamp": _now(),
        "success": success,
        "previous_primary": previous,
        "new_primary": db_replication.get_current_primary(),
        "replica_index": request.replica_index,
    }
    _record_failover(event)
    if not success:
        raise HTTPException(
            status_code=409,
            detail={"message": "promotion failed (failover disabled?)", "event": event},
        )
    return event


@router.get("/failover/history", summary="Durable failover history")
async def failover_history() -> Dict[str, Any]:
    events = [dict(v) for v in _failover_events.values()]
    events.sort(key=lambda e: e.get("timestamp", ""), reverse=True)
    return {"count": len(events), "events": events}


# --------------------------------------------------------------------------- #
# Read/write routing
# --------------------------------------------------------------------------- #
@router.get("/read-write-routing/stats", summary="Live routing statistics")
async def routing_stats() -> Dict[str, Any]:
    return _load_rw_router().get_routing_stats()


@router.post("/read-write-routing/configure", summary="Configure the read/write router")
async def configure_routing(request: ReadWriteRouterConfigRequest) -> Dict[str, Any]:
    global _rw_router
    config = request.model_dump()
    config["replicas"] = [
        {"host": r.host, "port": r.port} for r in request.replicas
    ]
    _router_store["config"] = config
    _rw_router = get_read_write_router(config)
    return _rw_router.get_routing_stats()


@router.post("/read-write-routing/route", summary="Classify and route a SQL statement")
async def route_query(request: RouteQueryRequest) -> Dict[str, Any]:
    rw = _load_rw_router()
    decision = rw.route_query(request.query)
    return {
        "target_host": decision.target_host,
        "target_port": decision.target_port,
        "query_type": decision.query_type.value,
        "replica_used": decision.replica_used,
        "routing_reason": decision.routing_reason,
        "metadata": decision.metadata,
    }


@router.post("/read-write-routing/splitting", summary="Enable/disable read-write splitting")
async def toggle_splitting(request: SplittingRequest) -> Dict[str, Any]:
    rw = _load_rw_router()
    rw.enable_read_write_splitting(request.enabled)
    return rw.get_routing_stats()


@router.post("/read-write-routing/replicas/{replica_id}", summary="Update a replica's state")
async def update_replica_state(replica_id: str, request: ReplicaStateRequest) -> Dict[str, Any]:
    rw = _load_rw_router()
    try:
        state = ReplicaState(request.state)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"invalid state {request.state!r}; expected one of "
            f"{[s.value for s in ReplicaState]}",
        )
    if replica_id not in rw.replicas:
        raise HTTPException(status_code=404, detail=f"unknown replica: {replica_id}")
    rw.update_replica_state(replica_id, state, lag=request.lag, connections=request.connections)
    return rw.get_routing_stats()


__all__ = ["router"]
