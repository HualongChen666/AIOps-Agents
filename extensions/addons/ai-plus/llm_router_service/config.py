# -*- coding: utf-8 -*-
"""LLM Router microservice configuration."""

from __future__ import annotations

from typing import Optional

try:
    from pydantic_settings import BaseSettings
except ImportError:  # pragma: no cover
    from pydantic import BaseModel as BaseSettings  # type: ignore[misc, assignment]


class LLMRouterSettings(BaseSettings):
    """Settings for the LLM router microservice."""

    service_name: str = "llm-router-service"
    environment: str = "development"
    log_level: str = "INFO"
    port: int = 9405
    redis_url: str = ""
    enable_prometheus: bool = True
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    default_strategy: str = "cost_optimized"
    budget_per_request: Optional[float] = None
    max_cost_per_hour: Optional[float] = None
    retry_policy: str = "exponential"
    max_retries: int = 3
    request_timeout: float = 60.0

    class Config:  # type: ignore[misc]
        env_prefix = "LLM_ROUTER_SERVICE_"
        env_file = ".env"
        extra = "ignore"


settings = LLMRouterSettings()
