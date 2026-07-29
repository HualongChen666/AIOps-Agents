# -*- coding: utf-8 -*-
"""Alert microservice configuration."""

from pydantic_settings import BaseSettings


class AlertServiceSettings(BaseSettings):
    """Settings for the alert microservice."""

    service_name: str = "alert-service"
    environment: str = "development"
    log_level: str = "INFO"

    # Service ports
    collector_port: int = 8001
    processor_port: int = 8002
    notifier_port: int = 8003

    # Infrastructure
    redis_url: str = "redis://localhost:6379/0"
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/aiops"  # noqa: E501
    use_in_memory: bool = True

    # Aggregation
    aggregator_window_seconds: int = 30

    # Rate limiting
    collector_max_alerts_per_second: int = 1000
    pipeline_max_concurrent: int = 20
    pipeline_max_retries: int = 3

    # Prometheus
    enable_prometheus: bool = True

    class Config:
        env_prefix = "ALERT_SERVICE_"
        env_file = ".env"
        extra = "ignore"


settings = AlertServiceSettings()
