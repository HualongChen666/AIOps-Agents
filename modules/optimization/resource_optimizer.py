# -*- coding: utf-8 -*-
"""
resource_optimizer.py
---------------------
成本优化 - 资源优化模块。

功能：
- 资源使用监控
- 资源利用率分析
- 自动扩缩容建议
- 成本估算
- 资源优化建议
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# 1️⃣ 资源类型枚举
# ----------------------------------------------------------------------
class ResourceType(Enum):
    """资源类型"""

    CPU = "cpu"
    MEMORY = "memory"
    STORAGE = "storage"
    NETWORK = "network"
    GPU = "gpu"


# ----------------------------------------------------------------------
# 2️⃣ 资源指标
# ----------------------------------------------------------------------
@dataclass
class ResourceMetric:
    """资源指标"""

    resource_type: ResourceType
    usage: float  # 使用量
    capacity: float  # 容量
    unit: str  # 单位
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def utilization(self) -> float:
        """利用率"""
        if self.capacity == 0:
            return 0.0
        return self.usage / self.capacity

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "resource_type": self.resource_type.value,
            "usage": self.usage,
            "capacity": self.capacity,
            "unit": self.unit,
            "utilization": self.utilization,
            "timestamp": self.timestamp.isoformat(),
        }


# ----------------------------------------------------------------------
# 3️⃣ 优化建议
# ----------------------------------------------------------------------
@dataclass
class OptimizationSuggestion:
    """优化建议"""

    resource_type: ResourceType
    suggestion_type: str  # "scale_up", "scale_down", "right_size", "terminate"
    current_value: float
    suggested_value: float
    reason: str
    estimated_savings: Optional[float] = None  # 预估节省（美元/月）

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "resource_type": self.resource_type.value,
            "suggestion_type": self.suggestion_type,
            "current_value": self.current_value,
            "suggested_value": self.suggested_value,
            "reason": self.reason,
            "estimated_savings": self.estimated_savings,
        }


# ----------------------------------------------------------------------
# 4️⃣ 资源监控器
# ----------------------------------------------------------------------
class ResourceMonitor:
    """资源监控器"""

    def __init__(self):
        self.metrics_history: Dict[str, List[ResourceMetric]] = {}
        self.current_metrics: Dict[str, ResourceMetric] = {}

    def record_metric(self, metric: ResourceMetric, resource_id: str = "default"):
        """
        记录资源指标

        Parameters
        ----------
        metric : ResourceMetric
            资源指标
        resource_id : str
            资源 ID
        """
        key = f"{resource_id}_{metric.resource_type.value}"

        if key not in self.metrics_history:
            self.metrics_history[key] = []

        self.metrics_history[key].append(metric)
        self.current_metrics[key] = metric

        # 保留最近 1000 条记录
        if len(self.metrics_history[key]) > 1000:
            self.metrics_history[key] = self.metrics_history[key][-1000:]

    def get_current_utilization(
        self,
        resource_id: str = "default",
    ) -> Dict[str, float]:
        """
        获取当前利用率

        Parameters
        ----------
        resource_id : str
            资源 ID

        Returns
        -------
        Dict[str, float]
            各资源类型的利用率
        """
        utilization = {}

        for resource_type in ResourceType:
            key = f"{resource_id}_{resource_type.value}"
            if key in self.current_metrics:
                utilization[resource_type.value] = self.current_metrics[key].utilization

        return utilization

    def get_average_utilization(
        self,
        resource_id: str = "default",
        hours: int = 24,
    ) -> Dict[str, float]:
        """
        获取平均利用率

        Parameters
        ----------
        resource_id : str
            资源 ID
        hours : int
            时间范围（小时）

        Returns
        -------
        Dict[str, float]
            各资源类型的平均利用率
        """
        cutoff = datetime.now() - timedelta(hours=hours)
        average_utilization = {}

        for resource_type in ResourceType:
            key = f"{resource_id}_{resource_type.value}"
            if key in self.metrics_history:
                recent_metrics = [m for m in self.metrics_history[key] if m.timestamp >= cutoff]

                if recent_metrics:
                    avg = sum(m.utilization for m in recent_metrics) / len(recent_metrics)
                    average_utilization[resource_type.value] = avg

        return average_utilization


# ----------------------------------------------------------------------
# 5️⃣ 资源优化器
# ----------------------------------------------------------------------
class ResourceOptimizer:
    """资源优化器"""

    def __init__(self, monitor: ResourceMonitor):
        """
        Parameters
        ----------
        monitor : ResourceMonitor
            资源监控器
        """
        self.monitor = monitor
        self.cost_per_unit: Dict[str, float] = {
            "cpu": 0.05,  # 每核心每小时
            "memory": 0.01,  # 每 GB 每小时
            "storage": 0.1,  # 每 GB 每月
            "network": 0.01,  # 每 GB 每小时
            "gpu": 1.0,  # 每个每小时
        }

    def analyze_optimization_opportunities(
        self,
        resource_id: str = "default",
    ) -> List[OptimizationSuggestion]:
        """
        分析优化机会

        Parameters
        ----------
        resource_id : str
            资源 ID

        Returns
        -------
        List[OptimizationSuggestion]
            优化建议列表
        """
        suggestions = []

        # 获取平均利用率
        avg_utilization = self.monitor.get_average_utilization(resource_id, hours=24)
        current_utilization = self.monitor.get_current_utilization(resource_id)

        for resource_type, utilization in avg_utilization.items():
            current = current_utilization.get(resource_type, 0)

            # 低利用率：建议缩容
            if utilization < 0.3:
                suggested = max(0.5, utilization * 1.5)  # 至少保留 50%
                savings = self._estimate_savings(resource_type, current, suggested)

                suggestions.append(
                    OptimizationSuggestion(
                        resource_type=ResourceType(resource_type),
                        suggestion_type="scale_down",
                        current_value=current,
                        suggested_value=suggested,
                        reason=f"Low average utilization ({utilization:.1%})",
                        estimated_savings=savings,
                    )
                )

            # 高利用率：建议扩容
            elif utilization > 0.8:
                suggested = min(1.0, utilization * 1.2)  # 最多 100%

                suggestions.append(
                    OptimizationSuggestion(
                        resource_type=ResourceType(resource_type),
                        suggestion_type="scale_up",
                        current_value=current,
                        suggested_value=suggested,
                        reason=f"High average utilization ({utilization:.1%})",
                    )
                )

            # 波动大：建议使用自动扩缩容
            elif self._is_volatile(resource_id, resource_type):
                suggestions.append(
                    OptimizationSuggestion(
                        resource_type=ResourceType(resource_type),
                        suggestion_type="auto_scaling",
                        current_value=current,
                        suggested_value=current,
                        reason="High utilization volatility, consider auto-scaling",
                    )
                )

        return suggestions

    def _is_volatile(
        self,
        resource_id: str,
        resource_type: str,
    ) -> bool:
        """检查利用率是否波动大"""
        key = f"{resource_id}_{resource_type}"

        if key not in self.monitor.metrics_history:
            return False

        metrics = self.monitor.metrics_history[key][-100:]  # 最近 100 条

        if len(metrics) < 10:
            return False

        utilizations = [m.utilization for m in metrics]

        # 计算标准差
        import statistics

        if len(utilizations) < 2:
            return False

        try:
            std_dev = statistics.stdev(utilizations)
            mean = statistics.mean(utilizations)

            # 变异系数 > 0.3 认为波动大
            return (std_dev / mean) > 0.3 if mean > 0 else False
        except BaseException:
            return False

    def _estimate_savings(
        self,
        resource_type: str,
        current_utilization: float,
        suggested_utilization: float,
    ) -> float:
        """估算节省"""
        cost_per_hour = self.cost_per_unit.get(resource_type, 0)

        # 简化计算：假设容量与利用率成反比
        reduction = (current_utilization - suggested_utilization) / current_utilization

        # 每月节省（730 小时）
        monthly_savings = reduction * cost_per_hour * 730

        return max(0, monthly_savings)

    def estimate_monthly_cost(
        self,
        resource_id: str = "default",
    ) -> Dict[str, float]:
        """
        估算月度成本

        Parameters
        ----------
        resource_id : str
            资源 ID

        Returns
        -------
        Dict[str, float]
            各资源类型的月度成本
        """
        current_utilization = self.monitor.get_current_utilization(resource_id)

        costs = {}
        total_cost = 0.0

        for resource_type, utilization in current_utilization.items():
            cost_per_hour = self.cost_per_unit.get(resource_type, 0)

            if resource_type == "storage":
                # 存储按月计算
                monthly_cost = cost_per_hour
            else:
                # 其他按小时计算
                monthly_cost = cost_per_hour * 730  # 30 天 * 24 小时

            costs[resource_type] = monthly_cost
            total_cost += monthly_cost

        costs["total"] = total_cost

        return costs

    def apply_optimization(
        self,
        suggestion: OptimizationSuggestion,
    ) -> bool:
        """
        应用优化建议

        Parameters
        ----------
        suggestion : OptimizationSuggestion
            优化建议

        Returns
        -------
        bool
            是否成功
        """
        # 简化实现：实际应调用云服务 API
        logger.info(f"Applying optimization: {  # noqa: E501
            suggestion.suggestion_type} for {suggestion.resource_type.value}")
        logger.info(f"  Current: {  # noqa: E501
            suggestion.current_value:.2f}, Suggested: {suggestion.suggested_value:.2f}")
        logger.info(f"  Reason: {suggestion.reason}")

        return True


# ----------------------------------------------------------------------
# 6️⃣ 成本分析器
# ----------------------------------------------------------------------
class CostAnalyzer:
    """成本分析器"""

    def __init__(self):
        self.cost_history: List[Dict[str, Any]] = []

    def record_cost(
        self,
        resource_id: str,
        cost: float,
        cost_breakdown: Dict[str, float],
    ):
        """
        记录成本

        Parameters
        ----------
        resource_id : str
            资源 ID
        cost : float
            总成本
        cost_breakdown : Dict[str, float]
            成本明细
        """
        self.cost_history.append(
            {
                "timestamp": datetime.now().isoformat(),
                "resource_id": resource_id,
                "cost": cost,
                "cost_breakdown": cost_breakdown,
            }
        )

    def get_cost_trend(
        self,
        resource_id: str,
        days: int = 30,
    ) -> Dict[str, Any]:
        """
        获取成本趋势

        Parameters
        ----------
        resource_id : str
            资源 ID
        days : int
            天数

        Returns
        -------
        Dict[str, Any]
            成本趋势分析
        """
        cutoff = datetime.now() - timedelta(days=days)

        recent_costs = [
            c
            for c in self.cost_history
            if c["resource_id"] == resource_id and datetime.fromisoformat(c["timestamp"]) >= cutoff
        ]

        if not recent_costs:
            return {}

        costs = [c["cost"] for c in recent_costs]

        return {
            "total_cost": sum(costs),
            "average_cost": sum(costs) / len(costs),
            "min_cost": min(costs),
            "max_cost": max(costs),
            "data_points": len(costs),
        }

    def identify_cost_anomalies(
        self,
        threshold: float = 2.0,
    ) -> List[Dict[str, Any]]:
        """
        识别成本异常

        Parameters
        ----------
        threshold : float
            异常阈值（标准差倍数）

        Returns
        -------
        List[Dict[str, Any]]
            异常列表
        """
        anomalies = []

        # 按资源 ID 分组
        by_resource: Dict[str, List[Dict[str, Any]]] = {}
        for cost_record in self.cost_history:
            rid = cost_record["resource_id"]
            if rid not in by_resource:
                by_resource[rid] = []
            by_resource[rid].append(cost_record)

        # 检测每个资源的异常
        for resource_id, records in by_resource.items():
            if len(records) < 10:
                continue

            costs = [r["cost"] for r in records]

            import statistics

            mean = statistics.mean(costs)
            std_dev = statistics.stdev(costs) if len(costs) > 1 else 0

            for record in records:
                cost = record["cost"]
                if std_dev > 0 and abs(cost - mean) > threshold * std_dev:
                    anomalies.append(
                        {
                            "resource_id": resource_id,
                            "timestamp": record["timestamp"],  # noqa: E501
                            "cost": cost,
                            "expected_range": (  # noqa: E501
                                f"{mean - threshold * std_dev:.2f} -"
                                f" {mean + threshold * std_dev:.2f}"
                            ),
                            "deviation": (cost - mean) / std_dev if std_dev > 0 else 0,
                        }
                    )

        return anomalies


# ----------------------------------------------------------------------
# 7️⃣ 工厂函数
# ----------------------------------------------------------------------
def create_resource_monitor() -> ResourceMonitor:
    """创建资源监控器"""
    return ResourceMonitor()


def create_resource_optimizer(monitor: ResourceMonitor) -> ResourceOptimizer:
    """创建资源优化器"""
    return ResourceOptimizer(monitor)


def create_cost_analyzer() -> CostAnalyzer:
    """创建成本分析器"""
    return CostAnalyzer()


# ----------------------------------------------------------------------
# 8️⃣ CLI 用于快速测试
# ----------------------------------------------------------------------
if __name__ == "__main__":  # pragma: no cover

    logging.basicConfig(level=logging.INFO)

    # 测试资源优化器
    logger.info("Testing resource optimizer")

    monitor = create_resource_monitor()
    optimizer = create_resource_optimizer(monitor)

    # 记录一些指标
    for i in range(100):
        monitor.record_metric(
            ResourceMetric(
                resource_type=ResourceType.CPU,
                usage=50 + i % 30,
                capacity=100,
                unit="cores",
            )
        )

        monitor.record_metric(
            ResourceMetric(
                resource_type=ResourceType.MEMORY,
                usage=40 + i % 20,
                capacity=80,
                unit="GB",
            )
        )

    # 分析优化机会
    suggestions = optimizer.analyze_optimization_opportunities()

    logger.info(f"Optimization suggestions: {len(suggestions)}")
    for suggestion in suggestions:
        logger.info(f"  - {suggestion.resource_type.value}: {suggestion.suggestion_type}")
        logger.info(f"    Reason: {suggestion.reason}")
        if suggestion.estimated_savings:
            logger.info(f"    Estimated savings: ${suggestion.estimated_savings:.2f}/month")

    # 估算成本
    costs = optimizer.estimate_monthly_cost()
    logger.info(f"Estimated monthly cost: ${costs.get('total', 0):.2f}")

    # 测试成本分析器
    logger.info("Testing cost analyzer")

    analyzer = create_cost_analyzer()

    for i in range(30):
        analyzer.record_cost(
            resource_id="server-1",
            cost=100 + i % 20,
            cost_breakdown={"cpu": 50, "memory": 30, "storage": 20},
        )

    trend = analyzer.get_cost_trend("server-1")
    logger.info(f"Cost trend: {trend}")

    anomalies = analyzer.identify_cost_anomalies()
    logger.info(f"Cost anomalies: {len(anomalies)}")

    logger.info("Test passed!")
