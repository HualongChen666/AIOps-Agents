# -*- coding: utf-8 -*-
# core/repositories/frontend_repository_impl.py
# Frontend Repository实现 - 实现数据库持久化

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from core.db_engine import AsyncSessionLocal
from core.models import (
    FrontendComponent,
    FrontendDashboardWidget,
    FrontendLayout,
    FrontendLocalization,
    FrontendReportTemplate,
    FrontendTheme,
    FrontendUserPreference,
)
from core.repositories.frontend_repository import FrontendRepository

logger = logging.getLogger(__name__)


class FrontendRepositoryImpl(FrontendRepository):
    """Frontend Repository实现 - 处理所有前端相关的数据库操作"""

    def __init__(self, session: Optional[AsyncSession] = None):
        """初始化Repository

        Args:
            session: 可选的数据库会话，如果未提供则创建新会话
        """
        self._session = session
        self._owns_session = session is None

    async def __aenter__(self):
        """异步上下文管理器入口"""
        if self._owns_session:
            self._session = AsyncSessionLocal()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器退出"""
        if self._owns_session and self._session:
            await self._session.close()

    @property
    def session(self) -> AsyncSession:
        """获取数据库会话"""
        if not self._session:
            raise RuntimeError("Session not initialized. Use async context manager or provide session.")
        return self._session

    # ==================== Component Methods ====================

    async def create_component(self, component: Dict[str, Any]) -> str:
        """创建前端组件"""
        try:
            new_component = FrontendComponent(
                id=component.get("id"),
                name=component["name"],
                type=component["type"],
                category=component.get("category"),
                description=component.get("description"),
                props=component.get("props"),
                code=component["code"],
                dependencies=component.get("dependencies"),
                is_public=component.get("is_public", False),
                created_by=component.get("created_by"),
                status=component.get("status", "active"),
            )
            self.session.add(new_component)
            await self.session.commit()
            await self.session.refresh(new_component)
            logger.info(f"✅ 组件创建成功 | id={new_component.id} | name={new_component.name}")
            return new_component.id
        except Exception as e:
            await self.session.rollback()
            logger.error(f"创建组件失败: {e}", exc_info=True)
            raise

    async def get_component(self, component_id: str) -> Optional[Dict[str, Any]]:
        """获取前端组件"""
        try:
            stmt = select(FrontendComponent).where(FrontendComponent.id == component_id)
            result = await self.session.execute(stmt)
            component = result.scalar_one_or_none()
            if component:
                return self._component_to_dict(component)
            return None
        except Exception as e:
            logger.error(f"获取组件失败 | component_id={component_id}: {e}", exc_info=True)
            raise

    async def list_components(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """列出前端组件"""
        try:
            stmt = select(FrontendComponent)
            if filters:
                if filters.get("type"):
                    stmt = stmt.where(FrontendComponent.type == filters["type"])
                if filters.get("category"):
                    stmt = stmt.where(FrontendComponent.category == filters["category"])
                if filters.get("is_public") is not None:
                    stmt = stmt.where(FrontendComponent.is_public == filters["is_public"])
                if filters.get("status"):
                    stmt = stmt.where(FrontendComponent.status == filters["status"])
            stmt = stmt.offset(offset).limit(limit)
            result = await self.session.execute(stmt)
            components = result.scalars().all()
            return [self._component_to_dict(c) for c in components]
        except Exception as e:
            logger.error(f"列出组件失败: {e}", exc_info=True)
            raise

    async def update_component(self, component_id: str, updates: Dict[str, Any]) -> bool:
        """更新前端组件"""
        try:
            stmt = update(FrontendComponent).where(FrontendComponent.id == component_id).values(
                **{k: v for k, v in updates.items() if k in FrontendComponent.__table__.columns}
            )
            result = await self.session.execute(stmt)
            await self.session.commit()
            count = result.rowcount if hasattr(result, "rowcount") else 0
            if count > 0:
                logger.info(f"✅ 组件更新成功 | component_id={component_id}")
                return True
            return False
        except Exception as e:
            await self.session.rollback()
            logger.error(f"更新组件失败 | component_id={component_id}: {e}", exc_info=True)
            raise

    async def delete_component(self, component_id: str) -> bool:
        """删除前端组件"""
        try:
            stmt = delete(FrontendComponent).where(FrontendComponent.id == component_id)
            result = await self.session.execute(stmt)
            await self.session.commit()
            count = result.rowcount if hasattr(result, "rowcount") else 0
            if count > 0:
                logger.info(f"✅ 组件删除成功 | component_id={component_id}")
                return True
            return False
        except Exception as e:
            await self.session.rollback()
            logger.error(f"删除组件失败 | component_id={component_id}: {e}", exc_info=True)
            raise

    async def count_components(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """统计组件数量"""
        try:
            from sqlalchemy import func

            stmt = select(func.count(FrontendComponent.id))
            if filters:
                if filters.get("type"):
                    stmt = stmt.where(FrontendComponent.type == filters["type"])
                if filters.get("category"):
                    stmt = stmt.where(FrontendComponent.category == filters["category"])
                if filters.get("is_public") is not None:
                    stmt = stmt.where(FrontendComponent.is_public == filters["is_public"])
                if filters.get("status"):
                    stmt = stmt.where(FrontendComponent.status == filters["status"])
            result = await self.session.execute(stmt)
            count = result.scalar()
            return count if count else 0
        except Exception as e:
            logger.error(f"统计组件数量失败: {e}", exc_info=True)
            raise

    def _component_to_dict(self, component: FrontendComponent) -> Dict[str, Any]:
        """将FrontendComponent对象转换为字典"""
        return {
            "id": component.id,
            "name": component.name,
            "type": component.type,
            "category": component.category,
            "description": component.description,
            "props": component.props,
            "code": component.code,
            "dependencies": component.dependencies,
            "is_public": component.is_public,
            "created_by": component.created_by,
            "status": component.status,
            "created_at": component.created_at.isoformat() if component.created_at else None,
            "updated_at": component.updated_at.isoformat() if component.updated_at else None,
        }

    # ==================== Theme Methods ====================

    async def create_theme(self, theme: Dict[str, Any]) -> str:
        """创建前端主题"""
        try:
            new_theme = FrontendTheme(
                id=theme.get("id"),
                name=theme["name"],
                base_theme=theme["base_theme"],
                description=theme.get("description"),
                colors=theme["colors"],
                fonts=theme.get("fonts"),
                spacing=theme.get("spacing"),
                is_default=theme.get("is_default", False),
                is_public=theme.get("is_public", False),
                created_by=theme.get("created_by"),
            )
            self.session.add(new_theme)
            await self.session.commit()
            await self.session.refresh(new_theme)
            logger.info(f"✅ 主题创建成功 | id={new_theme.id} | name={new_theme.name}")
            return new_theme.id
        except Exception as e:
            await self.session.rollback()
            logger.error(f"创建主题失败: {e}", exc_info=True)
            raise

    async def get_theme(self, theme_id: str) -> Optional[Dict[str, Any]]:
        """获取前端主题"""
        try:
            stmt = select(FrontendTheme).where(FrontendTheme.id == theme_id)
            result = await self.session.execute(stmt)
            theme = result.scalar_one_or_none()
            if theme:
                return self._theme_to_dict(theme)
            return None
        except Exception as e:
            logger.error(f"获取主题失败 | theme_id={theme_id}: {e}", exc_info=True)
            raise

    async def list_themes(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """列出前端主题"""
        try:
            stmt = select(FrontendTheme)
            if filters:
                if filters.get("base_theme"):
                    stmt = stmt.where(FrontendTheme.base_theme == filters["base_theme"])
                if filters.get("is_default") is not None:
                    stmt = stmt.where(FrontendTheme.is_default == filters["is_default"])
            stmt = stmt.offset(offset).limit(limit)
            result = await self.session.execute(stmt)
            themes = result.scalars().all()
            return [self._theme_to_dict(t) for t in themes]
        except Exception as e:
            logger.error(f"列出主题失败: {e}", exc_info=True)
            raise

    async def update_theme(self, theme_id: str, updates: Dict[str, Any]) -> bool:
        """更新前端主题"""
        try:
            stmt = update(FrontendTheme).where(FrontendTheme.id == theme_id).values(
                **{k: v for k, v in updates.items() if k in FrontendTheme.__table__.columns}
            )
            result = await self.session.execute(stmt)
            await self.session.commit()
            count = result.rowcount if hasattr(result, "rowcount") else 0
            if count > 0:
                logger.info(f"✅ 主题更新成功 | theme_id={theme_id}")
                return True
            return False
        except Exception as e:
            await self.session.rollback()
            logger.error(f"更新主题失败 | theme_id={theme_id}: {e}", exc_info=True)
            raise

    async def delete_theme(self, theme_id: str) -> bool:
        """删除前端主题"""
        try:
            stmt = delete(FrontendTheme).where(FrontendTheme.id == theme_id)
            result = await self.session.execute(stmt)
            await self.session.commit()
            count = result.rowcount if hasattr(result, "rowcount") else 0
            if count > 0:
                logger.info(f"✅ 主题删除成功 | theme_id={theme_id}")
                return True
            return False
        except Exception as e:
            await self.session.rollback()
            logger.error(f"删除主题失败 | theme_id={theme_id}: {e}", exc_info=True)
            raise

    async def count_themes(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """统计主题数量"""
        try:
            from sqlalchemy import func

            stmt = select(func.count(FrontendTheme.id))
            if filters:
                if filters.get("base_theme"):
                    stmt = stmt.where(FrontendTheme.base_theme == filters["base_theme"])
                if filters.get("is_default") is not None:
                    stmt = stmt.where(FrontendTheme.is_default == filters["is_default"])
            result = await self.session.execute(stmt)
            count = result.scalar()
            return count if count else 0
        except Exception as e:
            logger.error(f"统计主题数量失败: {e}", exc_info=True)
            raise

    def _theme_to_dict(self, theme: FrontendTheme) -> Dict[str, Any]:
        """将FrontendTheme对象转换为字典"""
        return {
            "id": theme.id,
            "name": theme.name,
            "base_theme": theme.base_theme,
            "description": theme.description,
            "colors": theme.colors,
            "fonts": theme.fonts,
            "spacing": theme.spacing,
            "is_default": theme.is_default,
            "is_public": theme.is_public,
            "created_by": theme.created_by,
            "created_at": theme.created_at.isoformat() if theme.created_at else None,
            "updated_at": theme.updated_at.isoformat() if theme.updated_at else None,
        }

    # ==================== Layout Methods ====================

    async def create_layout(self, layout: Dict[str, Any]) -> str:
        """创建前端布局"""
        try:
            new_layout = FrontendLayout(
                id=layout.get("id"),
                name=layout["name"],
                type=layout["type"],
                description=layout.get("description"),
                structure=layout["structure"],
                breakpoints=layout.get("breakpoints"),
                is_default=layout.get("is_default", False),
                is_public=layout.get("is_public", False),
                created_by=layout.get("created_by"),
            )
            self.session.add(new_layout)
            await self.session.commit()
            await self.session.refresh(new_layout)
            logger.info(f"✅ 布局创建成功 | id={new_layout.id} | name={new_layout.name}")
            return new_layout.id
        except Exception as e:
            await self.session.rollback()
            logger.error(f"创建布局失败: {e}", exc_info=True)
            raise

    async def get_layout(self, layout_id: str) -> Optional[Dict[str, Any]]:
        """获取前端布局"""
        try:
            stmt = select(FrontendLayout).where(FrontendLayout.id == layout_id)
            result = await self.session.execute(stmt)
            layout = result.scalar_one_or_none()
            if layout:
                return self._layout_to_dict(layout)
            return None
        except Exception as e:
            logger.error(f"获取布局失败 | layout_id={layout_id}: {e}", exc_info=True)
            raise

    async def list_layouts(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """列出前端布局"""
        try:
            stmt = select(FrontendLayout)
            if filters:
                if filters.get("type"):
                    stmt = stmt.where(FrontendLayout.type == filters["type"])
                if filters.get("is_default") is not None:
                    stmt = stmt.where(FrontendLayout.is_default == filters["is_default"])
            stmt = stmt.offset(offset).limit(limit)
            result = await self.session.execute(stmt)
            layouts = result.scalars().all()
            return [self._layout_to_dict(l) for l in layouts]
        except Exception as e:
            logger.error(f"列出布局失败: {e}", exc_info=True)
            raise

    async def update_layout(self, layout_id: str, updates: Dict[str, Any]) -> bool:
        """更新前端布局"""
        try:
            stmt = update(FrontendLayout).where(FrontendLayout.id == layout_id).values(
                **{k: v for k, v in updates.items() if k in FrontendLayout.__table__.columns}
            )
            result = await self.session.execute(stmt)
            await self.session.commit()
            count = result.rowcount if hasattr(result, "rowcount") else 0
            if count > 0:
                logger.info(f"✅ 布局更新成功 | layout_id={layout_id}")
                return True
            return False
        except Exception as e:
            await self.session.rollback()
            logger.error(f"更新布局失败 | layout_id={layout_id}: {e}", exc_info=True)
            raise

    async def delete_layout(self, layout_id: str) -> bool:
        """删除前端布局"""
        try:
            stmt = delete(FrontendLayout).where(FrontendLayout.id == layout_id)
            result = await self.session.execute(stmt)
            await self.session.commit()
            count = result.rowcount if hasattr(result, "rowcount") else 0
            if count > 0:
                logger.info(f"✅ 布局删除成功 | layout_id={layout_id}")
                return True
            return False
        except Exception as e:
            await self.session.rollback()
            logger.error(f"删除布局失败 | layout_id={layout_id}: {e}", exc_info=True)
            raise

    async def count_layouts(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """统计布局数量"""
        try:
            from sqlalchemy import func

            stmt = select(func.count(FrontendLayout.id))
            if filters:
                if filters.get("type"):
                    stmt = stmt.where(FrontendLayout.type == filters["type"])
                if filters.get("is_default") is not None:
                    stmt = stmt.where(FrontendLayout.is_default == filters["is_default"])
            result = await self.session.execute(stmt)
            count = result.scalar()
            return count if count else 0
        except Exception as e:
            logger.error(f"统计布局数量失败: {e}", exc_info=True)
            raise

    def _layout_to_dict(self, layout: FrontendLayout) -> Dict[str, Any]:
        """将FrontendLayout对象转换为字典"""
        return {
            "id": layout.id,
            "name": layout.name,
            "type": layout.type,
            "description": layout.description,
            "structure": layout.structure,
            "breakpoints": layout.breakpoints,
            "is_default": layout.is_default,
            "is_public": layout.is_public,
            "created_by": layout.created_by,
            "created_at": layout.created_at.isoformat() if layout.created_at else None,
            "updated_at": layout.updated_at.isoformat() if layout.updated_at else None,
        }

    # ==================== User Preference Methods ====================

    async def get_user_preferences(self, user_id: str) -> Optional[Dict[str, Any]]:
        """获取用户偏好设置"""
        try:
            stmt = select(FrontendUserPreference).where(FrontendUserPreference.user_id == user_id)
            result = await self.session.execute(stmt)
            pref = result.scalar_one_or_none()
            if pref:
                return self._user_preference_to_dict(pref)
            return None
        except Exception as e:
            logger.error(f"获取用户偏好失败 | user_id={user_id}: {e}", exc_info=True)
            raise

    async def update_user_preferences(self, user_id: str, preferences: Dict[str, Any]) -> bool:
        """更新用户偏好设置"""
        try:
            pref = await self.get_user_preferences(user_id)
            if not pref:
                return await self.create_user_preferences(user_id, preferences)

            stmt = (
                update(FrontendUserPreference)
                .where(FrontendUserPreference.user_id == user_id)
                .values(
                    **{k: v for k, v in preferences.items() if k in FrontendUserPreference.__table__.columns}
                )
            )
            result = await self.session.execute(stmt)
            await self.session.commit()
            count = result.rowcount if hasattr(result, "rowcount") else 0
            if count > 0:
                logger.info(f"✅ 用户偏好更新成功 | user_id={user_id}")
                return True
            return False
        except Exception as e:
            await self.session.rollback()
            logger.error(f"更新用户偏好失败 | user_id={user_id}: {e}", exc_info=True)
            raise

    async def create_user_preferences(self, user_id: str, preferences: Dict[str, Any]) -> bool:
        """创建用户偏好设置"""
        try:
            new_pref = FrontendUserPreference(
                user_id=user_id,
                theme=preferences.get("theme", "auto"),
                language=preferences.get("language", "zh-CN"),
                timezone=preferences.get("timezone", "UTC"),
                date_format=preferences.get("date_format", "YYYY-MM-DD"),
                time_format=preferences.get("time_format", "HH:mm:ss"),
                view_mode=preferences.get("view_mode", "grid"),
                notifications_enabled=preferences.get("notifications_enabled", True),
                notification_sound=preferences.get("notification_sound", False),
                auto_refresh_interval=preferences.get("auto_refresh_interval", 30),
                dashboard_layout=preferences.get("dashboard_layout"),
                custom_colors=preferences.get("custom_colors"),
                accessibility_settings=preferences.get("accessibility_settings"),
            )
            self.session.add(new_pref)
            await self.session.commit()
            logger.info(f"✅ 用户偏好创建成功 | user_id={user_id}")
            return True
        except Exception as e:
            await self.session.rollback()
            logger.error(f"创建用户偏好失败 | user_id={user_id}: {e}", exc_info=True)
            raise

    def _user_preference_to_dict(self, pref: FrontendUserPreference) -> Dict[str, Any]:
        """将FrontendUserPreference对象转换为字典"""
        return {
            "id": pref.id,
            "user_id": pref.user_id,
            "theme": pref.theme,
            "language": pref.language,
            "timezone": pref.timezone,
            "date_format": pref.date_format,
            "time_format": pref.time_format,
            "view_mode": pref.view_mode,
            "notifications_enabled": pref.notifications_enabled,
            "notification_sound": pref.notification_sound,
            "auto_refresh_interval": pref.auto_refresh_interval,
            "dashboard_layout": pref.dashboard_layout,
            "custom_colors": pref.custom_colors,
            "accessibility_settings": pref.accessibility_settings,
            "created_at": pref.created_at.isoformat() if pref.created_at else None,
            "updated_at": pref.updated_at.isoformat() if pref.updated_at else None,
        }

    # ==================== Dashboard Widget Methods ====================

    async def create_dashboard_widget(self, widget: Dict[str, Any]) -> str:
        """创建仪表板小部件"""
        try:
            new_widget = FrontendDashboardWidget(
                id=widget.get("id"),
                dashboard_id=widget["dashboard_id"],
                widget_id=widget["widget_id"],
                widget_type=widget["widget_type"],
                title=widget["title"],
                position=widget["position"],
                config=widget.get("config"),
                data_source=widget.get("data_source"),
                refresh_interval=widget.get("refresh_interval", 30),
                enabled=widget.get("enabled", True),
                created_by=widget.get("created_by"),
            )
            self.session.add(new_widget)
            await self.session.commit()
            await self.session.refresh(new_widget)
            logger.info(f"✅ 小部件创建成功 | id={new_widget.id} | dashboard_id={new_widget.dashboard_id}")
            return new_widget.id
        except Exception as e:
            await self.session.rollback()
            logger.error(f"创建小部件失败: {e}", exc_info=True)
            raise

    async def get_dashboard_widget(self, widget_id: str) -> Optional[Dict[str, Any]]:
        """获取仪表板小部件"""
        try:
            stmt = select(FrontendDashboardWidget).where(FrontendDashboardWidget.id == widget_id)
            result = await self.session.execute(stmt)
            widget = result.scalar_one_or_none()
            if widget:
                return self._dashboard_widget_to_dict(widget)
            return None
        except Exception as e:
            logger.error(f"获取小部件失败 | widget_id={widget_id}: {e}", exc_info=True)
            raise

    async def list_dashboard_widgets(
        self, dashboard_id: str, filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """列出仪表板小部件"""
        try:
            stmt = select(FrontendDashboardWidget).where(
                FrontendDashboardWidget.dashboard_id == dashboard_id
            )
            if filters:
                if filters.get("widget_type"):
                    stmt = stmt.where(FrontendDashboardWidget.widget_type == filters["widget_type"])
                if filters.get("enabled") is not None:
                    stmt = stmt.where(FrontendDashboardWidget.enabled == filters["enabled"])
            result = await self.session.execute(stmt)
            widgets = result.scalars().all()
            return [self._dashboard_widget_to_dict(w) for w in widgets]
        except Exception as e:
            logger.error(f"列出小部件失败 | dashboard_id={dashboard_id}: {e}", exc_info=True)
            raise

    async def update_dashboard_widget(self, widget_id: str, updates: Dict[str, Any]) -> bool:
        """更新仪表板小部件"""
        try:
            stmt = (
                update(FrontendDashboardWidget)
                .where(FrontendDashboardWidget.id == widget_id)
                .values(
                    **{
                        k: v
                        for k, v in updates.items()
                        if k in FrontendDashboardWidget.__table__.columns
                    }
                )
            )
            result = await self.session.execute(stmt)
            await self.session.commit()
            count = result.rowcount if hasattr(result, "rowcount") else 0
            if count > 0:
                logger.info(f"✅ 小部件更新成功 | widget_id={widget_id}")
                return True
            return False
        except Exception as e:
            await self.session.rollback()
            logger.error(f"更新小部件失败 | widget_id={widget_id}: {e}", exc_info=True)
            raise

    async def delete_dashboard_widget(self, widget_id: str) -> bool:
        """删除仪表板小部件"""
        try:
            stmt = delete(FrontendDashboardWidget).where(FrontendDashboardWidget.id == widget_id)
            result = await self.session.execute(stmt)
            await self.session.commit()
            count = result.rowcount if hasattr(result, "rowcount") else 0
            if count > 0:
                logger.info(f"✅ 小部件删除成功 | widget_id={widget_id}")
                return True
            return False
        except Exception as e:
            await self.session.rollback()
            logger.error(f"删除小部件失败 | widget_id={widget_id}: {e}", exc_info=True)
            raise

    def _dashboard_widget_to_dict(self, widget: FrontendDashboardWidget) -> Dict[str, Any]:
        """将FrontendDashboardWidget对象转换为字典"""
        return {
            "id": widget.id,
            "dashboard_id": widget.dashboard_id,
            "widget_id": widget.widget_id,
            "widget_type": widget.widget_type,
            "title": widget.title,
            "position": widget.position,
            "config": widget.config,
            "data_source": widget.data_source,
            "refresh_interval": widget.refresh_interval,
            "enabled": widget.enabled,
            "created_by": widget.created_by,
            "created_at": widget.created_at.isoformat() if widget.created_at else None,
            "updated_at": widget.updated_at.isoformat() if widget.updated_at else None,
        }

    # ==================== Report Template Methods ====================

    async def create_report_template(self, template: Dict[str, Any]) -> str:
        """创建报告模板"""
        try:
            new_template = FrontendReportTemplate(
                id=template.get("id"),
                name=template["name"],
                description=template.get("description"),
                data_sources=template["data_sources"],
                filters=template.get("filters"),
                visualization_config=template.get("visualization_config"),
                format=template.get("format", "pdf"),
                schedule=template.get("schedule"),
                created_by=template.get("created_by"),
            )
            self.session.add(new_template)
            await self.session.commit()
            await self.session.refresh(new_template)
            logger.info(f"✅ 报告模板创建成功 | id={new_template.id} | name={new_template.name}")
            return new_template.id
        except Exception as e:
            await self.session.rollback()
            logger.error(f"创建报告模板失败: {e}", exc_info=True)
            raise

    async def get_report_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        """获取报告模板"""
        try:
            stmt = select(FrontendReportTemplate).where(FrontendReportTemplate.id == template_id)
            result = await self.session.execute(stmt)
            template = result.scalar_one_or_none()
            if template:
                return self._report_template_to_dict(template)
            return None
        except Exception as e:
            logger.error(f"获取报告模板失败 | template_id={template_id}: {e}", exc_info=True)
            raise

    async def list_report_templates(
        self, filters: Optional[Dict[str, Any]] = None, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """列出报告模板"""
        try:
            stmt = select(FrontendReportTemplate)
            if filters:
                if filters.get("format"):
                    stmt = stmt.where(FrontendReportTemplate.format == filters["format"])
            stmt = stmt.limit(limit)
            result = await self.session.execute(stmt)
            templates = result.scalars().all()
            return [self._report_template_to_dict(t) for t in templates]
        except Exception as e:
            logger.error(f"列出报告模板失败: {e}", exc_info=True)
            raise

    async def update_report_template(self, template_id: str, updates: Dict[str, Any]) -> bool:
        """更新报告模板"""
        try:
            stmt = (
                update(FrontendReportTemplate)
                .where(FrontendReportTemplate.id == template_id)
                .values(
                    **{
                        k: v
                        for k, v in updates.items()
                        if k in FrontendReportTemplate.__table__.columns
                    }
                )
            )
            result = await self.session.execute(stmt)
            await self.session.commit()
            count = result.rowcount if hasattr(result, "rowcount") else 0
            if count > 0:
                logger.info(f"✅ 报告模板更新成功 | template_id={template_id}")
                return True
            return False
        except Exception as e:
            await self.session.rollback()
            logger.error(f"更新报告模板失败 | template_id={template_id}: {e}", exc_info=True)
            raise

    async def delete_report_template(self, template_id: str) -> bool:
        """删除报告模板"""
        try:
            stmt = delete(FrontendReportTemplate).where(FrontendReportTemplate.id == template_id)
            result = await self.session.execute(stmt)
            await self.session.commit()
            count = result.rowcount if hasattr(result, "rowcount") else 0
            if count > 0:
                logger.info(f"✅ 报告模板删除成功 | template_id={template_id}")
                return True
            return False
        except Exception as e:
            await self.session.rollback()
            logger.error(f"删除报告模板失败 | template_id={template_id}: {e}", exc_info=True)
            raise

    def _report_template_to_dict(self, template: FrontendReportTemplate) -> Dict[str, Any]:
        """将FrontendReportTemplate对象转换为字典"""
        return {
            "id": template.id,
            "name": template.name,
            "description": template.description,
            "data_sources": template.data_sources,
            "filters": template.filters,
            "visualization_config": template.visualization_config,
            "format": template.format,
            "schedule": template.schedule,
            "created_by": template.created_by,
            "created_at": template.created_at.isoformat() if template.created_at else None,
            "updated_at": template.updated_at.isoformat() if template.updated_at else None,
        }

    # ==================== Localization Methods ====================

    async def get_localization(
        self, language: str, translation_key: str
    ) -> Optional[Dict[str, Any]]:
        """获取本地化翻译"""
        try:
            stmt = select(FrontendLocalization).where(
                FrontendLocalization.language == language,
                FrontendLocalization.translation_key == translation_key,
            )
            result = await self.session.execute(stmt)
            loc = result.scalar_one_or_none()
            if loc:
                return self._localization_to_dict(loc)
            return None
        except Exception as e:
            logger.error(f"获取本地化失败 | language={language} | key={translation_key}: {e}", exc_info=True)
            raise

    async def list_localizations(
        self, language: Optional[str] = None, limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """列出本地化翻译"""
        try:
            stmt = select(FrontendLocalization)
            if language:
                stmt = stmt.where(FrontendLocalization.language == language)
            stmt = stmt.limit(limit)
            result = await self.session.execute(stmt)
            localizations = result.scalars().all()
            return [self._localization_to_dict(l) for l in localizations]
        except Exception as e:
            logger.error(f"列出本地化失败: {e}", exc_info=True)
            raise

    async def upsert_localization(
        self, language: str, translation_key: str, translation_value: str, context: Optional[str] = None
    ) -> bool:
        """创建或更新本地化翻译"""
        try:
            existing = await self.get_localization(language, translation_key)
            if existing:
                stmt = (
                    update(FrontendLocalization)
                    .where(
                        FrontendLocalization.language == language,
                        FrontendLocalization.translation_key == translation_key,
                    )
                    .values(translation_value=translation_value, context=context)
                )
                result = await self.session.execute(stmt)
                await self.session.commit()
                count = result.rowcount if hasattr(result, "rowcount") else 0
                return count > 0
            else:
                new_loc = FrontendLocalization(
                    language=language,
                    translation_key=translation_key,
                    translation_value=translation_value,
                    context=context,
                )
                self.session.add(new_loc)
                await self.session.commit()
                logger.info(f"✅ 本地化创建成功 | language={language} | key={translation_key}")
                return True
        except Exception as e:
            await self.session.rollback()
            logger.error(f"创建/更新本地化失败: {e}", exc_info=True)
            raise

    async def delete_localization(self, language: str, translation_key: str) -> bool:
        """删除本地化翻译"""
        try:
            stmt = delete(FrontendLocalization).where(
                FrontendLocalization.language == language,
                FrontendLocalization.translation_key == translation_key,
            )
            result = await self.session.execute(stmt)
            await self.session.commit()
            count = result.rowcount if hasattr(result, "rowcount") else 0
            if count > 0:
                logger.info(f"✅ 本地化删除成功 | language={language} | key={translation_key}")
                return True
            return False
        except Exception as e:
            await self.session.rollback()
            logger.error(f"删除本地化失败: {e}", exc_info=True)
            raise

    def _localization_to_dict(self, loc: FrontendLocalization) -> Dict[str, Any]:
        """将FrontendLocalization对象转换为字典"""
        return {
            "id": loc.id,
            "language": loc.language,
            "translation_key": loc.translation_key,
            "translation_value": loc.translation_value,
            "context": loc.context,
            "created_by": loc.created_by,
            "created_at": loc.created_at.isoformat() if loc.created_at else None,
            "updated_at": loc.updated_at.isoformat() if loc.updated_at else None,
        }
