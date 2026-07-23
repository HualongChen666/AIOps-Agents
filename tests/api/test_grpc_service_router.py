# -*- coding: utf-8 -*-
"""
gRPC Service Router Tests
gRPC服务管理路由API基础测试
"""

import sys
from unittest.mock import MagicMock, Mock, patch

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

# Mock problematic imports before importing router
sys.modules["core.grpc_service_manager"] = MagicMock()

from api.grpc_service_router import (
    create_alert_service,
    create_grpc_service,
    create_monitoring_service,
    export_proto_file,
    get_grpc_status,
)


@pytest.fixture
def client():
    """创建测试客户端"""
    app = FastAPI()
    # Create a new router without authentication dependencies
    test_router = APIRouter(prefix="/api/grpc-services", tags=["gRPC Services"])
    test_router.add_api_route("/status", get_grpc_status, methods=["GET"])
    test_router.add_api_route("/create", create_grpc_service, methods=["POST"])
    test_router.add_api_route("/create/monitoring", create_monitoring_service, methods=["POST"])
    test_router.add_api_route("/create/alert", create_alert_service, methods=["POST"])
    test_router.add_api_route("/export/proto/{service_name}", export_proto_file, methods=["GET"])
    app.include_router(test_router)
    return TestClient(app)


class TestGRPCServiceRouter:
    """测试gRPC服务管理路由"""

    def test_get_grpc_status(self, client):
        """测试获取gRPC服务状态"""
        with patch("core.grpc_service_manager.get_grpc_service_manager") as mock_manager:
            mock_instance = Mock()
            mock_instance.get_service_summary.return_value = {
                "total_services": 5,
                "active_services": 4,
            }
            mock_manager.return_value = mock_instance

            response = client.get("/api/grpc-services/status")
            assert response.status_code == 200
            data = response.json()
            assert "status" in data

    def test_get_grpc_status_error(self, client):
        """测试获取gRPC服务状态失败"""
        with patch("core.grpc_service_manager.get_grpc_service_manager") as mock_manager:
            mock_manager.side_effect = Exception("gRPC service error")

            response = client.get("/api/grpc-services/status")
            assert response.status_code == 500

    def test_create_grpc_service(self, client):
        """测试创建gRPC服务"""
        with (
            patch("core.grpc_service_manager.get_grpc_service_manager") as mock_manager,
            patch("core.grpc_service_manager.GRPCMethod") as mock_method,
        ):
            mock_instance = Mock()
            mock_service = Mock()
            mock_service.service_name = "UserService"
            mock_service.package_name = "user"
            mock_service.status.value = "active"
            mock_instance.create_service.return_value = mock_service
            mock_manager.return_value = mock_instance
            mock_method.return_value = Mock()

            response = client.post(
                "/api/grpc-services/create?service_name=UserService&package_name=user",
                json={
                    "methods": [
                        {
                            "method_name": "GetUser",
                            "request_type": "UserRequest",
                            "response_type": "UserResponse",
                        }
                    ]
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"

    def test_create_monitoring_service(self, client):
        """测试创建监控服务"""
        with patch("core.grpc_service_manager.get_grpc_service_manager") as mock_manager:
            mock_instance = Mock()
            mock_service = Mock()
            mock_service.service_name = "MonitoringService"
            mock_service.package_name = "monitoring"
            mock_service.status.value = "active"
            mock_instance.create_monitoring_service.return_value = mock_service
            mock_manager.return_value = mock_instance

            response = client.post("/api/grpc-services/create/monitoring")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"

    def test_create_alert_service(self, client):
        """测试创建告警服务"""
        with patch("core.grpc_service_manager.get_grpc_service_manager") as mock_manager:
            mock_instance = Mock()
            mock_service = Mock()
            mock_service.service_name = "AlertService"
            mock_service.package_name = "alert"
            mock_service.status.value = "active"
            mock_instance.create_alert_service.return_value = mock_service
            mock_manager.return_value = mock_instance

            response = client.post("/api/grpc-services/create/alert")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"

    def test_export_proto_file(self, client):
        """测试导出proto文件"""
        with patch("core.grpc_service_manager.get_grpc_service_manager") as mock_manager:
            mock_instance = Mock()
            mock_service = Mock()
            mock_service.proto_content = 'syntax = "proto3";'
            mock_instance.services = {"UserService": mock_service}
            mock_manager.return_value = mock_instance

            response = client.get("/api/grpc-services/export/proto/UserService")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
