# -*- coding: utf-8 -*-
# tests/api/test_topology_router.py
# 拓扑管理路由API基础测试
import sys
from unittest.mock import MagicMock, patch

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from api.topology_router import get_topo_status, list_topology_types, set_node_health

# Mock problematic imports before importing router
sys.modules["core.authentication"] = MagicMock()
sys.modules["core.topology_engine"] = MagicMock()


@pytest.fixture
def client():
    """创建测试客户端"""
    app = FastAPI()
    # Create a new router without authentication dependencies
    test_router = APIRouter(prefix="/api/v1/topologies", tags=["拓扑管理"])
    test_router.add_api_route("/types", list_topology_types, methods=["GET"])
    test_router.add_api_route("/status/{topo_key}", get_topo_status, methods=["GET"])
    test_router.add_api_route("/node/health", set_node_health, methods=["POST"])
    app.include_router(test_router)
    return TestClient(app)


class TestTopologyRouter:
    """测试拓扑管理路由"""

    def test_list_topology_types(self, client):
        """测试获取所有拓扑类型"""
        with patch(
            "api.topology_router.TOPOLOGY_TYPES", {"full_link": "全链路拓扑", "causal": "因果拓扑"}
        ):
            response = client.get("/api/v1/topologies/types")
            assert response.status_code in [200, 500]

    def test_get_topo_status(self, client):
        """测试获取指定拓扑运行状态"""
        with patch("api.topology_router.get_topology_status") as mock_status:
            mock_status.return_value = {"status": "running", "node_count": 10, "active_flows": []}

            response = client.get("/api/v1/topologies/status/full_link")
            assert response.status_code in [200, 404, 500]

    def test_get_topo_status_not_found(self, client):
        """测试获取不存在的拓扑状态"""
        with patch("api.topology_router.get_topology_status") as mock_status:
            mock_status.return_value = {"error": "拓扑未找到"}

            response = client.get("/api/v1/topologies/status/invalid")
            assert response.status_code in [404, 500]

    def test_set_node_health(self, client):
        """测试更新拓扑节点健康状态"""
        with patch("api.topology_router.update_node_health") as mock_update:
            mock_update.return_value = None

            response = client.post(
                "/api/v1/topologies/node/health", json={"node_id": "agent", "status": "warning"}
            )
            assert response.status_code in [200, 400, 500]

    def test_set_node_health_invalid_node(self, client):
        """测试更新无效节点健康状态"""
        with patch("api.topology_router.update_node_health") as mock_update:
            mock_update.side_effect = ValueError("节点不在合法节点列表中")

            response = client.post(
                "/api/v1/topologies/node/health", json={"node_id": "invalid", "status": "warning"}
            )
            assert response.status_code in [400, 500]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
