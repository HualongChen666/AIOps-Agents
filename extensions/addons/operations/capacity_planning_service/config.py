# -*- coding: utf-8 -*-
"""Configuration for the Capacity Planning microservice."""

from __future__ import annotations

try:
    from pydantic_settings import BaseSettings
except ImportError:  # pragma: no cover
    from pydantic import BaseModel as BaseSettings  # type: ignore[misc, assignment]


class CapacityPlanningServiceSettings(BaseSettings):
    """Settings for the Capacity Planning microservice."""

    service_name: str = "capacity-planning-service"
    environment: str = "development"
    log_level: str = "INFO"
    port: int = 9548
    redis_url: str = ""
    database_url: str = ""
    qdrant_url: str = ""
    enable_prometheus: bool = True
    max_retries: int = 3
    cache_ttl_seconds: int = 300
    request_timeout: float = 60.0

    class Config:  # type: ignore[misc]
        env_prefix = "CAPACITY_PLANNING_SERVICE_"
        env_file = ".env"
        extra = "ignore"


settings = CapacityPlanningServiceSettings()
