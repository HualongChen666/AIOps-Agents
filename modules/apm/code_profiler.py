# -*- coding: utf-8 -*-
"""
code_profiler.py
----------------
APM 代码级性能分析模块。

功能：
- 代码热点分析
- 函数调用链追踪
- 内存泄漏检测
- SQL 查询分析
- 性能瓶颈识别
"""

from __future__ import annotations

import functools
import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple  # noqa: F401

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# 1️⃣ 性能指标定义
# ----------------------------------------------------------------------
@dataclass
class PerformanceMetric:
    """性能指标"""

    function_name: str
    call_count: int = 0
    total_time: float = 0.0
    avg_time: float = 0.0
    max_time: float = 0.0
    min_time: float = float("inf")
    memory_usage: float = 0.0
    cpu_usage: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "function_name": self.function_name,
            "call_count": self.call_count,
            "total_time": self.total_time,
            "avg_time": self.avg_time,
            "max_time": self.max_time,
            "min_time": self.min_time if self.min_time != float("inf") else 0,
            "memory_usage": self.memory_usage,
            "cpu_usage": self.cpu_usage,
        }


# ----------------------------------------------------------------------
# 2️⃣ 调用栈追踪
# ----------------------------------------------------------------------
@dataclass
class CallStack:
    """调用栈"""

    function_name: str
    start_time: float
    end_time: Optional[float] = None
    children: List["CallStack"] = field(default_factory=list)
    parent: Optional["CallStack"] = None

    @property
    def duration(self) -> float:
        """持续时间"""
        if self.end_time is None:
            return time.time() - self.start_time
        return self.end_time - self.start_time

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "function_name": self.function_name,
            "duration": self.duration,
            "children": [child.to_dict() for child in self.children],
        }


# ----------------------------------------------------------------------
# 3️⃣ 代码性能分析器
# ----------------------------------------------------------------------
class CodeProfiler:
    """代码性能分析器"""

    def __init__(self):
        self.metrics: Dict[str, PerformanceMetric] = {}
        self.call_stacks: List[CallStack] = []
        self.current_stack: Optional[CallStack] = None
        self._lock = threading.Lock()
        self._enabled = True

    def enable(self):
        """启用分析器"""
        self._enabled = True
        logger.info("Code profiler enabled")

    def disable(self):
        """禁用分析器"""
        self._enabled = False
        logger.info("Code profiler disabled")

    def profile(self, function_name: Optional[str] = None):
        """
        装饰器：分析函数性能

        Parameters
        ----------
        function_name : str, optional
            函数名称（如果为 None，使用被装饰函数的名称）
        """

        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                if not self._enabled:
                    return func(*args, **kwargs)

                name = function_name or func.__name__
                start_time = time.time()

                # 创建调用栈节点
                with self._lock:
                    stack_node = CallStack(
                        function_name=name,
                        start_time=start_time,
                        parent=self.current_stack,
                    )

                    if self.current_stack:
                        self.current_stack.children.append(stack_node)
                    else:
                        self.call_stacks.append(stack_node)

                    prev_stack = self.current_stack
                    self.current_stack = stack_node

                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    end_time = time.time()
                    duration = end_time - start_time

                    with self._lock:
                        stack_node.end_time = end_time
                        self.current_stack = prev_stack

                        # 更新指标
                        if name not in self.metrics:
                            self.metrics[name] = PerformanceMetric(function_name=name)

                        metric = self.metrics[name]
                        metric.call_count += 1
                        metric.total_time += duration
                        metric.avg_time = metric.total_time / metric.call_count
                        metric.max_time = max(metric.max_time, duration)
                        metric.min_time = min(metric.min_time, duration)

            return wrapper

        return decorator

    def get_hotspots(
        self,
        top_n: int = 10,
        by: str = "total_time",
    ) -> List[PerformanceMetric]:
        """
        获取代码热点

        Parameters
        ----------
        top_n : int
            返回前 N 个热点
        by : str
            排序依据：'total_time', 'avg_time', 'call_count'

        Returns
        -------
        List[PerformanceMetric]
            热点列表
        """
        metrics = list(self.metrics.values())

        if by == "total_time":
            metrics.sort(key=lambda m: m.total_time, reverse=True)
        elif by == "avg_time":
            metrics.sort(key=lambda m: m.avg_time, reverse=True)
        elif by == "call_count":
            metrics.sort(key=lambda m: m.call_count, reverse=True)

        return metrics[:top_n]

    def get_call_tree(self) -> List[Dict[str, Any]]:
        """获取调用树"""
        return [stack.to_dict() for stack in self.call_stacks]

    def reset(self):
        """重置分析器"""
        with self._lock:
            self.metrics.clear()
            self.call_stacks.clear()
            self.current_stack = None
        logger.info("Code profiler reset")


# ----------------------------------------------------------------------
# 4️⃣ 内存分析器
# ----------------------------------------------------------------------
class MemoryProfiler:
    """内存分析器"""

    def __init__(self):
        self.memory_snapshots: List[Dict[str, Any]] = []
        self._enabled = True

    def enable(self):
        """启用内存分析器"""
        self._enabled = True
        logger.info("Memory profiler enabled")

    def disable(self):
        """禁用内存分析器"""
        self._enabled = False
        logger.info("Memory profiler disabled")

    def take_snapshot(self, label: str = ""):
        """
        获取内存快照

        Parameters
        ----------
        label : str
            快照标签
        """
        if not self._enabled:
            return

        try:
            import os

            import psutil

            process = psutil.Process(os.getpid())

            snapshot = {
                "label": label,
                "timestamp": time.time(),
                "rss": process.memory_info().rss / 1024 / 1024,  # MB
                "vms": process.memory_info().vms / 1024 / 1024,  # MB
                "percent": process.memory_percent(),
            }

            self.memory_snapshots.append(snapshot)
            logger.info(f"Memory snapshot taken: {label} - RSS: {snapshot['rss']:.2f} MB")

        except ImportError:
            logger.warning("psutil not available, memory profiling disabled")
            self._enabled = False
        except Exception as e:
            logger.error(f"Failed to take memory snapshot: {e}")

    def detect_leaks(self, threshold: float = 10.0) -> List[Dict[str, Any]]:
        """
        检测内存泄漏

        Parameters
        ----------
        threshold : float
            内存增长阈值（MB）

        Returns
        -------
        List[Dict[str, Any]]
            泄漏报告
        """
        if len(self.memory_snapshots) < 2:
            return []

        leaks = []

        for i in range(1, len(self.memory_snapshots)):
            prev = self.memory_snapshots[i - 1]
            curr = self.memory_snapshots[i]

            growth = curr["rss"] - prev["rss"]

            if growth > threshold:
                leaks.append(
                    {
                        "from_snapshot": prev["label"],
                        "to_snapshot": curr["label"],
                        "growth_mb": growth,
                        "from_rss": prev["rss"],
                        "to_rss": curr["rss"],
                    }
                )

        return leaks

    def get_memory_trend(self) -> Dict[str, Any]:
        """获取内存趋势"""
        if not self.memory_snapshots:
            return {}

        rss_values = [s["rss"] for s in self.memory_snapshots]

        return {
            "snapshots": len(self.memory_snapshots),
            "min_rss": min(rss_values),
            "max_rss": max(rss_values),
            "avg_rss": sum(rss_values) / len(rss_values),
            "total_growth": rss_values[-1] - rss_values[0] if len(rss_values) > 1 else 0,
        }


# ----------------------------------------------------------------------
# 5️⃣ SQL 查询分析器
# ----------------------------------------------------------------------
class SQLQueryAnalyzer:
    """SQL 查询分析器"""

    def __init__(self):
        self.queries: Dict[str, Dict[str, Any]] = {}
        self._enabled = True

    def enable(self):
        """启用 SQL 分析器"""
        self._enabled = True
        logger.info("SQL query analyzer enabled")

    def disable(self):
        """禁用 SQL 分析器"""
        self._enabled = False
        logger.info("SQL query analyzer disabled")

    def record_query(
        self,
        query: str,
        execution_time: float,
        rows_affected: int = 0,
    ):
        """
        记录 SQL 查询

        Parameters
        ----------
        query : str
            SQL 查询语句
        execution_time : float
            执行时间（秒）
        rows_affected : int
            影响的行数
        """
        if not self._enabled:
            return

        # 标准化查询（去除参数）
        normalized = self._normalize_query(query)

        if normalized not in self.queries:
            self.queries[normalized] = {
                "query": normalized,
                "call_count": 0,
                "total_time": 0.0,
                "avg_time": 0.0,
                "max_time": 0.0,
                "total_rows": 0,
            }

        stats = self.queries[normalized]
        stats["call_count"] += 1
        stats["total_time"] += execution_time
        stats["avg_time"] = stats["total_time"] / stats["call_count"]
        stats["max_time"] = max(stats["max_time"], execution_time)
        stats["total_rows"] += rows_affected

    def _normalize_query(self, query: str) -> str:
        """标准化查询（去除参数）"""
        import re

        # 移除字符串字面量
        query = re.sub(r"'[^']*'", "'?'", query)
        query = re.sub(r'"[^"]*"', '"?"', query)

        # 移除数字
        query = re.sub(r"\b\d+\b", "?", query)

        # 标准化空白
        query = " ".join(query.split())

        return query

    def get_slow_queries(
        self,
        threshold: float = 1.0,
        top_n: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        获取慢查询

        Parameters
        ----------
        threshold : float
        慢查询阈值（秒）
        top_n : int
            返回前 N 个

        Returns
        -------
        List[Dict[str, Any]]
            慢查询列表
        """
        slow_queries = [q for q in self.queries.values() if q["avg_time"] > threshold]

        slow_queries.sort(key=lambda q: q["avg_time"], reverse=True)

        return slow_queries[:top_n]

    def get_query_statistics(self) -> Dict[str, Any]:
        """获取查询统计"""
        if not self.queries:
            return {}

        total_calls = sum(q["call_count"] for q in self.queries.values())
        total_time = sum(q["total_time"] for q in self.queries.values())

        return {
            "total_queries": len(self.queries),
            "total_calls": total_calls,
            "total_time": total_time,
            "avg_query_time": total_time / total_calls if total_calls > 0 else 0,
        }


# ----------------------------------------------------------------------
# 6️⃣ 综合性能分析器
# ----------------------------------------------------------------------
class APMProfiler:
    """综合 APM 性能分析器"""

    def __init__(self):
        self.code_profiler = CodeProfiler()
        self.memory_profiler = MemoryProfiler()
        self.sql_analyzer = SQLQueryAnalyzer()

    def enable_all(self):
        """启用所有分析器"""
        self.code_profiler.enable()
        self.memory_profiler.enable()
        self.sql_analyzer.enable()
        logger.info("All APM profilers enabled")

    def disable_all(self):
        """禁用所有分析器"""
        self.code_profiler.disable()
        self.memory_profiler.disable()
        self.sql_analyzer.disable()
        logger.info("All APM profilers disabled")

    def get_performance_report(self) -> Dict[str, Any]:
        """获取性能报告"""
        return {
            "code_hotspots": [m.to_dict() for m in self.code_profiler.get_hotspots()],
            "call_tree": self.code_profiler.get_call_tree(),
            "memory_trend": self.memory_profiler.get_memory_trend(),
            "memory_leaks": self.memory_profiler.detect_leaks(),
            "slow_queries": self.sql_analyzer.get_slow_queries(),
            "query_stats": self.sql_analyzer.get_query_statistics(),
        }

    def reset(self):
        """重置所有分析器"""
        self.code_profiler.reset()
        self.memory_profiler.memory_snapshots.clear()
        self.sql_analyzer.queries.clear()
        logger.info("All APM profilers reset")


# ----------------------------------------------------------------------
# 7️⃣ 工厂函数
# ----------------------------------------------------------------------
def create_apm_profiler() -> APMProfiler:
    """创建 APM 性能分析器"""
    return APMProfiler()


# ----------------------------------------------------------------------
# 8️⃣ CLI 用于快速测试
# ----------------------------------------------------------------------
if __name__ == "__main__":  # pragma: no cover

    logging.basicConfig(level=logging.INFO)

    # 测试 APM 性能分析器
    logger.info("Testing APM profiler")

    profiler = create_apm_profiler()
    profiler.enable_all()

    # 测试代码分析
    @profiler.code_profiler.profile()
    def test_function():
        time.sleep(0.1)
        return "done"

    test_function()
    test_function()

    # 测试内存快照
    profiler.memory_profiler.take_snapshot("before")
    profiler.memory_profiler.take_snapshot("after")

    # 测试 SQL 分析
    profiler.sql_analyzer.record_query("SELECT * FROM users WHERE id = 1", 0.05, 1)
    profiler.sql_analyzer.record_query("SELECT * FROM users WHERE id = 2", 0.06, 1)
    profiler.sql_analyzer.record_query("SELECT * FROM orders WHERE user_id = 1", 0.5, 10)

    # 获取性能报告
    report = profiler.get_performance_report()

    logger.info(f"Code hotspots: {len(report['code_hotspots'])}")
    logger.info(f"Memory leaks: {len(report['memory_leaks'])}")
    logger.info(f"Slow queries: {len(report['slow_queries'])}")

    logger.info("Test passed!")
