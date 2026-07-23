# -*- coding: utf-8 -*-
"""Pydantic schemas for the data access microservice."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ServiceHealth(BaseModel):
    """Service health response."""

    status: str
    service: str
    uptime_seconds: int = 0
    index_size: int = 0


class StatsResponse(BaseModel):
    """Service statistics response."""

    total_requests: int
    cache_hits: int
    cache_misses: int
    operations: Dict[str, int] = Field(default_factory=dict)
    index_size: int


class ItemCreate(BaseModel):
    """Create an item."""

    name: str
    value: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ItemUpdate(BaseModel):
    """Update an item."""

    name: Optional[str] = None
    value: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ItemResponse(BaseModel):
    """Item response."""

    id: int
    name: str
    value: str
    metadata: Dict[str, Any]
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class QueryRequest(BaseModel):
    """Build a query."""

    table: str = "items"
    filters: Dict[str, Any] = Field(default_factory=dict)
    sort_by: Optional[str] = "id"
    sort_order: str = "asc"
    page: int = 1
    page_size: int = 10


class QueryResponse(BaseModel):
    """Query build response."""

    table: str
    compiled: str
    filter_count: int
    sort_by: Optional[str]
    page: int
    page_size: int


class TransactionOperation(BaseModel):
    """Single operation within a transaction."""

    op: str = Field(..., description="create, update, or delete")
    table: str = "items"
    data: Dict[str, Any] = Field(default_factory=dict)


class TransactionRequest(BaseModel):
    """Execute a transaction."""

    operations: List[TransactionOperation]
    rollback_on_error: bool = True


class TransactionResponse(BaseModel):
    """Transaction result."""

    success: bool
    results: List[Any]
    rolled_back: bool
    error: Optional[str] = None


class PoolStatus(BaseModel):
    """Connection pool status."""

    size: int
    checked_in: int
    checked_out: int
    overflow: int


class SlowQueryAlert(BaseModel):
    """Slow query alert."""

    query: str
    elapsed_ms: float
    threshold_ms: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class SlowQueryReport(BaseModel):
    """Slow query report."""

    alerts: List[SlowQueryAlert]
    total: int
    threshold_ms: float


class RouteRequest(BaseModel):
    """Read/write route request."""

    operation: str = "read"
    hints: Dict[str, Any] = Field(default_factory=dict)


class RouteResponse(BaseModel):
    """Route target response."""

    target: str
    strategy: str
    operation: str


class ShardRequest(BaseModel):
    """Shard route request."""

    key: str
    strategy: str = "hash"
    shard_count: int = 4


class ShardResponse(BaseModel):
    """Shard route response."""

    shard_index: int
    shard_key: str
    strategy: str
    shard_count: int


class DbRouteRequest(BaseModel):
    """Database route request."""

    database: str = "default"
    strategy: str = "round_robin"
    targets: Optional[List[str]] = None
    weights: Optional[Dict[str, int]] = None


class DbRouteResponse(BaseModel):
    """Database route response."""

    target: str
    strategy: str
    database: str


class IndexSuggestion(BaseModel):
    """Index suggestion."""

    columns: List[str]
    reason: str


class OptimizeRequest(BaseModel):
    """Query optimization request."""

    query: str
    table: str = "items"


class OptimizeResponse(BaseModel):
    """Query optimization response."""

    suggestions: List[IndexSuggestion]
    estimated_improvement: str
    rewritten_query: str


class RpcRequest(BaseModel):
    """RPC request payload wrapper."""

    payload: Optional[Dict[str, Any]] = None


class SortOrder(str, Enum):
    """Sort order."""

    ASC = "asc"
    DESC = "desc"
