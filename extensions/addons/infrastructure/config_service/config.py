# -*- coding: utf-8 -*-
"""Configuration microservice configuration."""

from __future__ import annotations

try:
    from pydantic_settings import BaseSettings
except ImportError:  # pragma: no cover
    from pydantic import BaseModel as BaseSettings  # type: ignore[misc, assignment]


class ConfigServiceSettings(BaseSettings):
    """Settings for the configuration microservice."""

    service_name: str = "config-service"
    environment: str = "development"
    log_level: str = "INFO"
    orchestrator_port: int = 9501

    redis_url: str = "redis://localhost:6379/6"
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/aiops"  # noqa: E501
    use_in_memory: bool = True

    enable_prometheus: bool = True
    encryption_key: str = "00000000000000000000000000000000"  # noqa: S105

    class Config:  # type: ignore[misc]
        env_prefix = "CONFIG_SERVICE_"
        env_file = ".env"
        extra = "ignore"


settings = ConfigServiceSettings()
