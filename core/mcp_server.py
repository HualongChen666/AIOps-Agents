# -*- coding: utf-8 -*-
"""MCP (Multi‑Channel Protocol) server implementation.

Provides a set of JSON‑RPC style HTTP endpoints that expose core
AIOps capabilities to external AI agents (Claude Desktop, Cursor,
etc.). The server is mounted under ``/mcp`` in the FastAPI app.
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .mcp_tools import (
    approve_repair,
    get_host_health,
    get_metrics,
    search_incident_history,
    trigger_repair_with_hitl,
)

_logger = logging.getLogger(__name__)
router = APIRouter(prefix="/mcp", tags=["MCP"])


class HostHealthRequest(BaseModel):
    host_id: str

    model_config = {"json_schema_extra": {"example": {"host_id": "example"}}}


class RepairRequest(BaseModel):
    alert_id: str
    user: str
    comment: Optional[str] = None

    model_config = {"json_schema_extra": {"example": {"alert_id": "example", "user": "example", "comment": "example"}}}


class SearchRequest(BaseModel):
    query: str
    limit: int = 10

    model_config = {"json_schema_extra": {"example": {"query": "example", "limit": 0}}}


class MetricsRequest(BaseModel):
    host_id: str
    metrics: List[str]

    model_config = {"json_schema_extra": {"example": {"host_id": "example", "metrics": []}}}


class ApproveRequest(BaseModel):
    repair_id: str
    approved: bool
    comment: Optional[str] = None

    model_config = {"json_schema_extra": {"example": {"repair_id": "example", "approved": True, "comment": "example"}}}


@router.post("/get_host_health")
async def api_get_host_health(req: HostHealthRequest) -> Dict[str, Any]:
    """获取指定主机的健康状态。"""
    try:
        return await get_host_health(req.host_id)
    except Exception as e:
        _logger.error("MCP get_host_health error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/trigger_repair_with_hitl")
async def api_trigger_repair(req: RepairRequest) -> Dict[str, Any]:
    """触发带 HITL（人工审核）流程的修复任务。"""
    try:
        return await trigger_repair_with_hitl(req.alert_id, req.user, req.comment)
    except Exception as e:
        _logger.error("MCP trigger_repair_with_hitl error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search_incident_history")
async def api_search_incident(req: SearchRequest) -> List[Dict[str, Any]]:
    """根据关键字搜索历史告警/修复记录。"""
    try:
        return await search_incident_history(req.query, req.limit)
    except Exception as e:
        _logger.error("MCP search_incident_history error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/get_metrics")
async def api_get_metrics(req: MetricsRequest) -> Dict[str, Any]:
    """一次性获取多个指标的当前数值。"""
    try:
        return await get_metrics(req.host_id, req.metrics)
    except Exception as e:
        _logger.error("MCP get_metrics error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/approve_repair")
async def api_approve_repair(req: ApproveRequest) -> Dict[str, Any]:
    try:
        return await approve_repair(req.repair_id, req.approved, req.comment)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
