# -*- coding: utf-8 -*-
"""Targeted functional coverage tests for batch 21a modules."""

import asyncio  # noqa: F401  # Imported for test setup
import json  # noqa: F401  # Imported for test setup
import time  # noqa: F401  # Imported for test setup
from dataclasses import dataclass
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pandas as pd
import pytest  # noqa: F401  # Imported for test setup

import core.ai_service as ai_service
import core.alert_intelligence as alert_intelligence
import core.message_queue as message_queue
import core.redis_cluster_manager as redis_cluster_manager
from core.ai.langgraph.workflow import (
    Workflow,
    WorkflowContext,
    WorkflowEdge,
    WorkflowNode,
    WorkflowState,
)
from core.message_queue import MessageQueue
from core.redis_cluster_manager import RedisClusterManager, _create_redis_client

pytestmark = [pytest.mark.core]


# -----------------------------------------------------------------------------
# core.message_queue
# -----------------------------------------------------------------------------
@pytest.fixture
def queue(tmp_path):
    return MessageQueue(persistence_file=tmp_path / "mq.json")


@pytest.mark.asyncio
async def test_message_queue_lifecycle(queue):
    assert queue.publish("alerts", {"id": "1"}) is True
    assert queue.publish_with_priority("jobs", {"name": "low"}, priority=0) is True
    assert queue.publish_with_priority("jobs", {"name": "high"}, priority=5) is True
    jobs = queue._queues["jobs"]
    assert jobs[0]["message"]["name"] == "high"

    assert queue.publish_with_retry("events", {"e": 1}, max_retries=1) is True
    assert queue.publish_batch("batch", [{"i": i} for i in range(3)]) == {"success": 3, "failed": 0}

    async def handler(msg):
        return msg["id"]

    assert await queue.consume("alerts", handler) == "1"
    assert queue.get_queue_stats("alerts")["queue_length"] == 0

    async def bad(msg):
        raise ValueError("boom")

    queue.publish("bad", {"x": 1})
    with pytest.raises(ValueError):
        await queue.consume("bad", bad)
    assert len(queue._dead_letter_queue) == 1
    assert queue.ack_message("any") is True

    queue.subscribe_with_filter("jobs", lambda m: True)
    assert queue.get_queue_stats("jobs")["consumers"] == 1
    queue.scale_consumers("jobs", 5)
    queue.join_cluster("c1")
    queue.enable_replication()
    assert queue.get_cluster_status()["queues"] >= 1


def test_message_queue_transactions_and_cleanup(queue):
    txn = queue.begin_transaction()
    assert txn.startswith("txn_")
    assert queue.commit_transaction(txn) is True
    assert queue.rollback_transaction(txn) is True
    assert queue.commit_transaction("missing") is False
    assert queue.rollback_transaction("missing") is False

    queue.publish("old", {"x": 1})
    queue.publish("old", {"x": 2})
    cleaned = queue.cleanup_old_messages("old", older_than_hours=0)
    assert cleaned["cleaned"] == 2
    assert queue.get_queue_stats("old")["queue_length"] == 0


def test_message_queue_persistence_and_backup(tmp_path):
    queue = MessageQueue(persistence_file=tmp_path / "mq.json")
    queue.enable_persistence()
    queue.publish("q", {"a": 1})
    backup = queue.create_backup("q")
    assert backup["backup_file"] is not None
    assert backup["size_mb"] >= 0

    assert queue.restore_backup(backup["backup_file"]) is True
    assert len(queue._queues.get("q", [])) == 1

    new_queue = MessageQueue(persistence_file=queue._persistence_file)
    assert "q" in new_queue._queues

    bad_dir = tmp_path / "bad"
    bad_dir.mkdir()
    bad_queue = MessageQueue(persistence_file=bad_dir)
    bad_queue.enable_persistence()  # persistence path is a directory; _save must swallow error


def test_message_queue_real_backend_fallback(monkeypatch, queue):
    monkeypatch.setenv("MESSAGE_QUEUE_BACKEND", "rabbitmq")
    monkeypatch.setenv("RABBITMQ_URL", "amqp://localhost")
    assert queue.publish("rabbit", {"x": 1}) is True
    assert queue.get_replication_status()["mode"] == "configured"

    monkeypatch.setenv("MESSAGE_QUEUE_BACKEND", "kafka")
    monkeypatch.setenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    assert queue.publish("kafka", {"x": 1}) is True

    monkeypatch.setenv("MESSAGE_QUEUE_BACKEND", "")
    assert queue.get_replication_status()["mode"] == "memory"


# -----------------------------------------------------------------------------
# core.ai.langgraph.workflow
# -----------------------------------------------------------------------------
class FakeNode(WorkflowNode):
    async def execute(self, context: WorkflowContext):
        context.set(self.name, f"result-{self.name}")
        return f"ok-{self.name}"


@pytest.fixture
def sample_workflow():
    wf = Workflow("test", "desc")
    wf.add_node(FakeNode("start"))
    wf.add_node(FakeNode("process"))
    wf.add_node(FakeNode("end"))
    wf.add_edge("start", "process")
    wf.add_edge(
        "process",
        "end",
        condition=lambda ctx: ctx.get("process") is not None,
    )
    wf.set_start_node("start")
    wf.add_end_node("end")
    return wf


@pytest.mark.asyncio
async def test_workflow_execute(sample_workflow):
    result = await sample_workflow.execute({"input": 1})  # noqa: F841  # Variable for test verification
    assert result["status"] == "completed"
    assert sample_workflow.context.get("process") == "result-process"
    assert len(result["history"]) == 3
    assert sample_workflow.state == WorkflowState.COMPLETED


def test_workflow_validation_and_repr(sample_workflow):
    assert sample_workflow.validate() is True
    d = sample_workflow.to_dict()
    assert d["name"] == "test"
    assert d["start_node"] == "start"
    assert d["end_nodes"] == ["end"]
    m = sample_workflow.to_mermaid()
    assert "graph TD" in m
    assert "start" in m
    assert "end" in m


def test_workflow_validation_errors():
    wf = Workflow("bad")
    assert wf.validate() is False

    wf.add_node(FakeNode("a"))
    wf.set_start_node("a")
    wf.add_edge("a", "missing")
    assert wf.validate() is False

    with pytest.raises(ValueError):
        wf.set_start_node("nope")
    with pytest.raises(ValueError):
        wf.add_end_node("nope")


@pytest.mark.asyncio
async def test_workflow_execute_failure():
    class FailNode(WorkflowNode):
        async def execute(self, ctx):
            raise RuntimeError("fail")

    wf = Workflow("f")
    wf.add_node(FailNode("start"))
    wf.set_start_node("start")
    result = await wf.execute()  # noqa: F841  # Variable for test verification
    assert result["status"] == "failed"
    assert "fail" in result["error"]


def test_workflow_context_and_edge():
    ctx = WorkflowContext(input_data={"a": 1})
    assert ctx.get("a") is None
    ctx.set("b", 2)
    assert ctx.get("b") == 2
    ctx.add_history("node1", "r1")
    assert len(ctx.history) == 1
    assert ctx.history[0]["node"] == "node1"

    edge = WorkflowEdge("a", "b", condition=lambda c: c.get("go") is True)
    assert edge.should_traverse(WorkflowContext()) is False
    ctx.set("go", True)
    assert edge.should_traverse(ctx) is True


# -----------------------------------------------------------------------------
# core.alert_intelligence
# -----------------------------------------------------------------------------
@pytest.fixture
def engine():
    return alert_intelligence.AlertIntelligenceEngine()


@pytest.mark.asyncio
async def test_alert_intelligence_analysis(engine, monkeypatch):
    monkeypatch.setattr(alert_intelligence, "ML_AVAILABLE", False)
    alerts = [
        {
            "level": "critical",
            "category": "performance",
            "title": "High CPU",
            "desc": "cpu high",
            "host": "h1",
            "metric": "cpu",
            "alert_type": "threshold",
        },
        {
            "level": "critical",
            "category": "performance",
            "title": "High CPU 2",
            "desc": "cpu high",
            "host": "h1",
            "metric": "cpu",
            "alert_type": "threshold",
        },
        {
            "level": "info",
            "category": "system",
            "title": "log",
            "desc": "info",
            "host": "h2",
            "metric": "log",
            "alert_type": "info",
        },
    ]
    result = await engine.analyze_and_aggregate_alerts(alerts)  # noqa: F841  # Variable for test verification
    assert result
    for r in result:
        if "aggregated_count" in r:
            assert r["aggregated_count"] >= 1

    stats = engine.get_alert_statistics()
    assert stats["total_patterns"] >= 1


def test_alert_intelligence_features_and_signature(engine):
    f = engine._extract_alert_features(
        [
            {
                "level": "critical",
                "category": "security",
                "title": "t",
                "desc": "d",
                "host": "h",
                "metric": "m",
            }
        ]
    )
    assert f.shape[0] == 1
    assert engine._encode_severity("critical") == 4
    assert engine._encode_severity("UNKNOWN") == 1
    assert engine._encode_category("security") == 4
    assert engine._encode_category("UNKNOWN") == 1
    sig = engine._create_alert_signature(
        {"level": "c", "category": "s", "alert_type": "t", "host": "h", "metric": "m"}
    )
    assert sig == "c|s|t|h|m"


@pytest.mark.asyncio
async def test_alert_intelligence_noise_and_patterns(engine):
    alert = {
        "level": "info",
        "category": "system",
        "title": "noise",
        "desc": "n",
        "host": "h",
        "metric": "m",
        "alert_type": "info",
    }
    engine._update_patterns([alert] * 12)
    sig = engine._create_alert_signature(alert)
    assert engine.patterns[sig].is_noise is True

    reduced = await engine._apply_noise_reduction([alert])
    assert len(reduced) == 0

    engine.patterns[sig].last_seen = datetime.now() - timedelta(seconds=600)
    reduced = await engine._apply_noise_reduction([alert])
    assert len(reduced) == 1


@pytest.mark.asyncio
async def test_alert_intelligence_routing_and_topology(engine):
    engine.add_routing_rule({"destination": "custom", "conditions": {"host": "h1"}})
    engine.add_suppression_rule({"condition": "x"})

    alerts = [
        {"level": "critical", "category": "security", "host": "h1"},
        {"level": "info", "category": "system", "host": "h2"},
        {"level": "warning", "category": "database", "host": "h3"},
    ]
    routed = await engine.route_alerts_intelligently(alerts)
    assert "custom" in routed
    assert any(dest in routed for dest in ("default", "infrastructure_team"))

    ctx = engine.build_topology_context(alerts)
    assert "nodes" in ctx
    assert "edges" in ctx
    assert "components" in ctx

    assert engine._matches_routing_rule({"host": "h1"}, {"conditions": {"host": "h1"}}) is True
    assert engine._matches_routing_rule({"host": "h2"}, {"conditions": {"host": "h1"}}) is False
    assert engine._determine_alert_route({"level": "critical"}, {}) == "immediate"
    assert engine._determine_alert_route({"category": "security"}, {}) == "security_team"
    assert engine._determine_alert_route({"category": "database"}, {}) == "infrastructure_team"


@pytest.mark.asyncio
async def test_alert_intelligence_cascade(engine):
    engine.topology_graph = {"h1": ["root"], "h2": ["root"], "root": []}
    aggregated = [
        {"host": "h1", "aggregated_alerts": [{"host": "h2"}]},
        {"host": "h2", "aggregated_alerts": []},
    ]
    result = await engine._detect_cascade_alerts(aggregated)  # noqa: F841  # Variable for test verification
    assert any("is_cascade" in r for r in result)
    for r in result:
        if "is_cascade" in r:
            assert r["cascade_root"] == "root"


def test_alert_intelligence_ancestors(engine):
    engine.topology_graph = {"a": ["b"], "b": ["c"], "c": ["d"], "d": []}
    ancestors = engine._get_all_ancestors("a")
    assert {"b", "c", "d"} <= ancestors
    assert engine._count_dependents("d") == 1
    assert engine._count_dependents("x") == 0


@pytest.mark.asyncio
async def test_alert_intelligence_ml_clustering(engine):
    alerts = [
        {
            "level": "critical",
            "category": "perf",
            "title": "a",
            "desc": "d",
            "host": "h",
            "metric": "m",
        },
        {
            "level": "high",
            "category": "perf",
            "title": "b",
            "desc": "d",
            "host": "h",
            "metric": "m",
        },
    ]
    features = engine._extract_alert_features(alerts)

    saved_scaler = engine.scaler
    engine.scaler = None
    result = await engine._ml_based_clustering(alerts, features)  # noqa: F841  # Variable for test verification
    assert len(result) == len(alerts)

    engine.scaler = saved_scaler
    result = await engine._ml_based_clustering(alerts, features)  # noqa: F841  # Variable for test verification
    assert len(result) == len(alerts)


@pytest.mark.asyncio
async def test_alert_intelligence_trend_prediction(engine, monkeypatch):
    base = datetime.now() - timedelta(hours=10)  # noqa: F841  # Variable for test verification
    hist = [(base + timedelta(hours=i), float(i)) for i in range(5)]
    pred = await engine.predict_alert_trends("m", hist, horizon_hours=3)
    assert pred.model_used == "insufficient_data"

    hist = [(base + timedelta(hours=i), float(i % 3)) for i in range(12)]
    pred = await engine.predict_alert_trends("m", hist, horizon_hours=3)
    assert pred.model_used == "rule_based"
    assert len(pred.predicted_values) == 3

    monkeypatch.setattr(alert_intelligence, "PROPHET_AVAILABLE", True)
    fake_prophet = MagicMock()
    future_df = pd.DataFrame({"ds": pd.date_range("2024-01-01", periods=15, freq="h")})
    forecast_df = pd.DataFrame(
        {
            "ds": pd.date_range("2024-01-01", periods=15, freq="h"),
            "yhat": list(range(15)),
            "yhat_lower": [-1] * 15,
            "yhat_upper": [20] * 15,
        }
    )
    fake_prophet.return_value.make_future_dataframe.return_value = future_df
    fake_prophet.return_value.predict.return_value = forecast_df
    setattr(alert_intelligence, "Prophet", fake_prophet)
    try:
        pred = await engine.predict_alert_trends("m", hist, horizon_hours=3)
    finally:
        if hasattr(alert_intelligence, "Prophet"):
            delattr(alert_intelligence, "Prophet")
    assert pred.model_used == "prophet"
    assert len(pred.predicted_values) == 3


# -----------------------------------------------------------------------------
# core.ai_service
# -----------------------------------------------------------------------------
@pytest.fixture
def ai_service_mocks(monkeypatch):
    snapshot = {
        "top_processes": [{"pid": 1, "name": "a"}],
        "cpu": {"usage": 10},
        "memory": {"total": 100, "used": 50},
        "disk": [{"mount": "/", "used_percent": 5}],
        "network": {"bytes_sent": 1},
        "system": {"hostname": "h1"},
    }
    monkeypatch.setattr(ai_service, "get_cached_snapshot", MagicMock(return_value=snapshot))

    @dataclass
    class FakeMetric:
        metric_name: str
        value: float

    @dataclass
    class FakeMetricNoValue:
        metric_name: str

    fake_mgr = MagicMock()
    fake_mgr.get_service_metrics.return_value = [
        FakeMetric("cpu", 0.5),
        FakeMetricNoValue("mem"),
        SimpleNamespace(metric_name="disk", value=0.9),
    ]
    monkeypatch.setattr(
        "core.service_monitoring_manager.get_service_monitoring_manager",
        MagicMock(return_value=fake_mgr),
    )

    monkeypatch.setattr(
        "core.alert_engine.alert_history",
        [
            {
                "level": "critical",
                "title": "t1",
                "desc": "d1",
                "raw_time": "2024-01-01",
                "metric": "m1",
                "value": "12.5",
                "host": "h1",
                "source": "s1",
            },
            {
                "level": 5,
                "title": "t2",
                "desc": "d2",
                "raw_time": "2024-01-02",
                "metric": "m2",
                "value": 99,
                "host": "h2",
                "source": "s2",
            },
            "not_a_dict",
        ],
    )
    monkeypatch.setattr("core.repair_engine.repair_history", [{"id": 1}, {"id": 2}])

    fake_metrics_history = MagicMock()
    fake_metrics_history.get_stats.return_value = "not_dict"
    fake_metrics_history.to_dict.return_value = {"from_to_dict": True}
    monkeypatch.setattr("core.metrics_history.metrics_history", fake_metrics_history)

    monkeypatch.setattr(
        "core.topology_engine.get_full_link_topology",
        AsyncMock(
            return_value={
                "nodes": ["a", "svc", "b"],
                "edges": [
                    {"source": "a", "target": "svc"},
                    {"source": "svc", "target": "b"},
                ],
            }
        ),
    )

    fake_config = MagicMock()
    fake_config._audit_log = [
        {"timestamp": "2024-01-01T00:00:00", "change": "c1", "details": "d1"},
        "not_a_dict",
    ]
    fake_config._config_history = [
        {"timestamp": "2024-01-02T00:00:00", "applied_at": None},
        {"applied_at": "2024-01-03T00:00:00"},
        "not_a_dict",
    ]
    monkeypatch.setattr("core.config_manager.config_manager", fake_config)
    return fake_mgr


@pytest.mark.asyncio
async def test_ai_context_service_collect(ai_service_mocks):
    svc = ai_service.AIContextService()
    result = await svc.collect_rich_context(service_name="svc")  # noqa: F841  # Variable for test verification
    assert isinstance(result, dict)
    assert result["top_processes"]
    assert result["recent_alerts"]
    assert result["recent_repairs"]
    assert result["stats"] == {"from_to_dict": True}
    assert "cpu" in result["service_metrics"]
    assert result["infrastructure_metrics"]
    assert result["topology"]
    assert "svc" in result["upstream_callers"]
    assert result["downstream_dependencies"]
    assert result["change_events"]
    assert result["correlated_alerts"] == []


@pytest.mark.asyncio
async def test_ai_context_service_timeout(ai_service_mocks, monkeypatch):
    monkeypatch.setattr(ai_service, "_RICH_CONTEXT_PER_SOURCE_TIMEOUT_SEC", 0.001)

    async def slow_topology():
        await asyncio.sleep(0.05)
        return {}

    monkeypatch.setattr("core.topology_engine.get_full_link_topology", slow_topology)
    svc = ai_service.AIContextService()
    result = await svc.collect_rich_context(service_name="svc")  # noqa: F841  # Variable for test verification
    assert result["topology"] == {}


def test_ai_service_helpers():
    assert ai_service._safe_alert_value(None) is None
    assert ai_service._safe_alert_value(42) == 42
    assert ai_service._safe_alert_value(3.5) == 3.5
    assert ai_service._safe_alert_value(True) is True
    assert ai_service._safe_alert_value("123.45") == 123.45
    assert ai_service._safe_alert_value("hello") == "hello"
    assert ai_service._safe_alert_value({"x": 1}) == str({"x": 1})[:64]

    assert ai_service._safe_get_metric("bad", "cpu", "usage") == "N/A"
    assert ai_service._safe_get_metric({}, "cpu", "usage") == "N/A"
    assert ai_service._safe_get_metric({"cpu": "notdict"}, "cpu", "usage") == "N/A"
    assert ai_service._safe_get_metric({"cpu": {"usage": 9}}, "cpu", "usage") == 9
    assert ai_service._safe_get_metric({"cpu": {}}, "cpu", "usage", default="x") == "x"

    assert ai_service._extract_gather_result(asyncio.CancelledError(), "x", dict) is None
    assert ai_service._extract_gather_result(ValueError("boom"), "x", dict) is None
    assert ai_service._extract_gather_result(None, "x", dict) is None
    assert ai_service._extract_gather_result({"a": 1}, "x", dict) == {"a": 1}
    assert ai_service._extract_gather_result([1, 2], "x", list) == [1, 2]
    assert ai_service._extract_gather_result("wrong", "x", dict) is None


class BadSnapshot(dict):
    def get(self, key, default=None):
        raise RuntimeError("bad snapshot")


class BadIterable:
    def __iter__(self):
        raise RuntimeError("bad iterable")


class BadConfig:
    @property
    def _audit_log(self):
        raise RuntimeError("bad config")


@pytest.mark.asyncio
async def test_ai_context_service_errors(monkeypatch):
    monkeypatch.setattr(ai_service, "get_cached_snapshot", MagicMock(return_value=BadSnapshot()))
    monkeypatch.setattr("core.alert_engine.alert_history", BadIterable())
    monkeypatch.setattr("core.repair_engine.repair_history", BadIterable())
    monkeypatch.setattr(
        "core.metrics_history.metrics_history",
        MagicMock(get_stats=MagicMock(side_effect=RuntimeError("stats bad"))),
    )
    monkeypatch.setattr(
        "core.service_monitoring_manager.get_service_monitoring_manager",
        MagicMock(side_effect=RuntimeError("mgr bad")),
    )
    monkeypatch.setattr(
        "core.topology_engine.get_full_link_topology",
        AsyncMock(side_effect=RuntimeError("topo bad")),
    )
    monkeypatch.setattr("core.config_manager.config_manager", BadConfig())

    svc = ai_service.AIContextService()
    result = await svc.collect_rich_context(service_name="svc")  # noqa: F841  # Variable for test verification
    assert result["topology"] == {}
    assert result["top_processes"] == []
    assert result["recent_alerts"] == []
    assert result["recent_repairs"] == []
    assert result["stats"] == {}
    assert result["service_metrics"] == {}
    assert result["infrastructure_metrics"] == {}
    assert result["change_events"] == []
    assert result["correlated_alerts"] == []


@pytest.mark.asyncio
async def test_ai_context_service_bad_snapshot(monkeypatch):
    monkeypatch.setattr(ai_service, "get_cached_snapshot", MagicMock(return_value="notdict"))
    svc = ai_service.AIContextService()
    result = await svc.collect_rich_context()  # noqa: F841  # Variable for test verification
    assert result["topology"] == {}


@pytest.mark.asyncio
async def test_ai_context_service_gather_cancel(monkeypatch):
    monkeypatch.setattr(
        "core.ai_service.asyncio.gather", MagicMock(side_effect=asyncio.CancelledError("cancel"))
    )
    svc = ai_service.AIContextService()
    with pytest.raises(asyncio.CancelledError):
        await svc.collect_rich_context()


@pytest.mark.asyncio
async def test_ai_context_service_gather_error(monkeypatch):
    monkeypatch.setattr("core.ai_service.asyncio.gather", MagicMock(side_effect=ValueError("boom")))
    svc = ai_service.AIContextService()
    with pytest.raises(ValueError):
        await svc.collect_rich_context()


# -----------------------------------------------------------------------------
# core.redis_cluster_manager
# -----------------------------------------------------------------------------
@pytest.fixture
def redis_manager(monkeypatch):
    monkeypatch.delenv("REDIS_URL", raising=False)
    return RedisClusterManager()


def test_redis_memory_operations(redis_manager, monkeypatch):
    monkeypatch.setattr("time.time", lambda: 0)
    assert redis_manager.set("k", "v") is True
    assert redis_manager.get("k") == "v"
    assert redis_manager.exists("k") is True

    assert redis_manager.mset({"k2": "v2", "k3": "v3"}) is True
    assert redis_manager.mget(["k", "k2", "missing"]) == ["v", "v2", None]

    redis_manager.set("exp", "val", ttl=1)
    monkeypatch.setattr("time.time", lambda: 100)
    assert redis_manager.get("exp") is None
    assert redis_manager.exists("exp") is False

    monkeypatch.setattr("time.time", lambda: 0)
    assert redis_manager.expire("k", 10) is True
    assert redis_manager.delete("k") is True
    assert redis_manager.delete("missing") is False


def test_redis_locks(redis_manager):
    assert redis_manager.distributed_lock("lock1") is True
    assert redis_manager.distributed_lock("lock1") is False
    assert redis_manager.release_lock("lock1") is True
    assert redis_manager.release_lock("lock1") is False


def test_redis_create_client(monkeypatch):
    monkeypatch.delenv("REDIS_URL", raising=False)
    assert _create_redis_client() is None

    monkeypatch.setenv("REDIS_URL", "redis://bad")
    monkeypatch.setattr("redis.from_url", MagicMock(side_effect=Exception("down")))
    assert _create_redis_client() is None

    mock_client = MagicMock()
    monkeypatch.setattr("redis.from_url", MagicMock(return_value=mock_client))
    assert _create_redis_client() is mock_client


def test_redis_connection_and_info(monkeypatch):
    monkeypatch.setattr("socket.create_connection", MagicMock(side_effect=OSError("no")))
    mgr = RedisClusterManager()
    assert mgr.connect("localhost", 6379)["status"] == "memory_fallback"
    assert mgr.ping()["mode"] == "memory"
    assert mgr.info()["mode"] == "memory"
    assert mgr.is_connected is False

    mock_client = MagicMock()
    mock_client.ping.return_value = True
    mock_client.info.return_value = {"role": "master"}
    monkeypatch.setattr("socket.create_connection", MagicMock())
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setattr("redis.from_url", MagicMock(return_value=mock_client))
    mgr = RedisClusterManager()
    result = mgr.connect("localhost", 6379)  # noqa: F841  # Variable for test verification
    assert result["status"] == "connected"
    assert mgr.is_connected is True
    assert mgr.ping()["ok"] is True
    assert mgr.info()["info"]["role"] == "master"


def test_redis_redis_fallback(monkeypatch):
    client = MagicMock()
    client.set.side_effect = Exception("redis down")
    client.get.side_effect = Exception("redis down")
    client.delete.side_effect = Exception("redis down")
    client.ping.side_effect = Exception("redis down")
    client.info.side_effect = Exception("redis down")
    monkeypatch.setattr("core.redis_cluster_manager._create_redis_client", lambda *a, **k: client)
    mgr = RedisClusterManager(connection_string="redis://x")
    assert mgr.is_connected is True
    assert mgr.set("k", "v") is True
    assert mgr.get("k") == "v"
    assert mgr.ping()["ok"] is False
    assert "error" in mgr.info()
    assert mgr.distributed_lock("l", ttl=10) is True
    assert mgr.release_lock("l") is True
    assert mgr.delete("k") is True
