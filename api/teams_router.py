# -*- coding: utf-8 -*-
"""Microsoft Teams Integration API Router

提供 Microsoft Teams 集成的 REST API 接口，基于 core.teams_adapter 实现。
- POST /api/teams/message        -> 发送文本消息
- POST /api/teams/interactive      -> 发送交互式卡片消息
- POST /api/teams/events           -> Teams 连接器回调（占位）
"""

import re
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from loguru import logger as _logger
from pydantic import BaseModel, Field

from core.authentication import get_current_active_user
from core.chat_command_handler import handle_instruction
from core.teams_adapter import post_interactive_message, post_message

router = APIRouter(prefix="/api/teams", tags=["Microsoft Teams Integration"])


class TeamsMessageRequest(BaseModel):
    """Teams 文本消息请求模型"""

    text: str = Field(..., description="消息文本")
    title: Optional[str] = Field(None, description="消息标题")
    channel: Optional[str] = Field(None, description="目标频道名称（仅用于记录）")
    color: Optional[str] = Field(None, description="主题颜色")

    model_config = {
        "extra": "ignore",
        "json_schema_extra": {
            "example": {
                "text": "Server CPU usage is above 80%",
                "title": "AIOps Alert",
                "channel": "General",
                "color": "ff0000",
            }
        },
    }


class TeamsAction(BaseModel):
    """Teams 卡片按钮配置"""

    title: str = Field(..., description="按钮标题")
    url: Optional[str] = Field(None, description="Action.OpenUrl 的目标地址")
    action: Optional[str] = Field(None, description="Action.Submit 提交标识")
    value: Optional[str] = Field(None, description="按钮提交值")
    type: Optional[str] = Field("Action.OpenUrl", description="Action 类型")


class TeamsInteractiveRequest(BaseModel):
    """Teams 交互式卡片请求模型"""

    title: str = Field(..., description="卡片标题")
    description: str = Field(..., description="卡片正文")
    actions: List[TeamsAction] = Field(..., description="交互按钮列表")
    channel: Optional[str] = Field(None, description="目标频道名称（仅用于记录）")
    color: Optional[str] = Field(None, description="主题颜色")

    model_config = {
        "extra": "ignore",
        "json_schema_extra": {
            "example": {
                "title": "Alert Acknowledgment",
                "description": "High CPU on server-01. Please acknowledge.",
                "actions": [
                    {
                        "title": "Acknowledge",
                        "type": "Action.Submit",
                        "action": "ack",
                        "value": "ok",
                    },
                    {
                        "title": "Open Dashboard",
                        "type": "Action.OpenUrl",
                        "url": "http://localhost:3000",
                    },
                ],
                "channel": "General",
                "color": "ff0000",
            }
        },
    }


@router.post(
    "/message",
    summary="发送消息到 Microsoft Teams",
    responses={
        200: {"description": "发送成功"},
        401: {"description": "未授权"},
        503: {"description": "Teams webhook 未配置"},
        500: {"description": "发送失败"},
    },
)
async def send_teams_message(
    request: TeamsMessageRequest, current_user: dict = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """发送普通文本消息到 Microsoft Teams 频道"""
    try:
        result = await post_message(
            text=request.text,
            title=request.title,
            channel=request.channel,
            color=request.color,
        )
        return {"success": True, "message": "Message sent successfully", "data": result}
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        _logger.error(f"Failed to send Teams message: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to send message: {str(e)}")


@router.post(
    "/interactive",
    summary="发送交互式卡片到 Microsoft Teams",
    responses={
        200: {"description": "发送成功"},
        401: {"description": "未授权"},
        503: {"description": "Teams webhook 未配置"},
        500: {"description": "发送失败"},
    },
)
async def send_teams_interactive_message(
    request: TeamsInteractiveRequest,
    current_user: dict = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """发送包含操作按钮的 Adaptive Card 到 Microsoft Teams"""
    try:
        actions = [action.model_dump() for action in request.actions]
        result = await post_interactive_message(
            title=request.title,
            description=request.description,
            actions=actions,
            channel=request.channel,
            color=request.color,
        )
        return {
            "success": True,
            "message": "Interactive card sent successfully",
            "data": result,
        }
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        _logger.error(f"Failed to send Teams interactive card: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to send card: {str(e)}")


@router.post(
    "/events",
    summary="Microsoft Teams 连接器回调（支持工程师回复/按钮交互）",
    responses={
        200: {"description": "接收成功"},
        401: {"description": "未授权"},
        500: {"description": "处理失败"},
    },
)
async def teams_events_callback(payload: Dict[str, Any]) -> Dict[str, Any]:
    """接收 Teams 连接器 / Power Automate 回传的 JSON 载荷,解析工程师命令/按钮"""
    _logger.info(f"Received Teams callback payload with keys: {list(payload.keys())}")

    # 处理 Adaptive Card 按钮提交
    action_data = payload.get("value") or payload.get("action") or {}
    if action_data:
        action_type = str(action_data.get("action", "")).lower()
        value = action_data.get("value", "")
        if action_type == "approve":
            return {"success": True, "action": {"type": "approve", "target": value}}
        if action_type == "reject":
            return {"success": True, "action": {"type": "reject", "target": value}}

    # 处理普通文本消息
    text = str(payload.get("text", payload.get("message", ""))).strip()
    user_id = str(payload.get("from", payload.get("user_id", "")))
    channel = str(payload.get("channel", payload.get("conversation", "")))
    if text:
        # 去除 @bot 提及
        text = re.sub(r"<at>[^<]*</at>", "", text).strip()
        parsed = handle_instruction(
            text,
            user_id=user_id,
            user_name=user_id,
            channel=f"teams:{channel}",
            verified=True,
        )
        _logger.info(f"Teams command parsed: {parsed}")
        return {"success": True, "action": parsed}

    return {"success": True, "message": "Callback received", "data": {}}
