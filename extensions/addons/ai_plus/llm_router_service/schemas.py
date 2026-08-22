# -*- coding: utf-8 -*-
"""Pydantic schemas for the LLM router microservice."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ProviderType(str, Enum):
    """Supported LLM providers."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OPEN_SOURCE = "open_source"
    LOCAL = "local"


class TaskType(str, Enum):
    """LLM task types."""

    CODE_GENERATION = "code_generation"
    ANALYSIS = "analysis"
    SUMMARIZATION = "summarization"
    QUESTION_ANSWERING = "qa"
    REASONING = "reasoning"
    GENERAL = "general"


class ModelConfig(BaseModel):
    """Model configuration."""

    name: str
    provider: ProviderType = ProviderType.OPENAI
    model_id: str = ""
    cost_per_1k: float = 0.0
    max_tokens: int = 0
    context_window: int = 0
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    capabilities: List[str] = Field(default_factory=list)


class RouteRequest(BaseModel):
    """Routing request."""

    prompt: str
    task_type: TaskType = TaskType.GENERAL
    force_model: Optional[str] = None
    context: Dict[str, Any] = Field(default_factory=dict)
    budget: Optional[float] = None
    strategy: str = "cost_optimized"
    max_tokens: int = 1024
    temperature: float = 0.7
    use_cache: bool = True


class RouteResponse(BaseModel):
    """Routing decision."""

    model_name: str
    provider: ProviderType
    estimated_cost: float
    estimated_tokens: int
    confidence: float
    reason: str
    latency_ms: Optional[float] = None


class GenerateRequest(BaseModel):
    """Generation request."""

    prompt: str
    model: Optional[str] = None
    task_type: TaskType = TaskType.GENERAL
    max_tokens: int = 1024
    temperature: float = 0.7
    budget: Optional[float] = None
    strategy: str = "cost_optimized"


class GenerateResponse(BaseModel):
    """Generation response."""

    content: str
    model: str
    provider: ProviderType
    tokens: int
    latency_ms: float
    cost: float


class ModelStatsSchema(BaseModel):
    """Model statistics."""

    model_name: str
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    avg_latency: float = 0.0
    last_error: Optional[str] = None


class CircuitStateSchema(BaseModel):
    """Circuit breaker state."""

    model_name: str
    state: str


class CostReport(BaseModel):
    """Cost report."""

    hourly_cost: float
    request_count: int
    avg_cost_per_request: float
    budget_per_request: Optional[float] = None
    max_cost_per_hour: Optional[float] = None


class PerformanceReport(BaseModel):
    """Performance report."""

    model_stats: List[ModelStatsSchema]
    circuit_states: List[CircuitStateSchema]
    cost_report: CostReport
    total_requests: int


class ServiceHealth(BaseModel):
    """Service health response."""

    status: str
    service: str
    uptime_seconds: int = 0
    model_count: int = 0


class LiteLLMRequest(BaseModel):
    """LiteLLM-compatible chat completion request."""

    model: str = "auto"
    messages: List[Dict[str, Any]] = Field(default_factory=list)
    max_tokens: int = 1024
    temperature: float = 0.7
    budget: Optional[float] = None
    strategy: str = "cost_optimized"


class LiteLLMChoice(BaseModel):
    """LiteLLM-compatible completion choice."""

    index: int = 0
    message: Dict[str, Any] = Field(default_factory=dict)
    finish_reason: str = "stop"


class LiteLLMUsage(BaseModel):
    """LiteLLM-compatible token usage."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class LiteLLMResponse(BaseModel):
    """LiteLLM-compatible chat completion response."""

    id: str = ""
    object: str = "chat.completion"
    created: int = Field(default_factory=lambda: int(datetime.utcnow().timestamp()))
    model: str = ""
    choices: List[LiteLLMChoice] = Field(default_factory=list)
    usage: LiteLLMUsage = Field(default_factory=LiteLLMUsage)
