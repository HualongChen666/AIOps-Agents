# -*- coding: utf-8 -*-
"""
Realtime Router
实时通信统一路由

聚合 SSE 与 WebSocket 能力，提供：
- GET /api/v1/realtime/events -> SSE 事件流
- GET /api/v1/realtime/ws     -> WebSocket 实时通信
- GET /api/v1/realtime/status -> 连接状态统计
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from core.websocket_manager import manager as websocket_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/realtime", tags=["Realtime"])


class RealtimeStatus(BaseModel):
    """实时通信状态统计"""

    connections: int = Field(0, description="当前 WebSocket 连接数")
    rooms: Dict[str, int] = Field(default_factory=dict, description="每个房间的连接数")
    timestamp: str = Field("", description="统计时间")

    model_config = {
        "json_schema_extra": {
            "example": {
                "connections": 0,
                "rooms": {"realtime": 0, "metrics": 0},
                "timestamp": "2026-07-22T14:00:00",
            }
        }
    }


@router.get(
    "/events",
    summary="SSE 实时事件流",
    response_class=StreamingResponse,
)
async def realtime_sse_events(
    count: int = Query(default=0, ge=0, description="最大推送事件数,0 表示无限"),
) -> StreamingResponse:
    """推送 Server-Sent Events 实时事件"""

    async def event_stream():
        emitted = 0
        while True:
            now = datetime.utcnow().isoformat()
            yield f'event: heartbeat\ndata: {{"count": {emitted}, "time": "{now}"}}\n\n'
            emitted += 1
            if count > 0 and emitted >= count:
                break
            await asyncio.sleep(5)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.websocket("/ws")
async def realtime_websocket(websocket: WebSocket):
    """WebSocket 实时通信端点（统一房间：realtime）"""
    await websocket_manager.connect(websocket, "realtime")
    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
            except json.JSONDecodeError:
                message = {"raw": data}

            await websocket_manager.broadcast(
                {"type": "message", "data": message, "timestamp": datetime.utcnow().isoformat()},
                "realtime",
            )
            await websocket_manager.send_personal_message(
                {"type": "status", "status": "received"}, websocket
            )
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket, "realtime")
        logger.info("Realtime WebSocket disconnected")
    except Exception as exc:
        logger.error(f"Realtime WebSocket error: {exc}")
        websocket_manager.disconnect(websocket, "realtime")


@router.get(
    "/status",
    summary="实时通信连接状态",
    response_model=RealtimeStatus,
)
async def realtime_status() -> Dict[str, Any]:
    """返回当前 WebSocket 连接统计"""
    try:
        rooms = getattr(websocket_manager, "rooms", {})
        connections = getattr(websocket_manager, "active_connections", [])
        room_counts = {
            room: len(conns) for room, conns in rooms.items() if isinstance(conns, (list, set))
        }
        count = len(connections) if isinstance(connections, list) else 0
    except Exception as exc:
        logger.warning(f"Failed to gather realtime status: {exc}")
        count = 0
        room_counts = {}

    return {
        "connections": count,
        "rooms": room_counts,
        "timestamp": datetime.utcnow().isoformat(),
    }
