# -*- coding: utf-8 -*-
"""Endpoint tests for config microservice."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

import services.config_service.main_app as main_app


@pytest.fixture(autouse=True)
def reset_orchestrator():
    main_app._orchestrator = None
    yield
    main_app._orchestrator = None


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=main_app.app), base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_health_and_metrics(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    response = await client.get("/metrics")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_config_crud(client):
    config = {
        "config_id": "c1",
        "key": "timeout",
        "value": "30",
        "namespace": "default",
    }
    response = await client.post("/configs", json=config)
    assert response.status_code == 200
    assert response.json()["value"] == "30"

    response = await client.get("/configs/c1")
    assert response.status_code == 200
    assert response.json()["key"] == "timeout"

    response = await client.get("/configs", params={"namespace": "default"})
    assert response.status_code == 200
    assert response.json()["total"] == 1

    response = await client.patch("/configs/c1", params={"value": "60"})
    assert response.status_code == 200
    assert response.json()["value"] == "60"

    response = await client.delete("/configs/c1")
    assert response.status_code == 200
    assert response.json()["deleted"] is True


@pytest.mark.asyncio
async def test_versions_and_snapshots(client):
    config = {"config_id": "v1", "key": "retries", "value": "3", "namespace": "default"}
    await client.post("/configs", json=config)

    response = await client.post(
        "/configs/versions", params={"namespace": "default", "message": "initial"}
    )
    assert response.status_code == 200
    assert response.json()["namespace"] == "default"

    response = await client.get("/configs/versions", params={"namespace": "default"})
    assert response.status_code == 200
    assert response.json()["total"] == 1

    response = await client.post("/configs/snapshots", params={"namespace": "default"})
    assert response.status_code == 200
    snapshot_id = response.json()["snapshot_id"]

    await client.patch("/configs/v1", params={"value": "5"})
    response = await client.post(f"/configs/snapshots/{snapshot_id}/restore")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_namespaces(client):
    response = await client.get("/namespaces")
    assert response.status_code == 200
    assert "default" in response.json()["namespaces"]


@pytest.mark.asyncio
async def test_saga_endpoint(client):
    saga = {
        "saga_id": "s1",
        "task_id": "t1",
        "steps": [
            {"step_id": "step-1", "service": "config", "action": "noop", "compensation": "noop"},
        ],
    }
    response = await client.post("/sagas", json=saga)
    assert response.status_code == 200
    assert response.json()["status"] == "success"
