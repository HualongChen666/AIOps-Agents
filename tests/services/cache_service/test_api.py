# -*- coding: utf-8 -*-
"""API tests for the cache microservice."""

from __future__ import annotations

import httpx
import pytest

from services.cache_service import main_app as main_module
from services.cache_service.cache import CacheManager
from services.cache_service.main_app import app
from services.cache_service.metrics import MetricsCollector
from services.cache_service.service import CacheService


@pytest.fixture(autouse=True)
async def reset_service():
    from services.cache_service import config

    config.settings.redis_url = ""
    metrics = MetricsCollector("cache_api_test")
    cache = CacheManager(metrics=metrics)
    service = CacheService(redis_url="", metrics=metrics, cache=cache)
    await service.reset()
    main_module._service = service
    yield


@pytest.mark.asyncio
async def test_health():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_metrics():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/metrics")
    assert response.status_code == 200
    assert "cache" in response.text


@pytest.mark.asyncio
async def test_set_and_get():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        await client.post("/cache/set", json={"key": "api-key", "value": "api-value", "ttl": 60})
        response = await client.post("/cache/get", json={"key": "api-key"})
    assert response.status_code == 200
    data = response.json()
    assert data["hit"] is True
    assert data["value"] == "api-value"


@pytest.mark.asyncio
async def test_preheat():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/cache/preheat", json={"data": {"p1": 1, "p2": 2}, "ttl": 60})
    assert response.status_code == 200
    assert response.json()["keys_loaded"] == 2


@pytest.mark.asyncio
async def test_breakdown():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/cache/breakdown/protect",
            json={"key": "break", "value": "v", "ttl": 60},
        )
    assert response.status_code == 200
    assert response.json()["locked"] is True


@pytest.mark.asyncio
async def test_avalanche():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/cache/avalanche/protect",
            json={"key": "ava", "value": "v", "base_ttl": 100, "jitter_seconds": 5},
        )
    assert response.status_code == 200
    assert 100 <= response.json()["ttl"] <= 105


@pytest.mark.asyncio
async def test_strategy():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/cache/strategy",
            json={"strategy": "cache-aside", "key": "strat", "value": "v", "ttl": 60},
        )
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_stats_and_clear():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        await client.post("/cache/set", json={"key": "s1", "value": "v", "ttl": 60})
        await client.post("/cache/get", json={"key": "s1"})
        stats = await client.get("/cache/stats")
        clear = await client.post("/cache/clear")
    assert stats.status_code == 200
    assert stats.json()["hits"] >= 1
    assert clear.status_code == 200
    assert clear.json()["cleared"] is True


@pytest.mark.asyncio
async def test_rpc():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        list_resp = await client.post("/rpc/list_methods", json={})
        assert list_resp.status_code == 200
        assert "preheat" in list_resp.json()

        set_resp = await client.post(
            "/rpc/set", json={"key": "rpc-key", "value": "rpc-val", "ttl": 60}
        )
        assert set_resp.status_code == 200
