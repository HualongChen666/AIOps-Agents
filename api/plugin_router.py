# -*- coding: utf-8 -*-
"""插件管理 API

提供完整的插件管理功能：
- ``GET /api/plugins`` → 列出所有插件
- ``POST /api/plugins`` → 创建新插件
- ``GET /api/plugins/{id}`` → 获取插件详情
- ``PUT /api/plugins/{id}`` → 更新插件
- ``DELETE /api/plugins/{id}`` → 删除插件
- ``POST /api/plugins/{name}/run`` → 执行插件
- ``GET /api/plugins/stats`` → 获取插件统计信息
- ``GET /api/plugins/{id}/executions`` → 获取插件执行记录
- ``GET /api/plugins/{id}/config`` → 获取插件配置
- ``PUT /api/plugins/{id}/config`` → 更新插件配置

所有接口受 JWT 认证和 RBAC 权限控制保护。
实现速率限制以防止滥用。
"""

from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from core.auth import check_rate_limit, get_current_user, require_permission, require_role
from core.database import get_db
from core.models import User
from core.plugin_manager import get_plugin, list_plugins, load_all
from loguru import logger
from services.plugin_service import (
    PluginConfigCreate,
    PluginConfigResponse,
    PluginConfigUpdate,
    PluginCreate,
    PluginExecutionListResponse,
    PluginExecutionResponse,
    PluginListResponse,
    PluginResponse,
    PluginRunRequest,
    PluginRunResponse,
    PluginService,
    PluginStatsResponse,
    PluginUpdate,
)

router = APIRouter(prefix="/api/plugins", tags=["plugins"])

# 在模块导入时主动发现 entry points（如果有）
load_all()


def get_plugin_service(db: Session = Depends(get_db)) -> PluginService:
    """Get plugin service instance."""
    return PluginService(db)


@router.get(
    "/",
    summary="列出所有插件",
    responses={
        200: {"description": "插件列表"},
        401: {"description": "未授权"},
        403: {"description": "权限不足"},
    },
)
def list_plugins_api(
    status: Optional[str] = Query(None, description="按状态过滤"),
    plugin_type: Optional[str] = Query(None, description="按类型过滤"),
    limit: int = Query(100, ge=1, le=1000, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
    current_user: User = Depends(require_permission("plugin", "read")),
    db: Session = Depends(get_db),
    request: Request = None,
) -> PluginListResponse:
    """列出所有插件，支持状态和类型过滤。"""
    # Rate limiting
    user_id = str(current_user.id)
    check_rate_limit(user_id, requests_per_minute=60)
    
    # Log IP address for security monitoring
    client_ip = request.client.host if request else "unknown"
    logger.info(f"Plugin list requested by user {current_user.username} from {client_ip}")
    
    service = get_plugin_service(db)
    
    # Convert status string to enum if provided
    from core.models import PluginStatus
    status_enum = PluginStatus(status) if status else None
    
    plugins = service.list_plugins(
        status=status_enum,
        plugin_type=plugin_type,
        limit=limit,
        offset=offset,
    )
    
    total = service.count_plugins(status=status_enum)
    
    return PluginListResponse(total=total, plugins=plugins)


@router.post(
    "/",
    summary="创建新插件",
    responses={
        200: {"description": "插件创建成功"},
        401: {"description": "未授权"},
        403: {"description": "权限不足"},
        400: {"description": "请求参数错误"},
    },
)
def create_plugin(
    plugin_data: PluginCreate,
    current_user: User = Depends(require_permission("plugin", "create")),
    db: Session = Depends(get_db),
    request: Request = None,
) -> PluginResponse:
    """创建新插件。需要plugin:create权限。"""
    # Rate limiting
    user_id = str(current_user.id)
    check_rate_limit(user_id, requests_per_minute=30)
    
    # Log for security monitoring
    client_ip = request.client.host if request else "unknown"
    logger.info(f"Plugin creation requested by user {current_user.username} from {client_ip}")
    
    service = get_plugin_service(db)
    
    try:
        plugin = service.create_plugin(plugin_data, created_by=current_user.username)
        return plugin
    except Exception as e:
        logger.error(f"Failed to create plugin: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/{plugin_id}",
    summary="获取插件详情",
    responses={
        200: {"description": "插件详情"},
        401: {"description": "未授权"},
        403: {"description": "权限不足"},
        404: {"description": "插件不存在"},
    },
)
def get_plugin_api(
    plugin_id: str,
    current_user: User = Depends(require_permission("plugin", "read")),
    db: Session = Depends(get_db),
    request: Request = None,
) -> PluginResponse:
    """获取插件详情。需要plugin:read权限。"""
    # Rate limiting
    user_id = str(current_user.id)
    check_rate_limit(user_id, requests_per_minute=60)
    
    # Log for security monitoring
    client_ip = request.client.host if request else "unknown"
    logger.info(f"Plugin details requested by user {current_user.username} from {client_ip}")
    
    service = get_plugin_service(db)
    plugin = service.get_plugin(plugin_id)
    
    if not plugin:
        raise HTTPException(status_code=404, detail=f"Plugin '{plugin_id}' not found")
    
    return plugin


@router.put(
    "/{plugin_id}",
    summary="更新插件",
    responses={
        200: {"description": "插件更新成功"},
        401: {"description": "未授权"},
        403: {"description": "权限不足"},
        404: {"description": "插件不存在"},
    },
)
def update_plugin(
    plugin_id: str,
    plugin_data: PluginUpdate,
    current_user: User = Depends(require_permission("plugin", "update")),
    db: Session = Depends(get_db),
    request: Request = None,
) -> PluginResponse:
    """更新插件。需要plugin:update权限。"""
    # Rate limiting
    user_id = str(current_user.id)
    check_rate_limit(user_id, requests_per_minute=30)
    
    # Log for security monitoring
    client_ip = request.client.host if request else "unknown"
    logger.info(f"Plugin update requested by user {current_user.username} from {client_ip}")
    
    service = get_plugin_service(db)
    plugin = service.update_plugin(plugin_id, plugin_data)
    
    if not plugin:
        raise HTTPException(status_code=404, detail=f"Plugin '{plugin_id}' not found")
    
    return plugin


@router.delete(
    "/{plugin_id}",
    summary="删除插件",
    responses={
        200: {"description": "插件删除成功"},
        401: {"description": "未授权"},
        403: {"description": "权限不足"},
        404: {"description": "插件不存在"},
    },
)
def delete_plugin(
    plugin_id: str,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
    request: Request = None,
) -> dict:
    """删除插件。需要admin角色。"""
    # Rate limiting
    user_id = str(current_user.id)
    check_rate_limit(user_id, requests_per_minute=10)
    
    # Log for security monitoring
    client_ip = request.client.host if request else "unknown"
    logger.warning(f"Plugin deletion requested by admin {current_user.username} from {client_ip}")
    
    service = get_plugin_service(db)
    success = service.delete_plugin(plugin_id)
    
    if not success:
        raise HTTPException(status_code=404, detail=f"Plugin '{plugin_id}' not found")
    
    return {"message": "Plugin deleted successfully"}


@router.post(
    "/{name}/run",
    summary="运行指定插件",
    responses={
        200: {"description": "插件执行结果"},
        401: {"description": "未授权"},
        403: {"description": "权限不足"},
        404: {"description": "插件不存在"},
        500: {"description": "插件执行失败"},
    },
)
def run_plugin(
    name: str,
    run_request: PluginRunRequest = PluginRunRequest(),
    current_user: User = Depends(require_permission("plugin", "execute")),
    db: Session = Depends(get_db),
    request: Request = None,
) -> PluginRunResponse:
    """运行指定插件并返回执行结果。需要plugin:execute权限。"""
    # Rate limiting
    user_id = str(current_user.id)
    check_rate_limit(user_id, requests_per_minute=30)
    
    # Log for security monitoring
    client_ip = request.client.host if request else "unknown"
    logger.info(f"Plugin execution requested by user {current_user.username} from {client_ip}")
    
    service = get_plugin_service(db)
    
    try:
        result = service.run_plugin(name, run_request, executed_by=current_user.username)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to run plugin '{name}': {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/stats",
    summary="获取插件统计信息",
    responses={
        200: {"description": "插件统计信息"},
        401: {"description": "未授权"},
        403: {"description": "权限不足"},
    },
)
def get_plugin_stats(
    current_user: User = Depends(require_permission("plugin", "read")),
    db: Session = Depends(get_db),
    request: Request = None,
) -> PluginStatsResponse:
    """获取插件统计信息。需要plugin:read权限。"""
    # Rate limiting
    user_id = str(current_user.id)
    check_rate_limit(user_id, requests_per_minute=60)
    
    # Log for security monitoring
    client_ip = request.client.host if request else "unknown"
    logger.info(f"Plugin stats requested by user {current_user.username} from {client_ip}")
    
    service = get_plugin_service(db)
    stats = service.get_stats()
    return stats


@router.get(
    "/{plugin_id}/executions",
    summary="获取插件执行记录",
    responses={
        200: {"description": "插件执行记录列表"},
        401: {"description": "未授权"},
        403: {"description": "权限不足"},
    },
)
def list_plugin_executions(
    plugin_id: str,
    success: Optional[bool] = Query(None, description="按成功状态过滤"),
    limit: int = Query(100, ge=1, le=1000, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
    current_user: User = Depends(require_permission("plugin", "read")),
    db: Session = Depends(get_db),
    request: Request = None,
) -> PluginExecutionListResponse:
    """获取插件执行记录。需要plugin:read权限。"""
    # Rate limiting
    user_id = str(current_user.id)
    check_rate_limit(user_id, requests_per_minute=60)
    
    # Log for security monitoring
    client_ip = request.client.host if request else "unknown"
    logger.info(f"Plugin executions requested by user {current_user.username} from {client_ip}")
    
    service = get_plugin_service(db)
    executions = service.list_executions(
        plugin_id=plugin_id,
        success=success,
        limit=limit,
        offset=offset,
    )
    
    total = service.count_executions(plugin_id=plugin_id, success=success)
    
    return PluginExecutionListResponse(total=total, executions=executions)


@router.get(
    "/{plugin_id}/config",
    summary="获取插件配置",
    responses={
        200: {"description": "插件配置"},
        401: {"description": "未授权"},
        403: {"description": "权限不足"},
        404: {"description": "插件配置不存在"},
    },
)
def get_plugin_config(
    plugin_id: str,
    current_user: User = Depends(require_permission("plugin", "read")),
    db: Session = Depends(get_db),
    request: Request = None,
) -> PluginConfigResponse:
    """获取插件配置。需要plugin:read权限。"""
    # Rate limiting
    user_id = str(current_user.id)
    check_rate_limit(user_id, requests_per_minute=60)
    
    # Log for security monitoring
    client_ip = request.client.host if request else "unknown"
    logger.info(f"Plugin config requested by user {current_user.username} from {client_ip}")
    
    service = get_plugin_service(db)
    config = service.get_config_by_plugin_id(plugin_id)
    
    if not config:
        raise HTTPException(status_code=404, detail=f"Plugin config for '{plugin_id}' not found")
    
    return config


@router.put(
    "/{plugin_id}/config",
    summary="更新插件配置",
    responses={
        200: {"description": "插件配置更新成功"},
        401: {"description": "未授权"},
        403: {"description": "权限不足"},
        404: {"description": "插件配置不存在"},
    },
)
def update_plugin_config(
    plugin_id: str,
    config_data: PluginConfigUpdate,
    current_user: User = Depends(require_permission("plugin", "update")),
    db: Session = Depends(get_db),
    request: Request = None,
) -> PluginConfigResponse:
    """更新插件配置。需要plugin:update权限。"""
    # Rate limiting
    user_id = str(current_user.id)
    check_rate_limit(user_id, requests_per_minute=30)
    
    # Log for security monitoring
    client_ip = request.client.host if request else "unknown"
    logger.info(f"Plugin config update requested by user {current_user.username} from {client_ip}")
    
    service = get_plugin_service(db)
    config = service.get_config_by_plugin_id(plugin_id)
    
    if not config:
        raise HTTPException(status_code=404, detail=f"Plugin config for '{plugin_id}' not found")
    
    updated_config = service.update_config(config.id, config_data, updated_by=current_user.username)
    return updated_config


__all__ = ["router"]
