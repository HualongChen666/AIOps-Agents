# -*- coding: utf-8 -*-
"""Unit tests for currently uncovered core optimizer modules."""

import asyncio  # noqa: F401  # Imported for test setup
import sys  # noqa: F401  # Imported for test setup
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import psutil
import pytest  # noqa: F401  # Imported for test setup

from core.api_response_time_optimizer import (
    APIResponseTimeOptimizer,
    OptimizationLevel,
    OptimizationRecommendation,
    ResponseTimeMetrics,
    get_api_response_time_optimizer,
)
from core.api_throughput_optimizer import (
    APIThroughputOptimizer,
    BackendServer,
    LoadBalancingStrategy,
    RateLimitStrategy,
    get_api_throughput_optimizer,
)
from core.cpu_usage_optimizer import (
    CPUOptimizationAction,
    CPUSnapshot,
    CPUUsageOptimizer,
    get_cpu_usage_optimizer,
)
from core.memory_usage_optimizer import (
    MemoryAction,
    MemorySnapshot,
    MemoryUsageOptimizer,
    get_memory_usage_optimizer,
)

pytestmark = pytest.mark.core


def _cpu_percent(*args, interval=None, percpu=False, **kwargs):
    if percpu:
        return [50.0, 50.0, 50.0, 50.0]
    return 50.0


def _virtual_memory():
    return SimpleNamespace(
        total=8_000_000_000,
        used=4_000_000_000,
        available=4_000_000_000,
        percent=50.0,
    )


class _FakeNumpy:
    @staticmethod
    def array(values):
        return values

    @staticmethod
    def polyfit(x, y, deg):
        return (15.0, 0.0)


def test_api_throughput_optimizer():
    opt = get_api_throughput_optimizer({})
    assert isinstance(opt, APIThroughputOptimizer)

    opt.set_rate_limit("token", 10.0, 20, RateLimitStrategy.TOKEN_BUCKET)
    opt.rate_limit_state["token"]["tokens"] = 100
    assert opt.check_rate_limit("token") is True

    opt.set_rate_limit("slide", 1.0, 10, RateLimitStrategy.SLIDING_WINDOW)
    assert opt.check_rate_limit("slide") is True

    opt.set_rate_limit("fixed", 10.0, 10, RateLimitStrategy.FIXED_WINDOW)
    assert opt.check_rate_limit("fixed") is True

    assert opt.check_rate_limit("unlimited") is True

    opt.add_backend_server("s1", "host1", 8080, weight=2, max_connections=100)
    opt.add_backend_server("s2", "host2", 8081, weight=1, max_connections=100)

    server = opt.get_backend_server()
    assert isinstance(server, BackendServer)
    assert server.server_id == "s1"

    server = opt.get_backend_server()
    assert server.server_id == "s2"

    opt.backend_servers[0].current_connections = 5
    opt.load_balancing_strategy = LoadBalancingStrategy.LEAST_CONNECTIONS
    server = opt.get_backend_server()
    assert server.server_id == "s2"

    opt.load_balancing_strategy = LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN
    server = opt.get_backend_server()
    assert server is not None

    opt.load_balancing_strategy = LoadBalancingStrategy.IP_HASH
    server = opt.get_backend_server("10.0.0.1")
    assert server is not None

    opt.load_balancing_strategy = LoadBalancingStrategy.CONSISTENT_HASH
    server = opt.get_backend_server()
    assert server is not None

    opt.set_concurrent_limit("/api/test", 2)
    assert opt.check_concurrent_limit("/api/test") is True
    assert opt.current_connections["/api/test"] == 1
    opt.release_connection("/api/test")
    assert opt.current_connections["/api/test"] == 0

    opt.track_request("/api/test", "GET", True, 120.0)
    metrics = opt.get_throughput_metrics("/api/test", "GET")
    assert metrics is not None
    assert metrics.total_requests == 1
    assert metrics.success_rate == 1.0

    all_metrics = opt.get_all_throughput_metrics()
    assert "GET:/api/test" in all_metrics

    recs = opt.optimize_throughput("/api/test", "GET")
    assert recs["endpoint"] == "/api/test"
    assert recs["method"] == "GET"
    assert "recommendations" in recs
    assert "current_metrics" in recs

    assert opt.health_check_backend("missing") is False
    assert opt.health_check_backend("s1") is True
    assert opt.backend_servers[0].last_health_check is not None

    empty_opt = get_api_throughput_optimizer({})
    assert empty_opt.get_backend_server() is None

    stats = opt.get_statistics()
    assert isinstance(stats, dict)
    assert "total_requests_processed" in stats
    assert stats["total_requests_processed"] == 1


def test_api_response_time_optimizer():
    async def _run():
        opt = get_api_response_time_optimizer({})
        assert isinstance(opt, APIResponseTimeOptimizer)

        for _ in range(20):
            opt.track_response("/api/slow", "GET", 1500.0, 200, response_size_bytes=1024)

        slow = opt.analyze_slow_endpoints()
        assert len(slow) == 1
        assert slow[0]["endpoint"] == "/api/slow"
        assert slow[0]["p95_response_time_ms"] == 1500.0

        recs = opt.generate_optimizations()
        assert len(recs) == 1
        rec = recs[0]
        assert isinstance(rec, OptimizationRecommendation)
        assert rec.level == OptimizationLevel.MEDIUM
        assert rec.optimization_type == "query_optimization"
        assert rec.endpoint == "/api/slow"
        assert rec.method == "GET"

        metrics = opt.get_response_metrics("/api/slow", "GET")
        assert isinstance(metrics, ResponseTimeMetrics)
        assert metrics.total_requests == 20
        assert metrics.p95_response_time_ms == 1500.0

        all_metrics = opt.get_all_metrics()
        assert "GET:/api/slow" in all_metrics

        opt.enable_response_caching("/api/slow", "GET", ttl_seconds=60)
        payload = {"result": "cached"}
        opt.cache_response("/api/slow", "GET", payload, cache_key="abc")
        cached = opt.get_cached_response("/api/slow", "GET", cache_key="abc")
        assert cached == payload
        assert opt.get_cached_response("/api/slow", "GET", cache_key="missing") is None

        stats = opt.get_statistics()
        assert isinstance(stats, dict)
        assert stats["total_requests_tracked"] == 20
        assert stats["total_cache_hits"] >= 1
        assert stats["total_cache_misses"] >= 1

        async def async_task():
            return 42

        result = await opt.process_async_task(async_task)  # noqa: F841  # Variable for test verification
        assert result == 42  # noqa: F841  # Variable for test verification

    asyncio.run(_run())


def test_cpu_usage_optimizer(monkeypatch):
    monkeypatch.setattr(psutil, "cpu_percent", _cpu_percent)
    monkeypatch.setattr(psutil, "cpu_count", lambda: 4)
    monkeypatch.setattr(psutil, "getloadavg", lambda: [0.1, 0.2, 0.3])
    monkeypatch.setattr(psutil, "pids", lambda: [1, 2, 3])

    opt = get_cpu_usage_optimizer({})
    assert isinstance(opt, CPUUsageOptimizer)

    snapshot = opt.take_cpu_snapshot()
    assert isinstance(snapshot, CPUSnapshot)
    assert snapshot.cpu_percent == 50.0
    assert snapshot.cpu_count == 4

    opt.set_cpu_limit("test", 100.0, 80.0, 95.0, CPUOptimizationAction.REDUCE_PRIORITY)
    opt.component_cpu["test"] = 50.0
    check = opt.check_cpu_limit("test")
    assert check["status"] == "normal"

    opt.component_cpu["test"] = 90.0
    check = opt.check_cpu_limit("test")
    assert check["status"] == "warning"
    assert check["action"] == CPUOptimizationAction.REDUCE_PRIORITY.value

    opt.set_cpu_limit("test", 100.0, 85.0, 95.0, CPUOptimizationAction.THROTTLE_PROCESSES)
    result = opt.optimize_cpu("test")  # noqa: F841  # Variable for test verification
    assert "throttle_processes" in result["actions_taken"]
    assert opt.total_optimizations_applied == 1

    opt.set_cpu_limit("test", 100.0, 90.0, 95.0, CPUOptimizationAction.DISTRIBUTE_LOAD)
    result = opt.optimize_cpu("test")  # noqa: F841  # Variable for test verification
    assert "distribute_load" in result["actions_taken"]

    opt.set_cpu_limit("test", 100.0, 95.0, 99.0, CPUOptimizationAction.SCALE_WORKERS)
    opt.component_cpu["test"] = 96.0
    result = opt.optimize_cpu("test")  # noqa: F841  # Variable for test verification
    assert "scale_workers" in result["actions_taken"]

    now = datetime.now(timezone.utc)
    for i in range(3):
        opt.cpu_snapshots.append(
            CPUSnapshot(
                snapshot_id=f"spike_before_{i}",
                timestamp=now - timedelta(seconds=5 - i),
                cpu_percent=40.0,
                cpu_count=4,
                per_cpu_percent=[40.0] * 4,
                load_average=[0.1, 0.1, 0.1],
                process_count=10,
                metadata={"component": "test"},
            )
        )
    for i in range(3):
        opt.cpu_snapshots.append(
            CPUSnapshot(
                snapshot_id=f"spike_after_{i}",
                timestamp=now - timedelta(seconds=i),
                cpu_percent=70.0,
                cpu_count=4,
                per_cpu_percent=[70.0] * 4,
                load_average=[0.5, 0.5, 0.5],
                process_count=10,
                metadata={"component": "test"},
            )
        )

    assert opt.detect_cpu_spike("test") is True
    assert opt.total_spike_detections >= 1

    opt.component_cpu["test"] = 90.0
    assert opt.detect_high_usage("test") is True
    assert opt.total_high_usage_detections >= 1

    opt.set_task_priority("task1", "test", 70, cpu_affinity=[0, 1], nice_value=-5)
    priority = opt.get_task_priority("task1")
    assert priority is not None
    assert priority.priority == 70
    assert priority.nice_value == -5

    for _ in range(10):
        opt.take_cpu_snapshot("test")

    efficiency = opt.get_cpu_efficiency("test")
    assert isinstance(efficiency, dict)
    assert "efficiency" in efficiency

    stats = opt.get_cpu_statistics()
    assert isinstance(stats, dict)
    assert "avg_cpu_percent" in stats

    assert opt.get_component_cpu("test") == 50.0
    assert opt.get_component_cpu("missing") is None

    summary = opt.get_statistics()
    assert isinstance(summary, dict)
    assert "total_optimizations_applied" in summary


def test_memory_usage_optimizer(monkeypatch):
    monkeypatch.setattr(psutil, "virtual_memory", _virtual_memory)
    monkeypatch.setitem(sys.modules, "numpy", _FakeNumpy())

    opt = get_memory_usage_optimizer({})
    assert isinstance(opt, MemoryUsageOptimizer)

    snapshot = opt.take_memory_snapshot()
    assert isinstance(snapshot, MemorySnapshot)
    assert snapshot.memory_percent == 50.0

    opt.set_memory_limit("test", 10000.0, 80.0, 95.0, MemoryAction.COLLECT_GARBAGE)

    opt.component_memory["test"] = 8500.0
    check = opt.check_memory_limit("test")
    assert check["status"] == "warning"

    opt.component_memory["test"] = 9600.0
    check = opt.check_memory_limit("test")
    assert check["status"] == "critical"

    opt.component_memory["test"] = 7000.0
    check = opt.check_memory_limit("test")
    assert check["status"] == "normal"

    opt.component_memory["test"] = 8500.0
    now = datetime.now(timezone.utc)
    for i in range(11):
        opt.memory_snapshots.append(
            MemorySnapshot(
                snapshot_id=f"mem_test_{i}",
                timestamp=now - timedelta(hours=10 - i),
                total_memory_mb=16000.0,
                used_memory_mb=100.0 + i * 20.0,
                available_memory_mb=15000.0,
                memory_percent=0.0,
                gc_objects=0,
                gc_collections={0: 0, 1: 0, 2: 0},
                metadata={"component": "test"},
            )
        )

    leaks = opt.detect_memory_leaks("test")
    assert len(leaks) == 1
    assert leaks[0].component == "test"
    assert leaks[0].severity in ("high", "medium")

    result = opt.optimize_memory("test")  # noqa: F841  # Variable for test verification
    assert "garbage_collection" in result["actions_taken"]
    assert result.get("leaks_detected") == 1

    gc_result = opt.collect_garbage()  # noqa: F841  # Variable for test verification
    assert isinstance(gc_result, dict)
    assert "collected_objects" in gc_result
    assert "memory_freed_mb" in gc_result

    trace = opt.get_memory_trace(limit=3)
    assert isinstance(trace, list)

    stats = opt.get_memory_statistics()
    assert isinstance(stats, dict)
    assert "used_memory_mb" in stats

    assert opt.get_component_memory("test") == 8500.0
    assert opt.get_component_memory("missing") is None

    summary = opt.get_statistics()
    assert isinstance(summary, dict)
    assert "total_gc_collections" in summary
