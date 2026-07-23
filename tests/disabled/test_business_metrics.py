# -*- coding: utf-8 -*-
# tests/test_business_metrics.py
# 业务指标单元测试
from datetime import datetime, timedelta, timezone

import pytest

from core.business_metrics import (
    AlertEvent,
    BusinessMetrics,
    BusinessMetricsCollector,
)


class TestAlertEvent:
    """告警事件测试"""

    def test_alert_event_creation(self):
        """测试告警事件创建"""
        event = AlertEvent(alert_id="test-001", created_at=datetime.now(timezone.utc))
        assert event.alert_id == "test-001"
        assert event.severity == "medium"
        assert event.auto_healed is False
        assert event.acknowledged_at is None
        assert event.resolved_at is None

    def test_alert_event_with_optional_fields(self):
        """测试告警事件可选字段"""
        now = datetime.now(timezone.utc)
        event = AlertEvent(
            alert_id="test-002",
            created_at=now,
            severity="critical",
            auto_healed=True,
            assigned_to="admin",
        )
        assert event.severity == "critical"
        assert event.auto_healed is True
        assert event.assigned_to == "admin"

    def test_alert_event_acknowledgment(self):
        """测试告警确认"""
        created = datetime.now(timezone.utc)
        acknowledged = created + timedelta(minutes=5)

        event = AlertEvent(alert_id="test-003", created_at=created, acknowledged_at=acknowledged)

        assert event.acknowledged_at == acknowledged
        # Calculate MTTA (Mean Time To Acknowledge)
        mtta = (event.acknowledged_at - event.created_at).total_seconds()
        assert mtta == 300.0  # 5 minutes in seconds

    def test_alert_event_resolution(self):
        """测试告警解决"""
        created = datetime.now(timezone.utc)
        resolved = created + timedelta(minutes=30)

        event = AlertEvent(alert_id="test-004", created_at=created, resolved_at=resolved)

        assert event.resolved_at == resolved
        # Calculate MTTR (Mean Time To Repair)
        mttr = (event.resolved_at - event.created_at).total_seconds()
        assert mttr == 1800.0  # 30 minutes in seconds


class TestBusinessMetrics:
    """业务指标测试"""

    def test_business_metrics_creation(self):
        """测试业务指标创建"""
        metrics = BusinessMetrics()
        assert metrics.alert_resolution_rate == 0.0
        assert metrics.mttr == 0.0
        assert metrics.mtta == 0.0
        assert metrics.auto_heal_success_rate == 0.0
        assert metrics.total_alerts == 0
        assert metrics.active_alerts == 0
        assert metrics.resolved_alerts == 0
        assert metrics.auto_healed_alerts == 0

    def test_business_metrics_with_values(self):
        """测试带值的业务指标"""
        metrics = BusinessMetrics(
            alert_resolution_rate=95.5,
            mttr=1800.0,
            mtta=300.0,
            auto_heal_success_rate=80.0,
            total_alerts=100,
            active_alerts=10,
            resolved_alerts=90,
            auto_healed_alerts=72,
        )

        assert metrics.alert_resolution_rate == 95.5
        assert metrics.mttr == 1800.0
        assert metrics.mtta == 300.0
        assert metrics.auto_heal_success_rate == 80.0
        assert metrics.total_alerts == 100
        assert metrics.active_alerts == 10
        assert metrics.resolved_alerts == 90
        assert metrics.auto_healed_alerts == 72

    def test_business_metrics_timestamp(self):
        """测试业务指标时间戳"""
        before = datetime.now(timezone.utc)
        metrics = BusinessMetrics()
        after = datetime.now(timezone.utc)

        assert before <= metrics.timestamp <= after


class TestBusinessMetricsCollector:
    """业务指标收集器测试"""

    def test_collector_initialization(self):
        """测试收集器初始化"""
        collector = BusinessMetricsCollector()
        assert collector.retention_days == 30
        assert len(collector._metrics_history) == 0

    def test_collector_custom_retention(self):
        """测试自定义保留期"""
        collector = BusinessMetricsCollector(retention_days=7)
        assert collector.retention_days == 7

    def test_record_alert(self):
        """测试记录告警"""
        collector = BusinessMetricsCollector()

        event = collector.record_alert("test-001", "critical")

        assert event.alert_id == "test-001"
        assert event.severity == "critical"
        assert "test-001" in collector._alert_events

    def test_acknowledge_alert(self):
        """测试确认告警"""
        collector = BusinessMetricsCollector()

        collector.record_alert("test-002", "medium")
        collector.acknowledge_alert("test-002", "admin")

        event = collector._alert_events["test-002"]
        assert event.acknowledged_at is not None
        assert event.assigned_to == "admin"

    def test_resolve_alert(self):
        """测试解决告警"""
        collector = BusinessMetricsCollector()

        collector.record_alert("test-003", "high")
        collector.resolve_alert("test-003", auto_healed=True)

        event = collector._alert_events["test-003"]
        assert event.resolved_at is not None
        assert event.auto_healed is True

    def test_calculate_metrics(self):
        """测试计算指标"""
        collector = BusinessMetricsCollector()

        # Record and resolve some alerts
        collector.record_alert("alert-1", "medium")
        collector.record_alert("alert-2", "high")
        collector.record_alert("alert-3", "critical")

        collector.acknowledge_alert("alert-1")
        collector.acknowledge_alert("alert-2")

        collector.resolve_alert("alert-1", auto_healed=True)
        collector.resolve_alert("alert-2", auto_healed=False)

        metrics = collector.calculate_metrics()

        assert metrics.total_alerts == 3
        assert metrics.resolved_alerts == 2
        assert metrics.auto_healed_alerts == 1
        assert metrics.active_alerts == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
