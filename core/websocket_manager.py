# -*- coding: utf-8 -*-
"""
WebSocket Connection Manager
WebSocket连接管理器

管理WebSocket连接和消息广播。
"""

import logging
from typing import Any, Dict, Set

from fastapi import WebSocket

logger = logging.getLogger(__name__)

try:
    from core.prometheus_metrics import get_metrics_exporter
except Exception as e:
    logging.exception("Unexpected exception: %s", e)
    get_metrics_exporter = None  # type: ignore[assignment]


class ConnectionManager:
    """WebSocket连接管理器"""

    def __init__(self):
        """初始化连接管理器"""
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, channel: str = "default"):
        """
        连接WebSocket

        Args:
            websocket: WebSocket连接
            channel: 频道名称
        """
        await websocket.accept()
        if channel not in self.active_connections:
            self.active_connections[channel] = set()
        self.active_connections[channel].add(websocket)
        count = len(self.active_connections[channel])
        if callable(get_metrics_exporter):
            try:
                get_metrics_exporter().record_websocket_connections(channel, count)
            except Exception as e:
                logging.exception("Unexpected exception: %s", e)
                logging.warning("Suppressed exception", exc_info=True)
                pass
        logger.info(f"WebSocket connected to channel: {channel}, total: {count}")  # noqa: E501

    def disconnect(self, websocket: WebSocket, channel: str = "default"):
        """
        断开WebSocket连接

        Args:
            websocket: WebSocket连接
            channel: 频道名称
        """
        if channel in self.active_connections:
            self.active_connections[channel].discard(websocket)
            count = len(self.active_connections[channel])
            if callable(get_metrics_exporter):
                try:
                    get_metrics_exporter().record_websocket_connections(channel, count)
                except Exception as e:
                    logging.exception("Unexpected exception: %s", e)
                    logging.warning("Suppressed exception", exc_info=True)
                    pass
            logger.info(f"WebSocket disconnected from channel: {channel}, " f"remaining: {count}")

    async def broadcast(self, message: Any, channel: str = "default"):
        """
        广播消息到频道

        Args:
            message: 消息内容
            channel: 频道名称
        """
        if channel not in self.active_connections:
            return

        disconnected = []
        for connection in self.active_connections[channel]:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Failed to send message to connection: {e}")
                disconnected.append(connection)

        # 清理断开的连接
        for conn in disconnected:
            self.active_connections[channel].discard(conn)

    async def send_personal_message(self, message: Any, websocket: WebSocket):
        """
        发送个人消息

        Args:
            message: 消息内容
            websocket: 目标WebSocket连接
        """
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Failed to send personal message: {e}")

    def get_connection_count(self, channel: str = "default") -> int:
        """
        获取频道连接数

        Args:
            channel: 频道名称

        Returns:
            连接数
        """
        return len(self.active_connections.get(channel, set()))


# 全局连接管理器实例
manager = ConnectionManager()
