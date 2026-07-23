# -*- coding: utf-8 -*-
"""
Performance Regression Detector
性能回归检测服务
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import select

from core.db_engine import AsyncSessionLocal
from core.models import (
    PerformanceBaseline,
    PerformanceRegression,
)

logger = logging.getLogger(__name__)


class PerformanceRegressionDetector:
    """性能回归检测器"""

    def __init__(self):
        """初始化性能回归检测器"""
        self.session = None

    async def __aenter__(self):
        """异步上下文管理器入口"""
        self.session = AsyncSessionLocal()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        if self.session:
            await self.session.close()

    async def detect_regression(
        self,
        component: str,
        current_value: float,
        metric_name: str = "p95_time_ms",
        environment: str = "dev",
    ) -> Optional[Dict[str, Any]]:
        """
        检测性能回归

        Args:
            component: 组件名称
            current_value: 当前性能值
            metric_name: 指标名称
            environment: 环境

        Returns:
            回归信息（如果检测到回归）
        """
        try:
            async with AsyncSessionLocal() as session:
                # 获取活跃的基准
                stmt = (
                    select(PerformanceBaseline)
                    .where(PerformanceBaseline.component == component)
                    .where(PerformanceBaseline.environment == environment)
                    .where(PerformanceBaseline.is_active)
                    .order_by(PerformanceBaseline.effective_from.desc())
                )

                result = await session.execute(stmt)
                baseline = result.scalar_one_or_none()

                if not baseline:
                    logger.warning(f"未找到组件 {component} 的性能基准")
                    return None

                # 获取基准值
                if metric_name == "p95_time_ms":
                    baseline_value = baseline.target_p95_ms
                elif metric_name == "p99_time_ms":
                    baseline_value = baseline.target_p99_ms
                elif metric_name == "throughput":
                    baseline_value = baseline.target_throughput
                else:
                    logger.warning(f"不支持的指标名称: {metric_name}")
                    return None

                if baseline_value is None:
                    logger.warning(f"基准中未定义指标 {metric_name}")
                    return None

                # 计算偏差
                if baseline_value > 0:
                    deviation = (current_value - baseline_value) / baseline_value
                else:
                    deviation = 0  # type: ignore[assignment]

                # 判断是否回归
                regression_threshold = baseline.regression_threshold or 0.1
                critical_threshold = baseline.critical_threshold or 0.3

                if abs(deviation) > regression_threshold:
                    # 检测到回归
                    severity = "critical" if abs(deviation) > critical_threshold else "warning"

                    # 创建回归记录
                    regression_id = f"regression-{component}-{datetime.now().timestamp()}"
                    regression = PerformanceRegression(
                        regression_id=regression_id,
                        component=component,
                        operation=baseline.operation,
                        baseline_value=baseline_value,
                        current_value=current_value,
                        deviation=deviation,
                        severity=severity,
                        environment=environment,
                    )

                    session.add(regression)
                    await session.commit()

                    logger.warning(
                        f"检测到性能回归: {component} - 偏差: {deviation:.2%} - 严重程度: {severity}"
                    )

                    return {
                        "regression_id": regression_id,
                        "component": component,
                        "baseline_value": baseline_value,
                        "current_value": current_value,
                        "deviation": deviation,
                        "severity": severity,
                        "detected_at": datetime.now().isoformat(),
                    }

                return None

        except Exception as e:
            logger.error(f"检测性能回归失败: {e}", exc_info=True)
            return None

    async def batch_detect_regressions(
        self,
        metrics_data: List[Dict[str, Any]],
        environment: str = "dev",
    ) -> List[Dict[str, Any]]:
        """
        批量检测性能回归

        Args:
            metrics_data: 性能指标数据列表
            environment: 环境

        Returns:
            回归信息列表
        """
        regressions = []

        for metric_data in metrics_data:
            component = metric_data.get("component")
            current_value = metric_data.get("p95_time_ms") or metric_data.get("mean_time_ms")

            if component and current_value:
                regression = await self.detect_regression(
                    component=component,
                    current_value=current_value,
                    metric_name="p95_time_ms",
                    environment=environment,
                )

                if regression:
                    regressions.append(regression)

        return regressions

    async def get_active_regressions(
        self,
        environment: Optional[str] = None,
        severity: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        获取活跃的性能回归

        Args:
            environment: 环境
            severity: 严重程度

        Returns:
            回归列表
        """
        try:
            async with AsyncSessionLocal() as session:
                stmt = select(PerformanceRegression).where(PerformanceRegression.status == "open")

                if environment:
                    stmt = stmt.where(PerformanceRegression.environment == environment)
                if severity:
                    stmt = stmt.where(PerformanceRegression.severity == severity)

                stmt = stmt.order_by(PerformanceRegression.detected_at.desc())

                result = await session.execute(stmt)
                regressions = result.scalars().all()

                return [
                    {
                        "regression_id": r.regression_id,
                        "component": r.component,
                        "operation": r.operation,
                        "baseline_value": r.baseline_value,
                        "current_value": r.current_value,
                        "deviation": r.deviation,
                        "severity": r.severity,
                        "detected_at": r.detected_at.isoformat() if r.detected_at else None,
                        "status": r.status,
                    }
                    for r in regressions
                ]

        except Exception as e:
            logger.error(f"获取活跃回归失败: {e}", exc_info=True)
            return []

    async def acknowledge_regression(
        self,
        regression_id: str,
        acknowledged_by: str,
    ) -> bool:
        """
        确认性能回归

        Args:
            regression_id: 回归ID
            acknowledged_by: 确认人

        Returns:
            是否成功
        """
        try:
            async with AsyncSessionLocal() as session:
                stmt = select(PerformanceRegression).where(
                    PerformanceRegression.regression_id == regression_id
                )
                result = await session.execute(stmt)
                regression = result.scalar_one_or_none()

                if regression:
                    regression.status = "acknowledged"  # type: ignore[assignment]
                    regression.acknowledged_by = acknowledged_by  # type: ignore[assignment]
                    regression.acknowledged_at = datetime.now()  # type: ignore[assignment]
                    await session.commit()

                    logger.info(f"性能回归已确认: {regression_id}")
                    return True

                return False

        except Exception as e:
            logger.error(f"确认性能回归失败: {e}", exc_info=True)
            return False

    async def resolve_regression(
        self,
        regression_id: str,
    ) -> bool:
        """
        解决性能回归

        Args:
            regression_id: 回归ID

        Returns:
            是否成功
        """
        try:
            async with AsyncSessionLocal() as session:
                stmt = select(PerformanceRegression).where(
                    PerformanceRegression.regression_id == regression_id
                )
                result = await session.execute(stmt)
                regression = result.scalar_one_or_none()

                if regression:
                    regression.status = "resolved"  # type: ignore[assignment]
                    regression.resolved_at = datetime.now()  # type: ignore[assignment]
                    await session.commit()

                    logger.info(f"性能回归已解决: {regression_id}")
                    return True

                return False

        except Exception as e:
            logger.error(f"解决性能回归失败: {e}", exc_info=True)
            return False


async def check_performance_regression(
    component: str,
    current_value: float,
    environment: str = "dev",
) -> Optional[Dict[str, Any]]:
    """
    检查性能回归的便捷函数

    Args:
        component: 组件名称
        current_value: 当前性能值
        environment: 环境

    Returns:
        回归信息（如果检测到回归）
    """
    detector = PerformanceRegressionDetector()
    return await detector.detect_regression(component, current_value, environment=environment)
