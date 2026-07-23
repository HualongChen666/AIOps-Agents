# -*- coding: utf-8 -*-
"""Pydantic schemas for the Agent Orchestration microservice."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AgentType(str, Enum):
    """Supported agent types."""

    GENERIC = "generic"
    MONITOR = "monitor"
    DIAGNOSTIC = "diagnostic"
    REPAIR = "repair"
    ANALYSIS = "analysis"


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    service: str


class SubTask(BaseModel):
    """A decomposed subtask."""

    task_id: str
    description: str
    agent_type: AgentType = AgentType.GENERIC
    input_data: Dict[str, Any] = Field(default_factory=dict)
    dependencies: List[str] = Field(default_factory=list)


class DecomposeRequest(BaseModel):
    """Request to decompose a task."""

    task: str
    max_subtasks: int = 5
    context: Dict[str, Any] = Field(default_factory=dict)


class DecomposeResponse(BaseModel):
    """Response from task decomposition."""

    task: str
    subtasks: List[SubTask]
    plan_id: str


class AgentRequest(BaseModel):
    """Request to run a single agent."""

    agent_type: AgentType
    input_data: Dict[str, Any] = Field(default_factory=dict)
    context: Dict[str, Any] = Field(default_factory=dict)
    max_tokens: int = 512
    temperature: float = 0.2


class AgentResult(BaseModel):
    """Result produced by a single agent."""

    agent_type: str
    task_id: Optional[str] = None
    output: str
    confidence: float = 0.0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AgentResponse(BaseModel):
    """Response from running an agent."""

    agent_type: str
    result: AgentResult
    latency_ms: float = 0.0


class CoordinateRequest(BaseModel):
    """Request to coordinate a plan of subtasks."""

    plan_id: Optional[str] = None
    subtasks: List[SubTask]
    run_parallel: bool = False
    context: Dict[str, Any] = Field(default_factory=dict)


class CoordinateResponse(BaseModel):
    """Response from execution coordination."""

    plan_id: str
    results: List[AgentResult]
    completed: List[str]
    failed: List[str]
    latency_ms: float = 0.0


class CollaborateRequest(BaseModel):
    """Request for multi-agent collaboration."""

    task: str
    agent_types: List[AgentType] = Field(default_factory=list)
    context: Dict[str, Any] = Field(default_factory=dict)
    run_parallel: bool = False
    aggregate_strategy: str = "concat"


class CollaborateResponse(BaseModel):
    """Response from multi-agent collaboration."""

    task: str
    results: List[AgentResult]
    aggregated_output: str
    plan_id: str
    latency_ms: float = 0.0


class AggregateRequest(BaseModel):
    """Request to aggregate a list of agent results."""

    results: List[AgentResult]
    strategy: str = "concat"
    prompt: Optional[str] = None


class AggregateResponse(BaseModel):
    """Response from result aggregation."""

    aggregated_output: str
    result_count: int
    strategy: str


class ErrorHandleRequest(BaseModel):
    """Request to handle an error."""

    error: str
    context: Dict[str, Any] = Field(default_factory=dict)
    operation: str = "unknown"


class ErrorHandleResponse(BaseModel):
    """Response from error handling."""

    recovered: bool
    strategy: str
    next_steps: List[str]
    message: str


class StatsResponse(BaseModel):
    """Service statistics response."""

    service: str
    request_counts: Dict[str, int]
    retry_policies: List[str]
    cache_size: int
