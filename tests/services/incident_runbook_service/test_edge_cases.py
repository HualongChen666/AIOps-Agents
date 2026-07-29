# -*- coding: utf-8 -*-
"""Edge-case and gRPC coverage tests for the Incident Runbook microservice."""

from __future__ import annotations

import uuid
from unittest import mock

import httpx
import pytest

import services.incident_runbook_service.grpc.client as grpc_client_module
from services.incident_runbook_service import config
from services.incident_runbook_service import main_app as main_module
from services.incident_runbook_service.cache import CacheManager
from services.incident_runbook_service.grpc.client import IncidentRunbookServiceRPCClient
from services.incident_runbook_service.grpc.server import IncidentRunbookServiceRPCServer
from services.incident_runbook_service.main_app import app, get_service
from services.incident_runbook_service.metrics import MetricsCollector
from services.incident_runbook_service.retry import RetryEngine
from services.incident_runbook_service.service import OPERATIONS, Service


@pytest.fixture
async def reset_app_service():
    """Reset the FastAPI singleton before/after edge-case tests."""
    config.settings.redis_url = ""
    metrics = MetricsCollector(f"incident_runbook_edge_{uuid.uuid4().hex[:6]}")
    service = Service(redis_url="", metrics=metrics)
    main_module._service = service
    yield service
    main_module._service = service


class _FakeRedis:
    """In-memory fake Redis that optionally fails."""

    def __init__(self, fail: bool = False):
        self._data: dict[str, str] = {}
        self._fail = fail

    async def get(self, key: str) -> str | None:
        if self._fail:
            raise ConnectionError("redis down")
        return self._data.get(key)

    async def setex(self, key: str, ttl: int, value: str) -> None:
        if self._fail:
            raise ConnectionError("redis down")
        self._data[key] = value

    async def delete(self, key: str) -> None:
        if self._fail:
            raise ConnectionError("redis down")
        self._data.pop(key, None)

    async def flushdb(self) -> None:
        if self._fail:
            raise ConnectionError("redis down")
        self._data.clear()


class _FakeAioredis:
    """Factory used to monkey-patch redis.asyncio."""

    def __init__(self, redis: _FakeRedis | None = None):
        self._redis = redis or _FakeRedis()

    def from_url(self, url: str, *, decode_responses: bool = True) -> _FakeRedis:
        return self._redis


@pytest.mark.asyncio
async def test_get_service_initializes_singleton():
    """Cover main_app.get_service when _service is None."""
    previous = main_module._service
    main_module._service = None
    try:
        svc = get_service()
        assert isinstance(svc, Service)
        assert main_module._service is svc
    finally:
        main_module._service = previous


@pytest.mark.asyncio
async def test_main_app_unknown_endpoint(reset_app_service):
    """Cover dispatch 404 branch."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/incident-runbook/unknown-feature", json={})
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_main_app_rpc_stats_and_unknown(reset_app_service):
    """Cover rpc stats branch and exception handler."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        stats_resp = await client.post("/rpc/stats")
        assert stats_resp.status_code == 200
        assert "total_requests" in stats_resp.json()

        err_resp = await client.post("/rpc/unknown_method", json={})
        assert err_resp.status_code == 500


@pytest.mark.asyncio
async def test_get_config_edge_cases():
    """Cover _get_config branches for None, non-dict and model_dump."""
    service = Service(redis_url="")
    assert service._get_config(None) == {}
    assert service._get_config("not a dict") == {}

    class _Model:
        def model_dump(self):
            return {"key": "value"}

    assert service._get_config(_Model()) == {"key": "value"}
    assert service._get_config({"config": {"nested": True}}) == {"nested": True}

    class _BadModel:
        def model_dump(self):
            return "not a dict"

    assert service._get_config(_BadModel()) == {}


@pytest.mark.asyncio
async def test_call_all_base_methods():
    """Cover every branch inside Service.call."""
    service = Service(redis_url="")
    first_op = OPERATIONS[0]
    await getattr(service, first_op)({"config": {"test": True}})

    assert (await service.call("list_methods"))["result"]["methods"] == OPERATIONS + [
        "get_state",
        "backup_state",
        "restore_state",
        "get_stats",
        "list_methods",
    ]
    stats = await service.call("get_stats")
    assert "total_requests" in stats["result"]

    found = await service.call("get_state", request={"config": {"feature": first_op}})
    assert found["success"] is True

    await service.call("backup_state", request={"config": {"name": "snap"}})
    restored = await service.call("restore_state", request={"config": {"name": "snap"}})
    assert restored["success"] is True

    op_result = await service.call(first_op, request={"config": {"test": True}})
    assert op_result["success"] is True

    with pytest.raises(ValueError):
        await service.call("totally_unknown")


@pytest.mark.asyncio
async def test_metrics_collector_singleton():
    """Cover MetricsCollector __new__ and __init__ singleton short-circuits."""
    name = f"singleton-{uuid.uuid4().hex[:6]}"
    m1 = MetricsCollector(name)
    m2 = MetricsCollector(name)
    assert m1 is m2
    m1.inc_request("x")
    assert m1.request_count == m2.request_count == 1


@pytest.mark.asyncio
async def test_cache_redis_hit_miss_and_clear(monkeypatch):
    """Cover cache Redis get miss / delete / clear success paths."""
    fake_redis = _FakeRedis()
    fake_aioredis = _FakeAioredis(fake_redis)
    monkeypatch.setattr("services.incident_runbook_service.cache.aioredis", fake_aioredis)

    metrics = MetricsCollector(f"incident_runbook_cache_{uuid.uuid4().hex[:6]}")
    cache = CacheManager(redis_url="redis://fake", metrics=metrics)

    # miss in redis, then fallback to memory (memory also misses)
    assert await cache.get("missing") is None

    await cache.set("k", {"x": 1})
    # hit in redis
    assert await cache.get("k") == {"x": 1}

    # delete success path
    await cache.delete("k")
    assert await cache.get("k") is None

    # clear success path
    await cache.set("k2", {"y": 2})
    await cache.clear()
    assert await cache.get("k2") is None


@pytest.mark.asyncio
async def test_retry_engine_unknown_and_jitter_policy(monkeypatch):
    """Cover RetryEngine unknown policy fallback and jitter branch."""
    monkeypatch.setattr("services.incident_runbook_service.retry.asyncio.sleep", mock.AsyncMock())

    engine_no_metrics = RetryEngine("nonexistent", metrics=None)
    fn = mock.AsyncMock(side_effect=Exception("retryable error"))
    with pytest.raises(Exception):
        await engine_no_metrics.execute(fn, operation="op", policy_name="missing_policy")
    assert fn.call_count == engine_no_metrics.default_policy.max_retries + 1

    engine_jitter = RetryEngine("jitter", metrics=None)
    fn2 = mock.AsyncMock(side_effect=Exception("retryable error"))
    with pytest.raises(Exception):
        await engine_jitter.execute(fn2, operation="op")
    assert fn2.call_count == engine_jitter.default_policy.max_retries + 1


@pytest.mark.asyncio
async def test_rpc_server_sync_and_async_handlers():
    """Cover gRPC server register/list/call including sync handlers."""
    server = IncidentRunbookServiceRPCServer()

    async def async_handler(name: str):
        return {"async": name}

    def sync_handler(name: str):
        return {"sync": name}

    server.register("async_op", async_handler)
    server.register("sync_op", sync_handler)
    assert "async_op" in server.list_methods()

    result = await server.call("async_op", name="x")
    assert result == {"async": "x"}

    result = await server.call("sync_op", name="y")
    assert result == {"sync": "y"}

    with pytest.raises(ValueError):
        await server.call("missing")


@pytest.mark.asyncio
async def test_rpc_client_call(monkeypatch):
    """Cover gRPC HTTP client success path."""

    class _FakeResponse:
        def __init__(self, data):
            self._data = data

        def raise_for_status(self) -> None:
            pass

        def json(self):
            return self._data

    class _FakeClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            pass

        async def post(self, url: str, *, json=None):
            return _FakeResponse({"success": True, "method": url.split("/")[-1]})

    monkeypatch.setattr(
        grpc_client_module, "httpx", type("httpx", (), {"AsyncClient": _FakeClient})
    )
    client = IncidentRunbookServiceRPCClient(base_url="http://test")
    result = await client.call("list_methods", payload={})
    assert result["success"] is True
