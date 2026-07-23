# -*- coding: utf-8 -*-
"""API tests for the data access microservice."""

from __future__ import annotations

import httpx
import pytest

from services.data_access_service import main_app as main_module
from services.data_access_service.cache import CacheManager
from services.data_access_service.main_app import app
from services.data_access_service.metrics import MetricsCollector
from services.data_access_service.service import DataAccessService


@pytest.fixture(autouse=True)
async def reset_service():
    """Reset the service to a clean in-memory database before each test."""
    from services.data_access_service import config

    config.settings.database_url = "sqlite+aiosqlite:///:memory:"
    config.settings.redis_url = ""
    metrics = MetricsCollector("data_access_api_test")
    cache = CacheManager(metrics=metrics)
    service = DataAccessService(
        database_url="sqlite+aiosqlite:///:memory:",
        redis_url="",
        metrics=metrics,
        cache=cache,
    )
    await service.initialize()
    await service.reset()
    main_module._service = service
    yield
    await service.engine.dispose()


@pytest.fixture
async def client():
    """Async HTTP client for the FastAPI app."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client


@pytest.mark.asyncio
async def test_health():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "data-access-service"


@pytest.mark.asyncio
async def test_metrics():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/metrics")
    assert response.status_code == 200
    assert "data_access" in response.text


@pytest.mark.asyncio
async def test_create_and_get_item():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        create_resp = await client.post("/items", json={"name": "alpha", "value": "1"})
    assert create_resp.status_code == 200
    item = create_resp.json()
    assert item["name"] == "alpha"

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        get_resp = await client.get(f"/items/{item['id']}")
    assert get_resp.status_code == 200
    assert get_resp.json()["name"] == "alpha"


@pytest.mark.asyncio
async def test_list_items():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        for i in range(3):
            await client.post("/items", json={"name": f"item-{i}", "value": str(i)})
        response = await client.get("/items?page=1&page_size=2&sort_by=id")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 3
    assert len(data["items"]) == 2


@pytest.mark.asyncio
async def test_update_and_delete_item():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        create_resp = await client.post("/items", json={"name": "beta", "value": "2"})
    item = create_resp.json()

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        update_resp = await client.put(f"/items/{item['id']}", json={"name": "beta-updated"})
    assert update_resp.status_code == 200
    assert update_resp.json()["name"] == "beta-updated"

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        delete_resp = await client.delete(f"/items/{item['id']}")
    assert delete_resp.status_code == 200
    assert delete_resp.json()["deleted"] is True


@pytest.mark.asyncio
async def test_build_query():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/query/build",
            json={"table": "items", "filters": {"name": "x"}, "page": 1, "page_size": 5},
        )
    assert response.status_code == 200
    data = response.json()
    assert "SELECT" in data["compiled"].upper()
    assert data["filter_count"] == 1


@pytest.mark.asyncio
async def test_transaction():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/transaction",
            json={
                "operations": [
                    {"op": "create", "table": "items", "data": {"name": "t1", "value": "v1"}}
                ]
            },
        )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert len(data["results"]) == 1


@pytest.mark.asyncio
async def test_pool_status():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/pool/status")
    assert response.status_code == 200
    data = response.json()
    assert "size" in data


@pytest.mark.asyncio
async def test_slow_query_monitor():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        await client.post("/monitor/slow?query=slow_test&elapsed_ms=250.0")
        response = await client.get("/monitor/slow")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_route_read_write():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        read_resp = await client.get("/route/read")
        write_resp = await client.get("/route/write")
    assert read_resp.status_code == 200
    assert write_resp.status_code == 200
    assert "read" in read_resp.json()["operation"]
    assert "write" in write_resp.json()["operation"]


@pytest.mark.asyncio
async def test_route_shard():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/route/shard",
            json={"key": "abc", "strategy": "hash", "shard_count": 4},
        )
    assert response.status_code == 200
    data = response.json()
    assert 0 <= data["shard_index"] < data["shard_count"]


@pytest.mark.asyncio
async def test_route_database():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/route/database",
            json={
                "database": "default",
                "strategy": "round_robin",
                "targets": ["primary", "replica1"],
            },
        )
    assert response.status_code == 200
    assert response.json()["target"] in ["primary", "replica1"]


@pytest.mark.asyncio
async def test_optimize():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/optimize",
            json={"query": "SELECT * FROM items WHERE name = 'x' ORDER BY id", "table": "items"},
        )
    assert response.status_code == 200
    data = response.json()
    assert len(data["suggestions"]) >= 1


@pytest.mark.asyncio
async def test_rpc():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        list_resp = await client.post("/rpc/list_methods", json={})
    assert list_resp.status_code == 200
    methods = list_resp.json()
    assert "create_item" in methods
    assert "build_query" in methods

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        rpc_resp = await client.post("/rpc/create_item", json={"name": "rpc_item", "value": "rv"})
    assert rpc_resp.status_code == 200
    assert rpc_resp.json()["name"] == "rpc_item"


@pytest.mark.asyncio
async def test_stats():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/stats")
    assert response.status_code == 200
    data = response.json()
    assert "total_requests" in data
