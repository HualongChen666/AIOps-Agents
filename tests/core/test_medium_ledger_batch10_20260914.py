# -*- coding: utf-8 -*-
"""Regression tests for medium ledger batch 10 (2026-09-14).

Covers genuine fixes (no mocks of the code under test where avoidable):

- core/performance_data_collector.py: persist ``meta_data`` (was ``metadata=``,
  a silent no-op against the real column name).
- core/query_optimization.py: eager-load only relationships that actually exist
  (was ``selectinload(Alert.details)`` etc. -> AttributeError).
- core/monitoring_system_integrator.py: evaluate the real ``condition``
  expression for every rule (was CPU-only).
- core/middleware/rate_limit_middleware.py: reject over-limit requests BEFORE
  invoking the downstream handler.
- core/log_router.py: pair each gathered result with its real destination.
- core/memory_usage_optimizer.py: record the component in snapshots + dispatch
  configured memory actions.
- core/performance_optimizer.py: warning-severity detection + stoppable monitor.
- core/plugin_development_sdk.py: templates generate runnable plugin code.
- core/loki_client.py: build URLs without dropping the base path prefix.
- core/priority/resource_allocator.py: reallocate freed capacity to pending tasks.
"""

import asyncio
import importlib
import sys
import threading
import types
from datetime import datetime

import pytest
from starlette.requests import Request
from fastapi.responses import Response

# ``core.log_router`` imports ``aiohttp`` at module import time. It is an
# optional runtime dependency that may be absent in a minimal test env, so
# provide a minimal stub only when the real package is unavailable.
try:  # pragma: no cover - depends on environment
    import aiohttp  # noqa: F401
except ImportError:  # pragma: no cover
    _aiohttp_stub = types.ModuleType("aiohttp")

    class _ClientSession:  # minimal placeholder used only for attribute access
        def __init__(self, *args, **kwargs):
            pass

    _aiohttp_stub.ClientSession = _ClientSession
    sys.modules.setdefault("aiohttp", _aiohttp_stub)


# ---------------------------------------------------------------------------
# core/performance_data_collector.py
# ---------------------------------------------------------------------------
from core.models import PerformanceMetric


class _FakeCollectorSession:
    def __init__(self):
        self.added = []

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        pass

    async def refresh(self, obj):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


def test_performance_collector_persists_metadata_to_meta_data(monkeypatch):
    import core.performance_data_collector as pdc

    fake = _FakeCollectorSession()
    monkeypatch.setattr(pdc, "AsyncSessionLocal", lambda *a, **k: fake)

    collector = pdc.PerformanceDataCollector()
    asyncio.run(
        collector.collect_metric(
            {"test_id": "t1", "component": "api", "metadata": {"k": "v"}}
        )
    )

    assert fake.added, "metric was not added to the session"
    metric = fake.added[0]
    # The real column is ``meta_data``; passing ``metadata=`` silently drops it.
    assert metric.meta_data == {"k": "v"}


# ---------------------------------------------------------------------------
# core/query_optimization.py
# ---------------------------------------------------------------------------
from core.query_optimization import optimize_alert_query, optimize_metrics_query


def test_optimize_alert_query_real_models_do_not_raise():
    # Real Alert/Metrics models have no ``details``/``tags``/``assignee``/
    # ``source`` relationships -> must not raise AttributeError.
    stmt = optimize_alert_query(None)
    assert stmt is not None
    stmt2 = optimize_metrics_query(None)
    assert stmt2 is not None


# ---------------------------------------------------------------------------
# core/monitoring_system_integrator.py
# ---------------------------------------------------------------------------
from core.monitoring_system_integrator import MonitoringSystemIntegrator


def test_monitoring_integrator_evaluates_memory_rule():
    integrator = MonitoringSystemIntegrator()
    integrator.evaluate_alert_rules({"system_memory_percent": 90.0})
    active_ids = {a.alert_id for a in integrator.get_active_alerts()}
    assert "high_memory_usage" in active_ids
    # CPU rule metric absent -> must NOT trigger.
    assert "high_cpu_usage" not in active_ids


def test_monitoring_integrator_evaluates_api_rule():
    integrator = MonitoringSystemIntegrator()
    integrator.evaluate_alert_rules({"api_error_rate": 0.2})
    active_ids = {a.alert_id for a in integrator.get_active_alerts()}
    assert "high_api_error_rate" in active_ids


def test_monitoring_integrator_no_false_trigger_below_threshold():
    integrator = MonitoringSystemIntegrator()
    integrator.evaluate_alert_rules({"system_memory_percent": 10.0})
    assert integrator.get_active_alerts() == []


# ---------------------------------------------------------------------------
# core/middleware/rate_limit_middleware.py
# ---------------------------------------------------------------------------
def _make_request(path: str, client=("1.2.3.4", 1234)) -> Request:
    scope = {
        "type": "http",
        "method": "POST",
        "path": path,
        "headers": [(b"host", b"test")],
        "client": client,
        "query_string": b"",
        "server": ("test", 80),
        "scheme": "http",
    }
    return Request(scope)


def test_rate_limit_rejects_before_downstream():
    mod = importlib.import_module("core.middleware.rate_limit_middleware")
    mod.rate_limiter._requests.clear()

    calls = {"n": 0}

    async def call_next(request):
        calls["n"] += 1
        return Response("ok")

    path = "/api/v1/repairs"  # limit (10, 60)
    req = _make_request(path)
    client_id = mod.rate_limiter._get_client_id(req)
    for _ in range(10):
        mod.rate_limiter.is_allowed(client_id, path)

    loop = asyncio.new_event_loop()
    try:
        before = calls["n"]
        resp = loop.run_until_complete(mod.rate_limit_middleware(req, call_next))
        assert resp.status_code == 429
        # The downstream handler MUST NOT run for a rejected request.
        assert calls["n"] == before

        mod.rate_limiter._requests.clear()
        resp2 = loop.run_until_complete(mod.rate_limit_middleware(req, call_next))
        assert resp2.status_code == 200
        assert resp2.headers["X-RateLimit-Remaining"] == str(10 - 1)
        assert calls["n"] == before + 1
    finally:
        loop.close()
        mod.rate_limiter._requests.clear()


# ---------------------------------------------------------------------------
# core/log_router.py
# ---------------------------------------------------------------------------
def test_log_router_unknown_destination_and_attribution():
    lr = importlib.import_module("core.log_router")
    router = lr.LogRouter({"destinations": ["loki", "bogus", "elasticsearch"]})

    async def _fail(entry):
        raise RuntimeError("loki down")

    async def _ok(entry):
        return True

    router.send_to_loki = _fail
    router.send_to_elasticsearch = _ok

    entry = router.create_log_entry("hello")
    # Unknown destination is skipped (no crash) and the real exception from loki
    # is attributed correctly -> overall failure.
    assert asyncio.new_event_loop().run_until_complete(router.route_log(entry)) is False

    router2 = lr.LogRouter({"destinations": ["loki", "bogus", "elasticsearch"]})
    router2.send_to_loki = _ok
    router2.send_to_elasticsearch = _ok
    assert asyncio.new_event_loop().run_until_complete(router2.route_log(entry)) is True


# ---------------------------------------------------------------------------
# core/memory_usage_optimizer.py
# ---------------------------------------------------------------------------
from core.memory_usage_optimizer import MemoryAction, MemoryUsageOptimizer


def test_memory_snapshot_records_component():
    opt = MemoryUsageOptimizer()
    snap = opt.take_memory_snapshot("api")
    assert snap.metadata.get("component") == "api"


def test_memory_leak_detection_for_non_system_component(monkeypatch):
    import numpy as np

    opt = MemoryUsageOptimizer()
    for _ in range(12):
        opt.take_memory_snapshot("api")

    # Force a positive growth rate so the detected leak path is exercised.
    monkeypatch.setattr(np, "polyfit", lambda x, y, deg: (50.0, 0.0))
    leaks = opt.detect_memory_leaks("api")
    assert leaks and leaks[0].component == "api"
    # No snapshots for the default "system" component -> no leaks.
    assert opt.detect_memory_leaks("system") == []


def test_memory_optimize_dispatches_registered_action():
    opt = MemoryUsageOptimizer()
    seen = []
    opt.register_action_handler(
        MemoryAction.REDUCE_POOL_SIZE, lambda comp: seen.append(comp) or {"ok": True}
    )
    opt.set_memory_limit("svc", 100.0, action_on_exceed=MemoryAction.REDUCE_POOL_SIZE)
    opt.component_memory["svc"] = 99.0

    result = opt.optimize_memory("svc")
    assert "reduce_pool_size" in result["actions_taken"]
    assert seen == ["svc"]


def test_memory_optimize_collect_garbage_label_preserved():
    opt = MemoryUsageOptimizer()
    opt.set_memory_limit("svc", 100.0, action_on_exceed=MemoryAction.COLLECT_GARBAGE)
    opt.component_memory["svc"] = 99.0
    result = opt.optimize_memory("svc")
    assert "garbage_collection" in result["actions_taken"]


# ---------------------------------------------------------------------------
# core/performance_optimizer.py
# ---------------------------------------------------------------------------
from core.performance_optimizer import PerformanceMetric, PerformanceOptimizer


def test_performance_optimizer_warning_severity(monkeypatch):
    monkeypatch.setenv("PERFORMANCE_OPTIMIZER_DISABLED", "true")
    opt = PerformanceOptimizer()
    now = datetime.now()
    # 85% is above memory warning (80) but below critical (95).
    opt.metrics_history["memory_usage"].extend([(now, 85.0)] * 6)
    detected = opt._detect_bottlenecks()
    assert detected["detected_count"] >= 1
    assert any(
        b.severity == "warning" and b.metric == PerformanceMetric.MEMORY_USAGE
        for b in opt.bottlenecks
    )


def test_performance_optimizer_monitor_is_stoppable(monkeypatch):
    monkeypatch.setenv("PERFORMANCE_OPTIMIZER_DISABLED", "true")
    opt = PerformanceOptimizer()
    # Neutralise collection so the loop only waits on the stop event.
    for name in (
        "_collect_metrics",
        "_detect_bottlenecks",
        "_check_alerts",
        "_cleanup_old_metrics",
    ):
        monkeypatch.setattr(opt, name, lambda *a, **k: None)

    opt._monitor_stop.clear()
    opt._monitor_thread = threading.Thread(target=opt._background_monitoring_loop, daemon=True)
    opt._monitor_thread.start()
    assert opt._monitor_thread.is_alive()

    opt.stop_background_monitoring(timeout=2.0)
    assert not opt._monitor_thread.is_alive()


# ---------------------------------------------------------------------------
# core/plugin_development_sdk.py
# ---------------------------------------------------------------------------
from core.plugin_development_sdk import PluginDevelopmentSDK


@pytest.mark.parametrize("template_type", ["monitoring", "integration", "ai"])
def test_plugin_sdk_generates_runnable_code(template_type):
    sdk = PluginDevelopmentSDK()
    code = sdk.generate_plugin_code(template_type, "My Plug", "MyPlug", "1.0.0", "me")

    # No leftover format escapes must remain in the generated source.
    assert "{{" not in code and "}}" not in code
    # datetime must be imported since the template body uses it.
    assert "from datetime import datetime, timezone" in code

    namespace = {}
    exec(compile(code, f"{template_type}_plugin.py", "exec"), namespace)
    instance = namespace["MyPlug"]({"x": 1})

    if template_type == "monitoring":
        assert instance.collect_metrics("target")["target"] == "target"
        assert instance.cleanup() is True
    elif template_type == "integration":
        assert instance.connect({}) is True
        assert instance.execute_action("a", {})["status"] == "success"
        assert instance.disconnect() is True
    else:
        assert instance.initialize_model({}) is True
        assert "timestamp" in instance.process_input({"d": 1})


# ---------------------------------------------------------------------------
# core/loki_client.py
# ---------------------------------------------------------------------------
from core.loki_client import LokiClient, LokiQueryResult


def test_loki_build_url_preserves_base_path():
    client = LokiClient(base_url="http://host:3100/loki")
    assert client._build_url("/api/v1/query") == "http://host:3100/loki/api/v1/query"

    client2 = LokiClient(base_url="http://host:3100/")
    assert client2._build_url("/loki/api/v1/labels") == "http://host:3100/loki/api/v1/labels"


def test_loki_query_result_allows_missing_data():
    # Loki error responses may omit ``data`` entirely.
    result = LokiQueryResult(status="error", error="bad request")
    assert result.data == {}


# ---------------------------------------------------------------------------
# core/priority/resource_allocator.py
# ---------------------------------------------------------------------------
from core.priority.resource_allocator import Resource, ResourceAllocator


def test_resource_allocator_reallocates_to_pending_high_priority():
    allocator = ResourceAllocator()
    allocator.add_resource(Resource(id="r1", type="cpu", capacity=10, available=10))

    allocator.allocate(
        [{"id": "lo", "priority": 0.1, "resource_requirement": {"cpu": 10}}], "cpu"
    )
    allocator.allocate(
        [{"id": "hi", "priority": 0.9, "resource_requirement": {"cpu": 10}}], "cpu"
    )
    assert [t["id"] for t in allocator.pending_tasks] == ["hi"]

    allocator.optimize_allocation()
    # The low-priority allocation is released and capacity reallocated to "hi".
    assert sorted(a.task_id for a in allocator.allocations) == ["hi"]
    assert allocator.pending_tasks == []
