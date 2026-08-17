# -*- coding: utf-8 -*-
"""Functional coverage tests for batch15_b core modules."""

import asyncio  # noqa: F401  # Imported for test setup
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest  # noqa: F401  # Imported for test setup
from fastapi import Response

import core.accessibility_support as accessibility_support
import core.api_deprecation as api_deprecation
import core.collaboration_engine as collaboration_engine
import core.service_discovery_manager as service_discovery_manager
import core.service_monitoring_manager as service_monitoring_manager

pytestmark = [pytest.mark.core]


# ---------------------------------------------------------------------------
# core.accessibility_support
# ---------------------------------------------------------------------------
class TestAccessibilitySupport:
    def test_add_accessibility_headers(self):
        response = Response()
        result = accessibility_support.AccessibilityHeaders.add_accessibility_headers(response)  # noqa: F841  # Variable for test verification
        assert result is response
        assert response.headers["Content-Language"] == "zh-CN"
        assert response.headers["Vary"] == "Accept-Language"

    def test_add_a11y_metadata(self):
        response = Response()
        metadata = {
            "wcag_level": "AA",
            "screen_reader_compatible": True,
            "keyboard_navigable": True,
        }
        result = accessibility_support.AccessibilityHeaders.add_a11y_metadata(response, metadata)  # noqa: F841  # Variable for test verification
        assert result is response
        assert response.headers["X-WCAG-Level"] == "AA"
        assert response.headers["X-ScreenReader-Compatible"] == "true"
        assert response.headers["X-Keyboard-Navigable"] == "true"

    def test_get_wcag_levels(self):
        assert accessibility_support.AccessibilityGuidelines.get_waag_level("A")["level"] == "A"
        assert accessibility_support.AccessibilityGuidelines.get_waag_level("AA")["level"] == "AA"
        assert accessibility_support.AccessibilityGuidelines.get_waag_level("AAA")["level"] == "AAA"
        assert accessibility_support.AccessibilityGuidelines.get_waag_level("ZZ")["level"] == "AA"

    def test_accessibility_audit(self):
        data = {
            "images": [
                {"src": "a.png"},
                {"src": "b.png", "alt": "ok"},
            ],
            "colors": [
                {"element": "div", "foreground": "#000", "background": "#fff"},
            ],
            "interactive_elements": [
                {"id": "btn1", "role": "button"},
                {"id": "btn2", "role": "presentation"},
            ],
        }
        result = accessibility_support.AccessibilityAudit.audit_response_data(data)  # noqa: F841  # Variable for test verification
        assert result["total_issues"] == 2
        assert result["wcag_level"] == "AA"
        assert any(i["type"] == "missing_alt_text" for i in result["issues"])
        assert any(i["type"] == "missing_tabindex" for i in result["issues"])

    def test_accessibility_middleware_config(self):
        middleware = accessibility_support.AccessibilityMiddleware()
        assert middleware.get_config()["wcag_level"] == "AA"
        middleware.update_config({"wcag_level": "AAA"})
        assert middleware.get_config()["wcag_level"] == "AAA"

    @pytest.mark.asyncio
    async def test_setup_accessibility_support(self):
        result = await accessibility_support.setup_accessibility_support()  # noqa: F841  # Variable for test verification
        assert result["status"] == "success"
        assert (
            result["wcag_level"]
            == accessibility_support.accessibility_middleware.get_config()["wcag_level"]
        )

    @pytest.mark.asyncio
    async def test_setup_accessibility_support_error(self, monkeypatch):
        monkeypatch.setattr(
            accessibility_support.accessibility_middleware,
            "get_config",
            MagicMock(side_effect=RuntimeError("boom")),
        )
        result = await accessibility_support.setup_accessibility_support()  # noqa: F841  # Variable for test verification
        assert result["status"] == "error"
        assert "boom" in result["error"]


# ---------------------------------------------------------------------------
# core.api_deprecation
# ---------------------------------------------------------------------------
class TestApiDeprecation:
    @pytest.mark.asyncio
    async def test_deprecation_middleware_adds_headers(self, monkeypatch):
        monkeypatch.setattr(api_deprecation, "DEPRECATED_ENDPOINTS", {})
        sunset = datetime.now(timezone.utc) + timedelta(days=30)
        api_deprecation.mark_deprecated("/api/v1/legacy", sunset, replacement="/api/v2/new")

        response = Response()
        call_next = AsyncMock(return_value=response)
        request = MagicMock()
        request.url.path = "/api/v1/legacy"

        result = await api_deprecation.deprecation_middleware(request, call_next)  # noqa: F841  # Variable for test verification
        assert result is response
        assert response.headers["X-API-Deprecated"] == "true"
        assert "X-API-Sunset-Date" in response.headers
        assert "X-API-Days-Until-Sunset" in response.headers
        assert response.headers["X-API-Replacement"] == "/api/v2/new"
        call_next.assert_awaited_once_with(request)

    @pytest.mark.asyncio
    async def test_deprecation_middleware_unchanged(self, monkeypatch):
        monkeypatch.setattr(api_deprecation, "DEPRECATED_ENDPOINTS", {})
        response = Response()
        call_next = AsyncMock(return_value=response)
        request = MagicMock()
        request.url.path = "/api/v1/ok"

        result = await api_deprecation.deprecation_middleware(request, call_next)  # noqa: F841  # Variable for test verification
        assert result is response
        assert "X-API-Deprecated" not in response.headers


# ---------------------------------------------------------------------------
# core.collaboration_engine
# ---------------------------------------------------------------------------
@pytest.fixture
def fresh_collab(tmp_path, monkeypatch):
    """Provide a fresh CollaborationEngine with isolated filesystem and mocked deps."""
    monkeypatch.setattr(collaboration_engine, "DATA_DIR", tmp_path)
    monkeypatch.setattr(collaboration_engine, "DATA_FILE", tmp_path / "collaboration.json")
    monkeypatch.setattr(
        collaboration_engine.alert_service,
        "get_alerts",
        MagicMock(return_value={"alerts": [{"id": "alert-1"}]}),
    )
    monkeypatch.setattr(
        collaboration_engine,
        "get_repair_history",
        MagicMock(return_value=[{"id": "repair-1"}]),
    )
    engine = collaboration_engine.CollaborationEngine()
    monkeypatch.setattr(collaboration_engine, "_collaboration_engine", engine)
    # Expose module-level shortcuts via the fresh engine so the test file also calls them.
    monkeypatch.setattr(collaboration_engine, "list_workspaces", engine.list_workspaces)
    monkeypatch.setattr(collaboration_engine, "get_workspace", engine.get_workspace)
    monkeypatch.setattr(collaboration_engine, "create_workspace", engine.create_workspace)
    monkeypatch.setattr(collaboration_engine, "post_message", engine.post_message)
    monkeypatch.setattr(collaboration_engine, "add_task", engine.add_task)
    monkeypatch.setattr(collaboration_engine, "assign_task", engine.assign_task)
    monkeypatch.setattr(collaboration_engine, "resolve_workspace", engine.resolve_workspace)
    monkeypatch.setattr(collaboration_engine, "get_active_context", engine.get_active_context)
    return engine


class TestCollaborationEngine:
    def test_create_and_list_workspace(self, fresh_collab):
        ws = fresh_collab.create_workspace("incident-1", alert_id="alert-1", assignees=["alice"])
        assert ws["name"] == "incident-1"
        assert ws["alert_id"] == "alert-1"
        assert "alice" in ws["assignees"]

        listed = fresh_collab.list_workspaces()
        assert len(listed) == 1
        assert listed[0]["id"] == ws["id"]

        by_alert = fresh_collab.list_workspaces(alert_id="alert-1")
        assert len(by_alert) == 1

        by_status = fresh_collab.list_workspaces(status="open")
        assert len(by_status) == 1

    def test_create_workspace_rejects_inactive_alert(self, fresh_collab):
        with pytest.raises(ValueError):
            fresh_collab.create_workspace("bad", alert_id="alert-2")

    def test_default_workspace_name(self, fresh_collab):
        ws = fresh_collab.create_workspace("  ")
        assert ws["name"].startswith("Workspace CW-")

    def test_post_message_and_tasks(self, fresh_collab):
        ws = fresh_collab.create_workspace("ops")
        ws_id = ws["id"]

        msg = fresh_collab.post_message(ws_id, "alice", "we have an issue")
        assert msg["user"] == "alice"
        assert msg["content"] == "we have an issue"

        task = fresh_collab.add_task(ws_id, "investigate", assignee="bob")
        assert task["title"] == "investigate"
        assert "bob" in fresh_collab.get_workspace(ws_id)["assignees"]

        updated = fresh_collab.assign_task(ws_id, task["id"], assignee="carol", status="done")
        assert updated["assignee"] == "carol"
        assert updated["status"] == "done"
        assert "carol" in fresh_collab.get_workspace(ws_id)["assignees"]

    def test_post_message_not_found(self, fresh_collab):
        with pytest.raises(ValueError):
            fresh_collab.post_message("no-such", "user", "msg")

    def test_resolve_workspace(self, fresh_collab):
        ws = fresh_collab.create_workspace("done")
        result = fresh_collab.resolve_workspace(ws["id"])  # noqa: F841  # Variable for test verification
        assert result["status"] == "resolved"
        assert any("Resolved at" in n for n in result["notes"])

        resolved = fresh_collab.list_workspaces(status="resolved")
        assert len(resolved) == 1

        with pytest.raises(ValueError):
            fresh_collab.resolve_workspace("missing")

    def test_get_active_context(self, fresh_collab):
        ctx = fresh_collab.get_active_context()
        assert ctx["alerts"] == [{"id": "alert-1"}]
        assert ctx["repairs"] == [{"id": "repair-1"}]

    def test_active_alert_and_repair_failure(self, fresh_collab, monkeypatch):
        monkeypatch.setattr(
            collaboration_engine.alert_service,
            "get_alerts",
            MagicMock(side_effect=Exception("alert down")),
        )
        monkeypatch.setattr(
            collaboration_engine,
            "get_repair_history",
            MagicMock(side_effect=Exception("repair down")),
        )
        assert fresh_collab._active_alert_ids() == set()
        assert fresh_collab._repair_records() == []

    def test_deep_copy_get_workspace(self, fresh_collab):
        ws = fresh_collab.create_workspace("copy")
        got = fresh_collab.get_workspace(ws["id"])
        assert got == ws
        assert got is not fresh_collab._workspaces[ws["id"]]

    def test_assign_task_not_found(self, fresh_collab):
        ws = fresh_collab.create_workspace("tasks")
        with pytest.raises(ValueError):
            fresh_collab.assign_task(ws["id"], "no-task")


# ---------------------------------------------------------------------------
# core.service_discovery_manager
# ---------------------------------------------------------------------------
class FakeRandom:
    def __init__(self, random_value=0.5):
        self.random_value = random_value
        self.exception = None

    def random(self):
        if self.exception:
            raise self.exception
        return self.random_value

    def choice(self, seq):
        return seq[0]

    def uniform(self, a, b):
        return a


@pytest.fixture
def fresh_discovery(monkeypatch):
    monkeypatch.setattr(service_discovery_manager, "_service_discovery_manager", None)
    return service_discovery_manager.ServiceDiscoveryManager()


class TestServiceDiscoveryManager:
    def test_register_and_deregister(self, fresh_discovery):
        inst = fresh_discovery.register_service(
            "web", "w1", "10.0.0.1", 8080, {"dc": "A"}, weight=2
        )
        assert inst.instance_id == "w1"
        assert inst.weight == 2

        # Update existing instance
        updated = fresh_discovery.register_service(
            "web", "w1", "10.0.0.2", 8080, {"dc": "B"}, weight=3
        )
        assert updated.host == "10.0.0.2"
        assert updated.weight == 3
        assert len(fresh_discovery.services["web"]) == 1

        assert fresh_discovery.deregister_service("web", "w1") is True
        assert fresh_discovery.deregister_service("web", "w1") is False

    def test_discover_and_load_balance(self, fresh_discovery, monkeypatch):
        fake_random = FakeRandom()
        monkeypatch.setattr(service_discovery_manager, "_random", fake_random)

        a = fresh_discovery.register_service("web", "a", "10.0.0.1", 8080, weight=1)
        b = fresh_discovery.register_service("web", "b", "10.0.0.2", 8080, weight=1)
        a.status = service_discovery_manager.ServiceStatus.HEALTHY
        b.status = service_discovery_manager.ServiceStatus.HEALTHY

        # Round-robin
        assert fresh_discovery.get_service_instance("web").instance_id == "a"
        assert fresh_discovery.get_service_instance("web").instance_id == "b"

        # Random
        assert (
            fresh_discovery.get_service_instance(
                "web", service_discovery_manager.LoadBalanceStrategy.RANDOM
            ).instance_id
            == "a"
        )

        # Least connections
        a.active_connections = 5
        b.active_connections = 1
        assert (
            fresh_discovery.get_service_instance(
                "web", service_discovery_manager.LoadBalanceStrategy.LEAST_CONNECTIONS
            ).instance_id
            == "b"
        )

        # Weighted
        a.weight = 3
        b.weight = 1
        assert (
            fresh_discovery.get_service_instance(
                "web", service_discovery_manager.LoadBalanceStrategy.WEIGHTED
            ).instance_id
            == "a"
        )

    def test_weighted_zero_weight(self, fresh_discovery, monkeypatch):
        fake_random = FakeRandom()
        monkeypatch.setattr(service_discovery_manager, "_random", fake_random)
        inst = fresh_discovery.register_service("web", "z", "10.0.0.1", 8080, weight=0)
        inst.status = service_discovery_manager.ServiceStatus.HEALTHY
        result = fresh_discovery.get_service_instance(  # noqa: F841  # Variable for test verification
            "web", service_discovery_manager.LoadBalanceStrategy.WEIGHTED
        )
        assert result.instance_id == "z"

    def test_discover_empty(self, fresh_discovery):
        assert fresh_discovery.discover_service("missing") == []

    @pytest.mark.asyncio
    async def test_health_check(self, fresh_discovery, monkeypatch):
        async def fake_sleep(delay):
            await asyncio.sleep(0)

        fake_asyncio = MagicMock()
        fake_asyncio.sleep = fake_sleep
        fake_asyncio.CancelledError = asyncio.CancelledError
        monkeypatch.setattr(service_discovery_manager, "asyncio", fake_asyncio)

        fake_random = FakeRandom(random_value=0.5)
        monkeypatch.setattr(service_discovery_manager, "_random", fake_random)

        inst = fresh_discovery.register_service("web", "h1", "10.0.0.1", 8080)
        healthy = await fresh_discovery.health_check(inst)
        assert healthy is True
        assert inst.status == service_discovery_manager.ServiceStatus.HEALTHY

        fake_random.random_value = 0.05
        unhealthy = await fresh_discovery.health_check(inst)
        assert unhealthy is False
        assert inst.status == service_discovery_manager.ServiceStatus.UNHEALTHY

    @pytest.mark.asyncio
    async def test_health_check_exception(self, fresh_discovery, monkeypatch):
        async def fake_sleep(delay):
            await asyncio.sleep(0)

        fake_asyncio = MagicMock()
        fake_asyncio.sleep = fake_sleep
        fake_asyncio.CancelledError = asyncio.CancelledError
        monkeypatch.setattr(service_discovery_manager, "asyncio", fake_asyncio)

        fake_random = FakeRandom()
        fake_random.exception = RuntimeError("random failed")
        monkeypatch.setattr(service_discovery_manager, "_random", fake_random)

        inst = fresh_discovery.register_service("web", "h2", "10.0.0.2", 8080)
        result = await fresh_discovery.health_check(inst)  # noqa: F841  # Variable for test verification
        assert result is False
        assert inst.status == service_discovery_manager.ServiceStatus.UNHEALTHY

    @pytest.mark.asyncio
    async def test_start_health_check_loop(self, fresh_discovery, monkeypatch):
        async def fake_sleep(delay):
            await asyncio.sleep(0)

        fake_asyncio = MagicMock()
        fake_asyncio.sleep = fake_sleep
        fake_asyncio.CancelledError = asyncio.CancelledError
        monkeypatch.setattr(service_discovery_manager, "asyncio", fake_asyncio)

        fake_random = FakeRandom(random_value=0.5)
        monkeypatch.setattr(service_discovery_manager, "_random", fake_random)

        fresh_discovery.health_check_config.interval_seconds = 0
        fresh_discovery.register_service("web", "loop", "10.0.0.1", 8080)

        task = asyncio.create_task(fresh_discovery.start_health_check_loop())
        await asyncio.sleep(0.01)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        assert fresh_discovery.total_health_checks > 0

    def test_get_service_summary_and_details(self, fresh_discovery):
        a = fresh_discovery.register_service("web", "a", "10.0.0.1", 8080)
        a.status = service_discovery_manager.ServiceStatus.HEALTHY
        b = fresh_discovery.register_service("web", "b", "10.0.0.2", 8080)
        b.status = service_discovery_manager.ServiceStatus.UNHEALTHY

        summary = fresh_discovery.get_service_summary()
        assert summary["total_services"] == 1
        assert summary["total_instances"] == 2
        assert summary["healthy_instances"] == 1
        assert summary["unhealthy_instances"] == 1

        details = fresh_discovery.get_service_details("web")
        assert details["service_name"] == "web"
        assert details["instance_count"] == 2

    def test_get_service_discovery_manager(self, monkeypatch):
        monkeypatch.setattr(service_discovery_manager, "_service_discovery_manager", None)
        manager = service_discovery_manager.get_service_discovery_manager()
        assert isinstance(manager, service_discovery_manager.ServiceDiscoveryManager)
        assert service_discovery_manager.get_service_discovery_manager() is manager

    def test_init_with_config(self):
        manager = service_discovery_manager.ServiceDiscoveryManager(
            {
                "load_balance_strategy": "random",
                "health_check": {"interval_seconds": 5},
            }
        )
        assert manager.load_balance_strategy == service_discovery_manager.LoadBalanceStrategy.RANDOM
        assert manager.health_check_config.interval_seconds == 5


# ---------------------------------------------------------------------------
# core.service_monitoring_manager
# ---------------------------------------------------------------------------
class TestServiceMonitoringManager:
    def test_record_and_get_metrics(self):
        manager = service_monitoring_manager.ServiceMonitoringManager()
        for i in range(3):
            manager.record_metric("cpu", "svc", 50.0 + i, labels={"host": "h1"})

        metrics = manager.get_service_metrics("svc")
        assert len(metrics) == 3

        recent = manager.get_service_metrics("svc", time_range=timedelta(minutes=1))
        assert len(recent) == 3

    def test_analyze_service_performance(self):
        manager = service_monitoring_manager.ServiceMonitoringManager()
        for i in range(5):
            manager.record_metric("cpu", "svc", 10.0 + i)

        analysis = manager.analyze_service_performance("svc")
        assert analysis["service_name"] == "svc"
        assert analysis["metrics_count"] == 5
        assert "cpu" in analysis["metric_analysis"]
        assert analysis["metric_analysis"]["cpu"]["avg"] == 12.0

        empty = manager.analyze_service_performance("none")
        assert empty["metrics_count"] == 0

    def test_detect_anomaly(self):
        manager = service_monitoring_manager.ServiceMonitoringManager()
        for i in range(12):
            manager.record_metric("latency", "web", 100.0 + (i % 3))

        normal = manager.detect_anomaly("latency", "web", 101.0)
        assert normal.is_anomaly is False

        anomaly = manager.detect_anomaly("latency", "web", 300.0)
        assert anomaly.is_anomaly is True
        assert anomaly.anomaly_score > 0
        assert manager.total_anomalies_detected == 1

        insufficient = manager.detect_anomaly("new", "web", 1.0)
        assert insufficient.is_anomaly is False
        assert "message" in insufficient.metadata

    def test_alert_rules(self):
        manager = service_monitoring_manager.ServiceMonitoringManager()

        manager.record_metric("cpu", "svc", 95.0)
        manager.record_metric("mem", "svc", 10.0)
        manager.record_metric("disk", "svc", 50.0)

        manager.create_alert_rule(
            "r1",
            "svc",
            "cpu",
            80.0,
            comparison="greater_than",
            severity=service_monitoring_manager.AlertSeverity.ERROR,
        )
        manager.create_alert_rule(
            "r2",
            "svc",
            "mem",
            20.0,
            comparison="less_than",
            severity=service_monitoring_manager.AlertSeverity.WARNING,
        )
        manager.create_alert_rule(
            "r3",
            "svc",
            "disk",
            50.0,
            comparison="equals",
            severity=service_monitoring_manager.AlertSeverity.INFO,
        )

        alerts = manager.check_alert_rules()
        assert len(alerts) == 3
        assert manager.total_alerts_generated == 3

        # Cooldown should suppress further alerts
        no_alerts = manager.check_alert_rules()
        assert len(no_alerts) == 0
        assert manager.total_alerts_generated == 3

        # Disable cooldown and re-trigger
        manager.alert_cooldown_seconds = 0
        more = manager.check_alert_rules()
        assert len(more) == 3
        assert manager.total_alerts_generated == 6

    def test_monitoring_summary(self):
        manager = service_monitoring_manager.ServiceMonitoringManager()
        manager.record_metric("cpu", "svc", 1.0)
        summary = manager.get_monitoring_summary()
        assert summary["total_metrics_collected"] == 1
        assert summary["total_services_monitored"] == 1

    def test_percentile(self):
        manager = service_monitoring_manager.ServiceMonitoringManager()
        assert manager._calculate_percentile([], 95) == 0.0
        assert manager._calculate_percentile([1, 2, 3, 4, 5], 95) == 5

    def test_get_service_monitoring_manager(self, monkeypatch):
        monkeypatch.setattr(service_monitoring_manager, "_service_monitoring_manager", None)
        manager = service_monitoring_manager.get_service_monitoring_manager()
        assert isinstance(manager, service_monitoring_manager.ServiceMonitoringManager)
        assert service_monitoring_manager.get_service_monitoring_manager() is manager
