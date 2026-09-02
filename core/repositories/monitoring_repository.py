# -*- coding: utf-8 -*-
"""
Monitoring Repository
=====================

Monitoring数据访问层，提供对Monitoring相关数据库模型的CRUD操作。

Features:
- Alert Rule CRUD operations
- Log Pattern CRUD operations
- Trace CRUD operations
- Service Call CRUD operations
- Metric CRUD operations
- Integration CRUD operations
- Dashboard CRUD operations
- Anomaly CRUD operations
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import (
    MonitoringAlertRule,
    MonitoringLogPattern,
    MonitoringTrace,
    MonitoringServiceCall,
    MonitoringMetric,
    MonitoringIntegration,
    MonitoringDashboard,
    MonitoringAnomaly,
)

logger = logging.getLogger(__name__)


class MonitoringRepository:
    """Monitoring数据访问层"""

    def __init__(self, db: AsyncSession):
        """
        初始化Monitoring Repository

        Args:
            db: 数据库会话
        """
        self.db = db

    # ==================== Alert Rule Operations ====================

    async def create_alert_rule(
        self,
        rule_id: str,
        rule_name: str,
        pattern: str,
        severity: str,
        status: str = "active",
        notification_channels: Optional[List[str]] = None,
        created_by: Optional[str] = None,
    ) -> MonitoringAlertRule:
        """
        创建告警规则

        Args:
            rule_id: 规则ID
            rule_name: 规则名称
            pattern: 匹配模式
            severity: 严重程度
            status: 状态
            notification_channels: 通知渠道
            created_by: 创建者

        Returns:
            创建的告警规则
        """
        alert_rule = MonitoringAlertRule(
            rule_id=rule_id,
            rule_name=rule_name,
            pattern=pattern,
            severity=severity,
            status=status,
            notification_channels=notification_channels,
            created_by=created_by,
        )

        self.db.add(alert_rule)
        await self.db.commit()
        await self.db.refresh(alert_rule)

        logger.info(f"Created alert rule: {rule_id}")
        return alert_rule

    async def get_alert_rule(self, rule_id: str) -> Optional[MonitoringAlertRule]:
        """
        获取告警规则

        Args:
            rule_id: 规则ID

        Returns:
            告警规则
        """
        result = await self.db.execute(
            select(MonitoringAlertRule).where(MonitoringAlertRule.rule_id == rule_id)
        )
        return result.scalar_one_or_none()

    async def get_all_alert_rules(
        self,
        status: Optional[str] = None,
        severity: Optional[str] = None,
    ) -> List[MonitoringAlertRule]:
        """
        获取所有告警规则

        Args:
            status: 状态过滤
            severity: 严重程度过滤

        Returns:
            告警规则列表
        """
        query = select(MonitoringAlertRule)

        if status:
            query = query.where(MonitoringAlertRule.status == status)
        if severity:
            query = query.where(MonitoringAlertRule.severity == severity)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def update_alert_rule(
        self,
        rule_id: str,
        rule_name: Optional[str] = None,
        pattern: Optional[str] = None,
        severity: Optional[str] = None,
        status: Optional[str] = None,
        notification_channels: Optional[List[str]] = None,
    ) -> Optional[MonitoringAlertRule]:
        """
        更新告警规则

        Args:
            rule_id: 规则ID
            rule_name: 规则名称
            pattern: 匹配模式
            severity: 严重程度
            status: 状态
            notification_channels: 通知渠道

        Returns:
            更新后的告警规则
        """
        update_data: Dict[str, Any] = {}
        if rule_name is not None:
            update_data["rule_name"] = rule_name
        if pattern is not None:
            update_data["pattern"] = pattern
        if severity is not None:
            update_data["severity"] = severity
        if status is not None:
            update_data["status"] = status
        if notification_channels is not None:
            update_data["notification_channels"] = notification_channels

        if update_data:
            await self.db.execute(
                update(MonitoringAlertRule)
                .where(MonitoringAlertRule.rule_id == rule_id)
                .values(**update_data)
            )
            await self.db.commit()

        return await self.get_alert_rule(rule_id)

    async def delete_alert_rule(self, rule_id: str) -> bool:
        """
        删除告警规则

        Args:
            rule_id: 规则ID

        Returns:
            是否删除成功
        """
        result = await self.db.execute(
            delete(MonitoringAlertRule).where(MonitoringAlertRule.rule_id == rule_id)
        )
        await self.db.commit()

        success = result.rowcount > 0
        if success:
            logger.info(f"Deleted alert rule: {rule_id}")

        return success

    async def increment_alert_rule_triggered_count(self, rule_id: str) -> bool:
        """
        增加告警规则触发次数

        Args:
            rule_id: 规则ID

        Returns:
            是否更新成功
        """
        await self.db.execute(
            update(MonitoringAlertRule)
            .where(MonitoringAlertRule.rule_id == rule_id)
            .values(
                triggered_count=MonitoringAlertRule.triggered_count + 1,
                last_triggered=datetime.now(),
            )
        )
        await self.db.commit()

        return True

    # ==================== Log Pattern Operations ====================

    async def create_log_pattern(
        self,
        pattern_id: str,
        pattern: str,
        severity: str,
        count: int = 0,
        frequency: float = 0.0,
    ) -> MonitoringLogPattern:
        """
        创建日志模式

        Args:
            pattern_id: 模式ID
            pattern: 模式
            severity: 严重程度
            count: 计数
            frequency: 频率

        Returns:
            创建的日志模式
        """
        log_pattern = MonitoringLogPattern(
            pattern_id=pattern_id,
            pattern=pattern,
            severity=severity,
            count=count,
            frequency=frequency,
        )

        self.db.add(log_pattern)
        await self.db.commit()
        await self.db.refresh(log_pattern)

        logger.info(f"Created log pattern: {pattern_id}")
        return log_pattern

    async def get_log_pattern(self, pattern_id: str) -> Optional[MonitoringLogPattern]:
        """
        获取日志模式

        Args:
            pattern_id: 模式ID

        Returns:
            日志模式
        """
        result = await self.db.execute(
            select(MonitoringLogPattern).where(MonitoringLogPattern.pattern_id == pattern_id)
        )
        return result.scalar_one_or_none()

    async def get_all_log_patterns(
        self,
        severity: Optional[str] = None,
    ) -> List[MonitoringLogPattern]:
        """
        获取所有日志模式

        Args:
            severity: 严重程度过滤

        Returns:
            日志模式列表
        """
        query = select(MonitoringLogPattern)

        if severity:
            query = query.where(MonitoringLogPattern.severity == severity)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def update_log_pattern(
        self,
        pattern_id: str,
        count: Optional[int] = None,
        frequency: Optional[float] = None,
        last_seen: Optional[datetime] = None,
    ) -> Optional[MonitoringLogPattern]:
        """
        更新日志模式

        Args:
            pattern_id: 模式ID
            count: 计数
            frequency: 频率
            last_seen: 最后出现时间

        Returns:
            更新后的日志模式
        """
        update_data: Dict[str, Any] = {}
        if count is not None:
            update_data["count"] = count
        if frequency is not None:
            update_data["frequency"] = frequency
        if last_seen is not None:
            update_data["last_seen"] = last_seen

        if update_data:
            await self.db.execute(
                update(MonitoringLogPattern)
                .where(MonitoringLogPattern.pattern_id == pattern_id)
                .values(**update_data)
            )
            await self.db.commit()

        return await self.get_log_pattern(pattern_id)

    # ==================== Trace Operations ====================

    async def create_trace(
        self,
        trace_id: str,
        service: str,
        start_time: datetime,
        duration_ms: int,
        span_count: int,
        root_span: Optional[str] = None,
    ) -> MonitoringTrace:
        """
        创建追踪

        Args:
            trace_id: 追踪ID
            service: 服务名称
            start_time: 开始时间
            duration_ms: 持续时间（毫秒）
            span_count: Span数量
            root_span: 根Span

        Returns:
            创建的追踪
        """
        trace = MonitoringTrace(
            trace_id=trace_id,
            service=service,
            start_time=start_time,
            duration_ms=duration_ms,
            span_count=span_count,
            root_span=root_span,
        )

        self.db.add(trace)
        await self.db.commit()
        await self.db.refresh(trace)

        logger.info(f"Created trace: {trace_id}")
        return trace

    async def get_trace(self, trace_id: str) -> Optional[MonitoringTrace]:
        """
        获取追踪

        Args:
            trace_id: 追踪ID

        Returns:
            追踪
        """
        result = await self.db.execute(
            select(MonitoringTrace).where(MonitoringTrace.trace_id == trace_id)
        )
        return result.scalar_one_or_none()

    async def get_traces_by_service(
        self,
        service: str,
        limit: int = 100,
    ) -> List[MonitoringTrace]:
        """
        根据服务获取追踪

        Args:
            service: 服务名称
            limit: 限制数量

        Returns:
            追踪列表
        """
        result = await self.db.execute(
            select(MonitoringTrace)
            .where(MonitoringTrace.service == service)
            .order_by(MonitoringTrace.start_time.desc())
            .limit(limit)
        )
        return result.scalars().all()

    # ==================== Service Call Operations ====================

    async def create_or_update_service_call(
        self,
        from_service: str,
        to_service: str,
        call_count: int = 1,
        avg_latency_ms: float = 0.0,
        error_rate: float = 0.0,
    ) -> MonitoringServiceCall:
        """
        创建或更新服务调用

        Args:
            from_service: 源服务
            to_service: 目标服务
            call_count: 调用次数
            avg_latency_ms: 平均延迟（毫秒）
            error_rate: 错误率

        Returns:
            服务调用记录
        """
        # 尝试获取现有记录
        result = await self.db.execute(
            select(MonitoringServiceCall).where(
                MonitoringServiceCall.from_service == from_service,
                MonitoringServiceCall.to_service == to_service,
            )
        )
        service_call = result.scalar_one_or_none()

        if service_call:
            # 更新现有记录
            service_call.call_count += call_count
            service_call.avg_latency_ms = (
                service_call.avg_latency_ms * 0.9 + avg_latency_ms * 0.1
            )  # 移动平均
            service_call.error_rate = (
                service_call.error_rate * 0.9 + error_rate * 0.1
            )  # 移动平均
        else:
            # 创建新记录
            service_call = MonitoringServiceCall(
                from_service=from_service,
                to_service=to_service,
                call_count=call_count,
                avg_latency_ms=avg_latency_ms,
                error_rate=error_rate,
            )
            self.db.add(service_call)

        await self.db.commit()
        await self.db.refresh(service_call)

        return service_call

    async def get_all_service_calls(self) -> List[MonitoringServiceCall]:
        """
        获取所有服务调用

        Returns:
            服务调用列表
        """
        result = await self.db.execute(select(MonitoringServiceCall))
        return result.scalars().all()

    # ==================== Metric Operations ====================

    async def create_metric(
        self,
        metric_name: str,
        metric_type: str,
        value: float,
        labels: Optional[Dict[str, str]] = None,
    ) -> MonitoringMetric:
        """
        创建指标

        Args:
            metric_name: 指标名称
            metric_type: 指标类型
            value: 指标值
            labels: 标签

        Returns:
            创建的指标
        """
        metric = MonitoringMetric(
            metric_name=metric_name,
            metric_type=metric_type,
            value=value,
            labels=labels,
        )

        self.db.add(metric)
        await self.db.commit()
        await self.db.refresh(metric)

        return metric

    async def get_metrics(
        self,
        metric_name: Optional[str] = None,
        limit: int = 100,
    ) -> List[MonitoringMetric]:
        """
        获取指标

        Args:
            metric_name: 指标名称过滤
            limit: 限制数量

        Returns:
            指标列表
        """
        query = select(MonitoringMetric)

        if metric_name:
            query = query.where(MonitoringMetric.metric_name == metric_name)

        query = query.order_by(MonitoringMetric.timestamp.desc()).limit(limit)

        result = await self.db.execute(query)
        return result.scalars().all()

    # ==================== Integration Operations ====================

    async def create_integration(
        self,
        integration_id: str,
        integration_name: str,
        integration_type: str,
        config: Dict[str, Any],
        created_by: Optional[str] = None,
    ) -> MonitoringIntegration:
        """
        创建集成

        Args:
            integration_id: 集成ID
            integration_name: 集成名称
            integration_type: 集成类型
            config: 配置
            created_by: 创建者

        Returns:
            创建的集成
        """
        integration = MonitoringIntegration(
            integration_id=integration_id,
            integration_name=integration_name,
            integration_type=integration_type,
            config=config,
            created_by=created_by,
        )

        self.db.add(integration)
        await self.db.commit()
        await self.db.refresh(integration)

        logger.info(f"Created integration: {integration_id}")
        return integration

    async def get_integration(self, integration_id: str) -> Optional[MonitoringIntegration]:
        """
        获取集成

        Args:
            integration_id: 集成ID

        Returns:
            集成
        """
        result = await self.db.execute(
            select(MonitoringIntegration).where(
                MonitoringIntegration.integration_id == integration_id
            )
        )
        return result.scalar_one_or_none()

    async def get_all_integrations(
        self,
        integration_type: Optional[str] = None,
        enabled: Optional[bool] = None,
    ) -> List[MonitoringIntegration]:
        """
        获取所有集成

        Args:
            integration_type: 集成类型过滤
            enabled: 启用状态过滤

        Returns:
            集成列表
        """
        query = select(MonitoringIntegration)

        if integration_type:
            query = query.where(MonitoringIntegration.integration_type == integration_type)
        if enabled is not None:
            query = query.where(MonitoringIntegration.enabled == enabled)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def update_integration(
        self,
        integration_id: str,
        config: Optional[Dict[str, Any]] = None,
        enabled: Optional[bool] = None,
        health_status: Optional[str] = None,
    ) -> Optional[MonitoringIntegration]:
        """
        更新集成

        Args:
            integration_id: 集成ID
            config: 配置
            enabled: 启用状态
            health_status: 健康状态

        Returns:
            更新后的集成
        """
        update_data: Dict[str, Any] = {}
        if config is not None:
            update_data["config"] = config
        if enabled is not None:
            update_data["enabled"] = enabled
        if health_status is not None:
            update_data["health_status"] = health_status
            update_data["last_health_check"] = datetime.now()

        if update_data:
            await self.db.execute(
                update(MonitoringIntegration)
                .where(MonitoringIntegration.integration_id == integration_id)
                .values(**update_data)
            )
            await self.db.commit()

        return await self.get_integration(integration_id)

    # ==================== Dashboard Operations ====================

    async def create_dashboard(
        self,
        dashboard_id: str,
        dashboard_name: str,
        panels: List[Dict[str, Any]],
        refresh_interval: str = "30s",
        time_range: str = "1h",
        created_by: Optional[str] = None,
    ) -> MonitoringDashboard:
        """
        创建仪表板

        Args:
            dashboard_id: 仪表板ID
            dashboard_name: 仪表板名称
            panels: 面板配置
            refresh_interval: 刷新间隔
            time_range: 时间范围
            created_by: 创建者

        Returns:
            创建的仪表板
        """
        dashboard = MonitoringDashboard(
            dashboard_id=dashboard_id,
            dashboard_name=dashboard_name,
            panels=panels,
            refresh_interval=refresh_interval,
            time_range=time_range,
            created_by=created_by,
        )

        self.db.add(dashboard)
        await self.db.commit()
        await self.db.refresh(dashboard)

        logger.info(f"Created dashboard: {dashboard_id}")
        return dashboard

    async def get_dashboard(self, dashboard_id: str) -> Optional[MonitoringDashboard]:
        """
        获取仪表板

        Args:
            dashboard_id: 仪表板ID

        Returns:
            仪表板
        """
        result = await self.db.execute(
            select(MonitoringDashboard).where(
                MonitoringDashboard.dashboard_id == dashboard_id
            )
        )
        return result.scalar_one_or_none()

    async def get_all_dashboards(
        self,
        enabled: Optional[bool] = None,
    ) -> List[MonitoringDashboard]:
        """
        获取所有仪表板

        Args:
            enabled: 启用状态过滤

        Returns:
            仪表板列表
        """
        query = select(MonitoringDashboard)

        if enabled is not None:
            query = query.where(MonitoringDashboard.enabled == enabled)

        result = await self.db.execute(query)
        return result.scalars().all()

    # ==================== Anomaly Operations ====================

    async def create_anomaly(
        self,
        anomaly_id: str,
        metric_name: str,
        service_name: str,
        anomaly_score: float,
        expected_value: float,
        actual_value: float,
        is_anomaly: bool,
    ) -> MonitoringAnomaly:
        """
        创建异常

        Args:
            anomaly_id: 异常ID
            metric_name: 指标名称
            service_name: 服务名称
            anomaly_score: 异常分数
            expected_value: 期望值
            actual_value: 实际值
            is_anomaly: 是否异常

        Returns:
            创建的异常
        """
        anomaly = MonitoringAnomaly(
            anomaly_id=anomaly_id,
            metric_name=metric_name,
            service_name=service_name,
            anomaly_score=anomaly_score,
            expected_value=expected_value,
            actual_value=actual_value,
            is_anomaly=is_anomaly,
        )

        self.db.add(anomaly)
        await self.db.commit()
        await self.db.refresh(anomaly)

        logger.info(f"Created anomaly: {anomaly_id}")
        return anomaly

    async def get_anomaly(self, anomaly_id: str) -> Optional[MonitoringAnomaly]:
        """
        获取异常

        Args:
            anomaly_id: 异常ID

        Returns:
            异常
        """
        result = await self.db.execute(
            select(MonitoringAnomaly).where(MonitoringAnomaly.anomaly_id == anomaly_id)
        )
        return result.scalar_one_or_none()

    async def get_all_anomalies(
        self,
        is_anomaly: Optional[bool] = None,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> List[MonitoringAnomaly]:
        """
        获取所有异常

        Args:
            is_anomaly: 是否异常过滤
            status: 状态过滤
            limit: 限制数量

        Returns:
            异常列表
        """
        query = select(MonitoringAnomaly)

        if is_anomaly is not None:
            query = query.where(MonitoringAnomaly.is_anomaly == is_anomaly)
        if status:
            query = query.where(MonitoringAnomaly.status == status)

        query = query.order_by(MonitoringAnomaly.detected_at.desc()).limit(limit)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def resolve_anomaly(self, anomaly_id: str) -> bool:
        """
        解决异常

        Args:
            anomaly_id: 异常ID

        Returns:
            是否解决成功
        """
        await self.db.execute(
            update(MonitoringAnomaly)
            .where(MonitoringAnomaly.anomaly_id == anomaly_id)
            .values(status="resolved", resolved_at=datetime.now())
        )
        await self.db.commit()

        logger.info(f"Resolved anomaly: {anomaly_id}")
        return True
