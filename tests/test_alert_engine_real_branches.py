# -*- coding: utf-8 -*-
"""
Real (no-mock) branch coverage tests for core.alert_engine.

Uses the actual AlertEngine module with in-memory data.  Exercises the
conditional branches for deduplication, suppression, enrichment, routing,
severity updates, correlation, missing alert fields, invalid provider/fallback,
and dynamic thresholds.
"""

import asyncio
import datetime
import math
import os
import statistics
from collections import deque
from typing import Any, Dict, List

import pytest

import core.alert_engine as ae
from core.alert_engine import (
    AlertRoutingStrategy,
    AlertTopologyCorrelation,
    AlertTrendPredictor,
    AutomaticAlertRouter,
    TrendPredictionModel,
    _check_ssh_brute_force,
    _cleanup_dedup_cache,
    _cleanup_ssh_brute_force_cache,
    _cpu_level,
    _dedup_key,
    _disk_level,
    _get_alert_repository,
    _get_dynamic_warn_threshold,
    _mem_level,
    _safe_float,
    _try_dedup,
    alert_history,
    alert_topology_correlation,
    alert_trend_predictor,
    automatic_alert_router,
    broadcast,
    check_and_generate_alerts,
    check_linux_security_alerts,
    clear_dedup_cache,
    clear_ssh_brute_force_cache,
    get_dedup_stats,
    get_summary_metrics,
    register_ws,
    unregister_ws,
)
from core.metrics_history import metrics_history


# ---------------------------------------------------------------------------
# In-memory helpers (not mocks – real minimal objects used by the engine)
# ---------------------------------------------------------------------------
class InMemoryAlertRepository:
    """Minimal in-memory repository used by the engine under test."""

    def __init__(self, initial: list[dict[str, Any]] | None = None):
        self.alerts: list[dict[str, Any]] = list(initial or [])

    async def save(self, alert: dict[str, Any]) -> None:
        self.alerts.append(alert)

    async def get_recent(self, limit: int = 1000) -> list[dict[str, Any]]:
        return self.alerts[-limit:][::-1]


class FailingSaveRepository(InMemoryAlertRepository):
    """Repository whose save() raises, to exercise fallback branches."""

    async def save(self, alert: dict[str, Any]) -> None:
        raise RuntimeError("simulated persistence failure")


class FailingGetRecentRepository(InMemoryAlertRepository):
    """Repository whose get_recent() raises, to exercise restore fallback."""

    async def get_recent(self, limit: int = 1000) -> list[dict[str, Any]]:
        raise RuntimeError("simulated get_recent failure")


# ---------------------------------------------------------------------------
# per-test setup / teardown
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def _reset_alert_engine_state():
    """Clear hot caches and global state before every test."""
    clear_dedup_cache()
    clear_ssh_brute_force_cache()
    alert_history.clear()
    metrics_history.clear()
    alert_trend_predictor.historical_data.clear()
    alert_trend_predictor.predictions.clear()
    alert_topology_correlation.topology_graph = {}
    alert_topology_correlation.alert_correlation_rules = []
    automatic_alert_router.routes = []
    automatic_alert_router.routing_history = []
    # keep default routes for the global router
    automatic_alert_router.add_route(
        route_id="critical_alert",
        conditions={"severity": "critical"},
        target_channel="email",
        priority=10,
    )
    automatic_alert_router.add_route(
        route_id="warning_alert",
        conditions={"severity": "warning"},
        target_channel="webhook",
        priority=5,
    )

    # disable dynamic thresholds by default; individual tests re-enable
    ae.DYNAMIC_THRESHOLD_CONFIG["enabled"] = False
    ae.DYNAMIC_THRESHOLD_CONFIG["min_samples"] = 30
    ae.DYNAMIC_THRESHOLD_CONFIG["sigma"] = 2.0
    ae.DYNAMIC_THRESHOLD_CONFIG["flat_boost"] = 5.0

    # avoid heavy auto-heal and external notification calls
    os.environ["HEAL_MAINTENANCE_MODE"] = "true"
    os.environ.setdefault("NOTIFY_ENABLED", "false")

    # attach an in-memory repository
    old_repo = ae.alert_repository
    ae.alert_repository = InMemoryAlertRepository()
    yield
    ae.alert_repository = old_repo
    if "HEAL_MAINTENANCE_MODE" in os.environ:
        del os.environ["HEAL_MAINTENANCE_MODE"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _disk_alert(alert_id: str, level: str = "warning") -> dict[str, Any]:
    return {
        "id": alert_id,
        "level": level,
        "metric": "disk_percent",
    }


def _cpu_alert(level: str = "warning") -> dict[str, Any]:
    return {
        "id": "CPU-12:00:00",
        "level": level,
        "metric": "cpu_percent",
    }


# ---------------------------------------------------------------------------
# Dedup / suppression / cache
# ---------------------------------------------------------------------------
def test_dedup_key_disk_branches():
    # full device extraction
    assert _dedup_key(_disk_alert("DISK-C:-12:00:00")) == "disk_percent_warning_C:"
    # DISK- prefix but not enough parts
    assert _dedup_key(_disk_alert("DISK-")) == "disk_percent_warning"
    assert _dedup_key(_disk_alert("DISK-X")) == "disk_percent_warning"
    # disk_percent but id does not start with DISK- falls back
    assert _dedup_key(_disk_alert("CPU-12:00:00")) == "disk_percent_warning"
    # non-disk metric
    assert _dedup_key(_cpu_alert()) == "cpu_percent_warning"


def test_dedup_suppression_and_stats():
    a = _cpu_alert()
    assert _try_dedup(a) is False
    # duplicate within the 5 minute window is suppressed
    assert _try_dedup(_cpu_alert()) is True
    stats = get_dedup_stats()
    assert stats["active_windows"] == 1
    assert stats["total_suppressed"] == 1


def test_dedup_expired_window_and_prev_suppressed():
    now = datetime.datetime.now()
    ae._dedup_cache["cpu_percent_warning"] = {
        "last_time": now - datetime.timedelta(seconds=ae._DEDUP_WINDOW_SEC + 1),
        "repeat_count": 3,
        "last_alert": _cpu_alert(),
    }
    a = _cpu_alert()
    result = _try_dedup(a)
    assert result is False
    assert a.get("prev_suppressed") == 3

    stats = get_dedup_stats()
    assert stats["active_windows"] == 1


def test_dedup_cache_capacity_and_cleanup():
    # manually stuff the cache above its hard max, then add a new key
    for i in range(ae._DEDUP_CACHE_MAX + 1):
        ae._dedup_cache[f"metric_{i}_warning"] = {
            "last_time": datetime.datetime.now(),
            "repeat_count": 0,
            "last_alert": {},
        }
    new_alert = {"id": f"CPU-{i}", "level": "warning", "metric": "cpu_percent"}
    assert _try_dedup(new_alert) is False
    assert len(ae._dedup_cache) == ae._DEDUP_CACHE_MAX


def test_cleanup_dedup_cache_removes_expired_with_suppressed():
    now = datetime.datetime.now()
    ae._dedup_cache["old_key"] = {
        "last_time": now - datetime.timedelta(seconds=ae._DEDUP_WINDOW_SEC * 2 + 1),
        "repeat_count": 7,
        "last_alert": {},
    }
    _cleanup_dedup_cache()
    assert "old_key" not in ae._dedup_cache


# ---------------------------------------------------------------------------
# SSH brute force
# ---------------------------------------------------------------------------
def test_ssh_brute_force_branches():
    clear_ssh_brute_force_cache()

    # not enough samples
    assert _check_ssh_brute_force("h1", 5) is None
    # low increment
    assert _check_ssh_brute_force("h1", 8) is None

    # fresh host, two samples, big jump -> alert
    first = _check_ssh_brute_force("h2", 0)
    assert first is None
    second = _check_ssh_brute_force("h2", 20)
    assert second is not None
    assert second["level"] == "critical"

    # cooldown
    assert _check_ssh_brute_force("h2", 25) is None

    # negative increment (logrotate) resets the window
    third = _check_ssh_brute_force("h2", 5)
    assert third is None

    # cooldown: still above threshold but within 10 minutes of last alert
    cooldown = _check_ssh_brute_force("h2", 35)
    assert cooldown is None


def test_cleanup_ssh_brute_force_cache():
    now = datetime.datetime.now()
    ae._ssh_failed_window["expired"] = []
    ae._ssh_failed_window["old"] = [
        (now - datetime.timedelta(seconds=ae._SSH_CACHE_EXPIRY_SEC + 5), 1)
    ]
    ae._ssh_last_alert_time["gone"] = now - datetime.timedelta(seconds=ae._SSH_CACHE_EXPIRY_SEC + 5)
    _cleanup_ssh_brute_force_cache()
    assert "expired" not in ae._ssh_failed_window
    assert "old" not in ae._ssh_failed_window
    assert "gone" not in ae._ssh_last_alert_time


def test_cleanup_ssh_brute_force_max_hosts():
    now = datetime.datetime.now()
    for i in range(ae._SSH_CACHE_MAX_HOSTS + 2):
        ae._ssh_failed_window[f"host_{i}"] = [(now - datetime.timedelta(seconds=i), i)]
    _cleanup_ssh_brute_force_cache()
    assert len(ae._ssh_failed_window) <= ae._SSH_CACHE_MAX_HOSTS


# ---------------------------------------------------------------------------
# Linux security alert pipeline
# ---------------------------------------------------------------------------
def test_check_linux_security_alerts_valid_and_fallback():
    hosts = [
        {"name": "host-a", "status": "ok", "metrics": {"ssh_failed_logins": {"value": 20}}},
    ]
    result = asyncio.run(check_linux_security_alerts(hosts))
    assert len(result) == 1
    assert result[0]["alert_type"] == "ssh_brute_force"


def test_check_linux_security_alerts_invalid_inputs():
    # not a list
    assert asyncio.run(check_linux_security_alerts(None)) == []
    assert asyncio.run(check_linux_security_alerts(123)) == []

    # invalid host entries
    hosts = [
        None,
        "not-a-dict",
        {"status": "down", "metrics": {"ssh_failed_logins": {"value": 20}}},
        {"name": "bad", "status": "ok", "metrics": "not-a-dict"},
        {"name": "bad", "status": "ok", "metrics": {"ssh_failed_logins": "not-a-dict"}},
        {"name": "bad", "status": "ok", "metrics": {"ssh_failed_logins": {"value": ""}}},
        {"name": "bad", "status": "ok", "metrics": {"ssh_failed_logins": {"value": "ERROR"}}},
        {"name": "bad", "status": "ok", "metrics": {"ssh_failed_logins": {"value": "abc"}}},
    ]
    result = asyncio.run(check_linux_security_alerts(hosts))
    assert result == []


def test_check_linux_security_alerts_cooldown():
    host = {"name": "cool", "status": "ok", "metrics": {"ssh_failed_logins": {"value": 20}}}
    first = asyncio.run(check_linux_security_alerts([host]))
    assert len(first) == 1
    # same host/count within cooldown should not fire a second alert
    second = asyncio.run(check_linux_security_alerts([host]))
    assert second == []


def test_check_linux_security_alerts_persistence_failure_falls_back():
    ae.alert_repository = FailingSaveRepository()
    host = {"name": "fail-db", "status": "ok", "metrics": {"ssh_failed_logins": {"value": 20}}}
    # engine catches the save error and still appends to memory
    result = asyncio.run(check_linux_security_alerts([host]))
    assert len(result) == 1


# ---------------------------------------------------------------------------
# Numeric helpers and severity levels
# ---------------------------------------------------------------------------
def test_safe_float():
    assert _safe_float(None) == 0.0
    assert _safe_float(42) == 42.0
    assert _safe_float(3.14) == 3.14
    assert _safe_float("  2.5 ") == 2.5
    assert _safe_float("nope") == 0.0


def test_cpu_mem_disk_levels():
    # dynamic disabled -> fixed thresholds
    ae.DYNAMIC_THRESHOLD_CONFIG["enabled"] = False
    assert _cpu_level(50.0) == "normal"
    assert _cpu_level(85.0) == "warning"
    assert _cpu_level(95.0) == "critical"

    assert _mem_level(50.0) == "normal"
    assert _mem_level(86.0) == "warning"
    assert _mem_level(95.0) == "critical"

    assert _disk_level(50.0) == "normal"
    assert _disk_level(91.0) == "warning"
    assert _disk_level(98.0) == "critical"


# ---------------------------------------------------------------------------
# Dynamic threshold fallback
# ---------------------------------------------------------------------------
def test_dynamic_threshold_branches():
    ae.DYNAMIC_THRESHOLD_CONFIG["enabled"] = True
    ae.DYNAMIC_THRESHOLD_CONFIG["min_samples"] = 3
    ae.DYNAMIC_THRESHOLD_CONFIG["sigma"] = 2.0
    ae.DYNAMIC_THRESHOLD_CONFIG["flat_boost"] = 5.0
    metrics_history.clear()

    # unknown metric falls back to static
    threshold = _get_dynamic_warn_threshold("disk_percent", 90.0)
    assert threshold == 90.0

    # flat data -> mean + flat_boost below static floor
    for _ in range(3):
        metrics_history.push_metric("cpu", 40.0, service="global")
    threshold = _get_dynamic_warn_threshold("cpu", 80.0)
    assert threshold == 80.0

    # variable data -> dynamic normal, but floor still respected
    metrics_history.clear()
    for v in [60.0, 70.0, 80.0, 90.0, 100.0]:
        metrics_history.push_metric("memory", v, service="global")
    threshold = _get_dynamic_warn_threshold("memory", 85.0)
    assert threshold > 85.0

    # disabled returns static immediately
    ae.DYNAMIC_THRESHOLD_CONFIG["enabled"] = False
    threshold = _get_dynamic_warn_threshold("cpu", 70.0)
    assert threshold == 70.0


# ---------------------------------------------------------------------------
# Alert generation
# ---------------------------------------------------------------------------
def test_check_and_generate_alerts_branches():
    ae.DYNAMIC_THRESHOLD_CONFIG["enabled"] = False
    metrics_history.clear()

    assert check_and_generate_alerts(None) == []
    assert check_and_generate_alerts("bad") == []
    assert check_and_generate_alerts({}) == []

    metrics = {
        "cpu": {"usage_percent": 90},
        "memory": {"usage_percent": 95, "used_gb": 8, "total_gb": 16},
        "disk": [
            {"device": "C:", "usage_percent": 92},
            {"device": "D:", "percent": 98},
            "not-a-dict",
            {"device": "E:"},  # missing usage -> normal
        ],
    }
    alerts = check_and_generate_alerts(metrics)
    assert len(alerts) == 4
    assert alerts[0]["metric"] == "cpu_percent"
    assert alerts[1]["metric"] == "memory_percent"
    assert alerts[2]["metric"] == "disk_percent"
    assert alerts[3]["metric"] == "disk_percent"
    assert alerts[0]["level"] == "warning"
    assert alerts[1]["level"] == "critical"
    assert alerts[2]["level"] == "warning"
    assert alerts[3]["level"] == "critical"


def test_check_and_generate_alerts_invalid_metric_types():
    metrics = {
        "cpu": "bad",
        "memory": "bad",
        "disk": "not-a-list",
    }
    assert check_and_generate_alerts(metrics) == []


# ---------------------------------------------------------------------------
# WebSocket broadcast
# ---------------------------------------------------------------------------
class FakeWebSocket:
    def __init__(self, fail: bool = False):
        self.fail = fail
        self.sent: list[str] = []

    async def send_text(self, text: str) -> None:
        if self.fail:
            raise RuntimeError("boom")
        self.sent.append(text)


def test_broadcast_and_ws_lifecycle():
    assert asyncio.run(broadcast({"type": "empty"})) is None

    ws1 = FakeWebSocket()
    ws2 = FakeWebSocket(fail=True)
    register_ws(ws1)
    register_ws(ws2)

    asyncio.run(broadcast({"type": "hello"}))
    assert len(ws1.sent) == 1
    assert ws2 not in ae._ws_subscribers

    # successful subscriber only -> no dead connections
    unregister_ws(ws1)
    ws3 = FakeWebSocket()
    register_ws(ws3)
    asyncio.run(broadcast({"type": "hello2"}))
    assert len(ws3.sent) == 1
    assert len(ae._ws_subscribers) == 1

    unregister_ws(ws3)
    assert len(ae._ws_subscribers) == 0


# ---------------------------------------------------------------------------
# Routing
# ---------------------------------------------------------------------------
def test_automatic_alert_router():
    router = AutomaticAlertRouter()
    router.add_route(
        route_id="cpu_warning",
        conditions={"metric": "cpu_percent"},
        target_channel="slack",
        priority=8,
    )
    router.add_route(
        route_id="disk_critical",
        conditions={"metric": "disk_percent", "level": "critical"},
        target_channel="pagerduty",
        priority=10,
    )

    # rule-based only
    router.strategy = AlertRoutingStrategy.RULE_BASED
    assert router.route_alert({"metric": "memory_percent"}) == []
    assert router.route_alert({"metric": "cpu_percent", "level": "warning"}) == ["slack"]

    # ML-only: high urgency keywords
    router.strategy = AlertRoutingStrategy.ML_BASED
    alert = {
        "id": "x",
        "severity": "critical",
        "title": "service outage down critical",
        "message": "latency timeout fail error",
        "source_service": "svc",
    }
    ml = router._ml_route_alert(alert)
    assert "email" in ml
    assert "sms" in ml
    assert "webhook" in ml

    # hybrid combines rule + ML channels
    router.strategy = AlertRoutingStrategy.HYBRID
    assert set(
        router.route_alert(
            {
                "metric": "cpu_percent",
                "severity": "critical",
                "title": "service outage down critical",
                "message": "latency timeout fail error",
            }
        )
    ) == {
        "slack",
        "email",
        "sms",
        "webhook",
    }

    # routing history trim
    for i in range(1001):
        router.route_alert({"id": f"h{i}"})
    assert len(router.routing_history) <= 1000


def test_ml_route_alert_same_source_boost():
    router = AutomaticAlertRouter()
    router.strategy = AlertRoutingStrategy.ML_BASED
    # seed history with a recent route for the same source
    router.routing_history = [
        {
            "alert_id": "prev",
            "channels": ["webhook"],
            "timestamp": datetime.datetime.now().isoformat(),
        },
    ]
    alert = {
        "id": "x",
        "severity": "warning",
        "title": "outage",
        "message": "",
        "source_service": "webhook",
    }
    # "webhook" appears in the previous channels string, triggering same_source boost
    channels = router._ml_route_alert(alert)
    assert "email" in channels


def test_match_conditions_missing_field():
    router = AutomaticAlertRouter()
    assert router._match_conditions({"a": 1}, {"a": 1}) is True
    assert router._match_conditions({"a": 1}, {"b": 1}) is False


def test_get_routing_stats():
    router = AutomaticAlertRouter()
    router.route_alert({"id": "a", "severity": "critical"})
    stats = router.get_routing_stats()
    assert stats["total_routes"] == 1
    assert stats["strategy"] == AlertRoutingStrategy.HYBRID.value


# ---------------------------------------------------------------------------
# Topology correlation
# ---------------------------------------------------------------------------
def test_alert_topology_correlation():
    corr = AlertTopologyCorrelation()
    alerts = [
        {"source": "web", "type": "cpu_high"},
        {"source": "web", "type": "cpu_high"},  # covers already-present branch
        {"source": "web", "type": "disk_high"},
        {"source": "web", "type": "disk_high"},  # covers already-present branch
        {"source": "db", "type": "cpu_high"},
    ]
    topo = corr.build_topology_from_alerts(alerts)
    assert "web" in topo
    assert "processes" in topo["web"]
    assert "storage" in topo["web"]

    # source not in graph
    assert corr.correlate_alerts_with_topology({"source": "missing"}) == []

    # build an explicit dependency so correlation returns the dependency
    corr.topology_graph = {"web": ["db"], "db": []}
    assert corr.correlate_alerts_with_topology({"source": "web"}) == ["db"]

    impact = corr.get_impact_analysis({"source": "db"})
    assert impact["source"] == "db"
    assert "web" in impact["affected_services"]


# ---------------------------------------------------------------------------
# Trend prediction
# ---------------------------------------------------------------------------
def test_alert_trend_predictor():
    tp = AlertTrendPredictor(model=TrendPredictionModel.MOVING_AVERAGE)

    # unknown metric
    assert tp.predict_trend("missing") is None

    # fewer than 10 samples
    for i in range(5):
        tp.add_historical_data("cpu", float(i))
    assert tp.predict_trend("cpu") is None

    # stable trend (ten identical values)
    if "cpu" in tp.historical_data:
        del tp.historical_data["cpu"]
    for _ in range(10):
        tp.add_historical_data("cpu", 10.0)
    pred = tp.predict_trend("cpu", 3)
    assert pred is not None
    assert pred.trend_direction == "stable"

    # increasing trend
    for i in range(10):
        tp.add_historical_data("up", float(i * 10))
    pred = tp.predict_trend("up", 3)
    assert pred.trend_direction == "increasing"

    # decreasing trend
    for i in range(10):
        tp.add_historical_data("down", float(100 - i * 10))
    pred = tp.predict_trend("down", 3)
    assert pred.trend_direction == "decreasing"

    # linear regression model
    tp_lr = AlertTrendPredictor(model=TrendPredictionModel.LINEAR_REGRESSION)
    for i in range(10):
        tp_lr.add_historical_data("lr", float(2 * i + 1))
    pred = tp_lr.predict_trend("lr", 3)
    assert pred is not None

    # else branch: exponential smoothing -> falls back to moving average
    tp_es = AlertTrendPredictor(model=TrendPredictionModel.EXPONENTIAL_SMOOTHING)
    for i in range(10):
        tp_es.add_historical_data("es", 5.0)
    pred = tp_es.predict_trend("es", 3)
    assert pred is not None


def test_alert_trend_predictor_trim():
    tp = AlertTrendPredictor()
    for i in range(1002):
        tp.add_historical_data("trim", float(i))
    assert len(tp.historical_data["trim"]) == 1000


def test_get_prediction_summary():
    tp = AlertTrendPredictor()
    for i in range(10):
        tp.add_historical_data("sum", float(i))
    tp.predict_trend("sum")
    summary = tp.get_prediction_summary()
    assert summary["metrics_with_predictions"] == 1


# ---------------------------------------------------------------------------
# Repository / cache helpers
# ---------------------------------------------------------------------------
def test_get_alert_repository_hook_and_restore():
    repo = InMemoryAlertRepository([{"id": "cached"}])
    ae.alert_repository = repo
    assert _get_alert_repository() is repo

    # with module-level attribute cleared, falls back to the default db import
    ae.alert_repository = None
    default_repo = _get_alert_repository()
    assert default_repo is not None
    ae.alert_repository = repo


def test_restore_alert_cache():
    repo = InMemoryAlertRepository([{"id": "r1"}, {"id": "r2"}])
    ae.alert_repository = repo
    alert_history.clear()
    asyncio.run(ae._restore_alert_cache())
    assert len(alert_history) == 2


def test_restore_alert_cache_failure():
    ae.alert_repository = FailingGetRecentRepository()
    alert_history.clear()
    asyncio.run(ae._restore_alert_cache())
    assert len(alert_history) == 0


def test_clear_caches():
    ae._dedup_cache["x"] = {"last_time": datetime.datetime.now()}
    ae._ssh_failed_window["h"] = []
    assert clear_dedup_cache() >= 0
    assert clear_ssh_brute_force_cache() >= 0


def test_cleanup_dedup_cache_empty_and_zero_repeat():
    _cleanup_dedup_cache()  # empty cache -> 1024 loop exits immediately
    now = datetime.datetime.now()
    ae._dedup_cache["zero"] = {
        "last_time": now - datetime.timedelta(seconds=ae._DEDUP_WINDOW_SEC * 2 + 1),
        "repeat_count": 0,
        "last_alert": {},
    }
    _cleanup_dedup_cache()
    assert "zero" not in ae._dedup_cache


# ---------------------------------------------------------------------------
# Summary metrics
# ---------------------------------------------------------------------------
def test_get_summary_metrics():
    summary = asyncio.run(get_summary_metrics())
    assert isinstance(summary, dict)


def test_alert_monitor_loop_one_iteration():
    # short sleep so a single real collection cycle can be cancelled quickly
    ae.COLLECT_INTERVAL_SEC = 0.01
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    task = loop.create_task(ae.alert_monitor_loop())
    # allow one collect_all + processing + a tiny sleep, then cancel
    loop.run_until_complete(asyncio.sleep(5))
    task.cancel()
    try:
        loop.run_until_complete(task)
    except asyncio.CancelledError:
        pass
    finally:
        loop.close()
