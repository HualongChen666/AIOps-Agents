# -*- coding: utf-8 -*-
"""Functional coverage tests for core batch 10-c modules."""

import asyncio  # noqa: F401  # Imported for test setup
import datetime
import shutil
from dataclasses import dataclass
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest  # noqa: F401  # Imported for test setup

pytestmark = [pytest.mark.core]


# ---------------------------------------------------------------------------
# Visualizer fixtures / helpers
# ---------------------------------------------------------------------------
@dataclass
class _FakeWorkflowNode:
    """Minimal concrete workflow node for visualizer tests."""

    name: str
    node_type: str = "base"
    config: dict = None  # type: ignore[assignment]

    def __post_init__(self):
        if self.config is None:
            self.config = {}

    async def execute(self, ctx):
        return f"executed {self.name}"


@pytest.fixture
def sample_workflow():
    from core.ai.langgraph.workflow import Workflow

    wf = Workflow("test-wf", "sample workflow")
    wf.add_node(_FakeWorkflowNode("start-node", "start"))
    wf.add_node(_FakeWorkflowNode("decide node", "condition"))
    wf.add_node(_FakeWorkflowNode("end-node", "end"))
    wf.add_edge("start-node", "decide node")
    wf.add_edge("decide node", "end-node", condition=lambda ctx: True)
    wf.set_start_node("start-node")
    wf.add_end_node("end-node")
    return wf


@pytest.fixture
def visualizer_module():
    import core.ai.langgraph.visualizer as vis

    return vis


@pytest.mark.asyncio
async def test_visualizer_to_mermaid(visualizer_module, sample_workflow):
    mermaid = visualizer_module.WorkflowVisualizer.to_mermaid(sample_workflow)
    assert "graph TD" in mermaid
    assert "start-node" in mermaid
    assert "end-node" in mermaid


def test_visualizer_to_graphviz(visualizer_module, sample_workflow):
    dot = visualizer_module.WorkflowVisualizer.to_graphviz(sample_workflow)
    assert dot.startswith("digraph workflow {")
    assert "start-node" in dot
    assert "end-node" in dot
    assert "lightgreen" in dot
    assert "lightblue" in dot
    assert "decide_node" in dot


def test_visualizer_to_ascii(visualizer_module, sample_workflow):
    ascii_art = visualizer_module.WorkflowVisualizer.to_ascii(sample_workflow)
    assert "Workflow: test-wf" in ascii_art
    assert "[start] start-node" in ascii_art
    assert "[condition] decide node" in ascii_art
    assert "[end] end-node" in ascii_art
    assert "start-node -> end-node" not in ascii_art  # edge uses from/to exactly
    assert "decide node -> end-node" in ascii_art


@pytest.mark.asyncio
async def test_visualizer_render_mermaid_to_file(visualizer_module, sample_workflow, tmp_path):
    out = tmp_path / "workflow.mmd"
    result = await visualizer_module.WorkflowVisualizer.render_mermaid(  # noqa: F841  # Variable for test verification
        sample_workflow, output_path=str(out)
    )
    assert out.read_text(encoding="utf-8") == result
    assert "graph TD" in result


@pytest.mark.asyncio
async def test_visualizer_render_mermaid_without_path(visualizer_module, sample_workflow):
    result = await visualizer_module.WorkflowVisualizer.render_mermaid(sample_workflow)  # noqa: F841  # Variable for test verification
    assert "graph TD" in result


@pytest.mark.asyncio
async def test_visualizer_render_graphviz_to_file(
    visualizer_module, sample_workflow, tmp_path, monkeypatch
):
    out = tmp_path / "workflow.dot"
    fake_run = MagicMock(return_value=MagicMock(returncode=0))
    monkeypatch.setattr(shutil, "which", lambda _x: r"C:\dot\dot.exe")
    monkeypatch.setattr("core.security.subprocess_runner.run", fake_run)

    result = await visualizer_module.WorkflowVisualizer.render_graphviz(  # noqa: F841  # Variable for test verification
        sample_workflow, output_path=str(out)
    )
    assert out.read_text(encoding="utf-8") == result
    assert fake_run.called


@pytest.mark.asyncio
async def test_visualizer_render_graphviz_without_path(visualizer_module, sample_workflow):
    result = await visualizer_module.WorkflowVisualizer.render_graphviz(sample_workflow)  # noqa: F841  # Variable for test verification
    assert "digraph workflow {" in result


# ---------------------------------------------------------------------------
# Dual-write fixtures / helpers
# ---------------------------------------------------------------------------
@pytest.fixture
def dual_write_module(monkeypatch):
    import core.dual_write as dw
    import core.metrics_history as mh

    fake_history = MagicMock()
    fake_history.push_metric = MagicMock(return_value=None)
    fake_history.query = MagicMock(return_value=[])
    monkeypatch.setattr(mh, "metrics_history", fake_history)
    return dw


@pytest.fixture
def victoriametrics_manager():
    manager = MagicMock()
    storage = AsyncMock()
    storage.initialize = MagicMock(return_value=True)
    storage.store = AsyncMock(return_value=True)
    manager.get_victoriametrics = MagicMock(return_value=storage)
    return manager


@pytest.mark.asyncio
async def test_dual_write_disabled(dual_write_module):
    strategy = dual_write_module.DualWriteStrategy()
    ok = await strategy.write_metric("cpu", 0.5, {"service": "web"}, timestamp=1700000000)
    assert ok is True
    stats = strategy.get_stats()
    assert stats["sqlite_writes"] == 1
    assert stats["vm_writes"] == 0
    assert stats["victoria_metrics_enabled"] is False


@pytest.mark.asyncio
async def test_dual_write_sqlite_only_failure(dual_write_module):
    """SQLite fails and VM disabled -> write_metric should fail."""
    import core.metrics_history as mh

    mh.metrics_history.push_metric.side_effect = RuntimeError("db locked")
    strategy = dual_write_module.DualWriteStrategy()
    ok = await strategy.write_metric("cpu", 0.5, {"service": "web"})
    assert ok is False
    stats = strategy.get_stats()
    assert stats["sqlite_writes"] == 0


@pytest.mark.asyncio
async def test_dual_write_initialize_disabled(dual_write_module):
    strategy = dual_write_module.DualWriteStrategy(
        victoria_metrics_enabled=False, fallback_on_error=True, async_write=True
    )
    await strategy.initialize()
    assert strategy.victoria_metrics_enabled is False


@pytest.mark.asyncio
async def test_dual_write_initialize_enabled(
    dual_write_module, victoriametrics_manager, monkeypatch
):
    import core.storage.l4.storage_manager as l4

    monkeypatch.setattr(l4, "init_l4_storage_manager", lambda _cfg: victoriametrics_manager)
    strategy = dual_write_module.DualWriteStrategy(victoria_metrics_enabled=True)
    await strategy.initialize()
    assert strategy.victoria_metrics_enabled is True
    assert strategy._vm_storage is not None


@pytest.mark.asyncio
async def test_dual_write_initialize_fails(dual_write_module, victoriametrics_manager, monkeypatch):
    import core.storage.l4.storage_manager as l4

    victoriametrics_manager.get_victoriametrics.return_value.initialize = MagicMock(
        return_value=False
    )
    monkeypatch.setattr(l4, "init_l4_storage_manager", lambda _cfg: victoriametrics_manager)
    strategy = dual_write_module.DualWriteStrategy(victoria_metrics_enabled=True)
    await strategy.initialize()
    assert strategy.victoria_metrics_enabled is False


@pytest.mark.asyncio
async def test_dual_write_vm_async_and_sync(
    dual_write_module, victoriametrics_manager, monkeypatch
):
    import core.storage.l4.storage_manager as l4

    monkeypatch.setattr(l4, "init_l4_storage_manager", lambda _cfg: victoriametrics_manager)

    strategy = dual_write_module.DualWriteStrategy(victoria_metrics_enabled=True, async_write=True)
    await strategy.initialize()
    ok = await strategy.write_metric("cpu", 0.5, {"service": "web"})
    assert ok is True
    await asyncio.sleep(0)  # allow background VM task to be processed

    stats = strategy.get_stats()
    assert stats["sqlite_writes"] == 1
    assert stats["vm_writes"] == 1

    # switch to synchronous write with a failing store
    strategy.async_write = False
    victoriametrics_manager.get_victoriametrics.return_value.store = AsyncMock(return_value=False)
    ok2 = await strategy.write_metric("cpu", 0.6, {"service": "web"})
    assert ok2 is True  # sqlite still works
    stats = strategy.get_stats()
    assert stats["vm_errors"] == 1
    assert stats["fallbacks"] == 1


@pytest.mark.asyncio
async def test_dual_write_vm_exception(dual_write_module, victoriametrics_manager, monkeypatch):
    import core.storage.l4.storage_manager as l4

    monkeypatch.setattr(l4, "init_l4_storage_manager", lambda _cfg: victoriametrics_manager)
    victoriametrics_manager.get_victoriametrics.return_value.store = AsyncMock(
        side_effect=RuntimeError("network")
    )
    strategy = dual_write_module.DualWriteStrategy(victoria_metrics_enabled=True, async_write=False)
    await strategy.initialize()
    ok = await strategy.write_metric("cpu", 0.5, {"service": "web"})
    assert ok is True
    assert strategy.get_stats()["vm_errors"] == 1


@pytest.mark.asyncio
async def test_dual_write_batch_metrics(dual_write_module, victoriametrics_manager, monkeypatch):
    import core.storage.l4.storage_manager as l4

    monkeypatch.setattr(l4, "init_l4_storage_manager", lambda _cfg: victoriametrics_manager)
    strategy = dual_write_module.DualWriteStrategy(victoria_metrics_enabled=True, async_write=False)
    await strategy.initialize()

    metrics = [
        {"name": "cpu", "value": 0.1, "labels": {"service": "web"}},
        {"name": "cpu", "value": 0.2, "labels": {"service": "web"}},
    ]
    ok = await strategy.write_batch_metrics(metrics)
    assert ok is True
    stats = strategy.get_stats()
    assert stats["sqlite_writes"] == 2
    assert stats["vm_writes"] == 2

    # empty batch
    assert await strategy.write_batch_metrics([]) is True

    # vm exception: each metric in the failing batch increments vm_errors
    victoriametrics_manager.get_victoriametrics.return_value.store = AsyncMock(
        side_effect=RuntimeError("timeout")
    )
    ok2 = await strategy.write_batch_metrics(metrics)
    assert ok2 is True
    assert strategy.get_stats()["vm_errors"] == 2


def test_dual_write_enable_disable(dual_write_module):
    strategy = dual_write_module.DualWriteStrategy()
    assert strategy.victoria_metrics_enabled is False
    strategy.enable_victoriametrics()
    assert strategy.victoria_metrics_enabled is True
    strategy.disable_victoriametrics()
    assert strategy.victoria_metrics_enabled is False


@pytest.mark.asyncio
async def test_dual_write_global_functions(dual_write_module, monkeypatch):
    monkeypatch.setattr(dual_write_module, "_dual_write_strategy", None)
    strategy = dual_write_module.get_dual_write_strategy()
    assert isinstance(strategy, dual_write_module.DualWriteStrategy)

    monkeypatch.setattr(dual_write_module, "_dual_write_strategy", None)
    strategy2 = await dual_write_module.init_dual_write_strategy(enabled=False)
    assert isinstance(strategy2, dual_write_module.DualWriteStrategy)
    assert strategy2.victoria_metrics_enabled is False


# ---------------------------------------------------------------------------
# Repair engine fixtures / helpers
# ---------------------------------------------------------------------------
class _FakeSubprocessRunner:
    """Lightweight fake for core.security.subprocess_runner used by _impl."""

    PIPE = -1
    STDOUT = -2
    TimeoutExpired = type("TimeoutExpired", (Exception,), {})

    def __init__(self, behaviour="ok", returncode=0, stdout="ok", stderr=""):
        self.behaviour = behaviour
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        self.calls = []

    def Popen(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        if self.behaviour == "not_found":
            raise FileNotFoundError("powershell not found")
        if self.behaviour == "pop_exception":
            raise OSError("popen failed")
        return _FakeProcess(self, self.returncode, self.stdout, self.stderr)


class _FakeProcess:
    def __init__(self, runner, returncode, stdout, stderr):
        self.runner = runner
        self.returncode = returncode
        self._stdout = stdout
        self._stderr = stderr
        self._killed = False

    def communicate(self, timeout=None):
        if self.runner.behaviour == "timeout" and not self._killed:
            raise self.runner.TimeoutExpired
        return (self._stdout, self._stderr)

    def kill(self):
        self._killed = True


@pytest.fixture
def repair_module(monkeypatch):
    import core.command_guard as cg
    import core.repair_engine._impl as impl
    import core.stats_engine as stats

    class _Risk:
        def __init__(self, value):
            self.value = value

    class _RiskLevel:
        SAFE = _Risk("safe")
        LOW = _Risk("low")
        MEDIUM = _Risk("medium")
        HIGH = _Risk("high")
        BLOCKED = _Risk("blocked")

    monkeypatch.setattr(cg, "RiskLevel", _RiskLevel)
    monkeypatch.setattr(cg, "analyze_command", lambda _c: {"risk_level": _RiskLevel.SAFE})
    monkeypatch.setattr(cg, "record_audit", lambda **kwargs: None)
    monkeypatch.setattr(cg, "get_protected_pids", lambda: set())

    async def fake_record_repair(data):
        return None

    monkeypatch.setattr(stats, "record_repair", fake_record_repair)
    monkeypatch.setattr(impl, "subprocess_runner", _FakeSubprocessRunner())

    impl.clear_repair_history()
    return impl


def test_repair_sanitize_param(repair_module):
    assert repair_module._sanitize_param("service_name", "w3svc") == "w3svc"
    assert repair_module._sanitize_param("service_name", "w3 svc") == "w3 svc"
    with pytest.raises(ValueError):
        repair_module._sanitize_param("service_name", "w3svc..")
    with pytest.raises(ValueError):
        repair_module._sanitize_param("service_name", " w3svc")
    with pytest.raises(ValueError):
        repair_module._sanitize_param("service_name", "w3  svc")
    with pytest.raises(ValueError):
        repair_module._sanitize_param("service_name", "café")
    with pytest.raises(ValueError):
        repair_module._sanitize_param(
            "service_name", "a" * (repair_module._SERVICE_NAME_MAX_LEN + 1)
        )

    assert repair_module._sanitize_param("pid", "1234") == "1234"
    with pytest.raises(ValueError):
        repair_module._sanitize_param("pid", "not-a-number")
    with pytest.raises(ValueError):
        repair_module._sanitize_param("pid", 3)

    # general dangerous chars should be stripped
    assert repair_module._sanitize_param("other", "a;b") == "ab"


def test_repair_render_command(repair_module):
    assert repair_module._render_command("", {}) == ""
    assert repair_module._render_command("echo", {}) == "echo"
    assert repair_module._render_command("echo {name}", {"name": "world"}) == "echo world"
    # empty key ignored
    assert repair_module._render_command("echo {name}", {"": "x", "name": "y"}) == "echo y"


def test_repair_repair_scripts_readonly(repair_module):
    with pytest.raises(TypeError):
        repair_module.REPAIR_SCRIPTS["new"] = {}
    with pytest.raises(TypeError):
        repair_module.REPAIR_SCRIPTS.pop("clear_temp")
    with pytest.raises(TypeError):
        repair_module.REPAIR_SCRIPTS.clear()


def test_repair_get_scripts_and_history(repair_module):
    scripts = repair_module.get_repair_scripts()
    keys = {s["key"] for s in scripts}
    assert "clear_temp" in keys
    assert "kill_high_cpu" in keys
    # deep copy protection
    scripts[0]["params"].append("injected")
    assert "injected" not in repair_module.REPAIR_SCRIPTS[scripts[0]["key"]].get("params", [])

    assert repair_module.get_repair_history(limit=5) == []
    assert repair_module.get_repair_history(limit=200) == []


@pytest.mark.asyncio
async def test_repair_execute_unknown_and_missing_params(repair_module):
    result = await repair_module.execute_repair("nonexistent")  # noqa: F841  # Variable for test verification
    assert result["success"] is False
    assert result["return_code"] == -1

    result = await repair_module.execute_repair("kill_high_cpu", {})  # noqa: F841  # Variable for test verification
    assert result["success"] is False
    assert "缺少必要参数" in result["error"]


@pytest.mark.asyncio
async def test_repair_execute_invalid_pid(repair_module):
    result = await repair_module.execute_repair("kill_high_cpu", {"pid": 2})  # noqa: F841  # Variable for test verification
    assert result["success"] is False
    assert "PID" in result["error"]


@pytest.mark.asyncio
async def test_repair_execute_blocked_by_guard(repair_module, monkeypatch):
    import core.command_guard as cg

    def blocked(_c):
        return {
            "risk_level": cg.RiskLevel.BLOCKED,
            "risk_name": "kill-self",
            "reason": "self-kill",
            "safe_alternative": "Restart-Service -Name x",
        }

    monkeypatch.setattr(cg, "analyze_command", blocked)
    result = await repair_module.execute_repair("flush_dns")  # noqa: F841  # Variable for test verification
    assert result["success"] is False
    assert result["blocked"] is True
    assert "safe_alternative" in result


@pytest.mark.asyncio
async def test_repair_execute_success_and_history(repair_module):
    result = await repair_module.execute_repair("clear_temp")  # noqa: F841  # Variable for test verification
    assert result["success"] is True
    assert result["return_code"] == 0
    assert result["sqlite_persisted"] is True
    assert len(repair_module.get_repair_history(limit=10)) == 1

    count = repair_module.clear_repair_history()
    assert count == 1
    assert len(repair_module.get_repair_history()) == 0


@pytest.mark.asyncio
async def test_repair_execute_failure(repair_module):
    repair_module.subprocess_runner = _FakeSubprocessRunner(
        returncode=1, stdout="", stderr="failed"
    )
    result = await repair_module.execute_repair("free_memory")  # noqa: F841  # Variable for test verification
    assert result["success"] is False
    assert result["return_code"] == 1


@pytest.mark.asyncio
async def test_repair_execute_powershell_timeout(repair_module):
    repair_module.subprocess_runner = _FakeSubprocessRunner(behaviour="timeout")
    result = await repair_module.execute_repair("check_disk")  # noqa: F841  # Variable for test verification
    assert result["success"] is False
    assert "超时" in result["error"]


@pytest.mark.asyncio
async def test_repair_execute_powershell_not_found(repair_module):
    repair_module.subprocess_runner = _FakeSubprocessRunner(behaviour="not_found")
    result = await repair_module.execute_repair("flush_dns")  # noqa: F841  # Variable for test verification
    assert result["success"] is False
    assert "PowerShell" in result["error"]


@pytest.mark.asyncio
async def test_repair_execute_sqlite_record_failure(repair_module, monkeypatch):
    import core.stats_engine as stats

    async def broken_record(_d):
        raise RuntimeError("sqlite closed")

    monkeypatch.setattr(stats, "record_repair", broken_record)
    result = await repair_module.execute_repair("free_memory")  # noqa: F841  # Variable for test verification
    assert result["success"] is True
    assert result["sqlite_persisted"] is False


@pytest.mark.asyncio
async def test_repair_execute_pop_exception(repair_module):
    repair_module.subprocess_runner = _FakeSubprocessRunner(behaviour="pop_exception")
    result = await repair_module.execute_repair("sfc_scan")  # noqa: F841  # Variable for test verification
    assert result["success"] is False
    assert result["return_code"] == -1


# ---------------------------------------------------------------------------
# SLO engine fixtures / helpers
# ---------------------------------------------------------------------------
@pytest.fixture
def slo_engine(monkeypatch):
    import core.metrics_history as mh
    import core.slo_engine as slo
    import core.slo_storage as storage

    monkeypatch.setattr(storage, "save_slos", lambda: None)
    monkeypatch.setattr(storage, "load_slos", lambda: None)
    monkeypatch.setattr(slo, "_slo_store", {})
    monkeypatch.setattr(slo, "_slo_counter", 0)

    fake_metrics = MagicMock()
    fake_metrics.query = MagicMock(return_value=[])
    monkeypatch.setattr(mh, "metrics_history", fake_metrics)
    return slo


def _make_point(value, ts=None):
    if ts is None:
        ts = datetime.datetime.utcnow()
    return SimpleNamespace(value=value, timestamp=ts)


def test_slo_window_helpers(slo_engine):
    assert slo_engine.parse_window("7d") == 168
    assert slo_engine.parse_window("6h") == 6
    assert slo_engine.parse_window("24h") == 24
    assert slo_engine.parse_window("90") == 90
    with pytest.raises(ValueError):
        slo_engine.parse_window("forever")

    assert slo_engine.format_window(168) == "7d"
    assert slo_engine.format_window(99) == "99h"


def test_slo_aggregation_and_metrics_helpers(slo_engine):
    assert slo_engine._validate_aggregation("uptime") == "uptime"
    assert slo_engine._validate_aggregation(None) == "good_ratio"
    with pytest.raises(ValueError):
        slo_engine._validate_aggregation("invalid")

    assert slo_engine._metric_point_value(SimpleNamespace(value=80.0), "cpu") == 0.8
    assert slo_engine._metric_point_value(SimpleNamespace(value=80.0), "memory") == 0.8
    assert slo_engine._metric_point_value(SimpleNamespace(value=0.5), "other") == 0.5

    rule = slo_engine.SLORule(
        id="x",
        name="x",
        service="s",
        metric="availability",
        target=0.95,
        window=1,
        alert_threshold=0.9,
    )
    assert slo_engine._point_is_good(SimpleNamespace(value=0.96), rule) is True
    rule2 = slo_engine.SLORule(
        id="x2", name="x2", service="s", metric="cpu", target=0.8, window=1, alert_threshold=0.9
    )
    assert slo_engine._point_is_good(SimpleNamespace(value=75.0), rule2) is True
    assert slo_engine._point_is_good(SimpleNamespace(value=85.0), rule2) is False

    assert slo_engine._to_epoch(1234567890) == 1234567890.0
    dt = datetime.datetime(2024, 1, 1, 12, 0, 0)
    assert slo_engine._to_epoch(dt) == pytest.approx(dt.timestamp())
    assert slo_engine._to_epoch("12:00:00") > 0
    assert slo_engine._to_epoch("bad") == 0.0

    assert slo_engine._percentile([], 0.99) == 0.0
    assert slo_engine._percentile([1, 2, 3, 4, 5], 0.5) in {2, 3}


def test_slo_uptime_ratio(slo_engine):
    rule = slo_engine.SLORule(
        id="u",
        name="u",
        service="s",
        metric="availability",
        target=0.95,
        window=1,
        alert_threshold=0.9,
        aggregation="uptime",
    )
    assert slo_engine._uptime_ratio([], rule) == 1.0
    assert slo_engine._uptime_ratio([_make_point(1.0)], rule) == 1.0
    assert slo_engine._uptime_ratio([_make_point(0.0)], rule) == 0.0

    base = datetime.datetime(2024, 1, 1, 12, 0, 0)  # noqa: F841  # Variable for test verification
    points = [
        _make_point(1.0, base),
        _make_point(1.0, base + datetime.timedelta(seconds=60)),
    ]
    assert slo_engine._uptime_ratio(points, rule) == 1.0


def test_slo_crud(slo_engine):
    rule = slo_engine.create_slo(
        name="cpu budget",
        service="web",
        metric="cpu",
        target=0.8,
        window=24,
        slo_id="slo-001",
        aggregation="good_ratio",
    )
    assert rule.id == "slo-001"
    assert rule.target == 0.8

    assert slo_engine.get_slo("slo-001") is rule
    assert len(slo_engine.list_slos()) == 1

    updated = slo_engine.update_slo("slo-001", target=0.85, aggregation="mean_lt")
    assert updated is not None
    assert updated.target == 0.85
    assert updated.aggregation == "mean_lt"

    assert slo_engine.delete_slo("slo-001") is True
    assert slo_engine.get_slo("slo-001") is None
    assert slo_engine.delete_slo("slo-001") is False
    assert slo_engine.update_slo("missing", target=0.5) is None


def test_slo_evaluate_empty_and_aggregations(slo_engine):
    rule = slo_engine.create_slo(
        name="avail",
        service="web",
        metric="availability",
        target=0.95,
        window=24,
        aggregation="good_ratio",
    )
    empty = slo_engine.evaluate_slo(rule, [])
    assert empty["status"] == "healthy"

    points = [_make_point(0.99), _make_point(0.94), _make_point(0.96)]
    result = slo_engine.evaluate_slo(rule, points)  # noqa: F841  # Variable for test verification
    assert 0 < result["current"] < 1
    assert result["status"] in {"healthy", "warning", "critical"}

    rule2 = slo_engine.create_slo(
        name="latency", service="api", metric="latency", target=0.1, window=1, aggregation="p99_lt"
    )
    p99_result = slo_engine.evaluate_slo(rule2, [_make_point(0.05), _make_point(0.2)])  # noqa: F841  # Variable for test verification
    assert p99_result["current"] in {0.0, 1.0}

    rule3 = slo_engine.create_slo(
        name="cpu-mean", service="db", metric="cpu", target=0.6, window=1, aggregation="mean_lt"
    )
    mean_result = slo_engine.evaluate_slo(rule3, [_make_point(80), _make_point(60)])  # noqa: F841  # Variable for test verification
    assert "status" in mean_result

    rule4 = slo_engine.create_slo(
        name="perfect",
        service="svc",
        metric="availability",
        target=1.0,
        window=1,
        aggregation="good_ratio",
    )
    perfect = slo_engine.evaluate_slo(rule4, [_make_point(0.5)])
    assert perfect["error_budget_remaining_percent"] == 0.0
    assert perfect["alert"] is True


def test_slo_generate_sla_report(slo_engine, monkeypatch):
    import core.metrics_history as mh

    rule = slo_engine.create_slo(
        name="web-availability",
        service="web",
        metric="availability",
        target=0.95,
        window=24,
        aggregation="good_ratio",
    )
    points = [
        _make_point(0.99),
        _make_point(0.94),
        _make_point(0.96),
    ]
    fake_metrics = MagicMock()
    fake_metrics.query = MagicMock(return_value=points)
    monkeypatch.setattr(mh, "metrics_history", fake_metrics)

    reports = slo_engine.generate_sla_report(period="24h")
    assert len(reports) == 1
    assert reports[0]["slo_id"] == rule.id
    assert "compliance" in reports[0]

    # uptime specific branch
    rule2 = slo_engine.create_slo(
        name="uptime-rule",
        service="api",
        metric="availability",
        target=0.95,
        window=24,
        aggregation="uptime",
    )
    base = datetime.datetime.utcnow() - datetime.timedelta(hours=2)  # noqa: F841  # Variable for test verification
    up_points = [
        _make_point(1.0, base),
        _make_point(1.0, base + datetime.timedelta(hours=1)),
    ]
    fake_metrics.query = MagicMock(return_value=up_points)
    reports2 = slo_engine.generate_sla_report(period="7d")
    assert any(r["slo_id"] == rule2.id for r in reports2)


# ---------------------------------------------------------------------------
# Connection pool optimization fixtures / helpers
# ---------------------------------------------------------------------------
@pytest.fixture
def cpo_module(monkeypatch):
    import core.connection_pool_optimization as cpo

    engine = MagicMock()
    pool = MagicMock()
    pool.size.return_value = 20
    pool.checkedin.return_value = 2
    pool.checkedout.return_value = 10
    pool.overflow.return_value = 5
    pool._max_overflow = 40
    engine.pool = pool

    conn = AsyncMock()
    result = MagicMock()  # noqa: F841  # Variable for test verification
    result.fetchone.return_value = (1,)
    conn.execute = AsyncMock(return_value=result)
    conn.__aenter__ = AsyncMock(return_value=conn)
    conn.__aexit__ = AsyncMock(return_value=False)
    engine.connect = MagicMock(return_value=conn)

    def fake_create(url, **kwargs):
        return engine

    monkeypatch.setattr(cpo, "create_async_engine", fake_create)
    return cpo, engine, pool, conn


@pytest.mark.asyncio
async def test_cpo_get_pool_status(cpo_module):
    cpo, engine, pool, _ = cpo_module
    monitor = cpo.ConnectionPoolMonitor(engine)
    status = await monitor.get_pool_status()
    assert status["size"] == 20
    assert status["checked_out"] == 10
    assert status["max_overflow"] == 40
    assert "timestamp" in status


@pytest.mark.asyncio
async def test_cpo_analyze_pool_high_utilization(cpo_module):
    cpo, engine, pool, _ = cpo_module
    pool.checkedout.return_value = 18  # 90%
    monitor = cpo.ConnectionPoolMonitor(engine)
    report = await monitor.analyze_pool_performance()
    assert "High pool utilization" in report["recommendations"][0]
    assert report["metrics_count"] == 1


@pytest.mark.asyncio
async def test_cpo_analyze_pool_low_utilization(cpo_module):
    cpo, engine, pool, _ = cpo_module
    pool.size.return_value = 20
    pool.checkedout.return_value = 1  # 5%
    monitor = cpo.ConnectionPoolMonitor(engine)
    report = await monitor.analyze_pool_performance()
    assert any("Low pool utilization" in r for r in report["recommendations"])


@pytest.mark.asyncio
async def test_cpo_analyze_pool_high_overflow(cpo_module):
    cpo, engine, pool, _ = cpo_module
    pool.size.return_value = 10
    pool.checkedout.return_value = 5
    pool.overflow.return_value = 35
    pool._max_overflow = 40
    monitor = cpo.ConnectionPoolMonitor(engine)
    report = await monitor.analyze_pool_performance()
    assert any("overflow" in r.lower() for r in report["recommendations"])


@pytest.mark.asyncio
async def test_cpo_connection_healthy(cpo_module):
    cpo, engine, _, _ = cpo_module
    monitor = cpo.ConnectionPoolMonitor(engine)
    health = await monitor.test_connection_health()
    assert health["status"] == "healthy"


@pytest.mark.asyncio
async def test_cpo_connection_unhealthy(cpo_module):
    cpo, engine, _, conn = cpo_module
    conn.__aenter__ = AsyncMock(side_effect=RuntimeError("db down"))
    monitor = cpo.ConnectionPoolMonitor(engine)
    health = await monitor.test_connection_health()
    assert health["status"] == "unhealthy"


@pytest.mark.asyncio
async def test_cpo_create_optimized_engine(cpo_module):
    cpo, engine, _, _ = cpo_module
    created = await cpo.create_optimized_engine("sqlite+aiosqlite:///:memory:")
    assert created is engine


@pytest.mark.asyncio
async def test_cpo_create_optimized_engine_failure(cpo_module, monkeypatch):
    cpo, _, _, _ = cpo_module

    def broken(*a, **k):
        raise RuntimeError("bad url")

    monkeypatch.setattr(cpo, "create_async_engine", broken)
    with pytest.raises(RuntimeError):
        await cpo.create_optimized_engine("bad")


@pytest.mark.asyncio
async def test_cpo_optimize_existing_engine(cpo_module):
    cpo, engine, _, _ = cpo_module
    result = await cpo.optimize_existing_engine(engine)  # noqa: F841  # Variable for test verification
    assert result["status"] == "analysis_completed"
    assert result["current_config"]["pool_size"] == 20


@pytest.mark.asyncio
async def test_cpo_optimize_existing_engine_failure(cpo_module):
    cpo, engine, _, _ = cpo_module
    del engine.pool
    result = await cpo.optimize_existing_engine(engine)  # noqa: F841  # Variable for test verification
    assert "error" in result


def test_cpo_recommendations(cpo_module):
    cpo, _, _, _ = cpo_module
    for wt in ("read_heavy", "write_heavy", "mixed", "analytics"):
        rec = cpo.get_connection_pool_recommendations(wt)
        assert "pool_size" in rec
    default = cpo.get_connection_pool_recommendations("unknown")
    assert default == cpo.get_connection_pool_recommendations("mixed")
