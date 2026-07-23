# -*- coding: utf-8 -*-
"""Unit and API tests for the alert microservice."""

from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient

from services.alert_service.aggregator import TimeWindowAggregator
from services.alert_service.classifier import Classifier
from services.alert_service.dedup import Deduplicator
from services.alert_service.escalator import Escalator
from services.alert_service.mq import message_queue
from services.alert_service.noise_suppressor import NoiseSuppressor
from services.alert_service.pattern_engine import PatternEngine
from services.alert_service.processor_core import AlertPipeline
from services.alert_service.repository import InMemoryAlertRepository
from services.alert_service.router import Router
from services.alert_service.saga import SagaContext, SagaOrchestrator, SagaStep
from services.alert_service.schemas import (
    Alert,
    AlertSeverity,
    ClassificationRule,
    EscalationRule,
    RoutingRule,
    SuppressionRule,
)


def alert_factory(**kwargs) -> Alert:
    defaults = {
        "id": "alert-1",
        "level": AlertSeverity.WARNING,
        "title": "CPU high",
        "description": "CPU usage is high",
        "category": "system",
        "alert_type": "cpu",
        "metric": "cpu_percent",
        "value": 85.0,
        "host": "host-a",
        "platform": "linux",
    }
    defaults.update(kwargs)
    return Alert(**defaults)


@pytest.fixture(autouse=True)
def reset_message_queue():
    message_queue.reset()
    yield
    message_queue.reset()


# ---------------------------------------------------------------------------
# Deduplication (24.4)
# ---------------------------------------------------------------------------


def test_deduplicator_fingerprint_window():
    dedup = Deduplicator(window_seconds=300)
    a1 = alert_factory(id="a1")
    a2 = alert_factory(id="a2")

    assert dedup.is_duplicate(a1) is False
    assert dedup.is_duplicate(a2) is True
    assert a1.fingerprint == a2.fingerprint

    a3 = alert_factory(id="a3")
    assert dedup.is_duplicate(a3) is True
    assert a3.prev_suppressed == 1


def test_deduplicator_different_alert_not_duplicate():
    dedup = Deduplicator(window_seconds=300)
    a1 = alert_factory(id="a1")
    a2 = alert_factory(id="a2", title="Memory high", metric="memory_percent")

    assert dedup.is_duplicate(a1) is False
    assert dedup.is_duplicate(a2) is False
    assert a1.fingerprint != a2.fingerprint


# ---------------------------------------------------------------------------
# Aggregation (24.3)
# ---------------------------------------------------------------------------


def test_aggregator_sliding_window():
    agg = TimeWindowAggregator(window_seconds=300, mode="sliding")
    a1 = alert_factory(id="a1")
    a2 = alert_factory(id="a2")

    assert agg.add(a1) == []
    result = agg.add(a2)
    assert len(result) == 1
    assert result[0].aggregated_count == 2
    assert "聚合" in result[0].title


def test_aggregator_tumbling_window():
    agg = TimeWindowAggregator(window_seconds=1, mode="tumbling")
    a1 = alert_factory(id="a1")
    a2 = alert_factory(id="a2")

    # First bucket
    assert agg.add(a1) == []
    assert agg.add(a2) == []

    # Force flush aggregates alerts in the same bucket.
    flushed = agg.flush(force=True)
    assert len(flushed) == 1
    assert flushed[0].aggregated_count == 2


# ---------------------------------------------------------------------------
# Classification (24.7)
# ---------------------------------------------------------------------------


def test_classifier_rule_and_fallback():
    classifier = Classifier()
    rule = ClassificationRule(
        name="cpu_rule",
        conditions={"metric": "cpu_percent"},
        category="performance",
        priority="P2",
    )
    classifier.add_rule(rule)

    a = alert_factory(title="CPU high", metric="cpu_percent")
    classifier.classify(a)
    assert a.category == "performance"
    assert a.priority == "P2"

    b = alert_factory(title="SSH brute force", metric="ssh_failed")
    classifier.classify(b)
    assert b.category == "security"
    assert b.priority == "P1"


# ---------------------------------------------------------------------------
# Routing (24.5)
# ---------------------------------------------------------------------------


def test_router_rule_and_default():
    router = Router()
    rule = RoutingRule(
        name="critical",
        conditions={"level": AlertSeverity.CRITICAL},
        destination="immediate",
        priority=1,
    )
    router.add_rule(rule)

    a = alert_factory(level=AlertSeverity.CRITICAL)
    assert router.route(a) == "immediate"

    b = alert_factory(level=AlertSeverity.WARNING, category="database")
    assert router.route(b) == "infrastructure_team"


# ---------------------------------------------------------------------------
# Escalation (24.6)
# ---------------------------------------------------------------------------


def test_escalator_time_threshold():
    import time

    escalator = Escalator()
    rule = EscalationRule(
        name="crit_escalate",
        level_threshold=AlertSeverity.CRITICAL,
        time_threshold_seconds=0,
    )
    escalator.add_rule(rule)

    a = alert_factory(id="esc-1", level=AlertSeverity.CRITICAL)
    escalator.track(a)
    time.sleep(0.01)
    assert escalator.should_escalate(a) == "oncall"

    b = alert_factory(id="esc-2", level=AlertSeverity.WARNING)
    escalator.track(b)
    assert escalator.should_escalate(b) is None


# ---------------------------------------------------------------------------
# Noise suppression (24.9)
# ---------------------------------------------------------------------------


def test_noise_suppressor_rule():
    suppressor = NoiseSuppressor()
    rule = SuppressionRule(
        name="cpu_noise",
        pattern="cpu",
        window_seconds=300,
        reason="known cpu fluctuation",
    )
    suppressor.add_rule(rule)

    a = alert_factory(title="CPU spike", level=AlertSeverity.WARNING)
    assert suppressor.is_noise(a) is True
    assert a.suppressed is True


def test_noise_suppressor_auto_detect():
    suppressor = NoiseSuppressor(min_noise_count=3, window_seconds=300)
    for i in range(3):
        a = alert_factory(id=f"n{i}", title="info alert", level=AlertSeverity.INFO)
        suppressor.is_noise(a)
    a4 = alert_factory(id="n3", title="info alert", level=AlertSeverity.INFO)
    assert suppressor.is_noise(a4) is True


# ---------------------------------------------------------------------------
# Pattern recognition (24.8)
# ---------------------------------------------------------------------------


def test_pattern_engine_recognize():
    engine = PatternEngine()
    alerts = [alert_factory(id=f"p{i}") for i in range(3)]
    engine.train(alerts)
    new_alert = alert_factory(id="p-new")
    pattern = engine.predict(new_alert)
    assert pattern != "unknown"
    assert len(engine.get_patterns()) >= 1


# ---------------------------------------------------------------------------
# Saga (24.10)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_saga_success():
    async def add_one(ctx: SagaContext):
        ctx.data["value"] = ctx.data.get("value", 0) + 1

    steps = [SagaStep(name="step1", action=add_one)]
    result = await SagaOrchestrator().execute(steps)
    assert result["status"] == "completed"
    assert result["data"]["value"] == 1


@pytest.mark.asyncio
async def test_saga_compensation():
    async def add_one(ctx: SagaContext):
        ctx.data["value"] = ctx.data.get("value", 0) + 1

    async def compensate(ctx: SagaContext):
        ctx.data["value"] = 0

    async def fail(ctx: SagaContext):
        raise RuntimeError("boom")

    steps = [
        SagaStep(name="step1", action=add_one, compensation=compensate),
        SagaStep(name="step2", action=fail),
    ]
    result = await SagaOrchestrator().execute(steps)
    assert result["status"] == "failed"
    assert result["compensated"] == ["step1"]


# ---------------------------------------------------------------------------
# Pipeline (24.2/24.3/24.4/24.5/24.6/24.7/24.8/24.9/24.10)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pipeline_process_and_flush():
    repo = InMemoryAlertRepository()
    pipeline = AlertPipeline(repository=repo, mq=message_queue, window_seconds=1)

    alert = alert_factory(id="pipe-1", title="CPU high")
    result = await pipeline.process_and_flush(alert)

    assert result["status"] == "buffered"
    assert result["alert_id"] == "pipe-1"
    assert len(result["flushed"]) >= 1
    saved = await repo.list(limit=10)
    assert len(saved) >= 1


# ---------------------------------------------------------------------------
# API endpoints
# ---------------------------------------------------------------------------


def test_collector_health():
    from services.alert_service import collector as collector_module

    with TestClient(collector_module.app) as client:
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["service"] == "alert-collector"


def test_collector_receive_alerts():
    from services.alert_service import collector as collector_module

    payload = {
        "version": "4",
        "groupKey": "{}:{}"[:6],
        "status": "firing",
        "receiver": "default",
        "alerts": [
            {
                "status": "firing",
                "labels": {
                    "alertname": "HighCPU",
                    "severity": "critical",
                    "instance": "host-1",
                    "__name__": "cpu_percent",
                    "value": "95.0",
                },
                "annotations": {
                    "summary": "CPU usage high",
                    "description": "CPU above threshold",
                },
                "startsAt": "2026-07-18T12:00:00Z",
            }
        ],
    }

    with TestClient(collector_module.app) as client:
        resp = client.post("/alerts", json=payload)
        assert resp.status_code == 200
        body = resp.json()
        assert body["received"] == 1
        assert body["saved"] == 1
        assert len(body["ids"]) == 1


def test_collector_metrics():
    from services.alert_service import collector as collector_module

    with TestClient(collector_module.app) as client:
        resp = client.get("/metrics")
        assert resp.status_code == 200
        assert "text/plain" in resp.headers.get("content-type", "")


def test_processor_health_and_rules():
    from services.alert_service import processor as processor_module

    with TestClient(processor_module.app) as client:
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["service"] == "alert-processor"

        rule = {
            "name": "critical_route",
            "conditions": {"level": "critical"},
            "destination": "immediate",
            "priority": 1,
            "enabled": True,
        }
        resp = client.post("/rules/routing", json=rule)
        assert resp.status_code == 200

        resp = client.get("/rules/routing")
        assert resp.status_code == 200
        assert len(resp.json()["rules"]) == 1


def test_processor_process_alert():
    from services.alert_service import processor as processor_module

    alert = {
        "id": "proc-1",
        "level": "critical",
        "title": "CPU critical",
        "description": "CPU usage critical",
        "metric": "cpu_percent",
        "value": 95.0,
        "host": "host-1",
    }

    with TestClient(processor_module.app) as client:
        resp = client.post("/process", json=alert)
        assert resp.status_code == 200
        body = resp.json()
        assert body["alert_id"] == "proc-1"

        resp = client.get("/stats")
        assert resp.status_code == 200


def test_notifier_health_and_notify():
    from services.alert_service import notifier as notifier_module

    alert = {
        "id": "not-1",
        "level": "critical",
        "title": "CPU critical",
        "description": "CPU usage critical",
        "host": "host-1",
    }

    with TestClient(notifier_module.app) as client:
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["service"] == "alert-notifier"

        resp = client.post("/notify", json=alert)
        assert resp.status_code == 200
        assert resp.json()["success"] is True

        resp = client.get("/history")
        assert resp.status_code == 200
        assert resp.json()["total"] == 1


# ---------------------------------------------------------------------------
# Repository
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_repository():
    repo = InMemoryAlertRepository()
    alert = alert_factory(id="repo-1")

    assert await repo.save(alert) == "repo-1"
    assert (await repo.get("repo-1")) is not None
    assert len(await repo.list(limit=10)) == 1
    assert await repo.count() == 1

    await repo.update("repo-1", {"status": "resolved"})
    updated = await repo.get("repo-1")
    assert updated.status == "resolved"

    assert await repo.delete("repo-1") is True
    assert await repo.delete("missing") is False
    assert await repo.clear() == 0


# ---------------------------------------------------------------------------
# Notification service
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_notification_service_webhook():
    from unittest.mock import AsyncMock

    from services.alert_service.notifier import NotificationService

    mock_client = AsyncMock()
    mock_response = AsyncMock()
    mock_response.is_success = True
    mock_response.status_code = 200
    mock_client.post.return_value = mock_response

    service = NotificationService(
        webhook_url="http://example.com/webhook",
        min_level="warning",
        client=mock_client,
    )
    result = await service.notify(alert_factory(id="not-2"))
    assert result["success"] is True
    assert len(service.history) == 1
    mock_client.post.assert_awaited_once()


@pytest.mark.asyncio
async def test_notification_service_consume():
    from unittest.mock import AsyncMock

    from services.alert_service.notifier import NotificationService

    service = NotificationService(client=AsyncMock())
    await message_queue.publish(
        "alerts.routed",
        {"type": "routed_alert", "alert": alert_factory(id="not-3").model_dump()},
    )
    try:
        await asyncio.wait_for(service.consume_loop(asyncio.Event()), timeout=2.0)
    except asyncio.TimeoutError:
        pass
    assert len(service.history) == 1


# ---------------------------------------------------------------------------
# Processor pipeline
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_processor_core_suppress_and_dedup():
    repo = InMemoryAlertRepository()
    pipeline = AlertPipeline(repository=repo, mq=message_queue, window_seconds=1)

    # Suppression rule matches title containing "fluctuation"
    pipeline.noise_suppressor.add_rule(
        SuppressionRule(name="fluctuation", pattern="fluctuation", reason="known pattern")
    )
    a1 = alert_factory(id="pc-s1", title="CPU fluctuation")
    result = await pipeline.process_and_flush(a1)
    assert result["status"] == "suppressed"

    # Deduplication: second identical alert is a duplicate
    a2 = alert_factory(id="pc-d1")
    a3 = alert_factory(id="pc-d2")
    r1 = await pipeline.process_and_flush(a2)
    r2 = await pipeline.process_and_flush(a3)
    assert r1["status"] == "buffered"
    assert r2["status"] == "duplicate"


@pytest.mark.asyncio
async def test_processor_core_flush_and_stats():
    import time

    from services.alert_service.processor_core import AlertPipeline

    repo = InMemoryAlertRepository()
    pipeline = AlertPipeline(repository=repo, mq=message_queue, window_seconds=1)

    a1 = alert_factory(id="pc-f1")
    a2 = alert_factory(id="pc-f2")
    await pipeline.process_alert(a1)
    await pipeline.process_alert(a2)

    time.sleep(1.1)
    flushed = await pipeline.flush(force=False)
    assert len(flushed) >= 1

    stats = pipeline.get_stats()
    assert "dedup" in stats
    assert "noise" in stats


@pytest.mark.asyncio
async def test_processor_core_run_stop():
    from services.alert_service.processor_core import AlertPipeline

    repo = InMemoryAlertRepository()
    pipeline = AlertPipeline(repository=repo, mq=message_queue, window_seconds=1)
    task = asyncio.create_task(pipeline.run())
    await asyncio.sleep(0.05)
    await pipeline.stop()
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


# ---------------------------------------------------------------------------
# Classifier / router / escalator helpers
# ---------------------------------------------------------------------------


def test_classifier_disabled_and_tag_rules():
    classifier = Classifier()
    disabled = ClassificationRule(
        name="disabled",
        conditions={"metric": "cpu_percent"},
        category="performance",
        priority="P2",
        enabled=False,
    )
    classifier.add_rule(disabled)

    tag_rule = ClassificationRule(
        name="tag_rule",
        conditions={"tags.env": "prod"},
        category="production",
        priority="P1",
    )
    classifier.add_rule(tag_rule)

    alert = alert_factory(tags={"env": "prod"})
    classifier.classify(alert)
    assert alert.category == "production"

    no_match = alert_factory(title="unknown event", description="no relevant info", metric="other")
    classifier.classify(no_match)
    assert no_match.category == "system"


def test_classifier_keyword_fallbacks():
    classifier = Classifier()
    db_alert = alert_factory(
        title="Postgres connection failed",
        description="database unreachable",
        metric="sql",
    )
    classifier.classify(db_alert)
    assert db_alert.category == "database"

    net_alert = alert_factory(
        title="High DNS latency",
        description="network slow",
        metric="latency",
    )
    classifier.classify(net_alert)
    assert net_alert.category == "network"


def test_classifier_list_rules():
    classifier = Classifier()
    rule = ClassificationRule(
        name="cpu",
        conditions={"metric": "cpu_percent"},
        category="performance",
        priority="P2",
    )
    classifier.add_rule(rule)
    assert len(classifier.list_rules()) == 1


def test_router_list_and_default():
    router = Router()
    router.add_rule(
        RoutingRule(
            name="db",
            conditions={"category": "database"},
            destination="dba_team",
        )
    )
    assert len(router.list_rules()) == 1
    a = alert_factory(category="database")
    assert router.route(a) == "dba_team"


def test_escalator_clear():
    escalator = Escalator()
    a = alert_factory(id="esc-clear")
    escalator.track(a)
    assert escalator.clear() == 1


def test_noise_suppressor_stats():
    suppressor = NoiseSuppressor()
    assert "pattern_count" in suppressor.get_stats()


def test_pattern_engine_patterns():
    engine = PatternEngine()
    alerts = [alert_factory(id=f"pat{i}") for i in range(2)]
    engine.train(alerts)
    assert len(engine.get_patterns()) >= 1


# ---------------------------------------------------------------------------
# Processor API rule endpoints
# ---------------------------------------------------------------------------


def test_processor_all_rule_endpoints():
    from services.alert_service import processor as processor_module

    with TestClient(processor_module.app) as client:
        resp = client.post(
            "/rules/suppression",
            json={
                "name": "s1",
                "pattern": "test",
                "window_seconds": 60,
                "reason": "test",
                "enabled": True,
            },
        )
        assert resp.status_code == 200

        resp = client.get("/rules/suppression")
        assert resp.status_code == 200

        resp = client.post(
            "/rules/escalation",
            json={
                "name": "e1",
                "level_threshold": "critical",
                "time_threshold_seconds": 0,
                "escalation_target": "oncall",
                "enabled": True,
            },
        )
        assert resp.status_code == 200

        resp = client.get("/rules/escalation")
        assert resp.status_code == 200

        resp = client.post(
            "/rules/classification",
            json={
                "name": "c1",
                "conditions": {"metric": "cpu_percent"},
                "category": "performance",
                "priority": "P2",
                "enabled": True,
            },
        )
        assert resp.status_code == 200

        resp = client.get("/rules/classification")
        assert resp.status_code == 200
