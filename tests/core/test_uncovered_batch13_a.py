# -*- coding: utf-8 -*-
"""Functional coverage tests for core batch 13-a modules."""

import numpy as np
import pytest

import core.kpi_config as kpi_config
import core.stats_engine as stats_engine
from core.causal.graph import CausalEdge, CausalGraph, CausalStrength
from core.causal.prediction import CausalPredictor, PredictionResult
from core.exceptions.third_party import (
    AIModelException,
    ExternalServiceException,
    IntegrationException,
    ThirdPartyException,
)
from core.priority.assessor import BusinessCriticality, BusinessImpact
from core.priority.ranker import PriorityRank, PriorityRanker

pytestmark = [pytest.mark.core]


@pytest.fixture(autouse=True)
def _reset_engine_state():
    """Reset global state used by stats_engine before each test."""
    stats_engine._summary_cache = {}
    stats_engine._decisions = []
    yield


# ---------------------------------------------------------------------------
# core.exceptions.third_party
# ---------------------------------------------------------------------------
def test_third_party_exceptions():
    base = ThirdPartyException("third party error", context={"x": 1})
    assert base.message == "third party error"
    assert base.error_code == "15_06_0001"
    assert base.context == {"x": 1}
    assert base.severity.value == "error"
    assert base.to_dict()["error_type"] == "ThirdPartyException"

    full_ext = ExternalServiceException(
        "service down",
        service_name="api",
        service_url="http://api.example.com",
        original_exception=ValueError("boom"),
    )
    assert full_ext.service_name == "api"
    assert full_ext.service_url == "http://api.example.com"
    assert full_ext.context["service_name"] == "api"
    assert full_ext.context["service_url"] == "http://api.example.com"

    min_ext = ExternalServiceException("service down")
    assert min_ext.service_name is None
    assert "service_name" not in min_ext.context

    full_ai = AIModelException("model failed", model_name="gpt-4", error_type="timeout")
    assert full_ai.model_name == "gpt-4"
    assert full_ai.error_type == "timeout"
    assert full_ai.context["model_name"] == "gpt-4"

    min_ai = AIModelException("model failed")
    assert min_ai.model_name is None
    assert "model_name" not in min_ai.context

    full_int = IntegrationException("sync failed", integration_type="Jira", sync_operation="pull")
    assert full_int.integration_type == "Jira"
    assert full_int.sync_operation == "pull"
    assert full_int.context["integration_type"] == "Jira"

    min_int = IntegrationException("sync failed")
    assert min_int.integration_type is None
    assert "integration_type" not in min_int.context


# ---------------------------------------------------------------------------
# core.kpi_config
# ---------------------------------------------------------------------------
def test_kpi_config_crud_and_resolve(tmp_path, monkeypatch):
    monkeypatch.setattr(
        kpi_config, "_KPI_CONFIG_PATH", str(tmp_path / "kpi_config.json")
    )

    # _ensure_defaults() now uses RLock, so calling _write_configs while holding
    # the same lock no longer deadlocks even when the file does not yet exist.
    configs = kpi_config.list_kpi_configs()
    assert len(configs) == 9
    assert configs == sorted(configs, key=lambda x: x["order"])

    first = configs[0]
    assert kpi_config.get_kpi_config(first["id"]) == first
    assert kpi_config.get_kpi_config("missing-id") is None

    new = kpi_config.create_kpi_config(
        {
            "name": "自定义指标",
            "endpoint": "snapshot",
            "field_path": "custom.value",
            "target": 42,
            "unit": "%",
            "visible": False,
        }
    )
    assert new["name"] == "自定义指标"
    assert new["endpoint"] == "snapshot"
    assert new["field_path"] == "custom.value"
    assert new["target"] == 42.0
    assert new["unit"] == "%"
    assert new["visible"] is False

    updated = kpi_config.update_kpi_config(
        new["id"], {"name": "updated", "target": 99, "order": 99}
    )
    assert updated is not None
    assert updated["name"] == "updated"
    assert updated["target"] == 99.0
    assert updated["order"] == 99

    assert kpi_config.update_kpi_config("missing-id", {"name": "x"}) is None

    assert kpi_config.delete_kpi_config(new["id"]) is True
    assert kpi_config.delete_kpi_config(new["id"]) is False

    assert kpi_config.resolve_field({"a": {"b": 1}}, "a.b") == 1
    assert kpi_config.resolve_field({"a": {}}, "a.b") is None
    assert kpi_config.resolve_field({"a": 1}, "a.b") is None
    assert kpi_config.resolve_field({"a": 1}, "b") is None
    assert kpi_config.resolve_field({"a": 1}, "") == {"a": 1}


# ---------------------------------------------------------------------------
# core.stats_engine
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_stats_engine_alerts_and_ingestion():
    stats_engine.record_ingestion(10)
    stats_engine.record_ingestion(5)
    stats_engine.record_alert_noise(100, 20)

    stats = await stats_engine.get_alert_stats()
    assert stats["alerts"]["raw"] == 100
    assert stats["alerts"]["effective"] == 20
    assert stats["ingestion"]["total_points"] == 15
    assert stats["ingestion"]["records"] == 2
    assert stats["period"]["start_time"] is None

    hourly = await stats_engine.get_alert_stats(aggregation="hourly")
    assert hourly == {"hourly": []}
    daily = await stats_engine.get_alert_stats(aggregation="daily")
    assert daily == {"daily": []}


@pytest.mark.asyncio
async def test_stats_engine_repairs_and_history():
    valid = await stats_engine.record_repair(
        {"script_key": "clear_temp", "host": "srv1"}
    )
    assert valid["success"] is True
    assert "repair_id" in valid

    missing_key = await stats_engine.record_repair({"host": "srv1"})
    assert missing_key["success"] is False
    not_a_dict = await stats_engine.record_repair("bad")
    assert not_a_dict["success"] is False

    await stats_engine.insert_repair_record({"host": "srv2", "service": "api"})
    await stats_engine.insert_repair_record({"host": "srv1", "service": "db"})
    await stats_engine.insert_repair_record({"host": "srv1", "service": "cache"})

    grouped = await stats_engine.get_repair_stats(group_by="host")
    assert grouped.get("srv1", 0) >= 1
    assert grouped.get("srv2", 0) >= 1

    ungrouped = await stats_engine.get_repair_stats()
    assert ungrouped["total_repairs"] >= 3
    assert "repairs" in ungrouped

    limited = await stats_engine.get_repair_history(limit=2)
    assert len(limited) == 2

    filtered = await stats_engine.get_repair_history(host="srv1")
    assert all(r["host"] == "srv1" for r in filtered)


@pytest.mark.asyncio
async def test_stats_engine_system_and_real_summary():
    systems = await stats_engine.get_system_stats()
    assert "cpu_percent" in systems
    assert "timestamp" in systems

    summary1 = await stats_engine.get_real_summary()
    assert summary1["from_cache"] is False
    assert "alerts" in summary1
    assert "repairs" in summary1
    assert "systems" in summary1

    summary2 = await stats_engine.get_real_summary()
    assert summary2["from_cache"] is True


def test_stats_engine_decision_accuracy():
    d1 = stats_engine.record_decision(prediction=True, decision_type="rca")
    d2 = stats_engine.record_decision(prediction=False, decision_type="remediate")
    assert stats_engine.record_outcome(d1, True) is True
    assert stats_engine.record_outcome(d2, True) is True
    assert stats_engine.record_outcome("unknown", True) is False

    rca = stats_engine.get_decision_accuracy("rca")
    assert rca["success"] is True
    assert rca["metrics"]["total"] == 1
    assert rca["metrics"]["true_positives"] == 1

    all_metrics = stats_engine.get_decision_accuracy()
    assert all_metrics["success"] is True
    assert all_metrics["metrics"]["total"] == 2

    summary = stats_engine.get_decision_summary()
    assert summary["success"] is True
    assert "rca" in summary["summary"]
    assert "remediate" in summary["summary"]
    assert "all" in summary["summary"]


def test_stats_engine_validation_and_client():
    assert stats_engine.validate_stats(
        {"total": 10, "success": 6, "failure": 4}
    ) == {"valid": True}
    assert stats_engine.validate_stats("not a dict")["valid"] is False
    assert stats_engine.validate_stats({"total": "x"})["valid"] is False
    assert (
        stats_engine.validate_stats({"total": 10, "success": 6, "failure": 3})["valid"]
        is False
    )

    client = stats_engine._get_http_client()
    assert client is not None
    client.close()

    stats_engine.record_collect({"provider": "aws"})


# ---------------------------------------------------------------------------
# core.causal.prediction
# ---------------------------------------------------------------------------
def test_causal_predictor():
    graph = CausalGraph("test")
    graph.add_node("cpu")
    graph.add_node("memory")
    graph.add_node("latency")
    graph.add_edge(CausalEdge("cpu", "latency", CausalStrength.STRONG))
    graph.add_edge(CausalEdge("memory", "latency", CausalStrength.MODERATE))

    predictor = CausalPredictor(graph)
    data = np.array(
        [
            [10.0, 8.0, 100.0],
            [20.0, 16.0, 90.0],
            [30.0, 24.0, 80.0],
            [40.0, 32.0, 70.0],
            [50.0, 40.0, 60.0],
        ],
        dtype=float,
    )
    predictor.fit(data, ["cpu", "memory", "latency"])

    result = predictor.predict("latency", {"cpu": 45.0, "memory": 36.0})
    assert isinstance(result, PredictionResult)
    assert result.target_node == "latency"
    assert 0 <= result.confidence <= 1

    no_parent = predictor.predict("cpu", {"cpu": 45.0})
    assert no_parent.confidence == 0.0
    assert no_parent.predicted_value == 45.0

    what_if = predictor.what_if(
        "cpu", 100.0, "latency", {"cpu": 45.0, "memory": 36.0}
    )
    assert what_if["has_effect"] is True
    assert "baseline_value" in what_if
    assert "predicted_value" in what_if
    assert "predicted_change" in what_if

    no_path = predictor.what_if(
        "cpu", 100.0, "memory", {"cpu": 45.0, "memory": 36.0}
    )
    assert no_path["has_effect"] is False
    assert "reason" in no_path

    counter = predictor.counterfactual(
        70.0, "latency", "cpu", {"cpu": 45.0, "memory": 36.0}
    )
    assert "counterfactual_effect" in counter
    assert "observed_outcome" in counter


# ---------------------------------------------------------------------------
# core.priority.ranker
# ---------------------------------------------------------------------------
def test_priority_ranker():
    alerts = [
        {
            "id": "a1",
            "service": "payment",
            "affected_users": 10000,
            "revenue_per_minute": 1000,
            "sla_violation": True,
            "urgency": "critical",
        },
        {
            "id": "a2",
            "service": "logging",
            "affected_users": 0,
            "revenue_per_minute": 0,
            "sla_violation": False,
            "urgency": "low",
        },
        {
            "id": "a3",
            "service": "api",
            "affected_users": 500,
            "revenue_per_minute": 100,
            "sla_violation": False,
            "urgency": "high",
        },
    ]

    ranker = PriorityRanker()
    ranked = ranker.rank_alerts(alerts)
    assert len(ranked) == 3
    assert ranked[0].alert_id == "a1"
    assert ranked[0].priority_level == "P0"
    assert all(rank.rank == i + 1 for i, rank in enumerate(ranked))

    top = ranker.get_top_n(alerts, n=2)
    assert len(top) == 2
    assert top[0].alert_id == "a1"

    filtered = ranker.filter_by_priority(alerts, min_level="P1")
    assert all(rank.priority_level in {"P0", "P1"} for rank in filtered)


def test_priority_ranker_thresholds_and_scoring():
    ranker = PriorityRanker()
    assert ranker._map_score_to_level(0.95) == "P0"
    assert ranker._map_score_to_level(0.8) == "P1"
    assert ranker._map_score_to_level(0.6) == "P2"
    assert ranker._map_score_to_level(0.3) == "P3"
    assert ranker._map_score_to_level(0.1) == "P4"

    impact = BusinessImpact(
        service="x",
        impact_score=0.8,
        criticality=BusinessCriticality.HIGH,
        affected_users=0,
        revenue_impact=0.0,
        sla_impact=False,
        factors={},
    )
    score = ranker._calculate_priority_score({"created_at": "now"}, impact)
    assert score == 0.8
