# -*- coding: utf-8 -*-
"""
Service Discovery Router Tests
服务发现路由API测试
"""

import sys
from unittest.mock import MagicMock, Mock, patch

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from api.service_discovery_router import (
    deregister_service,
    get_discovery_status,
    register_service,
)

# Mock problematic imports before importing router
sys.modules["core.service_discovery_manager"] = MagicMock()


@pytest.fixture
def client():
    """创建测试客户端"""
    app = FastAPI()
    # Create a new router without authentication dependencies
    test_router = APIRouter(prefix="/api/service-discovery", tags=["Service Discovery"])
    test_router.add_api_route("/status", get_discovery_status, methods=["GET"])
    test_router.add_api_route("/register", register_service, methods=["POST"])
    test_router.add_api_route("/deregister", deregister_service, methods=["DELETE"])
    app.include_router(test_router)
    return TestClient(app)


class TestServiceDiscoveryRouter:
    """测试服务发现路由"""

    def test_get_discovery_status(self, client):
        """测试获取服务发现状态"""
        with patch("core.service_discovery_manager.get_service_discovery_manager") as mock_manager:
            mock_instance = Mock()
            mock_instance.get_service_summary.return_value = {
                "total_services": 5,
                "healthy_services": 4,
            }
            mock_manager.return_value = mock_instance
            response = client.get("/api/service-discovery/status")
            assert response.status_code == 200

    def test_register_service(self, client):
        """测试注册服务"""
        with patch("core.service_discovery_manager.get_service_discovery_manager") as mock_manager:
            mock_instance = Mock()
            mock_instance.register_service.return_value = Mock(
                instance_id="instance1",
                service_name="Service 1",
                host="localhost",
                port=8000,
                status=Mock(value="healthy"),
            )
            mock_manager.return_value = mock_instance
            response = client.post(
                "/api/service-discovery/register",
                params={
                    "service_name": "Service 1",
                    "instance_id": "instance1",
                    "host": "localhost",
                    "port": 8000,
                },
            )
            assert response.status_code == 200

    def test_deregister_service(self, client):
        """测试注销服务"""
        with patch("core.service_discovery_manager.get_service_discovery_manager") as mock_manager:
            mock_instance = Mock()
            mock_instance.deregister_service.return_value = True
            mock_manager.return_value = mock_instance
            response = client.delete(
                "/api/service-discovery/deregister",
                params={"service_name": "Service 1", "instance_id": "instance1"},
            )
            assert response.status_code == 200

    def test_get_discovery_status_error(self, client):
        """测试获取状态失败"""
        with patch("core.service_discovery_manager.get_service_discovery_manager") as mock_manager:
            mock_manager.side_effect = Exception("Failed to get status")
            response = client.get("/api/service-discovery/status")
            assert response.status_code == 500

    def test_register_service_with_weight(self, client):
        """测试带权重的服务注册"""
        with patch("core.service_discovery_manager.get_service_discovery_manager") as mock_manager:
            mock_instance = Mock()
            mock_instance.register_service.return_value = Mock(
                instance_id="instance1",
                service_name="Service 1",
                host="localhost",
                port=8000,
                status=Mock(value="healthy"),
            )
            mock_manager.return_value = mock_instance
            response = client.post(
                "/api/service-discovery/register",
                params={
                    "service_name": "Service 1",
                    "instance_id": "instance1",
                    "host": "localhost",
                    "port": 8000,
                    "weight": 5,
                },
            )
            assert response.status_code == 200

    def test_deregister_service_not_found(self, client):
        """测试注销不存在的服务"""
        with patch("core.service_discovery_manager.get_service_discovery_manager") as mock_manager:
            mock_instance = Mock()
            mock_instance.deregister_service.side_effect = ValueError("Service not found")
            mock_manager.return_value = mock_instance
            response = client.delete(
                "/api/service-discovery/deregister",
                params={"service_name": "Service 1", "instance_id": "instance1"},
            )
            assert response.status_code == 500


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
