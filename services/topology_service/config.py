# -*- coding: utf-8 -*-
"""Topology microservice configuration."""

from __future__ import annotations

try:
    from pydantic_settings import BaseSettings
except ImportError:  # pragma: no cover - fallback for minimal installs
    from pydantic import BaseModel as BaseSettings  # type: ignore[misc, assignment]


class TopologyServiceSettings(BaseSettings):
    """Settings for the topology microservice."""

    service_name: str = "topology-service"
    environment: str = "development"
    log_level: str = "INFO"

    # Service ports
    orchestrator_port: int = 9101
    analyzer_port: int = 9102
    visualizer_port: int = 9103

    # Infrastructure
    redis_url: str = "redis://localhost:6379/2"
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/aiops"  # noqa: E501
    use_in_memory: bool = True

    # Prometheus
    enable_prometheus: bool = True

    # Performance tuning
    default_discovery_timeout: int = 30
    max_concurrent_discoveries: int = 100
    graph_cache_ttl_seconds: int = 60

    class Config:  # type: ignore[misc]
        env_prefix = "TOPOLOGY_SERVICE_"
        env_file = ".env"
        extra = "ignore"


settings = TopologyServiceSettings()
