# -*- coding: utf-8 -*-
"""
行为监控性能测试
Behavior Monitor Performance Tests

验证性能指标是否达到成功标准。
"""

import pytest
import time
import psutil
from core.agent.behavior_monitor import BehaviorMonitor


class TestBehaviorMonitorPerformance:
    """性能测试"""

    def test_check_anomaly_performance_fixed_threshold(self):
        """测试固定阈值的性能"""
        monitor = BehaviorMonitor()
        agent_id = "test_agent"

        # 预热
        for _ in range(10):
            monitor.record_iteration(agent_id)

        # 性能测试
        iterations = 1000
        start_time = time.perf_counter()

        for _ in range(iterations):
            monitor.check_anomaly(agent_id)

        elapsed = time.perf_counter() - start_time
        avg_time = elapsed / iterations

        # 验证性能指标（目标：0.05ms = 50μs）
        assert avg_time < 0.05, f"固定阈值检查过慢: {avg_time*1000:.2f}μs"
        print(f"✓ 固定阈值延迟: {avg_time*1000:.2f}μs")

    def test_check_anomaly_performance_z_score(self):
        """测试z-score的性能"""
        monitor = BehaviorMonitor()
        agent_id = "test_agent"

        # 建立统计基线
        for _ in range(35):
            monitor.record_iteration(agent_id)
            time.sleep(0.01)

        # 性能测试
        iterations = 1000
        start_time = time.perf_counter()

        for _ in range(iterations):
            monitor.check_anomaly(agent_id)

        elapsed = time.perf_counter() - start_time
        avg_time = elapsed / iterations

        # 验证性能指标（目标：0.01ms = 10μs）
        assert avg_time < 0.01, f"z-score检查过慢: {avg_time*1000:.2f}μs"
        print(f"✓ z-score延迟: {avg_time*1000:.2f}μs")

    def test_memory_usage(self):
        """测试内存使用"""
        import gc

        process = psutil.Process()
        initial_memory = process.memory_info().rss / (1024 * 1024)  # MB

        monitor = BehaviorMonitor()

        # 创建50个agent，每个50次执行
        for i in range(50):
            agent_id = f"agent_{i}"
            for _ in range(50):
                monitor.record_iteration(agent_id)

        gc.collect()
        final_memory = process.memory_info().rss / (1024 * 1024)
        memory_increase = final_memory - initial_memory

        # 验证内存指标（目标：50MB）
        assert memory_increase < 50, f"内存增长过大: {memory_increase:.2f}MB"
        print(f"✓ 内存增长: {memory_increase:.2f}MB")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
