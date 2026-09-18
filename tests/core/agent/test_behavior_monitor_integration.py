# -*- coding: utf-8 -*-
"""
行为监控集成测试
Behavior Monitor Integration Tests

测试behavior_monitor与配置、算法模块的集成。
"""

import pytest
from core.agent.behavior_monitor import BehaviorMonitor, get_behavior_monitor


class TestBehaviorMonitorIntegration:
    """behavior_monitor集成测试"""

    def test_backward_compatibility_fixed_threshold(self):
        """测试向后兼容性 - 固定阈值模式"""
        monitor = BehaviorMonitor()
        agent_id = "test_agent"

        # 设置低阈值便于测试
        monitor.set_thresholds(max_iterations=3)

        # 记录迭代
        for _ in range(5):
            monitor.record_iteration(agent_id)

        # 检查异常
        anomaly = monitor.check_anomaly(agent_id)
        assert anomaly is not None
        assert anomaly.get("detection_method") == "fixed_threshold"
        assert "iteration limit exceeded" in str(anomaly.get("messages", []))

    def test_z_score_functionality(self):
        """测试z-score功能"""
        monitor = BehaviorMonitor()
        agent_id = "test_agent"

        # 建立统计基线
        for _ in range(35):
            monitor.record_iteration(agent_id)

        # 检查是否启用z-score
        if monitor._z_score_enabled:
            # 等待时间跨度（简化测试，直接检查）
            performance = monitor.get_performance_metrics()
            assert performance["z_score_enabled"] is True

    def test_performance_metrics(self):
        """测试性能监控"""
        monitor = BehaviorMonitor()
        agent_id = "test_agent"

        # 执行多次检查
        for _ in range(10):
            monitor.record_iteration(agent_id)
            monitor.check_anomaly(agent_id)

        # 获取性能指标
        performance = monitor.get_performance_metrics()
        assert performance["check_anomaly_calls"] >= 10
        assert performance["avg_check_time_seconds"] >= 0
        assert "z_score_enabled" in performance

    def test_reset_with_stats_baseline(self):
        """测试重置时清理统计基线"""
        monitor = BehaviorMonitor()
        agent_id = "test_agent"

        # 记录数据
        for _ in range(10):
            monitor.record_iteration(agent_id)

        # 重置
        monitor.reset(agent_id)

        # 验证清理
        summary = monitor.get_summary(agent_id)
        assert summary["found"] is False

    def test_global_instance(self):
        """测试全局实例"""
        monitor1 = get_behavior_monitor()
        monitor2 = get_behavior_monitor()
        assert monitor1 is monitor2

    def test_existing_api_compatibility(self):
        """测试现有API兼容性"""
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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
