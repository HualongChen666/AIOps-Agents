# -*- coding: utf-8 -*-
"""
GraphQL Router
GraphQL路由

提供GraphQL API端点和GraphQL Schema查询端点
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import desc
from sqlalchemy.orm import Session

import config
from core.auth_db import User, get_session
from core.auth_service import get_current_user, require_roles
from core.graphql_schema import graphql_app, schema as graphql_schema
from core.interface.graphql.subscription import SubscriptionManager
from core.models import (
    GraphQLQueryConfig,
    GraphQLQueryHistory,
    GraphQLPerformanceStats,
)

logger = logging.getLogger(__name__)

# 环境变量配置
GRAPHQL_SCHEMA_ENABLED = os.getenv("GRAPHQL_SCHEMA_ENABLED", "true").lower() == "true"
GRAPHQL_SUBSCRIPTION_ENABLED = os.getenv("GRAPHQL_SUBSCRIPTION_ENABLED", "true").lower() == "true"
GRAPHQL_INCLUDE_INTROSPECTION = os.getenv("GRAPHQL_INCLUDE_INTROSPECTION", "true").lower() == "true"

# 创建 FastAPI 路由器
router = APIRouter(prefix="/api/graphql", tags=["GraphQL"])

# 将 strawberry GraphQL 应用挂载到 /graphql 路径
router.mount("/graphql", graphql_app)

# 创建订阅管理器实例
subscription_manager = SubscriptionManager()


# ============================================================================
# Pydantic Models for Schema Endpoint
# ============================================================================

class SchemaTypeField(BaseModel):
    """Schema 字段信息"""
    name: str
    type: str
    description: Optional[str] = None
    is_required: bool = False
    args: List[Dict[str, Any]] = Field(default_factory=list)


class SchemaTypeInfo(BaseModel):
    """Schema 类型信息"""
    name: str
    kind: str
    description: Optional[str] = None
    fields: List[SchemaTypeField] = Field(default_factory=list)
    interfaces: List[str] = Field(default_factory=list)


class GraphQLSchemaResponse(BaseModel):
    """GraphQL Schema 响应"""
    schema_definition: str
    types: List[SchemaTypeInfo]
    query_type: Optional[str] = None
    mutation_type: Optional[str] = None
    subscription_type: Optional[str] = None
    introspection_enabled: bool


# ============================================================================
# Pydantic Models for Subscription Endpoint
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

        logger.info(
            f"[graphql_router] GraphQL schema requested by user {current_user.username}, "
            f"types count: {len(types_info)}"
        )

        return GraphQLSchemaResponse(
            schema_definition=schema_sdl,
            types=types_info,
            query_type=query_type_name,
            mutation_type=mutation_type_name,
            subscription_type=subscription_type_name,
            introspection_enabled=GRAPHQL_INCLUDE_INTROSPECTION,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[graphql_router] Failed to get GraphQL schema: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve GraphQL schema: {str(e)}",
        )


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
        config_obj = _get_subscription_config()
        
        # 检查订阅功能是否启用
        if not config_obj.enabled:
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
            config=config_obj,
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


# ============================================================================
# GraphQL Query Management Endpoint
# ============================================================================


@router.get(
    "/graphql-query",
    summary="获取GraphQL查询信息",
    description="返回GraphQL查询配置、查询历史和性能统计信息",
    responses={
        200: {
            "description": "成功返回GraphQL查询信息",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "data": {
                            "query_configs": [],
                            "query_history": [],
                            "performance_stats": []
                        },
                        "timestamp": "2026-09-01T09:00:00Z"
                    }
                }
            }
        },
        401: {"description": "未授权"},
        403: {"description": "权限不足"},
        500: {"description": "服务器错误"},
    },
)
async def get_graphql_query_info(
    request: Request,
    db: Session = Depends(get_session),
    limit: int = Query(10, ge=1, le=100, description="返回记录数量限制"),
    config_id: Optional[str] = Query(None, description="查询配置ID过滤"),
    hours: int = Query(24, ge=1, le=168, description="查询历史时间范围（小时）"),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get GraphQL query information including configuration, history, and performance stats.
    
    This endpoint provides comprehensive GraphQL query management information:
    - Query configurations with permission and performance settings
    - Query execution history for auditing
    - Performance statistics for optimization
    
    Args:
        request: FastAPI request object
        db: Database session
        limit: Maximum number of records to return
        config_id: Optional filter by query configuration ID
        hours: Time range in hours for query history (default: 24)
        current_user: Current authenticated user
        
    Returns:
        Dictionary containing query configs, history, and performance stats
        
    Raises:
        HTTPException: If authorization fails or database error occurs
    """
    try:
        # Authorization check - all authenticated users can access
        user_role = getattr(current_user, "role", "viewer")
        user_id = getattr(current_user, "id", None)
        tenant_id = getattr(current_user, "tenant_id", "default")
        
        logger.info(f"User {current_user.username} (role: {user_role}) requesting GraphQL query info")
        
        # Get query configurations
        query_configs = []
        try:
            configs_query = db.query(GraphQLQueryConfig).filter(
                GraphQLQueryConfig.is_active == True
            )
            
            if config_id:
                configs_query = configs_query.filter(GraphQLQueryConfig.id == config_id)
            
            # Apply role-based filtering
            if user_role != "admin":
                # Non-admin users can only see configs that match their role
                configs_query = configs_query.filter(
                    (GraphQLQueryConfig.required_roles == None) |
                    (GraphQLQueryConfig.required_roles.contains([user_role]))
                )
            
            configs = configs_query.limit(limit).all()
            
            for config in configs:
                query_configs.append({
                    "id": config.id,
                    "config_name": config.config_name,
                    "description": config.description,
                    "required_roles": config.required_roles,
                    "required_permissions": config.required_permissions,
                    "max_complexity": config.max_complexity,
                    "max_depth": config.max_depth,
                    "timeout_ms": config.timeout_ms,
                    "cache_enabled": config.cache_enabled,
                    "cache_ttl_seconds": config.cache_ttl_seconds,
                    "created_by": config.created_by,
                    "updated_by": config.updated_by,
                    "created_at": config.created_at.isoformat() if config.created_at else None,
                    "updated_at": config.updated_at.isoformat() if config.updated_at else None,
                })
                
        except Exception as e:
            logger.error(f"Error fetching query configs: {e}")
            query_configs = []
        
        # Get query history
        query_history = []
        try:
            time_threshold = datetime.utcnow() - timedelta(hours=hours)
            
            history_query = db.query(GraphQLQueryHistory).filter(
                GraphQLQueryHistory.created_at >= time_threshold
            )
            
            # Apply tenant filtering
            if tenant_id != "default":
                history_query = history_query.filter(
                    (GraphQLQueryHistory.tenant_id == tenant_id) |
                    (GraphQLQueryHistory.tenant_id == None)
                )
            
            # Apply config filtering if specified
            if config_id:
                history_query = history_query.filter(GraphQLQueryHistory.query_id == config_id)
            
            # Non-admin users can only see their own history
            if user_role != "admin" and user_id:
                history_query = history_query.filter(GraphQLQueryHistory.user_id == user_id)
            
            history = history_query.order_by(
                desc(GraphQLQueryHistory.created_at)
            ).limit(limit).all()
            
            for record in history:
                query_history.append({
                    "id": record.id,
                    "query_id": record.query_id,
                    "operation_name": record.operation_name,
                    "user_id": record.user_id,
                    "username": record.username,
                    "tenant_id": record.tenant_id,
                    "execution_time_ms": record.execution_time_ms,
                    "complexity_score": record.complexity_score,
                    "depth": record.depth,
                    "success": record.success,
                    "error_message": record.error_message,
                    "error_code": record.error_code,
                    "result_size_bytes": record.result_size_bytes,
                    "created_at": record.created_at.isoformat() if record.created_at else None,
                })
                
        except Exception as e:
            logger.error(f"Error fetching query history: {e}")
            query_history = []
        
        # Get performance statistics
        performance_stats = []
        try:
            # Get stats for the recent time window
            time_threshold = datetime.utcnow() - timedelta(hours=hours)
            
            stats_query = db.query(GraphQLPerformanceStats).filter(
                GraphQLPerformanceStats.window_start >= time_threshold
            )
            
            # Apply tenant filtering
            if tenant_id != "default":
                stats_query = stats_query.filter(
                    (GraphQLPerformanceStats.tenant_id == tenant_id) |
                    (GraphQLPerformanceStats.tenant_id == None)
                )
            
            stats = stats_query.order_by(
                desc(GraphQLPerformanceStats.window_start)
            ).limit(limit).all()
            
            for stat in stats:
                performance_stats.append({
                    "id": stat.id,
                    "stat_type": stat.stat_type,
                    "stat_key": stat.stat_key,
                    "tenant_id": stat.tenant_id,
                    "window_start": stat.window_start.isoformat() if stat.window_start else None,
                    "window_end": stat.window_end.isoformat() if stat.window_end else None,
                    "total_executions": stat.total_executions,
                    "successful_executions": stat.successful_executions,
                    "failed_executions": stat.failed_executions,
                    "avg_execution_time_ms": stat.avg_execution_time_ms,
                    "min_execution_time_ms": stat.min_execution_time_ms,
                    "max_execution_time_ms": stat.max_execution_time_ms,
                    "p50_execution_time_ms": stat.p50_execution_time_ms,
                    "p95_execution_time_ms": stat.p95_execution_time_ms,
                    "p99_execution_time_ms": stat.p99_execution_time_ms,
                    "avg_complexity": stat.avg_complexity,
                    "avg_depth": stat.avg_depth,
                    "avg_result_size_bytes": stat.avg_result_size_bytes,
                    "total_result_size_bytes": stat.total_result_size_bytes,
                    "error_rate": stat.error_rate,
                    "common_errors": stat.common_errors,
                    "created_at": stat.created_at.isoformat() if stat.created_at else None,
                    "updated_at": stat.updated_at.isoformat() if stat.updated_at else None,
                })
                
        except Exception as e:
            logger.error(f"Error fetching performance stats: {e}")
            performance_stats = []
        
        return {
            "status": "success",
            "data": {
                "query_configs": query_configs,
                "query_history": query_history,
                "performance_stats": performance_stats,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_graphql_query_info: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# 导出路由器以便在main.py中使用
__all__ = ["router", "subscription_manager"]
