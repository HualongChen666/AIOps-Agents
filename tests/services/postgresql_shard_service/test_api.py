# -*- coding: utf-8 -*-
"""API tests for the PostgreSQL shard cluster microservice."""

from __future__ import annotations

import httpx
import pytest

from services.postgresql_shard_service import main_app as main_module
from services.postgresql_shard_service.main_app import app
from services.postgresql_shard_service.metrics import MetricsCollector
from services.postgresql_shard_service.service import ShardClusterService


@pytest.fixture(autouse=True)
async def reset_service():
    from services.postgresql_shard_service import config

    config.settings.redis_url = ""
    config.settings.database_url = ""
    config.settings.qdrant_url = ""
    metrics = MetricsCollector("postgresql_shard_api_test")
    service = ShardClusterService(
        backend="postgresql",
        redis_url="",
        database_url="",
        qdrant_url="",
        metrics=metrics,
    )
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
    assert "postgresql" in response.text or "shard" in response.text


@pytest.mark.asyncio
async def test_configure_and_route():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        cfg = await client.post(
            "/shards/configure",
            json={
                "nodes": [{"node_id": "n1", "host": "h1", "port": 5432}],
                "shard_count": 3,
                "strategy": "hash",
            },
        )
        assert cfg.status_code == 200
        response = await client.post("/shards/route", json={"key": "user:1001"})
    assert response.status_code == 200
    data = response.json()
    assert "shard_id" in data


@pytest.mark.asyncio
async def test_route_read_and_write():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        await client.post(
            "/replication/configure",
            json={"replication_factor": 2},
        )
        read_resp = await client.post("/shards/route/read", json={"key": "k1"})
        write_resp = await client.post("/shards/route/write", json={"key": "k1"})
    assert read_resp.status_code == 200
    assert write_resp.status_code == 200


@pytest.mark.asyncio
async def test_rebalance_and_ha():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        reb = await client.post("/shards/rebalance", json={"virtual_nodes": 50})
        ha = await client.post("/ha/configure", json={"enabled": True})
    assert reb.status_code == 200
    assert ha.status_code == 200


@pytest.mark.asyncio
async def test_failover_and_cross_shard():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        await client.post("/replication/configure", json={"replication_factor": 2})
        fo = await client.post("/failover", json={})
        cs = await client.post(
            "/cross_shard/query",
            json={"keys": ["a", "b", "c"], "query_type": "get"},
        )
    assert fo.status_code == 200
    assert cs.status_code == 200
    assert cs.json()["queried"] == 3


@pytest.mark.asyncio
async def test_backup_restore_and_performance():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        backup = await client.post("/backup", json={"name": "snap1"})
        restore = await client.post("/restore", json={"name": "snap1"})
        perf = await client.post("/performance", json={"iterations": 100})
    assert backup.status_code == 200
    assert restore.status_code == 200
    assert perf.status_code == 200


@pytest.mark.asyncio
async def test_rpc():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        methods = await client.post("/rpc/list_methods")
        assert methods.status_code == 200
        stats = await client.post("/rpc/stats")
        assert stats.status_code == 200
