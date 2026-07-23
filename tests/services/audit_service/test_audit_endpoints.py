# -*- coding: utf-8 -*-
"""Endpoint tests for audit microservice."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient

import services.audit_service.main_app as main_app


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
async def test_health(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_metrics(client):
    response = await client.get("/metrics")
    assert response.status_code == 200
    assert "audit" in response.text or "python_gc" in response.text


@pytest.mark.asyncio
async def test_record_and_list_events(client):
    event = {
        "event_id": "evt-1",
        "action": "login",
        "resource": "user",
        "user_id": "u1",
        "tenant_id": "t1",
        "severity": "high",
    }
    response = await client.post("/events", json=event)
    assert response.status_code == 200
    data = response.json()
    assert data["event_id"] == "evt-1"

    response = await client.get("/events", params={"tenant_id": "t1"})
    assert response.status_code == 200
    items = response.json()["items"]
    assert any(i["event_id"] == "evt-1" for i in items)


@pytest.mark.asyncio
async def test_record_and_list_logs(client):
    log = {
        "log_id": "log-1",
        "event_id": "evt-1",
        "action": "update",
        "actor": "admin",
    }
    response = await client.post("/logs", json=log)
    assert response.status_code == 200

    response = await client.get("/logs/evt-1")
    assert response.status_code == 200
    assert response.json()["total"] == 1


@pytest.mark.asyncio
async def test_create_and_list_reports(client):
    now = datetime.utcnow()
    response = await client.post(
        "/reports",
        params={
            "report_type": "soc2",
            "tenant_id": "t1",
            "start_time": (now - timedelta(hours=1)).isoformat(),
            "end_time": (now + timedelta(hours=1)).isoformat(),
        },
    )
    assert response.status_code == 200
    assert response.json()["tenant_id"] == "t1"

    response = await client.get("/reports", params={"tenant_id": "t1"})
    assert response.status_code == 200
    assert response.json()["total"] >= 1


@pytest.mark.asyncio
async def test_create_policy(client):
    policy = {
        "policy_id": "p1",
        "tenant_id": "t1",
        "ttl_days": 30,
        "archive_after_days": 7,
        "auto_archive": True,
    }
    response = await client.post("/policies", json=policy)
    assert response.status_code == 200
    assert response.json()["policy_id"] == "p1"


@pytest.mark.asyncio
async def test_execute_saga(client):
    saga = {
        "saga_id": "s1",
        "task_id": "t1",
        "steps": [
            {"step_id": "step-1", "service": "audit", "action": "log", "compensation": "undo"},
        ],
    }
    response = await client.post("/sagas", json=saga)
    assert response.status_code == 200
    assert response.json()["status"] == "success"


@pytest.mark.asyncio
async def test_query_filters(client):
    await client.post(
        "/events",
        json={
            "event_id": "evt-2",
            "action": "logout",
            "resource": "user",
            "user_id": "u1",
            "tenant_id": "t2",
            "severity": "low",
        },
    )
    response = await client.get("/events", params={"tenant_id": "t2", "action": "logout"})
    assert response.status_code == 200
    assert response.json()["total"] == 1
