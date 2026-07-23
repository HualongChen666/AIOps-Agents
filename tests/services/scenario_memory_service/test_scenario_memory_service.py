# -*- coding: utf-8 -*-
"""Tests for the Scenario Memory microservice."""

from __future__ import annotations

import httpx
import pytest

from services.scenario_memory_service.cache import CacheManager
from services.scenario_memory_service.grpc.client import ScenarioRPCClient
from services.scenario_memory_service.grpc.server import ScenarioRPCServer
from services.scenario_memory_service.main_app import app
from services.scenario_memory_service.orchestrator import (
    ScenarioMemoryOrchestrator,
    _cosine_similarity,
    _text_to_vector,
)
from services.scenario_memory_service.schemas import (
    AccumulateKnowledgeRequest,
    EventMemory,
    KnowledgeEntry,
    LearnExperienceRequest,
    LongTermRequest,
    PatternRequest,
    ProceduralRequest,
    SemanticRequest,
    ShortTermRequest,
    SimilarityQueryRequest,
    StoreEventRequest,
)


@pytest.fixture(autouse=True)
def reset_orchestrator():
    """Reset the orchestrator to a deterministic fallback for tests."""
    from services.scenario_memory_service import config, main_app

    config.settings.redis_url = ""
    main_app._orchestrator = ScenarioMemoryOrchestrator(cache=CacheManager())
    yield


@pytest.fixture
def orchestrator():
    return ScenarioMemoryOrchestrator(cache=CacheManager())


# ------------------------------------------------------------------
# API tests
# ------------------------------------------------------------------
@pytest.mark.asyncio
async def test_health():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "scenario-memory-service"


@pytest.mark.asyncio
async def test_metrics():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/metrics")
    assert response.status_code == 200
    assert "scenario_memory" in response.text


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
async def test_store_event():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/store/event",
            json={
                "event": {
                    "event_type": "alert",
                    "source": "cpu-monitor",
                    "payload": {"cpu": 95},
                    "tags": ["cpu", "high"],
                }
            },
        )
    assert response.status_code == 200
    data = response.json()
    assert data["stored"]
    assert data["event_id"]


@pytest.mark.asyncio
async def test_search_similar():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        await client.post(
            "/store/event",
            json={
                "event": {
                    "event_type": "alert",
                    "source": "cpu-monitor",
                    "payload": {"cpu": 95},
                    "tags": ["cpu", "high"],
                }
            },
        )
        response = await client.post(
            "/search/similar",
            json={"query": "cpu high alert", "top_k": 3},
        )
    assert response.status_code == 200
    data = response.json()
    assert "results" in data


@pytest.mark.asyncio
async def test_learn_experience():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/learn/experience",
            json={
                "situation": "cpu high",
                "action": "restart service",
                "outcome": "cpu normalized",
                "confidence": 0.9,
            },
        )
    assert response.status_code == 200
    data = response.json()
    assert data["learned"]
    assert data["confidence"] > 0


@pytest.mark.asyncio
async def test_accumulate_knowledge():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/accumulate/knowledge",
            json={
                "entries": [
                    {
                        "subject": "server",
                        "predicate": "has_issue",
                        "object": "cpu_high",
                        "weight": 1.0,
                        "source": "monitor",
                    }
                ]
            },
        )
    assert response.status_code == 200
    data = response.json()
    assert data["stored"] == 1
    assert len(data["knowledge_ids"]) == 1


@pytest.mark.asyncio
async def test_recognize_pattern():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/recognize/pattern",
            json={
                "data": [
                    {"event_type": "alert"},
                    {"event_type": "alert"},
                    {"event_type": "recovery"},
                    {"event_type": "alert"},
                    {"event_type": "recovery"},
                ],
                "pattern_type": "sequence",
            },
        )
    assert response.status_code == 200
    data = response.json()
    assert "patterns" in data


@pytest.mark.asyncio
async def test_short_term_memory():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        await client.post(
            "/memory/short-term/working_state",
            json={"key": "working_state", "value": {"task": "running"}, "ttl_seconds": 60},
        )
        response = await client.get("/memory/short-term/working_state")
    assert response.status_code == 200
    data = response.json()
    assert data["key"] == "working_state"
    assert data["value"]["task"] == "running"


@pytest.mark.asyncio
async def test_long_term_memory():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        await client.post(
            "/memory/long-term/incident_001",
            json={
                "key": "incident_001",
                "value": {"summary": "disk failure"},
                "importance": 0.9,
            },
        )
        response = await client.get("/memory/long-term/incident_001")
    assert response.status_code == 200
    data = response.json()
    assert data["value"]["summary"] == "disk failure"


@pytest.mark.asyncio
async def test_semantic_memory():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        await client.post(
            "/memory/semantic",
            json={
                "entity": "server",
                "relation": "causes",
                "target": "cpu_alert",
                "metadata": {"weight": 0.8},
            },
        )
        response = await client.get("/memory/semantic/server")
    assert response.status_code == 200
    data = response.json()
    assert len(data["triples"]) == 1
    assert data["triples"][0]["target"] == "cpu_alert"


@pytest.mark.asyncio
async def test_procedural_memory():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        store_response = await client.post(
            "/memory/procedural",
            json={
                "name": "handle_cpu_spike",
                "steps": ["check metrics", "identify process", "restart service"],
                "expected_outcome": "cpu normalized",
            },
        )
    assert store_response.status_code == 200
    data = store_response.json()
    proc_id = data["procedure_id"]
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(f"/memory/procedural/{proc_id}")
    assert response.status_code == 200
    assert response.json()["procedure"]["name"] == "handle_cpu_spike"


@pytest.mark.asyncio
async def test_rpc_methods():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/rpc/list_methods", json={})
    assert response.status_code == 200
    assert "store_event" in response.json()


# ------------------------------------------------------------------
# Core tests
# ------------------------------------------------------------------
@pytest.mark.asyncio
async def test_text_to_vector():
    v1 = _text_to_vector("hello", 128)
    v2 = _text_to_vector("hello", 128)
    assert len(v1) == 128
    assert abs(_cosine_similarity(v1, v2) - 1.0) < 1e-9


@pytest.mark.asyncio
async def test_store_event_core(orchestrator):
    request = StoreEventRequest(event=EventMemory(event_type="alert", source="cpu"))
    response = await orchestrator.store_event(request)
    assert response.stored
    assert response.event_id


@pytest.mark.asyncio
async def test_search_similar_core(orchestrator):
    event = EventMemory(event_type="alert", source="cpu", payload={"cpu": 95})
    await orchestrator.store_event(StoreEventRequest(event=event))
    response = await orchestrator.search_similar(SimilarityQueryRequest(query="cpu high alert"))
    assert len(response.results) >= 1


@pytest.mark.asyncio
async def test_learn_experience_core(orchestrator):
    response = await orchestrator.learn_experience(
        LearnExperienceRequest(
            situation="cpu high", action="restart", outcome="fixed", confidence=0.8
        )
    )
    assert response.learned
    assert response.confidence == 0.8

    # Repeating should update occurrences and confidence
    response2 = await orchestrator.learn_experience(
        LearnExperienceRequest(
            situation="cpu high", action="restart", outcome="fixed", confidence=0.8
        )
    )
    assert response2.experience_id == response.experience_id


@pytest.mark.asyncio
async def test_accumulate_knowledge_core(orchestrator):
    response = await orchestrator.accumulate_knowledge(
        AccumulateKnowledgeRequest(
            entries=[
                KnowledgeEntry(subject="server", predicate="has_issue", object="cpu_high"),
                KnowledgeEntry(subject="server", predicate="has_issue", object="cpu_high"),
            ]
        )
    )
    assert response.stored == 1
    assert response.updated == 1


@pytest.mark.asyncio
async def test_recognize_pattern_sequence(orchestrator):
    response = await orchestrator.recognize_pattern(
        PatternRequest(
            data=[
                {"event_type": "alert"},
                {"event_type": "alert"},
                {"event_type": "recovery"},
                {"event_type": "alert"},
                {"event_type": "recovery"},
            ],
            pattern_type="sequence",
        )
    )
    assert response.total >= 1


@pytest.mark.asyncio
async def test_recognize_pattern_frequency(orchestrator):
    response = await orchestrator.recognize_pattern(
        PatternRequest(
            data=[
                {"value": "timeout"},
                {"value": "timeout"},
                {"value": "timeout"},
                {"value": "timeout"},
                {"value": "error"},
            ],
            pattern_type="frequency",
        )
    )
    assert response.total >= 1


@pytest.mark.asyncio
async def test_short_term_memory_core(orchestrator):
    await orchestrator.store_short_term(
        ShortTermRequest(key="task", value={"status": "running"}, ttl_seconds=60)
    )
    value = await orchestrator.retrieve_short_term("task")
    assert value["status"] == "running"


@pytest.mark.asyncio
async def test_long_term_memory_core(orchestrator):
    await orchestrator.store_long_term(
        LongTermRequest(key="incident", value={"summary": "disk failure"}, importance=0.9)
    )
    value = await orchestrator.retrieve_long_term("incident")
    assert value["summary"] == "disk failure"


@pytest.mark.asyncio
async def test_semantic_memory_core(orchestrator):
    await orchestrator.store_semantic(
        SemanticRequest(entity="server", relation="causes", target="alert")
    )
    triples = await orchestrator.retrieve_semantic("server")
    assert len(triples) == 1
    assert triples[0].target == "alert"


@pytest.mark.asyncio
async def test_procedural_memory_core(orchestrator):
    response = await orchestrator.store_procedural(
        ProceduralRequest(
            name="fix_cpu",
            steps=["check", "restart"],
            expected_outcome="normal",
        )
    )
    proc = await orchestrator.retrieve_procedural(response.procedure_id)
    assert proc is not None
    assert proc.name == "fix_cpu"


@pytest.mark.asyncio
async def test_get_stats(orchestrator):
    await orchestrator.store_short_term(ShortTermRequest(key="x", value=1))
    stats = await orchestrator.get_stats()
    assert stats.service == "scenario-memory-service"
    assert "short_term" in stats.memory_entries


def test_list_methods(orchestrator):
    assert "store_event" in orchestrator.list_methods()
    assert "recognize_pattern" in orchestrator.list_methods()


def test_grpc_server():
    server = ScenarioRPCServer()
    server.register("echo", lambda x: x)
    assert "echo" in server.list_methods()


@pytest.mark.asyncio
async def test_rpc_client(mocker):
    from unittest.mock import AsyncMock, MagicMock, patch

    mock_response = MagicMock()
    mock_response.json.return_value = {"ok": True}
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.post.return_value = mock_response

    with patch(
        "services.scenario_memory_service.grpc.client.httpx.AsyncClient",
        return_value=mock_client,
    ):
        client = ScenarioRPCClient()
        result = await client.call("echo", {"x": "hello"})
    assert result == {"ok": True}


# ------------------------------------------------------------------
# Cache / retry / grpc unit tests
# ------------------------------------------------------------------
@pytest.mark.asyncio
async def test_cache_redis_path():
    from unittest.mock import AsyncMock

    fake_redis = AsyncMock()
    fake_redis.get.return_value = '{"value": 42}'

    cache = CacheManager("redis://localhost:6379")
    # Trigger fallback connect path (no aioredis installed) then inject fake redis.
    await cache.connect()
    cache._redis = fake_redis

    value = await cache.get("key")
    await cache.set("key", {"value": 1})
    await cache.delete("key")
    await cache.clear()

    assert value == {"value": 42}
    fake_redis.setex.assert_called_once()
    fake_redis.delete.assert_called_once()
    fake_redis.flushdb.assert_called_once()


@pytest.mark.asyncio
async def test_retry_engine_success():
    from services.scenario_memory_service.retry import ScenarioRetryEngine

    engine = ScenarioRetryEngine()

    async def ok():
        return "ok"

    result = await engine.execute(ok, operation="test")
    assert result == "ok"


@pytest.mark.asyncio
async def test_retry_engine_failure():
    from unittest.mock import patch

    from services.scenario_memory_service.retry import ScenarioRetryEngine

    engine = ScenarioRetryEngine("exponential_fast")
    calls = 0

    async def flaky():
        nonlocal calls
        calls += 1
        if calls < 2:
            raise RuntimeError("retryable error")
        return "ok"

    with patch("services.scenario_memory_service.retry.asyncio.sleep"):
        result = await engine.execute(flaky, operation="flaky")
    assert result == "ok"
    assert calls == 2


@pytest.mark.asyncio
async def test_grpc_server_async_call():
    server = ScenarioRPCServer()

    async def echo(x):
        return x

    server.register("echo", echo)
    result = await server.call("echo", x="hello")
    assert result == "hello"


async def test_grpc_server_unknown():
    server = ScenarioRPCServer()
    with pytest.raises(ValueError):
        await server.call("missing")


@pytest.mark.asyncio
async def test_cache_redis_errors():
    from unittest.mock import AsyncMock

    cache = CacheManager("redis://localhost")
    fake_redis = AsyncMock()
    fake_redis.get.side_effect = Exception("redis down")
    fake_redis.setex.side_effect = Exception("redis down")
    fake_redis.delete.side_effect = Exception("redis down")
    fake_redis.flushdb.side_effect = Exception("redis down")
    cache._redis = fake_redis

    await cache.set("k", {"a": 1})
    # Redis get fails; in-memory fallback should still hold the value.
    assert await cache.get("k") == {"a": 1}
    await cache.delete("k")
    await cache.clear()

    # Repeated connect with redis already set returns early.
    await cache.connect()


@pytest.mark.asyncio
async def test_retry_sync_and_final_raise():
    from unittest.mock import patch

    from services.scenario_memory_service.retry import ScenarioRetryEngine

    engine = ScenarioRetryEngine("none")

    def sync_ok():
        return "ok"

    assert await engine.execute(sync_ok, operation="sync") == "ok"

    async def always_fail():
        raise RuntimeError("fail")

    with patch("services.scenario_memory_service.retry.asyncio.sleep"):
        with pytest.raises(RuntimeError):
            await engine.execute(always_fail, operation="fail")


@pytest.mark.asyncio
async def test_recognize_pattern_correlation(orchestrator):
    response = await orchestrator.recognize_pattern(
        PatternRequest(
            data=[
                {"a": 1, "b": 2},
                {"a": 2, "b": 3},
            ],
            pattern_type="correlation",
        )
    )
    assert response.total >= 1
