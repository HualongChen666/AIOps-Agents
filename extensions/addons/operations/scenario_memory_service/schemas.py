# -*- coding: utf-8 -*-
"""Pydantic schemas for the Scenario Memory microservice."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class MemoryType(str, Enum):
    """Supported memory types."""

    EVENT = "event"
    SHORT_TERM = "short_term"
    LONG_TERM = "long_term"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    service: str
    environment: str


class StatsResponse(BaseModel):
    """Service statistics response."""

    service: str
    request_counts: Dict[str, int]
    memory_entries: Dict[str, int]
    cache_size: int
    retry_policies: List[str]


class EventMemory(BaseModel):
    """An event memory entry."""

    event_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    event_type: str = "generic"
    source: str = ""
    payload: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)
    vector: Optional[List[float]] = None
    session_id: Optional[str] = None


class StoreEventRequest(BaseModel):
    """Request to store an event memory."""

    event: EventMemory


class StoreEventResponse(BaseModel):
    """Response from storing an event memory."""

    event_id: str
    stored: bool
    indexed: bool
    cached: bool


class SimilarityQueryRequest(BaseModel):
    """Request to search similar events."""

    query: str
    vector: Optional[List[float]] = None
    top_k: int = 5
    threshold: float = 0.7
    session_id: Optional[str] = None


class SimilarEvent(BaseModel):
    """A similar event result."""

    event_id: str
    score: float
    event: EventMemory


class SimilarityQueryResponse(BaseModel):
    """Response from similar event search."""

    query: str
    results: List[SimilarEvent]
    total: int


class Experience(BaseModel):
    """A learned experience entry."""

    experience_id: Optional[str] = None
    situation: str = ""
    action: str = ""
    outcome: str = ""
    confidence: float = 0.0
    occurrences: int = 1
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    valid: bool = True
    corrected_by: Optional[str] = None
    session_id: Optional[str] = None


class LearnExperienceRequest(BaseModel):
    """Request to learn from an experience."""

    situation: str
    action: str
    outcome: str
    confidence: float = 1.0
    ttl_seconds: Optional[int] = None
    session_id: Optional[str] = None


class LearnExperienceResponse(BaseModel):
    """Response from experience learning."""

    experience_id: str
    learned: bool
    confidence: float
    expired: bool = False


class KnowledgeEntry(BaseModel):
    """A knowledge accumulation entry."""

    knowledge_id: Optional[str] = None
    subject: str = ""
    predicate: str = ""
    object: str = ""
    weight: float = 1.0
    source: str = ""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    valid: bool = True


class AccumulateKnowledgeRequest(BaseModel):
    """Request to accumulate knowledge."""

    entries: List[KnowledgeEntry]


class AccumulateKnowledgeResponse(BaseModel):
    """Response from knowledge accumulation."""

    stored: int
    updated: int
    knowledge_ids: List[str]


class PatternRequest(BaseModel):
    """Request to recognize a pattern."""

    data: List[Dict[str, Any]]
    pattern_type: str = "sequence"


class PatternResult(BaseModel):
    """A recognized pattern."""

    pattern_id: str
    pattern_type: str
    confidence: float
    description: str
    supporting_ids: List[str]


class PatternResponse(BaseModel):
    """Response from pattern recognition."""

    patterns: List[PatternResult]
    total: int


class ShortTermMemory(BaseModel):
    """Short-term working memory entry."""

    key: str
    value: Any
    ttl_seconds: int = 300
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    session_id: Optional[str] = None


class ShortTermRequest(BaseModel):
    """Request to store short-term memory."""

    key: str
    value: Any
    ttl_seconds: int = 300
    session_id: Optional[str] = None


class ShortTermResponse(BaseModel):
    """Response for short-term memory."""

    key: str
    stored: bool


class LongTermMemory(BaseModel):
    """Long-term historical memory entry."""

    key: str
    value: Any
    importance: float = 1.0
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    session_id: Optional[str] = None


class LongTermRequest(BaseModel):
    """Request to store long-term memory."""

    key: str
    value: Any
    importance: float = 1.0
    session_id: Optional[str] = None


class LongTermResponse(BaseModel):
    """Response for long-term memory."""

    key: str
    stored: bool


class SemanticMemory(BaseModel):
    """Semantic memory entry (knowledge graph node)."""

    entity: str
    relation: str
    target: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SemanticRequest(BaseModel):
    """Request to store semantic memory."""

    entity: str
    relation: str
    target: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SemanticResponse(BaseModel):
    """Response for semantic memory."""

    stored: bool
    triple_id: str


class ProceduralMemory(BaseModel):
    """Procedural memory entry (operation flow)."""

    procedure_id: Optional[str] = None
    name: str = ""
    steps: List[str] = Field(default_factory=list)
    preconditions: List[str] = Field(default_factory=list)
    expected_outcome: str = ""


class ProceduralRequest(BaseModel):
    """Request to store procedural memory."""

    name: str
    steps: List[str]
    preconditions: List[str] = Field(default_factory=list)
    expected_outcome: str = ""


class ProceduralResponse(BaseModel):
    """Response for procedural memory."""

    procedure_id: str
    stored: bool
