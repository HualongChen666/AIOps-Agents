# -*- coding: utf-8 -*-
"""Configuration for the Prometheus Integration microservice."""

from __future__ import annotations

try:
    from pydantic_settings import BaseSettings
except ImportError:  # pragma: no cover
    from pydantic import BaseModel as BaseSettings  # type: ignore[misc, assignment]


class PrometheusIntegrationServiceSettings(BaseSettings):
    """Settings for the Prometheus Integration microservice."""

    service_name: str = "prometheus-integration-service"
    environment: str = "development"
    log_level: str = "INFO"
    port: int = 9530
    redis_url: str = ""
    database_url: str = ""
    qdrant_url: str = ""
    enable_prometheus: bool = True
    max_retries: int = 3
    cache_ttl_seconds: int = 300
    request_timeout: float = 60.0
    enable_distributed_lock: bool = True
    lock_ttl_seconds: int = 30
    idempotency_ttl_seconds: int = 3600

    class Config:  # type: ignore[misc]
        env_prefix = "PROMETHEUS_INTEGRATION_SERVICE_"
        env_file = ".env"
        extra = "ignore"


settings = PrometheusIntegrationServiceSettings()
