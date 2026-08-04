# -*- coding: utf-8 -*-
# tests/api/test_service_mesh_router.py
# 服务网格路由API测试
import os
import sys
from unittest.mock import Mock, patch

import pytest  # noqa: F401
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

sys.modules["core.authentication"] = Mock()
sys.modules["core.authentication"].get_current_active_user = Mock()
sys.modules["core.authentication"].role_required = Mock(return_value=lambda: {"role": "admin"})
sys.modules["core.service_mesh_manager"] = Mock()
sys.modules["core.service_mesh_manager"].get_service_mesh_manager = Mock()

from api.service_mesh_router import router  # isort: skip


test_app = FastAPI()
test_app.include_router(router)
client = TestClient(test_app)


class TestServiceMeshRouter:
    """服务网格路由测试"""

    def test_get_mesh_status_success(self):
        """测试获取网格状态成功"""
        mock_manager = Mock()
        mock_manager.generate_service_mesh_summary.return_value = {
            "status": "healthy",
            "services": 5,
        }
        with patch("core.service_mesh_manager.get_service_mesh_manager") as mock_get_manager:
            mock_get_manager.return_value = mock_manager
            response = client.get("/api/service-mesh/status")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "data" in data
            assert "timestamp" in data

    def test_get_mesh_status_exception(self):
        """测试获取网格状态异常"""
        with patch("core.service_mesh_manager.get_service_mesh_manager") as mock_get_manager:
            mock_get_manager.side_effect = RuntimeError("Service unavailable")
            response = client.get("/api/service-mesh/status")
            assert response.status_code == 500

    def test_generate_istio_control_plane_success(self):
        """测试生成Istio控制平面配置成功"""
        mock_manager = Mock()
        mock_config = Mock()
        mock_config.mesh_id = "mesh-1"
        mock_config.control_plane_config = {"config": "data"}
        mock_config.auto_injection_enabled = True
        mock_manager.generate_istio_control_plane_config.return_value = mock_config
        with patch("core.service_mesh_manager.get_service_mesh_manager") as mock_get_manager:
            mock_get_manager.return_value = mock_manager
            response = client.post(
                "/api/service-mesh/istio/control-plane?mesh_id=mesh-1&namespace=istio-system&profile=default"
            )
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "data" in data

    def test_generate_istio_control_plane_exception(self):
        """测试生成Istio控制平面配置异常"""
        with patch("core.service_mesh_manager.get_service_mesh_manager") as mock_get_manager:
            mock_get_manager.side_effect = RuntimeError("Config generation failed")
            response = client.post(
                "/api/service-mesh/istio/control-plane?mesh_id=mesh-1&namespace=istio-system&profile=default"
            )
            assert response.status_code == 500

    def test_generate_auto_injection_success(self):
        """测试生成自动注入配置成功"""
        mock_manager = Mock()
        mock_config = {"namespace": "default", "enabled": True}
        mock_manager.generate_auto_injection_config.return_value = mock_config
        with patch("core.service_mesh_manager.get_service_mesh_manager") as mock_get_manager:
            mock_get_manager.return_value = mock_manager
            response = client.post(
                "/api/service-mesh/istio/auto-injection?namespace=default&enabled=true"
            )
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "data" in data

    def test_generate_auto_injection_exception(self):
        """测试生成自动注入配置异常"""
        with patch("core.service_mesh_manager.get_service_mesh_manager") as mock_get_manager:
            mock_get_manager.side_effect = RuntimeError("Auto-injection failed")
            response = client.post(
                "/api/service-mesh/istio/auto-injection?namespace=default&enabled=true"
            )
            assert response.status_code == 500

    def test_generate_virtual_service_success(self):
        """测试生成虚拟服务配置成功"""
        mock_manager = Mock()
        mock_config = Mock()
        mock_config.service_name = "test-service"
        mock_config.routing_rules = [{"destination": "v1"}]
        mock_manager.generate_virtual_service_config.return_value = mock_config
        with patch("core.service_mesh_manager.get_service_mesh_manager") as mock_get_manager:
            mock_get_manager.return_value = mock_manager
            response = client.post(
                "/api/service-mesh/istio/virtual-service?service_name=test-service&namespace=default",
                json={"destination": "v1"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "data" in data

    def test_generate_virtual_service_exception(self):
        """测试生成虚拟服务配置异常"""
        with patch("core.service_mesh_manager.get_service_mesh_manager") as mock_get_manager:
            mock_get_manager.side_effect = RuntimeError("Virtual service generation failed")
            response = client.post(
                "/api/service-mesh/istio/virtual-service?service_name=test-service&namespace=default",
                json={"destination": "v1"},
            )
            assert response.status_code == 500

    def test_generate_mtls_config_success(self):
        """测试生成mTLS配置成功"""
        mock_manager = Mock()
        mock_config = Mock()
        mock_config.mesh_id = "mesh-1"
        mock_config.mtls_enabled = True
        mock_config.authentication_policies = {"policy": "strict"}
        mock_manager.generate_mtls_config.return_value = mock_config
        with patch("core.service_mesh_manager.get_service_mesh_manager") as mock_get_manager:
            mock_get_manager.return_value = mock_manager
            response = client.post(
                "/api/service-mesh/istio/mtls?mesh_id=mesh-1&namespace=istio-system&strict_mode=true"
            )
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "data" in data

    def test_generate_mtls_config_exception(self):
        """测试生成mTLS配置异常"""
        with patch("core.service_mesh_manager.get_service_mesh_manager") as mock_get_manager:
            mock_get_manager.side_effect = RuntimeError("mTLS config generation failed")
            response = client.post(
                "/api/service-mesh/istio/mtls?mesh_id=mesh-1&namespace=istio-system&strict_mode=true"
            )
            assert response.status_code == 500

