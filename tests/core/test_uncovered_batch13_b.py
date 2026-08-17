# -*- coding: utf-8 -*-
"""Functional coverage tests for batch13_b core modules."""

import asyncio
import base64
import types
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from fastapi.responses import JSONResponse

from core.abac import Subject
from core.base.collector import (
    BaseCollector,
    Collector,
    collect_with_post_processing,
)
from core.escalation import (
    escalate_rollback_failure_sync,
    notify_rollback_failure,
)
from core.l2l3_workflow_integrator import (
    L2L3WorkflowIntegrator,
    WorkflowDefinition,
    WorkflowExecution,
    WorkflowStatus,
    WorkflowTriggerType,
    get_l2l3_workflow_integrator,
)
from core.third_party_service_integrator import (
    ServiceConfig,
    ServiceConnection,
    ServiceStatus,
    ServiceType,
    ThirdPartyServiceIntegrator,
    get_third_party_service_integrator,
)
from core.unified_access_control import (
    AccessControlPolicy,
    AccessRule,
    UnifiedAccessControl,
    add_access_control_middleware,
    require_permission,
    setup_default_access_policies,
)

pytestmark = [pytest.mark.core]


# ---------------------------------------------------------------------------
# core.base.collector
# ---------------------------------------------------------------------------
@pytest.fixture
def fake_telemetry(monkeypatch):
    """Provide fake OpenTelemetry helpers for the base collector."""
    meter = MagicMock()
    meter.create_counter = MagicMock(return_value=MagicMock())
    meter.create_histogram = MagicMock(return_value=MagicMock())

    class FakeSpan:
        def set_attribute(self, key, value):
            pass

        def record_exception(self, exc):
            pass

    class _FakeSpanContext:
        def __enter__(self):
            return FakeSpan()

        def __exit__(self, exc_type, exc, tb):
            return False

    class FakeTracer:
        def start_as_current_span(self, name):
            return _FakeSpanContext()

    monkeypatch.setattr("core.telemetry.get_meter", MagicMock(return_value=meter))
    monkeypatch.setattr("core.telemetry.get_tracer", MagicMock(return_value=FakeTracer()))
    return {"meter": meter}


def test_collector_init_status_and_validate(fake_telemetry):
    c = Collector("test-collector", {"host": "localhost"})
    assert c.name == "test-collector"
    assert c.config == {"host": "localhost"}
    assert c._is_initialized is False

    status = c.get_status()
    assert status["name"] == "test-collector"
    assert status["initialized"] is False
    assert status["running"] is False

    assert c.validate_config(["host"]) is True
    assert c.validate_config(["host", "missing"]) is False
    assert c.validate_config([]) is True


def test_collector_context_manager(fake_telemetry):
    with Collector("cm") as c:
        assert c._is_initialized is True
    assert c._is_running is False


@pytest.mark.asyncio
async def test_collect_with_tracing_success(fake_telemetry):
    c = Collector("t1")
    c.collect = AsyncMock(return_value={"ok": True})
    result = await c.collect_with_tracing()
    assert result == {"ok": True}


@pytest.mark.asyncio
async def test_collect_with_tracing_without_tracer(fake_telemetry):
    c = Collector("t2")
    c._tracer = None
    c.collect = AsyncMock(return_value={"payload": 1})
    result = await c.collect_with_tracing()
    assert result == {"payload": 1}


@pytest.mark.asyncio
async def test_collect_with_tracing_exception(fake_telemetry):
    c = Collector("t3")
    c.collect = AsyncMock(side_effect=RuntimeError("boom"))
    with pytest.raises(RuntimeError, match="boom"):
        await c.collect_with_tracing()


def test_init_telemetry_exception(monkeypatch):
    monkeypatch.setattr(
        "core.telemetry.get_meter",
        MagicMock(side_effect=RuntimeError("meter down")),
    )
    monkeypatch.setattr(
        "core.telemetry.get_tracer",
        MagicMock(side_effect=RuntimeError("tracer down")),
    )
    c = Collector("telem-err")
    assert c._tracer is None
    assert c._meter is None


def test_collect_with_post_processing_success():
    def collect_func(host_cfg):
        return {"host": host_cfg.get("host"), "value": 42}

    result = collect_with_post_processing(
        collect_func,
        {"host": "h1"},
        "platform",
        max_failures=3,
        cooldown_sec=5,
        metric_type="metrics",
    )
    assert result["host"] == "h1"
    assert result["value"] == 42


def test_collect_with_post_processing_default_host():
    result = collect_with_post_processing(
        lambda _: {"ok": True},
        {},
        "p",
        max_failures=1,
        cooldown_sec=1,
    )
    assert result == {"ok": True}


def test_collect_with_post_processing_collect_exception():
    def fail(_):
        raise RuntimeError("collect failed")

    result = collect_with_post_processing(fail, {"host": "h1"}, "p", max_failures=1, cooldown_sec=1)
    assert result == {}


def test_collect_with_post_processing_loki_exception(monkeypatch):
    monkeypatch.setattr("core.loki_sink.push_to_loki", MagicMock(side_effect=RuntimeError("x")))

    def collect_func(_):
        return {"data": 1}

    result = collect_with_post_processing(
        collect_func, {"host": "h1"}, "p", max_failures=1, cooldown_sec=1
    )
    assert result == {"data": 1}


def test_collect_with_post_processing_stats_exception(monkeypatch):
    monkeypatch.setattr(
        "core.stats_engine.record_collect", MagicMock(side_effect=RuntimeError("x"))
    )

    def collect_func(_):
        return {"data": 2}

    result = collect_with_post_processing(
        collect_func, {"host": "h1"}, "p", max_failures=1, cooldown_sec=1
    )
    assert result == {"data": 2}


def test_collect_with_post_processing_guard_exception(monkeypatch):
    monkeypatch.setattr(
        "core.command_guard.register_self_pid",
        MagicMock(side_effect=RuntimeError("x")),
    )

    def collect_func(_):
        return {"data": 3}

    result = collect_with_post_processing(
        collect_func, {"host": "h1"}, "p", max_failures=1, cooldown_sec=1
    )
    assert result == {"data": 3}


# ---------------------------------------------------------------------------
# core.third_party_service_integrator
# ---------------------------------------------------------------------------
class _FakeHttpxResponse:
    def __init__(self, status_code=200, text="", json_data=None, exc=None):
        self.status_code = status_code
        self.text = text
        self._json = json_data
        self._exc = exc

    def raise_for_status(self):
        if self._exc:
            raise self._exc

    def json(self):
        return self._json


def _fake_httpx_client(get_resp=None, put_resp=None, post_resp=None, get_side_effect=None):
    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            if get_side_effect is not None:
                self.get = AsyncMock(side_effect=get_side_effect)
            else:
                self.get = AsyncMock(return_value=get_resp)
            self.put = AsyncMock(return_value=put_resp)
            self.post = AsyncMock(return_value=post_resp)

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args, **kwargs):
            return None

        async def aclose(self):
            pass

        async def close(self):
            pass

    return FakeAsyncClient


def _fake_neo4j_factory():
    class FakeRecord:
        def __init__(self, data):
            self._data = data

        def data(self):
            return self._data

    class FakeResult:
        def __init__(self, records):
            self._records = iter(records)

        def __aiter__(self):
            return self

        async def __anext__(self):
            try:
                return next(self._records)
            except StopIteration:
                raise StopAsyncIteration

    class FakeSession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args, **kwargs):
            return None

        async def run(self, query, parameters):
            return FakeResult([FakeRecord({"node": 1})])

    class FakeDriver:
        def session(self, database=None):
            return FakeSession()

    return types.SimpleNamespace(driver=lambda uri, auth=None: FakeDriver())


@pytest.fixture
def integrator():
    return ThirdPartyServiceIntegrator({"health_check_enabled": False})


@pytest.mark.asyncio
async def test_connect_consul_and_kv(integrator, monkeypatch):
    leader_resp = _FakeHttpxResponse(status_code=200, text='"leader"')
    kv_resp = _FakeHttpxResponse(
        status_code=200,
        json_data=[{"Value": base64.b64encode(b"hello").decode()}],
    )
    missing_resp = _FakeHttpxResponse(status_code=200, json_data=[])
    not_found = _FakeHttpxResponse(status_code=404)
    put_true = _FakeHttpxResponse(status_code=200, text="true")

    def get_side_effect(url, *args, **kwargs):
        if url == "/v1/status/leader":
            return leader_resp
        if url == "/v1/kv/mykey":
            return kv_resp
        if url == "/v1/kv/missing":
            return missing_resp
        if url == "/v1/kv/other":
            return not_found
        return _FakeHttpxResponse(status_code=404)

    monkeypatch.setattr(
        "httpx.AsyncClient",
        _fake_httpx_client(put_resp=put_true, get_side_effect=get_side_effect),
    )

    cfg = ServiceConfig(
        service_type=ServiceType.CONSUL,
        host="localhost",
        port=8500,
    )
    sid = await integrator.connect_service(cfg)
    assert sid == "consul_localhost_8500"
    assert integrator.service_connections[sid].status == ServiceStatus.CONNECTED

    value = await integrator.consul_get_kv(sid, "mykey")
    assert value == "hello"

    ok = await integrator.consul_put_kv(sid, "mykey", "value")
    assert ok is True

    assert await integrator.consul_get_kv(sid, "missing") is None
    assert await integrator.consul_get_kv(sid, "other") is None


@pytest.mark.asyncio
async def test_connect_neo4j_and_query(integrator, monkeypatch):
    monkeypatch.setattr("core.third_party_service_integrator.NEO4J_AVAILABLE", True)
    monkeypatch.setattr(
        "core.third_party_service_integrator.AsyncGraphDatabase",
        _fake_neo4j_factory(),
    )

    cfg = ServiceConfig(
        service_type=ServiceType.NEO4J,
        host="localhost",
        port=7687,
        username="neo4j",
        password="secret",
        database="neo4j",
    )
    sid = await integrator.connect_service(cfg)
    assert integrator.service_connections[sid].status == ServiceStatus.CONNECTED

    results = await integrator.execute_neo4j_query(sid, "MATCH (n) RETURN n")
    assert results == [{"node": 1}]


@pytest.mark.asyncio
async def test_neo4j_unavailable(integrator, monkeypatch):
    monkeypatch.setattr("core.third_party_service_integrator.NEO4J_AVAILABLE", False)
    cfg = ServiceConfig(service_type=ServiceType.NEO4J, host="localhost", port=7687)
    sid = await integrator.connect_service(cfg)
    assert integrator.service_connections[sid].status == ServiceStatus.ERROR

    with pytest.raises(RuntimeError, match="neo4j driver not installed"):
        await integrator.execute_neo4j_query(sid, "RETURN 1")


@pytest.mark.asyncio
async def test_unsupported_service(integrator):
    cfg = ServiceConfig(service_type=ServiceType.REDIS, host="localhost", port=6379)
    sid = await integrator.connect_service(cfg)
    assert integrator.service_connections[sid].status == ServiceStatus.ERROR
    assert "Unsupported" in integrator.service_connections[sid].error_message


@pytest.mark.asyncio
async def test_disconnect_and_close_variants(integrator, monkeypatch):
    leader_resp = _FakeHttpxResponse(status_code=200)
    monkeypatch.setattr(
        "httpx.AsyncClient",
        _fake_httpx_client(get_resp=leader_resp),
    )
    cfg = ServiceConfig(service_type=ServiceType.CONSUL, host="localhost", port=8500)
    sid = await integrator.connect_service(cfg)

    assert await integrator.disconnect_service(sid) is True
    assert integrator.active_connections == 0

    assert await integrator.disconnect_service("missing") is False

    # client with no aclose should use close
    close_mock = AsyncMock()
    integrator.service_clients["close_only"] = types.SimpleNamespace(
        close=close_mock,
    )
    integrator.service_connections["close_only"] = ServiceConnection(
        service_id="close_only",
        service_type=ServiceType.CONSUL,
        status=ServiceStatus.CONNECTED,
    )
    await integrator._close_service_client("close_only")
    assert close_mock.called

    integrator.service_clients["broken"] = types.SimpleNamespace(
        aclose=AsyncMock(side_effect=RuntimeError("x"))
    )
    integrator.service_connections["broken"] = ServiceConnection(
        service_id="broken",
        service_type=ServiceType.CONSUL,
        status=ServiceStatus.CONNECTED,
    )
    integrator.active_connections = 1
    assert await integrator.disconnect_service("broken") is False


@pytest.mark.asyncio
async def test_consul_register_service(integrator, monkeypatch):
    leader_resp = _FakeHttpxResponse(status_code=200)
    ok_resp = _FakeHttpxResponse(status_code=200)
    monkeypatch.setattr(
        "httpx.AsyncClient",
        _fake_httpx_client(get_resp=leader_resp, put_resp=ok_resp),
    )
    cfg = ServiceConfig(service_type=ServiceType.CONSUL, host="localhost", port=8500)
    sid = await integrator.connect_service(cfg)

    ok = await integrator.consul_register_service(
        sid, "svc", "127.0.0.1", 8080, check_config={"TTL": "10s"}
    )
    assert ok is True


@pytest.mark.asyncio
async def test_health_check_and_status(integrator, monkeypatch):
    assert await integrator.health_check("missing") == {
        "service_id": "missing",
        "status": "unknown",
        "error": "Service not found",
    }

    leader_resp = _FakeHttpxResponse(status_code=200)
    monkeypatch.setattr(
        "httpx.AsyncClient",
        _fake_httpx_client(get_resp=leader_resp),
    )
    cfg = ServiceConfig(service_type=ServiceType.CONSUL, host="localhost", port=8500)
    sid = await integrator.connect_service(cfg)

    hc = await integrator.health_check(sid)
    assert hc["healthy"] is True
    assert hc["status"] == "connected"

    status = integrator.get_service_status(sid)
    assert status["service_id"] == sid
    assert status["service_type"] == "consul"

    services = integrator.list_services()
    assert len(services) == 1

    stats = integrator.get_statistics()
    assert stats["health_check_enabled"] is False
    assert stats["connected_services"] == 1


@pytest.mark.asyncio
async def test_start_health_check_loop(integrator, monkeypatch):
    integrator.health_check_enabled = False
    await integrator.start_health_check_loop()

    integrator.health_check_enabled = True
    monkeypatch.setattr(
        "core.third_party_service_integrator.asyncio.create_task",
        MagicMock(return_value=MagicMock()),
    )
    await integrator.start_health_check_loop()


def test_factory_third_party():
    inst = get_third_party_service_integrator({})
    assert isinstance(inst, ThirdPartyServiceIntegrator)


# ---------------------------------------------------------------------------
# core.unified_access_control
# ---------------------------------------------------------------------------
@pytest.fixture
def uac():
    return UnifiedAccessControl()


def test_add_remove_rules_and_priority(uac):
    r1 = AccessRule(
        id="r1",
        name="low",
        policy=AccessControlPolicy.ALLOW,
        resources=["metrics"],
        actions=["read"],
        roles=["viewer"],
        priority=10,
    )
    r2 = AccessRule(
        id="r2",
        name="high",
        policy=AccessControlPolicy.DENY,
        resources=["*"],
        actions=["*"],
        roles=["admin"],
        priority=100,
    )
    uac.add_access_rule(r1)
    uac.add_access_rule(r2)
    assert uac.access_rules[0].id == "r2"

    uac.remove_access_rule("r1")
    assert len(uac.access_rules) == 1


def test_check_access_allow_and_cache(uac):
    uac.add_access_rule(
        AccessRule(
            id="allow",
            name="allow",
            policy=AccessControlPolicy.ALLOW,
            resources=["metrics"],
            actions=["read"],
            roles=["viewer"],
        )
    )
    subject = Subject("u1", "user", {}, {"viewer"}, set())
    assert uac.check_access(subject, "metrics", "read") is True
    # cache hit next time
    assert uac.check_access(subject, "metrics", "read") is True


def test_check_access_deny(uac):
    uac.add_access_rule(
        AccessRule(
            id="deny",
            name="deny",
            policy=AccessControlPolicy.DENY,
            resources=["metrics"],
            actions=["read"],
            roles=["deny"],
        )
    )
    subject = Subject("u2", "user", {}, {"deny"}, set())
    assert uac.check_access(subject, "metrics", "read") is False


def test_check_access_conditions_mismatch(uac):
    uac.add_access_rule(
        AccessRule(
            id="cond",
            name="cond",
            policy=AccessControlPolicy.ALLOW,
            resources=["metrics"],
            actions=["read"],
            roles=["viewer"],
            conditions={"dept": "ops"},
        )
    )
    subject = Subject("u3", "user", {"dept": "dev"}, {"viewer"}, set())
    assert uac.check_access(subject, "metrics", "read") is False

    subject_ok = Subject("u4", "user", {"dept": "ops"}, {"viewer"}, set())
    assert uac.check_access(subject_ok, "metrics", "read") is True


def test_check_access_abac_engine(uac):
    uac.abac_engine = MagicMock(evaluate=MagicMock(return_value=True))
    subject = Subject("u5", "user", {}, set(), set())
    assert uac.check_access(subject, "workflow", "execute") is True
    uac.abac_engine.evaluate.assert_called_once()


def test_check_access_abac_default_deny(uac):
    subject = Subject("u6", "user", {}, set(), set())
    assert uac.check_access(subject, "service", "read") is False


def test_audit_log_and_stats(uac):
    uac.add_access_rule(
        AccessRule(
            id="audit",
            name="audit",
            policy=AccessControlPolicy.ALLOW,
            resources=["metrics"],
            actions=["read"],
            roles=["user"],
        )
    )
    subject = Subject("u7", "user", {}, {"user"}, set())
    uac.check_access(subject, "metrics", "read")
    uac.check_access(subject, "metrics", "write")

    assert len(uac.get_audit_log(1)) == 1
    stats = uac.get_access_stats()
    assert stats["total_decisions"] == 2
    assert stats["granted"] == 1
    assert stats["denied"] == 1
    assert stats["grant_rate"] == 0.5


def test_audit_log_truncation(uac):
    subj = Subject("u", "user", {}, set(), set())
    for _ in range(10001):
        uac._log_access_decision(subj, "r", "a", True, "rule")
    assert len(uac.audit_log) == 5000


@pytest.mark.asyncio
async def test_require_permission(monkeypatch):
    mock_uac = MagicMock()
    mock_uac.check_access = MagicMock(return_value=True)
    monkeypatch.setattr("core.unified_access_control.unified_access_control", mock_uac)

    dep = require_permission("service", "read")
    request = types.SimpleNamespace(
        state=types.SimpleNamespace(user={"id": "u", "type": "user", "roles": ["admin"]})
    )
    assert await dep.dependency(request) is True

    mock_uac.check_access.return_value = False
    with pytest.raises(HTTPException) as exc_info:
        await dep.dependency(request)
    assert exc_info.value.status_code == 403

    anon = types.SimpleNamespace(state=types.SimpleNamespace())
    with pytest.raises(HTTPException) as exc_info:
        await dep.dependency(anon)
    assert exc_info.value.status_code == 401


def test_setup_default_access_policies(monkeypatch):
    fresh = UnifiedAccessControl()
    monkeypatch.setattr("core.unified_access_control.unified_access_control", fresh)
    result = setup_default_access_policies()
    assert result["status"] == "success"
    assert result["rules_added"] == 3

    result2 = setup_default_access_policies()
    assert result2["status"] == "already_initialized"


@pytest.mark.asyncio
async def test_add_access_control_middleware(monkeypatch):
    monkeypatch.setenv("AIOPS_ENFORCE_ABAC", "true")
    mock_uac = MagicMock()
    mock_uac.check_access = MagicMock(return_value=True)
    monkeypatch.setattr("core.unified_access_control.unified_access_control", mock_uac)

    app = MagicMock()
    captured = []

    def capture_middleware(typ):
        def decorator(fn):
            captured.append(fn)
            return fn

        return decorator

    app.middleware = capture_middleware
    add_access_control_middleware(app)
    assert len(captured) == 1
    middleware = captured[0]

    call_next = AsyncMock(return_value=JSONResponse({"ok": 1}))

    # OPTIONS should skip
    req = types.SimpleNamespace(
        method="OPTIONS",
        state=types.SimpleNamespace(user={"id": "u", "type": "user", "roles": ["admin"]}),
    )
    resp = await middleware(req, call_next)
    assert resp.status_code == 200

    # allowed
    req = types.SimpleNamespace(
        method="GET",
        state=types.SimpleNamespace(user={"id": "u", "type": "user", "roles": ["admin"]}),
    )
    resp = await middleware(req, call_next)
    assert resp.status_code == 200

    # denied
    mock_uac.check_access.return_value = False
    resp = await middleware(req, call_next)
    assert resp.status_code == 403

    # unauthenticated
    req = types.SimpleNamespace(method="GET", state=types.SimpleNamespace())
    resp = await middleware(req, call_next)
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_access_control_middleware_not_enforced(monkeypatch):
    monkeypatch.setenv("AIOPS_ENFORCE_ABAC", "false")
    app = MagicMock()
    captured = []

    def capture_middleware(typ):
        def decorator(fn):
            captured.append(fn)
            return fn

        return decorator

    app.middleware = capture_middleware
    add_access_control_middleware(app)
    middleware = captured[0]

    call_next = AsyncMock(return_value=JSONResponse({"ok": 1}))
    req = types.SimpleNamespace(method="GET", state=types.SimpleNamespace())
    resp = await middleware(req, call_next)
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# core.l2l3_workflow_integrator
# ---------------------------------------------------------------------------
@pytest.fixture
def workflow_integrator():
    return L2L3WorkflowIntegrator()


def test_register_workflow_and_handler(workflow_integrator):
    wf = WorkflowDefinition(
        workflow_id="wf1",
        name="test",
        description="d",
        trigger_type=WorkflowTriggerType.MANUAL,
    )
    workflow_integrator.register_workflow(wf)
    assert "wf1" in workflow_integrator.workflows

    workflow_integrator.register_trigger_handler(WorkflowTriggerType.MANUAL, lambda: None)
    assert WorkflowTriggerType.MANUAL in workflow_integrator.trigger_handlers


@pytest.mark.asyncio
async def test_trigger_workflow_and_unknown(workflow_integrator):
    wf = WorkflowDefinition(
        workflow_id="wf2",
        name="t",
        description="d",
        trigger_type=WorkflowTriggerType.MANUAL,
    )
    workflow_integrator.register_workflow(wf)

    with pytest.raises(ValueError, match="Workflow not found"):
        await workflow_integrator.trigger_workflow("missing")

    execution_id = await workflow_integrator.trigger_workflow("wf2")
    assert execution_id
    assert execution_id in workflow_integrator.active_executions
    await asyncio.sleep(0.01)
    assert execution_id in [e.execution_id for e in workflow_integrator.execution_history]


@pytest.mark.asyncio
async def test_execute_workflow_all_steps(workflow_integrator):
    wf = WorkflowDefinition(
        workflow_id="wf3",
        name="all",
        description="d",
        trigger_type=WorkflowTriggerType.MANUAL,
        steps=[
            {"type": "causal_analysis", "config": {}},
            {"type": "workflow_execution", "config": {"workflow_name": "x"}},
            {"type": "data_processing", "config": {"processing_type": "filter", "data": [1, 2]}},
            {"type": "notification", "config": {"notification_type": "email", "recipients": ["a"]}},
            {"type": "unknown_type", "config": {}},
        ],
    )
    workflow_integrator.register_workflow(wf)
    execution = WorkflowExecution(
        execution_id="e1",
        workflow_id="wf3",
        metadata={
            "trigger_data": {
                "metrics_data": {"cpu": [1, 2]},
                "target_variable": "cpu",
            }
        },
    )
    workflow_integrator.active_executions["e1"] = execution

    class CausalResult:
        root_causes = ["cpu"]
        confidence = 0.9
        impact_scores = {"cpu": 0.9}

    workflow_integrator.causal_analyzer = MagicMock()
    workflow_integrator.causal_analyzer.analyze_causal_relationships = AsyncMock(
        return_value=CausalResult()
    )
    workflow_integrator.workflow_engine = MagicMock()

    await workflow_integrator._execute_workflow("e1")
    assert execution.status == WorkflowStatus.COMPLETED
    assert "step_0" in execution.results
    assert workflow_integrator.successful_executions == 1
    assert execution in workflow_integrator.execution_history

    status = workflow_integrator.get_execution_status("e1")
    assert status["status"] == "completed"


@pytest.mark.asyncio
async def test_causal_analysis_step_branches(workflow_integrator):
    workflow_integrator.causal_analyzer = None
    execution = WorkflowExecution("e2", "wf")

    # no analyzer
    res = await workflow_integrator._execute_causal_analysis_step({}, execution)
    assert res["reason"] == "causal_analyzer_not_available"

    # missing data
    workflow_integrator.causal_analyzer = MagicMock()
    res = await workflow_integrator._execute_causal_analysis_step({}, execution)
    assert res["reason"] == "missing_required_data"

    # success
    execution.metadata = {
        "trigger_data": {
            "metrics_data": {"cpu": [1]},
            "target_variable": "cpu",
        }
    }

    class CausalResult:
        root_causes = ["cpu"]
        confidence = 0.9
        impact_scores = {"cpu": 0.9}

    workflow_integrator.causal_analyzer.analyze_causal_relationships = AsyncMock(
        return_value=CausalResult()
    )
    res = await workflow_integrator._execute_causal_analysis_step({}, execution)
    assert res["status"] == "completed"

    # exception
    workflow_integrator.causal_analyzer.analyze_causal_relationships = AsyncMock(
        side_effect=RuntimeError("x")
    )
    res = await workflow_integrator._execute_causal_analysis_step({}, execution)
    assert res["status"] == "failed"


@pytest.mark.asyncio
async def test_workflow_step_branches(workflow_integrator):
    workflow_integrator.workflow_engine = None
    execution = WorkflowExecution("e3", "wf")
    res = await workflow_integrator._execute_workflow_step({}, execution)
    assert res["reason"] == "workflow_engine_not_available"

    workflow_integrator.workflow_engine = MagicMock()
    res = await workflow_integrator._execute_workflow_step(
        {"workflow_name": "x", "params": {"p": 1}}, execution
    )
    assert res["status"] == "completed"
    assert res["workflow_name"] == "x"


@pytest.mark.asyncio
async def test_data_processing_and_notification_steps(workflow_integrator):
    execution = WorkflowExecution("e4", "wf")
    res = await workflow_integrator._execute_data_processing_step(
        {"processing_type": "filter", "data": [1, 2, 3]}, execution
    )
    assert res["processed_count"] == 3

    class BadData(list):
        def __len__(self):
            raise RuntimeError("boom")

    bad = await workflow_integrator._execute_data_processing_step(
        {"processing_type": "x", "data": BadData()}, execution
    )
    assert bad["status"] == "failed"

    notify = await workflow_integrator._execute_notification_step(
        {"notification_type": "email", "recipients": ["a", "b"]}, execution
    )
    assert notify["recipients_count"] == 2

    bad_notify = await workflow_integrator._execute_notification_step(
        {"notification_type": "email", "recipients": object()}, execution
    )
    assert bad_notify["status"] == "failed"


@pytest.mark.asyncio
async def test_execute_workflow_failure_and_cancel(workflow_integrator):
    wf = WorkflowDefinition(
        workflow_id="wf4",
        name="fail",
        description="d",
        trigger_type=WorkflowTriggerType.MANUAL,
        steps=[{"type": "x"}],
    )
    workflow_integrator.register_workflow(wf)
    execution = WorkflowExecution("e5", "wf4")
    workflow_integrator.active_executions["e5"] = execution

    workflow_integrator._execute_step = AsyncMock(side_effect=RuntimeError("boom"))
    await workflow_integrator._execute_workflow("e5")
    assert execution.status == WorkflowStatus.FAILED
    assert workflow_integrator.failed_executions == 1

    # cancel
    wf2 = WorkflowDefinition(
        workflow_id="wf5",
        name="cancel",
        description="d",
        trigger_type=WorkflowTriggerType.MANUAL,
        steps=[{"type": "x"}, {"type": "y"}],
    )
    workflow_integrator.register_workflow(wf2)
    execution2 = WorkflowExecution("e6", "wf5")
    workflow_integrator.active_executions["e6"] = execution2

    async def fake_step(step, exec):
        exec.status = WorkflowStatus.CANCELLED
        return {"status": "done"}

    workflow_integrator._execute_step = AsyncMock(side_effect=fake_step)
    await workflow_integrator._execute_workflow("e6")
    # source sets COMPLETED after the loop's break; only the first step was executed
    assert execution2.status == WorkflowStatus.COMPLETED
    assert workflow_integrator._execute_step.call_count == 1


@pytest.mark.asyncio
async def test_handle_causal_analysis_trigger(workflow_integrator):
    wf = WorkflowDefinition(
        workflow_id="wf6",
        name="causal",
        description="d",
        trigger_type=WorkflowTriggerType.CAUSAL_ANALYSIS,
        trigger_config={"confidence_threshold": 0.5, "min_root_causes": 1},
    )
    workflow_integrator.register_workflow(wf)

    ids = await workflow_integrator.handle_causal_analysis_trigger(
        {"confidence": 0.8, "root_causes": ["cpu"]}
    )
    assert len(ids) == 1

    ids = await workflow_integrator.handle_causal_analysis_trigger(
        {"confidence": 0.1, "root_causes": []}
    )
    assert ids == []


def test_get_execution_status_not_found(workflow_integrator):
    assert workflow_integrator.get_execution_status("missing") == {
        "error": "Execution not found",
        "execution_id": "missing",
    }


@pytest.mark.asyncio
async def test_cancel_execution_and_statistics(workflow_integrator):
    wf = WorkflowDefinition(
        workflow_id="wf7",
        name="s",
        description="d",
        trigger_type=WorkflowTriggerType.MANUAL,
    )
    workflow_integrator.register_workflow(wf)
    execution = WorkflowExecution("e7", "wf7")
    workflow_integrator.active_executions["e7"] = execution

    assert await workflow_integrator.cancel_execution("e7") is True
    assert execution.status == WorkflowStatus.CANCELLED
    assert await workflow_integrator.cancel_execution("missing") is False

    workflow_integrator.total_executions = 5
    workflow_integrator.successful_executions = 3
    stats = workflow_integrator.get_statistics()
    assert stats["success_rate"] == 0.6
    assert stats["registered_workflows"] == 1


def test_get_l2l3_workflow_integrator_factory():
    inst = get_l2l3_workflow_integrator({})
    assert isinstance(inst, L2L3WorkflowIntegrator)


# ---------------------------------------------------------------------------
# core.escalation
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_notify_rollback_failure_no_webhook(monkeypatch):
    monkeypatch.delenv("ROLLBACK_FAILURE_WEBHOOK", raising=False)
    await notify_rollback_failure("a1", "rollback", "failed", snapshot_id="s1")


@pytest.mark.asyncio
async def test_notify_rollback_failure_with_webhook(monkeypatch):
    monkeypatch.setenv("ROLLBACK_FAILURE_WEBHOOK", "http://alert")

    class FakeResp:
        status_code = 200

    class FakeClient:
        instances = []

        def __init__(self, *args, **kwargs):
            FakeClient.instances.append(self)
            self.post = AsyncMock(return_value=FakeResp())

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args, **kwargs):
            return None

    monkeypatch.setattr("httpx.AsyncClient", FakeClient)
    await notify_rollback_failure("a2", "rollback", "err", snapshot_id="s2", extra={"team": "ops"})
    assert FakeClient.instances
    payload = FakeClient.instances[-1].post.call_args.kwargs["json"]
    assert payload["alert_id"] == "a2"
    assert payload["team"] == "ops"


@pytest.mark.asyncio
async def test_notify_rollback_failure_webhook_exception(monkeypatch):
    monkeypatch.setenv("ROLLBACK_FAILURE_WEBHOOK", "http://alert")

    class FakeClient:
        def __init__(self, *args, **kwargs):
            self.post = AsyncMock(side_effect=RuntimeError("net"))

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args, **kwargs):
            return None

    monkeypatch.setattr("httpx.AsyncClient", FakeClient)
    await notify_rollback_failure("a3", "rollback", "err")


def test_escalate_rollback_failure_sync():
    escalate_rollback_failure_sync("a4", "rollback", "err", snapshot_id="s3")
