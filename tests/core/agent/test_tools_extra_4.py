# -*- coding: utf-8 -*-
"""Additional coverage tests for core/agent/tools.py default tool implementations."""

import asyncio
import sys
import types
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

import core.agent.observability_client as oc
import core.agent.tools as tools
from core.agent.tools import (
    Tool,
    ToolCategory,
    ToolExecutor,
    ToolRegistry,
    create_tool_executor,
    create_tool_registry,
)

pytestmark = [pytest.mark.core]


class _FakeSubAgentDispatcher:
    def __init__(self, *args, **kwargs):
        pass

    def dispatch(self, *args, **kwargs):
        result = types.SimpleNamespace(to_dict=lambda: {"agent_id": "1", "status": "ok"})
        return result

    def shutdown(self, *args, **kwargs):
        pass


def _prom_value():
    return {"data": {"result": [{"value": [0, "10"]}]}}


def _patch_observability(monkeypatch):
    monkeypatch.setattr(oc, "get_prometheus_url", lambda: "http://prom")
    monkeypatch.setattr(oc, "get_kubernetes_api_url", lambda: "http://k8s")
    monkeypatch.setattr(oc, "get_change_events_url", lambda: "http://change")
    monkeypatch.setattr(oc, "query_prometheus", lambda q: _prom_value())
    monkeypatch.setattr(oc, "query_prometheus_range", lambda q, s, e, step="15s": _prom_value())
    monkeypatch.setattr(
        oc,
        "query_service_metrics",
        lambda s, h: {
            "request_rate": 10.0,
            "error_rate": 0.01,
            "latency_p95": 100.0,
            "latency_p99": 200.0,
            "latency_p50": 50.0,
            "connection_pool_usage": 0.5,
        },
    )
    monkeypatch.setattr(
        oc,
        "query_network_metrics",
        lambda t, d=60: {
            "packet_loss_percent": 0.0,
            "latency_ms": 10.0,
            "dns_resolution_error_rate": 0.0,
        },
    )
    monkeypatch.setattr(oc, "query_kubernetes_events", lambda ns, fs=None, limit=100: [{
        "type": "Warning", "reason": "OOMKilled", "message": "oom", "involvedObject": {"name": "pod", "kind": "Pod"},
        "metadata": {"namespace": "default"}, "lastTimestamp": "t",
    }])
    monkeypatch.setattr(
        oc,
        "query_kubernetes_pod",
        lambda pod, ns="default": {"available": True, "phase": "Running", "last_state": {}},
    )
    monkeypatch.setattr(
        oc,
        "query_kubernetes_node",
        lambda node: {"available": True, "conditions": {"Ready": "True"}},
    )
    monkeypatch.setattr(oc, "query_change_events", lambda t, h: [{"type": "deploy", "target": t, "timestamp": 9999999999}])


def _patch_external_modules(monkeypatch):
    hyp = types.SimpleNamespace(
        root_cause="network",
        confidence=0.85,
        expected_observations=["packet loss"],
        missing_data=[],
        verification_status="verified",
        evidence=["metric"],
    )
    rci = types.SimpleNamespace(
        topology_graph={"svc": ["db"], "api": ["svc"]},
        analyze_root_causes_enhanced=AsyncMock(return_value=[hyp]),
    )
    monkeypatch.setitem(sys.modules, "core.root_cause_intelligence", types.SimpleNamespace(root_cause_intelligence_engine=rci))
    monkeypatch.setitem(sys.modules, "core.alert_engine", types.SimpleNamespace(
        alert_history=[{
            "title": "svc down", "desc": "error", "host": "svc", "source": "svc", "level": "critical", "raw_time": "t",
        }]
    ))
    monkeypatch.setitem(
        sys.modules,
        "core.config_manager",
        types.SimpleNamespace(config_manager=types.SimpleNamespace(_audit_log=[{
            "timestamp": 9999999999, "change": "svc", "details": {"x": 1}, "type": "deploy",
        }])),
    )
    fake_mgr = MagicMock()
    fake_mgr.get_service_metrics = lambda service, time_range: [types.SimpleNamespace(
        metric_name="cpu", value=0.5, timestamp="t"
    )]
    monkeypatch.setitem(
        sys.modules,
        "core.service_monitoring_manager",
        types.SimpleNamespace(get_service_monitoring_manager=lambda: fake_mgr),
    )
    monkeypatch.setitem(
        sys.modules,
        "core.agent.subagent",
        types.SimpleNamespace(SubAgentDispatcher=_FakeSubAgentDispatcher),
    )


def _patch_system(monkeypatch):
    monkeypatch.setattr("httpx.get", lambda *a, **k: MagicMock(status_code=200))
    monkeypatch.setattr("shutil.which", lambda name: f"/bin/{name}")
    monkeypatch.setattr("subprocess.run", lambda *a, **k: MagicMock(returncode=0, stderr=""))


@pytest.fixture
def patched_executor(monkeypatch):
    _patch_observability(monkeypatch)
    _patch_external_modules(monkeypatch)
    _patch_system(monkeypatch)
    monkeypatch.setenv("FORCE_REPAIR_COMMANDS", "1")
    executor = create_tool_executor()
    return executor


def test_create_tool_executor_and_registry():
    registry = create_tool_registry()
    assert isinstance(registry, ToolRegistry)
    executor = create_tool_executor()
    assert isinstance(executor, ToolExecutor)
    assert executor.dry_run is False


def test_execute_all_default_tools(patched_executor):
    executor = patched_executor
    results = {}

    results["collect_metrics"] = executor.execute_tool("collect_metrics", target="localhost", duration=30)
    results["collect_service_metrics"] = executor.execute_tool("collect_service_metrics", service_name="api", time_range_hours=2)
    results["collect_network_metrics"] = executor.execute_tool("collect_network_metrics", target="gateway", duration=60)
    results["collect_change_events"] = executor.execute_tool("collect_change_events", target="svc", hours=6)
    results["collect_kubernetes_events"] = executor.execute_tool("collect_kubernetes_events", namespace="default", limit=10)
    results["collect_container_metrics"] = executor.execute_tool("collect_container_metrics", pod_name="pod", namespace="default")
    results["collect_host_metrics"] = executor.execute_tool("collect_host_metrics", node_name="node1")
    results["collect_database_metrics"] = executor.execute_tool("collect_database_metrics", database="db", time_range_hours=2)
    results["collect_correlated_alerts"] = executor.execute_tool("collect_correlated_alerts", service="svc", limit=5)
    results["collect_topology"] = executor.execute_tool("collect_topology", service="svc")
    results["analyze_anomaly"] = executor.execute_tool("analyze_anomaly", data=[1, 2, 3, 4, 100], threshold=0.5, method="transformer")
    results["root_cause_analysis"] = executor.execute_tool(
        "root_cause_analysis",
        alert_id="a1",
        alert={"id": "a1", "title": "cpu"},
        metrics_data={"cpu": 0.9},
        correlated_alerts=[{"title": "x"}],
        change_events=[{"type": "deploy"}],
        verification_data={"cpu": 0.5},
    )
    results["restart_service"] = executor.execute_tool("restart_service", service_name="nginx", timeout=30)
    results["scale_service"] = executor.execute_tool("scale_service", service_name="api", replicas=2)
    results["check_health"] = executor.execute_tool("check_health", target="http://localhost")
    results["run_diagnostic"] = executor.execute_tool("run_diagnostic", target="http://localhost", type="basic")
    results["dispatch_subagent"] = executor.execute_tool(
        "dispatch_subagent",
        goal="investigate",
        context={"alert": "x"},
        available_tools=["collect_metrics"],
        role="worker",
        wait=True,
    )

    assert all(isinstance(v, (dict, list, str)) for v in results.values())
    assert results["collect_metrics"]["cpu_usage"] is not None
    assert results["restart_service"]["status"] in ("restarted", "simulated")
    assert results["scale_service"]["status"] in ("scaled", "simulated")
    assert results["check_health"]["healthy"] is True
    assert results["root_cause_analysis"]["method"] == "causal"
    assert results["dispatch_subagent"]["status"] == "ok"

    stats = executor.get_execution_statistics()
    assert stats["total"] == len(results)
    assert stats["successful"] == len(results)


def test_check_health_socket_failure(monkeypatch):
    monkeypatch.setattr("httpx.get", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("bad")))
    monkeypatch.setattr("socket.create_connection", lambda *a, **k: (_ for _ in ()).throw(OSError("refused")))
    executor = create_tool_executor()
    result = executor.execute_tool("check_health", target="localhost:12345")
    assert result["healthy"] is False
    assert result["status"] == "error"


def test_collect_logs(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    (log_dir / "test.log").write_text("INFO hello\nDEBUG world\nINFO again\n")

    executor = create_tool_executor()
    result = executor.execute_tool("collect_logs", service="test", level="INFO", lines=10)
    assert isinstance(result, list)
    assert all("INFO" in line for line in result)


def test_execute_with_auto_selection_infers_params(monkeypatch):
    _patch_external_modules(monkeypatch)
    _patch_system(monkeypatch)
    monkeypatch.setattr(oc, "get_prometheus_url", lambda: None)
    monkeypatch.setenv("FORCE_REPAIR_COMMANDS", "0")

    executor = create_tool_executor()
    result = executor.execute_with_auto_selection("collect logs", {"service_name": "test"})
    assert isinstance(result, list)

    result2 = executor.execute_with_auto_selection("collect service metrics", {"target": "api"})
    assert isinstance(result2, dict)

    result3 = executor.execute_with_auto_selection("scale api service", {"service_name": "api", "replicas": 3})
    assert isinstance(result3, dict)


def test_tool_direct_validation_and_clamp():
    tool = Tool(
        name="range",
        description="range",
        category=ToolCategory.ANALYSIS,
        function=lambda duration: duration,
        required_params=["duration"],
    )
    assert tool.execute(duration=5) == 10
    assert tool.execute(duration=300) == 300


def test_tool_to_dict_and_registry_search():
    registry = create_tool_registry()
    tool = registry.get_tool("collect_metrics")
    d = tool.to_dict()
    assert d["name"] == "collect_metrics"
    assert "parameters" in d
    assert registry.search_tools("metrics")[0].name == "collect_metrics"


def test_select_tool_explicit_branches():
    executor = create_tool_executor()
    selector = executor.selector
    expected = {
        "collect logs": "collect_logs",
        "collect metrics for localhost": "collect_metrics",
        "detect anomaly": "analyze_anomaly",
        "root cause analysis": "root_cause_analysis",
        "restart nginx": "restart_service",
        "scale api to 3": "scale_service",
        "recent changes": "collect_change_events",
        "related alerts": "collect_correlated_alerts",
        "sli for api": "collect_service_metrics",
        "network packet loss": "collect_network_metrics",
        "database slow query": "collect_database_metrics",
        "kubernetes pod oom": "collect_kubernetes_events",
        "host node failure": "collect_kubernetes_events",
        "查看拓扑": "collect_topology",
        "健康检查": "check_health",
    }
    for task, expected_name in expected.items():
        tool = selector.select_tool(task, {})
        assert tool is not None, f"No tool for: {task}"
        assert tool.name == expected_name, f"Wrong tool for {task}: {tool.name}"
    assert selector.select_tool("do something weird", {}) is None


def test_tool_validate_value_types():
    tool = Tool(
        name="probe",
        description="probe",
        category=ToolCategory.ANALYSIS,
        function=lambda ctx=None, items=None, note=None: (ctx, items, note),
        required_params=[],
        optional_params=["ctx", "items", "note"],
    )
    # nested dict validation (non-data-container)
    tool.execute(ctx={"foo": "bar", "nested": {"a": 1}, "flag": True})
    # list validation
    tool.execute(items=["a", "b", "c"])
    # string with custom pattern
    tool2 = Tool(
        name="pattern",
        description="pattern",
        category=ToolCategory.ANALYSIS,
        function=lambda custom: custom,
        required_params=["custom"],
        param_patterns={"custom": __import__("re").compile(r"^[a-z]+$")},
    )
    tool2.execute(custom="abc")
    with pytest.raises(ValueError, match="does not match allowed pattern"):
        tool2.execute(custom="ABC")


def test_tool_missing_required():
    tool = Tool(
        name="req",
        description="req",
        category=ToolCategory.ANALYSIS,
        function=lambda x: x,
        required_params=["x"],
    )
    with pytest.raises(ValueError, match="Missing required parameters"):
        tool.execute()


def test_tool_selector_all_categories(patched_executor):
    selector = patched_executor.selector
    cases = [
        "collect system logs",
        "collect metrics for host",
        "detect anomaly in data",
        "root cause analysis",
        "restart nginx",
        "scale api to 3",
        "recent changes for host",
        "related alerts for svc",
        "sli for api",
        "network packet loss",
        "database slow query",
        "kubernetes pod OOMKilled",
        "host node failure",
        "topology for svc",
        "health check http://x",
    ]
    for task in cases:
        tool = selector.select_tool(task, {})
        assert tool is not None, f"No tool for {task}"

    chain = selector.select_tools_for_chain(["collect logs", "restart service"], {})
    assert len(chain) == 2


def test_execute_chain_and_failure(monkeypatch, patched_executor):
    def _bad():
        raise ValueError("boom")

    patched_executor.registry.register(
        Tool(name="bad_tool", description="bad", category=ToolCategory.ANALYSIS, function=_bad)
    )
    results = patched_executor.execute_chain([
        ("collect_metrics", {"target": "localhost"}),
        ("bad_tool", {}),
    ])
    assert len(results) == 1
    assert patched_executor.get_execution_statistics()["failed"] == 1


def test_execute_tool_not_found(patched_executor):
    with pytest.raises(ValueError, match="Tool not found"):
        patched_executor.execute_tool("missing_tool")


def test_command_guard_rejects_dangerous_command(monkeypatch):
    from core.command_guard import RiskLevel
    monkeypatch.setattr(tools, "_analyze_command", lambda cmd: {"risk_level": RiskLevel.HIGH, "reason": "dangerous"})
    monkeypatch.setattr(tools, "COMMAND_GUARD_AVAILABLE", True)
    monkeypatch.setattr(tools, "RiskLevel", RiskLevel)
    executor = create_tool_executor()
    with pytest.raises(ValueError, match="blocked by command_guard"):
        executor.execute_tool("root_cause_analysis", alert_id="a1", alert={"command": "rm -rf /"})


def test_tool_validate_value_branches(monkeypatch):
    from core.command_guard import RiskLevel
    monkeypatch.setattr(tools, "_analyze_command", lambda cmd: {"risk_level": RiskLevel.LOW, "reason": "ok"})
    monkeypatch.setattr(tools, "COMMAND_GUARD_AVAILABLE", True)
    monkeypatch.setattr(tools, "RiskLevel", RiskLevel)

    # bool
    tb = Tool("bool", "", ToolCategory.ANALYSIS, lambda wait: wait, required_params=["wait"])
    with pytest.raises(ValueError, match="must be a boolean"):
        tb.execute(wait="yes")

    # int invalid / out of range
    ti = Tool("int", "", ToolCategory.ANALYSIS, lambda duration: duration, required_params=["duration"])
    with pytest.raises(ValueError, match="must be an integer"):
        ti.execute(duration="abc")
    with pytest.raises(ValueError, match="between"):
        ti.execute(duration=0)

    # float invalid / out of range
    tf = Tool("float", "", ToolCategory.ANALYSIS, lambda threshold: threshold, required_params=["threshold"])
    with pytest.raises(ValueError, match="must be a number"):
        tf.execute(threshold="abc")
    with pytest.raises(ValueError, match="between"):
        tf.execute(threshold=2.0)

    # list string validation
    tl = Tool("list", "", ToolCategory.ANALYSIS, lambda tools: tools, required_params=["tools"])
    with pytest.raises(ValueError, match="exceeds maximum length"):
        tl.execute(tools="a" * 2000)
    with pytest.raises(ValueError, match="disallowed characters"):
        tl.execute(tools="a;b")

    # list of items with safe-text failure
    ti2 = Tool("items", "", ToolCategory.ANALYSIS, lambda items: items, required_params=["items"])
    with pytest.raises(ValueError, match="contains disallowed characters"):
        ti2.execute(items=["a#b"])

    # data container list too long
    tdc = Tool("dc", "", ToolCategory.ANALYSIS, lambda alert: alert, required_params=["alert"])
    with pytest.raises(ValueError, match="exceeds maximum list length"):
        tdc.execute(alert=["x"] * 10001)

    # nested depth exceeded
    tctx = Tool("ctx", "", ToolCategory.ANALYSIS, lambda ctx: ctx, required_params=["ctx"])
    with pytest.raises(ValueError, match="exceeds maximum nested depth"):
        tctx.execute(ctx={"a": {"b": {"c": {"d": {}}}}})

    # string empty / too long / path traversal / shell / pattern mismatch
    tp = Tool("pattern", "", ToolCategory.ANALYSIS, lambda target: target, required_params=["target"])
    with pytest.raises(ValueError, match="cannot be empty"):
        tp.execute(target="")
    with pytest.raises(ValueError, match="exceeds maximum length"):
        tp.execute(target="x" * 200)
    with pytest.raises(ValueError, match="path traversal"):
        tp.execute(target="../x")
    with pytest.raises(ValueError, match="dangerous characters"):
        tp.execute(target="a;b")
    with pytest.raises(ValueError, match="does not match allowed pattern"):
        tp.execute(target="x y")

    # default safe text whitelist
    tt = Tool("text", "", ToolCategory.ANALYSIS, lambda note: note, required_params=["note"])
    with pytest.raises(ValueError, match="contains disallowed characters"):
        tt.execute(note="x#y")

    # dict with command guard (HIGH and LOW)
    tcmd = Tool("cmd", "", ToolCategory.ANALYSIS, lambda ctx: ctx, required_params=["ctx"])
    monkeypatch.setattr(tools, "_analyze_command", lambda cmd: {"risk_level": RiskLevel.HIGH, "reason": "dangerous"})
    with pytest.raises(ValueError, match="blocked by command_guard"):
        tcmd.execute(ctx={"command": "rm -rf /"})
    monkeypatch.setattr(tools, "_analyze_command", lambda cmd: {"risk_level": RiskLevel.LOW, "reason": "ok"})
    tcmd.execute(ctx={"command": "ls", "nested": {"a": "b"}, "flag": True})

    # invalid timeout and dry run
    tto = Tool("to", "", ToolCategory.ANALYSIS, lambda x: x, required_params=["x"])
    with pytest.raises(ValueError, match="Invalid timeout value"):
        tto.execute(x=1, timeout="abc")
    tdr = Tool("dr", "", ToolCategory.ANALYSIS, lambda x: x, required_params=["x"])
    out = tdr.execute(x=1, dry_run=True)
    assert out["dry_run"] is True


def test_tool_registry_and_executor_edge_cases(monkeypatch):
    # approval manager / registry approval flows
    reg = ToolRegistry(approval_required=True)
    t = Tool("x", "", ToolCategory.ANALYSIS, lambda: 1, required_params=[])
    with pytest.raises(PermissionError, match="requires approval"):
        reg.register(t)
    reg.approve_tool("x", "me")
    reg.register(t)
    assert reg.is_tool_approved("x")
    assert reg.request_tool_approval("x", "me").startswith("approval_x")
    assert reg.get_tool("x") is t
    assert reg.get_tool("missing") is None
    assert t in reg.list_tools(ToolCategory.ANALYSIS)
    assert t in reg.search_tools("x")
    reg.unregister("x")
    assert reg.get_tool("x") is None

    # env-based approval
    monkeypatch.setenv("AIOPS_TOOL_REGISTRATION_APPROVAL_REQUIRED", "true")
    reg2 = ToolRegistry()
    assert reg2.approval_manager.approval_required is True

    # Disable env-based approval for the remaining registries in this test
    monkeypatch.setenv("AIOPS_TOOL_REGISTRATION_APPROVAL_REQUIRED", "false")

    # retry for monitoring timeout and no-retry for execution
    monkeypatch.setattr("core.agent.tools.time.sleep", lambda x: None)
    attempts = [0]
    def flaky():
        attempts[0] += 1
        if attempts[0] == 1:
            raise asyncio.TimeoutError("timeout")
        return "ok"

    ft = Tool("flaky", "", ToolCategory.MONITORING, function=flaky, required_params=[])
    reg3 = ToolRegistry()
    reg3.register(ft)
    executor = ToolExecutor(reg3, retry_policy={"max_retries": 1, "backoff": [0, 0]})
    assert executor.execute_tool("flaky") == "ok"
    assert attempts[0] == 2

    def boom():
        raise RuntimeError("boom")

    bt = Tool("boom", "", ToolCategory.EXECUTION, function=boom, required_params=[])
    reg3.register(bt)
    with pytest.raises(RuntimeError, match="boom"):
        executor.execute_tool("boom")

    # sanitize
    sanitized = executor._sanitize_params({
        "password": "secret",
        "user": "me",
        "config": {"api_key": "k"},
        "items": [{"token": "t", "x": 1}],
    })
    assert sanitized["password"] == "***"
    assert sanitized["config"]["api_key"] == "***"
    assert sanitized["items"][0]["token"] == "***"
    assert sanitized["items"][0]["x"] == 1


def test_default_tool_branches(patched_executor, monkeypatch):
    executor = patched_executor

    # analyze_anomaly empty and threshold method
    assert executor.execute_tool("analyze_anomaly", data=[], method="transformer")["is_anomaly"] is False
    assert executor.execute_tool("analyze_anomaly", data=[5.0, 1.0, 0.1], method="threshold", threshold=0.5)["is_anomaly"] is False

    # collect_metrics exception fallback
    monkeypatch.setattr(oc, "get_prometheus_url", lambda: "http://prom")
    monkeypatch.setattr(oc, "query_prometheus_range", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("fail")))
    result = executor.execute_tool("collect_metrics", target="host")
    assert "No Prometheus integration" in result["note"]

    # collect_service_metrics fallback with no prom / no manager
    monkeypatch.setattr(oc, "get_prometheus_url", lambda: None)
    monkeypatch.setitem(sys.modules, "core.service_monitoring_manager", None)
    result = executor.execute_tool("collect_service_metrics", service_name="svc")
    assert result["metrics"]["request_rate"] == "unknown"

    # collect_change_events external exception + non-dict local entry
    monkeypatch.setattr(oc, "query_change_events", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("fail")))
    monkeypatch.setitem(sys.modules, "core.config_manager", types.SimpleNamespace(config_manager=types.SimpleNamespace(_audit_log=["bad"])))
    result = executor.execute_tool("collect_change_events", target="svc", hours=1)
    assert isinstance(result, list)

    # collect_kubernetes_events namespace all path and exception path
    monkeypatch.setattr(oc, "query_kubernetes_events", lambda ns, fs=None, limit=100: [] if ns is None else (_ for _ in ()).throw(RuntimeError("fail")))
    assert executor.execute_tool("collect_kubernetes_events", namespace="all", limit=5) == []
    assert executor.execute_tool("collect_kubernetes_events", namespace="default") == []

    # container/host/database metrics with provided data
    assert executor.execute_tool("collect_container_metrics", pod_name="pod", namespace="default", container_metrics={"cpu": 0.5})["cpu"] == 0.5
    assert executor.execute_tool("collect_host_metrics", node_name="node", host_metrics={"cpu": 0.5})["cpu"] == 0.5
    assert executor.execute_tool("collect_database_metrics", database="db", database_metrics={"slow": 1})["slow"] == 1

    # collect_topology import failure
    monkeypatch.setitem(sys.modules, "core.root_cause_intelligence", None)
    result = executor.execute_tool("collect_topology", service="svc")
    assert "Topology engine not populated" in result["note"]

    # collect_correlated_alerts exception
    monkeypatch.setitem(sys.modules, "core.alert_engine", types.SimpleNamespace(alert_history=object()))
    assert executor.execute_tool("collect_correlated_alerts", service="svc") == []

    # run_diagnostic unhealthy path
    monkeypatch.setattr("httpx.get", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("bad")))
    monkeypatch.setattr("socket.create_connection", lambda *a, **k: (_ for _ in ()).throw(OSError("bad")))
    result = executor.execute_tool("run_diagnostic", target="bad", type="basic")
    assert result["status"] == "unhealthy"

    # restart/scale simulated when binaries not available
    monkeypatch.setattr("shutil.which", lambda name: None)
    assert executor.execute_tool("restart_service", service_name="nginx")["status"] == "simulated"
    assert executor.execute_tool("scale_service", service_name="api", replicas=2)["status"] == "simulated"

    # network metrics exception fallback
    monkeypatch.setattr(oc, "query_network_metrics", lambda t, d=60: (_ for _ in ()).throw(RuntimeError("fail")))
    result = executor.execute_tool("collect_network_metrics", target="gw", duration=60)
    assert "Network metric collection requires" in result["note"]

    # database metrics no prom fallback
    monkeypatch.setattr(oc, "get_prometheus_url", lambda: None)
    result = executor.execute_tool("collect_database_metrics", database="db")
    assert "No Prometheus database metrics" in result["note"]

    # container / host fallback when k8s and prom unavailable
    monkeypatch.setattr(oc, "get_prometheus_url", lambda: None)
    monkeypatch.setattr(oc, "query_kubernetes_pod", lambda p, ns: {"available": False})
    result = executor.execute_tool("collect_container_metrics", pod_name="pod", namespace="default")
    assert "No Kubernetes/Prometheus" in result["note"]
    monkeypatch.setattr(oc, "query_kubernetes_node", lambda n: {"available": False})
    result = executor.execute_tool("collect_host_metrics", node_name="node")
    assert "No Kubernetes/Prometheus" in result["note"]

    # execute_with_auto_selection no tool and parameter inference
    with pytest.raises(ValueError, match="No tool found for task"):
        executor.execute_with_auto_selection("banana", {})
    result = executor.execute_with_auto_selection("detect anomaly", {"metrics": [1, 2, 10]})
    assert result["method"] == "transformer"
    from core.command_guard import RiskLevel
    monkeypatch.setattr(tools, "_analyze_command", lambda cmd: {"risk_level": RiskLevel.HIGH, "reason": "dangerous"})
    monkeypatch.setattr(tools, "COMMAND_GUARD_AVAILABLE", True)
    monkeypatch.setattr(tools, "RiskLevel", RiskLevel)
    executor = create_tool_executor()
    with pytest.raises(ValueError, match="blocked by command_guard"):
        executor.execute_tool("root_cause_analysis", alert_id="a1", alert={"command": "rm -rf /"})
