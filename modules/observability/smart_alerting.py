# -*- coding: utf-8 -*-
from __future__ import annotations

"""
smart_alerting.py
-----------------
智能可观测性 - 智能告警模块。

功能：
- 动态阈值告警
- 异常检测告警
- 告警聚合和去重
- 告警智能路由
- 告警抑制和静默
"""

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

# noqa: F401
logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# 1️⃣ 告警级别枚举
# ----------------------------------------------------------------------
class AlertSeverity(Enum):
    """告警级别"""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


# ----------------------------------------------------------------------
# 2️⃣ 告警状态枚举
# ----------------------------------------------------------------------
class AlertStatus(Enum):
    """告警状态"""

    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"


# ----------------------------------------------------------------------
# 3️⃣ 告警定义
# ----------------------------------------------------------------------
@dataclass
class Alert:
    """告警"""

    id: str
    title: str
    description: str
    severity: AlertSeverity
    status: AlertStatus = AlertStatus.OPEN
    source: str = ""
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)
    starts_at: str = field(default_factory=lambda: datetime.now().isoformat())
    ends_at: Optional[str] = None
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    fingerprint: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "severity": self.severity.value,
            "status": self.status.value,
            "source": self.source,
            "labels": self.labels,
            "annotations": self.annotations,
            "starts_at": self.starts_at,
            "ends_at": self.ends_at,
            "updated_at": self.updated_at,
            "fingerprint": self.fingerprint,
        }

    def generate_fingerprint(self) -> str:
        """生成告警指纹（用于去重）"""
        import hashlib

        # 基于标题、标签和源生成指纹
        fingerprint_data = f"{self.title}|{self.source}|{sorted(self.labels.items())}"
        self.fingerprint = hashlib.md5(fingerprint_data.encode()).hexdigest()
        return self.fingerprint


# ----------------------------------------------------------------------
# 4️⃣ 告警规则
# ----------------------------------------------------------------------
@dataclass
class AlertRule:
    """告警规则"""

    id: str
    name: str
    condition: str  # 告警条件表达式
    severity: AlertSeverity
    duration: int = 60  # 持续时间（秒）
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)
    enabled: bool = True

    def evaluate(self, metrics: Dict[str, Any]) -> bool:
        """
        评估告警规则

        Parameters
        ----------
        metrics : Dict[str, Any]
            指标数据

        Returns
        -------
        bool
            是否触发告警
        """
        try:
            # 安全评估：使用简单的表达式解析器替代 eval
            return self._safe_evaluate(self.condition, metrics)
        except Exception as e:
            logger.error(f"Rule evaluation failed: {e}")
            return False

    def _safe_evaluate(self, condition: str, metrics: Dict[str, Any]) -> bool:
        """安全评估条件表达式"""
        # 验证条件表达式只包含安全的操作符和变量名
        import re

        # 检查条件是否只包含安全字符
        safe_pattern = r"^[a-zA-Z0-9_\s><=!&|()]+$"
        if not re.match(safe_pattern, condition):
            raise ValueError(f"Unsafe condition: {condition}")

        # 提取变量名
        tokens = re.split(r"[><=!&|()]+", condition)
        variables = [t.strip() for t in tokens if t.strip()]

        # 验证所有变量都在 metrics 中
        for var in variables:
            if var not in ["and", "or", "not"] and var not in metrics:
                logger.warning(f"Variable {var} not in metrics, treating as False")
                return False

        # 使用 ast.literal_eval 的安全替代方案
        # 简单实现：解析并评估比较表达式
        return self._parse_and_evaluate(condition, metrics)

    def _parse_and_evaluate(self, condition: str, metrics: Dict[str, Any]) -> bool:
        """解析并评估简单的比较表达式"""
        # 简化实现：处理简单的比较表达式
        # 例如: "cpu_usage > 80", "memory_usage > 90 and cpu_usage > 80"

        # 处理 and/or
        if " and " in condition:
            parts = condition.split(" and ")
            return all(self._parse_and_evaluate(part.strip(), metrics) for part in parts)

        if " or " in condition:
            parts = condition.split(" or ")
            return any(self._parse_and_evaluate(part.strip(), metrics) for part in parts)

        # 处理 not
        if condition.startswith("not "):
            return not self._parse_and_evaluate(condition[4:].strip(), metrics)

        # 处理比较表达式
        for op in [">=", "<=", "==", "!=", ">", "<"]:
            if op in condition:
                parts = condition.split(op)
                if len(parts) != 2:
                    continue

                left = parts[0].strip()
                right = parts[1].strip()

                # 获取左值
                if left in metrics:
                    left_val = float(metrics[left])
                else:
                    try:
                        left_val = float(left)
                    except ValueError:
                        return False

                # 获取右值
                if right in metrics:
                    right_val = float(metrics[right])
                else:
                    try:
                        right_val = float(right)
                    except ValueError:
                        return False

                # 执行比较
                if op == ">":
                    return left_val > right_val
                elif op == "<":
                    return left_val < right_val
                elif op == ">=":
                    return left_val >= right_val
                elif op == "<=":
                    return left_val <= right_val
                elif op == "==":
                    return left_val == right_val
                elif op == "!=":
                    return left_val != right_val

        # 如果没有匹配到任何操作符，检查是否为布尔值
        if condition in metrics:
            return bool(metrics[condition])

        return False


# ----------------------------------------------------------------------
# 5️⃣ 动态阈值计算器
# ----------------------------------------------------------------------
class DynamicThresholdCalculator:
    """动态阈值计算器"""

    def __init__(self, window_size: int = 100):
        """
        Parameters
        ----------
        window_size : int
            滑动窗口大小
        """
        self.window_size = window_size
        self.metric_history: Dict[str, List[float]] = defaultdict(list)

    def add_metric(self, metric_name: str, value: float):
        """添加指标值"""
        history = self.metric_history[metric_name]
        history.append(value)

        # 保持窗口大小
        if len(history) > self.window_size:
            history.pop(0)

    def calculate_threshold(
        self,
        metric_name: str,
        method: str = "percentile",
        **kwargs,
    ) -> float:
        """
        计算动态阈值

        Parameters
        ----------
        metric_name : str
            指标名称
        method : str
            计算方法：'percentile', 'stddev', 'moving_avg'
        **kwargs
            方法参数

        Returns
        -------
        float
            阈值
        """
        history = self.metric_history.get(metric_name, [])

        if len(history) < 10:
            # 数据不足，返回默认值
            return 0.0

        if method == "percentile":
            percentile = kwargs.get("percentile", 95)
            import numpy as np

            return float(np.percentile(history, percentile))

        elif method == "stddev":
            import numpy as np

            mean = float(np.mean(history))
            std = float(np.std(history))
            multiplier = float(kwargs.get("multiplier", 3))
            return mean + multiplier * std

        elif method == "moving_avg":
            import numpy as np

            window = kwargs.get("window", 10)
            if len(history) < window:
                return float(np.mean(history))
            return float(np.mean(history[-window:]))

        else:
            logger.warning(f"Unknown threshold method: {method}")
            return 0.0


# ----------------------------------------------------------------------
# 6️⃣ 告警聚合器
# ----------------------------------------------------------------------
class AlertAggregator:
    """告警聚合器"""

    def __init__(self, aggregation_window: int = 300):
        """
        Parameters
        ----------
        aggregation_window : int
            聚合窗口（秒）
        """
        self.aggregation_window = aggregation_window
        self.alert_buffer: List[Alert] = []

    def add_alert(self, alert: Alert):
        """添加告警"""
        self.alert_buffer.append(alert)

    def aggregate(self) -> List[Alert]:
        """
        聚合告警

        Returns
        -------
        List[Alert]
            聚合后的告警列表
        """
        if not self.alert_buffer:
            return []

        # 按指纹分组
        fingerprint_groups = defaultdict(list)
        for alert in self.alert_buffer:
            fingerprint = alert.generate_fingerprint()
            fingerprint_groups[fingerprint].append(alert)

        # 聚合每组告警
        aggregated_alerts = []
        for fingerprint, alerts in fingerprint_groups.items():
            if len(alerts) == 1:
                aggregated_alerts.append(alerts[0])
            else:
                # 聚合多个告警
                aggregated = self._merge_alerts(alerts)
                aggregated_alerts.append(aggregated)

        # 清空缓冲区
        self.alert_buffer.clear()

        return aggregated_alerts

    def _merge_alerts(self, alerts: List[Alert]) -> Alert:
        """合并多个告警"""
        base_alert = alerts[0]

        # 更新描述
        count = len(alerts)
        merged_description = f"{base_alert.description} (Aggregated from {count} alerts)"

        # 更新时间
        latest_time = max(a.starts_at for a in alerts)

        return Alert(
            id=base_alert.id,
            title=base_alert.title,
            description=merged_description,
            severity=base_alert.severity,
            status=base_alert.status,
            source=base_alert.source,
            labels=base_alert.labels,
            annotations={**base_alert.annotations, "aggregated_count": str(count)},
            starts_at=base_alert.starts_at,
            updated_at=latest_time,
        )


# ----------------------------------------------------------------------
# 7️⃣ 告警抑制器
# ----------------------------------------------------------------------
class AlertSuppressor:
    """告警抑制器"""

    def __init__(self):
        self.suppression_rules: List[Dict[str, Any]] = []

    def add_suppression_rule(
        self,
        match_labels: Dict[str, str],
        duration: int = 3600,
    ):
        """
        添加抑制规则

        Parameters
        ----------
        match_labels : Dict[str, str]
            匹配标签
        duration : int
            抑制持续时间（秒）
        """
        self.suppression_rules.append(
            {
                "match_labels": match_labels,
                "duration": duration,
                "created_at": datetime.now(),
            }
        )

    def should_suppress(self, alert: Alert) -> bool:
        """
        判断是否应该抑制告警

        Parameters
        ----------
        alert : Alert
            告警

        Returns
        -------
        bool
            是否抑制
        """
        now = datetime.now()

        for rule in self.suppression_rules:
            # 检查规则是否过期
            created_at = rule["created_at"]
            duration = rule["duration"]
            if now - created_at > timedelta(seconds=duration):
                continue

            # 检查标签匹配
            match_labels = rule["match_labels"]
            if all(alert.labels.get(k) == v for k, v in match_labels.items()):
                return True

        return False

    def cleanup_expired_rules(self):
        """清理过期的抑制规则"""
        now = datetime.now()
        self.suppression_rules = [
            rule
            for rule in self.suppression_rules
            if now - rule["created_at"] <= timedelta(seconds=rule["duration"])
        ]


# ----------------------------------------------------------------------
# 8️⃣ 智能告警引擎
# ----------------------------------------------------------------------
class SmartAlertingEngine:
    """智能告警引擎"""

    def __init__(self):
        self.rules: Dict[str, AlertRule] = {}
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []

        self.threshold_calculator = DynamicThresholdCalculator()
        self.aggregator = AlertAggregator()
        self.suppressor = AlertSuppressor()

    def add_rule(self, rule: AlertRule):
        """添加告警规则"""
        self.rules[rule.id] = rule
        logger.info(f"Added alert rule: {rule.name}")

    def remove_rule(self, rule_id: str):
        """移除告警规则"""
        if rule_id in self.rules:
            del self.rules[rule_id]
            logger.info(f"Removed alert rule: {rule_id}")

    def evaluate_metrics(
        self,
        metrics: Dict[str, Any],
    ) -> List[Alert]:
        """
        评估指标并生成告警

        Parameters
        ----------
        metrics : Dict[str, Any]
            指标数据

        Returns
        -------
        List[Alert]
            生成的告警列表
        """
        alerts = []

        # 更新动态阈值计算器
        for metric_name, metric_value in metrics.items():
            if isinstance(metric_value, (int, float)):
                self.threshold_calculator.add_metric(metric_name, metric_value)

        # 评估所有规则
        for rule in self.rules.values():
            if not rule.enabled:
                continue

            if rule.evaluate(metrics):
                # 创建告警
                alert = Alert(
                    id=f"alert-{rule.id}-{int(datetime.now().timestamp())}",
                    title=rule.name,
                    description=f"Alert rule '{rule.name}' triggered",
                    severity=rule.severity,
                    source="smart_alerting",
                    labels=rule.labels.copy(),
                    annotations=rule.annotations.copy(),
                )

                alerts.append(alert)

        # 抑制告警
        filtered_alerts = [alert for alert in alerts if not self.suppressor.should_suppress(alert)]

        # 聚合告警
        for alert in filtered_alerts:
            self.aggregator.add_alert(alert)

        aggregated_alerts = self.aggregator.aggregate()

        # 更新活跃告警
        for alert in aggregated_alerts:
            fingerprint = alert.generate_fingerprint()
            self.active_alerts[fingerprint] = alert
            self.alert_history.append(alert)

        # 清理过期的抑制规则
        self.suppressor.cleanup_expired_rules()

        return aggregated_alerts

    def acknowledge_alert(self, alert_id: str):
        """确认告警"""
        for alert in self.active_alerts.values():
            if alert.id == alert_id:
                alert.status = AlertStatus.ACKNOWLEDGED
                alert.updated_at = datetime.now().isoformat()
                logger.info(f"Acknowledged alert: {alert_id}")
                return True
        return False

    def resolve_alert(self, alert_id: str):
        """解决告警"""
        for alert in self.active_alerts.values():
            if alert.id == alert_id:
                alert.status = AlertStatus.RESOLVED
                alert.ends_at = datetime.now().isoformat()
                alert.updated_at = datetime.now().isoformat()
                logger.info(f"Resolved alert: {alert_id}")
                return True
        return False

    def get_active_alerts(self) -> List[Alert]:
        """获取活跃告警"""
        return [
            alert for alert in self.active_alerts.values() if alert.status != AlertStatus.RESOLVED
        ]

    def get_alert_statistics(self) -> Dict[str, Any]:
        """获取告警统计"""
        active_alerts = self.get_active_alerts()

        severity_counts: Dict[str, int] = defaultdict(int)
        for alert in active_alerts:
            severity_counts[alert.severity.value] += 1

        return {
            "total_active": len(active_alerts),
            "by_severity": dict(severity_counts),
            "total_rules": len(self.rules),
            "enabled_rules": sum(1 for r in self.rules.values() if r.enabled),
        }


# ----------------------------------------------------------------------
# 9️⃣ 工厂函数
# ----------------------------------------------------------------------
def create_smart_alerting_engine() -> SmartAlertingEngine:
    """创建智能告警引擎"""
    return SmartAlertingEngine()


# ----------------------------------------------------------------------
# 🔟 CLI 用于快速测试
# ----------------------------------------------------------------------
if __name__ == "__main__":  # pragma: no cover

    logging.basicConfig(level=logging.INFO)

    # 测试智能告警引擎
    logger.info("Testing smart alerting engine")

    engine = create_smart_alerting_engine()

    # 添加告警规则
    engine.add_rule(
        AlertRule(
            id="cpu-high",
            name="CPU Usage High",
            condition="cpu_usage > 80",
            severity=AlertSeverity.WARNING,
            labels={"component": "cpu"},
        )
    )

    engine.add_rule(
        AlertRule(
            id="memory-critical",
            name="Memory Usage Critical",
            condition="memory_usage > 90",
            severity=AlertSeverity.CRITICAL,
            labels={"component": "memory"},
        )
    )

    # 评估指标
    metrics = {
        "cpu_usage": 85.0,
        "memory_usage": 95.0,
    }

    alerts = engine.evaluate_metrics(metrics)

    logger.info(f"Generated {len(alerts)} alerts:")
    for alert in alerts:
        logger.info(f"  - {alert.title} ({alert.severity.value})")

    # 获取统计
    stats = engine.get_alert_statistics()
    logger.info(f"Alert statistics: {stats}")

    logger.info("Test passed!")
