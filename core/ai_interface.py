# -*- coding: utf-8 -*-
"""
ai_interface.py
--------------
AI 服务抽象接口

定义 AI 分析服务的标准接口，用于解耦具体实现与使用方。
所有依赖 AI 引擎的模块应依赖此接口而非 core.ai_engine 的具体实现。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional


class AnalysisType(str, Enum):
    """分析类型枚举"""

    ANOMALY = "anomaly"
    ROOT_CAUSE = "root_cause"
    RUNBOOK = "runbook"
    GENERAL = "general"


class AIAnalysisService(ABC):
    """AI 分析服务抽象接口"""

    @abstractmethod
    async def analyze(
        self, context: Dict[str, Any], analysis_type: AnalysisType = AnalysisType.GENERAL
    ) -> Dict[str, Any]:
        """
        执行 AI 分析

        Args:
            context: 分析上下文数据（包含指标、日志、告警等）
            analysis_type: 分析类型

        Returns:
            分析结果字典，包含建议、根因、置信度等
        """

    @abstractmethod
    async def observe(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        观察数据并生成洞察

        Args:
            data: 观察数据

        Returns:
            观察结果字典
        """

    @abstractmethod
    async def generate_runbook(
        self, alert_data: Dict[str, Any], context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        生成修复手册

        Args:
            alert_data: 告警数据
            context: 额外上下文信息

        Returns:
            修复手册字典，包含步骤、命令、验证方法等
        """

    @abstractmethod
    async def search_similar(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        搜索相似历史案例

        Args:
            query: 查询文本
            limit: 返回结果数量限制

        Returns:
            相似案例列表
        """

    @abstractmethod
    async def get_health_status(self) -> Dict[str, Any]:
        """
        获取 AI 服务健康状态

        Returns:
            健康状态字典，包含可用性、延迟、错误率等
        """
