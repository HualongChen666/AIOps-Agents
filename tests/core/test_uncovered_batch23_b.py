# -*- coding: utf-8 -*-
"""Functional coverage tests for core batch 23-b modules."""

import asyncio
import json
import sys
import types
from unittest.mock import AsyncMock, MagicMock

import pytest

import core.caching_strategy as caching_strategy
import core.database_cache_optimizer as cache_opt_mod
import core.database_connection_optimizer as conn_opt_mod
import core.database_optimization_manager as dom
import core.database_query_optimizer as query_opt_mod
import core.dependency_injection as di

# Load slo_engine first so that the cyclic slo_storage import resolves cleanly.
import core.slo_engine as _slo_engine  # noqa: F401
import core.slo_storage as slo_storage
import core.workflow.engine.dag as dag

pytestmark = [pytest.mark.core]


# ---------------------------------------------------------------------------
# core/slo_storage.py
# ---------------------------------------------------------------------------
@pytest.fixture
def fresh_slo_storage(tmp_path, monkeypatch):
    """Point SLO persistence at a temporary file and reset the store."""
    monkeypatch.setattr(slo_storage, "_DATA_DIR", tmp_path)
    monkeypatch.setattr(slo_storage, "_SLOS_FILE", tmp_path / "slos.json")
    monkeypatch.setattr(slo_storage, "_ensure_data_dir", lambda: None)

    original_store = _slo_engine._slo_store
    monkeypatch.setattr(_slo_engine, "_slo_store", {})
    monkeypatch.setattr(_slo_engine, "_slo_counter", 0)
    yield


def _make_slo_rule(slo_id="SLO-001", name="uptime", target=0.99):
    return _slo_engine.SLORule(
        id=slo_id,
        name=name,
        service="payments",
        metric="availability",
        target=target,
        window=24,
        alert_threshold=0.95,
        aggregation="good_ratio",
    )


def test_save_and_load_slos(fresh_slo_storage, monkeypatch):
    rule = _make_slo_rule()
    _slo_engine._slo_store[rule.id] = rule
    _slo_engine._slo_counter = 5

    info_calls = []
    monkeypatch.setattr(
        slo_storage.logger,
        "info",
        lambda *args, **kwargs: info_calls.append(args),
    )

    slo_storage.save_slos()
    assert slo_storage._SLOS_FILE.exists()

    # Reset and reload
    _slo_engine._slo_store.clear()
    _slo_engine._slo_counter = 0
    slo_storage.load_slos()

    assert _slo_engine._slo_counter == 5
    assert rule.id in _slo_engine._slo_store
    loaded = _slo_engine._slo_store[rule.id]
    assert loaded.name == rule.name
    assert loaded.target == rule.target


def test_load_slos_missing_file(fresh_slo_storage, monkeypatch):
    debug_calls = []
    monkeypatch.setattr(
        slo_storage.logger, "debug", lambda *args, **kwargs: debug_calls.append(args)
    )
    slo_storage.load_slos()
    assert any("No SLO persistence file" in str(c) for c in debug_calls)


def test_load_slos_invalid_json(fresh_slo_storage, monkeypatch):
    slo_storage._SLOS_FILE.write_text("not-json", encoding="utf-8")
    warning_calls = []
    monkeypatch.setattr(
        slo_storage.logger, "warning", lambda *args, **kwargs: warning_calls.append(args)
    )
    slo_storage.load_slos()
    assert any("Failed to load SLOs" in str(c) for c in warning_calls)
    assert not _slo_engine._slo_store


# ---------------------------------------------------------------------------
# core/workflow/engine/dag.py
# ---------------------------------------------------------------------------
def test_dag_build_and_topological_sort():
    graph = dag.DAG("deploy")
    nodes = [
        dag.DAGNode("a", "build"),
        dag.DAGNode("b", "test", dependencies=["a"]),
        dag.DAGNode("c", "deploy", dependencies=["b"]),
        dag.DAGNode("d", "notify", dependencies=["b"]),
    ]
    for n in nodes:
        graph.add_node(n)
    graph.add_edge(dag.Edge("a", "b", "ok"))
    graph.add_edge(dag.Edge("b", "c"))
    graph.add_edge(dag.Edge("b", "d"))

    order = graph.topological_sort()
    assert order.index("a") < order.index("b")
    assert order.index("b") < order.index("c")
    assert order.index("b") < order.index("d")

    assert graph.get_dependencies("c") == ["b"]
    assert graph.get_dependents("b") == ["a"]


def test_dag_cycle_detection_and_topological_error():
    graph = dag.DAG("cycle")
    for node_id in ("a", "b", "c"):
        graph.add_node(dag.DAGNode(node_id, node_id))
    graph.add_edge(dag.Edge("a", "b"))
    graph.add_edge(dag.Edge("b", "c"))
    graph.add_edge(dag.Edge("c", "a"))

    cycles = graph.detect_cycles()
    assert any("a" in cycle and "b" in cycle and "c" in cycle for cycle in cycles)

    with pytest.raises(ValueError, match="Cycle detected"):
        graph.topological_sort()


def test_dag_remove_node_and_serialization():
    graph = dag.DAG("remove-test")
    for node_id in ("a", "b", "c"):
        graph.add_node(dag.DAGNode(node_id, node_id))
    graph.add_edge(dag.Edge("a", "b"))
    graph.add_edge(dag.Edge("b", "c"))

    graph.remove_node("b")
    assert "b" not in graph.nodes
    assert all(edge.to_node != "b" and edge.from_node != "b" for edge in graph.edges)
    assert graph.get_dependencies("c") == ["b"]
    assert graph.get_dependents("a") == []

    graph.nodes["a"].status = dag.NodeStatus.SUCCESS
    graph.nodes["c"].status = dag.NodeStatus.PENDING
    ready = graph.get_ready_nodes()
    assert "c" in ready
    assert "a" not in ready

    payload = graph.to_dict()
    assert payload["name"] == "remove-test"
    assert "a" in payload["nodes"]
    assert isinstance(graph.to_json(), str)


# ---------------------------------------------------------------------------
# core/database_optimization_manager.py
# ---------------------------------------------------------------------------
class _FakeOptType:
    value = "index_addition"


class _FakePriority:
    value = "high"


class _FakeSlowQuery:
    query_id = "q1"
    avg_duration_ms = 42.0
    execution_count = 10


class _FakeOptimization:
    optimization_id = "opt1"
    optimization_type = _FakeOptType()
    priority = _FakePriority()
    expected_improvement = 0.25


class _FakeQueryOptimizer:
    def __init__(self):
        self.recorded = []

    def analyze_slow_queries(self):
        return [_FakeSlowQuery()]

    def generate_optimizations(self):
        return [_FakeOptimization()]

    def record_query_execution(self, **kwargs):
        self.recorded.append(kwargs)


class _FakeConnectionOptimizer:
    def get_pool_metrics(self, pool_name=None):
        return {"pool": pool_name or "default", "active": 1}

    def generate_optimization_recommendations(self):
        return ["increase-pool"]


class _FakeCacheOptimizer:
    configured = []

    def configure_cache(self, strategy, ttl_seconds):
        self.configured.append({"strategy": strategy, "ttl": ttl_seconds})


class _RaisingOptimizer:
    def __init__(self):
        raise RuntimeError("optimizer failure")


class _QueryOptimizerRaisesAnalyze:
    def __init__(self):
        pass

    def analyze_slow_queries(self):
        raise RuntimeError("analysis failure")

    def generate_optimizations(self):
        return []


class _QueryOptimizerRaisesGenerate:
    def analyze_slow_queries(self):
        return []

    def generate_optimizations(self):
        raise RuntimeError("generation failure")


class _QueryOptimizerRaisesRecord:
    def analyze_slow_queries(self):
        return []

    def generate_optimizations(self):
        return []

    def record_query_execution(self, **kwargs):
        raise RuntimeError("record failure")


class _ConnectionOptimizerRaisesMetrics:
    def get_pool_metrics(self, pool_name=None):
        raise RuntimeError("metrics failure")

    def generate_optimization_recommendations(self):
        return []


class _ConnectionOptimizerNoRecommendations:
    def get_pool_metrics(self, pool_name=None):
        return {"pool": pool_name or "default"}


class _CacheOptimizerRaisesConfigure:
    def configure_cache(self, strategy, ttl_seconds):
        raise RuntimeError("cache failure")


class _CacheOptimizerNoConfigure:
    pass


@pytest.fixture
def fake_optimizer_modules(monkeypatch):
    """Replace real optimizer classes with lightweight fakes."""
    monkeypatch.setattr(query_opt_mod, "DatabaseQueryOptimizer", _FakeQueryOptimizer)
    monkeypatch.setattr(conn_opt_mod, "DatabaseConnectionOptimizer", _FakeConnectionOptimizer)
    monkeypatch.setattr(cache_opt_mod, "DatabaseCacheOptimizer", _FakeCacheOptimizer)


def test_manager_loads_and_status(fake_optimizer_modules):
    manager = dom.DatabaseOptimizationManager()
    assert manager.status.query_optimization_enabled
    assert manager.status.connection_optimization_enabled
    assert manager.status.cache_optimization_enabled


def test_analyze_slow_queries(fake_optimizer_modules):
    manager = dom.DatabaseOptimizationManager()
    result = manager.analyze_slow_queries(limit=1)
    assert result["slow_queries_count"] == 1
    assert result["optimizations_count"] == 1
    assert result["slow_queries"][0]["query_id"] == "q1"
    assert result["optimizations"][0]["type"] == "index_addition"


def test_analyze_slow_queries_unavailable():
    manager = dom.DatabaseOptimizationManager()
    manager.query_optimizer = None
    assert manager.analyze_slow_queries() == {"error": "Query optimizer not available"}


def test_optimize_connection_pool(fake_optimizer_modules):
    manager = dom.DatabaseOptimizationManager()
    result = manager.optimize_connection_pool(pool_name="payments")
    assert result["optimization_applied"] is True
    assert result["current_metrics"]["pool"] == "payments"
    assert "increase-pool" in result["recommendations"]


def test_optimize_connection_pool_unavailable():
    manager = dom.DatabaseOptimizationManager()
    manager.connection_optimizer = None
    assert manager.optimize_connection_pool() == {"error": "Connection optimizer not available"}


def test_setup_query_cache(fake_optimizer_modules):
    manager = dom.DatabaseOptimizationManager()
    result = manager.setup_query_cache(cache_ttl_seconds=120)
    assert result["cache_enabled"] is True
    assert result["ttl_seconds"] == 120
    assert result["setup_successful"] is True
    assert _FakeCacheOptimizer.configured[-1]["ttl"] == 120


def test_setup_query_cache_unavailable():
    manager = dom.DatabaseOptimizationManager()
    manager.cache_optimizer = None
    assert manager.setup_query_cache() == {"error": "Cache optimizer not available"}


def test_get_optimization_recommendations(fake_optimizer_modules):
    manager = dom.DatabaseOptimizationManager()
    recs = manager.get_optimization_recommendations()
    assert len(recs) == 1
    assert recs[0]["expected_improvement"] == 0.25


def test_run_comprehensive_optimization(fake_optimizer_modules):
    manager = dom.DatabaseOptimizationManager()
    result = manager.run_comprehensive_optimization()
    assert result["overall_status"] == "complete"
    assert "query_optimization" in result
    assert "connection_optimization" in result
    assert "cache_optimization" in result
    assert manager.status.last_optimization_run is not None


def test_get_optimization_status(fake_optimizer_modules):
    manager = dom.DatabaseOptimizationManager()
    manager.run_comprehensive_optimization()
    status = manager.get_optimization_status()
    assert status["query_optimization_enabled"]
    assert status["total_optimizations_applied"] > 0
    assert status["last_optimization_run"] is not None


def test_record_query_execution(fake_optimizer_modules):
    manager = dom.DatabaseOptimizationManager()
    manager.record_query_execution(
        query_text="SELECT 1", duration_ms=12.0, database="db", table_name="t"
    )
    assert len(manager.query_optimizer.recorded) == 1
    assert manager.query_optimizer.recorded[0]["query_text"] == "SELECT 1"

    manager.record_query(query="SELECT 2", duration_ms=5.0, database="db2")
    assert manager.query_optimizer.recorded[-1]["query_text"] == "SELECT 2"


def test_record_query_execution_short_circuits():
    manager = dom.DatabaseOptimizationManager()
    manager.query_optimizer = None
    # Should return silently without raising or re-importing
    manager.record_query_execution(duration_ms=10.0)


def test_manager_load_failure_paths(monkeypatch):
    monkeypatch.setattr(query_opt_mod, "DatabaseQueryOptimizer", _RaisingOptimizer)
    monkeypatch.setattr(conn_opt_mod, "DatabaseConnectionOptimizer", _RaisingOptimizer)
    monkeypatch.setattr(cache_opt_mod, "DatabaseCacheOptimizer", _RaisingOptimizer)
    manager = dom.DatabaseOptimizationManager()
    assert not manager.status.query_optimization_enabled
    assert not manager.status.connection_optimization_enabled
    assert not manager.status.cache_optimization_enabled
    result = manager.run_comprehensive_optimization()
    assert result["overall_status"] == "failed"


def test_analyze_slow_queries_exception(monkeypatch):
    monkeypatch.setattr(query_opt_mod, "DatabaseQueryOptimizer", _QueryOptimizerRaisesAnalyze)
    manager = dom.DatabaseOptimizationManager()
    result = manager.analyze_slow_queries()
    assert "error" in result
    assert "analysis failure" in result["error"]


def test_optimize_connection_pool_exception(monkeypatch):
    monkeypatch.setattr(
        conn_opt_mod, "DatabaseConnectionOptimizer", _ConnectionOptimizerRaisesMetrics
    )
    manager = dom.DatabaseOptimizationManager()
    result = manager.optimize_connection_pool()
    assert "error" in result
    assert "metrics failure" in result["error"]


def test_optimize_connection_pool_no_recommendations(monkeypatch):
    monkeypatch.setattr(
        conn_opt_mod,
        "DatabaseConnectionOptimizer",
        _ConnectionOptimizerNoRecommendations,
    )
    manager = dom.DatabaseOptimizationManager()
    result = manager.optimize_connection_pool()
    assert result["optimization_applied"] is True
    assert result["recommendations"] == []


def test_setup_query_cache_exception(monkeypatch):
    monkeypatch.setattr(cache_opt_mod, "DatabaseCacheOptimizer", _CacheOptimizerRaisesConfigure)
    manager = dom.DatabaseOptimizationManager()
    result = manager.setup_query_cache()
    assert "error" in result
    assert "cache failure" in result["error"]


def test_setup_query_cache_no_configure(monkeypatch):
    monkeypatch.setattr(cache_opt_mod, "DatabaseCacheOptimizer", _CacheOptimizerNoConfigure)
    manager = dom.DatabaseOptimizationManager()
    result = manager.setup_query_cache()
    assert result["setup_successful"] is True
    assert result["cache_enabled"] is True


def test_get_optimization_recommendations_exception(monkeypatch):
    monkeypatch.setattr(query_opt_mod, "DatabaseQueryOptimizer", _QueryOptimizerRaisesGenerate)
    manager = dom.DatabaseOptimizationManager()
    assert manager.get_optimization_recommendations() == []


def test_record_query_execution_exception(monkeypatch):
    monkeypatch.setattr(query_opt_mod, "DatabaseQueryOptimizer", _QueryOptimizerRaisesRecord)
    manager = dom.DatabaseOptimizationManager()
    manager.record_query_execution(query_text="SELECT 1", duration_ms=10.0)


def test_run_comprehensive_optimization_exception(monkeypatch):
    monkeypatch.setattr(query_opt_mod, "DatabaseQueryOptimizer", _FakeQueryOptimizer)
    monkeypatch.setattr(conn_opt_mod, "DatabaseConnectionOptimizer", _FakeConnectionOptimizer)
    monkeypatch.setattr(cache_opt_mod, "DatabaseCacheOptimizer", _FakeCacheOptimizer)
    manager = dom.DatabaseOptimizationManager()
    manager.analyze_slow_queries = MagicMock(side_effect=RuntimeError("boom"))
    result = manager.run_comprehensive_optimization()
    assert "error" in result["query_optimization"]
    assert result["overall_status"] == "partial"


def test_get_database_optimization_manager_singleton(monkeypatch):
    monkeypatch.setattr(dom, "_optimization_manager", None)
    first = dom.get_database_optimization_manager()
    second = dom.get_database_optimization_manager()
    assert first is second


# ---------------------------------------------------------------------------
# core/dependency_injection.py
# ---------------------------------------------------------------------------
def test_container_register_get_and_stats():
    container = di.DIContainer()
    container.register_factory("counter", lambda: {"count": 0})
    assert container.get("counter") is container.get("counter")
    assert container.get_stats()["registered_factories"] == 1

    container.register_instance("settings", {"x": 1})
    assert container.get("settings") == {"x": 1}

    with pytest.raises(KeyError, match="Service not registered"):
        container.get("missing")


def test_container_context():
    container = di.DIContainer()
    container.register_factory("x", lambda: 1)
    container.set_context({"x": 42})
    assert container.get("x") == 42
    container.clear_context()
    assert container.get("x") == 1


@pytest.mark.asyncio
async def test_container_async_and_shutdown():
    class _FakeService:
        def __init__(self):
            self.value = 7

        def initialize(self):
            self.value = 8

    class _FakeLifecycle:
        async def shutdown(self, instance):
            instance.value = 9

    container = di.DIContainer()
    container.register_factory(
        "svc",
        _FakeService,
        singleton=True,
        lifecycle=_FakeLifecycle(),
    )
    inst = container.get_async("svc")
    assert isinstance(inst, _FakeService)
    assert inst.value == 8
    await container.shutdown()
    assert inst.value == 9


def test_inject_decorator(monkeypatch):
    container = di.DIContainer()
    container.register_factory("service", lambda: "injected")
    monkeypatch.setattr(di, "di_container", container)

    @di.inject("service")
    async def handler(service, extra):
        return f"{service}-{extra}"

    assert asyncio.run(handler("arg")) == "injected-arg"


def test_inject_context_decorator(monkeypatch):
    container = di.DIContainer()
    container.register_factory("cfg", lambda: "default")
    monkeypatch.setattr(di, "di_container", container)

    @di.inject_context({"cfg": "override"})
    async def handler():
        return di.di_container.get("cfg")

    assert asyncio.run(handler()) == "override"
    assert di.di_container.get("cfg") == "default"


def test_setup_core_services(monkeypatch):
    container = di.DIContainer()
    monkeypatch.setattr(di, "di_container", container)

    fake_db = types.ModuleType("core.db_engine")
    fake_db.AsyncSessionLocal = MagicMock(name="AsyncSessionLocal")
    monkeypatch.setitem(sys.modules, "core.db_engine", fake_db)

    fake_config = types.ModuleType("config")
    fake_config.REDIS_HOST = "localhost"
    fake_config.REDIS_PORT = 6379
    fake_config.REDIS_DB = 0
    monkeypatch.setitem(sys.modules, "config", fake_config)

    fake_redis = types.ModuleType("redis")
    fake_redis.Redis = MagicMock(name="Redis")
    monkeypatch.setitem(sys.modules, "redis", fake_redis)

    fake_ai = types.ModuleType("core.ai_engine")
    fake_ai.get_llm_router = MagicMock(return_value="router")
    monkeypatch.setitem(sys.modules, "core.ai_engine", fake_ai)

    fake_alert = types.ModuleType("core.alert_service")
    fake_alert.AlertService = MagicMock(return_value="alert-svc")
    monkeypatch.setitem(sys.modules, "core.alert_service", fake_alert)

    result = di.setup_core_services()
    assert result["status"] == "success"
    assert result["stats"]["registered_factories"] == 4
    assert container.get("ai_engine") == "router"
    assert container.get("database") is fake_db.AsyncSessionLocal


def test_setup_dependency_injection(monkeypatch):
    container = di.DIContainer()
    monkeypatch.setattr(di, "di_container", container)

    # Ensure imports in setup_core_services resolve to harmless fakes.
    for name, attrs in {
        "core.db_engine": {"AsyncSessionLocal": MagicMock()},
        "config": {"REDIS_HOST": "h", "REDIS_PORT": 1, "REDIS_DB": 0},
        "redis": {"Redis": MagicMock()},
        "core.ai_engine": {"get_llm_router": lambda: "router"},
        "core.alert_service": {"AlertService": MagicMock()},
    }.items():
        mod = types.ModuleType(name)
        for k, v in attrs.items():
            setattr(mod, k, v)
        monkeypatch.setitem(sys.modules, name, mod)

    result = asyncio.run(di.setup_dependency_injection())
    assert result["status"] == "success"
    assert result["core_services"]["status"] == "success"


# ---------------------------------------------------------------------------
# core/caching_strategy.py
# ---------------------------------------------------------------------------
@pytest.fixture
def fresh_cache(monkeypatch):
    """Provide a caching_strategy module with isolated in-memory state."""
    monkeypatch.setattr(
        caching_strategy,
        "_cache_config",
        {
            "enabled": True,
            "default_ttl_seconds": 300,
            "max_size": 1000,
            "cache_backend": "memory",
            "cache_key_prefix": "test",
            "compression_enabled": False,
            "serialization_format": "json",
        },
    )
    monkeypatch.setattr(caching_strategy, "_memory_cache", {})
    monkeypatch.setattr(
        caching_strategy,
        "_cache_stats",
        {"hits": 0, "misses": 0, "evictions": 0, "size": 0},
    )


def test_configure_and_basic_checks(fresh_cache):
    caching_strategy.configure_caching_strategy(
        default_ttl_seconds=60,
        max_size=500,
        cache_backend="redis",
        cache_key_prefix="test",
    )
    config = caching_strategy.get_cache_config()
    assert config["enabled"] is True
    assert config["cache_backend"] == "redis"
    assert config["max_size"] == 500
    assert caching_strategy.is_caching_enabled() is True
    assert caching_strategy.generate_cache_key("foo") == "test:foo"
    assert caching_strategy.generate_cache_key("foo", prefix="x") == "x:foo"


def test_set_get_delete_and_clear(fresh_cache):
    assert caching_strategy.set_cache("k1", {"a": 1}) is True
    assert caching_strategy.get_cache("k1") == {"a": 1}
    assert caching_strategy.delete_cache("k1") is True
    assert caching_strategy.get_cache("k1") is None
    assert caching_strategy.delete_cache("k1") is False

    caching_strategy.set_cache("x", 1)
    caching_strategy.set_cache("y", 2)
    assert caching_strategy.clear_cache() == 2
    assert caching_strategy.get_cache("x") is None


def test_cache_expiry(fresh_cache, monkeypatch):
    from datetime import datetime, timedelta, timezone

    class _AdvancingNow:
        _now = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

        @classmethod
        def now(cls, tz=None):
            return cls._now

    monkeypatch.setattr(caching_strategy, "datetime", _AdvancingNow)

    caching_strategy.set_cache("expires", "value", ttl_seconds=10)
    _AdvancingNow._now = datetime(2024, 1, 1, 0, 0, 30, tzinfo=timezone.utc)
    assert caching_strategy.get_cache("expires") is None
    assert caching_strategy.get_cache_statistics()["misses"] == 1


def test_max_size_eviction(fresh_cache, monkeypatch):
    monkeypatch.setattr(
        caching_strategy, "_cache_config", {**caching_strategy._cache_config, "max_size": 1}
    )
    caching_strategy.set_cache("first", 1)
    caching_strategy.set_cache("second", 2)
    assert caching_strategy.get_cache("first") is None
    assert caching_strategy.get_cache("second") == 2
    assert caching_strategy.get_cache_statistics()["evictions"] == 1


def test_cache_decorator(fresh_cache):
    calls = []

    @caching_strategy.cache_decorator(ttl_seconds=120)
    def expensive(x):
        calls.append(x)
        return x * 2

    assert expensive(5) == 10
    assert expensive(5) == 10
    assert len(calls) == 1
    assert expensive(7) == 14
    assert len(calls) == 2


def test_invalidate_pattern(fresh_cache):
    caching_strategy.set_cache("user:1", 1)
    caching_strategy.set_cache("user:2", 2)
    caching_strategy.set_cache("order:1", 3)
    count = caching_strategy.invalidate_pattern("user:")
    assert count == 2
    assert caching_strategy.get_cache("user:1") is None
    assert caching_strategy.get_cache("order:1") == 3


def test_cache_statistics_and_info(fresh_cache):
    caching_strategy.get_cache("missing")
    caching_strategy.set_cache("present", [1, 2, 3])
    caching_strategy.get_cache("present")
    stats = caching_strategy.get_cache_statistics()
    assert stats["hits"] == 1
    assert stats["misses"] == 1
    assert stats["hit_rate"] == 50.0
    assert stats["size"] == 1

    info = caching_strategy.get_cache_info()
    assert "present" in info["keys"][0]
    assert info["statistics"]["hits"] == 1

    caching_strategy.reset_cache_statistics()
    assert caching_strategy.get_cache_statistics()["hits"] == 0


def test_disabled_cache_paths(fresh_cache):
    caching_strategy._cache_config["enabled"] = False
    assert caching_strategy.set_cache("k", 1) is False
    assert caching_strategy.get_cache("k") is None
    assert caching_strategy.delete_cache("k") is False
    assert caching_strategy.invalidate_pattern("k") == 0


def test_get_cache_json_fallback(fresh_cache):
    caching_strategy._memory_cache["test:raw"] = {
        "value": "not-json",
        "expiry": float("inf"),
        "created": 0,
    }
    assert caching_strategy.get_cache("raw") == "not-json"


def test_set_cache_error_path(fresh_cache, monkeypatch):
    original_dumps = json.dumps
    monkeypatch.setattr(
        caching_strategy.json,
        "dumps",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    assert caching_strategy.set_cache("bad", {"a": 1}) is False
