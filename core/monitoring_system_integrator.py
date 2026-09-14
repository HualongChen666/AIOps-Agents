# -*- coding: utf-8 -*-
"""监控系统集成适配器

统一Prometheus、Loki、Tempo的监控数据，实现统一监控面板和告警
"""

import logging
import operator as _operator
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from core.monitoring_infrastructure import get_monitoring_infrastructure

_logger = logging.getLogger(__name__)


# 条件比较运算符映射（严格解析，避免 eval 注入）。
_COMPARISON_OPERATORS = {
    "<=": _operator.le,
    ">=": _operator.ge,
    "==": _operator.eq,
    "!=": _operator.ne,
    "<": _operator.lt,
    ">": _operator.gt,
}

# 形如 ``metric_name > 80`` 的原子条件。
_ATOMIC_CONDITION_RE = re.compile(
    r"^\s*([A-Za-z_][A-Za-z0-9_.]*)\s*(<=|>=|==|!=|<|>)\s*(-?\d+(?:\.\d+)?)\s*$"
)


class AlertSeverity(str, Enum):
    """告警严重级别"""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertStatus(str, Enum):
    """告警状态"""

    ACTIVE = "active"
    RESOLVED = "resolved"
    ACKNOWLEDGED = "acknowledged"
    SILENCED = "silenced"


@dataclass
class UnifiedAlert:
    """统一告警"""

    alert_id: str
    alert_name: str
    severity: AlertSeverity
    status: AlertStatus
    message: str
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)
    starts_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    ends_at: Optional[datetime] = None
    source: str = "prometheus"


@dataclass
class DashboardConfig:
    """仪表盘配置"""

    dashboard_id: str
    dashboard_name: str
    panels: List[Dict[str, Any]]
    refresh_interval: str = "30s"
    time_range: str = "1h"


class MonitoringSystemIntegrator:
    """监控系统集成器"""

    def __init__(self):
        """初始化监控系统集成器"""
        self.monitoring = get_monitoring_infrastructure()
        self.alerts: Dict[str, UnifiedAlert] = {}
        self.dashboards: Dict[str, DashboardConfig] = {}
        self.alert_rules: Dict[str, Dict[str, Any]] = {}

        self._setup_default_dashboards()
        self._setup_default_alert_rules()

    def _setup_default_dashboards(self):
        """设置默认仪表盘"""
        # 系统监控仪表盘
        system_dashboard = DashboardConfig(
            dashboard_id="system_overview",
            dashboard_name="System Overview",
            panels=[
                {
                    "id": "cpu_usage",
                    "title": "CPU Usage",
                    "type": "graph",
                    "targets": ["system_cpu_percent"],
                },
                {
                    "id": "memory_usage",
                    "title": "Memory Usage",
                    "type": "graph",
                    "targets": ["system_memory_percent"],
                },
                {
                    "id": "disk_usage",
                    "title": "Disk Usage",
                    "type": "graph",
                    "targets": ["system_disk_percent"],
                },
            ],
        )
        self.dashboards[system_dashboard.dashboard_id] = system_dashboard

        # API监控仪表盘
        api_dashboard = DashboardConfig(
            dashboard_id="api_overview",
            dashboard_name="API Overview",
            panels=[
                {
                    "id": "api_requests",
                    "title": "API Requests",
                    "type": "graph",
                    "targets": ["api_requests_total"],
                },
                {
                    "id": "api_latency",
                    "title": "API Latency",
                    "type": "graph",
                    "targets": ["api_request_duration"],
                },
                {
                    "id": "api_errors",
                    "title": "API Errors",
                    "type": "graph",
                    "targets": ["api_requests_total"],
                },
            ],
        )
        self.dashboards[api_dashboard.dashboard_id] = api_dashboard

        _logger.info(f"Default dashboards configured: {len(self.dashboards)}")

    def _setup_default_alert_rules(self):
        """设置默认告警规则"""
        # CPU告警规则
        cpu_alert_rule = {
            "alert_id": "high_cpu_usage",
            "alert_name": "High CPU Usage",
            "severity": AlertSeverity.WARNING,
            "condition": "system_cpu_percent > 80",
            "duration": "5m",
            "message": "CPU usage is above 80% for 5 minutes",
        }
        self.alert_rules[cpu_alert_rule["alert_id"]] = cpu_alert_rule

        # 内存告警规则
        memory_alert_rule = {
            "alert_id": "high_memory_usage",
            "alert_name": "High Memory Usage",
            "severity": AlertSeverity.WARNING,
            "condition": "system_memory_percent > 85",
            "duration": "5m",
            "message": "Memory usage is above 85% for 5 minutes",
        }
        self.alert_rules[memory_alert_rule["alert_id"]] = memory_alert_rule

        # API错误告警规则
        api_error_alert_rule = {
            "alert_id": "high_api_error_rate",
            "alert_name": "High API Error Rate",
            "severity": AlertSeverity.ERROR,
            "condition": "api_error_rate > 0.05",
            "duration": "5m",
            "message": "API error rate is above 5% for 5 minutes",
        }
        self.alert_rules[api_error_alert_rule["alert_id"]] = api_error_alert_rule

        _logger.info(f"Default alert rules configured: {len(self.alert_rules)}")

    def create_alert(self, alert: UnifiedAlert):
        """创建告警"""
        self.alerts[alert.alert_id] = alert

        # 记录告警指标
        self.monitoring.metrics_collector.increment_counter(
            "monitoring_alerts_total",
            labels={"severity": alert.severity.value, "status": alert.status.value},
        )

        _logger.info(f"Alert created: {alert.alert_name} ({alert.severity.value})")

    def resolve_alert(self, alert_id: str):
        """解决告警"""
        if alert_id in self.alerts:
            self.alerts[alert_id].status = AlertStatus.RESOLVED
            self.alerts[alert_id].ends_at = datetime.now(timezone.utc)

            self.monitoring.metrics_collector.increment_counter("monitoring_alerts_resolved_total")

            _logger.info(f"Alert resolved: {alert_id}")

    def acknowledge_alert(self, alert_id: str, user: str):
        """确认告警"""
        if alert_id in self.alerts:
            self.alerts[alert_id].status = AlertStatus.ACKNOWLEDGED
            self.alerts[alert_id].annotations["acknowledged_by"] = user
            self.alerts[alert_id].annotations["acknowledged_at"] = datetime.now(
                timezone.utc
            ).isoformat()

            _logger.info(f"Alert acknowledged: {alert_id} by {user}")

    def get_active_alerts(self) -> List[UnifiedAlert]:
        """获取活跃告警"""
        return [alert for alert in self.alerts.values() if alert.status == AlertStatus.ACTIVE]

    def get_alert_by_id(self, alert_id: str) -> Optional[UnifiedAlert]:
        """根据ID获取告警"""
        return self.alerts.get(alert_id)

    def evaluate_alert_rules(self, metrics: Dict[str, float]):
        """评估告警规则

        真正解析每条规则的 ``condition`` 表达式（如 ``system_memory_percent > 85``、
        ``api_error_rate > 0.05``）并对传入的 ``metrics`` 求值；命中即创建告警。
        支持 ``&&`` / ``and``、``||`` / ``or`` 组合以及 ``< <= > >= == !=`` 比较符，
        而非仅处理 ``cpu`` 关键词。
        """
        for rule_id, rule in self.alert_rules.items():
            try:
                condition = str(rule.get("condition", ""))
                if not condition:
                    continue

                if not self._evaluate_condition(condition, metrics):
                    continue

                summary = self._describe_condition(condition, metrics)
                alert = UnifiedAlert(
                    alert_id=rule_id,
                    alert_name=rule["alert_name"],
                    severity=rule["severity"],
                    status=AlertStatus.ACTIVE,
                    message=f"{rule['message']} ({summary})" if summary else rule["message"],
                )
                self.create_alert(alert)
            except Exception as e:
                _logger.error(f"Error evaluating alert rule {rule_id}: {e}")

    @staticmethod
    def _evaluate_condition(condition: str, metrics: Dict[str, float]) -> bool:
        """对单个条件表达式求值（不依赖 eval）。

        组合逻辑优先级：``||``/``or`` 低于 ``&&``/``and``。
        """
        expr = condition.strip()

        for sep in ("||", " or "):
            if sep in expr:
                return any(
                    MonitoringSystemIntegrator._evaluate_condition(part, metrics)
                    for part in expr.split(sep)
                )

        for sep in ("&&", " and "):
            if sep in expr:
                return all(
                    MonitoringSystemIntegrator._evaluate_condition(part, metrics)
                    for part in expr.split(sep)
                )

        match = _ATOMIC_CONDITION_RE.match(expr)
        if match is None:
            _logger.warning(f"Unsupported alert condition (skipped): {condition!r}")
            return False

        metric_name, op_symbol, threshold_str = match.group(1), match.group(2), match.group(3)

        # 指标缺失时不命中（无法判定满足阈值）。
        if metric_name not in metrics:
            return False

        try:
            value = float(metrics[metric_name])
            threshold = float(threshold_str)
        except (TypeError, ValueError):
            return False

        return _COMPARISON_OPERATORS[op_symbol](value, threshold)

    @staticmethod
    def _describe_condition(condition: str, metrics: Dict[str, float]) -> str:
        """生成用于告警消息的条件摘要，例如 ``system_memory_percent=90.0``。"""
        names = _ATOMIC_CONDITION_RE.findall(condition)
        if names:
            metric_name = names[0][0]
            if metric_name in metrics:
                return f"{metric_name}={metrics[metric_name]}"
        return condition

    def get_dashboard(self, dashboard_id: str) -> Optional[DashboardConfig]:
        """获取仪表盘配置"""
        return self.dashboards.get(dashboard_id)

    def get_all_dashboards(self) -> List[DashboardConfig]:
        """获取所有仪表盘"""
        return list(self.dashboards.values())

    def create_dashboard(self, dashboard: DashboardConfig):
        """创建仪表盘"""
        self.dashboards[dashboard.dashboard_id] = dashboard
        _logger.info(f"Dashboard created: {dashboard.dashboard_name}")

    def get_monitoring_summary(self) -> Dict[str, Any]:
        """获取监控摘要"""
        active_alerts = self.get_active_alerts()

        return {
            "total_alerts": len(self.alerts),
            "active_alerts": len(active_alerts),
            "critical_alerts": len(
                [a for a in active_alerts if a.severity == AlertSeverity.CRITICAL]
            ),
            "error_alerts": len([a for a in active_alerts if a.severity == AlertSeverity.ERROR]),
            "warning_alerts": len(
                [a for a in active_alerts if a.severity == AlertSeverity.WARNING]
            ),
            "total_dashboards": len(self.dashboards),
            "total_alert_rules": len(self.alert_rules),
            "monitoring_status": self.monitoring.get_monitoring_status(),
        }


# 全局实例
monitoring_system_integrator = MonitoringSystemIntegrator()


def get_monitoring_system_integrator() -> MonitoringSystemIntegrator:
    """获取监控系统集成器实例"""
    return monitoring_system_integrator
