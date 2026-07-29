# -*- coding: utf-8 -*-
"""Workflow microservice configuration."""

from __future__ import annotations

try:
    from pydantic_settings import BaseSettings
except ImportError:  # pragma: no cover - fallback for minimal installs
    from pydantic import BaseModel as BaseSettings  # type: ignore[misc, assignment]


class WorkflowServiceSettings(BaseSettings):
    """Settings for the workflow microservice."""

    service_name: str = "workflow-service"
    environment: str = "development"
    log_level: str = "INFO"

    # Service ports
    orchestrator_port: int = 9201
    scheduler_port: int = 9202
    executor_port: int = 9203

    # Infrastructure
    redis_url: str = "redis://localhost:6379/3"
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/aiops"  # noqa: E501
    use_in_memory: bool = True

    # Prometheus
    enable_prometheus: bool = True

    # Execution tuning
    default_execution_timeout: int = 120
    max_concurrent_workflows: int = 50
    scheduler_poll_interval_seconds: int = 1

    class Config:  # type: ignore[misc]
        env_prefix = "WORKFLOW_SERVICE_"
        env_file = ".env"
        extra = "ignore"


settings = WorkflowServiceSettings()
