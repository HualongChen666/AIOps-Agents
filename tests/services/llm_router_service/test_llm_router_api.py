# -*- coding: utf-8 -*-
"""API tests for the LLM router microservice."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from services.llm_router_service.main_app import app


def _fake_post(*args, **kwargs):
    url = args[0]
    response = MagicMock()
    response.raise_for_status = MagicMock()
    response.json = MagicMock()
    if "anthropic" in url:
        response.json.return_value = {
            "content": [{"text": "Anthropic response"}],
            "usage": {"input_tokens": 5, "output_tokens": 5},
        }
    else:
        response.json.return_value = {
            "choices": [{"message": {"content": "OpenAI-style response"}}],
            "usage": {"total_tokens": 10},
        }
    return response


@pytest.fixture(autouse=True)
def reset_orchestrator():
    from services.llm_router_service import config, main_app

    config.settings.redis_url = ""
    main_app._orchestrator = None
    main_app._rpc_server = None

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.post.side_effect = _fake_post
    with patch(
        "services.llm_router_service.providers.AsyncClient",
        return_value=mock_client,
    ):
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
    assert "llm_router" in response.text


@pytest.mark.asyncio
async def test_list_models():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/models")
    data = response.json()
    assert response.status_code == 200
    assert data["total"] >= 6


@pytest.mark.asyncio
async def test_route():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/route", json={"prompt": "hello", "task_type": "general"})
    data = response.json()
    assert response.status_code == 200
    assert "model_name" in data


@pytest.mark.asyncio
async def test_generate():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/generate", json={"prompt": "hello"})
    data = response.json()
    assert response.status_code == 200
    assert data["content"] == "OpenAI-style response"


@pytest.mark.asyncio
async def test_completion():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/completions",
            json={
                "model": "auto",
                "messages": [{"role": "user", "content": "hi"}],
            },
        )
    data = response.json()
    assert response.status_code == 200
    assert data["choices"][0]["message"]["content"] == "OpenAI-style response"


@pytest.mark.asyncio
async def test_stats():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/stats")
    assert response.status_code == 200
    assert "model_stats" in response.json()


@pytest.mark.asyncio
async def test_cost():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/cost")
    data = response.json()
    assert response.status_code == 200
    assert "hourly_cost" in data


@pytest.mark.asyncio
async def test_performance():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/performance")
    data = response.json()
    assert response.status_code == 200
    assert "model_stats" in data


@pytest.mark.asyncio
async def test_strategies():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/strategies")
    data = response.json()
    assert response.status_code == 200
    assert "cost_optimized" in data["strategies"]


@pytest.mark.asyncio
async def test_retry_policies():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/retry-policies")
    data = response.json()
    assert response.status_code == 200
    assert "exponential" in data["policies"]


@pytest.mark.asyncio
async def test_circuit_states():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/circuit-states")
    data = response.json()
    assert response.status_code == 200
    assert "states" in data


@pytest.mark.asyncio
async def test_batch_route():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/batch/route",
            json=[{"prompt": "a"}, {"prompt": "b"}],
        )
    data = response.json()
    assert response.status_code == 200
    assert len(data) == 2


@pytest.mark.asyncio
async def test_batch_generate():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/batch/generate",
            json=[{"prompt": "a"}, {"prompt": "b"}],
        )
    data = response.json()
    assert response.status_code == 200
    assert len(data) == 2
    assert data[0]["content"] == "OpenAI-style response"


@pytest.mark.asyncio
async def test_rpc_list_models():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/rpc/list_models", json={})
    data = response.json()
    assert response.status_code == 200
    assert len(data) >= 6


@pytest.mark.asyncio
async def test_rpc_unknown():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/rpc/unknown", json={})
    assert response.status_code == 404
