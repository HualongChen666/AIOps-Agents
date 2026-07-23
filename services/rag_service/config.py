# -*- coding: utf-8 -*-
"""RAG service microservice configuration."""

from __future__ import annotations

try:
    from pydantic_settings import BaseSettings
except ImportError:  # pragma: no cover
    from pydantic import BaseModel as BaseSettings  # type: ignore[misc, assignment]


class RAGSettings(BaseSettings):
    """Settings for the RAG microservice."""

    service_name: str = "rag-service"
    environment: str = "development"
    log_level: str = "INFO"
    port: int = 9406
    redis_url: str = ""
    enable_prometheus: bool = True
    openai_api_key: str = ""
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    rerank_model: str = ""
    vector_dimension: int = 384
    default_top_k: int = 5
    max_batch_size: int = 64
    cache_ttl_seconds: int = 300
    retry_policy: str = "exponential"
    max_retries: int = 3
    request_timeout: float = 60.0

    class Config:  # type: ignore[misc]
        env_prefix = "RAG_SERVICE_"
        env_file = ".env"
        extra = "ignore"


settings = RAGSettings()
