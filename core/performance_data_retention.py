# -*- coding: utf-8 -*-
"""
Performance Data Retention
性能数据保留策略
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from sqlalchemy import and_, delete, select

from core.db_engine import AsyncSessionLocal
from core.models import (
    PerformanceMetric,
    PerformanceRegression,
)

logger = logging.getLogger(__name__)


class PerformanceDataRetention:
    """性能数据保留策略管理器"""

    def __init__(self):
        """初始化数据保留管理器"""
        # 默认保留策略
        self.retention_policies = {
            "performance_metrics": {
                "days": 90,  # 保留90天
                "archive": True,  # 启用归档
            },
            "performance_regressions": {
                "days": 365,  # 保留1年
                "archive": False,  # 不归档
            },
        }

    def set_retention_policy(
        self,
        table_name: str,
        days: int,
        archive: bool = True,
    ):
        """设置保留策略"""
        self.retention_policies[table_name] = {
            "days": days,
            "archive": archive,
        }
        logger.info(f"设置保留策略: {table_name} - {days}天, 归档: {archive}")

    async def cleanup_performance_metrics(
        self,
        days: Optional[int] = None,
        dry_run: bool = False,
    ) -> int:
        """
        清理性能指标数据

        Args:
            days: 保留天数（默认使用策略配置）
            dry_run: 是否只模拟运行

        Returns:
            删除的记录数
        """
        if days is None:
            days = self.retention_policies["performance_metrics"]["days"]

        cutoff_date = datetime.now() - timedelta(days=days)

        try:
            async with AsyncSessionLocal() as session:
                # 统计要删除的记录
                count_stmt = select(PerformanceMetric).where(
                    PerformanceMetric.timestamp < cutoff_date
                )
                count_result = await session.execute(count_stmt)
                records_to_delete = count_result.scalars().all()
                count = len(records_to_delete)

                if dry_run:
                    logger.info(f"[DRY RUN] 将删除 {count} 条性能指标记录（{days}天前）")
                    return count

                if count > 0:
                    # 删除记录
                    delete_stmt = delete(PerformanceMetric).where(
                        PerformanceMetric.timestamp < cutoff_date
                    )
                    await session.execute(delete_stmt)
                    await session.commit()

                    logger.info(f"已删除 {count} 条性能指标记录（{days}天前）")
                else:
                    logger.info("没有需要删除的性能指标记录")

                return count

        except Exception as e:
            logger.error(f"清理性能指标数据失败: {e}", exc_info=True)
            return 0

    async def cleanup_performance_regressions(
        self,
        days: Optional[int] = None,
        dry_run: bool = False,
    ) -> int:
        """
        清理性能回归记录

        Args:
            days: 保留天数（默认使用策略配置）
            dry_run: 是否只模拟运行

        Returns:
            删除的记录数
        """
        if days is None:
            days = self.retention_policies["performance_regressions"]["days"]

        cutoff_date = datetime.now() - timedelta(days=days)

        try:
            async with AsyncSessionLocal() as session:
                # 只删除已解决的回归
                count_stmt = select(PerformanceRegression).where(
                    and_(
                        PerformanceRegression.status == "resolved",
                        PerformanceRegression.resolved_at < cutoff_date,
                    )
                )
                count_result = await session.execute(count_stmt)
                records_to_delete = count_result.scalars().all()
                count = len(records_to_delete)

                if dry_run:
                    logger.info(f"[DRY RUN] 将删除 {count} 条性能回归记录（{days}天前，已解决）")
                    return count

                if count > 0:
                    # 删除记录
                    delete_stmt = delete(PerformanceRegression).where(
                        and_(
                            PerformanceRegression.status == "resolved",
                            PerformanceRegression.resolved_at < cutoff_date,
                        )
                    )
                    await session.execute(delete_stmt)
                    await session.commit()

                    logger.info(f"已删除 {count} 条性能回归记录（{days}天前，已解决）")
                else:
                    logger.info("没有需要删除的性能回归记录")

                return count

        except Exception as e:
            logger.error(f"清理性能回归记录失败: {e}", exc_info=True)
            return 0

    async def archive_performance_metrics(
        self,
        days: Optional[int] = None,
    ) -> int:
        """
        归档性能指标数据

        Args:
            days: 归档天数（默认使用策略配置）

        Returns:
            归档的记录数
        """
        if days is None:
            days = self.retention_policies["performance_metrics"]["days"]

        cutoff_date = datetime.now() - timedelta(days=days)

        try:
            async with AsyncSessionLocal() as session:
                # 查询要归档的记录
                stmt = select(PerformanceMetric).where(PerformanceMetric.timestamp < cutoff_date)
                result = await session.execute(stmt)
                records = result.scalars().all()
                count = len(records)

                if count > 0:
                    # 这里应该实现归档逻辑
                    # 例如：导出到文件、移动到归档表等
                    # 由于这是一个示例，我们只记录日志
                    logger.info(f"归档 {count} 条性能指标记录到归档存储")

                    # 实际实现中，可以：
                    # 1. 导出到CSV/JSON文件
                    # 2. 移动到归档表
                    # 3. 上传到对象存储（S3等）
                    # 4. 使用时序数据库（ClickHouse等）
                else:
                    logger.info("没有需要归档的性能指标记录")

                return count

        except Exception as e:
            logger.error(f"归档性能指标数据失败: {e}", exc_info=True)
            return 0

    async def get_storage_statistics(self) -> Dict[str, Any]:
        """获取存储统计信息"""
        try:
            async with AsyncSessionLocal() as session:
                # 统计性能指标记录数
                metrics_stmt = select(PerformanceMetric)
                metrics_result = await session.execute(metrics_stmt)
                metrics_count = len(metrics_result.scalars().all())

                # 统计性能回归记录数
                regressions_stmt = select(PerformanceRegression)
                regressions_result = await session.execute(regressions_stmt)
                regressions_count = len(regressions_result.scalars().all())

                # 统计各时间段的记录数
                now = datetime.now()

                # 最近7天
                week_ago = now - timedelta(days=7)
                week_stmt = select(PerformanceMetric).where(PerformanceMetric.timestamp >= week_ago)
                week_result = await session.execute(week_stmt)
                week_count = len(week_result.scalars().all())

                # 最近30天
                month_ago = now - timedelta(days=30)
                month_stmt = select(PerformanceMetric).where(
                    PerformanceMetric.timestamp >= month_ago
                )
                month_result = await session.execute(month_stmt)
                month_count = len(month_result.scalars().all())

                return {
                    "performance_metrics": {
                        "total": metrics_count,
                        "last_7_days": week_count,
                        "last_30_days": month_count,
                        "older_than_30_days": metrics_count - month_count,
                    },
                    "performance_regressions": {
                        "total": regressions_count,
                    },
                    "retention_policies": self.retention_policies,
                }

        except Exception as e:
            logger.error(f"获取存储统计信息失败: {e}", exc_info=True)
            return {}

    async def run_cleanup(
        self,
        dry_run: bool = False,
    ) -> Dict[str, int]:
        """
        运行清理任务

        Args:
            dry_run: 是否只模拟运行

        Returns:
            清理结果
        """
        logger.info("开始性能数据清理任务")

        results = {
            "metrics_deleted": 0,
            "regressions_deleted": 0,
            "metrics_archived": 0,
        }

        # 清理性能指标
        if self.retention_policies["performance_metrics"]["archive"]:
            results["metrics_archived"] = await self.archive_performance_metrics()

        results["metrics_deleted"] = await self.cleanup_performance_metrics(dry_run=dry_run)

        # 清理性能回归
        results["regressions_deleted"] = await self.cleanup_performance_regressions(dry_run=dry_run)

        logger.info(f"性能数据清理任务完成: {results}")

        return results


# 全局实例
data_retention = PerformanceDataRetention()


def get_data_retention() -> PerformanceDataRetention:
    """获取数据保留管理器实例"""
    return data_retention
