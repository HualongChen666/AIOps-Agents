# -*- coding: utf-8 -*-
"""
Plugin System API Router
Provides API endpoints for plugin system management
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, HTTPException
from loguru import logger

router = APIRouter(prefix="/api/plugin-system", tags=["Plugin System"])


@router.get(
    "/status",
    summary="获取插件系统状态",
    responses={
        200: {
            "description": "系统状态",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "data": {"total_plugins": 10, "active_plugins": 8, "total_interfaces": 5},
                        "timestamp": "2026-07-03T09:00:00Z",
                    }
                }
            },
        },
        500: {"description": "获取失败"},
    },
)
async def get_system_status():
    """
    Get plugin system status

    Returns:
        Plugin system status
    """
    try:
        from core.plugin_system_manager import get_plugin_system_manager

        manager = get_plugin_system_manager()
        status = manager.get_system_summary()
        return {"status": "success", "data": status, "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/interface/define",
    summary="定义插件接口",
    responses={
        200: {
            "description": "接口定义结果",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "data": {
                            "interface_id": "data-collector",
                            "interface_name": "Data Collector",
                            "method_count": 3,
                            "event_count": 2,
                        },
                        "timestamp": "2026-07-03T09:00:00Z",
                    }
                }
            },
        },
        500: {"description": "定义失败"},
    },
)
async def define_plugin_interface(
    interface_id: str,
    interface_name: str,
    methods: List[Dict[str, Any]] = Body([]),
    events: List[Dict[str, Any]] = Body([]),
    configuration: Optional[Dict[str, Any]] = Body(None),
):
    """
    Define plugin interface specification

    Args:
        interface_id: Interface ID
        interface_name: Interface name
        methods: Interface methods
        events: Interface events
        configuration: Interface configuration

    Returns:
        Interface specification
    """
    try:
        from core.plugin_system_manager import get_plugin_system_manager

        manager = get_plugin_system_manager()

        interface = manager.define_plugin_interface(
            interface_id=interface_id,
            interface_name=interface_name,
            methods=methods,
            events=events,
            configuration=configuration,
        )

        return {
            "status": "success",
            "data": {
                "interface_id": interface.interface_id,
                "interface_name": interface.interface_name,
                "method_count": len(interface.methods),
                "event_count": len(interface.events),
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error defining interface: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/interface/spec/{interface_type}",
    summary="获取接口规范",
    responses={
        200: {
            "description": "接口规范",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "data": {
                            "interface_type": "data-collector",
                            "methods": [{"name": "collect", "params": []}],
                            "events": [{"name": "on_data_collected"}],
                        },
                        "timestamp": "2026-07-03T09:00:00Z",
                    }
                }
            },
        },
        500: {"description": "获取失败"},
    },
)
async def get_interface_spec(interface_type: str):
    """
    Get plugin interface specification for a type

    Args:
        interface_type: Interface type

    Returns:
        Interface specification
    """
    try:
        from core.plugin_system_manager import get_plugin_system_manager

        manager = get_plugin_system_manager()

        spec = manager.generate_plugin_interface_spec(interface_type)

        return {"status": "success", "data": spec, "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        logger.error(f"Error getting interface spec: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/plugin/register",
    summary="注册插件",
    responses={
        200: {
            "description": "注册结果",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "data": {
                            "plugin_id": "plugin-123",
                            "name": "CPU Monitor",
                            "version": "1.0.0",
                            "registered": True,
                        },
                        "timestamp": "2026-07-03T09:00:00Z",
                    }
                }
            },
        },
        500: {"description": "注册失败"},
    },
)
async def register_plugin(
    plugin_id: str,
    name: str,
    version: str,
    description: str,
    author: str,
    plugin_type: str,
    dependencies: Optional[Dict[str, Any]] = None,
):
    """
    Register plugin metadata

    Args:
        plugin_id: Plugin ID
        name: Plugin name
        version: Plugin version
        description: Plugin description
        author: Plugin author
        plugin_type: Plugin type
        dependencies: Plugin dependencies

    Returns:
        Registration result
    """
    try:
        from core.plugin_system_manager import (
            PluginMetadata,
            PluginType,
            get_plugin_system_manager,
        )

        manager = get_plugin_system_manager()

        metadata = PluginMetadata(
            plugin_id=plugin_id,
            name=name,
            version=version,
            description=description,
            author=author,
            plugin_type=PluginType(plugin_type),
            dependencies=dependencies.get("dependencies", []) if dependencies else [],
        )

        success = manager.register_plugin(plugin_id, metadata)

        return {
            "status": "success",
            "data": {"plugin_id": plugin_id, "registered": success},
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error registering plugin: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/plugin/{plugin_id}/enable",
    summary="启用插件",
    responses={
        200: {"description": "启用结果"},
        500: {"description": "启用失败"},
    },
)
async def enable_plugin(plugin_id: str):
    """
    Enable plugin

    Args:
        plugin_id: Plugin ID

    Returns:
        Enable result
    """
    try:
        from core.plugin_system_manager import get_plugin_system_manager

        manager = get_plugin_system_manager()

        success = manager.enable_plugin(plugin_id)

        return {
            "status": "success",
            "data": {"plugin_id": plugin_id, "enabled": success},
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error enabling plugin: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/plugin/{plugin_id}/disable",
    summary="禁用插件",
    responses={
        200: {"description": "禁用结果"},
        500: {"description": "禁用失败"},
    },
)
async def disable_plugin(plugin_id: str):
    """
    Disable plugin

    Args:
        plugin_id: Plugin ID

    Returns:
        Disable result
    """
    try:
        from core.plugin_system_manager import get_plugin_system_manager

        manager = get_plugin_system_manager()

        success = manager.disable_plugin(plugin_id)

        return {
            "status": "success",
            "data": {"plugin_id": plugin_id, "disabled": success},
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error disabling plugin: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/plugins",
    summary="列出插件",
    responses={
        200: {"description": "插件列表"},
        500: {"description": "获取失败"},
    },
)
async def list_plugins(plugin_type: Optional[str] = None, status: Optional[str] = None):
    """
    List plugins

    Args:
        plugin_type: Filter by plugin type
        status: Filter by status

    Returns:
        List of plugins
    """
    try:
        from core.plugin_system_manager import PluginStatus, PluginType, get_plugin_system_manager

        manager = get_plugin_system_manager()

        type_enum = PluginType(plugin_type) if plugin_type else None
        status_enum = PluginStatus(status) if status else None

        plugins = manager.list_plugins(type_enum, status_enum)

        return {
            "status": "success",
            "data": {"plugins": plugins, "count": len(plugins)},
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error listing plugins: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/plugin/{plugin_id}",
    summary="获取插件信息",
    responses={
        200: {"description": "插件信息"},
        404: {"description": "插件未找到"},
        500: {"description": "获取失败"},
    },
)
async def get_plugin_info(plugin_id: str):
    """
    Get plugin information

    Args:
        plugin_id: Plugin ID

    Returns:
        Plugin information
    """
    try:
        from core.plugin_system_manager import get_plugin_system_manager

        manager = get_plugin_system_manager()

        info = manager.get_plugin_info(plugin_id)

        if not info:
            raise HTTPException(status_code=404, detail="Plugin not found")

        return {"status": "success", "data": info, "timestamp": datetime.utcnow().isoformat()}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting plugin info: {e}")
        raise HTTPException(status_code=500, detail=str(e))
