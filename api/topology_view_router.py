# -*- coding: utf-8 -*-
"""
拓扑视图管理 API 路由

提供拓扑视图的 CRUD 操作，包括创建、查询、更新和删除拓扑视图。
"""

import logging
import re
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, field_validator

from core.topology_engine import (
    create_topology_view,
    delete_topology_view,
    get_all_topology_views,
    get_topology_view,
    update_topology_view,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/topology/view", tags=["拓扑视图管理"])
_VALID_VIEW_ID_PATTERN = re.compile("^[a-zA-Z0-9._\\-]+$")


# Pydantic Models for Request/Response Validation


class TopologyViewCreateRequest(BaseModel):
    """创建拓扑视图的请求模型"""

    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="视图名称",
        examples=["服务依赖视图"],
    )
    description: str = Field(
        default="",
        max_length=500,
        description="视图描述",
        examples=["展示微服务之间的依赖关系"],
    )
    view_type: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="视图类型",
        examples=["service", "network", "application"],
    )
    config: dict = Field(
        default_factory=dict,
        description="视图配置（过滤规则、布局设置等）",
        examples=[{"filters": {"environment": "production"}, "layout": "force"}],
    )
    created_by: str = Field(
        default="system",
        max_length=50,
        description="创建者用户名",
        examples=["admin"],
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("name 不能为空")
        return v

    @field_validator("view_type")
    @classmethod
    def validate_view_type(cls, v: str) -> str:
        v = v.strip().lower()
        valid_types = {"service", "network", "application", "infrastructure", "custom"}
        if v not in valid_types:
            raise ValueError(f"view_type 必须是以下之一: {', '.join(valid_types)}")
        return v

    model_config = {
        "extra": "ignore",
        "json_schema_extra": {
            "example": {
                "name": "服务依赖视图",
                "description": "展示微服务之间的依赖关系",
                "view_type": "service",
                "config": {"filters": {"environment": "production"}, "layout": "force"},
                "created_by": "admin",
            }
        },
    }


class TopologyViewUpdateRequest(BaseModel):
    """更新拓扑视图的请求模型"""

    name: Optional[str] = Field(
        None,
        min_length=1,
        max_length=100,
        description="视图名称",
        examples=["更新后的服务依赖视图"],
    )
    description: Optional[str] = Field(
        None,
        max_length=500,
        description="视图描述",
        examples=["更新后的描述"],
    )
    view_type: Optional[str] = Field(
        None,
        min_length=1,
        max_length=50,
        description="视图类型",
        examples=["service"],
    )
    config: Optional[dict] = Field(
        None,
        description="视图配置",
        examples=[{"filters": {"environment": "staging"}, "layout": "circular"}],
    )
    updated_by: str = Field(
        default="system",
        max_length=50,
        description="更新者用户名",
        examples=["admin"],
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("name 不能为空")
        return v

    @field_validator("view_type")
    @classmethod
    def validate_view_type(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip().lower()
            valid_types = {"service", "network", "application", "infrastructure", "custom"}
            if v not in valid_types:
                raise ValueError(f"view_type 必须是以下之一: {', '.join(valid_types)}")
        return v

    model_config = {
        "extra": "ignore",
        "json_schema_extra": {
            "example": {
                "name": "更新后的服务依赖视图",
                "description": "更新后的描述",
                "view_type": "service",
                "config": {"filters": {"environment": "staging"}, "layout": "circular"},
                "updated_by": "admin",
            }
        },
    }


class TopologyViewResponse(BaseModel):
    """拓扑视图响应模型"""

    id: str = Field(..., description="视图ID")
    name: str = Field(..., description="视图名称")
    description: str = Field(..., description="视图描述")
    view_type: str = Field(..., description="视图类型")
    config: dict = Field(..., description="视图配置")
    created_by: str = Field(..., description="创建者")
    created_at: str = Field(..., description="创建时间")
    updated_at: str = Field(..., description="更新时间")
    updated_by: Optional[str] = Field(None, description="更新者")

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "view-abc123def456",
                "name": "服务依赖视图",
                "description": "展示微服务之间的依赖关系",
                "view_type": "service",
                "config": {"filters": {"environment": "production"}, "layout": "force"},
                "created_by": "admin",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
                "updated_by": "admin",
            }
        }
    }


# Helper Functions


def _validate_view_id(view_id: str) -> str:
    """验证视图ID的格式"""
    if not view_id or not isinstance(view_id, str):
        raise HTTPException(status_code=422, detail="view_id 不能为空")
    cleaned = view_id.strip()
    if not cleaned:
        raise HTTPException(status_code=422, detail="view_id 不能为纯空白")
    if not _VALID_VIEW_ID_PATTERN.match(cleaned):
        raise HTTPException(status_code=422, detail="view_id 仅允许字母数字和 '._-'")
    if len(cleaned) > 64:
        raise HTTPException(status_code=422, detail="view_id 长度超出 64 字符")
    return cleaned


# API Endpoints


@router.get(
    "",
    summary="获取所有拓扑视图",
    responses={
        (200): {"description": "拓扑视图列表"},
        (500): {"description": "获取失败"},
    },
)
async def list_topology_views(
    view_type: Optional[str] = Query(
        None,
        description="按视图类型过滤",
        examples=["service"],
    ),
) -> dict[str, Any]:
    """
    获取所有拓扑视图，可选择按类型过滤

    Args:
        view_type: 可选的视图类型过滤器

    Returns:
        包含视图列表的响应
    """
    logger.info(f"请求拓扑视图列表 | view_type={view_type}")
    try:
        views = await get_all_topology_views(view_type=view_type)
        logger.debug(f"成功获取 {len(views)} 个拓扑视图")
        return {"views": views, "count": len(views)}
    except Exception as e:
        logger.error(f"获取拓扑视图列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取拓扑视图列表失败: {str(e)[:200]}")


@router.get(
    "/{view_id}",
    summary="获取特定拓扑视图",
    responses={
        (200): {"description": "拓扑视图详情"},
        (404): {"description": "视图未找到"},
        (422): {"description": "参数错误"},
        (500): {"description": "获取失败"},
    },
)
async def get_topology_view_by_id(view_id: str) -> dict[str, Any]:
    """
    根据ID获取特定的拓扑视图

    Args:
        view_id: 视图ID

    Returns:
        视图详情
    """
    cleaned_view_id = _validate_view_id(view_id)
    logger.info(f"请求拓扑视图详情 | view_id={cleaned_view_id}")
    try:
        view = await get_topology_view(cleaned_view_id)
        if view is None:
            logger.warning(f"拓扑视图未找到 | view_id={cleaned_view_id}")
            raise HTTPException(status_code=404, detail=f"拓扑视图未找到: {cleaned_view_id}")
        logger.debug(f"成功获取拓扑视图 | view_id={cleaned_view_id}")
        return view
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取拓扑视图失败 | view_id={cleaned_view_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取拓扑视图失败: {str(e)[:200]}")


@router.post(
    "",
    summary="创建拓扑视图",
    responses={
        (201): {"description": "创建成功"},
        (400): {"description": "请求参数错误"},
        (500): {"description": "创建失败"},
    },
)
async def create_topology_view_endpoint(payload: TopologyViewCreateRequest) -> dict[str, Any]:
    """
    创建新的拓扑视图

    Args:
        payload: 创建视图的请求体

    Returns:
        创建的视图数据
    """
    logger.info(f"创建拓扑视图 | name={payload.name} | type={payload.view_type}")
    try:
        view = await create_topology_view(
            name=payload.name,
            description=payload.description,
            view_type=payload.view_type,
            config=payload.config,
            created_by=payload.created_by,
        )
        logger.info(f"拓扑视图创建成功 | view_id={view['id']}")
        return view
    except ValueError as ve:
        logger.warning(f"拓扑视图创建失败(参数错误): {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"拓扑视图创建失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"拓扑视图创建失败: {str(e)[:200]}")


@router.put(
    "/{view_id}",
    summary="更新拓扑视图",
    responses={
        (200): {"description": "更新成功"},
        (404): {"description": "视图未找到"},
        (422): {"description": "参数错误"},
        (500): {"description": "更新失败"},
    },
)
async def update_topology_view_endpoint(
    view_id: str, payload: TopologyViewUpdateRequest
) -> dict[str, Any]:
    """
    更新现有的拓扑视图

    Args:
        view_id: 视图ID
        payload: 更新视图的请求体

    Returns:
        更新后的视图数据
    """
    cleaned_view_id = _validate_view_id(view_id)
    logger.info(f"更新拓扑视图 | view_id={cleaned_view_id}")
    try:
        view = await update_topology_view(
            view_id=cleaned_view_id,
            name=payload.name,
            description=payload.description,
            view_type=payload.view_type,
            config=payload.config,
            updated_by=payload.updated_by,
        )
        if view is None:
            logger.warning(f"拓扑视图未找到 | view_id={cleaned_view_id}")
            raise HTTPException(status_code=404, detail=f"拓扑视图未找到: {cleaned_view_id}")
        logger.info(f"拓扑视图更新成功 | view_id={cleaned_view_id}")
        return view
    except HTTPException:
        raise
    except ValueError as ve:
        logger.warning(f"拓扑视图更新失败(参数错误): {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"拓扑视图更新失败 | view_id={cleaned_view_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"拓扑视图更新失败: {str(e)[:200]}")


@router.delete(
    "/{view_id}",
    summary="删除拓扑视图",
    responses={
        (200): {"description": "删除成功"},
        (404): {"description": "视图未找到"},
        (422): {"description": "参数错误"},
        (500): {"description": "删除失败"},
    },
)
async def delete_topology_view_endpoint(view_id: str) -> dict[str, Any]:
    """
    删除拓扑视图

    Args:
        view_id: 视图ID

    Returns:
        删除结果
    """
    cleaned_view_id = _validate_view_id(view_id)
    logger.info(f"删除拓扑视图 | view_id={cleaned_view_id}")
    try:
        success = await delete_topology_view(cleaned_view_id)
        if not success:
            logger.warning(f"拓扑视图未找到 | view_id={cleaned_view_id}")
            raise HTTPException(status_code=404, detail=f"拓扑视图未找到: {cleaned_view_id}")
        logger.info(f"拓扑视图删除成功 | view_id={cleaned_view_id}")
        return {"status": "ok", "message": f"拓扑视图 {cleaned_view_id} 已删除"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"拓扑视图删除失败 | view_id={cleaned_view_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"拓扑视图删除失败: {str(e)[:200]}")
