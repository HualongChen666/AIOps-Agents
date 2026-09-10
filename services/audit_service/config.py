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
    database_url: str = "postgresql+asyncpg://postgres@localhost:5432/aiops"  # noqa: E501 - no embedded password
    use_in_memory: bool = False

    enable_prometheus: bool = True
    default_execution_timeout: int = 120
    max_concurrent_events: int = 10000

    # Must be provided via AUDIT_SERVICE_ENCRYPTION_KEY; never ship a default key.
    encryption_key: str = ""  # noqa: S105

    class Config:  # type: ignore[misc]
        env_prefix = "AUDIT_SERVICE_"
        env_file = ".env"
        extra = "ignore"


settings = AuditServiceSettings()

if settings.environment.strip().lower() == "production" and not settings.encryption_key.strip():
    raise RuntimeError(
        "AUDIT_SERVICE_ENCRYPTION_KEY must be set in production environment. "
        "Audit data must not be encrypted with an implicit/empty key."
    )
