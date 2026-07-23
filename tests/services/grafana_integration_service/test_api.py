# -*- coding: utf-8 -*-
"""API tests for the Grafana Integration microservice."""

from __future__ import annotations

import uuid

import httpx
import pytest

from services.grafana_integration_service import config
from services.grafana_integration_service import main_app as main_module
from services.grafana_integration_service.config import settings
from services.grafana_integration_service.main_app import app
from services.grafana_integration_service.metrics import MetricsCollector
from services.grafana_integration_service.service import OPERATIONS, Service


@pytest.fixture(autouse=True)
async def reset_service():
    """Reset the service singleton before each test."""
    config.settings.redis_url = ""
    metrics = MetricsCollector(f"grafana_integration_api_test_{uuid.uuid4().hex[:6]}")
    service = Service(redis_url="", metrics=metrics)
    main_module._service = service
    first_op = OPERATIONS[0]
    await getattr(service, first_op)({"config": {"test": True}})
    await service.backup_state({"config": {"name": "default"}})
    yield


@pytest.mark.asyncio
async def test_health():
    """Test the health endpoint."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_metrics():
    """Test the metrics endpoint."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/metrics")
    assert response.status_code == 200
    expected = settings.service_name.replace("-", "_")
    assert expected in response.text or "request" in response.text


@pytest.mark.asyncio
async def test_stats():
    """Test the stats endpoint."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/stats")
    assert response.status_code == 200
    data = response.json()
    assert "total_requests" in data


@pytest.mark.asyncio
async def test_all_feature_endpoints():
    """Test all feature endpoints."""
    service = main_module._service
    methods_data = await service.list_methods()
    methods = methods_data["result"]["methods"]
    first_op = OPERATIONS[0]
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        for method in methods:
            payload = {"config": {"test": True}}
            if method == "get_state":
                payload = {"config": {"feature": first_op}}
            elif method == "restore_state":
                payload = {"config": {"name": "default"}}
            response = await client.post(
                f"/grafana-integration/{method.replace('_', '-')}",
                json=payload,
            )
            assert response.status_code == 200, f"{method} failed: {response.text}"
            data = response.json()
            assert data["success"] is True, f"{method} returned {data}"


@pytest.mark.asyncio
async def test_rpc():
    """Test the generic RPC endpoint."""
    first_op = OPERATIONS[0]
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post("/rpc/list_methods")
        assert resp.status_code == 200
        methods = resp.json()
        assert first_op in methods
        resp = await client.post(f"/rpc/{first_op}", json={"config": {"test": True}})
        assert resp.status_code == 200
        assert resp.json()["success"] is True
