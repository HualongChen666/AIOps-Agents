# -*- coding: utf-8 -*-
"""Unit tests for previously uncovered enhanced core modules.

These tests exercise the public factory/main class methods of the enhanced AI,
root cause, and integration manager modules without touching real network or
ML model training.  Optional external dependencies are stubbed with monkeypatch
and AsyncMock so the suite runs offline.
"""

from datetime import datetime
from unittest.mock import AsyncMock

import pytest  # noqa: F401  # Imported for test setup

import core.enhanced_ai_capabilities as ai
import core.enhanced_root_cause_analyzer as rca
import core.integration_manager as im

pytestmark = [pytest.mark.core]


# ---------------------------------------------------------------------------
# Fakes for core.enhanced_ai_capabilities
# ---------------------------------------------------------------------------


class _FakeArray:
    def __init__(self, data):
        self._data = list(data)

    def reshape(self, *args):
        return self

    def __len__(self):
        return len(self._data)

    def __iter__(self):
        return iter(self._data)

    def __getitem__(self, idx):
        return self._data[idx]


class _FakeNP:
    @staticmethod
    def array(data):
        return _FakeArray(data)

    @staticmethod
    def mean(values):
        return sum(values) / len(values) if values else 0.0


class _FakeSeries:
    def __init__(self, values):
        self.values = list(values)
        self.iloc = self

    def tail(self, n):
        return _FakeSeries(self.values[-n:])

    def tolist(self):
        return self.values

    def __getitem__(self, idx):
        return self.values[idx]


class _FakePD:
    @staticmethod
    def DataFrame(data, columns=None):
        if columns and data:
            return dict(zip(columns, zip(*data)))
        return {}

    @staticmethod
    def to_datetime(values):
        if hasattr(values, "__iter__") and not isinstance(values, str):
            return list(values)
        return [values]


class _FakeProphet:
    def __init__(self, **kwargs):
        pass

    def fit(self, df):
        pass

    def make_future_dataframe(self, periods):
        return None

    def predict(self, future):
        return {
            "yhat": _FakeSeries([1.0] * 24),
            "yhat_lower": _FakeSeries([0.5] * 24),
            "yhat_upper": _FakeSeries([1.5] * 24),
            "ds": _FakeSeries([datetime.now()] * 24),
        }


class _FakeIsolationForest:
    def __init__(self, **kwargs):
        pass

    def fit(self, X):
        pass

    def predict(self, X):
        return [-1]

    def decision_function(self, X):
        return [0.5]


# ---------------------------------------------------------------------------
# core.enhanced_ai_capabilities
# ---------------------------------------------------------------------------


@pytest.fixture
def ai_cap(monkeypatch):
    """Provide an EnhancedAICapabilities instance with ML deps stubbed."""
    monkeypatch.setattr(ai, "ML_AVAILABLE", True)
    monkeypatch.setattr(ai, "PROPHET_AVAILABLE", True)
    monkeypatch.setattr(ai, "np", _FakeNP(), raising=False)
    monkeypatch.setattr(ai, "pd", _FakePD(), raising=False)
    monkeypatch.setattr(ai, "Prophet", _FakeProphet, raising=False)
    monkeypatch.setattr(ai, "IsolationForest", _FakeIsolationForest, raising=False)
    monkeypatch.setattr(ai, "_fit_model", AsyncMock())

    cap = ai.EnhancedAICapabilities()
    cap.min_samples_for_training = 3
    return cap


async def test_enhanced_ai_predict_timeseries(ai_cap):
    historical = [(datetime.now(), float(i)) for i in range(30)]
    result = await ai_cap.predict_timeseries("cpu_usage", historical)  # noqa: F841  # Variable for test verification
    assert isinstance(result, ai.PredictionResult)
    assert result.prediction_type == ai.PredictionType.TIMESERIES
    assert isinstance(result.predicted_values, list)
    assert len(result.predicted_values) == 24
    assert "horizon_hours" in result.metadata


async def test_enhanced_ai_predict_anomalies(ai_cap):
    historical = [(datetime.now(), float(i)) for i in range(50)]
    result = await ai_cap.predict_anomalies("cpu_usage", 95.0, historical)  # noqa: F841  # Variable for test verification
    assert isinstance(result, ai.AnomalyPrediction)
    assert isinstance(result.is_anomalous, bool)
    assert result.confidence >= 0.0
    assert result.confidence <= 1.0
    assert isinstance(result.explanation, str)


async def test_enhanced_ai_adaptive_learn(ai_cap):
    ai_cap.prediction_models["rf_test"] = object()
    samples = [({"feature": 1}, 1.0), ({"feature": 2}, 2.0)]
    update = await ai_cap.adaptive_learn("rf_test", samples, ai.LearningMode.ONLINE)
    assert isinstance(update, ai.LearningUpdate)
    assert update.model_id == "rf_test"
    assert update.samples_added == 2


async def test_enhanced_ai_parse_natural_language(ai_cap):
    result = await ai_cap.parse_natural_language("analyze cpu usage above 90 in the last hour")  # noqa: F841  # Variable for test verification
    assert isinstance(result, ai.NLParseResult)
    assert isinstance(result.intent, str)
    assert isinstance(result.entities, dict)
    assert isinstance(result.confidence, float)
    assert isinstance(result.suggested_actions, list)


async def test_enhanced_ai_explain_decision(ai_cap):
    result = await ai_cap.explain_decision("scale_up", {"metrics": {}, "confidence": 0.8})  # noqa: F841  # Variable for test verification
    assert isinstance(result, ai.DecisionExplanation)
    assert isinstance(result.reasoning, list)
    assert isinstance(result.alternative_options, list)
    assert isinstance(result.data_sources, list)
    assert result.decision == "scale_up"


async def test_enhanced_ai_knowledge_and_stats(ai_cap):
    await ai_cap.accumulate_knowledge(
        {
            "symptoms": ["cpu high"],
            "root_causes": ["overload"],
            "resolution": "scale out",
            "id": "inc-1",
        }
    )
    pattern = ai_cap._generate_knowledge_pattern(["cpu high"], ["overload"])
    insights = await ai_cap.get_knowledge_insights(pattern)
    assert isinstance(insights, dict)
    assert "incident_count" in insights
    assert insights["incident_count"] >= 1

    stats = await ai_cap.get_ai_statistics()
    assert isinstance(stats, dict)
    assert {"prediction_models", "anomaly_detectors", "knowledge_patterns"} <= set(stats.keys())


# ---------------------------------------------------------------------------
# core.enhanced_root_cause_analyzer
# ---------------------------------------------------------------------------


@pytest.fixture
def rca_analyzer(monkeypatch):
    """Provide an EnhancedRootCauseAnalyzer with ML disabled for speed."""
    monkeypatch.setattr(rca, "ML_AVAILABLE", False)
    return rca.EnhancedRootCauseAnalyzer()


async def test_enhanced_rca_build_graph_and_discover(rca_analyzer):
    rca_analyzer.edges = {
        "svc1": [rca.TopologyEdge("svc1", "db1", "reads")],
    }
    rca_analyzer.nodes = {
        "svc1": rca.TopologyNode("svc1", "service", "svc1"),
        "db1": rca.TopologyNode("db1", "database", "db1"),
    }

    await rca_analyzer._build_causal_graph()
    assert "svc1" in rca_analyzer.causal_graph
    assert "db1" in rca_analyzer.causal_graph["svc1"]

    topology = await rca_analyzer.discover_topology()
    assert isinstance(topology, dict)
    assert {"nodes_count", "edges_count", "discovery_time"} <= set(topology.keys())


async def test_enhanced_rca_analyze(rca_analyzer):
    rca_analyzer.edges = {
        "svc1": [rca.TopologyEdge("svc1", "db1", "reads")],
    }
    rca_analyzer.nodes = {
        "svc1": rca.TopologyNode("svc1", "service", "svc1"),
        "db1": rca.TopologyNode("db1", "database", "db1"),
    }
    await rca_analyzer._build_causal_graph()

    hypotheses = await rca_analyzer.analyze_root_causes({"svc1"})
    assert isinstance(hypotheses, list)
    assert len(hypotheses) >= 1
    assert isinstance(hypotheses[0], rca.RootCauseHypothesis)
    assert isinstance(hypotheses[0].node_id, str)
    assert 0.0 <= hypotheses[0].confidence <= 1.0


async def test_enhanced_rca_predict(rca_analyzer, monkeypatch):
    monkeypatch.setattr(
        rca_analyzer,
        "_analyze_state_trends",
        AsyncMock(return_value=[{"trend": "up"}]),
    )
    monkeypatch.setattr(
        rca_analyzer,
        "_predict_potential_failures",
        AsyncMock(
            return_value=[
                {
                    "node": "db1",
                    "probability": 0.9,
                    "impact": 1.0,
                    "trend": "up",
                    "predicted_impact": {},
                }
            ]
        ),
    )

    hypotheses = await rca_analyzer.predict_root_causes({"cpu": 95.0})
    assert isinstance(hypotheses, list)
    assert len(hypotheses) >= 1
    assert isinstance(hypotheses[0], rca.RootCauseHypothesis)
    assert hypotheses[0].node_id == "db1"


async def test_enhanced_rca_verify(rca_analyzer):
    rca_analyzer.nodes["db1"] = rca.TopologyNode("db1", "database", "db1", health_status="critical")
    hypothesis = rca.RootCauseHypothesis(
        node_id="db1",
        confidence=0.8,
        explanation="test",
        evidence=[],
        impact_score=0.5,
        severity=rca.RCASeverity.HIGH,
    )
    verified = await rca_analyzer.verify_root_cause(hypothesis)
    assert isinstance(verified, bool)
    assert hypothesis.verification_status in ("verified", "rejected")


async def test_enhanced_rca_record_and_stats(rca_analyzer):
    incident = rca.HistoricalIncident(
        id="i1",
        timestamp=datetime.now(),
        symptoms=["cpu high"],
        root_causes=["overload"],
        resolution="scale out",
        similarity_hash="hash1",
    )
    await rca_analyzer.record_incident(incident)
    stats = await rca_analyzer.get_analysis_statistics()
    assert isinstance(stats, dict)
    assert stats["historical_incidents"] >= 1
    assert "total_nodes" in stats


# ---------------------------------------------------------------------------
# core.integration_manager
# ---------------------------------------------------------------------------


@pytest.fixture
def integration_manager(monkeypatch):
    """Provide an IntegrationManager with HTTP/boto3 disabled."""
    monkeypatch.setattr(im, "HTTP_AVAILABLE", False)
    monkeypatch.setattr(im, "BOTO3_AVAILABLE", False)
    return im.IntegrationManager({})


async def test_integration_manager_register_and_summary(integration_manager):
    integration = await integration_manager.register_integration(
        im.IntegrationType.CICD,
        "Jenkins",
        {"url": "http://jenkins", "username": "admin", "api_token": "token"},
    )
    assert isinstance(integration, im.IntegrationConfig)
    assert integration.status == im.IntegrationStatus.ACTIVE
    assert integration.integration_id in integration_manager.integrations

    summary = integration_manager.get_integration_summary()
    assert isinstance(summary, dict)
    assert summary["total_integrations"] >= 1
    assert summary["active_integrations"] >= 1
    assert "integrations_by_type" in summary
    assert "webhooks_registered" in summary


async def test_integration_manager_health_and_invoke(integration_manager):
    integration = await integration_manager.register_integration(
        im.IntegrationType.CICD,
        "Jenkins",
        {"url": "http://jenkins", "username": "admin", "api_token": "token"},
    )

    health = await integration_manager.test_integration(integration.integration_id)
    assert isinstance(health, dict)
    assert health["success"] is True

    result = await integration_manager.trigger_jenkins_job(integration.integration_id, "build", {})  # noqa: F841  # Variable for test verification
    assert isinstance(result, dict)
    assert result.get("success") is True
    assert "build" in result.get("message", "")


async def test_integration_manager_webhooks(integration_manager):
    webhook_id = await integration_manager.register_webhook(
        "slack", "alert", "http://hooks.example.com/slack"
    )
    assert isinstance(webhook_id, str)
    assert webhook_id in integration_manager.webhooks

    result = await integration_manager.handle_webhook(webhook_id, {"text": "cpu high"})  # noqa: F841  # Variable for test verification
    assert isinstance(result, dict)
    assert result.get("success") is True
    assert "event_id" in result


async def test_integration_manager_notification(integration_manager):
    integration_manager.notification_channels["email"] = {
        "name": "email",
        "type": "email",
        "config": {},
        "enabled": True,
    }
    message = await integration_manager.send_notification(
        "email", "ops@example.com", "test subject", "test body"
    )
    assert isinstance(message, im.NotificationMessage)
    assert message.message_id.startswith("msg_")
    assert message.channel == "email"
