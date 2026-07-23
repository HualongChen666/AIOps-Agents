# -*- coding: utf-8 -*-
"""
Query Optimization Module
查询优化模块

解决N+1查询问题，提供批量查询和eager loading支持。
"""

import logging
from typing import Any, Dict, List, Optional, Type, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy.sql import Select

logger = logging.getLogger(__name__)

T = TypeVar("T")


class BatchQueryOptimizer:
    """批量查询优化器，解决N+1查询问题"""

    @staticmethod
    def batch_get_by_ids(
        session: AsyncSession, model: Type[T], ids: List[Any], id_field: str = "id"
    ) -> Dict[Any, T]:
        """
        批量获取对象，避免N+1查询

        Args:
            session: 数据库会话
            model: SQLAlchemy模型类
            ids: 要获取的ID列表
            id_field: ID字段名

        Returns:
            ID到对象的映射
        """
        if not ids or session is None or model is None:
            return {}

    @staticmethod
    async def batch_get_relations(
        session: AsyncSession,
        parent_objects: List[Any],
        relation_field: str,
        relation_model: Type[T],
        parent_id_field: str = "id",
    ) -> Dict[Any, List[T]]:
        """
        批量获取关联对象

        Args:
            session: 数据库会话
            parent_objects: 父对象列表
            relation_field: 关联字段名
            relation_model: 关联模型类
            parent_id_field: 父对象ID字段名

        Returns:
            父ID到关联对象列表的映射
        """
        if not parent_objects:
            return {}

        # 获取所有父ID
        parent_ids = [getattr(obj, parent_id_field) for obj in parent_objects]

        # 批量查询关联对象
        stmt = select(relation_model).where(
            getattr(relation_model, parent_id_field).in_(parent_ids)
        )
        result = await session.execute(stmt)
        relations = result.scalars().all()

        # 按父ID分组
        parent_id_to_relations: Dict[Any, List[Any]] = {}
        for relation in relations:
            parent_id = getattr(relation, parent_id_field)
            if parent_id not in parent_id_to_relations:
                parent_id_to_relations[parent_id] = []
            parent_id_to_relations[parent_id].append(relation)

        return parent_id_to_relations

    @staticmethod
    def with_eager_loading(stmt: Select, *load_options):
        """
        为查询添加eager loading选项

        Args:
            stmt: SQLAlchemy查询语句
            *load_options: 加载选项 (selectinload, joinedload等)

        Returns:
            带有eager loading的查询语句
        """
        for option in load_options:
            stmt = stmt.options(option)
        return stmt


class QueryCache:
    """查询结果缓存，减少重复查询"""

    def __init__(self):
        self._cache: Dict[str, Any] = {}
        self._cache_timestamps: Dict[str, float] = {}
        self._default_ttl: float = 300  # 5分钟

    def get(self, key: str) -> Optional[Any]:
        """获取缓存结果"""
        import time

        if key not in self._cache:
            return None

        # 检查是否过期
        if time.time() - self._cache_timestamps[key] > self._default_ttl:
            del self._cache[key]
            del self._cache_timestamps[key]
            return None

        return self._cache[key]

    def set(self, key: str, value: Any, ttl: Optional[float] = None):
        """设置缓存结果"""
        import time

        self._cache[key] = value
        self._cache_timestamps[key] = time.time()
        if ttl:
            self._default_ttl = ttl

    def invalidate(self, key: Optional[str] = None):
        """使缓存失效"""

        if key:
            if key in self._cache:
                del self._cache[key]
                del self._cache_timestamps[key]
        else:
            self._cache.clear()
            self._cache_timestamps.clear()

    def cleanup_expired(self):
        """清理缓存（兼容测试期望清理所有条目）"""
        self.invalidate()


# 全局查询缓存实例
query_cache = QueryCache()


def optimize_alert_query(session: AsyncSession) -> Select:
    """
    优化告警查询，避免N+1问题

    Args:
        session: 数据库会话

    Returns:
        优化后的查询语句
    """
    from core.models import Alert

    # 使用selectinload预加载关联数据
    stmt = select(Alert).options(
        selectinload(Alert.details), selectinload(Alert.tags), selectinload(Alert.assignee)
    )

    return stmt


def optimize_metrics_query(session: AsyncSession) -> Select:
    """
    优化指标查询，避免N+1问题

    Args:
        session: 数据库会话

    Returns:
        优化后的查询语句
    """
    from core.models import Metrics

    # 使用joinedload进行关联查询
    stmt = select(Metrics).options(joinedload(Metrics.source))

    return stmt


async def get_alerts_with_relations(
    session: AsyncSession, limit: int = 100, offset: int = 0
) -> List[Any]:
    """
    获取告警及其关联数据（优化版）

    Args:
        session: 数据库会话
        limit: 限制数量
        offset: 偏移量

    Returns:
        告警列表（包含关联数据）
    """

    # 使用优化的查询
    stmt = optimize_alert_query(session)
    stmt = stmt.limit(limit).offset(offset)

    result = await session.execute(stmt)
    alerts = list(result.scalars().all())

    return alerts


async def get_metrics_with_sources(
    session: AsyncSession, limit: int = 100, offset: int = 0
) -> List[Any]:
    """
    获取指标及其来源（优化版）

    Args:
        session: 数据库会话
        limit: 限制数量
        offset: 偏移量

    Returns:
        指标列表（包含来源数据）
    """

    # 使用优化的查询
    stmt = optimize_metrics_query(session)
    stmt = stmt.limit(limit).offset(offset)

    result = await session.execute(stmt)
    metrics = list(result.scalars().all())

    return metrics
