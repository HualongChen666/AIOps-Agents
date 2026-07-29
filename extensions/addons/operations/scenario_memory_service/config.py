# -*- coding: utf-8 -*-
"""Pydantic settings for the Scenario Memory microservice."""

from __future__ import annotations

from pydantic_settings import BaseSettings


class ScenarioMemorySettings(BaseSettings):
    """Settings for the scenario memory microservice."""

    service_name: str = "scenario-memory-service"
    environment: str = "development"
    log_level: str = "INFO"
    port: int = 9408
    redis_url: str = ""
    enable_prometheus: bool = True
    embedding_dimension: int = 128
    max_similar_results: int = 10
    default_cache_ttl: int = 300
    max_memory_entries: int = 10000
    similarity_threshold: float = 0.75
    knowledge_decay_rate: float = 0.01
    experience_decay_rate: float = 0.005
    short_term_capacity: int = 1000
    long_term_capacity: int = 10000
    pattern_threshold: float = 0.8
    batch_size: int = 100
    request_timeout: float = 60.0

    class Config:  # type: ignore[misc]
        env_prefix = "SCENARIO_MEMORY_"


settings = ScenarioMemorySettings()
