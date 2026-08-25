# -*- coding: utf-8 -*-
"""Targeted coverage tests for batch 29 (database cache, DI, RCA, AI, LLM router)."""

import asyncio  # noqa: F401  # Imported for test setup
import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest  # noqa: F401  # Imported for test setup

from core.ai.llm_router.capability_evaluator import (
    CapabilityEvaluator,
    ModelCapability,
    TaskType,
)
from core.database_cache_optimizer import (
    CacheEntry,
    CacheInvalidationPolicy,
    CacheMetrics,
    CacheStrategy,
    DatabaseCacheOptimizer,
    _Cache,
    get_database_cache_optimizer,
)
from core.dependency_injection import (
    DIContainer,
    ServiceLifecycle,
    inject,
    inject_context,
    setup_core_services,
    setup_dependency_injection,
)
from core.enhanced_ai_capabilities import (
    EnhancedAICapabilities,
    LearningMode,
    PredictionType,
)
from core.enhanced_root_cause_analyzer import (
    EnhancedRootCauseAnalyzer,
    HistoricalIncident,
    RCASeverity,
    RootCauseHypothesis,
    TopologyChange,
    TopologyChangeType,
    TopologyEdge,
    TopologyNode,
)

pytestmark = [pytest.mark.core]


def _run(coro):
    return asyncio.run(coro)


# =============================================================================
# core.database_cache_optimizer
# =============================================================================


def test_cache_entry_lifecycle():
    entry = CacheEntry("k", "v")
    assert not entry.is_expired()
    entry.touch()
    assert entry.access_count == 1

    entry2 = CacheEntry("k2", "v2", ttl_seconds=0.01)
    assert not entry2.is_expired()
    import time  # noqa: F401  # Imported for test setup

    time.sleep(0.02)
    assert entry2.is_expired()
    entry2.touch()
    assert entry2.access_count == 1


def test_cache_metrics_aliases():
    m = CacheMetrics("m", hit_count=5, miss_count=3)
    assert m.hits == 5
    assert m.misses == 3


def test_cache_lru_eviction():
    cache = _Cache("lru", strategy=CacheStrategy.LRU, size=2)
    cache.set("a", 1)
    cache.set("b", 2)
    cache.set("c", 3)
    assert cache.get("a") is None
    assert cache.get("b") == 2
    cache.set("d", 4)
    assert cache.get("b") == 2  # touched


def test_cache_lfu_eviction():
    cache = _Cache("lfu", strategy=CacheStrategy.LFU, size=2)
    cache.set("a", 1)
    cache.set("a", 1)
    cache.set("b", 2)
    cache.set("c", 3)
    assert cache.get("a") == 1
    assert cache.get("b") is None or cache.get("c") is not None


def test_cache_ttl_and_invalidate_clear():
    cache = _Cache("ttl", strategy=CacheStrategy.TTL, size=2)
    cache.set("a", 1)
    assert cache.get("a") == 1
    cache.invalidate("a")
    assert cache.get("a") is None
    cache.set("b", 2)
    cache.clear()
    assert cache.get("b") is None
    assert cache.get_stats()["hits"] == 1


def test_database_cache_optimizer_full_flow():
    opt = DatabaseCacheOptimizer({"default_cache_size": 2, "default_ttl_seconds": 0.01})
    assert opt.get_statistics()["total_caches"] == 0

    opt.create_cache("c1", cache_size=2, strategy=CacheStrategy.LRU)
    opt.create_cache("c1")  # duplicate warning path
    assert "c1" in opt.caches

    opt.set("c1", "SELECT 1", ["row"])
    assert opt.get("c1", "SELECT 1") == ["row"]
    assert opt.get("missing", "SELECT 1") is None

    # cache key with params
    opt.set("c1", "SELECT *", "data", params={"x": 1})
    assert opt.get("c1", "SELECT *", params={"x": 1}) == "data"
    assert opt.get("c1", "SELECT *", params={"x": 2}) is None

    assert opt.invalidate("no_cache") == 0
    assert opt.invalidate("c1", "SELECT 1") == 1
    assert opt.invalidate("c1", "SELECT 1") == 0
    assert opt.invalidate("c1") > 0
    assert opt.get("c1", "SELECT *", params={"x": 1}) is None


def test_database_cache_expiration_and_eviction():
    opt = DatabaseCacheOptimizer()
    opt.create_cache("c2", strategy=CacheStrategy.LRU, cache_size=1)
    opt.set("c2", "q1", "v1")
    opt.set("c2", "q2", "v2")
    assert opt.get("c2", "q1") is None
    assert opt.get("c2", "q2") == "v2"

    opt.create_cache("c3", strategy=CacheStrategy.LFU, cache_size=2)
    opt.set("c3", "q1", "v1")
    opt.set("c3", "q1", "v1")  # hit freq
    opt.set("c3", "q2", "v2")
    opt.set("c3", "q3", "v3")  # evict least freq

    opt.create_cache("c4", strategy=CacheStrategy.TTL, cache_size=2)
    opt.set("c4", "q1", "v1")
    opt.set("c4", "q2", "v2")
    opt.set("c4", "q3", "v3")


def test_database_cache_metrics_and_optimization():
    opt = DatabaseCacheOptimizer()
    opt.create_cache("c5", cache_size=100)
    opt.set("c5", "q1", "v1")
    opt.get("c5", "q1")
    opt.get("c5", "q2")
    metrics = opt.get_cache_metrics("c5")
    assert metrics is not None
    assert metrics.hit_rate > 0
    assert "c5" in opt.get_all_cache_metrics()

    # low hit rate
    opt2 = DatabaseCacheOptimizer()
    opt2.create_cache("c6", cache_size=10)
    opt2._update_metrics("c6", hit=False)
    opt2._update_metrics("c6", hit=False)
    rec = opt2.optimize_cache_size("c6", target_hit_rate=0.9)
    assert rec["recommendations"][0]["type"] == "increase_size"

    # high hit rate
    opt2.total_cache_hits = 100
    opt2.total_cache_misses = 0
    opt2._update_metrics("c6", hit=True)
    opt2._update_metrics("c6", hit=True)
    opt2._update_metrics("c6", hit=True)
    rec2 = opt2.optimize_cache_size("c6", target_hit_rate=0.1)
    assert rec2["recommendations"][0]["type"] == "decrease_size"

    # optimal
    opt3 = DatabaseCacheOptimizer()
    opt3.create_cache("c7", cache_size=10)
    opt3._update_metrics("c7", hit=True)
    opt3._update_metrics("c7", hit=True)
    opt3._update_metrics("c7", hit=False)
    rec3 = opt3.optimize_cache_size("c7", target_hit_rate=0.66)
    assert rec3["recommendations"][0]["type"] == "no_change"

    assert opt3.optimize_cache_size("missing") == {"error": "Cache not found"}


def test_database_cache_preload_and_cleanup():
    opt = DatabaseCacheOptimizer()
    opt.create_cache("pre", cache_size=10)
    opt.add_preload_query("pre", "SELECT 1")
    opt.add_preload_query("pre", "SELECT 2", priority=5)

    count = opt.preload_cache("pre", {"a": 1, "b": 2})
    assert count == 2

    def loader(query, params):
        if query == "SELECT 1":
            return "one"
        raise RuntimeError("boom")

    count = opt.preload_cache("pre", loader)
    assert count == 1

    opt.create_cache("c8", ttl_seconds=0.01)
    opt.set("c8", "q", "v")
    import time  # noqa: F401  # Imported for test setup

    time.sleep(0.02)
    assert opt.cleanup_expired_entries("c8") == 1
    assert opt.get_cache("c9", strategy=CacheStrategy.LFU).name == "c9"


# =============================================================================
# core.dependency_injection
# =============================================================================


def test_di_container_basic():
    c = DIContainer()
    c.register_factory("a", lambda: 42)
    assert c.get("a") == 42
    assert c.get("a") == 42  # singleton

    c.register_instance("b", "hello")
    assert c.get("b") == "hello"

    with pytest.raises(KeyError):
        c.get("missing")


def test_di_container_context():
    c = DIContainer()
    c.register_factory("ctx", lambda: "default")
    c.set_context({"ctx": "overridden"})
    assert c.get("ctx") == "overridden"
    c.clear_context()
    assert c.get("ctx") == "default"


async def _async_init_hook(self):
    return None


@pytest.mark.asyncio
async def test_di_container_async(monkeypatch):
    c = DIContainer()
    called = {"init": False, "shutdown": False}

    class FakeService:
        async def initialize(self):
            called["init"] = True

    class FakeLife:
        async def shutdown(self, instance):
            called["shutdown"] = True

    c.register_factory("svc", FakeService, lifecycle=FakeLife())
    c.get_async("svc")
    await asyncio.sleep(0)
    assert called["init"]

    await c.shutdown()
    assert called["shutdown"]

    # sync init
    c2 = DIContainer()
    c2.register_factory(
        "svc2",
        lambda: type("S", (), {"initialize": lambda: None})(),
    )
    c2.get_async("svc2")


def test_di_container_sync_shutdown_coroutine():
    c = DIContainer()

    class FakeLife:
        def shutdown(self, instance):
            async def _inner():
                return "done"

            return _inner()

    c.register_factory(
        "svc3", lambda: type("O", (), {"initialize": lambda s: None})(), lifecycle=FakeLife()
    )
    c.get_async("svc3")
    _run(c.shutdown())


def test_di_container_shutdown_exception(monkeypatch):
    c = DIContainer()

    class BadLife:
        async def shutdown(self, instance):
            raise RuntimeError("bad")

    c.register_factory("bad", lambda: None, lifecycle=BadLife())
    c._services["bad"] = "x"
    _run(c.shutdown())


def test_di_container_stats():
    c = DIContainer()
    c.register_factory("x", lambda: 1)
    c.register_instance("y", 2)
    stats = c.get_stats()
    assert stats["registered_factories"] == 1
    assert stats["singletons"] == 2


@pytest.mark.asyncio
async def test_inject_decorator(monkeypatch):
    fresh = DIContainer()
    fresh.register_factory("svc", lambda: "injected")
    monkeypatch.setattr("core.dependency_injection.di_container", fresh)

    @inject("svc")
    async def use_svc(svc, extra):
        return svc, extra

    result = await use_svc("arg")  # noqa: F841  # Variable for test verification
    assert result == ("injected", "arg")  # noqa: F841  # Variable for test verification


@pytest.mark.asyncio
async def test_inject_context_decorator(monkeypatch):
    fresh = DIContainer()
    fresh.register_factory("ctx", lambda: "base")
    monkeypatch.setattr("core.dependency_injection.di_container", fresh)

    @inject_context({"ctx": "ctxvalue"})
    async def use_ctx():
        return fresh.get("ctx")

    assert await use_ctx() == "ctxvalue"


def test_setup_core_services(monkeypatch):
    monkeypatch.setattr("core.db_engine.AsyncSessionLocal", "session")
    monkeypatch.setattr("config.REDIS_HOST", "localhost")
    monkeypatch.setattr("config.REDIS_PORT", 6379)
    monkeypatch.setattr("config.REDIS_DB", 0)
    fake_redis = MagicMock()
    monkeypatch.setattr("redis.Redis", lambda **kw: fake_redis)
    fake_router = MagicMock()
    monkeypatch.setattr("core.ai_engine.get_llm_router", lambda: fake_router)
    fake_alert = MagicMock()
    monkeypatch.setattr("core.alert_service.AlertService", lambda: fake_alert)

    result = setup_core_services()  # noqa: F841  # Variable for test verification
    assert result["status"] == "success"


def test_setup_core_services_failure(monkeypatch):
    def boom(*a, **kw):
        raise RuntimeError("bad")

    monkeypatch.setattr("core.dependency_injection.di_container.register_factory", boom)
    result = setup_core_services()  # noqa: F841  # Variable for test verification
    assert result["status"] == "error"


def test_setup_dependency_injection(monkeypatch):
    monkeypatch.setattr("core.db_engine.AsyncSessionLocal", "session")
    monkeypatch.setattr("config.REDIS_HOST", "localhost")
    monkeypatch.setattr("config.REDIS_PORT", 6379)
    monkeypatch.setattr("config.REDIS_DB", 0)
    monkeypatch.setattr("redis.Redis", MagicMock())
    monkeypatch.setattr("core.ai_engine.get_llm_router", lambda: MagicMock())
    monkeypatch.setattr("core.alert_service.AlertService", lambda: MagicMock())

    result = _run(setup_dependency_injection())  # noqa: F841  # Variable for test verification
    assert result["status"] == "success"


# =============================================================================
# core.enhanced_root_cause_analyzer
# =============================================================================


@pytest.fixture
def rca():
    analyzer = EnhancedRootCauseAnalyzer()
    # prevent background loops in initialize
    analyzer._learning_loop = AsyncMock()
    return analyzer


def test_rca_dataclasses_and_enums():
    assert RCASeverity.CRITICAL.value == "critical"
    n = TopologyNode("1", "service", "svc")
    e = TopologyEdge("1", "2", "calls")
    c = TopologyChange(TopologyChangeType.ADD_NODE, datetime.datetime.now(), {})
    assert c.change_type == TopologyChangeType.ADD_NODE


def test_rca_initialization(monkeypatch):
    a = EnhancedRootCauseAnalyzer()
    monkeypatch.setattr(asyncio, "create_task", lambda c: None)
    _run(a.initialize())
    assert a.rca_classifier is not None


def test_rca_toplogy_discovery(monkeypatch):
    a = EnhancedRootCauseAnalyzer()
    info = _run(a.discover_topology())
    assert "nodes_count" in info

    # error path
    async def boom(*a, **kw):
        raise RuntimeError("boom")

    monkeypatch.setattr(a, "_discover_nodes", boom)
    info2 = _run(a.discover_topology())
    assert "error" in info2


def test_rca_detect_and_apply_changes():
    a = EnhancedRootCauseAnalyzer()
    n1 = TopologyNode("n1", "service", "svc1")
    n2 = TopologyNode("n2", "service", "svc2")
    changes = a._detect_topology_changes([n1, n2], [])
    assert len(changes) == 2
    assert all(c.change_type == TopologyChangeType.ADD_NODE for c in changes)

    # set known state then detect a removal
    a.nodes = {"n1": n1, "n2": n2}
    _run(a._update_topology([n2], []))
    assert any(c.change_type == TopologyChangeType.REMOVE_NODE for c in a.topology_changes)
    for c in a.topology_changes:
        _run(a._apply_topology_change(c))
    for ct in TopologyChangeType:
        _run(a._apply_topology_change(TopologyChange(ct, datetime.datetime.now(), {})))


def test_rca_build_causal_and_cross_layer():
    a = EnhancedRootCauseAnalyzer()
    a.nodes["db"] = TopologyNode("db", "database", "db")
    a.nodes["svc"] = TopologyNode("svc", "service", "svc")
    a.nodes["biz"] = TopologyNode("biz", "business", "biz")
    a.edges["db"].append(TopologyEdge("db", "svc", "reads"))
    a.edges["svc"].append(TopologyEdge("svc", "biz", "calls"))
    _run(a._build_causal_graph())
    _run(a._add_cross_layer_causality())
    assert a.causal_graph["db"] == {"svc"}
    assert a.causal_graph["svc"] == {"biz"}


def test_rca_analyze_root_causes():
    a = EnhancedRootCauseAnalyzer()
    a.causal_graph["db"].add("svc")
    a.causal_strength[("db", "svc")] = 0.9
    hypotheses = _run(a.analyze_root_causes({"svc"}))
    assert isinstance(hypotheses, list)

    # with context
    h2 = _run(a.analyze_root_causes({"svc"}, context={"x": 1}))
    assert isinstance(h2, list)

    # matching historical pattern
    a.pattern_similarity_threshold = 0.0
    inc = HistoricalIncident(
        id="i1",
        timestamp=datetime.datetime.now(),
        symptoms=["slow"],
        root_causes=["db"],
        resolution="restart",
        similarity_hash="sh",
    )
    _run(a.record_incident(inc))
    h3 = _run(a.analyze_root_causes({"svc"}))
    assert any(h.node_id == "db" for h in h3)


def test_rca_hypothesis_combination_and_ranking():
    a = EnhancedRootCauseAnalyzer()
    h1 = RootCauseHypothesis(
        node_id="db",
        confidence=0.8,
        explanation="x",
        evidence=["e1"],
        impact_score=0.7,
        severity=RCASeverity.HIGH,
    )
    h2 = RootCauseHypothesis(
        node_id="db",
        confidence=0.9,
        explanation="y",
        evidence=["e2"],
        impact_score=0.8,
        severity=RCASeverity.CRITICAL,
    )
    h3 = RootCauseHypothesis(
        node_id="cache",
        confidence=0.5,
        explanation="z",
        evidence=["e3"],
        impact_score=0.4,
        severity=RCASeverity.LOW,
    )
    combined = _run(a._combine_hypotheses([h1, h2], [h3]))
    assert len(combined) == 2
    ranked = _run(a._rank_hypotheses(combined))
    assert ranked[0].node_id == "db"
    assert a._severity_score(RCASeverity.LOW) == 0.4
    assert a._severity_score("x") == 0.5


def test_rca_prediction_and_verification():
    a = EnhancedRootCauseAnalyzer()
    preds = _run(a.predict_root_causes({"cpu": 0.9}))
    assert isinstance(preds, list)

    h = RootCauseHypothesis(
        node_id="n1",
        confidence=0.5,
        explanation="x",
        evidence=["e"],
        impact_score=0.5,
        severity=RCASeverity.MEDIUM,
    )
    assert _run(a.verify_root_cause(h)) is False
    a.nodes["n1"] = TopologyNode("n1", "service", "n1", health_status="unhealthy")
    a._evaluate_verification_evidence = AsyncMock(return_value=0.9)
    assert _run(a.verify_root_cause(h)) is True
    assert h.verification_status == "verified"


def test_rca_helpers():
    a = EnhancedRootCauseAnalyzer()
    a.nodes["n1"] = TopologyNode("n1", "service", "n1")
    a.causal_graph["n1"].add("n2")
    a.causal_graph["n2"].add("n1")  # cycle
    upstream = a._find_upstream_causes("n1")
    assert "n2" in upstream

    assert a._generate_similarity_hash({"a": 1}) == a._generate_similarity_hash({"a": 1})
    assert a._calculate_pattern_similarity("a", "b") == 0.0
    assert a._calculate_pattern_similarity("a", "a") == 1.0

    _run(a._load_historical_incidents())
    assert a._extract_features({"n1"}, None)["node_count"] == 1
    assert a._get_node_types({"n1"}) == ["service"]
    assert a._extract_ml_features(set(), None) == []
    assert a._generate_analysis_key({"a", "b"}, None) != ""

    assert _run(a._identify_critical_nodes()) == []
    assert _run(a._is_single_point_of_failure("x")) is False
    assert _run(a._analyze_dependency_chains({"x"})) == []
    assert _run(a._analyze_state_trends({})) == []
    assert _run(a._predict_potential_failures([])) == []

    inc = HistoricalIncident(
        id="i1",
        timestamp=datetime.datetime.now(),
        symptoms=["x"],
        root_causes=["y"],
        resolution="z",
        similarity_hash="sh",
    )
    _run(a.record_incident(inc))
    assert len(a.historical_incidents) == 1
    assert a.pattern_index["sh"]

    stats = _run(a.get_analysis_statistics())
    assert "total_nodes" in stats


# =============================================================================
# core.enhanced_ai_capabilities
# =============================================================================


@pytest.fixture
def ai():
    obj = EnhancedAICapabilities()
    return obj


def test_ai_dataclasses_and_enums():
    assert PredictionType.ANOMALY.value == "anomaly"
    assert LearningMode.ONLINE.value == "online"


def test_ai_initialization(monkeypatch):
    a = EnhancedAICapabilities()
    monkeypatch.setattr(asyncio, "create_task", lambda c: None)
    _run(a.initialize())
    assert len(a.anomaly_detectors) > 0


def test_ai_fit_model_branches(ai, monkeypatch):
    from core.enhanced_ai_capabilities import _fit_model

    # empty samples
    _run(_fit_model(None, []))

    # no ML
    monkeypatch.setattr("core.enhanced_ai_capabilities.ML_AVAILABLE", False)
    fake = MagicMock()
    acc = {str(id(fake)): []}
    _run(_fit_model(fake, [({"a": 1}, 1)], knowledge_accumulator=acc))
    assert str(id(fake)) in acc

    # ML available path with fake partial_fit
    monkeypatch.setattr("core.enhanced_ai_capabilities.ML_AVAILABLE", True)

    class FakeClf:
        __name__ = "FakeClassifier"
        partial_fit = MagicMock()

    _run(_fit_model(FakeClf(), [({"a": 1}, 1), ({"a": 2}, 2)], incremental=True))
    assert FakeClf.partial_fit.called

    class FakeReg:
        __name__ = "RandomForestRegressor"
        fit = MagicMock()

    _run(_fit_model(FakeReg(), [({"a": 1}, 1)]))
    assert FakeReg.fit.called


def test_ai_timeseries_prediction(ai, monkeypatch):
    # short data
    assert _run(ai.predict_timeseries("m", [(datetime.datetime.now(), 1.0)] * 5)) is None

    # fake Prophet available
    class FakeProphet:
        def __init__(self, **kw):
            pass

        def fit(self, df):
            self._df = df

        def make_future_dataframe(self, periods):
            return self._df

        def predict(self, future):
            import pandas as pd

            n = len(future)
            return pd.DataFrame(
                {
                    "ds": future["ds"],
                    "yhat": [1.0] * n,
                    "yhat_lower": [0.9] * n,
                    "yhat_upper": [1.1] * n,
                }
            )

    import core.enhanced_ai_capabilities as eai

    monkeypatch.setattr(eai, "PROPHET_AVAILABLE", True)
    monkeypatch.setattr(eai, "Prophet", FakeProphet, raising=False)

    data = [(datetime.datetime.now() - datetime.timedelta(hours=i), float(i)) for i in range(30)]
    data.reverse()
    result = _run(
        ai.predict_timeseries("cpu_usage", data)
    )  # noqa: F841  # Variable for test verification
    assert result is not None
    assert result.prediction_type == PredictionType.TIMESERIES

    # cache hit
    result2 = _run(ai.predict_timeseries("cpu_usage", data))
    assert result2 is result


def test_ai_anomaly_prediction(ai, monkeypatch):
    import numpy as np

    class FakeDetector:
        def fit(self, X):
            return self

        def predict(self, X):
            return [-1]

        def decision_function(self, X):
            return np.array([2.5])

    monkeypatch.setattr("core.enhanced_ai_capabilities.ML_AVAILABLE", True)
    ai.anomaly_detectors["cpu"] = FakeDetector()
    data = [(datetime.datetime.now() - datetime.timedelta(hours=i), 1.0) for i in range(60)]
    data.reverse()
    result = _run(
        ai.predict_anomalies("cpu", 100.0, data)
    )  # noqa: F841  # Variable for test verification
    assert result is not None
    assert result.is_anomalous is True

    # no ML path
    monkeypatch.setattr("core.enhanced_ai_capabilities.ML_AVAILABLE", False)
    assert _run(ai.predict_anomalies("cpu", 1.0, data)) is None


def test_ai_adaptive_learning(ai, monkeypatch):
    monkeypatch.setattr("core.enhanced_ai_capabilities.ML_AVAILABLE", True)

    class FakeModel:
        __name__ = "FakeClassifier"
        partial_fit = MagicMock()

    ai.prediction_models["fake"] = FakeModel()
    update = _run(
        ai.adaptive_learn(
            "fake",
            [({"a": 1}, 1), ({"a": 2}, 2)],
            learning_mode=LearningMode.ONLINE,
        )
    )
    assert update is not None
    assert update.learning_mode == LearningMode.ONLINE

    update2 = _run(
        ai.adaptive_learn(
            "fake",
            [({"a": 1}, 1)],
            learning_mode=LearningMode.BATCH,
        )
    )
    assert update2 is not None

    update3 = _run(
        ai.adaptive_learn(
            "fake",
            [({"a": 1}, 1)],
            learning_mode=LearningMode.TRANSFER,
        )
    )
    assert update3 is not None

    # missing model
    assert _run(ai.adaptive_learn("missing", [])) is None

    # ML unavailable
    monkeypatch.setattr("core.enhanced_ai_capabilities.ML_AVAILABLE", False)
    assert _run(ai.adaptive_learn("fake", [])) is None


def test_ai_natural_language_parsing(ai):
    r = _run(ai.parse_natural_language("monitor cpu last hour"))
    assert r is not None
    assert r.intent == "monitor"
    assert "cpu_usage" in r.entities.values() or "cpu_usage" in r.entities.values()

    r2 = _run(ai.parse_natural_language("predict memory next week"))
    assert r2.intent == "predict"

    r3 = _run(ai.parse_natural_language("random unknown query"))
    assert r3.intent == "unknown"
    assert r3.requires_clarification is True


def test_ai_decision_explanation(ai):
    exp = _run(ai.explain_decision("scale_up", {"metrics": True, "confidence": 0.9}))
    assert exp is not None
    assert "scale_up" in exp.decision
    assert exp.alternative_options

    exp2 = _run(ai.explain_decision("restart_service", {"ml_model": "m1"}))
    assert "ml_model" in exp2.data_sources


def test_ai_knowledge_accumulation(ai):
    _run(
        ai.accumulate_knowledge(
            {
                "id": "i1",
                "symptoms": ["slow"],
                "root_causes": ["db"],
                "resolution": "restart",
                "success": True,
            }
        )
    )
    pattern = ai._generate_knowledge_pattern(["slow"], ["db"])
    insights = _run(ai.get_knowledge_insights(pattern))
    assert insights["success_rate"] == 1.0

    # error path
    _run(ai.accumulate_knowledge(None))  # should not raise


def test_ai_should_relearn_and_stats(ai):
    ai.performance_metrics["m1"] = [0.9, 0.9, 0.9]
    assert _run(ai._should_relearn("m1")) is False
    ai.performance_metrics["m1"].append(0.0)
    assert _run(ai._should_relearn("m1")) is True
    assert _run(ai._should_relearn("missing")) is False
    assert _run(ai._should_relearn("m2")) is False

    ai.learning_history.append(MagicMock())
    stats = _run(ai.get_ai_statistics())
    assert "prediction_models" in stats


# =============================================================================
# core.ai.llm_router.capability_evaluator
# =============================================================================


def test_capability_evaluator_basic():
    configs = [
        {"model": "gpt-4", "max_tokens": 8192, "context_window": 32000},
        {"name": "gpt-3.5", "max_tokens": 4096, "context_window": 16000},
        {"model": "claude-3-opus", "max_tokens": 8192, "context_window": 200000},
        {"model": "claude-3-sonnet", "max_tokens": 4096, "context_window": 16000},
        {"model": "tiny-llama", "max_tokens": 2048, "context_window": 2048},
        {"model": "custom-model"},
    ]
    ce = CapabilityEvaluator(configs)

    # cache and model not found
    assert ce.evaluate_model("missing", TaskType.CODE_GENERATION) == 0.5
    assert ce.evaluate_model("gpt-4", TaskType.CODE_GENERATION) == 1.0

    # cached
    assert ce.evaluate_model("gpt-4", TaskType.CODE_GENERATION) == 1.0

    # analysis reasoning
    assert ce.evaluate_model("claude-3-opus", TaskType.REASONING) == 1.0
    assert ce.evaluate_model("claude-3-sonnet", TaskType.ANALYSIS) == 0.95

    # code gen context branches
    assert ce.evaluate_model("tiny-llama", TaskType.CODE_GENERATION) < 0.5
    assert ce.evaluate_model("gpt-3.5", TaskType.CODE_GENERATION) == 0.7

    # base score tiers
    assert 0.5 < ce.evaluate_model("custom-model", TaskType.GENERAL) < 0.8


def test_capability_evaluator_rank_and_best():
    configs = [
        {"model": "gpt-4"},
        {"model": "tiny-llama"},
    ]
    ce = CapabilityEvaluator(configs)
    ranked = ce.rank_models_for_task(TaskType.GENERAL)
    assert len(ranked) == 2
    assert ranked[0].score >= ranked[1].score
    assert ranked[0].model_name == "gpt-4"

    assert ce.get_best_model_for_task(TaskType.GENERAL) == "gpt-4"
    assert ce.get_best_model_for_task(TaskType.GENERAL, models=[]) is None
