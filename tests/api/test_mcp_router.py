# -*- coding: utf-8 -*-
"""
MCP Router Tests
覆盖 api/mcp_router 和 core/mcp_server 的基础成功与异常分支。
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.mcp_router import router


@pytest.fixture
def client():
    """创建测试客户端"""
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


class TestMcpRouter:
    """测试 MCP 路由"""

    @patch("core.mcp_server.get_host_health", new_callable=AsyncMock)
    def test_get_host_health_success(self, mock_host, client):
        """测试获取主机健康状态"""
        mock_host.return_value = {"status": "healthy"}
        response = client.post("/api/mcp/get_host_health", json={"host_id": "host-1"})
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    @patch("core.mcp_server.get_host_health", new_callable=AsyncMock)
    def test_get_host_health_error(self, mock_host, client):
        """测试获取主机健康状态异常"""
        mock_host.side_effect = RuntimeError("host error")
        response = client.post("/api/mcp/get_host_health", json={"host_id": "host-1"})
        assert response.status_code == 500

    @patch("core.mcp_server.trigger_repair_with_hitl", new_callable=AsyncMock)
    def test_trigger_repair_success(self, mock_repair, client):
        """测试触发修复"""
        mock_repair.return_value = {"status": "triggered"}
        response = client.post(
            "/api/mcp/trigger_repair_with_hitl",
            json={"alert_id": "a1", "user": "admin", "comment": ""},
        )
        assert response.status_code == 200

    @patch("core.mcp_server.trigger_repair_with_hitl", new_callable=AsyncMock)
    def test_trigger_repair_error(self, mock_repair, client):
        """测试触发修复异常"""
        mock_repair.side_effect = RuntimeError("repair error")
        response = client.post(
            "/api/mcp/trigger_repair_with_hitl",
            json={"alert_id": "a1", "user": "admin"},
        )
        assert response.status_code == 500

    @patch("core.mcp_server.search_incident_history", new_callable=AsyncMock)
    def test_search_incident_history_success(self, mock_search, client):
        """测试搜索历史事件"""
        mock_search.return_value = [{"id": "i1"}]
        response = client.post(
            "/api/mcp/search_incident_history", json={"query": "cpu", "limit": 5}
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    @patch("core.mcp_server.search_incident_history", new_callable=AsyncMock)
    def test_search_incident_history_error(self, mock_search, client):
        """测试搜索历史事件异常"""
        mock_search.side_effect = RuntimeError("search error")
        response = client.post("/api/mcp/search_incident_history", json={"query": "cpu"})
        assert response.status_code == 500

    @patch("core.mcp_server.get_metrics", new_callable=AsyncMock)
    def test_get_metrics_success(self, mock_metrics, client):
        """测试获取指标"""
        mock_metrics.return_value = {"cpu": 10}
        response = client.post(
            "/api/mcp/get_metrics",
            json={"host_id": "host-1", "metrics": ["cpu"]},
        )
        assert response.status_code == 200

    @patch("core.mcp_server.get_metrics", new_callable=AsyncMock)
    def test_get_metrics_error(self, mock_metrics, client):
        """测试获取指标异常"""
        mock_metrics.side_effect = RuntimeError("metrics error")
        response = client.post(
            "/api/mcp/get_metrics",
            json={"host_id": "host-1", "metrics": ["cpu"]},
        )
        assert response.status_code == 500

    @patch("core.mcp_server.approve_repair", new_callable=AsyncMock)
    def test_approve_repair_success(self, mock_approve, client):
        """测试审批修复"""
        mock_approve.return_value = {"approved": True}
        response = client.post(
            "/api/mcp/approve_repair",
            json={"repair_id": "r1", "approved": True},
        )
        assert response.status_code == 200

    @patch("core.mcp_server.approve_repair", new_callable=AsyncMock)
    def test_approve_repair_error(self, mock_approve, client):
        """测试审批修复异常"""
        mock_approve.side_effect = RuntimeError("approve error")
        response = client.post(
            "/api/mcp/approve_repair",
            json={"repair_id": "r1", "approved": False},
        )
        assert response.status_code == 500


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
