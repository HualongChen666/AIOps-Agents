# -*- coding: utf-8 -*-
# tests/unit/test_business_metrics_unit.py
# Business Metrics模块单元测试
from datetime import datetime, timedelta, timezone

import pytest  # noqa: F401


class TestAlertEvent:
    """测试告警事件"""

    def test_alert_event_creation(self):
        """测试告警事件创建"""
        from core.business_metrics import AlertEvent

        event = AlertEvent(
            alert_id="test_alert_1", created_at=datetime.now(timezone.utc), severity="high"
        )

        assert event.alert_id == "test_alert_1"
        assert event.severity == "high"
        assert event.acknowledged_at is None
        assert event.resolved_at is None
        assert event.auto_healed is False

    def test_alert_event_with_optional_fields(self):
        """测试告警事件带可选字段"""
        from core.business_metrics import AlertEvent

        now = datetime.now(timezone.utc)
        event = AlertEvent(
            alert_id="test_alert_2",
            created_at=now,
            acknowledged_at=now + timedelta(minutes=5),
            resolved_at=now + timedelta(hours=1),
            severity="critical",
            auto_healed=True,
            assigned_to="admin",
        )

        assert event.alert_id == "test_alert_2"
        assert event.acknowledged_at is not None
        assert event.resolved_at is not None
        assert event.auto_healed is True
        assert event.assigned_to == "admin"


class TestBusinessMetrics:
    """测试业务指标"""

    def test_business_metrics_creation(self):
        """测试业务指标创建"""
        from core.business_metrics import BusinessMetrics

        metrics = BusinessMetrics()

        assert metrics.alert_resolution_rate == 0.0
        assert metrics.mttr == 0.0
        assert metrics.mtta == 0.0
        assert metrics.auto_heal_success_rate == 0.0
        assert metrics.total_alerts == 0
        assert metrics.active_alerts == 0
        assert metrics.resolved_alerts == 0
        assert metrics.auto_healed_alerts == 0
        assert metrics.timestamp is not None

    def test_business_metrics_with_values(self):
        """测试业务指标带值"""
        from core.business_metrics import BusinessMetrics

        metrics = BusinessMetrics(
            alert_resolution_rate=0.95,
            mttr=300.0,
            mtta=60.0,
            auto_heal_success_rate=0.85,
            total_alerts=100,
            active_alerts=10,
            resolved_alerts=90,
            auto_healed_alerts=50,
        )

        assert metrics.alert_resolution_rate == 0.95
        assert metrics.mttr == 300.0
        assert metrics.mtta == 60.0
        assert metrics.auto_heal_success_rate == 0.85
        assert metrics.total_alerts == 100
        assert metrics.active_alerts == 10
        assert metrics.resolved_alerts == 90
        assert metrics.auto_healed_alerts == 50


class TestBusinessMetricsCollector:
    """测试业务指标收集器"""

    def test_collector_initialization(self):
        """测试收集器初始化"""
        from core.business_metrics import BusinessMetricsCollector

        collector = BusinessMetricsCollector()

        assert collector.retention_days == 30

    def test_collector_custom_retention(self):
        """测试收集器自定义保留天数"""
        from core.business_metrics import BusinessMetricsCollector

        collector = BusinessMetricsCollector(retention_days=60)

        assert collector.retention_days == 60
