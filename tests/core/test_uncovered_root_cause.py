# -*- coding: utf-8 -*-
"""Unit tests for the large uncovered core modules root_cause_intelligence and heal_graph.

These tests exercise the public factory/entry-point methods and the main classes without
requiring real DB, network, or slow ML model training.  External/optional dependencies
are stubbed with monkeypatch or unittest.mock so the suite runs quickly offline.
"""

from datetime import datetime
from unittest.mock import AsyncMock

import pytest  # noqa: F401  # Imported for test setup

import core.ai_engine as ai_engine
import core.heal_graph as hg
import core.priority_engine as priority_engine
import core.root_cause_intelligence as rci
import core.runbook_generator as runbook_generator
import core.verifier as verifier

pytestmark = [pytest.mark.core]


@pytest.fixture
def rci_engine(monkeypatch):
    """Provide a RootCauseIntelligenceEngine with ML dependencies disabled for speed."""
    monkeypatch.setattr(rci, "ML_AVAILABLE", False)
    return rci.RootCauseIntelligenceEngine(config={})


@pytest.fixture
def stub_heal(monkeypatch):
    """Stub out all external side effects for core.heal_graph."""

    # Risk / command guard stubs
    class RL:
        BLOCKED = "BLOCKED"
        HIGH = "HIGH"
        LOW = "LOW"
        SAFE = "SAFE"

    monkeypatch.setattr(hg, "RiskLevel", RL)
    monkeypatch.setattr(hg, "analyze_command", lambda cmd: {"risk_level": RL.LOW, "reason": "ok"})

    # Audit / trace stubs
    monkeypatch.setattr(hg, "_set_trace_id", lambda _tid: None)
    monkeypatch.setattr(hg, "_get_trace_id", lambda: None)
    monkeypatch.setattr(hg, "_log_audit_event", lambda *a, **k: None)
    monkeypatch.setattr(hg, "record_audit", lambda *a, **k: None)

    # Notification / persistence stubs
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
    monkeypatch.setattr(hg, "notify_rollback_failure", AsyncMock())

    # Configuration
    monkeypatch.setattr(
        hg, "SNAPSHOT_CONFIG", {"enabled": True, "rollback_approval_required": False}
    )

    # Downstream core module functions imported inside the node functions
    monkeypatch.setattr(
        ai_engine, "analyze", AsyncMock(return_value="AI analysis: restart service")
    )
    monkeypatch.setattr(priority_engine, "compute_sla_score", lambda alert: 2)
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
def stub_heal_failed(stub_heal, monkeypatch):
    """Same as stub_heal but with a failing verification to exercise rollback."""
    monkeypatch.setattr(
        verifier,
        "verify_repair",
        AsyncMock(
            return_value={
                "verified": False,
                "passed": False,
                "strategy": "metric_threshold",
            }
        ),
    )
    return stub_heal


# ---------------------------------------------------------------------------
# core.root_cause_intelligence
# ---------------------------------------------------------------------------


def test_root_cause_statistics(rci_engine):
    stats = rci_engine.get_analysis_statistics()
    assert isinstance(stats, dict)
    expected = {
        "topology_nodes",
        "historical_patterns",
        "active_hypotheses",
        "verification_results",
        "pattern_match_accuracy",
        "average_verification_score",
    }
    assert set(stats.keys()) == expected
    assert stats["topology_nodes"] == 0
    assert 0 <= stats["pattern_match_accuracy"] <= 1
    assert 0 <= stats["average_verification_score"] <= 1


async def test_root_cause_topology_discovery(rci_engine):
    metrics_data = {
        "hosts": [{"hostname": "host1", "health": "healthy", "metrics": {"cpu": 0.1}}],
        "services": [{"name": "svc1", "health": "unhealthy", "port": 8080}],
        "applications": [{"name": "app1", "health": "healthy"}],
        "network_connections": [{"source": "svc1", "target": "host1"}],
    }
    alert = {
        "id": "a1",
        "service": "svc1",
        "affected_services": ["app1"],
    }
    result = await rci_engine.discover_topology_realtime(metrics_data, alert)  # noqa: F841  # Variable for test verification
    assert isinstance(result, dict)
    assert "discovered_nodes" in result
    assert "total_nodes" in result
    assert "topology_summary" in result
    assert result["discovered_nodes"] >= 3
    assert result["total_nodes"] >= result["discovered_nodes"]
    summary = result["topology_summary"]
    assert "layers" in summary and isinstance(summary["layers"], dict)
    assert "health_distribution" in summary and isinstance(summary["health_distribution"], dict)


async def test_root_cause_cross_layer_tracking(rci_engine):
    metrics_data = {
        "services": [{"name": "svc1", "health": "unhealthy", "port": 8080}],
        "network_connections": [
            {"source": "svc1", "target": "svc2"},
            {"source": "svc2", "target": "svc3"},
        ],
    }
    alert = {
        "id": "a2",
        "service": "svc1",
        "affected_services": ["svc1"],
    }
    await rci_engine.discover_topology_realtime(metrics_data, alert)
    path = await rci_engine.perform_cross_layer_tracking(alert, max_depth=5)
    assert isinstance(path, list)
    assert len(path) >= 1
    assert path[0] == "svc1"


async def test_root_cause_historical_patterns(rci_engine):
    symptoms = {
        "alerts": [{"alert_type": "cpu_high", "host": "host1"}],
        "metrics": {"cpu": 95.0},
    }
    rci_engine.learn_historical_pattern(symptoms, "cpu_overload", 120.0, 0.9)
    patterns = await rci_engine.match_historical_patterns(symptoms)
    assert isinstance(patterns, list)
    assert len(patterns) >= 1
    assert patterns[0].root_cause == "cpu_overload"
    assert patterns[0].frequency >= 1
    stats = rci_engine.get_analysis_statistics()
    assert stats["historical_patterns"] == 1


async def test_root_cause_analyze_enhanced(rci_engine):
    alert = {
        "id": "a3",
        "title": "DNS resolution timeout",
        "service": "web",
        "affected_services": ["api"],
    }
    metrics_data = {
        "service": "web",
        "target": "api",
        "dns_resolution_error_rate": 5.0,
        "dns_lookup_time_ms": 1500,
    }
    context = {
        "correlated_alerts": [],
        "change_events": [
            {
                "target": "api",
                "type": "deploy",
                "timestamp": "2026-08-12T15:00:00",
            }
        ],
    }
    results = await rci_engine.analyze_root_causes_enhanced(alert, metrics_data, context)
    assert isinstance(results, list)
    assert len(results) >= 1
    assert all(isinstance(h, rci.RootCauseHypothesis) for h in results)
    top = results[0]
    assert isinstance(top.root_cause, str)
    assert 0.0 <= top.confidence <= 1.0
    assert top.recommended_action in ("auto_heal", "collect_more_data", "escalate")


async def test_root_cause_verify(rci_engine):
    alert = {
        "id": "a4",
        "service": "svc",
        "affected_services": ["svc"],
    }
    metrics_data = {"service": "svc", "target": "api"}
    await rci_engine.discover_topology_realtime(metrics_data, alert)
    hypothesis = rci.RootCauseHypothesis(hypothesis_id="h1", root_cause="api", confidence=0.8)
    verification_data = {
        "active_components": ["api", "svc"],
    }
    result = await rci_engine.verify_root_cause(hypothesis, verification_data)  # noqa: F841  # Variable for test verification
    assert isinstance(result, dict)
    assert "verification_status" in result
    assert "verification_score" in result
    assert result["verification_score"] >= 0.0
    assert result["verification_status"] in (
        "verified",
        "partially_verified",
        "rejected",
    )


async def test_root_cause_predict(rci_engine):
    symptoms = {
        "alerts": [{"alert_type": "oom", "host": "node1"}],
        "metrics": {"memory_usage_percent": 96.0},
    }
    rci_engine.learn_historical_pattern(symptoms, "pod_oom", 60.0, 0.85)
    prediction = await rci_engine.predict_root_causes(symptoms, prediction_horizon=30)
    assert isinstance(prediction, dict)
    assert prediction["prediction_horizon"] == 30
    assert "predicted_root_causes" in prediction
    assert "confidence" in prediction
    assert len(prediction["predicted_root_causes"]) >= 1
    assert "probability" in prediction["predicted_root_causes"][0]


# ---------------------------------------------------------------------------
# core.heal_graph
# ---------------------------------------------------------------------------


def test_heal_state_defaults():
    state = hg.HealState()
    assert state.alert == {}
    assert state.sla_score is None
    assert state.analysis is None
    assert state.runbook is None
    assert state.fix_applied is False
    assert state.error is None
    assert state.executed_commands == []
    assert state.metrics == {}


def test_build_heal_graph():
    import asyncio  # noqa: F401  # Imported for test setup

    runner = hg._build_graph()
    assert callable(runner)
    assert asyncio.iscoroutinefunction(runner)


async def test_run_heal_success(stub_heal):
    state = hg.HealState(
        alert={
            "id": "alert-1",
            "title": "service down",
            "desc": "service is not responding",
            "metric": "service_down",
            "host": "host1",
            "platform": "linux",
        }
    )
    final = await hg.run_heal(state)
    assert isinstance(final, hg.HealState)
    assert final.error is None
    assert final.sla_score == 2
    assert final.analysis is not None
    assert isinstance(final.runbook, dict)
    assert final.runbook.get("success") is True
    assert final.fix_applied is True
    assert final.verification is not None
    assert final.verification.get("passed") is True
    assert final.metrics.get("status") == "success"
    assert final.snapshot_id == "snap-123"


async def test_run_heal_rollback(stub_heal_failed):
    state = hg.HealState(
        alert={
            "id": "alert-2",
            "title": "memory high",
            "desc": "memory usage exceeded threshold",
            "metric": "memory_high",
            "host": "host2",
            "platform": "linux",
        }
    )
    final = await hg.run_heal(state)
    assert isinstance(final, hg.HealState)
    assert final.fix_applied is False
    assert final.verification is not None
    assert final.verification.get("passed") is False
    assert final.snapshot_id == "snap-123"
