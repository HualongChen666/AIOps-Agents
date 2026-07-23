# -*- coding: utf-8 -*-
"""
Performance Report Generator
性能报告生成服务
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from sqlalchemy import select

from core.db_engine import AsyncSessionLocal
from core.models import (
    PerformanceMetric,
    PerformanceRegression,
)

logger = logging.getLogger(__name__)


class PerformanceReportGenerator:
    """性能报告生成器"""

    def __init__(self):
        """初始化性能报告生成器"""
        self.session = None

    async def __aenter__(self):
        """异步上下文管理器入口"""
        self.session = AsyncSessionLocal()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        if self.session:
            await self.session.close()

    async def generate_daily_report(
        self,
        environment: str = "dev",
        date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        生成日报

        Args:
            environment: 环境
            date: 日期（默认为今天）

        Returns:
            日报数据
        """
        if date is None:
            date = datetime.now()

        start_time = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = start_time + timedelta(days=1)

        try:
            async with AsyncSessionLocal() as session:
                # 查询当天的性能指标
                stmt = (
                    select(PerformanceMetric)
                    .where(PerformanceMetric.environment == environment)
                    .where(PerformanceMetric.timestamp >= start_time)
                    .where(PerformanceMetric.timestamp < end_time)
                )

                result = await session.execute(stmt)
                metrics = result.scalars().all()

                # 按组件分组统计
                component_stats = {}
                for metric in metrics:
                    component = metric.component
                    if component not in component_stats:
                        component_stats[component] = {
                            "count": 0,
                            "total_p95": 0.0,
                            "total_throughput": 0.0,
                            "total_errors": 0,
                        }

                    stats = component_stats[component]
                    stats["count"] += 1
                    if metric.p95_time_ms:
                        p95 = metric.p95_time_ms
                        stats["total_p95"] += p95  # type: ignore[assignment]
                    if metric.throughput_ops:
                        throughput_ops = metric.throughput_ops
                        stats["total_throughput"] += throughput_ops  # type: ignore[assignment]
                    if metric.error_count:
                        error_count = metric.error_count
                        stats["total_errors"] += error_count  # type: ignore[assignment]

                # 计算平均值
                for component, stats in component_stats.items():
                    if stats["count"] > 0:
                        stats["avg_p95"] = stats["total_p95"] / stats["count"]
                        stats["avg_throughput"] = stats["total_throughput"] / stats["count"]

                # 查询当天的回归
                regression_stmt = (
                    select(PerformanceRegression)
                    .where(PerformanceRegression.environment == environment)
                    .where(PerformanceRegression.detected_at >= start_time)
                    .where(PerformanceRegression.detected_at < end_time)
                )

                regression_result = await session.execute(regression_stmt)
                regressions = regression_result.scalars().all()

                return {
                    "report_type": "daily",
                    "date": date.strftime("%Y-%m-%d"),
                    "environment": environment,
                    "summary": {
                        "total_tests": len(metrics),
                        "total_components": len(component_stats),
                        "total_regressions": len(regressions),
                    },
                    "component_stats": component_stats,
                    "regressions": [
                        {
                            "regression_id": r.regression_id,
                            "component": r.component,
                            "severity": r.severity,
                            "deviation": r.deviation,
                        }
                        for r in regressions
                    ],
                }

        except Exception as e:
            logger.error(f"生成日报失败: {e}", exc_info=True)
            return {}

    async def generate_weekly_report(
        self,
        environment: str = "dev",
        start_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        生成周报

        Args:
            environment: 环境
            start_date: 开始日期（默认为7天前）

        Returns:
            周报数据
        """
        if start_date is None:
            start_date = datetime.now() - timedelta(days=7)

        end_date = start_date + timedelta(days=7)

        try:
            async with AsyncSessionLocal() as session:
                # 查询周内的性能指标
                stmt = (
                    select(PerformanceMetric)
                    .where(PerformanceMetric.environment == environment)
                    .where(PerformanceMetric.timestamp >= start_date)
                    .where(PerformanceMetric.timestamp < end_date)
                )

                result = await session.execute(stmt)
                metrics = result.scalars().all()

                # 按天分组统计
                daily_stats = {}
                for metric in metrics:
                    day_key = metric.timestamp.strftime("%Y-%m-%d")
                    if day_key not in daily_stats:
                        daily_stats[day_key] = {
                            "count": 0,
                            "total_p95": 0.0,
                        }

                    daily_stats[day_key]["count"] += 1
                    if metric.p95_time_ms:
                        p95 = metric.p95_time_ms
                        daily_stats[day_key]["total_p95"] += p95  # type: ignore[assignment]

                # 计算每天的平均值
                for day_key, stats in daily_stats.items():
                    if stats["count"] > 0:
                        stats["avg_p95"] = stats["total_p95"] / stats["count"]

                # 查询周内的回归
                regression_stmt = (
                    select(PerformanceRegression)
                    .where(PerformanceRegression.environment == environment)
                    .where(PerformanceRegression.detected_at >= start_date)
                    .where(PerformanceRegression.detected_at < end_date)
                )

                regression_result = await session.execute(regression_stmt)
                regressions = regression_result.scalars().all()

                return {
                    "report_type": "weekly",
                    "start_date": start_date.strftime("%Y-%m-%d"),
                    "end_date": end_date.strftime("%Y-%m-%d"),
                    "environment": environment,
                    "summary": {
                        "total_tests": len(metrics),
                        "total_days": len(daily_stats),
                        "total_regressions": len(regressions),
                    },
                    "daily_stats": daily_stats,
                    "regressions": [
                        {
                            "regression_id": r.regression_id,
                            "component": r.component,
                            "severity": r.severity,
                            "deviation": r.deviation,
                            "detected_at": r.detected_at.isoformat() if r.detected_at else None,
                        }
                        for r in regressions
                    ],
                }

        except Exception as e:
            logger.error(f"生成周报失败: {e}", exc_info=True)
            return {}

    async def generate_monthly_report(
        self,
        environment: str = "dev",
        year: Optional[int] = None,
        month: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        生成月报

        Args:
            environment: 环境
            year: 年份（默认为当前年）
            month: 月份（默认为当前月）

        Returns:
            月报数据
        """
        if year is None:
            year = datetime.now().year
        if month is None:
            month = datetime.now().month

        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)

        try:
            async with AsyncSessionLocal() as session:
                # 查询月内的性能指标
                stmt = (
                    select(PerformanceMetric)
                    .where(PerformanceMetric.environment == environment)
                    .where(PerformanceMetric.timestamp >= start_date)
                    .where(PerformanceMetric.timestamp < end_date)
                )

                result = await session.execute(stmt)
                metrics = result.scalars().all()

                # 按周分组统计
                weekly_stats = {}
                for metric in metrics:
                    week_key = metric.timestamp.strftime("%Y-W%W")
                    if week_key not in weekly_stats:
                        weekly_stats[week_key] = {
                            "count": 0,
                            "total_p95": 0.0,
                        }

                    weekly_stats[week_key]["count"] += 1
                    if metric.p95_time_ms:
                        p95 = metric.p95_time_ms
                        weekly_stats[week_key]["total_p95"] += p95  # type: ignore[assignment]

                # 计算每周的平均值
                for week_key, stats in weekly_stats.items():
                    if stats["count"] > 0:
                        stats["avg_p95"] = stats["total_p95"] / stats["count"]

                # 查询月内的回归
                regression_stmt = (
                    select(PerformanceRegression)
                    .where(PerformanceRegression.environment == environment)
                    .where(PerformanceRegression.detected_at >= start_date)
                    .where(PerformanceRegression.detected_at < end_date)
                )

                regression_result = await session.execute(regression_stmt)
                regressions = regression_result.scalars().all()

                return {
                    "report_type": "monthly",
                    "year": year,
                    "month": month,
                    "environment": environment,
                    "summary": {
                        "total_tests": len(metrics),
                        "total_weeks": len(weekly_stats),
                        "total_regressions": len(regressions),
                    },
                    "weekly_stats": weekly_stats,
                    "regressions": [
                        {
                            "regression_id": r.regression_id,
                            "component": r.component,
                            "severity": r.severity,
                            "deviation": r.deviation,
                            "detected_at": r.detected_at.isoformat() if r.detected_at else None,
                        }
                        for r in regressions
                    ],
                }

        except Exception as e:
            logger.error(f"生成月报失败: {e}", exc_info=True)
            return {}

    async def generate_trend_analysis(
        self,
        component: str,
        metric_name: str = "p95_time_ms",
        days: int = 30,
        environment: str = "dev",
    ) -> Dict[str, Any]:
        """
        生成趋势分析报告

        Args:
            component: 组件名称
            metric_name: 指标名称
            days: 天数
            environment: 环境

        Returns:
            趋势分析数据
        """
        try:
            async with AsyncSessionLocal() as session:
                start_time = datetime.now() - timedelta(days=days)

                # 查询历史数据
                stmt = (
                    select(PerformanceMetric)
                    .where(PerformanceMetric.component == component)
                    .where(PerformanceMetric.environment == environment)
                    .where(PerformanceMetric.timestamp >= start_time)
                    .order_by(PerformanceMetric.timestamp)
                )

                result = await session.execute(stmt)
                metrics = result.scalars().all()

                # 提取指标值
                values = []
                for metric in metrics:
                    metric_value = getattr(metric, metric_name, None)
                    if metric_value:
                        values.append(
                            {
                                "timestamp": metric.timestamp.isoformat(),
                                "value": metric_value,
                            }
                        )

                # 计算趋势
                if len(values) >= 2:
                    first_value = values[0]["value"]
                    last_value = values[-1]["value"]

                    if first_value > 0:
                        change = (last_value - first_value) / first_value
                    else:
                        change = 0

                    trend_direction = "up" if change > 0 else "down" if change < 0 else "stable"
                else:
                    change = 0
                    trend_direction = "stable"

                return {
                    "component": component,
                    "metric_name": metric_name,
                    "days": days,
                    "environment": environment,
                    "data_points": len(values),
                    "trend_direction": trend_direction,
                    "change_percentage": change * 100,
                    "values": values,
                }

        except Exception as e:
            logger.error(f"生成趋势分析失败: {e}", exc_info=True)
            return {}


async def generate_performance_report(
    report_type: str = "daily",
    environment: str = "dev",
) -> Dict[str, Any]:
    """
    生成性能报告的便捷函数

    Args:
        report_type: 报告类型（daily, weekly, monthly）
        environment: 环境

    Returns:
        报告数据
    """
    generator = PerformanceReportGenerator()

    if report_type == "daily":
        return await generator.generate_daily_report(environment)
    elif report_type == "weekly":
        return await generator.generate_weekly_report(environment)
    elif report_type == "monthly":
        return await generator.generate_monthly_report(environment)
    else:
        logger.error(f"不支持的报告类型: {report_type}")
        return {}
