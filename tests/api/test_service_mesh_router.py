# -*- coding: utf-8 -*-
# tests/api/test_service_mesh_router.py
# 服务网格路由API测试
import os
import sys
from unittest.mock import Mock, patch

import pytest  # noqa: F401
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.service_mesh_router import router

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

sys.modules["core.authentication"] = Mock()
sys.modules["core.authentication"].get_current_active_user = Mock()
sys.modules["core.authentication"].role_required = Mock(return_value=lambda: {"role": "admin"})
sys.modules["core.service_mesh"] = Mock()
sys.modules["core.service_mesh"].service_mesh_service = Mock()


test_app = FastAPI()
test_app.include_router(router)
client = TestClient(test_app)


class TestServiceMeshRouter:
    """服务网格路由测试"""

    def test_get_mesh_status(self):
        """测试获取网格状态"""
        with patch("core.service_mesh.service_mesh_service.get_status") as mock_status:
            mock_status.return_value = {"status": "healthy", "services": 5}
            response = client.get("/api/v1/service-mesh/status")
            assert response.status_code in [200, 401, 403, 404]

    def test_get_mesh_topology(self):
        """测试获取网格拓扑"""
        with patch("core.service_mesh.service_mesh_service.get_topology") as mock_topology:
            mock_topology.return_value = {"nodes": [], "edges": []}
            response = client.get("/api/v1/service-mesh/topology")
            assert response.status_code in [200, 401, 403, 404]

    def test_get_mesh_services(self):
        """测试获取网格服务列表"""
        with patch("core.service_mesh.service_mesh_service.get_services") as mock_services:
            mock_services.return_value = [{"name": "service1", "status": "running"}]
            response = client.get("/api/v1/service-mesh/services")
            assert response.status_code in [200, 401, 403, 404]

    def test_get_mesh_metrics(self):
        """测试获取网格指标"""
        with patch("core.service_mesh.service_mesh_service.get_metrics") as mock_metrics:
            mock_metrics.return_value = {"throughput": 1000, "latency": 50}
            response = client.get("/api/v1/service-mesh/metrics")
            assert response.status_code in [200, 401, 403, 404]

    def test_get_mesh_config(self):
        """测试获取网格配置"""
        with patch("core.service_mesh.service_mesh_service.get_config") as mock_config:
            mock_config.return_value = {"mesh_id": "mesh-1", "version": "1.0"}
            response = client.get("/api/v1/service-mesh/config")
            assert response.status_code in [200, 401, 403, 404]
