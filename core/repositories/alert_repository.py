# -*- coding: utf-8 -*-
"""
alert_repository.py
-------------------
告警数据仓储抽象接口

定义告警数据访问的标准接口，用于解耦数据库访问逻辑。
所有需要访问告警数据的模块应依赖此接口而非直接使用 db_engine。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional


class AlertSeverity(str, Enum):
    """告警严重程度"""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertStatus(str, Enum):
    """告警状态"""

    ACTIVE = "active"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"


class AlertRepository(ABC):
    """告警数据仓储抽象接口"""

    @abstractmethod
    async def save(self, alert: Dict[str, Any]) -> str:
        """
        保存告警

        Args:
            alert: 告警数据字典

        Returns:
            告警 ID
        """

    @abstractmethod
    async def query(
        self, filters: Optional[Dict[str, Any]] = None, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        查询告警

        Args:
            filters: 过滤条件（可选）
            limit: 返回结果数量限制

        Returns:
            告警列表
        """

    @abstractmethod
    async def get_by_id(self, alert_id: str) -> Optional[Dict[str, Any]]:
        """
        根据 ID 获取告警

        Args:
            alert_id: 告警 ID

        Returns:
            告警数据字典，如果不存在返回 None
        """

    @abstractmethod
    async def update_status(self, alert_id: str, status: AlertStatus) -> bool:
        """
        更新告警状态

        Args:
            alert_id: 告警 ID
            status: 新状态

        Returns:
            更新成功返回 True，否则返回 False
        """

    @abstractmethod
    async def delete(self, alert_id: str) -> bool:
        """
        删除告警

        Args:
            alert_id: 告警 ID

        Returns:
            删除成功返回 True，否则返回 False
        """

    @abstractmethod
    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        统计告警数量

        Args:
            filters: 过滤条件（可选）

        Returns:
            告警数量
        """

    @abstractmethod
    async def clear_all(self) -> bool:
        """
        清空所有告警

        Returns:
            清空成功返回 True，否则返回 False
        """

    @abstractmethod
    async def get_recent(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        获取最近的告警

        Args:
            limit: 返回结果数量限制

        Returns:
            最近告警列表
        """
