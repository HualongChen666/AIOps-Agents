# -*- coding: utf-8 -*-
"""Targeted coverage tests for core.analysis.l2.enhanced_causal_analyzer and
core.intelligent_alert_analyzer.
"""

import asyncio  # noqa: F401  # Imported for test setup
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytest  # noqa: F401  # Imported for test setup

pytestmark = [pytest.mark.core]

import core.analysis.l2.enhanced_causal_analyzer as eca
import core.intelligent_alert_analyzer as analyzer

# -----------------------------------------------------------------------------
# core.analysis.l2.enhanced_causal_analyzer
# -----------------------------------------------------------------------------


@pytest.fixture
def eca_fallback(monkeypatch):
    """Enhanced causal analyzer in simplified/fallback mode."""
    monkeypatch.setattr(eca, "CAUSAL_AVAILABLE", False)
    return eca.get_enhanced_causal_analyzer(config={"mode": "realtime"})


@pytest.fixture
def eca_full(monkeypatch):
    """Enhanced causal analyzer with mocked causal components."""

    class MockTimeSeriesPreprocessor:
        def __init__(self, *args, **kwargs):
            pass

        def preprocess(self, data):
            return data

    class MockRootCauseInference:
        def __init__(self, *args, **kwargs):
            pass

        def infer(self, graph, target):
            return ["memory", "disk"]

    class MockImpactAnalyzer:
        def __init__(self, *args, **kwargs):
            pass

        def analyze(self, graph, root_causes):
            return {cause: 0.9 for cause in root_causes}

    class MockCausalPredictor:
        def __init__(self, *args, **kwargs):
            pass

    class MockPCAlgorithm:
        def __init__(self, *args, **kwargs):
            pass

        def discover(self, *args, **kwargs):
            if len(args) == 2 and isinstance(args[0], dict):
                raise TypeError("dict signature not supported")
            if len(args) == 2 and isinstance(args[1], list):
                raise TypeError("array+names not supported")
            return [
                eca.FallbackCausalEdge(
                    "memory",
                    "cpu",
                    eca.FallbackCausalStrength.MODERATE,
                    0.95,
                )
            ]

    monkeypatch.setattr(eca, "CAUSAL_AVAILABLE", True)
    monkeypatch.setattr(eca, "CausalGraph", eca.FallbackCausalGraph)
    monkeypatch.setattr(eca, "CausalEdge", eca.FallbackCausalEdge)
    monkeypatch.setattr(eca, "CausalStrength", eca.FallbackCausalStrength)
    monkeypatch.setattr(eca, "TimeSeriesPreprocessor", MockTimeSeriesPreprocessor)
    monkeypatch.setattr(eca, "RootCauseInference", MockRootCauseInference)
    monkeypatch.setattr(eca, "ImpactAnalyzer", MockImpactAnalyzer)
    monkeypatch.setattr(eca, "CausalPredictor", MockCausalPredictor)
    monkeypatch.setattr(eca, "PCAlgorithm", MockPCAlgorithm)
    return eca.get_enhanced_causal_analyzer(config={"mode": "batch"})


def test_causal_analysis_mode_and_result():
    assert eca.CausalAnalysisMode.BATCH.value == "batch"
    result = eca.CausalAnalysisResult()  # noqa: F841  # Variable for test verification
    assert result.root_causes == []
    assert result.confidence == 0.0


def test_fallback_causal_graph_duplicate_node():
    g = eca.FallbackCausalGraph(name="g")
    g.add_node("a")
    g.add_node("a")
    assert g.nodes == ["a"]


async def test_enhanced_analyze_with_full_components(eca_full):
    data = {
        "cpu": [10.0, 20.0, 30.0, 40.0],
        "memory": [10.0, 20.0, 30.0, 40.0],
        "disk": [1.0, 2.0, 1.0, 2.0],
    }
    timestamps = [datetime.now(timezone.utc) for _ in range(len(data["cpu"]))]
    result = await eca_full.analyze_causal_relationships(
        data, timestamps, target_variable="cpu"
    )  # noqa: F841  # Variable for test verification
    assert isinstance(result, eca.CausalAnalysisResult)
    assert result.confidence > 0.0
    assert "memory" in result.root_causes
    assert result.metadata["nodes_count"] == 3
    assert result.metadata["edges_count"] >= 1
    assert result.metadata["mode"] == "batch"

    metrics = eca_full.get_performance_metrics()
    assert metrics["analysis_count"] == 1
    assert metrics["avg_analysis_time"] >= 0.0


async def test_enhanced_analyze_error_path(eca_full, monkeypatch):
    class BadPreprocessor:
        def __init__(self, *args, **kwargs):
            pass

        def preprocess(self, data):
            raise RuntimeError("preprocess failed")

    monkeypatch.setattr(eca, "TimeSeriesPreprocessor", BadPreprocessor)
    an = eca.get_enhanced_causal_analyzer(config={"mode": "realtime"})
    data = {"cpu": [1.0]}
    result = await an.analyze_causal_relationships(  # noqa: F841  # Variable for test verification
        data, [datetime.now(timezone.utc)], target_variable="cpu"
    )
    assert isinstance(result, eca.CausalAnalysisResult)
    assert result.root_causes == ["cpu"]
    assert result.confidence == 0.5
    assert "error" in result.metadata


def test_enhanced_add_correlation_edges_exception(eca_fallback):
    graph = eca.FallbackCausalGraph(name="g")
    data = {"cpu": [1.0, 2.0, 3.0], "memory": [10.0]}
    eca_fallback._add_correlation_edges(graph, data, "cpu")
    assert len(graph.edges) == 0


def test_enhanced_simplified_helpers(eca_fallback):
    g = eca.FallbackCausalGraph(name="g")
    for n in ("cpu", "memory", "disk"):
        g.add_node(n)
    g.add_edge(eca.FallbackCausalEdge("memory", "cpu", eca.FallbackCausalStrength.MODERATE, 0.9))
    g.add_edge(eca.FallbackCausalEdge("disk", "cpu", eca.FallbackCausalStrength.STRONG, 0.95))

    roots = eca_fallback._infer_root_causes_simplified(g, "cpu")
    assert "memory" in roots
    assert "disk" in roots

    impact = eca_fallback._analyze_impact_simplified(g, roots)
    for cause in roots:
        assert cause in impact
        assert isinstance(impact[cause], float)

    g2 = eca.FallbackCausalGraph(name="g2")
    g2.add_node("cpu")
    g2.add_edge(eca.FallbackCausalEdge("memory", "cpu", eca.FallbackCausalStrength.MODERATE, 0.9))
    g2.add_edge("not-an-edge")
    assert eca_fallback._get_edge_confidence(g2, "memory", "cpu") == 0.9
    assert eca_fallback._get_edge_confidence(g2, "missing", "cpu") == 0.0


def test_enhanced_find_path_and_causal_paths(eca_fallback):
    g = eca.FallbackCausalGraph(name="g")
    for n in ("a", "b", "c", "d"):
        g.add_node(n)
    g.add_edge(eca.FallbackCausalEdge("a", "b"))
    g.add_edge(eca.FallbackCausalEdge("b", "c"))
    g.add_edge("bad")
    g.add_edge(object())

    assert eca_fallback._find_path(g, "a", "c") == ["a", "b", "c"]
    assert eca_fallback._find_path(g, "c", "a") == []
    assert eca_fallback._find_path(g, "d", "a") == []

    paths = eca_fallback._find_causal_paths(g, "c")
    assert ["a", "b", "c"] in paths
    assert ["b", "c"] in paths


async def test_enhanced_build_causal_graph_noniterable(eca_full, monkeypatch):
    class MockPCAlgorithmNonIterable:
        def __init__(self, *args, **kwargs):
            pass

        def discover(self, *args, **kwargs):
            return 123  # non-iterable, triggers fallback to correlation edges

    monkeypatch.setattr(eca, "PCAlgorithm", MockPCAlgorithmNonIterable)
    data = {
        "cpu": [10.0, 20.0, 30.0, 40.0],
        "memory": [10.0, 20.0, 30.0, 40.0],
    }
    graph = await eca_full._build_causal_graph(data, "cpu")
    assert "cpu" in graph.nodes
    assert "memory" in graph.nodes


# -----------------------------------------------------------------------------
# core.intelligent_alert_analyzer
# -----------------------------------------------------------------------------


async def test_intelligent_initialize_without_ml(monkeypatch):
    monkeypatch.setattr(analyzer, "ML_AVAILABLE", False)
    a = analyzer.IntelligentAlertAnalyzer()
    await a.initialize()
    assert a.tfidf_vectorizer is None
    assert a.clustering_model is None

    alerts = [
        analyzer.Alert(
            "1",
            analyzer.AlertSeverity.HIGH,
            "disk full",
            "host-a",
            datetime.now(),
        )
    ]
    aggregated = await a.aggregate_alerts(alerts)
    assert len(aggregated) == 1


async def test_intelligent_ml_aggregation_paths(monkeypatch):
    a = analyzer.IntelligentAlertAnalyzer()
    await a.initialize()
    alerts = [
        analyzer.Alert(
            "1",
            analyzer.AlertSeverity.HIGH,
            "disk full",
            "host-a",
            datetime.now(),
        ),
        analyzer.Alert(
            "2",
            analyzer.AlertSeverity.HIGH,
            "disk full",
            "host-a",
            datetime.now(),
        ),
    ]
    agg1 = await a.aggregate_alerts(alerts)
    assert len(agg1) >= 1

    # second call reuses fitted vectorizer and clustering model
    agg2 = await a.aggregate_alerts(alerts)
    assert len(agg2) >= 1

    def raise_error(*args, **kwargs):
        raise RuntimeError("similarity boom")

    monkeypatch.setattr(analyzer, "cosine_similarity", raise_error)
    agg3 = await a.aggregate_alerts(alerts)
    assert len(agg3) >= 1


def test_intelligent_determine_trend():
    a = analyzer.IntelligentAlertAnalyzer()
    now = datetime.now()
    increasing = a._determine_trend(
        [(now, 10.0)] * 5,
        [100.0] * 5,
    )
    assert increasing == "increasing"
    decreasing = a._determine_trend(
        [(now, 10.0)] * 5,
        [5.0] * 5,
    )
    assert decreasing == "decreasing"
    stable = a._determine_trend(
        [(now, 10.0)] * 5,
        [10.0] * 5,
    )
    assert stable == "stable"
    empty = a._determine_trend([], [])
    assert empty == "stable"


async def test_intelligent_trend_prediction(monkeypatch):
    class FakeProphet:
        def __init__(self, *args, **kwargs):
            pass

        def make_future_dataframe(self, periods):
            return pd.DataFrame({"ds": pd.date_range("2026-01-01", periods=periods, freq="h")})

        def predict(self, future):
            df = future.copy()
            df["yhat"] = 5.0
            return df

    monkeypatch.setattr(analyzer, "PROPHET_AVAILABLE", True)
    monkeypatch.setattr(analyzer, "Prophet", FakeProphet)
    a = analyzer.IntelligentAlertAnalyzer()
    now = datetime.now()
    data = [(now - timedelta(hours=i), float(i)) for i in range(20)]
    pred1 = await a.predict_alert_trends("cpu", data)
    assert pred1 is not None
    assert pred1.trend == "decreasing"
    assert len(pred1.predicted_values) == 24

    # reuse existing prophet model
    pred2 = await a.predict_alert_trends("cpu", data)
    assert pred2 is not None


async def test_intelligent_trend_prediction_exception(monkeypatch):
    class BadProphet:
        def __init__(self, *args, **kwargs):
            pass

        def make_future_dataframe(self, *args, **kwargs):
            raise RuntimeError("prophet boom")

    monkeypatch.setattr(analyzer, "PROPHET_AVAILABLE", True)
    monkeypatch.setattr(analyzer, "Prophet", BadProphet)
    a = analyzer.IntelligentAlertAnalyzer()
    now = datetime.now()
    data = [(now - timedelta(hours=i), float(i)) for i in range(20)]
    assert await a.predict_alert_trends("cpu", data) is None


def test_intelligent_routing_rule_matching():
    a = analyzer.IntelligentAlertAnalyzer()
    alert = analyzer.Alert(
        "r1",
        analyzer.AlertSeverity.CRITICAL,
        "db down",
        "db",
        datetime.now(),
        labels=["team:sre", "env:prod"],
    )
    assert a._matches_routing_rule(alert, {"severity": "critical"}) is True
    assert a._matches_routing_rule(alert, {"severity": "high"}) is False
    assert a._matches_routing_rule(alert, {"source": "db"}) is True
    assert a._matches_routing_rule(alert, {"source": "other"}) is False
    assert a._matches_routing_rule(alert, {"labels": ["team:sre"]}) is True
    assert a._matches_routing_rule(alert, {"labels": ["missing"]}) is False
    assert a._matches_routing_rule(alert, {}) is True


def test_intelligent_topology_routing_and_team_mapping():
    a = analyzer.IntelligentAlertAnalyzer()
    a.topology_graph = {"db": ["api"]}
    alert_db = analyzer.Alert(
        "r1",
        analyzer.AlertSeverity.HIGH,
        "db slow",
        "db",
        datetime.now(),
        related_entities=["db"],
    )
    teams = a._topology_aware_routing(alert_db)
    assert "backend-team" in teams

    unknown_alert = analyzer.Alert(
        "r2",
        analyzer.AlertSeverity.HIGH,
        "x",
        "x",
        datetime.now(),
        related_entities=["unknown"],
    )
    assert a._topology_aware_routing(unknown_alert) == []

    assert a._get_team_for_entity("database") == "database-team"
    assert a._get_team_for_entity("noop") is None


def test_intelligent_suppression_rules():
    a = analyzer.IntelligentAlertAnalyzer()
    alert = analyzer.Alert(
        "s1",
        analyzer.AlertSeverity.INFO,
        "this is noise",
        "src",
        datetime.now(),
    )
    assert a._matches_suppression_rule(alert, {"pattern": "noise"}) is True
    assert a._matches_suppression_rule(alert, {"pattern": "xyz"}) is False
    assert a._matches_suppression_rule(alert, {"time_window": 60, "max_frequency": 10}) is False


async def test_intelligent_noise_reduction_and_known_patterns():
    a = analyzer.IntelligentAlertAnalyzer()
    await a.add_suppression_rule({"time_window": 300, "max_frequency": 5})
    now = datetime.now()
    alert = analyzer.Alert(
        "n1",
        analyzer.AlertSeverity.INFO,
        "ignore this",
        "host",
        now,
    )
    # no matching pattern yet -> not suppressed
    result = await a.reduce_alert_noise([alert])  # noqa: F841  # Variable for test verification
    assert len(result) == 1
    assert result[0].id == "n1"

    # create a known noise pattern
    key = a._generate_pattern_key(alert)
    for i in range(12):
        a.alert_patterns[key].append(
            analyzer.Alert(
                f"p{i}",
                analyzer.AlertSeverity.INFO,
                "ignore this",
                "host",
                now,
            )
        )
    result2 = await a.reduce_alert_noise([alert])
    assert result2 == []


async def test_intelligent_correlate_topology_expansion():
    a = analyzer.IntelligentAlertAnalyzer()
    await a.update_topology({"db": ["api"]})
    alert_db = analyzer.Alert(
        "a1",
        analyzer.AlertSeverity.HIGH,
        "db",
        "db",
        datetime.now(),
        related_entities=["db"],
    )
    alert_api = analyzer.Alert(
        "a2",
        analyzer.AlertSeverity.HIGH,
        "api",
        "api",
        datetime.now(),
        related_entities=["api"],
    )
    correlated = await a.correlate_alerts_with_topology([alert_db, alert_api])
    assert "db" in correlated
    assert "api" in correlated
    assert any(alert.id == "a2" for alert in correlated["db"])

    # dependency not present as its own correlation group
    correlated2 = await a.correlate_alerts_with_topology([alert_db])
    assert "db" in correlated2
    assert all(alert.id == "a1" for alert in correlated2["db"])
