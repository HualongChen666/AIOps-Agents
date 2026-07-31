# -*- coding: utf-8 -*-
# tests/test_collector.py
# 指标采集器单元测试
import time  # noqa: F401
from unittest.mock import MagicMock, patch  # noqa: F401

import pytest

pytestmark = pytest.mark.integration

from core.collector import (
    collect_all,
    get_cached_snapshot,
    get_collect_metrics,
    get_cpu_metrics,
    get_disk_metrics,
    get_memory_metrics,
    get_network_metrics,
    get_system_info,
    get_top_processes,
    invalidate_collect_cache,
)


class TestCPUMetrics:
    """CPU 指标采集测试"""

    def test_get_cpu_metrics_success(self):
        """测试 CPU 指标采集成功"""
        result = get_cpu_metrics()

        # 验证采集成功
        assert "usage_percent" in result
        assert "core_count" in result
        assert "logical_count" in result
        assert "frequency_mhz" in result
        assert "per_core" in result
        assert 0 <= result["usage_percent"] <= 100
        assert result["core_count"] >= 1
        assert result["logical_count"] >= 1


class TestMemoryMetrics:
    """内存指标采集测试"""

    def test_get_memory_metrics_success(self):
        """测试内存指标采集成功"""
        result = get_memory_metrics()

        # 验证采集成功
        assert "total_gb" in result
        assert "used_gb" in result
        assert "available_gb" in result
        assert "usage_percent" in result
        assert "swap_total_gb" in result
        assert "swap_used_gb" in result
        assert "swap_percent" in result
        assert result["total_gb"] > 0
        assert 0 <= result["usage_percent"] <= 100


class TestDiskMetrics:
    """磁盘指标采集测试"""

    def test_get_disk_metrics_success(self):
        """测试磁盘指标采集成功"""
        result = get_disk_metrics()

        # 验证采集成功
        assert isinstance(result, list)
        if len(result) > 0:
            assert "device" in result[0]
            assert "mountpoint" in result[0]
            assert "fstype" in result[0]
            assert "total_gb" in result[0]
            assert "used_gb" in result[0]
            assert "free_gb" in result[0]
            assert "usage_percent" in result[0]


class TestNetworkMetrics:
    """网络指标采集测试"""

    def test_get_network_metrics_success(self):
        """测试网络指标采集成功"""
        result = get_network_metrics()

        # 验证采集成功
        assert "recv_speed_mb" in result
        assert "sent_speed_mb" in result
        assert "bytes_recv_total_mb" in result
        assert "bytes_sent_total_mb" in result
        assert "packets_recv" in result
        assert "packets_sent" in result
        assert "errin" in result
        assert "errout" in result
        assert result["recv_speed_mb"] >= 0
        assert result["sent_speed_mb"] >= 0


class TestTopProcesses:
    """Top 进程采集测试"""

    def test_get_top_processes_success(self):
        """测试 Top 进程采集成功"""
        result = get_top_processes(limit=10)

        # 验证采集成功
        assert isinstance(result, list)
        assert len(result) <= 10
        if len(result) > 0:
            assert "pid" in result[0]
            assert "name" in result[0]
            assert "cpu_percent" in result[0]
            assert "memory_percent" in result[0]
            assert "status" in result[0]
            assert "username" in result[0]

    def test_get_top_processes_custom_limit(self):
        """测试自定义限制数量"""
        result = get_top_processes(limit=5)

        # 验证限制生效
        assert isinstance(result, list)
        assert len(result) <= 5


class TestSystemInfo:
    """系统信息采集测试"""

    def test_get_system_info_success(self):
        """测试系统信息采集成功"""
        result = get_system_info()

        # 验证采集成功
        assert "os" in result
        assert "os_version" in result
        assert "os_release" in result
        assert "hostname" in result
        assert "architecture" in result
        assert "processor" in result
        assert "boot_time" in result
        assert "uptime_hours" in result
        assert result["uptime_hours"] >= 0


class TestCollectAll:
    """全量采集测试"""

    def test_collect_all_success(self):
        """测试全量采集成功"""
        result = collect_all()

        # 验证采集成功
        assert isinstance(result, dict)
        assert "cpu" in result
        assert "memory" in result
        assert "disk" in result
        assert "network" in result
        # processes and system might not be in the result
        # depending on implementation

    def test_collect_all_cache_hit(self):
        """测试缓存命中"""
        # 第一次采集
        result1 = collect_all()

        # 第二次采集应该命中缓存（在 TTL 内）
        result2 = collect_all()

        # 验证两次结果结构一致
        assert isinstance(result1, dict)
        assert isinstance(result2, dict)
        assert set(result1.keys()) == set(result2.keys())


class TestCacheFunctions:
    """缓存功能测试"""

    def test_get_cached_snapshot(self):
        """测试获取缓存快照"""
        # 先执行一次采集以填充缓存
        collect_all()

        # 获取缓存快照
        snapshot = get_cached_snapshot()

        # 验证快照结构
        if snapshot is not None:
            assert isinstance(snapshot, dict)
            assert "cpu" in snapshot
            assert "memory" in snapshot

    def test_invalidate_collect_cache(self):
        """测试失效缓存"""
        # 先执行一次采集以填充缓存
        collect_all()

        # 失效缓存
        invalidate_collect_cache()

        # 验证缓存已被失效
        snapshot = get_cached_snapshot()
        assert snapshot is None


class TestCollectMetrics:
    """采集性能指标测试"""

    def test_get_collect_metrics(self):
        """测试获取采集性能指标"""
        # 先执行一次采集
        collect_all()

        # 获取性能指标
        metrics = get_collect_metrics()

        # 验证指标结构
        assert isinstance(metrics, dict)
        assert "total_calls" in metrics
        assert "cache_hits" in metrics
        assert "cache_misses" in metrics
        assert "last_collect_ms" in metrics
        assert "avg_collect_ms" in metrics
        assert "timeout_count" in metrics
        assert "cache_hit_rate" in metrics
        assert metrics["total_calls"] >= 0
        assert 0 <= metrics["cache_hit_rate"] <= 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
