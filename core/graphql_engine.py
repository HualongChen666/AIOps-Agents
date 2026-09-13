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
from typing import Any, List, Optional

import strawberry
from strawberry.exceptions import GraphQLError

from core.db_engine import async_query_repairs
from core.mcp_tools import get_host_health
from core.metrics_history import get_metrics_history

_logger = logging.getLogger(__name__)


def _coerce_datetime(value: Any) -> datetime:
    """把 ISO 字符串 / datetime / None 统一为 datetime（供 strawberry datetime 标量使用）。"""
    if isinstance(value, datetime):
        return value
    if isinstance(value, str) and value:
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            pass
    return datetime.now(timezone.utc)


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
                    timestamp=_coerce_datetime(entry["timestamp"]),
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
    async def incidents(self, host_id: Optional[str] = None, limit: int = 20) -> List[Incident]:
        """查询历史 incident（来源于 db_engine 的真实修复记录）。

        每条修复记录即一次事件处置：其 repair_time 作为 created_at，
        host 作为 host_id，risk 作为 severity 等。
        """
        try:
            rows = await async_query_repairs(limit=limit)
            results: List[Incident] = []
            for row in rows:
                if host_id is not None and row.get("host") != host_id:
                    continue
                created_at = _coerce_datetime(row.get("repair_time"))
                results.append(
                    Incident(
                        incident_id=str(row.get("id")),
                        host_id=row.get("host"),
                        alert_id=row.get("alert_id"),
                        script_key=row.get("script_key"),
                        created_at=created_at,
                        status=str(row.get("status") or "unknown"),
                        severity=row.get("risk"),
                    )
                )
            return results
        except Exception as exc:
            _logger.error("GraphQL incidents 查询失败: %s", exc, exc_info=True)
            raise GraphQLError(str(exc))


# ----------------------------------------------------------------------
# Schema 实例（供 FastAPI 使用）
# ----------------------------------------------------------------------
schema = strawberry.Schema(query=Query)
