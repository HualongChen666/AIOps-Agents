# -*- coding: utf-8 -*-
"""Database Sharding & PostgreSQL Partitioning API router.

Exposes the real sharding engine in :mod:`core.db_sharding`:

* ``/api/v1/database/sharding/*`` — application-level sharding: manage the
  shard topology, route keys (consistent-hash / modulo / range / list), build
  scatter-gather plans and rebalance the hash ring.
* ``/api/v1/database/postgresql-shard/*`` — PostgreSQL declarative
  partitioning: manage partition definitions, render executable
  ``CREATE TABLE … PARTITION BY …`` DDL and (when the configured database is
  PostgreSQL) apply it.

Every response is derived from the persisted topology or from the submitted
keys — nothing is seeded or fabricated.  A missing topology or missing
PostgreSQL backend yields an explicit error rather than a plausible-looking
fake.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, HTTPException
from pydantic import BaseModel, Field

from core.backend_requirements import requires_backend
from core.db_sharding import (
    ShardStrategy,
    ShardingError,
    ShardingNotConfigured,
    get_partition_manager,
    get_shard_manager,
)
from loguru import logger

router = APIRouter(prefix="/api/v1/database", tags=["Database Sharding"])


# --------------------------------------------------------------------------- #
# Schemas
# --------------------------------------------------------------------------- #
class NodeSpec(BaseModel):
    """A backing node for a shard."""

    node_id: Optional[str] = None
    host: str = "localhost"
    port: int = 5432
    role: str = Field("primary", description="primary | replica")


class ConfigureRequest(BaseModel):
    """Initialise a hash/modulo sharding topology."""

    strategy: str = Field("hash", description="hash | modulo")
    shard_count: int = Field(2, ge=1, le=1024)
    shard_key: str = "id"
    table_name: Optional[str] = None
    virtual_nodes: int = Field(128, ge=1, le=4096)
    nodes: List[NodeSpec] = Field(default_factory=list)
    replace: bool = True


class ShardSpec(BaseModel):
    """An explicitly-defined shard (required for range/list)."""

    shard_id: Optional[str] = None
    name: Optional[str] = None
    strategy: Optional[str] = None
    range_start: Optional[str] = None
    range_end: Optional[str] = None
    values: List[str] = Field(default_factory=list)
    nodes: List[NodeSpec] = Field(default_factory=list)


class RouteRequest(BaseModel):
    """Route one key to its shard."""

    key: str


class BatchKeysRequest(BaseModel):
    """Route many keys at once."""

    keys: List[str] = Field(default_factory=list)


class RebalanceRequest(BaseModel):
    """Rebalance the hash ring."""

    keys: List[str] = Field(default_factory=list)
    virtual_nodes: Optional[int] = Field(None, ge=1, le=4096)


class PartitionSpec(BaseModel):
    """A declarative partition definition."""

    name: str
    modulus: Optional[int] = None
    remainder: Optional[int] = None
    range_from: Optional[str] = None
    range_to: Optional[str] = None
    values: List[str] = Field(default_factory=list)


class ColumnSpec(BaseModel):
    """A column definition used when rendering DDL."""

    name: str
    type: str = "TEXT"


class PartitionPlanRequest(BaseModel):
    """Configure a PostgreSQL declarative-partitioning plan."""

    table: str
    strategy: str = Field("hash", description="hash | range | list")
    column: str
    column_type: str = "BIGINT"
    schema: str = "public"
    columns: List[ColumnSpec] = Field(default_factory=list)
    partitions: Optional[List[PartitionSpec]] = None
    partition_count: int = Field(4, ge=1, le=1024)


def _handle(exc: Exception) -> HTTPException:
    if isinstance(exc, ShardingNotConfigured):
        return HTTPException(status_code=409, detail=str(exc))
    return HTTPException(status_code=400, detail=str(exc))


# --------------------------------------------------------------------------- #
# Application-level sharding
# --------------------------------------------------------------------------- #
@router.get("/sharding/status", summary="Sharding topology status")
async def sharding_status() -> Dict[str, Any]:
    """Return the persisted sharding topology and its routing-index size."""
    return get_shard_manager().status()


@router.get("/sharding/shards", summary="List shards")
async def list_shards() -> Dict[str, Any]:
    manager = get_shard_manager()
    return {
        "configured": manager.configured,
        "shard_count": len(manager.list_shards()),
        "shards": manager.list_shards(),
    }


@router.post("/sharding/configure", summary="Configure a hash/modulo topology")
async def configure_sharding(request: ConfigureRequest) -> Dict[str, Any]:
    try:
        return get_shard_manager().configure(
            strategy=request.strategy,
            shard_count=request.shard_count,
            shard_key=request.shard_key,
            table_name=request.table_name,
            virtual_nodes=request.virtual_nodes,
            nodes=[n.model_dump() for n in request.nodes],
            replace=request.replace,
        )
    except ShardingError as exc:
        raise _handle(exc)
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("configure_sharding failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/sharding/shards", summary="Add a shard")
async def add_shard(request: ShardSpec) -> Dict[str, Any]:
    try:
        payload = request.model_dump()
        payload["nodes"] = [n for n in payload.get("nodes") or []]
        return get_shard_manager().add_shard(payload)
    except ShardingError as exc:
        raise _handle(exc)
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("add_shard failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.delete("/sharding/shards/{shard_id}", summary="Remove a shard")
async def remove_shard(shard_id: str) -> Dict[str, Any]:
    try:
        return get_shard_manager().remove_shard(shard_id)
    except ShardingError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/sharding/route", summary="Route a key to its shard")
async def route_key(request: RouteRequest) -> Dict[str, Any]:
    try:
        return get_shard_manager().route(request.key).to_dict()
    except ShardingError as exc:
        raise _handle(exc)


@router.post("/sharding/route/batch", summary="Route a batch of keys")
async def route_batch(request: BatchKeysRequest) -> Dict[str, Any]:
    try:
        return get_shard_manager().route_batch(request.keys)
    except ShardingError as exc:
        raise _handle(exc)


@router.post("/sharding/scatter-plan", summary="Build a scatter/gather plan")
async def scatter_plan(request: BatchKeysRequest) -> Dict[str, Any]:
    try:
        return get_shard_manager().scatter_plan(request.keys)
    except ShardingError as exc:
        raise _handle(exc)


@router.post("/sharding/rebalance", summary="Rebalance the hash ring")
async def rebalance(request: RebalanceRequest) -> Dict[str, Any]:
    try:
        return get_shard_manager().rebalance(
            keys=request.keys or None, virtual_nodes=request.virtual_nodes
        )
    except ShardingError as exc:
        raise _handle(exc)


@router.get("/sharding/health", summary="Probe every shard node")
async def sharding_health() -> Dict[str, Any]:
    return await get_shard_manager().health()


@router.delete("/sharding", summary="Reset the sharding topology")
async def reset_sharding() -> Dict[str, Any]:
    manager = get_shard_manager()
    manager.reset()
    return {"reset": True, "status": manager.status()}


# --------------------------------------------------------------------------- #
# PostgreSQL declarative partitioning
# --------------------------------------------------------------------------- #
@router.get("/postgresql-shard/plan", summary="Current partition plan")
async def get_partition_plan() -> Dict[str, Any]:
    return get_partition_manager().plan()


@router.post("/postgresql-shard/plan", summary="Configure a partition plan")
async def configure_partition_plan(request: PartitionPlanRequest) -> Dict[str, Any]:
    try:
        return get_partition_manager().configure(
            table=request.table,
            strategy=request.strategy,
            column=request.column,
            column_type=request.column_type,
            schema=request.schema,
            columns=[c.model_dump() for c in request.columns],
            partitions=(
                [p.model_dump() for p in request.partitions]
                if request.partitions is not None
                else None
            ),
            partition_count=request.partition_count,
        )
    except ShardingError as exc:
        raise _handle(exc)
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("configure_partition_plan failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.delete("/postgresql-shard/plan", summary="Reset the partition plan")
async def reset_partition_plan() -> Dict[str, Any]:
    manager = get_partition_manager()
    manager.reset()
    return {"reset": True, "plan": manager.plan()}


@router.get("/postgresql-shard/partitions", summary="List partitions")
async def list_partitions() -> Dict[str, Any]:
    manager = get_partition_manager()
    plan = manager.plan()
    return {
        "configured": plan["configured"],
        "strategy": plan["strategy"],
        "table": plan["table"],
        "partition_count": len(manager.list_partitions()),
        "partitions": manager.list_partitions(),
    }


@router.post("/postgresql-shard/partitions", summary="Add a partition")
async def add_partition(request: PartitionSpec) -> Dict[str, Any]:
    try:
        return get_partition_manager().add_partition(request.model_dump())
    except ShardingError as exc:
        raise _handle(exc)


@router.delete("/postgresql-shard/partitions/{name}", summary="Remove a partition")
async def remove_partition(name: str) -> Dict[str, Any]:
    try:
        return get_partition_manager().remove_partition(name)
    except ShardingError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/postgresql-shard/ddl", summary="Render partitioning DDL")
async def get_partition_ddl() -> Dict[str, Any]:
    manager = get_partition_manager()
    try:
        ddl = manager.generate_ddl()
    except ShardingError as exc:
        raise _handle(exc)
    return {"plan": manager.plan(), "ddl": ddl}


class ApplyDdlRequest(BaseModel):
    """Optional: apply DDL to the configured PostgreSQL database."""

    ddl: Optional[str] = None


@router.post("/postgresql-shard/apply", summary="Apply partitioning DDL (PostgreSQL only)")
async def apply_partition_ddl(request: ApplyDdlRequest = Body(default=ApplyDdlRequest())) -> Dict[str, Any]:
    """Execute the plan's DDL against the configured database.

    Only a PostgreSQL backend can execute ``PARTITION BY`` DDL; on any other
    dialect the endpoint returns the canonical ``requires-backend`` marker
    instead of pretending the statement ran.
    """
    from core.database import engine

    if engine.dialect.name != "postgresql":
        requires_backend(
            "postgresql",
            capability="postgresql declarative partitioning",
            reason=(
                f"the configured database dialect is '{engine.dialect.name}'; "
                "PARTITION BY DDL requires PostgreSQL"
            ),
        )

    manager = get_partition_manager()
    try:
        ddl = request.ddl or manager.generate_ddl()
    except ShardingError as exc:
        raise _handle(exc)

    statements = [s.strip() for s in _split_sql(ddl) if s.strip()]
    from sqlalchemy import text

    executed: List[str] = []
    try:
        with engine.begin() as conn:
            for statement in statements:
                conn.execute(text(statement))
                executed.append(statement.splitlines()[0])
    except Exception as exc:
        logger.error("apply_partition_ddl failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"DDL execution failed: {exc}")
    return {"applied": True, "statements_executed": len(executed), "statements": executed}


def _split_sql(ddl: str) -> List[str]:
    """Split a DDL script on statement-terminating semicolons (comment-safe)."""
    statements: List[str] = []
    current: List[str] = []
    for line in ddl.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("--"):
            continue
        current.append(line)
        if stripped.endswith(";"):
            statements.append("\n".join(current))
            current = []
    if current:
        statements.append("\n".join(current))
    return [s[:-1] if s.rstrip().endswith(";") else s for s in statements]


__all__ = ["router"]
