# -*- coding: utf-8 -*-
"""
内存泄漏检测测试
Memory Leak Detection Tests

验证长时间运行时的内存使用情况，确保无内存泄漏。
"""

import pytest
import time
import gc
import psutil
from core.agent.behavior_monitor import BehaviorMonitor


class TestMemoryLeakDetection:
    """内存泄漏检测"""

    def test_long_running_memory_stability(self):
        """长时间运行的内存稳定性"""
        process = psutil.Process()
        initial_memory = process.memory_info().rss / (1024 * 1024)  # MB

        monitor = BehaviorMonitor()

        # 模拟长时间运行：创建和销毁大量agent
        for cycle in range(10):
            # 创建100个agent
            for i in range(100):
                agent_id = f"agent_cycle{cycle}_id{i}"
                for _ in range(50):
                    monitor.record_iteration(agent_id)

            # 清理一半
            for i in range(50):
                agent_id = f"agent_cycle{cycle}_id{i}"
                monitor.reset(agent_id)

            # 强制垃圾回收
            gc.collect()

        final_memory = process.memory_info().rss / (1024 * 1024)
        memory_increase = final_memory - initial_memory

        # 内存增长应该合理（< 100MB）
        assert memory_increase < 100, f"内存增长过大，可能存在泄漏: {memory_increase:.2f}MB"
        print(f"✓ 长时间运行内存增长: {memory_increase:.2f}MB")

    def test_stats_baseline_cleanup(self):
        """统计基线清理机制"""
        monitor = BehaviorMonitor()
        agent_id = "test_agent"

        # 建立统计基线
        for _ in range(50):
            monitor.record_iteration(agent_id)

        # 重置agent
        monitor.reset(agent_id)

        # 验证统计基线被清理
        if monitor._z_score_enabled:
            assert agent_id not in monitor._stats_baselines or len(monitor._stats_baselines[agent_id]) == 0

    def test_performance_metrics_no_growth(self):
        """性能监控指标无异常增长"""
        monitor = BehaviorMonitor()

        # 执行大量操作
        for i in range(1000):
            agent_id = f"agent_{i % 10}"  # 复用10个agent
            monitor.record_iteration(agent_id)
            monitor.check_anomaly(agent_id)

        # 性能指标应该保持合理
        performance = monitor.get_performance_metrics()
        assert performance["check_anomaly_calls"] == 1000
        assert performance["avg_check_time_seconds"] < 0.1  # 平均延迟应<100ms


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
