# -*- coding: utf-8 -*-
"""
Dashboard Router Tests
仪表盘路由API基础测试
"""

import sys
from unittest.mock import MagicMock, Mock

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from api.dashboard_router import summary

# Mock problematic imports before importing router
sys.modules["core.authentication"] = MagicMock()
sys.modules["core.authentication"].role_required = Mock(return_value=lambda: {"role": "user"})


@pytest.fixture
def client():
    """创建测试客户端（绕过认证）"""
    app = FastAPI()
    # Create a new router without authentication dependencies
    test_router = APIRouter(prefix="/dashboard", tags=["dashboard"])
    test_router.add_api_route("/summary", summary, methods=["GET"])
    app.include_router(test_router)
    return TestClient(app)


class TestDashboardRouter:
    """测试仪表盘路由"""

    def test_summary_success(self, client):
        """测试成功获取仪表盘摘要"""
        response = client.get("/dashboard/summary")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    def test_summary_response_structure(self, client):
        """测试响应结构"""
        response = client.get("/dashboard/summary")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "message" in data

    def test_summary_status_field(self, client):
        """测试status字段值"""
        response = client.get("/dashboard/summary")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert isinstance(data["status"], str)

    def test_summary_message_field(self, client):
        """测试message字段值"""
        response = client.get("/dashboard/summary")
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Dashboard default_value"
        assert isinstance(data["message"], str)

    def test_summary_content_type(self, client):
        """测试响应内容类型"""
        response = client.get("/dashboard/summary")
        assert response.status_code == 200
        assert "application/json" in response.headers.get("content-type", "")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
