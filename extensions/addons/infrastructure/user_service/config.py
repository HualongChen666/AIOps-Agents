# -*- coding: utf-8 -*-
"""User microservice configuration."""

from __future__ import annotations

try:
    from pydantic_settings import BaseSettings
except ImportError:  # pragma: no cover
    from pydantic import BaseModel as BaseSettings  # type: ignore[misc, assignment]


class UserServiceSettings(BaseSettings):
    """Settings for the user microservice."""

    service_name: str = "user-service"
    environment: str = "development"
    log_level: str = "INFO"
    orchestrator_port: int = 9401

    redis_url: str = "redis://localhost:6379/5"
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/aiops"  # noqa: E501
    use_in_memory: bool = True

    enable_prometheus: bool = True
    jwt_secret: str = "dev-jwt-secret-do-not-use-in-production"  # noqa: S105
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    oauth_client_id: str = "aiops-user-service"
    oauth_client_secret: str = "dev-oauth-secret"  # noqa: S105

    class Config:  # type: ignore[misc]
        env_prefix = "USER_SERVICE_"
        env_file = ".env"
        extra = "ignore"


settings = UserServiceSettings()
