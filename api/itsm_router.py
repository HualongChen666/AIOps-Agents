# -*- coding: utf-8 -*-
import logging
import os
from typing import Any, Dict

from fastapi import APIRouter, HTTPException

# from core.itsm_engine import (
#     create_incident as itsm_create_incident,
#     resolve_incident as itsm_resolve_incident  # Not implemented
# )

router = APIRouter(prefix="/api/itsm", tags=["ITSM"])
logger = logging.getLogger(__name__)

# ---------- ServiceNow 配置（兼容旧实现） ----------
SERVICE_NOW_URL = os.getenv("SERVICENOW_URL")
SERVICE_NOW_TOKEN = os.getenv("SERVICENOW_TOKEN")

# ---------- Jira 配置 ----------
JIRA_URL = os.getenv("JIRA_URL")
JIRA_TOKEN = os.getenv("JIRA_TOKEN")


@router.post(
    "/incident",
    summary="创建 ITSM 工单（ServiceNow/Jira）",
    responses={
        200: {
            "description": "工单创建成功",
            "content": {
                "application/json": {
                    "example": {
                        "status": "pending",
                        "message": "itsm_create_incident not implemented",
                    }
                }
            },
        },
        400: {"description": "不支持的ITSM提供商"},
        500: {"description": "配置未完成或创建失败"},
    },
)
async def create_incident(data: Dict, provider: str = "servicenow") -> Dict[str, Any]:
    """创建工单，默认使用 ServiceNow。如需使用 Jira，请传入 provider="jira" 并提供对应的 payload 结构。"""
    if provider.lower() == "servicenow":
        if not SERVICE_NOW_URL or not SERVICE_NOW_TOKEN:
            raise HTTPException(status_code=500, detail="ServiceNow 配置未完成")
    elif provider.lower() == "jira":
        if not JIRA_URL or not JIRA_TOKEN:
            raise HTTPException(status_code=500, detail="Jira 配置未完成")
    else:
        raise HTTPException(status_code=400, detail="Unsupported ITSM provider")
    try:
        # result = await itsm_create_incident(provider, data)
        result = {"status": "pending", "message": "itsm_create_incident not implemented"}
        return result
    except Exception:
        logger.exception("Create incident failed")
        raise HTTPException(status_code=500, detail="Failed to create ITSM incident")


@router.patch(
    "/incident/{incident_id}",
    summary="解决/关闭 ITSM 工单（ServiceNow/Jira）",
    responses={
        200: {
            "description": "工单关闭成功",
            "content": {
                "application/json": {
                    "example": {
                        "status": "pending",
                        "message": "itsm_resolve_incident not implemented",
                    }
                }
            },
        },
        400: {"description": "不支持的ITSM提供商"},
        500: {"description": "配置未完成或关闭失败"},
    },
)
async def resolve_incident(incident_id: str, provider: str = "servicenow") -> Dict[str, Any]:
    """关闭工单。ServiceNow 使用 sys_id，Jira 使用 issue key（如 PROJ-123）。"""
    if provider.lower() == "servicenow":
        if not SERVICE_NOW_URL or not SERVICE_NOW_TOKEN:
            raise HTTPException(status_code=500, detail="ServiceNow 配置未完成")
    elif provider.lower() == "jira":
        if not JIRA_URL or not JIRA_TOKEN:
            raise HTTPException(status_code=500, detail="Jira 配置未完成")
    else:
        raise HTTPException(status_code=400, detail="Unsupported ITSM provider")
    try:
        # result = await itsm_resolve_incident(provider, incident_id)
        result = {"status": "pending", "message": "itsm_resolve_incident not implemented"}
        return result
    except Exception:
        logger.exception("Resolve incident failed")
        raise HTTPException(status_code=500, detail="Failed to resolve ITSM incident")
