# -*- coding: utf-8 -*-
"""测试WebSocket集成器模块"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest


class FakeWebSocketManager:
    """component WebSocket manager for integrator tests."""

    def __init__(self):
        self.register_message_handler = MagicMock()
        self.start_heartbeat = AsyncMock()
        self.stop_heartbeat = AsyncMock()
        self.broadcast = AsyncMock(return_value=2)


@pytest.fixture
def integrator(monkeypatch):
    monkeypatch.setattr(
        "core.enhanced_websocket_manager.get_enhanced_websocket_manager",
        lambda: FakeWebSocketManager(),
    )
    from core.websocket_integrator import WebSocketIntegrationConfig, WebSocketIntegrator

    config = WebSocketIntegrationConfig(
        enable_realtime_alerts=False,
        enable_realtime_metrics=False,
        enable_realtime_logs=False,
        enable_realtime_status=False,
    )
    return WebSocketIntegrator(config)


class TestWebSocketIntegrator:
    def test_init(self, integrator):
        assert integrator.websocket_manager is not None
        assert integrator.is_running is False

    def test_start_stop(self, integrator):
        asyncio.run(integrator.start())
        assert integrator.is_running is True
        integrator.websocket_manager.start_heartbeat.assert_awaited_once()
        integrator.websocket_manager.register_message_handler.assert_called()

        asyncio.run(integrator.stop())
        assert integrator.is_running is False
        integrator.websocket_manager.stop_heartbeat.assert_awaited_once()

    def test_stop_when_not_running(self, integrator):
        asyncio.run(integrator.stop())
        assert integrator.is_running is False

    def test_broadcast_alert(self, integrator):
        asyncio.run(integrator.start())
        count = asyncio.run(integrator.broadcast_alert({"level": "critical"}))
        assert count == 2

    def test_broadcast_metrics(self, integrator):
        asyncio.run(integrator.start())
        count = asyncio.run(integrator.broadcast_metrics({"cpu": 0.5}))
        assert count == 2

    def test_broadcast_log(self, integrator):
        asyncio.run(integrator.start())
        count = asyncio.run(integrator.broadcast_log({"message": "m"}))
        assert count == 2

    def test_broadcast_not_running(self, integrator):
        assert asyncio.run(integrator.broadcast_alert({})) == 0

    def test_register_handlers(self, integrator):
        integrator.register_alert_handler(lambda d: None)
        integrator.register_metrics_handler(lambda d: None)
        integrator.register_log_handler(lambda d: None)
        integrator.register_status_handler(lambda d: None)
        assert len(integrator.alert_handlers) == 1
        assert len(integrator.metrics_handlers) == 1
        assert len(integrator.log_handlers) == 1
        assert len(integrator.status_handlers) == 1

    def test_get_integration_status(self, integrator):
        status = integrator.get_integration_status()
        assert status["is_running"] is False
        assert status["websocket_manager_available"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
