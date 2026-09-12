# -*- coding: utf-8 -*-
"""Repair microservice configuration."""

from __future__ import annotations

try:
    from pydantic_settings import BaseSettings
except ImportError:  # pragma: no cover - fallback for minimal installs
    from pydantic import BaseModel as BaseSettings  # type: ignore[misc, assignment]


class RepairServiceSettings(BaseSettings):
    """Settings for the repair microservice."""

    service_name: str = "repair-service"
    environment: str = "development"
    log_level: str = "INFO"

    # Service ports
    orchestrator_port: int = 9001
    executor_port: int = 9002
    verifier_port: int = 9003

    # Infrastructure
    redis_url: str = "redis://localhost:6379/1"
    database_url: str = "postgresql+asyncpg://postgres@localhost:5432/aiops"  # noqa: E501 - no embedded password
    use_in_memory: bool = False
    # 安全闸门：默认不执行真实 shell 命令（dry-run）。仅当显式开启时（环境变量
    # REPAIR_SERVICE_ALLOW_REAL_EXECUTION=1）才真实执行 runbook 中的命令。
    allow_real_execution: bool = False

    # Prometheus
    enable_prometheus: bool = True

    # Saga / execution tuning
    default_execution_timeout: int = 120
    max_concurrent_executions: int = 50

    class Config:  # type: ignore[misc]
        env_prefix = "REPAIR_SERVICE_"
        env_file = ".env"
        extra = "ignore"


settings = RepairServiceSettings()
