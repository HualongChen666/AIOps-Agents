# -*- coding: utf-8 -*-
"""
错误日志处理器模块

提供错误日志的统计、聚合和分析功能。
"""

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional


class ErrorLogHandler:
    """
    错误日志处理器

    负责错误日志的统计、聚合和分析。
    """

    def __init__(self):
        """初始化错误日志处理器"""
        self._error_stats: Dict[str, int] = defaultdict(int)
        self._error_history: List[Dict[str, Any]] = []
        self._error_trends: Dict[str, List[datetime]] = defaultdict(list)

    def record_error(
        self,
        error_code: str,
        severity: str,
        category: str,
        timestamp: Optional[datetime] = None,
    ):
        """
        记录错误

        Args:
            error_code: 错误码
            severity: 严重程度
            category: 错误分类
            timestamp: 时间戳
        """
        if timestamp is None:
            timestamp = datetime.now()

        # 统计错误码
        self._error_stats[error_code] += 1

        # 记录错误历史
        self._error_history.append(
            {
                "error_code": error_code,
                "severity": severity,
                "category": category,
                "timestamp": timestamp,
            }
        )

        # 记录错误趋势
        self._error_trends[error_code].append(timestamp)

        # 限制历史记录数量
        if len(self._error_history) > 10000:
            self._error_history = self._error_history[-5000:]

    def get_error_stats(self) -> Dict[str, int]:
        """
        获取错误统计

        Returns:
            错误码统计字典
        """
        return dict(self._error_stats)

    def get_error_count(self, error_code: Optional[str] = None) -> int:
        """
        获取错误数量

        Args:
            error_code: 错误码，如果为None则返回总错误数

        Returns:
            错误数量
        """
        if error_code is None:
            return sum(self._error_stats.values())
        return self._error_stats.get(error_code, 0)

    def get_error_history(
        self,
        limit: int = 100,
        error_code: Optional[str] = None,
        severity: Optional[str] = None,
        category: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        获取错误历史

        Args:
            limit: 返回数量限制
            error_code: 错误码过滤
            severity: 严重程度过滤
            category: 分类过滤

        Returns:
            错误历史列表
        """
        history = self._error_history

        if error_code:
            history = [e for e in history if e["error_code"] == error_code]

        if severity:
            history = [e for e in history if e["severity"] == severity]

        if category:
            history = [e for e in history if e["category"] == category]

        return history[-limit:]

    def get_error_trends(
        self,
        error_code: str,
        hours: int = 24,
    ) -> List[datetime]:
        """
        获取错误趋势

        Args:
            error_code: 错误码
            hours: 时间范围（小时）

        Returns:
            时间戳列表
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        return [t for t in self._error_trends[error_code] if t >= cutoff_time]

    def get_error_rate(
        self,
        error_code: Optional[str] = None,
        hours: int = 1,
    ) -> float:
        """
        获取错误率

        Args:
            error_code: 错误码，如果为None则计算总错误率
            hours: 时间范围（小时）

        Returns:
            错误率（错误数/小时）
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)

        if error_code:
            timestamps = self._error_trends[error_code]
        else:
            timestamps = []
            for ts_list in self._error_trends.values():
                timestamps.extend(ts_list)

        recent_errors = [t for t in timestamps if t >= cutoff_time]
        return len(recent_errors) / hours if hours > 0 else 0

    def get_top_errors(self, limit: int = 10) -> List[tuple[str, int]]:
        """
        获取最频繁的错误

        Args:
            limit: 返回数量限制

        Returns:
            (错误码, 数量)列表，按数量降序排列
        """
        sorted_errors = sorted(self._error_stats.items(), key=lambda x: x[1], reverse=True)
        return sorted_errors[:limit]

    def get_category_stats(self) -> Dict[str, int]:
        """
        获取分类统计

        Returns:
            分类统计字典
        """
        category_stats = defaultdict(int)  # type: ignore[var-annotated]
        for error in self._error_history:
            category_stats[error["category"]] += 1
        return dict(category_stats)

    def get_severity_stats(self) -> Dict[str, int]:
        """
        获取严重程度统计

        Returns:
            严重程度统计字典
        """
        severity_stats = defaultdict(int)  # type: ignore[var-annotated]
        for error in self._error_history:
            severity_stats[error["severity"]] += 1
        return dict(severity_stats)

    def clear_history(self):
        """清空历史记录"""
        self._error_history.clear()
        self._error_stats.clear()
        self._error_trends.clear()


# 全局错误日志处理器实例
_error_log_handler = ErrorLogHandler()


def record_error(
    error_code: str,
    severity: str,
    category: str,
    timestamp: Optional[datetime] = None,
):
    """
    记录错误（便捷函数）

    Args:
        error_code: 错误码
        severity: 严重程度
        category: 错误分类
        timestamp: 时间戳
    """
    _error_log_handler.record_error(error_code, severity, category, timestamp)


def get_error_stats() -> Dict[str, int]:
    """
    获取错误统计（便捷函数）

    Returns:
        错误码统计字典
    """
    return _error_log_handler.get_error_stats()


def get_error_count(error_code: Optional[str] = None) -> int:
    """
    获取错误数量（便捷函数）

    Args:
        error_code: 错误码，如果为None则返回总错误数

    Returns:
        错误数量
    """
    return _error_log_handler.get_error_count(error_code)


def get_error_log_handler() -> ErrorLogHandler:
    """
    获取错误日志处理器实例

    Returns:
        错误日志处理器实例
    """
    return _error_log_handler
