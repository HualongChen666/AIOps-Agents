# -*- coding: utf-8 -*-
"""Targeted functional coverage tests for core.cloud_collector,
core.workflow.engine.dsl, core.maturity_engine,
core.system_resource_optimizer and core.integration_testing_system.
"""

import asyncio  # noqa: F401  # Imported for test setup
import json  # noqa: F401  # Imported for test setup
import secrets
import sys  # noqa: F401  # Imported for test setup
import types
from contextlib import suppress
from unittest.mock import AsyncMock, MagicMock

import pytest  # noqa: F401  # Imported for test setup

import core.cloud_collector as cloud_collector
import core.integration_testing_system as its_module
import core.maturity_engine as maturity_engine
import core.system_resource_optimizer as sro_module
import core.workflow.engine.dsl as dsl_module

pytestmark = [pytest.mark.core]


# -----------------------------------------------------------------------------
# core.cloud_collector
# -----------------------------------------------------------------------------


def _install_cloud_sdk_fakes(monkeypatch, exc_provider=None):
    """Install lightweight fake cloud SDKs into sys.modules for deterministic tests."""

    # --- AWS ---
    class _FakeCloudWatchClient:
        _metrics = {
            "CPUUtilization": [
                {"Timestamp": 2, "Average": 42.5, "Unit": "Percent"},
                {"Timestamp": 1, "Average": 10.0, "Unit": "Percent"},
            ],
            "DiskReadOps": [],
        }

        def get_metric_statistics(self, **kwargs):
            if exc_provider == "aws":
                raise RuntimeError("AWS API throttled")
            return {"Datapoints": self._metrics.get(kwargs.get("MetricName"), [])}

    class _FakeBoto3Session:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def client(self, name):
            return _FakeCloudWatchClient()

    fake_boto3 = types.ModuleType("boto3")
    fake_boto3.Session = _FakeBoto3Session

    # --- Azure ---
    class _FakeCredential:
        def __init__(self, tenant_id, client_id, client_secret):
            self.tenant_id = tenant_id

    class _FakeData:
        def __init__(self, average, timestamp=None):
            self.average = average
            self.timestamp = timestamp or "2024-01-01T00:00:00Z"

    class _FakeTimeSeries:
        def __init__(self, data):
            self.data = data

    class _FakeMetric:
        def __init__(self, timeseries, unit):
            self.timeseries = timeseries
            self.unit = unit

    class _FakeQueryResponse:
        def __init__(self, metrics):
            self.metrics = metrics

    class _FakeMetricsQueryClient:
        def __init__(self, credential):
            self.credential = credential

        def query_resource(self, resource_id, metric_names, timespan, interval):
            if exc_provider == "azure":
                raise RuntimeError("Azure API throttled")
            name = metric_names[0]
            if name == "cpu_percent":
                return _FakeQueryResponse(
                    [_FakeMetric([_FakeTimeSeries([_FakeData(55.0)])], "Percent")]
                )
            return _FakeQueryResponse([_FakeMetric([], "Percent")])

    fake_azure = types.ModuleType("azure")
    fake_azure_identity = types.ModuleType("azure.identity")
    fake_azure_identity.ClientSecretCredential = _FakeCredential
    fake_azure_monitor = types.ModuleType("azure.monitor.query")
    fake_azure_monitor.MetricsQueryClient = _FakeMetricsQueryClient
    fake_azure.identity = fake_azure_identity
    fake_azure.monitor = types.ModuleType("azure.monitor")
    fake_azure.monitor.query = fake_azure_monitor

    # --- Alibaba ---
    class _FakeAcsClient:
        _datapoints = {
            "cpu_total": [{"Timestamp": 3, "Average": 77.0, "Unit": "Percent"}],
            "memory_used": [],
        }

        def __init__(self, ak, sk, region):
            self.region = region

        def do_action_with_exception(self, request):
            if exc_provider == "alibaba":
                raise RuntimeError("Alibaba API throttled")
            return json.dumps(
                {"Datapoints": self._datapoints.get(getattr(request, "_metric_name", ""), [])}
            )

    class _FakeAliyunRequestClass:
        def __init__(self, *args, **kwargs):
            pass

        def set_accept_format(self, v):
            pass

        def set_Namespace(self, v):
            pass

        def set_MetricName(self, v):
            self._metric_name = v

        def set_Dimensions(self, v):
            pass

        def set_Period(self, v):
            pass

        def set_StartTime(self, v):
            pass

        def set_EndTime(self, v):
            pass

    _FakeAliyunRequestClass.DescribeMetricListRequest = _FakeAliyunRequestClass

    fake_aliyunsdkcore = types.ModuleType("aliyunsdkcore")
    fake_aliyunsdkcore.client = types.ModuleType("aliyunsdkcore.client")
    fake_aliyunsdkcore.client.AcsClient = _FakeAcsClient

    fake_aliyunsdkcms = types.ModuleType("aliyunsdkcms")
    fake_aliyunsdkcms.request = types.ModuleType("aliyunsdkcms.request")
    fake_aliyunsdkcms.request.v20180308 = types.ModuleType("aliyunsdkcms.request.v20180308")
    fake_aliyunsdkcms.request.v20180308.DescribeMetricListRequest = _FakeAliyunRequestClass

    monkeypatch.setitem(sys.modules, "boto3", fake_boto3)
    monkeypatch.setitem(sys.modules, "azure", fake_azure)
    monkeypatch.setitem(sys.modules, "azure.identity", fake_azure_identity)
    monkeypatch.setitem(sys.modules, "azure.monitor.query", fake_azure_monitor)
    monkeypatch.setitem(sys.modules, "aliyunsdkcore", fake_aliyunsdkcore)
    monkeypatch.setitem(sys.modules, "aliyunsdkcore.client", fake_aliyunsdkcore.client)
    monkeypatch.setitem(sys.modules, "aliyunsdkcms", fake_aliyunsdkcms)
    monkeypatch.setitem(sys.modules, "aliyunsdkcms.request", fake_aliyunsdkcms.request)
    monkeypatch.setitem(
        sys.modules, "aliyunsdkcms.request.v20180308", fake_aliyunsdkcms.request.v20180308
    )

    # neutralize internal sinks / guard
    monkeypatch.setattr(cloud_collector, "push_to_loki", lambda snapshot: None)
    monkeypatch.setattr(cloud_collector, "record_collect", lambda data: None)
    monkeypatch.setattr(cloud_collector, "register_self_pid", lambda: None)


@pytest.fixture
def cloud_fakes(monkeypatch):
    _install_cloud_sdk_fakes(monkeypatch)
    return None


def test_collect_cloud_aws(cloud_fakes):
    cfg = {
        "provider": "aws",
        "access_key": "AK",
        "secret_key": "SK",
        "region": "us-east-1",
        "metrics": ["CPUUtilization", "DiskReadOps"],
        "namespace": "AWS/EC2",
        "dimensions": [{"Name": "InstanceId", "Value": "i-123"}],
    }
    result = cloud_collector.collect_cloud_provider(cfg)  # noqa: F841  # Variable for test verification
    assert result["provider"] == "aws"
    assert len(result["metrics"]) == 1
    assert result["metrics"][0]["name"] == "CPUUtilization"
    assert result["metrics"][0]["value"] == 42.5
    assert "timestamp" in result
    assert "raw" in result


def test_collect_cloud_azure(cloud_fakes):
    cfg = {
        "provider": "azure",
        "tenant_id": "t1",
        "client_id": "c1",
        "client_secret": "s1",
        "resource_id": "/subscriptions/123/resourceGroups/rg",
        "metrics": ["cpu_percent", "memory_percent"],
    }
    result = cloud_collector.collect_cloud_provider(cfg)  # noqa: F841  # Variable for test verification
    assert result["provider"] == "azure"
    assert len(result["metrics"]) == 1
    assert result["metrics"][0]["value"] == 55.0


def test_collect_cloud_alibaba(cloud_fakes):
    cfg = {
        "provider": "alibaba",
        "access_key_id": "AK",
        "access_key_secret": "SK",
        "region": "cn-hangzhou",
        "instance_id": "i-123",
        "metrics": ["cpu_total", "memory_used"],
    }
    result = cloud_collector.collect_cloud_provider(cfg)  # noqa: F841  # Variable for test verification
    assert result["provider"] == "alibaba"
    assert len(result["metrics"]) == 1
    assert result["metrics"][0]["value"] == 77.0


def test_collect_cloud_alicloud_alias(cloud_fakes):
    cfg = {
        "provider": "alicloud",
        "access_key_id": "AK",
        "access_key_secret": "SK",
        "region": "cn-hangzhou",
        "instance_id": "i-123",
        "metrics": ["cpu_total"],
    }
    result = cloud_collector.collect_cloud_provider(cfg)  # noqa: F841  # Variable for test verification
    assert result["provider"] == "alibaba"


def test_collect_cloud_unsupported(cloud_fakes):
    with pytest.raises(ValueError, match="Unsupported cloud provider"):
        cloud_collector.collect_cloud_provider({"provider": "gcp"})


def test_collect_cloud_full_pipeline(cloud_fakes):
    cfg = {
        "provider": "aws",
        "access_key": "AK",
        "secret_key": "SK",
        "region": "us-east-1",
        "metrics": ["CPUUtilization"],
    }
    result = cloud_collector.collect_cloud(cfg)  # noqa: F841  # Variable for test verification
    assert result["provider"] == "aws"
    history = cloud_collector.get_cloud_collect_history(limit=5)
    assert len(history) >= 1


def test_collect_cloud_sink_failures(cloud_fakes, monkeypatch):
    monkeypatch.setattr(
        cloud_collector, "push_to_loki", lambda s: (_ for _ in ()).throw(RuntimeError("loki down"))
    )
    monkeypatch.setattr(
        cloud_collector, "record_collect", lambda d: (_ for _ in ()).throw(RuntimeError("db down"))
    )
    monkeypatch.setattr(
        cloud_collector,
        "register_self_pid",
        lambda: (_ for _ in ()).throw(RuntimeError("guard down")),
    )
    cfg = {
        "provider": "aws",
        "access_key": "AK",
        "secret_key": "SK",
        "region": "us-east-1",
        "metrics": ["CPUUtilization"],
    }
    result = cloud_collector.collect_cloud(cfg)  # noqa: F841  # Variable for test verification
    assert result["provider"] == "aws"


def test_collect_cloud_sdk_exception(cloud_fakes, monkeypatch):
    _install_cloud_sdk_fakes(monkeypatch, exc_provider="aws")
    cfg = {
        "provider": "aws",
        "access_key": "AK",
        "secret_key": "SK",
        "region": "us-east-1",
        "metrics": ["CPUUtilization"],
    }
    result = cloud_collector.collect_cloud(cfg)  # noqa: F841  # Variable for test verification
    assert result == {}  # noqa: F841  # Variable for test verification


def test_collect_all_cloud(cloud_fakes, monkeypatch):
    monkeypatch.setattr(
        cloud_collector,
        "CLOUD_PROVIDERS",
        [
            {
                "provider": "aws",
                "access_key": "AK",
                "secret_key": "SK",
                "region": "us-east-1",
                "metrics": ["CPUUtilization"],
            },
            {
                "provider": "azure",
                "tenant_id": "t",
                "client_id": "c",
                "client_secret": "s",
                "resource_id": "r",
                "metrics": ["cpu_percent"],
            },
            {"provider": "unsupported"},
        ],
    )
    results = cloud_collector.collect_all_cloud()
    assert len(results) == 3
    assert results[0].get("provider") == "aws"
    assert results[1].get("provider") == "azure"
    assert results[2] == {}


# -----------------------------------------------------------------------------
# core.workflow.engine.dsl
# -----------------------------------------------------------------------------

VALID_YAML = """
name: deploy_pipeline
nodes:
  - id: build
    name: Build
  - id: test
    name: Test
    dependencies: [build]
  - id: deploy
    name: Deploy
    dependencies: [test]
edges:
  - from: build
    to: test
  - from: test
    to: deploy
"""


def test_dsl_parse_yaml_and_validate():
    dsl = dsl_module.WorkflowDSL()
    dag = dsl.parse_yaml(VALID_YAML)
    assert dag.name == "deploy_pipeline"
    assert set(dag.nodes) == {"build", "test", "deploy"}
    assert dsl.validate(dag) is True


def test_dsl_parse_json_workflow():
    data = {
        "name": "json_flow",
        "nodes": [
            {"id": "a", "name": "A", "config": {"timeout": 30}},
            {"id": "b", "type": "condition"},
        ],
        "edges": [{"from": "a", "to": "b", "condition": "ok"}],
    }
    dag = dsl_module.parse_json_workflow(json.dumps(data))
    assert dag.name == "json_flow"
    assert dag.nodes["b"].type == "condition"
    assert dag.nodes["b"].config == {}


def test_dsl_load_template_and_missing_fields():
    dsl = dsl_module.WorkflowDSL()
    dsl.load_template("t1", {"name": "sample"})
    assert "t1" in dsl._templates

    with pytest.raises(ValueError, match="must have 'name' field"):
        dsl.parse_yaml("nodes: []")

    with pytest.raises(ValueError, match="must have 'nodes' field"):
        dsl.parse_yaml("name: only_name")


def test_dsl_edge_and_cycle_errors():
    dsl = dsl_module.WorkflowDSL()

    with pytest.raises(ValueError, match="Edge must have 'from' and 'to' fields"):
        dsl.parse_yaml("name: bad\nnodes:\n  - id: a\nedges:\n  - to: a")

    cyclic = """
name: cyclic
nodes:
  - id: a
  - id: b
  - id: c
edges:
  - from: a
    to: b
  - from: b
    to: c
  - from: c
    to: a
"""
    with pytest.raises(ValueError, match="Workflow contains cycles"):
        dsl.parse_yaml(cyclic)


def test_dsl_validate_orphan_and_missing_dependency():
    dsl = dsl_module.WorkflowDSL()
    data = {
        "name": "orphan",
        "nodes": [
            {"id": "start"},
            {"id": "lonely"},
            {"id": "missing_dep", "dependencies": ["ghost"]},
        ],
        "edges": [{"from": "start", "to": "lonely"}],
    }
    dag = dsl_module.parse_json_workflow(json.dumps(data))
    assert dsl.validate(dag) is False

    # parse invalid json
    with pytest.raises(ValueError, match="JSON parsing failed"):
        dsl_module.parse_json_workflow("not json")

    # parse invalid yaml
    with pytest.raises(ValueError, match="YAML parsing failed"):
        dsl_module.parse_yaml_workflow("\t: bad")


# -----------------------------------------------------------------------------
# core.maturity_engine
# -----------------------------------------------------------------------------


@pytest.fixture
def maturity_mocks(monkeypatch):
    fake_alert_service = MagicMock()
    fake_alert_service.get_alerts = MagicMock(
        return_value={
            "total": 5,
            "alerts": [
                {"level": "critical"},
                {"severity": "high"},
                {"level": "info"},
                "not_a_dict",
            ],
        }
    )
    monkeypatch.setattr(maturity_engine, "alert_service", fake_alert_service)
    monkeypatch.setattr(
        maturity_engine,
        "get_repair_history",
        lambda limit=50: [
            {"success": True},
            {"success": False},
            {"success": True},
        ],
    )
    monkeypatch.setattr(
        maturity_engine,
        "get_repair_scripts",
        lambda: [
            {"name": "fix1", "description": "fix one"},
            {"name": "fix2"},
            {},
        ],
    )
    monkeypatch.setattr(
        maturity_engine,
        "get_pending_approvals",
        AsyncMock(return_value=[{"id": 1}, {"id": 2}]),
    )
    monkeypatch.setattr(
        maturity_engine,
        "get_decision_accuracy",
        lambda: {"success": True, "metrics": {"total": 100, "f1_score": 0.85}},
    )
    monkeypatch.setattr(
        maturity_engine,
        "get_cached_snapshot",
        lambda host_id=None: {
            "cpu": {"usage_percent": 45.0},
            "memory": {"usage_percent": 60.0},
            "disk": [{"used_percent": 10.0}],
            "network": {"bytes_sent": 1},
            "top_processes": [{"pid": 1}, {"pid": 2}],
        },
    )


@pytest.mark.asyncio
async def test_assess_maturity_full(maturity_mocks):
    result = await maturity_engine.assess_maturity()  # noqa: F841  # Variable for test verification
    assert "overall_score" in result
    assert "level" in result
    assert "level_name" in result
    assert len(result["dimensions"]) == 6
    assert all("recommendations" in d for d in result["dimensions"]) is False
    assert len(result["recommendations"]) > 0
    assert any(r["priority"] == "high" for r in result["recommendations"])


def test_get_dimension_metadata():
    meta = maturity_engine.get_dimension_metadata()
    assert len(meta) == 6
    assert all("maxScore" in m for m in meta)


@pytest.mark.asyncio
async def test_assess_maturity_empty_signals(monkeypatch):
    monkeypatch.setattr(maturity_engine, "alert_service", None)
    monkeypatch.setattr(maturity_engine, "get_repair_history", lambda limit=50: [])
    monkeypatch.setattr(maturity_engine, "get_repair_scripts", lambda: [])
    monkeypatch.setattr(maturity_engine, "get_pending_approvals", lambda: [])
    monkeypatch.setattr(
        maturity_engine,
        "get_decision_accuracy",
        lambda: {"success": False, "metrics": {}},
    )
    monkeypatch.setattr(maturity_engine, "get_cached_snapshot", lambda host_id=None: None)
    result = await maturity_engine.assess_maturity()  # noqa: F841  # Variable for test verification
    assert result["overall_score"] >= 0
    assert len(result["dimensions"]) == 6
    assert len(result["recommendations"]) >= 0


# -----------------------------------------------------------------------------
# core.system_resource_optimizer
# -----------------------------------------------------------------------------


def _install_optimizer_fakes(monkeypatch):
    fake_mem = types.ModuleType("core.memory_usage_optimizer")

    class _FakeMemSnap:
        used_memory_mb = 1024.0
        memory_percent = 50.0
        gc_objects = 123

    class _FakeMemoryOptimizer:
        def get_memory_snapshot(self):
            return _FakeMemSnap()

        def analyze_memory_patterns(self):
            return {"pattern": "stable"}

        def detect_memory_leaks(self):
            return [{"component": "cache", "leak_size_mb": 10.0}]

        def run_garbage_collection(self):
            return {"freed_mb": 100.0}

        def clear_caches(self):
            return {"cleared": True}

        def apply_memory_optimizations(self):
            return [{"op": "gc"}, {"op": "cache"}]

    fake_mem.MemoryUsageOptimizer = _FakeMemoryOptimizer

    fake_cpu = types.ModuleType("core.cpu_usage_optimizer")

    class _FakeCPUSnap:
        cpu_percent = 30.0
        per_cpu_percent = [25.0, 35.0]
        load_average = [0.5, 0.6, 0.7]
        process_count = 42

    class _FakeCPUOptimizer:
        def get_cpu_snapshot(self):
            return _FakeCPUSnap()

        def analyze_cpu_patterns(self):
            return {"pattern": "normal"}

        def detect_cpu_spikes(self):
            return [{"process": "worker"}]

        def apply_cpu_optimizations(self):
            return [{"op": "nice"}]

        def optimize_process_priorities(self):
            return {"adjusted": 1}

    fake_cpu.CPUUsageOptimizer = _FakeCPUOptimizer

    class _FakeSConn:
        def __init__(self, status):
            self.status = status

    class _FakeNetIO:
        bytes_sent = 1000
        bytes_recv = 2000
        packets_sent = 10
        packets_recv = 20

    fake_psutil = types.ModuleType("psutil")
    fake_psutil.net_io_counters = lambda: _FakeNetIO()
    fake_psutil.net_connections = lambda: [
        _FakeSConn("ESTABLISHED"),
        _FakeSConn("CLOSE_WAIT"),
    ]

    monkeypatch.setitem(sys.modules, "core.memory_usage_optimizer", fake_mem)
    monkeypatch.setitem(sys.modules, "core.cpu_usage_optimizer", fake_cpu)
    monkeypatch.setitem(sys.modules, "psutil", fake_psutil)


def _boom():
    raise RuntimeError("boom")


def _boom_bound(_self):
    raise RuntimeError("boom")


@pytest.fixture
def optimizer_fakes(monkeypatch):
    _install_optimizer_fakes(monkeypatch)
    return None


def test_optimizer_initialization_and_status(optimizer_fakes):
    opt = sro_module.SystemResourceOptimizer()
    assert opt.status.memory_optimization_enabled is True
    assert opt.status.cpu_optimization_enabled is True
    assert opt.status.network_optimization_enabled is True
    status = opt.get_optimization_status()
    assert status["memory_optimization_enabled"] is True


def test_optimizer_memory_and_cpu_analysis(optimizer_fakes):
    opt = sro_module.SystemResourceOptimizer()

    mem = opt.analyze_memory_usage()
    assert mem["current_usage_mb"] == 1024.0
    assert mem["leaks_detected"] == 1

    cpu = opt.analyze_cpu_usage()
    assert cpu["current_cpu_percent"] == 30.0
    assert cpu["spikes_detected"] == 1


def test_optimizer_optimizations(optimizer_fakes):
    opt = sro_module.SystemResourceOptimizer()
    mem_opt = opt.optimize_memory()
    assert mem_opt["garbage_collection"] == {"freed_mb": 100.0}
    assert mem_opt["optimizations_applied"] == 2

    cpu_opt = opt.optimize_cpu()
    assert cpu_opt["optimizations_applied"] == 1
    assert cpu_opt["priority_optimization"] == {"adjusted": 1}

    net = opt.optimize_network()
    assert net["active_connections"] == 1
    assert "recommendations" in net


def test_optimizer_unavailable_modules(monkeypatch):
    _install_optimizer_fakes(monkeypatch)
    # Force one submodule import to fail
    real_import = __builtins__["__import__"]

    def selective_import(name, *args, **kwargs):
        if name == "core.memory_usage_optimizer":
            raise ImportError("missing memory module")
        return real_import(name, *args, **kwargs)

    monkeypatch.setitem(__builtins__, "__import__", selective_import)
    opt = sro_module.SystemResourceOptimizer()
    assert opt.status.memory_optimization_enabled is False
    assert opt.analyze_memory_usage() == {"error": "Memory optimizer not available"}
    assert opt.optimize_memory() == {"error": "Memory optimizer not available"}


def test_optimizer_comprehensive_and_summary(optimizer_fakes):
    opt = sro_module.SystemResourceOptimizer()
    result = opt.run_comprehensive_optimization()  # noqa: F841  # Variable for test verification
    assert result["overall_status"] == "complete"
    assert "memory_optimization" in result
    assert "cpu_optimization" in result
    assert "network_optimization" in result

    summary = opt.get_resource_summary()
    assert "memory" in summary
    assert "cpu" in summary
    assert "network" in summary


def test_optimizer_network_error(monkeypatch):
    _install_optimizer_fakes(monkeypatch)
    fake_psutil = types.ModuleType("psutil")
    fake_psutil.net_io_counters = lambda: (_ for _ in ()).throw(RuntimeError("psutil failed"))
    fake_psutil.net_connections = lambda: []
    monkeypatch.setitem(sys.modules, "psutil", fake_psutil)
    opt = sro_module.SystemResourceOptimizer()
    net = opt.optimize_network()
    assert "error" in net

    result = opt.run_comprehensive_optimization()  # noqa: F841  # Variable for test verification
    assert result["overall_status"] == "partial"


def test_get_system_resource_optimizer(monkeypatch):
    _install_optimizer_fakes(monkeypatch)
    monkeypatch.setattr(sro_module, "_resource_optimizer", None)
    first = sro_module.get_system_resource_optimizer()
    second = sro_module.get_system_resource_optimizer()
    assert first is second


def test_optimizer_cpu_unavailable(monkeypatch):
    _install_optimizer_fakes(monkeypatch)
    real_import = __builtins__["__import__"]

    def selective_import(name, *args, **kwargs):
        if name == "core.cpu_usage_optimizer":
            raise ImportError("missing cpu module")
        return real_import(name, *args, **kwargs)

    monkeypatch.setitem(__builtins__, "__import__", selective_import)
    opt = sro_module.SystemResourceOptimizer()
    assert opt.status.cpu_optimization_enabled is False
    assert opt.analyze_cpu_usage() == {"error": "CPU optimizer not available"}
    assert opt.optimize_cpu() == {"error": "CPU optimizer not available"}


def test_optimizer_analyze_and_optimize_errors(optimizer_fakes, monkeypatch):
    opt = sro_module.SystemResourceOptimizer()
    monkeypatch.setattr(opt.memory_optimizer, "get_memory_snapshot", _boom)
    monkeypatch.setattr(opt.memory_optimizer, "run_garbage_collection", _boom)
    monkeypatch.setattr(opt.cpu_optimizer, "get_cpu_snapshot", _boom)
    monkeypatch.setattr(opt.cpu_optimizer, "apply_cpu_optimizations", _boom)
    assert "error" in opt.analyze_memory_usage()
    assert "error" in opt.optimize_memory()
    assert "error" in opt.analyze_cpu_usage()
    assert "error" in opt.optimize_cpu()


def test_optimizer_comprehensive_and_summary_errors(optimizer_fakes, monkeypatch):
    opt = sro_module.SystemResourceOptimizer()
    monkeypatch.setattr(opt, "analyze_memory_usage", _boom_bound)
    monkeypatch.setattr(opt, "optimize_memory", _boom_bound)
    monkeypatch.setattr(opt, "analyze_cpu_usage", _boom_bound)
    monkeypatch.setattr(opt, "optimize_cpu", _boom_bound)
    monkeypatch.setattr(opt, "optimize_network", _boom_bound)
    result = opt.run_comprehensive_optimization()  # noqa: F841  # Variable for test verification
    assert result["overall_status"] == "failed"
    assert "error" in result["memory_optimization"]
    assert "error" in result["cpu_optimization"]
    assert "error" in result["network_optimization"]
    summary = opt.get_resource_summary()
    assert "error" in summary["memory"]
    assert "error" in summary["cpu"]
    assert "error" in summary["network"]


def test_optimizer_comprehensive_no_suboptimizers(optimizer_fakes):
    opt = sro_module.SystemResourceOptimizer()
    opt.memory_optimizer = None
    opt.cpu_optimizer = None
    result = opt.run_comprehensive_optimization()  # noqa: F841  # Variable for test verification
    assert result["overall_status"] == "partial"
    assert result["memory_optimization"] is None
    assert result["cpu_optimization"] is None
    assert "network_optimization" in result


# -----------------------------------------------------------------------------
# core.integration_testing_system
# -----------------------------------------------------------------------------


def _install_its_helpers(monkeypatch):
    real_sleep = asyncio.sleep

    async def fake_sleep(delay):
        return await real_sleep(0)

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    class _FixedRandom:
        _value = 0.9

        def __init__(self, *args, **kwargs):
            pass

        def random(self):
            return _FixedRandom._value

        def uniform(self, a, b):
            return 80.0

    monkeypatch.setattr(secrets, "SystemRandom", _FixedRandom)


@pytest.fixture
def its_helpers(monkeypatch):
    _install_its_helpers(monkeypatch)
    return None


@pytest.mark.asyncio
async def test_its_register_and_run_test_pass(its_helpers):
    system = its_module.get_integration_testing_system()
    new_test = its_module.IntegrationTest(
        test_id="health_probe",
        test_name="Health Probe",
        test_type=its_module.TestType.SERVICE_TEST,
        test_suite="service_tests",
    )
    system.register_test(new_test)
    assert "health_probe" in system.integration_tests

    exec_id = await system.run_test("health_probe")
    assert exec_id.startswith("exec_health_probe_")
    await system._wait_for_execution(exec_id)
    status = system.get_execution_status(exec_id)
    assert status["passed"] is True
    assert status["coverage"] == 80.0


@pytest.mark.asyncio
async def test_its_run_test_failure(its_helpers, monkeypatch):
    class _FailingRandom:
        def __init__(self, *args, **kwargs):
            pass

        def random(self):
            return 0.1

        def uniform(self, a, b):
            return 70.0

    monkeypatch.setattr(secrets, "SystemRandom", _FailingRandom)
    system = its_module.get_integration_testing_system()
    exec_id = await system.run_test("api_user_crud")
    await system._wait_for_execution(exec_id)
    status = system.get_execution_status(exec_id)
    assert status["failed"] is True
    assert status["error_message"] == "Test assertion failed"


@pytest.mark.asyncio
async def test_its_run_suite_and_report(its_helpers):
    system = its_module.get_integration_testing_system()
    exec_ids = await system.run_suite("api_suite")
    assert len(exec_ids) == 2
    for eid in exec_ids:
        assert system.get_execution_status(eid)["passed"] is True

    report = await system.generate_test_report("api_suite")
    assert report["summary"]["total"] == 2
    assert report["summary"]["passed"] == 2
    assert report["summary"]["pass_rate"] == 1.0
    assert report["suite_id"] == "api_suite"


@pytest.mark.asyncio
async def test_its_generate_report_no_suite(its_helpers):
    system = its_module.get_integration_testing_system()
    report = await system.generate_test_report("missing_suite")
    assert report["summary"]["total"] == 0


def test_its_register_suite_and_statistics():
    system = its_module.get_integration_testing_system()
    suite = its_module.TestSuite(
        suite_id="custom",
        suite_name="Custom Suite",
        description="custom",
        tests=["api_user_crud"],
    )
    system.register_suite(suite)
    assert "custom" in system.test_suites
    stats = system.get_statistics()
    assert stats["total_tests"] >= 6
    assert stats["total_suites"] >= 5


def test_its_get_execution_status_missing():
    system = its_module.get_integration_testing_system()
    assert system.get_execution_status("nope") is None


@pytest.mark.asyncio
async def test_its_run_test_not_found_or_disabled():
    system = its_module.get_integration_testing_system()
    with pytest.raises(ValueError, match="Test not found"):
        await system.run_test("missing")

    disabled = its_module.IntegrationTest(
        test_id="disabled_test",
        test_name="Disabled",
        test_type=its_module.TestType.SERVICE_TEST,
        test_suite="x",
        enabled=False,
    )
    system.register_test(disabled)
    with pytest.raises(ValueError, match="Test is not enabled"):
        await system.run_test("disabled_test")


@pytest.mark.asyncio
async def test_its_auto_run_disabled():
    system = its_module.get_integration_testing_system({"auto_run": False})
    result = await system.start_auto_run()  # noqa: F841  # Variable for test verification
    assert result is None


@pytest.mark.asyncio
async def test_its_auto_run_enabled(its_helpers):
    system = its_module.get_integration_testing_system({"auto_run": True, "run_interval": 86400})
    await system.start_auto_run()
    # yield to let the auto loop run at least one pass
    for _ in range(20):
        if system.get_statistics()["total_executions"] > 0:
            break
        await asyncio.sleep(0)
    # cancel all background tasks except the current test
    current = asyncio.current_task()
    for task in asyncio.all_tasks():
        if task is not current:
            task.cancel()
    others = [t for t in asyncio.all_tasks() if t is not current]
    with suppress(asyncio.CancelledError):
        if others:
            await asyncio.gather(*others, return_exceptions=True)
    assert system.get_statistics()["total_executions"] > 0
