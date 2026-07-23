# -*- coding: utf-8 -*-
"""
Plugin Marketplace API Router
Provides API endpoints for plugin marketplace management
"""

from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from loguru import logger

router = APIRouter(prefix="/api/plugin-marketplace", tags=["Plugin Marketplace"])


@router.get(
    "/status",
    summary="获取插件市场状态",
    responses={
        200: {
            "description": "市场状态",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "data": {"total_plugins": 50, "published_plugins": 40},
                        "timestamp": "2026-07-03T09:00:00Z",
                    }
                }
            },
        },
        500: {"description": "获取失败"},
    },
)
async def get_marketplace_status():
    """
    Get plugin marketplace status

    Returns:
        Marketplace status
    """
    try:
        from core.plugin_marketplace_manager import get_marketplace_manager

        manager = get_marketplace_manager()
        status = manager.get_marketplace_summary()
        return {"status": "success", "data": status, "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        logger.error(f"Error getting marketplace status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/publish",
    summary="发布插件到市场",
    responses={
        200: {
            "description": "发布结果",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "data": {"plugin_id": "plugin-123", "published": True},
                        "timestamp": "2026-07-03T09:00:00Z",
                    }
                }
            },
        },
        500: {"description": "发布失败"},
    },
)
async def publish_plugin(
    plugin_id: str,
    plugin_name: str,
    version: str,
    description: str,
    author: str,
    plugin_code: str,
    plugin_config: Dict[str, Any],
    quality: str = "community",
):
    """
    Publish plugin to marketplace

    Args:
        plugin_id: Plugin ID
        plugin_name: Plugin name
        version: Plugin version
        description: Plugin description
        author: Plugin author
        plugin_code: Plugin code
        plugin_config: Plugin configuration
        quality: Plugin quality level

    Returns:
        Publishing result
    """
    try:
        from core.plugin_marketplace_manager import PluginQuality, get_marketplace_manager

        manager = get_marketplace_manager()

        quality_enum = PluginQuality(quality)
        success = manager.publish_plugin(
            plugin_id=plugin_id,
            plugin_name=plugin_name,
            version=version,
            description=description,
            author=author,
            plugin_code=plugin_code,
            plugin_config=plugin_config,
            quality=quality_enum,
        )

        return {
            "status": "success",
            "data": {"plugin_id": plugin_id, "published": success},
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error publishing plugin: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/plugin/{plugin_id}/approve",
    summary="批准插件",
    responses={
        200: {"description": "批准结果"},
        500: {"description": "批准失败"},
    },
)
async def approve_plugin(plugin_id: str, reviewer: str):
    """
    Approve plugin for marketplace

    Args:
        plugin_id: Plugin ID
        reviewer: Reviewer name

    Returns:
        Approval result
    """
    try:
        from core.plugin_marketplace_manager import get_marketplace_manager

        manager = get_marketplace_manager()

        success = manager.approve_plugin(plugin_id, reviewer)

        return {
            "status": "success",
            "data": {"plugin_id": plugin_id, "approved": success},
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error approving plugin: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/plugin/{plugin_id}/reject",
    summary="拒绝插件",
    responses={
        200: {"description": "拒绝结果"},
        500: {"description": "拒绝失败"},
    },
)
async def reject_plugin(plugin_id: str, reason: str):
    """
    Reject plugin from marketplace

    Args:
        plugin_id: Plugin ID
        reason: Rejection reason

    Returns:
        Rejection result
    """
    try:
        from core.plugin_marketplace_manager import get_marketplace_manager

        manager = get_marketplace_manager()

        success = manager.reject_plugin(plugin_id, reason)

        return {
            "status": "success",
            "data": {"plugin_id": plugin_id, "rejected": success},
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error rejecting plugin: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/plugin/{plugin_id}/download",
    summary="下载插件",
    responses={
        200: {"description": "下载结果"},
        404: {"description": "插件未找到或未批准"},
        500: {"description": "下载失败"},
    },
)
async def download_plugin(plugin_id: str):
    """
    Download plugin from marketplace

    Args:
        plugin_id: Plugin ID

    Returns:
        Download result
    """
    try:
        from core.plugin_marketplace_manager import get_marketplace_manager

        manager = get_marketplace_manager()

        result = manager.download_plugin(plugin_id)

        if not result:
            raise HTTPException(status_code=404, detail="Plugin not found or not approved")

        return {"status": "success", "data": result, "timestamp": datetime.utcnow().isoformat()}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading plugin: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/listings",
    summary="获取插件列表",
    responses={
        200: {"description": "插件列表"},
        500: {"description": "获取失败"},
    },
)
async def get_plugin_listings(quality: Optional[str] = None, review_status: Optional[str] = None):
    """
    Get plugin listings from marketplace

    Args:
        quality: Filter by quality
        review_status: Filter by review status

    Returns:
        List of plugin listings
    """
    try:
        from core.plugin_marketplace_manager import (
            PluginQuality,
            PluginReviewStatus,
            get_marketplace_manager,
        )

        manager = get_marketplace_manager()

        quality_enum = PluginQuality(quality) if quality else None
        status_enum = PluginReviewStatus(review_status) if review_status else None

        listings = manager.get_plugin_listings(quality_enum, status_enum)

        return {
            "status": "success",
            "data": {"listings": listings, "count": len(listings)},
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error getting listings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/plugin/{plugin_id}/review",
    summary="添加插件评论",
    responses={
        200: {"description": "评论结果"},
        500: {"description": "添加失败"},
    },
)
async def add_plugin_review(plugin_id: str, reviewer: str, rating: int, comment: str):
    """
    Add review for plugin

    Args:
        plugin_id: Plugin ID
        reviewer: Reviewer name
        rating: Rating (1-5)
        comment: Review comment

    Returns:
        Review result
    """
    try:
        from core.plugin_marketplace_manager import get_marketplace_manager

        manager = get_marketplace_manager()

        success = manager.add_review(plugin_id, reviewer, rating, comment)

        return {
            "status": "success",
            "data": {"plugin_id": plugin_id, "review_added": success},
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error adding review: {e}")
        raise HTTPException(status_code=500, detail=str(e))
