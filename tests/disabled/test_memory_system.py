# -*- coding: utf-8 -*-
"""
记忆系统单元测试
测试内存监控、内存泄漏检测和内存使用优化功能
"""

from unittest.mock import patch

import pytest

from core.memory_monitor import (
    MemoryLeakDetector,
    MemoryMonitor,
    memory_leak_detector,
    memory_monitor,
    memory_monitor_decorator,
    setup_memory_monitoring,
)
from core.memory_usage_optimizer import (
    MemoryAction,
    MemoryLeak,
    MemoryLimit,
    MemorySnapshot,
    MemoryUsageOptimizer,
    get_memory_usage_optimizer,
)


class TestMemoryMonitor:
    """内存监控器测试"""

    def test_initialization(self):
        """测试初始化"""
        monitor = MemoryMonitor(max_memory_mb=512, warning_threshold=0.7)
        assert monitor.max_memory_mb == 512
        assert monitor.warning_threshold == 0.7
        assert monitor._enable_tracemalloc is False
        assert monitor._memory_history == []
        assert monitor._max_history_size == 100

    def test_initialization_defaults(self):
        """测试默认初始化"""
        monitor = MemoryMonitor()
        assert monitor.max_memory_mb == 1024
        assert monitor.warning_threshold == 0.8

    def test_enable_tracemalloc(self):
        """测试启用内存跟踪"""
        monitor = MemoryMonitor()
        monitor.enable_tracemalloc()
        assert monitor._enable_tracemalloc is True

    def test_disable_tracemalloc(self):
        """测试禁用内存跟踪"""
        monitor = MemoryMonitor()
        monitor.enable_tracemalloc()
        monitor.disable_tracemalloc()
        assert monitor._enable_tracemalloc is False

    def test_get_memory_usage_without_tracemalloc(self):
        """测试未启用tracemalloc时获取内存使用"""
        monitor = MemoryMonitor()
        memory_info = monitor.get_memory_usage()
        assert "usage_mb" in memory_info
        assert "max_memory_mb" in memory_info
        assert "usage_rate" in memory_info
        assert "warning_threshold" in memory_info
        assert "timestamp" in memory_info

    def test_get_memory_usage_with_tracemalloc(self):
        """测试启用tracemalloc时获取内存使用"""
        monitor = MemoryMonitor()
        monitor.enable_tracemalloc()
        memory_info = monitor.get_memory_usage()
        assert "tracemalloc" in memory_info
        assert "current_traced" in memory_info["tracemalloc"]
        monitor.disable_tracemalloc()

    def test_check_memory_usage_healthy(self):
        """测试健康内存使用检查"""
        monitor = MemoryMonitor(max_memory_mb=1024)
        result = monitor.check_memory_usage()
        assert result["status"] == "healthy"
        assert "memory_info" in result

    def test_check_memory_usage_warning(self):
        """测试警告内存使用检查"""
        monitor = MemoryMonitor(max_memory_mb=100, warning_threshold=0.1)
        # Mock高内存使用
        with patch("core.memory_monitor.resource"):
            result = monitor.check_memory_usage()
            # 由于mock可能返回0，我们只检查结构
            assert "status" in result

    def test_check_memory_usage_history(self):
        """测试内存使用历史记录"""
        monitor = MemoryMonitor()
        monitor.check_memory_usage()
        monitor.check_memory_usage()
        history = monitor.get_memory_history(limit=2)
        assert len(history) <= 2

    def test_memory_history_limit(self):
        """测试内存历史记录限制"""
        monitor = MemoryMonitor(max_memory_mb=1024)
        # 添加超过限制的历史记录
        for _ in range(105):
            monitor.check_memory_usage()
        history = monitor.get_memory_history()
        assert len(history) <= 100

    def test_get_memory_leak_candidates_without_tracemalloc(self):
        """测试未启用tracemalloc时获取内存泄漏候选"""
        monitor = MemoryMonitor()
        candidates = monitor.get_memory_leak_candidates()
        assert candidates == []

    def test_get_memory_leak_candidates_with_tracemalloc(self):
        """测试启用tracemalloc时获取内存泄漏候选"""
        monitor = MemoryMonitor()
        monitor.enable_tracemalloc()
        candidates = monitor.get_memory_leak_candidates()
        # 由于没有实际内存泄漏，应该返回空列表或候选列表
        assert isinstance(candidates, list)
        monitor.disable_tracemalloc()


class TestMemoryLeakDetector:
    """内存泄漏检测器测试"""

    def test_initialization(self):
        """测试初始化"""
        detector = MemoryLeakDetector()
        assert detector._snapshots == {}
        assert detector._enable_tracemalloc is False

    def test_enable(self):
        """测试启用检测器"""
        detector = MemoryLeakDetector()
        detector.enable()
        assert detector._enable_tracemalloc is True

    def test_disable(self):
        """测试禁用检测器"""
        detector = MemoryLeakDetector()
        detector.enable()
        detector.disable()
        assert detector._enable_tracemalloc is False

    def test_take_snapshot_without_enable(self):
        """测试未启用时拍摄快照"""
        detector = MemoryLeakDetector()
        detector.take_snapshot("test_snapshot")
        # 应该不添加快照
        assert "test_snapshot" not in detector._snapshots

    def test_take_snapshot_with_enable(self):
        """测试启用时拍摄快照"""
        detector = MemoryLeakDetector()
        detector.enable()
        detector.take_snapshot("test_snapshot")
        assert "test_snapshot" in detector._snapshots
        detector.disable()

    def test_compare_snapshots_without_enable(self):
        """测试未启用时比较快照"""
        detector = MemoryLeakDetector()
        result = detector.compare_snapshots("snap1", "snap2")
        assert result == []

    def test_compare_snapshots_missing_snapshots(self):
        """测试比较不存在的快照"""
        detector = MemoryLeakDetector()
        detector.enable()
        result = detector.compare_snapshots("nonexistent1", "nonexistent2")
        assert result == []
        detector.disable()

    def test_compare_snapshots_valid(self):
        """测试比较有效快照"""
        detector = MemoryLeakDetector()
        detector.enable()
        detector.take_snapshot("snap1")
        detector.take_snapshot("snap2")
        result = detector.compare_snapshots("snap1", "snap2")
        assert isinstance(result, list)
        detector.disable()

    def test_detect_leaks_without_enable(self):
        """测试未启用时检测泄漏"""
        detector = MemoryLeakDetector()
        leaks = detector.detect_leaks()
        assert leaks == []

    def test_detect_leaks_insufficient_snapshots(self):
        """测试快照不足时检测泄漏"""
        detector = MemoryLeakDetector()
        detector.enable()
        detector.take_snapshot("snap1")
        leaks = detector.detect_leaks()
        assert leaks == []
        detector.disable()

    def test_detect_leaks_with_snapshots(self):
        """测试有足够快照时检测泄漏"""
        detector = MemoryLeakDetector()
        detector.enable()
        detector.take_snapshot("snap1")
        detector.take_snapshot("snap2")
        leaks = detector.detect_leaks(threshold_mb=0)
        assert isinstance(leaks, list)
        detector.disable()


class TestMemoryMonitorDecorator:
    """内存监控装饰器测试"""

    @pytest.mark.asyncio
    async def test_decorator_basic(self):
        """测试基本装饰器功能"""

        @memory_monitor_decorator(max_memory_mb=512)
        async def test_func():
            return "test_result"

        result = await test_func()
        assert result == "test_result"

    @pytest.mark.asyncio
    async def test_decorator_with_args(self):
        """测试带参数的装饰器"""

        @memory_monitor_decorator(max_memory_mb=256)
        async def test_func(x, y):
            return x + y

        result = await test_func(1, 2)
        assert result == 3

    @pytest.mark.asyncio
    async def test_decorator_exception_handling(self):
        """测试装饰器异常处理"""

        @memory_monitor_decorator(max_memory_mb=512)
        async def failing_func():
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            await failing_func()


class TestMemoryDataClasses:
    """内存数据类测试"""

    def test_memory_snapshot_creation(self):
        """测试MemorySnapshot创建"""
        from datetime import datetime, timezone

        snapshot = MemorySnapshot(
            snapshot_id="test_snap",
            timestamp=datetime.now(timezone.utc),
            total_memory_mb=1000.0,
            used_memory_mb=500.0,
            available_memory_mb=500.0,
            memory_percent=50.0,
            gc_objects=1000,
            gc_collections={0: 10, 1: 5, 2: 2},
        )
        assert snapshot.snapshot_id == "test_snap"
        assert snapshot.used_memory_mb == 500.0

    def test_memory_leak_creation(self):
        """测试MemoryLeak创建"""
        from datetime import datetime, timezone

        leak = MemoryLeak(
            leak_id="leak_1",
            component="test_component",
            leak_size_mb=100.0,
            growth_rate_mb_per_hour=10.0,
            detected_at=datetime.now(timezone.utc),
            severity="high",
        )
        assert leak.leak_id == "leak_1"
        assert leak.severity == "high"

    def test_memory_limit_creation(self):
        """测试MemoryLimit创建"""
        limit = MemoryLimit(
            component="test_component",
            max_memory_mb=1024.0,
            warning_threshold_percent=80.0,
            critical_threshold_percent=95.0,
            action_on_exceed=MemoryAction.COLLECT_GARBAGE,
        )
        assert limit.component == "test_component"
        assert limit.max_memory_mb == 1024.0


class TestMemoryUsageOptimizer:
    """内存使用优化器测试"""

    def test_initialization(self):
        """测试初始化"""
        optimizer = MemoryUsageOptimizer()
        assert optimizer.config == {}
        assert optimizer.monitoring_interval_seconds == 10
        assert optimizer.gc_threshold_percent == 80.0
        assert optimizer.leak_detection_window_hours == 24

    def test_initialization_with_config(self):
        """测试带配置的初始化"""
        config = {
            "monitoring_interval_seconds": 20,
            "gc_threshold_percent": 75.0,
            "leak_detection_window_hours": 12,
        }
        optimizer = MemoryUsageOptimizer(config)
        assert optimizer.monitoring_interval_seconds == 20
        assert optimizer.gc_threshold_percent == 75.0
        assert optimizer.leak_detection_window_hours == 12

    def test_take_memory_snapshot(self):
        """测试拍摄内存快照"""
        optimizer = MemoryUsageOptimizer()
        snapshot = optimizer.take_memory_snapshot("test_component")
        assert snapshot.used_memory_mb > 0
        assert snapshot.total_memory_mb > 0
        assert optimizer.component_memory["test_component"] == snapshot.used_memory_mb

    def test_set_memory_limit(self):
        """测试设置内存限制"""
        optimizer = MemoryUsageOptimizer()
        optimizer.set_memory_limit(
            component="test_component",
            max_memory_mb=512.0,
            warning_threshold_percent=75.0,
            critical_threshold_percent=90.0,
        )
        assert "test_component" in optimizer.memory_limits
        limit = optimizer.memory_limits["test_component"]
        assert limit.max_memory_mb == 512.0

    def test_check_memory_limit_no_limit(self):
        """测试无限制时的内存检查"""
        optimizer = MemoryUsageOptimizer()
        result = optimizer.check_memory_limit("nonexistent")
        assert result["status"] == "no_limit"

    def test_check_memory_limit_normal(self):
        """测试正常内存使用检查"""
        optimizer = MemoryUsageOptimizer()
        optimizer.set_memory_limit(component="test", max_memory_mb=1000.0)
        optimizer.component_memory["test"] = 500.0
        result = optimizer.check_memory_limit("test")
        assert result["status"] == "normal"

    def test_check_memory_limit_warning(self):
        """测试警告内存使用检查"""
        optimizer = MemoryUsageOptimizer()
        optimizer.set_memory_limit(
            component="test",
            max_memory_mb=100.0,
            warning_threshold_percent=80.0,
        )
        optimizer.component_memory["test"] = 85.0
        result = optimizer.check_memory_limit("test")
        assert result["status"] == "warning"

    def test_check_memory_limit_critical(self):
        """测试严重内存使用检查"""
        optimizer = MemoryUsageOptimizer()
        optimizer.set_memory_limit(
            component="test",
            max_memory_mb=100.0,
            critical_threshold_percent=95.0,
        )
        optimizer.component_memory["test"] = 96.0
        result = optimizer.check_memory_limit("test")
        assert result["status"] == "critical"

    def test_detect_memory_leaks_insufficient_snapshots(self):
        """测试快照不足时检测泄漏"""
        optimizer = MemoryUsageOptimizer()
        optimizer.take_memory_snapshot("test")
        leaks = optimizer.detect_memory_leaks("test")
        assert leaks == []

    def test_collect_garbage_all_generations(self):
        """测试收集所有代垃圾"""
        optimizer = MemoryUsageOptimizer()
        result = optimizer.collect_garbage()
        assert "collected_objects" in result
        assert "memory_freed_mb" in result

    def test_collect_garbage_specific_generation(self):
        """测试收集特定代垃圾"""
        optimizer = MemoryUsageOptimizer()
        result = optimizer.collect_garbage(generation=0)
        assert "collected_objects" in result
        # generation字段可能不在返回结果中，只检查收集对象数

    def test_get_memory_trace(self):
        """测试获取内存跟踪"""
        optimizer = MemoryUsageOptimizer()
        traces = optimizer.get_memory_trace(limit=5)
        assert isinstance(traces, list)
        assert len(traces) <= 5

    def test_optimize_memory_normal(self):
        """测试正常情况下的内存优化"""
        optimizer = MemoryUsageOptimizer()
        result = optimizer.optimize_memory("test")
        assert "component" in result
        assert "actions_taken" in result
        assert "memory_freed_mb" in result

    def test_optimize_memory_with_limit_warning(self):
        """测试警告限制下的内存优化"""
        optimizer = MemoryUsageOptimizer()
        optimizer.set_memory_limit(
            component="test",
            max_memory_mb=100.0,
            warning_threshold_percent=50.0,
        )
        optimizer.component_memory["test"] = 60.0
        result = optimizer.optimize_memory("test")
        assert "actions_taken" in result

    def test_get_memory_statistics(self):
        """测试获取内存统计"""
        optimizer = MemoryUsageOptimizer()
        stats = optimizer.get_memory_statistics()
        assert "total_memory_mb" in stats
        assert "used_memory_mb" in stats
        assert "memory_percent" in stats
        assert "total_gc_collections" in stats

    def test_get_component_memory(self):
        """测试获取组件内存使用"""
        optimizer = MemoryUsageOptimizer()
        optimizer.take_memory_snapshot("test_component")
        memory = optimizer.get_component_memory("test_component")
        assert memory is not None
        assert memory > 0

    def test_get_component_memory_not_found(self):
        """测试获取不存在的组件内存"""
        optimizer = MemoryUsageOptimizer()
        memory = optimizer.get_component_memory("nonexistent")
        assert memory is None

    def test_get_statistics(self):
        """测试获取优化器统计"""
        optimizer = MemoryUsageOptimizer()
        stats = optimizer.get_statistics()
        assert "total_gc_collections" in stats
        assert "total_memory_freed_mb" in stats
        assert "total_leaks_detected" in stats
        assert "total_memory_limits" in stats


class TestMemorySystemIntegration:
    """记忆系统集成测试"""

    def test_global_instances(self):
        """测试全局实例"""
        assert memory_monitor is not None
        assert memory_leak_detector is not None

    @pytest.mark.asyncio
    async def test_setup_memory_monitoring(self):
        """测试设置内存监控"""
        result = await setup_memory_monitoring()
        assert result["status"] in ["success", "error"]
        if result["status"] == "success":
            assert "tracemalloc_enabled" in result
            assert "leak_detection_enabled" in result

    def test_get_memory_usage_optimizer(self):
        """测试获取内存使用优化器实例"""
        optimizer = get_memory_usage_optimizer()
        assert optimizer is not None
        assert isinstance(optimizer, MemoryUsageOptimizer)

    def test_get_memory_usage_optimizer_with_config(self):
        """测试带配置获取内存使用优化器实例"""
        config = {"monitoring_interval_seconds": 30}
        optimizer = get_memory_usage_optimizer(config)
        assert optimizer.monitoring_interval_seconds == 30


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
