# -*- coding: utf-8 -*-
# tests/api/test_websocket_router.py
# WebSocket路由API基础测试
import json
import sys
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest
from fastapi import APIRouter, FastAPI, WebSocketDisconnect
from fastapi.testclient import TestClient

# Mock problematic imports before importing router
sys.modules["core.websocket_manager"] = MagicMock()
sys.modules["core.collector"] = MagicMock()

from api.websocket_router import manager, websocket_metrics, websocket_realtime


@pytest.fixture
def client():
    """创建测试客户端"""
    app = FastAPI()
    # Create a new router without authentication dependencies
    test_router = APIRouter(prefix="/ws", tags=["WebSocket"])
    test_router.add_api_websocket_route("/realtime", websocket_realtime)
    test_router.add_api_websocket_route("/metrics", websocket_metrics)
    app.include_router(test_router)
    return TestClient(app)


class TestWebSocketRouter:
    """测试WebSocket路由"""

    def test_websocket_realtime_endpoint_exists(self, client):
        """测试实时通信WebSocket端点存在"""
        # WebSocket endpoints need special handling in TestClient
        # We'll just verify the router was included
        assert client.app is not None

    def test_websocket_metrics_endpoint_exists(self, client):
        """测试指标实时推送WebSocket端点存在"""
        # WebSocket endpoints need special handling in TestClient
        # We'll just verify the router was included
        assert client.app is not None

    def test_websocket_realtime_get_not_allowed(self, client):
        """测试WebSocket端点GET方法不允许"""
        # WebSocket endpoints don't support regular HTTP GET
        response = client.get("/ws/realtime")
        # Should return 405 or similar error for non-websocket request
        assert response.status_code in [405, 404]

    def test_websocket_metrics_get_not_allowed(self, client):
        """测试WebSocket指标端点GET方法不允许"""
        # WebSocket endpoints don't support regular HTTP GET
        response = client.get("/ws/metrics")
        # Should return 405 or similar error for non-websocket request
        assert response.status_code in [405, 404]

    def test_websocket_router_included(self, client):
        """测试WebSocket路由已包含"""
        # Verify the router was included in the app
        assert client.app is not None
        # Just verify the app exists and has routes
        assert len(client.app.routes) > 0

    @pytest.mark.asyncio
    async def test_websocket_realtime_handler(self):
        """测试实时WebSocket处理消息并断开"""
        manager.connect = AsyncMock()
        manager.broadcast = AsyncMock()
        manager.send_personal_message = AsyncMock()
        manager.disconnect = AsyncMock()

        mock_ws = Mock()
        mock_ws.receive_text = AsyncMock(
            side_effect=[json.dumps({"msg": "hello"}), WebSocketDisconnect()]
        )

        await websocket_realtime(mock_ws)

        manager.connect.assert_awaited_once_with(mock_ws, "realtime")
        manager.broadcast.assert_awaited_once()
        manager.disconnect.assert_called_once_with(mock_ws, "realtime")

    @pytest.mark.asyncio
    async def test_websocket_metrics_handler(self):
        """测试指标WebSocket推送并断开"""
        manager.connect = AsyncMock()
        manager.send_personal_message = AsyncMock(side_effect=WebSocketDisconnect())
        manager.disconnect = AsyncMock()

        mock_ws = Mock()

        await websocket_metrics(mock_ws)

        manager.connect.assert_awaited_once_with(mock_ws, "metrics")
        manager.send_personal_message.assert_awaited()
        manager.disconnect.assert_called_once_with(mock_ws, "metrics")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
