# -*- coding: utf-8 -*-
"""Audit microservice configuration."""

from __future__ import annotations

try:
    from pydantic_settings import BaseSettings
except ImportError:  # pragma: no cover
    from pydantic import BaseModel as BaseSettings  # type: ignore[misc, assignment]


class AuditServiceSettings(BaseSettings):
    """Settings for the audit microservice."""

    service_name: str = "audit-service"
    environment: str = "development"
    log_level: str = "INFO"
    orchestrator_port: int = 9301
    analyzer_port: int = 9302
    reporter_port: int = 9303

    redis_url: str = "redis://localhost:6379/4"
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/aiops"  # noqa: E501
    use_in_memory: bool = True

    enable_prometheus: bool = True
    default_execution_timeout: int = 120
    max_concurrent_events: int = 10000

    encryption_key: str = "00000000000000000000000000000000"  # noqa: S105 - dev only

    class Config:  # type: ignore[misc]
        env_prefix = "AUDIT_SERVICE_"
        env_file = ".env"
        extra = "ignore"


settings = AuditServiceSettings()
