# -*- coding: utf-8 -*-
"""Real-execution branch coverage for the Scenario Memory orchestrator."""

from __future__ import annotations

import math
from datetime import datetime, timedelta
from typing import Any, Dict, List

import pytest

from extensions.addons.operations.scenario_memory_service.cache import CacheManager
from extensions.addons.operations.scenario_memory_service.config import ScenarioMemorySettings
from extensions.addons.operations.scenario_memory_service.orchestrator import (
    ScenarioMemoryOrchestrator,
    _cosine_similarity,
    _text_to_vector,
    _tokenize,
)
from extensions.addons.operations.scenario_memory_service.retry import ScenarioRetryEngine
from extensions.addons.operations.scenario_memory_service.schemas import (
    AccumulateKnowledgeRequest,
    EventMemory,
    Experience,
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
def orchestrator() -> ScenarioMemoryOrchestrator:
    """Return a fresh orchestrator backed by real in-memory components."""
    return ScenarioMemoryOrchestrator(
        cache=CacheManager(""),
        retry_engine=ScenarioRetryEngine(),
    )


@pytest.fixture
def small_settings() -> ScenarioMemorySettings:
    """Return real settings tuned for capacity/branch tests."""
    return ScenarioMemorySettings(
        short_term_capacity=1,
        long_term_capacity=1,
        default_cache_ttl=60,
        embedding_dimension=128,
    )


# ------------------------------------------------------------------
# Internal text vectorizer helpers
# ------------------------------------------------------------------
def test_tokenize_varied_text():
    assert _tokenize("") == []
    assert _tokenize("!!!") == []
    assert _tokenize("hello") == ["hello"]
    assert _tokenize("你好世界") == ["你好", "好世", "世界"]
    assert _tokenize("Mix123_abc 中国") == ["中国", "mix123_abc"]


def test_text_to_vector_edge_cases():
    empty = _text_to_vector("")
    assert len(empty) == 128
    assert all(v == 0.0 for v in empty)

    repeated = _text_to_vector("hello hello hello")
    norm = math.sqrt(sum(v * v for v in repeated))
    assert math.isclose(norm, 1.0, rel_tol=1e-9)


def test_cosine_similarity_with_zero_and_different_lengths():
    a = _text_to_vector("hello")
    b = _text_to_vector("")
    # zero vector has all components == 1.0 after fallback norm
    assert _cosine_similarity(a, b) == 0.0
    assert _cosine_similarity([1.0, 0.0], [1.0, 0.0, 2.0]) <= 1.0


# ------------------------------------------------------------------
# Stats / introspection
# ------------------------------------------------------------------
async def test_list_methods_and_get_stats(orchestrator: ScenarioMemoryOrchestrator):
    methods = orchestrator.list_methods()
    assert "store_event" in methods
    assert "get_stats" in methods

    stats = await orchestrator.get_stats()
    assert stats.service == orchestrator.settings.service_name
    assert stats.cache_size == 0
    assert set(stats.retry_policies) == {"exponential", "linear", "none"}


# ------------------------------------------------------------------
# store_event and search_similar branches
# ------------------------------------------------------------------
async def test_store_event_generates_id_and_vector(orchestrator: ScenarioMemoryOrchestrator):
    event = EventMemory(event_type="test", source="unit", payload={"x": 1})
    resp = await orchestrator.store_event(StoreEventRequest(event=event))
    assert resp.event_id
    assert resp.stored and resp.indexed and resp.cached
    assert orchestrator._events[resp.event_id].vector is not None


async def test_store_event_keeps_provided_id_and_vector(orchestrator: ScenarioMemoryOrchestrator):
    vector = _text_to_vector("provided")
    event = EventMemory(
        event_id="e1",
        event_type="test",
        source="unit",
        payload={"x": 1},
        vector=vector,
    )
    resp = await orchestrator.store_event(StoreEventRequest(event=event))
    assert resp.event_id == "e1"
    assert orchestrator._events["e1"].vector == vector


async def test_search_similar_with_no_vector_events(orchestrator: ScenarioMemoryOrchestrator):
    orchestrator._events["e2"] = EventMemory(
        event_id="e2",
        event_type="missing",
        source="unit",
        payload={},
    )
    resp = await orchestrator.search_similar(
        SimilarityQueryRequest(query="foo", top_k=5, threshold=0.0)
    )
    assert resp.total == 0


async def test_search_similar_with_session_filtering(orchestrator: ScenarioMemoryOrchestrator):
    # Two events with explicit, nearly identical vectors.
    v = _text_to_vector("cpu high load")
    for eid, sid in [("e3", "s1"), ("e4", "s2")]:
        orchestrator._events[eid] = EventMemory(
            event_id=eid,
            event_type="alert",
            source="unit",
            payload={"text": "cpu high load"},
            vector=v,
            session_id=sid,
        )
        orchestrator._event_index["alert"].append(eid)

    resp = await orchestrator.search_similar(
        SimilarityQueryRequest(
            query="cpu high load", vector=v, top_k=5, threshold=1.0, session_id="s2"
        )
    )
    assert resp.total == 1
    assert resp.results[0].event_id == "e4"


async def test_search_similar_below_threshold(orchestrator: ScenarioMemoryOrchestrator):
    v1 = _text_to_vector("alpha")
    v2 = _text_to_vector("zebra entirely unrelated phrase")
    orchestrator._events["e5"] = EventMemory(
        event_id="e5",
        event_type="metric",
        source="unit",
        payload={},
        vector=v2,
    )
    orchestrator._event_index["metric"].append("e5")

    resp = await orchestrator.search_similar(
        SimilarityQueryRequest(query="alpha", vector=v1, top_k=5, threshold=0.99)
    )
    assert resp.total == 0


async def test_search_similar_generates_query_vector(orchestrator: ScenarioMemoryOrchestrator):
    v = _text_to_vector("cpu load")
    orchestrator._events["e6"] = EventMemory(
        event_id="e6",
        event_type="metric",
        source="unit",
        payload={"text": "cpu load"},
        vector=v,
    )
    orchestrator._event_index["metric"].append("e6")

    resp = await orchestrator.search_similar(
        SimilarityQueryRequest(query="cpu load", vector=None, top_k=5, threshold=0.9)
    )
    assert resp.total == 1


# ------------------------------------------------------------------
# Experience learning, correction, expiration and filtering
# ------------------------------------------------------------------
async def test_learn_experience_new_and_update(orchestrator: ScenarioMemoryOrchestrator):
    r1 = await orchestrator.learn_experience(
        LearnExperienceRequest(situation="s", action="a", outcome="ok", confidence=0.5)
    )
    assert r1.learned
    assert r1.expired is False

    r2 = await orchestrator.learn_experience(
        LearnExperienceRequest(situation="s", action="a", outcome="ok", confidence=0.5)
    )
    assert r2.learned
    assert r2.confidence >= r1.confidence
    assert orchestrator._experiences["s::a"].occurrences == 2


async def test_learn_experience_takes_default_ttl(orchestrator: ScenarioMemoryOrchestrator):
    r = await orchestrator.learn_experience(
        LearnExperienceRequest(
            situation="s", action="a", outcome="ok", confidence=0.5, ttl_seconds=None
        )
    )
    assert r.learned
    assert orchestrator._experiences["s::a"].expires_at is not None

    r2 = await orchestrator.learn_experience(
        LearnExperienceRequest(
            situation="s2", action="a2", outcome="ok", confidence=0.5, ttl_seconds=0
        )
    )
    assert r2.learned
    assert orchestrator._experiences["s2::a2"].expires_at is not None


async def test_learn_experience_invalid_existing_treated_as_new(
    orchestrator: ScenarioMemoryOrchestrator,
):
    key = "s::a"
    orch2 = ScenarioMemoryOrchestrator()
    orch2._experiences[key] = Experience(
        experience_id="x",
        situation="s",
        action="a",
        outcome="bad",
        confidence=0.1,
        occurrences=5,
        valid=False,
    )
    r = await orch2.learn_experience(
        LearnExperienceRequest(situation="s", action="a", outcome="ok", confidence=0.5)
    )
    assert r.learned
    assert orch2._experiences[key].occurrences == 1
    assert orch2._experiences[key].valid is True
    assert orch2._experiences[key].corrected_by is None


async def test_learn_experience_expired_existing_treated_as_new(
    orchestrator: ScenarioMemoryOrchestrator,
):
    key = "s::a"
    orch2 = ScenarioMemoryOrchestrator()
    orch2._experiences[key] = Experience(
        experience_id="x",
        situation="s",
        action="a",
        outcome="bad",
        confidence=0.1,
        occurrences=5,
        expires_at=datetime.utcnow() - timedelta(seconds=10),
    )
    r = await orch2.learn_experience(
        LearnExperienceRequest(situation="s", action="a", outcome="ok", confidence=0.5)
    )
    assert r.learned
    assert r.expired is True
    assert orch2._experiences[key].occurrences == 1


async def test_learn_experience_raises_when_experience_id_is_none():
    orch = ScenarioMemoryOrchestrator()
    key = "s::a"
    orch._experiences[key] = Experience(
        experience_id=None,
        situation="s",
        action="a",
        outcome="bad",
        confidence=0.1,
    )
    with pytest.raises(ValueError, match="experience_id must not be None"):
        await orch.learn_experience(
            LearnExperienceRequest(situation="s", action="a", outcome="ok", confidence=0.5)
        )


async def test_correct_experience_missing_returns_none(orchestrator: ScenarioMemoryOrchestrator):
    assert await orchestrator.correct_experience("s", "a", "user") is None


async def test_correct_experience_without_correction_outcome(
    orchestrator: ScenarioMemoryOrchestrator,
):
    await orchestrator.learn_experience(
        LearnExperienceRequest(situation="s", action="a", outcome="old", confidence=0.5)
    )
    corrected = await orchestrator.correct_experience("s", "a", "user")
    assert corrected is not None
    assert orchestrator._experiences["s::a"].valid is False
    assert orchestrator._experiences["s::a"].corrected_by == "user"


async def test_correct_experience_with_correction_outcome(orchestrator: ScenarioMemoryOrchestrator):
    await orchestrator.learn_experience(
        LearnExperienceRequest(situation="s", action="a", outcome="old", confidence=0.5)
    )
    corrected_id = await orchestrator.correct_experience("s", "a", "user", "new_outcome")
    assert corrected_id is not None
    assert corrected_id != orchestrator._experiences["s::a"].experience_id
    assert any(
        exp.outcome == "new_outcome" and exp.valid and exp.corrected_by is None
        for exp in orchestrator._experiences.values()
    )


async def test_find_experiences_filters_invalid_expired_and_session(
    orchestrator: ScenarioMemoryOrchestrator,
):
    orch = ScenarioMemoryOrchestrator()
    # valid, session s1
    await orch.learn_experience(
        LearnExperienceRequest(
            situation="cpu spike",
            action="restart",
            outcome="ok",
            confidence=0.5,
            session_id="s1",
        )
    )
    # invalid same session
    orch._experiences["cpu spike::restart"].valid = False
    # expired, session s2
    await orch.learn_experience(
        LearnExperienceRequest(
            situation="disk full",
            action="clean",
            outcome="ok",
            confidence=0.5,
            session_id="s2",
        )
    )
    orch._experiences["disk full::clean"].expires_at = datetime.utcnow() - timedelta(seconds=1)
    # valid, session s3
    await orch.learn_experience(
        LearnExperienceRequest(
            situation="disk full",
            action="expand",
            outcome="ok",
            confidence=0.5,
            session_id="s3",
        )
    )

    # Query that matches situation only; invalid should be excluded.
    matches = await orch.find_experiences("cpu", session_id="s1")
    assert matches == []

    # Query that matches two situations; expired filtered.
    matches = await orch.find_experiences("disk", session_id="s2")
    assert matches == []

    # Valid from s3 should appear.
    matches = await orch.find_experiences("disk", session_id="s3")
    assert len(matches) == 1
    assert matches[0].action == "expand"


# ------------------------------------------------------------------
# Knowledge accumulation
# ------------------------------------------------------------------
async def test_accumulate_knowledge_new_and_update(orchestrator: ScenarioMemoryOrchestrator):
    req = AccumulateKnowledgeRequest(
        entries=[
            KnowledgeEntry(subject="host", predicate="has", object="disk", weight=1.0),
            KnowledgeEntry(subject="host", predicate="has", object="disk", weight=1.0),
        ]
    )
    r = await orchestrator.accumulate_knowledge(req)
    assert r.stored == 1
    assert r.updated == 1
    assert len(r.knowledge_ids) == 2
    assert orchestrator._knowledge["host::has::disk"].weight == pytest.approx(1.98, rel=1e-9)


async def test_accumulate_knowledge_keeps_provided_expires_at(
    orchestrator: ScenarioMemoryOrchestrator,
):
    future = datetime.utcnow() + timedelta(days=10)
    req = AccumulateKnowledgeRequest(
        entries=[
            KnowledgeEntry(
                knowledge_id="k1",
                subject="a",
                predicate="b",
                object="c",
                weight=2.0,
                expires_at=future,
            )
        ]
    )
    r = await orchestrator.accumulate_knowledge(req)
    assert r.stored == 1
    assert orchestrator._knowledge["a::b::c"].expires_at == future


async def test_accumulate_knowledge_raises_on_existing_with_none_knowledge_id():
    orch = ScenarioMemoryOrchestrator()
    key = "a::b::c"
    orch._knowledge[key] = KnowledgeEntry(
        knowledge_id=None,
        subject="a",
        predicate="b",
        object="c",
        weight=1.0,
    )
    with pytest.raises(ValueError, match="knowledge_id must not be None"):
        await orch.accumulate_knowledge(
            AccumulateKnowledgeRequest(
                entries=[KnowledgeEntry(subject="a", predicate="b", object="c", weight=1.0)]
            )
        )


# ------------------------------------------------------------------
# Pattern recognition (sequence, frequency, correlation)
# ------------------------------------------------------------------
async def test_recognize_sequence_missing_data(orchestrator: ScenarioMemoryOrchestrator):
    # len < 2 -> false arm of the `and`
    resp = await orchestrator.recognize_pattern(
        PatternRequest(pattern_type="sequence", data=[{"event_type": "a"}])
    )
    assert resp.total == 0


async def test_recognize_sequence_no_repeat(orchestrator: ScenarioMemoryOrchestrator):
    resp = await orchestrator.recognize_pattern(
        PatternRequest(
            pattern_type="sequence",
            data=[
                {"event_type": "a"},
                {"event_type": "b"},
                {"event_type": "c"},
            ],
        )
    )
    assert resp.total == 0


async def test_recognize_sequence_with_repeat(orchestrator: ScenarioMemoryOrchestrator):
    resp = await orchestrator.recognize_pattern(
        PatternRequest(
            pattern_type="sequence",
            data=[
                {"event_type": "a"},
                {"event_type": "b"},
                {"event_type": "a"},
                {"event_type": "b"},
            ],
        )
    )
    assert resp.total >= 1
    assert all(p.pattern_type == "sequence" for p in resp.patterns)


async def test_recognize_frequency_below_threshold(orchestrator: ScenarioMemoryOrchestrator):
    resp = await orchestrator.recognize_pattern(
        PatternRequest(
            pattern_type="frequency",
            data=[{"value": "a"}, {"value": "b"}, {"value": "c"}],
        )
    )
    assert resp.total == 0


async def test_recognize_frequency_above_threshold(orchestrator: ScenarioMemoryOrchestrator):
    resp = await orchestrator.recognize_pattern(
        PatternRequest(
            pattern_type="frequency",
            data=[{"value": "x"}, {"value": "x"}, {"value": "x"}],
        )
    )
    assert resp.total == 1
    assert resp.patterns[0].pattern_type == "frequency"


async def test_recognize_correlation_short_data(orchestrator: ScenarioMemoryOrchestrator):
    resp = await orchestrator.recognize_pattern(
        PatternRequest(
            pattern_type="correlation",
            data=[{"a": 1}],
        )
    )
    assert resp.total == 0


async def test_recognize_correlation_with_repeat(orchestrator: ScenarioMemoryOrchestrator):
    resp = await orchestrator.recognize_pattern(
        PatternRequest(
            pattern_type="correlation",
            data=[
                {"x": 1, "y": 2},
                {"x": 2, "y": 3},
            ],
        )
    )
    assert resp.total == 1
    assert resp.patterns[0].pattern_type == "correlation"


async def test_recognize_unknown_pattern_type(orchestrator: ScenarioMemoryOrchestrator):
    resp = await orchestrator.recognize_pattern(
        PatternRequest(pattern_type="unknown", data=[{"x": 1}])
    )
    assert resp.total == 0


# ------------------------------------------------------------------
# Short-term memory (session namespacing, cache miss, expiration, capacity)
# ------------------------------------------------------------------
async def test_short_term_session_namespacing(orchestrator: ScenarioMemoryOrchestrator):
    await orchestrator.store_short_term(
        ShortTermRequest(key="k", value="v", ttl_seconds=300, session_id="s1")
    )
    assert await orchestrator.retrieve_short_term("k", session_id="s1") == "v"
    assert await orchestrator.retrieve_short_term("k") is None
    assert await orchestrator.retrieve_short_term("k", session_id="s2") is None


async def test_short_term_cache_miss_then_memory_hit(orchestrator: ScenarioMemoryOrchestrator):
    await orchestrator.store_short_term(ShortTermRequest(key="k", value="v", ttl_seconds=300))
    # Simulate cache miss without touching the cache implementation.
    orchestrator.cache._memory.pop("stm:k", None)
    assert await orchestrator.retrieve_short_term("k") == "v"


async def test_short_term_memory_expired(orchestrator: ScenarioMemoryOrchestrator):
    await orchestrator.store_short_term(ShortTermRequest(key="k", value="v", ttl_seconds=300))
    orchestrator.cache._memory.pop("stm:k", None)
    orchestrator._short_term["k"].timestamp = datetime.utcnow() - timedelta(seconds=400)
    assert await orchestrator.retrieve_short_term("k") is None


async def test_short_term_capacity_eviction(
    orchestrator: ScenarioMemoryOrchestrator, small_settings
):
    orchestrator.settings = small_settings
    await orchestrator.store_short_term(ShortTermRequest(key="first", value=1, ttl_seconds=300))
    await orchestrator.store_short_term(ShortTermRequest(key="second", value=2, ttl_seconds=300))
    assert "first" not in orchestrator._short_term
    assert "second" in orchestrator._short_term


# ------------------------------------------------------------------
# Long-term memory (capacity, cache miss)
# ------------------------------------------------------------------
async def test_long_term_session_namespacing(orchestrator: ScenarioMemoryOrchestrator):
    await orchestrator.store_long_term(
        LongTermRequest(key="k", value="v", importance=1.0, session_id="s1")
    )
    assert await orchestrator.retrieve_long_term("k", session_id="s1") == "v"
    assert await orchestrator.retrieve_long_term("k") is None


async def test_long_term_cache_miss_then_memory_hit(orchestrator: ScenarioMemoryOrchestrator):
    await orchestrator.store_long_term(LongTermRequest(key="k", value="v", importance=1.0))
    orchestrator.cache._memory.pop("ltm:k", None)
    assert await orchestrator.retrieve_long_term("k") == "v"


async def test_long_term_capacity_eviction(
    orchestrator: ScenarioMemoryOrchestrator, small_settings
):
    orchestrator.settings = small_settings
    await orchestrator.store_long_term(LongTermRequest(key="low", value=1, importance=0.1))
    await orchestrator.store_long_term(LongTermRequest(key="high", value=2, importance=0.9))
    assert "low" not in orchestrator._long_term
    assert "high" in orchestrator._long_term


# ------------------------------------------------------------------
# Semantic and procedural memory
# ------------------------------------------------------------------
async def test_semantic_store_and_retrieve(orchestrator: ScenarioMemoryOrchestrator):
    await orchestrator.store_semantic(
        SemanticRequest(entity="server", relation="runs", target="app", metadata={"dc": "us"})
    )
    triples = await orchestrator.retrieve_semantic("server")
    assert len(triples) == 1
    assert triples[0].target == "app"
    assert await orchestrator.retrieve_semantic("missing") == []


async def test_procedural_store_and_retrieve(orchestrator: ScenarioMemoryOrchestrator):
    resp = await orchestrator.store_procedural(
        ProceduralRequest(
            name="reboot",
            steps=["ssh", "reboot"],
            preconditions=["alert"],
            expected_outcome="up",
        )
    )
    by_id = await orchestrator.retrieve_procedural(resp.procedure_id)
    by_name = await orchestrator.retrieve_procedural("reboot")
    assert by_id is not None
    assert by_name is not None
    assert await orchestrator.retrieve_procedural("missing") is None
