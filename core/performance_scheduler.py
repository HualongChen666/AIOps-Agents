# -*- coding: utf-8 -*-
"""
Performance Task Scheduler
性能任务调度器
"""

import logging
import os
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from core.performance_data_collector import PerformanceDataCollector
from core.performance_regression_detector import PerformanceRegressionDetector
from core.performance_report_generator import PerformanceReportGenerator

logger = logging.getLogger(__name__)


class PerformanceTaskScheduler:
    """性能任务调度器"""

    def __init__(self):
        """初始化任务调度器"""
        self.scheduler = AsyncIOScheduler()
        self.data_collector = PerformanceDataCollector()
        self.regression_detector = PerformanceRegressionDetector()
        self.report_generator = PerformanceReportGenerator()

    async def collect_daily_metrics(self):
        """每日采集性能指标（采集真实主机资源指标并落库）

        采集当前主机的 CPU / 内存 / 磁盘使用率（psutil 实测），写入
        ``performance_metrics`` 表，供后续回归检测与报表消费。
        """
        logger.info("开始每日性能指标采集")
        try:
            import psutil

            cpu = psutil.cpu_percent(interval=None)
            memory = psutil.virtual_memory().percent
            disk = psutil.disk_usage(os.path.abspath(os.sep)).percent

            async with PerformanceDataCollector() as collector:
                await collector.collect_metric(
                    {
                        "test_id": "system-daily",
                        "test_name": "daily host resource sample",
                        "test_type": "system",
                        "component": "host",
                        "operation": "resource_sample",
                        "mean_time_ms": 0.0,
                        "min_time_ms": 0.0,
                        "max_time_ms": 0.0,
                        "total_requests": 1,
                        "cpu_usage": cpu,
                        "memory_usage": memory,
                        "disk_io": disk,
                        "environment": os.getenv("ENVIRONMENT", "dev"),
                    }
                )
            logger.info(f"性能指标采集完成 | cpu={cpu}% memory={memory}% disk={disk}%")
        except Exception as e:
            logger.error(f"性能指标采集失败: {e}", exc_info=True)

    async def detect_daily_regressions(self):
        """每日检测性能回归"""
        logger.info("开始每日性能回归检测")
        try:
            # 获取活跃的回归
            regressions = await self.regression_detector.get_active_regressions()
            logger.info(f"当前活跃回归数量: {len(regressions)}")

            # 如果有新的回归，可以发送通知
            if regressions:
                logger.warning(f"检测到 {len(regressions)} 个活跃的性能回归")
                # 这里可以集成通知功能
        except Exception as e:
            logger.error(f"性能回归检测失败: {e}", exc_info=True)

    async def generate_daily_report(self):
        """每日生成性能报告"""
        logger.info("开始每日性能报告生成")
        try:
            report = await self.report_generator.generate_daily_report()
            logger.info(f"性能报告生成完成: {report.get('report_type')}")

            # 这里可以发送报告邮件
            # 或者保存到文件系统
        except Exception as e:
            logger.error(f"性能报告生成失败: {e}", exc_info=True)

    async def generate_weekly_report(self):
        """每周生成性能报告"""
        logger.info("开始每周性能报告生成")
        try:
            report = await self.report_generator.generate_weekly_report()
            logger.info(f"周报生成完成: {report.get('report_type')}")
        except Exception as e:
            logger.error(f"周报生成失败: {e}", exc_info=True)

    async def generate_monthly_report(self):
        """每月生成性能报告"""
        logger.info("开始每月性能报告生成")
        try:
            report = await self.report_generator.generate_monthly_report()
            logger.info(f"月报生成完成: {report.get('report_type')}")
        except Exception as e:
            logger.error(f"月报生成失败: {e}", exc_info=True)

    async def cleanup_old_metrics(self, retention_days: int = 30) -> int:
        """清理超过保留期的性能指标数据

        Args:
            retention_days: 保留天数，早于该窗口的 ``performance_metrics``
                记录会被真实删除。

        Returns:
            删除的记录数
        """
        logger.info("开始清理旧性能指标数据")
        try:
            from datetime import timedelta

            from sqlalchemy import delete

            from core.db_engine import AsyncSessionLocal
            from core.models import PerformanceMetric

            cutoff = datetime.now() - timedelta(days=retention_days)
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    delete(PerformanceMetric).where(PerformanceMetric.timestamp < cutoff)
                )
                await session.commit()
                deleted = int(result.rowcount or 0)
            logger.info(f"旧性能指标数据清理完成: 删除 {deleted} 条")
            return deleted
        except Exception as e:
            logger.error(f"数据清理失败: {e}", exc_info=True)
            return 0

    def setup_jobs(self):
        """设置定时任务"""
        # 每日凌晨2点采集性能指标
        self.scheduler.add_job(
            self.collect_daily_metrics,
            CronTrigger(hour=2, minute=0),
            id="collect_daily_metrics",
            name="每日性能指标采集",
            replace_existing=True,
        )

        # 每日凌晨3点检测性能回归
        self.scheduler.add_job(
            self.detect_daily_regressions,
            CronTrigger(hour=3, minute=0),
            id="detect_daily_regressions",
            name="每日性能回归检测",
            replace_existing=True,
        )

        # 每日凌晨4点生成日报
        self.scheduler.add_job(
            self.generate_daily_report,
            CronTrigger(hour=4, minute=0),
            id="generate_daily_report",
            name="每日性能报告生成",
            replace_existing=True,
        )

        # 每周一凌晨5点生成周报
        self.scheduler.add_job(
            self.generate_weekly_report,
            CronTrigger(day_of_week="mon", hour=5, minute=0),
            id="generate_weekly_report",
            name="每周性能报告生成",
            replace_existing=True,
        )

        # 每月1日凌晨6点生成月报
        self.scheduler.add_job(
            self.generate_monthly_report,
            CronTrigger(day=1, hour=6, minute=0),
            id="generate_monthly_report",
            name="每月性能报告生成",
            replace_existing=True,
        )

        # 每周日凌晨7点清理旧数据
        self.scheduler.add_job(
            self.cleanup_old_metrics,
            CronTrigger(day_of_week="sun", hour=7, minute=0),
            id="cleanup_old_metrics",
            name="清理旧性能指标数据",
            replace_existing=True,
        )

        logger.info("定时任务设置完成")

    def start(self):
        """启动调度器"""
        self.setup_jobs()
        self.scheduler.start()
        logger.info("性能任务调度器已启动")

    def shutdown(self):
        """关闭调度器"""
        self.scheduler.shutdown()
        logger.info("性能任务调度器已关闭")


# 全局实例
task_scheduler = PerformanceTaskScheduler()


def get_task_scheduler() -> PerformanceTaskScheduler:
    """获取任务调度器实例"""
    return task_scheduler
