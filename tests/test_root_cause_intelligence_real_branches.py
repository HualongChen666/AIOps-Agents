# -*- coding: utf-8 -*-
"""Real branch coverage tests for core.root_cause_intelligence.

These tests exercise the public and internal methods of
RootCauseIntelligenceEngine with real class/function calls and real data.
No mocks or monkeypatching are used; each test constructs a fresh engine and
manipulates inputs to hit branches reported missing in coverage.json.
"""

import pytest  # noqa: F401  # Imported for test setup

import core.root_cause_intelligence as rci

pytestmark = [pytest.mark.core]


# ---------------------------------------------------------------------------
# Direct helper/branch tests
# ---------------------------------------------------------------------------


def test_detect_scenario_metric_keys():
    engine = rci.RootCauseIntelligenceEngine()
    alert = {"title": "generic alert"}
    assert engine._detect_scenario(alert, {"dns_resolution_error_rate": 1.0}) == "dns"
    assert engine._detect_scenario(alert, {"avg_query_duration_ms": 2000}) == "sql"
    assert engine._detect_scenario(alert, {"memory_usage_percent": 95}) == "oom"
    assert engine._detect_scenario(alert, "not-a-dict") == "generic"


def test_verify_scenario_metrics_branches():
    engine = rci.RootCauseIntelligenceEngine()
    h = rci.RootCauseHypothesis(
        confidence=0.5,
        hypothesis_id="h",
        root_cause="dns_resolution_failure_target",
    )
    assert engine._verify_scenario_metrics(h, {"dns_resolution_error_rate": 0.5}) is True
    assert engine._verify_scenario_metrics(h, {"dns_lookup_time_ms": 600}) is True
    assert engine._verify_scenario_metrics(h, {}) is False

    h.root_cause = "slow_sql_after_release_db"
    assert engine._verify_scenario_metrics(h, {"slow_query_rate": 0.0}) is False

    h.root_cause = "pod_oom_app"
    assert (
        engine._verify_scenario_metrics(h, {"memory_usage_percent": 80, "last_state": {}}) is False
    )


def test_populate_expected_and_missing_branches():
    engine = rci.RootCauseIntelligenceEngine()

    # Change type with both fields empty
    h = rci.RootCauseHypothesis(
        confidence=0.5,
        hypothesis_id="change_svc",
        root_cause="svc",
        expected_observations=[],
        missing_data=[],
    )
    out = engine._populate_expected_and_missing(h, {})
    assert "degrade" in out.expected_observations[0].lower()
    assert "baseline" in out.missing_data[0].lower()

    # Topology/cascade with expected present, missing empty
    h = rci.RootCauseHypothesis(
        confidence=0.5,
        hypothesis_id="topology_x",
        root_cause="x",
        expected_observations=["exists"],
        missing_data=[],
    )
    out = engine._populate_expected_and_missing(h, {})
    assert out.expected_observations == ["exists"]
    assert "health metrics" in out.missing_data[0].lower()

    # multi_root / escalate special types
    h = rci.RootCauseHypothesis(
        confidence=0.5,
        hypothesis_id="multi_root",
        root_cause="multi",
        expected_observations=[],
        missing_data=[],
    )
    out = engine._populate_expected_and_missing(h, {})
    assert out.hypothesis_id == "multi_root"
    assert out.expected_observations
    assert out.missing_data

    # Generic fallback
    h = rci.RootCauseHypothesis(
        confidence=0.5,
        hypothesis_id="other",
        root_cause="other",
        expected_observations=[],
        missing_data=[],
    )
    out = engine._populate_expected_and_missing(h, {})
    assert out.expected_observations
    assert out.missing_data


async def test_ml_based_analysis_low_confidence():
    engine = rci.RootCauseIntelligenceEngine()
    results = await engine._ml_based_analysis({"metric": "cpu", "value": "n/a"}, {})
    assert len(results) == 1
    assert results[0].confidence == 0.4


async def test_predict_root_causes_with_matches():
    engine = rci.RootCauseIntelligenceEngine()
    symptoms = {
        "alerts": [{"alert_type": "oom", "host": "node1"}],
        "metrics": {"memory_usage_percent": 96.0},
    }
    engine.learn_historical_pattern(symptoms, "pod_oom", 60.0, 0.85)
    pred = await engine.predict_root_causes(symptoms, prediction_horizon=30)
    assert pred["predicted_root_causes"]
    assert pred["confidence"] > 0.0


def test_generate_change_event_candidate_branches():
    engine = rci.RootCauseIntelligenceEngine()
    alert = {"source": "svc", "affected_services": "api"}
    no_match = engine._generate_change_event_candidate(alert, [{"target": "other"}])
    assert no_match is None

    events = [
        {"target": "api", "type": "deploy", "timestamp": "2026-08-12T15:00:00"},
        {"target": "api", "type": "deploy", "timestamp": "2026-08-12T16:10:00"},
    ]
    alert = {"source": "svc", "affected_services": "api", "timestamp": "2026-08-12T15:00:00"}
    # Within 15 minutes
    h = engine._generate_change_event_candidate(alert, [events[0]])
    assert h.confidence == 0.85
    # Within 60 minutes
    h = engine._generate_change_event_candidate(
        {**alert, "timestamp": "2026-08-12T15:40:00"}, [events[0]]
    )
    assert h.confidence == 0.7
    # More than 60 minutes
    h = engine._generate_change_event_candidate(alert, [events[1]])
    assert h.confidence == 0.55
    # Multiple events where the second does not score higher
    h = engine._generate_change_event_candidate(alert, events)
    assert h.confidence == 0.85


def test_learn_historical_pattern_update():
    engine = rci.RootCauseIntelligenceEngine()
    symptoms = {"alerts": [{"alert_type": "x", "host": "h"}], "metrics": {}}
    engine.learn_historical_pattern(symptoms, "dup", 10.0, 0.5)
    engine.learn_historical_pattern(symptoms, "dup", 20.0, 0.9)
    assert len(engine.historical_patterns) == 1
    assert list(engine.historical_patterns.values())[0].frequency == 2


async def test_find_common_upstream_dependency_branches():
    engine = rci.RootCauseIntelligenceEngine()
    await engine.discover_topology_realtime(
        {
            "services": [
                {"name": "svc1", "health": "unhealthy"},
                {"name": "svc2", "health": "unhealthy"},
                {"name": "svc3", "health": "unhealthy"},
                {"name": "db", "health": "unhealthy"},
            ],
            "service_dependencies": [
                {"service": "svc1", "depends_on": "db"},
                {"service": "svc2", "depends_on": "db"},
            ],
        }
    )

    assert await engine._find_common_upstream_dependency(["missing"], max_depth=5) is None
    assert await engine._find_common_upstream_dependency(["svc1", "svc3"], max_depth=5) is None
    assert await engine._find_common_upstream_dependency(["svc1", "svc2"], max_depth=5) == "db"


async def test_bfs_reachable_branches():
    engine = rci.RootCauseIntelligenceEngine()
    await engine.discover_topology_realtime(
        {
            "services": [
                {"name": "a", "health": "unhealthy"},
                {"name": "b", "health": "unhealthy"},
                {"name": "c", "health": "unhealthy"},
            ],
            "network_connections": [
                {"source": "a", "target": "b"},
                {"source": "b", "target": "c"},
            ],
        }
    )
    # max_depth=1 should not reach c
    distances, _ = engine._bfs_reachable("a", max_depth=1)
    assert "b" in distances
    assert "c" not in distances

    # dependents only, starting from b should reach a
    distances, _ = engine._bfs_reachable(
        "b", max_depth=5, use_dependencies=False, use_dependents=True
    )
    assert "a" in distances


async def test_cross_layer_tracking_scoring():
    engine = rci.RootCauseIntelligenceEngine()
    await engine.discover_topology_realtime(
        {
            "services": [
                {"name": "svc1", "health": "unhealthy"},
                {"name": "svc2", "health": "unhealthy"},
            ],
            "service_dependencies": [{"service": "svc1", "depends_on": "svc2"}],
        }
    )
    # affected_services is a string this time
    alert = {"id": "a1", "service": "svc1", "affected_services": "svc2"}
    path = await engine.perform_cross_layer_tracking(alert, max_depth=5)
    assert path == ["svc1", "svc2"]


async def test_verify_root_cause_pattern_match_and_impact_accuracy():
    engine = rci.RootCauseIntelligenceEngine()
    engine.learn_historical_pattern(
        {"alerts": [{"alert_type": "x", "host": "h"}], "metrics": {}},
        "api",
        10.0,
        0.8,
    )
    await engine.discover_topology_realtime({"services": [{"name": "api", "health": "unhealthy"}]})
    h = rci.RootCauseHypothesis(
        confidence=0.5,
        hypothesis_id="h",
        root_cause="api",
        causal_path=["api"],
        expected_observations=[],
        missing_data=[],
        predicted_impact={"cpu": 0.9, "mem": 0.5},
    )
    result = await engine.verify_root_cause(  # noqa: F841  # Variable for test verification
        h,
        {
            "active_components": ["api"],
            "actual_impact": {"cpu": 0.85},
            "observed_symptoms": [],
        },
    )
    checks = {c["check"]: c["passed"] for c in result["checks"]}
    assert checks["historical_pattern_match"]
    assert result["verification_status"] in (
        "verified",
        "partially_verified",
        "rejected",
    )


# ---------------------------------------------------------------------------
# analyze_root_causes_enhanced branch tests
# ---------------------------------------------------------------------------


async def test_analyze_max_steps_zero():
    engine = rci.RootCauseIntelligenceEngine()
    results = await engine.analyze_root_causes_enhanced(
        {"id": "a", "title": "x", "service": "svc"},
        {},
        {"max_steps": 0},
    )
    assert results and results[0].hypothesis_id == "escalate"


async def test_analyze_topology_discovery_exception():
    engine = rci.RootCauseIntelligenceEngine()
    results = await engine.analyze_root_causes_enhanced(
        {"id": "a", "title": "x", "service": "svc"},
        "bad-metrics",  # not a dict, will raise inside discover_topology_realtime
        {},
    )
    assert isinstance(results, list)
    assert results[0].hypothesis_id == "escalate"


async def test_analyze_rejected_candidate_continue():
    engine = rci.RootCauseIntelligenceEngine()
    alert = {
        "id": "a",
        "title": "x",
        "service": "web",
        "source": "web",
        "affected_services": "api",
        "timestamp": "2026-08-12T15:00:00",
    }
    metrics = {"service": "web", "target": "api"}
    context = {
        "change_events": [{"target": "api", "type": "deploy", "timestamp": "2026-08-12T15:00:00"}],
        "verification_data": {"active_components": [], "observed_symptoms": []},
    }
    results = await engine.analyze_root_causes_enhanced(alert, metrics, context)
    assert any(h.hypothesis_id == "escalate" for h in results)


async def test_analyze_verify_exception():
    engine = rci.RootCauseIntelligenceEngine()
    alert = {"id": "a", "title": "x", "service": "web", "affected_services": ["api"]}
    metrics = {"service": "web", "target": "api"}
    context = {"verification_data": "not-a-dict"}
    results = await engine.analyze_root_causes_enhanced(alert, metrics, context)
    assert results
    assert all(h.verification_status == "pending" for h in results)


async def test_analyze_gating_collect_more_data():
    engine = rci.RootCauseIntelligenceEngine()
    engine.learn_historical_pattern(
        {"alerts": [{"alert_type": "x", "host": "api"}], "metrics": {}},
        "api",
        10.0,
        0.8,
    )
    alert = {
        "id": "a",
        "title": "x",
        "service": "web",
        "source": "web",
        "affected_services": "api",
    }
    metrics = {
        "services": [
            {"name": "api", "health": "unhealthy"},
            {"name": "web", "health": "unhealthy"},
        ],
        "service_dependencies": [{"service": "web", "depends_on": "api"}],
    }
    await engine.discover_topology_realtime(metrics, alert)
    context = {
        "verification_data": {
            "active_components": ["api", "web"],
            "observed_symptoms": [
                "Node api should show abnormal metrics (CPU, memory, latency, errors)",
                "Downstream services dependent on api should report correlated failures",
                "Path web -> api should be observable in traces/dependencies",
            ],
            "real-time health metrics for all nodes in the causal path": "ok",
            "network path traces between source and root": "ok",
            "dependency call error rates and latency": "ok",
        }
    }
    results = await engine.analyze_root_causes_enhanced(alert, metrics, context)
    topo = [h for h in results if h.hypothesis_id.startswith("topology_")]
    assert topo
    assert topo[0].confidence == 0.7
    assert topo[0].recommended_action == "collect_more_data"
    assert topo[0].requires_approval is True


async def test_analyze_gating_escalate_low_confidence():
    engine = rci.RootCauseIntelligenceEngine()
    engine.learn_historical_pattern(
        {"alerts": [{"alert_type": "x", "host": "api"}], "metrics": {}},
        "api",
        10.0,
        0.8,
    )
    await engine.discover_topology_realtime(
        {
            "services": [
                {"name": "api", "health": "unhealthy"},
                {"name": "web", "health": "unhealthy"},
            ],
            "service_dependencies": [{"service": "web", "depends_on": "api"}],
        }
    )
    alert = {
        "id": "a",
        "title": "x",
        "service": "web",
        "source": "web",
        "affected_services": "api",
        "timestamp": "2026-08-12T15:00:00",
    }
    metrics = {"service": "web", "target": "api"}
    context = {
        "change_events": [
            # >60 minutes apart -> confidence 0.55
            {"target": "api", "type": "deploy", "timestamp": "2026-08-12T16:10:00"}
        ],
        "verification_data": {
            "active_components": ["api", "web"],
            "observed_symptoms": [
                "Metrics should degrade after change to api",
                "Rollback or mitigation of api should relieve symptoms",
                "Node api should show abnormal metrics (CPU, memory, latency, errors)",
                "Downstream services dependent on api should report correlated failures",
                "Path web -> api should be observable in traces/dependencies",
            ],
            "real-time health metrics for all nodes in the causal path": "ok",
            "network path traces between source and root": "ok",
            "dependency call error rates and latency": "ok",
            "pre-change baseline metrics": "ok",
            "post-change metric diff": "ok",
            "change impact scope and rollback success data": "ok",
        },
    }
    results = await engine.analyze_root_causes_enhanced(alert, metrics, context)
    change = [h for h in results if h.hypothesis_id.startswith("change_")]
    assert change
    assert change[0].confidence == 0.55
    assert change[0].recommended_action == "escalate"
    assert change[0].requires_approval is True


async def test_analyze_max_candidates_break():
    engine = rci.RootCauseIntelligenceEngine()
    base = {"alerts": [{"alert_type": "x", "host": "web"}], "metrics": {}}  # noqa: F841  # Variable for test verification
    for i, name in enumerate(["pat1", "pat2", "pat3"], 1):
        engine.learn_historical_pattern({**base, "metrics": {f"m{i}": 95.0}}, name, 10.0, 0.8)

    metrics_data = {
        "m1": 95.0,
        "m2": 95.0,
        "m3": 95.0,
        "services": [
            {"name": "web", "health": "unhealthy"},
            {"name": "api", "health": "unhealthy"},
            {"name": "api_deploy", "health": "unhealthy"},
            {"name": "db", "health": "unhealthy"},
        ],
        "service_dependencies": [
            {"service": "web", "depends_on": "db"},
            {"service": "api", "depends_on": "db"},
        ],
    }
    alert = {
        "id": "a",
        "alert_type": "x",
        "host": "web",
        "service": "web",
        "affected_services": ["api", "api_deploy"],
        "timestamp": "2026-08-12T15:00:00",
    }
    context = {
        "change_events": [
            {
                "target": "api_deploy",
                "type": "deploy",
                "timestamp": "2026-08-12T15:05:00",
            }
        ],
    }
    results = await engine.analyze_root_causes_enhanced(alert, metrics_data, context)
    assert len(results) == rci.MAX_ROOT_CAUSE_CANDIDATES


async def test_generate_candidates_branches():
    engine = rci.RootCauseIntelligenceEngine()
    base = {  # noqa: F841  # Variable for test verification
        "alerts": [
            {"alert_type": "x", "host": "svc1"},
            {"alert_type": "x", "host": "svc2"},
        ],
        "metrics": {},
    }
    engine.learn_historical_pattern({**base, "metrics": {"e1": 5.0}}, "pat1", 10.0, 0.8)
    engine.learn_historical_pattern({**base, "metrics": {"e2": 5.0}}, "pat2", 10.0, 0.8)

    await engine.discover_topology_realtime(
        {
            "services": [
                {"name": "svc1", "health": "unhealthy"},
                {"name": "svc2", "health": "unhealthy"},
                {"name": "db", "health": "unhealthy"},
            ],
            "service_dependencies": [
                {"service": "svc1", "depends_on": "db"},
                {"service": "svc2", "depends_on": "db"},
            ],
        }
    )

    cands = await engine._generate_candidates(
        alert={"id": "a", "alert_type": "x", "host": "svc1", "service": "svc1"},
        metrics_data={"e1": 5.0, "e2": 5.0},
        affected=["svc2"],
        related_alerts=[{"host": "svc2", "alert_type": "x"}],
        change_events=[{"target": "svc1", "type": "deploy", "timestamp": "2026-08-12T15:00:00"}],
        excluded_ids=set(),
        seen_roots={"pat1"},  # force pattern continue for pat1
    )
    roots = {c.root_cause for c in cands}
    ids = {c.hypothesis_id for c in cands}
    assert "pat2" in roots
    assert "db" in roots
    assert any(i.startswith("change_") for i in ids)


# ---------------------------------------------------------------------------
# Scenario and verify tests
# ---------------------------------------------------------------------------


def test_generate_scenario_candidates_branches():
    engine = rci.RootCauseIntelligenceEngine()
    alert = {"title": "symptoms"}
    changes = []
    seen = set()

    dns = engine._generate_scenario_candidates(
        alert,
        {"dns_resolution_error_rate": 2.0, "dns_lookup_time_ms": 2000, "target": "api"},
        changes,
        seen,
    )
    assert dns
    assert dns[0].confidence == 0.95

    sql = engine._generate_scenario_candidates(
        alert,
        {
            "slow_query_rate": 2.0,
            "avg_query_duration_ms": 2000,
            "database": "db",
        },
        changes,
        seen,
    )
    assert sql
    assert sql[0].confidence == 0.95

    oom = engine._generate_scenario_candidates(
        alert,
        {"pod_name": "p1", "node_name": "n1", "memory_usage_percent": 96},
        changes,
        seen,
    )
    assert any("host_memory_pressure" in c.root_cause for c in oom)
