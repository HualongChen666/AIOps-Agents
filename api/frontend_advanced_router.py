# -*- coding: utf-8 -*-
"""
Frontend Advanced API Router
=============================

Advanced API endpoints for frontend enhancements including:
- Component management (CRUD)
- Theme management (CRUD)
- Layout management (CRUD)
- Localization management
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, status
from loguru import logger
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/v1/frontend", tags=["前端增强"])

# Try to import frontend enhancement manager
try:
    from core.frontend_enhancement import (
        ThemeType,
        frontend_enhancement_manager,
    )

    FRONTEND_AVAILABLE = True
except ImportError:
    FRONTEND_AVAILABLE = False
    logger.warning("Frontend enhancement manager not available")


# Pydantic Models
class ComponentCreate(BaseModel):
    """Request model for creating a component"""

    component_id: Optional[str] = Field(
        None, description="Component ID (auto-generated if not provided)"
    )
    name: str = Field(..., description="Component name")
    type: str = Field(..., description="Component type")
    category: str = Field(..., description="Component category")
    description: str = Field(..., description="Component description")
    props: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Component props")
    code: str = Field(..., description="Component code")
    dependencies: Optional[List[str]] = Field(
        default_factory=list, description="Component dependencies"
    )
    is_public: bool = Field(default=False, description="Is public component")

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "CustomButton",
                "type": "button",
                "category": "ui",
                "description": "A custom button component",
                "code": "export const CustomButton = () => { ... }",
                "is_public": True,
            }
        }
    }


class ComponentUpdate(BaseModel):
    """Request model for updating a component"""

    name: Optional[str] = Field(None, description="Component name")
    description: Optional[str] = Field(None, description="Component description")
    props: Optional[Dict[str, Any]] = Field(None, description="Component props")
    code: Optional[str] = Field(None, description="Component code")
    dependencies: Optional[List[str]] = Field(None, description="Component dependencies")
    is_public: Optional[bool] = Field(None, description="Is public component")
    status: Optional[str] = Field(None, description="Component status")

    model_config = {
        "json_schema_extra": {"example": {"description": "Updated description", "status": "active"}}
    }


class ThemeCreate(BaseModel):
    """Request model for creating a theme"""

    theme_id: Optional[str] = Field(None, description="Theme ID (auto-generated if not provided)")
    name: str = Field(..., description="Theme name")
    base_theme: str = Field(default="light", description="Base theme (light, dark)")
    colors: Dict[str, str] = Field(..., description="Color palette")
    fonts: Optional[Dict[str, str]] = Field(default_factory=dict, description="Font settings")
    spacing: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Spacing settings")
    is_default: bool = Field(default=False, description="Is default theme")

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Custom Blue",
                "base_theme": "light",
                "colors": {
                    "primary": "#3b82f6",
                    "secondary": "#6366f1",
                    "background": "#ffffff",
                    "text": "#1f2937",
                },
            }
        }
    }


class ThemeUpdate(BaseModel):
    """Request model for updating a theme"""

    name: Optional[str] = Field(None, description="Theme name")
    colors: Optional[Dict[str, str]] = Field(None, description="Color palette")
    fonts: Optional[Dict[str, str]] = Field(None, description="Font settings")
    spacing: Optional[Dict[str, Any]] = Field(None, description="Spacing settings")
    is_default: Optional[bool] = Field(None, description="Is default theme")

    model_config = {
        "json_schema_extra": {
            "example": {"name": "Updated Theme", "colors": {"primary": "#8b5cf6"}}
        }
    }


class LayoutCreate(BaseModel):
    """Request model for creating a layout"""

    layout_id: Optional[str] = Field(None, description="Layout ID (auto-generated if not provided)")
    name: str = Field(..., description="Layout name")
    type: str = Field(..., description="Layout type (dashboard, page, modal, etc.)")
    structure: Dict[str, Any] = Field(..., description="Layout structure")
    breakpoints: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Responsive breakpoints"
    )
    is_default: bool = Field(default=False, description="Is default layout")

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Main Dashboard",
                "type": "dashboard",
                "structure": {
                    "header": {"height": 64},
                    "sidebar": {"width": 240},
                    "content": {"flex": 1},
                },
                "breakpoints": {"mobile": {"sidebar": {"width": 0}}},
            }
        }
    }


class LayoutUpdate(BaseModel):
    """Request model for updating a layout"""

    name: Optional[str] = Field(None, description="Layout name")
    structure: Optional[Dict[str, Any]] = Field(None, description="Layout structure")
    breakpoints: Optional[Dict[str, Any]] = Field(None, description="Responsive breakpoints")
    is_default: Optional[bool] = Field(None, description="Is default layout")

    model_config = {
        "json_schema_extra": {
            "example": {"name": "Updated Layout", "structure": {"header": {"height": 72}}}
        }
    }


class LocalizationUpdate(BaseModel):
    """Request model for updating localization"""

    language: str = Field(..., description="Language code (e.g., en-US, zh-CN)")
    translations: Dict[str, str] = Field(..., description="Translation key-value pairs")

    model_config = {
        "json_schema_extra": {
            "example": {
                "language": "zh-CN",
                "translations": {"welcome": "欢迎", "dashboard": "仪表板"},
            }
        }
    }


# In-memory storage
components: Dict[str, Dict[str, Any]] = {}
themes: Dict[str, Dict[str, Any]] = {}
layouts: Dict[str, Dict[str, Any]] = {}
localization: Dict[str, Dict[str, str]] = {
    "en-US": {
        "welcome": "Welcome",
        "dashboard": "Dashboard",
        "settings": "Settings",
        "logout": "Logout",
    },
    "zh-CN": {"welcome": "欢迎", "dashboard": "仪表板", "settings": "设置", "logout": "退出"},
}


@router.get(
    "/components",
    summary="列出所有组件",
    responses={
        200: {"description": "组件列表"},
        500: {"description": "获取失败"},
    },
)
async def list_components(
    type: Optional[str] = Query(None, description="按组件类型过滤"),
    category: Optional[str] = Query(None, description="按分类过滤"),
    is_public: Optional[bool] = Query(None, description="是否为公共组件"),
    status: Optional[str] = Query(None, description="按状态过滤"),
    limit: int = Query(default=100, ge=1, le=500, description="返回数量限制"),
    offset: int = Query(default=0, ge=0, description="偏移量"),
) -> Dict[str, Any]:
    """
    获取组件列表，支持过滤和分页
    """
    try:
        filtered_components = list(components.values())

        # Apply filters
        if type:
            filtered_components = [c for c in filtered_components if c.get("type") == type]
        if category:
            filtered_components = [c for c in filtered_components if c.get("category") == category]
        if is_public is not None:
            filtered_components = [
                c for c in filtered_components if c.get("is_public") == is_public
            ]
        if status:
            filtered_components = [c for c in filtered_components if c.get("status") == status]

        # Apply pagination
        total = len(filtered_components)
        paginated_components = filtered_components[offset : offset + limit]

        return {
            "status": "success",
            "data": {
                "components": paginated_components,
                "total": total,
                "limit": limit,
                "offset": offset,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error listing components: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/components",
    summary="创建新组件",
    responses={
        201: {"description": "组件创建成功"},
        400: {"description": "请求参数错误"},
        500: {"description": "创建失败"},
    },
    status_code=status.HTTP_201_CREATED,
)
async def create_component(request: ComponentCreate) -> Dict[str, Any]:
    """
    创建新组件
    """
    try:
        # Generate component_id if not provided
        component_id = request.component_id or f"comp-{uuid4().hex[:8]}"

        # Check if component already exists
        if component_id in components:
            raise HTTPException(status_code=400, detail="组件ID已存在")

        # Create component
        component = {
            "component_id": component_id,
            "name": request.name,
            "type": request.type,
            "category": request.category,
            "description": request.description,
            "props": request.props or {},
            "code": request.code,
            "dependencies": request.dependencies or [],
            "is_public": request.is_public,
            "status": "active",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

        components[component_id] = component

        return {"status": "success", "data": component, "timestamp": datetime.utcnow().isoformat()}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating component: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/components/{component_id}",
    summary="获取组件详情",
    responses={
        200: {"description": "组件详情"},
        404: {"description": "组件未找到"},
        500: {"description": "获取失败"},
    },
)
async def get_component(component_id: str) -> Dict[str, Any]:
    """
    根据ID获取组件详情
    """
    try:
        component = components.get(component_id)
        if not component:
            raise HTTPException(status_code=404, detail="组件未找到")

        return {"status": "success", "data": component, "timestamp": datetime.utcnow().isoformat()}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting component: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch(
    "/components/{component_id}",
    summary="更新组件",
    responses={
        200: {"description": "组件更新成功"},
        404: {"description": "组件未找到"},
        400: {"description": "请求参数错误"},
        500: {"description": "更新失败"},
    },
)
async def update_component(component_id: str, request: ComponentUpdate) -> Dict[str, Any]:
    """
    更新组件信息
    """
    try:
        component = components.get(component_id)
        if not component:
            raise HTTPException(status_code=404, detail="组件未找到")

        # Update fields
        if request.name is not None:
            component["name"] = request.name
        if request.description is not None:
            component["description"] = request.description
        if request.props is not None:
            component["props"].update(request.props)
        if request.code is not None:
            component["code"] = request.code
        if request.dependencies is not None:
            component["dependencies"] = request.dependencies
        if request.is_public is not None:
            component["is_public"] = request.is_public
        if request.status is not None:
            component["status"] = request.status

        component["updated_at"] = datetime.utcnow().isoformat()

        return {"status": "success", "data": component, "timestamp": datetime.utcnow().isoformat()}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating component: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete(
    "/components/{component_id}",
    summary="删除组件",
    responses={
        200: {"description": "组件删除成功"},
        404: {"description": "组件未找到"},
        500: {"description": "删除失败"},
    },
)
async def delete_component(component_id: str) -> Dict[str, Any]:
    """
    删除组件
    """
    try:
        component = components.get(component_id)
        if not component:
            raise HTTPException(status_code=404, detail="组件未找到")

        # Delete component
        del components[component_id]

        return {
            "status": "success",
            "data": {"component_id": component_id, "deleted": True},
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting component: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/themes",
    summary="列出所有主题",
    responses={
        200: {"description": "主题列表"},
        500: {"description": "获取失败"},
    },
)
async def list_themes(
    base_theme: Optional[str] = Query(None, description="按基础主题过滤"),
    is_default: Optional[bool] = Query(None, description="是否为默认主题"),
    limit: int = Query(default=100, ge=1, le=500, description="返回数量限制"),
    offset: int = Query(default=0, ge=0, description="偏移量"),
) -> Dict[str, Any]:
    """
    获取主题列表，支持过滤和分页
    """
    try:
        filtered_themes = list(themes.values())

        # Apply filters
        if base_theme:
            filtered_themes = [t for t in filtered_themes if t.get("base_theme") == base_theme]
        if is_default is not None:
            filtered_themes = [t for t in filtered_themes if t.get("is_default") == is_default]

        # Apply pagination
        total = len(filtered_themes)
        paginated_themes = filtered_themes[offset : offset + limit]

        # Add built-in themes from frontend enhancement manager if available
        built_in_themes = []
        if FRONTEND_AVAILABLE:
            for theme_type in ThemeType:
                config = frontend_enhancement_manager.get_theme_config(theme_type)
                built_in_themes.append(
                    {
                        "theme_id": f"builtin-{theme_type.value}",
                        "name": f"Built-in {theme_type.value.title()}",
                        "base_theme": theme_type.value,
                        "colors": config,
                        "is_builtin": True,
                    }
                )

        return {
            "status": "success",
            "data": {
                "themes": paginated_themes,
                "built_in_themes": built_in_themes,
                "total": total,
                "limit": limit,
                "offset": offset,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error listing themes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/themes",
    summary="创建新主题",
    responses={
        201: {"description": "主题创建成功"},
        400: {"description": "请求参数错误"},
        500: {"description": "创建失败"},
    },
    status_code=status.HTTP_201_CREATED,
)
async def create_theme(request: ThemeCreate) -> Dict[str, Any]:
    """
    创建新主题
    """
    try:
        # Generate theme_id if not provided
        theme_id = request.theme_id or f"theme-{uuid4().hex[:8]}"

        # Check if theme already exists
        if theme_id in themes:
            raise HTTPException(status_code=400, detail="主题ID已存在")

        # Create theme
        theme = {
            "theme_id": theme_id,
            "name": request.name,
            "base_theme": request.base_theme,
            "colors": request.colors,
            "fonts": request.fonts or {},
            "spacing": request.spacing or {},
            "is_default": request.is_default,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

        themes[theme_id] = theme

        # Add to frontend enhancement manager if available
        if FRONTEND_AVAILABLE:
            try:
                base_theme_enum = ThemeType(request.base_theme)
                frontend_enhancement_manager.create_custom_theme(
                    theme_id=theme_id,
                    name=request.name,
                    colors=request.colors,
                    base_theme=base_theme_enum,
                )
            except ValueError:
                pass  # Ignore if base_theme is invalid

        return {"status": "success", "data": theme, "timestamp": datetime.utcnow().isoformat()}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating theme: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/layouts",
    summary="列出所有布局",
    responses={
        200: {"description": "布局列表"},
        500: {"description": "获取失败"},
    },
)
async def list_layouts(
    type: Optional[str] = Query(None, description="按布局类型过滤"),
    is_default: Optional[bool] = Query(None, description="是否为默认布局"),
    limit: int = Query(default=100, ge=1, le=500, description="返回数量限制"),
    offset: int = Query(default=0, ge=0, description="偏移量"),
) -> Dict[str, Any]:
    """
    获取布局列表，支持过滤和分页
    """
    try:
        filtered_layouts = list(layouts.values())

        # Apply filters
        if type:
            filtered_layouts = [l for l in filtered_layouts if l.get("type") == type]
        if is_default is not None:
            filtered_layouts = [l for l in filtered_layouts if l.get("is_default") == is_default]

        # Apply pagination
        total = len(filtered_layouts)
        paginated_layouts = filtered_layouts[offset : offset + limit]

        return {
            "status": "success",
            "data": {
                "layouts": paginated_layouts,
                "total": total,
                "limit": limit,
                "offset": offset,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error listing layouts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/layouts",
    summary="创建新布局",
    responses={
        201: {"description": "布局创建成功"},
        400: {"description": "请求参数错误"},
        500: {"description": "创建失败"},
    },
    status_code=status.HTTP_201_CREATED,
)
async def create_layout(request: LayoutCreate) -> Dict[str, Any]:
    """
    创建新布局
    """
    try:
        # Generate layout_id if not provided
        layout_id = request.layout_id or f"layout-{uuid4().hex[:8]}"

        # Check if layout already exists
        if layout_id in layouts:
            raise HTTPException(status_code=400, detail="布局ID已存在")

        # Create layout
        layout = {
            "layout_id": layout_id,
            "name": request.name,
            "type": request.type,
            "structure": request.structure,
            "breakpoints": request.breakpoints or {},
            "is_default": request.is_default,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

        layouts[layout_id] = layout

        return {"status": "success", "data": layout, "timestamp": datetime.utcnow().isoformat()}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating layout: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/layouts/{layout_id}",
    summary="获取布局详情",
    responses={
        200: {"description": "布局详情"},
        404: {"description": "布局未找到"},
        500: {"description": "获取失败"},
    },
)
async def get_layout(layout_id: str) -> Dict[str, Any]:
    """
    根据ID获取布局详情
    """
    try:
        layout = layouts.get(layout_id)
        if not layout:
            raise HTTPException(status_code=404, detail="布局未找到")

        return {"status": "success", "data": layout, "timestamp": datetime.utcnow().isoformat()}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting layout: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch(
    "/layouts/{layout_id}",
    summary="更新布局",
    responses={
        200: {"description": "布局更新成功"},
        404: {"description": "布局未找到"},
        400: {"description": "请求参数错误"},
        500: {"description": "更新失败"},
    },
)
async def update_layout(layout_id: str, request: LayoutUpdate) -> Dict[str, Any]:
    """
    更新布局信息
    """
    try:
        layout = layouts.get(layout_id)
        if not layout:
            raise HTTPException(status_code=404, detail="布局未找到")

        # Update fields
        if request.name is not None:
            layout["name"] = request.name
        if request.structure is not None:
            layout["structure"].update(request.structure)
        if request.breakpoints is not None:
            layout["breakpoints"].update(request.breakpoints)
        if request.is_default is not None:
            layout["is_default"] = request.is_default

        layout["updated_at"] = datetime.utcnow().isoformat()

        return {"status": "success", "data": layout, "timestamp": datetime.utcnow().isoformat()}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating layout: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete(
    "/layouts/{layout_id}",
    summary="删除布局",
    responses={
        200: {"description": "布局删除成功"},
        404: {"description": "布局未找到"},
        500: {"description": "删除失败"},
    },
)
async def delete_layout(layout_id: str) -> Dict[str, Any]:
    """
    删除布局
    """
    try:
        layout = layouts.get(layout_id)
        if not layout:
            raise HTTPException(status_code=404, detail="布局未找到")

        # Delete layout
        del layouts[layout_id]

        return {
            "status": "success",
            "data": {"layout_id": layout_id, "deleted": True},
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting layout: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/localization",
    summary="获取本地化设置",
    responses={
        200: {"description": "本地化设置"},
        500: {"description": "获取失败"},
    },
)
async def get_localization(
    language: Optional[str] = Query(None, description="语言代码")
) -> Dict[str, Any]:
    """
    获取本地化翻译
    """
    try:
        if language:
            translations = localization.get(language, {})
            return {
                "status": "success",
                "data": {"language": language, "translations": translations},
                "timestamp": datetime.utcnow().isoformat(),
            }
        else:
            return {
                "status": "success",
                "data": {
                    "available_languages": list(localization.keys()),
                    "localization": localization,
                },
                "timestamp": datetime.utcnow().isoformat(),
            }
    except Exception as e:
        logger.error(f"Error getting localization: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch(
    "/localization",
    summary="更新本地化设置",
    responses={
        200: {"description": "本地化设置更新成功"},
        400: {"description": "请求参数错误"},
        500: {"description": "更新失败"},
    },
)
async def update_localization(request: LocalizationUpdate) -> Dict[str, Any]:
    """
    更新本地化翻译
    """
    try:
        # Initialize language if not exists
        if request.language not in localization:
            localization[request.language] = {}

        # Update translations
        localization[request.language].update(request.translations)

        return {
            "status": "success",
            "data": {"language": request.language, "translations": localization[request.language]},
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error updating localization: {e}")
        raise HTTPException(status_code=500, detail=str(e))
