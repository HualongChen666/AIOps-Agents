# -*- coding: utf-8 -*-
"""
Comprehensive test suite for Infrastructure Advanced API Router
Tests all endpoints with various scenarios including success, error cases, validation, and mocking
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from fastapi import HTTPException
from fastapi.testclient import TestClient

from api.infrastructure_advanced_router import (
    router,
    InfrastructureResource,
    InfrastructureResourceCreate,
    InfrastructureResourceUpdate,
    TopologyNode,
    TopologyEdge,
    InfrastructureTopology,
    HealthCheck,
    InfrastructureHealth,
    CapacityMetrics,
    InfrastructureCapacity,
    ProvisioningRequest,
    ProvisioningResponse,
    _resources,
    _provisioning_tasks
)


@pytest.fixture
def client():
    """Create a test client for the infrastructure router"""
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


@pytest.fixture(autouse=True)
def clear_storage():
    """Clear in-memory storage before each test"""
    _resources.clear()
    _provisioning_tasks.clear()
    yield


class TestInfrastructureResourceEndpoints:
    """Test infrastructure resource endpoints"""

    def test_get_resources_success(self, client):
        """Test GET /resources - successful retrieval"""
        resource_id = "res-1"
        _resources[resource_id] = {
            "resource_id": resource_id,
            "name": "web-server-01",
            "resource_type": "virtual_machine",
            "provider": "aws",
            "region": "us-east-1",
            "status": "running",
            "cpu_cores": 4,
            "memory_gb": 8,
            "disk_gb": 100,
            "tags": {"environment": "production"},
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }

        response = client.get("/api/v1/infrastructure/resources")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_get_resources_with_type_filter(self, client):
        """Test GET /resources with resource_type filter"""
        _resources["res-1"] = {
            "resource_id": "res-1",
            "name": "web-server-01",
            "resource_type": "virtual_machine",
            "provider": "aws",
            "region": "us-east-1",
            "status": "running",
            "cpu_cores": 4,
            "memory_gb": 8,
            "disk_gb": 100,
            "tags": {},
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        _resources["res-2"] = {
            "resource_id": "res-2",
            "name": "db-server-01",
            "resource_type": "database",
            "provider": "aws",
            "region": "us-east-1",
            "status": "running",
            "cpu_cores": 8,
            "memory_gb": 32,
            "disk_gb": 500,
            "tags": {},
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }

        response = client.get("/api/v1/infrastructure/resources?resource_type=virtual_machine")
        assert response.status_code == 200
        data = response.json()
        assert all(res["resource_type"] == "virtual_machine" for res in data)

    def test_get_resources_with_provider_filter(self, client):
        """Test GET /resources with provider filter"""
        _resources["res-1"] = {
            "resource_id": "res-1",
            "name": "web-server-01",
            "resource_type": "virtual_machine",
            "provider": "aws",
            "region": "us-east-1",
            "status": "running",
            "cpu_cores": 4,
            "memory_gb": 8,
            "disk_gb": 100,
            "tags": {},
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        _resources["res-2"] = {
            "resource_id": "res-2",
            "name": "web-server-02",
            "resource_type": "virtual_machine",
            "provider": "gcp",
            "region": "us-central1",
            "status": "running",
            "cpu_cores": 4,
            "memory_gb": 8,
            "disk_gb": 100,
            "tags": {},
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }

        response = client.get("/api/v1/infrastructure/resources?provider=aws")
        assert response.status_code == 200
        data = response.json()
        assert all(res["provider"] == "aws" for res in data)

    def test_get_resources_with_region_filter(self, client):
        """Test GET /resources with region filter"""
        _resources["res-1"] = {
            "resource_id": "res-1",
            "name": "web-server-01",
            "resource_type": "virtual_machine",
            "provider": "aws",
            "region": "us-east-1",
            "status": "running",
            "cpu_cores": 4,
            "memory_gb": 8,
            "disk_gb": 100,
            "tags": {},
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        _resources["res-2"] = {
            "resource_id": "res-2",
            "name": "web-server-02",
            "resource_type": "virtual_machine",
            "provider": "aws",
            "region": "us-west-2",
            "status": "running",
            "cpu_cores": 4,
            "memory_gb": 8,
            "disk_gb": 100,
            "tags": {},
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }

        response = client.get("/api/v1/infrastructure/resources?region=us-east-1")
        assert response.status_code == 200
        data = response.json()
        assert all(res["region"] == "us-east-1" for res in data)

    def test_get_resources_with_status_filter(self, client):
        """Test GET /resources with status filter"""
        _resources["res-1"] = {
            "resource_id": "res-1",
            "name": "web-server-01",
            "resource_type": "virtual_machine",
            "provider": "aws",
            "region": "us-east-1",
            "status": "running",
            "cpu_cores": 4,
            "memory_gb": 8,
            "disk_gb": 100,
            "tags": {},
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        _resources["res-2"] = {
            "resource_id": "res-2",
            "name": "web-server-02",
            "resource_type": "virtual_machine",
            "provider": "aws",
            "region": "us-east-1",
            "status": "stopped",
            "cpu_cores": 4,
            "memory_gb": 8,
            "disk_gb": 100,
            "tags": {},
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }

        response = client.get("/api/v1/infrastructure/resources?status=running")
        assert response.status_code == 200
        data = response.json()
        assert all(res["status"] == "running" for res in data)

    def test_get_resources_empty_returns_defaults(self, client):
        """Test GET /resources returns default resources when empty"""
        response = client.get("/api/v1/infrastructure/resources")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

    def test_create_resource_success(self, client):
        """Test POST /resources - successful creation"""
        request_data = {
            "name": "app-server-01",
            "resource_type": "virtual_machine",
            "provider": "aws",
            "region": "us-west-2",
            "cpu_cores": 4,
            "memory_gb": 16,
            "disk_gb": 200,
            "tags": {"environment": "production", "team": "platform"}
        }

        response = client.post("/api/v1/infrastructure/resources", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert "resource_id" in data
        assert data["name"] == request_data["name"]
        assert data["resource_type"] == request_data["resource_type"]
        assert data["status"] == "running"

    def test_create_resource_with_defaults(self, client):
        """Test POST /resources with default values"""
        request_data = {
            "name": "test-server",
            "resource_type": "virtual_machine",
            "provider": "aws",
            "region": "us-east-1"
        }

        response = client.post("/api/v1/infrastructure/resources", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert data["cpu_cores"] == 2  # Default
        assert data["memory_gb"] == 4  # Default
        assert data["disk_gb"] == 20  # Default
        assert data["tags"] == {}  # Default

    def test_create_resource_validation_error(self, client):
        """Test POST /resources with invalid data"""
        request_data = {
            "name": "",  # Empty name should fail
            "resource_type": "virtual_machine",
            "provider": "aws",
            "region": "us-east-1",
            "cpu_cores": 0,  # Below minimum
            "memory_gb": 0,  # Below minimum
            "disk_gb": 5  # Below minimum
        }

        response = client.post("/api/v1/infrastructure/resources", json=request_data)
        assert response.status_code == 422

    def test_create_resource_cpu_validation(self, client):
        """Test POST /resources with CPU validation"""
        # Test CPU above maximum
        request_data = {
            "name": "test-server",
            "resource_type": "virtual_machine",
            "provider": "aws",
            "region": "us-east-1",
            "cpu_cores": 129  # Above maximum of 128
        }

        response = client.post("/api/v1/infrastructure/resources", json=request_data)
        assert response.status_code == 422

    def test_create_resource_memory_validation(self, client):
        """Test POST /resources with memory validation"""
        # Test memory above maximum
        request_data = {
            "name": "test-server",
            "resource_type": "virtual_machine",
            "provider": "aws",
            "region": "us-east-1",
            "memory_gb": 513  # Above maximum of 512
        }

        response = client.post("/api/v1/infrastructure/resources", json=request_data)
        assert response.status_code == 422

    def test_create_resource_disk_validation(self, client):
        """Test POST /resources with disk validation"""
        # Test disk above maximum
        request_data = {
            "name": "test-server",
            "resource_type": "virtual_machine",
            "provider": "aws",
            "region": "us-east-1",
            "disk_gb": 10001  # Above maximum of 10000
        }

        response = client.post("/api/v1/infrastructure/resources", json=request_data)
        assert response.status_code == 422

    def test_get_resource_by_id_success(self, client):
        """Test GET /resources/{resource_id} - successful retrieval"""
        resource_id = "res-1"
        _resources[resource_id] = {
            "resource_id": resource_id,
            "name": "web-server-01",
            "resource_type": "virtual_machine",
            "provider": "aws",
            "region": "us-east-1",
            "status": "running",
            "cpu_cores": 4,
            "memory_gb": 8,
            "disk_gb": 100,
            "tags": {},
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }

        response = client.get(f"/api/v1/infrastructure/resources/{resource_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["resource_id"] == resource_id

    def test_get_resource_by_id_not_found(self, client):
        """Test GET /resources/{resource_id} with non-existent ID"""
        response = client.get("/api/v1/infrastructure/resources/non-existent-id")
        assert response.status_code == 404

    def test_update_resource_success(self, client):
        """Test PATCH /resources/{resource_id} - successful update"""
        resource_id = "res-1"
        _resources[resource_id] = {
            "resource_id": resource_id,
            "name": "web-server-01",
            "resource_type": "virtual_machine",
            "provider": "aws",
            "region": "us-east-1",
            "status": "running",
            "cpu_cores": 4,
            "memory_gb": 8,
            "disk_gb": 100,
            "tags": {},
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }

        update_data = {
            "name": "web-server-01-updated",
            "cpu_cores": 8,
            "memory_gb": 16
        }

        response = client.patch(f"/api/v1/infrastructure/resources/{resource_id}", json=update_data)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "web-server-01-updated"
        assert data["cpu_cores"] == 8
        assert data["memory_gb"] == 16

    def test_update_resource_not_found(self, client):
        """Test PATCH /resources/{resource_id} with non-existent ID"""
        update_data = {"name": "updated"}

        response = client.patch("/api/v1/infrastructure/resources/non-existent-id", json=update_data)
        assert response.status_code == 404

    def test_update_resource_validation_error(self, client):
        """Test PATCH /resources/{resource_id} with invalid data"""
        resource_id = "res-1"
        _resources[resource_id] = {
            "resource_id": resource_id,
            "name": "web-server-01",
            "resource_type": "virtual_machine",
            "provider": "aws",
            "region": "us-east-1",
            "status": "running",
            "cpu_cores": 4,
            "memory_gb": 8,
            "disk_gb": 100,
            "tags": {},
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }

        update_data = {
            "cpu_cores": 0  # Below minimum
        }

        response = client.patch(f"/api/v1/infrastructure/resources/{resource_id}", json=update_data)
        assert response.status_code == 422

    def test_update_resource_partial_update(self, client):
        """Test PATCH /resources/{resource_id} with partial update"""
        resource_id = "res-1"
        _resources[resource_id] = {
            "resource_id": resource_id,
            "name": "web-server-01",
            "resource_type": "virtual_machine",
            "provider": "aws",
            "region": "us-east-1",
            "status": "running",
            "cpu_cores": 4,
            "memory_gb": 8,
            "disk_gb": 100,
            "tags": {},
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }

        update_data = {
            "status": "stopped"
        }

        response = client.patch(f"/api/v1/infrastructure/resources/{resource_id}", json=update_data)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "stopped"
        assert data["cpu_cores"] == 4  # Unchanged

    def test_delete_resource_success(self, client):
        """Test DELETE /resources/{resource_id} - successful deletion"""
        resource_id = "res-1"
        _resources[resource_id] = {
            "resource_id": resource_id,
            "name": "web-server-01",
            "resource_type": "virtual_machine",
            "provider": "aws",
            "region": "us-east-1",
            "status": "running",
            "cpu_cores": 4,
            "memory_gb": 8,
            "disk_gb": 100,
            "tags": {},
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }

        response = client.delete(f"/api/v1/infrastructure/resources/{resource_id}")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert resource_id not in _resources

    def test_delete_resource_not_found(self, client):
        """Test DELETE /resources/{resource_id} with non-existent ID"""
        response = client.delete("/api/v1/infrastructure/resources/non-existent-id")
        assert response.status_code == 404


class TestInfrastructureTopologyEndpoints:
    """Test infrastructure topology endpoints"""

    @patch('core.service_discovery_manager.get_service_discovery_manager')
    @patch('core.service_mesh_manager.get_service_mesh_manager')
    def test_get_topology_success(self, mock_get_mesh, mock_get_discovery, client):
        """Test GET /topology - successful retrieval"""
        mock_get_discovery.return_value = Mock()
        mock_get_mesh.return_value = Mock()

        response = client.get("/api/v1/infrastructure/topology")
        assert response.status_code == 200
        data = response.json()
        assert "nodes" in data
        assert "edges" in data
        assert "last_updated" in data
        assert isinstance(data["nodes"], list)
        assert isinstance(data["edges"], list)

    @patch('core.service_discovery_manager.get_service_discovery_manager')
    @patch('core.service_mesh_manager.get_service_mesh_manager')
    def test_get_topology_manager_error(self, mock_get_mesh, mock_get_discovery, client):
        """Test GET /topology when managers raise an error"""
        mock_get_discovery.side_effect = Exception("Discovery error")
        mock_get_mesh.side_effect = Exception("Mesh error")

        response = client.get("/api/v1/infrastructure/topology")
        assert response.status_code == 200  # Should return default topology (not empty)
        data = response.json()
        # The function returns default topology even on error
        assert len(data["nodes"]) > 0  # Default nodes are returned


class TestInfrastructureHealthEndpoints:
    """Test infrastructure health endpoints"""

    @patch('core.monitoring_infrastructure.get_monitoring_infrastructure')
    @patch('core.service_monitoring_manager.get_service_monitoring_manager')
    def test_get_health_success(self, mock_get_service, mock_get_monitoring, client):
        """Test GET /health - successful retrieval"""
        mock_monitoring = Mock()
        mock_monitoring.get_monitoring_status.return_value = "healthy"
        mock_get_monitoring.return_value = mock_monitoring
        mock_get_service.return_value = Mock()

        response = client.get("/api/v1/infrastructure/health")
        assert response.status_code == 200
        data = response.json()
        assert "overall_status" in data
        assert "overall_health_score" in data
        assert "components" in data
        assert "last_updated" in data
        assert isinstance(data["components"], list)

    @patch('core.monitoring_infrastructure.get_monitoring_infrastructure')
    @patch('core.service_monitoring_manager.get_service_monitoring_manager')
    def test_get_health_manager_error(self, mock_get_service, mock_get_monitoring, client):
        """Test GET /health when managers raise an error"""
        mock_get_monitoring.side_effect = Exception("Monitoring error")
        mock_get_service.side_effect = Exception("Service error")

        response = client.get("/api/v1/infrastructure/health")
        assert response.status_code == 200  # Should return default health
        data = response.json()
        assert data["overall_status"] == "unknown"
        assert data["overall_health_score"] == 0.0


class TestInfrastructureCapacityEndpoints:
    """Test infrastructure capacity endpoints"""

    @patch('core.system_resource_optimizer.get_system_resource_optimizer')
    def test_get_capacity_success(self, mock_get_optimizer, client):
        """Test GET /capacity - successful retrieval"""
        mock_get_optimizer.return_value = Mock()

        response = client.get("/api/v1/infrastructure/capacity")
        assert response.status_code == 200
        data = response.json()
        assert "total_resources" in data
        assert "capacity_metrics" in data
        assert "recommendations" in data
        assert "last_updated" in data
        assert isinstance(data["capacity_metrics"], list)
        assert isinstance(data["recommendations"], list)

    @patch('core.system_resource_optimizer.get_system_resource_optimizer')
    def test_get_capacity_manager_error(self, mock_get_optimizer, client):
        """Test GET /capacity when manager raises an error"""
        mock_get_optimizer.side_effect = Exception("Optimizer error")

        response = client.get("/api/v1/infrastructure/capacity")
        assert response.status_code == 200  # Should return default capacity
        data = response.json()
        # The function returns default capacity even on error
        assert data["total_resources"] >= 0  # May return default data


class TestInfrastructureProvisioningEndpoints:
    """Test infrastructure provisioning endpoints"""

    def test_provision_resource_success(self, client):
        """Test POST /provisioning - successful provisioning"""
        request_data = {
            "name": "app-server-02",
            "resource_type": "virtual_machine",
            "provider": "aws",
            "region": "us-west-2",
            "specification": {
                "instance_type": "t3.large",
                "cpu_cores": 2,
                "memory_gb": 8,
                "disk_gb": 50
            },
            "configuration": {
                "security_groups": ["web-sg"],
                "subnet": "public-subnet-1"
            }
        }

        response = client.post("/api/v1/infrastructure/provisioning", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert "provisioning_id" in data
        assert "resource_id" in data
        assert data["status"] == "completed"
        assert data["progress"] == 100

    def test_provision_resource_minimal_request(self, client):
        """Test POST /provisioning with minimal required fields"""
        request_data = {
            "name": "test-server",
            "resource_type": "virtual_machine",
            "provider": "aws",
            "region": "us-east-1",
            "specification": {
                "cpu_cores": 2,
                "memory_gb": 4,
                "disk_gb": 20
            }
        }

        response = client.post("/api/v1/infrastructure/provisioning", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"

    def test_provision_resource_validation_error(self, client):
        """Test POST /provisioning with invalid data"""
        request_data = {
            # Missing required fields
        }

        response = client.post("/api/v1/infrastructure/provisioning", json=request_data)
        assert response.status_code == 422

    def test_provision_resource_creates_resource(self, client):
        """Test POST /provisioning creates the actual resource"""
        request_data = {
            "name": "new-server",
            "resource_type": "virtual_machine",
            "provider": "aws",
            "region": "us-east-1",
            "specification": {
                "cpu_cores": 4,
                "memory_gb": 8,
                "disk_gb": 100
            }
        }

        response = client.post("/api/v1/infrastructure/provisioning", json=request_data)
        assert response.status_code == 200
        data = response.json()
        resource_id = data["resource_id"]

        # Verify resource was created
        assert resource_id in _resources
        assert _resources[resource_id]["name"] == "new-server"


class TestInfrastructureRouterErrorHandling:
    """Test error handling across all endpoints"""

    def test_invalid_endpoint(self, client):
        """Test accessing invalid endpoint"""
        response = client.get("/api/v1/infrastructure/invalid")
        assert response.status_code == 404

    def test_invalid_method(self, client):
        """Test using invalid HTTP method"""
        response = client.put("/api/v1/infrastructure/resources")
        assert response.status_code == 405  # Method not allowed

    def test_malformed_json(self, client):
        """Test sending malformed JSON"""
        response = client.post(
            "/api/v1/infrastructure/resources",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422


class TestInfrastructureRouterDataValidation:
    """Test data validation across all endpoints"""

    def test_resource_create_field_types(self, client):
        """Test field type validation for resource creation"""
        # Test with invalid type for cpu_cores
        request_data = {
            "name": "test-server",
            "resource_type": "virtual_machine",
            "provider": "aws",
            "region": "us-east-1",
            "cpu_cores": "not_an_integer"  # Should be integer
        }

        response = client.post("/api/v1/infrastructure/resources", json=request_data)
        assert response.status_code == 422

    def test_resource_update_field_validation(self, client):
        """Test field validation for resource update"""
        resource_id = "res-1"
        _resources[resource_id] = {
            "resource_id": resource_id,
            "name": "web-server-01",
            "resource_type": "virtual_machine",
            "provider": "aws",
            "region": "us-east-1",
            "status": "running",
            "cpu_cores": 4,
            "memory_gb": 8,
            "disk_gb": 100,
            "tags": {},
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }

        # Test with invalid cpu_cores
        update_data = {
            "cpu_cores": 200  # Above maximum
        }

        response = client.patch(f"/api/v1/infrastructure/resources/{resource_id}", json=update_data)
        assert response.status_code == 422

    def test_provisioning_specification_validation(self, client):
        """Test specification validation for provisioning"""
        request_data = {
            "name": "test-server",
            "resource_type": "virtual_machine",
            "provider": "aws",
            "region": "us-east-1",
            "specification": "invalid"  # Should be a dict
        }

        response = client.post("/api/v1/infrastructure/provisioning", json=request_data)
        assert response.status_code == 422


class TestInfrastructureRouterResponseModels:
    """Test response model validation"""

    def test_resource_response_structure(self, client):
        """Test resource response has correct structure"""
        resource_id = "res-1"
        _resources[resource_id] = {
            "resource_id": resource_id,
            "name": "web-server-01",
            "resource_type": "virtual_machine",
            "provider": "aws",
            "region": "us-east-1",
            "status": "running",
            "cpu_cores": 4,
            "memory_gb": 8,
            "disk_gb": 100,
            "tags": {},
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }

        response = client.get("/api/v1/infrastructure/resources")
        assert response.status_code == 200
        data = response.json()
        if len(data) > 0:
            required_fields = [
                "resource_id", "name", "resource_type", "provider", "region",
                "status", "cpu_cores", "memory_gb", "disk_gb", "tags",
                "created_at", "updated_at"
            ]
            for field in required_fields:
                assert field in data[0]

    def test_topology_response_structure(self, client):
        """Test topology response has correct structure"""
        with patch('core.service_discovery_manager.get_service_discovery_manager'), \
             patch('core.service_mesh_manager.get_service_mesh_manager'):
            response = client.get("/api/v1/infrastructure/topology")
            assert response.status_code == 200
            data = response.json()
            required_fields = ["nodes", "edges", "last_updated"]
            for field in required_fields:
                assert field in data

    def test_health_response_structure(self, client):
        """Test health response has correct structure"""
        with patch('core.monitoring_infrastructure.get_monitoring_infrastructure') as mock_get_monitoring, \
             patch('core.service_monitoring_manager.get_service_monitoring_manager'):
            mock_monitoring = Mock()
            mock_monitoring.get_monitoring_status.return_value = "healthy"
            mock_get_monitoring.return_value = mock_monitoring

            response = client.get("/api/v1/infrastructure/health")
            assert response.status_code == 200
            data = response.json()
            required_fields = ["overall_status", "overall_health_score", "components", "last_updated"]
            for field in required_fields:
                assert field in data

    def test_capacity_response_structure(self, client):
        """Test capacity response has correct structure"""
        with patch('core.system_resource_optimizer.get_system_resource_optimizer'):
            response = client.get("/api/v1/infrastructure/capacity")
            assert response.status_code == 200
            data = response.json()
            required_fields = ["total_resources", "capacity_metrics", "recommendations", "last_updated"]
            for field in required_fields:
                assert field in data

    def test_provisioning_response_structure(self, client):
        """Test provisioning response has correct structure"""
        request_data = {
            "name": "test-server",
            "resource_type": "virtual_machine",
            "provider": "aws",
            "region": "us-east-1",
            "specification": {
                "cpu_cores": 2,
                "memory_gb": 4,
                "disk_gb": 20
            }
        }

        response = client.post("/api/v1/infrastructure/provisioning", json=request_data)
        assert response.status_code == 200
        data = response.json()
        required_fields = [
            "provisioning_id", "resource_id", "status",
            "estimated_completion_time", "progress", "logs"
        ]
        for field in required_fields:
            assert field in data


class TestInfrastructureRouterEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_resource_with_max_cpu(self, client):
        """Test creating resource with maximum CPU"""
        request_data = {
            "name": "max-cpu-server",
            "resource_type": "virtual_machine",
            "provider": "aws",
            "region": "us-east-1",
            "cpu_cores": 128  # Maximum
        }

        response = client.post("/api/v1/infrastructure/resources", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert data["cpu_cores"] == 128

    def test_resource_with_max_memory(self, client):
        """Test creating resource with maximum memory"""
        request_data = {
            "name": "max-memory-server",
            "resource_type": "virtual_machine",
            "provider": "aws",
            "region": "us-east-1",
            "memory_gb": 512  # Maximum
        }

        response = client.post("/api/v1/infrastructure/resources", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert data["memory_gb"] == 512

    def test_resource_with_max_disk(self, client):
        """Test creating resource with maximum disk"""
        request_data = {
            "name": "max-disk-server",
            "resource_type": "virtual_machine",
            "provider": "aws",
            "region": "us-east-1",
            "disk_gb": 10000  # Maximum
        }

        response = client.post("/api/v1/infrastructure/resources", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert data["disk_gb"] == 10000

    def test_resource_with_min_cpu(self, client):
        """Test creating resource with minimum CPU"""
        request_data = {
            "name": "min-cpu-server",
            "resource_type": "virtual_machine",
            "provider": "aws",
            "region": "us-east-1",
            "cpu_cores": 1  # Minimum
        }

        response = client.post("/api/v1/infrastructure/resources", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert data["cpu_cores"] == 1

    def test_resource_with_min_memory(self, client):
        """Test creating resource with minimum memory"""
        request_data = {
            "name": "min-memory-server",
            "resource_type": "virtual_machine",
            "provider": "aws",
            "region": "us-east-1",
            "memory_gb": 1  # Minimum
        }

        response = client.post("/api/v1/infrastructure/resources", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert data["memory_gb"] == 1

    def test_resource_with_min_disk(self, client):
        """Test creating resource with minimum disk"""
        request_data = {
            "name": "min-disk-server",
            "resource_type": "virtual_machine",
            "provider": "aws",
            "region": "us-east-1",
            "disk_gb": 10  # Minimum
        }

        response = client.post("/api/v1/infrastructure/resources", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert data["disk_gb"] == 10

    def test_multiple_filters_combined(self, client):
        """Test combining multiple filters"""
        _resources["res-1"] = {
            "resource_id": "res-1",
            "name": "web-server-01",
            "resource_type": "virtual_machine",
            "provider": "aws",
            "region": "us-east-1",
            "status": "running",
            "cpu_cores": 4,
            "memory_gb": 8,
            "disk_gb": 100,
            "tags": {},
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        _resources["res-2"] = {
            "resource_id": "res-2",
            "name": "web-server-02",
            "resource_type": "virtual_machine",
            "provider": "gcp",
            "region": "us-east-1",
            "status": "running",
            "cpu_cores": 4,
            "memory_gb": 8,
            "disk_gb": 100,
            "tags": {},
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }

        response = client.get(
            "/api/v1/infrastructure/resources?resource_type=virtual_machine&provider=aws&status=running"
        )
        assert response.status_code == 200
        data = response.json()
        assert all(res["provider"] == "aws" for res in data)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=api.infrastructure_advanced_router", "--cov-report=html"])
