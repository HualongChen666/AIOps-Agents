# -*- coding: utf-8 -*-
"""Pydantic schemas for the shard cluster microservice."""

from __future__ import annotations

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
    index_size: int = 0


class NodeConfig(BaseModel):
    """Node configuration."""

    node_id: str
    host: str
    port: int = 5432
    role: str = "master"


class ConfigureClusterRequest(BaseModel):
    """Configure a sharded cluster."""

    nodes: List[NodeConfig] = Field(default_factory=list)
    shard_count: int = 10
    strategy: str = "hash"
    replication_factor: int = 1
    virtual_nodes: int = 100


class ConfigureClusterResponse(BaseModel):
    """Configure cluster response."""

    backend: str
    shards: int
    strategy: str


class RouteRequest(BaseModel):
    """Route a key to its shard."""

    key: Optional[str] = None
    vector: Optional[List[float]] = None
    strategy: str = "hash"


class RouteResponse(BaseModel):
    """Route response."""

    backend: str
    shard_id: str
    node_id: str
    host: str
    port: int
    role: str
    slot: Optional[int] = None
    strategy: str


class RebalanceRequest(BaseModel):
    """Rebalance shards request."""

    virtual_nodes: int = 100


class RebalanceResponse(BaseModel):
    """Rebalance response."""

    backend: str
    shards: int
    rebalanced: bool


class ReplicationRequest(BaseModel):
    """Configure replication request."""

    replication_factor: int = 2


class ReplicationResponse(BaseModel):
    """Replication response."""

    replication_factor: int
    shards: int


class HARequest(BaseModel):
    """Configure high availability."""

    enabled: bool = True
    failover_timeout_seconds: int = 5
    mode: Optional[str] = None


class HAResponse(BaseModel):
    """HA response."""

    ha_configured: bool
    config: Dict[str, Any]


class FailoverRequest(BaseModel):
    """Trigger failover."""

    shard_id: Optional[str] = None


class FailoverResponse(BaseModel):
    """Failover response."""

    failover: bool
    shard_id: str = ""
    new_master: str = ""
    error: Optional[str] = None


class CrossShardQueryRequest(BaseModel):
    """Cross-shard query request."""

    keys: List[str] = Field(default_factory=list)
    vectors: Optional[List[List[float]]] = None
    query_type: str = "get"


class CrossShardQueryResponse(BaseModel):
    """Cross-shard query response."""

    backend: str
    queried: int
    results: List[Dict[str, Any]]


class MetricsResponse(BaseModel):
    """Metrics response."""

    backend: str
    shards: int
    nodes: int
    healthy_nodes: int
    replication_factor: int


class BackupRequest(BaseModel):
    """Backup request."""

    name: str = "default"


class BackupResponse(BaseModel):
    """Backup response."""

    snapshot: str
    saved: bool


class RestoreRequest(BaseModel):
    """Restore request."""

    name: str = "default"


class RestoreResponse(BaseModel):
    """Restore response."""

    restored: bool
    snapshot: str
    error: Optional[str] = None


class PerformanceRequest(BaseModel):
    """Performance test request."""

    iterations: int = 1000


class PerformanceResponse(BaseModel):
    """Performance test response."""

    backend: str
    iterations: int
    throughput_per_second: int
    latency_ms: float
    status: str


class RpcRequest(BaseModel):
    """RPC request wrapper."""

    payload: Optional[Dict[str, Any]] = None
