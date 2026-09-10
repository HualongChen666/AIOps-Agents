# -*- coding: utf-8 -*-
"""Plugin microservice configuration."""

from __future__ import annotations

try:
    from pydantic_settings import BaseSettings
except ImportError:  # pragma: no cover
    from pydantic import BaseModel as BaseSettings  # type: ignore[misc, assignment]


class PluginServiceSettings(BaseSettings):
    """Settings for the plugin microservice."""

    service_name: str = "plugin-service"
    environment: str = "development"
    log_level: str = "INFO"
    orchestrator_port: int = 9501

    # Sync SQLAlchemy URL: this service uses the synchronous ORM session that
    # ``services.plugin_service.repository`` is written against.
    database_url: str = "postgresql+psycopg2://postgres@localhost:5432/aiops"  # noqa: E501 - no embedded password
    use_in_memory: bool = False

    enable_prometheus: bool = True
    default_execution_timeout: int = 120
    max_concurrent_executions: int = 1000

    class Config:  # type: ignore[misc]
        env_prefix = "PLUGIN_SERVICE_"
        env_file = ".env"
        extra = "ignore"


settings = PluginServiceSettings()
