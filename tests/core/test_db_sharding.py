# -*- coding: utf-8 -*-
"""Unit tests for the real sharding engine (``core.db_sharding``)."""

import pytest

from core.db_sharding import (
    ConsistentHashRing,
    PostgresPartitionManager,
    ShardManager,
    ShardingError,
    ShardingNotConfigured,
    hash_key,
    render_postgres_partition_ddl,
)


def _fresh(ns: str) -> ShardManager:
    manager = ShardManager(ns)
    manager.reset()
    return manager


class TestHashKey:
    def test_deterministic_and_stable(self):
        # Same input -> same 64-bit value, independent of PYTHONHASHSEED.
        assert hash_key("user-1") == hash_key("user-1")
        assert 0 <= hash_key("user-1") < 2**64
        assert hash_key("user-1") != hash_key("user-2")


class TestConsistentHashRing:
    def test_empty_ring_raises(self):
        ring = ConsistentHashRing(16)
        with pytest.raises(ShardingNotConfigured):
            ring.get_shard("x")

    def test_points_and_balances(self):
        ring = ConsistentHashRing(64)
        for sid in ("s0", "s1", "s2", "s3"):
            ring.add_shard(sid)
        assert ring.size == 64 * 4
        assert set(ring.owned_counts()) == {"s0", "s1", "s2", "s3"}
        # A key always maps to the same shard.
        assert ring.get_shard("k") == ring.get_shard("k")

    def test_remove_shard_removes_points(self):
        ring = ConsistentHashRing(32)
        ring.add_shard("s0")
        ring.add_shard("s1")
        ring.remove_shard("s1")
        assert ring.size == 32
        assert set(ring.owned_counts()) == {"s0"}


class TestShardManager:
    def test_not_configured(self):
        manager = _fresh("test-not-configured")
        assert manager.configured is False
        with pytest.raises(ShardingNotConfigured):
            manager.route("k")

    def test_configure_and_route_hash(self):
        manager = _fresh("test-hash")
        manager.configure(strategy="hash", shard_count=4, shard_key="id", virtual_nodes=64)
        assert manager.configured
        assert manager.status()["shard_count"] == 4
        route = manager.route("user-42")
        assert route.shard_id in {f"shard-{i}" for i in range(4)}
        # Deterministic.
        assert route.shard_id == manager.route("user-42").shard_id

    def test_route_batch_distribution_covers_all_shards(self):
        manager = _fresh("test-batch")
        manager.configure(strategy="hash", shard_count=4, virtual_nodes=128)
        result = manager.route_batch([f"k{i}" for i in range(2000)])
        assert result["total_keys"] == 2000
        assert set(result["distribution"]) == {f"shard-{i}" for i in range(4)}
        # Every key accounted for exactly once.
        assert sum(result["distribution"].values()) == 2000

    def test_modulo_strategy(self):
        manager = _fresh("test-modulo")
        manager.configure(strategy="modulo", shard_count=3)
        result = manager.route_batch([f"k{i}" for i in range(300)])
        assert set(result["distribution"]) == {"shard-0", "shard-1", "shard-2"}

    def test_range_strategy(self):
        manager = _fresh("test-range")
        manager._strategy = "range"
        manager._configured = True
        manager.add_shard({"shard_id": "r0", "name": "r0", "range_start": "0", "range_end": "100"})
        manager.add_shard({"shard_id": "r1", "name": "r1", "range_start": "100", "range_end": "200"})
        assert manager.route(42).shard_id == "r0"
        assert manager.route(150).shard_id == "r1"
        with pytest.raises(ShardingError):
            manager.route(500)  # above the highest bound

    def test_list_strategy_rejects_duplicates(self):
        manager = _fresh("test-list")
        manager._strategy = "list"
        manager._configured = True
        manager.add_shard({"shard_id": "eu", "name": "eu", "values": ["DE", "FR"]})
        with pytest.raises(ShardingError):
            manager.add_shard({"shard_id": "na", "name": "na", "values": ["FR"]})

    def test_scatter_plan_groups_by_shard(self):
        manager = _fresh("test-scatter")
        manager.configure(strategy="hash", shard_count=3)
        plan = manager.scatter_plan([f"k{i}" for i in range(100)])
        assert plan["total_keys"] == 100
        assert sum(s["count"] for s in plan["shards"]) == 100
        assert plan["fanout"] == len(plan["shards"])

    def test_rebalance_reports_real_movement(self):
        manager = _fresh("test-rebalance")
        manager.configure(strategy="hash", shard_count=3, virtual_nodes=32)
        keys = [f"k{i}" for i in range(1000)]
        result = manager.rebalance(keys=keys, virtual_nodes=256)
        assert result["virtual_nodes"] == 256
        assert result["keys_total"] == 1000
        # The ring definitely changed size, so some points must have moved.
        assert result["points_moved"] > 0
        assert 0.0 <= result["max_deviation_percent"]

    def test_rebalance_requires_hash(self):
        manager = _fresh("test-rebalance-range")
        manager._strategy = "range"
        manager._configured = True
        manager.add_shard({"shard_id": "r0", "range_start": "0", "range_end": "10"})
        with pytest.raises(ShardingError):
            manager.rebalance()

    def test_add_and_remove_shard_persist(self):
        manager = _fresh("test-persist")
        manager.configure(strategy="hash", shard_count=2, virtual_nodes=16)
        manager.add_shard({"shard_id": "shard-extra", "name": "shard-extra"})
        assert manager.status()["shard_count"] == 3
        # Reload from the persistent store -> topology survives.
        reloaded = ShardManager("test-persist")
        assert reloaded.status()["shard_count"] == 3
        reloaded.remove_shard("shard-extra")
        assert reloaded.status()["shard_count"] == 2


class TestPostgresPartitionManager:
    def test_not_configured(self):
        manager = PostgresPartitionManager("pg-not-configured")
        manager.reset()
        with pytest.raises(ShardingNotConfigured):
            manager.generate_ddl()

    def test_hash_plan_ddl(self):
        manager = PostgresPartitionManager("pg-hash")
        manager.reset()
        plan = manager.configure(
            table="orders", strategy="hash", column="customer_id",
            columns=[{"name": "id", "type": "BIGINT"}, {"name": "customer_id", "type": "BIGINT"}],
            partition_count=4,
        )
        assert plan["partition_count"] == 4
        ddl = manager.generate_ddl()
        assert "PARTITION BY HASH (customer_id)" in ddl
        assert "MODULUS 4, REMAINDER 0" in ddl
        assert "MODULUS 4, REMAINDER 3" in ddl

    def test_range_plan_overlap_rejected(self):
        manager = PostgresPartitionManager("pg-range-overlap")
        manager.reset()
        with pytest.raises(ShardingError):
            manager.configure(
                table="events", strategy="range", column="created_at",
                partitions=[
                    {"name": "e1", "range_from": "2024-01-01", "range_to": "2025-01-01"},
                    {"name": "e2", "range_from": "2024-06-01", "range_to": "2025-06-01"},
                ],
            )

    def test_list_plan_ddl(self):
        manager = PostgresPartitionManager("pg-list")
        manager.reset()
        manager.configure(
            table="customers", strategy="list", column="region",
            partitions=[
                {"name": "customers_eu", "values": ["DE", "FR"]},
                {"name": "customers_us", "values": ["US"]},
            ],
        )
        ddl = manager.generate_ddl()
        assert "PARTITION BY LIST (region)" in ddl
        assert "FOR VALUES IN ('DE', 'FR')" in ddl


class TestRenderDdl:
    def test_minimal_plan_renders_partition_key_column(self):
        ddl = render_postgres_partition_ddl(
            {
                "table": "t", "column": "id", "strategy": "hash",
                "schema": "public", "columns": [],
                "partitions": [{"name": "t_p0", "kind": "hash", "modulus": 2, "remainder": 0}],
            }
        )
        assert "id BIGINT NOT NULL" in ddl
        assert "PARTITION OF public.t" in ddl

    def test_invalid_identifier_rejected(self):
        with pytest.raises(ShardingError):
            render_postgres_partition_ddl(
                {"table": "t; DROP TABLE x", "column": "id", "strategy": "hash", "partitions": []}
            )
