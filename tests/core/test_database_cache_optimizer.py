# -*- coding: utf-8 -*-
"""Tests for core/database_cache_optimizer.py."""

import time  # noqa: F401  # Imported for test setup

from core.database_cache_optimizer import (
    DatabaseCacheOptimizer,
    get_database_cache_optimizer,
)


def test_optimizer_factory():
    opt = get_database_cache_optimizer({"default_cache_size": 50})
    assert isinstance(opt, DatabaseCacheOptimizer)


def test_create_and_use_cache():
    opt = DatabaseCacheOptimizer()
    opt.create_cache("test")
    assert "test" in opt.caches

    opt.set("test", "SELECT 1", ["row"])
    assert opt.get("test", "SELECT 1") == ["row"]
    assert opt.get("missing", "SELECT 1") is None

    assert opt.invalidate("test", "SELECT 1") == 1
    assert opt.invalidate("test", "SELECT 1") == 0


def test_cache_expiration_and_cleanup():
    opt = DatabaseCacheOptimizer()
    opt.create_cache("exp", ttl_seconds=0.1)
    opt.set("exp", "q", "v")
    time.sleep(0.15)
    assert opt.get("exp", "q") is None
    opt.set("exp", "q", "v")
    time.sleep(0.15)
    assert opt.cleanup_expired_entries("exp") == 1


def test_get_cache():
    opt = DatabaseCacheOptimizer()
    cache = opt.get_cache("my_cache")
    cache.set("k", "v")
    assert cache.get("k") == "v"


def test_cache_metrics_and_statistics():
    opt = DatabaseCacheOptimizer()
    opt.create_cache("metrics")
    opt.set("metrics", "q", "v")
    opt.get("metrics", "q")
    opt.get("metrics", "missing")

    metrics = opt.get_cache_metrics("metrics")
    assert metrics is not None
    assert metrics.cache_name == "metrics"
    assert isinstance(opt.get_all_cache_metrics(), dict)

    stats = opt.get_statistics()
    assert "total_caches" in stats
    assert stats["total_cache_hits"] == 1

    opt.optimize_cache_size("metrics", target_hit_rate=0.95)


def test_preload_cache():
    opt = DatabaseCacheOptimizer()
    opt.create_cache("preload")
    opt.add_preload_query("preload", "SELECT 1")
    opt.add_preload_query("preload", "SELECT 2", priority=5)

    def loader(query, params):
        return {"q": query}

    assert opt.preload_cache("preload", loader) == 2

    # Preload with dict data_loader uses get_cache path
    assert opt.preload_cache("preload_dict", {"a": 1}) == 1
