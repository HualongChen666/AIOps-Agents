# -*- coding: utf-8 -*-
"""
GraphQL Schema and Implementation
GraphQL Schema和实现

使用strawberry-graphql实现完整的GraphQL端点。
"""

import logging
from datetime import datetime, timezone
from typing import List, Optional

import strawberry
from strawberry import field, mutation, type
from strawberry.fastapi import GraphQLRouter

logger = logging.getLogger(__name__)


@type
class Alert:
    """告警类型"""

    id: str
    severity: str
    message: str
    source: str
    created_at: datetime
    status: str


@type
class Metric:
    """指标类型"""

    id: str
    name: str
    value: float
    unit: str
    timestamp: datetime
    source: str


@type
class HealthStatus:
    """健康状态类型"""

    status: str
    database: str
    redis: str
    message: str


@type
class Query:
    """GraphQL查询"""

    @field
    async def alerts(
        self, limit: int = 10, offset: int = 0, severity: Optional[str] = None
    ) -> List[Alert]:
        """
        查询告警列表

        Args:
            limit: 限制数量
            offset: 偏移量
            severity: 严重程度过滤

        Returns:
            告警列表
        """
        try:
            from core.alert_service import AlertService

            service = AlertService()

            # 获取告警 (sync call, no offset support)
            alerts_data = service.get_alerts(limit=limit)

            # 转换为GraphQL类型
            alerts = []
            for alert in alerts_data.get("alerts", []):
                alerts.append(
                    Alert(
                        id=str(alert.get("id", "")),
                        severity=alert.get("severity", "unknown"),
                        message=alert.get("message", ""),
                        source=alert.get("source", ""),
                        created_at=alert.get("created_at", datetime.now(timezone.utc)),
                        status=alert.get("status", "active"),
                    )
                )

            return alerts
        except Exception as e:
            logger.error(f"Failed to query alerts: {e}")
            return []

    @field
    async def metrics(self, limit: int = 10, source: Optional[str] = None) -> List[Metric]:
        """
        查询指标列表

        Args:
            limit: 限制数量
            source: 来源过滤

        Returns:
            指标列表
        """
        try:
            from core.collector import collect_all

            metrics_data = collect_all()

            # 转换为GraphQL类型
            metrics = []
            for name, value in metrics_data.items():
                if source is None or name.startswith(source):
                    metrics.append(
                        Metric(
                            id=name,
                            name=name,
                            value=float(value) if isinstance(value, (int, float)) else 0.0,
                            unit="",
                            timestamp=datetime.now(timezone.utc),
                            source=source or "system",
                        )
                    )

            return metrics[:limit]
        except Exception as e:
            logger.error(f"Failed to query metrics: {e}")
            return []

    @field
    async def health(self) -> HealthStatus:
        """
        查询健康状态

        Returns:
            健康状态
        """
        try:
            from core.module_health_check import check_all_modules_health

            health_data = await check_all_modules_health()

            return HealthStatus(
                status="healthy",
                database=health_data.get("database", {}).get("status", "unknown"),
                redis=health_data.get("redis", {}).get("status", "unknown"),
                message="System is operational",
            )
        except Exception as e:
            logger.error(f"Failed to query health: {e}")
            return HealthStatus(
                status="unhealthy", database="unknown", redis="unknown", message=str(e)
            )


@type
class Mutation:
    """GraphQL变更"""

    @mutation
    async def create_alert(self, severity: str, message: str, source: str) -> Alert:
        """创建告警。"""
        try:
            from core.alert_service import alert_service

            created = await alert_service.create_alert(severity, message, source)
            return Alert(
                id=created["id"],
                severity=created["severity"],
                message=created["message"],
                source=created["source"],
                created_at=created["created_at"],
                status=created["status"],
            )
        except Exception as e:
            logger.error(f"Failed to create alert: {e}")
            raise Exception(f"Failed to create alert: {str(e)}")

    @mutation
    async def acknowledge_alert(self, alert_id: str) -> Alert:
        """确认告警。"""
        try:
            from core.alert_service import alert_service

            found = await alert_service.acknowledge_alert(alert_id)
            if not found:
                raise ValueError(f"Alert not found: {alert_id}")

            for alert in alert_history:
                if alert.get("id") == alert_id:
                    return Alert(
                        id=alert["id"],
                        severity=alert.get("severity", "unknown"),
                        message=alert.get("message", ""),
                        source=alert.get("source", ""),
                        created_at=alert.get("created_at", datetime.now(timezone.utc)),
                        status=alert.get("status", "acknowledged"),
                    )
            raise ValueError(f"Alert not found after acknowledgement: {alert_id}")
        except Exception as e:
            logger.error(f"Failed to acknowledge alert: {e}")
            raise Exception(f"Failed to acknowledge alert: {str(e)}")


# 创建GraphQL Schema
schema = strawberry.Schema(query=Query, mutation=Mutation)

# 创建 GraphQL 路由
# strawberry-graphql GraphQLRouter 需要显式 path，否则 FastAPI 会因空路径报错
graphql_app = GraphQLRouter(schema, path="/graphql", graphql_ide="graphiql")
