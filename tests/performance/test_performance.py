# -*- coding: utf-8 -*-
# tests/performance/test_performance.py
# 性能测试示例
import pytest


class TestPerformanceBasics:
    """基础性能测试"""

    def test_simple_performance(self):
        """简单性能测试示例"""
        import time

        start_time = time.time()

        # 模拟一些计算
        result = sum(range(1000))

        end_time = time.time()
        duration = end_time - start_time

        # 断言执行时间在合理范围内
        assert duration < 1.0, f"Performance test took too long: {duration}s"
        assert result == 499500


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
