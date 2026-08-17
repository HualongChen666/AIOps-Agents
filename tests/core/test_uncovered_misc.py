# -*- coding: utf-8 -*-
"""Unit tests for low-coverage core alert, snapshot and integration modules."""

import json
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from core import snapshot_store
from core.alert_intelligence import AlertIntelligenceEngine
from core.integration_manager import IntegrationManager, IntegrationType

pytestmark = [pytest.mark.core]


# ---------------------------------------------------------------------------
# core.alert_intelligence
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_alert_intelligence_empty_analysis():
    engine = AlertIntelligenceEngine()
    result = await engine.analyze_and_aggregate_alerts([])
    assert result == []


@pytest.mark.asyncio
async def test_alert_intelligence_analyze_and_route():
    engine = AlertIntelligenceEngine()
    alerts = [
        {
            "id": "1",
            "level": "warning",
            "category": "database",
            "title": "cpu high",
            "desc": "d1",
            "host": "db1",
            "metric": "cpu",
        },
        {
            "id": "2",
            "level": "warning",
            "category": "database",
            "title": "cpu high 2",
            "desc": "d2",
            "host": "db1",
            "metric": "cpu",
        },
    ]
    aggregated = await engine.analyze_and_aggregate_alerts(alerts)
    assert isinstance(aggregated, list)
    assert len(aggregated) == 1
    assert "aggregated_count" in aggregated[0]

    routed = await engine.route_alerts_intelligently(aggregated)
    assert isinstance(routed, dict)
    assert "infrastructure_team" in routed


@pytest.mark.asyncio
async def test_alert_intelligence_predict_and_stats():
    engine = AlertIntelligenceEngine()
    now = datetime.now()
    data = [(now, float(i)) for i in range(5)]
    prediction = await engine.predict_alert_trends("cpu", data, horizon_hours=4)
    assert prediction.metric_name == "cpu"
    assert prediction.model_used == "insufficient_data"

    engine.add_routing_rule({"destination": "slack", "conditions": {"level": "critical"}})
    engine.add_suppression_rule({"signature": "x"})
    stats = engine.get_alert_statistics()
    assert isinstance(stats, dict)
    assert stats["routing_rules"] == 1
    assert stats["suppression_rules"] == 1


def test_alert_intelligence_topology():
    engine = AlertIntelligenceEngine()
    ctx = engine.build_topology_context(
        [
            {"host": "db1", "category": "database"},
            {"host": "app1", "category": "availability"},
        ]
    )
    assert isinstance(ctx, dict)
    assert "nodes" in ctx
    assert "edges" in ctx
    assert "components" in ctx
    assert "alert_count_by_component" in ctx


# ---------------------------------------------------------------------------
# core.snapshot_store
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_session(monkeypatch):
    """Replace AsyncSessionLocal with an async context manager returning a fake session."""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.add = MagicMock()
    session.get = AsyncMock(return_value=None)
    session.execute = AsyncMock(return_value=MagicMock(rowcount=0))

    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=session)
    cm.__aexit__ = AsyncMock(return_value=False)

    monkeypatch.setattr(snapshot_store, "AsyncSessionLocal", MagicMock(return_value=cm))
    return session


def test_snapshot_store_classify_and_helpers():
    assert (
        snapshot_store.classify_operation_type(
            ["kubectl rollout restart deployment/nginx -n default"], ""
        )
        == "pod_restart"
    )
    assert snapshot_store.classify_operation_type(["echo", "test"], "script") == "generic"

    resource = snapshot_store._extract_k8s_resource(
        "kubectl scale deployment nginx --replicas=3 --namespace bar"
    )
    assert resource is not None
    assert resource[0] == "deployment"
    assert resource[2] == "bar"


@pytest.mark.asyncio
async def test_snapshot_store_build_pre_state():
    pre = await snapshot_store.build_pre_state("generic", {"id": "a1"}, ["echo"], "linux", "h1")
    assert isinstance(pre, dict)
    assert pre["operation_type"] == "generic"
    assert "resources" in pre


@pytest.mark.asyncio
async def test_snapshot_store_save_and_get(monkeypatch, fake_session):
    monkeypatch.setenv("SNAPSHOT_ENCRYPTION_ENABLED", "false")

    state = SimpleNamespace(
        alert={"id": "a1", "platform": "linux", "host": "h1"},
        snapshot=None,
        runbook={"script_key": ""},
    )
    snapshot_id = await snapshot_store.save_snapshot(
        state, ["echo", "test"], ["rollback"], "r1", {"cpu": 1.0}
    )
    assert isinstance(snapshot_id, str)
    assert state.snapshot_id == snapshot_id
    assert isinstance(state.snapshot, dict)
    assert "pre_state" in state.snapshot
    assert state.rollback_info is not None

    now = datetime.now(timezone.utc)
    plain = json.dumps({"x": 1})
    snap = snapshot_store.Snapshot(
        id=snapshot_id,
        alert_id="a1",
        repair_record_id="r1",
        operation_type="generic",
        pre_state=snapshot_store.encrypt_snapshot(plain),
        post_state=snapshot_store.encrypt_snapshot(json.dumps({"y": 2})),
        rollback_plan=snapshot_store.encrypt_snapshot(json.dumps({"commands": []})),
        status="completed",
        retention_days=7,
        expires_at=now,
        created_at=now,
        completed_at=now,
        error_message=None,
    )
    fake_session.get.return_value = snap

    result = await snapshot_store.get_snapshot(snapshot_id)
    assert isinstance(result, dict)
    assert result["id"] == snapshot_id
    assert result["alert_id"] == "a1"
    assert "pre_state" in result
    assert result["pre_state"] == {"x": 1}


@pytest.mark.asyncio
async def test_snapshot_store_update_status(monkeypatch, fake_session):
    monkeypatch.setenv("SNAPSHOT_ENCRYPTION_ENABLED", "false")
    snap = SimpleNamespace(
        status="pending",
        completed_at=None,
        post_state=None,
        error_message=None,
    )
    fake_session.get.return_value = snap

    await snapshot_store.update_snapshot_status("snap-1", "completed", {"cpu": 1.0}, "error msg")
    assert snap.status == "completed"
    assert snap.error_message == "error msg"
    assert snap.post_state is not None
    assert snap.completed_at is not None


@pytest.mark.asyncio
async def test_snapshot_store_cleanup_expired(fake_session):
    fake_session.execute.return_value = MagicMock(rowcount=5)
    count = await snapshot_store.cleanup_expired_snapshots()
    assert count == 5


# ---------------------------------------------------------------------------
# core.integration_manager
# ---------------------------------------------------------------------------


def _make_manager(monkeypatch):
    """Build an IntegrationManager with a mocked httpx client."""
    fake_client = AsyncMock()
    response = MagicMock()
    response.status_code = 200
    response.text = "ok"
    response.json.return_value = {"data": {"result": []}}
    response.raise_for_status = MagicMock()
    fake_client.get = AsyncMock(return_value=response)
    fake_client.post = AsyncMock(return_value=response)

    monkeypatch.setattr("httpx.AsyncClient", lambda **kwargs: fake_client)
    return IntegrationManager({}), fake_client, response


@pytest.mark.asyncio
async def test_integration_manager_register_and_summary(monkeypatch):
    manager, _, _ = _make_manager(monkeypatch)
    config = await manager.register_integration(
        IntegrationType.MONITORING, "prometheus", {"url": "http://prometheus:9090"}
    )
    assert config.name == "prometheus"
    assert config.status.value == "active"

    summary = manager.get_integration_summary()
    assert isinstance(summary, dict)
    assert summary["total_integrations"] == 1


@pytest.mark.asyncio
async def test_integration_manager_query_prometheus(monkeypatch):
    manager, _, response = _make_manager(monkeypatch)
    config = await manager.register_integration(
        IntegrationType.MONITORING, "prometheus", {"url": "http://prometheus:9090"}
    )
    response.json.return_value = {"data": {"result": [{"values": []}]}}
    result = await manager.query_prometheus_metrics(config.integration_id, "up", "1h")
    assert isinstance(result, dict)
    assert "data" in result


@pytest.mark.asyncio
async def test_integration_manager_query_pagerduty(monkeypatch):
    manager, _, response = _make_manager(monkeypatch)
    config = await manager.register_integration(
        IntegrationType.ITSM, "pagerduty", {"api_key": "pd-key"}
    )
    response.json.return_value = {"incidents": []}
    result = await manager.query_pagerduty_incidents(config.integration_id, "svc", "1h")
    assert isinstance(result, dict)
    assert "incidents" in result


@pytest.mark.asyncio
async def test_integration_manager_query_cloudwatch(monkeypatch):
    manager, _, _ = _make_manager(monkeypatch)
    config = await manager.register_integration(
        IntegrationType.CLOUD,
        "cloudwatch",
        {
            "region": "us-east-1",
            "aws_access_key_id": "a",
            "aws_secret_access_key": "s",
        },
    )
    result = await manager.query_cloudwatch_metrics(
        config.integration_id, "AWS/EC2/CPUUtilization", "1h"
    )
    assert isinstance(result, dict)
    assert "error" in result


@pytest.mark.asyncio
async def test_integration_manager_jira_and_jenkins(monkeypatch):
    manager, _, _ = _make_manager(monkeypatch)
    jenkins = await manager.register_integration(
        IntegrationType.CICD,
        "jenkins",
        {"url": "http://jenkins", "username": "u", "api_token": "t"},
    )
    result = await manager.trigger_jenkins_job(jenkins.integration_id, "build")
    assert result["success"] is True
    assert result["job_name"] == "build"

    jira = await manager.register_integration(
        IntegrationType.ITSM,
        "jira",
        {"url": "http://jira", "username": "u", "api_token": "t"},
    )
    result = await manager.create_jira_issue(jira.integration_id, "bug", "desc")
    assert result["success"] is True
    assert "issue_key" in result


@pytest.mark.asyncio
async def test_integration_manager_webhook(monkeypatch):
    manager, _, _ = _make_manager(monkeypatch)
    webhook_id = await manager.register_webhook("github", "push", "http://example/hook")
    assert isinstance(webhook_id, str)

    result = await manager.handle_webhook(webhook_id, {"ref": "refs/heads/main"})
    assert result["success"] is True
    assert "event_id" in result


@pytest.mark.asyncio
async def test_integration_manager_send_notification(monkeypatch):
    manager, _, _ = _make_manager(monkeypatch)
    manager.notification_channels["slack"] = {
        "name": "slack",
        "type": "webhook",
        "config": {"url": "http://slack/hook"},
        "enabled": True,
    }
    msg = await manager.send_notification("slack", "#alerts", "subject", "body")
    assert msg.channel == "slack"
    assert msg.sent is True
