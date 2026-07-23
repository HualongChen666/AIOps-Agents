# -*- coding: utf-8 -*-
"""
Plugin Ecosystem API Router
"""

from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, HTTPException
from loguru import logger

router = APIRouter(prefix="/api/plugin-ecosystem", tags=["Plugin Ecosystem"])


@router.get(
    "/status",
    summary="获取插件生态系统状态",
    responses={
        200: {
            "description": "生态系统状态",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "data": {"total_plugins": 10, "active_plugins": 8},
                        "timestamp": "2026-07-03T09:00:00Z",
                    }
                }
            },
        },
        500: {"description": "获取失败"},
    },
)
async def get_ecosystem_status():
    """Get plugin ecosystem status"""
    try:
        from core.plugin_ecosystem_manager import get_ecosystem_manager

        manager = get_ecosystem_manager()
        status = manager.get_ecosystem_summary()
        return {"status": "success", "data": status, "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        logger.error(f"Error getting ecosystem status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/activity",
    summary="记录插件活动",
    responses={
        200: {
            "description": "记录成功",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "data": {"activity_id": "act-123", "activity_type": "install"},
                        "timestamp": "2026-07-03T09:00:00Z",
                    }
                }
            },
        },
        500: {"description": "记录失败"},
    },
)
async def record_activity(plugin_id: str, activity_type: str, user_id: str):
    """Record plugin activity"""
    try:
        from core.plugin_ecosystem_manager import PluginActivityType, get_ecosystem_manager

        manager = get_ecosystem_manager()
        metadata: dict[str, Any] = {}
        activity_type_enum = PluginActivityType(activity_type)
        activity = manager.record_activity(plugin_id, activity_type_enum, user_id, metadata)
        return {
            "status": "success",
            "data": {
                "activity_id": activity.activity_id,
                "activity_type": activity.activity_type.value,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error recording activity: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/activities/{plugin_id}",
    summary="获取插件活动",
    responses={
        200: {
            "description": "活动列表",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "data": {
                            "plugin_id": "plugin-123",
                            "activities": [{"activity_id": "act-123", "activity_type": "install"}],
                            "count": 1,
                        },
                        "timestamp": "2026-07-03T09:00:00Z",
                    }
                }
            },
        },
        500: {"description": "获取失败"},
    },
)
async def get_plugin_activities(plugin_id: str, time_range_hours: int = 24):
    """Get plugin activities"""
    try:
        from core.plugin_ecosystem_manager import get_ecosystem_manager

        manager = get_ecosystem_manager()
        time_range = timedelta(hours=time_range_hours)
        activities = manager.get_plugin_activities(plugin_id, time_range)
        return {
            "status": "success",
            "data": {"plugin_id": plugin_id, "activities": activities, "count": len(activities)},
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error getting activities: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/developer/register",
    summary="注册插件开发者",
    responses={
        200: {
            "description": "注册成功",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "data": {"developer_id": "dev-123", "name": "Developer Name"},
                        "timestamp": "2026-07-03T09:00:00Z",
                    }
                }
            },
        },
        500: {"description": "注册失败"},
    },
)
async def register_developer(developer_id: str, name: str, email: str):
    """Register plugin developer"""
    try:
        from core.plugin_ecosystem_manager import PluginSupportLevel, get_ecosystem_manager

        manager = get_ecosystem_manager()
        support_level_enum = PluginSupportLevel("community")
        success = manager.register_developer(developer_id, name, email, None, support_level_enum)
        return {
            "status": "success",
            "data": {"developer_id": developer_id, "registered": success},
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error registering developer: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/developer/{developer_id}",
    summary="获取开发者统计",
    responses={
        200: {"description": "开发者统计"},
        404: {"description": "开发者未找到"},
        500: {"description": "获取失败"},
    },
)
async def get_developer_stats(developer_id: str):
    """Get developer statistics"""
    try:
        from core.plugin_ecosystem_manager import get_ecosystem_manager

        manager = get_ecosystem_manager()
        stats = manager.get_developer_stats(developer_id)
        if not stats:
            raise HTTPException(status_code=404, detail="Developer not found")
        return {"status": "success", "data": stats, "timestamp": datetime.utcnow().isoformat()}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting developer stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
