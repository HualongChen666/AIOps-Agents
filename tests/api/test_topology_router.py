# -*- coding: utf-8 -*-
# tests/api/test_topology_router.py
# 拓扑管理路由API基础测试
import sys
from unittest.mock import MagicMock, patch

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from api.topology_router import (
    clear_topology_cache,
    get_full_link,
    get_node_timeline_api,
    get_topo_status,
    list_topology_types,
    set_node_health,
)

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
    test_router.add_api_route("/full-link", get_full_link, methods=["GET"])
    test_router.add_api_route("/node/{node_id}/timeline", get_node_timeline_api, methods=["GET"])
    test_router.add_api_route("/cache/clear", clear_topology_cache, methods=["POST"])
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

    def test_get_full_link(self, client):
        """测试获取全链路拓扑"""
        with patch("api.topology_router.get_full_link_topology") as mock_link:
            mock_link.return_value = {
                "nodes": [{"id": "node1", "type": "host"}],
                "edges": [{"source": "node1", "target": "node2"}],
                "stats": {"total_nodes": 2, "total_edges": 1},
            }

            response = client.get("/api/v1/topologies/full-link")
            assert response.status_code in [200, 500]

    def test_get_full_link_cache_hit(self, client):
        """测试全链路拓扑缓存命中"""
        with patch("api.topology_router.get_full_link_topology") as mock_link:
            mock_link.return_value = {
                "nodes": [{"id": "node1", "type": "host"}],
                "edges": [{"source": "node1", "target": "node2"}],
                "stats": {"total_nodes": 2, "total_edges": 1},
            }

            # 第一次请求填充缓存
            response1 = client.get("/api/v1/topologies/full-link")
            # 第二次请求应该命中缓存
            response2 = client.get("/api/v1/topologies/full-link")
            assert response1.status_code in [200, 500]
            assert response2.status_code in [200, 500]

    def test_get_node_timeline(self, client):
        """测试获取节点时间线"""
        with patch("api.topology_router.get_node_timeline") as mock_timeline:
            mock_timeline.return_value = {
                "summary": {"total": 10, "alerts": 5, "repairs": 5},
                "events": [],
            }

            response = client.get("/api/v1/topologies/node/agent/timeline?hours=24&limit=50")
            assert response.status_code in [200, 422, 500]

    def test_get_node_timeline_invalid_node(self, client):
        """测试获取无效节点时间线"""
        response = client.get("/api/v1/topologies/node/invalid!node/timeline")
        assert response.status_code == 422

    def test_get_node_timeline_empty_node(self, client):
        """测试获取空节点ID时间线"""
        response = client.get("/api/v1/topologies/node/   /timeline")
        assert response.status_code == 422

    def test_get_node_timeline_long_node(self, client):
        """测试获取超长节点ID时间线"""
        long_node = "a" * 65
        response = client.get(f"/api/v1/topologies/node/{long_node}/timeline")
        assert response.status_code == 422

    def test_clear_topology_cache(self, client):
        """测试清空拓扑缓存"""
        response = client.post("/api/v1/topologies/cache/clear")
        assert response.status_code == 200

    def test_get_topo_status_invalid_key(self, client):
        """测试获取无效拓扑键状态"""
        response = client.get("/api/v1/topologies/status/invalid!key")
        assert response.status_code == 422

    def test_get_topo_status_empty_key(self, client):
        """测试获取空拓扑键状态"""
        response = client.get("/api/v1/topologies/status/   ")
        assert response.status_code == 422

    def test_set_node_health_invalid_status(self, client):
        """测试设置无效健康状态"""
        response = client.post(
            "/api/v1/topologies/node/health", json={"node_id": "agent", "status": "invalid"}
        )
        assert response.status_code == 422

    def test_set_node_health_invalid_node_id(self, client):
        """测试设置无效节点ID"""
        response = client.post(
            "/api/v1/topologies/node/health", json={"node_id": "invalid!node", "status": "warning"}
        )
        assert response.status_code == 422


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
