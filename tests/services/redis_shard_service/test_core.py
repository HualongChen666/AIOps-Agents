# -*- coding: utf-8 -*-
"""Core service tests for all shard cluster backends."""

from __future__ import annotations

import uuid

import pytest

from services.redis_shard_service.metrics import MetricsCollector
from services.redis_shard_service.service import ShardClusterService


@pytest.mark.asyncio
async def _exercise_backend(backend: str) -> None:
    service = ShardClusterService(
        backend=backend,
        redis_url="",
        database_url="",
        qdrant_url="",
        metrics=MetricsCollector(f"redis_shard_core_{backend}_{uuid.uuid4().hex[:6]}"),
    )

    cfg = await service.configure_cluster(
        {
            "nodes": [
                {"node_id": f"{backend}-n1", "host": "localhost", "port": 5432},
                {"node_id": f"{backend}-n2", "host": "localhost", "port": 5433},
            ],
            "shard_count": 12,
            "strategy": "hash",
        }
    )
    assert cfg["shards"] == 12

    route = await service.route_key({"key": "test", "strategy": "hash"})
    assert "shard_id" in route

    read_route = await service.route_read({"key": "test"})
    write_route = await service.route_write({"key": "test"})
    assert read_route["shard_id"] == write_route["shard_id"]

    reb = await service.rebalance_cluster({"virtual_nodes": 80})
    assert reb["rebalanced"] is True

    repl = await service.configure_replication({"replication_factor": 3})
    assert repl["replication_factor"] == 3

    ha = await service.configure_ha({"enabled": True})
    assert ha["ha_configured"] is True

    fo = await service.failover({"shard_id": route["shard_id"]})
    assert fo["failover"] is True

    cs = await service.cross_shard_query({"keys": ["a", "b"], "query_type": "get"})
    assert cs["queried"] == 2

    metrics = await service.get_metrics()
    assert metrics["shards"] == 12

    backup = await service.backup({"name": "core_snapshot"})
    assert backup["saved"] is True

    restore = await service.restore({"name": "core_snapshot"})
    assert restore["restored"] is True

    perf = await service.test_performance({"iterations": 100})
    assert perf["status"] == "passed"


@pytest.mark.asyncio
async def test_postgresql_backend():
    await _exercise_backend("postgresql")
    service = ShardClusterService(backend="postgresql", redis_url="")
    range_route = await service.route_key({"key": "x", "strategy": "range"})
    assert range_route["backend"] == "postgresql"


@pytest.mark.asyncio
async def test_redis_backend():
    await _exercise_backend("redis")
    service = ShardClusterService(backend="redis", redis_url="")
    route = await service.route_key({"key": "slotkey"})
    assert route["slot"] is not None and 0 <= route["slot"] < 16384


@pytest.mark.asyncio
async def test_qdrant_backend():
    await _exercise_backend("qdrant")
    service = ShardClusterService(backend="qdrant", redis_url="")
    route = await service.route_key({"vector": [0.1, 0.2, 0.3]})
    assert route["backend"] == "qdrant"


@pytest.mark.asyncio
async def test_call_and_stats():
    service = ShardClusterService(backend="redis", redis_url="")
    methods = service.list_methods()
    assert "route_key" in methods
    stats = service.get_stats()
    assert "total_requests" in stats
    with pytest.raises(ValueError):
        await service.call("unknown_method")
