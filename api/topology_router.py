# -*- coding: utf-8 -*-
import logging
import re
import time
from threading import Lock
from typing import Any, Literal, Optional, cast

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, field_validator

from core.topology_engine import (
    TOPOLOGY_TYPES,
    add_edge,
    add_node,
    build_topology,
    create_topology_view,
    delete_edge,
    delete_node,
    delete_topology_view,
    get_all_topology_views,
    get_full_link_topology,
    get_impact_analysis,
    get_node_dependencies,
    get_node_timeline,
    get_topology,
    get_topology_status,
    get_topology_view,
    get_transitive_dependencies,
    insert_edge,
    insert_node,
    insert_topology,
    node_exists,
    query_dependencies,
    query_topology,
    remove_edge,
    remove_node,
    update_node_health,
    update_topology_view,
    validate_topology,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/topologies", tags=["拓扑管理"])
_VALID_NODE_ID_PATTERN = re.compile("^[a-zA-Z0-9._\\-]+$")
_FULL_LINK_CACHE_TTL_SEC = 5
_full_link_cache: dict[str, Any] = {"data": None, "ts": 0.0}
_full_link_cache_lock = Lock()

# 批量操作配置
_BATCH_SIZE_LIMIT = 100
_RATE_LIMIT_DELAY = 0.1  # 秒


class NodeHealthUpdateRequest(BaseModel):
    node_id: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="节点 ID,例如: agent / detect / rca",
        examples=["agent"],
    )
    status: Literal["healthy", "warning", "critical"] = Field(
        ..., description="节点健康状态: healthy | warning | critical", examples=["warning"]
    )

    @field_validator("node_id")
    @classmethod
    def _validate_node_id(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("node_id 不能为纯空白")
        if not _VALID_NODE_ID_PATTERN.match(v):
            raise ValueError(f"node_id 仅允许字母数字和 '._-',收到: {v!r}")
        return v

    model_config = {
        "extra": "ignore",
        "json_schema_extra": {"example": {"node_id": "example", "status": None}},
    }


# ============================================================
# Pydantic Models for New Endpoints
# ============================================================


class TopologyCreateRequest(BaseModel):
    """创建拓扑的请求模型"""

    nodes: list[dict[str, Any]] = Field(
        ..., min_length=1, description="节点列表", examples=[[{"id": "node-1", "name": "Service A"}]]
    )
    edges: list[dict[str, Any]] = Field(
        default_factory=list, description="边列表", examples=[[{"source": "node-1", "target": "node-2"}]]
    )
    name: Optional[str] = Field(None, max_length=100, description="拓扑名称")
    description: Optional[str] = Field(None, max_length=500, description="拓扑描述")

    @field_validator("nodes")
    @classmethod
    def _validate_nodes(cls, v: list[dict[str, Any]]) -> list[dict[str, Any]]:
        for node in v:
            if not isinstance(node, dict) or not node.get("id"):
                raise ValueError("每个节点必须包含 id 字段")
        return v

    model_config = {
        "extra": "ignore",
        "json_schema_extra": {
            "example": {
                "nodes": [{"id": "node-1", "name": "Service A"}],
                "edges": [{"source": "node-1", "target": "node-2"}],
                "name": "My Topology",
            }
        },
    }


class TopologyUpdateRequest(BaseModel):
    """更新拓扑的请求模型"""

    nodes: Optional[list[dict[str, Any]]] = None
    edges: Optional[list[dict[str, Any]]] = None
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = Field(None, max_length=500)

    model_config = {"extra": "ignore"}


class NodeCreateRequest(BaseModel):
    """创建节点的请求模型"""

    id: str = Field(..., min_length=1, max_length=64, description="节点ID")
    name: str = Field(..., min_length=1, max_length=100, description="节点名称")
    type: str = Field(default="service", description="节点类型")
    status: str = Field(default="healthy", description="节点状态")
    metadata: dict[str, Any] = Field(default_factory=dict, description="节点元数据")

    @field_validator("id")
    @classmethod
    def _validate_node_id(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("id 不能为纯空白")
        if not _VALID_NODE_ID_PATTERN.match(v):
            raise ValueError(f"id 仅允许字母数字和 '._-',收到: {v!r}")
        return v

    model_config = {
        "extra": "ignore",
        "json_schema_extra": {"example": {"id": "node-1", "name": "Service A", "type": "service"}},
    }


class NodeUpdateRequest(BaseModel):
    """更新节点的请求模型"""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    type: Optional[str] = None
    status: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None

    model_config = {"extra": "ignore"}


class EdgeCreateRequest(BaseModel):
    """创建边的请求模型"""

    id: Optional[str] = Field(None, max_length=64, description="边ID（可选，自动生成）")
    source: str = Field(..., min_length=1, max_length=64, description="源节点ID")
    target: str = Field(..., min_length=1, max_length=64, description="目标节点ID")
    type: str = Field(default="sync", description="边类型")
    weight: float = Field(default=1.0, ge=0, description="边权重")
    metadata: dict[str, Any] = Field(default_factory=dict, description="边元数据")

    @field_validator("source", "target")
    @classmethod
    def _validate_node_id(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("节点ID 不能为纯空白")
        if not _VALID_NODE_ID_PATTERN.match(v):
            raise ValueError(f"节点ID 仅允许字母数字和 '._-',收到: {v!r}")
        return v

    model_config = {
        "extra": "ignore",
        "json_schema_extra": {"example": {"source": "node-1", "target": "node-2", "type": "sync"}},
    }


class BatchNodeCreateRequest(BaseModel):
    """批量创建节点的请求模型"""

    nodes: list[NodeCreateRequest] = Field(..., min_length=1, max_length=_BATCH_SIZE_LIMIT)

    @field_validator("nodes")
    @classmethod
    def _validate_batch_size(cls, v: list[NodeCreateRequest]) -> list[NodeCreateRequest]:
        if len(v) > _BATCH_SIZE_LIMIT:
            raise ValueError(f"批量操作最多支持 {_BATCH_SIZE_LIMIT} 个节点")
        return v

    model_config = {"extra": "ignore"}


class BatchEdgeCreateRequest(BaseModel):
    """批量创建边的请求模型"""

    edges: list[EdgeCreateRequest] = Field(..., min_length=1, max_length=_BATCH_SIZE_LIMIT)

    @field_validator("edges")
    @classmethod
    def _validate_batch_size(cls, v: list[EdgeCreateRequest]) -> list[EdgeCreateRequest]:
        if len(v) > _BATCH_SIZE_LIMIT:
            raise ValueError(f"批量操作最多支持 {_BATCH_SIZE_LIMIT} 条边")
        return v

    model_config = {"extra": "ignore"}


class BatchDeleteRequest(BaseModel):
    """批量删除请求模型"""

    ids: list[str] = Field(..., min_length=1, max_length=_BATCH_SIZE_LIMIT)

    @field_validator("ids")
    @classmethod
    def _validate_batch_size(cls, v: list[str]) -> list[str]:
        if len(v) > _BATCH_SIZE_LIMIT:
            raise ValueError(f"批量操作最多支持 {_BATCH_SIZE_LIMIT} 个ID")
        return v

    model_config = {"extra": "ignore"}


class TopologyViewCreateRequest(BaseModel):
    """创建拓扑视图的请求模型"""

    name: str = Field(..., min_length=1, max_length=100, description="视图名称")
    description: str = Field(default="", max_length=500, description="视图描述")
    view_type: str = Field(..., min_length=1, max_length=50, description="视图类型")
    config: dict[str, Any] = Field(default_factory=dict, description="视图配置")
    created_by: str = Field(default="system", max_length=50, description="创建者")

    @field_validator("view_type")
    @classmethod
    def _validate_view_type(cls, v: str) -> str:
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
                "config": {"filters": {"environment": "production"}},
            }
        },
    }


class TopologyViewUpdateRequest(BaseModel):
    """更新拓扑视图的请求模型"""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    view_type: Optional[str] = Field(None, min_length=1, max_length=50)
    config: Optional[dict[str, Any]] = None
    updated_by: str = Field(default="system", max_length=50)

    @field_validator("view_type")
    @classmethod
    def _validate_view_type(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip().lower()
            valid_types = {"service", "network", "application", "infrastructure", "custom"}
            if v not in valid_types:
                raise ValueError(f"view_type 必须是以下之一: {', '.join(valid_types)}")
        return v

    model_config = {"extra": "ignore"}


def _validate_path_node_id(node_id: str) -> str:
    """
    路径参数 node_id 字符校验
    🔧 TR2:防御路径遍历攻击(如 ../etc/passwd)
    🔧 TR4:严格白名单
    """
    if not node_id or not isinstance(node_id, str):
        raise HTTPException(status_code=422, detail="node_id 不能为空")
    cleaned = node_id.strip()
    if not cleaned:
        raise HTTPException(status_code=422, detail="node_id 不能为纯空白")
    if not _VALID_NODE_ID_PATTERN.match(cleaned):
        raise HTTPException(status_code=422, detail="node_id 仅允许字母数字和 '._-'")
    if len(cleaned) > 64:
        raise HTTPException(status_code=422, detail="node_id 长度超出 64 字符")
    return cleaned


@router.get(
    "/types",
    summary="获取所有拓扑类型列表",
    responses={(200): {"description": "拓扑类型列表"}, (500): {"description": "获取失败"}},
)
async def list_topology_types() -> dict[str, Any]:
    """返回所有可用的拓扑类型,供前端拓扑选择器初始化"""
    logger.info("请求拓扑类型列表")
    try:
        types = [{"key": k, "name": v} for k, v in TOPOLOGY_TYPES.items()]
        logger.debug(f"拓扑类型列表返回成功,共 {len(types)} 种")
        return {"types": types}
    except Exception as e:
        logger.error(f"拓扑类型列表获取失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"拓扑类型列表获取失败: {str(e)[:200]}")


@router.get(
    "/status/{topo_key}",
    summary="获取指定拓扑运行状态",
    responses={
        (200): {"description": "拓扑运行状态"},
        (404): {"description": "拓扑未找到"},
        (422): {"description": "参数错误"},
        (500): {"description": "获取失败"},
    },
)
async def get_topo_status(topo_key: str) -> dict[str, Any]:
    """
    返回指定拓扑的实时运行状态、节点健康度、活跃数据流
    对应前端:点击"激活数据流"后拉取节点状态并上色

    🔧 TR4:topo_key 字符校验
    """
    cleaned_key = topo_key.strip() if isinstance(topo_key, str) else ""
    if not cleaned_key or not _VALID_NODE_ID_PATTERN.match(cleaned_key):
        raise HTTPException(status_code=422, detail="topo_key 仅允许字母数字和 '._-'")
    logger.info(f"请求拓扑运行状态,topo_key='{cleaned_key}'")
    try:
        result = get_topology_status(cleaned_key)
        if "error" in result:
            logger.warning(f"拓扑状态查询失败,未知 topo_key='{cleaned_key}'")
            raise HTTPException(status_code=404, detail=result["error"])
        logger.debug(
            f"拓扑状态查询成功 | topo='{cleaned_key}' | 节点数={result.get('node_count', 'N/A')} |"
            f" 活跃流={len(result.get('active_flows', []))}"
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"拓扑状态查询内部错误,topo_key='{cleaned_key}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"拓扑状态查询失败: {str(e)[:200]}")


@router.post(
    "/node/health",
    summary="更新拓扑节点健康状态",
    responses={
        (200): {"description": "更新结果"},
        (422): {"description": "参数错误"},
        (500): {"description": "更新失败"},
    },
)
async def set_node_health(payload: NodeHealthUpdateRequest) -> dict[str, Any]:
    """
    手动或由告警引擎调用,更新指定节点的健康状态

    请求体:
    {
        "node_id": "agent",
        "status":  "warning"
    }

    status 合法值: healthy | warning | critical
    (非法值由 Pydantic Literal 自动拦截,返回 422)

    ✅ 修复6:ValueError → 400(客户端传入非法 node_id)
              其他异常 → 500
    🔧 TR1:Pydantic 字段验证已严格校验 node_id
    """
    logger.warning(f"节点健康状态变更 | node_id='{payload.node_id}' | 新状态='{payload.status}'")
    try:
        update_node_health(payload.node_id, payload.status)
        logger.info(f"节点状态更新成功 | node_id='{payload.node_id}' | status='{payload.status}'")
        with _full_link_cache_lock:
            _full_link_cache["data"] = None
            _full_link_cache["ts"] = 0.0
        return {"status": "ok", "node_id": payload.node_id, "health": payload.status}
    except ValueError as ve:
        logger.warning(f"节点状态更新被拒绝(非法参数)| node_id='{payload.node_id}' | 原因: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"节点状态更新失败 | node_id='{payload.node_id}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"节点状态更新失败: {str(e)[:200]}")


@router.get(
    "/full-link",
    summary="获取全链路拓扑(M-3 阶段3,5秒TTL)",
    responses={(200): {"description": "全链路拓扑数据"}, (500): {"description": "生成失败"}},
)
async def get_full_link() -> dict[str, Any]:
    """
    返回基于 .env LINUX_HOSTS 配置生成的全链路拓扑数据
    包含:节点列表、依赖边、统计摘要、更新时间
    供前端"🌐 全链路拓扑"视图渲染

    🔧 TR5 [P2]:5 秒 TTL 缓存
        - 减少 collector._last_collect_cache 高频读取
        - 减少 _apply_causal_propagation BFS 重复计算
    """
    now = time.monotonic()
    with _full_link_cache_lock:
        if (
            _full_link_cache["data"] is not None
            and now - _full_link_cache["ts"] < _FULL_LINK_CACHE_TTL_SEC
        ):
            logger.debug("全链路拓扑命中缓存")
            return cast(dict[str, Any], _full_link_cache["data"])
    logger.info("请求全链路拓扑数据(缓存未命中)")
    try:
        result = await get_full_link_topology()
        with _full_link_cache_lock:
            _full_link_cache["data"] = dict(result)
            _full_link_cache["ts"] = time.monotonic()
        logger.debug(
            f"全链路拓扑生成成功 | 节点={len(result.get('nodes', []))} |"
            f" 边={len(result.get('edges', []))} | stats={result.get('stats', {})}"
        )
        return result
    except Exception as e:
        logger.error(f"全链路拓扑生成失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"全链路拓扑生成失败: {str(e)[:200]}")


@router.get(
    "/node/{node_id}/timeline",
    summary="获取节点最近 N 小时的事件时间线(M-3 阶段5)",
    responses={
        (200): {"description": "节点事件时间线"},
        (422): {"description": "参数错误"},
        (500): {"description": "获取失败"},
    },
)
async def get_node_timeline_api(
    node_id: str,
    hours: int = Query(default=24, ge=1, le=168),
    limit: int = Query(default=50, ge=1, le=200),
) -> dict[str, Any]:
    """
    返回指定节点最近 N 小时的告警/修复事件时间线
    供前端"节点时间线浮窗"展示

    🔧 TR2 [P1]:path 参数严格字符校验,防御路径遍历

    Args:
        node_id: 节点 ID(主机名或 'internet')
        hours:   查询时间窗口(1-168 小时,默认 24)
        limit:   最多返回事件数(1-200,默认 50)
    """
    cleaned_node_id = _validate_path_node_id(node_id)
    logger.info(f"请求节点时间线 | node_id={cleaned_node_id} | hours={hours} | limit={limit}")
    try:
        result = get_node_timeline(cleaned_node_id)
        logger.debug(
            f"节点时间线生成成功 | node={cleaned_node_id} |"
            f" 事件数={result.get('summary', {}).get('total', 0)}"
        )
        return result
    except Exception as e:
        logger.error(f"节点时间线查询失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"节点时间线查询失败: {str(e)[:200]}")


@router.post("/cache/clear", summary="清空全链路拓扑缓存(维护用)", include_in_schema=False)
async def clear_topology_cache() -> dict[str, Any]:
    """
    清空全链路拓扑的内存缓存
    供测试或紧急维护使用,生产环境无需调用
    """
    cleared = _full_link_cache["data"] is not None
    with _full_link_cache_lock:
        _full_link_cache["data"] = None
        _full_link_cache["ts"] = 0.0
    logger.warning(f"⚠️ 全链路拓扑缓存已被清空 | cleared={'是' if cleared else '原本为空'}")
    return {"status": "ok", "cleared": cleared}


# ============================================================
# Topology CRUD Endpoints (7 new endpoints)
# ============================================================


@router.get(
    "",
    summary="获取所有拓扑列表",
    responses={
        (200): {"description": "拓扑列表"},
        (500): {"description": "获取失败"},
    },
)
async def list_topologies(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    """
    获取所有拓扑列表

    Args:
        limit: 返回数量限制
        offset: 偏移量

    Returns:
        拓扑列表
    """
    logger.info(f"获取拓扑列表 | limit={limit} | offset={offset}")
    try:
        from core.topology_engine import _topology_cache

        topologies = list(_topology_cache.values())
        total = len(topologies)

        # 应用分页
        paginated = topologies[offset : offset + limit]

        logger.debug(f"拓扑列表获取成功 | 总数={total} | 返回={len(paginated)}")
        return {"topologies": paginated, "total": total, "limit": limit, "offset": offset}
    except Exception as e:
        logger.error(f"获取拓扑列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取拓扑列表失败: {str(e)[:200]}")


@router.post(
    "",
    summary="创建拓扑",
    responses={
        (200): {"description": "创建成功"},
        (400): {"description": "参数错误"},
        (500): {"description": "创建失败"},
    },
)
async def create_topology(payload: TopologyCreateRequest) -> dict[str, Any]:
    """
    创建新的拓扑

    Args:
        payload: 包含节点、边和拓扑信息的请求体

    Returns:
        创建的拓扑数据，包含拓扑ID
    """
    logger.info(f"创建拓扑 | 节点数={len(payload.nodes)} | 边数={len(payload.edges)}")
    try:
        result = await build_topology(payload.nodes, payload.edges)
        if not result.get("success"):
            logger.warning(f"拓扑创建失败: {result.get('error')}")
            raise HTTPException(status_code=400, detail=result.get("error"))

        topology_id = result.get("topology_id")
        logger.info(f"拓扑创建成功 | topology_id={topology_id}")
        return {"topology_id": topology_id, "nodes": payload.nodes, "edges": payload.edges}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"拓扑创建失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"拓扑创建失败: {str(e)[:200]}")


@router.get(
    "/{topology_id}",
    summary="获取拓扑详情",
    responses={
        (200): {"description": "拓扑详情"},
        (404): {"description": "拓扑未找到"},
        (422): {"description": "参数错误"},
        (500): {"description": "获取失败"},
    },
)
async def get_topology_by_id(topology_id: str) -> dict[str, Any]:
    """
    根据ID获取拓扑详情

    Args:
        topology_id: 拓扑ID

    Returns:
        拓扑详情数据
    """
    cleaned_id = _validate_path_node_id(topology_id)
    logger.info(f"获取拓扑详情 | topology_id={cleaned_id}")
    try:
        result = await get_topology(cleaned_id)
        if not result.get("success"):
            logger.warning(f"拓扑未找到 | topology_id={cleaned_id}")
            raise HTTPException(status_code=404, detail=result.get("error"))

        logger.debug(f"拓扑详情获取成功 | topology_id={cleaned_id}")
        return result.get("topology", {})
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取拓扑详情失败 | topology_id={cleaned_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取拓扑详情失败: {str(e)[:200]}")


# ============================================================
# Topology View Endpoints (5 new endpoints)
# ============================================================


@router.post(
    "/views",
    summary="创建拓扑视图",
    responses={
        (200): {"description": "创建成功"},
        (400): {"description": "参数错误"},
        (500): {"description": "创建失败"},
    },
)
async def create_topology_view_endpoint(payload: TopologyViewCreateRequest) -> dict[str, Any]:
    """
    创建新的拓扑视图

    Args:
        payload: 视图数据

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


@router.get(
    "/views",
    summary="获取所有拓扑视图",
    responses={
        (200): {"description": "视图列表"},
        (500): {"description": "获取失败"},
    },
)
async def list_topology_views_endpoint(
    view_type: Optional[str] = Query(None, description="按视图类型过滤"),
) -> dict[str, Any]:
    """
    获取所有拓扑视图

    Args:
        view_type: 视图类型过滤

    Returns:
        视图列表
    """
    logger.info(f"获取拓扑视图列表 | view_type={view_type}")
    try:
        views = await get_all_topology_views(view_type=view_type)
        logger.debug(f"拓扑视图列表获取成功 | 总数={len(views)}")
        return {"views": views, "count": len(views)}
    except Exception as e:
        logger.error(f"获取拓扑视图列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取拓扑视图列表失败: {str(e)[:200]}")


@router.get(
    "/views/{view_id}",
    summary="获取拓扑视图详情",
    responses={
        (200): {"description": "视图详情"},
        (404): {"description": "视图未找到"},
        (422): {"description": "参数错误"},
        (500): {"description": "获取失败"},
    },
)
async def get_topology_view_by_id_endpoint(view_id: str) -> dict[str, Any]:
    """
    获取拓扑视图详情

    Args:
        view_id: 视图ID

    Returns:
        视图详情
    """
    cleaned_id = _validate_path_node_id(view_id)
    logger.info(f"获取拓扑视图详情 | view_id={cleaned_id}")
    try:
        view = await get_topology_view(cleaned_id)
        if view is None:
            logger.warning(f"拓扑视图未找到 | view_id={cleaned_id}")
            raise HTTPException(status_code=404, detail="拓扑视图未找到")

        logger.debug(f"拓扑视图详情获取成功 | view_id={cleaned_id}")
        return view
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取拓扑视图详情失败 | view_id={cleaned_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取拓扑视图详情失败: {str(e)[:200]}")


@router.put(
    "/views/{view_id}",
    summary="更新拓扑视图",
    responses={
        (200): {"description": "更新成功"},
        (404): {"description": "视图未找到"},
        (422): {"description": "参数错误"},
        (500): {"description": "更新失败"},
    },
)
async def update_topology_view_endpoint(view_id: str, payload: TopologyViewUpdateRequest) -> dict[str, Any]:
    """
    更新拓扑视图

    Args:
        view_id: 视图ID
        payload: 更新数据

    Returns:
        更新后的视图数据
    """
    cleaned_id = _validate_path_node_id(view_id)
    logger.info(f"更新拓扑视图 | view_id={cleaned_id}")
    try:
        view = await update_topology_view(
            view_id=cleaned_id,
            name=payload.name,
            description=payload.description,
            view_type=payload.view_type,
            config=payload.config,
            updated_by=payload.updated_by,
        )
        if view is None:
            logger.warning(f"拓扑视图未找到 | view_id={cleaned_id}")
            raise HTTPException(status_code=404, detail="拓扑视图未找到")

        logger.info(f"拓扑视图更新成功 | view_id={cleaned_id}")
        return view
    except HTTPException:
        raise
    except ValueError as ve:
        logger.warning(f"拓扑视图更新失败(参数错误): {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"更新拓扑视图失败 | view_id={cleaned_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"更新拓扑视图失败: {str(e)[:200]}")


@router.delete(
    "/views/{view_id}",
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
    cleaned_id = _validate_path_node_id(view_id)
    logger.info(f"删除拓扑视图 | view_id={cleaned_id}")
    try:
        success = await delete_topology_view(cleaned_id)
        if not success:
            logger.warning(f"拓扑视图未找到 | view_id={cleaned_id}")
            raise HTTPException(status_code=404, detail="拓扑视图未找到")

        logger.info(f"拓扑视图删除成功 | view_id={cleaned_id}")
        return {"status": "ok", "message": f"拓扑视图 {cleaned_id} 已删除"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除拓扑视图失败 | view_id={cleaned_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"删除拓扑视图失败: {str(e)[:200]}")


@router.put(
    "/{topology_id}",
    summary="更新拓扑",
    responses={
        (200): {"description": "更新成功"},
        (404): {"description": "拓扑未找到"},
        (422): {"description": "参数错误"},
        (500): {"description": "更新失败"},
    },
)
async def update_topology(topology_id: str, payload: TopologyUpdateRequest) -> dict[str, Any]:
    """
    更新现有拓扑

    Args:
        topology_id: 拓扑ID
        payload: 更新数据

    Returns:
        更新后的拓扑数据
    """
    cleaned_id = _validate_path_node_id(topology_id)
    logger.info(f"更新拓扑 | topology_id={cleaned_id}")
    try:
        from core.topology_engine import _topology_cache

        if cleaned_id not in _topology_cache:
            logger.warning(f"拓扑未找到 | topology_id={cleaned_id}")
            raise HTTPException(status_code=404, detail="拓扑未找到")

        topology = _topology_cache[cleaned_id]

        # 更新字段
        if payload.nodes is not None:
            topology["nodes"] = payload.nodes
        if payload.edges is not None:
            topology["edges"] = payload.edges
        if payload.name is not None:
            topology["name"] = payload.name
        if payload.description is not None:
            topology["description"] = payload.description

        logger.info(f"拓扑更新成功 | topology_id={cleaned_id}")
        return topology
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新拓扑失败 | topology_id={cleaned_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"更新拓扑失败: {str(e)[:200]}")


@router.delete(
    "/{topology_id}",
    summary="删除拓扑",
    responses={
        (200): {"description": "删除成功"},
        (404): {"description": "拓扑未找到"},
        (422): {"description": "参数错误"},
        (500): {"description": "删除失败"},
    },
)
async def delete_topology(topology_id: str) -> dict[str, Any]:
    """
    删除拓扑

    Args:
        topology_id: 拓扑ID

    Returns:
        删除结果
    """
    cleaned_id = _validate_path_node_id(topology_id)
    logger.info(f"删除拓扑 | topology_id={cleaned_id}")
    try:
        from core.topology_engine import _topology_cache

        if cleaned_id not in _topology_cache:
            logger.warning(f"拓扑未找到 | topology_id={cleaned_id}")
            raise HTTPException(status_code=404, detail="拓扑未找到")

        del _topology_cache[cleaned_id]
        logger.info(f"拓扑删除成功 | topology_id={cleaned_id}")
        return {"status": "ok", "message": f"拓扑 {cleaned_id} 已删除"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除拓扑失败 | topology_id={cleaned_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"删除拓扑失败: {str(e)[:200]}")


@router.post(
    "/validate",
    summary="验证拓扑",
    responses={
        (200): {"description": "验证结果"},
        (400): {"description": "参数错误"},
        (500): {"description": "验证失败"},
    },
)
async def validate_topology_endpoint(payload: dict[str, Any]) -> dict[str, Any]:
    """
    验证拓扑的有效性

    Args:
        payload: 包含nodes和edges的拓扑数据

    Returns:
        验证结果，包含valid状态和warnings
    """
    logger.info("验证拓扑")
    try:
        result = validate_topology(payload)
        logger.debug(f"拓扑验证完成 | valid={result.get('valid')} | warnings={len(result.get('warnings', []))}")
        return result
    except Exception as e:
        logger.error(f"拓扑验证失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"拓扑验证失败: {str(e)[:200]}")


@router.get(
    "/{topology_id}/export",
    summary="导出拓扑",
    responses={
        (200): {"description": "导出成功"},
        (404): {"description": "拓扑未找到"},
        (422): {"description": "参数错误"},
        (500): {"description": "导出失败"},
    },
)
async def export_topology(topology_id: str, format: str = Query(default="json")) -> dict[str, Any]:
    """
    导出拓扑数据

    Args:
        topology_id: 拓扑ID
        format: 导出格式 (json, yaml)

    Returns:
        导出的拓扑数据
    """
    cleaned_id = _validate_path_node_id(topology_id)
    logger.info(f"导出拓扑 | topology_id={cleaned_id} | format={format}")
    try:
        result = await get_topology(cleaned_id)
        if not result.get("success"):
            logger.warning(f"拓扑未找到 | topology_id={cleaned_id}")
            raise HTTPException(status_code=404, detail="拓扑未找到")

        topology = result.get("topology", {})

        if format == "yaml":
            import yaml

            yaml_data = yaml.dump(topology, default_flow_style=False)
            return {"format": "yaml", "data": yaml_data}

        return {"format": "json", "data": topology}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"导出拓扑失败 | topology_id={cleaned_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"导出拓扑失败: {str(e)[:200]}")


# ============================================================
# Node Management Endpoints (6 new endpoints)
# ============================================================


@router.post(
    "/nodes",
    summary="添加节点",
    responses={
        (200): {"description": "添加成功"},
        (400): {"description": "参数错误"},
        (409): {"description": "节点已存在"},
        (500): {"description": "添加失败"},
    },
)
async def create_node_endpoint(payload: NodeCreateRequest) -> dict[str, Any]:
    """
    添加新节点到拓扑

    Args:
        payload: 节点数据

    Returns:
        添加结果
    """
    logger.info(f"添加节点 | node_id={payload.id}")
    try:
        node_data = payload.model_dump()
        result = await add_node(node_data)
        if not result.get("success"):
            logger.warning(f"节点添加失败: {result.get('error')}")
            if "duplicate" in result.get("error", "").lower():
                raise HTTPException(status_code=409, detail=result.get("error"))
            raise HTTPException(status_code=400, detail=result.get("error"))

        logger.info(f"节点添加成功 | node_id={payload.id}")
        return {"status": "ok", "node_id": payload.id, "node": node_data}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"添加节点失败 | node_id={payload.id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"添加节点失败: {str(e)[:200]}")


@router.get(
    "/nodes",
    summary="获取所有节点",
    responses={
        (200): {"description": "节点列表"},
        (500): {"description": "获取失败"},
    },
)
async def list_nodes(
    type: Optional[str] = Query(None, description="按类型过滤"),
    status: Optional[str] = Query(None, description="按状态过滤"),
) -> dict[str, Any]:
    """
    获取所有节点列表

    Args:
        type: 节点类型过滤
        status: 节点状态过滤

    Returns:
        节点列表
    """
    logger.info(f"获取节点列表 | type={type} | status={status}")
    try:
        from core.topology_engine import _nodes

        nodes = list(_nodes.values())

        # 应用过滤
        if type:
            nodes = [n for n in nodes if n.get("type") == type]
        if status:
            nodes = [n for n in nodes if n.get("status") == status]

        logger.debug(f"节点列表获取成功 | 总数={len(nodes)}")
        return {"nodes": nodes, "total": len(nodes)}
    except Exception as e:
        logger.error(f"获取节点列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取节点列表失败: {str(e)[:200]}")


@router.get(
    "/nodes/{node_id}",
    summary="获取节点详情",
    responses={
        (200): {"description": "节点详情"},
        (404): {"description": "节点未找到"},
        (422): {"description": "参数错误"},
        (500): {"description": "获取失败"},
    },
)
async def get_node_by_id(node_id: str) -> dict[str, Any]:
    """
    获取节点详情

    Args:
        node_id: 节点ID

    Returns:
        节点详情
    """
    cleaned_id = _validate_path_node_id(node_id)
    logger.info(f"获取节点详情 | node_id={cleaned_id}")
    try:
        from core.topology_engine import _nodes

        if cleaned_id not in _nodes:
            logger.warning(f"节点未找到 | node_id={cleaned_id}")
            raise HTTPException(status_code=404, detail="节点未找到")

        logger.debug(f"节点详情获取成功 | node_id={cleaned_id}")
        return _nodes[cleaned_id]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取节点详情失败 | node_id={cleaned_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取节点详情失败: {str(e)[:200]}")


@router.put(
    "/nodes/{node_id}",
    summary="更新节点",
    responses={
        (200): {"description": "更新成功"},
        (404): {"description": "节点未找到"},
        (422): {"description": "参数错误"},
        (500): {"description": "更新失败"},
    },
)
async def update_node_endpoint(node_id: str, payload: NodeUpdateRequest) -> dict[str, Any]:
    """
    更新节点信息

    Args:
        node_id: 节点ID
        payload: 更新数据

    Returns:
        更新后的节点数据
    """
    cleaned_id = _validate_path_node_id(node_id)
    logger.info(f"更新节点 | node_id={cleaned_id}")
    try:
        from core.topology_engine import _nodes

        if cleaned_id not in _nodes:
            logger.warning(f"节点未找到 | node_id={cleaned_id}")
            raise HTTPException(status_code=404, detail="节点未找到")

        node = _nodes[cleaned_id]
        update_data = payload.model_dump(exclude_unset=True)

        for key, value in update_data.items():
            node[key] = value

        # 同步健康状态到核心引擎
        if "status" in update_data:
            try:
                update_node_health(cleaned_id, node["status"])
            except Exception as e:
                logger.warning(f"同步节点健康状态失败: {e}")

        logger.info(f"节点更新成功 | node_id={cleaned_id}")
        return node
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新节点失败 | node_id={cleaned_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"更新节点失败: {str(e)[:200]}")


@router.delete(
    "/nodes/{node_id}",
    summary="删除节点",
    responses={
        (200): {"description": "删除成功"},
        (404): {"description": "节点未找到"},
        (422): {"description": "参数错误"},
        (500): {"description": "删除失败"},
    },
)
async def delete_node_endpoint(node_id: str) -> dict[str, Any]:
    """
    删除节点

    Args:
        node_id: 节点ID

    Returns:
        删除结果
    """
    cleaned_id = _validate_path_node_id(node_id)
    logger.info(f"删除节点 | node_id={cleaned_id}")
    try:
        result = await remove_node(cleaned_id)
        if not result.get("success"):
            logger.warning(f"节点删除失败: {result.get('error')}")
            # Return 404 if node has dependencies or not found
            if "not found" in result.get("error", "").lower() or "dependencies" in result.get("error", "").lower():
                raise HTTPException(status_code=404, detail=result.get("error"))
            raise HTTPException(status_code=400, detail=result.get("error"))

        logger.info(f"节点删除成功 | node_id={cleaned_id}")
        return {"status": "ok", "message": f"节点 {cleaned_id} 已删除"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除节点失败 | node_id={cleaned_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"删除节点失败: {str(e)[:200]}")


@router.get(
    "/nodes/{node_id}/exists",
    summary="检查节点是否存在",
    responses={
        (200): {"description": "检查结果"},
        (422): {"description": "参数错误"},
        (500): {"description": "检查失败"},
    },
)
async def check_node_exists(node_id: str) -> dict[str, Any]:
    """
    检查节点是否存在

    Args:
        node_id: 节点ID

    Returns:
        检查结果
    """
    cleaned_id = _validate_path_node_id(node_id)
    logger.info(f"检查节点是否存在 | node_id={cleaned_id}")
    try:
        exists = await node_exists(cleaned_id)
        logger.debug(f"节点存在性检查完成 | node_id={cleaned_id} | exists={exists}")
        return {"node_id": cleaned_id, "exists": exists}
    except Exception as e:
        logger.error(f"检查节点存在性失败 | node_id={cleaned_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"检查节点存在性失败: {str(e)[:200]}")


# ============================================================
# Edge Management Endpoints (5 new endpoints)
# ============================================================


@router.post(
    "/edges",
    summary="添加边",
    responses={
        (200): {"description": "添加成功"},
        (400): {"description": "参数错误"},
        (409): {"description": "边已存在"},
        (500): {"description": "添加失败"},
    },
)
async def create_edge_endpoint(payload: EdgeCreateRequest) -> dict[str, Any]:
    """
    添加新边到拓扑

    Args:
        payload: 边数据

    Returns:
        添加结果
    """
    logger.info(f"添加边 | source={payload.source} | target={payload.target}")
    try:
        edge_data = payload.model_dump()

        # 生成边ID（如果未提供）
        if not edge_data.get("id"):
            edge_data["id"] = f"{payload.source}__{payload.target}"

        result = await add_edge(edge_data)
        if not result.get("success"):
            logger.warning(f"边添加失败: {result.get('error')}")
            if "duplicate" in result.get("error", "").lower():
                raise HTTPException(status_code=409, detail=result.get("error"))
            raise HTTPException(status_code=400, detail=result.get("error"))

        logger.info(f"边添加成功 | edge_id={edge_data['id']}")
        return {"status": "ok", "edge_id": edge_data["id"], "edge": edge_data}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"添加边失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"添加边失败: {str(e)[:200]}")


@router.get(
    "/edges",
    summary="获取所有边",
    responses={
        (200): {"description": "边列表"},
        (500): {"description": "获取失败"},
    },
)
async def list_edges(
    source: Optional[str] = Query(None, description="按源节点过滤"),
    target: Optional[str] = Query(None, description="按目标节点过滤"),
    type: Optional[str] = Query(None, description="按类型过滤"),
) -> dict[str, Any]:
    """
    获取所有边列表

    Args:
        source: 源节点过滤
        target: 目标节点过滤
        type: 边类型过滤

    Returns:
        边列表
    """
    logger.info(f"获取边列表 | source={source} | target={target} | type={type}")
    try:
        from core.topology_engine import _edges

        edges = list(_edges)

        # 应用过滤
        if source:
            edges = [e for e in edges if e.get("source") == source]
        if target:
            edges = [e for e in edges if e.get("target") == target]
        if type:
            edges = [e for e in edges if e.get("type") == type]

        logger.debug(f"边列表获取成功 | 总数={len(edges)}")
        return {"edges": edges, "total": len(edges)}
    except Exception as e:
        logger.error(f"获取边列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取边列表失败: {str(e)[:200]}")


@router.get(
    "/edges/{edge_id}",
    summary="获取边详情",
    responses={
        (200): {"description": "边详情"},
        (404): {"description": "边未找到"},
        (422): {"description": "参数错误"},
        (500): {"description": "获取失败"},
    },
)
async def get_edge_by_id(edge_id: str) -> dict[str, Any]:
    """
    获取边详情

    Args:
        edge_id: 边ID

    Returns:
        边详情
    """
    cleaned_id = _validate_path_node_id(edge_id)
    logger.info(f"获取边详情 | edge_id={cleaned_id}")
    try:
        from core.topology_engine import _edges

        # 查找边
        edge = None
        for e in _edges:
            if e.get("id") == cleaned_id:
                edge = e
                break

        if not edge:
            logger.warning(f"边未找到 | edge_id={cleaned_id}")
            raise HTTPException(status_code=404, detail="边未找到")

        logger.debug(f"边详情获取成功 | edge_id={cleaned_id}")
        return edge
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取边详情失败 | edge_id={cleaned_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取边详情失败: {str(e)[:200]}")


@router.delete(
    "/edges/{edge_id}",
    summary="删除边",
    responses={
        (200): {"description": "删除成功"},
        (404): {"description": "边未找到"},
        (422): {"description": "参数错误"},
        (500): {"description": "删除失败"},
    },
)
async def delete_edge_endpoint(edge_id: str) -> dict[str, Any]:
    """
    删除边

    Args:
        edge_id: 边ID

    Returns:
        删除结果
    """
    cleaned_id = _validate_path_node_id(edge_id)
    logger.info(f"删除边 | edge_id={cleaned_id}")
    try:
        result = await remove_edge(cleaned_id)
        if not result.get("success"):
            logger.warning(f"边删除失败: {result.get('error')}")
            # Return 404 if edge not found
            if "not found" in result.get("error", "").lower():
                raise HTTPException(status_code=404, detail=result.get("error"))
            raise HTTPException(status_code=400, detail=result.get("error"))

        logger.info(f"边删除成功 | edge_id={cleaned_id}")
        return {"status": "ok", "message": f"边 {cleaned_id} 已删除"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除边失败 | edge_id={cleaned_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"删除边失败: {str(e)[:200]}")


@router.get(
    "/edges/{edge_id}/exists",
    summary="检查边是否存在",
    responses={
        (200): {"description": "检查结果"},
        (422): {"description": "参数错误"},
        (500): {"description": "检查失败"},
    },
)
async def check_edge_exists(edge_id: str) -> dict[str, Any]:
    """
    检查边是否存在

    Args:
        edge_id: 边ID

    Returns:
        检查结果
    """
    cleaned_id = _validate_path_node_id(edge_id)
    logger.info(f"检查边是否存在 | edge_id={cleaned_id}")
    try:
        from core.topology_engine import _edges

        exists = any(e.get("id") == cleaned_id for e in _edges)
        logger.debug(f"边存在性检查完成 | edge_id={cleaned_id} | exists={exists}")
        return {"edge_id": cleaned_id, "exists": exists}
    except Exception as e:
        logger.error(f"检查边存在性失败 | edge_id={cleaned_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"检查边存在性失败: {str(e)[:200]}")


# ============================================================
# Dependency Analysis Endpoints (3 new endpoints)
# ============================================================


@router.get(
    "/nodes/{node_id}/dependencies",
    summary="获取节点依赖",
    responses={
        (200): {"description": "依赖列表"},
        (404): {"description": "节点未找到"},
        (422): {"description": "参数错误"},
        (500): {"description": "获取失败"},
    },
)
async def get_node_dependencies_endpoint(node_id: str) -> dict[str, Any]:
    """
    获取节点的直接依赖

    Args:
        node_id: 节点ID

    Returns:
        依赖列表
    """
    cleaned_id = _validate_path_node_id(node_id)
    logger.info(f"获取节点依赖 | node_id={cleaned_id}")
    try:
        dependencies = await get_node_dependencies(cleaned_id)
        logger.debug(f"节点依赖获取成功 | node_id={cleaned_id} | 依赖数={len(dependencies)}")
        return {"node_id": cleaned_id, "dependencies": dependencies, "count": len(dependencies)}
    except Exception as e:
        logger.error(f"获取节点依赖失败 | node_id={cleaned_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取节点依赖失败: {str(e)[:200]}")


@router.get(
    "/nodes/{node_id}/transitive-dependencies",
    summary="获取传递依赖",
    responses={
        (200): {"description": "传递依赖列表"},
        (404): {"description": "节点未找到"},
        (422): {"description": "参数错误"},
        (500): {"description": "获取失败"},
    },
)
async def get_transitive_dependencies_endpoint(node_id: str) -> dict[str, Any]:
    """
    获取节点的传递依赖（所有下游节点）

    Args:
        node_id: 节点ID

    Returns:
        传递依赖列表
    """
    cleaned_id = _validate_path_node_id(node_id)
    logger.info(f"获取传递依赖 | node_id={cleaned_id}")
    try:
        transitive_deps = await get_transitive_dependencies(cleaned_id)
        logger.debug(
            f"传递依赖获取成功 | node_id={cleaned_id} | 传递依赖数={len(transitive_deps)}"
        )
        return {"node_id": cleaned_id, "transitive_dependencies": transitive_deps, "count": len(transitive_deps)}
    except Exception as e:
        logger.error(f"获取传递依赖失败 | node_id={cleaned_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取传递依赖失败: {str(e)[:200]}")


@router.get(
    "/nodes/{node_id}/impact",
    summary="获取影响分析",
    responses={
        (200): {"description": "影响分析结果"},
        (404): {"description": "节点未找到"},
        (422): {"description": "参数错误"},
        (500): {"description": "获取失败"},
    },
)
async def get_impact_analysis_endpoint(node_id: str) -> dict[str, Any]:
    """
    获取节点的影响分析（直接和传递影响）

    Args:
        node_id: 节点ID

    Returns:
        影响分析结果
    """
    cleaned_id = _validate_path_node_id(node_id)
    logger.info(f"获取影响分析 | node_id={cleaned_id}")
    try:
        impact = await get_impact_analysis(cleaned_id)
        logger.debug(f"影响分析获取成功 | node_id={cleaned_id}")
        return {"node_id": cleaned_id, "impact": impact}
    except Exception as e:
        logger.error(f"获取影响分析失败 | node_id={cleaned_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取影响分析失败: {str(e)[:200]}")


# ============================================================
# Batch Operations Endpoints (3 new endpoints)
# ============================================================


@router.post(
    "/nodes/batch",
    summary="批量添加节点",
    responses={
        (201): {"description": "批量添加成功"},
        (400): {"description": "参数错误"},
        (500): {"description": "批量添加失败"},
    },
)
async def batch_create_nodes(payload: BatchNodeCreateRequest) -> dict[str, Any]:
    """
    批量添加节点（分批处理以避免速率限制）

    Args:
        payload: 批量节点数据

    Returns:
        批量添加结果
    """
    logger.info(f"批量添加节点 | 数量={len(payload.nodes)}")
    try:
        import asyncio

        results = []
        errors = []

        # 分批处理，避免速率限制
        batch_size = 10
        for i in range(0, len(payload.nodes), batch_size):
            batch = payload.nodes[i : i + batch_size]
            for node_data in batch:
                try:
                    node_dict = node_data.model_dump() if hasattr(node_data, "model_dump") else node_data
                    result = await add_node(node_dict)
                    if result.get("success"):
                        results.append({"node_id": node_dict.get("id"), "status": "success"})
                    else:
                        errors.append({"node_id": node_dict.get("id"), "error": result.get("error")})
                except Exception as e:
                    errors.append({"node_id": node_dict.get("id"), "error": str(e)})

            # 速率限制延迟
            if i + batch_size < len(payload.nodes):
                await asyncio.sleep(_RATE_LIMIT_DELAY)

        logger.info(
            f"批量添加节点完成 | 成功={len(results)} | 失败={len(errors)}"
        )
        return {"total": len(payload.nodes), "success": len(results), "failed": len(errors), "results": results, "errors": errors}
    except Exception as e:
        logger.error(f"批量添加节点失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"批量添加节点失败: {str(e)[:200]}")


@router.post(
    "/edges/batch",
    summary="批量添加边",
    responses={
        (201): {"description": "批量添加成功"},
        (400): {"description": "参数错误"},
        (500): {"description": "批量添加失败"},
    },
)
async def batch_create_edges(payload: BatchEdgeCreateRequest) -> dict[str, Any]:
    """
    批量添加边（分批处理以避免速率限制）

    Args:
        payload: 批量边数据

    Returns:
        批量添加结果
    """
    logger.info(f"批量添加边 | 数量={len(payload.edges)}")
    try:
        import asyncio

        results = []
        errors = []

        # 分批处理，避免速率限制
        batch_size = 10
        for i in range(0, len(payload.edges), batch_size):
            batch = payload.edges[i : i + batch_size]
            for edge_data in batch:
                try:
                    edge_dict = edge_data.model_dump() if hasattr(edge_data, "model_dump") else edge_data
                    # 生成边ID（如果未提供）
                    if not edge_dict.get("id"):
                        edge_dict["id"] = f"{edge_dict.get('source')}__{edge_dict.get('target')}"
                    result = await add_edge(edge_dict)
                    if result.get("success"):
                        results.append({"edge_id": edge_dict.get("id"), "status": "success"})
                    else:
                        errors.append({"edge_id": edge_dict.get("id"), "error": result.get("error")})
                except Exception as e:
                    errors.append({"edge_id": edge_dict.get("id"), "error": str(e)})

            # 速率限制延迟
            if i + batch_size < len(payload.edges):
                await asyncio.sleep(_RATE_LIMIT_DELAY)

        logger.info(f"批量添加边完成 | 成功={len(results)} | 失败={len(errors)}")
        return {"total": len(payload.edges), "success": len(results), "failed": len(errors), "results": results, "errors": errors}
    except Exception as e:
        logger.error(f"批量添加边失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"批量添加边失败: {str(e)[:200]}")


@router.post(
    "/nodes/batch/delete",
    summary="批量删除节点",
    responses={
        (200): {"description": "批量删除成功"},
        (400): {"description": "参数错误"},
        (500): {"description": "批量删除失败"},
    },
)
async def batch_delete_nodes(payload: BatchDeleteRequest) -> dict[str, Any]:
    """
    批量删除节点（分批处理以避免速率限制）

    Args:
        payload: 批量删除请求

    Returns:
        批量删除结果
    """
    logger.info(f"批量删除节点 | 数量={len(payload.ids)}")
    try:
        import asyncio

        results = []
        errors = []

        # 分批处理，避免速率限制
        batch_size = 10
        for i in range(0, len(payload.ids), batch_size):
            batch = payload.ids[i : i + batch_size]
            for node_id in batch:
                try:
                    result = await remove_node(node_id)
                    if result.get("success"):
                        results.append({"node_id": node_id, "status": "success"})
                    else:
                        errors.append({"node_id": node_id, "error": result.get("error")})
                except Exception as e:
                    errors.append({"node_id": node_id, "error": str(e)})

            # 速率限制延迟
            if i + batch_size < len(payload.ids):
                await asyncio.sleep(_RATE_LIMIT_DELAY)

        logger.info(f"批量删除节点完成 | 成功={len(results)} | 失败={len(errors)}")
        return {"total": len(payload.ids), "success": len(results), "failed": len(errors), "results": results, "errors": errors}
    except Exception as e:
        logger.error(f"批量删除节点失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"批量删除节点失败: {str(e)[:200]}")
