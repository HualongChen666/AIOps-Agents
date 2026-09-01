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
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.auth_service import get_current_user
from core.auth_db import User
from core.database import get_db
from core.models import RealtimeEvent, RealtimeStream, RealtimeSubscription, RealtimeWebhook
from core.websocket_manager import manager as websocket_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/realtime", tags=["Realtime"])


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


class RealtimeDataItem(BaseModel):
    """实时数据项"""

    id: str = Field(..., description="数据项ID")
    name: str = Field(..., description="数据项名称")
    status: str = Field(..., description="状态")
    created_at: str = Field(..., description="创建时间")

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "STR-001",
                "name": "示例流",
                "status": "active",
                "created_at": "2026-07-22T14:00:00",
            }
        }
    }


class RealtimeDataList(BaseModel):
    """实时数据列表响应"""

    items: List[RealtimeDataItem] = Field(default_factory=list, description="数据项列表")
    total: int = Field(0, description="总数")
    timestamp: str = Field(..., description="响应时间")

    model_config = {
        "json_schema_extra": {
            "example": {
                "items": [],
                "total": 0,
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
async def realtime_status(current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
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


# ==================== Additional Realtime Endpoints ====================


@router.get(
    "/stream-monitoring",
    summary="流监控",
    response_model=RealtimeDataList,
)
async def stream_monitoring(
    limit: int = Query(default=50, ge=1, le=200, description="返回数量限制"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """获取流监控数据"""
    try:
        query = db.query(RealtimeStream).filter(RealtimeStream.stream_type == "sse")
        streams = query.order_by(RealtimeStream.created_at.desc()).limit(limit).all()

        items = [
            {
                "id": stream.id,
                "name": stream.name,
                "status": stream.status,
                "created_at": stream.created_at.isoformat() if stream.created_at else "",
            }
            for stream in streams
        ]

        logger.info(f"User {current_user.username} retrieved stream monitoring data: {len(items)} items")
        return {
            "items": items,
            "total": len(items),
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Failed to retrieve stream monitoring data: {e}")
        raise HTTPException(status_code=500, detail=f"获取流监控数据失败: {str(e)}")


@router.get(
    "/event-processing",
    summary="事件处理",
    response_model=RealtimeDataList,
)
async def event_processing(
    limit: int = Query(default=50, ge=1, le=200, description="返回数量限制"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """获取事件处理数据"""
    try:
        query = db.query(RealtimeEvent)
        events = query.order_by(RealtimeEvent.timestamp.desc()).limit(limit).all()

        items = [
            {
                "id": f"EVT-{event.id}",
                "name": f"{event.event_type}事件",
                "status": "processed",
                "created_at": event.timestamp.isoformat() if event.timestamp else "",
            }
            for event in events
        ]

        logger.info(f"User {current_user.username} retrieved event processing data: {len(items)} items")
        return {
            "items": items,
            "total": len(items),
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Failed to retrieve event processing data: {e}")
        raise HTTPException(status_code=500, detail=f"获取事件处理数据失败: {str(e)}")


@router.get(
    "/flink-stream",
    summary="Flink流处理",
    response_model=RealtimeDataList,
)
async def flink_stream(
    limit: int = Query(default=50, ge=1, le=200, description="返回数量限制"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """获取Flink流处理数据"""
    try:
        query = db.query(RealtimeStream).filter(RealtimeStream.stream_type == "kafka")
        streams = query.order_by(RealtimeStream.created_at.desc()).limit(limit).all()

        items = [
            {
                "id": stream.id,
                "name": stream.name,
                "status": stream.status,
                "created_at": stream.created_at.isoformat() if stream.created_at else "",
            }
            for stream in streams
        ]

        logger.info(f"User {current_user.username} retrieved Flink stream data: {len(items)} items")
        return {
            "items": items,
            "total": len(items),
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Failed to retrieve Flink stream data: {e}")
        raise HTTPException(status_code=500, detail=f"获取Flink流处理数据失败: {str(e)}")


@router.get(
    "/kafka-stream",
    summary="Kafka流处理",
    response_model=RealtimeDataList,
)
async def kafka_stream(
    limit: int = Query(default=50, ge=1, le=200, description="返回数量限制"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """获取Kafka流处理数据"""
    try:
        query = db.query(RealtimeStream).filter(RealtimeStream.source.like("%kafka%"))
        streams = query.order_by(RealtimeStream.created_at.desc()).limit(limit).all()

        items = [
            {
                "id": stream.id,
                "name": stream.name,
                "status": stream.status,
                "created_at": stream.created_at.isoformat() if stream.created_at else "",
            }
            for stream in streams
        ]

        logger.info(f"User {current_user.username} retrieved Kafka stream data: {len(items)} items")
        return {
            "items": items,
            "total": len(items),
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Failed to retrieve Kafka stream data: {e}")
        raise HTTPException(status_code=500, detail=f"获取Kafka流处理数据失败: {str(e)}")


@router.get(
    "/message-queue",
    summary="消息队列",
    response_model=RealtimeDataList,
)
async def message_queue(
    limit: int = Query(default=50, ge=1, le=200, description="返回数量限制"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """获取消息队列数据"""
    try:
        query = db.query(RealtimeSubscription)
        subscriptions = query.order_by(RealtimeSubscription.created_at.desc()).limit(limit).all()

        items = [
            {
                "id": sub.id,
                "name": f"{sub.subscriber_id}订阅",
                "status": sub.status,
                "created_at": sub.created_at.isoformat() if sub.created_at else "",
            }
            for sub in subscriptions
        ]

        logger.info(f"User {current_user.username} retrieved message queue data: {len(items)} items")
        return {
            "items": items,
            "total": len(items),
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Failed to retrieve message queue data: {e}")
        raise HTTPException(status_code=500, detail=f"获取消息队列数据失败: {str(e)}")


@router.get(
    "/push-notification",
    summary="推送通知",
    response_model=RealtimeDataList,
)
async def push_notification(
    limit: int = Query(default=50, ge=1, le=200, description="返回数量限制"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """获取推送通知数据"""
    try:
        query = db.query(RealtimeWebhook).filter(RealtimeWebhook.enabled == True)
        webhooks = query.order_by(RealtimeWebhook.created_at.desc()).limit(limit).all()

        items = [
            {
                "id": webhook.id,
                "name": webhook.name,
                "status": "enabled" if webhook.enabled else "disabled",
                "created_at": webhook.created_at.isoformat() if webhook.created_at else "",
            }
            for webhook in webhooks
        ]

        logger.info(f"User {current_user.username} retrieved push notification data: {len(items)} items")
        return {
            "items": items,
            "total": len(items),
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Failed to retrieve push notification data: {e}")
        raise HTTPException(status_code=500, detail=f"获取推送通知数据失败: {str(e)}")


@router.get(
    "/bidirectional-communication",
    summary="双向通信",
    response_model=RealtimeDataList,
)
async def bidirectional_communication(
    limit: int = Query(default=50, ge=1, le=200, description="返回数量限制"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """获取双向通信数据"""
    try:
        query = db.query(RealtimeStream).filter(RealtimeStream.stream_type == "websocket")
        streams = query.order_by(RealtimeStream.created_at.desc()).limit(limit).all()

        items = [
            {
                "id": stream.id,
                "name": stream.name,
                "status": stream.status,
                "created_at": stream.created_at.isoformat() if stream.created_at else "",
            }
            for stream in streams
        ]

        logger.info(f"User {current_user.username} retrieved bidirectional communication data: {len(items)} items")
        return {
            "items": items,
            "total": len(items),
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Failed to retrieve bidirectional communication data: {e}")
        raise HTTPException(status_code=500, detail=f"获取双向通信数据失败: {str(e)}")


@router.get(
    "/sse",
    summary="SSE事件流",
    response_model=RealtimeDataList,
)
async def sse(
    limit: int = Query(default=50, ge=1, le=200, description="返回数量限制"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """获取SSE事件流数据"""
    try:
        query = db.query(RealtimeStream).filter(RealtimeStream.stream_type == "sse")
        streams = query.order_by(RealtimeStream.created_at.desc()).limit(limit).all()

        items = [
            {
                "id": stream.id,
                "name": stream.name,
                "status": stream.status,
                "created_at": stream.created_at.isoformat() if stream.created_at else "",
            }
            for stream in streams
        ]

        logger.info(f"User {current_user.username} retrieved SSE data: {len(items)} items")
        return {
            "items": items,
            "total": len(items),
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Failed to retrieve SSE data: {e}")
        raise HTTPException(status_code=500, detail=f"获取SSE事件流数据失败: {str(e)}")


@router.get(
    "/enhanced-websocket",
    summary="增强WebSocket",
    response_model=RealtimeDataList,
)
async def enhanced_websocket(
    limit: int = Query(default=50, ge=1, le=200, description="返回数量限制"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """获取增强WebSocket数据"""
    try:
        query = db.query(RealtimeStream).filter(RealtimeStream.stream_type == "websocket")
        streams = query.order_by(RealtimeStream.created_at.desc()).limit(limit).all()

        items = [
            {
                "id": stream.id,
                "name": stream.name,
                "status": stream.status,
                "created_at": stream.created_at.isoformat() if stream.created_at else "",
            }
            for stream in streams
        ]

        logger.info(f"User {current_user.username} retrieved enhanced WebSocket data: {len(items)} items")
        return {
            "items": items,
            "total": len(items),
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Failed to retrieve enhanced WebSocket data: {e}")
        raise HTTPException(status_code=500, detail=f"获取增强WebSocket数据失败: {str(e)}")


@router.get(
    "/websocket-manager",
    summary="WebSocket管理",
    response_model=RealtimeDataList,
)
async def websocket_manager_endpoint(
    limit: int = Query(default=50, ge=1, le=200, description="返回数量限制"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """获取WebSocket管理数据"""
    try:
        query = db.query(RealtimeSubscription).filter(RealtimeSubscription.subscription_type == "websocket")
        subscriptions = query.order_by(RealtimeSubscription.created_at.desc()).limit(limit).all()

        items = [
            {
                "id": sub.id,
                "name": f"{sub.subscriber_id}连接",
                "status": sub.status,
                "created_at": sub.created_at.isoformat() if sub.created_at else "",
            }
            for sub in subscriptions
        ]

        logger.info(f"User {current_user.username} retrieved WebSocket manager data: {len(items)} items")
        return {
            "items": items,
            "total": len(items),
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Failed to retrieve WebSocket manager data: {e}")
        raise HTTPException(status_code=500, detail=f"获取WebSocket管理数据失败: {str(e)}")


@router.get(
    "/websocket-connection",
    summary="WebSocket连接",
    response_model=RealtimeDataList,
)
async def websocket_connection(
    limit: int = Query(default=50, ge=1, le=200, description="返回数量限制"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """获取WebSocket连接数据"""
    try:
        query = db.query(RealtimeSubscription).filter(RealtimeSubscription.subscription_type == "websocket")
        subscriptions = query.order_by(RealtimeSubscription.created_at.desc()).limit(limit).all()

        items = [
            {
                "id": sub.id,
                "name": f"连接-{sub.subscriber_id}",
                "status": sub.status,
                "created_at": sub.created_at.isoformat() if sub.created_at else "",
            }
            for sub in subscriptions
        ]

        logger.info(f"User {current_user.username} retrieved WebSocket connection data: {len(items)} items")
        return {
            "items": items,
            "total": len(items),
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Failed to retrieve WebSocket connection data: {e}")
        raise HTTPException(status_code=500, detail=f"获取WebSocket连接数据失败: {str(e)}")


@router.get(
    "/websocket",
    summary="WebSocket",
    response_model=RealtimeDataList,
)
async def websocket_endpoint(
    limit: int = Query(default=50, ge=1, le=200, description="返回数量限制"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """获取WebSocket数据"""
    try:
        query = db.query(RealtimeStream).filter(RealtimeStream.stream_type == "websocket")
        streams = query.order_by(RealtimeStream.created_at.desc()).limit(limit).all()

        items = [
            {
                "id": stream.id,
                "name": stream.name,
                "status": stream.status,
                "created_at": stream.created_at.isoformat() if stream.created_at else "",
            }
            for stream in streams
        ]

        logger.info(f"User {current_user.username} retrieved WebSocket data: {len(items)} items")
        return {
            "items": items,
            "total": len(items),
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Failed to retrieve WebSocket data: {e}")
        raise HTTPException(status_code=500, detail=f"获取WebSocket数据失败: {str(e)}")


@router.get(
    "/event-stream",
    summary="事件流",
    response_model=RealtimeDataList,
)
async def event_stream(
    limit: int = Query(default=50, ge=1, le=200, description="返回数量限制"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """获取事件流数据"""
    try:
        query = db.query(RealtimeEvent)
        events = query.order_by(RealtimeEvent.timestamp.desc()).limit(limit).all()

        items = [
            {
                "id": f"EVT-{event.id}",
                "name": f"{event.event_type}流",
                "status": "active",
                "created_at": event.timestamp.isoformat() if event.timestamp else "",
            }
            for event in events
        ]

        logger.info(f"User {current_user.username} retrieved event stream data: {len(items)} items")
        return {
            "items": items,
            "total": len(items),
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Failed to retrieve event stream data: {e}")
        raise HTTPException(status_code=500, detail=f"获取事件流数据失败: {str(e)}")


@router.get(
    "/realtime-communication",
    summary="实时通信",
    response_model=RealtimeDataList,
)
async def realtime_communication(
    limit: int = Query(default=50, ge=1, le=200, description="返回数量限制"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """获取实时通信数据"""
    try:
        query = db.query(RealtimeStream)
        streams = query.order_by(RealtimeStream.created_at.desc()).limit(limit).all()

        items = [
            {
                "id": stream.id,
                "name": stream.name,
                "status": stream.status,
                "created_at": stream.created_at.isoformat() if stream.created_at else "",
            }
            for stream in streams
        ]

        logger.info(f"User {current_user.username} retrieved realtime communication data: {len(items)} items")
        return {
            "items": items,
            "total": len(items),
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Failed to retrieve realtime communication data: {e}")
        raise HTTPException(status_code=500, detail=f"获取实时通信数据失败: {str(e)}")
