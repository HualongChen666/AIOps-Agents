# -*- coding: utf-8 -*-
"""Pydantic settings for the Knowledge Graph microservice."""

from __future__ import annotations

from pydantic_settings import BaseSettings


class KnowledgeGraphSettings(BaseSettings):
    """Settings for the knowledge graph microservice."""

    service_name: str = "knowledge-graph-service"
    environment: str = "development"
    log_level: str = "INFO"
    port: int = 9409
    redis_url: str = ""
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "neo4j"
    enable_prometheus: bool = True
    embedding_dimension: int = 128
    default_cache_ttl: int = 300
    batch_size: int = 100
    request_timeout: float = 60.0
    max_query_depth: int = 5
    top_k_default: int = 10

    class Config:  # type: ignore[misc]
        env_prefix = "KNOWLEDGE_GRAPH_"


settings = KnowledgeGraphSettings()
