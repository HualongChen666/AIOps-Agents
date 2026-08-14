# -*- coding: utf-8 -*-
"""Functional coverage tests for batch20c core modules."""

import asyncio
import json
import sys
from datetime import datetime, timezone
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

import core.log_router
import core.processing.l3.workflow_engine as we_mod

from core.log_router import (
    LogDestination,
    LogEntry,
    LogLevel,
    LogRouter,
    LogRouterManager,
    create_log_router,
)
from core.plugin_manager import get_plugin, get_plugin_manager, load_all, list_plugins
from core.processing.l3.workflow_engine import (
    FallbackWorkflowState,
    Workflow,
    WorkflowEngine,
    WorkflowStep,
    get_workflow_engine,
    init_workflow_engine,
)
from core.snapshot_store import (
    build_pre_state,
    classify_operation_type,
    cleanup_expired_snapshots,
    get_snapshot,
    save_snapshot,
    update_snapshot_status,
    _extract_k8s_resource,
    _extract_pid_or_name,
    _extract_service_name,
    _parse_namespace,
    _run_shell_capture,
    _safe_name,
    _safe_service_name,
)
import core.integration_helpers as ih

pytestmark = [pytest.mark.core]


@pytest.fixture(autouse=True)
def _patch_workflow_state(monkeypatch):
    monkeypatch.setattr(we_mod, "WorkflowStateClass", FallbackWorkflowState)


# ---------------------------------------------------------------------------
# core/snapshot_store.py
# ---------------------------------------------------------------------------
class _FakeSession:
    def __init__(self, result=None):
        self.result = result

    def add(self, obj):
        self.added = obj

    async def commit(self):
        pass

    async def get(self, model, key):
        return self.result

    async def execute(self, stmt):
        class _Result:
            rowcount = self.result if isinstance(self.result, int) else 1

            def scalar_one_or_none(self):
                return self.result

        return _Result()


class _AsyncSessionCM:
    def __init__(self, result=None, exc=None):
        self.result = result
        self.exc = exc

    async def __aenter__(self):
        if self.exc:
            raise self.exc
        return _FakeSession(self.result)

    async def __aexit__(self, *args):
        pass


def _fake_state():
    return SimpleNamespace(
        alert={"id": "a1", "platform": "linux", "host": "h1"},
        runbook={"script_key": "restart"},
        snapshot={},
    )


def test_classify_operation_type():
    assert classify_operation_type(["kubectl rollout restart deploy/nginx"]) == "pod_restart"
    assert classify_operation_type(["kubectl apply -f cm.yaml"]) == "config_mod"
    assert classify_operation_type(["kubectl scale deploy nginx --replicas=3"]) == "scale"
    assert (
        classify_operation_type(["kubectl get networkpolicy allow"])
        == "network_policy"
    )
    assert classify_operation_type(["systemctl restart nginx"]) == "service_restart"
    assert classify_operation_type(["kill -9 1234"]) == "process_kill"
    assert classify_operation_type(["ip addr flush"]) == "network_fix"
    assert classify_operation_type(["echo hello"]) == "generic"


def test_safe_names():
    assert _safe_name("nginx-1") == "nginx-1"
    assert _safe_name("bad;name") is None
    assert _safe_name("") is None
    assert _safe_service_name("mysql@1") == "mysql@1"
    assert _safe_service_name("bad;svc") is None


def test_parse_namespace():
    assert _parse_namespace("kubectl get pod -n=kube-system") == "kube-system"
    assert _parse_namespace("kubectl get pod -n default") == "default"
    assert _parse_namespace("kubectl get pod --namespace=app") == "app"
    assert _parse_namespace("kubectl get pods") == "default"


def test_extract_k8s_resource():
    assert _extract_k8s_resource(
        "kubectl rollout restart deployment/nginx -n foo"
    ) == ("deployment", "nginx", "foo")
    assert _extract_k8s_resource(
        "kubectl scale deployment nginx --replicas=3 --namespace bar"
    ) == ("deployment", "nginx", "bar")
    assert _extract_k8s_resource(
        "kubectl get configmap my-cm -n ns1"
    ) == ("configmap", "my-cm", "ns1")
    assert _extract_k8s_resource("kubectl apply -f file.yaml") is None
    assert _extract_k8s_resource("echo hello") is None


def test_extract_service_name():
    assert _extract_service_name("systemctl restart nginx") == "nginx"
    assert _extract_service_name("systemctl status mysql@1") == "mysql@1"
    assert _extract_service_name("Restart-Service -Name 'w3svc'") == "w3svc"
    assert _extract_service_name("Restart-Service w3svc") == "w3svc"
    assert _extract_service_name("echo hello") is None


def test_extract_pid_or_name():
    assert _extract_pid_or_name("kill 1234") == "1234"
    assert _extract_pid_or_name("pkill nginx") == "nginx"
    assert _extract_pid_or_name("killall -TERM app") == "app"
    assert _extract_pid_or_name("Stop-Process -Id 5678") == "5678"
    assert _extract_pid_or_name("Stop-Process -Name foo") == "foo"
    assert _extract_pid_or_name("taskkill /PID 9999") == "9999"
    assert _extract_pid_or_name("taskkill /IM notepad.exe") == "notepad.exe"
    assert _extract_pid_or_name("echo") is None


def test_run_shell_capture_success(monkeypatch):
    async def _communicate():
        return b"output\n", b""

    proc = AsyncMock()
    proc.returncode = 0
    proc.communicate = _communicate
    monkeypatch.setattr(asyncio, "create_subprocess_shell", AsyncMock(return_value=proc))

    out = asyncio.run(_run_shell_capture("uptime", "linux"))
    assert out == "output"


def test_run_shell_capture_powershell(monkeypatch):
    async def _communicate():
        return b"svc output", b""

    proc = AsyncMock()
    proc.returncode = 0
    proc.communicate = _communicate
    monkeypatch.setattr(asyncio, "create_subprocess_exec", AsyncMock(return_value=proc))

    out = asyncio.run(
        _run_shell_capture(
            'powershell -Command "Get-Service"',
            "windows",
        )
    )
    assert out == "svc output"


def test_run_shell_capture_error(monkeypatch):
    async def _communicate():
        return b"", b"boom"

    proc = AsyncMock()
    proc.returncode = 1
    proc.communicate = _communicate
    monkeypatch.setattr(asyncio, "create_subprocess_shell", AsyncMock(return_value=proc))

    out = asyncio.run(_run_shell_capture("bad", "linux"))
    assert "rc=1" in out
    assert "boom" in out


def test_run_shell_capture_timeout(monkeypatch):
    proc = AsyncMock()
    proc.communicate = AsyncMock(side_effect=asyncio.TimeoutError)
    monkeypatch.setattr(asyncio, "create_subprocess_shell", AsyncMock(return_value=proc))

    out = asyncio.run(_run_shell_capture("slow", "linux"))
    assert "timeout" in out


def test_run_shell_capture_generic_exception(monkeypatch):
    proc = AsyncMock()
    proc.communicate = AsyncMock(side_effect=RuntimeError("boom"))
    monkeypatch.setattr(asyncio, "create_subprocess_shell", AsyncMock(return_value=proc))

    out = asyncio.run(_run_shell_capture("bad", "linux"))
    assert "error capturing state" in out


def test_build_pre_state_pod_restart(monkeypatch):
    monkeypatch.setattr(
        "core.snapshot_store._run_shell_capture", AsyncMock(return_value="{}")
    )
    pre = asyncio.run(
        build_pre_state(
            "pod_restart",
            {"id": "a1"},
            ["kubectl rollout restart deployment/nginx -n default"],
            "linux",
        )
    )
    assert pre["operation_type"] == "pod_restart"
    assert len(pre["resources"]) == 1
    assert pre["resources"][0]["resource_type"] == "deployment"


def test_build_pre_state_config_mod_and_scale(monkeypatch):
    monkeypatch.setattr(
        "core.snapshot_store._run_shell_capture", AsyncMock(return_value="{}")
    )
    pre = asyncio.run(
        build_pre_state(
            "config_mod",
            {"id": "a1"},
            ["kubectl get configmap my-cm -n ns1"],
            "linux",
        )
    )
    assert pre["resources"][0]["resource_type"] == "configmap"

    pre = asyncio.run(
        build_pre_state(
            "scale",
            {"id": "a1"},
            ["kubectl scale deployment nginx --replicas=3 --namespace bar"],
            "linux",
        )
    )
    assert pre["resources"][0]["resource_type"] == "deployment"


def test_build_pre_state_network_policy(monkeypatch):
    monkeypatch.setattr(
        "core.snapshot_store._run_shell_capture", AsyncMock(return_value="---")
    )
    pre = asyncio.run(
        build_pre_state(
            "network_policy",
            {"id": "a1"},
            ["kubectl get networkpolicy allow -n kube-system"],
            "linux",
        )
    )
    assert pre["resources"][0]["namespace"] == "kube-system"


def test_build_pre_state_service_restart(monkeypatch):
    monkeypatch.setattr(
        "core.snapshot_store._run_shell_capture", AsyncMock(return_value="active")
    )
    pre = asyncio.run(
        build_pre_state(
            "service_restart",
            {"id": "a1"},
            ["systemctl restart nginx", "Restart-Service -Name mysql"],
            "linux",
        )
    )
    assert len(pre["resources"]) == 2

    pre_win = asyncio.run(
        build_pre_state(
            "service_restart",
            {"id": "a1"},
            ["Restart-Service -Name w3svc"],
            "windows",
        )
    )
    assert pre_win["platform"] == "windows"


def test_build_pre_state_process_kill(monkeypatch):
    monkeypatch.setattr(
        "core.snapshot_store._run_shell_capture", AsyncMock(return_value="info")
    )
    pre = asyncio.run(
        build_pre_state(
            "process_kill",
            {"id": "a1"},
            ["kill 1234", "taskkill /PID 5678"],
            "linux",
        )
    )
    assert len(pre["resources"]) == 2

    pre_win = asyncio.run(
        build_pre_state(
            "process_kill",
            {"id": "a1"},
            ["taskkill /PID 9999"],
            "windows",
        )
    )
    assert pre_win["platform"] == "windows"


def test_build_pre_state_generic(monkeypatch):
    monkeypatch.setattr(
        "core.snapshot_store._run_shell_capture", AsyncMock(return_value="")
    )
    pre = asyncio.run(
        build_pre_state(
            "generic",
            {"id": "a1"},
            ["echo hello"],
            "linux",
        )
    )
    assert pre["resources"][0]["note"]


def test_save_snapshot_success(monkeypatch):
    monkeypatch.setenv("SNAPSHOT_ENCRYPTION_ENABLED", "false")
    monkeypatch.setattr(
        "core.snapshot_store.AsyncSessionLocal",
        lambda result=None: _AsyncSessionCM(result),
    )
    state = _fake_state()
    sid = asyncio.run(
        save_snapshot(
            state,
            ["systemctl restart nginx"],
            ["systemctl start nginx"],
            pre_metrics={"cpu": 0.5},
        )
    )
    assert sid is not None
    assert sid.startswith("snap-a1-")
    assert state.snapshot_id == sid
    assert state.snapshot["snapshot_id"] == sid
    assert "pre_state" in state.rollback_info


def test_save_snapshot_missing_alert(monkeypatch):
    state = SimpleNamespace(alert=None, snapshot={})
    assert (
        asyncio.run(
            save_snapshot(
                state,
                ["systemctl restart nginx"],
                ["systemctl start nginx"],
            )
        )
        is None
    )


def test_save_snapshot_db_failure(monkeypatch):
    monkeypatch.setenv("SNAPSHOT_ENCRYPTION_ENABLED", "false")
    monkeypatch.setattr(
        "core.snapshot_store.AsyncSessionLocal",
        lambda result=None: _AsyncSessionCM(result, exc=RuntimeError("db fail")),
    )
    state = _fake_state()
    assert (
        asyncio.run(
            save_snapshot(
                state,
                ["systemctl restart nginx"],
                ["systemctl start nginx"],
            )
        )
        is None
    )


def test_update_snapshot_status(monkeypatch):
    monkeypatch.setenv("SNAPSHOT_ENCRYPTION_ENABLED", "false")
    snapshot = SimpleNamespace(
        status="pending",
        completed_at=None,
        post_state=None,
        error_message=None,
    )
    monkeypatch.setattr(
        "core.snapshot_store.AsyncSessionLocal",
        lambda result=None: _AsyncSessionCM(snapshot),
    )
    asyncio.run(
        update_snapshot_status(
            "s1",
            "completed",
            post_state={"ok": True},
            error_message="",
        )
    )
    assert snapshot.status == "completed"
    assert snapshot.post_state is not None


def test_update_snapshot_status_missing_and_error(monkeypatch):
    monkeypatch.setenv("SNAPSHOT_ENCRYPTION_ENABLED", "false")
    asyncio.run(update_snapshot_status(None, "completed"))  # no-op
    monkeypatch.setattr(
        "core.snapshot_store.AsyncSessionLocal",
        lambda result=None: _AsyncSessionCM(result, exc=RuntimeError("db fail")),
    )
    asyncio.run(update_snapshot_status("s1", "failed"))  # should not raise


def test_get_snapshot(monkeypatch):
    monkeypatch.setenv("SNAPSHOT_ENCRYPTION_ENABLED", "false")
    snapshot = SimpleNamespace(
        id="s1",
        alert_id="a1",
        repair_record_id="r1",
        operation_type="test",
        pre_state="PLAINTEXT::{\"x\":1}",
        post_state=None,
        rollback_plan="PLAINTEXT::{\"commands\":[]}",
        status="pending",
        retention_days=7,
        expires_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
        completed_at=None,
        error_message=None,
    )
    monkeypatch.setattr(
        "core.snapshot_store.AsyncSessionLocal",
        lambda result=None: _AsyncSessionCM(snapshot),
    )
    result = asyncio.run(get_snapshot("s1"))
    assert result["id"] == "s1"
    assert result["pre_state"] == {"x": 1}
    assert result["post_state"] is None


def test_get_snapshot_not_found_and_error(monkeypatch):
    monkeypatch.setattr(
        "core.snapshot_store.AsyncSessionLocal",
        lambda result=None: _AsyncSessionCM(None),
    )
    assert asyncio.run(get_snapshot("missing")) is None
    monkeypatch.setattr(
        "core.snapshot_store.AsyncSessionLocal",
        lambda result=None: _AsyncSessionCM(result, exc=RuntimeError("db fail")),
    )
    assert asyncio.run(get_snapshot("s1")) is None


def test_cleanup_expired_snapshots(monkeypatch):
    monkeypatch.setattr(
        "core.snapshot_store.AsyncSessionLocal",
        lambda result=None: _AsyncSessionCM(5),
    )
    assert asyncio.run(cleanup_expired_snapshots()) == 5


def test_cleanup_expired_snapshots_error(monkeypatch):
    monkeypatch.setattr(
        "core.snapshot_store.AsyncSessionLocal",
        lambda result=None: _AsyncSessionCM(result, exc=RuntimeError("db fail")),
    )
    assert asyncio.run(cleanup_expired_snapshots()) == 0


# ---------------------------------------------------------------------------
# core/processing/l3/workflow_engine.py
# ---------------------------------------------------------------------------
def test_workflow_step_and_workflow():
    step = WorkflowStep("s1", AsyncMock(return_value={"ok": True}))
    wf = Workflow("wf1", "test")
    assert wf.add_step(step) is wf
    assert wf.get_step("s1") is step
    assert wf.get_step("missing") is None
    assert step.state.value == "pending"


def test_workflow_engine_lifecycle():
    engine = WorkflowEngine({"max_parallel_nodes": 2})
    assert engine.get_status()["initialized"] is True
    assert engine.get_workflow("missing") is None

    wf = Workflow("wf1")
    engine.register_workflow(wf)
    assert engine.get_workflow("wf1") is wf
    assert "wf1" in engine.get_status()["workflows"]

    init_workflow_engine({})
    assert get_workflow_engine() is not None


def test_execute_workflow_not_found():
    engine = WorkflowEngine()
    result = asyncio.run(engine.execute_workflow("missing"))
    assert "error" in result


def test_execute_workflow_success():
    engine = WorkflowEngine()
    wf = Workflow("wf1")
    wf.add_step(WorkflowStep("s1", AsyncMock(return_value={"ok": True})))
    engine.register_workflow(wf)
    result = asyncio.run(engine.execute_workflow("wf1", {"x": 1}))
    assert result["state"] == "completed"
    assert result["steps_executed"] == 1
    assert wf.context["s1"]["ok"] is True


def test_execute_workflow_failing_step():
    engine = WorkflowEngine()
    wf = Workflow("wf1")
    wf.add_step(WorkflowStep("s1", AsyncMock(side_effect=RuntimeError("fail"))))
    engine.register_workflow(wf)
    result = asyncio.run(engine.execute_workflow("wf1"))
    assert result["state"] == "failed"
    assert result["failed_step"] == "s1"


def test_incident_response_workflow():
    engine = WorkflowEngine()
    engine.create_incident_response_workflow()
    result = asyncio.run(
        engine.execute_workflow(
            "incident_response",
            {
                "alert": "cpu high",
                "metrics": {"cpu": "normal"},
                "status": "resolved",
            },
        )
    )
    assert result["state"] == "completed"
    assert result["steps_executed"] == 6


def test_analyze_incident_handler():
    engine = WorkflowEngine()
    cases = [
        ("cpu", "CPU resource exhaustion"),
        ("memory", "Memory exhaustion"),
        ("disk", "Disk space issue"),
        ("network", "Network connectivity issue"),
        ("service", "Service failure"),
        ("xyz", "Unknown root cause"),
    ]
    for keyword, expected in cases:
        result = asyncio.run(
            engine._analyze_incident_handler({"alert": keyword}, {"use_rag": True})
        )
        assert result["root_cause"] == expected


def test_determine_severity_handler():
    engine = WorkflowEngine()
    result = asyncio.run(
        engine._determine_severity_handler(
            {"analyze_incident": {"root_cause": "cpu high"}}, {}
        )
    )
    assert result["severity"] == "high"
    assert result["priority"] == 1

    result = asyncio.run(
        engine._determine_severity_handler(
            {"analyze_incident": {"root_cause": "warning"}}, {}
        )
    )
    assert result["severity"] == "medium"

    result = asyncio.run(
        engine._determine_severity_handler(
            {"analyze_incident": {"root_cause": "xyz"}}, {}
        )
    )
    assert result["severity"] == "low"


def test_generate_repair_plan_handler():
    engine = WorkflowEngine()
    cases = [
        ("cpu", "Scale CPU or restart overloaded processes"),
        ("memory", "Free memory or restart leaking service"),
        ("disk", "Clean up disk space"),
        ("network", "Check network connectivity and DNS"),
        ("service", "Restart affected service"),
        ("xyz", "Investigate incident manually"),
    ]
    for keyword, expected in cases:
        result = asyncio.run(
            engine._generate_repair_plan_handler(
                {
                    "analyze_incident": {"root_cause": keyword},
                    "determine_severity": {"severity": "high"},
                },
                {},
            )
        )
        assert result["plan"] == expected
        assert result["estimated_time"] == "5min"


def test_request_approval_handler():
    engine = WorkflowEngine()
    low = asyncio.run(
        engine._request_approval_handler(
            {"determine_severity": {"severity": "low"}}, {}
        )
    )
    assert low["approved"] is True
    high = asyncio.run(
        engine._request_approval_handler(
            {"determine_severity": {"severity": "high"}}, {}
        )
    )
    assert high["approved"] is False


def test_execute_repair_handler():
    engine = WorkflowEngine()
    cases = [
        ("restart", "Restarted affected service"),
        ("scale", "Scaled CPU resources"),
        ("free", "Freed memory and recycled service"),
        ("clean", "Cleaned up disk space"),
        ("manual", "Executed remediation: manual"),
    ]
    for plan, expected in cases:
        result = asyncio.run(
            engine._execute_repair_handler(
                {"generate_repair_plan": {"plan": plan}, "determine_severity": {}},
                {},
            )
        )
        assert result["action"] == expected


def test_verify_fix_handler():
    engine = WorkflowEngine()
    ok = asyncio.run(
        engine._verify_fix_handler(
            {"status": "resolved", "metrics": {"cpu": "normal"}}, {}
        )
    )
    assert ok["verified"] is True

    bad = asyncio.run(
        engine._verify_fix_handler(
            {"status": "resolved", "metrics": {"cpu": "critical"}}, {}
        )
    )
    assert bad["verified"] is False

    no_metrics = asyncio.run(
        engine._verify_fix_handler({"status": "resolved"}, {})
    )
    assert no_metrics["verified"] is True


# ---------------------------------------------------------------------------
# core/plugin_manager.py
# ---------------------------------------------------------------------------
class _FakePluginManager:
    def __init__(self):
        self.plugins = [{"metadata": {"name": "p1"}}, {"metadata": {"name": "p2"}}]

    def discover_plugins(self):
        pass

    def load_all_plugins(self):
        pass

    def list_plugins(self, plugin_type=None):
        return self.plugins

    def get_plugin(self, name):
        for p in self.plugins:
            if p["metadata"]["name"] == name:
                return p
        return None


def test_plugin_manager_cached(monkeypatch):
    fake = _FakePluginManager()
    monkeypatch.setattr("core.plugin_manager._plugin_manager", fake)
    assert get_plugin_manager() is fake


def test_plugin_manager_create(monkeypatch):
    monkeypatch.setattr("core.plugin_manager._plugin_manager", None)
    fake = _FakePluginManager()
    monkeypatch.setattr(
        "core.plugin_manager.create_plugin_manager", lambda: fake
    )
    assert get_plugin_manager() is fake
    load_all()  # calls discover and load methods
    assert list_plugins() == ["p1", "p2"]
    assert get_plugin("p1") is not None
    assert get_plugin("missing") is None


# ---------------------------------------------------------------------------
# core/log_router.py
# ---------------------------------------------------------------------------
class _FakeResponse:
    def __init__(self, status):
        self.status = status


class _FakeResponseContext:
    def __init__(self, status=204, exc=None):
        self._status = status
        self._exc = exc

    async def __aenter__(self):
        if self._exc:
            raise self._exc
        return _FakeResponse(self._status)

    async def __aexit__(self, *args):
        pass


class _FakeClientSession:
    def __init__(self, status=204, exc=None):
        self._status = status
        self._exc = exc

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    async def close(self):
        pass

    def post(self, url, json, headers):
        return _FakeResponseContext(self._status, self._exc)


class _FakeAiohttp:
    ClientSession = _FakeClientSession


def test_log_entry():
    ts = datetime.now(timezone.utc)
    entry = LogEntry(
        timestamp=ts,
        level=LogLevel.INFO,
        message="msg",
        service="svc",
        host="h1",
        environment="prod",
        labels={"a": "b"},
        extra={},
    )
    d = entry.to_dict()
    assert d["timestamp"] == ts.isoformat()
    assert d["level"] == "info"
    loki = entry.to_loki_format()
    assert loki["streams"][0]["stream"]["service"] == "svc"


def test_log_router_context_manager(monkeypatch):
    monkeypatch.setattr(core.log_router, "aiohttp", _FakeAiohttp())

    async def _use():
        async with LogRouter({"destinations": ["loki"]}) as router:
            return router

    router = asyncio.run(_use())
    assert router.session is not None


def test_send_to_loki_and_elasticsearch(monkeypatch):
    monkeypatch.setattr(core.log_router, "aiohttp", _FakeAiohttp())
    router = LogRouter({"destinations": ["loki"]})
    router.session = _FakeClientSession(status=204)
    entry = router.create_log_entry("hello")
    assert asyncio.run(router.send_to_loki(entry)) is True

    router.session = _FakeClientSession(status=404)
    assert asyncio.run(router.send_to_loki(entry)) is False

    router.session = _FakeClientSession(status=201)
    assert asyncio.run(router.send_to_elasticsearch(entry)) is True

    router.session = _FakeClientSession(status=500)
    assert asyncio.run(router.send_to_elasticsearch(entry)) is False


def test_send_to_loki_creates_session(monkeypatch):
    monkeypatch.setattr(core.log_router, "aiohttp", _FakeAiohttp())
    router = LogRouter({"destinations": ["loki"], "loki_url": "http://loki"})
    entry = router.create_log_entry("hello")
    assert router.session is None
    assert asyncio.run(router.send_to_loki(entry)) is True
    assert router.session is not None


def test_send_to_loki_exception(monkeypatch):
    monkeypatch.setattr(core.log_router, "aiohttp", _FakeAiohttp())
    router = LogRouter({"destinations": ["loki"]})
    router.session = _FakeClientSession(exc=RuntimeError("network"))
    entry = router.create_log_entry("hello")
    assert asyncio.run(router.send_to_loki(entry)) is False


def test_send_to_kafka_and_s3(monkeypatch):
    kafka_mod = ModuleType("kafka")

    class _FakeProducer:
        def __init__(self, **kwargs):
            pass

        def send(self, topic, value):
            return MagicMock()

        def flush(self):
            pass

        def close(self):
            pass

    kafka_mod.KafkaProducer = _FakeProducer
    monkeypatch.setitem(sys.modules, "kafka", kafka_mod)

    boto3_mod = ModuleType("boto3")
    boto3_mod.client = MagicMock(return_value=MagicMock(put_object=MagicMock()))
    monkeypatch.setitem(sys.modules, "boto3", boto3_mod)

    router = LogRouter(
        {
            "destinations": ["kafka", "s3"],
            "kafka_brokers": ["localhost:9092"],
            "s3_bucket": "bucket",
        }
    )
    entry = router.create_log_entry("hello")
    assert asyncio.run(router.send_to_kafka(entry)) is True
    assert asyncio.run(router.send_to_s3(entry)) is True

    # missing configuration
    empty = LogRouter({"destinations": ["kafka"], "kafka_brokers": ""})
    assert asyncio.run(empty.send_to_kafka(entry)) is False
    empty_s3 = LogRouter({"destinations": ["s3"], "s3_bucket": ""})
    assert asyncio.run(empty_s3.send_to_s3(entry)) is False


def test_send_to_kafka_exception(monkeypatch):
    kafka_mod = ModuleType("kafka")

    class _BadProducer:
        def __init__(self, **kwargs):
            raise RuntimeError("kafka down")

    kafka_mod.KafkaProducer = _BadProducer
    monkeypatch.setitem(sys.modules, "kafka", kafka_mod)

    router = LogRouter(
        {"destinations": ["kafka"], "kafka_brokers": ["localhost:9092"]}
    )
    entry = router.create_log_entry("hello")
    assert asyncio.run(router.send_to_kafka(entry)) is False


def test_route_log_and_batch(monkeypatch):
    monkeypatch.setattr(core.log_router, "aiohttp", _FakeAiohttp())
    router = LogRouter({"destinations": ["loki"]})
    router.session = _FakeClientSession(status=204)
    entry = router.create_log_entry("hello")

    assert asyncio.run(router.route_log(entry)) is True

    router.disable()
    assert asyncio.run(router.route_log(entry)) is False
    router.enable()

    router.destinations = ["loki", "elasticsearch"]
    monkeypatch.setattr(
        router, "send_to_loki", AsyncMock(side_effect=RuntimeError("fail"))
    )
    monkeypatch.setattr(router, "send_to_elasticsearch", AsyncMock(return_value=True))
    assert asyncio.run(router.route_log(entry)) is False

    router.destinations = []
    assert asyncio.run(router.route_log(entry)) is True

    monkeypatch.setattr(
        router, "route_log", AsyncMock(side_effect=[True, False])
    )
    results = asyncio.run(router.batch_route_logs([entry, entry]))
    assert results["success"] == 1
    assert results["failed"] == 1


def test_parse_fluent_bit_log_and_create_entry():
    router = LogRouter({})
    ts = datetime.now(timezone.utc).isoformat()
    parsed = router.parse_fluent_bit_log(
        json.dumps(
            {
                "timestamp": ts,
                "level": "warning",
                "message": "m",
                "service": "s",
                "host": "h",
                "environment": "e",
                "labels": {"l": "v"},
                "extra": {"x": 1},
            }
        )
    )
    assert parsed is not None
    assert parsed.level == LogLevel.WARNING
    assert router.parse_fluent_bit_log("not-json{") is None
    entry = router.create_log_entry("msg", host=None)
    assert entry.host is not None


def test_log_router_manager():
    manager = LogRouterManager()
    r1 = manager.add_router("r1", {"destinations": ["loki"]})
    r2 = manager.add_router("r2", {"destinations": ["kafka"]})
    assert manager.get_router("r1") is r1
    assert manager.default_router is r1
    assert manager.set_default_router("r2") is True
    assert manager.default_router is r2
    assert manager.set_default_router("missing") is False
    assert manager.remove_router("r1") is True
    assert manager.get_router("r1") is None
    assert isinstance(create_log_router({}), LogRouter)


# ---------------------------------------------------------------------------
# core/integration_helpers.py
# ---------------------------------------------------------------------------
def _fake_retry_module(success=True, init_raise=None):
    mod = ModuleType("core.retry_enhanced")

    class _RetryStrategy:
        EXPONENTIAL_BACKOFF = "exp"

    class _EnhancedRetry:
        def __init__(self, **kwargs):
            if init_raise:
                raise init_raise

        def __call__(self, func):
            async def _async_wrapper(*a, **k):
                return await func(*a, **k) if asyncio.iscoroutinefunction(func) else func(*a, **k)

            def _sync_wrapper(*a, **k):
                return func(*a, **k)

            if asyncio.iscoroutinefunction(func):
                return _async_wrapper
            return _sync_wrapper

    mod.EnhancedRetry = _EnhancedRetry
    mod.RetryStrategy = _RetryStrategy
    return mod


def test_apply_enhanced_retry_success(monkeypatch):
    mod = _fake_retry_module()
    monkeypatch.setitem(sys.modules, "core.retry_enhanced", mod)

    def original(x):
        return x * 2

    enhanced = ih.apply_enhanced_retry_to_function(original)
    assert enhanced(3) == 6


def test_apply_enhanced_retry_import_error(monkeypatch):
    monkeypatch.setitem(sys.modules, "core.retry_enhanced", None)

    def original(x):
        return x

    enhanced = ih.apply_enhanced_retry_to_function(original)
    assert enhanced(1) == 1


def test_apply_enhanced_retry_init_exception(monkeypatch):
    mod = _fake_retry_module(init_raise=RuntimeError("retry init fail"))
    monkeypatch.setitem(sys.modules, "core.retry_enhanced", mod)

    def original(x):
        return x

    enhanced = ih.apply_enhanced_retry_to_function(original)
    assert enhanced(1) == 1


def test_enhance_notify_engine(monkeypatch):
    notify_mod = ModuleType("core.notify_engine")
    notify_mod._post_webhook = lambda x: x
    monkeypatch.setitem(sys.modules, "core.notify_engine", notify_mod)

    mod = _fake_retry_module()
    monkeypatch.setitem(sys.modules, "core.retry_enhanced", mod)

    ih.enhance_notify_engine()
    assert notify_mod._post_webhook is not None


def test_enhance_notify_engine_no_webhook(monkeypatch):
    notify_mod = ModuleType("core.notify_engine")
    monkeypatch.setitem(sys.modules, "core.notify_engine", notify_mod)
    ih.enhance_notify_engine()  # just warns


def test_enhance_notify_engine_import_error(monkeypatch):
    monkeypatch.setitem(sys.modules, "core.notify_engine", None)
    ih.enhance_notify_engine()


def test_enhance_ai_engine(monkeypatch):
    ih.enhance_ai_engine()
    # cover exception branch by making logger raise
    monkeypatch.setattr(ih.logger, "info", MagicMock(side_effect=RuntimeError("log fail")))
    ih.enhance_ai_engine()
    # cover ImportError branch
    monkeypatch.setattr(ih.logger, "info", MagicMock(side_effect=ImportError("log fail")))
    ih.enhance_ai_engine()


def test_enhance_db_engine(monkeypatch):
    cp_mod = ModuleType("core.connection_pool_optimization")
    cp_mod.create_optimized_engine = AsyncMock(return_value=None)
    monkeypatch.setitem(sys.modules, "core.connection_pool_optimization", cp_mod)
    asyncio.run(ih.enhance_db_engine())

    # ImportError branch
    monkeypatch.setitem(sys.modules, "core.connection_pool_optimization", None)
    asyncio.run(ih.enhance_db_engine())

    # Exception branch
    bad_mod = ModuleType("core.connection_pool_optimization")
    bad_mod.create_optimized_engine = AsyncMock(side_effect=RuntimeError("pool fail"))
    monkeypatch.setitem(sys.modules, "core.connection_pool_optimization", bad_mod)
    asyncio.run(ih.enhance_db_engine())


def test_apply_all_enhancements(monkeypatch):
    notify_mod = ModuleType("core.notify_engine")
    notify_mod._post_webhook = lambda x: x
    monkeypatch.setitem(sys.modules, "core.notify_engine", notify_mod)
    monkeypatch.setitem(sys.modules, "core.retry_enhanced", _fake_retry_module())
    cp_mod = ModuleType("core.connection_pool_optimization")
    cp_mod.create_optimized_engine = AsyncMock(return_value=None)
    monkeypatch.setitem(sys.modules, "core.connection_pool_optimization", cp_mod)
    asyncio.run(ih.apply_all_enhancements())
