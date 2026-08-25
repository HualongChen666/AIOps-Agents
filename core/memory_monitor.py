# -*- coding: utf-8 -*-
"""
Memory Monitor Module
内存监控模块

提供内存使用监控和内存泄漏防护功能。
"""

import gc
import logging
import sys
import tracemalloc
from datetime import datetime, timezone
from functools import wraps
from typing import Any, Callable, Dict, List, cast

# resource module is Unix-only, make it optional
if sys.platform != "win32":
    import resource

    HAS_RESOURCE = True
else:
    resource = None
    HAS_RESOURCE = False
    # On Windows, use psutil if available
    try:
        pass

        HAS_PSUTIL = True
    except ImportError:
        HAS_PSUTIL = False

logger = logging.getLogger(__name__)


class MemoryMonitor:
    """内存监控器"""

    def __init__(self, max_memory_mb: int = 1024, warning_threshold: float = 0.8):
        """
        初始化内存监控器

        Args:
            max_memory_mb: 最大内存限制（MB）
            warning_threshold: 警告阈值（0-1）
        """
        self.max_memory_mb = max_memory_mb
        self.warning_threshold = warning_threshold
        self._enable_tracemalloc = False
        self._memory_history: list = []
        self._max_history_size = 100

    def enable_tracemalloc(self):
        """启用内存跟踪"""
        tracemalloc.start()
        self._enable_tracemalloc = True
        logger.info("Memory tracking enabled")

    def disable_tracemalloc(self):
        """禁用内存跟踪"""
        if self._enable_tracemalloc:
            tracemalloc.stop()
            self._enable_tracemalloc = False
            logger.info("Memory tracking disabled")

    def get_memory_usage(self) -> Dict[str, Any]:
        """
        获取当前内存使用情况

        Returns:
            内存使用信息字典
        """
        # 获取当前进程的内存使用
        if HAS_RESOURCE:
            if resource is None:
                raise RuntimeError("resource module is not available")
            usage_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024  # KB to MB
        elif HAS_PSUTIL:
            import psutil

            process = psutil.Process()
            usage_mb = process.memory_info().rss / 1024 / 1024  # bytes to MB
        else:
            # Fallback to tracemalloc if available
            if self._enable_tracemalloc:
                current, _ = tracemalloc.get_traced_memory()
                usage_mb = current / 1024 / 1024  # bytes to MB
            else:
                usage_mb = 0

        # 如果启用了tracemalloc，获取更详细的信息
        tracemalloc_info = {}
        if self._enable_tracemalloc:
            current, peak = tracemalloc.get_traced_memory()
            tracemalloc_info = {
                "current_traced": current / 1024 / 1024,  # bytes to MB
                "peak_traced": peak / 1024 / 1024,  # bytes to MB
            }

        # 计算使用率
        usage_rate = usage_mb / self.max_memory_mb

        return {
            "usage_mb": usage_mb,
            "max_memory_mb": self.max_memory_mb,
            "usage_rate": usage_rate,
            "warning_threshold": self.warning_threshold,
            "tracemalloc": tracemalloc_info,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def check_memory_usage(self) -> Dict[str, Any]:
        """
        检查内存使用情况

        Returns:
            检查结果字典
        """
        memory_info = self.get_memory_usage()
        usage_rate = memory_info["usage_rate"]

        # 记录历史
        self._memory_history.append(
            {
                "usage_mb": memory_info["usage_mb"],
                "usage_rate": usage_rate,
                "timestamp": memory_info["timestamp"],
            }
        )

        # 限制历史大小
        if len(self._memory_history) > self._max_history_size:
            self._memory_history = self._memory_history[-self._max_history_size :]

        # 检查是否超过阈值
        if usage_rate > self.warning_threshold:
            logger.warning(
                f"Memory usage high: {memory_info['usage_mb']:.2f}MB "
                f"({usage_rate:.1%} of {self.max_memory_mb}MB limit)"
            )

            # 触发垃圾回收
            self._trigger_gc()

            return {
                "status": "warning",
                "memory_info": memory_info,
                "message": f"Memory usage exceeds {self.warning_threshold:.0%} threshold",
            }
        elif usage_rate > 0.95:
            logger.error(
                f"Memory usage critical: {memory_info['usage_mb']:.2f}MB "
                f"({usage_rate:.1%} of {self.max_memory_mb}MB limit)"
            )

            return {
                "status": "critical",
                "memory_info": memory_info,
                "message": "Memory usage critical, immediate action required",
            }
        else:
            return {"status": "healthy", "memory_info": memory_info}

    def _trigger_gc(self):
        """触发垃圾回收"""
        logger.info("Triggering garbage collection due to high memory usage")

        # 执行垃圾回收
        collected = gc.collect()

        logger.info(f"Garbage collection completed, {collected} objects collected")

        # 如果启用了tracemalloc，获取快照
        if self._enable_tracemalloc:
            snapshot = tracemalloc.take_snapshot()
            logger.info(f"Memory snapshot taken: {snapshot}")

    def get_memory_history(self, limit: int = 10) -> list:
        """
        获取内存使用历史

        Args:
            limit: 返回的历史记录数量

        Returns:
            内存使用历史记录
        """
        return self._memory_history[-limit:]

    def get_memory_leak_candidates(self) -> list:
        """
        获取可能的内存泄漏候选对象

        Returns:
            可能泄漏的对象列表
        """
        if not self._enable_tracemalloc:
            logger.warning("Tracemalloc not enabled, cannot detect memory leaks")
            return []

        # 获取所有对象的统计信息
        snapshot1 = tracemalloc.take_snapshot()

        # 执行一些操作后再次快照
        snapshot2 = tracemalloc.take_snapshot()

        # 比较快照
        stats = snapshot2.compare_to(snapshot1, "lineno")

        # 返回增长最多的对象
        leak_candidates = sorted(stats, key=lambda x: x.size_diff, reverse=True)[:10]

        return [
            {
                "file": stat.traceback[0].filename,
                "line": stat.traceback[0].lineno,
                "size_diff": stat.size_diff,
                "size": stat.size,
            }
            for stat in leak_candidates
        ]


def memory_monitor_decorator(max_memory_mb: int = 512):
    """
    内存监控装饰器

    Args:
        max_memory_mb: 最大内存限制（MB）
    """

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            monitor = MemoryMonitor(max_memory_mb=max_memory_mb)
            monitor.enable_tracemalloc()

            try:
                # 执行前检查
                pre_check = monitor.check_memory_usage()
                logger.debug(f"Pre-execution memory check: {pre_check['status']}")

                # 执行函数
                result = await func(*args, **kwargs)

                # 执行后检查
                post_check = monitor.check_memory_usage()
                logger.debug(f"Post-execution memory check: {post_check['status']}")

                return result

            finally:
                monitor.disable_tracemalloc()

        return wrapper

    return decorator


class MemoryLeakDetector:
    """内存泄漏检测器"""

    def __init__(self):
        """初始化内存泄漏检测器"""
        self._snapshots = {}
        self._enable_tracemalloc = False

    def enable(self):
        """启用内存泄漏检测"""
        tracemalloc.start(25)  # 追踪25帧调用栈
        self._enable_tracemalloc = True
        logger.info("Memory leak detection enabled")

    def disable(self):
        """禁用内存泄漏检测"""
        if self._enable_tracemalloc:
            tracemalloc.stop()
            self._enable_tracemalloc = False
            logger.info("Memory leak detection disabled")

    def take_snapshot(self, name: str):
        """
        拍摄内存快照

        Args:
            name: 快照名称
        """
        if not self._enable_tracemalloc:
            logger.warning("Tracemalloc not enabled, cannot take snapshot")
            return

        snapshot_id = tracemalloc.take_snapshot()
        self._snapshots[name] = snapshot_id
        logger.info(f"Memory snapshot taken: {name} (ID: {snapshot_id})")

    def compare_snapshots(self, name1: str, name2: str) -> List[Any]:
        """
        比较两个内存快照

        Args:
            name1: 第一个快照名称
            name2: 第二个快照名称

        Returns:
            内存差异统计
        """
        if not self._enable_tracemalloc:
            logger.warning("Tracemalloc not enabled, cannot compare snapshots")
            return []

        if name1 not in self._snapshots or name2 not in self._snapshots:
            logger.error(f"Snapshots not found: {name1}, {name2}")
            return []

        snapshot1 = self._snapshots[name1]
        snapshot2 = self._snapshots[name2]

        stats = snapshot2.compare_to(snapshot1, "lineno")

        logger.info(f"Memory comparison between {name1} and {name2}: {len(stats)} differences")

        return cast(List[Any], stats)

    def detect_leaks(self, threshold_mb: int = 10) -> list:
        """
        检测内存泄漏

        Args:
            threshold_mb: 内存增长阈值（MB）

        Returns:
            可能的内存泄漏点
        """
        if not self._enable_tracemalloc:
            logger.warning("Tracemalloc not enabled, cannot detect leaks")
            return []

        if len(self._snapshots) < 2:
            logger.warning("Need at least 2 snapshots to detect leaks")
            return []

        # 获取最早的和最新的快照
        snapshot_names = list(self._snapshots.keys())
        first_snapshot = snapshot_names[0]
        last_snapshot = snapshot_names[-1]

        stats = self.compare_snapshots(first_snapshot, last_snapshot)

        # 过滤出增长超过阈值的
        leaks = [
            stat for stat in stats if stat.size_diff / 1024 / 1024 > threshold_mb  # bytes to MB
        ]

        logger.info(f"Detected {len(leaks)} potential memory leaks (threshold: {threshold_mb}MB)")

        return leaks


# 全局内存监控实例
MEMORY_MONITOR = MemoryMonitor()
MEMORY_LEAK_DETECTOR = MemoryLeakDetector()


async def setup_memory_monitoring():
    """
    设置内存监控

    Returns:
        设置结果
    """
    try:
        # 启用内存跟踪
        MEMORY_MONITOR.enable_tracemalloc()

        # 启用内存泄漏检测
        memory_leak_detector.enable()

        logger.info("Memory monitoring setup completed")

        return {
            "status": "success",
            "max_memory_mb": memory_monitor.max_memory_mb,
            "warning_threshold": memory_monitor.warning_threshold,
            "tracemalloc_enabled": memory_monitor._enable_tracemalloc,
            "leak_detection_enabled": memory_leak_detector._enable_tracemalloc,
        }

    except Exception as e:
        logger.error(f"Memory monitoring setup failed: {e}")
        return {"status": "error", "error": str(e)}
