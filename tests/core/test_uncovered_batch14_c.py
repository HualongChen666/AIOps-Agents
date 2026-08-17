# -*- coding: utf-8 -*-
"""Functional coverage tests for core batch 14-c modules."""

import asyncio  # noqa: F401  # Imported for test setup
import sys  # noqa: F401  # Imported for test setup
import time  # noqa: F401  # Imported for test setup
from unittest.mock import AsyncMock, MagicMock, patch

import pytest  # noqa: F401  # Imported for test setup

import core.ai.rag.fusion as fusion
import core.ai.rag.retriever as retriever
import core.chaos_engineering as ce
import core.hitl.approval as approval
import core.logging.analysis.log_alerting as alerting
import core.memory_monitor as cm
from core.ai.rag.vectorizer import DocumentChunk
from core.logging.analysis.log_analyzer import LogAnalyzer

pytestmark = [pytest.mark.core]


# ---------------------------------------------------------------------------
# core.hitl.approval
# ---------------------------------------------------------------------------
@pytest.fixture
def fresh_workflow():
    """Return a fresh approval workflow instance."""
    return approval.ApprovalWorkflow()


def test_approval_enums_and_dataclasses():
    assert approval.ApprovalStatus.PENDING.value == "pending"
    assert approval.ApprovalStatus.APPROVED.value == "approved"

    step = approval.ApprovalStep(
        step_id="s1",
        name="step one",
        approver="alice",
    )
    d = step.to_dict()
    assert d["step_id"] == "s1"
    assert d["status"] == "pending"

    request = approval.ApprovalRequest(
        request_id="r1",
        workflow_id="wf1",
        title="test",
        description="desc",
        steps=[step],
    )
    rd = request.to_dict()
    assert rd["request_id"] == "r1"
    assert len(rd["steps"]) == 1


def test_create_request_and_status(fresh_workflow):
    wf = fresh_workflow
    step = approval.ApprovalStep("s1", "step1", "alice")
    req = wf.create_request(
        "wf1",
        "test title",
        "test desc",
        [step],
        context={"foo": "bar"},
        tenant_id="t1",
    )
    assert req.request_id.startswith("wf1-")
    assert req.tenant_id == "t1"
    assert req in wf.active_requests.values()

    status = wf.get_request_status(req.request_id)
    assert status is not None
    assert status["title"] == "test title"
    assert status["steps"][0]["status"] == "pending"

    assert wf.get_request_status(req.request_id, tenant_id="wrong") is None
    assert wf.get_request_status("missing") is None


def test_approve_step_and_advance(fresh_workflow):
    wf = fresh_workflow
    s1 = approval.ApprovalStep("s1", "step1", "alice")
    s2 = approval.ApprovalStep("s2", "step2", "bob")
    req = wf.create_request("wf1", "t", "d", [s1, s2])

    # wrong request
    assert wf.approve_step("missing", "s1", "alice") is False
    # wrong tenant
    assert wf.approve_step(req.request_id, "s1", "alice", tenant_id="other") is False
    # wrong step
    assert wf.approve_step(req.request_id, "nope", "alice") is False
    # wrong approver
    assert wf.approve_step(req.request_id, "s1", "bob") is False

    assert wf.approve_step(req.request_id, "s1", "alice", comment="ok") is True
    assert s1.status == approval.ApprovalStatus.APPROVED
    assert s1.approved_at is not None
    assert req.current_step == 1

    assert wf.approve_step(req.request_id, "s2", "bob") is True
    assert req.status == approval.ApprovalStatus.APPROVED
    assert req in wf.completed_requests.values()
    assert req.request_id not in wf.active_requests


def test_reject_step(fresh_workflow):
    wf = fresh_workflow
    s1 = approval.ApprovalStep("s1", "step1", "alice")
    s2 = approval.ApprovalStep("s2", "step2", "bob")
    req = wf.create_request("wf1", "t", "d", [s1, s2])

    assert wf.reject_step(req.request_id, "s1", "alice", comment="no") is True
    assert s1.status == approval.ApprovalStatus.REJECTED
    assert req.status == approval.ApprovalStatus.REJECTED
    assert req in wf.completed_requests.values()


def test_cancel_request(fresh_workflow):
    wf = fresh_workflow
    s1 = approval.ApprovalStep("s1", "step1", "alice")
    req = wf.create_request("wf1", "t", "d", [s1])

    assert wf.cancel_request("missing") is False
    assert wf.cancel_request(req.request_id, tenant_id="other") is False

    assert wf.cancel_request(req.request_id, reason="manual") is True
    assert req.status == approval.ApprovalStatus.REJECTED
    assert s1.status == approval.ApprovalStatus.REJECTED


def test_visualization_and_progress(fresh_workflow):
    wf = fresh_workflow
    s1 = approval.ApprovalStep("s1", "step1", "alice")
    s2 = approval.ApprovalStep("s2", "step2", "bob")
    req = wf.create_request("wf1", "t", "d", [s1, s2])

    # empty steps
    empty = wf.create_request("wf-empty", "t", "d", [])
    assert wf._calculate_progress(empty) == 0.0

    vis = wf.get_visualization_data(req.request_id)
    assert vis["progress"] == 0.0
    assert vis["steps"][0]["is_current"] is True

    wf.approve_step(req.request_id, "s1", "alice")
    vis = wf.get_visualization_data(req.request_id)
    assert vis["progress"] == 0.5
    assert vis["steps"][0]["is_current"] is False
    assert vis["steps"][1]["is_current"] is True

    assert wf.get_visualization_data("missing") is None


def test_timeout_and_validity(fresh_workflow, monkeypatch):
    wf = fresh_workflow
    s1 = approval.ApprovalStep("s1", "step1", "alice", timeout_minutes=1)
    req = wf.create_request("wf1", "t", "d", [s1])

    # not timed out
    assert wf.is_timed_out(req.request_id) is False

    # fake created_at in the past
    req.created_at = __import__("datetime").datetime.now() - __import__("datetime").timedelta(
        minutes=2
    )
    assert wf.is_timed_out(req.request_id) is True

    # completed / invalid request
    assert wf.is_timed_out("missing") is False
    req.current_step = 5
    assert wf.is_timed_out(req.request_id) is False

    # validity
    wf2 = approval.ApprovalWorkflow()
    s1b = approval.ApprovalStep("s1", "step1", "alice")
    req2 = wf2.create_request("wf2", "t", "d", [s1b])
    assert wf2.is_approval_valid(req2.request_id) is False  # not approved
    wf2.approve_step(req2.request_id, "s1", "alice")
    assert wf2.is_approval_valid(req2.request_id) is True
    # expire
    s1b.expires_at = __import__("datetime").datetime.now() - __import__("datetime").timedelta(
        seconds=1
    )
    assert wf2.is_approval_valid(req2.request_id) is False


def test_revalidate_before_execution(fresh_workflow):
    wf = fresh_workflow
    s1 = approval.ApprovalStep("s1", "step1", "alice")
    req = wf.create_request("wf1", "t", "d", [s1])

    ok, reason = wf.revalidate_before_execution("missing")
    assert ok is False
    assert "not found" in reason

    ok, _ = wf.revalidate_before_execution(req.request_id)
    assert ok is False
    assert "not approved" in _

    wf.approve_step(req.request_id, "s1", "alice")
    ok, _ = wf.revalidate_before_execution(req.request_id)
    assert ok is True

    # context interruption
    req.context["agent_interrupted"] = True
    ok, reason = wf.revalidate_before_execution(req.request_id)
    assert ok is False
    assert "interrupted" in reason
    del req.context["agent_interrupted"]

    # failing precondition
    req.precondition_checker = lambda r: False
    ok, reason = wf.revalidate_before_execution(req.request_id)
    assert ok is False
    assert "precondition check failed" in reason

    # raising precondition
    req.precondition_checker = lambda r: 1 / 0
    ok, reason = wf.revalidate_before_execution(req.request_id)
    assert ok is False
    assert "precondition checker error" in reason

    # async precondition
    async def async_ok(r):
        return True

    req.precondition_checker = async_ok
    ok, _ = wf.revalidate_before_execution(req.request_id)
    assert ok is True


def test_interrupt_associated_agent(fresh_workflow, monkeypatch):
    wf = fresh_workflow
    s1 = approval.ApprovalStep("s1", "step1", "alice")
    req = wf.create_request("wf1", "t", "d", [s1])

    # no subagent available
    assert wf._interrupt_associated_agent(req) is False

    # no agent_id in context
    monkeypatch.setattr(approval, "SUBAGENT_AVAILABLE", True)
    monkeypatch.setattr(approval, "SubAgentDispatcher", MagicMock())
    assert wf._interrupt_associated_agent(req) is False

    # agent id present and terminate returns True
    fake_dispatcher = MagicMock()
    fake_dispatcher.terminate.return_value = True
    fake_cls = MagicMock()
    fake_cls._instance = fake_dispatcher
    monkeypatch.setattr(approval, "SubAgentDispatcher", fake_cls)
    req.context["agent_id"] = "agent-123"
    assert wf._interrupt_associated_agent(req) is True
    fake_dispatcher.terminate.assert_called_once_with("agent-123")

    # terminate exception
    fake_dispatcher.terminate.side_effect = RuntimeError("boom")
    assert wf._interrupt_associated_agent(req) is False


# ---------------------------------------------------------------------------
# core.chaos_engineering
# ---------------------------------------------------------------------------
@pytest.fixture
def chaos(monkeypatch):
    """Return a fresh ChaosEngine with sleeps removed."""
    engine = ce.ChaosEngine()
    # patch sleep to avoid real delays
    monkeypatch.setattr(ce.asyncio, "sleep", AsyncMock())
    # patch measurement / health helpers
    monkeypatch.setattr(engine, "_measure_response_time", AsyncMock(return_value=123.0))
    monkeypatch.setattr(engine, "_check_system_health", AsyncMock(return_value=True))
    monkeypatch.setattr(engine, "_check_network_connectivity", AsyncMock(return_value=True))
    monkeypatch.setattr(engine, "_verify_service_degradation", AsyncMock(return_value=True))
    monkeypatch.setattr(engine, "_test_service_recovery", AsyncMock(return_value=500.0))
    # patch memory usage to avoid psutil
    fake_mem = MagicMock()
    fake_mem.get_memory_usage.return_value = {"usage_mb": 123}
    monkeypatch.setattr(cm, "memory_monitor", fake_mem)
    return engine


def test_engine_enable_disable():
    assert ce.chaos_engine.is_enabled() is False
    ce.chaos_engine.enable()
    assert ce.chaos_engine.is_enabled() is True
    ce.chaos_engine.disable()
    assert ce.chaos_engine.is_enabled() is False


@pytest.mark.asyncio
async def test_run_experiment_disabled():
    engine = ce.ChaosEngine()
    result = await engine.run_experiment(ce.ChaosExperiment.LATENCY_INJECTION)  # noqa: F841  # Variable for test verification
    assert result.status == ce.ExperimentStatus.ABORTED
    assert result.success is False
    assert "disabled" in result.error_message


@pytest.mark.asyncio
async def test_run_experiment_concurrent_error(chaos):
    chaos.enable()
    chaos._current_experiment = ce.ExperimentResult(
        experiment=ce.ChaosExperiment.LATENCY_INJECTION,
        status=ce.ExperimentStatus.RUNNING,
        start_time=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
    )
    with pytest.raises(RuntimeError, match="already running"):
        await chaos.run_experiment(ce.ChaosExperiment.LATENCY_INJECTION)


@pytest.mark.asyncio
async def test_run_latency_injection(chaos, monkeypatch):
    chaos.enable()
    monkeypatch.setattr(ce._random, "randint", lambda a, b: 200)
    result = await chaos.run_experiment(ce.ChaosExperiment.LATENCY_INJECTION, {"delay_ms": 200})  # noqa: F841  # Variable for test verification
    assert result.status == ce.ExperimentStatus.COMPLETED
    assert result.success is True
    assert result.metrics["injected_latency_ms"] == 200


@pytest.mark.asyncio
async def test_run_fault_injection(chaos):
    chaos.enable()
    for fault in ["database_error", "cache_error", "api_error", "random"]:
        result = await chaos.run_experiment(  # noqa: F841  # Variable for test verification
            ce.ChaosExperiment.FAULT_INJECTION, {"fault_type": fault}
        )
        assert result.status == ce.ExperimentStatus.COMPLETED
        assert result.success is True
        assert result.metrics["fault_type"] == fault


@pytest.mark.asyncio
async def test_run_resource_limitation(chaos):
    chaos.enable()
    result = await chaos.run_experiment(  # noqa: F841  # Variable for test verification
        ce.ChaosExperiment.RESOURCE_LIMITATION,
        {"resource_type": "cpu", "limit": 0.5},
    )
    assert result.status == ce.ExperimentStatus.COMPLETED
    assert result.success is True
    assert result.metrics["resource_type"] == "cpu"


@pytest.mark.asyncio
async def test_run_network_partition(chaos):
    chaos.enable()
    result = await chaos.run_experiment(  # noqa: F841  # Variable for test verification
        ce.ChaosExperiment.NETWORK_PARTITION, {"partition_type": "full"}
    )
    assert result.status == ce.ExperimentStatus.COMPLETED
    assert result.success is True
    assert result.metrics["partition_type"] == "full"


@pytest.mark.asyncio
async def test_run_service_failure(chaos):
    chaos.enable()
    result = await chaos.run_experiment(  # noqa: F841  # Variable for test verification
        ce.ChaosExperiment.SERVICE_FAILURE, {"service_name": "payment"}
    )
    assert result.status == ce.ExperimentStatus.COMPLETED
    assert result.success is True
    assert result.metrics["service_name"] == "payment"


@pytest.mark.asyncio
async def test_run_unknown_experiment(chaos):
    chaos.enable()
    result = await chaos.run_experiment("bad")  # noqa: F841  # Variable for test verification
    assert result.status == ce.ExperimentStatus.FAILED
    assert result.success is False
    assert "Unknown experiment" in result.error_message


@pytest.mark.asyncio
async def test_run_experiment_failure(chaos, monkeypatch):
    chaos.enable()
    monkeypatch.setattr(chaos, "_inject_latency", AsyncMock(side_effect=RuntimeError("boom")))
    result = await chaos.run_experiment(ce.ChaosExperiment.LATENCY_INJECTION)  # noqa: F841  # Variable for test verification
    assert result.status == ce.ExperimentStatus.FAILED
    assert result.success is False
    assert "boom" in result.error_message


@pytest.mark.asyncio
async def test_experiment_history_and_stats(chaos, monkeypatch):
    chaos.enable()
    await chaos.run_experiment(ce.ChaosExperiment.LATENCY_INJECTION)
    await chaos.run_experiment(ce.ChaosExperiment.FAULT_INJECTION, {"fault_type": "api_error"})
    await chaos.run_experiment(ce.ChaosExperiment.SERVICE_FAILURE, {"service_name": "x"})

    history = chaos.get_experiment_history(limit=2)
    assert len(history) == 2

    stats = chaos.get_experiment_stats()
    assert stats["total_experiments"] == 3
    assert stats["successful_experiments"] == 3
    assert stats["enabled"] is True
    assert "latency_injection" in stats["experiment_stats"]

    # stats with empty history
    fresh = ce.ChaosEngine()
    assert fresh.get_experiment_stats() == {"total_experiments": 0}


@pytest.mark.asyncio
async def test_setup_chaos_engineering():
    result = await ce.setup_chaos_engineering()  # noqa: F841  # Variable for test verification
    assert result["status"] == "success"
    assert result["enabled"] is False
    assert "latency_injection" in result["experiments"]


# ---------------------------------------------------------------------------
# core.ai.rag.fusion
# ---------------------------------------------------------------------------
def _chunk(cid, did, content, score=0.5, metadata=None):
    return retriever.RetrievalResult(
        chunk=DocumentChunk(
            id=cid,
            document_id=did,
            content=content,
            chunk_index=0,
            metadata=metadata or {},
        ),
        score=score,
        metadata={"s": "x"},
    )


def test_concatenation_fusion():
    r1 = _chunk("c1", "d1", "hello")
    r2 = _chunk("c2", "d1", "world")
    fused = fusion.ConcatenationFusion().fuse("q", [r1, r2], max_context_length=100)
    assert "hello" in fused and "world" in fused

    # over limit
    big = _chunk("c3", "d1", "x" * 200)
    fused = fusion.ConcatenationFusion().fuse("q", [big, r1], max_context_length=50)
    assert fused == ""


def test_relevance_fusion():
    r1 = _chunk("c1", "d1", "first", score=0.1)
    r2 = _chunk("c2", "d1", "second", score=0.9)
    fused = fusion.RelevanceFusion().fuse("q", [r1, r2], max_context_length=1000)
    assert fused.startswith("[Score: 0.90]")
    assert "second" in fused


@pytest.mark.asyncio
async def test_rag_pipeline_query():
    r1 = _chunk("c1", "d1", "hello", score=0.9)
    r2 = _chunk("c2", "d1", "world", score=0.5)

    fake_retriever = AsyncMock()
    fake_retriever.retrieve.return_value = [r1, r2]

    fake_reranker = AsyncMock()
    fake_reranker.rerank.return_value = [r2, r1]

    pipe = fusion.RAGPipeline(
        retriever=fake_retriever,
        reranker=fake_reranker,
        fusion_strategy=fusion.RelevanceFusion(),
    )
    result = await pipe.query("hello", top_k=2, rerank=True, max_context_length=500)  # noqa: F841  # Variable for test verification
    assert result["query"] == "hello"
    assert "hello" in result["context"]
    assert len(result["sources"]) == 2
    fake_reranker.rerank.assert_awaited_once()

    # without reranker
    pipe2 = fusion.RAGPipeline(retriever=fake_retriever, reranker=None)
    result2 = await pipe2.query("q", top_k=2, rerank=True)
    assert fake_retriever.retrieve.call_count == 2


@pytest.mark.asyncio
async def test_rag_pipeline_retrieve_and_generate():
    r1 = _chunk("c1", "d1", "content")
    fake_retriever = AsyncMock()
    fake_retriever.retrieve.return_value = [r1]
    pipe = fusion.RAGPipeline(retriever=fake_retriever)
    context = await pipe.retrieve_and_generate("q", top_k=1)
    assert "content" in context


# ---------------------------------------------------------------------------
# core.logging.analysis.log_alerting
# ---------------------------------------------------------------------------
class FakeStats:
    total_logs = 100
    error_rate = 0.2
    avg_response_time = 120.0
    unique_users = 5


class FakeTrends:
    time_series = [(__import__("datetime").datetime.now(), 10)]
    growth_rate = 0.1
    peak_value = 10


class FakePattern:
    def __init__(self, pattern, count, severity="error"):
        self.pattern = pattern
        self.count = count
        self.examples = ["ex1", "ex2"]
        self.severity = severity


def test_threshold_alert_operators():
    assert alerting.ThresholdAlert("a", "m", 10, ">").evaluate(11) is True
    assert alerting.ThresholdAlert("a", "m", 10, ">").evaluate(9) is False
    assert alerting.ThresholdAlert("a", "m", 10, "<").evaluate(9) is True
    assert alerting.ThresholdAlert("a", "m", 10, ">=").evaluate(10) is True
    assert alerting.ThresholdAlert("a", "m", 10, "<=").evaluate(10) is True
    assert alerting.ThresholdAlert("a", "m", 10, "==").evaluate(10) is True
    assert alerting.ThresholdAlert("a", "m", 10, "bad").evaluate(10) is False


def test_log_alert_to_dict():
    alert = alerting.LogAlert(
        alert_id="a1",
        alert_type="test",
        severity=alerting.AlertSeverity.WARNING,
        message="msg",
        timestamp=__import__("datetime").datetime.now(),
        metadata={"x": 1},
        triggered_by="t",
    )
    d = alert.to_dict()
    assert d["severity"] == "warning"
    assert d["metadata"] == {"x": 1}


def test_anomaly_detector_error_rate():
    analyzer = MagicMock()
    analyzer.calculate_statistics.return_value = FakeStats()
    detector = alerting.AnomalyDetector(analyzer)
    # not enough baseline
    for _ in range(5):
        detector.detect_error_rate_anomaly()
    for _ in range(10):
        alert = detector.detect_error_rate_anomaly()
    assert alert is None

    # raise error rate far above baseline
    for _ in range(10):
        analyzer.calculate_statistics.return_value = type(
            "S", (), {"total_logs": 100, "error_rate": 0.95}
        )()
        alert = detector.detect_error_rate_anomaly(threshold=0.1)
    assert alert is not None
    assert alert.alert_type == "error_rate_anomaly"

    # empty stats
    analyzer.calculate_statistics.return_value = type(
        "S", (), {"total_logs": 0, "error_rate": 0.0}
    )()
    assert detector.detect_error_rate_anomaly() is None


def test_anomaly_detector_volume_and_pattern():
    analyzer = MagicMock()
    analyzer.calculate_trends.return_value = FakeTrends()
    analyzer.detect_patterns.return_value = [
        FakePattern("p1", 5, "error"),
        FakePattern("p2", 3, "warning"),
    ]
    detector = alerting.AnomalyDetector(analyzer)

    # not enough baseline for volume
    for _ in range(5):
        assert detector.detect_volume_anomaly() is None

    # enough baseline, large volume
    for i in range(15):
        analyzer.calculate_trends.return_value = type(
            "T", (), {"time_series": [(__import__("datetime").datetime.now(), 100 + i * 50)]}
        )()
        alert = detector.detect_volume_anomaly(threshold=0.1)
    assert alert is not None
    assert alert.alert_type == "volume_anomaly"

    # empty time series
    analyzer.calculate_trends.return_value = type("T", (), {"time_series": []})()
    assert detector.detect_volume_anomaly() is None

    # pattern anomaly
    alert = detector.detect_pattern_anomaly()
    assert alert is not None
    assert "p1" in alert.message
    assert alert.severity == alerting.AlertSeverity.ERROR

    # no error patterns
    analyzer.detect_patterns.return_value = [FakePattern("p3", 2, "warning")]
    assert detector.detect_pattern_anomaly() is None


class DummyHandler(alerting.AlertHandler):
    def __init__(self):
        self.alerts = []

    def handle_alert(self, alert):
        self.alerts.append(alert)


def test_alert_manager_thresholds():
    stats = MagicMock()
    stats.error_rate = 0.5
    stats.total_logs = 100
    stats.avg_response_time = 50.0
    stats.unique_users = 3
    trends = MagicMock()
    trends.growth_rate = 0.2
    trends.peak_value = 100

    fake_analyzer = MagicMock()
    fake_analyzer.calculate_statistics.return_value = stats
    fake_analyzer.calculate_trends.return_value = trends

    manager = alerting.LogAlertManager(log_analyzer=fake_analyzer)
    alert = alerting.ThresholdAlert("high_errors", "error_rate", 0.1)
    manager.add_threshold_alert(alert)
    assert "high_errors" in manager.threshold_alerts
    manager.remove_threshold_alert("high_errors")
    assert "high_errors" not in manager.threshold_alerts

    # metric mapping
    for metric in ["error_rate", "total_logs", "avg_response_time", "unique_users"]:
        assert manager._get_metric_value(metric, stats, trends) is not None
    for metric in ["growth_rate", "peak_value"]:
        assert manager._get_metric_value(metric, stats, trends) is not None
    assert manager._get_metric_value("unknown", stats, trends) is None

    # triggered threshold
    manager.threshold_alerts["t1"] = alerting.ThresholdAlert("t1", "error_rate", 0.1)
    triggered = manager.check_thresholds()
    assert len(triggered) == 1
    assert triggered[0].alert_type == "threshold"

    # disabled alert
    manager.threshold_alerts["t2"] = alerting.ThresholdAlert("t2", "error_rate", 0.1, enabled=False)
    triggered = manager.check_thresholds()
    assert len(triggered) == 1  # t1 still active


def test_alert_manager_anomalies_and_run_check(monkeypatch):
    analyzer = MagicMock()
    stats = MagicMock()
    stats.total_logs = 10
    stats.error_rate = 0.5
    trends = MagicMock()
    trends.time_series = [(__import__("datetime").datetime.now(), 10)]
    analyzer.calculate_statistics.return_value = stats
    analyzer.calculate_trends.return_value = trends
    analyzer.detect_patterns.return_value = [FakePattern("p", 5, "error")]

    manager = alerting.LogAlertManager(log_analyzer=analyzer)

    handler = DummyHandler()
    manager.add_alert_handler(handler)
    assert len(manager.alert_handlers) == 1

    # clear history and run check
    manager.clear_alert_history()
    manager.run_check()
    assert len(manager.get_alert_history()) > 0
    assert len(handler.alerts) > 0

    manager.remove_alert_handler(handler)
    assert len(manager.alert_handlers) == 0

    # handler error is logged
    bad_handler = DummyHandler()
    bad_handler.handle_alert = MagicMock(side_effect=RuntimeError("boom"))
    manager.add_alert_handler(bad_handler)
    monkeypatch.setattr(alerting.logger, "error", MagicMock())
    manager.trigger_alert(
        alerting.LogAlert(
            "a", "t", alerting.AlertSeverity.INFO, "m", __import__("datetime").datetime.now()
        )
    )
    alerting.logger.error.assert_called_once()


def test_alert_manager_monitoring(monkeypatch):
    manager = alerting.LogAlertManager()
    monkeypatch.setattr(manager, "run_check", MagicMock())
    monkeypatch.setattr(manager, "_check_interval", 0.001)
    monkeypatch.setattr(alerting.time, "sleep", MagicMock())

    manager.start_monitoring()
    assert manager._running is True
    # second start warns
    monkeypatch.setattr(alerting.logger, "warning", MagicMock())
    manager.start_monitoring()
    alerting.logger.warning.assert_called_once()

    manager.stop_monitoring()
    assert manager._running is False


def test_get_alert_manager(monkeypatch):
    monkeypatch.setattr(alerting, "_global_alert_manager", None)
    manager = alerting.get_alert_manager()
    assert isinstance(manager, alerting.LogAlertManager)
    # reuse
    monkeypatch.setattr(alerting, "_global_alert_manager", manager)
    assert alerting.get_alert_manager() is manager


# ---------------------------------------------------------------------------
# core.ai.rag.retriever
# ---------------------------------------------------------------------------
def test_retrieval_strategy_abc():
    with pytest.raises(NotImplementedError):
        asyncio.run(retriever.RetrievalStrategy().retrieve("q"))


@pytest.mark.asyncio
async def test_hybrid_retrieval():
    chunks = [
        DocumentChunk("c1", "d1", "hello", 0, {}),
        DocumentChunk("c2", "d1", "world", 0, {}),
    ]
    s1 = MagicMock(spec=retriever.RetrievalStrategy)
    s1.retrieve = AsyncMock(
        return_value=[
            retriever.RetrievalResult(chunk=chunks[0], score=1.0, metadata={}),
        ]
    )
    s2 = MagicMock(spec=retriever.RetrievalStrategy)
    s2.retrieve = AsyncMock(
        return_value=[
            retriever.RetrievalResult(chunk=chunks[1], score=2.0, metadata={}),
        ]
    )

    hybrid = retriever.HybridRetrieval([s1, s2], weights=[0.5, 1.0])
    results = await hybrid.retrieve("q", top_k=1)
    assert len(results) == 1
    assert results[0].score == 2.0  # s2 weighted


def test_bm25_retrieval_no_rank_bm25():
    chunks = [DocumentChunk("c1", "d1", "hello world", 0, {})]
    bm25 = retriever.BM25Retrieval(chunks)
    # ensure index not built
    result = asyncio.run(bm25.retrieve("hello"))  # noqa: F841  # Variable for test verification
    assert result == []  # noqa: F841  # Variable for test verification


def test_bm25_retrieval_with_fake_rankbm25(monkeypatch):
    chunks = [
        DocumentChunk("c1", "d1", "hello world", 0, {"tag": "a"}),
        DocumentChunk("c2", "d1", "foo bar", 0, {"tag": "b"}),
    ]
    bm25 = retriever.BM25Retrieval(chunks)

    class FakeIndex:
        def get_scores(self, tokens):
            return [5.0, 1.0]

    fake_mod = MagicMock()
    fake_mod.BM25Okapi = lambda docs: FakeIndex()
    monkeypatch.setitem(sys.modules, "rank_bm25", fake_mod)

    result = asyncio.run(bm25.retrieve("hello", top_k=2))  # noqa: F841  # Variable for test verification
    assert len(result) == 2
    assert result[0].score == 5.0
    assert result[0].chunk.id == "c1"

    # with filters
    result = asyncio.run(bm25.retrieve("hello", filters={"tag": "b"}))  # noqa: F841  # Variable for test verification
    assert len(result) == 1
    assert result[0].chunk.id == "c2"

    # simulate get_scores exception
    class BadIndex:
        def get_scores(self, tokens):
            raise RuntimeError("boom")

    fake_mod.BM25Okapi = lambda docs: BadIndex()
    bm25._index = None
    result = asyncio.run(bm25.retrieve("hello"))  # noqa: F841  # Variable for test verification
    assert result == []  # noqa: F841  # Variable for test verification


@pytest.mark.asyncio
async def test_retriever_primary_and_fallback():
    chunk = DocumentChunk("c1", "d1", "content", 0, {})
    primary = MagicMock(spec=retriever.RetrievalStrategy)
    primary.retrieve = AsyncMock(
        return_value=[retriever.RetrievalResult(chunk=chunk, score=1.0, metadata={})]
    )
    fallback = MagicMock(spec=retriever.RetrievalStrategy)
    fallback.retrieve = AsyncMock(
        return_value=[retriever.RetrievalResult(chunk=chunk, score=0.5, metadata={})]
    )

    r = retriever.Retriever(primary, [fallback])
    results = await r.retrieve("q", top_k=1)
    assert len(results) == 1
    assert fallback.retrieve.call_count == 0  # primary succeeded

    primary.retrieve = AsyncMock(return_value=[])
    results = await r.retrieve("q")
    assert len(results) == 1
    assert fallback.retrieve.call_count == 1


@pytest.mark.asyncio
async def test_retriever_all_fail():
    primary = MagicMock(spec=retriever.RetrievalStrategy)
    primary.retrieve = AsyncMock(side_effect=RuntimeError("boom"))
    fallback = MagicMock(spec=retriever.RetrievalStrategy)
    fallback.retrieve = AsyncMock(return_value=[])

    r = retriever.Retriever(primary, [fallback])
    results = await r.retrieve("q")
    assert results == []
