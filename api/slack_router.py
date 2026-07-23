# -*- coding: utf-8 -*-
"""Slack Integration API Router

提供Slack集成的REST API接口，基于core.slack_adapter实现。
- POST /api/slack/message → 发送消息到Slack频道
- POST /api/slack/interactive → 发送交互式消息
- POST /api/slack/events → Slack Events API回调端点
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from loguru import logger as _logger
from pydantic import BaseModel, Field

from core.authentication import get_current_active_user
from core.slack_adapter import post_interactive_message, post_message, verify_slack_signature

router = APIRouter(prefix="/api/slack", tags=["Slack Integration"])


class SlackMessageRequest(BaseModel):
    """Slack消息请求模型"""

    text: str = Field(..., description="消息文本")
    channel: Optional[str] = Field(None, description="目标频道ID或名称")
    thread_ts: Optional[str] = Field(None, description="线程时间戳（用于回复）")
    blocks: Optional[List[Dict[str, Any]]] = Field(None, description="Block-Kit结构体")

    model_config = {
        "extra": "ignore",
        "json_schema_extra": {
            "example": {
                "text": "example",
                "channel": "example",
                "thread_ts": "example",
                "blocks": "example",
            }
        },
    }


class SlackInteractiveMessageRequest(BaseModel):
    """Slack交互式消息请求模型"""

    text: str = Field(..., description="消息文本")
    channel: Optional[str] = Field(None, description="目标频道ID或名称")
    actions: List[Dict[str, Any]] = Field(..., description="交互按钮/下拉列表配置")

    model_config = {
        "extra": "ignore",
        "json_schema_extra": {"example": {"text": "example", "channel": "example", "actions": []}},
    }


@router.post(
    "/message",
    summary="发送消息到Slack",
    responses={
        (200): {"description": "发送成功"},
        (401): {"description": "未授权"},
        (503): {"description": "Slack配置错误"},
        (500): {"description": "发送失败"},
    },
)
async def send_slack_message(
    request: SlackMessageRequest, current_user: dict = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """发送普通文本或Block-Kit消息到Slack频道"""
    try:
        result = await post_message(
            text=request.text,
            channel=request.channel,
            blocks=request.blocks,
            thread_ts=request.thread_ts,
        )
        return {"success": True, "message": "Message sent successfully", "data": result}
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send message: {str(e)}")


@router.post(
    "/interactive",
    summary="发送交互式消息到Slack",
    responses={
        (200): {"description": "发送成功"},
        (401): {"description": "未授权"},
        (503): {"description": "Slack配置错误"},
        (500): {"description": "发送失败"},
    },
)
async def send_slack_interactive_message(
    request: SlackInteractiveMessageRequest, current_user: dict = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """发送包含按钮/下拉列表的交互式消息到Slack频道"""
    try:
        result = await post_interactive_message(
            title=request.text, description="", actions=request.actions, channel=request.channel
        )
        return {"success": True, "message": "Interactive message sent successfully", "data": result}
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send interactive message: {str(e)}")


@router.post(
    "/events",
    summary="Slack Events API回调端点",
    responses={
        (200): {"description": "处理成功"},
        (403): {"description": "签名验证失败"},
        (500): {"description": "处理失败"},
    },
)
async def slack_events_callback(
    request: Request,
    x_slack_signature: Optional[str] = Header(None, alias="X-Slack-Signature"),
    x_slack_timestamp: Optional[str] = Header(None, alias="X-Slack-Timestamp"),
) -> Dict[str, str]:
    """处理Slack Events API的回调请求"""
    try:
        body = await request.body()
        if x_slack_timestamp is None or x_slack_signature is None:
            raise HTTPException(status_code=403, detail="Missing Slack signature headers")
        if not verify_slack_signature(x_slack_timestamp, x_slack_signature, body):
            raise HTTPException(status_code=403, detail="Invalid Slack signature")
        event_data = await request.json()
        if event_data.get("type") == "url_verification":
            return {"challenge": event_data.get("challenge")}
        event_type = event_data.get("event", {}).get("type")
        _logger.info(f"Received Slack event: {event_type}")
        return {"status": "ok"}
    except HTTPException:
        raise
    except Exception as e:
        _logger.error(f"Error processing Slack event: {e}")
        raise HTTPException(status_code=500, detail="Failed to process event")


@router.get(
    "/health",
    summary="Slack集成健康检查",
    responses={(200): {"description": "健康状态"}, (401): {"description": "未授权"}},
)
async def slack_health_check(
    current_user: dict = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """检查Slack集成状态"""
    from config import SLACK_BOT_TOKEN, SLACK_DEFAULT_CHANNEL

    return {
        "status": "healthy" if SLACK_BOT_TOKEN else "not_configured",
        "default_channel": SLACK_DEFAULT_CHANNEL,
        "token_configured": bool(SLACK_BOT_TOKEN),
    }


__all__ = ["router"]
