# -*- coding: utf-8 -*-
# tests/unit/test_api_performance_unit.py
# API性能监控模块单元测试
import asyncio

import pytest


class TestAPIPerformance:
    """API性能监控测试"""

    def test_api_performance_import(self):
        """测试API性能监控导入"""
        from core.api_performance import API_PERFORMANCE_STATS, monitor_api_performance

        assert API_PERFORMANCE_STATS is not None
        assert monitor_api_performance is not None

    def test_api_performance_stats_initial(self):
        """测试性能统计初始状态"""
        from core.api_performance import API_PERFORMANCE_STATS

        assert isinstance(API_PERFORMANCE_STATS, dict)
        assert len(API_PERFORMANCE_STATS) == 0

    @pytest.mark.asyncio
    async def test_monitor_api_performance_fast(self):
        """测试快速API监控"""
        from core.api_performance import API_PERFORMANCE_STATS, monitor_api_performance

        API_PERFORMANCE_STATS.clear()

        @monitor_api_performance
        async def fast_function():
            await asyncio.sleep(0.01)
            return "result"

        result = await fast_function()
        assert result == "result"
        assert "fast_function" in API_PERFORMANCE_STATS
        assert len(API_PERFORMANCE_STATS["fast_function"]) == 1

    @pytest.mark.asyncio
    async def test_monitor_api_performance_slow(self):
        """测试慢API监控"""
        from core.api_performance import API_PERFORMANCE_STATS, monitor_api_performance

        API_PERFORMANCE_STATS.clear()

        @monitor_api_performance
        async def slow_function():
            await asyncio.sleep(1.1)  # 超过1秒阈值，触发慢API告警
            return "result"

        result = await slow_function()
        assert result == "result"
        assert "slow_function" in API_PERFORMANCE_STATS
        assert len(API_PERFORMANCE_STATS["slow_function"]) == 1

    @pytest.mark.asyncio
    async def test_monitor_api_performance_multiple_calls(self):
        """测试多次调用监控"""
        from core.api_performance import API_PERFORMANCE_STATS, monitor_api_performance

        API_PERFORMANCE_STATS.clear()

        @monitor_api_performance
        async def test_function():
            await asyncio.sleep(0.01)
            return "result"

        await test_function()
        await test_function()
        await test_function()

        assert "test_function" in API_PERFORMANCE_STATS
        assert len(API_PERFORMANCE_STATS["test_function"]) == 3

    @pytest.mark.asyncio
    async def test_monitor_api_performance_exception(self):
        """测试异常情况监控"""
        from core.api_performance import API_PERFORMANCE_STATS, monitor_api_performance

        API_PERFORMANCE_STATS.clear()

        @monitor_api_performance
        async def error_function():
            await asyncio.sleep(0.01)
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            await error_function()

        # 即使抛出异常，也应该记录性能
        assert "error_function" in API_PERFORMANCE_STATS
        assert len(API_PERFORMANCE_STATS["error_function"]) == 1

    @pytest.mark.asyncio
    async def test_monitor_api_performance_decorator_preserves_name(self):
        """测试装饰器保留函数名"""
        from core.api_performance import monitor_api_performance

        @monitor_api_performance
        async def my_function():
            return "result"

        assert my_function.__name__ == "my_function"
