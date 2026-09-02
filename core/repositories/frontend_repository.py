# -*- coding: utf-8 -*-
"""
frontend_repository.py
----------------------
Frontend数据仓储抽象接口

定义前端数据访问的标准接口，用于解耦数据库访问逻辑。
所有需要访问前端数据的模块应依赖此接口而非直接使用 db_engine。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class FrontendRepository(ABC):
    """前端数据仓储抽象接口"""

    # ==================== Component Methods ====================

    @abstractmethod
    async def create_component(self, component: Dict[str, Any]) -> str:
        """
        创建前端组件

        Args:
            component: 组件数据字典

        Returns:
            组件 ID
        """

    @abstractmethod
    async def get_component(self, component_id: str) -> Optional[Dict[str, Any]]:
        """
        获取前端组件

        Args:
            component_id: 组件 ID

        Returns:
            组件数据字典，如果不存在返回 None
        """

    @abstractmethod
    async def list_components(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        列出前端组件

        Args:
            filters: 过滤条件（可选）
            limit: 返回结果数量限制
            offset: 偏移量

        Returns:
            组件列表
        """

    @abstractmethod
    async def update_component(self, component_id: str, updates: Dict[str, Any]) -> bool:
        """
        更新前端组件

        Args:
            component_id: 组件 ID
            updates: 更新数据字典

        Returns:
            更新成功返回 True，否则返回 False
        """

    @abstractmethod
    async def delete_component(self, component_id: str) -> bool:
        """
        删除前端组件

        Args:
            component_id: 组件 ID

        Returns:
            删除成功返回 True，否则返回 False
        """

    @abstractmethod
    async def count_components(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        统计组件数量

        Args:
            filters: 过滤条件（可选）

        Returns:
            组件数量
        """

    # ==================== Theme Methods ====================

    @abstractmethod
    async def create_theme(self, theme: Dict[str, Any]) -> str:
        """
        创建前端主题

        Args:
            theme: 主题数据字典

        Returns:
            主题 ID
        """

    @abstractmethod
    async def get_theme(self, theme_id: str) -> Optional[Dict[str, Any]]:
        """
        获取前端主题

        Args:
            theme_id: 主题 ID

        Returns:
            主题数据字典，如果不存在返回 None
        """

    @abstractmethod
    async def list_themes(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        列出前端主题

        Args:
            filters: 过滤条件（可选）
            limit: 返回结果数量限制
            offset: 偏移量

        Returns:
            主题列表
        """

    @abstractmethod
    async def update_theme(self, theme_id: str, updates: Dict[str, Any]) -> bool:
        """
        更新前端主题

        Args:
            theme_id: 主题 ID
            updates: 更新数据字典

        Returns:
            更新成功返回 True，否则返回 False
        """

    @abstractmethod
    async def delete_theme(self, theme_id: str) -> bool:
        """
        删除前端主题

        Args:
            theme_id: 主题 ID

        Returns:
            删除成功返回 True，否则返回 False
        """

    @abstractmethod
    async def count_themes(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        统计主题数量

        Args:
            filters: 过滤条件（可选）

        Returns:
            主题数量
        """

    # ==================== Layout Methods ====================

    @abstractmethod
    async def create_layout(self, layout: Dict[str, Any]) -> str:
        """
        创建前端布局

        Args:
            layout: 布局数据字典

        Returns:
            布局 ID
        """

    @abstractmethod
    async def get_layout(self, layout_id: str) -> Optional[Dict[str, Any]]:
        """
        获取前端布局

        Args:
            layout_id: 布局 ID

        Returns:
            布局数据字典，如果不存在返回 None
        """

    @abstractmethod
    async def list_layouts(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        列出前端布局

        Args:
            filters: 过滤条件（可选）
            limit: 返回结果数量限制
            offset: 偏移量

        Returns:
            布局列表
        """

    @abstractmethod
    async def update_layout(self, layout_id: str, updates: Dict[str, Any]) -> bool:
        """
        更新前端布局

        Args:
            layout_id: 布局 ID
            updates: 更新数据字典

        Returns:
            更新成功返回 True，否则返回 False
        """

    @abstractmethod
    async def delete_layout(self, layout_id: str) -> bool:
        """
        删除前端布局

        Args:
            layout_id: 布局 ID

        Returns:
            删除成功返回 True，否则返回 False
        """

    @abstractmethod
    async def count_layouts(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        统计布局数量

        Args:
            filters: 过滤条件（可选）

        Returns:
            布局数量
        """

    # ==================== User Preference Methods ====================

    @abstractmethod
    async def get_user_preferences(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        获取用户偏好设置

        Args:
            user_id: 用户 ID

        Returns:
            用户偏好数据字典，如果不存在返回 None
        """

    @abstractmethod
    async def update_user_preferences(self, user_id: str, preferences: Dict[str, Any]) -> bool:
        """
        更新用户偏好设置

        Args:
            user_id: 用户 ID
            preferences: 偏好设置字典

        Returns:
            更新成功返回 True，否则返回 False
        """

    @abstractmethod
    async def create_user_preferences(self, user_id: str, preferences: Dict[str, Any]) -> bool:
        """
        创建用户偏好设置

        Args:
            user_id: 用户 ID
            preferences: 偏好设置字典

        Returns:
            创建成功返回 True，否则返回 False
        """

    # ==================== Dashboard Widget Methods ====================

    @abstractmethod
    async def create_dashboard_widget(self, widget: Dict[str, Any]) -> str:
        """
        创建仪表板小部件

        Args:
            widget: 小部件数据字典

        Returns:
            小部件 ID
        """

    @abstractmethod
    async def get_dashboard_widget(self, widget_id: str) -> Optional[Dict[str, Any]]:
        """
        获取仪表板小部件

        Args:
            widget_id: 小部件 ID

        Returns:
            小部件数据字典，如果不存在返回 None
        """

    @abstractmethod
    async def list_dashboard_widgets(
        self, dashboard_id: str, filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        列出仪表板小部件

        Args:
            dashboard_id: 仪表板 ID
            filters: 过滤条件（可选）

        Returns:
            小部件列表
        """

    @abstractmethod
    async def update_dashboard_widget(self, widget_id: str, updates: Dict[str, Any]) -> bool:
        """
        更新仪表板小部件

        Args:
            widget_id: 小部件 ID
            updates: 更新数据字典

        Returns:
            更新成功返回 True，否则返回 False
        """

    @abstractmethod
    async def delete_dashboard_widget(self, widget_id: str) -> bool:
        """
        删除仪表板小部件

        Args:
            widget_id: 小部件 ID

        Returns:
            删除成功返回 True，否则返回 False
        """

    # ==================== Report Template Methods ====================

    @abstractmethod
    async def create_report_template(self, template: Dict[str, Any]) -> str:
        """
        创建报告模板

        Args:
            template: 模板数据字典

        Returns:
            模板 ID
        """

    @abstractmethod
    async def get_report_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        """
        获取报告模板

        Args:
            template_id: 模板 ID

        Returns:
            模板数据字典，如果不存在返回 None
        """

    @abstractmethod
    async def list_report_templates(
        self, filters: Optional[Dict[str, Any]] = None, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        列出报告模板

        Args:
            filters: 过滤条件（可选）
            limit: 返回结果数量限制

        Returns:
            模板列表
        """

    @abstractmethod
    async def update_report_template(self, template_id: str, updates: Dict[str, Any]) -> bool:
        """
        更新报告模板

        Args:
            template_id: 模板 ID
            updates: 更新数据字典

        Returns:
            更新成功返回 True，否则返回 False
        """

    @abstractmethod
    async def delete_report_template(self, template_id: str) -> bool:
        """
        删除报告模板

        Args:
            template_id: 模板 ID

        Returns:
            删除成功返回 True，否则返回 False
        """

    # ==================== Localization Methods ====================

    @abstractmethod
    async def get_localization(
        self, language: str, translation_key: str
    ) -> Optional[Dict[str, Any]]:
        """
        获取本地化翻译

        Args:
            language: 语言代码
            translation_key: 翻译键

        Returns:
            翻译数据字典，如果不存在返回 None
        """

    @abstractmethod
    async def list_localizations(
        self, language: Optional[str] = None, limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        列出本地化翻译

        Args:
            language: 语言代码（可选）
            limit: 返回结果数量限制

        Returns:
            翻译列表
        """

    @abstractmethod
    async def upsert_localization(
        self, language: str, translation_key: str, translation_value: str, context: Optional[str] = None
    ) -> bool:
        """
        创建或更新本地化翻译

        Args:
            language: 语言代码
            translation_key: 翻译键
            translation_value: 翻译值
            context: 上下文（可选）

        Returns:
            操作成功返回 True，否则返回 False
        """

    @abstractmethod
    async def delete_localization(self, language: str, translation_key: str) -> bool:
        """
        删除本地化翻译

        Args:
            language: 语言代码
            translation_key: 翻译键

        Returns:
            删除成功返回 True，否则返回 False
        """
