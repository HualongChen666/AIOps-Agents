# -*- coding: utf-8 -*-
"""Core tests for the Agent Orchestration microservice."""

from __future__ import annotations

import pytest

from services.agent_orchestration_service.cache import CacheManager
from services.agent_orchestration_service.orchestrator import AgentOrchestrator, LangGraphAdapter
from services.agent_orchestration_service.retry import AgentRetryEngine
from services.agent_orchestration_service.schemas import (
    AgentRequest,
    AgentResult,
    AgentType,
    AggregateRequest,
    CollaborateRequest,
    CoordinateRequest,
    DecomposeRequest,
    ErrorHandleRequest,
    SubTask,
)


@pytest.fixture
def orchestrator():
    return AgentOrchestrator(llm_model="fallback", cache=CacheManager())


@pytest.mark.asyncio
async def test_decompose_task(orchestrator):
    request = DecomposeRequest(task="monitor and diagnose system failure", max_subtasks=3)
    response = await orchestrator.decompose_task(request)
    assert response.task == request.task
    assert len(response.subtasks) >= 1
    assert response.plan_id


@pytest.mark.asyncio
async def test_run_agent_monitor(orchestrator):
    request = AgentRequest(
        agent_type=AgentType.MONITOR,
        input_data={"task": "check CPU"},
        context={"metric": "cpu"},
    )
    response = await orchestrator.run_agent(request)
    assert response.result.agent_type == "monitor"
    assert "check CPU" in response.result.output


@pytest.mark.asyncio
async def test_run_agent_diagnostic(orchestrator):
    request = AgentRequest(
        agent_type=AgentType.DIAGNOSTIC,
        input_data={"task": "find root cause"},
    )
    response = await orchestrator.run_agent(request)
    assert response.result.agent_type == "diagnostic"


@pytest.mark.asyncio
async def test_run_agent_repair(orchestrator):
    request = AgentRequest(
        agent_type=AgentType.REPAIR,
        input_data={"task": "restart service"},
    )
    response = await orchestrator.run_agent(request)
    assert response.result.agent_type == "repair"


@pytest.mark.asyncio
async def test_run_agent_analysis(orchestrator):
    request = AgentRequest(
        agent_type=AgentType.ANALYSIS,
        input_data={"task": "summarize findings"},
    )
    response = await orchestrator.run_agent(request)
    assert response.result.agent_type == "analysis"


@pytest.mark.asyncio
async def test_run_agent_generic(orchestrator):
    request = AgentRequest(
        agent_type=AgentType.GENERIC,
        input_data={"task": "generic task"},
    )
    response = await orchestrator.run_agent(request)
    assert response.result.agent_type == "generic"


@pytest.mark.asyncio
async def test_coordinate_sequential(orchestrator):
    request = CoordinateRequest(
        subtasks=[
            SubTask(task_id="a", description="collect metrics", agent_type=AgentType.MONITOR),
            SubTask(task_id="b", description="find cause", agent_type=AgentType.DIAGNOSTIC),
        ]
    )
    response = await orchestrator.coordinate(request)
    assert response.plan_id
    assert len(response.completed) == 2
    assert not response.failed


@pytest.mark.asyncio
async def test_coordinate_parallel(orchestrator):
    request = CoordinateRequest(
        subtasks=[
            SubTask(task_id="a", description="collect metrics", agent_type=AgentType.MONITOR),
            SubTask(task_id="b", description="find cause", agent_type=AgentType.DIAGNOSTIC),
        ],
        run_parallel=True,
    )
    response = await orchestrator.coordinate(request)
    assert response.plan_id
    assert len(response.completed) == 2


@pytest.mark.asyncio
async def test_collaborate_sequential(orchestrator):
    request = CollaborateRequest(
        task="diagnose and repair the issue",
        agent_types=[AgentType.DIAGNOSTIC, AgentType.REPAIR],
    )
    response = await orchestrator.collaborate(request)
    assert response.task == request.task
    assert len(response.results) == 2
    assert response.aggregated_output


@pytest.mark.asyncio
async def test_collaborate_parallel(orchestrator):
    request = CollaborateRequest(
        task="diagnose and repair the issue",
        agent_types=[AgentType.DIAGNOSTIC, AgentType.REPAIR],
        run_parallel=True,
    )
    response = await orchestrator.collaborate(request)
    assert len(response.results) == 2
    assert response.aggregated_output


@pytest.mark.asyncio
async def test_aggregate_concat(orchestrator):
    results = [
        AgentResult(agent_type="a", output="result a"),
        AgentResult(agent_type="b", output="result b"),
    ]
    response = await orchestrator.aggregate(AggregateRequest(results=results, strategy="concat"))
    assert response.result_count == 2
    assert "result a" in response.aggregated_output


@pytest.mark.asyncio
async def test_aggregate_merge(orchestrator):
    results = [
        AgentResult(agent_type="a", output="hello"),
        AgentResult(agent_type="b", output="world"),
    ]
    response = await orchestrator.aggregate(AggregateRequest(results=results, strategy="merge"))
    assert "hello" in response.aggregated_output
    assert "world" in response.aggregated_output


@pytest.mark.asyncio
async def test_aggregate_vote(orchestrator):
    results = [
        AgentResult(agent_type="a", output="yes"),
        AgentResult(agent_type="b", output="yes"),
        AgentResult(agent_type="c", output="no"),
    ]
    response = await orchestrator.aggregate(AggregateRequest(results=results, strategy="vote"))
    assert response.aggregated_output == "yes"


@pytest.mark.asyncio
async def test_handle_error_timeout(orchestrator):
    response = await orchestrator.handle_error(
        ErrorHandleRequest(error="connection timeout", operation="test")
    )
    assert response.recovered
    assert response.strategy == "retry_with_backoff"


@pytest.mark.asyncio
async def test_handle_error_auth(orchestrator):
    response = await orchestrator.handle_error(
        ErrorHandleRequest(error="authentication failed", operation="test")
    )
    assert not response.recovered
    assert response.strategy == "escalate"


@pytest.mark.asyncio
async def test_handle_error_rate_limit(orchestrator):
    response = await orchestrator.handle_error(
        ErrorHandleRequest(error="rate limit exceeded", operation="test")
    )
    assert response.strategy == "throttle"


@pytest.mark.asyncio
async def test_handle_error_not_found(orchestrator):
    response = await orchestrator.handle_error(
        ErrorHandleRequest(error="resource not found 404", operation="test")
    )
    assert response.strategy == "verify_input"


@pytest.mark.asyncio
async def test_get_stats(orchestrator):
    await orchestrator.decompose_task(DecomposeRequest(task="x"))
    stats = await orchestrator.get_stats()
    assert stats.service
    assert "decompose" in stats.request_counts
    assert stats.retry_policies


def test_list_methods(orchestrator):
    methods = orchestrator.list_methods()
    assert "decompose_task" in methods
    assert "collaborate" in methods


@pytest.mark.asyncio
async def test_langgraph_adapter():
    adapter = LangGraphAdapter()
    result = await adapter.execute(None, {"task": "test"})
    assert "fallback" in result["result"]


@pytest.mark.asyncio
async def test_retry_engine_execute():
    engine = AgentRetryEngine()

    async def ok():
        return "ok"

    result = await engine.execute(ok, operation="test")
    assert result == "ok"


@pytest.mark.asyncio
async def test_retry_engine_failure():
    from unittest.mock import patch

    engine = AgentRetryEngine("exponential_fast")
    calls = 0

    async def flaky():
        nonlocal calls
        calls += 1
        if calls < 2:
            raise RuntimeError("retryable error")
        return "ok"

    with patch("services.agent_orchestration_service.retry.asyncio.sleep"):
        result = await engine.execute(flaky, operation="flaky")
    assert result == "ok"
    assert calls == 2


@pytest.mark.asyncio
async def test_cache_redis():
    from unittest.mock import AsyncMock, MagicMock, patch

    from services.agent_orchestration_service.cache import CacheManager

    fake_redis = AsyncMock()
    fake_redis.get.return_value = '{"value": 42}'
    fake_from_url = MagicMock(return_value=fake_redis)

    mock_redis_module = MagicMock()
    mock_redis_module.from_url = fake_from_url

    with patch(
        "services.agent_orchestration_service.cache.aioredis",
        mock_redis_module,
        create=True,
    ):
        cache = CacheManager("redis://localhost:6379")
        value = await cache.get("key")
        await cache.set("key", {"value": 1})
        await cache.clear()

    assert value == {"value": 42}
    fake_redis.setex.assert_called_once()
    fake_redis.flushdb.assert_called_once()


@pytest.mark.asyncio
async def test_grpc_server():
    from services.agent_orchestration_service.grpc.server import AgentRPCServer

    server = AgentRPCServer()
    server.register("echo", lambda x: x)
    assert "echo" in server.list_methods()
    result = await server.call("echo", x="hello")
    assert result == "hello"


@pytest.mark.asyncio
async def test_grpc_client():
    from unittest.mock import AsyncMock, MagicMock, patch

    from services.agent_orchestration_service.grpc.client import AgentRPCClient

    mock_response = MagicMock()
    mock_response.json.return_value = {"ok": True}
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.post.return_value = mock_response

    with patch(
        "services.agent_orchestration_service.grpc.client.httpx.AsyncClient",
        return_value=mock_client,
    ):
        client = AgentRPCClient()
        result = await client.call("echo", {"x": "hello"})
    assert result == {"ok": True}
