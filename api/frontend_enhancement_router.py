# -*- coding: utf-8 -*-
"""
Frontend Enhancement Router
===========================

API endpoints for frontend user experience enhancements including:
- User preference management
- Theme customization
- Dashboard configuration
- Report generation
- Responsive configuration
- Accessibility settings
"""

import logging
from typing import Any, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/frontend", tags=["前端增强"])
try:
    from core.frontend_enhancement import ThemeType, ViewMode, frontend_enhancement_manager

    FRONTEND_AVAILABLE = True
except ImportError:
    FRONTEND_AVAILABLE = False
    logger.warning("Frontend enhancement manager not available")


class UserPreferenceUpdateRequest(BaseModel):
    """Request for updating user preferences"""

    theme: Optional[str] = None
    language: Optional[str] = None
    timezone: Optional[str] = None
    date_format: Optional[str] = None
    time_format: Optional[str] = None
    view_mode: Optional[str] = None
    notifications_enabled: Optional[bool] = None
    notification_sound: Optional[bool] = None
    auto_refresh_interval: Optional[int] = None
    dashboard_layout: Optional[dict[str, Any]] = None
    custom_colors: Optional[dict[str, str]] = None
    accessibility_settings: Optional[dict[str, Any]] = None

    model_config = {
        "extra": "ignore",
        "json_schema_extra": {
            "example": {
                "theme": "example",
                "language": "example",
                "timezone": "example",
                "date_format": "example",
                "time_format": "example",
                "view_mode": "example",
                "notifications_enabled": True,
                "notification_sound": True,
                "auto_refresh_interval": 0,
                "dashboard_layout": "example",
                "custom_colors": "example",
                "accessibility_settings": "example",
            }
        },
    }


class CustomThemeRequest(BaseModel):
    """Request for creating custom theme"""

    theme_id: str
    name: str
    colors: dict[str, str]
    base_theme: str = "light"

    model_config = {
        "extra": "ignore",
        "json_schema_extra": {
            "example": {"theme_id": "example", "name": "example", "colors": {}},
            "base_theme": "example",
        },
    }


class DashboardWidgetRequest(BaseModel):
    """Request for adding dashboard widget"""

    dashboard_id: str
    widget_id: str
    widget_type: str
    title: str
    position: dict[str, int]
    config: Optional[dict[str, Any]] = None
    data_source: Optional[str] = None
    refresh_interval: int = 30

    model_config = {
        "extra": "ignore",
        "json_schema_extra": {
            "example": {
                "dashboard_id": "example",
                "widget_id": "example",
                "widget_type": "example",
                "title": "example",
                "position": {},
            },
            "config": "example",
            "data_source": "example",
            "refresh_interval": 0,
        },
    }


class ReportTemplateRequest(BaseModel):
    """Request for creating report template"""

    template_id: str
    name: str
    description: str
    data_sources: list[str]
    visualization_config: dict[str, Any]
    format: str = "pdf"
    schedule: Optional[str] = None
    created_by: str = "system"

    model_config = {
        "extra": "ignore",
        "json_schema_extra": {
            "example": {
                "template_id": "example",
                "name": "example",
                "description": "example",
                "data_sources": [],
                "visualization_config": {},
            },
            "format": "example",
            "schedule": "example",
            "created_by": "example",
        },
    }


class ReportGenerationRequest(BaseModel):
    """Request for generating report"""

    template_id: str
    filters: Optional[dict[str, Any]] = None

    model_config = {
        "extra": "ignore",
        "json_schema_extra": {"example": {"template_id": "example", "filters": "example"}},
    }


@router.get(
    "/preferences/{user_id}",
    summary="获取用户偏好",
    responses={
        (200): {
            "description": "用户偏好",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "preferences": {
                            "user_id": "user-123",
                            "theme": "light",
                            "language": "zh-CN",
                            "timezone": "Asia/Shanghai",
                        },
                    }
                }
            },
        },
        (503): {"description": "前端增强管理器不可用"},
    },
)
async def get_user_preferences(user_id: str) -> dict[str, Any]:
    """
    获取指定用户的偏好设置
    """
    if not FRONTEND_AVAILABLE:
        raise HTTPException(status_code=503, detail="前端增强管理器不可用")
    preferences = frontend_enhancement_manager.get_user_preferences(user_id)
    return {
        "status": "success",
        "preferences": {
            "user_id": preferences.user_id,
            "theme": preferences.theme.value,
            "language": preferences.language,
            "timezone": preferences.timezone,
            "date_format": preferences.date_format,
            "time_format": preferences.time_format,
            "view_mode": preferences.view_mode.value,
            "notifications_enabled": preferences.notifications_enabled,
            "notification_sound": preferences.notification_sound,
            "auto_refresh_interval": preferences.auto_refresh_interval,
            "dashboard_layout": preferences.dashboard_layout,
            "custom_colors": preferences.custom_colors,
            "accessibility_settings": preferences.accessibility_settings,
            "last_updated": preferences.last_updated.isoformat(),
        },
    }


@router.put(
    "/preferences/{user_id}",
    summary="更新用户偏好",
    responses={
        (200): {
            "description": "更新结果",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "preferences": {
                            "user_id": "user-123",
                            "theme": "dark",
                            "language": "en-US",
                        },
                    }
                }
            },
        },
        (503): {"description": "前端增强管理器不可用"},
    },
)
async def update_user_preferences(
    user_id: str, request: UserPreferenceUpdateRequest
) -> dict[str, Any]:
    """
    更新用户偏好设置
    """
    if not FRONTEND_AVAILABLE:
        raise HTTPException(status_code=503, detail="前端增强管理器不可用")
    updates = {k: v for k, v in request.dict().items() if v is not None}
    preferences = frontend_enhancement_manager.update_user_preferences(user_id, updates)
    return {
        "status": "success",
        "preferences": {
            "user_id": preferences.user_id,
            "theme": preferences.theme.value,
            "language": preferences.language,
            "timezone": preferences.timezone,
            "date_format": preferences.date_format,
            "time_format": preferences.time_format,
            "view_mode": preferences.view_mode.value,
            "notifications_enabled": preferences.notifications_enabled,
            "notification_sound": preferences.notification_sound,
            "auto_refresh_interval": preferences.auto_refresh_interval,
            "dashboard_layout": preferences.dashboard_layout,
            "custom_colors": preferences.custom_colors,
            "accessibility_settings": preferences.accessibility_settings,
            "last_updated": preferences.last_updated.isoformat(),
        },
    }


@router.get(
    "/preferences/{user_id}/export",
    summary="导出用户偏好",
    responses={
        (200): {
            "description": "导出结果",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "exported_data": {"theme": "light", "language": "zh-CN"},
                        "exported_at": "2026-07-03T09:00:00Z",
                    }
                }
            },
        },
        (503): {"description": "前端增强管理器不可用"},
    },
)
async def export_user_preferences(user_id: str) -> dict[str, Any]:
    """
    导出用户偏好设置为JSON
    """
    if not FRONTEND_AVAILABLE:
        raise HTTPException(status_code=503, detail="前端增强管理器不可用")
    preferences = frontend_enhancement_manager.export_user_preferences(user_id)
    return {"status": "success", "preferences": preferences}


@router.post(
    "/preferences/{user_id}/import",
    summary="导入用户偏好",
    responses={(200): {"description": "导入结果"}, (503): {"description": "前端增强管理器不可用"}},
)
async def import_user_preferences(user_id: str, preferences: dict[str, Any]) -> dict[str, Any]:
    """
    从JSON导入用户偏好设置
    """
    if not FRONTEND_AVAILABLE:
        raise HTTPException(status_code=503, detail="前端增强管理器不可用")
    imported_preferences = frontend_enhancement_manager.import_user_preferences(
        user_id, preferences
    )
    return {
        "status": "success",
        "preferences": {
            "user_id": imported_preferences.user_id,
            "theme": imported_preferences.theme.value,
            "language": imported_preferences.language,
            "timezone": imported_preferences.timezone,
            "last_updated": imported_preferences.last_updated.isoformat(),
        },
    }


@router.get(
    "/themes",
    summary="获取可用主题",
    responses={(200): {"description": "主题列表"}, (503): {"description": "前端增强管理器不可用"}},
)
async def get_available_themes() -> dict[str, Any]:
    """
    获取可用的主题列表
    """
    if not FRONTEND_AVAILABLE:
        raise HTTPException(status_code=503, detail="前端增强管理器不可用")
    themes: List[dict[str, Any]] = []
    for theme_type in ThemeType:
        config = frontend_enhancement_manager.get_theme_config(theme_type)
        themes.append({"type": theme_type.value, "config": config})
    return {
        "status": "success",
        "themes": themes,
        "custom_themes": frontend_enhancement_manager.custom_themes,
    }


@router.post(
    "/themes/custom",
    summary="创建自定义主题",
    responses={(200): {"description": "创建结果"}, (503): {"description": "前端增强管理器不可用"}},
)
async def create_custom_theme(request: CustomThemeRequest) -> dict[str, Any]:
    """
    创建自定义主题
    """
    if not FRONTEND_AVAILABLE:
        raise HTTPException(status_code=503, detail="前端增强管理器不可用")
    try:
        base_theme: ThemeType = ThemeType(request.base_theme)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"无效的基础主题: {request.base_theme}")
    custom_theme: dict[str, Any] = frontend_enhancement_manager.create_custom_theme(
        theme_id=request.theme_id, name=request.name, colors=request.colors, base_theme=base_theme
    )
    return {"status": "success", "custom_theme": custom_theme}


@router.get(
    "/dashboard/{dashboard_id}",
    summary="获取仪表板配置",
    responses={
        (200): {"description": "仪表板配置"},
        (503): {"description": "前端增强管理器不可用"},
    },
)
async def get_dashboard_config(dashboard_id: str) -> dict[str, Any]:
    """
    获取仪表板的小部件配置
    """
    if not FRONTEND_AVAILABLE:
        raise HTTPException(status_code=503, detail="前端增强管理器不可用")
    widgets: List[Any] = frontend_enhancement_manager.get_dashboard_config(dashboard_id)
    return {
        "status": "success",
        "dashboard_id": dashboard_id,
        "widgets": [
            {
                "widget_id": widget.widget_id,
                "widget_type": widget.widget_type,
                "title": widget.title,
                "position": widget.position,
                "config": widget.config,
                "data_source": widget.data_source,
                "refresh_interval": widget.refresh_interval,
                "enabled": widget.enabled,
            }
            for widget in widgets
        ],
    }


@router.post(
    "/dashboard/widget",
    summary="添加仪表板小部件",
    responses={(200): {"description": "添加结果"}, (503): {"description": "前端增强管理器不可用"}},
)
async def add_dashboard_widget(request: DashboardWidgetRequest) -> dict[str, Any]:
    """
    向仪表板添加小部件
    """
    if not FRONTEND_AVAILABLE:
        raise HTTPException(status_code=503, detail="前端增强管理器不可用")
    from core.frontend_enhancement import DashboardWidget

    widget = DashboardWidget(
        widget_id=request.widget_id,
        widget_type=request.widget_type,
        title=request.title,
        position=request.position,
        config=request.config or {},
        data_source=request.data_source,
        refresh_interval=request.refresh_interval,
    )
    added_widget = frontend_enhancement_manager.add_dashboard_widget(request.dashboard_id, widget)
    return {
        "status": "success",
        "widget": {
            "widget_id": added_widget.widget_id,
            "widget_type": added_widget.widget_type,
            "title": added_widget.title,
            "position": added_widget.position,
        },
    }


@router.delete(
    "/dashboard/{dashboard_id}/widget/{widget_id}",
    summary="删除仪表板小部件",
    responses={
        (200): {"description": "删除结果"},
        (404): {"description": "小部件未找到"},
        (503): {"description": "前端增强管理器不可用"},
    },
)
async def remove_dashboard_widget(dashboard_id: str, widget_id: str) -> dict[str, Any]:
    """
    从仪表板删除小部件
    """
    if not FRONTEND_AVAILABLE:
        raise HTTPException(status_code=503, detail="前端增强管理器不可用")
    removed = frontend_enhancement_manager.remove_dashboard_widget(dashboard_id, widget_id)
    if not removed:
        raise HTTPException(status_code=404, detail="小部件未找到")
    return {"status": "success", "message": f"小部件 {widget_id} 已删除"}


@router.put(
    "/dashboard/{dashboard_id}/widget/{widget_id}",
    summary="更新仪表板小部件",
    responses={
        (200): {"description": "更新结果"},
        (404): {"description": "小部件未找到"},
        (503): {"description": "前端增强管理器不可用"},
    },
)
async def update_dashboard_widget(
    dashboard_id: str, widget_id: str, updates: dict[str, Any]
) -> dict[str, Any]:
    """
    更新仪表板小部件
    """
    if not FRONTEND_AVAILABLE:
        raise HTTPException(status_code=503, detail="前端增强管理器不可用")
    updated_widget = frontend_enhancement_manager.update_dashboard_widget(
        dashboard_id, widget_id, updates
    )
    if not updated_widget:
        raise HTTPException(status_code=404, detail="小部件未找到")
    return {
        "status": "success",
        "widget": {
            "widget_id": updated_widget.widget_id,
            "widget_type": updated_widget.widget_type,
            "title": updated_widget.title,
            "position": updated_widget.position,
            "config": updated_widget.config,
            "refresh_interval": updated_widget.refresh_interval,
            "enabled": updated_widget.enabled,
        },
    }


@router.post(
    "/reports/templates",
    summary="创建报告模板",
    responses={(200): {"description": "创建结果"}, (503): {"description": "前端增强管理器不可用"}},
)
async def create_report_template(request: ReportTemplateRequest) -> dict[str, Any]:
    """
    创建报告模板
    """
    if not FRONTEND_AVAILABLE:
        raise HTTPException(status_code=503, detail="前端增强管理器不可用")
    template = frontend_enhancement_manager.create_report_template(
        template_id=request.template_id,
        name=request.name,
        description=request.description,
        data_sources=request.data_sources,
        visualization_config=request.visualization_config,
        format=request.format,
        schedule=request.schedule,
        created_by=request.created_by,
    )
    return {
        "status": "success",
        "template": {
            "template_id": template.template_id,
            "name": template.name,
            "description": template.description,
            "data_sources": template.data_sources,
            "format": template.format,
            "schedule": template.schedule,
            "created_by": template.created_by,
            "created_at": template.created_at.isoformat(),
        },
    }


@router.get(
    "/reports/templates",
    summary="获取报告模板列表",
    responses={(200): {"description": "模板列表"}, (503): {"description": "前端增强管理器不可用"}},
)
async def get_report_templates() -> dict[str, Any]:
    """
    获取所有报告模板
    """
    if not FRONTEND_AVAILABLE:
        raise HTTPException(status_code=503, detail="前端增强管理器不可用")
    templates = []
    for template in frontend_enhancement_manager.report_templates.values():
        templates.append(
            {
                "template_id": template.template_id,
                "name": template.name,
                "description": template.description,
                "data_sources": template.data_sources,
                "format": template.format,
                "schedule": template.schedule,
                "created_by": template.created_by,
                "created_at": template.created_at.isoformat(),
            }
        )
    return {"status": "success", "templates": templates}


@router.post(
    "/reports/generate",
    summary="生成报告",
    responses={(200): {"description": "生成结果"}, (503): {"description": "前端增强管理器不可用"}},
)
async def generate_report(request: ReportGenerationRequest) -> dict[str, Any]:
    """
    根据模板生成报告
    """
    if not FRONTEND_AVAILABLE:
        raise HTTPException(status_code=503, detail="前端增强管理器不可用")
    report = frontend_enhancement_manager.generate_report(
        template_id=request.template_id, filters=request.filters
    )
    if "error" in report:
        raise HTTPException(status_code=400, detail=report["error"])
    return {"status": "success", "report": report}


@router.get(
    "/responsive/{viewport_width}",
    summary="获取响应式配置",
    responses={
        (200): {"description": "响应式配置"},
        (503): {"description": "前端增强管理器不可用"},
    },
)
async def get_responsive_config(viewport_width: int) -> dict[str, Any]:
    """
    根据视口宽度获取响应式配置
    """
    if not FRONTEND_AVAILABLE:
        raise HTTPException(status_code=503, detail="前端增强管理器不可用")
    config = frontend_enhancement_manager.get_responsive_config(viewport_width)
    return {"status": "success", "viewport_width": viewport_width, "responsive_config": config}


@router.get(
    "/accessibility/{user_id}",
    summary="获取无障碍设置",
    responses={
        (200): {"description": "无障碍设置"},
        (503): {"description": "前端增强管理器不可用"},
    },
)
async def get_accessibility_settings(user_id: str) -> dict[str, Any]:
    """
    获取用户的无障碍设置
    """
    if not FRONTEND_AVAILABLE:
        raise HTTPException(status_code=503, detail="前端增强管理器不可用")
    settings = frontend_enhancement_manager.get_accessibility_settings(user_id)
    return {"status": "success", "accessibility_settings": settings}


@router.put("/accessibility/{user_id}", summary="更新无障碍设置")
async def update_accessibility_settings(user_id: str, settings: dict[str, Any]) -> dict[str, Any]:
    """
    更新用户的无障碍设置
    """
    if not FRONTEND_AVAILABLE:
        raise HTTPException(status_code=503, detail="前端增强管理器不可用")
    # Update accessibility settings
    manager = frontend_enhancement_manager
    updated_settings = manager.update_accessibility_settings(user_id, settings)
    return {"status": "success", "accessibility_settings": updated_settings}


@router.get(
    "/summary",
    summary="获取前端增强摘要",
    responses={
        (200): {"description": "前端增强摘要"},
        (503): {"description": "前端增强管理器不可用"},
    },
)
async def get_frontend_summary() -> dict[str, Any]:
    """
    获取前端增强功能的摘要信息
    """
    if not FRONTEND_AVAILABLE:
        raise HTTPException(status_code=503, detail="前端增强管理器不可用")
    summary = frontend_enhancement_manager.get_frontend_summary()
    return {"status": "success", "frontend_summary": summary}


@router.get(
    "/view-modes",
    summary="获取支持的视图模式",
    responses={
        (200): {"description": "视图模式列表"},
        (503): {"description": "前端增强管理器不可用"},
    },
)
async def get_view_modes() -> dict[str, Any]:
    """
    获取支持的视图模式列表
    """
    view_modes = [mode.value for mode in ViewMode]
    return {"status": "success", "view_modes": view_modes}


@router.get(
    "/breakpoints",
    summary="获取响应式断点",
    responses={(200): {"description": "断点列表"}, (503): {"description": "前端增强管理器不可用"}},
)
async def get_responsive_breakpoints() -> dict[str, Any]:
    """
    获取响应式设计断点
    """
    if not FRONTEND_AVAILABLE:
        raise HTTPException(status_code=503, detail="前端增强管理器不可用")
    breakpoints = frontend_enhancement_manager.responsive_breakpoints
    return {"status": "success", "breakpoints": breakpoints}
