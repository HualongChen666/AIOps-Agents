# -*- coding: utf-8 -*-
"""
Frontend Advanced API Router
=============================

Advanced API endpoints for frontend enhancements including:
- Component management (CRUD)
- Theme management (CRUD)
- Layout management (CRUD)
- Localization management

Features:
- Database persistence via Repository pattern
- JWT authentication
- RBAC authorization
- Rate limiting
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.repositories.frontend_repository_impl import FrontendRepositoryImpl
from api.middleware.auth_middleware import get_current_active_user
from api.middleware.rbac_auth_middleware import require_permission
from core.models import User

router = APIRouter(prefix="/api/v1/frontend", tags=["前端增强"])

# Rate limiting configuration
from slowapi import Limiter
from slowapi.util import get_remote_address
limiter = Limiter(key_func=get_remote_address)


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


# Repository dependency
async def get_frontend_repository(db: AsyncSession = Depends(get_db)) -> FrontendRepositoryImpl:
    """获取Frontend Repository实例"""
    return FrontendRepositoryImpl(session=db)


@router.get(
    "/components",
    summary="列出所有组件",
    responses={
        200: {"description": "组件列表"},
        401: {"description": "未认证"},
        403: {"description": "权限不足"},
        500: {"description": "获取失败"},
    },
)
@limiter.limit("100/minute")
async def list_components(
    type: Optional[str] = Query(None, description="按组件类型过滤"),
    category: Optional[str] = Query(None, description="按分类过滤"),
    is_public: Optional[bool] = Query(None, description="是否为公共组件"),
    status: Optional[str] = Query(None, description="按状态过滤"),
    limit: int = Query(default=100, ge=1, le=500, description="返回数量限制"),
    offset: int = Query(default=0, ge=0, description="偏移量"),
    current_user: User = Depends(require_permission("components:read")),
    repo: FrontendRepositoryImpl = Depends(get_frontend_repository),
) -> Dict[str, Any]:
    """
    获取组件列表，支持过滤和分页
    """
    try:
        filters = {}
        if type:
            filters["type"] = type
        if category:
            filters["category"] = category
        if is_public is not None:
            filters["is_public"] = is_public
        if status:
            filters["status"] = status

        components = await repo.list_components(filters=filters, limit=limit, offset=offset)
        total = await repo.count_components(filters=filters)

        return {
            "status": "success",
            "data": {
                "components": components,
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
        401: {"description": "未认证"},
        403: {"description": "权限不足"},
        500: {"description": "创建失败"},
    },
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("20/minute")
async def create_component(
    request: ComponentCreate,
    current_user: User = Depends(require_permission("components:write")),
    repo: FrontendRepositoryImpl = Depends(get_frontend_repository),
) -> Dict[str, Any]:
    """
    创建新组件
    """
    try:
        # Generate component_id if not provided
        component_id = request.component_id or f"comp-{uuid4().hex[:8]}"

        # Create component data
        component_data = {
            "id": component_id,
            "name": request.name,
            "type": request.type,
            "category": request.category,
            "description": request.description,
            "props": request.props or {},
            "code": request.code,
            "dependencies": request.dependencies or [],
            "is_public": request.is_public,
            "status": "active",
            "created_by": current_user.username,
        }

        created_id = await repo.create_component(component_data)
        component = await repo.get_component(created_id)

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
        401: {"description": "未认证"},
        403: {"description": "权限不足"},
        404: {"description": "组件未找到"},
        500: {"description": "获取失败"},
    },
)
@limiter.limit("100/minute")
async def get_component(
    component_id: str,
    current_user: User = Depends(require_permission("components:read")),
    repo: FrontendRepositoryImpl = Depends(get_frontend_repository),
) -> Dict[str, Any]:
    """
    根据ID获取组件详情
    """
    try:
        component = await repo.get_component(component_id)
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
        401: {"description": "未认证"},
        403: {"description": "权限不足"},
        500: {"description": "更新失败"},
    },
)
@limiter.limit("50/minute")
async def update_component(
    component_id: str,
    request: ComponentUpdate,
    current_user: User = Depends(require_permission("components:write")),
    repo: FrontendRepositoryImpl = Depends(get_frontend_repository),
) -> Dict[str, Any]:
    """
    更新组件信息
    """
    try:
        updates = {}
        if request.name is not None:
            updates["name"] = request.name
        if request.description is not None:
            updates["description"] = request.description
        if request.props is not None:
            updates["props"] = request.props
        if request.code is not None:
            updates["code"] = request.code
        if request.dependencies is not None:
            updates["dependencies"] = request.dependencies
        if request.is_public is not None:
            updates["is_public"] = request.is_public
        if request.status is not None:
            updates["status"] = request.status

        success = await repo.update_component(component_id, updates)
        if not success:
            raise HTTPException(status_code=404, detail="组件未找到")

        component = await repo.get_component(component_id)
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
        401: {"description": "未认证"},
        403: {"description": "权限不足"},
        500: {"description": "删除失败"},
    },
)
@limiter.limit("20/minute")
async def delete_component(
    component_id: str,
    current_user: User = Depends(require_permission("components:write")),
    repo: FrontendRepositoryImpl = Depends(get_frontend_repository),
) -> Dict[str, Any]:
    """
    删除组件
    """
    try:
        success = await repo.delete_component(component_id)
        if not success:
            raise HTTPException(status_code=404, detail="组件未找到")

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
        401: {"description": "未认证"},
        403: {"description": "权限不足"},
        500: {"description": "获取失败"},
    },
)
@limiter.limit("100/minute")
async def list_themes(
    base_theme: Optional[str] = Query(None, description="按基础主题过滤"),
    is_default: Optional[bool] = Query(None, description="是否为默认主题"),
    limit: int = Query(default=100, ge=1, le=500, description="返回数量限制"),
    offset: int = Query(default=0, ge=0, description="偏移量"),
    current_user: User = Depends(require_permission("themes:read")),
    repo: FrontendRepositoryImpl = Depends(get_frontend_repository),
) -> Dict[str, Any]:
    """
    获取主题列表，支持过滤和分页
    """
    try:
        filters = {}
        if base_theme:
            filters["base_theme"] = base_theme
        if is_default is not None:
            filters["is_default"] = is_default

        themes = await repo.list_themes(filters=filters, limit=limit, offset=offset)
        total = await repo.count_themes(filters=filters)

        return {
            "status": "success",
            "data": {
                "themes": themes,
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
        401: {"description": "未认证"},
        403: {"description": "权限不足"},
        500: {"description": "创建失败"},
    },
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("20/minute")
async def create_theme(
    request: ThemeCreate,
    current_user: User = Depends(require_permission("themes:write")),
    repo: FrontendRepositoryImpl = Depends(get_frontend_repository),
) -> Dict[str, Any]:
    """
    创建新主题
    """
    try:
        theme_id = request.theme_id or f"theme-{uuid4().hex[:8]}"

        theme_data = {
            "id": theme_id,
            "name": request.name,
            "base_theme": request.base_theme,
            "colors": request.colors,
            "fonts": request.fonts or {},
            "spacing": request.spacing or {},
            "is_default": request.is_default,
            "created_by": current_user.username,
        }

        created_id = await repo.create_theme(theme_data)
        theme = await repo.get_theme(created_id)

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
        401: {"description": "未认证"},
        403: {"description": "权限不足"},
        500: {"description": "获取失败"},
    },
)
@limiter.limit("100/minute")
async def list_layouts(
    type: Optional[str] = Query(None, description="按布局类型过滤"),
    is_default: Optional[bool] = Query(None, description="是否为默认布局"),
    limit: int = Query(default=100, ge=1, le=500, description="返回数量限制"),
    offset: int = Query(default=0, ge=0, description="偏移量"),
    current_user: User = Depends(require_permission("layouts:read")),
    repo: FrontendRepositoryImpl = Depends(get_frontend_repository),
) -> Dict[str, Any]:
    """
    获取布局列表，支持过滤和分页
    """
    try:
        filters = {}
        if type:
            filters["type"] = type
        if is_default is not None:
            filters["is_default"] = is_default

        layouts = await repo.list_layouts(filters=filters, limit=limit, offset=offset)
        total = await repo.count_layouts(filters=filters)

        return {
            "status": "success",
            "data": {
                "layouts": layouts,
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
        401: {"description": "未认证"},
        403: {"description": "权限不足"},
        500: {"description": "创建失败"},
    },
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("20/minute")
async def create_layout(
    request: LayoutCreate,
    current_user: User = Depends(require_permission("layouts:write")),
    repo: FrontendRepositoryImpl = Depends(get_frontend_repository),
) -> Dict[str, Any]:
    """
    创建新布局
    """
    try:
        layout_id = request.layout_id or f"layout-{uuid4().hex[:8]}"

        layout_data = {
            "id": layout_id,
            "name": request.name,
            "type": request.type,
            "structure": request.structure,
            "breakpoints": request.breakpoints or {},
            "is_default": request.is_default,
            "created_by": current_user.username,
        }

        created_id = await repo.create_layout(layout_data)
        layout = await repo.get_layout(created_id)

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
