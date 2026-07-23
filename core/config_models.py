# -*- coding: utf-8 -*-
"""Pydantic-settings based configuration models for the AIOps Agent.

This module provides strongly typed, environment-aware configuration classes
using pydantic-settings.  Nested models use Field aliases so that existing
environment variables (e.g. POSTGRES_HOST, REDIS_PORT) are picked up by
BaseSettings.  List-typed fields that are commonly supplied as comma separated
values (CORS_ORIGINS, CORS_ALLOW_METHODS) are intentionally left without an
alias and are parsed by ConfigManager to avoid forcing JSON syntax in .env.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    """Application environment."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TEST = "test"


class DatabaseConfig(BaseSettings):
    """Database configuration."""

    model_config = SettingsConfigDict(env_prefix="APP_", extra="ignore", populate_by_name=True)

    host: str = Field(default="localhost", alias="POSTGRES_HOST")
    port: int = Field(default=5432, alias="POSTGRES_PORT")
    database: str = Field(default="aiops", alias="POSTGRES_DB")
    username: str = Field(default="postgres", alias="POSTGRES_USER")
    password: str = Field(default="", alias="POSTGRES_PASSWORD")
    pool_size: int = Field(default=10, alias="DB_POOL_SIZE")
    ssl_mode: str = Field(default="prefer", alias="POSTGRES_SSL_MODE")
    min_pool_size: int = Field(default=5, alias="DB_MIN_POOL_SIZE")
    max_pool_size: int = Field(default=20, alias="DB_MAX_POOL_SIZE")
    pool_timeout: int = Field(default=30, alias="DB_POOL_TIMEOUT")
    connection_timeout: int = Field(default=10, alias="DB_CONNECTION_TIMEOUT")
    command_timeout: int = Field(default=60, alias="DB_COMMAND_TIMEOUT")
    echo: bool = Field(default=False, alias="DB_ECHO")
    server_settings: Dict[str, Any] = Field(default_factory=dict, alias="POSTGRES_SERVER_SETTINGS")


class RedisConfig(BaseSettings):
    """Redis configuration."""

    model_config = SettingsConfigDict(env_prefix="APP_", extra="ignore", populate_by_name=True)

    host: str = Field(default="localhost", alias="REDIS_HOST")
    port: int = Field(default=6379, alias="REDIS_PORT")
    db: int = Field(default=0, alias="REDIS_DB")
    password: Optional[str] = Field(default=None, alias="REDIS_PASSWORD")
    socket_timeout: float = Field(default=5.0, alias="REDIS_SOCKET_TIMEOUT")
    socket_connect_timeout: float = Field(default=5.0, alias="REDIS_SOCKET_CONNECT_TIMEOUT")
    pool_size: int = Field(default=10, alias="REDIS_POOL_SIZE")
    ssl: bool = Field(default=False, alias="REDIS_SSL")
    ssl_cert_reqs: str = Field(default="none", alias="REDIS_SSL_CERT_REQS")
    decode_responses: bool = Field(default=True, alias="REDIS_DECODE_RESPONSES")


class SecurityConfig(BaseSettings):
    """Security configuration."""

    model_config = SettingsConfigDict(env_prefix="APP_", extra="ignore", populate_by_name=True)

    jwt_secret_key: str = Field(default="", alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_access_token_expire_minutes: int = Field(default=30, alias="JWT_ACCESS_EXPIRE_MINUTES")
    tls_enabled: bool = Field(default=False, alias="TLS_ENABLED")
    tls_cert_path: str = Field(default="", alias="TLS_CERT_PATH")
    tls_key_path: str = Field(default="", alias="TLS_KEY_PATH")
    mfa_enabled: bool = Field(default=False, alias="MFA_ENABLED")
    password_policy_enabled: bool = Field(default=True, alias="PASSWORD_POLICY_ENABLED")
    rate_limiting_enabled: bool = Field(default=True, alias="RATE_LIMITING_ENABLED")
    rate_limit_max_requests: int = Field(default=100, alias="RATE_LIMIT_MAX_REQUESTS")
    rate_limit_time_window: int = Field(default=60, alias="RATE_LIMIT_TIME_WINDOW")
    bcrypt_rounds: int = Field(default=12, alias="BCRYPT_ROUNDS")


class MonitoringConfig(BaseSettings):
    """Monitoring configuration."""

    model_config = SettingsConfigDict(env_prefix="APP_", extra="ignore", populate_by_name=True)

    enabled: bool = Field(default=True, alias="METRICS_ENABLED")
    prometheus_port: int = Field(default=9090, alias="METRICS_PORT")
    metrics_path: str = Field(default="/metrics", alias="METRICS_PATH")
    tracing_enabled: bool = Field(default=True, alias="TRACING_ENABLED")
    tracing_sample_rate: float = Field(default=1.0, alias="TRACING_SAMPLE_RATE")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")


class AIConfig(BaseSettings):
    """AI/LLM configuration."""

    model_config = SettingsConfigDict(env_prefix="APP_", extra="ignore", populate_by_name=True)

    enabled: bool = Field(default=True, alias="AI_ENABLED")
    api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    base_url: str = Field(default="", alias="AI_BASE_URL")
    model_provider: str = Field(default="openai", alias="AI_MODEL_PROVIDER")
    model_name: str = Field(default="gpt-4", alias="AI_MODEL")
    timeout: int = Field(default=60, alias="AI_TIMEOUT")
    max_retries: int = Field(default=3, alias="AI_MAX_RETRIES")
    temperature: float = Field(default=0.0, alias="AI_TEMPERATURE")
    max_tokens: int = Field(default=2000, alias="AI_MAX_TOKENS")
    cache_enabled: bool = Field(default=True, alias="AI_CACHE_ENABLED")
    cache_ttl: int = Field(default=3600, alias="AI_CACHE_TTL")


class CorsConfig(BaseSettings):
    """CORS configuration (standalone model)."""

    model_config = SettingsConfigDict(env_prefix="APP_", extra="ignore", populate_by_name=True)

    allow_origins: List[str] = Field(default_factory=lambda: ["*"], alias="CORS_ORIGINS")
    allow_methods: List[str] = Field(
        default_factory=lambda: ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        alias="CORS_ALLOW_METHODS",
    )
    allow_headers: List[str] = Field(default_factory=lambda: ["*"], alias="CORS_ALLOW_HEADERS")
    allow_credentials: bool = Field(default=False, alias="CORS_ALLOW_CREDENTIALS")
    max_age: int = Field(default=3600, alias="CORS_MAX_AGE")


class CacheConfig(BaseSettings):
    """Cache configuration."""

    model_config = SettingsConfigDict(env_prefix="APP_", extra="ignore", populate_by_name=True)

    enabled: bool = Field(default=True, alias="CACHE_ENABLED")
    ttl: int = Field(default=300, alias="CACHE_TTL")
    max_size: int = Field(default=1000, alias="CACHE_MAX_SIZE")
    provider: str = Field(default="redis", alias="CACHE_PROVIDER")


class RateLimitConfig(BaseSettings):
    """Rate limit configuration (standalone model)."""

    model_config = SettingsConfigDict(env_prefix="APP_", extra="ignore", populate_by_name=True)

    enabled: bool = Field(default=True, alias="RATE_LIMITING_ENABLED")
    max_requests: int = Field(default=100, alias="RATE_LIMIT_MAX_REQUESTS")
    time_window: int = Field(default=60, alias="RATE_LIMIT_TIME_WINDOW")


class LoggingConfig(BaseSettings):
    """Logging configuration."""

    model_config = SettingsConfigDict(env_prefix="APP_", extra="ignore", populate_by_name=True)

    level: str = Field(default="INFO", alias="LOG_LEVEL")
    format: str = Field(default="json", alias="LOG_FORMAT")
    output_path: str = Field(default="logs", alias="LOG_OUTPUT_PATH")
    rotation: str = Field(default="00:00", alias="LOG_ROTATION")
    retention: str = Field(default="30 days", alias="LOG_RETENTION")


class OpenTelemetryConfig(BaseSettings):
    """OpenTelemetry configuration."""

    model_config = SettingsConfigDict(env_prefix="APP_", extra="ignore", populate_by_name=True)

    enabled: bool = Field(default=True, alias="OTEL_ENABLED")
    service_name: str = Field(default="aiops-agent", alias="OTEL_SERVICE_NAME")
    endpoint: str = Field(default="", alias="OTEL_ENDPOINT")
    sampler: str = Field(default="parentbased_traceidratio", alias="OTEL_SAMPLER")
    propagators: List[str] = Field(
        default_factory=lambda: ["tracecontext", "baggage"], alias="OTEL_PROPAGATORS"
    )


class SlackConfig(BaseSettings):
    """Slack integration configuration."""

    model_config = SettingsConfigDict(env_prefix="APP_", extra="ignore", populate_by_name=True)

    enabled: bool = Field(default=False, alias="SLACK_ENABLED")
    webhook_url: str = Field(default="", alias="SLACK_WEBHOOK_URL")
    channel: str = Field(default="", alias="SLACK_CHANNEL")
    token: str = Field(default="", alias="SLACK_TOKEN")


class TeamsConfig(BaseSettings):
    """Microsoft Teams integration configuration."""

    model_config = SettingsConfigDict(env_prefix="APP_", extra="ignore", populate_by_name=True)

    enabled: bool = Field(default=False, alias="TEAMS_ENABLED")
    webhook_url: str = Field(default="", alias="TEAMS_WEBHOOK_URL")
    tenant_id: str = Field(default="", alias="TEAMS_TENANT_ID")
    client_id: str = Field(default="", alias="TEAMS_CLIENT_ID")
    client_secret: str = Field(default="", alias="TEAMS_CLIENT_SECRET")


class IntegrationConfig(BaseSettings):
    """Generic integration configuration."""

    model_config = SettingsConfigDict(env_prefix="APP_", extra="ignore", populate_by_name=True)

    enabled: bool = Field(default=False, alias="INTEGRATION_ENABLED")
    base_url: str = Field(default="", alias="INTEGRATION_BASE_URL")
    timeout: int = Field(default=30, alias="INTEGRATION_TIMEOUT")
    max_retries: int = Field(default=3, alias="INTEGRATION_MAX_RETRIES")


class FeatureFlags(BaseSettings):
    """Feature flags."""

    model_config = SettingsConfigDict(env_prefix="APP_", extra="ignore", populate_by_name=True)

    enable_ai: bool = Field(default=True, alias="FEATURE_ENABLE_AI")
    enable_metrics: bool = Field(default=True, alias="FEATURE_ENABLE_METRICS")
    enable_caching: bool = Field(default=True, alias="FEATURE_ENABLE_CACHING")
    enable_audit: bool = Field(default=True, alias="FEATURE_ENABLE_AUDIT")
    enable_rate_limiting: bool = Field(default=True, alias="FEATURE_ENABLE_RATE_LIMITING")


class StorageConfig(BaseSettings):
    """Storage backend configuration."""

    model_config = SettingsConfigDict(env_prefix="APP_", extra="ignore", populate_by_name=True)

    victoriametrics_enabled: bool = Field(default=False, alias="STORAGE_VICTORIAMETRICS_ENABLED")
    loki_enabled: bool = Field(default=False, alias="STORAGE_LOKI_ENABLED")
    tempo_enabled: bool = Field(default=False, alias="STORAGE_TEMPO_ENABLED")
    minio_enabled: bool = Field(default=False, alias="STORAGE_MINIO_ENABLED")
    s3_enabled: bool = Field(default=False, alias="STORAGE_S3_ENABLED")


class L2AnalysisConfig(BaseSettings):
    """L2 analysis layer configuration."""

    model_config = SettingsConfigDict(env_prefix="APP_", extra="ignore", populate_by_name=True)

    enabled: bool = Field(default=True, alias="L2_ANALYSIS_ENABLED")
    max_workers: int = Field(default=4, alias="L2_ANALYSIS_MAX_WORKERS")
    queue_size: int = Field(default=1000, alias="L2_ANALYSIS_QUEUE_SIZE")


class L3ProcessingConfig(BaseSettings):
    """L3 processing layer configuration."""

    model_config = SettingsConfigDict(env_prefix="APP_", extra="ignore", populate_by_name=True)

    enabled: bool = Field(default=True, alias="L3_PROCESSING_ENABLED")
    batch_size: int = Field(default=100, alias="L3_PROCESSING_BATCH_SIZE")
    flush_interval: float = Field(default=1.0, alias="L3_PROCESSING_FLUSH_INTERVAL")


class L5InterfaceConfig(BaseSettings):
    """L5 interface layer configuration."""

    model_config = SettingsConfigDict(env_prefix="APP_", extra="ignore", populate_by_name=True)

    enabled: bool = Field(default=True, alias="L5_INTERFACE_ENABLED")
    api_timeout: int = Field(default=30, alias="L5_INTERFACE_API_TIMEOUT")
    max_payload_size: int = Field(default=10485760, alias="L5_INTERFACE_MAX_PAYLOAD_SIZE")


class L6ExecutionConfig(BaseSettings):
    """L6 execution layer configuration."""

    model_config = SettingsConfigDict(env_prefix="APP_", extra="ignore", populate_by_name=True)

    enabled: bool = Field(default=True, alias="L6_EXECUTION_ENABLED")
    executor_pool_size: int = Field(default=4, alias="L6_EXECUTION_EXECUTOR_POOL_SIZE")
    task_timeout: int = Field(default=300, alias="L6_EXECUTION_TASK_TIMEOUT")


class L7IntegrationConfig(BaseSettings):
    """L7 integration layer configuration."""

    model_config = SettingsConfigDict(env_prefix="APP_", extra="ignore", populate_by_name=True)

    enabled: bool = Field(default=True, alias="L7_INTEGRATION_ENABLED")
    adapter_timeout: int = Field(default=30, alias="L7_INTEGRATION_ADAPTER_TIMEOUT")
    max_retries: int = Field(default=3, alias="L7_INTEGRATION_MAX_RETRIES")


class ServiceWorkerConfig(BaseSettings):
    """Service worker configuration."""

    model_config = SettingsConfigDict(env_prefix="APP_", extra="ignore", populate_by_name=True)

    cache_name: str = Field(default="aiops-v1", alias="SW_CACHE_NAME")
    offline_fallback: str = Field(default="/offline.html", alias="SW_OFFLINE_FALLBACK")
    precache_urls: List[str] = Field(default_factory=list, alias="SW_PRECACHE_URLS")


class AppConfig(BaseSettings):
    """Root application configuration."""

    model_config = SettingsConfigDict(
        env_prefix="APP_",
        extra="ignore",
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=False,
    )

    environment: Environment = Field(default=Environment.DEVELOPMENT, alias="ENVIRONMENT")
    debug: bool = Field(default=True, alias="DEBUG")
    app_name: str = Field(default="AIOps Agent", alias="APP_NAME")
    app_version: str = Field(default="1.0.0", alias="APP_VERSION")
    host: str = Field(default="127.0.0.1", alias="HOST")
    port: int = Field(default=8000, alias="PORT")
    workers: int = Field(default=4, alias="WORKERS")

    cors_origins: List[str] = Field(default_factory=lambda: ["*"])
    cors_allow_methods: List[str] = Field(
        default_factory=lambda: ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    )
    cors_allow_headers: List[str] = Field(default_factory=lambda: ["*"])
    cors_allow_credentials: bool = Field(default=False, alias="CORS_ALLOW_CREDENTIALS")
    cors_max_age: int = Field(default=3600, alias="CORS_MAX_AGE")

    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    redis: RedisConfig = Field(default_factory=RedisConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig)
    ai: AIConfig = Field(default_factory=AIConfig)
    cache: CacheConfig = Field(default_factory=CacheConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    opentelemetry: OpenTelemetryConfig = Field(default_factory=OpenTelemetryConfig)
    slack: SlackConfig = Field(default_factory=SlackConfig)
    teams: TeamsConfig = Field(default_factory=TeamsConfig)
    integration: IntegrationConfig = Field(default_factory=IntegrationConfig)
    feature_flags: FeatureFlags = Field(default_factory=FeatureFlags)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    l2_analysis: L2AnalysisConfig = Field(default_factory=L2AnalysisConfig)
    l3_processing: L3ProcessingConfig = Field(default_factory=L3ProcessingConfig)
    l5_interface: L5InterfaceConfig = Field(default_factory=L5InterfaceConfig)
    l6_execution: L6ExecutionConfig = Field(default_factory=L6ExecutionConfig)
    l7_integration: L7IntegrationConfig = Field(default_factory=L7IntegrationConfig)
    service_worker: ServiceWorkerConfig = Field(default_factory=ServiceWorkerConfig)


# Backward compatible aliases and additional names requested by the task.
DatabaseSettings = DatabaseConfig
RedisSettings = RedisConfig
SecuritySettings = SecurityConfig
MonitoringSettings = MonitoringConfig
AISettings = AIConfig
CorsSettings = CorsConfig
CacheSettings = CacheConfig
RateLimitSettings = RateLimitConfig
LoggingSettings = LoggingConfig
OpenTelemetrySettings = OpenTelemetryConfig
SlackSettings = SlackConfig
TeamsSettings = TeamsConfig
IntegrationSettings = IntegrationConfig
StorageSettings = StorageConfig
L2AnalysisSettings = L2AnalysisConfig
L3ProcessingSettings = L3ProcessingConfig
L5InterfaceSettings = L5InterfaceConfig
L6ExecutionSettings = L6ExecutionConfig
L7IntegrationSettings = L7IntegrationConfig
ServiceWorkerSettings = ServiceWorkerConfig

AppSettings = AppConfig
Settings = AppConfig
UnifiedConfig = AppConfig
