# -*- coding: utf-8 -*-
"""Functional coverage tests for batch19c core modules."""

import asyncio  # noqa: F401  # Imported for test setup
import sys  # noqa: F401  # Imported for test setup
from datetime import datetime, timedelta, timezone
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock

import pytest  # noqa: F401  # Imported for test setup

from core.api_governance import (
    APIEndpoint,
    APIGovernance,
    APIStatus,
    api_governance,
    setup_api_governance,
)
from core.error_logging.handler import (
    ErrorLogHandler,
    get_error_count,
    get_error_log_handler,
    get_error_stats,
    record_error,
)
from core.hitl.history import ApprovalHistory, ApprovalRecord
from core.kubernetes_deployment_manager import (
    DeploymentConfig,
    DeploymentState,
    DeploymentStatus,
    KubernetesDeploymentManager,
    ResourceType,
    get_kubernetes_deployment_manager,
)

pytestmark = [pytest.mark.core]


# -----------------------------------------------------------------------------
# core.api_governance
# -----------------------------------------------------------------------------
def test_api_governance_lifecycle():
    gov = APIGovernance()

    # default setup
    versions = gov.get_api_versions()
    assert len(versions) == 1
    assert versions[0]["version"] == "v1"

    # register a new endpoint
    ep = APIEndpoint(
        path="/api/v2/events",
        method="POST",
        version="v2",
        description="Events endpoint",
    )
    gov.register_endpoint(ep)
    assert gov.check_endpoint_status("/api/v2/events", "POST")["status"] == "active"

    # record usage
    gov.record_endpoint_usage("/api/v1/alerts", "GET")
    gov.record_endpoint_usage("/api/v2/events", "POST")
    assert gov._endpoints["GET:/api/v1/alerts"].usage_count == 1

    # deprecate endpoint
    sunset = datetime.now(timezone.utc) + timedelta(days=30)
    result = gov.deprecate_endpoint(  # noqa: F841  # Variable for test verification
        "/api/v1/alerts", "GET", sunset, replacement_path="/api/v2/alerts"
    )
    assert result["status"] == "success"
    assert "replacement" in result

    # check deprecated status
    status = gov.check_endpoint_status("/api/v1/alerts", "GET")
    assert status["status"] == "deprecated"
    assert "warning" in status
    assert status["replacement"] == "/api/v2/alerts"

    # sunset endpoint via registering a sunset endpoint
    sunset_ep = APIEndpoint(
        path="/api/v1/legacy",
        method="GET",
        version="v1",
        status=APIStatus.SUNSET,
    )
    gov.register_endpoint(sunset_ep)
    assert len(gov.get_sunset_endpoints()) == 1

    # retire endpoint
    retire_result = gov.retire_endpoint("/api/v1/metrics", "GET")  # noqa: F841  # Variable for test verification
    assert retire_result["status"] == "success"
    retired = gov.check_endpoint_status("/api/v1/metrics", "GET")
    assert retired["status"] == "retired"
    assert retired["error"] == "This endpoint has been retired"

    # unknown endpoints
    assert gov.deprecate_endpoint("/missing", "GET", sunset)["status"] == "error"
    assert gov.retire_endpoint("/missing", "GET")["status"] == "error"
    assert gov.check_endpoint_status("/missing", "GET")["status"] == "error"

    # get by status
    assert len(gov.get_deprecated_endpoints()) >= 1
    assert len(gov.get_endpoints_by_status(APIStatus.RETIRED)) >= 1

    # usage stats
    stats = gov.get_usage_stats()
    assert stats["total_endpoints"] == len(gov._endpoints)
    assert stats["total_usage"] >= 2
    assert isinstance(stats["endpoint_stats"], list)


async def _setup_api_governance():
    return await setup_api_governance()


def test_setup_api_governance():
    result = asyncio.run(_setup_api_governance())  # noqa: F841  # Variable for test verification
    assert result["status"] == "success"
    assert result["versions"] == 1
    assert result["endpoints"] == len(api_governance._endpoints)


# -----------------------------------------------------------------------------
# core.error_logging.handler
# -----------------------------------------------------------------------------
def test_error_log_handler_functions():
    handler = ErrorLogHandler()

    ts = datetime.now() - timedelta(minutes=5)
    handler.record_error("E001", "critical", "database", timestamp=ts)
    handler.record_error("E001", "critical", "database", timestamp=ts)
    handler.record_error("E002", "warning", "network", timestamp=ts)

    assert handler.get_error_stats() == {"E001": 2, "E002": 1}
    assert handler.get_error_count() == 3
    assert handler.get_error_count("E001") == 2
    assert handler.get_error_count("missing") == 0

    history = handler.get_error_history(limit=10)
    assert len(history) == 3
    assert len(handler.get_error_history(error_code="E001")) == 2

    severe = handler.get_error_history(severity="warning")
    assert all(h["severity"] == "warning" for h in severe)

    db = handler.get_error_history(category="database")
    assert all(h["category"] == "database" for h in db)

    trends = handler.get_error_trends("E001", hours=24)
    assert len(trends) == 2

    rate = handler.get_error_rate(hours=1)
    assert rate >= 3.0
    rate_specific = handler.get_error_rate("E001", hours=1)
    assert rate_specific == 2.0

    top = handler.get_top_errors(limit=1)
    assert top[0][0] == "E001"

    assert handler.get_category_stats() == {"database": 2, "network": 1}
    assert handler.get_severity_stats() == {"critical": 2, "warning": 1}

    handler.clear_history()
    assert handler.get_error_count() == 0
    assert len(handler._error_history) == 0


def test_error_log_pruning_and_global_helpers(monkeypatch):
    handler = get_error_log_handler()
    handler.clear_history()

    for i in range(10001):
        record_error(f"E{i % 3:03d}", "critical", "load")

    assert len(handler._error_history) == 5000
    assert handler.get_error_count() > 0
    assert get_error_count("E000") > 0
    assert "E000" in get_error_stats()

    handler.clear_history()


# -----------------------------------------------------------------------------
# core.hitl.history
# -----------------------------------------------------------------------------
def test_approval_history():
    history = ApprovalHistory()

    record = history.record_action(
        request_id="req-1",
        workflow_id="wf-1",
        action="approved",
        actor="alice",
        details={"comment": "looks good"},
    )
    assert record.action == "approved"
    assert record.details == {"comment": "looks good"}

    history.record_action(
        request_id="req-1",
        workflow_id="wf-1",
        action="commented",
        actor="bob",
        details={"comment": "check again"},
    )
    history.record_action(
        request_id="req-2",
        workflow_id="wf-2",
        action="rejected",
        actor="alice",
    )

    all_records = history.get_history()
    assert len(all_records) == 3

    req1 = history.get_history(request_id="req-1")
    assert len(req1) == 2

    wf2 = history.get_history(workflow_id="wf-2")
    assert len(wf2) == 1

    alice = history.get_history(actor="alice")
    assert len(alice) == 2

    since = datetime.now() - timedelta(minutes=1)
    recent = history.get_history(since=since)
    assert len(recent) == 3

    trail = history.get_audit_trail("req-1")
    assert len(trail) == 2
    assert trail[0]["request_id"] == "req-1"


def test_approval_record_to_dict():
    record = ApprovalRecord(
        record_id="r1",
        request_id="req-1",
        workflow_id="wf-1",
        action="approved",
        actor="charlie",
    )
    d = record.to_dict()
    assert d["record_id"] == "r1"
    assert d["actor"] == "charlie"
    assert "timestamp" in d


# -----------------------------------------------------------------------------
# core.kubernetes_deployment_manager
# -----------------------------------------------------------------------------
def _new_manager(tmp_path):
    return KubernetesDeploymentManager(config={"manifests_dir": str(tmp_path / "manifests")})


def test_kubernetes_manager_factory_and_resource_types():
    manager = get_kubernetes_deployment_manager()
    assert isinstance(manager, KubernetesDeploymentManager)
    assert ResourceType.DEPLOYMENT.value == "deployment"
    assert ResourceType.SERVICE.value == "service"
    assert ResourceType.SECRET.value in ("secret", "")


def test_kubernetes_deployment_lifecycle(tmp_path, monkeypatch):
    manager = _new_manager(tmp_path)
    monkeypatch.setattr(manager, "_execute_deployment", AsyncMock())

    config = DeploymentConfig(
        deployment_id="dep-1",
        app_name="app-1",
        namespace="default",
        replicas=2,
        image="app:1.0",
        auto_scaling=False,
    )

    dep_id = asyncio.run(manager.deploy_application(config))
    assert dep_id == "dep-1"
    assert "dep-1" in manager.deployments
    assert manager.total_deployments == 1

    status = manager.get_deployment_status("dep-1")
    assert status["deployment_id"] == "dep-1"
    assert status["status"] == "pending"

    deployments = manager.list_deployments()
    assert len(deployments) == 1

    assert asyncio.run(manager.scale_deployment("dep-1", 5)) is True
    assert manager.deployments["dep-1"].replicas == 5
    scaled = manager.get_deployment_status("dep-1")
    assert scaled["current_replicas"] == 5

    assert asyncio.run(manager.rollback_deployment("dep-1")) is True
    assert manager.deployment_states["dep-1"].status == DeploymentStatus.RUNNING

    assert asyncio.run(manager.delete_deployment("dep-1")) is True
    assert "dep-1" not in manager.deployments
    assert manager.get_deployment_status("dep-1") is None
    assert manager.list_deployments() == []

    assert asyncio.run(manager.scale_deployment("missing", 1)) is False
    assert asyncio.run(manager.rollback_deployment("missing")) is False
    assert asyncio.run(manager.delete_deployment("missing")) is False


async def _execute(manager, dep_id):
    await manager._execute_deployment(dep_id)


def test_kubernetes_execute_deployment_success(tmp_path, monkeypatch):
    manager = _new_manager(tmp_path)
    config = DeploymentConfig(
        deployment_id="dep-ok",
        app_name="app-ok",
        namespace="default",
        replicas=1,
        image="app:1.0",
        auto_scaling=True,
    )
    manager.deployments["dep-ok"] = config
    manager.deployment_states["dep-ok"] = DeploymentState(
        deployment_id="dep-ok", status=DeploymentStatus.PENDING
    )

    monkeypatch.setattr(manager, "_apply_manifests", AsyncMock())
    monkeypatch.setattr(manager, "_wait_for_deployment_ready", AsyncMock())

    asyncio.run(_execute(manager, "dep-ok"))

    state = manager.deployment_states["dep-ok"]
    assert state.status == DeploymentStatus.RUNNING
    assert state.current_replicas == 1
    assert state.ready_replicas == 1
    assert state.error_message is None
    assert manager.successful_deployments == 1

    manifest_dir = manager.manifests_dir / "dep-ok"
    assert (manifest_dir / "deployment.yaml").exists()
    assert (manifest_dir / "service.yaml").exists()
    assert (manifest_dir / "hpa.yaml").exists()

    # manifest generators
    d_manifest = manager._generate_deployment_manifest(config)
    assert config.app_name in d_manifest
    s_manifest = manager._generate_service_manifest(config)
    assert "LoadBalancer" in s_manifest
    h_manifest = manager._generate_hpa_manifest(config)
    assert config.app_name in h_manifest


def test_kubernetes_execute_deployment_failure(tmp_path, monkeypatch):
    manager = _new_manager(tmp_path)
    config = DeploymentConfig(
        deployment_id="dep-fail",
        app_name="app-fail",
        namespace="default",
        replicas=1,
        image="app:1.0",
    )
    manager.deployments["dep-fail"] = config
    manager.deployment_states["dep-fail"] = DeploymentState(
        deployment_id="dep-fail", status=DeploymentStatus.PENDING
    )

    monkeypatch.setattr(manager, "_generate_manifests", AsyncMock(side_effect=RuntimeError("fail")))

    asyncio.run(_execute(manager, "dep-fail"))

    state = manager.deployment_states["dep-fail"]
    assert state.status == DeploymentStatus.FAILED
    assert "fail" in state.error_message
    assert manager.failed_deployments == 1

    stats = manager.get_statistics()
    assert stats["total_deployments"] == 0
    assert stats["success_rate"] == 0.0


def test_kubernetes_statistics():
    manager = KubernetesDeploymentManager(config={})
    empty = manager.get_statistics()
    assert empty["total_deployments"] == 0
    assert empty["success_rate"] == 0.0
    assert empty["active_deployments"] == 0


# -----------------------------------------------------------------------------
# core.graphql_schema
# -----------------------------------------------------------------------------
@pytest.fixture
def graphql_module(monkeypatch):
    # Mock external core modules used by GraphQL resolvers before the schema loads.
    alert_service_mod = ModuleType("core.alert_service")
    alert_service_mod.AlertService = MagicMock(
        return_value=MagicMock(get_alerts=MagicMock(return_value={"alerts": []}))
    )
    alert_service_mod.alert_service = AsyncMock()
    monkeypatch.setitem(sys.modules, "core.alert_service", alert_service_mod)

    collector_mod = ModuleType("core.collector")
    collector_mod.collect_all = MagicMock(return_value={"cpu_usage": 0.5, "mem_usage": 0.8})
    monkeypatch.setitem(sys.modules, "core.collector", collector_mod)

    health_mod = ModuleType("core.module_health_check")
    health_mod.check_all_modules_health = AsyncMock(
        return_value={
            "database": {"status": "healthy"},
            "redis": {"status": "healthy"},
        }
    )
    monkeypatch.setitem(sys.modules, "core.module_health_check", health_mod)

    engine_mod = ModuleType("core.alert_engine")
    engine_mod.alert_history = [
        {
            "id": "a-1",
            "severity": "high",
            "message": "boom",
            "source": "test",
            "created_at": datetime.now(timezone.utc),
        }
    ]
    engine_mod.acknowledge_alert = AsyncMock(return_value=True)
    monkeypatch.setitem(sys.modules, "core.alert_engine", engine_mod)

    from core.graphql_schema import Mutation, Query

    return Query(), Mutation(), alert_service_mod, collector_mod, health_mod, engine_mod


async def _run_query(query, severity=None, source=None, limit=10):
    if severity:
        return await query.alerts(limit=limit, severity=severity)
    if source:
        return await query.metrics(limit=limit, source=source)
    return await query.metrics(limit=limit)


async def _run_health(query):
    return await query.health()


async def _run_create(mutation, sev, msg, src):
    return await mutation.create_alert(sev, msg, src)


async def _run_ack(mutation, alert_id):
    return await mutation.acknowledge_alert(alert_id)


def test_graphql_alerts_happy_path(graphql_module):
    query, _, alert_mod, *_ = graphql_module
    alert_mod.AlertService.return_value.get_alerts.return_value = {
        "alerts": [
            {
                "id": "1",
                "severity": "critical",
                "message": "m",
                "source": "s",
                "created_at": datetime.now(timezone.utc),
                "status": "active",
            }
        ]
    }
    alerts = asyncio.run(_run_query(query, severity="critical"))
    assert len(alerts) == 1
    assert alerts[0].id == "1"


def test_graphql_alerts_exception(graphql_module):
    query, _, alert_mod, *_ = graphql_module
    alert_mod.AlertService.return_value.get_alerts.side_effect = RuntimeError("db down")
    alerts = asyncio.run(_run_query(query, severity="high"))
    assert alerts == []


def test_graphql_metrics_happy_path(graphql_module):
    query, _, _, collector_mod, *_ = graphql_module
    collector_mod.collect_all.return_value = {"cpu_usage": 0.5, "memory_usage": 0.9}
    metrics = asyncio.run(_run_query(query, source="cpu"))
    assert any("cpu" in m.id for m in metrics)


def test_graphql_metrics_exception(graphql_module):
    query, _, _, collector_mod, *_ = graphql_module
    collector_mod.collect_all.side_effect = RuntimeError("no metrics")
    metrics = asyncio.run(_run_query(query))
    assert metrics == []


def test_graphql_health_happy_path(graphql_module):
    query, _, _, _, health_mod, *_ = graphql_module
    health = asyncio.run(_run_health(query))
    assert health.status == "healthy"
    assert health.database == "healthy"  # noqa: F841  # Variable for test verification


def test_graphql_health_exception(graphql_module):
    query, _, _, _, health_mod, *_ = graphql_module
    health_mod.check_all_modules_health.side_effect = RuntimeError("health down")
    health = asyncio.run(_run_health(query))
    assert health.status == "unhealthy"


def test_graphql_create_alert_happy_path(graphql_module):
    _, mutation, alert_mod, *_ = graphql_module
    now = datetime.now(timezone.utc)
    alert_mod.alert_service.create_alert = AsyncMock(
        return_value={
            "id": "a-2",
            "severity": "high",
            "message": "msg",
            "source": "src",
            "created_at": now,
            "status": "active",
        }
    )
    alert = asyncio.run(_run_create(mutation, "high", "msg", "src"))
    assert alert.id == "a-2"


def test_graphql_create_alert_exception(graphql_module):
    _, mutation, alert_mod, *_ = graphql_module
    alert_mod.alert_service.create_alert = AsyncMock(side_effect=RuntimeError("create fail"))
    with pytest.raises(Exception):
        asyncio.run(_run_create(mutation, "high", "msg", "src"))


def test_graphql_acknowledge_alert_happy_path(graphql_module):
    _, mutation, _, _, _, engine_mod = graphql_module
    engine_mod.acknowledge_alert = AsyncMock(return_value=True)
    alert = asyncio.run(_run_ack(mutation, "a-1"))
    assert alert.id == "a-1"
    assert alert.status == "acknowledged"


def test_graphql_acknowledge_alert_not_found(graphql_module):
    _, mutation, _, _, _, engine_mod = graphql_module
    engine_mod.acknowledge_alert = AsyncMock(return_value=False)
    with pytest.raises(Exception, match="Failed to acknowledge alert"):
        asyncio.run(_run_ack(mutation, "missing"))
