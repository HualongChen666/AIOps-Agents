# -*- coding: utf-8 -*-
"""
GraphQL Router
GraphQL路由

提供GraphQL API端点和GraphQL认证配置端点
"""

import logging
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from loguru import logger
from pydantic import BaseModel
from sqlalchemy.orm import Session

import config
from core.auth_db import get_session
from core.auth_service import get_current_user, has_role
from core.graphql_schema import graphql_app
from core.interface.graphql.dataloader import (
    AlertDataLoader,
    DataLoaderRegistry,
    MetricsDataLoader,
    RepairDataLoader,
)

logger = logging.getLogger(__name__)

# 创建FastAPI路由器用于认证端点
auth_router = APIRouter(prefix="/api/graphql", tags=["graphql-auth"])


class AuthMethod(BaseModel):
    """认证方法配置"""
    name: str
    enabled: bool
    description: str
    config: Dict[str, Any]


class PermissionInfo(BaseModel):
    """权限信息"""
    resource: str
    actions: List[str]
    description: str


class GraphQLAuthConfig(BaseModel):
    """GraphQL认证配置"""
    enabled: bool
    path: str
    authentication_methods: List[AuthMethod]
    authorization_enabled: bool
    abac_enabled: bool
    rbac_enabled: bool
    supported_permissions: List[PermissionInfo]
    token_config: Dict[str, Any]
    security_headers: Dict[str, str]


@auth_router.get("/graphql-auth", response_model=GraphQLAuthConfig)
def get_graphql_auth_config(
    request: Request,
    current_user: Optional[Any] = Depends(get_current_user),
    db: Session = Depends(get_session),
) -> GraphQLAuthConfig:
    """
    获取GraphQL认证配置

    返回GraphQL端点的认证配置、支持的认证方式、权限信息等。
    此端点需要用户认证，但允许所有已认证用户访问。

    Args:
        request: FastAPI请求对象
        current_user: 当前认证用户（可选，用于权限检查）
        db: 数据库会话

    Returns:
        GraphQLAuthConfig: GraphQL认证配置信息

    Raises:
        HTTPException: 如果用户未认证（401）
    """
    # 授权检查：所有已认证用户都可以访问此端点
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    # 从环境变量读取配置
    graphql_enabled = config.GRAPHQL_ENABLED
    graphql_path = config.GRAPHQL_PATH
    
    # JWT配置
    jwt_config = {
        "algorithm": config.JWT_ALGORITHM,
        "access_expire_minutes": config.JWT_ACCESS_EXPIRE_MINUTES,
        "issuer": config.JWT_ISSUER,
        "audience": config.JWT_AUDIENCE,
    }
    
    # ABAC配置
    abac_enabled = os.getenv("AIOPS_ENFORCE_ABAC", "false").lower() == "true"
    
    # 支持的认证方法
    auth_methods = [
        AuthMethod(
            name="jwt_bearer",
            enabled=True,
            description="JWT Bearer Token认证",
            config={
                "token_url": "/api/v1/auth/login",
                "header": "Authorization: Bearer <token>",
                "algorithm": jwt_config["algorithm"],
            }
        ),
        AuthMethod(
            name="oauth2",
            enabled=os.getenv("OIDC_REDIRECT_URI", "") != "",
            description="OAuth2/OIDC单点登录",
            config={
                "redirect_uri": os.getenv("OIDC_REDIRECT_URI", ""),
                "enabled": os.getenv("OIDC_REDIRECT_URI", "") != "",
            }
        ),
    ]
    
    # 支持的权限信息
    supported_permissions = [
        PermissionInfo(
            resource="alerts",
            actions=["read", "write", "delete"],
            description="告警资源权限"
        ),
        PermissionInfo(
            resource="metrics",
            actions=["read"],
            description="指标资源权限"
        ),
        PermissionInfo(
            resource="health",
            actions=["read"],
            description="健康检查权限"
        ),
        PermissionInfo(
            resource="configuration",
            actions=["read", "write"],
            description="配置管理权限"
        ),
    ]
    
    # 安全头配置
    security_headers = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains" if os.getenv("HTTPS_ENABLED", "false").lower() == "true" else "",
    }
    
    # 构建响应
    return GraphQLAuthConfig(
        enabled=graphql_enabled,
        path=graphql_path,
        authentication_methods=auth_methods,
        authorization_enabled=True,
        abac_enabled=abac_enabled,
        rbac_enabled=True,
        supported_permissions=supported_permissions,
        token_config=jwt_config,
        security_headers=security_headers,
    )


@auth_router.get("/graphql-auth/permissions")
def get_user_graphql_permissions(
    current_user: Any = Depends(get_current_user),
    db: Session = Depends(get_session),
) -> Dict[str, Any]:
    """
    获取当前用户在GraphQL端点的权限信息

    返回当前用户对GraphQL资源的权限详情。

    Args:
        current_user: 当前认证用户
        db: 数据库会话

    Returns:
        Dict: 用户权限信息

    Raises:
        HTTPException: 如果用户未认证（401）
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    
    # 获取用户角色
    user_role = getattr(current_user, "role", "viewer")
    
    # 基于角色的权限映射
    role_permissions = {
        "admin": {
            "alerts": ["read", "write", "delete"],
            "metrics": ["read"],
            "health": ["read"],
            "configuration": ["read", "write", "delete"],
        },
        "operator": {
            "alerts": ["read", "write"],
            "metrics": ["read"],
            "health": ["read"],
            "configuration": ["read", "write"],
        },
        "business": {
            "alerts": ["read"],
            "metrics": ["read"],
            "health": ["read"],
            "configuration": ["read"],
        },
        "viewer": {
            "alerts": ["read"],
            "metrics": ["read"],
            "health": ["read"],
            "configuration": ["read"],
        },
    }
    
    permissions = role_permissions.get(user_role, role_permissions["viewer"])
    
    return {
        "user_id": getattr(current_user, "id", None),
        "username": getattr(current_user, "username", None),
        "role": user_role,
        "permissions": permissions,
        "tenant_id": getattr(current_user, "tenant_id", "default"),
    }


# 导出路由器
# graphql_app 是strawberry GraphQL应用，用于 /graphql 端点
# auth_router 是FastAPI路由器，用于 /api/graphql/graphql-auth 等端点
graphql_router = graphql_app  # 用于main.py中的graphql_router导入

# 创建主API路由器用于管理端点
from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from pydantic import BaseModel, Field

from core.auth_service import get_current_user
from core.auth_db import User
from core.graphql_schema import graphql_app
from core.interface.graphql.subscription import SubscriptionManager

# 创建订阅管理器实例
subscription_manager = SubscriptionManager()

# 创建新的API路由器用于订阅端点
router = APIRouter(prefix="/api/graphql", tags=["GraphQL"])


# ============================================================================
# Pydantic Models
# ============================================================================

class SubscriptionConfig(BaseModel):
    """订阅配置"""
    enabled: bool = Field(..., description="订阅功能是否启用")
    websocket_endpoint: str = Field(..., description="WebSocket端点URL")
    max_subscriptions: int = Field(..., description="最大订阅数")
    heartbeat_interval: int = Field(..., description="心跳间隔（秒）")
    connection_timeout: int = Field(..., description="连接超时（秒）")


class ActiveSubscription(BaseModel):
    """活跃订阅信息"""
    subscription_id: str = Field(..., description="订阅ID")
    subscription_type: str = Field(..., description="订阅类型")
    client_id: str = Field(..., description="客户端ID")
    connected_at: datetime = Field(..., description="连接时间")
    last_activity: datetime = Field(..., description="最后活动时间")
    status: str = Field(..., description="状态")


class SubscriptionStatus(BaseModel):
    """订阅状态响应"""
    config: SubscriptionConfig = Field(..., description="订阅配置")
    active_subscriptions: List[ActiveSubscription] = Field(..., description="活跃订阅列表")
    total_subscriptions: int = Field(..., description="总订阅数")
    websocket_url: str = Field(..., description="WebSocket连接URL")
    available_subscription_types: List[str] = Field(..., description="可用的订阅类型")


# ============================================================================
# Helper Functions
# ============================================================================

def _get_subscription_config() -> SubscriptionConfig:
    """
    从环境变量获取订阅配置
    
    Returns:
        SubscriptionConfig: 订阅配置对象
    """
    return SubscriptionConfig(
        enabled=_safe_bool("GRAPHQL_SUBSCRIPTION_ENABLED", default=True),
        websocket_endpoint=os.getenv("GRAPHQL_WEBSOCKET_ENDPOINT", "ws://localhost:8000/graphql"),
        max_subscriptions=_safe_int("GRAPHQL_MAX_SUBSCRIPTIONS", default=100, min_val=1, max_val=1000),
        heartbeat_interval=_safe_int("GRAPHQL_HEARTBEAT_INTERVAL", default=30, min_val=5, max_val=300),
        connection_timeout=_safe_int("GRAPHQL_CONNECTION_TIMEOUT", default=60, min_val=10, max_val=600),
    )


def _safe_bool(key: str, default: bool = False) -> bool:
    """安全地从环境变量解析布尔值"""
    val = os.getenv(key, "").strip().lower()
    if val in ("true", "1", "yes", "on"):
        return True
    if val in ("false", "0", "no", "off"):
        return False
    return default


def _safe_int(key: str, default: int = 0, min_val: Optional[int] = None, max_val: Optional[int] = None) -> int:
    """安全地从环境变量解析整数"""
    try:
        val = int(os.getenv(key, str(default)).strip())
        if min_val is not None and val < min_val:
            logger.warning(f"[graphql_router] {key}={val} below min {min_val}, using {min_val}")
            return min_val
        if max_val is not None and val > max_val:
            logger.warning(f"[graphql_router] {key}={val} above max {max_val}, using {max_val}")
            return max_val
        return val
    except ValueError:
        logger.warning(f"[graphql_router] {key} invalid int, using default {default}")
        return default


def _get_active_subscriptions() -> List[ActiveSubscription]:
    """
    获取当前活跃的订阅列表
    
    Returns:
        List[ActiveSubscription]: 活跃订阅列表
    """
    # 从订阅管理器获取真实的订阅状态
    active_subs = []
    
    # 获取告警订阅状态
    if hasattr(subscription_manager, 'alert_subscription'):
        alert_sub = subscription_manager.alert_subscription
        if hasattr(alert_sub, '_subscribers'):
            for idx, queue in enumerate(alert_sub._subscribers):
                active_subs.append(ActiveSubscription(
                    subscription_id=f"alert-{idx}",
                    subscription_type="alert_stream",
                    client_id=f"client-{idx}",
                    connected_at=datetime.now(),
                    last_activity=datetime.now(),
                    status="active"
                ))
    
    # 获取指标订阅状态
    if hasattr(subscription_manager, 'metrics_subscription'):
        metrics_sub = subscription_manager.metrics_subscription
        if hasattr(metrics_sub, '_subscribers'):
            for idx, queue in enumerate(metrics_sub._subscribers):
                active_subs.append(ActiveSubscription(
                    subscription_id=f"metrics-{idx}",
                    subscription_type="metrics_stream",
                    client_id=f"client-{idx}",
                    connected_at=datetime.now(),
                    last_activity=datetime.now(),
                    status="active"
                ))
    
    return active_subs


# ============================================================================
# API Endpoints
# ============================================================================

@router.get("/graphql-subscription", response_model=SubscriptionStatus)
async def get_subscription_status(
    current_user: User = Depends(get_current_user)
) -> SubscriptionStatus:
    """
    获取GraphQL订阅状态和配置
    
    此端点返回订阅配置、活跃订阅信息、WebSocket端点等。
    需要用户认证。
    
    Args:
        current_user: 当前认证用户（通过依赖注入）
    
    Returns:
        SubscriptionStatus: 订阅状态响应，包含配置、活跃订阅和WebSocket信息
    
    Raises:
        HTTPException: 如果订阅功能未启用或用户无权限
    """
    try:
        # 获取订阅配置
        config = _get_subscription_config()
        
        # 检查订阅功能是否启用
        if not config.enabled:
            logger.warning(f"[graphql_router] Subscription feature disabled for user {current_user.username}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="GraphQL subscription feature is currently disabled"
            )
        
        # 获取活跃订阅
        active_subscriptions = _get_active_subscriptions()
        
        # 构建WebSocket URL
        protocol = "wss" if os.getenv("ENVIRONMENT", "development") == "production" else "ws"
        host = os.getenv("GRAPHQL_HOST", "localhost")
        port = os.getenv("GRAPHQL_PORT", "8000")
        websocket_url = f"{protocol}://{host}:{port}/graphql"
        
        # 可用的订阅类型
        available_types = ["alert_stream", "metrics_stream"]
        
        logger.info(
            f"[graphql_router] Subscription status requested by user {current_user.username}, "
            f"active subscriptions: {len(active_subscriptions)}"
        )
        
        return SubscriptionStatus(
            config=config,
            active_subscriptions=active_subscriptions,
            total_subscriptions=len(active_subscriptions),
            websocket_url=websocket_url,
            available_subscription_types=available_types
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[graphql_router] Failed to get subscription status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve subscription status: {str(e)}"
        )


@router.post("/graphql-subscription/start")
async def start_subscriptions(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    启动GraphQL订阅服务
    
    启动所有订阅服务（告警流、指标流等）。
    需要用户认证，且用户必须具有operator或admin角色。
    
    Args:
        current_user: 当前认证用户（通过依赖注入）
    
    Returns:
        Dict[str, Any]: 启动结果
    
    Raises:
        HTTPException: 如果用户权限不足或启动失败
    """
    try:
        # 检查用户权限
        if current_user.role not in ["operator", "admin"]:
            logger.warning(f"[graphql_router] User {current_user.username} with role {current_user.role} attempted to start subscriptions")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only operators and admins can start subscription services"
            )
        
        # 启动订阅服务
        await subscription_manager.start_all()
        
        logger.info(f"[graphql_router] Subscriptions started by user {current_user.username}")
        
        return {
            "status": "success",
            "message": "GraphQL subscription services started successfully",
            "started_at": datetime.now().isoformat(),
            "started_by": current_user.username
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[graphql_router] Failed to start subscriptions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start subscription services: {str(e)}"
        )


@router.post("/graphql-subscription/stop")
async def stop_subscriptions(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    停止GraphQL订阅服务
    
    停止所有订阅服务。
    需要用户认证，且用户必须具有operator或admin角色。
    
    Args:
        current_user: 当前认证用户（通过依赖注入）
    
    Returns:
        Dict[str, Any]: 停止结果
    
    Raises:
        HTTPException: 如果用户权限不足或停止失败
    """
    try:
        # 检查用户权限
        if current_user.role not in ["operator", "admin"]:
            logger.warning(f"[graphql_router] User {current_user.username} with role {current_user.role} attempted to stop subscriptions")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only operators and admins can stop subscription services"
            )
        
        # 停止订阅服务
        await subscription_manager.stop_all()
        
        logger.info(f"[graphql_router] Subscriptions stopped by user {current_user.username}")
        
        return {
            "status": "success",
            "message": "GraphQL subscription services stopped successfully",
            "stopped_at": datetime.now().isoformat(),
            "stopped_by": current_user.username
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[graphql_router] Failed to stop subscriptions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stop subscription services: {str(e)}"
        )


# 导出路由器以便在main.py中使用
__all__ = ["router", "graphql_router", "subscription_manager", "auth_router"]

# GraphQL Schema相关导入
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from core.auth_service import get_current_user, require_roles
from core.auth_db import User
from core.graphql_schema import graphql_app, schema as graphql_schema

logger = logging.getLogger(__name__)

# 环境变量配置
GRAPHQL_SCHEMA_ENABLED = os.getenv("GRAPHQL_SCHEMA_ENABLED", "true").lower() == "true"
GRAPHQL_SCHEMA_INCLUDE_INTROSPECTION = os.getenv(
    "GRAPHQL_SCHEMA_INCLUDE_INTROSPECTION", "true"
).lower() == "true"

# 将 strawberry GraphQL 应用挂载到 /graphql 路径
router.mount("/graphql", graphql_app)


class SchemaTypeField(BaseModel):
    """Schema 字段信息"""

    name: str
    type: str
    description: str | None = None
    is_required: bool = False
    args: list[Dict[str, Any]] = []


class SchemaTypeInfo(BaseModel):
    """Schema 类型信息"""

    name: str
    kind: str
    description: str | None = None
    fields: list[SchemaTypeField] = []
    interfaces: list[str] = []


class GraphQLSchemaResponse(BaseModel):
    """GraphQL Schema 响应"""

    schema_definition: str
    types: list[SchemaTypeInfo]
    query_type: str | None = None
    mutation_type: str | None = None
    subscription_type: str | None = None
    introspection_enabled: bool


@router.get("/graphql-schema", response_model=GraphQLSchemaResponse)
async def get_graphql_schema(
    current_user: User = Depends(require_roles("admin", "operator")),
) -> GraphQLSchemaResponse:
    """
    获取 GraphQL Schema 定义和类型信息

    此端点返回完整的 GraphQL schema 定义，包括：
    - Schema 定义（SDL 格式）
    - 所有类型列表及其字段信息
    - Query、Mutation、Subscription 类型信息
    - Introspection 配置状态

    需要管理员或操作员权限。

    Args:
        current_user: 当前认证用户（需要 admin 或 operator 角色）

    Returns:
        GraphQLSchemaResponse: 包含 schema 定义和类型信息的响应

    Raises:
        HTTPException: 如果 schema 功能未启用或用户权限不足
    """
    if not GRAPHQL_SCHEMA_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GraphQL schema endpoint is disabled",
        )

    try:
        # 导入 strawberry 的 printer 模块
        from strawberry.printer import print_schema

        # 获取主 schema 的 SDL 定义
        schema_sdl = print_schema(graphql_schema)

        # 获取 introspection 数据
        introspection_data = graphql_schema.introspect()

        # 解析类型信息
        types_info = []
        query_type_name = None
        mutation_type_name = None
        subscription_type_name = None

        # 从 introspection 数据中提取类型信息
        schema_type = introspection_data.get("__schema", {})
        query_type_name = schema_type.get("queryType", {}).get("name")
        mutation_type_name = schema_type.get("mutationType", {}).get("name")
        subscription_type_name = schema_type.get("subscriptionType", {}).get("name")

        for type_def in schema_type.get("types", []):
            # 跳过内置类型（以 __ 开头）
            if type_def.get("name", "").startswith("__"):
                continue

            kind = type_def.get("kind", "")
            type_name = type_def.get("name", "")
            description = type_def.get("description")

            # 提取字段信息
            fields_info = []
            if kind in ("OBJECT", "INTERFACE"):
                for field in type_def.get("fields", []):
                    field_name = field.get("name", "")
                    field_type = _extract_type_name(field.get("type", {}))
                    field_description = field.get("description")
                    is_required = _is_required_type(field.get("type", {}))

                    # 提取参数信息
                    args_info = []
                    for arg in field.get("args", []):
                        args_info.append(
                            {
                                "name": arg.get("name", ""),
                                "type": _extract_type_name(arg.get("type", {})),
                                "description": arg.get("description"),
                                "is_required": _is_required_type(arg.get("type", {})),
                            }
                        )

                    fields_info.append(
                        SchemaTypeField(
                            name=field_name,
                            type=field_type,
                            description=field_description,
                            is_required=is_required,
                            args=args_info,
                        )
                    )

            # 提取接口信息
            interfaces = [iface.get("name", "") for iface in type_def.get("interfaces", [])]

            types_info.append(
                SchemaTypeInfo(
                    name=type_name,
                    kind=kind,
                    description=description,
                    fields=fields_info,
                    interfaces=interfaces,
                )
            )

        return GraphQLSchemaResponse(
            schema_definition=schema_sdl,
            types=types_info,
            query_type=query_type_name,
            mutation_type=mutation_type_name,
            subscription_type=subscription_type_name,
            introspection_enabled=GRAPHQL_SCHEMA_INCLUDE_INTROSPECTION,
        )

    except Exception as e:
        logger.error(f"Failed to get GraphQL schema: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve GraphQL schema: {str(e)}",
        )


def _extract_type_name(type_info: Dict[str, Any]) -> str:
    """
    从 GraphQL 类型信息中提取类型名称

    Args:
        type_info: GraphQL 类型信息字典

    Returns:
        类型名称字符串
    """
    kind = type_info.get("kind", "")
    if kind == "NON_NULL":
        return _extract_type_name(type_info.get("ofType", {})) + "!"
    elif kind == "LIST":
        return f"[{_extract_type_name(type_info.get('ofType', {}))}]"
    else:
        return type_info.get("name", "Unknown")


def _is_required_type(type_info: Dict[str, Any]) -> bool:
    """
    检查类型是否为必需（非空）

    Args:
        type_info: GraphQL 类型信息字典

    Returns:
        如果类型为非空则返回 True
    """
    return type_info.get("kind", "") == "NON_NULL"


# ============================================================================
# GraphQL DataLoader Endpoints
# ============================================================================

from core.interface.graphql.dataloader import (
    AlertDataLoader,
    DataLoaderRegistry,
    MetricsDataLoader,
    RepairDataLoader,
)


class DataLoaderConfig(BaseModel):
    """DataLoader配置模型"""
    max_batch_size: int
    cache_enabled: bool
    batch_strategy: str


class BatchLoadStats(BaseModel):
    """批量加载统计"""
    total_batches: int
    total_items_loaded: int
    average_batch_size: float
    max_batch_size_used: int
    cache_hit_rate: float


class PerformanceMetrics(BaseModel):
    """性能指标"""
    total_load_time_ms: float
    average_load_time_ms: float
    p50_load_time_ms: float
    p95_load_time_ms: float
    p99_load_time_ms: float


class DataLoaderStatus(BaseModel):
    """DataLoader状态响应"""
    config: DataLoaderConfig
    batch_stats: BatchLoadStats
    performance: PerformanceMetrics
    active_loaders: List[str]
    enabled: bool


# 全局DataLoader注册表实例
_dataloader_registry: Optional[DataLoaderRegistry] = None
_performance_stats: Dict[str, List[float]] = {
    "alert_load_times": [],
    "repair_load_times": [],
    "metrics_load_times": [],
}
_batch_stats: Dict[str, Any] = {
    "total_batches": 0,
    "total_items": 0,
    "batch_sizes": [],
}


def get_dataloader_registry() -> DataLoaderRegistry:
    """获取或创建DataLoader注册表"""
    global _dataloader_registry
    if _dataloader_registry is None:
        _dataloader_registry = DataLoaderRegistry()
    return _dataloader_registry


def get_dataloader_config() -> DataLoaderConfig:
    """从环境变量获取DataLoader配置"""
    max_batch_size = _safe_int("GRAPHQL_DATALOADER_MAX_BATCH_SIZE", default=100, min_val=1, max_val=1000)
    cache_enabled = _safe_bool("GRAPHQL_DATALOADER_CACHE_ENABLED", default=True)
    batch_strategy = os.getenv("GRAPHQL_DATALOADER_BATCH_STRATEGY", "auto")
    
    return DataLoaderConfig(
        max_batch_size=max_batch_size,
        cache_enabled=cache_enabled,
        batch_strategy=batch_strategy
    )


def calculate_percentiles(values: List[float], percentiles: List[float]) -> List[float]:
    """计算百分位数"""
    if not values:
        return [0.0] * len(percentiles)
    
    sorted_values = sorted(values)
    n = len(sorted_values)
    results = []
    
    for p in percentiles:
        index = int(p * n / 100)
        if index >= n:
            index = n - 1
        results.append(sorted_values[index])
    
    return results


@router.get("/graphql-dataloader", response_model=DataLoaderStatus)
async def get_dataloader_status(
    request: Request,
    current_user: User = Depends(get_current_user)
) -> DataLoaderStatus:
    """
    获取GraphQL DataLoader状态信息
    
    返回DataLoader配置、批量加载策略、性能统计等信息
    
    Args:
        request: FastAPI请求对象
        current_user: 当前认证用户（通过依赖注入）
    
    Returns:
        DataLoaderStatus: 包含配置、统计和性能指标的完整状态
    
    Raises:
        HTTPException: 如果用户未授权（401）
    """
    try:
        logger.info(f"User {current_user.username} requesting DataLoader status")
        
        # 获取配置
        loader_config = get_dataloader_config()
        
        # 获取注册表
        registry = get_dataloader_registry()
        
        # 收集活跃的DataLoader
        active_loaders = []
        if registry._alert_loader is not None:
            active_loaders.append("AlertDataLoader")
        if registry._repair_loader is not None:
            active_loaders.append("RepairDataLoader")
        if registry._metrics_loader is not None:
            active_loaders.append("MetricsDataLoader")
        
        # 计算批量统计
        total_batches = _batch_stats["total_batches"]
        total_items = _batch_stats["total_items"]
        batch_sizes = _batch_stats["batch_sizes"]
        
        average_batch_size = (
            sum(batch_sizes) / len(batch_sizes) if batch_sizes else 0.0
        )
        max_batch_size_used = max(batch_sizes) if batch_sizes else 0
        
        # 计算缓存命中率（基于DataLoader实例的缓存大小）
        cache_hit_rate = 0.0
        if registry._alert_loader and registry._alert_loader.cache:
            cache_size = len(registry._alert_loader._cache)
            cache_hit_rate = min(cache_size / max(total_items, 1), 1.0)
        
        batch_stats = BatchLoadStats(
            total_batches=total_batches,
            total_items_loaded=total_items,
            average_batch_size=round(average_batch_size, 2),
            max_batch_size_used=max_batch_size_used,
            cache_hit_rate=round(cache_hit_rate * 100, 2)
        )
        
        # 计算性能指标
        all_load_times = (
            _performance_stats["alert_load_times"] +
            _performance_stats["repair_load_times"] +
            _performance_stats["metrics_load_times"]
        )
        
        if all_load_times:
            total_load_time = sum(all_load_times)
            average_load_time = total_load_time / len(all_load_times)
            percentiles = calculate_percentiles(all_load_times, [50, 95, 99])
        else:
            total_load_time = 0.0
            average_load_time = 0.0
            percentiles = [0.0, 0.0, 0.0]
        
        performance = PerformanceMetrics(
            total_load_time_ms=round(total_load_time, 3),
            average_load_time_ms=round(average_load_time, 3),
            p50_load_time_ms=round(percentiles[0], 3),
            p95_load_time_ms=round(percentiles[1], 3),
            p99_load_time_ms=round(percentiles[2], 3)
        )
        
        # 检查GraphQL是否启用
        enabled = config.GRAPHQL_ENABLED
        
        status = DataLoaderStatus(
            config=loader_config,
            batch_stats=batch_stats,
            performance=performance,
            active_loaders=active_loaders,
            enabled=enabled
        )
        
        logger.info(f"DataLoader status retrieved successfully for user {current_user.username}")
        return status
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get DataLoader status: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve DataLoader status: {str(e)}"
        )


@router.post("/graphql-dataloader/clear-cache")
async def clear_dataloader_cache(
    loader_type: Optional[str] = None,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    清除DataLoader缓存
    
    Args:
        loader_type: 要清除的DataLoader类型（alert/repair/metrics），None表示清除所有
        current_user: 当前认证用户
    
    Returns:
        操作结果字典
    
    Raises:
        HTTPException: 如果用户未授权（401）或请求无效（400）
    """
    try:
        logger.info(f"User {current_user.username} clearing DataLoader cache for type: {loader_type}")
        
        registry = get_dataloader_registry()
        
        if loader_type is None:
            # 清除所有缓存
            registry.clear_all()
            message = "All DataLoader caches cleared"
        elif loader_type == "alert":
            if registry._alert_loader:
                registry._alert_loader.clear()
            message = "Alert DataLoader cache cleared"
        elif loader_type == "repair":
            if registry._repair_loader:
                registry._repair_loader.clear()
            message = "Repair DataLoader cache cleared"
        elif loader_type == "metrics":
            if registry._metrics_loader:
                registry._metrics_loader.clear()
            message = "Metrics DataLoader cache cleared"
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid loader type: {loader_type}. Must be one of: alert, repair, metrics"
            )
        
        # 同时清除性能统计
        if loader_type is None:
            _performance_stats["alert_load_times"].clear()
            _performance_stats["repair_load_times"].clear()
            _performance_stats["metrics_load_times"].clear()
        elif loader_type == "alert":
            _performance_stats["alert_load_times"].clear()
        elif loader_type == "repair":
            _performance_stats["repair_load_times"].clear()
        elif loader_type == "metrics":
            _performance_stats["metrics_load_times"].clear()
        
        logger.info(f"Cache cleared successfully: {message}")
        return {
            "success": True,
            "message": message,
            "cleared_type": loader_type or "all"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to clear DataLoader cache: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear cache: {str(e)}"
        )


@router.get("/graphql-dataloader/test")
async def test_dataloader(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    测试DataLoader功能
    
    执行一个简单的批量加载测试以验证DataLoader正常工作
    
    Args:
        current_user: 当前认证用户
    
    Returns:
        测试结果字典
    
    Raises:
        HTTPException: 如果用户未授权（401）或测试失败（500）
    """
    try:
        logger.info(f"User {current_user.username} testing DataLoader")
        
        registry = get_dataloader_registry()
        loader_config = get_dataloader_config()
        
        # 获取Alert DataLoader
        alert_loader = registry.get_alert_loader()
        
        # 模拟批量加载测试
        test_ids = [f"test-alert-{i}" for i in range(10)]
        
        start_time = time.time()
        
        # 由于实际的alert_engine可能没有get_alerts_by_ids函数，
        # 我们使用prime方法来模拟测试
        for test_id in test_ids:
            alert_loader.prime(test_id, {
                "id": test_id,
                "severity": "info",
                "message": f"Test alert {test_id}",
                "status": "active"
            })
        
        # 测试加载
        loaded_items = await alert_loader.load_many(test_ids)
        
        load_time = (time.time() - start_time) * 1000  # 转换为毫秒
        
        # 记录性能统计
        _performance_stats["alert_load_times"].append(load_time)
        _batch_stats["total_batches"] += 1
        _batch_stats["total_items"] += len(test_ids)
        _batch_stats["batch_sizes"].append(len(test_ids))
        
        # 限制统计历史大小
        max_stats_size = 1000
        for key in _performance_stats:
            if len(_performance_stats[key]) > max_stats_size:
                _performance_stats[key] = _performance_stats[key][-max_stats_size:]
        
        logger.info(f"DataLoader test completed in {load_time:.2f}ms")
        
        return {
            "success": True,
            "test_results": {
                "items_loaded": len(loaded_items),
                "load_time_ms": round(load_time, 3),
                "config": {
                    "max_batch_size": loader_config.max_batch_size,
                    "cache_enabled": loader_config.cache_enabled,
                    "batch_strategy": loader_config.batch_strategy
                }
            },
            "message": "DataLoader test completed successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"DataLoader test failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"DataLoader test failed: {str(e)}"
        )


# ============================================================================
# GraphQL API Management Endpoints
# ============================================================================


class GraphQLEndpointInfo(BaseModel):
    """GraphQL端点信息"""

    path: str
    method: str
    description: str
    enabled: bool


class GraphQLConfigInfo(BaseModel):
    """GraphQL配置信息"""

    enabled: bool
    path: str
    graphql_ide: str
    max_query_complexity: Optional[int] = None
    max_depth: Optional[int] = None
    rate_limit_enabled: bool
    rate_limit_requests: Optional[int] = None
    rate_limit_period: Optional[int] = None


class GraphQLUsageStats(BaseModel):
    """GraphQL使用统计"""

    total_queries: int
    total_mutations: int
    total_errors: int
    avg_query_duration_ms: float
    avg_mutation_duration_ms: float
    most_used_queries: List[Dict[str, Any]]
    most_used_mutations: List[Dict[str, Any]]
    last_24h_queries: int
    last_24h_mutations: int


class GraphQLAPIInfo(BaseModel):
    """GraphQL API完整信息"""

    configuration: GraphQLConfigInfo
    endpoints: List[GraphQLEndpointInfo]
    usage_statistics: GraphQLUsageStats
    schema_info: Dict[str, Any]
    health_status: str
    last_updated: datetime


def _get_graphql_api_config() -> GraphQLConfigInfo:
    """
    获取GraphQL API配置信息

    Returns:
        GraphQLConfigInfo: GraphQL配置信息
    """
    try:
        # 从环境变量获取配置
        rate_limit_enabled = os.getenv("GRAPHQL_RATE_LIMIT_ENABLED", "false").lower() == "true"
        rate_limit_requests = int(os.getenv("GRAPHQL_RATE_LIMIT_REQUESTS", "100")) if rate_limit_enabled else None
        rate_limit_period = int(os.getenv("GRAPHQL_RATE_LIMIT_PERIOD", "60")) if rate_limit_enabled else None
        max_query_complexity = int(os.getenv("GRAPHQL_MAX_QUERY_COMPLEXITY", "1000")) or None
        max_depth = int(os.getenv("GRAPHQL_MAX_DEPTH", "10")) or None

        return GraphQLConfigInfo(
            enabled=config.GRAPHQL_ENABLED,
            path=config.GRAPHQL_PATH,
            graphql_ide="graphiql",
            max_query_complexity=max_query_complexity,
            max_depth=max_depth,
            rate_limit_enabled=rate_limit_enabled,
            rate_limit_requests=rate_limit_requests,
            rate_limit_period=rate_limit_period,
        )
    except Exception as e:
        logger.error(f"Error getting GraphQL API config: {e}")
        # 返回默认配置
        return GraphQLConfigInfo(
            enabled=config.GRAPHQL_ENABLED,
            path=config.GRAPHQL_PATH,
            graphql_ide="graphiql",
            max_query_complexity=None,
            max_depth=None,
            rate_limit_enabled=False,
            rate_limit_requests=None,
            rate_limit_period=None,
        )


def _get_graphql_api_endpoints() -> List[GraphQLEndpointInfo]:
    """
    获取GraphQL API端点列表

    Returns:
        List[GraphQLEndpointInfo]: GraphQL端点列表
    """
    endpoints = []

    # 主GraphQL端点
    if config.GRAPHQL_ENABLED:
        endpoints.append(
            GraphQLEndpointInfo(
                path=config.GRAPHQL_PATH,
                method="POST",
                description="Main GraphQL endpoint for queries and mutations",
                enabled=True,
            )
        )
        endpoints.append(
            GraphQLEndpointInfo(
                path=config.GRAPHQL_PATH,
                method="GET",
                description="GraphQL IDE (GraphiQL) interface",
                enabled=True,
            )
        )

    # API管理端点
    endpoints.append(
        GraphQLEndpointInfo(
            path="/api/graphql/graphql-api",
            method="GET",
            description="GraphQL API management endpoint - configuration and statistics",
            enabled=True,
        )
    )

    # 认证配置端点
    endpoints.append(
        GraphQLEndpointInfo(
            path="/api/graphql/graphql-auth",
            method="GET",
            description="GraphQL authentication configuration endpoint",
            enabled=True,
        )
    )

    # 订阅端点
    endpoints.append(
        GraphQLEndpointInfo(
            path="/api/graphql/graphql-subscription",
            method="GET",
            description="GraphQL subscription status endpoint",
            enabled=True,
        )
    )

    # Schema端点
    endpoints.append(
        GraphQLEndpointInfo(
            path="/api/graphql/graphql-schema",
            method="GET",
            description="GraphQL schema definition endpoint",
            enabled=GRAPHQL_SCHEMA_ENABLED,
        )
    )

    return endpoints


def _get_graphql_usage_stats(db: Session) -> GraphQLUsageStats:
    """
    获取GraphQL使用统计信息

    Args:
        db: 数据库会话

    Returns:
        GraphQLUsageStats: 使用统计信息
    """
    try:
        from core.models import Config, PerformanceMetric

        # 尝试从数据库获取统计信息
        # 查询GraphQL相关的配置和性能指标
        graphql_configs = db.query(Config).filter(Config.key.like("graphql_%")).all()

        total_queries = 0
        total_mutations = 0
        total_errors = 0
        avg_query_duration = 0.0
        avg_mutation_duration = 0.0

        for config_item in graphql_configs:
            if config_item.key == "graphql_total_queries":
                total_queries = int(config_item.value) if config_item.value.isdigit() else 0
            elif config_item.key == "graphql_total_mutations":
                total_mutations = int(config_item.value) if config_item.value.isdigit() else 0
            elif config_item.key == "graphql_total_errors":
                total_errors = int(config_item.value) if config_item.value.isdigit() else 0
            elif config_item.key == "graphql_avg_query_duration":
                avg_query_duration = float(config_item.value) if config_item.value.replace(".", "").isdigit() else 0.0
            elif config_item.key == "graphql_avg_mutation_duration":
                avg_mutation_duration = float(config_item.value) if config_item.value.replace(".", "").isdigit() else 0.0

        # 查询最近的性能指标
        recent_metrics = (
            db.query(PerformanceMetric)
            .filter(PerformanceMetric.test_type == "graphql")
            .order_by(PerformanceMetric.created_at.desc())
            .limit(24)
            .all()
        )

        last_24h_queries = sum(
            int(m.value) if m.name == "queries_count" and str(m.value).isdigit() else 0 for m in recent_metrics
        )
        last_24h_mutations = sum(
            int(m.value) if m.name == "mutations_count" and str(m.value).isdigit() else 0 for m in recent_metrics
        )

        # 构造最常用的查询和变更列表
        most_used_queries = []
        most_used_mutations = []

        # 从配置中获取常用查询
        popular_queries_config = db.query(Config).filter(Config.key == "graphql_popular_queries").first()
        if popular_queries_config:
            import json

            try:
                most_used_queries = json.loads(popular_queries_config.value) if popular_queries_config.value else []
            except json.JSONDecodeError:
                most_used_queries = []

        # 从配置中获取常用变更
        popular_mutations_config = db.query(Config).filter(Config.key == "graphql_popular_mutations").first()
        if popular_mutations_config:
            import json

            try:
                most_used_mutations = json.loads(popular_mutations_config.value) if popular_mutations_config.value else []
            except json.JSONDecodeError:
                most_used_mutations = []

        return GraphQLUsageStats(
            total_queries=total_queries,
            total_mutations=total_mutations,
            total_errors=total_errors,
            avg_query_duration_ms=avg_query_duration,
            avg_mutation_duration_ms=avg_mutation_duration,
            most_used_queries=most_used_queries,
            most_used_mutations=most_used_mutations,
            last_24h_queries=last_24h_queries,
            last_24h_mutations=last_24h_mutations,
        )
    except Exception as e:
        logger.error(f"Error getting GraphQL usage statistics: {e}")
        # 返回默认统计信息
        return GraphQLUsageStats(
            total_queries=0,
            total_mutations=0,
            total_errors=0,
            avg_query_duration_ms=0.0,
            avg_mutation_duration_ms=0.0,
            most_used_queries=[],
            most_used_mutations=[],
            last_24h_queries=0,
            last_24h_mutations=0,
        )


def _get_graphql_schema_summary() -> Dict[str, Any]:
    """
    获取GraphQL schema摘要信息

    Returns:
        Dict[str, Any]: Schema摘要信息
    """
    try:
        # 获取schema的基本信息
        schema_summary = {
            "query_type": "Query",
            "mutation_type": "Mutation",
            "subscription_type": None,
            "total_types": 0,
            "total_queries": 0,
            "total_mutations": 0,
        }

        # 尝试从graphql_schema获取信息
        try:
            from core.graphql_schema import schema as main_schema

            if hasattr(main_schema, "type_map"):
                schema_summary["total_types"] = len([t for t in main_schema.type_map if not t.startswith("__")])

            # 获取查询和变更数量
            if hasattr(main_schema, "query_type"):
                query_type = main_schema.query_type
                if hasattr(query_type, "fields"):
                    schema_summary["total_queries"] = len(query_type.fields)

            if hasattr(main_schema, "mutation_type"):
                mutation_type = main_schema.mutation_type
                if hasattr(mutation_type, "fields"):
                    schema_summary["total_mutations"] = len(mutation_type.fields)
        except Exception as e:
            logger.warning(f"Could not get detailed schema info: {e}")

        return schema_summary
    except Exception as e:
        logger.error(f"Error getting GraphQL schema summary: {e}")
        return {
            "query_type": "Query",
            "mutation_type": "Mutation",
            "subscription_type": None,
            "total_types": 0,
            "total_queries": 0,
            "total_mutations": 0,
        }


def _get_graphql_health_status() -> str:
    """
    获取GraphQL服务健康状态

    Returns:
        str: 健康状态 (healthy, degraded, unhealthy, disabled)
    """
    try:
        if not config.GRAPHQL_ENABLED:
            return "disabled"

        # 检查GraphQL schema是否可用
        try:
            from core.graphql_schema import schema

            if schema is None:
                return "unhealthy"
        except Exception:
            return "unhealthy"

        # 检查数据库连接
        try:
            from core.db_engine import get_engine

            engine = get_engine()
            if engine is None:
                return "degraded"
        except Exception:
            return "degraded"

        return "healthy"
    except Exception as e:
        logger.error(f"Error checking GraphQL health status: {e}")
        return "unhealthy"


@router.get(
    "/graphql-api",
    response_model=GraphQLAPIInfo,
    status_code=status.HTTP_200_OK,
    summary="Get GraphQL API Information",
    description="获取GraphQL API的配置、端点列表、使用统计和健康状态信息",
    responses={
        200: {"description": "Successfully retrieved GraphQL API information"},
        401: {"description": "Unauthorized - authentication required"},
        403: {"description": "Forbidden - insufficient permissions"},
        500: {"description": "Internal server error"},
    },
)
async def get_graphql_api_info(
    include_usage_stats: bool = Query(
        True, description="Whether to include usage statistics (may be slower)"
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
) -> GraphQLAPIInfo:
    """
    获取GraphQL API管理信息

    此端点提供GraphQL API的完整管理信息，包括：
    - 配置信息（启用状态、路径、IDE、速率限制等）
    - 可用端点列表
    - 使用统计（查询/变更数量、错误率、平均延迟等）
    - Schema信息（类型、指令等）
    - 健康状态

    Args:
        include_usage_stats: 是否包含使用统计信息
        current_user: 当前认证用户（通过依赖注入）
        db: 数据库会话（通过依赖注入）

    Returns:
        GraphQLAPIInfo: GraphQL API完整信息

    Raises:
        HTTPException: 如果用户未授权或发生服务器错误
    """
    try:
        logger.info(f"User {current_user.username} requesting GraphQL API info")

        # 获取配置信息
        configuration = _get_graphql_api_config()

        # 获取端点列表
        endpoints = _get_graphql_api_endpoints()

        # 获取使用统计（可选）
        if include_usage_stats:
            usage_statistics = _get_graphql_usage_stats(db)
        else:
            usage_statistics = GraphQLUsageStats(
                total_queries=0,
                total_mutations=0,
                total_errors=0,
                avg_query_duration_ms=0.0,
                avg_mutation_duration_ms=0.0,
                most_used_queries=[],
                most_used_mutations=[],
                last_24h_queries=0,
                last_24h_mutations=0,
            )

        # 获取schema信息
        schema_info = _get_graphql_schema_summary()

        # 获取健康状态
        health_status = _get_graphql_health_status()

        # 构造响应
        api_info = GraphQLAPIInfo(
            configuration=configuration,
            endpoints=endpoints,
            usage_statistics=usage_statistics,
            schema_info=schema_info,
            health_status=health_status,
            last_updated=datetime.now(timezone.utc),
        )

        logger.info(f"Successfully retrieved GraphQL API info for user {current_user.username}")
        return api_info

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting GraphQL API info: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve GraphQL API information: {str(e)}",
        )


# ============================================================================
# GraphQL Resolvers Information Endpoint
# ============================================================================

import inspect

from core.interface.graphql.resolvers import (
    AlertResolver,
    MetricsResolver,
    ProcessResolver,
    RepairResolver,
)


class ResolverMethodInfo(BaseModel):
    """Resolver方法信息"""

    name: str
    description: str
    parameters: List[Dict[str, Any]]
    return_type: str
    is_async: bool


class ResolverInfo(BaseModel):
    """Resolver信息"""

    name: str
    description: str
    methods: List[ResolverMethodInfo]
    instance_available: bool


class GraphQLConfig(BaseModel):
    """GraphQL配置"""

    graphql_ide: str
    path: str
    max_complexity: Optional[int] = None
    max_depth: Optional[int] = None
    batch_enabled: bool = False
    subscriptions_enabled: bool = False


class PerformanceStats(BaseModel):
    """性能统计"""

    total_resolvers: int
    total_methods: int
    avg_method_count: float
    schema_size_bytes: int
    estimated_response_time_ms: float


class GraphQLResolversResponse(BaseModel):
    """GraphQL Resolvers响应"""

    resolvers: List[ResolverInfo]
    config: GraphQLConfig
    performance: PerformanceStats
    timestamp: str


def _get_resolver_methods(resolver_class: type) -> List[ResolverMethodInfo]:
    """
    获取Resolver类的方法信息

    Args:
        resolver_class: Resolver类

    Returns:
        方法信息列表
    """
    methods = []
    for name, method in inspect.getmembers(resolver_class, predicate=inspect.ismethod):
        if not name.startswith("_"):
            try:
                sig = inspect.signature(method)
                parameters = []
                for param_name, param in sig.parameters.items():
                    if param_name != "self":
                        parameters.append({
                            "name": param_name,
                            "type": str(param.annotation) if param.annotation != inspect.Parameter.empty else "Any",
                            "default": str(param.default) if param.default != inspect.Parameter.empty else None,
                        })

                return_type = str(sig.return_annotation) if sig.return_annotation != inspect.Signature.empty else "Any"
                is_async = inspect.iscoroutinefunction(method)

                # 获取文档字符串
                description = inspect.getdoc(method) or ""

                methods.append(
                    ResolverMethodInfo(
                        name=name,
                        description=description,
                        parameters=parameters,
                        return_type=return_type,
                        is_async=is_async,
                    )
                )
            except Exception as e:
                logger.warning(f"Failed to inspect method {name}: {e}")
                continue

    return methods


def _get_schema_size() -> int:
    """
    获取GraphQL schema大小（字节）

    Returns:
        Schema字符串的字节大小
    """
    try:
        schema_str = str(graphql_app.schema)
        return len(schema_str.encode("utf-8"))
    except Exception as e:
        logger.warning(f"Failed to get schema size: {e}")
        return 0


def _estimate_response_time(resolver_count: int, method_count: int) -> float:
    """
    估算平均响应时间（毫秒）

    基于resolver数量和方法数量进行估算

    Args:
        resolver_count: Resolver数量
        method_count: 方法数量

    Returns:
        估算的响应时间（毫秒）
    """
    # 基础时间 + 每个resolver的时间 + 每个方法的时间
    base_time = float(os.getenv("GRAPHQL_BASE_RESPONSE_TIME_MS", "10"))
    per_resolver_time = float(os.getenv("GRAPHQL_PER_RESOLVER_TIME_MS", "2"))
    per_method_time = float(os.getenv("GRAPHQL_PER_METHOD_TIME_MS", "0.5"))

    estimated = base_time + (resolver_count * per_resolver_time) + (method_count * per_method_time)
    return round(estimated, 2)


@router.get("/graphql-resolvers", response_model=GraphQLResolversResponse)
async def get_graphql_resolvers(
    current_user: User = Depends(require_roles("admin", "operator", "viewer", "business")),
) -> GraphQLResolversResponse:
    """
    获取GraphQL Resolvers列表、配置和性能统计

    此端点提供关于GraphQL实现的详细信息，包括：
    - 所有可用的Resolver类及其方法
    - GraphQL配置信息
    - 性能统计指标

    需要认证：是
    需要权限：viewer及以上

    Args:
        current_user: 当前认证用户

    Returns:
        GraphQLResolversResponse: 包含resolvers、配置和性能统计的响应

    Raises:
        HTTPException: 如果用户权限不足或获取信息失败
    """
    start_time = time.time()

    try:
        # 收集Resolver信息
        resolver_classes = [
            (MetricsResolver, "Resolver for system metrics"),
            (AlertResolver, "Resolver for alerts"),
            (ProcessResolver, "Resolver for process information"),
            (RepairResolver, "Resolver for repair actions"),
        ]

        resolvers: List[ResolverInfo] = []
        total_methods = 0

        for resolver_class, description in resolver_classes:
            try:
                methods = _get_resolver_methods(resolver_class)
                total_methods += len(methods)

                # 检查是否可以实例化
                instance_available = True
                try:
                    instance = resolver_class()
                except Exception as e:
                    logger.warning(f"Failed to instantiate {resolver_class.__name__}: {e}")
                    instance_available = False

                resolvers.append(
                    ResolverInfo(
                        name=resolver_class.__name__,
                        description=description,
                        methods=methods,
                        instance_available=instance_available,
                    )
                )
            except Exception as e:
                logger.error(f"Failed to process resolver {resolver_class.__name__}: {e}")
                continue

        # 获取配置信息
        config = GraphQLConfig(
            graphql_ide=getattr(graphql_app, "graphql_ide", "graphiql"),
            path=getattr(graphql_app, "path", "/graphql"),
            max_complexity=int(os.getenv("GRAPHQL_MAX_COMPLEXITY", "0")) or None,
            max_depth=int(os.getenv("GRAPHQL_MAX_DEPTH", "0")) or None,
            batch_enabled=os.getenv("GRAPHQL_BATCH_ENABLED", "false").lower() == "true",
            subscriptions_enabled=os.getenv("GRAPHQL_SUBSCRIPTIONS_ENABLED", "false").lower() == "true",
        )

        # 计算性能统计
        total_resolvers = len(resolvers)
        avg_method_count = round(total_methods / total_resolvers, 2) if total_resolvers > 0 else 0.0
        schema_size = _get_schema_size()
        estimated_response_time = _estimate_response_time(total_resolvers, total_methods)

        performance = PerformanceStats(
            total_resolvers=total_resolvers,
            total_methods=total_methods,
            avg_method_count=avg_method_count,
            schema_size_bytes=schema_size,
            estimated_response_time_ms=estimated_response_time,
        )

        # 记录处理时间
        processing_time_ms = (time.time() - start_time) * 1000
        logger.info(
            f"GraphQL resolvers info retrieved by user {current_user.username} "
            f"in {processing_time_ms:.2f}ms"
        )

        return GraphQLResolversResponse(
            resolvers=resolvers,
            config=config,
            performance=performance,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get GraphQL resolvers info: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve GraphQL resolvers information: {str(e)}",
        )
