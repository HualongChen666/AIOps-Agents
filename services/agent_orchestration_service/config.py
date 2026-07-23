# -*- coding: utf-8 -*-
"""Pydantic settings for the Agent Orchestration microservice."""

from __future__ import annotations

from pydantic_settings import BaseSettings


class AgentOrchestrationSettings(BaseSettings):
    """Settings for the agent orchestration microservice."""

    service_name: str = "agent-orchestration-service"
    environment: str = "development"
    log_level: str = "INFO"
    port: int = 9407
    redis_url: str = ""
    enable_prometheus: bool = True
    openai_api_key: str = ""
    default_agent: str = "generic"
    max_agents_per_plan: int = 10
    collaboration_timeout_seconds: float = 120.0
    retry_policy: str = "exponential"
    max_retries: int = 3
    request_timeout: float = 60.0

    class Config:  # type: ignore[misc]
        env_prefix = "AGENT_ORCHESTRATION_"


settings = AgentOrchestrationSettings()
