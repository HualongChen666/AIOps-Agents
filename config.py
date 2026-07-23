# -*- coding: utf-8 -*-
import importlib
import os
import pathlib
import time
from pathlib import Path
from typing import Any, Dict, List, Optional  # noqa: F401
from urllib.parse import quote_plus

from loguru import logger

# Optional watchdog for hot reload support
try:
    from watchdog.events import FileSystemEventHandler  # noqa: E402
    from watchdog.observers import Observer  # noqa: E402

    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    logger.info("[config] watchdog not available, hot reload disabled")

# Load .env file if it exists
env_file = Path(".env")
if env_file.exists():
    from dotenv import load_dotenv  # noqa: E402

    load_dotenv()
    logger.info("[config] Loaded environment from .env")


# =============================
# Helper functions for safe environment variable parsing
# =============================
def _safe_bool(key: str, default: bool = False) -> bool:
    """Safely parse boolean from environment variable."""
    val = os.getenv(key, "").strip().lower()
    if val in ("true", "1", "yes", "on"):
        return True
    if val in ("false", "0", "no", "off"):
        return False
    return default


def _safe_int(
    key: str, default: int = 0, min_val: Optional[int] = None, max_val: Optional[int] = None
) -> int:
    """Safely parse integer from environment variable with bounds checking."""
    try:
        val = int(os.getenv(key, str(default)).strip())
        if min_val is not None and val < min_val:
            logger.warning(f"[config] {key}={val} below min {min_val}, using {min_val}")
            return min_val
        if max_val is not None and val > max_val:
            logger.warning(f"[config] {key}={val} above max {max_val}, using {max_val}")
            return max_val
        return val
    except ValueError:
        logger.warning(f"[config] {key} invalid int, using default {default}")
        return default


def _safe_float(
    key: str, default: float = 0.0, min_val: Optional[float] = None, max_val: Optional[float] = None
) -> float:
    """Safely parse float from environment variable with bounds checking."""
    try:
        val = float(os.getenv(key, str(default)).strip())
        if min_val is not None and val < min_val:
            logger.warning(f"[config] {key}={val} below min {min_val}, using {min_val}")
            return min_val
        if max_val is not None and val > max_val:
            logger.warning(f"[config] {key}={val} above max {max_val}, using {max_val}")
            return max_val
        return val
    except ValueError:
        logger.warning(f"[config] {key} invalid float, using default {default}")
        return default


# ============================================================
# Environment Detection
# ============================================================
environment = os.getenv("ENVIRONMENT", "development")

# ============================================================
# Microsoft Teams Configuration (Incoming Webhook)
# ============================================================
TEAMS_WEBHOOK_URL: str = os.getenv("TEAMS_WEBHOOK_URL", "").strip()
TEAMS_DEFAULT_CHANNEL: str = os.getenv("TEAMS_DEFAULT_CHANNEL", "General").strip()

# ============================================================
# Internal API Key for protected endpoints
# ============================================================
INTERNAL_API_KEY: str = os.getenv("INTERNAL_API_KEY", "").strip()

# ============================================================
# Proxy configuration
# ============================================================
TRUST_PROXY_HEADER: str = os.getenv("TRUST_PROXY_HEADER", "X-Forwarded-For").strip()
# ALLOWED_LOCAL_IPS is defined later in Health Check section

# ============================================================
# OpenTelemetry Collector endpoint
# ============================================================
OTEL_COLLECTOR_ENDPOINT: str = os.getenv("OTEL_COLLECTOR_ENDPOINT", "http://localhost:4318").strip()

# ============================================================
# LLM Router Configuration (Cost Optimization)
# ============================================================
LLM_ROUTER_MODELS = [
    {
        "provider": "openai",
        "model": "gpt-4o-mini",
        "max_tokens": 128000,
        "cost_per_1k": 0.015,
    },
    {
        "provider": "openai",
        "model": "gpt-3.5-turbo",
        "max_tokens": 16384,
        "cost_per_1k": 0.005,
    },
    {
        "provider": "minimax",
        "model": "MiniMax-Text-01",
        "max_tokens": 12000,
        "cost_per_1k": 0.02,
    },
]

LLM_ROUTER_TOKEN_COST_THRESHOLD = 20000

# ============================================================
# Redis Configuration
# ============================================================
REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost").strip()
REDIS_PORT: int = _safe_int("REDIS_PORT", default=6379, min_val=1, max_val=65535)
REDIS_DB: int = _safe_int("REDIS_DB", default=0, min_val=0, max_val=15)
REDIS_URL: str = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"

# ============================================================
# PostgreSQL Database Configuration
# ============================================================
POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost").strip()
POSTGRES_PORT: int = _safe_int("POSTGRES_PORT", default=5432, min_val=1, max_val=65535)
POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres").strip()
POSTGRES_DB: str = os.getenv("POSTGRES_DB", "aiops").strip()
POSTGRES_DATABASE: str = POSTGRES_DB

# Secure password handling
POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "").strip()
if environment == "production":
    if not POSTGRES_PASSWORD:
        raise ValueError(
            "POSTGRES_PASSWORD must be set in production environment. "
            "Set it via environment variable."
        )
else:
    if not POSTGRES_PASSWORD:
        POSTGRES_PASSWORD = "postgres"

POSTGRES_URL: str = (
    f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"  # noqa: E501  # noqa: E501
)

# ============================================================
# Qdrant Vector Database Configuration
# ============================================================
QDRANT_HOST: str = os.getenv("QDRANT_HOST", "localhost").strip()
QDRANT_PORT: int = _safe_int("QDRANT_PORT", default=6333, min_val=1, max_val=65535)
QDRANT_URL: str = f"http://{QDRANT_HOST}:{QDRANT_PORT}"

# ============================================================
# Loki Log Aggregation Configuration
# ============================================================
# LOKI_HOST, LOKI_PORT, LOKI_URL are defined in L4 Storage Layer Configuration section

# ============================================================
# Elasticsearch Configuration
# ============================================================
ELASTICSEARCH_HOST: str = os.getenv("ELASTICSEARCH_HOST", "localhost").strip()
ELASTICSEARCH_PORT: int = _safe_int("ELASTICSEARCH_PORT", default=9200, min_val=1, max_val=65535)
ELASTICSEARCH_URL: str = f"http://{ELASTICSEARCH_HOST}:{ELASTICSEARCH_PORT}"

# ============================================================
# Kafka Configuration (Original)
# ============================================================
KAFKA_BROKERS: list[str] = os.getenv("KAFKA_BROKERS", "localhost:9092").strip().split(",")

# ============================================================
# DataHub Metadata Platform Configuration
# ============================================================
DATAHUB_HOST: str = os.getenv("DATAHUB_HOST", "localhost").strip()
DATAHUB_PORT: int = _safe_int("DATAHUB_PORT", default=8080, min_val=1, max_val=65535)
DATAHUB_REST_URL: str = f"http://{DATAHUB_HOST}:{DATAHUB_PORT}"

# ============================================================
# OpenTelemetry OTLP Configuration
# ============================================================
OTEL_EXPORTER_OTLP_ENDPOINT: str = os.getenv(
    "OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317"
).strip()

# ============================================================
# Repair Engine Configuration
# ============================================================
REPAIR_HOST: str = os.getenv("REPAIR_HOST", "localhost").strip()

# ============================================================
# Health Check IP Whitelist
# ============================================================
ALLOWED_LOCAL_IPS: list[str] = (
    os.getenv("ALLOWED_LOCAL_IPS", "127.0.0.1,::1,localhost").strip().split(",")
)

# ============================================================
# Guard Default Host
# ============================================================
GUARD_DEFAULT_HOST: str = os.getenv("GUARD_DEFAULT_HOST", "localhost").strip()

# ============================================================
# Health Check URL
# ============================================================
HEALTH_CHECK_URL: str = os.getenv("HEALTH_CHECK_URL", "http://localhost").strip()

# ============================================================
# JWT Authentication Configuration
# ============================================================
JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "").strip()
if environment == "production":
    if not JWT_SECRET_KEY:
        raise ValueError(
            "JWT_SECRET_KEY must be set in production environment. "
            "Set it via environment variable or use a strong random secret."
        )
else:
    if not JWT_SECRET_KEY:
        JWT_SECRET_KEY = "dev-secret-key-change-me-in-production"

JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256").strip()
JWT_ACCESS_EXPIRE_MINUTES: int = _safe_int(
    "JWT_ACCESS_EXPIRE_MINUTES", default=30, min_val=1, max_val=1440
)
JWT_ISSUER: str = os.getenv("JWT_ISSUER", "aiops-agent").strip()
JWT_AUDIENCE: str = os.getenv("JWT_AUDIENCE", "aiops-api").strip()

# ============================================================
# Password Hash Configuration
# ============================================================
BCRYPT_ROUNDS: int = _safe_int("BCRYPT_ROUNDS", default=12, min_val=4, max_val=14)

# ============================================================
# HTTPS/TLS Configuration
# ============================================================
HTTPS_ENABLED: bool = _safe_bool("HTTPS_ENABLED", default=False)
SSL_CERT_FILE: str = os.getenv("SSL_CERT_FILE", "").strip()
SSL_KEY_FILE: str = os.getenv("SSL_KEY_FILE", "").strip()

# ============================================================
# Database URL with Encoding
# ============================================================

_encoded_password = quote_plus(POSTGRES_PASSWORD)
DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    f"postgresql+asyncpg://{POSTGRES_USER}:{_encoded_password}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}",  # noqa: E501
).strip()

# ============================================================
# Redis Password Configuration
# ============================================================
REDIS_PASSWORD: str = os.getenv("REDIS_PASSWORD", "").strip()

# ============================================================
# Temporal Configuration
# ============================================================
TEMPORAL_ADDRESS: str = os.getenv("TEMPORAL_ADDRESS", "localhost:7233").strip()

# ============================================================
# SSO/OIDC Configuration
# ============================================================
OIDC_REDIRECT_URI: str = os.getenv(
    "OIDC_REDIRECT_URI", "http://localhost:8000/auth/callback"
).strip()

# ============================================================
# Log Configuration
# ============================================================
DEFAULT_LOG_HOST: str = os.getenv("DEFAULT_LOG_HOST", "localhost").strip()
DEFAULT_HOST: str = os.getenv("DEFAULT_HOST", "localhost").strip()

# ============================================================
# AI Engine Configuration (MiniMax / OpenAI Compatible)
# ============================================================
AI_CONFIG: dict[str, Any] = {
    "is_enabled": _safe_bool("AI_ENABLED", default=False),
    "api_key": os.getenv("AI_API_KEY", "").strip(),
    "base_url": os.getenv("AI_BASE_URL", "https://api.minimaxi.com/v1").strip(),
    "model": os.getenv("AI_MODEL", "MiniMax-Text-01").strip(),
    "timeout": _safe_int("AI_TIMEOUT", default=30, min_val=1, max_val=300),
    "max_retries": _safe_int("AI_MAX_RETRIES", default=2, min_val=0, max_val=5),
}

# ============================================================
# AI Rich Context Timeout Configuration
# ============================================================
AI_RICH_CONTEXT_TIMEOUT_SEC: float = _safe_float(
    "AI_RICH_CONTEXT_TIMEOUT_SEC", default=2.0, min_val=0.5, max_val=10.0
)

if AI_CONFIG["is_enabled"] and not AI_CONFIG["api_key"]:
    logger.warning("[config] ⚠️ AI_ENABLED=true 但 AI_API_KEY 未配置,服务将降级到规则引擎")

# ============================================================
# CORS Configuration
# ============================================================
CORS_ORIGINS: list[str] = os.getenv("CORS_ORIGINS", "*").strip().split(",")
CORS_ALLOW_CREDENTIALS: bool = _safe_bool("CORS_ALLOW_CREDENTIALS", default=False)
CORS_ALLOW_METHODS: list[str] = (
    os.getenv("CORS_ALLOW_METHODS", "GET,POST,PUT,DELETE,OPTIONS").strip().split(",")
)
CORS_ALLOW_HEADERS: list[str] = os.getenv("CORS_ALLOW_HEADERS", "*").strip().split(",")

# ============================================================
# API Rate Limiting Configuration
# ============================================================
API_RATE_LIMIT_ENABLED: bool = _safe_bool("API_RATE_LIMIT_ENABLED", default=True)
API_RATE_LIMIT_PER_MINUTE: int = _safe_int(
    "API_RATE_LIMIT_PER_MINUTE", default=60, min_val=1, max_val=1000
)
API_RATE_LIMIT_PER_HOUR: int = _safe_int(
    "API_RATE_LIMIT_PER_HOUR", default=1000, min_val=1, max_val=10000
)

# ============================================================
# Cache Configuration
# ============================================================
# Basic cache configuration - Enhanced version is in Caching Strategy Configuration section

# ============================================================
# Self-Learning / Verification Configuration
# ============================================================
VERIFY_CONFIG: dict[str, Any] = {
    "self_learning_enabled": _safe_bool("VERIFY_SELF_LEARNING_ENABLED", default=True),
    "history_lookback_days": _safe_int(
        "VERIFY_HISTORY_LOOKBACK_DAYS", default=30, min_val=1, max_val=365
    ),
    "min_samples_for_learning": _safe_int(
        "VERIFY_MIN_SAMPLES_FOR_LEARNING", default=3, min_val=1, max_val=10
    ),
}

# ============================================================
# K8S Configuration
# ============================================================
K8S_HOSTS: list[dict] = []
K8S_HOST_MAX_FAILURES: int = _safe_int("K8S_HOST_MAX_FAILURES", default=5, min_val=1, max_val=20)
K8S_HOST_COOLDOWN_SEC: int = _safe_int(
    "K8S_HOST_COOLDOWN_SEC", default=300, min_val=60, max_val=3600
)

# ============================================================
# Docker Configuration
# ============================================================
DOCKER_HOSTS: list[dict] = []
DOCKER_HOST_MAX_FAILURES: int = _safe_int(
    "DOCKER_HOST_MAX_FAILURES", default=5, min_val=1, max_val=20
)
DOCKER_HOST_COOLDOWN_SEC: int = _safe_int(
    "DOCKER_HOST_COOLDOWN_SEC", default=300, min_val=60, max_val=3600
)

# ============================================================
# Windows Configuration
# ============================================================
WIN_HOSTS: list[dict] = []
WIN_HOST_MAX_FAILURES: int = _safe_int("WIN_HOST_MAX_FAILURES", default=5, min_val=1, max_val=20)
WIN_HOST_COOLDOWN_SEC: int = _safe_int(
    "WIN_HOST_COOLDOWN_SEC", default=300, min_val=60, max_val=3600
)

# ============================================================
# Linux Configuration
# ============================================================
LINUX_SSH_BATCH_SIZE: int = _safe_int("LINUX_SSH_BATCH_SIZE", default=20, min_val=5, max_val=50)
LINUX_HOST_MAX_FAILURES: int = _safe_int(
    "LINUX_HOST_MAX_FAILURES", default=5, min_val=1, max_val=20
)
LINUX_HOST_COOLDOWN_SEC: int = _safe_int(
    "LINUX_HOST_COOLDOWN_SEC", default=300, min_val=60, max_val=3600
)

# ============================================================
# Base Directory
# ============================================================

BASE_DIR: pathlib.Path = pathlib.Path(__file__).parent.resolve()

# ============================================================
# Cloud Configuration
# ============================================================
CLOUD_PROVIDERS: list[dict] = []
CLOUD_HOST_MAX_FAILURES: int = _safe_int(
    "CLOUD_HOST_MAX_FAILURES", default=5, min_val=1, max_val=20
)
CLOUD_HOST_COOLDOWN_SEC: int = _safe_int(
    "CLOUD_HOST_COOLDOWN_SEC", default=300, min_val=60, max_val=3600
)

# ============================================================
# Linux Configuration
# ============================================================
LINUX_SSH_TIMEOUT: int = _safe_int("LINUX_SSH_TIMEOUT", default=30, min_val=5, max_val=120)

# ============================================================
# Kafka Configuration for Real-time Stream Processing (Enhanced)
# ============================================================
KAFKA_BROKERS_ENHANCED: str = os.getenv("KAFKA_BROKERS", "localhost:9092")
KAFKA_GROUP_ID: str = os.getenv("KAFKA_GROUP_ID", "aiops-agent")
KAFKA_AUTO_OFFSET_RESET: str = os.getenv("KAFKA_AUTO_OFFSET_RESET", "latest")
KAFKA_ENABLE_AUTO_COMMIT: bool = _safe_bool("KAFKA_ENABLE_AUTO_COMMIT", default=True)
KAFKA_ACKS: str = os.getenv("KAFKA_ACKS", "all")

# ============================================================
# Flink Configuration for Stream Processing
# ============================================================
FLINK_CONFIG: dict[str, Any] = {
    "job_parallelism": _safe_int("FLINK_JOB_PARALLELISM", default=2, min_val=1, max_val=10),
    "checkpoint_interval": _safe_int(
        "FLINK_CHECKPOINT_INTERVAL", default=60000, min_val=10000, max_val=300000
    ),
    "savepoint_path": os.getenv("FLINK_SAVEPOINT_PATH", "/tmp/flink-savepoints"),
    "state_backend": os.getenv("FLINK_STATE_BACKEND", "file:///tmp/flink-checkpoints"),
    "enable_state_backend": _safe_bool("FLINK_ENABLE_STATE_BACKEND", default=False),
}

# ============================================================
# Langfuse Configuration (LLM Observability)
# ============================================================
LANGFUSE_CONFIG: dict[str, Any] = {
    "is_enabled": _safe_bool("LANGFUSE_ENABLED", default=False),
    "public_key": os.getenv("LANGFUSE_PUBLIC_KEY", "").strip(),
    "secret_key": os.getenv("LANGFUSE_SECRET_KEY", "").strip(),
    "host": os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com").strip(),
    "session_id": os.getenv("LANGFUSE_SESSION_ID", "").strip(),
}

if LANGFUSE_CONFIG["is_enabled"] and not (
    LANGFUSE_CONFIG["public_key"] and LANGFUSE_CONFIG["secret_key"]
):
    logger.warning(
        "[config] ⚠️ LANGFUSE_ENABLED=true 但 LANGFUSE_PUBLIC_KEY 或 LANGFUSE_SECRET_KEY"
        " 未配置,追踪功能将禁用"
    )
    LANGFUSE_CONFIG["is_enabled"] = False

# ============================================================
# Alert Thresholds Configuration
# ============================================================
ALERT_THRESHOLDS: dict[str, float] = {
    "cpu_percent": _safe_int("ALERT_CPU_THRESHOLD", default=80, min_val=1, max_val=100),
    "memory_percent": _safe_int("ALERT_MEMORY_THRESHOLD", default=85, min_val=1, max_val=100),
    "disk_percent": _safe_int("ALERT_DISK_THRESHOLD", default=90, min_val=1, max_val=100),
}

COLLECT_INTERVAL_SEC: int = _safe_int("COLLECT_INTERVAL_SEC", default=5, min_val=1, max_val=60)
ALERT_HISTORY_MAX: int = _safe_int("ALERT_HISTORY_MAX", default=1000, min_val=100, max_val=10000)

DYNAMIC_THRESHOLD_CONFIG: dict[str, Any] = {
    "enabled": _safe_bool("DYNAMIC_THRESHOLD_ENABLED", default=False),
    "window_size": _safe_int("DYNAMIC_THRESHOLD_WINDOW", default=60, min_val=10, max_val=300),
    "std_dev_multiplier": _safe_float(
        "DYNAMIC_THRESHOLD_STD_DEV", default=2.0, min_val=1.0, max_val=5.0
    ),
}

LINUX_HOSTS: dict[str, Any] = {
    "enabled": _safe_bool("LINUX_HOSTS_ENABLED", default=False),
    "hosts": [],
}

# ============================================================
# L4 Storage Layer Configuration (7-Layer Architecture)
# ============================================================
VICTORIAMETRICS_ENABLED: bool = _safe_bool("VICTORIAMETRICS_ENABLED", default=False)
VICTORIAMETRICS_HOST: str = os.getenv("VICTORIAMETRICS_HOST", "localhost").strip()
VICTORIAMETRICS_PORT: int = _safe_int(
    "VICTORIAMETRICS_PORT", default=8428, min_val=1, max_val=65535
)
VICTORIAMETRICS_URL: str = f"http://{VICTORIAMETRICS_HOST}:{VICTORIAMETRICS_PORT}"
VICTORIAMETRICS_TIMEOUT: int = _safe_int(
    "VICTORIAMETRICS_TIMEOUT", default=30, min_val=1, max_val=300
)

LOKI_ENABLED: bool = _safe_bool("LOKI_ENABLED", default=False)
LOKI_HOST: str = os.getenv("LOKI_HOST", "localhost").strip()
LOKI_PORT: int = _safe_int("LOKI_PORT", default=3100, min_val=1, max_val=65535)
LOKI_URL: str = f"http://{LOKI_HOST}:{LOKI_PORT}"
LOKI_TIMEOUT: int = _safe_int("LOKI_TIMEOUT", default=30, min_val=1, max_val=300)

TEMPO_ENABLED: bool = _safe_bool("TEMPO_ENABLED", default=False)
TEMPO_HOST: str = os.getenv("TEMPO_HOST", "localhost").strip()
TEMPO_PORT: int = _safe_int("TEMPO_PORT", default=3200, min_val=1, max_val=65535)
TEMPO_URL: str = f"http://{TEMPO_HOST}:{TEMPO_PORT}"
TEMPO_TIMEOUT: int = _safe_int("TEMPO_TIMEOUT", default=30, min_val=1, max_val=300)

L4_STORAGE_CONFIG: dict[str, Any] = {
    "victoriametrics": {
        "enabled": VICTORIAMETRICS_ENABLED,
        "base_url": VICTORIAMETRICS_URL,
        "timeout": VICTORIAMETRICS_TIMEOUT,
    },
    "loki": {
        "enabled": LOKI_ENABLED,
        "base_url": LOKI_URL,
        "timeout": LOKI_TIMEOUT,
    },
    "tempo": {
        "enabled": TEMPO_ENABLED,
        "base_url": TEMPO_URL,
        "timeout": TEMPO_TIMEOUT,
    },
}

# ============================================================
# L2 Analysis Layer Configuration (7-Layer Architecture)
# ============================================================
LANGGRAPH_ENABLED: bool = _safe_bool("LANGGRAPH_ENABLED", default=False)

RAG_ENABLED: bool = _safe_bool("RAG_ENABLED", default=False)
RAG_COLLECTION_NAME: str = os.getenv("RAG_COLLECTION_NAME", "aiops_knowledge").strip()
RAG_EMBEDDING_MODEL: str = os.getenv("RAG_EMBEDDING_MODEL", "all-MiniLM-L6-v2").strip()
RAG_RETRIEVAL_LIMIT: int = _safe_int("RAG_RETRIEVAL_LIMIT", default=5, min_val=1, max_val=20)
RAG_SCORE_THRESHOLD: float = float(os.getenv("RAG_SCORE_THRESHOLD", "0.5"))

L2_ANALYSIS_CONFIG: dict[str, Any] = {
    "langgraph": {
        "enabled": LANGGRAPH_ENABLED,
    },
    "rag": {
        "enabled": RAG_ENABLED,
        "qdrant_host": QDRANT_HOST,
        "qdrant_port": QDRANT_PORT,
        "collection_name": RAG_COLLECTION_NAME,
        "embedding_model": RAG_EMBEDDING_MODEL,
        "retrieval_limit": RAG_RETRIEVAL_LIMIT,
        "score_threshold": RAG_SCORE_THRESHOLD,
    },
    "model_router": {
        "models": LLM_ROUTER_MODELS,
        "token_cost_threshold": LLM_ROUTER_TOKEN_COST_THRESHOLD,
    },
}

# ============================================================
# L5 Interface Layer Configuration (7-Layer Architecture)
# ============================================================
MCP_ENABLED: bool = _safe_bool("MCP_ENABLED", default=False)

GRAPHQL_ENABLED: bool = _safe_bool("GRAPHQL_ENABLED", default=False)
GRAPHQL_PATH: str = os.getenv("GRAPHQL_PATH", "/graphql").strip()

L5_INTERFACE_CONFIG: dict[str, Any] = {
    "mcp": {
        "enabled": MCP_ENABLED,
    },
    "graphql": {
        "enabled": GRAPHQL_ENABLED,
        "path": GRAPHQL_PATH,
    },
}

# ============================================================
# L7 Integration Layer Configuration (7-Layer Architecture)
# ============================================================
SERVICENOW_ENABLED: bool = _safe_bool("SERVICENOW_ENABLED", default=False)
SERVICENOW_INSTANCE: str = os.getenv("SERVICENOW_INSTANCE", "").strip()
SERVICENOW_USERNAME: str = os.getenv("SERVICENOW_USERNAME", "").strip()
SERVICENOW_PASSWORD: str = os.getenv("SERVICENOW_PASSWORD", "").strip()

JIRA_ENABLED: bool = _safe_bool("JIRA_ENABLED", default=False)
JIRA_URL: str = os.getenv("JIRA_URL", "").strip()
JIRA_USERNAME: str = os.getenv("JIRA_USERNAME", "").strip()
JIRA_API_TOKEN: str = os.getenv("JIRA_API_TOKEN", "").strip()

SLACK_ENABLED: bool = _safe_bool("SLACK_ENABLED", default=False)
SLACK_BOT_TOKEN: str = os.getenv("SLACK_BOT_TOKEN", "").strip()
SLACK_SIGNING_SECRET: str = os.getenv("SLACK_SIGNING_SECRET", "").strip()
SLACK_DEFAULT_CHANNEL: str = os.getenv("SLACK_DEFAULT_CHANNEL", "#aiops-alerts").strip()
SLACK_CHANNEL: str = os.getenv("SLACK_CHANNEL", "#aiops-alerts").strip()

TEAMS_ENABLED: bool = _safe_bool("TEAMS_ENABLED", default=False)
TEAMS_WEBHOOK: str = os.getenv("TEAMS_WEBHOOK", "").strip()
TEAMS_CHANNEL: str = os.getenv("TEAMS_CHANNEL", "aiops-alerts").strip()

L7_INTEGRATION_CONFIG: dict[str, Any] = {
    "itsm": {
        "servicenow": {
            "enabled": SERVICENOW_ENABLED,
            "instance": SERVICENOW_INSTANCE,
            "username": SERVICENOW_USERNAME,
            "password": SERVICENOW_PASSWORD,
        },
        "jira": {
            "enabled": JIRA_ENABLED,
            "url": JIRA_URL,
            "username": JIRA_USERNAME,
            "api_token": JIRA_API_TOKEN,
        },
    },
    "collaboration": {
        "slack": {
            "enabled": SLACK_ENABLED,
            "bot_token": SLACK_BOT_TOKEN,
            "channel": SLACK_CHANNEL,
        },
        "teams": {
            "enabled": TEAMS_ENABLED,
            "webhook": TEAMS_WEBHOOK,
            "channel": TEAMS_CHANNEL,
        },
    },
}

# ============================================================
# L3 Processing Layer Configuration (7-Layer Architecture)
# ============================================================
WORKFLOW_ENGINE_ENABLED: bool = _safe_bool("WORKFLOW_ENGINE_ENABLED", default=False)
WORKFLOW_ENGINE_MAX_CONCURRENT: int = _safe_int(
    "WORKFLOW_ENGINE_MAX_CONCURRENT", default=10, min_val=1, max_val=50
)

CAUSAL_GRAPH_ENABLED: bool = _safe_bool("CAUSAL_GRAPH_ENABLED", default=False)
CAUSAL_GRAPH_AUTO_BUILD: bool = _safe_bool("CAUSAL_GRAPH_AUTO_BUILD", default=True)

L3_PROCESSING_CONFIG: dict[str, Any] = {
    "workflow_engine": {
        "enabled": WORKFLOW_ENGINE_ENABLED,
        "max_concurrent": WORKFLOW_ENGINE_MAX_CONCURRENT,
    },
    "causal_graph": {
        "enabled": CAUSAL_GRAPH_ENABLED,
        "auto_build": CAUSAL_GRAPH_AUTO_BUILD,
    },
}

# ============================================================
# L6 Execution Layer Configuration (7-Layer Architecture)
# ============================================================
EXECUTOR_CACHE_ENABLED: bool = _safe_bool("EXECUTOR_CACHE_ENABLED", default=True)
EXECUTOR_CACHE_TTL: int = _safe_int("EXECUTOR_CACHE_TTL", default=300, min_val=60, max_val=3600)
EXECUTOR_MAX_PARALLEL: int = _safe_int("EXECUTOR_MAX_PARALLEL", default=5, min_val=1, max_val=20)
EXECUTOR_L2_INTEGRATION: bool = _safe_bool("EXECUTOR_L2_INTEGRATION", default=True)
EXECUTOR_L3_INTEGRATION: bool = _safe_bool("EXECUTOR_L3_INTEGRATION", default=True)
EXECUTOR_L4_INTEGRATION: bool = _safe_bool("EXECUTOR_L4_INTEGRATION", default=True)

L6_EXECUTION_CONFIG: dict[str, Any] = {
    "cache_enabled": EXECUTOR_CACHE_ENABLED,
    "cache_ttl": EXECUTOR_CACHE_TTL,
    "max_parallel_tasks": EXECUTOR_MAX_PARALLEL,
    "l2_integration": EXECUTOR_L2_INTEGRATION,
    "l3_integration": EXECUTOR_L3_INTEGRATION,
    "l4_integration": EXECUTOR_L4_INTEGRATION,
}

BUSINESS_SLA: dict[str, int] = {
    "critical": 0,
    "high": 1,
    "medium": 2,
    "low": 3,
}
DEFAULT_SLA: int = 3

# ============================================================
# Rate Limiting Configuration
# ============================================================
RATE_LIMIT_ENABLED: bool = _safe_bool("RATE_LIMIT_ENABLED", True)
RATE_LIMIT_PER_MINUTE: int = _safe_int("RATE_LIMIT_PER_MINUTE", 60, min_val=1, max_val=1000)
RATE_LIMIT_PER_HOUR: int = _safe_int("RATE_LIMIT_PER_HOUR", 1000, min_val=10, max_val=10000)
RATE_LIMIT_PER_DAY: int = _safe_int("RATE_LIMIT_PER_DAY", 10000, min_val=100, max_val=100000)

RATE_LIMIT_AUTH_PER_MINUTE: int = _safe_int("RATE_LIMIT_AUTH_PER_MINUTE", 5, min_val=1, max_val=100)
RATE_LIMIT_API_PER_MINUTE: int = _safe_int("RATE_LIMIT_API_PER_MINUTE", 60, min_val=1, max_val=1000)
RATE_LIMIT_ADMIN_PER_MINUTE: int = _safe_int(
    "RATE_LIMIT_ADMIN_PER_MINUTE", 200, min_val=1, max_val=2000
)

# ============================================================
# Business Metrics Configuration
# ============================================================
METRICS_ENABLED: bool = _safe_bool("METRICS_ENABLED", True)
METRICS_PORT: int = _safe_int("METRICS_PORT", 9090, min_val=1024, max_val=65535)
METRICS_PATH: str = os.getenv("METRICS_PATH", "/metrics")

METRICS_COLLECTION_INTERVAL_SECONDS: int = _safe_int(
    "METRICS_COLLECTION_INTERVAL_SECONDS", 10, min_val=1, max_val=300
)
METRICS_HISTORY_RETENTION_DAYS: int = _safe_int(
    "METRICS_HISTORY_RETENTION_DAYS", 30, min_val=1, max_val=365
)

ALERT_GENERATION_THRESHOLD_CRITICAL: int = _safe_int(
    "ALERT_GENERATION_THRESHOLD_CRITICAL", 10, min_val=1, max_val=100
)
ALERT_GENERATION_THRESHOLD_WARNING: int = _safe_int(
    "ALERT_GENERATION_THRESHOLD_WARNING", 5, min_val=1, max_val=50
)
REPAIR_EXECUTION_THRESHOLD_CRITICAL: int = _safe_int(
    "REPAIR_EXECUTION_THRESHOLD_CRITICAL", 20, min_val=1, max_val=300
)
REPAIR_EXECUTION_THRESHOLD_WARNING: int = _safe_int(
    "REPAIR_EXECUTION_THRESHOLD_WARNING", 10, min_val=1, max_val=150
)

SLO_UPTIME_TARGET: float = _safe_float("SLO_UPTIME_TARGET", 0.995, min_val=0.9, max_val=1.0)
SLO_RESPONSE_TIME_MS: int = _safe_int("SLO_RESPONSE_TIME_MS", 500, min_val=100, max_val=5000)
SLO_ERROR_RATE_PERCENT: float = _safe_float("SLO_ERROR_RATE_PERCENT", 0.1, min_val=0.0, max_val=5.0)

# ============================================================
# Alert Rules Configuration
# ============================================================
ALERT_RULES_ENABLED: bool = _safe_bool("ALERT_RULES_ENABLED", True)
ALERT_RULES_FILE: str = os.getenv("ALERT_RULES_FILE", "config/alert_rules.yml")

DEFAULT_ALERT_RULES: dict[str, Any] = {
    "cpu_high": {
        "enabled": True,
        "threshold": 90.0,
        "severity": "warning",
        "duration_seconds": 300,
        "description": "CPU usage exceeds threshold",
    },
    "cpu_critical": {
        "enabled": True,
        "threshold": 95.0,
        "severity": "critical",
        "duration_seconds": 60,
        "description": "CPU usage critically high",
    },
    "memory_high": {
        "enabled": True,
        "threshold": 85.0,
        "severity": "warning",
        "duration_seconds": 300,
        "description": "Memory usage exceeds threshold",
    },
    "memory_critical": {
        "enabled": True,
        "threshold": 95.0,
        "severity": "critical",
        "duration_seconds": 60,
        "description": "Memory usage critically high",
    },
    "disk_high": {
        "enabled": True,
        "threshold": 90.0,
        "severity": "warning",
        "duration_seconds": 600,
        "description": "Disk usage exceeds threshold",
    },
    "disk_critical": {
        "enabled": True,
        "threshold": 98.0,
        "severity": "critical",
        "duration_seconds": 300,
        "description": "Disk usage critically high",
    },
    "api_error_rate": {
        "enabled": True,
        "threshold": 5.0,
        "severity": "warning",
        "duration_seconds": 300,
        "description": "API error rate exceeds threshold",
    },
    "response_time": {
        "enabled": True,
        "threshold": 1000,
        "severity": "warning",
        "duration_seconds": 300,
        "description": "API response time exceeds threshold",
    },
}

ALERT_NOTIFICATION_CHANNELS: list[str] = os.getenv(
    "ALERT_NOTIFICATION_CHANNELS", "email,webhook"
).split(",")

ALERT_AGGREGATION_ENABLED: bool = _safe_bool("ALERT_AGGREGATION_ENABLED", True)
ALERT_AGGREGATION_INTERVAL_SECONDS: int = _safe_int(
    "ALERT_AGGREGATION_INTERVAL_SECONDS", 60, min_val=10, max_val=600
)
ALERT_AGGREGATION_MAX_PER_INTERVAL: int = _safe_int(
    "ALERT_AGGREGATION_MAX_PER_INTERVAL", 10, min_val=1, max_val=100
)

# ============================================================
# Database Replication Configuration
# ============================================================
DB_REPLICATION_ENABLED: bool = _safe_bool("DB_REPLICATION_ENABLED", False)
DB_READ_WRITE_SPLITTING: bool = _safe_bool("DB_READ_WRITE_SPLITTING", False)
DB_FAILOVER_ENABLED: bool = _safe_bool("DB_FAILOVER_ENABLED", False)
DB_FAILOVER_TIMEOUT_SECONDS: int = _safe_int(
    "DB_FAILOVER_TIMEOUT_SECONDS", 30, min_val=5, max_val=300
)
DB_HEALTH_CHECK_INTERVAL_SECONDS: int = _safe_int(
    "DB_HEALTH_CHECK_INTERVAL_SECONDS", 10, min_val=1, max_val=60
)

DB_PRIMARY_HOST: str = os.getenv("DB_PRIMARY_HOST", "localhost")
DB_PRIMARY_PORT: int = _safe_int("DB_PRIMARY_PORT", 5432, min_val=1, max_val=65535)
DB_PRIMARY_DATABASE: str = os.getenv("DB_PRIMARY_DATABASE", "aiops")
DB_PRIMARY_USERNAME: str = os.getenv("DB_PRIMARY_USERNAME", "aiops")
DB_PRIMARY_PASSWORD: str = os.getenv("DB_PRIMARY_PASSWORD", "")

DB_REPLICA_HOSTS: str = os.getenv("DB_REPLICA_HOSTS", "")
DB_REPLICA_PORT: int = _safe_int("DB_REPLICA_PORT", 5432, min_val=1, max_val=65535)

# ============================================================
# Redis Cluster Configuration
# ============================================================
REDIS_CLUSTER_ENABLED: bool = _safe_bool("REDIS_CLUSTER_ENABLED", False)
REDIS_MODE: str = os.getenv("REDIS_MODE", "standalone")
REDIS_NODES: str = os.getenv("REDIS_NODES", "")
REDIS_SENTINEL_MASTER_NAME: str = os.getenv("REDIS_SENTINEL_MASTER_NAME", "mymaster")
REDIS_SENTINELS: str = os.getenv("REDIS_SENTINELS", "")
REDIS_CONNECTION_POOL_SIZE: int = _safe_int(
    "REDIS_CONNECTION_POOL_SIZE", 10, min_val=1, max_val=100
)
REDIS_CONNECTION_TIMEOUT_SECONDS: int = _safe_int(
    "REDIS_CONNECTION_TIMEOUT_SECONDS", 5, min_val=1, max_val=30
)
REDIS_SOCKET_TIMEOUT_SECONDS: int = _safe_int(
    "REDIS_SOCKET_TIMEOUT_SECONDS", 5, min_val=1, max_val=30
)
REDIS_RETRY_ON_TIMEOUT: bool = _safe_bool("REDIS_RETRY_ON_TIMEOUT", True)
REDIS_MAX_RETRIES: int = _safe_int("REDIS_MAX_RETRIES", 3, min_val=0, max_val=10)

# ============================================================
# Backup Strategy Configuration
# ============================================================
BACKUP_ENABLED: bool = _safe_bool("BACKUP_ENABLED", False)
BACKUP_INTERVAL_HOURS: int = _safe_int("BACKUP_INTERVAL_HOURS", 24, min_val=1, max_val=168)
BACKUP_RETENTION_DAYS: int = _safe_int("BACKUP_RETENTION_DAYS", 30, min_val=1, max_val=365)
BACKUP_LOCATION: str = os.getenv("BACKUP_LOCATION", "/backups")
BACKUP_COMPRESSION_ENABLED: bool = _safe_bool("BACKUP_COMPRESSION_ENABLED", True)
BACKUP_ENCRYPTION_ENABLED: bool = _safe_bool("BACKUP_ENCRYPTION_ENABLED", False)
BACKUP_TYPES: str = os.getenv("BACKUP_TYPES", "database,config,logs")

# ============================================================
# Database Optimization Configuration
# ============================================================
DB_OPTIMIZATION_ENABLED: bool = _safe_bool("DB_OPTIMIZATION_ENABLED", False)
DB_CONNECTION_POOL_SIZE: int = _safe_int("DB_CONNECTION_POOL_SIZE", 20, min_val=1, max_val=100)
DB_MAX_OVERFLOW: int = _safe_int("DB_MAX_OVERFLOW", 10, min_val=0, max_val=50)
DB_POOL_TIMEOUT: int = _safe_int("DB_POOL_TIMEOUT", 30, min_val=1, max_val=300)
DB_POOL_RECYCLE: int = _safe_int("DB_POOL_RECYCLE", 3600, min_val=60, max_val=86400)
DB_QUERY_CACHE_ENABLED: bool = _safe_bool("DB_QUERY_CACHE_ENABLED", True)
DB_QUERY_CACHE_SIZE: int = _safe_int("DB_QUERY_CACHE_SIZE", 1000, min_val=100, max_val=10000)
DB_SLOW_QUERY_THRESHOLD_SECONDS: float = _safe_float(
    "DB_SLOW_QUERY_THRESHOLD_SECONDS", 1.0, min_val=0.1, max_val=10.0
)
DB_INDEX_OPTIMIZATION_ENABLED: bool = _safe_bool("DB_INDEX_OPTIMIZATION_ENABLED", True)
DB_AUTO_VACUUM_ENABLED: bool = _safe_bool("DB_AUTO_VACUUM_ENABLED", True)

# ============================================================
# Caching Strategy Configuration (Enhanced)
# ============================================================
CACHE_ENABLED: bool = _safe_bool("CACHE_ENABLED", True)
CACHE_DEFAULT_TTL_SECONDS: int = _safe_int(
    "CACHE_DEFAULT_TTL_SECONDS", 300, min_val=10, max_val=86400
)
CACHE_MAX_SIZE: int = _safe_int("CACHE_MAX_SIZE", 10000, min_val=100, max_val=100000)
CACHE_BACKEND: str = os.getenv("CACHE_BACKEND", "memory")
CACHE_KEY_PREFIX: str = os.getenv("CACHE_KEY_PREFIX", "aiops")
CACHE_COMPRESSION_ENABLED: bool = _safe_bool("CACHE_COMPRESSION_ENABLED", False)
CACHE_SERIALIZATION_FORMAT: str = os.getenv("CACHE_SERIALIZATION_FORMAT", "json")

# ============================================================
# P2 Performance Optimization Configuration
# ============================================================
# API Performance Configuration
SLOW_API_THRESHOLD_MS: int = _safe_int("SLOW_API_THRESHOLD_MS", 500, min_val=100, max_val=5000)
UVICORN_WORKERS: int = _safe_int("UVICORN_WORKERS", 4, min_val=1, max_val=16)
UVICORN_HOST: str = os.getenv("UVICORN_HOST", "0.0.0.0").strip()
UVICORN_PORT: int = _safe_int("UVICORN_PORT", 8000, min_val=1024, max_val=65535)

# Redis Configuration Optimization
REDIS_SOCKET_TIMEOUT: int = _safe_int("REDIS_SOCKET_TIMEOUT", 5, min_val=1, max_val=30)
REDIS_SOCKET_CONNECT_TIMEOUT: int = _safe_int(
    "REDIS_SOCKET_CONNECT_TIMEOUT", 5, min_val=1, max_val=30
)

# Cache Performance Optimization
CACHE_L1_ENABLED: bool = _safe_bool("CACHE_L1_ENABLED", True)  # Memory cache
CACHE_L2_ENABLED: bool = _safe_bool("CACHE_L2_ENABLED", True)  # Redis cache
CACHE_L3_ENABLED: bool = _safe_bool("CACHE_L3_ENABLED", True)  # Database cache
CACHE_PREHEAT_ENABLED: bool = _safe_bool("CACHE_PREHEAT_ENABLED", False)
CACHE_EVICTION_POLICY: str = os.getenv("CACHE_EVICTION_POLICY", "lru").strip()

# Performance Monitoring
PERFORMANCE_MONITORING_ENABLED: bool = _safe_bool("PERFORMANCE_MONITORING_ENABLED", True)
PERFORMANCE_SAMPLE_RATE: float = _safe_float(
    "PERFORMANCE_SAMPLE_RATE", 0.1, min_val=0.01, max_val=1.0
)
PERFORMANCE_ALERT_ENABLED: bool = _safe_bool("PERFORMANCE_ALERT_ENABLED", True)


# ============================================================
# Configuration Validation
# ============================================================
def validate_config() -> Dict[str, Any]:
    """
    Validate configuration completeness and correctness.
    Returns a dictionary with validation results.
    """
    validation_results: dict[str, Any] = {
        "is_valid": True,
        "errors": [],
        "warnings": [],
        "info": [],
    }

    environment = os.getenv("ENVIRONMENT", "development")

    # Security validation for production
    if environment == "production":
        # Check JWT secret key
        if JWT_SECRET_KEY == "dev-secret-key-change-me-in-production":
            validation_results["errors"].append(
                "JWT_SECRET_KEY is using default value in production environment"
            )
            validation_results["is_valid"] = False

        # Check PostgreSQL password
        if POSTGRES_PASSWORD in ("", "postgres"):
            validation_results["errors"].append(
                "POSTGRES_PASSWORD is using default/empty value in production environment"
            )
            validation_results["is_valid"] = False

        # Check internal API key
        if not INTERNAL_API_KEY:
            validation_results["warnings"].append(
                "INTERNAL_API_KEY is not set in production environment"
            )

    # Database connectivity validation
    try:
        # Validate PostgreSQL URL format
        if not POSTGRES_URL.startswith(("postgresql://", "postgresql+asyncpg://")):
            validation_results["errors"].append(f"Invalid POSTGRES_URL format: {POSTGRES_URL}")
            validation_results["is_valid"] = False
    except Exception as e:
        validation_results["errors"].append(f"Error validating POSTGRES_URL: {str(e)}")
        validation_results["is_valid"] = False

    # Redis configuration validation
    if REDIS_PASSWORD and REDIS_MODE == "standalone":
        validation_results["info"].append("Redis password is configured for standalone mode")

    if REDIS_CLUSTER_ENABLED and not REDIS_NODES:
        validation_results["errors"].append(
            "REDIS_CLUSTER_ENABLED is True but REDUS_NODES is not configured"
        )
        validation_results["is_valid"] = False

    # AI configuration validation
    if AI_CONFIG["is_enabled"]:
        if not AI_CONFIG["api_key"]:
            validation_results["warnings"].append(
                "AI_ENABLED is True but AI_API_KEY is not configured, service will degrade to rule engine"  # noqa: E501
            )
        else:
            validation_results["info"].append("AI configuration is properly set up")

    # LLM Router validation
    if not LLM_ROUTER_MODELS:
        validation_results["errors"].append("LLM_ROUTER_MODELS is empty")
        validation_results["is_valid"] = False

    # L4 Storage Layer validation
    l4_enabled_count = sum([VICTORIAMETRICS_ENABLED, LOKI_ENABLED, TEMPO_ENABLED])

    if l4_enabled_count == 0:
        validation_results["warnings"].append(
            "No L4 storage backends are enabled (VictoriaMetrics, Loki, Tempo)"
        )
    else:
        validation_results["info"].append(f"{l4_enabled_count} L4 storage backend(s) enabled")

    # L2 Analysis Layer validation
    if LANGGRAPH_ENABLED and not RAG_ENABLED:
        validation_results["warnings"].append("LANGGRAPH_ENABLED is True but RAG_ENABLED is False")

    # Integration validation
    if L7_INTEGRATION_CONFIG["itsm"]["servicenow"]["enabled"]:
        if not all([SERVICENOW_INSTANCE, SERVICENOW_USERNAME, SERVICENOW_PASSWORD]):
            validation_results["errors"].append(
                "SERVICENOW_ENABLED is True but required credentials are missing"
            )
            validation_results["is_valid"] = False

    if L7_INTEGRATION_CONFIG["itsm"]["jira"]["enabled"]:
        if not all([JIRA_URL, JIRA_USERNAME, JIRA_API_TOKEN]):
            validation_results["errors"].append(
                "JIRA_ENABLED is True but required credentials are missing"
            )
            validation_results["is_valid"] = False

    # Collaboration tools validation
    if SLACK_ENABLED and not SLACK_BOT_TOKEN:
        validation_results["warnings"].append(
            "SLACK_ENABLED is True but SLACK_BOT_TOKEN is not configured"
        )

    if TEAMS_ENABLED and not TEAMS_WEBHOOK:
        validation_results["warnings"].append(
            "TEAMS_ENABLED is True but TEAMS_WEBHOOK is not configured"
        )

    # Kafka validation
    if not KAFKA_BROKERS:
        validation_results["warnings"].append("KAFKA_BROKERS is empty")

    # Flink validation
    if FLINK_CONFIG["enable_state_backend"] and not FLINK_CONFIG["state_backend"]:
        validation_results["errors"].append(
            "FLINK_ENABLE_STATE_BACKEND is True but FLINK_STATE_BACKEND is not configured"
        )
        validation_results["is_valid"] = False

    # Langfuse validation
    if LANGFUSE_CONFIG["is_enabled"]:
        if not all([LANGFUSE_CONFIG["public_key"], LANGFUSE_CONFIG["secret_key"]]):
            validation_results["warnings"].append(
                "LANGFUSE_ENABLED is True but required keys are missing, tracking will be disabled"
            )

    # Database replication validation
    if DB_REPLICATION_ENABLED:
        if not DB_REPLICA_HOSTS:
            validation_results["warnings"].append(
                "DB_REPLICATION_ENABLED is True but DB_REPLICA_HOSTS is not configured"
            )

    # Backup validation
    if BACKUP_ENABLED:
        if not BACKUP_LOCATION:
            validation_results["errors"].append(
                "BACKUP_ENABLED is True but BACKUP_LOCATION is not configured"
            )
            validation_results["is_valid"] = False

    # Port validation
    ports_to_check = {
        "REDIS_PORT": REDIS_PORT,
        "POSTGRES_PORT": POSTGRES_PORT,
        "QDRANT_PORT": QDRANT_PORT,
        "LOKI_PORT": LOKI_PORT,
        "ELASTICSEARCH_PORT": ELASTICSEARCH_PORT,
        "DATAHUB_PORT": DATAHUB_PORT,
        "VICTORIAMETRICS_PORT": VICTORIAMETRICS_PORT,
        "TEMPO_PORT": TEMPO_PORT,
    }

    for port_name, port_value in ports_to_check.items():
        if not (1 <= port_value <= 65535):
            validation_results["errors"].append(f"{port_name} has invalid value: {port_value}")
            validation_results["is_valid"] = False

    # Log validation results
    if validation_results["errors"]:
        for error in validation_results["errors"]:
            logger.error(f"[config validation] ERROR: {error}")

    if validation_results["warnings"]:
        for warning in validation_results["warnings"]:
            logger.info(f"[config validation] WARNING: {warning}")

    if validation_results["info"]:
        for info in validation_results["info"]:
            logger.info(f"[config validation] INFO: {info}")

    if validation_results["is_valid"]:
        logger.info("[config validation] Configuration validation passed")
    else:
        logger.error("[config validation] Configuration validation failed")

    return validation_results


# Auto-validate configuration on import
if os.getenv("CONFIG_VALIDATION_ENABLED", "true").lower() in ("true", "1", "yes"):
    validate_config()


# ============================================================
# Configuration Documentation Generator
# ============================================================
def generate_config_documentation() -> str:
    """
    Generate comprehensive configuration documentation.
    Returns a markdown string with all configuration items.
    """
    doc_lines = [
        "# AIOps Agent Configuration Documentation",
        "",
        "This document describes all configuration items in the AIOps Agent system.",
        "",
        "## Table of Contents",
        "",
        "- [Environment Variables](#environment-variables)",
        "- [Core Configuration](#core-configuration)",
        "- [Database Configuration](#database-configuration)",
        "- [AI Configuration](#ai-configuration)",
        "- [Monitoring Configuration](#monitoring-configuration)",
        "- [Security Configuration](#security-configuration)",
        "- [Integration Configuration](#integration-configuration)",
        "- [Performance Configuration](#performance-configuration)",
        "",
        "## Environment Variables",
        "",
        "The following environment variables can be used to override default values:",
        "",
        "### Core Environment Variables",
        "",
        "| Variable | Description | Default | Required in Production |",
        "|----------|-------------|---------|------------------------|",
        "| `ENVIRONMENT` | Runtime environment (development/production) | `development` | No |",
        "| `CONFIG_VALIDATION_ENABLED` | Enable configuration validation on import | `true` | No |",
        "",
        "### Security Environment Variables",
        "",
        "| Variable | Description | Default | Required in Production |",
        "|----------|-------------|---------|------------------------|",
        (  # noqa: E501
            "| `JWT_SECRET_KEY` | Secret key for JWT token signing |"
            " `dev-secret-key-change-me-in-production` | **Yes** |"
        ),
        "| `JWT_ALGORITHM` | JWT signing algorithm | `HS256` | No |",
        "| `JWT_ACCESS_EXPIRE_MINUTES` | JWT token expiration time in minutes | `30` | No |",
        "| `JWT_ISSUER` | JWT token issuer | `aiops-agent` | No |",
        "| `JWT_AUDIENCE` | JWT token audience | `aiops-api` | No |",
        "| `BCRYPT_ROUNDS` | Number of rounds for bcrypt password hashing | `12` | No |",
        "| `INTERNAL_API_KEY` | API key for protected endpoints | `` | Recommended |",
        "",
        "### Database Environment Variables",
        "",
        "| Variable | Description | Default | Required in Production |",
        "|----------|-------------|---------|------------------------|",
        "| `POSTGRES_HOST` | PostgreSQL database host | `localhost` | No |",
        "| `POSTGRES_PORT` | PostgreSQL database port | `5432` | No |",
        "| `POSTGRES_USER` | PostgreSQL database user | `postgres` | No |",
        "| `POSTGRES_PASSWORD` | PostgreSQL database password | `postgres` | **Yes** |",
        "| `POSTGRES_DB` | PostgreSQL database name | `aiops` | No |",
        "| `REDIS_HOST` | Redis server host | `localhost` | No |",
        "| `REDIS_PORT` | Redis server port | `6379` | No |",
        "| `REDIS_PASSWORD` | Redis server password | `` | Recommended |",
        "| `REDIS_MODE` | Redis mode (standalone/cluster/sentinel) | `standalone` | No |",
        "| `REDIS_CLUSTER_ENABLED` | Enable Redis cluster mode | `False` | No |",
        "| `REDIS_NODES` | Redis cluster nodes (comma-separated) | `` | Conditional |",
        "| `REDIS_SENTINELS` | Redis sentinel nodes (comma-separated) | `` | Conditional |",
        "| `REDIS_SENTINEL_MASTER_NAME` | Redis sentinel master name | `mymaster` | Conditional |",
        "",
        "### AI Environment Variables",
        "",
        "| Variable | Description | Default | Required in Production |",
        "|----------|-------------|---------|------------------------|",
        "| `AI_ENABLED` | Enable AI engine | `False` | No |",
        "| `AI_API_KEY` | AI service API key | `` | Conditional |",
        "| `AI_BASE_URL` | AI service base URL | `https://api.minimaxi.com/v1` | No |",
        "| `AI_MODEL` | AI model name | `MiniMax-Text-01` | No |",
        "| `AI_TIMEOUT` | AI request timeout in seconds | `30` | No |",
        "| `AI_MAX_RETRIES` | Maximum number of AI request retries | `2` | No |",
        "| `AI_RICH_CONTEXT_TIMEOUT_SEC` | AI rich context timeout in seconds | `2.0` | No |",
        "",
        "### Monitoring Environment Variables",
        "",
        "| Variable | Description | Default | Required in Production |",
        "|----------|-------------|---------|------------------------|",
        "| `LOKI_ENABLED` | Enable Loki log aggregation | `False` | No |",
        "| `LOKI_HOST` | Loki server host | `localhost` | Conditional |",
        "| `LOKI_PORT` | Loki server port | `3100` | Conditional |",
        "| `VICTORIAMETRICS_ENABLED` | Enable VictoriaMetrics | `False` | No |",
        "| `VICTORIAMETRICS_HOST` | VictoriaMetrics host | `localhost` | Conditional |",
        "| `VICTORIAMETRICS_PORT` | VictoriaMetrics port | `8428` | Conditional |",
        "| `TEMPO_ENABLED` | Enable Tempo tracing | `False` | No |",
        "| `TEMPO_HOST` | Tempo host | `localhost` | Conditional |",
        "| `TEMPO_PORT` | Tempo port | `3200` | Conditional |",
        "| `LANGFUSE_ENABLED` | Enable Langfuse LLM observability | `False` | No |",
        "| `LANGFUSE_PUBLIC_KEY` | Langfuse public key | `` | Conditional |",
        "| `LANGFUSE_SECRET_KEY` | Langfuse secret key | `` | Conditional |",
        "| `LANGFUSE_HOST` | Langfuse host URL | `https://cloud.langfuse.com` | Conditional |",
        "",
        "### Integration Environment Variables",
        "",
        "| Variable | Description | Default | Required in Production |",
        "|----------|-------------|---------|------------------------|",
        "| `SERVICENOW_ENABLED` | Enable ServiceNow integration | `False` | No |",
        "| `SERVICENOW_INSTANCE` | ServiceNow instance name | `` | Conditional |",
        "| `SERVICENOW_USERNAME` | ServiceNow username | `` | Conditional |",
        "| `SERVICENOW_PASSWORD` | ServiceNow password | `` | Conditional |",
        "| `JIRA_ENABLED` | Enable Jira integration | `False` | No |",
        "| `JIRA_URL` | Jira server URL | `` | Conditional |",
        "| `JIRA_USERNAME` | Jira username | `` | Conditional |",
        "| `JIRA_API_TOKEN` | Jira API token | `` | Conditional |",
        "| `SLACK_ENABLED` | Enable Slack integration | `False` | No |",
        "| `SLACK_BOT_TOKEN` | Slack bot token | `` | Conditional |",
        "| `SLACK_SIGNING_SECRET` | Slack signing secret | `` | Conditional |",
        "| `SLACK_DEFAULT_CHANNEL` | Default Slack channel | `#aiops-alerts` | Conditional |",
        "| `TEAMS_ENABLED` | Enable Microsoft Teams integration | `False` | No |",
        "| `TEAMS_WEBHOOK` | Teams webhook URL | `` | Conditional |",
        "| `TEAMS_CHANNEL` | Teams channel | `aiops-alerts` | Conditional |",
        "",
        "### Performance Environment Variables",
        "",
        "| Variable | Description | Default | Required in Production |",
        "|----------|-------------|---------|------------------------|",
        "| `CACHE_ENABLED` | Enable caching | `True` | No |",
        "| `CACHE_BACKEND` | Cache backend (memory/redis) | `memory` | No |",
        "| `CACHE_DEFAULT_TTL_SECONDS` | Default cache TTL in seconds | `3600` | No |",
        "| `CACHE_MAX_SIZE` | Maximum cache size | `10000` | No |",
        "| `CACHE_COMPRESSION_ENABLED` | Enable cache compression | `False` | No |",
        "| `CACHE_SERIALIZATION_FORMAT` | Cache serialization format | `json` | No |",
        "",
        "### Rate Limiting Environment Variables",
        "",
        "| Variable | Description | Default | Required in Production |",
        "|----------|-------------|---------|------------------------|",
        "| `RATE_LIMIT_ENABLED` | Enable rate limiting | `True` | No |",
        "| `RATE_LIMIT_PER_MINUTE` | Requests per minute limit | `60` | No |",
        "| `RATE_LIMIT_PER_HOUR` | Requests per hour limit | `1000` | No |",
        "| `RATE_LIMIT_PER_DAY` | Requests per day limit | `10000` | No |",
        "",
        "## Configuration Sections",
        "",
        "### Core Configuration",
        "",
        "Core configuration includes basic system settings like environment detection,",
        "proxy settings, and internal API keys.",
        "",
        "### Database Configuration",
        "",
        "Database configuration covers PostgreSQL, Redis, Qdrant (vector database),",
        "and Elasticsearch settings with support for replication, clustering, and",
        "high availability.",
        "",
        "### AI Configuration",
        "",
        "AI configuration includes LLM routing, RAG (Retrieval-Augmented Generation),",
        "LangGraph workflows, and model cost optimization settings.",
        "",
        "### Monitoring Configuration",
        "",
        "Monitoring configuration includes Loki (logs), VictoriaMetrics (metrics),",
        "Tempo (tracing), and OpenTelemetry settings for comprehensive observability.",
        "",
        "### Security Configuration",
        "",
        "Security configuration includes JWT authentication, password hashing, CORS,",
        "rate limiting, and HTTPS/TLS settings.",
        "",
        "### Integration Configuration",
        "",
        "Integration configuration includes ITSM systems (ServiceNow, Jira) and",
        "collaboration tools (Slack, Microsoft Teams) for alerting and incident management.",
        "",
        "### Performance Configuration",
        "",
        "Performance configuration includes caching strategies, database optimization,",
        "backup strategies, and connection pooling settings.",
        "",
        "## 7-Layer Architecture Configuration",
        "",
        "The system follows a 7-layer architecture with specific configuration for each layer:",
        "",
        "- **L1 - Data Collection**: System metrics, logs, and traces collection",
        "- **L2 - Analysis Layer**: Anomaly detection, RAG, and LangGraph analysis",
        "- **L3 - Processing Layer**: Causal graph analysis and workflow execution",
        "- **L4 - Storage Layer**: Multi-backend storage with fallback mechanisms",
        "- **L5 - Priority Layer**: Resource allocation and SLA-aware scheduling",
        "- **L6 - Interface Layer**: MCP interface for external integrations",
        "- **L7 - Application Layer**: FastAPI REST API and frontend",
        "",
        "## Security Best Practices",
        "",
        "1. **Always override default passwords** in production environments",
        "2. **Use strong JWT secret keys** (at least 32 characters)",
        "3. **Enable HTTPS/TLS** in production",
        "4. **Configure rate limiting** to prevent abuse",
        "5. **Use environment variables** for sensitive data",
        "6. **Regularly rotate API keys** and credentials",
        "7. **Enable audit logging** for security-sensitive operations",
        "",
        "## Configuration Validation",
        "",
        "The system includes automatic configuration validation that checks:",
        "",
        "- Required production environment variables",
        "- Configuration value validity (ports, URLs, etc.)",
        "- Dependency relationships between configuration items",
        "- Security best practices compliance",
        "",
        "To disable automatic validation, set `CONFIG_VALIDATION_ENABLED=false`.",
        "",
        "## Getting Help",
        "",
        "For more information about configuration, see:",
        "- Architecture documentation: `docs/ARCHITECTURE.md`",
        "- Deployment guide: `docs/DEPLOYMENT.md`",
        "- API documentation: `docs/API.md`",
        "",
        "---",
        "",
        (  # noqa: E501
            "*This documentation is automatically generated by"
            " `config.generate_config_documentation()`*"
        ),
        "*Last updated: " + str(__import__("datetime").datetime.now()) + "*",
    ]

    return "\n".join(doc_lines)


def save_config_documentation(output_path: str = "CONFIG_DOCUMENTATION.md") -> None:
    """
    Save configuration documentation to a file.

    Args:
        output_path: Path to save the documentation file
    """
    documentation = generate_config_documentation()
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(documentation)
    logger.info(f"[config] Configuration documentation saved to {output_path}")


# ============================================================
# Configuration Hot Reload Support
# ============================================================

if WATCHDOG_AVAILABLE:

    class ConfigReloadHandler(FileSystemEventHandler):
        """Handler for configuration file changes."""

        def __init__(self, config_module_name: str = "config"):
            self.config_module_name = config_module_name
            self.last_reload_time = 0.0
            self.reload_cooldown = 2.0  # seconds
            self.reload_callback = None

        def set_reload_callback(self, callback):
            """Set callback function to be called on config reload."""
            self.reload_callback = callback

        def on_modified(self, event):
            """Handle file modification events."""
            if event.src_path.endswith("config.py"):
                current_time = time.time()
                if current_time - self.last_reload_time < self.reload_cooldown:
                    return  # Skip reloads within cooldown period

                self.last_reload_time = current_time
                logger.info(
                    "[config hot-reload] Detected config.py modification, attempting reload..."
                )

                try:
                    self.reload_config()
                except Exception as e:
                    logger.error(f"[config hot-reload] Failed to reload config: {str(e)}")

        def reload_config(self):
            """Reload the configuration module."""
            try:
                # Reload the config module
                config_module = importlib.import_module(self.config_module_name)
                importlib.reload(config_module)

                logger.info("[config hot-reload] Configuration reloaded successfully")

                # Call callback if set
                if self.reload_callback:
                    self.reload_callback()

            except Exception as e:
                logger.error(f"[config hot-reload] Error during config reload: {str(e)}")

else:

    class ConfigReloadHandler:  # type: ignore[no-redef]
        """Stub handler when watchdog is not available."""

        def __init__(self, config_module_name: str = "config"):
            logger.warning("[config hot-reload] Watchdog not available, hot reload disabled")

        def set_reload_callback(self, callback):
            """Stub method."""


_config_reload_observer = None
_config_reload_handler = None


def enable_config_hot_reload(callback=None):
    """
    Enable configuration hot reload support.

    Args:
        callback: Optional callback function to be called after successful reload
    """
    global _config_reload_observer, _config_reload_handler

    if not WATCHDOG_AVAILABLE:
        logger.warning("[config hot-reload] Watchdog not available, hot reload disabled")
        return

    if _config_reload_observer is not None:
        logger.warning("[config hot-reload] Hot reload already enabled")
        return

    if not _safe_bool("CONFIG_HOT_RELOAD_ENABLED", default=False):
        logger.info("[config hot-reload] Hot reload disabled via CONFIG_HOT_RELOAD_ENABLED")
        return

    try:
        # Create observer and handler
        _config_reload_handler = ConfigReloadHandler()
        if callback:
            _config_reload_handler.set_reload_callback(callback)

        _config_reload_observer = Observer()
        _config_reload_observer.schedule(
            _config_reload_handler, path=str(BASE_DIR), recursive=False
        )

        # Start observer
        _config_reload_observer.start()
        logger.info("[config hot-reload] Configuration hot reload enabled")

    except Exception as e:
        logger.error(f"[config hot-reload] Failed to enable hot reload: {str(e)}")


def disable_config_hot_reload():
    """Disable configuration hot reload support."""
    global _config_reload_observer, _config_reload_handler

    if _config_reload_observer is not None:
        _config_reload_observer.stop()
        _config_reload_observer.join()
        _config_reload_observer = None
        _config_reload_handler = None
        logger.info("[config hot-reload] Configuration hot reload disabled")


def is_config_hot_reload_enabled() -> bool:
    """Check if configuration hot reload is currently enabled."""
    return _config_reload_observer is not None


# Auto-enable hot reload if configured
if _safe_bool("CONFIG_HOT_RELOAD_ENABLED", default=False):
    enable_config_hot_reload()


# Backward-compatible alias for code/tests expecting a Config class.
from core.config_manager import ConfigManager as Config  # noqa: F401
