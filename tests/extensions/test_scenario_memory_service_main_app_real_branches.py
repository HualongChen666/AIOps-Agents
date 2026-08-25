# -*- coding: utf-8 -*-
"""Real-execution branch coverage for the Scenario Memory main_app.py."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from httpx import HTTPStatusError

from extensions.addons.operations.scenario_memory_service.cache import CacheManager
from extensions.addons.operations.scenario_memory_service.main_app import app, get_orchestrator
from extensions.addons.operations.scenario_memory_service.orchestrator import (
    ScenarioMemoryOrchestrator,
)
from extensions.addons.operations.scenario_memory_service.retry import ScenarioRetryEngine
from extensions.addons.operations.scenario_memory_service.schemas import (
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


@pytest.fixture
def client():
    """Return a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def orchestrator_with_cache():
    """Return an orchestrator with connected cache."""
    orch = ScenarioMemoryOrchestrator(
        cache=CacheManager(""),
        retry_engine=ScenarioRetryEngine(),
    )
    # Override the global orchestrator
    import extensions.addons.operations.scenario_memory_service.main_app as main_app_module

    main_app_module._orchestrator = orch
    return orch


# ------------------------------------------------------------------
# Exception handling in POST endpoints (lines 78-81, 86-89, 94-97, 104-107, 112-115, 120-125, 137-138, 143-148, 160-161, 166-169, 177-178, 183-186, 198-199, 204-214, 224-237)
# ------------------------------------------------------------------
def test_store_event_exception_handling(client, orchestrator_with_cache):
    """Test exception handling in store_event endpoint (lines 78-81)."""
    # Force an exception by making orchestrator raise
    original_orch = get_orchestrator()

    async def broken_store_event(request):
        raise ValueError("Test exception")

    original_fn = original_orch.store_event
    original_orch.store_event = broken_store_event

    response = client.post(
        "/store/event",
        json={"event": {"event_type": "test", "source": "unit", "payload": {}}},
    )
    assert response.status_code == 500
    assert "Test exception" in response.json()["detail"]

    # Restore
    original_orch.store_event = original_fn


def test_search_similar_exception_handling(client, orchestrator_with_cache):
    """Test exception handling in search_similar endpoint (lines 86-89)."""
    original_orch = get_orchestrator()

    async def broken_search_similar(request):
        raise RuntimeError("Search failed")

    original_fn = original_orch.search_similar
    original_orch.search_similar = broken_search_similar

    response = client.post(
        "/search/similar",
        json={"query": "test", "top_k": 5, "threshold": 0.7},
    )
    assert response.status_code == 500
    assert "Search failed" in response.json()["detail"]

    original_orch.search_similar = original_fn


def test_learn_experience_exception_handling(client, orchestrator_with_cache):
    """Test exception handling in learn_experience endpoint (lines 94-97)."""
    original_orch = get_orchestrator()

    async def broken_learn_experience(request):
        raise KeyError("Missing key")

    original_fn = original_orch.learn_experience
    original_orch.learn_experience = broken_learn_experience

    response = client.post(
        "/learn/experience",
        json={"situation": "s", "action": "a", "outcome": "ok", "confidence": 0.5},
    )
    assert response.status_code == 500
    assert "Missing key" in response.json()["detail"]

    original_orch.learn_experience = original_fn


def test_accumulate_knowledge_exception_handling(client, orchestrator_with_cache):
    """Test exception handling in accumulate_knowledge endpoint (lines 104-107)."""
    original_orch = get_orchestrator()

    async def broken_accumulate_knowledge(request):
        raise TypeError("Type error")

    original_fn = original_orch.accumulate_knowledge
    original_orch.accumulate_knowledge = broken_accumulate_knowledge

    response = client.post(
        "/accumulate/knowledge",
        json={"entries": [{"subject": "a", "predicate": "b", "object": "c", "weight": 1.0}]},
    )
    assert response.status_code == 500
    assert "Type error" in response.json()["detail"]

    original_orch.accumulate_knowledge = original_fn


def test_recognize_pattern_exception_handling(client, orchestrator_with_cache):
    """Test exception handling in recognize_pattern endpoint (lines 112-115)."""
    original_orch = get_orchestrator()

    async def broken_recognize_pattern(request):
        raise AttributeError("Attribute error")

    original_fn = original_orch.recognize_pattern
    original_orch.recognize_pattern = broken_recognize_pattern

    response = client.post(
        "/recognize/pattern",
        json={"pattern_type": "sequence", "data": [{"event_type": "a"}]},
    )
    assert response.status_code == 500
    assert "Attribute error" in response.json()["detail"]

    original_orch.recognize_pattern = original_fn


def test_store_short_term_key_mismatch(client, orchestrator_with_cache):
    """Test key mismatch handling in store_short_term (lines 121-122)."""
    # This tests the branch where request.key != key
    response = client.post(
        "/memory/short-term/path_key",
        json={"key": "request_key", "value": "test_value", "ttl_seconds": 300},
    )
    assert response.status_code == 200
    assert response.json()["key"] == "path_key"


def test_store_short_term_exception_handling(client, orchestrator_with_cache):
    """Test exception handling in store_short_term endpoint (lines 124-125)."""
    original_orch = get_orchestrator()

    async def broken_store_short_term(request):
        raise ValueError("Storage error")

    original_fn = original_orch.store_short_term
    original_orch.store_short_term = broken_store_short_term

    response = client.post(
        "/memory/short-term/test_key",
        json={"key": "test_key", "value": "test_value", "ttl_seconds": 300},
    )
    assert response.status_code == 500
    assert "Storage error" in response.json()["detail"]

    original_orch.store_short_term = original_fn


def test_retrieve_short_term_not_found(client, orchestrator_with_cache):
    """Test 404 when short-term memory not found (line 133-134)."""
    response = client.get("/memory/short-term/nonexistent_key")
    assert response.status_code == 404
    assert "Short-term memory not found" in response.json()["detail"]


def test_retrieve_short_term_exception_handling(client, orchestrator_with_cache):
    """Test exception handling in retrieve_short_term endpoint (lines 137-138)."""
    original_orch = get_orchestrator()

    async def broken_retrieve_short_term(key, session_id=None):
        raise RuntimeError("Retrieval error")

    original_fn = original_orch.retrieve_short_term
    original_orch.retrieve_short_term = broken_retrieve_short_term

    response = client.get("/memory/short-term/test_key")
    assert response.status_code == 500
    assert "Retrieval error" in response.json()["detail"]

    original_orch.retrieve_short_term = original_fn


def test_store_long_term_key_mismatch(client, orchestrator_with_cache):
    """Test key mismatch handling in store_long_term (lines 144-145)."""
    response = client.post(
        "/memory/long-term/path_key",
        json={"key": "request_key", "value": "test_value", "importance": 1.0},
    )
    assert response.status_code == 200
    assert response.json()["key"] == "path_key"


def test_store_long_term_exception_handling(client, orchestrator_with_cache):
    """Test exception handling in store_long_term endpoint (lines 147-148)."""
    original_orch = get_orchestrator()

    async def broken_store_long_term(request):
        raise ValueError("Long-term storage error")

    original_fn = original_orch.store_long_term
    original_orch.store_long_term = broken_store_long_term

    response = client.post(
        "/memory/long-term/test_key",
        json={"key": "test_key", "value": "test_value", "importance": 1.0},
    )
    assert response.status_code == 500
    assert "Long-term storage error" in response.json()["detail"]

    original_orch.store_long_term = original_fn


def test_retrieve_long_term_not_found(client, orchestrator_with_cache):
    """Test 404 when long-term memory not found (line 156-157)."""
    response = client.get("/memory/long-term/nonexistent_key")
    assert response.status_code == 404
    assert "Long-term memory not found" in response.json()["detail"]


def test_retrieve_long_term_exception_handling(client, orchestrator_with_cache):
    """Test exception handling in retrieve_long_term endpoint (lines 160-161)."""
    original_orch = get_orchestrator()

    async def broken_retrieve_long_term(key, session_id=None):
        raise RuntimeError("Long-term retrieval error")

    original_fn = original_orch.retrieve_long_term
    original_orch.retrieve_long_term = broken_retrieve_long_term

    response = client.get("/memory/long-term/test_key")
    assert response.status_code == 500
    assert "Long-term retrieval error" in response.json()["detail"]

    original_orch.retrieve_long_term = original_fn


def test_store_semantic_exception_handling(client, orchestrator_with_cache):
    """Test exception handling in store_semantic endpoint (lines 166-169)."""
    original_orch = get_orchestrator()

    async def broken_store_semantic(request):
        raise ValueError("Semantic storage error")

    original_fn = original_orch.store_semantic
    original_orch.store_semantic = broken_store_semantic

    response = client.post(
        "/memory/semantic",
        json={"entity": "test", "relation": "has", "target": "property"},
    )
    assert response.status_code == 500
    assert "Semantic storage error" in response.json()["detail"]

    original_orch.store_semantic = original_fn


def test_retrieve_semantic_exception_handling(client, orchestrator_with_cache):
    """Test exception handling in retrieve_semantic endpoint (lines 177-178)."""
    original_orch = get_orchestrator()

    async def broken_retrieve_semantic(entity):
        raise RuntimeError("Semantic retrieval error")

    original_fn = original_orch.retrieve_semantic
    original_orch.retrieve_semantic = broken_retrieve_semantic

    response = client.get("/memory/semantic/test_entity")
    assert response.status_code == 500
    assert "Semantic retrieval error" in response.json()["detail"]

    original_orch.retrieve_semantic = original_fn


def test_store_procedural_exception_handling(client, orchestrator_with_cache):
    """Test exception handling in store_procedural endpoint (lines 183-186)."""
    original_orch = get_orchestrator()

    async def broken_store_procedural(request):
        raise ValueError("Procedural storage error")

    original_fn = original_orch.store_procedural
    original_orch.store_procedural = broken_store_procedural

    response = client.post(
        "/memory/procedural",
        json={"name": "test_procedure", "steps": ["step1", "step2"]},
    )
    assert response.status_code == 500
    assert "Procedural storage error" in response.json()["detail"]

    original_orch.store_procedural = original_fn


def test_retrieve_procedural_not_found(client, orchestrator_with_cache):
    """Test 404 when procedural memory not found (line 194-195)."""
    response = client.get("/memory/procedural/nonexistent_key")
    assert response.status_code == 404
    assert "Procedural memory not found" in response.json()["detail"]


def test_retrieve_procedural_exception_handling(client, orchestrator_with_cache):
    """Test exception handling in retrieve_procedural endpoint (lines 198-199)."""
    original_orch = get_orchestrator()

    async def broken_retrieve_procedural(key):
        raise RuntimeError("Procedural retrieval error")

    original_fn = original_orch.retrieve_procedural
    original_orch.retrieve_procedural = broken_retrieve_procedural

    response = client.get("/memory/procedural/test_key")
    assert response.status_code == 500
    assert "Procedural retrieval error" in response.json()["detail"]

    original_orch.retrieve_procedural = original_fn


def test_find_experiences_exception_handling(client, orchestrator_with_cache):
    """Test exception handling in find_experiences endpoint (lines 213-214)."""
    original_orch = get_orchestrator()

    async def broken_find_experiences(query, top_k=5, session_id=None):
        raise RuntimeError("Find experiences error")

    original_fn = original_orch.find_experiences
    original_orch.find_experiences = broken_find_experiences

    response = client.get("/experiences/find?query=test")
    assert response.status_code == 500
    assert "Find experiences error" in response.json()["detail"]

    original_orch.find_experiences = original_fn


def test_correct_experience_not_found(client, orchestrator_with_cache):
    """Test 404 when experience to correct not found (lines 231-232)."""
    response = client.post(
        "/experience/correct?situation=nonexistent&action=missing&corrected_by=user"
    )
    assert response.status_code == 404
    assert "Experience not found" in response.json()["detail"]


def test_correct_experience_exception_handling(client, orchestrator_with_cache):
    """Test exception handling in correct_experience endpoint (lines 236-237)."""
    original_orch = get_orchestrator()

    async def broken_correct_experience(situation, action, corrected_by, corrected_outcome=None):
        raise RuntimeError("Correction error")

    original_fn = original_orch.correct_experience
    original_orch.correct_experience = broken_correct_experience

    response = client.post("/experience/correct?situation=test&action=test&corrected_by=user")
    assert response.status_code == 500
    assert "Correction error" in response.json()["detail"]

    original_orch.correct_experience = original_fn


# ------------------------------------------------------------------
# RPC endpoint branches (lines 243-278)
# ------------------------------------------------------------------
def test_rpc_with_none_payload(client, orchestrator_with_cache):
    """Test RPC with None payload (line 243-244)."""
    response = client.post("/rpc/list_methods")
    assert response.status_code == 200
    assert "store_event" in response.json()


def test_rpc_list_methods(client, orchestrator_with_cache):
    """Test RPC list_methods branch (line 246-247)."""
    response = client.post("/rpc/list_methods", json={})
    assert response.status_code == 200
    assert "store_event" in response.json()
    assert "get_stats" in response.json()


def test_rpc_stats(client, orchestrator_with_cache):
    """Test RPC stats branch (line 248-249)."""
    response = client.post("/rpc/stats", json={})
    assert response.status_code == 200
    assert "service" in response.json()


def test_rpc_unknown_method(client, orchestrator_with_cache):
    """Test RPC unknown method branch (lines 250-251)."""
    response = client.post("/rpc/unknown_method", json={})
    assert response.status_code == 404
    assert "Unknown RPC method" in response.json()["detail"]


def test_rpc_with_request_type(client, orchestrator_with_cache):
    """Test RPC with request type (lines 266-267)."""
    # First store an event
    response = client.post(
        "/rpc/store_event",
        json={"event": {"event_type": "test", "source": "unit", "payload": {"test": "data"}}},
    )
    assert response.status_code == 200
    assert "event_id" in response.json()


def test_rpc_without_request_type(client, orchestrator_with_cache):
    """Test RPC without request type (line 269)."""
    # Call a method that doesn't require a request type
    response = client.post("/rpc/get_stats", json={})
    assert response.status_code == 200


def test_rpc_exception_handling(client, orchestrator_with_cache):
    """Test RPC exception handling (lines 275-278)."""
    original_orch = get_orchestrator()

    async def broken_method(**kwargs):
        raise ValueError("RPC method error")

    # Add a broken method to orchestrator
    original_orch.broken_method = broken_method

    response = client.post("/rpc/broken_method", json={})
    assert response.status_code == 404  # Will be 404 because it's not in the request_types dict

    # Test with a method that is in request_types but fails
    original_store_event = original_orch.store_event

    async def broken_store_event_with_request(request):
        raise ValueError("Store event error")

    original_orch.store_event = broken_store_event_with_request

    response = client.post(
        "/rpc/store_event", json={"event": {"event_type": "test", "source": "unit", "payload": {}}}
    )
    assert response.status_code == 500
    assert "Store event error" in response.json()["detail"]

    original_orch.store_event = original_store_event


# ------------------------------------------------------------------
# Happy path tests to ensure basic functionality
# ------------------------------------------------------------------
def test_health_endpoint(client):
    """Test health endpoint works."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_metrics_endpoint(client):
    """Test metrics endpoint works."""
    response = client.get("/metrics")
    assert response.status_code == 200


def test_stats_endpoint(client, orchestrator_with_cache):
    """Test stats endpoint works."""
    response = client.get("/stats")
    assert response.status_code == 200
    assert "service" in response.json()


def test_store_event_happy_path(client, orchestrator_with_cache):
    """Test store_event happy path."""
    response = client.post(
        "/store/event",
        json={"event": {"event_type": "test", "source": "unit", "payload": {}}},
    )
    assert response.status_code == 200
    assert response.json()["stored"] is True


def test_search_similar_happy_path(client, orchestrator_with_cache):
    """Test search_similar happy path."""
    # First store an event
    client.post(
        "/store/event",
        json={"event": {"event_type": "test", "source": "unit", "payload": {"text": "cpu high"}}},
    )

    response = client.post(
        "/search/similar",
        json={"query": "cpu high", "top_k": 5, "threshold": 0.0},
    )
    assert response.status_code == 200
    assert "total" in response.json()


def test_learn_experience_happy_path(client, orchestrator_with_cache):
    """Test learn_experience happy path."""
    response = client.post(
        "/learn/experience",
        json={"situation": "cpu high", "action": "restart", "outcome": "ok", "confidence": 0.8},
    )
    assert response.status_code == 200
    assert response.json()["learned"] is True


def test_accumulate_knowledge_happy_path(client, orchestrator_with_cache):
    """Test accumulate_knowledge happy path."""
    response = client.post(
        "/accumulate/knowledge",
        json={
            "entries": [{"subject": "host", "predicate": "has", "object": "disk", "weight": 1.0}]
        },
    )
    assert response.status_code == 200
    assert response.json()["stored"] == 1


def test_recognize_pattern_happy_path(client, orchestrator_with_cache):
    """Test recognize_pattern happy path."""
    response = client.post(
        "/recognize/pattern",
        json={
            "pattern_type": "sequence",
            "data": [
                {"event_type": "a"},
                {"event_type": "b"},
                {"event_type": "a"},
                {"event_type": "b"},
            ],
        },
    )
    assert response.status_code == 200
    assert "total" in response.json()


def test_store_short_term_happy_path(client, orchestrator_with_cache):
    """Test store_short_term happy path."""
    response = client.post(
        "/memory/short-term/test_key",
        json={"key": "test_key", "value": "test_value", "ttl_seconds": 300},
    )
    assert response.status_code == 200
    assert response.json()["stored"] is True


def test_retrieve_short_term_happy_path(client, orchestrator_with_cache):
    """Test retrieve_short_term happy path."""
    # First store
    client.post(
        "/memory/short-term/test_key",
        json={"key": "test_key", "value": "test_value", "ttl_seconds": 300},
    )

    # Then retrieve
    response = client.get("/memory/short-term/test_key")
    assert response.status_code == 200
    assert response.json()["value"] == "test_value"


def test_store_long_term_happy_path(client, orchestrator_with_cache):
    """Test store_long_term happy path."""
    response = client.post(
        "/memory/long-term/test_key",
        json={"key": "test_key", "value": "test_value", "importance": 1.0},
    )
    assert response.status_code == 200
    assert response.json()["stored"] is True


def test_retrieve_long_term_happy_path(client, orchestrator_with_cache):
    """Test retrieve_long_term happy path."""
    # First store
    client.post(
        "/memory/long-term/test_key",
        json={"key": "test_key", "value": "test_value", "importance": 1.0},
    )

    # Then retrieve
    response = client.get("/memory/long-term/test_key")
    assert response.status_code == 200
    assert response.json()["value"] == "test_value"


def test_store_semantic_happy_path(client, orchestrator_with_cache):
    """Test store_semantic happy path."""
    response = client.post(
        "/memory/semantic",
        json={"entity": "host", "relation": "has", "target": "disk"},
    )
    assert response.status_code == 200
    assert response.json()["stored"] is True


def test_retrieve_semantic_happy_path(client, orchestrator_with_cache):
    """Test retrieve_semantic happy path."""
    # First store
    client.post(
        "/memory/semantic",
        json={"entity": "host", "relation": "has", "target": "disk"},
    )

    # Then retrieve
    response = client.get("/memory/semantic/host")
    assert response.status_code == 200
    assert "entity" in response.json()


def test_store_procedural_happy_path(client, orchestrator_with_cache):
    """Test store_procedural happy path."""
    response = client.post(
        "/memory/procedural",
        json={"name": "restart", "steps": ["stop", "start"]},
    )
    assert response.status_code == 200
    assert response.json()["stored"] is True


def test_retrieve_procedural_happy_path(client, orchestrator_with_cache):
    """Test retrieve_procedural happy path."""
    # First store
    response = client.post(
        "/memory/procedural",
        json={"name": "restart", "steps": ["stop", "start"]},
    )
    proc_id = response.json()["procedure_id"]

    # Then retrieve
    response = client.get(f"/memory/procedural/{proc_id}")
    assert response.status_code == 200
    assert "procedure" in response.json()


def test_find_experiences_happy_path(client, orchestrator_with_cache):
    """Test find_experiences happy path."""
    # First learn an experience
    client.post(
        "/learn/experience",
        json={"situation": "cpu high", "action": "restart", "outcome": "ok", "confidence": 0.8},
    )

    # Then find
    response = client.get("/experiences/find?query=cpu")
    assert response.status_code == 200
    assert "experiences" in response.json()


def test_correct_experience_happy_path(client, orchestrator_with_cache):
    """Test correct_experience happy path."""
    # First learn an experience
    client.post(
        "/learn/experience",
        json={"situation": "cpu high", "action": "restart", "outcome": "bad", "confidence": 0.8},
    )

    # Then correct
    response = client.post(
        "/experience/correct?situation=cpu high&action=restart&corrected_by=admin&corrected_outcome=ok"
    )
    assert response.status_code == 200
    assert "corrected_experience_id" in response.json()


# ------------------------------------------------------------------
# Additional tests to cover remaining branches (lines 47, 53-54, 274, 276)
# ------------------------------------------------------------------
def test_get_orchestrator_singleton(client, orchestrator_with_cache):
    """Test get_orchestrator singleton pattern (line 47)."""
    # Reset the global orchestrator to None to test the initialization branch
    import extensions.addons.operations.scenario_memory_service.main_app as main_app_module

    main_app_module._orchestrator = None

    # Call get_orchestrator to trigger the initialization
    orch = main_app_module.get_orchestrator()
    assert orch is not None

    # Call again to test the cached branch
    orch2 = main_app_module.get_orchestrator()
    assert orch is orch2


def test_startup_event(client, orchestrator_with_cache):
    """Test startup event connects cache (lines 53-54)."""
    # The startup event is called automatically when the app starts
    # We can test by ensuring the cache is connected
    import asyncio

    from extensions.addons.operations.scenario_memory_service.main_app import (
        get_orchestrator,
        startup,
    )

    orch = get_orchestrator()
    # Cache should be connected after startup
    assert orch.cache is not None

    # Test the actual startup function
    # Run startup to trigger the connect call
    # This will call orch.cache.connect() which is the branch we want to cover
    asyncio.run(startup())
    # Verify cache is still valid
    assert orch.cache is not None


def test_rpc_with_base_model_result(client, orchestrator_with_cache):
    """Test RPC with BaseModel result (line 274)."""
    # Test a method that returns a BaseModel
    response = client.post(
        "/rpc/store_event",
        json={"event": {"event_type": "test", "source": "unit", "payload": {"test": "data"}}},
    )
    assert response.status_code == 200
    # The result should be a dict (model_dump of BaseModel)
    assert isinstance(response.json(), dict)

    # Also test with a method that's in request_types but doesn't require payload
    response = client.post("/rpc/stats", json={})
    assert response.status_code == 200
    # StatsResponse is also a BaseModel
    assert isinstance(response.json(), dict)

    # Test accumulate_knowledge which also returns a BaseModel
    response = client.post(
        "/rpc/accumulate_knowledge",
        json={
            "entries": [{"subject": "host", "predicate": "has", "object": "disk", "weight": 1.0}]
        },
    )
    assert response.status_code == 200
    assert isinstance(response.json(), dict)

    # Test list_methods which returns a list (not BaseModel) to cover line 274
    response = client.post("/rpc/list_methods", json={})
    assert response.status_code == 200
    # The result should be a list (not a BaseModel, so it's returned as-is)
    assert isinstance(response.json(), list)

    # Test find_experiences which returns a List[Experience] (not a BaseModel instance)
    # First learn an experience
    client.post(
        "/learn/experience",
        json={"situation": "cpu high", "action": "restart", "outcome": "ok", "confidence": 0.8},
    )
    # Then call via RPC - this should hit line 274 since it returns a list
    response = client.post("/rpc/find_experiences", json={"query": "cpu", "top_k": 5})
    assert response.status_code == 200
    # The result is a list of Experience objects (not a BaseModel instance)
    assert isinstance(response.json(), list)


def test_rpc_http_exception_reraise(client, orchestrator_with_cache):
    """Test RPC HTTPException is re-raised (line 276)."""
    original_orch = get_orchestrator()

    # Create a method that raises HTTPException
    from fastapi import HTTPException

    async def method_with_http_exception(**kwargs):
        raise HTTPException(status_code=400, detail="Bad request")

    original_orch.method_with_http_exception = method_with_http_exception

    response = client.post("/rpc/method_with_http_exception", json={})
    # Should get 404 because method is not in request_types
    assert response.status_code == 404

    # Now test with a method that IS in request_types and raises HTTPException
    original_store_event = original_orch.store_event

    async def store_event_with_http_exception(request):
        raise HTTPException(status_code=400, detail="Bad request from store_event")

    original_orch.store_event = store_event_with_http_exception

    response = client.post(
        "/rpc/store_event", json={"event": {"event_type": "test", "source": "unit", "payload": {}}}
    )
    # Should get 400 from the HTTPException
    assert response.status_code == 400
    assert "Bad request from store_event" in response.json()["detail"]

    # Restore
    original_orch.store_event = original_store_event
