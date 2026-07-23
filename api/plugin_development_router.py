# -*- coding: utf-8 -*-
"""
Plugin Development SDK API Router
Provides API endpoints for plugin development tools
"""

from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from loguru import logger

router = APIRouter(prefix="/api/plugin-sdk", tags=["Plugin SDK"])


@router.get(
    "/status",
    summary="获取插件SDK状态",
    responses={
        200: {
            "description": "SDK状态",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "data": {"sdk_version": "1.0.0", "available": True},
                        "timestamp": "2026-07-03T09:00:00Z",
                    }
                }
            },
        },
        500: {"description": "获取失败"},
    },
)
async def get_sdk_status():
    """
    Get plugin SDK status

    Returns:
        SDK status
    """
    try:
        from core.plugin_development_sdk import get_plugin_sdk

        sdk = get_plugin_sdk()
        status = sdk.get_sdk_summary()
        return {"status": "success", "data": status, "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        logger.error(f"Error getting SDK status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/templates",
    summary="获取可用插件模板",
    responses={
        200: {
            "description": "模板列表",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "data": {"templates": ["collector", "analyzer", "notifier"], "count": 3},
                        "timestamp": "2026-07-03T09:00:00Z",
                    }
                }
            },
        },
        500: {"description": "获取失败"},
    },
)
async def get_available_templates():
    """
    Get available plugin templates

    Returns:
        List of available templates
    """
    try:
        from core.plugin_development_sdk import get_plugin_sdk

        sdk = get_plugin_sdk()

        templates = sdk.get_available_templates()

        return {
            "status": "success",
            "data": {"templates": templates, "count": len(templates)},
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error getting templates: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/generate",
    summary="生成插件包",
    responses={
        200: {
            "description": "生成结果",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "data": {
                            "plugin_id": "plugin-123",
                            "package_path": "/tmp/plugin-123.zip",
                        },  # nosec B108
                        "timestamp": "2026-07-03T09:00:00Z",
                    }
                }
            },
        },
        500: {"description": "生成失败"},
    },
)
async def generate_plugin_package(
    template_type: str,
    plugin_name: str,
    class_name: str,
    version: str = "1.0.0",
    author: str = "Unknown",
    custom_config: Optional[Dict[str, Any]] = None,
):
    """
    Generate plugin package from template

    Args:
        template_type: Template type
        plugin_name: Plugin name
        class_name: Class name
        version: Plugin version
        author: Plugin author
        custom_config: Custom configuration

    Returns:
        Generated plugin package
    """
    try:
        from core.plugin_development_sdk import get_plugin_sdk

        sdk = get_plugin_sdk()

        package = sdk.create_plugin_package(
            template_type=template_type,
            plugin_name=plugin_name,
            class_name=class_name,
            version=version,
            author=author,
            custom_config=custom_config,
        )

        return {
            "status": "success",
            "data": {
                "plugin_id": f"{plugin_name.lower().replace(' ', '_')}_{version.replace('.', '_')}",
                "plugin_name": package["plugin_name"],
                "version": package["version"],
                "template_type": package["template_type"],
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error generating plugin package: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/generate/code",
    summary="生成插件代码",
    responses={
        200: {"description": "生成结果"},
        500: {"description": "生成失败"},
    },
)
async def generate_plugin_code(
    template_type: str,
    plugin_name: str,
    class_name: str,
    version: str = "1.0.0",
    author: str = "Unknown",
):
    """
    Generate plugin code from template

    Args:
        template_type: Template type
        plugin_name: Plugin name
        class_name: Class name
        version: Plugin version
        author: Plugin author

    Returns:
        Generated plugin code
    """
    try:
        from core.plugin_development_sdk import get_plugin_sdk

        sdk = get_plugin_sdk()

        code = sdk.generate_plugin_code(
            template_type=template_type,
            plugin_name=plugin_name,
            class_name=class_name,
            version=version,
            author=author,
        )

        return {
            "status": "success",
            "data": {
                "code": code,
                "template_type": template_type,
                "line_count": len(code.split("\n")),
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error generating plugin code: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/generate/config",
    summary="生成插件配置",
    responses={
        200: {"description": "生成结果"},
        500: {"description": "生成失败"},
    },
)
async def generate_plugin_config(
    template_type: str, custom_config: Optional[Dict[str, Any]] = None
):
    """
    Generate plugin configuration from template

    Args:
        template_type: Template type
        custom_config: Custom configuration

    Returns:
        Generated configuration
    """
    try:
        from core.plugin_development_sdk import get_plugin_sdk

        sdk = get_plugin_sdk()

        config = sdk.generate_plugin_config(template_type, custom_config)

        return {"status": "success", "data": config, "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        logger.error(f"Error generating plugin config: {e}")
        raise HTTPException(status_code=500, detail=str(e))
