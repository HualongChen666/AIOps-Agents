# -*- coding: utf-8 -*-
"""API tests for the sharding + HA routers (mounted standalone)."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.database_ha_router import router as ha_router
from api.database_sharding_router import router as sharding_router
from core.db_sharding import get_partition_manager, get_shard_manager


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(sharding_router)
    app.include_router(ha_router)
    get_shard_manager().reset()
    get_partition_manager().reset()
    return TestClient(app)


class TestShardingEndpoints:
    def test_status_unconfigured(self, client):
        resp = client.get("/api/v1/database/sharding/status")
        assert resp.status_code == 200
        assert resp.json()["configured"] is False

    def test_route_before_configure_is_conflict(self, client):
        resp = client.post("/api/v1/database/sharding/route", json={"key": "k"})
        assert resp.status_code == 409

    def test_configure_then_route(self, client):
        resp = client.post(
            "/api/v1/database/sharding/configure",
            json={"strategy": "hash", "shard_count": 4, "shard_key": "user_id", "virtual_nodes": 64},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["shard_count"] == 4

        route = client.post("/api/v1/database/sharding/route", json={"key": "user-7"})
        assert route.status_code == 200, route.text
        body = route.json()
        assert body["shard_id"].startswith("shard-")
        assert body["strategy"] == "hash"

    def test_route_batch_and_scatter(self, client):
        client.post("/api/v1/database/sharding/configure", json={"strategy": "hash", "shard_count": 3})
        batch = client.post("/api/v1/database/sharding/route/batch", json={"keys": [f"k{i}" for i in range(300)]})
        assert batch.status_code == 200
        assert sum(batch.json()["distribution"].values()) == 300

        scatter = client.post("/api/v1/database/sharding/scatter-plan", json={"keys": ["a", "b", "c"]})
        assert scatter.status_code == 200
        assert scatter.json()["total_keys"] == 3

    def test_add_and_remove_shard(self, client):
        client.post("/api/v1/database/sharding/configure", json={"strategy": "hash", "shard_count": 2})
        add = client.post("/api/v1/database/sharding/shards", json={"shard_id": "shard-x", "name": "shard-x"})
        assert add.status_code == 200, add.text
        listing = client.get("/api/v1/database/sharding/shards")
        assert listing.json()["shard_count"] == 3
        remove = client.delete("/api/v1/database/sharding/shards/shard-x")
        assert remove.status_code == 200
        missing = client.delete("/api/v1/database/sharding/shards/nope")
        assert missing.status_code == 404

    def test_rebalance(self, client):
        client.post("/api/v1/database/sharding/configure", json={"strategy": "hash", "shard_count": 3, "virtual_nodes": 32})
        resp = client.post("/api/v1/database/sharding/rebalance", json={"keys": [f"k{i}" for i in range(500)], "virtual_nodes": 128})
        assert resp.status_code == 200, resp.text
        assert resp.json()["keys_total"] == 500


class TestPostgresShardEndpoints:
    def test_plan_unconfigured(self, client):
        resp = client.get("/api/v1/database/postgresql-shard/plan")
        assert resp.status_code == 200
        assert resp.json()["configured"] is False

    def test_configure_plan_and_render_ddl(self, client):
        resp = client.post(
            "/api/v1/database/postgresql-shard/plan",
            json={
                "table": "orders", "strategy": "range", "column": "created_at", "column_type": "DATE",
                "columns": [{"name": "id", "type": "BIGINT"}, {"name": "created_at", "type": "DATE"}],
                "partitions": [
                    {"name": "orders_2024", "range_from": "2024-01-01", "range_to": "2025-01-01"},
                    {"name": "orders_2025", "range_from": "2025-01-01", "range_to": "2026-01-01"},
                ],
            },
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["partition_count"] == 2

        ddl = client.get("/api/v1/database/postgresql-shard/ddl")
        assert ddl.status_code == 200
        assert "PARTITION BY RANGE (created_at)" in ddl.json()["ddl"]

        parts = client.get("/api/v1/database/postgresql-shard/partitions")
        assert parts.json()["partition_count"] == 2

    def test_add_partition(self, client):
        client.post(
            "/api/v1/database/postgresql-shard/plan",
            json={"table": "t", "strategy": "hash", "column": "id", "partition_count": 2},
        )
        add = client.post("/api/v1/database/postgresql-shard/partitions", json={"name": "t_p9", "modulus": 2, "remainder": 1})
        # remainder 1 already exists -> overlap/duplicate -> 400
        assert add.status_code == 400

    def test_apply_requires_postgresql(self, client):
        client.post(
            "/api/v1/database/postgresql-shard/plan",
            json={"table": "t", "strategy": "hash", "column": "id", "partition_count": 2},
        )
        resp = client.post("/api/v1/database/postgresql-shard/apply", json={})
        # The app DB is SQLite -> canonical requires-backend marker.
        assert resp.status_code == 503, resp.text
        assert resp.json()["detail"]["error"] == "requires-backend"


class TestReplicationEndpoints:
    def test_status(self, client):
        resp = client.get("/api/v1/database/replication/status")
        assert resp.status_code == 200
        assert "current_primary" in resp.json()

    def test_configure(self, client):
        resp = client.post(
            "/api/v1/database/replication/configure",
            json={
                "primary": {"host": "127.0.0.1", "port": 54329},
                "replicas": [{"host": "127.0.0.1", "port": 54330}],
                "read_write_splitting": True,
                "failover_enabled": True,
            },
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["replica_count"] == 1

    def test_health_reports_real_probe(self, client):
        client.post(
            "/api/v1/database/replication/configure",
            json={"primary": {"host": "127.0.0.1", "port": 1}, "replicas": [{"host": "127.0.0.1", "port": 1}]},
        )
        resp = client.get("/api/v1/database/replication/health")
        assert resp.status_code == 200
        # An unreachable port must report 'unhealthy' - never a fabricated 'healthy'.
        assert resp.json()["health"]["primary"]["status"] == "unhealthy"


class TestFailoverEndpoints:
    def test_status(self, client):
        resp = client.get("/api/v1/database/failover/status")
        assert resp.status_code == 200

    def test_execute_without_healthy_replica_conflicts(self, client):
        client.post(
            "/api/v1/database/replication/configure",
            json={
                "primary": {"host": "127.0.0.1", "port": 1},
                "replicas": [{"host": "127.0.0.1", "port": 1}],
                "failover_enabled": True,
            },
        )
        resp = client.post("/api/v1/database/failover/execute")
        assert resp.status_code == 409, resp.text
        # The failed attempt is still recorded in the real history.
        history = client.get("/api/v1/database/failover/history")
        assert history.json()["count"] >= 1

    def test_promote_unknown_replica(self, client):
        client.post(
            "/api/v1/database/replication/configure",
            json={"primary": {"host": "h", "port": 5432}, "replicas": [], "failover_enabled": True},
        )
        resp = client.post("/api/v1/database/failover/promote", json={"replica_index": 5})
        assert resp.status_code == 404


class TestReadWriteRoutingEndpoints:
    def test_configure_and_route(self, client):
        cfg = client.post(
            "/api/v1/database/read-write-routing/configure",
            json={
                "primary_host": "primary.local", "primary_port": 5432,
                "replicas": [{"host": "replica1.local", "port": 5432}],
                "read_write_splitting_enabled": True,
                "load_balancing_method": "least_lag",
            },
        )
        assert cfg.status_code == 200, cfg.text

        read = client.post("/api/v1/database/read-write-routing/route", json={"query": "SELECT * FROM t"})
        assert read.status_code == 200
        assert read.json()["query_type"] == "read"
        assert read.json()["replica_used"] is True

        write = client.post("/api/v1/database/read-write-routing/route", json={"query": "UPDATE t SET a=1"})
        assert write.json()["query_type"] == "write"
        assert write.json()["replica_used"] is False

    def test_toggle_splitting(self, client):
        client.post("/api/v1/database/read-write-routing/configure", json={"primary_host": "h"})
        resp = client.post("/api/v1/database/read-write-routing/splitting", json={"enabled": False})
        assert resp.status_code == 200
        assert resp.json()["read_write_splitting_enabled"] is False

    def test_update_replica_state(self, client):
        client.post(
            "/api/v1/database/read-write-routing/configure",
            json={"primary_host": "h", "replicas": [{"host": "r1"}]},
        )
        resp = client.post(
            "/api/v1/database/read-write-routing/replicas/replica_0",
            json={"state": "unhealthy", "lag": 9.5},
        )
        assert resp.status_code == 200
        assert resp.json()["replicas"]["replica_0"]["state"] == "unhealthy"
        bad = client.post("/api/v1/database/read-write-routing/replicas/nope", json={"state": "healthy"})
        assert bad.status_code == 404
