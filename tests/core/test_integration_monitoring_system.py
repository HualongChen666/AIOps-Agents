# -*- coding: utf-8 -*-
"""测试集成监控系统模块"""

import asyncio

import pytest

from core.integration_monitoring_system import (
    Alert,
    AlertSeverity,
    IntegrationMonitoringSystem,
    MetricType,
    Monitor,
    get_integration_monitoring_system,
)


@pytest.fixture
def system():
    return IntegrationMonitoringSystem({"data_retention_hours": 168})


class TestInitialization:
    def test_default_monitors_and_alerts(self):
        s = IntegrationMonitoringSystem()
        assert "cpu_monitor" in s.monitors
        assert "cpu_alert" in s.alerts

    def test_get_system(self):
        s = get_integration_monitoring_system()
        assert isinstance(s, IntegrationMonitoringSystem)


class TestMetricsAndAlerts:
    def test_record_metric_triggers_alert(self, system):
        calls = []

        async def handler(alert, instance):
            calls.append(alert.alert_id)

        system.register_notification_handler(handler)
        asyncio.run(system.record_metric("system.cpu.usage", 95.0))

        assert len(system.alert_instances) == 1
        assert system.alert_instances[0].alert_id == "cpu_alert"
        assert calls == ["cpu_alert"]
        assert system.total_metrics == 1
        assert system.active_alerts == 1

    def test_record_metric_no_alert_below_threshold(self, system):
        asyncio.run(system.record_metric("system.cpu.usage", 50.0))
        assert len(system.alert_instances) == 0

    def test_record_metric_less_than(self, system):
        asyncio.run(system.record_metric("integration.health", 0.5))
        assert any(a.alert_id == "integration_health_alert" for a in system.alert_instances)

    def test_register_monitor_and_alert(self, system):
        m = Monitor(
            monitor_id="custom",
            monitor_name="Custom",
            metric_type=MetricType.GAUGE,
            target="custom.metric",
            threshold=10.0,
            comparison="greater_than",
        )
        system.register_monitor(m)
        assert system.monitors["custom"] is m

        a = Alert(
            alert_id="custom_alert",
            alert_name="Custom Alert",
            monitor_id="custom",
            severity=AlertSeverity.WARNING,
            condition="x > 10",
        )
        system.register_alert(a)
        assert system.alerts["custom_alert"] is a


class TestQueriesAndResolve:
    def test_get_metrics_filter_and_limit(self, system):
        asyncio.run(system.record_metric("system.cpu.usage", 70.0))
        asyncio.run(system.record_metric("system.cpu.usage", 80.0))
        asyncio.run(system.record_metric("system.memory.usage", 60.0))

        all_cpu = system.get_metrics("system.cpu.usage")
        assert len(all_cpu) == 2
        assert all_cpu[-1]["value"] == 80.0

        assert system.get_metrics("unknown") == []

    def test_get_alerts_filter(self, system):
        asyncio.run(system.record_metric("system.cpu.usage", 95.0))
        asyncio.run(system.record_metric("api.latency", 600.0))

        all_alerts = system.get_alerts()
        assert len(all_alerts) == 2

        critical = system.get_alerts(severity=AlertSeverity.CRITICAL)
        assert len(critical) == 0  # cpu=warning, latency=error

    def test_resolve_alert(self, system):
        asyncio.run(system.record_metric("system.cpu.usage", 95.0))
        instance = system.alert_instances[0]
        assert asyncio.run(system.resolve_alert(instance.alert_instance_id)) is True
        assert instance.status == "resolved"
        assert system.active_alerts == 0


class TestPruneAndStatistics:
    def test_prune_old_metrics(self):
        s = IntegrationMonitoringSystem({"data_retention_hours": -1})
        asyncio.run(s.record_metric("system.cpu.usage", 95.0))
        asyncio.run(s._prune_old_metrics())
        assert len(s.metrics.get("system.cpu.usage", [])) == 0

    def test_get_statistics(self, system):
        asyncio.run(system.record_metric("system.cpu.usage", 95.0))
        stats = system.get_statistics()
        assert stats["total_metrics"] == 1
        assert stats["total_alert_instances"] >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
