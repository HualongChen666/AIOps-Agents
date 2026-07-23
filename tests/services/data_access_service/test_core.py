# -*- coding: utf-8 -*-
"""Core service tests for the data access microservice."""

from __future__ import annotations

import pytest

from services.data_access_service.cache import CacheManager
from services.data_access_service.grpc.client import DataAccessServiceRPCClient
from services.data_access_service.grpc.server import DataAccessServiceRPCServer
from services.data_access_service.metrics import MetricsCollector
from services.data_access_service.retry import RetryEngine
from services.data_access_service.schemas import (
    DbRouteRequest,
    OptimizeRequest,
    QueryRequest,
    RouteRequest,
    ShardRequest,
    TransactionOperation,
    TransactionRequest,
)
from services.data_access_service.service import DataAccessService, ItemCreate, ItemUpdate


@pytest.fixture
async def service():
    """Provide a fresh in-memory DataAccessService."""
    metrics = MetricsCollector("data_access_core_test")
    cache = CacheManager(metrics=metrics)
    svc = DataAccessService(
        database_url="sqlite+aiosqlite:///:memory:",
        redis_url="",
        metrics=metrics,
        cache=cache,
    )
    await svc.initialize()
    await svc.reset()
    yield svc
    await svc.engine.dispose()


@pytest.mark.asyncio
async def test_orm_crud(service: DataAccessService):
    created = await service.create_item(ItemCreate(name="foo", value="bar"))
    assert created.name == "foo"

    fetched = await service.get_item(created.id)
    assert fetched is not None
    assert fetched.name == "foo"

    updated = await service.update_item(created.id, ItemUpdate(name="baz"))
    assert updated is not None
    assert updated.name == "baz"

    listed = await service.list_items(filters={"name": "baz"})
    assert listed["total"] == 1

    deleted = await service.delete_item(created.id)
    assert deleted is True
    assert await service.get_item(created.id) is None


@pytest.mark.asyncio
async def test_cache_hit(service: DataAccessService):
    created = await service.create_item(ItemCreate(name="cached", value="v"))
    first = await service.get_item(created.id)
    assert first is not None
    # second fetch should hit the in-memory cache
    second = await service.get_item(created.id)
    assert second is not None
    assert service.metrics.cache_hits_count >= 1


@pytest.mark.asyncio
async def test_query_builder(service: DataAccessService):
    req = QueryRequest(filters={"name": "x"}, sort_by="id", sort_order="asc", page=1, page_size=5)
    result = service.build_query(req)
    assert "items" in result.compiled.lower()
    assert result.filter_count == 1


@pytest.mark.asyncio
async def test_transaction_update_and_delete(service: DataAccessService):
    created = await service.create_item(ItemCreate(name="txn", value="1"))
    req = TransactionRequest(
        operations=[
            TransactionOperation(
                op="update",
                table="items",
                data={"id": created.id, "name": "txn-updated", "value": "2"},
            )
        ]
    )
    resp = await service.execute_transaction(req)
    assert resp.success is True
    assert len(resp.results) == 1

    req2 = TransactionRequest(
        operations=[TransactionOperation(op="delete", table="items", data={"id": created.id})]
    )
    resp2 = await service.execute_transaction(req2)
    assert resp2.success is True


@pytest.mark.asyncio
async def test_transaction_rollback(service: DataAccessService):
    req = TransactionRequest(
        operations=[
            TransactionOperation(op="unknown", table="items", data={}),
        ]
    )
    resp = await service.execute_transaction(req)
    assert resp.success is False
    assert resp.rolled_back is True


@pytest.mark.asyncio
async def test_slow_query_monitor(service: DataAccessService):
    service.set_slow_query_threshold(50.0)
    service.record_slow_query("SELECT * FROM slow", 100.0)
    report = service.get_slow_queries()
    assert report.total == 1
    assert report.alerts[0].query == "SELECT * FROM slow"


@pytest.mark.asyncio
async def test_routing(service: DataAccessService):
    read = service.route_read(RouteRequest(operation="read"))
    assert read.operation == "read"
    write = service.route_write(RouteRequest(operation="write"))
    assert write.operation == "write"


@pytest.mark.asyncio
async def test_shard_routing(service: DataAccessService):
    hash_route = service.route_shard(ShardRequest(key="abc", strategy="hash", shard_count=8))
    assert 0 <= hash_route.shard_index < 8

    range_route = service.route_shard(ShardRequest(key="100", strategy="range", shard_count=4))
    assert 0 <= range_route.shard_index < 4


@pytest.mark.asyncio
async def test_database_router(service: DataAccessService):
    req = DbRouteRequest(
        database="default",
        strategy="round_robin",
        targets=["primary", "replica1", "replica2"],
    )
    targets = [service.route_database(req).target for _ in range(6)]
    assert set(targets) == {"primary", "replica1", "replica2"}

    weighted = DbRouteRequest(
        database="default",
        strategy="weighted",
        targets=["primary", "replica1"],
        weights={"primary": 3, "replica1": 1},
    )
    assert service.route_database(weighted).target in ["primary", "replica1"]

    random_req = DbRouteRequest(
        database="default",
        strategy="random",
        targets=["primary", "replica1"],
    )
    assert service.route_database(random_req).target in ["primary", "replica1"]


@pytest.mark.asyncio
async def test_optimizer(service: DataAccessService):
    req = OptimizeRequest(
        query="SELECT * FROM items WHERE name = 'x' ORDER BY id",
        table="items",
    )
    result = service.optimize_query(req)
    assert len(result.suggestions) >= 1
    assert "LIMIT" in result.rewritten_query.upper()


@pytest.mark.asyncio
async def test_pool_status(service: DataAccessService):
    status = service.pool_status()
    assert status.size >= 0


@pytest.mark.asyncio
async def test_list_methods(service: DataAccessService):
    methods = service.list_methods()
    assert "create_item" in methods
    assert "optimize_query" in methods


@pytest.mark.asyncio
async def test_cache_manager():
    metrics = MetricsCollector("cache_manager_test")
    cache = CacheManager(metrics=metrics)
    assert await cache.get("missing") is None
    assert metrics.cache_misses_count == 1
    await cache.set("key", {"value": 42}, ttl=60)
    assert await cache.get("key") == {"value": 42}
    assert metrics.cache_hits_count == 1
    await cache.delete("key")
    assert await cache.get("key") is None
    await cache.set("a", 1)
    await cache.set("b", 2)
    await cache.clear()
    assert await cache.get("a") is None


@pytest.mark.asyncio
async def test_retry_engine_success():
    engine = RetryEngine("no_retry")
    assert "no_retry" in engine.list_policies()

    async def success():
        return 42

    result = await engine.execute(success)
    assert result == 42


@pytest.mark.asyncio
async def test_retry_engine_with_retry():
    from unittest.mock import AsyncMock

    engine = RetryEngine("exponential_fast")
    fn = AsyncMock(side_effect=[Exception("retryable failure"), "ok"])
    result = await engine.execute(fn, operation="test")
    assert result == "ok"
    assert fn.await_count == 2


@pytest.mark.asyncio
async def test_retry_engine_non_retryable():
    from unittest.mock import AsyncMock

    engine = RetryEngine("exponential_fast")
    fn = AsyncMock(side_effect=Exception("fatal"))
    with pytest.raises(Exception):
        await engine.execute(fn)


@pytest.mark.asyncio
async def test_retry_jitter_delay():
    engine = RetryEngine("jitter")
    policy = engine.policies["jitter"]
    delay = engine._compute_delay(1, policy)
    assert policy.base_delay_seconds / 2 <= delay <= policy.max_delay_seconds


@pytest.mark.asyncio
async def test_rpc_server():
    server = DataAccessServiceRPCServer()
    server.register("echo", lambda x: x)
    server.register("async_echo", lambda x: x)
    assert "echo" in server.list_methods()
    assert await server.call("echo", x="hello") == "hello"
    with pytest.raises(ValueError):
        await server.call("missing")


@pytest.mark.asyncio
async def test_rpc_client():
    from unittest.mock import AsyncMock, MagicMock, patch

    response = MagicMock()
    response.json.return_value = {"ok": True}
    response.raise_for_status.return_value = None
    client_mock = MagicMock()
    client_mock.__aenter__ = AsyncMock(return_value=client_mock)
    client_mock.__aexit__ = AsyncMock(return_value=None)
    client_mock.post = AsyncMock(return_value=response)

    with patch(
        "services.data_access_service.grpc.client.httpx.AsyncClient",
        return_value=client_mock,
    ):
        client = DataAccessServiceRPCClient(base_url="http://test")
        result = await client.call("stats")
    assert result["ok"] is True
    client_mock.post.assert_awaited_once_with("http://test/rpc/stats", json={})


def test_metrics_collector():
    metrics = MetricsCollector("metrics_test")
    metrics.inc_request("op")
    metrics.inc_cache_hit()
    metrics.inc_cache_miss()
    metrics.inc_failure("op", "err")
    metrics.observe_batch_size("op", 5)
    metrics.inc_operation("op")
    with metrics.time_operation("timed"):
        pass
    assert metrics.request_count == 1
    assert metrics.cache_hits_count == 1
    assert metrics.cache_misses_count == 1
