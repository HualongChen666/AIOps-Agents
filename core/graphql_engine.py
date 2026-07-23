# -*- coding: utf-8 -*-
"""
GraphQL 引擎（基于 strawberry）
提供实时查询能力，当前实现以下 Query：
- hostHealth(host_id: ID!): HostHealth
- metrics(limit: Int = 20): List[Metric]
- incidents(host_id: ID, limit: Int = 20): List[Incident]

后续可在此文件中继续扩展 Types、Mutations、Subscriptions。
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import List, Optional

import strawberry
from strawberry.exceptions import GraphQLError

from core.db_engine import get_incident_history  # type: ignore[attr-defined]
from core.mcp_tools import get_host_health
from core.metrics_history import get_metrics_history  # type: ignore[attr-defined]

_logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# GraphQL Types
# ----------------------------------------------------------------------
@strawberry.type
class HostHealth:
    host_id: str
    status: str
    last_checked: datetime
    details: Optional[str] = None


@strawberry.type
class Metric:
    timestamp: datetime
    name: str
    value: float
    host_id: Optional[str] = None


@strawberry.type
class Incident:
    incident_id: str
    host_id: Optional[str]
    alert_id: Optional[str]
    script_key: Optional[str]
    created_at: datetime
    status: str
    severity: Optional[str] = None


# ----------------------------------------------------------------------
# Resolvers
# ----------------------------------------------------------------------
@strawberry.type
class Query:
    @strawberry.field
    async def host_health(self, host_id: str) -> HostHealth:
        """返回单个主机的最新健康检查结果（来自 MCP Tools）"""
        try:
            health = await get_host_health(host_id)
            # health 可能返回 dict，统一映射到 HostHealth
            return HostHealth(
                host_id=host_id,
                status=health.get("status", "unknown"),
                last_checked=health.get("timestamp", datetime.now(timezone.utc)),
                details=health.get("details"),
            )
        except Exception as exc:
            _logger.error("GraphQL host_health 查询失败: %s", exc, exc_info=True)
            raise GraphQLError(str(exc))

    @strawberry.field
    def metrics(self, limit: int = 20) -> List[Metric]:
        """返回最近的 metrics（统一由 metrics_history 提供）"""
        try:
            raw = get_metrics_history(limit=limit)
            return [
                Metric(
                    timestamp=entry["timestamp"],
                    name=entry["name"],
                    value=float(entry["value"]),
                    host_id=entry.get("host_id"),
                )
                for entry in raw
            ]
        except Exception as exc:
            _logger.error("GraphQL metrics 查询失败: %s", exc, exc_info=True)
            raise GraphQLError(str(exc))

    @strawberry.field
    def incidents(self, host_id: Optional[str] = None, limit: int = 20) -> List[Incident]:
        """查询历史 incident（通过 db_engine 提供的通用查询）"""
        try:
            raw = get_incident_history(host_id=host_id, limit=limit)
            return [
                Incident(
                    incident_id=row["id"],
                    host_id=row.get("host_id"),
                    alert_id=row.get("alert_id"),
                    script_key=row.get("script_key"),
                    created_at=row["created_at"],
                    status=row["status"],
                    severity=row.get("severity"),
                )
                for row in raw
            ]
        except Exception as exc:
            _logger.error("GraphQL incidents 查询失败: %s", exc, exc_info=True)
            raise


# ----------------------------------------------------------------------
# Schema 实例（供 FastAPI 使用）
# ----------------------------------------------------------------------
schema = strawberry.Schema(query=Query)
