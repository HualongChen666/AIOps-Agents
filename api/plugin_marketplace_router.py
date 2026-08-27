# -*- coding: utf-8 -*-
"""
Plugin Marketplace Router
插件市场路由

提供完整的插件市场API端点，包括插件列表、上传、审核、安装等功能。
"""

import json
import uuid
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, UploadFile, File
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.api_response_standard import (
    ErrorCode,
    create_error_response,
    create_success_response,
)
from core.auth_db import get_session
from core.models import (
    PluginListingDB,
    PluginReviewDB,
    PluginCategoryDB,
    InstalledPluginDB,
)
from core.cache_manager import cache_manager, cache_key_generator

router = APIRouter(prefix="/api/v1/plugin-marketplace", tags=["插件市场"])


# Pydantic Models
class PluginQualityEnum(str, Enum):
    """插件质量枚举"""
    COMMUNITY = "community"
    VERIFIED = "verified"
    OFFICIAL = "official"


class PluginCategoryEnum(str, Enum):
    """插件分类枚举"""
    GENERAL = "general"
    MONITORING = "monitoring"
    ALERTING = "alerting"
    AUTOMATION = "automation"
    ANALYTICS = "analytics"
    SECURITY = "security"
    PERFORMANCE = "performance"
    INTEGRATION = "integration"


class PluginListingRequest(BaseModel):
    """插件列表请求"""
    plugin_id: str = Field(..., description="插件ID")
    plugin_name: str = Field(..., description="插件名称")
    version: str = Field(..., description="版本号")
    description: str = Field(..., description="描述")
    author: str = Field(..., description="作者")
    category: PluginCategoryEnum = Field(default=PluginCategoryEnum.GENERAL, description="分类")
    tags: Optional[List[str]] = Field(default=None, description="标签")
    price: Optional[float] = Field(default=None, description="价格")
    quality: PluginQualityEnum = Field(default=PluginQualityEnum.COMMUNITY, description="质量")
    download_url: str = Field(..., description="下载URL")
    screenshot_urls: Optional[List[str]] = Field(default=None, description="截图URL")
    documentation_url: Optional[str] = Field(default=None, description="文档URL")
    repository_url: Optional[str] = Field(default=None, description="仓库URL")


class PluginReviewRequest(BaseModel):
    """插件评论请求"""
    plugin_id: str = Field(..., description="插件ID")
    reviewer_id: str = Field(..., description="评论者ID")
    reviewer_name: str = Field(..., description="评论者名称")
    rating: int = Field(..., ge=1, le=5, description="评分")
    review_text: Optional[str] = Field(default=None, description="评论内容")


class PluginInstallRequest(BaseModel):
    """插件安装请求"""
    plugin_id: str = Field(..., description="插件ID")
    installed_version: str = Field(..., description="安装版本")
    configuration: Optional[Dict[str, Any]] = Field(default=None, description="配置")


# Helper functions
def _generate_id(prefix: str) -> str:
    """生成ID"""
    return f"{prefix}-{uuid.uuid4().hex[:8].upper()}"


def _now() -> str:
    """获取当前时间"""
    return datetime.now(timezone.utc).isoformat()


# API Endpoints
@router.get(
    "/plugins",
    summary="获取插件列表",
    responses={
        200: {"description": "成功获取插件列表"},
        500: {"description": "服务器错误"},
    },
)
async def get_plugin_listings(
    category: Optional[PluginCategoryEnum] = Query(None, description="按分类筛选"),
    quality: Optional[PluginQualityEnum] = Query(None, description="按质量筛选"),
    enabled: Optional[bool] = Query(None, description="按启用状态筛选"),
    limit: int = Query(20, ge=1, le=100, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
) -> Dict[str, Any]:
    """
    获取插件市场列表

    支持按分类、质量、启用状态筛选，支持分页。
    """
    try:
        # 生成缓存键
        cache_key = cache_key_generator(
            "plugin_listings",
            category.value if category else None,
            quality.value if quality else None,
            enabled,
            limit,
            offset
        )
        
        # 尝试从缓存获取
        cached_result = cache_manager.get(cache_key)
        if cached_result is not None:
            return create_success_response(cached_result)
        
        # 从数据库获取数据
        db = get_session()
        try:
            query = db.query(PluginListingDB)
            
            # 过滤
            if category:
                query = query.filter(PluginListingDB.category == category.value)
            if quality:
                query = query.filter(PluginListingDB.quality == quality.value)
            if enabled is not None:
                query = query.filter(PluginListingDB.enabled == enabled)
            
            # 分页
            total = query.count()
            results = query.offset(offset).limit(limit).all()
            
            # 转换为字典格式
            items = []
            for result in results:
                items.append({
                    "id": result.id,
                    "plugin_id": result.plugin_id,
                    "plugin_name": result.plugin_name,
                    "version": result.version,
                    "description": result.description,
                    "author": result.author,
                    "category": result.category,
                    "tags": result.tags,
                    "price": result.price,
                    "quality": result.quality,
                    "download_url": result.download_url,
                    "screenshot_urls": result.screenshot_urls,
                    "documentation_url": result.documentation_url,
                    "repository_url": result.repository_url,
                    "download_count": result.download_count,
                    "rating": result.rating,
                    "review_count": result.review_count,
                    "enabled": result.enabled,
                    "created_at": result.created_at.isoformat() if result.created_at else None,
                    "updated_at": result.updated_at.isoformat() if result.updated_at else None,
                })
            
            response_data = {
                "items": items,
                "total": total,
                "limit": limit,
                "offset": offset,
            }
            
            # 设置缓存，TTL为10分钟
            cache_manager.set(cache_key, response_data, ttl=600)
            
            return create_success_response(response_data)
        finally:
            db.close()
    except Exception as e:
        return create_error_response(
            error=str(e), error_code=ErrorCode.INTERNAL_ERROR, message="获取插件列表失败"
        )


@router.post(
    "/plugins",
    summary="上传插件",
    status_code=201,
    responses={
        201: {"description": "插件上传成功"},
        400: {"description": "请求参数错误"},
        500: {"description": "服务器错误"},
    },
)
async def upload_plugin(request: PluginListingRequest) -> Dict[str, Any]:
    """
    上传新插件到市场

    创建新的插件列表项，等待审核。
    """
    try:
        db = get_session()
        try:
            # 检查插件是否已存在
            existing = db.query(PluginListingDB).filter(
                PluginListingDB.plugin_id == request.plugin_id
            ).first()
            if existing:
                return create_error_response(
                    error="Plugin already exists",
                    error_code=ErrorCode.VALIDATION_ERROR,
                    message="插件已存在"
                )
            
            # 创建插件列表
            plugin = PluginListingDB(
                id=_generate_id("PLUGIN"),
                plugin_id=request.plugin_id,
                plugin_name=request.plugin_name,
                version=request.version,
                description=request.description,
                author=request.author,
                category=request.category.value,
                tags=request.tags,
                price=request.price,
                quality=request.quality.value,
                download_url=request.download_url,
                screenshot_urls=request.screenshot_urls,
                documentation_url=request.documentation_url,
                repository_url=request.repository_url,
                download_count=0,
                rating=0.0,
                review_count=0,
                enabled=False,  # 默认禁用，等待审核
            )
            
            db.add(plugin)
            db.commit()
            
            # 失效缓存
            cache_manager.delete_pattern("plugin_listings:*")
            
            return create_success_response(
                {
                    "id": plugin.id,
                    "plugin_id": plugin.plugin_id,
                    "plugin_name": plugin.plugin_name,
                    "status": "pending_review",
                },
                "插件上传成功，等待审核"
            )
        finally:
            db.close()
    except Exception as e:
        return create_error_response(
            error=str(e), error_code=ErrorCode.INTERNAL_ERROR, message="上传插件失败"
        )


@router.post(
    "/plugins/{plugin_id}/reviews",
    summary="添加插件评论",
    status_code=201,
    responses={
        201: {"description": "评论添加成功"},
        400: {"description": "请求参数错误"},
        500: {"description": "服务器错误"},
    },
)
async def add_plugin_review(plugin_id: str, request: PluginReviewRequest) -> Dict[str, Any]:
    """
    为插件添加评论

    用户可以对插件进行评分和评论。
    """
    try:
        db = get_session()
        try:
            # 检查插件是否存在
            plugin = db.query(PluginListingDB).filter(
                PluginListingDB.plugin_id == plugin_id
            ).first()
            if not plugin:
                return create_error_response(
                    error="Plugin not found",
                    error_code=ErrorCode.NOT_FOUND,
                    message="插件不存在"
                )
            
            # 创建评论
            review = PluginReviewDB(
                id=_generate_id("REVIEW"),
                plugin_id=plugin_id,
                reviewer_id=request.reviewer_id,
                reviewer_name=request.reviewer_name,
                rating=request.rating,
                review_text=request.review_text,
            )
            
            db.add(review)
            
            # 更新插件评分
            plugin.review_count += 1
            # 简单的评分更新逻辑
            plugin.rating = (plugin.rating * (plugin.review_count - 1) + request.rating) / plugin.review_count
            
            db.commit()
            
            # 失效缓存
            cache_manager.delete_pattern("plugin_listings:*")
            
            return create_success_response(
                {
                    "id": review.id,
                    "plugin_id": review.plugin_id,
                    "rating": review.rating,
                },
                "评论添加成功"
            )
        finally:
            db.close()
    except Exception as e:
        return create_error_response(
            error=str(e), error_code=ErrorCode.INTERNAL_ERROR, message="添加评论失败"
        )


@router.post(
    "/plugins/{plugin_id}/install",
    summary="安装插件",
    status_code=201,
    responses={
        201: {"description": "插件安装成功"},
        400: {"description": "请求参数错误"},
        500: {"description": "服务器错误"},
    },
)
async def install_plugin(plugin_id: str, request: PluginInstallRequest) -> Dict[str, Any]:
    """
    安装插件

    将插件安装到系统中。
    """
    try:
        db = get_session()
        try:
            # 检查插件是否存在
            plugin = db.query(PluginListingDB).filter(
                PluginListingDB.plugin_id == plugin_id
            ).first()
            if not plugin:
                return create_error_response(
                    error="Plugin not found",
                    error_code=ErrorCode.NOT_FOUND,
                    message="插件不存在"
                )
            
            # 检查是否已安装
            existing = db.query(InstalledPluginDB).filter(
                InstalledPluginDB.plugin_id == plugin_id
            ).first()
            if existing:
                return create_error_response(
                    error="Plugin already installed",
                    error_code=ErrorCode.VALIDATION_ERROR,
                    message="插件已安装"
                )
            
            # 创建安装记录
            installed = InstalledPluginDB(
                id=_generate_id("INSTALLED"),
                plugin_id=plugin_id,
                installed_version=request.installed_version,
                status="active",
                configuration=request.configuration,
            )
            
            db.add(installed)
            
            # 更新下载计数
            plugin.download_count += 1
            
            db.commit()
            
            # 失效缓存
            cache_manager.delete_pattern("plugin_listings:*")
            
            return create_success_response(
                {
                    "id": installed.id,
                    "plugin_id": installed.plugin_id,
                    "installed_version": installed.installed_version,
                    "status": installed.status,
                },
                "插件安装成功"
            )
        finally:
            db.close()
    except Exception as e:
        return create_error_response(
            error=str(e), error_code=ErrorCode.INTERNAL_ERROR, message="安装插件失败"
        )


@router.get(
    "/plugins/installed",
    summary="获取已安装插件列表",
    responses={
        200: {"description": "成功获取已安装插件列表"},
        500: {"description": "服务器错误"},
    },
)
async def get_installed_plugins(
    enabled: Optional[bool] = Query(None, description="按启用状态筛选"),
    limit: int = Query(20, ge=1, le=100, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
) -> Dict[str, Any]:
    """
    获取已安装插件列表

    支持按启用状态筛选，支持分页。
    """
    try:
        db = get_session()
        try:
            query = db.query(InstalledPluginDB)
            
            # 过滤
            if enabled is not None:
                query = query.filter(InstalledPluginDB.enabled == enabled)
            
            # 分页
            total = query.count()
            results = query.offset(offset).limit(limit).all()
            
            # 转换为字典格式
            items = []
            for result in results:
                items.append({
                    "id": result.id,
                    "plugin_id": result.plugin_id,
                    "installed_version": result.installed_version,
                    "installation_date": result.installation_date.isoformat() if result.installation_date else None,
                    "status": result.status,
                    "configuration": result.configuration,
                    "enabled": result.enabled,
                    "updated_at": result.updated_at.isoformat() if result.updated_at else None,
                })
            
            response_data = {
                "items": items,
                "total": total,
                "limit": limit,
                "offset": offset,
            }
            
            return create_success_response(response_data)
        finally:
            db.close()
    except Exception as e:
        return create_error_response(
            error=str(e), error_code=ErrorCode.INTERNAL_ERROR, message="获取已安装插件列表失败"
        )


@router.delete(
    "/plugins/installed/{plugin_id}",
    summary="卸载插件",
    responses={
        200: {"description": "插件卸载成功"},
        404: {"description": "插件未安装"},
        500: {"description": "服务器错误"},
    },
)
async def uninstall_plugin(plugin_id: str) -> Dict[str, Any]:
    """
    卸载插件

    从系统中卸载插件。
    """
    try:
        db = get_session()
        try:
            # 查找已安装的插件
            installed = db.query(InstalledPluginDB).filter(
                InstalledPluginDB.plugin_id == plugin_id
            ).first()
            if not installed:
                return create_error_response(
                    error="Plugin not installed",
                    error_code=ErrorCode.NOT_FOUND,
                    message="插件未安装"
                )
            
            # 删除安装记录
            db.delete(installed)
            db.commit()
            
            return create_success_response(
                {"plugin_id": plugin_id},
                "插件卸载成功"
            )
        finally:
            db.close()
    except Exception as e:
        return create_error_response(
            error=str(e), error_code=ErrorCode.INTERNAL_ERROR, message="卸载插件失败"
        )