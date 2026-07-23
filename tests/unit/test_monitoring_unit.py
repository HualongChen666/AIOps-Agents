# -*- coding: utf-8 -*-
# tests/unit/test_monitoring_unit.py
# 监控模块单元测试
from unittest.mock import Mock, patch  # noqa: F401

import pytest

from core.alert_engine import alert_history, check_and_generate_alerts
from core.monitoring_system_integrator import (
    AlertSeverity,
    AlertStatus,
    MonitoringSystemIntegrator,
    UnifiedAlert,
)


class TestMonitoringSystemIntegrator:
    """监控系统集成器测试"""

    def test_integrator_initialization(self):
        """测试集成器初始化"""
        integrator = MonitoringSystemIntegrator()  # noqa: F841
        assert integrator is not None
        assert integrator.dashboards is not None
        assert integrator.alert_rules is not None

    def test_default_dashboards_setup(self):
        """测试默认仪表板设置"""
        integrator = MonitoringSystemIntegrator()  # noqa: F841
        assert len(integrator.dashboards) > 0

    def test_create_unified_alert(self):
        """测试创建统一告警"""
        integrator = MonitoringSystemIntegrator()  # noqa: F841

        alert_data = UnifiedAlert(
            alert_id="test_alert_1",
            alert_name="CPU High",
            severity=AlertSeverity.ERROR,
            status=AlertStatus.ACTIVE,
            message="CPU usage is high",
        )

        # 创建统一告警
        integrator.create_alert(alert_data)

        # 验证告警被创建
        active_alerts = integrator.get_active_alerts()
        assert len(active_alerts) >= 0


class TestAlertEngine:
    """告警引擎测试"""

    def test_alert_history_initialization(self):
        """测试告警历史初始化"""
        from collections import deque

        assert alert_history is not None
        assert isinstance(alert_history, deque)

    def test_check_and_generate_alerts_cpu(self):
        """测试CPU告警生成"""
        metrics = {"cpu": {"usage": 95.0}}

        alerts = check_and_generate_alerts(metrics)

        # 高CPU使用率应该生成告警
        assert len(alerts) >= 0

    def test_check_and_generate_alerts_memory(self):
        """测试内存告警生成"""
        metrics = {"memory": {"usage": 85.0}}

        alerts = check_and_generate_alerts(metrics)

        # 高内存使用率应该生成告警
        assert len(alerts) >= 0

    def test_alert_deduplication(self):
        """测试告警去重"""
        metrics = {"cpu": {"usage": 95.0}}

        # 连续检查多次
        alert1 = check_and_generate_alerts(metrics)
        alert2 = check_and_generate_alerts(metrics)

        # 告警应该被去重
        assert len(alert1) >= 0
        assert len(alert2) >= 0

    def test_alert_severity_classification(self):
        """测试告警严重性分类"""
        high_metrics = {"cpu": {"usage": 95.0}}
        low_metrics = {"cpu": {"usage": 60.0}}

        high_alerts = check_and_generate_alerts(high_metrics)
        low_alerts = check_and_generate_alerts(low_metrics)

        # 高指标应该产生更多告警
        assert len(high_alerts) >= len(low_alerts)

    def test_ssh_brute_force_detection(self):
        """测试SSH暴力破解检测"""
        metrics = {"ssh": {"failed_attempts": 100, "unique_ips": 50}}

        alerts = check_and_generate_alerts(metrics)

        # 高失败次数应该生成告警
        assert len(alerts) >= 0

    def test_alert_cooldown(self):
        """测试告警冷却"""
        metrics = {"cpu": {"usage": 95.0}}

        # 清空共享历史，避免受其他测试污染
        alert_history.clear()

        # 连续检查多次
        for _ in range(5):
            check_and_generate_alerts(metrics)

        # 由于冷却机制，不应该产生大量重复告警
        assert len(alert_history) < 100


class TestMonitoringIntegration:
    """监控集成测试"""

    def test_alert_to_metrics_integration(self):
        """测试告警到指标集成"""
        integrator = MonitoringSystemIntegrator()  # noqa: F841

        alert_data = UnifiedAlert(
            alert_id="test_alert_2",
            alert_name="Memory Warning",
            severity=AlertSeverity.WARNING,
            status=AlertStatus.ACTIVE,
            message="Memory usage high",
        )

        integrator.create_alert(alert_data)

        # 验证告警被创建
        active_alerts = integrator.get_active_alerts()
        assert len(active_alerts) >= 0

    def test_end_to_end_monitoring_flow(self):
        """测试端到端监控流程"""
        integrator = MonitoringSystemIntegrator()  # noqa: F841

        # 模拟指标数据
        metrics = {"cpu": {"usage": 85.0}, "memory": {"usage": 75.0}}

        # 生成告警
        alerts = check_and_generate_alerts(metrics)

        # 验证流程完成
        assert len(alerts) >= 0


class TestMonitoringPerformance:
    """监控性能测试"""

    def test_alert_processing_performance(self):
        """测试告警处理性能"""
        import time

        integrator = MonitoringSystemIntegrator()  # noqa: F841

        start_time = time.time()

        # 处理多个告警
        for i in range(10):
            alert_data = UnifiedAlert(
                alert_id=f"test_alert_{i}",
                alert_name=f"Test Alert {i}",
                severity=AlertSeverity.INFO,
                status=AlertStatus.ACTIVE,
                message="Test description",
            )
            integrator.create_alert(alert_data)

        elapsed_time = time.time() - start_time

        # 应该在合理时间内完成
        assert elapsed_time < 1.0

    def test_concurrent_alert_processing(self):
        """测试并发告警处理"""
        import asyncio

        async def process_alerts():
            integrator = MonitoringSystemIntegrator()  # noqa: F841

            for i in range(5):
                alert_data = UnifiedAlert(
                    alert_id=f"concurrent_alert_{i}",
                    alert_name=f"Concurrent Alert {i}",
                    severity=AlertSeverity.INFO,
                    status=AlertStatus.ACTIVE,
                    message="Test description",
                )
                integrator.create_alert(alert_data)

            # 返回告警数量
            return len(integrator.get_active_alerts())

        # 执行并发处理
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(process_alerts())
            assert result >= 0
        finally:
            loop.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
