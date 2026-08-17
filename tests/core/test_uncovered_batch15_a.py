# -*- coding: utf-8 -*-
"""Functional coverage tests for core batch 15-a modules."""

import asyncio
import json
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from core.agent.coding_subagent import CodingSubAgent, create_coding_subagent_dispatcher
from core.api_response import APIResponse, api_response_middleware
from core.integration_monitoring_system import (
    Alert,
    AlertInstance,
    AlertSeverity,
    IntegrationMonitoringSystem,
    MetricData,
    MetricType,
    Monitor,
    MonitorStatus,
    get_integration_monitoring_system,
)
from core.l3l4_storage_integrator import (
    DataType,
    L3L4StorageIntegrator,
    StorageBackend,
    StoragePolicy,
    StorageRequest,
    StorageResult,
    get_l3l4_storage_integrator,
)
from core.priority.sla_aware import (
    SLAAwareScheduler,
    SLARequirement,
    SLAViolation,
)

pytestmark = [pytest.mark.core]


# ---------------------------------------------------------------------------
# core.priority.sla_aware
# ---------------------------------------------------------------------------
def test_sla_aware_scheduler_lifecycle():
    now = datetime.now()
    scheduler = SLAAwareScheduler()

    req = SLARequirement(
        service="payment",
        response_time_target=0.5,
        availability_target=99.9,
        deadline=now + timedelta(hours=1),
        priority=2,
    )
    scheduler.register_sla(req)
    assert "payment" in scheduler.sla_requirements

    assert scheduler.check_sla_compliance("unknown", {"response_time": 1.0}) is True
    assert scheduler.check_sla_compliance("payment", {"response_time": 0.1}) is True
    assert scheduler.check_sla_compliance("payment", {"response_time": 1.0}) is False
    assert scheduler.check_sla_compliance("payment", {"availability": 99.0}) is False
    assert (
        scheduler.check_sla_compliance("payment", {"response_time": 0.2, "availability": 99.95})
        is True
    )

    tasks = [
        {"service": "payment", "name": "pay_task"},
        {"service": "logging", "name": "log_task"},
        {"service": "unknown", "name": "other"},
    ]
    scheduled = scheduler.schedule_tasks(tasks, current_time=now)
    assert scheduled[0]["service"] == "payment"
    assert "sla_score" in scheduled[0]
    assert scheduled[-1]["time_to_deadline"] is None

    violation = SLAViolation(
        service="payment",
        violation_type="response_time",
        severity="high",
        timestamp=now,
        impact=2.0,
    )
    scheduler.violations.append(violation)

    all_v = scheduler.get_violations()
    assert len(all_v) >= 1
    assert len(scheduler.get_violations(service="payment")) >= 1
    assert len(scheduler.get_violations(service="missing")) == 0
    assert len(scheduler.get_violations(since=now + timedelta(minutes=1))) == 0

    status = scheduler.get_sla_status("payment")
    assert status["compliance_status"] == "violated"
    assert status["recent_violations"] >= 1

    status_no = scheduler.get_sla_status("missing")
    assert status_no["status"] == "no_sla_defined"

    # Reset violations to test compliant status
    scheduler.violations.clear()
    status2 = scheduler.get_sla_status("payment")
    assert status2["compliance_status"] == "compliant"


# ---------------------------------------------------------------------------
# core.agent.coding_subagent
# ---------------------------------------------------------------------------
def test_coding_subagent_success_and_exception():
    tool_executor = MagicMock()
    tool_executor.execute_tool.return_value = {"ok": True}

    sub = CodingSubAgent(agent_id="c1", tool_executor=tool_executor)
    result = sub.run("goal", {"tool": "bash", "params": {"command": "ls"}}, ["bash"])
    assert result.status == "completed"
    assert result.result == {"ok": True}
    assert result.metadata["tool"] == "bash"

    tool_executor.execute_tool.side_effect = RuntimeError("boom")
    sub2 = CodingSubAgent(agent_id="c2", tool_executor=tool_executor)
    result2 = sub2.run("goal", {"tool": "read_file"}, ["read_file"])
    assert result2.status == "failed"
    assert "boom" in result2.error


def test_coding_subagent_terminated():
    sub = CodingSubAgent(agent_id="c3")
    sub._stop_event.set()
    result = sub.run("goal", {"tool": "bash"}, ["bash"])
    assert result.status == "terminated"


def test_create_coding_subagent_dispatcher():
    dispatcher = create_coding_subagent_dispatcher(max_workers=1)
    assert dispatcher.subagent_factory is CodingSubAgent
    dispatcher.shutdown(wait=False)


# ---------------------------------------------------------------------------
# core.api_response
# ---------------------------------------------------------------------------
def test_api_response_static_methods():
    success = APIResponse.success(data={"x": 1})
    assert success["success"] is True
    assert success["data"] == {"x": 1}
    assert "meta" not in success

    success_meta = APIResponse.success(data=[1, 2], meta={"page": 1})
    assert success_meta["meta"] == {"page": 1}

    err = APIResponse.error("ERR_1", "bad")
    assert err["success"] is False
    assert err["error"]["details"] is None

    err_det = APIResponse.error("ERR_2", "bad", details="detail", status_code=400)
    assert err_det["error"]["details"] == "detail"


@pytest.mark.asyncio
async def test_api_response_middleware_already_success():
    request = MagicMock()
    response = APIResponse.success(data=[1, 2])
    call_next = AsyncMock(return_value=json_response(response))
    out = await api_response_middleware(request, call_next)
    assert out is call_next.return_value
    assert b'"success"' in out.body


@pytest.mark.asyncio
async def test_api_response_middleware_wraps_json():
    request = MagicMock()
    call_next = AsyncMock(return_value=json_response({"foo": "bar"}))
    out = await api_response_middleware(request, call_next)
    assert out.status_code == 200
    payload = json.loads(out.body)
    assert payload["success"] is True
    assert payload["data"] == {"foo": "bar"}


@pytest.mark.asyncio
async def test_api_response_middleware_non_json_sets_header():
    from fastapi.responses import Response

    request = MagicMock()
    call_next = AsyncMock(return_value=Response(content="plain"))
    out = await api_response_middleware(request, call_next)
    assert out.headers["X-Process-Time"] is not None


@pytest.mark.asyncio
async def test_api_response_middleware_json_parse_error(monkeypatch):
    request = MagicMock()
    original = json.loads
    monkeypatch.setattr(json, "loads", MagicMock(side_effect=ValueError("bad")))
    try:
        call_next = AsyncMock(return_value=json_response({"foo": "bar"}))
        out = await api_response_middleware(request, call_next)
        assert out is call_next.return_value
    finally:
        monkeypatch.undo()


def json_response(content):
    from fastapi.responses import JSONResponse

    return JSONResponse(content=content)


# ---------------------------------------------------------------------------
# core.integration_monitoring_system
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_integration_monitoring_system_lifecycle():
    system = IntegrationMonitoringSystem(config={"data_retention_hours": 1})
    assert system.config is not None
    assert len(system.monitors) > 0
    assert len(system.alerts) > 0

    # Register custom monitor and alert
    custom_monitor = Monitor(
        monitor_id="eq_mon",
        monitor_name="Equal Monitor",
        metric_type=MetricType.GAUGE,
        target="eq.target",
        threshold=5.0,
        comparison="equal_to",
    )
    custom_alert = Alert(
        alert_id="eq_alert",
        alert_name="Equal Alert",
        monitor_id="eq_mon",
        severity=AlertSeverity.WARNING,
        condition="value == 5",
    )
    system.register_monitor(custom_monitor)
    system.register_alert(custom_alert)

    # Record metric triggering less_than alert
    await system.record_metric("integration.health", 0.0)
    # Record metric triggering greater_than alert
    await system.record_metric("system.cpu.usage", 99.0)
    # Record metric triggering equal_to alert
    await system.record_metric("eq.target", 5.0)
    # Record a healthy metric
    await system.record_metric("system.memory.usage", 10.0)

    # Prune old data
    old = MetricData(
        metric_id="cpu",
        value=50.0,
        timestamp=datetime.now(timezone.utc) - timedelta(hours=2),
    )
    system.metrics["cpu"] = [old]
    await system.record_metric("cpu", 1.0)
    assert all(
        m.timestamp > datetime.now(timezone.utc) - timedelta(hours=1) for m in system.metrics["cpu"]
    )

    # Queries and filters
    cpu_metrics = system.get_metrics("system.cpu.usage")
    assert len(cpu_metrics) >= 1
    assert "value" in cpu_metrics[0]

    alerts = system.get_alerts()
    assert len(alerts) >= 1
    assert system.get_alerts(status="resolved") == []
    assert len(system.get_alerts(severity=AlertSeverity.WARNING)) >= 1

    # Resolve a triggered alert
    instance_id = system.alert_instances[0].alert_instance_id
    assert await system.resolve_alert(instance_id) is True
    assert await system.resolve_alert("missing") is False

    stats = system.get_statistics()
    assert stats["total_monitors"] == len(system.monitors)
    assert stats["total_metrics"] > 0

    # Factory
    assert isinstance(get_integration_monitoring_system(), IntegrationMonitoringSystem)


@pytest.mark.asyncio
async def test_integration_monitoring_system_notifications_and_collection(monkeypatch):
    system = IntegrationMonitoringSystem()
    calls = []

    def sync_handler(alert, instance):
        calls.append(("sync", alert.alert_id))

    async def async_handler(alert, instance):
        calls.append(("async", alert.alert_id))

    def bad_handler(alert, instance):
        raise ValueError("notify fail")

    system.register_notification_handler(sync_handler)
    system.register_notification_handler(async_handler)
    system.register_notification_handler(bad_handler)

    await system.record_metric("system.cpu.usage", 99.0)
    assert any(c[0] == "sync" for c in calls)
    assert any(c[0] == "async" for c in calls)

    # _collect_metrics directly
    await system._collect_metrics()
    assert system.total_metrics > 0

    # start_monitoring + cancel
    created_tasks = []
    original_create_task = asyncio.create_task

    def patched_create_task(coro, *, name=None):
        task = original_create_task(coro, name=name)
        created_tasks.append(task)
        return task

    monkeypatch.setattr(asyncio, "create_task", patched_create_task)
    monkeypatch.setattr(system, "_collect_metrics", AsyncMock())
    await system.start_monitoring()
    assert len(created_tasks) == 1
    await asyncio.sleep(0)
    created_tasks[0].cancel()
    try:
        await created_tasks[0]
    except asyncio.CancelledError:
        pass

    assert system._collect_metrics.called


# ---------------------------------------------------------------------------
# core.l3l4_storage_integrator
# ---------------------------------------------------------------------------
def _mock_adapter(store_value=None, retrieve_value=None, delete_value=True, query_value=None):
    adapter = MagicMock()
    if store_value is not None:
        adapter.store = AsyncMock(return_value=store_value)
    else:
        adapter.store = AsyncMock(
            return_value=StorageResult(
                success=True, backend=StorageBackend.POSTGRESQL, data_id="pg"
            )
        )
    if retrieve_value is not None:
        adapter.retrieve = AsyncMock(return_value=retrieve_value)
    else:
        adapter.retrieve = AsyncMock(return_value={"data": "value"})
    adapter.delete = AsyncMock(return_value=delete_value)
    adapter.query = AsyncMock(return_value=query_value if query_value is not None else [{"row": 1}])
    return adapter


@pytest.mark.asyncio
async def test_l3l4_storage_integrator_factory_and_policies():
    integrator = get_l3l4_storage_integrator({"cache_enabled": True, "cache_ttl": 60})
    assert isinstance(integrator, L3L4StorageIntegrator)

    # Default policies and empty adapters
    policy = integrator.get_storage_policy(DataType.METRICS)
    assert policy is not None
    assert policy.primary_backend == StorageBackend.VICTORIAMETRICS

    stats = integrator.get_storage_statistics()
    assert "data_type_stats" in stats
    assert stats["registered_policies"] == len(integrator.storage_policies)
    assert stats["cache_enabled"] is True

    # _create_backend_adapter always returns None
    assert integrator._create_backend_adapter(StorageBackend.POSTGRESQL) is None

    # Exception path in _initialize_backend_adapters
    original = L3L4StorageIntegrator._create_backend_adapter
    L3L4StorageIntegrator._create_backend_adapter = lambda self, backend: (_ for _ in ()).throw(
        ValueError("boom")
    )
    try:
        broken = L3L4StorageIntegrator()
        assert broken.backend_adapters == {}
    finally:
        L3L4StorageIntegrator._create_backend_adapter = original

    # Register custom policy
    custom = integrator.storage_policies[DataType.ALERTS]
    integrator.register_storage_policy(custom)
    assert integrator.get_storage_policy(DataType.ALERTS) is custom


@pytest.mark.asyncio
async def test_l3l4_storage_integrator_operations(monkeypatch):
    integrator = L3L4StorageIntegrator()

    pg = _mock_adapter(
        store_value=StorageResult(success=True, backend=StorageBackend.POSTGRESQL, data_id="pg")
    )
    redis = _mock_adapter(
        store_value=StorageResult(success=True, backend=StorageBackend.REDIS, data_id="redis")
    )
    none_adapter = _mock_adapter(
        store_value=StorageResult(success=False, backend=StorageBackend.VICTORIAMETRICS)
    )

    integrator.backend_adapters[StorageBackend.POSTGRESQL] = pg
    integrator.backend_adapters[StorageBackend.REDIS] = redis
    integrator.backend_adapters[StorageBackend.VICTORIAMETRICS] = none_adapter

    # Store primary success with secondary async
    request = StorageRequest(data_type=DataType.ALERTS, data={"msg": "alert"})
    created = []
    original_create_task = asyncio.create_task

    def patched_create_task(coro, *, name=None):
        task = original_create_task(coro, name=name)
        created.append(task)
        return task

    monkeypatch.setattr(asyncio, "create_task", patched_create_task)
    try:
        result = await integrator.store_data(request)
        assert result.success is True
        assert result.backend == StorageBackend.POSTGRESQL
        if created:
            await asyncio.gather(*created, return_exceptions=True)
    finally:
        monkeypatch.undo()

    # Primary failure falls back to secondary
    pg.store = AsyncMock(
        return_value=StorageResult(success=False, backend=StorageBackend.POSTGRESQL)
    )
    result2 = await integrator.store_data(request)
    assert result2.success is True
    assert result2.backend == StorageBackend.REDIS

    # All fail
    redis.store = AsyncMock(return_value=StorageResult(success=False, backend=StorageBackend.REDIS))
    result3 = await integrator.store_data(request)
    assert result3.success is False

    # Exception during primary
    pg.store = AsyncMock(side_effect=RuntimeError("connection lost"))
    result4 = await integrator.store_data(request)
    assert result4.success is False
    assert "connection lost" in str(result4.error)

    # No adapter for primary and secondaries
    other = StorageRequest(
        data_type=DataType.METRICS,
        data={"x": 1},
        policy=StoragePolicy(
            data_type=DataType.METRICS,
            primary_backend=StorageBackend.TEMPO,
            secondary_backends=[],
        ),
    )
    result5 = await integrator.store_data(other)
    assert result5.success is False
    assert "not available" in str(result5.error)

    # Cache hit on retrieve
    monkeypatch.setattr(
        integrator, "_retrieve_from_cache", AsyncMock(return_value={"cached": True})
    )
    cached = await integrator.retrieve_data("id1", DataType.ALERTS)
    assert cached == {"cached": True}
    assert integrator.storage_stats["alerts"]["cache_hits"] >= 1
    monkeypatch.undo()

    # Cache miss + retrieve from primary
    got = await integrator.retrieve_data("id2", DataType.ALERTS)
    assert got == {"data": "value"}
    assert integrator.storage_stats["alerts"]["cache_misses"] >= 1

    # Fallback to secondary when primary adapter missing
    integrator.backend_adapters.pop(StorageBackend.POSTGRESQL, None)
    redis.retrieve = AsyncMock(return_value={"from": "redis"})
    got2 = await integrator.retrieve_data("id3", DataType.ALERTS)
    assert got2 == {"from": "redis"}

    # No adapter at all
    integrator.backend_adapters.pop(StorageBackend.REDIS, None)
    assert await integrator.retrieve_data("id4", DataType.ALERTS) is None

    # Query with backend
    integrator.backend_adapters[StorageBackend.POSTGRESQL] = pg
    pg.query = AsyncMock(return_value=[{"q": 1}])
    rows = await integrator.query_data({"x": 1}, DataType.ALERTS)
    assert rows == [{"q": 1}]

    # Query no adapter
    integrator.backend_adapters.pop(StorageBackend.VICTORIAMETRICS, None)
    assert await integrator.query_data({"x": 1}, DataType.METRICS) == []

    # Delete
    integrator.backend_adapters[StorageBackend.POSTGRESQL] = pg
    integrator.backend_adapters[StorageBackend.REDIS] = redis
    pg.delete = AsyncMock(return_value=True)
    redis.delete = AsyncMock(return_value=False)
    assert await integrator.delete_data("id5", DataType.ALERTS) is True

    # Delete no policy
    integrator.storage_policies.pop(DataType.METRICS, None)
    assert await integrator.delete_data("id6", DataType.METRICS) is False
