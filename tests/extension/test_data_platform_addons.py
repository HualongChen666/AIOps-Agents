# -*- coding: utf-8 -*-
"""Tests for Group 2 data platform addons using mocked storage clients."""

from __future__ import annotations

import sqlite3
import sys
import types
from unittest.mock import MagicMock, patch

import pytest

from extensions.addons.infrastructure.cache_service.service import Service as CacheService
from extensions.addons.infrastructure.cache_optimization_service.service import (
    Service as CacheOptimizationService,
)
from extensions.addons.infrastructure.data_access_service.service import (
    Service as DataAccessService,
)
from extensions.addons.infrastructure.database_optimization_service.service import (
    Service as DatabaseOptimizationService,
)
from extensions.addons.infrastructure.postgresql_shard_service.service import (
    Service as PostgresqlShardService,
)
from extensions.addons.infrastructure.qdrant_shard_service.service import (
    Service as QdrantShardService,
)
from extensions.addons.infrastructure.redis_shard_service.service import (
    Service as RedisShardService,
)
from extensions.addons.infrastructure.vector_retrieval_service.service import (
    Service as VectorRetrievalService,
)

OP_PARAMS = {
    "cache_get": {"key": "test-key"},
    "cache_set": {"key": "test-key", "value": "test-value", "ttl": 60},
    "sql": {"query": "SELECT 1", "params": [], "readonly": True},
    "get_stats": {},
    "vector_create_collection": {"name": "test", "size": 128, "distance": "Cosine"},
    "vector_upsert": {
        "name": "test",
        "ids": ["1"],
        "vectors": [[0.1] * 128],
        "payloads": [{"foo": "bar"}],
    },
    "vector_search": {"name": "test", "vector": [0.1] * 128, "top": 3},
}

ADDONS = [
    ("cache_service", CacheService, {"redis_url": "redis://localhost"}),
    ("redis_shard_service", RedisShardService, {"redis_url": "redis://localhost"}),
    (
        "postgresql_shard_service",
        PostgresqlShardService,
        {"database_url": "postgresql://localhost/db"},
    ),
    (
        "qdrant_shard_service",
        QdrantShardService,
        {"qdrant_url": "http://qdrant:6333"},
    ),
    (
        "vector_retrieval_service",
        VectorRetrievalService,
        {"qdrant_url": "http://qdrant:6333"},
    ),
    (
        "cache_optimization_service",
        CacheOptimizationService,
        {"redis_url": "redis://localhost"},
    ),
    (
        "database_optimization_service",
        DatabaseOptimizationService,
        {"database_url": "postgresql://localhost/db"},
    ),
    ("data_access_service", DataAccessService, {"database_url": "sqlite:///:memory:"}),
]


def _fake_redis_module() -> types.ModuleType:
    mod = types.ModuleType("redis")

    class Redis:
        @classmethod
        def from_url(cls, url: str):
            client = MagicMock()
            client.get.return_value = b"mock-value"
            return client

    mod.Redis = Redis
    return mod


def _fake_psycopg_module(mock_conn: MagicMock) -> types.ModuleType:
    mod = types.ModuleType("psycopg")
    mod.connect = MagicMock(return_value=mock_conn)
    return mod


def _fake_httpx_module() -> types.ModuleType:
    mod = types.ModuleType("httpx")

    def _client():
        resp = MagicMock()
        resp.content = b"{}"
        resp.json.return_value = {"result": []}
        client = MagicMock()
        client.get.return_value = resp
        client.put.return_value = resp
        client.post.return_value = resp
        return client

    mod.Client = _client
    return mod


@pytest.fixture
def mock_env_and_clients(monkeypatch):
    """Enable real-execution path and provide mocked clients in sys.modules."""
    monkeypatch.setenv("INFRA_EXECUTE_ENABLED", "true")

    # Fake redis module so cache_* operations can be exercised.
    monkeypatch.setitem(sys.modules, "redis", _fake_redis_module())

    # Fake psycopg connection for SQL operations.
    mock_cur = MagicMock()
    mock_cur.fetchall.return_value = [(1,)]
    mock_cur.description = [("id",)]
    mock_cur.rowcount = 1
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cur
    monkeypatch.setitem(sys.modules, "psycopg", _fake_psycopg_module(mock_conn))

    # Fake httpx client for Qdrant vector operations.
    monkeypatch.setitem(sys.modules, "httpx", _fake_httpx_module())

    # Patch sqlite3.connect for the data-access SQLite path.
    sqlite_cur = MagicMock()
    sqlite_cur.fetchall.return_value = [{"id": 1}]
    sqlite_cur.rowcount = 1
    sqlite_conn = MagicMock()
    sqlite_conn.cursor.return_value = sqlite_cur
    sqlite_conn.total_changes = 1
    with patch("sqlite3.connect", return_value=sqlite_conn):
        yield


def _params_for(op: str, service_name: str) -> dict:
    if op in OP_PARAMS:
        return OP_PARAMS[op]
    if service_name == "cache_optimization_service":
        return {"config": {"test": 1}, "ttl": 60}
    if service_name == "database_optimization_service":
        return {"query": "SELECT 1", "params": [], "readonly": True}
    return {}


@pytest.mark.parametrize("service_name, service_cls, driver_kwargs", ADDONS)
def test_service_execute_operations(
    mock_env_and_clients, service_name, service_cls, driver_kwargs
):
    service = service_cls(dry_run=False, **driver_kwargs)
    for op in service_cls.OPERATIONS:
        params = _params_for(op, service_name)
        result = service.execute_operation(op, params)
        assert result is not None
        if op == "get_stats":
            assert isinstance(result, dict)
            assert "cache_hits" in result or "db_size" in result or "vector_count" in result
