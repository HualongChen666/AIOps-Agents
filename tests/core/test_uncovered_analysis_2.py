# -*- coding: utf-8 -*-
"""Unit tests for partially-covered core analysis modules.

Covers branches and edge cases in:
  - core.root_cause_intelligence
  - core.heal_graph
  - core.analysis.l2.langgraph_engine
  - core.analysis.l2.enhanced_causal_analyzer
"""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

import core.root_cause_intelligence as rci
import core.heal_graph as hg
import core.ai_engine as ai_engine
import core.priority_engine as priority_engine
import core.runbook_generator as runbook_generator
import core.verifier as verifier
import core.analysis.l2.langgraph_engine as l2e
import core.analysis.l2.enhanced_causal_analyzer as eca
import core.phase3_metrics as phase3_metrics

pytestmark = [pytest.mark.core]


@pytest.fixture
def rci_engine(monkeypatch):
    """RootCauseIntelligenceEngine with ML components disabled."""
    monkeypatch.setattr(rci, "ML_AVAILABLE", False)
    engine = rci.RootCauseIntelligenceEngine(config={})
    return engine


@pytest.fixture
def stub_heal(monkeypatch):
    """Stub all heavy external side effects for heal_graph tests."""
    # Risk / command guard
    class RL:
        BLOCKED = "BLOCKED"
        HIGH = "HIGH"
        LOW = "LOW"
        SAFE = "SAFE"

    monkeypatch.setattr(hg, "RiskLevel", RL)
    monkeypatch.setattr(
        hg, "analyze_command", lambda cmd: {"risk_level": RL.LOW, "reason": "ok"}
    )

    # Audit / trace
    monkeypatch.setattr(hg, "_set_trace_id", lambda _tid: None)
    monkeypatch.setattr(hg, "_get_trace_id", lambda: None)
    monkeypatch.setattr(hg, "_log_audit_event", lambda *a, **k: None)
    monkeypatch.setattr(hg, "record_audit", lambda *a, **k: None)

    # Notifications / persistence
    monkeypatch.setattr(hg, "notify_rollback_failure", AsyncMock())
    monkeypatch.setattr(hg, "_send_alert_notification", AsyncMock())
    monkeypatch.setattr(
        hg,
        "async_get_approval_by_alert",
        AsyncMock(
            return_value={
                "status": "approved",
                "approved_at": datetime.now().isoformat(),
            }
        ),
    )
    monkeypatch.setattr(hg, "async_upsert_pending_approval", AsyncMock())
    monkeypatch.setattr(hg, "async_update_approval_status_by_alert", AsyncMock())
    monkeypatch.setattr(hg, "save_snapshot", AsyncMock(return_value="snap-123"))
    monkeypatch.setattr(hg, "update_snapshot_status", AsyncMock())
    monkeypatch.setattr(hg, "cleanup_expired_snapshots", AsyncMock())
    monkeypatch.setattr(hg, "async_insert_repair_record", AsyncMock())
    monkeypatch.setattr(hg, "record_decision", lambda *a, **k: "dec-1")
    monkeypatch.setattr(hg, "record_outcome", lambda *a, **k: None)

    # Metrics history stub
    monkeypatch.setattr(hg, "_metrics_history", MagicMock(to_dict=lambda: {}))

    # Configuration
    monkeypatch.setattr(
        hg,
        "SNAPSHOT_CONFIG",
        {"enabled": False, "rollback_approval_required": False},
    )

    # Prometheus counter stubs
    monkeypatch.setattr(phase3_metrics, "HEAL_TOTAL", MagicMock())
    monkeypatch.setattr(phase3_metrics, "HEAL_SUCCESS", MagicMock())
    monkeypatch.setattr(phase3_metrics, "HEAL_FAILED", MagicMock())
    monkeypatch.setattr(phase3_metrics, "LLM_COST_PER_INCIDENT", MagicMock())
    monkeypatch.setattr(phase3_metrics, "VERIFY_PASSED", MagicMock())
    monkeypatch.setattr(phase3_metrics, "VERIFY_FAILED", MagicMock())
    monkeypatch.setattr(phase3_metrics, "HEAL_PENDING_APPROVAL", MagicMock())

    # Core dependencies used by node functions
    monkeypatch.setattr(
        priority_engine, "compute_sla_score", lambda alert: 2
    )
    monkeypatch.setattr(
        ai_engine, "analyze", AsyncMock(return_value="AI analysis: restart service")
    )
    monkeypatch.setattr(
        runbook_generator,
        "generate_repair_runbook",
        AsyncMock(
            return_value={
                "success": True,
                "alert_id": "alert-1",
                "source": "AI_DYNAMIC",
                "worst_risk": "LOW",
                "auto_executable": True,
                "needs_approval": False,
                "guard_results": [],
                "runbook": {
                    "script_key": "AI_DYNAMIC",
                    "name": "AI generated runbook",
                    "commands": ["echo 'fix applied'"],
                    "rollback": "echo 'rollback'",
                    "risk_level": "LOW",
                    "params": {},
                    "confidence": 0.95,
                },
            }
        ),
    )
    monkeypatch.setattr(
        verifier,
        "verify_repair",
        AsyncMock(
            return_value={
                "verified": True,
                "passed": True,
                "strategy": "service_status",
            }
        ),
    )
    return hg


@pytest.fixture
def l2_engine(monkeypatch):
    """LangGraph analysis engine forced into fallback mode."""
    monkeypatch.setattr(l2e, "LANGGRAPH_AVAILABLE", False)
    engine = l2e.LangGraphAnalysisEngine(config={"model": "test"})
    return engine


@pytest.fixture
def eca_analyzer(monkeypatch):
    """Enhanced causal analyzer in fallback mode."""
    monkeypatch.setattr(eca, "CAUSAL_AVAILABLE", False)
    return eca.get_enhanced_causal_analyzer(config={"mode": "realtime"})


# ---------------------------------------------------------------------------
# core.root_cause_intelligence
# ---------------------------------------------------------------------------


def test_is_abnormal_true(rci_engine):
    metrics = {"cpu_usage_percent": 95.0}
    assert rci_engine._is_abnormal(metrics) is True
    metrics = {"error_rate": 0.1}
    assert rci_engine._is_abnormal(metrics) is True


def test_is_abnormal_false(rci_engine):
    metrics = {"cpu_usage_percent": 50.0, "error_rate": 0.01}
    assert rci_engine._is_abnormal(metrics) is False


async def test_topology_source_not_found(rci_engine):
    result = await rci_engine.perform_cross_layer_tracking(
        {"id": "a1", "service": "missing"}, max_depth=3
    )
    assert isinstance(result, list)
    assert result == ["missing"]


async def test_find_common_upstream_single(rci_engine):
    common = await rci_engine._find_common_upstream_dependency(["only"])
    assert common is None


async def test_match_historical_patterns_empty(rci_engine):
    patterns = await rci_engine.match_historical_patterns({"alerts": []})
    assert patterns == []


def test_learn_and_update_historical_pattern(rci_engine):
    symptoms = {"alerts": [{"alert_type": "cpu_high", "host": "host1"}], "metrics": {}}
    rci_engine.learn_historical_pattern(symptoms, "cpu_overload", 120.0, 0.9)
    first = list(rci_engine.historical_patterns.values())[0]
    assert first.frequency == 1
    first_conf = first.confidence
    rci_engine.learn_historical_pattern(symptoms, "cpu_overload", 100.0, 0.8)
    updated = list(rci_engine.historical_patterns.values())[0]
    assert updated.frequency == 2
    assert updated.confidence >= first_conf


async def test_causal_graph_analysis(rci_engine):
    alert = {"id": "a5", "source_service": "svc", "metric": "cpu", "value": 99}
    metrics = {"cpu": 99}
    result = await rci_engine._causal_graph_analysis(alert, metrics)
    assert isinstance(result, list)
    assert all(isinstance(h, rci.RootCauseHypothesis) for h in result)
    assert result[0].causal_path[0] == "svc"


async def test_ml_based_analysis(rci_engine):
    alert = {"metric": "cpu", "value": 100, "threshold": 80}
    metrics = {"cpu": 10.0, "cpu2": 20.0}
    result = await rci_engine._ml_based_analysis(alert, metrics)
    assert isinstance(result, list)
    assert isinstance(result[0], rci.RootCauseHypothesis)
    assert 0.0 <= result[0].confidence <= 1.0


async def test_analyze_enhanced_sql(rci_engine):
    alert = {
        "id": "a6",
        "title": "slow query",
        "service": "orders",
    }
    metrics = {
        "database": "orders_db",
        "slow_query_rate": 5.0,
        "avg_query_duration_ms": 2000,
    }
    context = {"correlated_alerts": [], "change_events": []}
    results = await rci_engine.analyze_root_causes_enhanced(alert, metrics, context)
    assert isinstance(results, list)
    assert all(isinstance(h, rci.RootCauseHypothesis) for h in results)
    causes = {h.root_cause for h in results}
    assert any("slow_sql" in c or "escalate" in c for c in causes)


async def test_analyze_enhanced_oom(rci_engine):
    alert = {"id": "a7", "title": "pod OOMKilled", "pod": "web-1"}
    metrics = {
        "pod_name": "web-1",
        "namespace": "prod",
        "node_name": "node-1",
        "memory_usage_percent": 96.0,
        "last_state": {"terminated": {"reason": "OOMKilled"}},
    }
    context = {"correlated_alerts": [], "change_events": []}
    results = await rci_engine.analyze_root_causes_enhanced(alert, metrics, context)
    assert isinstance(results, list)
    assert any(isinstance(h, rci.RootCauseHypothesis) for h in results)


async def test_analyze_enhanced_escalation(rci_engine):
    alert = {"id": "a8", "title": "unknown anomaly"}
    metrics = {}
    context = {"correlated_alerts": [], "change_events": []}
    results = await rci_engine.analyze_root_causes_enhanced(alert, metrics, context)
    assert isinstance(results, list)
    assert any(h.hypothesis_id == "escalate" for h in results)


async def test_verify_root_cause_scenarios(rci_engine):
    hyp = rci.RootCauseHypothesis(
        hypothesis_id="h-dns",
        root_cause="dns_resolution_failure_api",
        confidence=0.8,
        expected_observations=["dns timeout"],
    )
    data = {
        "active_components": ["api"],
        "observed_symptoms": ["dns timeout"],
        "dns_resolution_error_rate": 2.0,
    }
    result = await rci_engine.verify_root_cause(hyp, data)
    assert isinstance(result, dict)
    assert result["verification_status"] in (
        "verified",
        "partially_verified",
        "rejected",
    )


async def test_predict_root_causes_empty(rci_engine):
    prediction = await rci_engine.predict_root_causes({"alerts": [], "metrics": {}})
    assert isinstance(prediction, dict)
    assert prediction["prediction_horizon"] == 60
    assert prediction["predicted_root_causes"] == []
    assert prediction["confidence"] == 0.0


def test_parse_timestamp(rci_engine):
    assert rci_engine._parse_timestamp("2026-08-12T15:00:00Z") is not None
    assert rci_engine._parse_timestamp(1700000000) is not None
    assert rci_engine._parse_timestamp("not-a-date") is None
    assert rci_engine._parse_timestamp(None) is None


def test_populate_expected_and_missing(rci_engine):
    h = rci.RootCauseHypothesis(
        hypothesis_id="topology_host1",
        root_cause="host1",
        confidence=0.7,
        causal_path=["svc", "host1"],
    )
    populated = rci_engine._populate_expected_and_missing(h, {})
    assert populated.expected_observations
    assert populated.missing_data
    assert "host1" in populated.expected_observations[0]


def test_analysis_statistics_with_results(rci_engine):
    rci_engine.verification_results["v1"] = {
        "verification_status": "verified",
        "verification_score": 0.9,
    }
    stats = rci_engine.get_analysis_statistics()
    assert stats["verification_results"] == 1
    assert 0 <= stats["pattern_match_accuracy"] <= 1
    assert 0 <= stats["average_verification_score"] <= 1


# ---------------------------------------------------------------------------
# core.heal_graph
# ---------------------------------------------------------------------------


def test_heal_state_edge_defaults():
    state = hg.HealState()
    assert state.alert == {}
    assert state.sla_score is None
    assert state.fix_applied is False
    assert state.executed_commands == []
    assert state.metrics == {}
    state.alert = {"id": "x"}
    assert state.alert["id"] == "x"


def test_build_graph_exists(stub_heal):
    runner = stub_heal._build_graph()
    assert runner is not None


async def test_run_heal_missing_alert_id(monkeypatch, stub_heal):
    async def _fake_runner(state):
        state.error = "Missing alert_id; cannot execute repair without approval"
        return state

    monkeypatch.setattr(stub_heal, "_heal_graph_runner", _fake_runner)
    state = hg.HealState(alert={"title": "fail"})
    final = await stub_heal.run_heal(state)
    assert isinstance(final, hg.HealState)
    assert final.error is not None
    assert "Missing alert_id" in final.error


async def test_run_heal_success_path(monkeypatch, stub_heal):
    async def _fake_runner(state):
        state.sla_score = 2
        state.analysis = {"root_cause": "x"}
        state.runbook = {"success": True}
        state.fix_applied = True
        state.verification = {"passed": True}
        state.snapshot_id = "snap-123"
        return state

    monkeypatch.setattr(stub_heal, "_heal_graph_runner", _fake_runner)
    state = hg.HealState(alert={"id": "alert-ok", "metric": "cpu_high"})
    final = await stub_heal.run_heal(state)
    assert isinstance(final, hg.HealState)
    assert final.error is None
    assert final.sla_score == 2


async def test_apply_fix_no_runbook(stub_heal):
    state = hg.HealState(alert={"id": "alert-3"})
    result = await stub_heal.apply_fix(state)
    assert isinstance(result, hg.HealState)
    assert "No valid runbook" in (result.error or "")


async def test_apply_fix_missing_alert_id(stub_heal):
    state = hg.HealState(alert={"title": "no id"}, runbook={"success": True})
    result = await stub_heal.apply_fix(state)
    assert "Missing alert_id" in (result.error or "")


async def test_generate_runbook_success(stub_heal):
    state = hg.HealState(
        alert={"id": "g1", "title": "x", "desc": "y"},
        analysis={"query": "x"},
    )
    result = await stub_heal.generate_runbook(state)
    assert isinstance(result.runbook, dict)
    assert result.runbook.get("success") is True


async def test_evaluate_string_runbook(stub_heal):
    state = hg.HealState(
        alert={"id": "e1"},
        fix_applied=True,
        runbook="plain runbook text",
    )
    result = await stub_heal.evaluate(state)
    assert isinstance(result.verification, dict)
    assert result.verification.get("passed") is True


async def test_rollback_blocked_without_approval(monkeypatch, stub_heal):
    monkeypatch.setattr(
        stub_heal, "SNAPSHOT_CONFIG", {"rollback_approval_required": True}
    )
    state = hg.HealState(
        alert={"id": "r1"},
        verification={"passed": False},
        approval_status=None,
        rollback_info={"rollback_commands": ["echo rollback"]},
    )
    result = await stub_heal.rollback(state)
    assert isinstance(result, hg.HealState)
    assert "not approved" in (result.error or "").lower()


async def test_rollback_no_commands(stub_heal):
    state = hg.HealState(
        alert={"id": "r2"},
        verification={"passed": False},
        approval_status="approved",
        rollback_info={"rollback_commands": []},
        snapshot_id="snap-123",
    )
    result = await stub_heal.rollback(state)
    assert isinstance(result, hg.HealState)


async def test_complete_status_variants(stub_heal):
    state = hg.HealState(
        alert={"id": "c1"},
        fix_applied=True,
        verification={"passed": True},
    )
    result = await stub_heal.complete(state)
    assert result.metrics.get("status") == "success"

    state.fix_applied = True
    state.verification = {"passed": False}
    state.error = "it failed"
    result = await stub_heal.complete(state)
    assert result.metrics.get("status") == "failure"


def test_heal_helpers():
    assert hg._is_alert_resolved({"status": "resolved"}) is True
    assert hg._is_alert_resolved({"resolved": True}) is True
    assert hg._is_alert_resolved({"resolved_condition": {"metric": "x", "operator": ">", "threshold": 1}}) is False
    assert hg._is_hardware_alert({"category": "hardware"}) is True
    assert hg._is_hardware_alert({"metric": "ipmi fan failure"}) is True
    assert hg._extract_command_target("systemctl restart nginx") == "nginx"
    assert hg._extract_command_target("echo hello") is None
    assert "nginx" in hg._allowed_targets_from_alert({"service": "nginx"})


# ---------------------------------------------------------------------------
# core.analysis.l2.langgraph_engine
# ---------------------------------------------------------------------------


def test_langgraph_engine_status(l2_engine):
    status = l2_engine.get_status()
    assert isinstance(status, dict)
    assert "initialized" in status
    assert "langgraph_available" in status
    assert status["config"]["model"] == "test"


async def test_langgraph_engine_analyze_fallback(l2_engine, monkeypatch):
    monkeypatch.setattr(
        ai_engine,
        "analyze",
        lambda _prompt, **kwargs: {
            "candidates": [
                {
                    "root_cause": "dns",
                    "confidence": 0.8,
                    "expected_observations_if_true": [],
                    "missing_data": [],
                    "is_verifiable": True,
                }
            ],
            "escalation_recommended": False,
        },
    )
    result = await l2_engine.analyze("dns latency", context={"cluster": "c1"})
    assert isinstance(result, dict)
    assert "candidates" in result or "error" in result


def test_langgraph_query_builders(l2_engine):
    promql = l2_engine._build_promql_query("cpu high on orders")
    assert "cpu" in promql.lower()
    logql = l2_engine._build_logql_query("error timeout")
    assert "error" in logql.lower()
    prompt = l2_engine._build_analysis_prompt("slow", {"metrics": "m"})
    assert "Analyze" in prompt
    assert "JSON" in prompt


def test_langgraph_assess_completeness(l2_engine):
    result = l2_engine._assess_completeness(
        {"data": []}, {"_data_completeness": "failed"}
    )
    assert isinstance(result, dict)
    assert result["metrics_available"] is True
    assert result["logs_available"] is False
    assert "logs" in result["sources_missing"]


# ---------------------------------------------------------------------------
# core.analysis.l2.enhanced_causal_analyzer
# ---------------------------------------------------------------------------


def test_enhanced_causal_factory():
    analyzer = eca.get_enhanced_causal_analyzer(config={"mode": "batch"})
    assert isinstance(analyzer, eca.EnhancedCausalAnalyzer)
    assert analyzer.mode.value == "batch"
    metrics = analyzer.get_performance_metrics()
    assert isinstance(metrics, dict)
    assert "analysis_count" in metrics


async def test_enhanced_causal_analyze_relationships(eca_analyzer):
    data = {
        "cpu": [10.0, 20.0, 30.0, 40.0],
        "memory": [100.0, 200.0, 300.0, 400.0],
        "disk": [1.0, 2.0, 3.0, 4.0],
    }
    timestamps = [datetime.now(timezone.utc) for _ in range(len(data["cpu"]))]
    result = await eca_analyzer.analyze_causal_relationships(
        data, timestamps, target_variable="cpu"
    )
    assert isinstance(result, eca.CausalAnalysisResult)
    assert result.confidence >= 0.0
    assert "analysis_time" in result.metadata


async def test_enhanced_causal_realtime(eca_analyzer):
    stream = {"cpu": 80.0, "memory": 70.0}
    result = await eca_analyzer.realtime_analysis(stream, window_size=10)
    assert isinstance(result, eca.CausalAnalysisResult)
    assert result.confidence == 0.7
    assert "cpu" in result.root_causes


def test_enhanced_simplified_graph(eca_analyzer):
    graph = eca_analyzer._build_simplified_causal_graph(
        {"cpu": [1, 2, 3], "memory": [10, 20, 30]}, target="unknown"
    )
    nodes = [n for n in graph.nodes]
    assert "cpu" in nodes
    assert "memory" in nodes
    assert "unknown" not in nodes
    assert len(graph.edges) == 0

    graph2 = eca_analyzer._build_simplified_causal_graph(
        {"cpu": [1, 2, 3], "memory": [10, 20, 30]}, target="cpu"
    )
    assert any(e.to_var == "cpu" for e in graph2.edges)


def test_enhanced_find_path(eca_analyzer):
    graph = eca.FallbackCausalGraph(name="g")
    for n in ("a", "b", "c"):
        graph.add_node(n)
    graph.add_edge(eca.FallbackCausalEdge("a", "b"))
    graph.add_edge(eca.FallbackCausalEdge("b", "c"))
    path = eca_analyzer._find_path(graph, "a", "c")
    assert path == ["a", "b", "c"]
    no_path = eca_analyzer._find_path(graph, "c", "a")
    assert no_path == []


def test_enhanced_confidence_calculation(eca_analyzer):
    assert eca_analyzer._calculate_confidence(["a"], {"a": 0.8}) == 0.8
    assert eca_analyzer._calculate_confidence([], {}) == 0.0
