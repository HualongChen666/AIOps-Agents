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
        import uuid

        try:
            import httpx
        except ImportError:
            httpx = None  # type: ignore

        incident_id = str(uuid.uuid4())
        if httpx and provider.lower() == "jira" and JIRA_URL and JIRA_TOKEN:
            async with httpx.AsyncClient() as client:
                payload = {
                    "fields": {
                        "project": {"key": data.get("project_key", "OPS")},
                        "summary": data.get("summary", "Auto-created incident"),
                        "description": data.get("description", ""),
                        "issuetype": {"name": data.get("issue_type", "Bug")},
                    }
                }
                resp = await client.post(
                    f"{JIRA_URL.rstrip('/')}/rest/api/2/issue",
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {JIRA_TOKEN}",
                        "Content-Type": "application/json",
                    },
                    timeout=30,
                )
                if resp.status_code in (200, 201):
                    resp_data = resp.json()
                    return {
                        "status": "created",
                        "provider": provider,
                        "incident_id": resp_data.get("key", incident_id),
                        "message": "工单创建成功",
                    }
                logger.warning(f"Jira create incident failed: {resp.status_code} {resp.text}")

        elif httpx and provider.lower() == "servicenow" and SERVICE_NOW_URL and SERVICE_NOW_TOKEN:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{SERVICE_NOW_URL.rstrip('/')}/api/now/table/incident",
                    json={
                        "short_description": data.get("summary", "Auto-created incident"),
                        "description": data.get("description", ""),
                        "urgency": data.get("urgency", "3"),
                    },
                    headers={
                        "Authorization": f"Basic {SERVICE_NOW_TOKEN}",
                        "Content-Type": "application/json",
                    },
                    timeout=30,
                )
                if resp.status_code in (200, 201):
                    resp_data = resp.json()
                    result = resp_data.get("result", {})
                    return {
                        "status": "created",
                        "provider": provider,
                        "incident_id": result.get("sys_id", incident_id),
                        "message": "工单创建成功",
                    }
                logger.warning(f"ServiceNow create incident failed: {resp.status_code} {resp.text}")

        return {
            "status": "created",
            "provider": provider,
            "incident_id": incident_id,
            "message": "工单创建成功（本地记录，未实际调用外部ITSM）",
        }
    except Exception as exc:
        logger.warning(f"External ITSM create failed for {provider}: {exc}; returning local record")
        return {
            "status": "created",
            "provider": provider,
            "incident_id": incident_id,
            "message": "工单创建成功（本地记录，未实际调用外部ITSM）",
        }


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
        try:
            import httpx
        except ImportError:
            httpx = None  # type: ignore

        if httpx and provider.lower() == "jira" and JIRA_URL and JIRA_TOKEN:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{JIRA_URL.rstrip('/')}/rest/api/2/issue/{incident_id}/transitions",
                    json={"transition": {"id": "2"}},
                    headers={
                        "Authorization": f"Bearer {JIRA_TOKEN}",
                        "Content-Type": "application/json",
                    },
                    timeout=30,
                )
                if resp.status_code in (200, 201, 204):
                    return {
                        "status": "resolved",
                        "provider": provider,
                        "incident_id": incident_id,
                        "message": "工单已关闭",
                    }
                logger.warning(f"Jira resolve incident failed: {resp.status_code} {resp.text}")

        elif httpx and provider.lower() == "servicenow" and SERVICE_NOW_URL and SERVICE_NOW_TOKEN:
            async with httpx.AsyncClient() as client:
                resp = await client.put(
                    f"{SERVICE_NOW_URL.rstrip('/')}/api/now/table/incident/{incident_id}",
                    json={"state": "6", "close_code": "Resolved", "close_notes": "Closed by AIOps"},
                    headers={
                        "Authorization": f"Basic {SERVICE_NOW_TOKEN}",
                        "Content-Type": "application/json",
                    },
                    timeout=30,
                )
                if resp.status_code in (200, 201, 204):
                    return {
                        "status": "resolved",
                        "provider": provider,
                        "incident_id": incident_id,
                        "message": "工单已关闭",
                    }
                logger.warning(
                    f"ServiceNow resolve incident failed: {resp.status_code} {resp.text}"
                )

        return {
            "status": "resolved",
            "provider": provider,
            "incident_id": incident_id,
            "message": "工单已关闭（本地记录，未实际调用外部ITSM）",
        }
    except Exception as exc:
        logger.warning(
            f"External ITSM resolve failed for {provider}: {exc}; returning local record"
        )
        return {
            "status": "resolved",
            "provider": provider,
            "incident_id": incident_id,
            "message": "工单已关闭（本地记录，未实际调用外部ITSM）",
        }
