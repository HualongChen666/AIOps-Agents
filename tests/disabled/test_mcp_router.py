# -*- coding: utf-8 -*-
"""MCP Router Tests
MCP多通道协议路由API基础测试
"""

import sys
from unittest.mock import MagicMock, patch

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

# Mock problematic imports before importing router
sys.modules["core.mcp_tools"] = MagicMock()

from core.mcp_server import (
    api_approve_repair,
    api_get_host_health,
    api_get_metrics,
    api_search_incident,
    api_trigger_repair,
)


@pytest.fixture
def client():
    """创建测试客户端"""
    app = FastAPI()
    # Create a new router without authentication dependencies
    test_router = APIRouter(prefix="/mcp", tags=["MCP"])
    test_router.add_api_route("/get_host_health", api_get_host_health, methods=["POST"])
    test_router.add_api_route("/trigger_repair_with_hitl", api_trigger_repair, methods=["POST"])
    test_router.add_api_route("/search_incident_history", api_search_incident, methods=["POST"])
    test_router.add_api_route("/get_metrics", api_get_metrics, methods=["POST"])
    test_router.add_api_route("/approve_repair", api_approve_repair, methods=["POST"])
    app.include_router(test_router)
    return TestClient(app)


class TestMCPRouter:
    """测试MCP路由"""

    def test_get_host_health(self, client):
        """测试获取主机健康状态"""
        with patch("core.mcp_server.get_host_health") as mock_health:

            async def mock_func(host_id):
                return {"host_id": host_id, "status": "healthy"}

            mock_health.side_effect = mock_func
            response = client.post("/mcp/get_host_health", json={"host_id": "host-001"})
            assert response.status_code == 200
            data = response.json()
            assert data["host_id"] == "host-001"

    def test_trigger_repair_with_hitl(self, client):
        """测试触发带HITL的修复任务"""
        with patch("core.mcp_server.trigger_repair_with_hitl") as mock_repair:

            async def mock_func(alert_id, user, comment):
                return {"alert_id": alert_id, "status": "triggered", "user": user}

            mock_repair.side_effect = mock_func
            response = client.post(
                "/mcp/trigger_repair_with_hitl", json={"alert_id": "alert-001", "user": "admin"}
            )
            assert response.status_code == 200
            data = response.json()
            assert data["alert_id"] == "alert-001"

    def test_search_incident_history(self, client):
        """测试搜索历史告警记录"""
        with patch("core.mcp_server.search_incident_history") as mock_search:

            async def mock_func(query, limit):
                return [{"id": 1, "query": query}]

            mock_search.side_effect = mock_func
            response = client.post(
                "/mcp/search_incident_history", json={"query": "error", "limit": 10}
            )
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)

    def test_get_metrics(self, client):
        """测试获取多个指标"""
        with patch("core.mcp_server.get_metrics") as mock_metrics:

            async def mock_func(host_id, metrics):
                return {"host_id": host_id, "cpu": 45.2, "memory": 68.3}

            mock_metrics.side_effect = mock_func
            response = client.post(
                "/mcp/get_metrics", json={"host_id": "host-001", "metrics": ["cpu", "memory"]}
            )
            assert response.status_code == 200
            data = response.json()
            assert "cpu" in data

    def test_approve_repair(self, client):
        """测试批准修复"""
        with patch("core.mcp_server.approve_repair") as mock_approve:

            async def mock_func(repair_id, approved, comment):
                return {"repair_id": repair_id, "approved": approved}

            mock_approve.side_effect = mock_func
            response = client.post(
                "/mcp/approve_repair", json={"repair_id": "repair-001", "approved": True}
            )
            assert response.status_code == 200
            data = response.json()
            assert data["approved"] is True

    def test_get_host_health_error(self, client):
        """测试获取主机健康状态失败"""
        with patch("core.mcp_server.get_host_health") as mock_health:

            async def mock_func(host_id):
                raise Exception("Host not found")

            mock_health.side_effect = mock_func
            response = client.post("/mcp/get_host_health", json={"host_id": "host-001"})
            assert response.status_code == 500


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
