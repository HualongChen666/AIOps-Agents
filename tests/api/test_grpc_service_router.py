# -*- coding: utf-8 -*-
"""
Tests for gRPC Service Router API endpoints
Tests for grpc_service_router.py endpoints
"""

import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException
from datetime import datetime


class TestGrpcServiceRouterStatus:
    """Test gRPC service status endpoint"""

    @pytest.mark.asyncio
    async def test_get_grpc_status_success(self):
        """Test successful gRPC status retrieval"""
        from main import app
        from fastapi.testclient import TestClient

        mock_manager = MagicMock()
        mock_manager.get_service_summary.return_value = {
            "total_services": 3,
            "total_methods": 10,
            "services": [
                {"name": "MonitoringService", "package": "monitoring", "status": "defined"},
                {"name": "AlertService", "package": "alert", "status": "defined"},
            ],
        }

        with patch("api.grpc_service_router.get_grpc_service_manager", return_value=mock_manager):
            with TestClient(app) as client:
                response = client.get("/api/grpc-services/status")
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "success"
                assert "data" in data
                assert "timestamp" in data
                mock_manager.get_service_summary.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_grpc_status_error(self):
        """Test gRPC status retrieval with error"""
        from main import app
        from fastapi.testclient import TestClient

        mock_manager = MagicMock()
        mock_manager.get_service_summary.side_effect = Exception("Manager error")

        with patch("api.grpc_service_router.get_grpc_service_manager", return_value=mock_manager):
            with TestClient(app) as client:
                response = client.get("/api/grpc-services/status")
                assert response.status_code == 500


class TestGrpcServiceRouterCreate:
    """Test gRPC service creation endpoint"""

    @pytest.mark.asyncio
    async def test_create_grpc_service_success(self, client):
        """Test successful gRPC service creation"""
        mock_manager = MagicMock()
        mock_service = MagicMock()
        mock_service.service_name = "TestService"
        mock_service.package_name = "test"
        mock_service.status.value = "defined"
        mock_manager.create_service.return_value = mock_service

        with patch("api.grpc_service_router.get_grpc_service_manager", return_value=mock_manager):
            payload = {
                "service_name": "TestService",
                "package_name": "test",
                "methods": {
                    "methods": [
                        {
                            "method_name": "TestMethod",
                            "request_type": "TestRequest",
                            "response_type": "TestResponse",
                            "streaming_type": "unary",
                            "description": "Test method",
                        }
                    ]
                },
            }
            response = await client.post("/api/grpc-services/create", json=payload)
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["data"]["service_name"] == "TestService"
            assert data["data"]["package_name"] == "test"
            assert data["data"]["method_count"] == 1

    @pytest.mark.asyncio
    async def test_create_grpc_service_error(self, client):
        """Test gRPC service creation with error"""
        mock_manager = MagicMock()
        mock_manager.create_service.side_effect = Exception("Creation error")

        with patch("api.grpc_service_router.get_grpc_service_manager", return_value=mock_manager):
            payload = {
                "service_name": "TestService",
                "package_name": "test",
                "methods": {"methods": []},
            }
            response = await client.post("/api/grpc-services/create", json=payload)
            assert response.status_code == 500


class TestGrpcServiceRouterCreateMonitoring:
    """Test monitoring service creation endpoint"""

    @pytest.mark.asyncio
    async def test_create_monitoring_service_success(self, client):
        """Test successful monitoring service creation"""
        mock_manager = MagicMock()
        mock_service = MagicMock()
        mock_service.service_name = "MonitoringService"
        mock_service.package_name = "monitoring"
        mock_service.status.value = "defined"
        mock_manager.create_monitoring_service.return_value = mock_service

        with patch("api.grpc_service_router.get_grpc_service_manager", return_value=mock_manager):
            response = await client.post("/api/grpc-services/create/monitoring")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["data"]["service_name"] == "MonitoringService"
            mock_manager.create_monitoring_service.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_monitoring_service_error(self, client):
        """Test monitoring service creation with error"""
        mock_manager = MagicMock()
        mock_manager.create_monitoring_service.side_effect = Exception("Error")

        with patch("api.grpc_service_router.get_grpc_service_manager", return_value=mock_manager):
            response = await client.post("/api/grpc-services/create/monitoring")
            assert response.status_code == 500


class TestGrpcServiceRouterCreateAlert:
    """Test alert service creation endpoint"""

    @pytest.mark.asyncio
    async def test_create_alert_service_success(self, client):
        """Test successful alert service creation"""
        mock_manager = MagicMock()
        mock_service = MagicMock()
        mock_service.service_name = "AlertService"
        mock_service.package_name = "alert"
        mock_service.status.value = "defined"
        mock_manager.create_alert_service.return_value = mock_service

        with patch("api.grpc_service_router.get_grpc_service_manager", return_value=mock_manager):
            response = await client.post("/api/grpc-services/create/alert")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["data"]["service_name"] == "AlertService"
            mock_manager.create_alert_service.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_alert_service_error(self, client):
        """Test alert service creation with error"""
        mock_manager = MagicMock()
        mock_manager.create_alert_service.side_effect = Exception("Error")

        with patch("api.grpc_service_router.get_grpc_service_manager", return_value=mock_manager):
            response = await client.post("/api/grpc-services/create/alert")
            assert response.status_code == 500


class TestGrpcServiceRouterCreateRepair:
    """Test repair service creation endpoint"""

    @pytest.mark.asyncio
    async def test_create_repair_service_success(self, client):
        """Test successful repair service creation"""
        mock_manager = MagicMock()
        mock_service = MagicMock()
        mock_service.service_name = "RepairService"
        mock_service.package_name = "repair"
        mock_service.status.value = "defined"
        mock_manager.create_repair_service.return_value = mock_service

        with patch("api.grpc_service_router.get_grpc_service_manager", return_value=mock_manager):
            response = await client.post("/api/grpc-services/create/repair")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["data"]["service_name"] == "RepairService"
            mock_manager.create_repair_service.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_repair_service_error(self, client):
        """Test repair service creation with error"""
        mock_manager = MagicMock()
        mock_manager.create_repair_service.side_effect = Exception("Error")

        with patch("api.grpc_service_router.get_grpc_service_manager", return_value=mock_manager):
            response = await client.post("/api/grpc-services/create/repair")
            assert response.status_code == 500


class TestGrpcServiceRouterExportProto:
    """Test proto file export endpoint"""

    @pytest.mark.asyncio
    async def test_export_proto_file_success(self, client):
        """Test successful proto file export"""
        mock_manager = MagicMock()
        mock_service = MagicMock()
        mock_service.proto_content = "syntax = \"proto3\";\npackage test;"
        mock_manager.services = {"TestService": mock_service}

        with patch("api.grpc_service_router.get_grpc_service_manager", return_value=mock_manager):
            response = await client.get("/api/grpc-services/export/proto/TestService")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["data"]["service_name"] == "TestService"
            assert "proto_content" in data["data"]

    @pytest.mark.asyncio
    async def test_export_proto_file_not_found(self, client):
        """Test proto file export for non-existent service"""
        mock_manager = MagicMock()
        mock_manager.services = {}

        with patch("api.grpc_service_router.get_grpc_service_manager", return_value=mock_manager):
            response = await client.get("/api/grpc-services/export/proto/NonExistent")
            assert response.status_code == 404


class TestGrpcServiceRouterExportPython:
    """Test Python file export endpoint"""

    @pytest.mark.asyncio
    async def test_export_python_file_success(self, client):
        """Test successful Python file export"""
        mock_manager = MagicMock()
        mock_service = MagicMock()
        mock_service.python_content = "# Test service\nimport grpc"
        mock_manager.services = {"TestService": mock_service}

        with patch("api.grpc_service_router.get_grpc_service_manager", return_value=mock_manager):
            response = await client.get("/api/grpc-services/export/python/TestService")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["data"]["service_name"] == "TestService"
            assert "python_content" in data["data"]

    @pytest.mark.asyncio
    async def test_export_python_file_not_found(self, client):
        """Test Python file export for non-existent service"""
        mock_manager = MagicMock()
        mock_manager.services = {}

        with patch("api.grpc_service_router.get_grpc_service_manager", return_value=mock_manager):
            response = await client.get("/api/grpc-services/export/python/NonExistent")
            assert response.status_code == 404


class TestGrpcServiceRouterList:
    """Test list services endpoint"""

    @pytest.mark.asyncio
    async def test_list_grpc_services_success(self, client):
        """Test successful service listing"""
        mock_manager = MagicMock()
        mock_manager.get_service_summary.return_value = {
            "total_services": 2,
            "total_methods": 5,
            "services": [
                {"name": "Service1", "package": "pkg1", "status": "defined"},
                {"name": "Service2", "package": "pkg2", "status": "implemented"},
            ],
        }

        with patch("api.grpc_service_router.get_grpc_service_manager", return_value=mock_manager):
            response = await client.get("/api/grpc-services/list")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["data"]["total_services"] == 2
            assert len(data["data"]["services"]) == 2

    @pytest.mark.asyncio
    async def test_list_grpc_services_empty(self, client):
        """Test listing when no services exist"""
        mock_manager = MagicMock()
        mock_manager.get_service_summary.return_value = {
            "total_services": 0,
            "total_methods": 0,
            "services": [],
        }

        with patch("api.grpc_service_router.get_grpc_service_manager", return_value=mock_manager):
            response = await client.get("/api/grpc-services/list")
            assert response.status_code == 200
            data = response.json()
            assert data["data"]["total_services"] == 0


class TestGrpcServiceRouterGetService:
    """Test get single service endpoint"""

    @pytest.mark.asyncio
    async def test_get_grpc_service_success(self, client):
        """Test successful service retrieval"""
        mock_manager = MagicMock()
        mock_service = MagicMock()
        mock_service.service_name = "TestService"
        mock_service.package_name = "test"
        mock_service.status.value = "defined"
        mock_service.metadata = {"created_at": "2024-01-01T00:00:00Z"}
        mock_manager.services = {"TestService": mock_service}

        mock_method = MagicMock()
        mock_method.method_name = "TestMethod"
        mock_method.request_type = "TestRequest"
        mock_method.response_type = "TestResponse"
        mock_method.streaming_type = "unary"
        mock_method.description = "Test"
        mock_manager.methods = {"TestService": [mock_method]}

        with patch("api.grpc_service_router.get_grpc_service_manager", return_value=mock_manager):
            response = await client.get("/api/grpc-services/TestService")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["data"]["service_name"] == "TestService"
            assert len(data["data"]["methods"]) == 1

    @pytest.mark.asyncio
    async def test_get_grpc_service_not_found(self, client):
        """Test getting non-existent service"""
        mock_manager = MagicMock()
        mock_manager.services = {}

        with patch("api.grpc_service_router.get_grpc_service_manager", return_value=mock_manager):
            response = await client.get("/api/grpc-services/NonExistent")
            assert response.status_code == 404


class TestGrpcServiceRouterDelete:
    """Test delete service endpoint"""

    @pytest.mark.asyncio
    async def test_delete_grpc_service_success(self, client):
        """Test successful service deletion"""
        mock_manager = MagicMock()
        mock_service = MagicMock()
        mock_manager.services = {"TestService": mock_service}
        mock_manager.methods = {"TestService": []}
        mock_manager.total_services_defined = 1

        with patch("api.grpc_service_router.get_grpc_service_manager", return_value=mock_manager):
            response = await client.delete("/api/grpc-services/TestService")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["data"]["service_name"] == "TestService"
            assert "TestService" not in mock_manager.services

    @pytest.mark.asyncio
    async def test_delete_grpc_service_not_found(self, client):
        """Test deleting non-existent service"""
        mock_manager = MagicMock()
        mock_manager.services = {}

        with patch("api.grpc_service_router.get_grpc_service_manager", return_value=mock_manager):
            response = await client.delete("/api/grpc-services/NonExistent")
            assert response.status_code == 404


class TestGrpcServiceRouterUpdateStatus:
    """Test update service status endpoint"""

    @pytest.mark.asyncio
    async def test_update_service_status_success(self, client):
        """Test successful status update"""
        from core.grpc_service_manager import ServiceStatus

        mock_manager = MagicMock()
        mock_service = MagicMock()
        mock_service.status = ServiceStatus.DEFINED
        mock_manager.services = {"TestService": mock_service}

        with patch("api.grpc_service_router.get_grpc_service_manager", return_value=mock_manager):
            response = await client.post(
                "/api/grpc-services/TestService/status", params={"status": "implemented"}
            )
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["data"]["service_name"] == "TestService"

    @pytest.mark.asyncio
    async def test_update_service_status_not_found(self, client):
        """Test updating status for non-existent service"""
        mock_manager = MagicMock()
        mock_manager.services = {}

        with patch("api.grpc_service_router.get_grpc_service_manager", return_value=mock_manager):
            response = await client.post(
                "/api/grpc-services/NonExistent/status", params={"status": "implemented"}
            )
            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_service_status_invalid(self, client):
        """Test updating with invalid status"""
        mock_manager = MagicMock()
        mock_service = MagicMock()
        mock_manager.services = {"TestService": mock_service}

        with patch("api.grpc_service_router.get_grpc_service_manager", return_value=mock_manager):
            response = await client.post(
                "/api/grpc-services/TestService/status", params={"status": "invalid_status"}
            )
            assert response.status_code == 400


class TestGrpcServiceRouterIntegration:
    """Integration tests for gRPC service router"""

    @pytest.mark.asyncio
    async def test_full_service_lifecycle(self, client):
        """Test full service lifecycle: create -> get -> update -> delete"""
        mock_manager = MagicMock()
        mock_service = MagicMock()
        mock_service.service_name = "TestService"
        mock_service.package_name = "test"
        mock_service.status.value = "defined"
        mock_service.metadata = {}
        mock_service.proto_content = "proto content"
        mock_service.python_content = "python content"
        mock_manager.create_service.return_value = mock_service
        mock_manager.services = {"TestService": mock_service}
        mock_manager.methods = {"TestService": []}
        mock_manager.total_services_defined = 1

        with patch("api.grpc_service_router.get_grpc_service_manager", return_value=mock_manager):
            # Create service
            payload = {
                "service_name": "TestService",
                "package_name": "test",
                "methods": {"methods": []},
            }
            response = await client.post("/api/grpc-services/create", json=payload)
            assert response.status_code == 200

            # Get service
            response = await client.get("/api/grpc-services/TestService")
            assert response.status_code == 200

            # Update status
            response = await client.post(
                "/api/grpc-services/TestService/status", params={"status": "implemented"}
            )
            assert response.status_code == 200

            # Delete service
            response = await client.delete("/api/grpc-services/TestService")
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_batch_operations(self, client):
        """Test batch service operations"""
        import asyncio

        mock_manager = MagicMock()
        mock_service = MagicMock()
        mock_service.service_name = "TestService"
        mock_service.package_name = "test"
        mock_service.status.value = "defined"
        mock_service.metadata = {}
        mock_service.proto_content = "proto"
        mock_service.python_content = "python"
        mock_manager.create_service.return_value = mock_service
        mock_manager.services = {"TestService": mock_service}
        mock_manager.methods = {"TestService": []}
        mock_manager.total_services_defined = 1
        mock_manager.get_service_summary.return_value = {
            "total_services": 1,
            "total_methods": 0,
            "services": [],
        }

        with patch("api.grpc_service_router.get_grpc_service_manager", return_value=mock_manager):
            # Create multiple services concurrently
            tasks = [
                client.post(
                    "/api/grpc-services/create",
                    json={
                        "service_name": f"Service{i}",
                        "package_name": "test",
                        "methods": {"methods": []},
                    },
                )
                for i in range(3)
            ]
            responses = await asyncio.gather(*tasks)

            for response in responses:
                assert response.status_code == 200

            # List services
            response = await client.get("/api/grpc-services/list")
            assert response.status_code == 200
