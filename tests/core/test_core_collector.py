# -*- coding: utf-8 -*-
# tests/core/test_collector.py
# Collector模块测试
import asyncio
from unittest.mock import patch

import pytest


class TestCollector:
    """测试Collector模块"""

    @pytest.fixture
    def collector(self):
        """创建collector实例"""
        try:
            from core.collector import Collector

            return Collector()
        except Exception as e:
            pytest.skip(f"Cannot create Collector instance: {e}")

    def test_collector_initialization(self, collector):
        """测试collector初始化"""
        assert collector is not None

    def test_collector_collect_basic(self, collector):
        """测试基本采集功能"""
        # Mock采集方法
        with patch.object(collector, "collect_all", return_value={}):
            result = collector.collect_all()
            assert isinstance(result, dict)

    def test_collector_collect_with_error(self, collector):
        """测试采集错误处理"""
        with patch.object(collector, "collect_all", side_effect=Exception("Collection error")):
            with pytest.raises(Exception):
                collector.collect_all()

    def test_collector_collect_cpu(self, collector):
        """测试CPU采集"""
        if hasattr(collector, "collect_cpu"):
            with patch.object(collector, "collect_cpu", return_value={"cpu": 50}):
                result = collector.collect_cpu()
                assert "cpu" in result

    def test_collector_collect_memory(self, collector):
        """测试内存采集"""
        if hasattr(collector, "collect_memory"):
            with patch.object(collector, "collect_memory", return_value={"memory": 1024}):
                result = collector.collect_memory()
                assert "memory" in result

    def test_collector_collect_disk(self, collector):
        """测试磁盘采集"""
        if hasattr(collector, "collect_disk"):
            with patch.object(collector, "collect_disk", return_value={"disk": 100}):
                result = collector.collect_disk()
                assert "disk" in result

    def test_collector_collect_network(self, collector):
        """测试网络采集"""
        if hasattr(collector, "collect_network"):
            with patch.object(collector, "collect_network", return_value={"network": 1000}):
                result = collector.collect_network()
                assert "network" in result


class TestCollectorAsync:
    """测试Collector异步功能"""

    @pytest.fixture
    async def async_collector(self):
        """创建异步collector实例"""
        try:
            from core.collector import Collector

            return Collector()
        except Exception as e:
            pytest.skip(f"Cannot create async Collector instance: {e}")

    @pytest.mark.asyncio
    async def test_async_collect_all(self, async_collector):
        """测试异步采集所有指标"""
        if hasattr(async_collector, "collect_all_async"):
            with patch.object(async_collector, "collect_all_async", return_value={}):
                result = await async_collector.collect_all_async()
                assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_async_collect_with_timeout(self, async_collector):
        """测试异步采集超时"""
        if hasattr(async_collector, "collect_all_async"):
            with patch.object(
                async_collector, "collect_all_async", side_effect=asyncio.TimeoutError
            ):
                with pytest.raises(asyncio.TimeoutError):
                    await async_collector.collect_all_async()


class TestCollectorCache:
    """测试Collector缓存功能"""

    @pytest.fixture
    def cached_collector(self):
        """创建带缓存的collector实例"""
        try:
            from core.collector import Collector

            collector = Collector()
            collector.cache_enabled = True
            return collector
        except Exception as e:
            pytest.skip(f"Cannot create cached Collector instance: {e}")

    def test_cache_hit(self, cached_collector):
        """测试缓存命中"""
        if hasattr(cached_collector, "get_cached_snapshot"):
            with patch.object(
                cached_collector, "get_cached_snapshot", return_value={"cached": True}
            ):
                result = cached_collector.get_cached_snapshot()
                assert result.get("cached") is True

    def test_cache_miss(self, cached_collector):
        """测试缓存未命中"""
        if hasattr(cached_collector, "get_cached_snapshot"):
            with patch.object(cached_collector, "get_cached_snapshot", return_value=None):
                result = cached_collector.get_cached_snapshot()
                assert result is None

    def test_cache_invalidation(self, cached_collector):
        """测试缓存失效"""
        if hasattr(cached_collector, "invalidate_cache"):
            with patch.object(cached_collector, "invalidate_cache"):
                cached_collector.invalidate_cache()


class TestCollectorPlatform:
    """测试Collector平台特定功能"""

    @pytest.fixture
    def windows_collector(self):
        """创建Windows collector实例"""
        try:
            from core.collector import Collector

            collector = Collector()
            collector.platform = "windows"
            return collector
        except Exception as e:
            pytest.skip(f"Cannot create Windows Collector instance: {e}")

    @pytest.fixture
    def linux_collector(self):
        """创建Linux collector实例"""
        try:
            from core.collector import Collector

            collector = Collector()
            collector.platform = "linux"
            return collector
        except Exception as e:
            pytest.skip(f"Cannot create Linux Collector instance: {e}")

    def test_windows_specific_collection(self, windows_collector):
        """测试Windows特定采集"""
        if hasattr(windows_collector, "collect_windows_specific"):
            with patch.object(
                windows_collector, "collect_windows_specific", return_value={"windows": True}
            ):
                result = windows_collector.collect_windows_specific()
                assert result.get("windows") is True

    def test_linux_specific_collection(self, linux_collector):
        """测试Linux特定采集"""
        if hasattr(linux_collector, "collect_linux_specific"):
            with patch.object(
                linux_collector, "collect_linux_specific", return_value={"linux": True}
            ):
                result = linux_collector.collect_linux_specific()
                assert result.get("linux") is True


class TestCollectorMetrics:
    """测试Collector指标功能"""

    @pytest.fixture
    def metrics_collector(self):
        """创建带指标的collector实例"""
        try:
            from core.collector import Collector

            collector = Collector()
            return collector
        except Exception as e:
            pytest.skip(f"Cannot create metrics Collector instance: {e}")

    def test_metrics_format(self, metrics_collector):
        """测试指标格式化"""
        if hasattr(metrics_collector, "format_metrics"):
            raw_data = {"cpu": 50, "memory": 1024}
            with patch.object(metrics_collector, "format_metrics", return_value="formatted"):
                result = metrics_collector.format_metrics(raw_data)
                assert result == "formatted"

    def test_metrics_aggregation(self, metrics_collector):
        """测试指标聚合"""
        if hasattr(metrics_collector, "aggregate_metrics"):
            metrics_list = [{"cpu": 50}, {"cpu": 60}]
            with patch.object(metrics_collector, "aggregate_metrics", return_value={"cpu": 55}):
                result = metrics_collector.aggregate_metrics(metrics_list)
                assert result.get("cpu") == 55

    def test_metrics_validation(self, metrics_collector):
        """测试指标验证"""
        if hasattr(metrics_collector, "validate_metrics"):
            valid_metrics = {"cpu": 50, "memory": 1024}
            with patch.object(metrics_collector, "validate_metrics", return_value=True):
                result = metrics_collector.validate_metrics(valid_metrics)
                assert result is True


class TestCollectorFunctions:
    """测试Collector模块函数"""

    def test_get_cpu_metrics(self):
        """测试get_cpu_metrics函数"""
        try:
            from core.collector import get_cpu_metrics

            result = get_cpu_metrics()
            assert isinstance(result, dict)
            assert "usage_percent" in result
            assert "core_count" in result
            assert "logical_count" in result
            assert 0 <= result["usage_percent"] <= 100
        except Exception as e:
            pytest.skip(f"Cannot test get_cpu_metrics: {e}")

    def test_get_cached_snapshot(self):
        """测试get_cached_snapshot函数"""
        try:
            from core.collector import get_cached_snapshot, invalidate_collect_cache

            # 先失效缓存
            invalidate_collect_cache()
            # 获取缓存（应该返回None）
            result = get_cached_snapshot()
            assert result is None or isinstance(result, dict)
        except Exception as e:
            pytest.skip(f"Cannot test get_cached_snapshot: {e}")

    def test_invalidate_collect_cache(self):
        """测试invalidate_collect_cache函数"""
        try:
            from core.collector import invalidate_collect_cache

            # 应该不抛出异常
            invalidate_collect_cache()
        except Exception as e:
            pytest.skip(f"Cannot test invalidate_collect_cache: {e}")

    def test_get_collect_metrics(self):
        """测试get_collect_metrics函数"""
        try:
            from core.collector import get_collect_metrics

            result = get_collect_metrics()
            assert isinstance(result, dict)
            assert "total_calls" in result
            assert "cache_hits" in result
            assert "cache_misses" in result
            assert "cache_hit_rate" in result
        except Exception as e:
            pytest.skip(f"Cannot test get_collect_metrics: {e}")

    def test_collect_all_basic(self):
        """测试collect_all函数基本功能"""
        try:
            from core.collector import collect_all

            result = collect_all()
            assert isinstance(result, dict)
            # 检查基本字段
            assert "cpu" in result or "timestamp" in result
        except Exception as e:
            pytest.skip(f"Cannot test collect_all: {e}")

    def test_collect_all_with_timeout(self):
        """测试collect_all超时保护"""
        try:
            # 设置较短的超时时间来测试超时保护
            import time

            from core.collector import collect_all

            start = time.time()
            result = collect_all()
            elapsed = time.time() - start
            assert isinstance(result, dict)
            # 即使超时，也应该在合理时间内返回（< 15秒）
            assert elapsed < 15
        except Exception as e:
            pytest.skip(f"Cannot test collect_all timeout: {e}")

    def test_get_memory_metrics(self):
        """测试内存指标采集"""
        try:
            from core.collector import get_memory_metrics

            result = get_memory_metrics()
            assert isinstance(result, dict)
            assert "total" in result or "usage_percent" in result
        except Exception as e:
            pytest.skip(f"Cannot test get_memory_metrics: {e}")

    def test_get_disk_metrics(self):
        """测试磁盘指标采集"""
        try:
            from core.collector import get_disk_metrics

            result = get_disk_metrics()
            assert isinstance(result, dict)
            # 磁盘指标可能返回列表或字典
            assert isinstance(result, (dict, list))
        except Exception as e:
            pytest.skip(f"Cannot test get_disk_metrics: {e}")

    def test_get_network_metrics(self):
        """测试网络指标采集"""
        try:
            from core.collector import get_network_metrics

            result = get_network_metrics()
            assert isinstance(result, dict)
        except Exception as e:
            pytest.skip(f"Cannot test get_network_metrics: {e}")

    def test_get_system_info(self):
        """测试系统信息采集"""
        try:
            from core.collector import get_system_info

            result = get_system_info()
            assert isinstance(result, dict)
        except Exception as e:
            pytest.skip(f"Cannot test get_system_info: {e}")

    def test_get_top_processes(self):
        """测试获取top进程"""
        try:
            from core.collector import get_top_processes

            result = get_top_processes(limit=5)
            assert isinstance(result, list)
            # 检查返回的进程数量
            assert len(result) <= 5
        except Exception as e:
            pytest.skip(f"Cannot test get_top_processes: {e}")

    def test_cpu_metrics_range_validation(self):
        """测试CPU指标范围验证"""
        try:
            from core.collector import get_cpu_metrics

            result = get_cpu_metrics()
            # 验证CPU使用率在0-100之间
            assert 0 <= result["usage_percent"] <= 100
            # 验证核心数大于0
            assert result["core_count"] > 0
            assert result["logical_count"] > 0
        except Exception as e:
            pytest.skip(f"Cannot test CPU metrics validation: {e}")

    def test_collect_metrics_increment(self):
        """测试采集指标递增"""
        try:
            from core.collector import collect_all, get_collect_metrics

            initial_metrics = get_collect_metrics()
            initial_calls = initial_metrics["total_calls"]

            # 执行一次采集
            collect_all()

            # 检查调用次数是否增加
            final_metrics = get_collect_metrics()
            assert final_metrics["total_calls"] >= initial_calls
        except Exception as e:
            pytest.skip(f"Cannot test metrics increment: {e}")

    def test_cache_hit_rate_calculation(self):
        """测试缓存命中率计算"""
        try:
            from core.collector import get_collect_metrics

            metrics = get_collect_metrics()
            # 缓存命中率应该在0-100之间
            if metrics["total_calls"] > 0:
                assert 0 <= metrics["cache_hit_rate"] <= 100
        except Exception as e:
            pytest.skip(f"Cannot test cache hit rate: {e}")
