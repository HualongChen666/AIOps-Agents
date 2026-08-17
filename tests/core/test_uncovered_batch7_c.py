# -*- coding: utf-8 -*-
"""Functional tests for core.redis_cluster, core.resilience, core.real_integration,
core.priority.dynamic and core.vector_pipeline."""

import asyncio
import copy
import datetime as dt
import importlib
import sys
import types
from unittest.mock import AsyncMock, MagicMock

import pytest

import core.ai_engine as ai_engine
import core.real_integration as real_integration
import core.redis_cluster as redis_cluster
import core.resilience as resilience
import core.vector_pipeline as vector_pipeline
from core.priority.assessor import BusinessCriticality, BusinessImpact
from core.priority.dynamic import DynamicPriorityAdjuster, PriorityAdjustment
from core.priority.ranker import PriorityRank

pytestmark = [pytest.mark.core]


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------
_DEFAULT_REDIS_CONFIG = copy.deepcopy(redis_cluster._redis_cluster_config)


@pytest.fixture(autouse=True)
def _reset_redis_cluster_state():
    """Reset the global Redis cluster state before each test."""
    redis_cluster._redis_cluster_config = copy.deepcopy(_DEFAULT_REDIS_CONFIG)
    redis_cluster._node_health = {}
    redis_cluster._current_master = ""


class _FakeRedisReader:
    def __init__(self, response):
        self._response = response

    async def readline(self):
        return self._response


class _FakeRedisWriter:
    def __init__(self):
        self.written = b""

    def write(self, data):
        self.written += data

    async def drain(self):
        pass

    def close(self):
        pass

    async def wait_closed(self):
        pass


def _patch_resilience_delays(monkeypatch):
    monkeypatch.setattr("core.resilience.time.sleep", lambda s: None)

    async def _fake_async_sleep(delay):
        return None

    monkeypatch.setattr("core.resilience.asyncio.sleep", _fake_async_sleep)


# ---------------------------------------------------------------------------
# core.redis_cluster
# ---------------------------------------------------------------------------
def test_configure_and_get_redis_cluster_config():
    sentinel_config = {"master_name": "mymaster", "sentinels": [{"host": "s1", "port": 26379}]}
    cluster_config = {"slots": 16384, "replicas": 2}
    nodes = [{"host": "r1", "port": 6379, "role": "master"}]

    redis_cluster.configure_redis_cluster(
        mode="sentinel",
        nodes=nodes,
        sentinel_config=sentinel_config,
        cluster_config=cluster_config,
    )

    config = redis_cluster.get_redis_cluster_config()
    assert config["enabled"] is True
    assert config["mode"] == "sentinel"
    assert config["nodes"] == nodes
    assert config["sentinel_config"] == sentinel_config
    assert config["cluster_config"] == cluster_config
    assert redis_cluster.is_redis_cluster_enabled() is True
    assert redis_cluster.get_redis_mode() == "sentinel"
    assert redis_cluster.get_node_health() == {
        "node_0": {
            "status": "unknown",
            "last_check": None,
            "latency_ms": None,
            "role": "master",
        }
    }


def test_connection_strings():
    redis_cluster.configure_redis_cluster(
        mode="standalone",
        nodes=[{"host": "localhost", "port": 6379}],
    )
    assert redis_cluster.get_connection_string() == "redis://localhost:6379"

    redis_cluster.configure_redis_cluster(
        mode="cluster",
        nodes=[
            {"host": "c1", "port": 7000},
            {"host": "c2", "port": 7001},
        ],
    )
    assert redis_cluster.get_connection_string() == "redis-cluster://c1:7000,c2:7001"

    redis_cluster.configure_redis_cluster(
        mode="sentinel",
        sentinel_config={
            "master_name": "mymaster",
            "sentinels": [{"host": "s1", "port": 26379}, {"host": "s2", "port": 26379}],
        },
    )
    assert redis_cluster.get_connection_string() == "sentinel://mymaster@s1:26379,s2:26379"

    redis_cluster._redis_cluster_config["enabled"] = False
    assert redis_cluster.get_connection_string() is None

    redis_cluster._redis_cluster_config["enabled"] = True
    redis_cluster._redis_cluster_config["mode"] = "unknown"
    assert redis_cluster.get_connection_string() is None


@pytest.mark.parametrize(
    "response,expected_status",
    [
        (b"+PONG\r\n", "healthy"),
        (b"-ERR\r\n", "unhealthy"),
    ],
)
def test_check_node_health(monkeypatch, response, expected_status):
    async def _open(host, port):
        return _FakeRedisReader(response), _FakeRedisWriter()

    monkeypatch.setattr("core.redis_cluster.asyncio.open_connection", _open)
    redis_cluster.configure_redis_cluster(
        mode="standalone",
        nodes=[{"host": "localhost", "port": 6379, "role": "master"}],
    )

    result = asyncio.run(redis_cluster.check_node_health(0))
    assert result["status"] == expected_status
    assert result["role"] == "master"
    assert result["last_check"] is not None


def test_check_node_health_unreachable(monkeypatch):
    async def _open(host, port):
        raise ConnectionRefusedError("refused")

    monkeypatch.setattr("core.redis_cluster.asyncio.open_connection", _open)
    redis_cluster.configure_redis_cluster(
        mode="standalone",
        nodes=[{"host": "localhost", "port": 6379, "role": "master"}],
    )

    result = asyncio.run(redis_cluster.check_node_health(0))
    assert result["status"] == "unhealthy"
    assert "error" in result


def test_check_node_health_missing_node():
    result = asyncio.run(redis_cluster.check_node_health(99))
    assert result["status"] == "unhealthy"
    assert "is not configured" in result["error"]


def test_check_all_nodes_health(monkeypatch):
    responses = [b"+PONG\r\n", b"-ERR\r\n"]

    async def _open(host, port):
        return _FakeRedisReader(responses.pop(0)), _FakeRedisWriter()

    monkeypatch.setattr("core.redis_cluster.asyncio.open_connection", _open)
    redis_cluster.configure_redis_cluster(
        mode="cluster",
        nodes=[
            {"host": "n0", "port": 6379, "role": "master"},
            {"host": "n1", "port": 6380, "role": "replica"},
        ],
    )

    results = asyncio.run(redis_cluster.check_all_nodes_health())
    assert results["node_0"]["status"] == "healthy"
    assert results["node_1"]["status"] == "unhealthy"


def test_node_role_queries_and_promotion():
    redis_cluster._node_health = {
        "node_0": {"status": "healthy", "role": "master"},
        "node_1": {"status": "healthy", "role": "replica"},
        "node_2": {"status": "healthy", "role": "replica"},
    }

    assert redis_cluster.get_healthy_nodes() == ["node_0", "node_1", "node_2"]
    assert redis_cluster.get_master_nodes() == ["node_0"]
    assert redis_cluster.get_replica_nodes() == ["node_1", "node_2"]

    assert asyncio.run(redis_cluster.promote_replica_to_master(1)) is True
    assert redis_cluster.get_current_master() == "node_1"
    assert redis_cluster.get_master_nodes() == ["node_0", "node_1"]


def test_perform_failover_to_healthy_replica():
    redis_cluster.configure_redis_cluster(
        mode="cluster",
        nodes=[
            {"host": "n0", "port": 6379, "role": "master"},
            {"host": "n1", "port": 6380, "role": "replica"},
        ],
    )
    redis_cluster._node_health["node_0"] = {"status": "unhealthy", "role": "master"}
    redis_cluster._node_health["node_1"] = {"status": "healthy", "role": "replica"}

    assert asyncio.run(redis_cluster.perform_failover()) is True
    assert redis_cluster.get_current_master() == "node_1"


def test_perform_failover_no_healthy_replicas():
    redis_cluster.configure_redis_cluster(
        mode="standalone",
        nodes=[{"host": "n0", "port": 6379, "role": "master"}],
    )
    redis_cluster._node_health["node_0"] = {"status": "unhealthy", "role": "master"}

    assert asyncio.run(redis_cluster.perform_failover()) is False


def test_perform_failover_healthy_master():
    redis_cluster.configure_redis_cluster(
        mode="standalone",
        nodes=[{"host": "n0", "port": 6379, "role": "master"}],
    )
    redis_cluster._node_health["node_0"] = {"status": "healthy", "role": "master"}

    assert asyncio.run(redis_cluster.perform_failover()) is True
    assert redis_cluster.get_current_master() == ""


def test_get_cluster_status():
    redis_cluster.configure_redis_cluster(
        mode="cluster",
        nodes=[{"host": "n0", "port": 6379}],
    )
    redis_cluster._node_health["node_0"] = {"status": "healthy", "role": "master"}
    redis_cluster._current_master = "node_0"

    status = redis_cluster.get_cluster_status()
    assert status["enabled"] is True
    assert status["mode"] == "cluster"
    assert status["node_count"] == 1
    assert status["current_master"] == "node_0"
    assert status["health_status"]["node_0"]["status"] == "healthy"


# ---------------------------------------------------------------------------
# core.resilience
# ---------------------------------------------------------------------------
def test_retry_sync_success(monkeypatch):
    _patch_resilience_delays(monkeypatch)

    @resilience.retry_with_backoff(max_retries=2, base_delay=0, exceptions=(ValueError,))
    def maybe_fail(times):
        if times[0] < 2:
            times[0] += 1
            raise ValueError("not yet")
        return "done"

    assert maybe_fail([0]) == "done"


def test_retry_sync_exhausted(monkeypatch):
    _patch_resilience_delays(monkeypatch)

    @resilience.retry_with_backoff(max_retries=1, base_delay=0, exceptions=(ValueError,))
    def always_fail():
        raise ValueError("boom")

    with pytest.raises(ValueError, match="boom"):
        always_fail()


def test_retry_async_success(monkeypatch):
    _patch_resilience_delays(monkeypatch)

    @resilience.retry_with_backoff(max_retries=2, base_delay=0, exceptions=(RuntimeError,))
    async def async_maybe_fail(times):
        if times[0] < 2:
            times[0] += 1
            raise RuntimeError("not yet")
        return "async-done"

    assert asyncio.run(async_maybe_fail([0])) == "async-done"


def test_retry_async_exhausted(monkeypatch):
    _patch_resilience_delays(monkeypatch)

    @resilience.retry_with_backoff(max_retries=1, base_delay=0, exceptions=(RuntimeError,))
    async def async_always_fail():
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        asyncio.run(async_always_fail())


def test_retry_on_retry_callback_and_callback_error(monkeypatch, caplog):
    _patch_resilience_delays(monkeypatch)
    logged = []

    def on_retry(exc, attempt):
        logged.append((str(exc), attempt))
        if attempt == 2:
            raise RuntimeError("callback failure")

    calls = {"count": 0}

    @resilience.retry_with_backoff(
        max_retries=3, base_delay=0, exceptions=(ValueError,), on_retry=on_retry
    )
    def fail_a_few_times():
        calls["count"] += 1
        raise ValueError("retry")

    with pytest.raises(ValueError):
        fail_a_few_times()

    assert len(logged) == 3
    assert any(msg for msg in caplog.text.split("\n") if "callback failure" in msg)


def test_retry_async_on_retry_exception(monkeypatch, caplog):
    _patch_resilience_delays(monkeypatch)
    logged = []

    def on_retry(exc, attempt):
        logged.append(attempt)
        if attempt == 2:
            raise RuntimeError("callback failure")

    calls = {"count": 0}

    @resilience.retry_with_backoff(
        max_retries=3, base_delay=0, exceptions=(ValueError,), on_retry=on_retry
    )
    async def async_fail():
        calls["count"] += 1
        raise ValueError("retry")

    with pytest.raises(ValueError):
        asyncio.run(async_fail())

    assert len(logged) == 3
    assert any("callback failure" in msg for msg in caplog.text.split("\n"))


def test_circuit_breaker_states(monkeypatch):
    current_time = {"t": 0}
    monkeypatch.setattr("core.resilience.time.time", lambda: current_time["t"])

    cb = resilience.CircuitBreaker(failure_threshold=2, recovery_timeout=10)
    assert cb._is_open() is False

    current_time["t"] = 100
    cb.record_failure()
    assert cb.open is False
    cb.record_failure()
    assert cb.open is True

    assert cb._is_open() is True

    cb2 = resilience.CircuitBreaker(failure_threshold=1, recovery_timeout=5)
    current_time["t"] = 200
    cb2.record_failure()
    assert cb2.open is True

    current_time["t"] = 206
    assert cb2._is_open() is False
    assert cb2.open is False
    cb2.record_success()
    assert cb2.failures == 0

    # record_success while the circuit is open should close it
    cb3 = resilience.CircuitBreaker(failure_threshold=1, recovery_timeout=60)
    current_time["t"] = 300
    cb3.record_failure()
    assert cb3.open is True
    cb3.record_success()
    assert cb3.open is False


def test_circuit_breaker_call_and_call_async(monkeypatch):
    _patch_resilience_delays(monkeypatch)

    cb = resilience.CircuitBreaker(failure_threshold=1)

    def success():
        return "ok"

    assert cb.call(success) == "ok"
    assert cb.failures == 0

    cb.record_failure()
    assert cb.open is True
    with pytest.raises(RuntimeError, match="is OPEN"):
        cb.call(success)

    cb2 = resilience.CircuitBreaker(failure_threshold=1)
    cb2.record_failure()

    async def async_ok():
        return "async-ok"

    with pytest.raises(RuntimeError, match="is OPEN"):
        asyncio.run(cb2.call_async(async_ok))

    cb3 = resilience.CircuitBreaker(failure_threshold=2)
    cb3.record_failure()
    cb3.record_failure()
    assert cb3.open is True
    cb3.record_success()
    assert cb3.open is False

    # call_async with a sync fallback function
    cb4 = resilience.CircuitBreaker(failure_threshold=2)
    assert asyncio.run(cb4.call_async(lambda: "sync-via-async")) == "sync-via-async"


def test_circuit_breaker_decorators(monkeypatch):
    _patch_resilience_delays(monkeypatch)

    @resilience.circuit_breaker(failure_threshold=2, name="sync_cb")
    def decorated_sync():
        return "sync"

    assert decorated_sync() == "sync"

    @resilience.circuit_breaker(failure_threshold=2, name="async_cb")
    async def decorated_async():
        return "async"

    assert asyncio.run(decorated_async()) == "async"


def test_fallback_sync_and_async(monkeypatch):
    _patch_resilience_delays(monkeypatch)

    @resilience.fallback_on_error(fallback=lambda *a, **k: "sync-fb")
    def sync_fail():
        raise ValueError("boom")

    assert sync_fail() == "sync-fb"

    async def async_fallback(*args, **kwargs):
        return "async-fb"

    @resilience.fallback_on_error(async_fallback)
    async def async_fail():
        raise RuntimeError("boom")

    assert asyncio.run(async_fail()) == "async-fb"

    @resilience.fallback_on_error(lambda *a, **k: "sync-fb2", log_warning=False)
    async def async_fail_sync_fallback():
        raise RuntimeError("boom")

    assert asyncio.run(async_fail_sync_fallback()) == "sync-fb2"


# ---------------------------------------------------------------------------
# core.real_integration
# ---------------------------------------------------------------------------
def _setup_real_integration_mocks(monkeypatch, fail_mode=False):
    """Provide deterministic fake modules for the real integration entry point."""
    real_integration._real_enhanced_cache = None
    modules = {}

    config_mod = types.ModuleType("config")
    config_mod.POSTGRES_URL = "postgresql+asyncpg://test"
    modules["config"] = config_mod

    # sqlalchemy
    sa_asyncio = types.ModuleType("sqlalchemy.ext.asyncio")
    new_engine = MagicMock()
    sa_asyncio.create_async_engine = MagicMock(return_value=new_engine)
    if fail_mode:
        sa_asyncio.create_async_engine = MagicMock(side_effect=RuntimeError("db fail"))
    modules["sqlalchemy.ext.asyncio"] = sa_asyncio

    # core.db_engine
    db_engine_mod = types.ModuleType("core.db_engine")
    old_engine = MagicMock()
    old_engine.dispose = AsyncMock(return_value=None)
    db_engine_mod.engine = old_engine
    modules["core.db_engine"] = db_engine_mod

    # connection pool optimization
    cpo_mod = types.ModuleType("core.connection_pool_optimization")
    cpo_mod.CONNECTION_POOL_CONFIG = {
        "echo": False,
        "future": True,
        "pool_size": 20,
        "max_overflow": 40,
        "pool_timeout": 30,
        "pool_recycle": 3600,
        "pool_pre_ping": True,
    }
    modules["core.connection_pool_optimization"] = cpo_mod

    # core.ai_engine
    ai_engine_mod = types.ModuleType("core.ai_engine")
    ai_engine_mod.analyze = AsyncMock(return_value={"diagnosis": "ok"})
    modules["core.ai_engine"] = ai_engine_mod

    # core.ai_enhancement
    class FakeAIEnhancer:
        def __init__(self):
            self.cache = {}

        def generate_context_key(self, ctx):
            return "key"

        def get_cached_analysis(self, key):
            return self.cache.get(key)

        def get_context_suggestions(self, ctx):
            return ["check metrics"]

        def cache_analysis(self, key, value):
            self.cache[key] = value

    ai_enhancement_mod = types.ModuleType("core.ai_enhancement")
    if fail_mode:

        def _raise_ai_enhancer():
            raise RuntimeError("ai fail")

        ai_enhancement_mod.get_ai_enhancer = _raise_ai_enhancer
    else:
        ai_enhancement_mod.get_ai_enhancer = lambda: FakeAIEnhancer()
    modules["core.ai_enhancement"] = ai_enhancement_mod

    # core.notify_engine
    notify_mod = types.ModuleType("core.notify_engine")
    notify_mod._post_webhook = MagicMock(return_value={"ok": True})
    modules["core.notify_engine"] = notify_mod

    # core.retry_enhanced
    retry_mod = types.ModuleType("core.retry_enhanced")

    class RetryStrategy:
        EXPONENTIAL_BACKOFF = "exp"

    class EnhancedRetry:
        def __init__(self, **kwargs):
            if fail_mode:
                raise RuntimeError("retry fail")
            self.kwargs = kwargs

        def __call__(self, func):
            return func

    retry_mod.RetryStrategy = RetryStrategy
    retry_mod.EnhancedRetry = EnhancedRetry
    modules["core.retry_enhanced"] = retry_mod

    # core.db_optimization
    if fail_mode:
        db_opt_mod = types.ModuleType("core.db_optimization")
    else:
        db_opt_mod = types.ModuleType("core.db_optimization")
        db_opt_mod.create_performance_indexes = AsyncMock(return_value="indexes created")
    modules["core.db_optimization"] = db_opt_mod

    # core.cache_helpers
    cache_mod = types.ModuleType("core.cache_helpers")

    class MultiLevelCache:
        def __init__(self, memory_ttl, redis_ttl):
            if fail_mode:
                raise RuntimeError("cache fail")
            self.memory_ttl = memory_ttl
            self.redis_ttl = redis_ttl

    cache_mod.MultiLevelCache = MultiLevelCache
    modules["core.cache_helpers"] = cache_mod

    for name, mod in modules.items():
        monkeypatch.setitem(sys.modules, name, mod)

    return modules, {"new_engine": new_engine, "old_engine": old_engine}


def test_apply_real_integrations_success(monkeypatch):
    monkeypatch.setattr(ai_engine, "analyze", ai_engine.analyze)
    modules, mocks = _setup_real_integration_mocks(monkeypatch, fail_mode=False)

    async def _run():
        real_integration.apply_real_integrations()
        current = asyncio.current_task()
        pending = [t for t in asyncio.all_tasks() if t is not current]
        if pending:
            await asyncio.gather(*pending)

    asyncio.run(_run())

    assert modules["core.db_engine"].engine is not None
    modules["sqlalchemy.ext.asyncio"].create_async_engine.assert_called_once_with(
        "postgresql+asyncpg://test",
        echo=False,
        future=True,
        pool_size=20,
        max_overflow=40,
        pool_timeout=30,
        pool_recycle=3600,
        pool_pre_ping=True,
    )
    assert real_integration._real_enhanced_cache is not None

    # core.ai_engine.analyze was replaced by the enhanced wrapper
    assert modules["core.ai_engine"].analyze is not None


def test_apply_real_integrations_handles_failures(monkeypatch, caplog):
    monkeypatch.setattr(ai_engine, "analyze", ai_engine.analyze)
    _setup_real_integration_mocks(monkeypatch, fail_mode=True)

    async def _run():
        real_integration.apply_real_integrations()
        current = asyncio.current_task()
        pending = [t for t in asyncio.all_tasks() if t is not current]
        if pending:
            await asyncio.gather(*pending)

    asyncio.run(_run())
    assert real_integration._real_enhanced_cache is None
    assert "Failed to apply database optimization" in caplog.text
    assert "Failed to integrate AI enhancement" in caplog.text
    assert "Failed to apply enhanced retry" in caplog.text
    assert "Failed to create performance indexes" in caplog.text
    assert "Failed to initialize enhanced cache" in caplog.text


# ---------------------------------------------------------------------------
# core.priority.dynamic
# ---------------------------------------------------------------------------
def _make_rank(alert_id, score, level, factors=None):
    factors = factors or {}
    impact = BusinessImpact(
        service="payment",
        impact_score=score,
        criticality=BusinessCriticality.CRITICAL,
        affected_users=1000,
        revenue_impact=100.0,
        sla_impact=True,
        factors=factors,
    )
    return PriorityRank(
        alert_id=alert_id,
        priority_score=score,
        priority_level=level,
        business_impact=impact,
    )


def test_adjust_priorities_no_change():
    adjuster = DynamicPriorityAdjuster()
    # age between 1 and 24 hours should not trigger age multipliers
    created = dt.datetime.now() - dt.timedelta(hours=2)
    rank = _make_rank("a1", 0.6, "P2", {"created_at": created})

    adjustments = adjuster.adjust_priorities([rank])
    assert adjustments == []
    assert rank.priority_level == "P2"


def test_adjust_priorities_high_load_deprioritizes_non_critical():
    adjuster = DynamicPriorityAdjuster()
    rank = _make_rank("a1", 0.6, "P2", {})
    adjustments = adjuster.adjust_priorities([rank], system_state={"system_load": 0.9})

    assert len(adjustments) == 1
    assert adjustments[0].old_priority == "P2"
    assert adjustments[0].new_priority == "P3"
    assert "high_system_load" in adjustments[0].reason


def test_adjust_priorities_high_load_ignores_p0():
    adjuster = DynamicPriorityAdjuster()
    rank = _make_rank("a1", 0.95, "P0", {})
    adjustments = adjuster.adjust_priorities([rank], system_state={"system_load": 0.95})
    assert adjustments == []


def test_adjust_priorities_low_load_escalates():
    adjuster = DynamicPriorityAdjuster()
    rank = _make_rank("a1", 0.82, "P1", {})
    adjuster.adjust_priorities([rank], system_state={"system_load": 0.1})
    assert rank.priority_level == "P0"


def test_adjust_priorities_old_age_deprioritizes():
    adjuster = DynamicPriorityAdjuster()
    now = dt.datetime.now()
    old_rank = _make_rank("old", 0.78, "P1", {"created_at": now - dt.timedelta(hours=26)})
    adjuster.adjust_priorities([old_rank])
    assert old_rank.priority_level == "P2"


def test_adjust_priorities_new_age_escalates():
    adjuster = DynamicPriorityAdjuster()
    now = dt.datetime.now()
    new_rank = _make_rank("new", 0.82, "P1", {"created_at": now - dt.timedelta(minutes=30)})
    adjuster.adjust_priorities([new_rank])
    assert new_rank.priority_level == "P0"


def test_adjust_priorities_related_surge_escalates():
    adjuster = DynamicPriorityAdjuster()
    rank = _make_rank("surge", 0.78, "P1", {})
    adjuster.adjust_priorities([rank], system_state={"related_alert_count": 10})
    assert rank.priority_level == "P0"
    assert rank.priority_score == pytest.approx(0.936)


def test_adjust_priorities_created_at_timestamp():
    adjuster = DynamicPriorityAdjuster()
    now = dt.datetime.now()
    timestamp = (now - dt.timedelta(hours=26)).timestamp()
    rank = _make_rank("ts", 0.78, "P1", {"created_at": timestamp})
    adjuster.adjust_priorities([rank])
    assert rank.priority_level == "P2"


def test_map_score_to_level_and_reason():
    adjuster = DynamicPriorityAdjuster()
    assert adjuster._map_score_to_level(0.95) == "P0"
    assert adjuster._map_score_to_level(0.8) == "P1"
    assert adjuster._map_score_to_level(0.6) == "P2"
    assert adjuster._map_score_to_level(0.4) == "P3"
    assert adjuster._map_score_to_level(0.1) == "P4"

    rank = _make_rank("r", 0.5, "P2", {})
    assert adjuster._determine_adjustment_reason(rank, 0.6, None) == "time_based_adjustment"
    assert (
        adjuster._determine_adjustment_reason(
            rank, 0.6, {"system_load": 0.9, "related_alert_count": 10}
        )
        == "high_system_load, related_alert_surge"
    )


def test_adjustment_history_filters():
    adjuster = DynamicPriorityAdjuster()
    rank = _make_rank("a1", 0.45, "P2", {})
    adjuster.adjust_priorities([rank], system_state={"system_load": 0.9})

    assert len(adjuster.get_adjustment_history()) == 1
    assert len(adjuster.get_adjustment_history(alert_id="a1")) == 1
    assert len(adjuster.get_adjustment_history(alert_id="missing")) == 0
    assert len(adjuster.get_adjustment_history(since=dt.datetime.now() + dt.timedelta(days=1))) == 0


# ---------------------------------------------------------------------------
# core.vector_pipeline
# ---------------------------------------------------------------------------
class _FakeNumpyArray:
    def __init__(self, data):
        self._data = data

    def tolist(self):
        return self._data


class _FakeSentenceTransformer:
    built = []

    def __init__(self, model_name):
        self.model_name = model_name
        self.dimension = 384
        _FakeSentenceTransformer.built.append(model_name)

    def encode(self, texts, convert_to_numpy=True, show_progress_bar=False):
        return _FakeNumpyArray([[0.1, 0.2, 0.3] for _ in list(texts)])

    def get_sentence_embedding_dimension(self):
        return self.dimension


def _fake_sentence_transformers_module():
    mod = types.ModuleType("sentence_transformers")
    mod.SentenceTransformer = _FakeSentenceTransformer
    return mod


@pytest.fixture
def reset_vector_pipeline(monkeypatch):
    """Reset the vector pipeline singleton and inject a fake backend."""
    monkeypatch.setattr(vector_pipeline, "_model_instance", None)
    monkeypatch.setitem(sys.modules, "sentence_transformers", _fake_sentence_transformers_module())
    _FakeSentenceTransformer.built = []


def test_vector_pipeline_env_model_name(monkeypatch):
    monkeypatch.setenv("SENTENCE_TRANSFORMERS_MODEL", "custom-model")
    importlib.reload(vector_pipeline)
    assert vector_pipeline._SENTENCE_MODEL_NAME == "custom-model"
    monkeypatch.delenv("SENTENCE_TRANSFORMERS_MODEL")
    importlib.reload(vector_pipeline)
    assert vector_pipeline._SENTENCE_MODEL_NAME == "all-MiniLM-L6-v2"


def test_embed_documents_and_query(reset_vector_pipeline):
    docs = ["doc one", "doc two"]
    embeddings = vector_pipeline.embed_documents(docs)
    assert len(embeddings) == 2
    assert all(len(vec) == 3 for vec in embeddings)

    query = vector_pipeline.embed_query("query")
    assert isinstance(query, list)
    assert len(query) == 3


def test_model_dimension_and_singleton(reset_vector_pipeline):
    assert vector_pipeline.model_dimension() == 384
    assert vector_pipeline._model_instance is not None

    # second call must reuse the cached model
    vector_pipeline.embed_documents(["another"])
    assert len(_FakeSentenceTransformer.built) == 1


def test_model_load_import_error(monkeypatch):
    monkeypatch.setattr(vector_pipeline, "_model_instance", None)
    empty_mod = types.ModuleType("sentence_transformers")
    monkeypatch.setitem(sys.modules, "sentence_transformers", empty_mod)

    with pytest.raises(RuntimeError, match="sentence-transformers is required"):
        vector_pipeline._load_model()
