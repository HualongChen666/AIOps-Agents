# -*- coding: utf-8 -*-
"""
WebSocket Router
WebSocket路由
"""

import json
import logging
from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from core.websocket_manager import manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["WebSocket"])


@router.websocket("/realtime")
async def websocket_realtime(websocket: WebSocket):
    """实时通信WebSocket端点"""
    await manager.connect(websocket, "realtime")
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            # 广播消息到所有连接
            await manager.broadcast({"type": "message", "data": message}, "realtime")

            # 回复发送者
            await manager.send_personal_message({"status": "received"}, websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket, "realtime")
        logger.info("WebSocket disconnected")


@router.websocket("/alerts")
async def websocket_alerts(websocket: WebSocket):
    """告警实时推送 WebSocket 端点"""
    await manager.connect(websocket, "alerts")
    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
            except json.JSONDecodeError:
                message = {"raw": data}
            await manager.send_personal_message({"type": "ack", "received": message}, websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket, "alerts")
        logger.info("Alerts WebSocket disconnected")


@router.websocket("/metrics")
async def websocket_metrics(websocket: WebSocket):
    """指标实时推送WebSocket端点"""
    await manager.connect(websocket, "metrics")
    try:
        import asyncio

        while True:
            # 推送指标数据
            from core.collector import collect_all

            metrics = collect_all()

            try:
                metrics = collect_all()
            except Exception as exc:
                await manager.send_personal_message(
                    {"type": "error", "message": str(exc)}, websocket
                )
                break

            await manager.send_personal_message(
                {"type": "metrics", "data": metrics, "timestamp": str(datetime.utcnow())}, websocket
            )

            await asyncio.sleep(5)
    except WebSocketDisconnect:
        manager.disconnect(websocket, "metrics")
        logger.info("Metrics WebSocket disconnected")
    except Exception:
        manager.disconnect(websocket, "metrics")
        logger.exception("Metrics WebSocket error")
