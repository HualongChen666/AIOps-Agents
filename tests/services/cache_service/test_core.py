# -*- coding: utf-8 -*-
"""Core tests for the cache microservice."""

from __future__ import annotations

import asyncio

import pytest

from services.cache_service.cache import CacheManager
from services.cache_service.grpc.client import CacheServiceRPCClient
from services.cache_service.grpc.server import CacheServiceRPCServer
from services.cache_service.metrics import MetricsCollector
from services.cache_service.retry import RetryEngine
from services.cache_service.schemas import (
    AvalancheProtectRequest,
    BreakdownProtectRequest,
    CacheGetRequest,
    CachePreheatRequest,
    CacheSetRequest,
    CacheStrategy,
    CacheStrategyRequest,
)
from services.cache_service.service import CacheService


@pytest.fixture
async def service():
    metrics = MetricsCollector("cache_core_test")
    svc = CacheService(metrics=metrics, cache=CacheManager(metrics=metrics))
    await svc.reset()
    yield svc


@pytest.mark.asyncio
async def test_get_set_delete(service: CacheService):
    set_req = CacheSetRequest(key="k1", value="v1")
    assert (await service.set(set_req))["stored"] is True
    get_resp = await service.get(CacheGetRequest(key="k1"))
    assert get_resp.hit is True
    assert get_resp.value == "v1"
    del_resp = await service.delete(CacheGetRequest(key="k1"))
    assert del_resp["deleted"] is True


@pytest.mark.asyncio
async def test_preheat(service: CacheService):
    req = CachePreheatRequest(data={"a": 1, "b": 2}, ttl=60)
    resp = await service.preheat(req)
    assert resp.keys_loaded == 2
    assert (await service.get(CacheGetRequest(key="a"))).value == 1


@pytest.mark.asyncio
async def test_breakdown_protect(service: CacheService):
    req = BreakdownProtectRequest(key="hot", value="hot-value", ttl=60)
    resp = await service.protect_breakdown(req)
    assert resp.locked is True
    assert resp.value == "hot-value"
    # second call should hit cache inside lock
    resp2 = await service.protect_breakdown(req)
    assert resp2.value == "hot-value"


@pytest.mark.asyncio
async def test_avalanche_protect(service: CacheService):
    req = AvalancheProtectRequest(key="ttl-key", value="v", base_ttl=100, jitter_seconds=10)
    resp = await service.protect_avalanche(req)
    assert resp.ttl >= 100
    assert resp.ttl <= 110


@pytest.mark.asyncio
async def test_cache_aside(service: CacheService):
    req = CacheStrategyRequest(strategy=CacheStrategy.CACHE_ASIDE, key="aside", value="x", ttl=60)
    resp = await service.execute_strategy(req)
    assert resp.strategy == "cache-aside"
    # second call hits cache
    resp2 = await service.execute_strategy(req)
    assert resp2.value == "x"


@pytest.mark.asyncio
async def test_write_through(service: CacheService):
    req = CacheStrategyRequest(strategy=CacheStrategy.WRITE_THROUGH, key="wt", value="y", ttl=60)
    resp = await service.execute_strategy(req)
    assert resp.backend_written is True
    assert service.get_backend("wt") == "y"


@pytest.mark.asyncio
async def test_write_behind_and_refresh_ahead(service: CacheService):
    req = CacheStrategyRequest(strategy=CacheStrategy.WRITE_BEHIND, key="wb", value="z", ttl=60)
    resp = await service.execute_strategy(req)
    assert resp.strategy == "write-behind"
    await asyncio.sleep(0.05)
    assert service.get_backend("wb") == "z"

    req2 = CacheStrategyRequest(strategy=CacheStrategy.REFRESH_AHEAD, key="ra", value="w", ttl=60)
    resp2 = await service.execute_strategy(req2)
    assert resp2.strategy == "refresh-ahead"


@pytest.mark.asyncio
async def test_stats(service: CacheService):
    await service.get(CacheGetRequest(key="nope"))
    stats = service.get_cache_stats()
    assert stats.misses >= 1


@pytest.mark.asyncio
async def test_retry_engine():
    engine = RetryEngine("no_retry")
    assert "no_retry" in engine.list_policies()

    async def ok():
        return 1

    assert await engine.execute(ok) == 1


@pytest.mark.asyncio
async def test_rpc_server():
    server = CacheServiceRPCServer()
    server.register("echo", lambda x: x)
    assert "echo" in server.list_methods()
    assert await server.call("echo", x="hi") == "hi"


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

    with patch("services.cache_service.grpc.client.httpx.AsyncClient", return_value=client_mock):
        client = CacheServiceRPCClient(base_url="http://test")
        result = await client.call("stats")
    assert result["ok"] is True


def test_metrics_collector():
    metrics = MetricsCollector("cache_metrics_test")
    metrics.inc_request("get")
    metrics.inc_cache_hit()
    metrics.inc_cache_miss()
    with metrics.time_operation("op"):
        pass
    assert metrics.request_count == 1
    assert metrics.cache_hits_count == 1
    assert metrics.cache_misses_count == 1
