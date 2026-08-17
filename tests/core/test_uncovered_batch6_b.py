# -*- coding: utf-8 -*-
"""Targeted coverage tests for core/cloud_repair, core/config,
core/cross_service_tracing and core/docker_collector."""

import asyncio
import importlib
import sys
import types
from collections import deque
from unittest.mock import MagicMock

import pytest
from docker.errors import DockerException
from opentelemetry.trace import SpanKind

import core.cloud_repair as cloud_repair
import core.config as cfg
import core.cross_service_tracing as tracing
import core.docker_collector as docker_collector

pytestmark = [pytest.mark.core]


# -----------------------------------------------------------------------------
# core/cloud_repair.py
# -----------------------------------------------------------------------------


@pytest.fixture
def fresh_repair_history(monkeypatch):
    """Provide an isolated repair history deque for each test."""
    monkeypatch.setattr(cloud_repair, "_REPAIR_HISTORY", deque(maxlen=1000))


@pytest.fixture
def stub_boto3(monkeypatch):
    """Stub boto3 so AWS repair actions run without real credentials."""

    class FakeEC2:
        def __init__(self):
            self.calls = []

        def reboot_instances(self, InstanceIds):
            self.calls.append(("reboot", InstanceIds))

        def start_instances(self, InstanceIds):
            self.calls.append(("start", InstanceIds))

        def stop_instances(self, InstanceIds):
            self.calls.append(("stop", InstanceIds))

    class FakeSession:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def client(self, name):
            assert name == "ec2"
            return FakeEC2()

    mod = types.SimpleNamespace(Session=FakeSession)
    monkeypatch.setitem(sys.modules, "boto3", mod)
    return mod


@pytest.fixture
def stub_azure(monkeypatch):
    """Stub Azure SDK so Azure VM repair actions run without real credentials."""

    class FakeCredential:
        def __init__(self, tenant_id, client_id, client_secret):
            self.tenant_id = tenant_id
            self.client_id = client_id
            self.client_secret = client_secret

    class FakeVMs:
        def __init__(self):
            self.calls = []

        def begin_restart(self, resource_group_name, vm_name):
            self.calls.append(("restart", resource_group_name, vm_name))
            return "restart-op"

        def begin_start(self, resource_group_name, vm_name):
            self.calls.append(("start", resource_group_name, vm_name))
            return "start-op"

        def begin_deallocate(self, resource_group_name, vm_name):
            self.calls.append(("deallocate", resource_group_name, vm_name))
            return "deallocate-op"

    class FakeCompute:
        def __init__(self, credential, subscription_id):
            self.credential = credential
            self.subscription_id = subscription_id
            self.virtual_machines = FakeVMs()

    identity = types.SimpleNamespace(ClientSecretCredential=FakeCredential)
    compute = types.SimpleNamespace(ComputeManagementClient=FakeCompute)
    monkeypatch.setitem(sys.modules, "azure.identity", identity)
    monkeypatch.setitem(sys.modules, "azure.mgmt.compute", compute)
    return identity, compute


@pytest.fixture
def missing_boto3(monkeypatch):
    monkeypatch.setitem(sys.modules, "boto3", None)


@pytest.fixture
def missing_azure(monkeypatch):
    monkeypatch.setitem(sys.modules, "azure.identity", None)
    monkeypatch.setitem(sys.modules, "azure.mgmt.compute", None)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "action,expected_call",
    [
        ("restart_instance", "reboot"),
        ("start_instance", "start"),
        ("stop_instance", "stop"),
    ],
)
async def test_aws_repair_actions(fresh_repair_history, stub_boto3, action, expected_call):
    result = await cloud_repair.execute_cloud_repair(
        {
            "provider": "aws",
            "access_key": "ak",
            "secret_key": "sk",
            "region": "us-east-1",
        },
        action,
        instance_id="i-0123456789abcdef0",
    )
    assert result["success"] is True
    assert result["provider"] == "aws"
    assert result["action"] == action
    assert "i-0123456789abcdef0" in result["message"]
    history = cloud_repair.get_cloud_repair_history()
    assert len(history) == 1
    assert history[0]["provider"] == "aws"


@pytest.mark.asyncio
async def test_aws_repair_missing_instance_id(fresh_repair_history, stub_boto3):
    with pytest.raises(ValueError, match="instance_id is required"):
        await cloud_repair.execute_cloud_repair(
            {
                "provider": "aws",
                "access_key": "ak",
                "secret_key": "sk",
                "region": "us-east-1",
            },
            "restart_instance",
        )


@pytest.mark.asyncio
async def test_aws_repair_unsupported_action(fresh_repair_history, stub_boto3):
    with pytest.raises(ValueError, match="Unsupported AWS action"):
        await cloud_repair.execute_cloud_repair(
            {
                "provider": "aws",
                "access_key": "ak",
                "secret_key": "sk",
                "region": "us-east-1",
            },
            "terminate_instance",
            instance_id="i-123",
        )


@pytest.mark.asyncio
async def test_aws_repair_missing_boto3(fresh_repair_history, missing_boto3):
    with pytest.raises(RuntimeError, match="boto3 not installed"):
        await cloud_repair.execute_cloud_repair(
            {
                "provider": "aws",
                "access_key": "ak",
                "secret_key": "sk",
                "region": "us-east-1",
            },
            "restart_instance",
            instance_id="i-123",
        )


@pytest.mark.asyncio
@pytest.mark.parametrize("action", ["restart_vm", "start_vm", "stop_vm"])
async def test_azure_repair_actions(fresh_repair_history, stub_azure, action):
    result = await cloud_repair.execute_cloud_repair(
        {
            "provider": "azure",
            "tenant_id": "t",
            "client_id": "c",
            "client_secret": "s",
            "subscription_id": "sub-1",
        },
        action,
        resource_group_name="rg-prod",
        vm_name="web-01",
    )
    assert result["success"] is True
    assert result["provider"] == "azure"
    assert result["action"] == action
    assert "web-01" in result["message"]
    history = cloud_repair.get_cloud_repair_history()
    assert len(history) == 1


@pytest.mark.asyncio
async def test_azure_repair_missing_params(fresh_repair_history, stub_azure):
    with pytest.raises(ValueError, match="subscription_id, resource_group_name and vm_name"):
        await cloud_repair.execute_cloud_repair(
            {
                "provider": "azure",
                "tenant_id": "t",
                "client_id": "c",
                "client_secret": "s",
            },
            "restart_vm",
            resource_group_name="rg-prod",
        )


@pytest.mark.asyncio
async def test_azure_repair_unsupported_action(fresh_repair_history, stub_azure):
    with pytest.raises(ValueError, match="Unsupported Azure action"):
        await cloud_repair.execute_cloud_repair(
            {
                "provider": "azure",
                "tenant_id": "t",
                "client_id": "c",
                "client_secret": "s",
                "subscription_id": "sub-1",
            },
            "scale_vm",
            resource_group_name="rg-prod",
            vm_name="web-01",
        )


@pytest.mark.asyncio
async def test_azure_repair_missing_sdk(fresh_repair_history, missing_azure):
    with pytest.raises(RuntimeError, match="azure-mgmt-compute or azure-identity"):
        await cloud_repair.execute_cloud_repair(
            {
                "provider": "azure",
                "tenant_id": "t",
                "client_id": "c",
                "client_secret": "s",
                "subscription_id": "sub-1",
            },
            "restart_vm",
            resource_group_name="rg-prod",
            vm_name="web-01",
        )


@pytest.mark.asyncio
async def test_alibaba_repair_not_supported(fresh_repair_history):
    with pytest.raises(RuntimeError, match="Alibaba Cloud repair SDK not installed"):
        await cloud_repair.execute_cloud_repair({"provider": "alibaba"}, "restart_instance")


@pytest.mark.asyncio
async def test_execute_cloud_repair_unsupported_provider(fresh_repair_history):
    with pytest.raises(ValueError, match="Unsupported cloud provider"):
        await cloud_repair.execute_cloud_repair({"provider": "gcp"}, "restart_instance")


@pytest.mark.asyncio
async def test_get_cloud_repair_history_limit(fresh_repair_history, stub_boto3, stub_azure):
    await cloud_repair.execute_cloud_repair(
        {
            "provider": "aws",
            "access_key": "ak",
            "secret_key": "sk",
            "region": "us-east-1",
        },
        "start_instance",
        instance_id="i-1",
    )
    await cloud_repair.execute_cloud_repair(
        {
            "provider": "azure",
            "tenant_id": "t",
            "client_id": "c",
            "client_secret": "s",
            "subscription_id": "sub-1",
        },
        "stop_vm",
        resource_group_name="rg",
        vm_name="vm-1",
    )
    assert len(cloud_repair.get_cloud_repair_history()) == 2
    assert cloud_repair.get_cloud_repair_history(limit=1)[0]["provider"] == "azure"


# -----------------------------------------------------------------------------
# core/config.py
# -----------------------------------------------------------------------------


def test_config_reexports_root_attributes():
    """core.config must re-export top-level configuration symbols."""
    assert hasattr(cfg, "DOCKER_HOSTS")
    # DOCKER_HOSTS is a real config attribute; it may be a list or dict.
    assert cfg.DOCKER_HOSTS is not None


def test_config_reload_failure_when_spec_is_none(monkeypatch):
    """Reloading core.config with a missing spec file must raise ImportError."""
    import importlib.util

    monkeypatch.setattr(importlib.util, "spec_from_file_location", lambda *a, **k: None)
    with pytest.raises(ImportError, match="Failed to load top-level config.py"):
        importlib.reload(cfg)


def test_config_reload_failure_when_loader_is_none(monkeypatch):
    """Reloading core.config with a spec lacking a loader must raise ImportError."""
    import importlib.util

    fake_spec = type("Spec", (), {"loader": None})()
    monkeypatch.setattr(importlib.util, "spec_from_file_location", lambda *a, **k: fake_spec)
    with pytest.raises(ImportError, match="Failed to load top-level config.py"):
        importlib.reload(cfg)


# -----------------------------------------------------------------------------
# core/cross_service_tracing.py
# -----------------------------------------------------------------------------


@pytest.fixture
def fake_tracing_manager():
    """Return a minimal tracing manager whose create_span yields a mock span."""
    m = MagicMock()
    m.create_span.return_value = MagicMock()
    return m


@pytest.fixture
def tracing_patches(monkeypatch):
    """Patch OpenTelemetry propagation functions for deterministic tests."""
    inject_mock = MagicMock(side_effect=lambda carrier: carrier.update({"traceparent": "00-test"}))
    extract_mock = MagicMock(return_value={"trace_id": "abc"})
    monkeypatch.setattr(
        tracing.trace,
        "get_current_span",
        lambda: MagicMock(get_span_context=lambda: MagicMock()),
    )
    monkeypatch.setattr(tracing.propagate, "inject", inject_mock)
    monkeypatch.setattr(tracing.propagate, "extract", extract_mock)
    return {"inject": inject_mock, "extract": extract_mock}


def test_tracing_context_inject(tracing_patches):
    headers = {}
    tracing.TracingContext().inject(headers)
    assert headers == {"traceparent": "00-test"}
    tracing_patches["inject"].assert_called_once()


def test_tracing_context_inject_no_current_context(monkeypatch, tracing_patches):
    monkeypatch.setattr(
        tracing.trace,
        "get_current_span",
        lambda: MagicMock(get_span_context=lambda: None),
    )
    headers = {}
    tracing.TracingContext().inject(headers)
    assert headers == {}
    tracing_patches["inject"].assert_not_called()


def test_tracing_context_extract(tracing_patches):
    ctx = tracing.TracingContext().extract({"traceparent": "00-test"})
    assert ctx == {"trace_id": "abc"}
    tracing_patches["extract"].assert_called_once_with({"traceparent": "00-test"})


def test_http_interceptor_success(fake_tracing_manager, tracing_patches):
    interceptor = tracing.HTTPTracingInterceptor(fake_tracing_manager)
    headers = {}
    with interceptor.trace_http_request("GET", "http://billing/api", headers=headers) as span:
        assert span is fake_tracing_manager.create_span.return_value
    fake_tracing_manager.create_span.assert_called_once_with(
        name="GET http://billing/api",
        kind=SpanKind.CLIENT,
        attributes={"http.method": "GET", "http.url": "http://billing/api"},
    )
    span = fake_tracing_manager.create_span.return_value
    span.end.assert_called_once()
    span.record_exception.assert_not_called()
    assert headers == {"traceparent": "00-test"}


def test_http_interceptor_headers_created_when_none(fake_tracing_manager, tracing_patches):
    interceptor = tracing.HTTPTracingInterceptor(fake_tracing_manager)
    with interceptor.trace_http_request("POST", "http://orders/api") as span:
        pass
    # The headers dict is created internally; propagation was invoked.
    tracing_patches["inject"].assert_called_once()


def test_http_interceptor_exception(fake_tracing_manager, tracing_patches):
    interceptor = tracing.HTTPTracingInterceptor(fake_tracing_manager)
    with pytest.raises(RuntimeError, match="boom"):
        with interceptor.trace_http_request("DELETE", "http://orders/api/1"):
            raise RuntimeError("boom")
    span = fake_tracing_manager.create_span.return_value
    span.record_exception.assert_called_once()
    span.set_status.assert_called_once()
    span.end.assert_called_once()


@pytest.mark.asyncio
async def test_http_interceptor_async(fake_tracing_manager, tracing_patches):
    interceptor = tracing.HTTPTracingInterceptor(fake_tracing_manager)
    span = await interceptor.trace_http_request_async(
        "PUT", "http://inventory/api/2", headers={"x-request-id": "42"}
    )
    assert span is fake_tracing_manager.create_span.return_value
    fake_tracing_manager.create_span.assert_called_once_with(
        name="PUT http://inventory/api/2",
        kind=SpanKind.CLIENT,
        attributes={
            "http.method": "PUT",
            "http.url": "http://inventory/api/2",
        },
    )
    tracing_patches["inject"].assert_called_once()


@pytest.mark.asyncio
async def test_http_interceptor_async_headers_none(fake_tracing_manager, tracing_patches):
    interceptor = tracing.HTTPTracingInterceptor(fake_tracing_manager)
    span = await interceptor.trace_http_request_async("PATCH", "http://inventory/api/3")
    assert span is fake_tracing_manager.create_span.return_value
    fake_tracing_manager.create_span.assert_called_once_with(
        name="PATCH http://inventory/api/3",
        kind=SpanKind.CLIENT,
        attributes={
            "http.method": "PATCH",
            "http.url": "http://inventory/api/3",
        },
    )
    tracing_patches["inject"].assert_called_once()


def test_db_interceptor_query(fake_tracing_manager):
    db = tracing.DatabaseTracingInterceptor(fake_tracing_manager)
    with db.trace_database_query("postgresql", "orders", "SELECT", "SELECT * FROM orders") as span:
        assert span is fake_tracing_manager.create_span.return_value
    fake_tracing_manager.create_span.assert_called_once_with(
        name="SELECT orders",
        kind=SpanKind.CLIENT,
        attributes={
            "db.system": "postgresql",
            "db.name": "orders",
            "db.operation": "SELECT",
            "db.statement": "SELECT * FROM orders",
        },
    )
    span = fake_tracing_manager.create_span.return_value
    span.end.assert_called_once()


def test_db_interceptor_query_exception(fake_tracing_manager):
    db = tracing.DatabaseTracingInterceptor(fake_tracing_manager)
    with pytest.raises(ValueError, match="syntax"):
        with db.trace_database_query("mysql", "logs", "INSERT", "INSERT INTO logs VALUES (1)"):
            raise ValueError("syntax error")
    span = fake_tracing_manager.create_span.return_value
    span.record_exception.assert_called_once()
    span.set_status.assert_called_once()
    span.end.assert_called_once()


@pytest.mark.asyncio
async def test_db_interceptor_query_async(fake_tracing_manager):
    db = tracing.DatabaseTracingInterceptor(fake_tracing_manager)
    span = await db.trace_database_query_async(
        "postgresql", "users", "UPDATE", "UPDATE users SET active = 1"
    )
    assert span is fake_tracing_manager.create_span.return_value


def test_mq_interceptor_publish(fake_tracing_manager, tracing_patches):
    mq = tracing.MessageQueueTracingInterceptor(fake_tracing_manager)
    headers = {}
    with mq.trace_message_publish(
        "kafka", "orders", "order.created", "msg-1", headers=headers
    ) as span:
        assert span is fake_tracing_manager.create_span.return_value
    fake_tracing_manager.create_span.assert_called_once_with(
        name="publish orders",
        kind=SpanKind.PRODUCER,
        attributes={
            "messaging.system": "kafka",
            "messaging.destination": "orders",
            "messaging.message_type": "order.created",
            "messaging.message_id": "msg-1",
        },
    )
    assert headers == {"traceparent": "00-test"}
    span = fake_tracing_manager.create_span.return_value
    span.end.assert_called_once()


def test_mq_interceptor_publish_exception(fake_tracing_manager, tracing_patches):
    mq = tracing.MessageQueueTracingInterceptor(fake_tracing_manager)
    with pytest.raises(ConnectionError, match="broker down"):
        with mq.trace_message_publish("kafka", "orders", "order.created", "msg-2"):
            raise ConnectionError("broker down")
    span = fake_tracing_manager.create_span.return_value
    span.record_exception.assert_called_once()
    span.set_status.assert_called_once()
    span.end.assert_called_once()


def test_mq_interceptor_consume(fake_tracing_manager, tracing_patches):
    mq = tracing.MessageQueueTracingInterceptor(fake_tracing_manager)
    headers = {"b3": "abc"}
    with mq.trace_message_consume(
        "rabbitmq", "events", "event.received", "msg-3", headers=headers
    ) as span:
        assert span is fake_tracing_manager.create_span.return_value
    fake_tracing_manager.create_span.assert_called_once_with(
        name="consume events",
        kind=SpanKind.CONSUMER,
        attributes={
            "messaging.system": "rabbitmq",
            "messaging.destination": "events",
            "messaging.message_type": "event.received",
            "messaging.message_id": "msg-3",
        },
    )
    tracing_patches["extract"].assert_called_once_with(headers)
    span = fake_tracing_manager.create_span.return_value
    span.end.assert_called_once()


def test_mq_interceptor_consume_no_headers(fake_tracing_manager, tracing_patches):
    mq = tracing.MessageQueueTracingInterceptor(fake_tracing_manager)
    with mq.trace_message_consume("rabbitmq", "events", "event.received", "msg-4") as span:
        pass
    tracing_patches["extract"].assert_not_called()
    span = fake_tracing_manager.create_span.return_value
    span.end.assert_called_once()


def test_mq_interceptor_consume_exception(fake_tracing_manager, tracing_patches):
    mq = tracing.MessageQueueTracingInterceptor(fake_tracing_manager)
    with pytest.raises(RuntimeError, match="bad message"):
        with mq.trace_message_consume(
            "rabbitmq", "events", "event.received", "msg-5", headers={"b3": "x"}
        ):
            raise RuntimeError("bad message")
    span = fake_tracing_manager.create_span.return_value
    span.record_exception.assert_called_once()
    span.set_status.assert_called_once()
    span.end.assert_called_once()


def test_cross_service_manager_factory_and_interceptors(fake_tracing_manager):
    mgr = tracing.get_cross_service_tracing_manager(fake_tracing_manager)
    assert isinstance(mgr, tracing.CrossServiceTracingManager)
    assert mgr.get_http_interceptor() is mgr.http_interceptor
    assert mgr.get_database_interceptor() is mgr.database_interceptor
    assert mgr.get_message_queue_interceptor() is mgr.message_queue_interceptor


def test_cross_service_manager_trace_calls_and_statistics(fake_tracing_manager):
    mgr = tracing.CrossServiceTracingManager(fake_tracing_manager)
    service_span = mgr.trace_service_call("billing", "charge")
    assert service_span is fake_tracing_manager.create_span.return_value
    internal_span = mgr.trace_internal_operation("worker", "cleanup")
    assert internal_span is fake_tracing_manager.create_span.return_value
    stats = mgr.get_statistics()
    assert stats["http_requests"] == 1
    assert stats["database_queries"] == 0
    assert stats["message_operations"] == 0
    assert stats["total_traced_operations"] == 1


# -----------------------------------------------------------------------------
# core/docker_collector.py
# -----------------------------------------------------------------------------


class FakeContainer:
    """Minimal container double for the Docker SDK."""

    def __init__(self, name, cid, status, stats=None, raise_stats=False):
        self.name = name
        self.id = cid
        self.status = status
        self._stats = stats or {}
        self._raise = raise_stats

    def stats(self, stream=False):
        if self._raise:
            raise RuntimeError("stats stream broken")
        return self._stats


class FakeContainers:
    def __init__(self, containers):
        self._containers = containers

    def list(self, all=True):
        return self._containers


class FakeDockerClient:
    def __init__(self, containers):
        self._containers = FakeContainers(containers)

    def ping(self):
        return True

    def close(self):
        return

    @property
    def containers(self):
        return self._containers


STATS_NORMAL = {
    "cpu_stats": {
        "cpu_usage": {
            "total_usage": 100_000_000,
            "percpu_usage": [0, 0, 0, 0],
        },
        "system_cpu_usage": 2_000_000_000,
    },
    "precpu_stats": {
        "cpu_usage": {"total_usage": 50_000_000},
        "system_cpu_usage": 1_000_000_000,
    },
    "memory_stats": {"usage": 128_000_000, "limit": 2_147_483_648},
    "networks": {"eth0": {"rx_bytes": 12_345, "tx_bytes": 67_890}},
}


STATS_ZERO_CPU = {
    "cpu_stats": {
        "cpu_usage": {"total_usage": 1_000, "percpu_usage": []},
        "system_cpu_usage": 1_000,
    },
    "precpu_stats": {
        "cpu_usage": {"total_usage": 500},
        "system_cpu_usage": 1_000,
    },
    "memory_stats": {},
    "networks": {},
}


def test_docker_raw_collects_metrics(monkeypatch):
    ctr = FakeContainer("web_app", "abc123def456", "running", STATS_NORMAL)
    monkeypatch.setattr(
        docker_collector.docker, "DockerClient", lambda *a, **k: FakeDockerClient([ctr])
    )
    result = docker_collector._collect_docker_raw(
        {"host": "10.0.0.5", "port": 2376, "tls": False, "version": "auto"}
    )
    assert result["host"] == "10.0.0.5"
    assert "timestamp" in result
    assert len(result["containers"]) == 1
    c = result["containers"][0]
    assert c["id"] == "abc123def456"[:12]
    assert c["name"] == "web_app"
    assert c["status"] == "running"
    # (50M / 1B) * 4 * 100 = 20.0
    assert c["cpu_percent"] == 20.0
    assert c["mem_usage"] == 128_000_000
    assert c["mem_limit"] == 2_147_483_648
    assert c["net_io"] == {"rx_bytes": 12_345, "tx_bytes": 67_890}


def test_docker_raw_zero_cpu_and_skip_broken_container(monkeypatch):
    ok = FakeContainer("ok_app", "okid123456789", "running", STATS_ZERO_CPU)
    broken = FakeContainer("broken_app", "broken123456", "running", raise_stats=True)
    monkeypatch.setattr(
        docker_collector.docker,
        "DockerClient",
        lambda *a, **k: FakeDockerClient([ok, broken]),
    )
    result = docker_collector._collect_docker_raw({"host": "10.0.0.5", "port": 2375})
    assert len(result["containers"]) == 1
    c = result["containers"][0]
    assert c["name"] == "ok_app"
    assert c["cpu_percent"] == 0.0
    assert c["mem_usage"] == 0
    assert c["mem_limit"] == 0
    assert c["net_io"] == {"rx_bytes": 0, "tx_bytes": 0}


def test_docker_raw_connection_failure(monkeypatch):
    def fail(*args, **kwargs):
        raise DockerException("connection refused")

    monkeypatch.setattr(docker_collector.docker, "DockerClient", fail)
    result = docker_collector._collect_docker_raw({"host": "192.0.2.1", "port": 2375})
    assert result == {}


def test_collect_docker_integration(monkeypatch):
    ctr = FakeContainer("worker", "xyz789uvw000", "running", STATS_NORMAL)
    monkeypatch.setattr(
        docker_collector.docker, "DockerClient", lambda *a, **k: FakeDockerClient([ctr])
    )
    result = docker_collector.collect_docker(
        {"host": "10.0.0.6", "port": 2376, "tls": False, "version": "auto"}
    )
    assert result["host"] == "10.0.0.6"
    assert len(result["containers"]) == 1
    assert result["containers"][0]["name"] == "worker"
