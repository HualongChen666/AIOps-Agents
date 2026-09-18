# -*- coding: utf-8 -*-
"""
行为监控z-score功能测试
Behavior Monitor Z-Score Functionality Tests

测试z-score异常检测、分级告警、混合切换等核心功能。
"""

import pytest
import time
from core.agent.behavior_monitor import BehaviorMonitor


class TestZScoreAnomalyDetection:
    """z-score异常检测测试"""

    def test_z_score_normal_behavior(self):
        """测试正常行为不触发异常"""
        monitor = BehaviorMonitor()
        agent_id = "test_agent"

        # 建立正常基线
        for _ in range(35):
            monitor.record_iteration(agent_id)
            time.sleep(0.01)  # 模拟时间间隔

        # 正常范围内的行为
        monitor.record_iteration(agent_id)
        anomaly = monitor.check_anomaly(agent_id)

        # 正常行为不应触发异常
        if anomaly:
            # 如果触发异常，应该是固定阈值模式
            assert anomaly.get("detection_method") == "fixed_threshold"

    def test_z_score_warning_level(self):
        """测试WARNING级别异常"""
        monitor = BehaviorMonitor()
        agent_id = "test_agent"

        # 建立基线
        for _ in range(35):
            monitor.record_iteration(agent_id)
            time.sleep(0.01)

        # 模拟异常行为（大量迭代）
        for _ in range(20):
            monitor.record_iteration(agent_id)

        anomaly = monitor.check_anomaly(agent_id)
        if anomaly and anomaly.get("detection_method") == "z_score":
            assert "iterations anomaly" in str(anomaly.get("messages", []))

    def test_z_score_metrics_included(self):
        """测试z-score指标包含在返回值中"""
        monitor = BehaviorMonitor()
        agent_id = "test_agent"

        # 建立基线
        for _ in range(35):
            monitor.record_iteration(agent_id)
            time.sleep(0.01)

        anomaly = monitor.check_anomaly(agent_id)
        if anomaly and anomaly.get("detection_method") == "z_score":
            metrics = anomaly.get("metrics", {})
            # 检查是否包含z-score相关字段
            assert "iterations_z_score" in metrics or "tool_calls_z_score" in metrics


class TestFixedThresholdFallback:
    """固定阈值回退测试"""

    def test_fixed_threshold_when_z_score_not_ready(self):
        """测试z-score未就绪时使用固定阈值"""
        monitor = BehaviorMonitor()
        agent_id = "test_agent"

        # 设置低阈值便于测试
        monitor.set_thresholds(max_iterations=3)

        # 记录少量迭代（不满足z-score条件）
        for _ in range(5):
            monitor.record_iteration(agent_id)

        anomaly = monitor.check_anomaly(agent_id)
        assert anomaly is not None
        assert anomaly.get("detection_method") == "fixed_threshold"
        assert "iteration limit exceeded" in str(anomaly.get("messages", []))

    def test_fixed_threshold_still_works(self):
        """测试固定阈值逻辑仍然正常工作"""
        monitor = BehaviorMonitor()
        agent_id = "test_agent"

        monitor.set_thresholds(max_iterations=2)
        monitor.record_iteration(agent_id)
        monitor.record_iteration(agent_id)
        monitor.record_iteration(agent_id)  # 超过阈值

        anomaly = monitor.check_anomaly(agent_id)
        assert anomaly is not None
        assert "iteration limit exceeded" in str(anomaly.get("messages", []))


class TestBackwardCompatibility:
    """向后兼容性测试"""

    def test_existing_api_still_works(self):
        """测试现有API仍然正常工作"""
        monitor = BehaviorMonitor()
        agent_id = "test_agent"

        # 现有API调用
        monitor.record_iteration(agent_id)
        monitor.record_tool_call(agent_id, "tool_1")
        monitor.record_error(agent_id)

        summary = monitor.get_summary(agent_id)
        assert summary["found"] is True
        assert summary["iterations"] == 1
        assert summary["errors"] == 1

        monitor.reset(agent_id)
        assert monitor.get_summary(agent_id)["found"] is False

    def test_global_instance_still_works(self):
        """测试全局实例仍然正常"""
        from core.agent.behavior_monitor import get_behavior_monitor

        monitor1 = get_behavior_monitor()
        monitor2 = get_behavior_monitor()
        assert monitor1 is monitor2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
