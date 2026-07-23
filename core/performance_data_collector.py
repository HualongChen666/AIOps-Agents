# -*- coding: utf-8 -*-
"""
Performance Data Collector
性能数据采集服务
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import select

from core.db_engine import AsyncSessionLocal
from core.models import (
    PerformanceMetric,
)

logger = logging.getLogger(__name__)


class PerformanceDataCollector:
    """性能数据采集器"""

    def __init__(self):
        """初始化性能数据采集器"""
        self.session = None

    async def __aenter__(self):
        """异步上下文管理器入口"""
        self.session = AsyncSessionLocal()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        if self.session:
            await self.session.close()

    async def collect_metric(self, metric_data: Dict[str, Any]) -> str:
        """
        采集性能指标

        Args:
            metric_data: 性能指标数据

        Returns:
            记录ID
        """
        try:
            async with AsyncSessionLocal() as session:
                metric = PerformanceMetric(
                    test_id=metric_data.get("test_id"),
                    test_name=metric_data.get("test_name"),
                    test_type=metric_data.get("test_type"),
                    component=metric_data.get("component"),
                    operation=metric_data.get("operation"),
                    mean_time_ms=metric_data.get("mean_time_ms"),
                    min_time_ms=metric_data.get("min_time_ms"),
                    max_time_ms=metric_data.get("max_time_ms"),
                    p50_time_ms=metric_data.get("p50_time_ms"),
                    p95_time_ms=metric_data.get("p95_time_ms"),
                    p99_time_ms=metric_data.get("p99_time_ms"),
                    std_dev_ms=metric_data.get("std_dev_ms"),
                    throughput_ops=metric_data.get("throughput_ops"),
                    qps=metric_data.get("qps"),
                    error_rate=metric_data.get("error_rate"),
                    error_count=metric_data.get("error_count"),
                    total_requests=metric_data.get("total_requests", 1),
                    cpu_usage=metric_data.get("cpu_usage"),
                    memory_usage=metric_data.get("memory_usage"),
                    disk_io=metric_data.get("disk_io"),
                    network_io=metric_data.get("network_io"),
                    token_usage=metric_data.get("token_usage"),
                    cost_usd=metric_data.get("cost_usd"),
                    model_name=metric_data.get("model_name"),
                    data_volume=metric_data.get("data_volume"),
                    pool_size=metric_data.get("pool_size"),
                    connection_count=metric_data.get("connection_count"),
                    environment=metric_data.get("environment", "dev"),
                    git_commit=metric_data.get("git_commit"),
                    git_branch=metric_data.get("git_branch"),
                    metadata=metric_data.get("metadata"),
                )

                session.add(metric)
                await session.commit()
                await session.refresh(metric)

                logger.info(f"性能指标已采集: {metric.test_id} - {metric.component}")
                return str(metric.id)

        except Exception as e:
            logger.error(f"采集性能指标失败: {e}", exc_info=True)
            raise

    async def collect_batch_metrics(self, metrics_data: List[Dict[str, Any]]) -> List[str]:
        """
        批量采集性能指标

        Args:
            metrics_data: 性能指标数据列表

        Returns:
            记录ID列表
        """
        try:
            async with AsyncSessionLocal() as session:
                metrics = []
                for metric_data in metrics_data:
                    metric = PerformanceMetric(
                        test_id=metric_data.get("test_id"),
                        test_name=metric_data.get("test_name"),
                        test_type=metric_data.get("test_type"),
                        component=metric_data.get("component"),
                        operation=metric_data.get("operation"),
                        mean_time_ms=metric_data.get("mean_time_ms"),
                        min_time_ms=metric_data.get("min_time_ms"),
                        max_time_ms=metric_data.get("max_time_ms"),
                        p50_time_ms=metric_data.get("p50_time_ms"),
                        p95_time_ms=metric_data.get("p95_time_ms"),
                        p99_time_ms=metric_data.get("p99_time_ms"),
                        std_dev_ms=metric_data.get("std_dev_ms"),
                        throughput_ops=metric_data.get("throughput_ops"),
                        qps=metric_data.get("qps"),
                        error_rate=metric_data.get("error_rate"),
                        error_count=metric_data.get("error_count"),
                        total_requests=metric_data.get("total_requests", 1),
                        cpu_usage=metric_data.get("cpu_usage"),
                        memory_usage=metric_data.get("memory_usage"),
                        disk_io=metric_data.get("disk_io"),
                        network_io=metric_data.get("network_io"),
                        token_usage=metric_data.get("token_usage"),
                        cost_usd=metric_data.get("cost_usd"),
                        model_name=metric_data.get("model_name"),
                        data_volume=metric_data.get("data_volume"),
                        pool_size=metric_data.get("pool_size"),
                        connection_count=metric_data.get("connection_count"),
                        environment=metric_data.get("environment", "dev"),
                        git_commit=metric_data.get("git_commit"),
                        git_branch=metric_data.get("git_branch"),
                        metadata=metric_data.get("metadata"),
                    )
                    metrics.append(metric)

                session.add_all(metrics)
                await session.commit()

                logger.info(f"批量采集性能指标: {len(metrics)} 条")
                return [str(m.id) for m in metrics]

        except Exception as e:
            logger.error(f"批量采集性能指标失败: {e}", exc_info=True)
            raise

    async def query_metrics(
        self,
        component: Optional[str] = None,
        test_type: Optional[str] = None,
        environment: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        查询性能指标

        Args:
            component: 组件名称
            test_type: 测试类型
            environment: 环境
            start_time: 开始时间
            end_time: 结束时间
            limit: 返回数量限制

        Returns:
            性能指标列表
        """
        try:
            async with AsyncSessionLocal() as session:
                stmt = select(PerformanceMetric)

                if component:
                    stmt = stmt.where(PerformanceMetric.component == component)
                if test_type:
                    stmt = stmt.where(PerformanceMetric.test_type == test_type)
                if environment:
                    stmt = stmt.where(PerformanceMetric.environment == environment)
                if start_time:
                    stmt = stmt.where(PerformanceMetric.timestamp >= start_time)
                if end_time:
                    stmt = stmt.where(PerformanceMetric.timestamp <= end_time)

                stmt = stmt.order_by(PerformanceMetric.timestamp.desc()).limit(limit)

                result = await session.execute(stmt)
                metrics = result.scalars().all()

                return [
                    {
                        "id": m.id,
                        "test_id": m.test_id,
                        "test_name": m.test_name,
                        "test_type": m.test_type,
                        "component": m.component,
                        "operation": m.operation,
                        "mean_time_ms": m.mean_time_ms,
                        "p95_time_ms": m.p95_time_ms,
                        "p99_time_ms": m.p99_time_ms,
                        "throughput_ops": m.throughput_ops,
                        "error_rate": m.error_rate,
                        "timestamp": m.timestamp.isoformat() if m.timestamp else None,
                    }
                    for m in metrics
                ]

        except Exception as e:
            logger.error(f"查询性能指标失败: {e}", exc_info=True)
            return []

    async def get_aggregated_metrics(
        self,
        component: str,
        metric_name: str,
        interval: str = "hour",
        hours: int = 24,
    ) -> List[Dict[str, Any]]:
        """
        获取聚合性能指标

        Args:
            component: 组件名称
            metric_name: 指标名称（p95_time_ms, throughput等）
            interval: 聚合间隔（hour, day）
            hours: 时间范围（小时）

        Returns:
            聚合指标列表
        """
        try:
            async with AsyncSessionLocal() as session:
                from datetime import timedelta

                start_time = datetime.now() - timedelta(hours=hours)

                # 简化实现：直接查询并按时间分组
                stmt = (
                    select(PerformanceMetric)
                    .where(PerformanceMetric.component == component)
                    .where(PerformanceMetric.timestamp >= start_time)
                    .order_by(PerformanceMetric.timestamp)
                )

                result = await session.execute(stmt)
                metrics = result.scalars().all()

                # 按时间分组聚合
                aggregated = {}
                for m in metrics:
                    if interval == "hour":
                        time_key = m.timestamp.strftime("%Y-%m-%d %H:00")
                    else:
                        time_key = m.timestamp.strftime("%Y-%m-%d")

                    if time_key not in aggregated:
                        aggregated[time_key] = {
                            "timestamp": time_key,
                            "count": 0,
                            "sum": 0.0,
                        }

                    metric_value = getattr(m, metric_name, 0)
                    if metric_value:
                        aggregated[time_key]["count"] += 1
                        aggregated[time_key]["sum"] += metric_value

                # 计算平均值
                result_list = []
                for time_key, data in aggregated.items():
                    if data["count"] > 0:
                        result_list.append(
                            {
                                "timestamp": time_key,
                                "value": data["sum"] / data["count"],
                                "count": data["count"],
                            }
                        )

                return sorted(result_list, key=lambda x: x["timestamp"])

        except Exception as e:
            logger.error(f"获取聚合性能指标失败: {e}", exc_info=True)
            return []


async def collect_performance_test_result(test_result: Dict[str, Any]) -> str:
    """
    采集性能测试结果的便捷函数

    Args:
        test_result: 测试结果数据

    Returns:
        记录ID
    """
    collector = PerformanceDataCollector()
    return await collector.collect_metric(test_result)
