# -*- coding: utf-8 -*-
"""
Business Metrics Collector Module
业务指标收集模块

提供业务指标收集、计算和监控功能。
"""

import asyncio
import logging
import statistics
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class AlertEvent:
    """告警事件"""

    alert_id: str
    created_at: datetime
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    severity: str = "medium"
    auto_healed: bool = False
    assigned_to: Optional[str] = None


@dataclass
class BusinessMetrics:
    """业务指标"""

    alert_resolution_rate: float = 0.0
    mttr: float = 0.0  # Mean Time To Repair (seconds)
    mtta: float = 0.0  # Mean Time To Acknowledge (seconds)
    auto_heal_success_rate: float = 0.0
    total_alerts: int = 0
    active_alerts: int = 0
    resolved_alerts: int = 0
    auto_healed_alerts: int = 0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class BusinessMetricsCollector:
    """业务指标收集器"""

    def __init__(self, retention_days: int = 30):
        """
        初始化业务指标收集器

        Args:
            retention_days: 数据保留天数
        """
        self.retention_days = retention_days
        self._alert_events: Dict[str, AlertEvent] = {}
        self._metrics_history: List[BusinessMetrics] = []
        self._max_history_size = 1000

    def record_alert(self, alert_id: str, severity: str = "medium") -> AlertEvent:
        """
        记录告警事件

        Args:
            alert_id: 告警ID
            severity: 告警严重程度

        Returns:
            告警事件
        """
        event = AlertEvent(
            alert_id=alert_id, created_at=datetime.now(timezone.utc), severity=severity
        )
        self._alert_events[alert_id] = event
        logger.debug(f"Recorded alert event: {alert_id}")
        return event

    def acknowledge_alert(self, alert_id: str, acknowledged_by: Optional[str] = None):
        """
        确认告警

        Args:
            alert_id: 告警ID
            acknowledged_by: 确认人
        """
        if alert_id in self._alert_events:
            self._alert_events[alert_id].acknowledged_at = datetime.now(timezone.utc)
            self._alert_events[alert_id].assigned_to = acknowledged_by
            logger.debug(f"Acknowledged alert: {alert_id}")

    def resolve_alert(self, alert_id: str, auto_healed: bool = False):
        """
        解决告警

        Args:
            alert_id: 告警ID
            auto_healed: 是否自动修复
        """
        if alert_id in self._alert_events:
            self._alert_events[alert_id].resolved_at = datetime.now(timezone.utc)
            self._alert_events[alert_id].auto_healed = auto_healed
            logger.debug(f"Resolved alert: {alert_id} (auto_healed={auto_healed})")

    def calculate_metrics(self, time_window: timedelta = timedelta(hours=24)) -> BusinessMetrics:
        """
        计算业务指标

        Args:
            time_window: 时间窗口

        Returns:
            业务指标
        """
        now = datetime.now(timezone.utc)
        cutoff_time = now - time_window

        # 过滤时间窗口内的事件
        recent_events = [
            event for event in self._alert_events.values() if event.created_at >= cutoff_time
        ]

        if not recent_events:
            return BusinessMetrics()

        # 计算基础指标
        total_alerts = len(recent_events)
        active_alerts = len([e for e in recent_events if e.resolved_at is None])
        resolved_alerts = len([e for e in recent_events if e.resolved_at is not None])
        auto_healed_alerts = len([e for e in recent_events if e.auto_healed])

        # 计算告警解决率
        alert_resolution_rate = (resolved_alerts / total_alerts * 100) if total_alerts > 0 else 0.0

        # 计算MTTR (Mean Time To Repair)
        resolved_with_times = [e for e in recent_events if e.resolved_at is not None]
        repair_times = [
            (e.resolved_at - e.created_at).total_seconds()
            for e in resolved_with_times
            if e.resolved_at is not None
        ]
        mttr = statistics.mean(repair_times) if repair_times else 0.0

        # 计算MTTA (Mean Time To Acknowledge)
        acknowledged_with_times = [e for e in recent_events if e.acknowledged_at is not None]
        acknowledge_times = [
            (e.acknowledged_at - e.created_at).total_seconds()
            for e in acknowledged_with_times
            if e.acknowledged_at is not None
        ]
        mtta = statistics.mean(acknowledge_times) if acknowledge_times else 0.0

        # 计算自动修复成功率
        auto_heal_success_rate = (
            (auto_healed_alerts / resolved_alerts * 100) if resolved_alerts > 0 else 0.0
        )

        metrics = BusinessMetrics(
            alert_resolution_rate=alert_resolution_rate,
            mttr=mttr,
            mtta=mtta,
            auto_heal_success_rate=auto_heal_success_rate,
            total_alerts=total_alerts,
            active_alerts=active_alerts,
            resolved_alerts=resolved_alerts,
            auto_healed_alerts=auto_healed_alerts,
            timestamp=now,
        )

        # 保存到历史
        self._metrics_history.append(metrics)
        if len(self._metrics_history) > self._max_history_size:
            self._metrics_history = self._metrics_history[-self._max_history_size:]

        logger.info(f"Calculated business metrics: {metrics}")
        return metrics

    def get_metrics(self) -> BusinessMetrics:
        """
        获取当前指标

        Returns:
            当前业务指标
        """
        return self.calculate_metrics()

    def get_metrics_history(self, limit: int = 100) -> List[BusinessMetrics]:
        """
        获取指标历史

        Args:
            limit: 返回的历史记录数量

        Returns:
            指标历史记录
        """
        return self._metrics_history[-limit:]

    def get_metrics_trend(self, metric_name: str, hours: int = 24) -> List[float]:
        """
        获取指标趋势

        Args:
            metric_name: 指标名称
            hours: 时间范围（小时）

        Returns:
            指标趋势数据
        """
        now = datetime.now(timezone.utc)
        cutoff_time = now - timedelta(hours=hours)

        recent_metrics = [m for m in self._metrics_history if m.timestamp >= cutoff_time]

        return [getattr(m, metric_name, 0.0) for m in recent_metrics]

    def cleanup_old_data(self):
        """清理旧数据"""
        cutoff_time = datetime.now(timezone.utc) - timedelta(days=self.retention_days)

        # 清理旧的告警事件
        old_alerts = [
            alert_id
            for alert_id, event in self._alert_events.items()
            if event.created_at < cutoff_time
        ]

        for alert_id in old_alerts:
            del self._alert_events[alert_id]

        # 清理旧的指标历史
        old_metrics = [
            i for i, metrics in enumerate(self._metrics_history) if metrics.timestamp < cutoff_time
        ]

        for i in reversed(old_metrics):
            self._metrics_history.pop(i)

        logger.info(
            f"Cleaned up {len(old_alerts)} old alert events and {len(old_metrics)} old metrics"
        )

    def get_alerts_by_severity(self) -> Dict[str, int]:
        """
        按严重程度统计告警

        Returns:
            严重程度分布
        """
        severity_counts: Dict[str, int] = defaultdict(int)
        for event in self._alert_events.values():
            severity_counts[event.severity] += 1
        return dict(severity_counts)

    def get_top_assignees(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取处理告警最多的负责人

        Args:
            limit: 返回数量

        Returns:
            负责人列表
        """
        assignee_counts: Dict[str, int] = defaultdict(int)
        for event in self._alert_events.values():
            if event.assigned_to:
                assignee_counts[event.assigned_to] += 1

        sorted_assignees = sorted(assignee_counts.items(), key=lambda x: x[1], reverse=True)[:limit]

        return [{"assignee": name, "count": count} for name, count in sorted_assignees]


# 全局业务指标收集器实例
business_metrics_collector = BusinessMetricsCollector()


async def setup_business_metrics() -> Any:
    """
    设置业务指标监控

    Returns:
        设置结果
    """
    try:
        logger.info("Business metrics monitoring setup completed")

        return {
            "status": "success",
            "retention_days": business_metrics_collector.retention_days,
            "collector": "BusinessMetricsCollector",
        }

    except Exception as e:
        logger.error(f"Business metrics setup failed: {e}")
        return {"status": "error", "error": str(e)}


async def collect_business_metrics_task() -> Any:
    """
    定期收集业务指标的任务
    """
    while True:
        try:
            metrics = business_metrics_collector.get_metrics()
            logger.info(f"Collected business metrics: {metrics}")

            # 清理旧数据
            business_metrics_collector.cleanup_old_data()

            # 每小时收集一次
            await asyncio.sleep(3600)

        except Exception as e:
            logger.error(f"Business metrics collection failed: {e}")
            await asyncio.sleep(60)  # 出错后等待1分钟再重试
