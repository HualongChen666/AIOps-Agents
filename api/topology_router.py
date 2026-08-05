# -*- coding: utf-8 -*-
import logging
import re
import time
from threading import Lock
from typing import Any, Literal, cast

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator


from core.topology_engine import (
    TOPOLOGY_TYPES,
    get_full_link_topology,
    get_node_timeline,
    get_topology_status,
    update_node_health,
)

logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/api/v1/topologies", tags=["拓扑管理"]
)
_VALID_NODE_ID_PATTERN = re.compile("^[a-zA-Z0-9._\\-]+$")
_FULL_LINK_CACHE_TTL_SEC = 5
_full_link_cache: dict[str, Any] = {"data": None, "ts": 0.0}
_full_link_cache_lock = Lock()


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
