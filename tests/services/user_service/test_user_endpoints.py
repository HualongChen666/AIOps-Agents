# -*- coding: utf-8 -*-
"""Endpoint tests for user microservice."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

import services.user_service.main_app as main_app


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
async def test_user_crud_endpoints(client):
    user = {
        "username": "alice",
        "email": "alice@example.com",
        "full_name": "Alice",
    }
    response = await client.post("/users", json=user)
    assert response.status_code == 200
    user_id = response.json()["user_id"]

    response = await client.get(f"/users/{user_id}")
    assert response.status_code == 200
    assert response.json()["username"] == "alice"

    response = await client.patch(f"/users/{user_id}", json={"full_name": "Alice Smith"})
    assert response.status_code == 200
    assert response.json()["full_name"] == "Alice Smith"

    response = await client.get("/users", params={"tenant_id": "default"})
    assert response.status_code == 200
    assert response.json()["total"] == 1

    response = await client.delete(f"/users/{user_id}")
    assert response.status_code == 200
    assert response.json()["deleted"] is True


@pytest.mark.asyncio
async def test_login_and_session(client):
    user = {
        "username": "bob",
        "email": "bob@example.com",
        "password": "password",
    }
    await client.post("/users", json=user)
    response = await client.post("/auth/login", params={"username": "bob", "password": "password"})
    assert response.status_code == 200
    assert "access_token" in response.json()

    response = await client.post("/sessions", params={"user_id": "user-bob"})
    assert response.status_code == 200
    assert response.json()["user_id"] == "user-bob"


@pytest.mark.asyncio
async def test_roles_and_organizations(client):
    role = {
        "role_id": "admin",
        "name": "Administrator",
        "permissions": ["p1", "p2"],
        "tenant_id": "default",
    }
    response = await client.post("/roles", json=role)
    assert response.status_code == 200

    response = await client.get("/roles", params={"tenant_id": "default"})
    assert response.status_code == 200
    assert response.json()["total"] == 1

    org = {
        "org_id": "root",
        "name": "Root Org",
        "tenant_id": "default",
    }
    response = await client.post("/organizations", json=org)
    assert response.status_code == 200

    response = await client.get("/organizations/tree", params={"tenant_id": "default"})
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_saga_endpoint(client):
    saga = {
        "saga_id": "s1",
        "task_id": "t1",
        "steps": [
            {"step_id": "step-1", "service": "user", "action": "noop", "compensation": "noop"},
        ],
    }
    response = await client.post("/sagas", json=saga)
    assert response.status_code == 200
    assert response.json()["status"] == "success"
