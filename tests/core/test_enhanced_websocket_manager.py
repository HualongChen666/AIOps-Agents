# -*- coding: utf-8 -*-
"""测试增强WebSocket管理器模块"""

import asyncio
from unittest.mock import AsyncMock

import pytest


@pytest.fixture
def manager():
    from core.enhanced_websocket_manager import EnhancedWebSocketManager

    return EnhancedWebSocketManager()


@pytest.fixture
def websocket():
    ws = AsyncMock()
    ws.accept = AsyncMock()
    ws.send_text = AsyncMock()
    return ws


class TestMessageAndClient:
    def test_websocket_message_to_dict_and_json(self):
        from core.enhanced_websocket_manager import MessageType, WebSocketMessage

        msg = WebSocketMessage(message_type=MessageType.ALERT, data={"k": "v"}, channel="c")
        data = msg.to_dict()
        assert data["message_type"] == "alert"
        assert data["channel"] == "c"
        assert isinstance(msg.to_json(), str)

    def test_client_info_defaults(self):
        from core.enhanced_websocket_manager import ClientInfo

        client = ClientInfo(client_id="1")
        assert client.channels == set()
        assert client.state.value == "connected"


class TestConnectionManagement:
    def test_connect_and_disconnect(self, manager, websocket):
        asyncio.run(manager.connect(websocket, ["alerts"], {"ip": "127.0.0.1"}))
        assert len(manager.client_info) == 1
        assert "alerts" in manager.active_connections

        asyncio.run(manager.disconnect(websocket))
        assert len(manager.client_info) == 0

    def test_connect_max_connections(self, manager, websocket):
        manager.max_connections = 0
        with pytest.raises(Exception):
            asyncio.run(manager.connect(websocket))

    def test_subscribe_unsubscribe(self, manager, websocket):
        asyncio.run(manager.connect(websocket, ["alerts"]))
        assert asyncio.run(manager.subscribe_channel(websocket, "metrics")) is True
        assert asyncio.run(manager.subscribe_channel(websocket, "metrics")) is False
        assert asyncio.run(manager.unsubscribe_channel(websocket, "metrics")) is True
        assert asyncio.run(manager.unsubscribe_channel(websocket, "unknown")) is False


class TestMessaging:
    def test_send_personal_message(self, manager, websocket):
        asyncio.run(manager.connect(websocket))
        from core.enhanced_websocket_manager import MessageType, WebSocketMessage

        msg = WebSocketMessage(message_type=MessageType.STATUS, data={"ok": True})
        assert asyncio.run(manager.send_personal_message(websocket, msg)) is True
        assert manager.message_count == 2

    def test_send_personal_message_failure(self, manager, websocket):
        websocket.send_text = AsyncMock(side_effect=RuntimeError("fail"))
        asyncio.run(manager.connect(websocket))
        from core.enhanced_websocket_manager import MessageType, WebSocketMessage

        msg = WebSocketMessage(message_type=MessageType.STATUS, data={})
        assert asyncio.run(manager.send_personal_message(websocket, msg)) is False

    def test_broadcast(self, manager, websocket):
        asyncio.run(manager.connect(websocket, ["alerts"]))
        from core.enhanced_websocket_manager import MessageType, WebSocketMessage

        msg = WebSocketMessage(message_type=MessageType.ALERT, data={"x": 1})
        assert asyncio.run(manager.broadcast(msg, "alerts")) == 1

    def test_broadcast_no_channel(self, manager):
        from core.enhanced_websocket_manager import MessageType, WebSocketMessage

        msg = WebSocketMessage(message_type=MessageType.ALERT, data={})
        assert asyncio.run(manager.broadcast(msg, "missing")) == 0

    def test_broadcast_to_channels(self, manager, websocket):
        asyncio.run(manager.connect(websocket, ["a", "b"]))
        from core.enhanced_websocket_manager import MessageType, WebSocketMessage

        msg = WebSocketMessage(message_type=MessageType.METRIC, data={})
        results = asyncio.run(manager.broadcast_to_channels(msg, ["a", "b"]))
        assert results["a"] == 1
        assert results["b"] == 1


class TestHandlersAndStatistics:
    def test_handle_message(self, manager, websocket):
        calls = []

        def handler(ws, msg):
            calls.append(msg.data)

        from core.enhanced_websocket_manager import MessageType

        manager.register_message_handler(MessageType.ALERT, handler)
        asyncio.run(manager.connect(websocket))
        asyncio.run(manager.handle_message(websocket, {"message_type": "alert", "data": {"x": 1}}))
        assert calls == [{"x": 1}]

    def test_emit_event(self, manager):
        calls = []
        manager.register_event_handler("custom", lambda data: calls.append(data))
        asyncio.run(manager.emit_event("custom", {"x": 2}))
        assert calls == [{"x": 2}]

    def test_statistics_and_channel_info(self, manager, websocket):
        asyncio.run(manager.connect(websocket, ["alerts"]))
        stats = manager.get_statistics()
        assert stats["connection_count"] == 1
        assert stats["active_channels"] == 1

        info = manager.get_channel_info("alerts")
        assert info["active_connections"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
