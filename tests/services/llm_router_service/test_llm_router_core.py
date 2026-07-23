# -*- coding: utf-8 -*-
"""Core tests for the LLM router microservice."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.llm_router_service.cache import CacheManager
from services.llm_router_service.config import settings as router_settings
from services.llm_router_service.grpc.client import LLMRouterRPCClient
from services.llm_router_service.grpc.server import LLMRouterRPCServer
from services.llm_router_service.health_check import HealthCheckEngine
from services.llm_router_service.orchestrator import LLMRouterOrchestrator
from services.llm_router_service.providers import (
    AnthropicProvider,
    LocalProvider,
    OpenAIProvider,
    OpenSourceProvider,
    ProviderFactory,
)
from services.llm_router_service.retry import LLMRetryEngine, RetryPolicy
from services.llm_router_service.schemas import (
    GenerateRequest,
    LiteLLMRequest,
    ModelConfig,
    ProviderType,
    RouteRequest,
    RouteResponse,
    TaskType,
)


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
def httpx_mock():
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.post.side_effect = _fake_post
    with patch(
        "services.llm_router_service.providers.AsyncClient",
        return_value=mock_client,
    ):
        yield


@pytest.mark.asyncio
async def test_settings():
    assert router_settings.service_name == "llm-router-service"
    assert router_settings.default_strategy == "cost_optimized"


@pytest.mark.asyncio
async def test_schemas():
    config = ModelConfig(
        name="gpt-4",
        provider=ProviderType.OPENAI,
        model_id="gpt-4",
        cost_per_1k=0.03,
    )
    assert config.name == "gpt-4"
    request = RouteRequest(prompt="hello", task_type=TaskType.GENERAL)
    assert request.prompt == "hello"
    response = RouteResponse(
        model_name="gpt-4",
        provider=ProviderType.OPENAI,
        estimated_cost=0.0,
        estimated_tokens=1,
        confidence=1.0,
        reason="test",
    )
    assert response.model_name == "gpt-4"


@pytest.mark.asyncio
async def test_cache_manager():
    cache = CacheManager()
    await cache.set("key", {"value": 1})
    result = await cache.get("key")
    assert result == {"value": 1}
    missing = await cache.get("missing")
    assert missing is None


@pytest.mark.asyncio
async def test_retry_policies_count():
    engine = LLMRetryEngine()
    assert len(engine.list_policies()) >= 10


@pytest.mark.asyncio
async def test_retry_success():
    engine = LLMRetryEngine()
    fn = AsyncMock(return_value="ok")
    result = await engine.execute(fn, "arg")
    assert result == "ok"


@pytest.mark.asyncio
async def test_retry_non_retryable():
    engine = LLMRetryEngine()
    fn = AsyncMock(side_effect=RuntimeError("fatal error"))
    with pytest.raises(RuntimeError):
        await engine.execute(fn, "arg")


@pytest.mark.asyncio
async def test_retry_then_success():
    engine = LLMRetryEngine()
    fn = AsyncMock(side_effect=[RuntimeError("retryable"), "ok"])
    result = await engine.execute(fn, "arg", policy_name="exponential_fast")
    assert result == "ok"
    assert fn.call_count == 2


@pytest.mark.asyncio
async def test_add_retry_policy():
    engine = LLMRetryEngine()
    engine.add_policy(RetryPolicy(name="custom", max_retries=1))
    assert "custom" in engine.list_policies()


def test_provider_factory():
    openai = ProviderFactory.create({"name": "gpt-4", "model": "gpt-4", "provider": "openai"})
    assert isinstance(openai, OpenAIProvider)
    anthropic = ProviderFactory.create(
        {"name": "claude", "model": "claude-3-opus", "provider": "anthropic"}
    )
    assert isinstance(anthropic, AnthropicProvider)
    open_source = ProviderFactory.create(
        {"name": "llama", "model": "llama2", "provider": "open_source"}
    )
    assert isinstance(open_source, OpenSourceProvider)
    local = ProviderFactory.create({"name": "local", "model": "local", "provider": "local"})
    assert isinstance(local, LocalProvider)


@pytest.mark.asyncio
async def test_openai_provider_call():
    provider = OpenAIProvider(
        name="gpt-4",
        model_id="gpt-4",
        cost_per_1k=0.03,
        max_tokens=128000,
        context_window=128000,
        api_key="test-key",
    )
    result = await provider.call("hello")
    assert result.content == "OpenAI-style response"
    assert result.provider == ProviderType.OPENAI
    assert result.tokens == 10


@pytest.mark.asyncio
async def test_anthropic_provider_call():
    provider = AnthropicProvider(
        name="claude",
        model_id="claude-3-opus",
        cost_per_1k=0.03,
        max_tokens=200000,
        context_window=200000,
        api_key="test-key",
    )
    result = await provider.call("hello")
    assert result.content == "Anthropic response"
    assert result.provider == ProviderType.ANTHROPIC
    assert result.tokens == 10


@pytest.mark.asyncio
async def test_open_source_provider_call():
    provider = OpenSourceProvider(
        name="llama",
        model_id="llama2",
        cost_per_1k=0.0005,
        max_tokens=4096,
        context_window=4096,
    )
    result = await provider.call("hello")
    assert result.content == "OpenAI-style response"
    assert result.provider == ProviderType.OPEN_SOURCE


@pytest.mark.asyncio
async def test_local_provider_call():
    provider = LocalProvider(
        name="local",
        model_id="local",
        cost_per_1k=0.0,
        max_tokens=4096,
        context_window=4096,
    )
    result = await provider.call("hello")
    assert result.content == "OpenAI-style response"
    assert result.provider == ProviderType.LOCAL


@pytest.mark.asyncio
async def test_health_check():
    engine = HealthCheckEngine()
    health = await engine.check("llm-router", 5)
    assert health.status == "ok"
    assert health.model_count == 5


@pytest.mark.asyncio
async def test_orchestrator_init():
    orchestrator = LLMRouterOrchestrator()
    assert len(orchestrator.list_models()) == 6
    assert "local-llm" in orchestrator.providers


@pytest.mark.asyncio
async def test_orchestrator_route():
    orchestrator = LLMRouterOrchestrator()
    request = RouteRequest(prompt="hello", task_type=TaskType.GENERAL)
    response = await orchestrator.route(request)
    assert response.model_name
    assert response.estimated_cost >= 0
    assert response.confidence > 0


@pytest.mark.asyncio
async def test_orchestrator_generate():
    orchestrator = LLMRouterOrchestrator()
    request = GenerateRequest(prompt="hello")
    response = await orchestrator.generate(request)
    assert response.content == "OpenAI-style response"
    assert response.tokens == 10
    assert response.provider == ProviderType.LOCAL


@pytest.mark.asyncio
async def test_orchestrator_completion():
    orchestrator = LLMRouterOrchestrator()
    request = LiteLLMRequest(
        model="auto",
        messages=[{"role": "user", "content": "hi"}],
    )
    response = await orchestrator.completion(request)
    assert response.choices[0].message["content"] == "OpenAI-style response"
    assert response.usage.total_tokens == 10


@pytest.mark.asyncio
async def test_orchestrator_route_batch():
    orchestrator = LLMRouterOrchestrator()
    requests = [
        RouteRequest(prompt="a"),
        RouteRequest(prompt="b"),
    ]
    responses = await orchestrator.route_batch(requests)
    assert len(responses) == 2


@pytest.mark.asyncio
async def test_orchestrator_generate_batch():
    orchestrator = LLMRouterOrchestrator()
    requests = [
        GenerateRequest(prompt="a"),
        GenerateRequest(prompt="b"),
    ]
    responses = await orchestrator.generate_batch(requests)
    assert len(responses) == 2
    assert all(r.content == "OpenAI-style response" for r in responses)


@pytest.mark.asyncio
async def test_orchestrator_stats():
    orchestrator = LLMRouterOrchestrator()
    stats = orchestrator.get_stats()
    assert "model_stats" in stats
    assert "circuit_states" in stats


@pytest.mark.asyncio
async def test_orchestrator_cost_report():
    orchestrator = LLMRouterOrchestrator()
    report = await orchestrator.get_cost_report()
    assert report.request_count == 0


@pytest.mark.asyncio
async def test_orchestrator_performance_report():
    orchestrator = LLMRouterOrchestrator()
    report = await orchestrator.get_performance_report()
    assert report.total_requests == 0
    assert len(report.model_stats) == 6


@pytest.mark.asyncio
async def test_orchestrator_fallback():
    configs = [
        {
            "name": "bad",
            "model": "bad",
            "provider": "openai",
            "cost_per_1k": 0.0,
            "max_tokens": 100,
            "context_window": 100,
            "api_key": "x",
        },
        {
            "name": "good",
            "model": "good",
            "provider": "openai",
            "cost_per_1k": 0.0,
            "max_tokens": 100,
            "context_window": 100,
            "api_key": "x",
        },
    ]
    orchestrator = LLMRouterOrchestrator(settings_obj=router_settings, model_configs=configs)
    orchestrator.providers["bad"].call = AsyncMock(side_effect=RuntimeError("non retryable"))
    request = GenerateRequest(prompt="hello", model="bad")
    response = await orchestrator.generate(request)
    assert response.model == "good"
    assert response.content == "OpenAI-style response"


@pytest.mark.asyncio
async def test_rpc_server():
    server = LLMRouterRPCServer()

    async def echo(**kwargs):
        return kwargs.get("x")

    server.register("echo", echo)
    assert "echo" in server.list_methods()
    result = await server.call("echo", x=42)
    assert result == 42
    with pytest.raises(ValueError):
        await server.call("unknown")


@pytest.mark.asyncio
async def test_rpc_client():
    server = LLMRouterRPCServer()
    server.register("add", lambda x, y: x + y)
    client = LLMRouterRPCClient(server=server)
    result = await client.call("add", x=2, y=3)
    assert result == 5


@pytest.mark.asyncio
async def test_cache_redis_operations():
    cache = CacheManager(redis_url="redis://localhost")
    redis_mock = AsyncMock()
    cache._redis = redis_mock

    redis_mock.get = AsyncMock(return_value=json.dumps({"value": 1}))
    result = await cache.get("k")
    assert result == {"value": 1}

    await cache.set("k2", {"value": 2})
    redis_mock.setex.assert_awaited()

    redis_mock.setex = AsyncMock(side_effect=Exception("redis down"))
    await cache.set("k3", {"value": 3})
    redis_mock.get = AsyncMock(side_effect=Exception("redis down"))
    result = await cache.get("k3")
    assert result == {"value": 3}


@pytest.mark.asyncio
async def test_rpc_client_http():
    mock_http = AsyncMock()
    mock_http.__aenter__.return_value = mock_http
    response = MagicMock()
    response.raise_for_status = MagicMock()
    response.json = MagicMock(return_value={"result": "ok"})
    mock_http.post.return_value = response

    with patch(
        "services.llm_router_service.grpc.client.httpx.AsyncClient",
        return_value=mock_http,
    ):
        client = LLMRouterRPCClient(base_url="http://test")
        result = await client.call("echo", x=1)
        assert result == {"result": "ok"}
        await client.close()
