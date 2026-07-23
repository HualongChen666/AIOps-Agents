# -*- coding: utf-8 -*-
"""Scenario Memory orchestrator for the microservice."""

from __future__ import annotations

import hashlib
import json
import math
import uuid
from collections import Counter, defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

from . import metrics
from .cache import CacheManager
from .config import settings
from .retry import ScenarioRetryEngine
from .schemas import (
    AccumulateKnowledgeRequest,
    AccumulateKnowledgeResponse,
    EventMemory,
    Experience,
    KnowledgeEntry,
    LearnExperienceRequest,
    LearnExperienceResponse,
    LongTermMemory,
    LongTermRequest,
    LongTermResponse,
    MemoryType,
    PatternRequest,
    PatternResponse,
    PatternResult,
    ProceduralMemory,
    ProceduralRequest,
    ProceduralResponse,
    SemanticMemory,
    SemanticRequest,
    SemanticResponse,
    ShortTermMemory,
    ShortTermRequest,
    ShortTermResponse,
    SimilarEvent,
    SimilarityQueryRequest,
    SimilarityQueryResponse,
    StatsResponse,
    StoreEventRequest,
    StoreEventResponse,
)


def _text_to_vector(text: str, dimension: int = 128) -> List[float]:
    """Generate a deterministic normalized vector from text."""
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    floats = []
    for i in range(dimension):
        chunk = digest[(i * 4) % len(digest) : ((i * 4) % len(digest)) + 4]
        if len(chunk) < 4:
            chunk += digest[: 4 - len(chunk)]
        value = int.from_bytes(chunk, "big") / (2**32 - 1)
        floats.append(value)
    norm = math.sqrt(sum(v * v for v in floats)) or 1.0
    return [v / norm for v in floats]


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    """Compute cosine similarity between two vectors."""
    min_len = min(len(a), len(b))
    a = a[:min_len]
    b = b[:min_len]
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a)) or 1.0
    norm_b = math.sqrt(sum(x * x for x in b)) or 1.0
    return dot / (norm_a * norm_b)


class ScenarioMemoryOrchestrator:
    """Orchestrator implementing task 34 (scenario memory service)."""

    def __init__(
        self,
        cache: Optional[CacheManager] = None,
        retry_engine: Optional[ScenarioRetryEngine] = None,
    ) -> None:
        self.settings = settings
        self.cache = cache or CacheManager(settings.redis_url)
        self.retry_engine = retry_engine or ScenarioRetryEngine()
        self._request_counts: Dict[str, int] = {}

        self._events: Dict[str, EventMemory] = {}
        self._event_index: Dict[str, List[str]] = defaultdict(list)

        self._experiences: Dict[str, Experience] = {}

        self._knowledge: Dict[str, KnowledgeEntry] = {}

        self._patterns: List[PatternResult] = []

        self._short_term: Dict[str, ShortTermMemory] = {}
        self._long_term: Dict[str, LongTermMemory] = {}
        self._semantic: Dict[str, List[SemanticMemory]] = defaultdict(list)
        self._procedural: Dict[str, ProceduralMemory] = {}

    def _new_id(self) -> str:
        return str(uuid.uuid4())

    def _increment_count(self, operation: str) -> None:
        self._request_counts[operation] = self._request_counts.get(operation, 0) + 1
        metrics.request_counter.labels(operation=operation).inc()

    def list_methods(self) -> List[str]:
        return [
            "store_event",
            "search_similar",
            "learn_experience",
            "accumulate_knowledge",
            "recognize_pattern",
            "store_short_term",
            "retrieve_short_term",
            "store_long_term",
            "retrieve_long_term",
            "store_semantic",
            "retrieve_semantic",
            "store_procedural",
            "retrieve_procedural",
            "get_stats",
        ]

    async def get_stats(self) -> StatsResponse:
        return StatsResponse(
            service=self.settings.service_name,
            request_counts=self._request_counts.copy(),
            memory_entries={
                "event": len(self._events),
                "short_term": len(self._short_term),
                "long_term": len(self._long_term),
                "semantic": sum(len(v) for v in self._semantic.values()),
                "procedural": len(self._procedural),
                "experience": len(self._experiences),
                "knowledge": len(self._knowledge),
                "pattern": len(self._patterns),
            },
            cache_size=len(self.cache._memory),
            retry_policies=self.retry_engine.list_policies(),
        )

    # ------------------------------------------------------------------
    # 34.2 Event memory storage
    # ------------------------------------------------------------------
    async def store_event(self, request: StoreEventRequest) -> StoreEventResponse:
        self._increment_count("store_event")
        event = request.event
        if not event.event_id:
            event.event_id = self._new_id()
        if not event.vector:
            event.vector = _text_to_vector(
                f"{event.event_type} {event.source} {json.dumps(event.payload, sort_keys=True)}",
                self.settings.embedding_dimension,
            )

        self._events[event.event_id] = event
        for tag in event.tags:
            self._event_index[tag].append(event.event_id)
        self._event_index[event.event_type].append(event.event_id)

        await self.cache.set(
            f"event:{event.event_id}", event.model_dump(), ttl=self.settings.default_cache_ttl
        )
        metrics.memory_size_gauge.labels(memory_type=MemoryType.EVENT.value).inc()
        logger.info(f"Stored event {event.event_id}")
        return StoreEventResponse(event_id=event.event_id, stored=True, indexed=True, cached=True)

    # ------------------------------------------------------------------
    # 34.3 Similar event retrieval
    # ------------------------------------------------------------------
    async def search_similar(self, request: SimilarityQueryRequest) -> SimilarityQueryResponse:
        self._increment_count("search_similar")
        query_vector = request.vector
        if not query_vector:
            query_vector = _text_to_vector(request.query, self.settings.embedding_dimension)

        top_k = min(request.top_k, self.settings.max_similar_results)
        threshold = request.threshold or self.settings.similarity_threshold

        scored: List[Tuple[float, str]] = []
        for event_id, event in self._events.items():
            if event.vector:
                score = _cosine_similarity(query_vector, event.vector)
                if score >= threshold:
                    scored.append((score, event_id))

        scored.sort(reverse=True)
        top = scored[:top_k]
        results = [
            SimilarEvent(
                event_id=event_id,
                score=score,
                event=self._events[event_id],
            )
            for score, event_id in top
        ]
        return SimilarityQueryResponse(query=request.query, results=results, total=len(results))

    # ------------------------------------------------------------------
    # 34.4 Experience learning
    # ------------------------------------------------------------------
    async def learn_experience(self, request: LearnExperienceRequest) -> LearnExperienceResponse:
        self._increment_count("learn_experience")
        key = f"{request.situation.strip()}::{request.action.strip()}"
        existing = self._experiences.get(key)
        if existing:
            existing.occurrences += 1
            existing.outcome = request.outcome
            existing.last_updated = datetime.utcnow()
            existing.confidence = min(
                1.0,
                request.confidence
                + (1.0 - existing.confidence) * (1.0 - self.settings.experience_decay_rate),
            )
        else:
            experience_id = self._new_id()
            existing = Experience(
                experience_id=experience_id,
                situation=request.situation,
                action=request.action,
                outcome=request.outcome,
                confidence=request.confidence,
                occurrences=1,
            )
            self._experiences[key] = existing
        if existing.experience_id is None:
            raise ValueError("experience_id must not be None")
        return LearnExperienceResponse(
            experience_id=existing.experience_id,
            learned=True,
            confidence=existing.confidence,
        )

    # ------------------------------------------------------------------
    # 34.5 Knowledge accumulation
    # ------------------------------------------------------------------
    async def accumulate_knowledge(
        self, request: AccumulateKnowledgeRequest
    ) -> AccumulateKnowledgeResponse:
        self._increment_count("accumulate_knowledge")
        stored = 0
        updated = 0
        knowledge_ids: List[str] = []

        for entry in request.entries:
            if not entry.knowledge_id:
                entry.knowledge_id = self._new_id()
            if entry.knowledge_id is None:
                raise ValueError("knowledge_id must not be None")
            key = f"{entry.subject.strip()}::{entry.predicate.strip()}::{entry.object.strip()}"
            existing = self._knowledge.get(key)
            if existing:
                existing.weight += entry.weight
                existing.weight *= 1.0 - self.settings.knowledge_decay_rate
                updated += 1
                existing_kid = existing.knowledge_id
                if existing_kid is None:
                    raise ValueError("knowledge_id must not be None")
                knowledge_ids.append(existing_kid)
            else:
                self._knowledge[key] = entry
                stored += 1
                knowledge_ids.append(entry.knowledge_id)
        return AccumulateKnowledgeResponse(
            stored=stored, updated=updated, knowledge_ids=knowledge_ids
        )

    # ------------------------------------------------------------------
    # 34.6 Pattern recognition
    # ------------------------------------------------------------------
    async def recognize_pattern(self, request: PatternRequest) -> PatternResponse:
        self._increment_count("recognize_pattern")
        patterns: List[PatternResult] = []
        pattern_type = request.pattern_type

        if pattern_type == "sequence" and len(request.data) >= 2:
            sequence = [str(d.get("event_type", "")) for d in request.data]
            freq: Dict[Tuple[str, str], int] = defaultdict(int)
            for i in range(len(sequence) - 1):
                freq[(sequence[i], sequence[i + 1])] += 1

            for (a, b), count in freq.items():
                if count >= 2:
                    patterns.append(
                        PatternResult(
                            pattern_id=self._new_id(),
                            pattern_type="sequence",
                            confidence=min(1.0, count / len(request.data) + 0.5),
                            description=f"Sequence pattern: {a} -> {b}",
                            supporting_ids=[str(i) for i in range(len(request.data))],
                        )
                    )

        if pattern_type == "frequency":
            counter = Counter(str(d.get("value", "")) for d in request.data)
            total = max(1, len(request.data))
            for value, count in counter.most_common(3):
                confidence = count / total
                if confidence >= self.settings.pattern_threshold:
                    patterns.append(
                        PatternResult(
                            pattern_id=self._new_id(),
                            pattern_type="frequency",
                            confidence=confidence,
                            description=f"Frequent value: {value}",
                            supporting_ids=[
                                str(i)
                                for i, d in enumerate(request.data)
                                if str(d.get("value", "")) == value
                            ],
                        )
                    )

        if pattern_type == "correlation" and len(request.data) >= 2:
            pairs: Dict[Tuple[str, str], int] = defaultdict(int)
            for d in request.data:
                keys = sorted(str(k) for k in d.keys())
                for i in range(len(keys)):
                    for j in range(i + 1, len(keys)):
                        pairs[(keys[i], keys[j])] += 1
            for (k1, k2), count in pairs.items():
                if count >= 2:
                    patterns.append(
                        PatternResult(
                            pattern_id=self._new_id(),
                            pattern_type="correlation",
                            confidence=min(1.0, count / len(request.data)),
                            description=f"Correlation: {k1} with {k2}",
                            supporting_ids=[str(i) for i in range(len(request.data))],
                        )
                    )

        self._patterns.extend(patterns)
        return PatternResponse(patterns=patterns, total=len(patterns))

    # ------------------------------------------------------------------
    # 34.7 Short-term memory
    # ------------------------------------------------------------------
    async def store_short_term(self, request: ShortTermRequest) -> ShortTermResponse:
        self._increment_count("store_short_term")
        if len(self._short_term) >= self.settings.short_term_capacity:
            oldest = min(self._short_term.items(), key=lambda x: x[1].timestamp)
            del self._short_term[oldest[0]]
        self._short_term[request.key] = ShortTermMemory(
            key=request.key,
            value=request.value,
            ttl_seconds=request.ttl_seconds,
        )
        await self.cache.set(f"stm:{request.key}", request.value, ttl=request.ttl_seconds)
        metrics.memory_size_gauge.labels(memory_type=MemoryType.SHORT_TERM.value).inc()
        return ShortTermResponse(key=request.key, stored=True)

    async def retrieve_short_term(self, key: str) -> Optional[Any]:
        self._increment_count("retrieve_short_term")
        cached = await self.cache.get(f"stm:{key}")
        if cached is not None:
            return cached
        entry = self._short_term.get(key)
        if entry:
            age = (datetime.utcnow() - entry.timestamp).total_seconds()
            if age < entry.ttl_seconds:
                return entry.value
            self._short_term.pop(key, None)
        return None

    # ------------------------------------------------------------------
    # 34.8 Long-term memory
    # ------------------------------------------------------------------
    async def store_long_term(self, request: LongTermRequest) -> LongTermResponse:
        self._increment_count("store_long_term")
        if len(self._long_term) >= self.settings.long_term_capacity:
            sorted_items = sorted(self._long_term.items(), key=lambda x: x[1].importance)
            del self._long_term[sorted_items[0][0]]
        self._long_term[request.key] = LongTermMemory(
            key=request.key,
            value=request.value,
            importance=request.importance,
        )
        await self.cache.set(
            f"ltm:{request.key}", request.value, ttl=self.settings.default_cache_ttl * 10
        )
        metrics.memory_size_gauge.labels(memory_type=MemoryType.LONG_TERM.value).inc()
        return LongTermResponse(key=request.key, stored=True)

    async def retrieve_long_term(self, key: str) -> Optional[Any]:
        self._increment_count("retrieve_long_term")
        cached = await self.cache.get(f"ltm:{key}")
        if cached is not None:
            return cached
        entry = self._long_term.get(key)
        if entry:
            entry.timestamp = datetime.utcnow()
            return entry.value
        return None

    # ------------------------------------------------------------------
    # 34.9 Semantic memory (knowledge graph)
    # ------------------------------------------------------------------
    async def store_semantic(self, request: SemanticRequest) -> SemanticResponse:
        self._increment_count("store_semantic")
        triple = SemanticMemory(
            entity=request.entity,
            relation=request.relation,
            target=request.target,
            metadata=request.metadata,
        )
        triple_id = f"{request.entity}::{request.relation}::{request.target}"
        self._semantic[request.entity].append(triple)
        await self.cache.set(
            f"semantic:{triple_id}", triple.model_dump(), ttl=self.settings.default_cache_ttl * 5
        )
        metrics.memory_size_gauge.labels(memory_type=MemoryType.SEMANTIC.value).inc()
        return SemanticResponse(stored=True, triple_id=triple_id)

    async def retrieve_semantic(self, entity: str) -> List[SemanticMemory]:
        self._increment_count("retrieve_semantic")
        return self._semantic.get(entity, [])

    # ------------------------------------------------------------------
    # 34.10 Procedural memory
    # ------------------------------------------------------------------
    async def store_procedural(self, request: ProceduralRequest) -> ProceduralResponse:
        self._increment_count("store_procedural")
        procedure_id = self._new_id()
        proc = ProceduralMemory(
            procedure_id=procedure_id,
            name=request.name,
            steps=request.steps,
            preconditions=request.preconditions,
            expected_outcome=request.expected_outcome,
        )
        self._procedural[procedure_id] = proc
        self._procedural[request.name] = proc
        await self.cache.set(
            f"procedural:{procedure_id}",
            proc.model_dump(),
            ttl=self.settings.default_cache_ttl * 10,
        )
        metrics.memory_size_gauge.labels(memory_type=MemoryType.PROCEDURAL.value).inc()
        return ProceduralResponse(procedure_id=procedure_id, stored=True)

    async def retrieve_procedural(self, key: str) -> Optional[ProceduralMemory]:
        self._increment_count("retrieve_procedural")
        return self._procedural.get(key)
