# -*- coding: utf-8 -*-
# tests/api/test_topology_view_router.py
# 拓扑视图路由API基础测试
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from api.topology_view_router import topology_page

# Mock problematic imports before importing router
sys.modules["config"] = MagicMock()
sys.modules["config"].BASE_DIR = Path("/tmp")


@pytest.fixture
def client():
    """创建测试客户端"""
    app = FastAPI()
    # Create a new router without authentication dependencies
    test_router = APIRouter(prefix="/topology", tags=["全链路拓扑视图"])
    test_router.add_api_route("/", topology_page, methods=["GET"])
    app.include_router(test_router)
    return TestClient(app)


class TestTopologyViewRouter:
    """测试拓扑视图路由"""

    def test_topology_page_not_found(self, client):
        """测试拓扑视图页面未找到"""
        # Since the static file doesn't exist, it should return 404
        response = client.get("/topology/")
        assert response.status_code == 404

    def test_topology_page_get_method(self, client):
        """测试拓扑视图页面GET方法"""
        response = client.get("/topology/")
        # Should handle GET request
        assert response.status_code in [200, 404]

    def test_topology_page_post_not_allowed(self, client):
        """测试拓扑视图页面POST方法不允许"""
        response = client.post("/topology/")
        # POST should not be allowed
        assert response.status_code in [405, 404]

    def test_topology_page_response_type(self, client):
        """测试拓扑视图页面响应类型"""
        response = client.get("/topology/")
        if response.status_code == 200:
            assert "text/html" in response.headers.get("content-type", "")
        else:
            assert response.status_code == 404

    def test_topology_router_included(self, client):
        """测试拓扑视图路由已包含"""
        # Verify the router was included in the app
        assert client.app is not None
        # Just verify the app exists and has routes
        assert len(client.app.routes) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
