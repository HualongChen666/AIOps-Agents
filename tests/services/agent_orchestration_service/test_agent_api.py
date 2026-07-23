# -*- coding: utf-8 -*-
"""API tests for the Agent Orchestration microservice."""

from __future__ import annotations

import httpx
import pytest

from services.agent_orchestration_service.cache import CacheManager
from services.agent_orchestration_service.main_app import app
from services.agent_orchestration_service.orchestrator import AgentOrchestrator


@pytest.fixture(autouse=True)
def reset_orchestrator():
    """Reset the agent orchestrator to a deterministic fallback for tests."""
    from services.agent_orchestration_service import config, main_app

    config.settings.redis_url = ""
    config.settings.openai_api_key = ""
    main_app._orchestrator = AgentOrchestrator(llm_model="fallback", cache=CacheManager())
    yield


@pytest.mark.asyncio
async def test_health():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "agent-orchestration-service"


@pytest.mark.asyncio
async def test_metrics():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/metrics")
    assert response.status_code == 200
    assert "agent_" in response.text


@pytest.mark.asyncio
async def test_stats():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["service"]


@pytest.mark.asyncio
async def test_agents_list():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/agents")
    assert response.status_code == 200
    data = response.json()
    assert "monitor" in data
    assert "diagnostic" in data


@pytest.mark.asyncio
async def test_decompose():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/decompose", json={"task": "monitor and fix issue"})
    assert response.status_code == 200
    data = response.json()
    assert len(data["subtasks"]) >= 1
    assert data["plan_id"]


@pytest.mark.asyncio
async def test_run_agent():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/run/monitor",
            json={"agent_type": "monitor", "input_data": {"task": "cpu high"}},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["result"]["agent_type"] == "monitor"


@pytest.mark.asyncio
async def test_coordinate():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/coordinate",
            json={
                "subtasks": [
                    {
                        "task_id": "a",
                        "description": "collect metrics",
                        "agent_type": "monitor",
                    },
                    {
                        "task_id": "b",
                        "description": "find root cause",
                        "agent_type": "diagnostic",
                    },
                ]
            },
        )
    assert response.status_code == 200
    data = response.json()
    assert len(data["completed"]) == 2


@pytest.mark.asyncio
async def test_collaborate():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/collaborate",
            json={
                "task": "diagnose and repair",
                "agent_types": ["diagnostic", "repair"],
                "run_parallel": True,
            },
        )
    assert response.status_code == 200
    data = response.json()
    assert len(data["results"]) == 2
    assert data["aggregated_output"]


@pytest.mark.asyncio
async def test_aggregate():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/aggregate",
            json={
                "results": [
                    {"agent_type": "a", "output": "hello"},
                    {"agent_type": "b", "output": "world"},
                ],
                "strategy": "concat",
            },
        )
    assert response.status_code == 200
    data = response.json()
    assert data["result_count"] == 2


@pytest.mark.asyncio
async def test_handle_error():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/handle-error",
            json={"error": "connection timeout", "operation": "test"},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["strategy"] == "retry_with_backoff"


@pytest.mark.asyncio
async def test_rpc_methods():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/rpc/list_methods", json={})
    assert response.status_code == 200
    methods = response.json()
    assert "decompose_task" in methods


@pytest.mark.asyncio
async def test_rpc_decompose():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/rpc/decompose_task",
            json={"task": "monitor and report"},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["plan_id"]


@pytest.mark.asyncio
async def test_rpc_unknown():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/rpc/unknown", json={})
    assert response.status_code == 404
