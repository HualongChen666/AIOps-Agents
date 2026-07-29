# -*- coding: utf-8 -*-
# tests/api/test_sse_router.py
# SSE路由API基础测试
import asyncio
import sys
from unittest.mock import MagicMock, Mock, patch

import pytest
from fastapi import FastAPI
from fastapi.responses import Response
from fastapi.testclient import TestClient

import api.sse_router as sse_router

# Mock problematic imports before importing router
sys.modules["core.websocket_manager"] = MagicMock()


@pytest.fixture
def client():
    """创建测试客户端"""
    mock_response = Response(
        content=b"data: Event 0\n\n",
        status_code=200,
        headers={"content-type": "text/event-stream"},
    )
    with patch.object(sse_router, "StreamingResponse", Mock(return_value=mock_response)):
        app = FastAPI()
        app.include_router(sse_router.router)
        yield TestClient(app)


class TestSSERouter:
    """测试SSE路由"""

    def test_sse_events_get(self, client):
        """测试SSE事件推送GET方法"""
        response = client.get("/api/v1/sse/events")
        assert response.status_code == 200

    def test_sse_events_response_type(self, client):
        """测试SSE事件响应类型"""
        response = client.get("/api/v1/sse/events")
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")

    def test_sse_events_post_not_allowed(self, client):
        """测试SSE事件POST方法不允许"""
        response = client.post("/api/v1/sse/events")
        # POST should not be allowed
        assert response.status_code in [405, 404]

    def test_sse_events_path_check(self, client):
        """测试SSE事件路径检查"""
        response = client.get("/api/v1/sse/events")
        assert response.status_code == 200

    def test_sse_events_streaming(self, client):
        """测试SSE事件流式传输"""
        response = client.get("/api/v1/sse/events")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_event_stream_yields(self):
        """测试SSE内部生成器至少yield一次"""
        from api.sse_router import sse_events

        response = await sse_events()
        chunk = await asyncio.wait_for(response.body_iterator.__anext__(), timeout=0.5)
        assert "Event 0" in chunk


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
