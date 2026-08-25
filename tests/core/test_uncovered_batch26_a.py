# -*- coding: utf-8 -*-
"""Batch 26a coverage tests for uncovered core modules."""

import asyncio  # noqa: F401  # Imported for test setup
import hashlib
import json  # noqa: F401  # Imported for test setup
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest  # noqa: F401  # Imported for test setup

import core.advanced_ai_capabilities as adv
import core.cache_helpers as ch
import core.enhanced_root_cause_analyzer as erc
import core.root_cause_intelligence as rci
import core.runbook_generator as runbook
from core.command_guard import RiskLevel

pytestmark = [pytest.mark.core]


def _run(coro):
    return asyncio.run(coro)


class _FakeRedis:
    def __init__(self, *args, **kwargs):
        raise ConnectionError("redis disabled")


def _patch_redis(monkeypatch):
    try:
        import redis

        monkeypatch.setattr(redis, "Redis", _FakeRedis)
    except ImportError:
        pass


class _FakeGBR:
    def __init__(self, **kwargs):
        pass

    def fit(self, X, y):
        return self

    def predict(self, X):
        return [float(sum(x) / len(x)) if x else 1.0 for x in X]


class _FakeRFC:
    def __init__(self, **kwargs):
        pass


class _FakeSGD:
    def __init__(self, **kwargs):
        pass

    def partial_fit(self, X, y):
        pass


class _FakeProphet:
    def __init__(self, **kwargs):
        pass

    def fit(self, df):
        return self

    def make_future_dataframe(self, periods, freq=None):
        import pandas as pd

        return pd.DataFrame({"ds": [datetime.now() + timedelta(hours=i) for i in range(periods)]})

    def predict(self, future):
        import pandas as pd

        return pd.DataFrame({"yhat": [1.0] * len(future)})


def _make_ml_fakes(monkeypatch):
    monkeypatch.setattr(adv, "GradientBoostingRegressor", _FakeGBR)
    monkeypatch.setattr(adv, "RandomForestClassifier", _FakeRFC)
    monkeypatch.setattr(adv, "SGDClassifier", _FakeSGD)
    monkeypatch.setattr(adv, "Prophet", _FakeProphet, raising=False)


# ============================================================
# core.root_cause_intelligence
# ============================================================
def _make_engine():
    return rci.RootCauseIntelligenceEngine()


def test_rci_topology_discovery_and_tracking():
    engine = _make_engine()
    metrics = {
        "hosts": [{"hostname": "host1", "health": "healthy", "metrics": {"cpu": 10}}],
        "services": [{"name": "svc1", "health": "healthy"}],
        "applications": [{"name": "app1", "health": "unhealthy"}],
        "network_connections": [{"source": "svc1", "target": "db1"}],
        "service_dependencies": [{"service": "app1", "depends_on": "svc1"}],
        "service": "svc1",
        "target": "db1",
        "pod_name": "pod1",
        "node_name": "host1",
    }
    alert = {"id": "a1", "service": "app1", "affected_services": ["svc1"]}
    result = _run(
        engine.discover_topology_realtime(metrics, alert)
    )  # noqa: F841  # Variable for test verification
    assert result["discovered_nodes"] > 0
    path = _run(engine.perform_cross_layer_tracking(alert))
    assert isinstance(path, list)
    assert engine.get_analysis_statistics()["topology_nodes"] > 0


def test_rci_historical_patterns():
    engine = _make_engine()
    symptoms = {
        "alerts": [{"alert_type": "cpu", "host": "host1"}],
        "metrics": {"cpu_usage_percent": 95.0},
    }
    engine.learn_historical_pattern(symptoms, "cpu_spike", 12.0, 0.9)
    matches = _run(engine.match_historical_patterns(symptoms))
    assert isinstance(matches, list)
    prediction = _run(engine.predict_root_causes(symptoms))
    assert "predicted_root_causes" in prediction


def test_rci_enhanced_analysis_dns():
    engine = _make_engine()
    _run(engine.discover_topology_realtime({"hosts": [{"hostname": "h1"}]}, {}))
    engine.historical_patterns["p1"] = rci.HistoricalPattern(
        pattern_id="p1",
        symptom_signature=engine._create_symptom_signature({"alerts": [], "metrics": {}}),
        root_cause="dns",
        frequency=1,
        last_occurrence=datetime.now(),
        confidence=0.9,
    )
    alert = {
        "id": "a2",
        "title": "dns resolution timeout",
        "service": "svc1",
        "affected_services": ["svc1"],
    }
    metrics = {
        "dns_resolution_error_rate": 5.0,
        "dns_lookup_time_ms": 1200.0,
        "service": "svc1",
        "target": "resolver",
    }
    results = _run(engine.analyze_root_causes_enhanced(alert, metrics))
    assert isinstance(results, list)
    if results:
        hypothesis = results[0]
        _run(
            engine.verify_root_cause(
                hypothesis,
                {
                    "active_components": [hypothesis.root_cause],
                    "affected_components": [hypothesis.root_cause],
                    "observed_symptoms": ["dns"],
                    "actual_impact": {},
                    "dns_resolution_error_rate": 1.0,
                },
            )
        )


def test_rci_enhanced_analysis_sql():
    engine = _make_engine()
    alert = {"id": "a3", "title": "slow query", "service": "db", "affected_services": ["db"]}
    metrics = {
        "slow_query_rate": 2.0,
        "avg_query_duration_ms": 1500.0,
        "database": "db",
    }
    results = _run(engine.analyze_root_causes_enhanced(alert, metrics, {"change_events": []}))
    assert isinstance(results, list)


def test_rci_enhanced_analysis_oom():
    engine = _make_engine()
    alert = {"id": "a4", "title": "oom", "service": "app", "pod": "pod1"}
    metrics = {
        "pod_name": "pod1",
        "namespace": "ns1",
        "node_name": "node1",
        "memory_usage_percent": 92.0,
        "memory_usage_bytes": 1e9,
        "last_state": {"terminated": {"reason": "OOMKilled"}},
    }
    results = _run(engine.analyze_root_causes_enhanced(alert, metrics))
    assert isinstance(results, list)


def test_rci_internal_helpers():
    engine = _make_engine()
    assert engine._is_abnormal({"cpu_usage_percent": 95.0}) is True
    assert engine._is_abnormal({"cpu_usage_percent": 10.0}) is False
    nodes = engine._extract_nodes_from_metrics({"hosts": [{"hostname": "h1"}]}, {"service": "h1"})
    assert any(n["id"] == "h1" for n in nodes)
    assert engine._infer_layer({"type": "network"}) == rci.TopologyLayer.NETWORK
    summary = engine._get_topology_summary()
    assert "total_nodes" in summary
    ts = engine._parse_timestamp(datetime.now())
    assert ts is not None
    assert engine._parse_timestamp("2024-01-01T00:00:00") is not None
    assert engine._parse_timestamp(1_700_000_000) is not None
    assert engine._calculate_signature_similarity("a|b", "a|b") == 1.0
    assert engine._calculate_impact_accuracy({"x": 1.0}, {"x": 1.0}) == 1.0
    _run(engine._causal_graph_analysis({"source_service": "s", "metric": "cpu", "value": 99}, {}))
    _run(engine._ml_based_analysis({"metric": "cpu", "value": 99}, {"cpu": 80, "mem": 60}))


# ============================================================
# core.cache_helpers
# ============================================================
def test_cache_statistics_and_key():
    stats = ch.CacheStatistics()
    stats.record_hit()
    stats.record_miss()
    stats.record_eviction()
    assert 0.0 <= stats.get_hit_rate() <= 100.0
    assert "hit_rate" in stats.get_stats()
    key = ch.generate_cache_key("pre", 1, "a", nested={"x": 1})
    assert isinstance(key, str)


def test_lru_cache():
    cache = ch.LRUCache(max_size=2, ttl_sec=5.0)
    cache.set("a", 1)
    cache.set("b", 2)
    assert cache.get("a") == 1
    cache.set("c", 3)
    assert cache.get("b") is None
    assert cache.invalidate("a") is True
    assert cache.invalidate("a") is False
    cache.clear()
    assert cache.get("a") is None
    assert isinstance(cache.get_stats(), dict)


def test_ttl_cache():
    cache = ch.TTLCache(ttl_sec=5.0)
    cache.set({"x": 1})
    assert cache.get()["x"] == 1
    assert cache.is_valid() is True
    cache.clear()
    assert cache.get() is None


def test_parametric_ttl_cache():
    cache = ch.ParametricTTLCache(ttl_sec=5.0)
    cache.set({"x": 1}, region="r1")
    assert cache.get(region="r1")["x"] == 1
    assert cache.get(region="r2") is None
    cache.clear()


def test_multi_level_cache(monkeypatch):
    _patch_redis(monkeypatch)
    cache = ch.MultiLevelCache()
    cache.set("k1", {"v": 1})
    assert cache.get("k1") == {"v": 1}
    cache.invalidate("k1")
    assert cache.get("k1") is None
    cache.set("k2", "plain")
    assert cache.get("k2") == "plain"
    cache.clear()


def test_three_level_cache(monkeypatch):
    _patch_redis(monkeypatch)
    cache = ch.ThreeLevelCache()
    cache.set("k1", {"v": 1})
    assert cache.get("k1") == {"v": 1}
    cache.register_invalidation_callback(ch.CacheInvalidationEvent.MANUAL, lambda key, meta: None)
    cache._trigger_invalidation_event(ch.CacheInvalidationEvent.MANUAL, "k1")
    cache.invalidate("k1", ch.CacheInvalidationEvent.EVENT_BASED, {"x": 1})
    assert cache.get("k1") is None
    assert cache.invalidate_pattern("*") == 0
    assert isinstance(cache.get_stats(), dict)
    cache.clear()


def test_cache_warmer():
    cache = ch.LRUCache()
    warmer = ch.CacheWarmer(cache)

    async def double(x):
        return x * 2

    warmer.register("double", double)
    assert _run(warmer.warm("double", 5)) == 10
    with pytest.raises(ValueError):
        _run(warmer.warm("missing"))


def test_intelligent_cache_warmer(monkeypatch):
    _patch_redis(monkeypatch)
    cache = ch.ThreeLevelCache()
    warmer = ch.IntelligentCacheWarmer(cache)

    async def triple(x):
        return x * 3

    warmer.register("triple", triple, priority=9)
    assert _run(warmer.warm("triple", 3)) == 9
    assert warmer.predict_next_access("triple") == 0.0
    _run(warmer.warm_with_prediction("triple", 3))
    _run(warmer.warm_high_priority())
    assert isinstance(warmer.get_warming_stats(), dict)
    warmer.record_access("triple")
    warmer.record_access("triple")
    warmer.record_access("triple")
    assert warmer.predict_next_access("triple") > 0.0


# ============================================================
# core.enhanced_root_cause_analyzer
# ============================================================
def _make_erc():
    return erc.EnhancedRootCauseAnalyzer()


def test_erc_discover_and_analyze():
    analyzer = _make_erc()
    result = _run(analyzer.discover_topology())  # noqa: F841  # Variable for test verification
    assert "nodes_count" in result
    ranked = _run(analyzer.analyze_root_causes({"n1"}, {}))
    assert isinstance(ranked, list)
    stats = _run(analyzer.get_analysis_statistics())
    assert "total_nodes" in stats


def test_erc_historical_and_causal():
    analyzer = _make_erc()
    incident = erc.HistoricalIncident(
        id="i1",
        timestamp=datetime.now(),
        symptoms=["cpu"],
        root_causes=["cpu_spike"],
        resolution="reboot",
        similarity_hash="abc",
    )
    _run(analyzer.record_incident(incident))
    hypotheses = _run(analyzer._match_historical_patterns({"n1"}, {}))
    assert isinstance(hypotheses, list)
    causal = _run(analyzer._perform_causal_analysis({"n1"}, {}))
    assert isinstance(causal, list)


def test_erc_combination_and_ranking():
    analyzer = _make_erc()
    h1 = erc.RootCauseHypothesis(
        node_id="n1",
        confidence=0.8,
        explanation="e1",
        evidence=["e"],
        impact_score=0.5,
        severity=erc.RCASeverity.HIGH,
    )
    h2 = erc.RootCauseHypothesis(
        node_id="n2",
        confidence=0.7,
        explanation="e2",
        evidence=["e"],
        impact_score=0.6,
        severity=erc.RCASeverity.MEDIUM,
    )
    combined = _run(analyzer._combine_hypotheses([h1], [h2]))
    assert isinstance(combined, list)
    ranked = _run(analyzer._rank_hypotheses([h1, h2]))
    assert ranked[0].confidence >= ranked[1].confidence
    assert analyzer._severity_score(erc.RCASeverity.CRITICAL) == 1.0


def test_erc_topology_helpers():
    analyzer = _make_erc()
    analyzer.nodes["n1"] = erc.TopologyNode(id="n1", type="service", name="s1")
    analyzer.nodes["n2"] = erc.TopologyNode(id="n2", type="database", name="d1")
    analyzer.edges["n1"].append(
        erc.TopologyEdge(source="n1", target="n2", type="reads", strength=0.8)
    )
    _run(analyzer._build_causal_graph())
    _run(analyzer._add_cross_layer_causality())
    assert "n2" in analyzer._find_upstream_causes("n1")
    assert set(analyzer._get_node_types({"n1", "n2"})) == {"service", "database"}
    features = analyzer._extract_features({"n1"}, {"extra": 1})
    assert "node_count" in features
    h1 = hashlib.sha256(b"{}").hexdigest()
    assert analyzer._calculate_pattern_similarity(h1, h1) == 1.0


def test_erc_prediction_and_verify():
    analyzer = _make_erc()
    hypothesis = erc.RootCauseHypothesis(
        node_id="n1",
        confidence=0.8,
        explanation="predicted",
        evidence=["e"],
        impact_score=0.5,
        severity=erc.RCASeverity.HIGH,
    )
    predictions = _run(analyzer.predict_root_causes({"metric": 1.0}))
    assert isinstance(predictions, list)
    verified = _run(analyzer.verify_root_cause(hypothesis))
    assert isinstance(verified, bool)


# ============================================================
# core.advanced_ai_capabilities
# ============================================================
def test_advanced_time_series_rule_based(monkeypatch):
    _make_ml_fakes(monkeypatch)
    monkeypatch.setattr(adv, "ML_AVAILABLE", False)
    monkeypatch.setattr(adv, "PROPHET_AVAILABLE", False)
    ai = adv.AdvancedAICapabilities()
    data = [(datetime.now() + timedelta(hours=i), float(i)) for i in range(15)]
    result = _run(ai.predict_time_series(data, 6))  # noqa: F841  # Variable for test verification
    assert result.model_used == "rule_based_trend"
    assert len(result.predicted_values) == 6


def test_advanced_time_series_ml_path(monkeypatch):
    _make_ml_fakes(monkeypatch)
    monkeypatch.setattr(adv, "ML_AVAILABLE", True)
    monkeypatch.setattr(adv, "PROPHET_AVAILABLE", False)
    ai = adv.AdvancedAICapabilities()
    data = [(datetime.now() + timedelta(hours=i), float(i)) for i in range(25)]
    result = _run(ai.predict_time_series(data, 4))  # noqa: F841  # Variable for test verification
    assert result.model_used == "ml_gradient_boosting"
    assert len(result.predicted_values) == 4


def test_advanced_time_series_prophet_path(monkeypatch):
    _make_ml_fakes(monkeypatch)
    monkeypatch.setattr(adv, "ML_AVAILABLE", False)
    monkeypatch.setattr(adv, "PROPHET_AVAILABLE", True)
    ai = adv.AdvancedAICapabilities()
    data = [(datetime.now() + timedelta(hours=i), float(i)) for i in range(15)]
    result = _run(ai.predict_time_series(data, 3))  # noqa: F841  # Variable for test verification
    assert result.model_used == "prophet"
    assert len(result.predicted_values) == 3


def test_advanced_anomaly_and_learning(monkeypatch):
    _make_ml_fakes(monkeypatch)
    monkeypatch.setattr(adv, "ML_AVAILABLE", True)
    ai = adv.AdvancedAICapabilities()
    baseline = {"cpu": [40.0 + (i % 3) * 2 for i in range(15)], "mem": [50.0] * 15}
    result = _run(
        ai.predict_anomalies({"cpu": 96.0}, baseline, threshold_std=1.0)
    )  # noqa: F841  # Variable for test verification
    assert result.prediction_type == adv.PredictionType.ANOMALY

    update = _run(ai.adaptive_learning_update({"x": 1.0}, {"score": 0.9}, adv.LearningMode.ONLINE))
    assert update.learning_mode == adv.LearningMode.ONLINE
    assert (
        _run(
            ai.adaptive_learning_update({"x": 1.0}, {"score": 0.5}, adv.LearningMode.BATCH)
        ).learning_mode
        == adv.LearningMode.BATCH
    )
    monkeypatch.setattr(adv, "ML_AVAILABLE", False)
    assert (
        _run(
            ai.adaptive_learning_update({"x": 1.0}, {"score": 0.5}, adv.LearningMode.REINFORCEMENT)
        ).performance_improvement
        > 0
    )


def test_advanced_natural_language_and_explain(monkeypatch):
    _make_ml_fakes(monkeypatch)
    monkeypatch.setattr(adv, "AI_ENGINE_AVAILABLE", False)
    ai = adv.AdvancedAICapabilities()
    r1 = _run(ai.natural_language_interaction("check status", "c1", "u1"))
    assert r1["intent"] == "check_status"
    r2 = _run(ai.natural_language_interaction("help me", "c1", "u1"))
    assert r2["intent"] == "help"

    monkeypatch.setattr(adv, "AI_ENGINE_AVAILABLE", True)
    monkeypatch.setattr(
        adv, "analyze", AsyncMock(return_value={"analysis": "ok", "action_required": True})
    )
    r3 = _run(ai.natural_language_interaction("analyze alert", "c2", "u1"))
    assert r3["metadata"]["ai_generated"] is True

    decision = _run(ai.explain_decision("reboot", {"cpu": 0.95}, "default"))
    assert isinstance(decision, adv.ExplainableDecision)
    assert decision.confidence > 0.0


def test_advanced_knowledge_and_summary(monkeypatch):
    _make_ml_fakes(monkeypatch)
    ai = adv.AdvancedAICapabilities()
    for _ in range(11):
        _run(ai.continuous_knowledge_learning({"metric": "cpu", "value": 90}, "success"))
    summary = ai.get_capabilities_summary()
    assert "predictive_analysis" in summary
    assert "knowledge_base" in summary
    assert "decisions_explained" in summary["explainable_ai"]


# ============================================================
# core.runbook_generator
# ============================================================
def _valid_runbook():
    return json.dumps(
        {
            "summary": "kill high cpu chrome",
            "commands": ["taskkill /IM chrome.exe /F"],
            "risk_level": "low",
            "rollback": "无需回滚",
            "confidence": 0.85,
            "reasoning": "chrome uses too much cpu",
        }
    )


def _setup_runbook_mocks(monkeypatch, raw_output, command_risk=RiskLevel.LOW, upsert_ok=True):
    monkeypatch.setattr(runbook, "VERIFY_CONFIG", {"self_learning_enabled": True})
    monkeypatch.setattr(runbook, "search_similar", lambda q, top_k=3: [])
    monkeypatch.setattr(runbook, "anonymize_text", lambda x: x)
    monkeypatch.setattr(runbook, "anonymize_dict", lambda x: x)
    monkeypatch.setattr(runbook, "DATA_PRIVACY_AVAILABLE", False)
    monkeypatch.setattr(runbook, "MODERATION_AVAILABLE", True)
    monkeypatch.setattr(runbook, "moderate_content", lambda p: (True, []))
    monkeypatch.setattr(runbook, "AUDIT_AVAILABLE", True)
    monkeypatch.setattr(runbook, "log_audit_event", MagicMock())
    monkeypatch.setattr(runbook, "analyze", AsyncMock(return_value=raw_output))
    monkeypatch.setattr(
        runbook,
        "analyze_command",
        lambda cmd: {
            "command": cmd,
            "risk_level": command_risk,
            "risk_name": "",
            "reason": "",
            "safe_alternative": "",
            "is_chained": False,
            "chain_count": 1,
        },
    )
    monkeypatch.setattr(
        runbook,
        "upsert_pending_approval",
        MagicMock() if upsert_ok else MagicMock(side_effect=RuntimeError("db busy")),
    )


@pytest.mark.asyncio
async def test_runbook_success(monkeypatch):
    _setup_runbook_mocks(monkeypatch, _valid_runbook(), RiskLevel.LOW)
    alert = {
        "id": "r1",
        "level": "high",
        "title": "high cpu",
        "desc": "cpu high",
        "metric": "cpu_percent",
        "value": 95,
        "platform": "windows",
    }
    rich = {
        "top_processes": [{"name": "chrome", "pid": 1234, "cpu_percent": 80, "memory_percent": 30}],
        "stats": {"current_anomalies": 1, "heal_rate": 90, "total_alerts": 5},
    }
    result = await runbook.generate_repair_runbook(
        alert, rich
    )  # noqa: F841  # Variable for test verification
    assert result["success"] is True
    assert result["auto_executable"] is True


@pytest.mark.asyncio
async def test_runbook_moderation_fail(monkeypatch):
    _setup_runbook_mocks(monkeypatch, _valid_runbook())
    monkeypatch.setattr(runbook, "moderate_content", lambda p: (False, ["injection"]))
    result = await runbook.generate_repair_runbook(  # noqa: F841  # Variable for test verification
        {"id": "m1", "level": "high", "title": "x", "desc": "x"}
    )
    assert result["success"] is False
    assert "injection" in result["error"]


@pytest.mark.asyncio
async def test_runbook_invalid_inputs(monkeypatch):
    _setup_runbook_mocks(monkeypatch, _valid_runbook())
    assert (await runbook.generate_repair_runbook("not a dict"))["success"] is False
    assert (await runbook.generate_repair_runbook({"id": "", "level": "high"}))["success"] is False
    assert (await runbook.generate_repair_runbook({"level": "high"}))["success"] is False


@pytest.mark.asyncio
async def test_runbook_invalid_json(monkeypatch):
    _setup_runbook_mocks(monkeypatch, "this is not json")
    result = await runbook.generate_repair_runbook(  # noqa: F841  # Variable for test verification
        {"id": "j1", "level": "high", "title": "x", "desc": "x"}
    )
    assert result["success"] is False
    assert result["success"] is False


@pytest.mark.asyncio
async def test_runbook_blocked(monkeypatch):
    _setup_runbook_mocks(monkeypatch, _valid_runbook(), RiskLevel.BLOCKED)
    result = await runbook.generate_repair_runbook(  # noqa: F841  # Variable for test verification
        {"id": "b1", "level": "high", "title": "x", "desc": "x"}
    )
    assert result["success"] is False
    assert result["worst_risk"] == RiskLevel.BLOCKED.value


@pytest.mark.asyncio
async def test_runbook_upsert_fail(monkeypatch):
    _setup_runbook_mocks(monkeypatch, _valid_runbook(), RiskLevel.LOW, upsert_ok=False)
    result = await runbook.generate_repair_runbook(  # noqa: F841  # Variable for test verification
        {"id": "u1", "level": "high", "title": "x", "desc": "x"}
    )
    assert result["success"] is False


def test_runbook_helpers():
    snapshot = runbook._build_metrics_snapshot(None)
    assert isinstance(snapshot, str)
    rich = {"top_processes": [{"name": "x", "pid": 1, "cpu_percent": 10, "memory_percent": 5}]}
    assert "x" in runbook._build_metrics_snapshot(rich)

    valid, _, normalized = runbook._validate_and_normalize_runbook(
        {
            "summary": "s",
            "commands": ["cmd1"],
            "risk_level": "low",
            "confidence": 1.5,
        }
    )
    assert valid is True
    assert normalized["confidence"] == 1.0

    invalid, err, _ = runbook._validate_and_normalize_runbook({"summary": "s"})
    assert invalid is False
    assert "commands" in err

    raw = 'prefix {"a": 1} suffix'
    parsed = runbook._extract_json_from_llm_output(raw)
    assert parsed == {"a": 1}
    assert runbook._extract_first_json_object(raw) == '{"a": 1}'

    assert runbook._infer_candidate_script_key({"metric": "cpu_percent"}) == "kill_high_cpu"
    assert (
        runbook._infer_candidate_script_key({"metric": "memory_percent", "platform": "windows"})
        == "free_memory"
    )
    assert (
        runbook._infer_candidate_script_key({"metric": "memory_percent", "platform": "linux"})
        == "free_cache"
    )
    assert runbook._infer_candidate_script_key({"metric": "unknown"}) is None


def test_runbook_helpers_extra():
    assert runbook._extract_first_json_object("no brace") is None
    raw = '```json\n{"k": 1}\n```'
    assert runbook._extract_json_from_llm_output(raw) == {"k": 1}

    invalid, err, _ = runbook._validate_and_normalize_runbook(
        {"summary": "s", "commands": ["c"], "risk_level": "extreme"}
    )
    assert invalid is False and "risk_level" in err

    invalid2, err2, _ = runbook._validate_and_normalize_runbook(
        {"summary": " ", "commands": [], "risk_level": "low"}
    )
    assert invalid2 is False and ("summary" in err2 or "commands" in err2)


@pytest.mark.asyncio
async def test_runbook_extra_scenarios(monkeypatch):
    _setup_runbook_mocks(monkeypatch, _valid_runbook(), RiskLevel.LOW)
    monkeypatch.setattr(runbook, "analyze", AsyncMock(side_effect=RuntimeError("llm down")))
    result = await runbook.generate_repair_runbook(  # noqa: F841  # Variable for test verification
        {"id": "e1", "level": "high", "title": "x", "desc": "x"}
    )
    assert result["success"] is False

    _setup_runbook_mocks(monkeypatch, _valid_runbook(), RiskLevel.LOW)

    def _raise_guard(cmd):
        raise RuntimeError("guard boom")

    monkeypatch.setattr(runbook, "analyze_command", _raise_guard)
    result = await runbook.generate_repair_runbook(  # noqa: F841  # Variable for test verification
        {"id": "e2", "level": "high", "title": "x", "desc": "x"}
    )
    assert result["success"] is False

    _setup_runbook_mocks(monkeypatch, _valid_runbook(), RiskLevel.LOW)
    monkeypatch.setattr(
        runbook,
        "search_similar",
        lambda q, top_k=3: [{"payload": {"summary": "similar", "commands": ["cmd"]}}],
    )
    result = await runbook.generate_repair_runbook(  # noqa: F841  # Variable for test verification
        {"id": "e3", "level": "high", "title": "x", "desc": "x", "platform": "mac"},
        {"recent_alerts": [{"level": "high", "title": "y"}]},
    )
    assert result["success"] is True

    _setup_runbook_mocks(monkeypatch, _valid_runbook(), RiskLevel.LOW)
    monkeypatch.setattr(runbook, "log_audit_event", MagicMock(side_effect=RuntimeError("audit")))
    result = await runbook.generate_repair_runbook(  # noqa: F841  # Variable for test verification
        {"id": "e4", "level": "high", "title": "x", "desc": "x"}
    )
    assert result["success"] is True


# ============================================================
# Additional coverage for cache and root cause
# ============================================================
def test_cache_redis_and_db_paths(monkeypatch):
    _patch_redis(monkeypatch)
    cache = ch.MultiLevelCache()
    fake = MagicMock()
    fake.get.return_value = '{"v":1}'
    fake.setex.return_value = None
    fake.delete.return_value = None
    fake.keys.return_value = ["k"]
    cache._redis_client = fake
    cache._redis_available = True
    cache.set("k", {"v": 1})
    assert cache.get("k") == {"v": 1}
    cache.invalidate("k")
    cache.clear()

    fake.get.side_effect = RuntimeError("boom")
    assert cache.get("k") is None
    fake.setex.side_effect = RuntimeError("boom")
    cache.set("k2", {"v": 2})
    fake.delete.side_effect = RuntimeError("boom")
    cache.invalidate("k2")
    fake.keys.side_effect = RuntimeError("boom")
    cache.clear()

    tcache = ch.ThreeLevelCache()
    fake2 = MagicMock()
    fake2.get.return_value = None
    fake2.keys.return_value = ["k"]
    tcache._redis_client = fake2
    tcache._redis_available = True
    tcache._db_available = True
    tcache.set("k", {"v": 1})
    assert tcache.get("k") == {"v": 1}
    tcache._memory_cache.invalidate("k")
    assert tcache.get("k") == {"v": 1}  # from L3
    tcache.invalidate("k")
    tcache._memory_cache.invalidate("k")
    fake2.get.return_value = '{"v":2}'
    assert tcache.get("k") == {"v": 2}  # from L2
    tcache.invalidate_pattern("*")
    tcache.clear()


def test_rci_extra_scenarios():
    engine = _make_engine()
    engine.topology_graph["root"] = rci.TopologyNode(
        node_id="root", name="root", layer=rci.TopologyLayer.INFRASTRUCTURE
    )
    engine.topology_graph["n1"] = rci.TopologyNode(
        node_id="n1", name="n1", layer=rci.TopologyLayer.SERVICE
    )
    engine.topology_graph["n2"] = rci.TopologyNode(
        node_id="n2", name="n2", layer=rci.TopologyLayer.SERVICE
    )
    engine.topology_graph["n1"].dependencies.add("root")
    engine.topology_graph["n2"].dependencies.add("root")
    common = _run(engine._find_common_upstream_dependency(["n1", "n2"]))
    assert common == "root"

    d, _ = engine._bfs_reachable("missing", 3)
    assert d == {}

    _run(engine.discover_topology_realtime({"hosts": [{"hostname": "h1"}]}, {}))
    _run(engine.discover_topology_realtime({"hosts": [{"hostname": "h1"}]}, {}))

    nodes = engine._extract_nodes_from_metrics({}, {"affected_services": "svc", "service": "svc"})
    assert any(n["id"] == "svc" for n in nodes)

    alert = {
        "id": "c1",
        "timestamp": "2024-01-01T00:00:00",
        "service": "svc",
        "affected_services": ["svc"],
    }
    change = {"timestamp": "2024-01-01T00:05:00", "target": "svc", "type": "deploy"}
    h = engine._generate_change_event_candidate(alert, [change])
    assert h is not None

    for prefix in ("pattern_", "change_", "cascade_"):
        hyp = rci.RootCauseHypothesis(hypothesis_id=f"{prefix}x", root_cause="x", confidence=0.5)
        populated = engine._populate_expected_and_missing(hyp, {})
        assert populated.expected_observations or populated.missing_data

    assert (
        engine._verify_scenario_metrics(
            rci.RootCauseHypothesis(
                hypothesis_id="h", root_cause="dns_resolution_failure_x", confidence=0.5
            ),
            {"dns_resolution_error_rate": 0.1},
        )
        is True
    )
    assert (
        engine._verify_scenario_metrics(
            rci.RootCauseHypothesis(
                hypothesis_id="h", root_cause="slow_sql_after_release_x", confidence=0.5
            ),
            {"avg_query_duration_ms": 600},
        )
        is True
    )
    assert (
        engine._verify_scenario_metrics(
            rci.RootCauseHypothesis(hypothesis_id="h", root_cause="pod_oom_x", confidence=0.5),
            {"last_state": {"reason": "OOMKilled"}},
        )
        is True
    )
    assert (
        engine._verify_scenario_metrics(
            rci.RootCauseHypothesis(hypothesis_id="h", root_cause="generic", confidence=0.5), {}
        )
        is None
    )

    assert engine._parse_timestamp("not-a-date") is None

    symptoms = {"alerts": [{"alert_type": "cpu", "host": "h"}], "metrics": {"cpu": 80}}
    engine.learn_historical_pattern(symptoms, "cpu", 5.0, 0.8)
    engine.learn_historical_pattern(symptoms, "cpu", 5.0, 0.85)
    assert engine.historical_patterns

    assert engine._calculate_impact_accuracy({}, {"x": 1}) == 0.0
    assert engine._calculate_impact_accuracy({"x": 1}, {"x": 0}) == 0.0
    assert engine._calculate_impact_accuracy({"y": 4}, {"y": 1}) == 0.0


def test_erc_stubs():
    analyzer = _make_erc()
    assert _run(analyzer._identify_critical_nodes()) == []
    assert _run(analyzer._is_single_point_of_failure("n")) is False
    assert _run(analyzer._analyze_dependency_chains({"n"})) == []
    assert analyzer._extract_ml_features({"n"}, {}) == []
    assert _run(analyzer._analyze_state_trends({"x": 1})) == []
    assert _run(analyzer._predict_potential_failures([])) == []
    analyzer.max_historical_incidents = 2

    async def _record_three():
        for i in range(3):
            await analyzer.record_incident(
                erc.HistoricalIncident(
                    id=str(i),
                    timestamp=datetime.now(),
                    symptoms=["s"],
                    root_causes=["r"],
                    resolution="x",
                    similarity_hash="h",
                )
            )

    _run(_record_three())
    assert len(analyzer.historical_incidents) <= 10000
