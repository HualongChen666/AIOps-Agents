# -*- coding: utf-8 -*-
"""Batch 26c coverage tests for zero-coverage core modules."""

import asyncio
import datetime
import hashlib
import json
import sys
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Dict, List, Optional

import pytest

from core import cache_manager as cm
from core import type_validation as tv
from core.api_response_time_optimizer import (
    APIResponseTimeOptimizer,
    CacheStrategy,
    OptimizationLevel,
    get_api_response_time_optimizer,
)
from core.cpu_usage_optimizer import (
    CPUEventType,
    CPUOptimizationAction,
    CPUUsageOptimizer,
    get_cpu_usage_optimizer,
)
from core.tracing_visualization import (
    ServiceNode,
    SpanNode,
    TimeRange,
    TraceData,
    TracingVisualizationManager,
    VisualizationType,
    get_tracing_visualization_manager,
)

pytestmark = [pytest.mark.core]


# ---------------------------------------------------------------------------
# Tracing visualization
# ---------------------------------------------------------------------------
class TestTracingVisualization:
    @pytest.fixture
    def manager(self):
        return TracingVisualizationManager({"some": "config"})

    @pytest.fixture
    def trace(self):
        now = datetime.datetime.now(datetime.timezone.utc)
        spans = [
            {
                "span_id": "s1",
                "parent_span_id": None,
                "operation_name": "op1",
                "service_name": "svc-a",
                "start_time": now.isoformat(),
                "duration_ms": 50.0,
                "status": "OK",
                "attributes": {"k": "v"},
            },
            {
                "span_id": "s2",
                "parent_span_id": "s1",
                "operation_name": "op2",
                "service_name": "svc-a",
                "start_time": now.isoformat(),
                "duration_ms": 20.0,
                "status": "ERROR",
                "attributes": {},
            },
            {
                "span_id": "s3",
                "parent_span_id": "s1",
                "operation_name": "op3",
                "service_name": "svc-b",
                "start_time": now.isoformat(),
                "duration_ms": 10.0,
                "status": "OK",
                "attributes": {},
            },
        ]
        return TraceData(
            trace_id="t-1",
            root_span_id="s1",
            service_name="svc-a",
            operation_name="root-op",
            start_time=now,
            end_time=now + datetime.timedelta(milliseconds=90),
            duration_ms=90.0,
            status="OK",
            spans=spans,
            attributes={"env": "test"},
            metadata={"version": "1"},
        )

    def test_add_trace_and_generate_views(self, manager, trace):
        manager.add_trace_data(trace)
        assert manager.total_traces == 1
        assert "svc-a" in manager.service_map

        # trace view
        view = manager.generate_trace_view("t-1")
        assert view["visualization_type"] == VisualizationType.TRACE_VIEW.value
        assert view["trace_id"] == "t-1"
        assert len(view["span_tree"]["roots"]) == 1
        assert view["span_statistics"]["total_spans"] == 3

        # service map
        smap = manager.generate_service_map()
        assert smap["visualization_type"] == VisualizationType.SERVICE_MAP.value
        assert smap["total_services"] == 2

        # flame graph
        flame = manager.generate_flame_graph("t-1")
        assert flame["visualization_type"] == VisualizationType.FLAME_GRAPH.value
        assert flame["total_spans"] == 3

        # gantt
        gantt = manager.generate_gantt_chart("t-1")
        assert gantt["visualization_type"] == VisualizationType.GANTT_CHART.value
        assert gantt["total_spans"] == 3

    def test_generate_missing_trace(self, manager):
        assert manager.generate_trace_view("missing") is None
        assert manager.generate_flame_graph("missing") is None
        assert manager.generate_gantt_chart("missing") is None

    def test_metrics_dashboard_time_ranges(self, manager, trace):
        manager.add_trace_data(trace)
        for tr in TimeRange:
            dash = manager.generate_metrics_dashboard(tr)
            assert dash["visualization_type"] == VisualizationType.METRICS_DASHBOARD.value
            assert tr.value in ("15m", "30m", "1h", "6h", "24h", "7d", "custom")

    def test_statistics_and_factory(self):
        m = get_tracing_visualization_manager({})
        assert isinstance(m, TracingVisualizationManager)
        stats = m.get_statistics()
        assert "total_traces" in stats

    def test_span_statistics_empty(self, manager):
        assert manager._calculate_span_statistics([]) == {}


# ---------------------------------------------------------------------------
# CPU usage optimizer
# ---------------------------------------------------------------------------
class TestCPUUsageOptimizer:
    @pytest.fixture
    def optimizer(self, monkeypatch):
        cmod = sys.modules["core.cpu_usage_optimizer"]
        monkeypatch.setattr(
            cmod.psutil,
            "cpu_percent",
            lambda interval=None, percpu=False: [10.0, 20.0] if percpu else 15.0,
        )
        monkeypatch.setattr(cmod.psutil, "cpu_count", lambda: 4)
        monkeypatch.setattr(cmod.psutil, "getloadavg", lambda: [1.0, 2.0, 3.0], raising=False)
        monkeypatch.setattr(cmod.psutil, "pids", lambda: [1, 2, 3, 4])
        return CPUUsageOptimizer(
            {"spike_threshold_percent": 5.0, "high_usage_threshold_percent": 10.0}
        )

    def test_snapshot_and_limits(self, optimizer):
        snap = optimizer.take_cpu_snapshot(component="web")
        assert snap.cpu_percent == 15.0
        assert snap.cpu_count == 4
        assert len(snap.load_average) == 3

        optimizer.set_cpu_limit(
            component="web",
            max_cpu_percent=50.0,
            warning_threshold_percent=20.0,
            critical_threshold_percent=50.0,
            action_on_exceed=CPUOptimizationAction.THROTTLE_PROCESSES,
        )
        assert "web" in optimizer.cpu_limits

    def test_check_cpu_limit_branches(self, optimizer):
        # no limit
        assert optimizer.check_cpu_limit("db")["status"] == "no_limit"

        optimizer.set_cpu_limit(
            "db",
            max_cpu_percent=100.0,
            warning_threshold_percent=50.0,
            critical_threshold_percent=90.0,
        )
        # normal
        optimizer.component_cpu["db"] = 20.0
        assert optimizer.check_cpu_limit("db")["status"] == "normal"

        # warning
        optimizer.component_cpu["db"] = 60.0
        assert optimizer.check_cpu_limit("db")["status"] == "warning"

        # critical
        optimizer.component_cpu["db"] = 95.0
        assert optimizer.check_cpu_limit("db")["status"] == "critical"

    def test_spike_and_high_usage_detection(self, optimizer):
        base = 10.0
        for i in range(10):
            snap = SimpleNamespace(
                timestamp=datetime.datetime.now(datetime.timezone.utc),
                cpu_percent=base + i * 5,
                metadata={"component": "app"},
            )
            optimizer.cpu_snapshots.append(snap)
        optimizer.component_cpu["app"] = 95.0

        assert optimizer.detect_cpu_spike("app") is True
        assert optimizer.total_spike_detections == 1
        assert optimizer.detect_high_usage("app") is True
        assert optimizer.total_high_usage_detections == 1
        assert optimizer.detect_cpu_spike("empty") is False
        assert optimizer.get_component_cpu("missing") is None

    def test_task_priority_and_get(self, optimizer):
        optimizer.set_task_priority("t1", "worker", 50, cpu_affinity=[0, 1], nice_value=-5)
        tp = optimizer.get_task_priority("t1")
        assert tp.priority == 50
        assert tp.nice_value == -5

    def test_optimize_cpu_actions(self, optimizer):
        for action in CPUOptimizationAction:
            optimizer.cpu_limits.clear()
            optimizer.set_cpu_limit(action.value, max_cpu_percent=100.0, action_on_exceed=action)
            optimizer.component_cpu[action.value] = 120.0
            result = optimizer.optimize_cpu(action.value)
            assert result["component"] == action.value
            if action != CPUOptimizationAction.ALERT_ONLY:
                assert len(result["actions_taken"]) == 1

    def test_statistics(self, optimizer):
        stats = optimizer.get_statistics()
        assert "total_snapshots" in stats
        assert stats["total_task_priorities"] == 0

    def test_get_cpu_statistics_and_efficiency(self, optimizer):
        optimizer.take_cpu_snapshot("web")
        stats = optimizer.get_cpu_statistics()
        assert stats["avg_cpu_percent"] > 0

        now = datetime.datetime.now(datetime.timezone.utc)
        for val, comp in [(45, "under"), (75, "optimal"), (90, "over"), (60, "acceptable")]:
            for _ in range(10):
                optimizer.cpu_snapshots.append(
                    SimpleNamespace(
                        timestamp=now,
                        cpu_percent=float(val),
                        metadata={"component": comp},
                    )
                )
            eff = optimizer.get_cpu_efficiency(comp)
            assert eff["efficiency"] in ("underutilized", "optimal", "overutilized", "acceptable")

    def test_getloadavg_oserror(self, monkeypatch):
        cmod = sys.modules["core.cpu_usage_optimizer"]
        monkeypatch.setattr(
            cmod.psutil, "getloadavg", lambda: (_ for _ in ()).throw(OSError("fail")), raising=False
        )
        monkeypatch.setattr(
            cmod.psutil,
            "cpu_percent",
            lambda interval=None, percpu=False: [10.0] if percpu else 10.0,
        )
        monkeypatch.setattr(cmod.psutil, "cpu_count", lambda: 2)
        monkeypatch.setattr(cmod.psutil, "pids", lambda: [1])
        opt = CPUUsageOptimizer()
        snap = opt.take_cpu_snapshot()
        assert snap.load_average == [0.0, 0.0, 0.0]


# ---------------------------------------------------------------------------
# API response time optimizer
# ---------------------------------------------------------------------------
class TestAPIResponseTimeOptimizer:
    @pytest.fixture
    def optimizer(self):
        return APIResponseTimeOptimizer(
            {"slow_response_threshold_ms": 1000, "cache_ttl_seconds": 300}
        )

    def test_track_and_metrics(self, optimizer):
        for i in range(100):
            optimizer.track_response(
                endpoint="/slow",
                method="GET",
                response_time_ms=10000.0,
                status_code=200,
                response_size_bytes=1024,
            )
        metrics = optimizer.get_response_metrics("/slow", "GET")
        assert metrics.total_requests == 100
        assert metrics.p99_response_time_ms > 0

    def test_analyze_and_generate_optimizations(self, optimizer):
        # critical
        for _ in range(100):
            optimizer.track_response("/critical", "POST", 10000.0, 500)
        # high
        for _ in range(25):
            optimizer.track_response("/high", "GET", 3000.0, 200)
        # medium
        for _ in range(25):
            optimizer.track_response("/medium", "GET", 1500.0, 200)
        # not slow
        for _ in range(10):
            optimizer.track_response("/fast", "GET", 100.0, 200)

        slow = optimizer.analyze_slow_endpoints()
        assert any(e["endpoint"] == "/critical" for e in slow)

        recs = optimizer.generate_optimizations()
        types = {r.optimization_type for r in recs}
        assert "async_processing" in types

    def test_caching(self, optimizer):
        optimizer.enable_response_caching("/cached", "GET", ttl_seconds=300)
        assert optimizer.get_cached_response("/cached", "GET") is None

        optimizer.cache_response("/cached", "GET", {"data": [1, 2, 3]}, cache_key="k1")
        hit = optimizer.get_cached_response("/cached", "GET", cache_key="k1")
        assert hit == {"data": [1, 2, 3]}
        assert optimizer.total_cache_hits == 1

        # expired with negative ttl
        optimizer.enable_response_caching("/expired", "GET", ttl_seconds=-1)
        optimizer.cache_response("/expired", "GET", "x", cache_key="k2")
        assert optimizer.get_cached_response("/expired", "GET", cache_key="k2") is None
        assert optimizer.total_cache_misses > 0

    def test_process_async_task(self, optimizer):
        async def good():
            return 42

        async def bad():
            raise ValueError("boom")

        assert asyncio.run(optimizer.process_async_task(good)) == 42
        with pytest.raises(ValueError):
            asyncio.run(optimizer.process_async_task(bad))

    def test_get_statistics(self, optimizer):
        optimizer.track_response("/x", "GET", 10.0, 200)
        stats = optimizer.get_statistics()
        assert stats["total_requests_tracked"] == 1


# ---------------------------------------------------------------------------
# Type validation
# ---------------------------------------------------------------------------
class TestTypeValidation:
    def test_validate_type_basic(self):
        assert tv.RuntimeTypeValidator.validate_type(5, int) == 5
        with pytest.raises(tv.TypeValidationError):
            tv.RuntimeTypeValidator.validate_type("5", int)

    def test_validate_type_optional_and_none(self):
        assert tv.RuntimeTypeValidator.validate_type(None, Optional[int]) is None
        with pytest.raises(tv.TypeValidationError):
            tv.RuntimeTypeValidator.validate_type(None, int)

    def test_validate_type_collection(self):
        assert tv.RuntimeTypeValidator.validate_type([1, 2, 3], List[int]) == [1, 2, 3]
        with pytest.raises(tv.TypeValidationError):
            tv.RuntimeTypeValidator.validate_type([1, "two"], List[int])
        assert tv.RuntimeTypeValidator.validate_type({"a": 1}, Dict[str, int]) == {"a": 1}

    def test_validate_dataclass(self):
        @dataclass
        class Person:
            name: str
            age: int

        p = Person(name="alice", age=30)
        assert tv.RuntimeTypeValidator.validate_type(p, Person) is p
        p2 = Person(name="bob", age="thirty")
        with pytest.raises(tv.TypeValidationError):
            tv.RuntimeTypeValidator.validate_type(p2, Person)

    def test_coerce_type(self):
        assert tv.RuntimeTypeValidator.coerce_type("42", int) == 42
        assert tv.RuntimeTypeValidator.coerce_type("3.14", float) == 3.14
        assert tv.RuntimeTypeValidator.coerce_type(123, str) == "123"
        assert tv.RuntimeTypeValidator.coerce_type("true", bool) is True
        with pytest.raises(tv.TypeValidationError):
            tv.RuntimeTypeValidator.coerce_type("abc", int)

    def test_validate_types_decorator(self):
        @tv.validate_types(x=int, y=int)
        def add(x, y):
            return x + y

        assert add(2, 3) == 5
        with pytest.raises(tv.TypeValidationError):
            add("a", 3)
        with pytest.raises(tv.TypeValidationError):
            add(x="2", y=3)

    def test_validate_return_type_decorator(self):
        @tv.validate_return_type(str)
        def greet(name):
            return "hello " + name

        assert greet("world") == "hello world"

        @tv.validate_return_type(int)
        def bad():
            return "not int"

        with pytest.raises(tv.TypeValidationError):
            bad()

    def test_type_safe_api(self):
        schema = {"name": str, "age": int}
        data = {"name": "alice", "age": 30}
        assert tv.TypeSafeAPI.validate_request_data(data, schema) == data

        with pytest.raises(tv.TypeValidationError):
            tv.TypeSafeAPI.validate_request_data({"name": "bob"}, schema)
        with pytest.raises(tv.TypeValidationError):
            tv.TypeSafeAPI.validate_request_data({"name": "bob", "age": "thirty"}, schema)

    def test_sanitize_response(self):
        class Color(tv.Enum):
            RED = "red"

        raw = {
            "list": [1, datetime.datetime(2024, 1, 1, tzinfo=datetime.timezone.utc)],
            "enum": Color.RED,
            "nested": {"date": datetime.date(2024, 1, 1)},
        }
        clean = tv.TypeSafeAPI.sanitize_response_data(raw, max_depth=3)
        assert clean["enum"] == "red"

    def test_type_utilities(self):
        assert tv.get_optional_type(int) is not None
        assert tv.get_list_type(int) is not None
        assert tv.get_dict_type(str, int) is not None

    def test_async_decorators(self):
        @tv.validate_request({"payload": str})
        async def handler(data):
            return data

        assert asyncio.run(handler({"payload": "ok"})) == {"payload": "ok"}

        @tv.sanitize_response
        async def producer():
            return {"now": datetime.datetime.now(datetime.timezone.utc)}

        result = asyncio.run(producer())
        assert isinstance(result["now"], str)


# ---------------------------------------------------------------------------
# Cache manager
# ---------------------------------------------------------------------------
class TestCacheManager:
    def test_memory_backend_get_set_delete(self):
        backend = cm.MemoryCacheBackend()
        assert backend.get("missing") is None
        backend.set("key", "value", 100)
        assert backend.get("key") == "value"
        assert backend.stats()["total_hits"] == 1
        assert backend.delete("key") is True
        assert backend.delete("key") is False
        backend.set("expire", "v", -1)
        assert backend.get("expire") is None
        assert backend.clear() is True

    def test_redis_backend_with_mock(self):
        client = SimpleNamespace(
            get=lambda k: json.dumps({"x": 1}),
            setex=lambda *a, **k: None,
            delete=lambda k: 1,
            flushdb=lambda: None,
            info=lambda: {"keyspace_hits": 5, "keyspace_misses": 2},
            dbsize=lambda: 10,
        )
        rb = cm.RedisCacheBackend(client)
        assert rb.get("k") == {"x": 1}
        rb.set("k", "v", 10)
        assert rb.delete("k") is True
        assert rb.clear() is True
        assert rb.stats()["cache_size"] == 10

    def test_disk_backend_with_mock(self):
        class FakeCache:
            def get(self, k):
                return "val"

            def set(self, *a, **k):
                pass

            def delete(self, k):
                return True

            def clear(self):
                pass

            def __len__(self):
                return 3

        db = cm.DiskCacheBackend(FakeCache())
        assert db.get("k") == "val"
        db.set("k", "v", 10)
        assert db.delete("k") is True
        assert db.clear() is True
        assert db.stats()["cache_size"] == 3

    def test_cache_result_decorator(self):
        # Ensure we start on a fresh memory backend for this test
        cm._BACKEND = "memory"
        cm._BACKENDS.clear()

        @cm.cache_result(ttl=60, enable_monitoring=True)
        def compute(x, y, extra="d"):
            return x + y + len(extra)

        assert compute(1, 2) == 4
        assert compute(1, 2) == 4
        assert cm.get_cache_stats("compute")["function_size"] == 1

    def test_invalidate_backup_restore_flush(self, monkeypatch):
        monkeypatch.setattr(cm, "_BACKEND", "memory")
        monkeypatch.setattr(cm, "_BACKENDS", {})

        @cm.cache_result(ttl=60)
        def sample_func(a):
            return a * 2

        sample_func(5)
        sample_func(7)

        assert cm.invalidate_cache("sample_func") == 2

        backup = cm.backup_cache("sample_func")
        assert len(backup) == 0  # deleted before backup

        sample_func(1)
        backup = cm.backup_cache("sample_func")
        assert cm.restore_cache(backup) == 1

        assert cm.flush_all() is True
        assert cm.get_cache_metrics("sample_func")["cache_size"] == 0

    def test_configure_backend_redis_fallback(self, monkeypatch):
        monkeypatch.setenv("REDIS_URL", "redis://localhost")
        try:
            import redis as redis_mod

            monkeypatch.setattr(
                redis_mod, "from_url", lambda *a, **k: (_ for _ in ()).throw(Exception("no redis"))
            )
        except ImportError:
            pass
        monkeypatch.setattr(cm, "_BACKEND", "memory")
        monkeypatch.setattr(cm, "_BACKENDS", {})

        assert cm.configure_backend("redis") is True
        assert cm._get_backend().__class__.__name__ == "MemoryCacheBackend"
        # reset to memory for following tests
        cm._BACKEND = "memory"
        cm._BACKENDS.clear()

    def test_configure_backend_disk_fallback(self, monkeypatch):
        monkeypatch.setenv("DISK_CACHE_DIR", "data/cache")
        try:
            import diskcache as dc

            monkeypatch.setattr(
                dc, "Cache", lambda *a, **k: (_ for _ in ()).throw(Exception("no diskcache"))
            )
        except ImportError:
            pass
        monkeypatch.setattr(cm, "_BACKEND", "memory")
        monkeypatch.setattr(cm, "_BACKENDS", {})

        assert cm.configure_backend("disk") is True
        assert cm._get_backend().__class__.__name__ == "MemoryCacheBackend"
        cm._BACKEND = "memory"
        cm._BACKENDS.clear()
