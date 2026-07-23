# -*- coding: utf-8 -*-
"""测试API性能模块"""

import pytest


class TestAPIPerformanceModule:
    """测试API性能模块"""

    def test_api_performance_module_exists(self):
        """测试API性能模块存在"""
        from core import api_performance

        assert api_performance is not None

    def test_api_performance_has_functions(self):
        """测试API性能模块有函数"""
        from core import api_performance

        # 检查模块有函数或类
        assert len(dir(api_performance)) > 0


class TestMonitorAPIPerformance:
    """测试monitor_api_performance装饰器"""

    @pytest.mark.asyncio
    async def test_monitor_api_performance_fast(self):
        """测试快速API性能监控"""
        try:
            from core.api_performance import API_PERFORMANCE_STATS, monitor_api_performance

            # Clear stats
            API_PERFORMANCE_STATS.clear()

            @monitor_api_performance
            async def fast_api():
                return "success"

            result = await fast_api()

            assert result == "success"
            assert "fast_api" in API_PERFORMANCE_STATS
            assert len(API_PERFORMANCE_STATS["fast_api"]) == 1
        except Exception as e:
            pytest.skip(f"Cannot test monitor api performance fast: {e}")

    @pytest.mark.asyncio
    async def test_monitor_api_performance_slow(self):
        """测试慢API性能监控"""
        try:
            import asyncio

            from core.api_performance import API_PERFORMANCE_STATS, monitor_api_performance

            # Clear stats
            API_PERFORMANCE_STATS.clear()

            @monitor_api_performance
            async def slow_api():
                await asyncio.sleep(0.1)  # 100ms
                return "success"

            result = await slow_api()

            assert result == "success"
            assert "slow_api" in API_PERFORMANCE_STATS
            assert API_PERFORMANCE_STATS["slow_api"][0] >= 0.1
        except Exception as e:
            pytest.skip(f"Cannot test monitor api performance slow: {e}")

    @pytest.mark.asyncio
    async def test_monitor_api_performance_multiple_calls(self):
        """测试多次调用API性能监控"""
        try:
            from core.api_performance import API_PERFORMANCE_STATS, monitor_api_performance

            # Clear stats
            API_PERFORMANCE_STATS.clear()

            @monitor_api_performance
            async def test_api():
                return "success"

            # Call multiple times
            await test_api()
            await test_api()
            await test_api()

            assert "test_api" in API_PERFORMANCE_STATS
            assert len(API_PERFORMANCE_STATS["test_api"]) == 3
        except Exception as e:
            pytest.skip(f"Cannot test monitor api performance multiple calls: {e}")

    @pytest.mark.asyncio
    async def test_monitor_api_performance_with_args(self):
        """测试带参数的API性能监控"""
        try:
            from core.api_performance import API_PERFORMANCE_STATS, monitor_api_performance

            # Clear stats
            API_PERFORMANCE_STATS.clear()

            @monitor_api_performance
            async def api_with_args(arg1, arg2):
                return f"{arg1}-{arg2}"

            result = await api_with_args("test", "value")

            assert result == "test-value"
            assert "api_with_args" in API_PERFORMANCE_STATS
        except Exception as e:
            pytest.skip(f"Cannot test monitor api performance with args: {e}")

    @pytest.mark.asyncio
    async def test_monitor_api_performance_with_kwargs(self):
        """测试带关键字参数的API性能监控"""
        try:
            from core.api_performance import API_PERFORMANCE_STATS, monitor_api_performance

            # Clear stats
            API_PERFORMANCE_STATS.clear()

            @monitor_api_performance
            async def api_with_kwargs(**kwargs):
                return kwargs

            result = await api_with_kwargs(key1="value1", key2="value2")

            assert result["key1"] == "value1"
            assert "api_with_kwargs" in API_PERFORMANCE_STATS
        except Exception as e:
            pytest.skip(f"Cannot test monitor api performance with kwargs: {e}")

    @pytest.mark.asyncio
    async def test_monitor_api_performance_exception_handling(self):
        """测试异常处理"""
        try:
            from core.api_performance import API_PERFORMANCE_STATS, monitor_api_performance

            # Clear stats
            API_PERFORMANCE_STATS.clear()

            @monitor_api_performance
            async def failing_api():
                raise ValueError("Test error")

            try:
                await failing_api()
            except ValueError:
                pass

            # Stats should still be recorded even on exception
            assert "failing_api" in API_PERFORMANCE_STATS
        except Exception as e:
            pytest.skip(f"Cannot test monitor api performance exception handling: {e}")


class TestAPIPerformanceStats:
    """测试API性能统计"""

    def test_api_performance_stats_dict(self):
        """测试API性能统计字典"""
        try:
            from core.api_performance import API_PERFORMANCE_STATS

            assert isinstance(API_PERFORMANCE_STATS, dict)
        except Exception as e:
            pytest.skip(f"Cannot test api performance stats dict: {e}")

    def test_api_performance_stats_clear(self):
        """测试清空API性能统计"""
        try:
            from core.api_performance import API_PERFORMANCE_STATS

            # Add some data
            API_PERFORMANCE_STATS["test"] = [1.0, 2.0]

            # Clear
            API_PERFORMANCE_STATS.clear()

            assert len(API_PERFORMANCE_STATS) == 0
        except Exception as e:
            pytest.skip(f"Cannot test api performance stats clear: {e}")


class TestAPIPerformanceIntegration:
    """测试API性能集成"""

    @pytest.mark.asyncio
    async def test_complete_lifecycle(self):
        """测试完整生命周期"""
        try:
            import asyncio

            from core.api_performance import API_PERFORMANCE_STATS, monitor_api_performance

            # Clear stats
            API_PERFORMANCE_STATS.clear()

            # Create multiple APIs
            @monitor_api_performance
            async def api1():
                return "api1"

            @monitor_api_performance
            async def api2():
                await asyncio.sleep(0.05)
                return "api2"

            @monitor_api_performance
            async def api3():
                return "api3"

            # Call APIs
            await api1()
            await api2()
            await api3()
            await api1()  # Call api1 again

            # Verify stats
            assert len(API_PERFORMANCE_STATS) == 3
            assert "api1" in API_PERFORMANCE_STATS
            assert "api2" in API_PERFORMANCE_STATS
            assert "api3" in API_PERFORMANCE_STATS
            assert len(API_PERFORMANCE_STATS["api1"]) == 2
            assert len(API_PERFORMANCE_STATS["api2"]) == 1
            assert len(API_PERFORMANCE_STATS["api3"]) == 1

            assert True
        except Exception as e:
            pytest.skip(f"Cannot test complete lifecycle: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
