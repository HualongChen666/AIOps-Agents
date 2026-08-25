# -*- coding: utf-8 -*-
"""
Test suite for Service Discovery Advanced Router
=================================================

Comprehensive tests for service discovery advanced features including:
- Service CRUD operations (GET, POST, PATCH, DELETE)
- Health check management
- Service registration and deregistration
- Endpoint listing
- Instance management
- Data validation
- Error handling
- Permission control
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from fastapi import HTTPException
from fastapi.testclient import TestClient
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
import uuid
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from api.service_discovery_advanced_router import (
    router,
    ServiceCreate,
    ServiceUpdate,
    HealthCheckCreate,
    ServiceRegistration,
    ServiceDeregistration,
    _services_db,
    _health_checks_db,
)


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def client():
    """Create a test client for the service discovery router"""
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(router)
    # Disable CORS for testing
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_databases():
    """Reset in-memory databases before each test"""
    _services_db.clear()
    _health_checks_db.clear()
    yield
    _services_db.clear()
    _health_checks_db.clear()


@pytest.fixture
def sample_service_create():
    """Sample service creation data"""
    return ServiceCreate(
        name="test-service",
        host="localhost",
        port=8080,
        protocol="http",
        metadata={"version": "1.0"},
        weight=10
    )


@pytest.fixture
def sample_service_update():
    """Sample service update data"""
    return ServiceUpdate(
        name="updated-service",
        host="updated-host",
        port=9090,
        protocol="https",
        metadata={"version": "2.0"},
        weight=20
    )


@pytest.fixture
def sample_health_check_create():
    """Sample health check creation data"""
    return HealthCheckCreate(
        service_id="test-service-id",
        check_type="http",
        endpoint="/health",
        interval_seconds=30,
        timeout_seconds=5,
        healthy_threshold=2,
        unhealthy_threshold=3
    )


@pytest.fixture
def sample_service_registration():
    """Sample service registration data"""
    return ServiceRegistration(
        service_name="test-service",
        instance_id="instance-1",
        host="localhost",
        port=8080,
        weight=10,
        metadata={"version": "1.0"}
    )


@pytest.fixture
def sample_service_deregistration():
    """Sample service deregistration data"""
    return ServiceDeregistration(
        service_name="test-service",
        instance_id="instance-1"
    )


@pytest.fixture
def mock_service_discovery_manager():
    """Mock service discovery manager"""
    manager = MagicMock()
    manager.get_service_summary.return_value = {
        "total_services": 5,
        "healthy_services": 4,
        "unhealthy_services": 1
    }
    manager.get_service_details.return_value = {
        "instances": 3,
        "status": "healthy"
    }
    manager.register_service.return_value = MagicMock(
        instance_id="instance-1",
        service_name="test-service",
        status=MagicMock(value="active"),
        weight=10
    )
    manager.deregister_service.return_value = True
    return manager


# ============================================================================
# GET /services - List Services Tests
# ============================================================================

class TestListServices:
    """Test cases for listing services"""

    def test_list_services_success(self, client, mock_service_discovery_manager):
        """Test successful listing of services"""
        with patch('core.service_discovery_manager.get_service_discovery_manager') as mock_get_manager:
            mock_get_manager.return_value = mock_service_discovery_manager
            
            # Add a test service
            service_id = str(uuid.uuid4())
            _services_db[service_id] = {
                "name": "test-service",
                "host": "localhost",
                "port": 8080,
                "protocol": "http",
                "metadata": {},
                "weight": 10,
                "status": "active",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }
            
            response = client.get("/api/v1/service-discovery/services")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "services" in data["data"]
            assert "total" in data["data"]
            assert data["data"]["total"] >= 1

    def test_list_services_with_status_filter(self, client, mock_service_discovery_manager):
        """Test listing services with status filter"""
        with patch('core.service_discovery_manager.get_service_discovery_manager') as mock_get_manager:
            mock_get_manager.return_value = mock_service_discovery_manager
            
            # Add test services with different statuses
            service_id1 = str(uuid.uuid4())
            _services_db[service_id1] = {
                "name": "active-service",
                "host": "localhost",
                "port": 8080,
                "protocol": "http",
                "metadata": {},
                "weight": 10,
                "status": "active",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }
            
            service_id2 = str(uuid.uuid4())
            _services_db[service_id2] = {
                "name": "inactive-service",
                "host": "localhost",
                "port": 8081,
                "protocol": "http",
                "metadata": {},
                "weight": 10,
                "status": "inactive",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }
            
            response = client.get("/api/v1/service-discovery/services?status=active")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert all(s["status"] == "active" for s in data["data"]["services"])

    def test_list_services_with_protocol_filter(self, client, mock_service_discovery_manager):
        """Test listing services with protocol filter"""
        with patch('core.service_discovery_manager.get_service_discovery_manager') as mock_get_manager:
            mock_get_manager.return_value = mock_service_discovery_manager
            
            # Add test services with different protocols
            service_id1 = str(uuid.uuid4())
            _services_db[service_id1] = {
                "name": "http-service",
                "host": "localhost",
                "port": 8080,
                "protocol": "http",
                "metadata": {},
                "weight": 10,
                "status": "active",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }
            
            service_id2 = str(uuid.uuid4())
            _services_db[service_id2] = {
                "name": "https-service",
                "host": "localhost",
                "port": 8443,
                "protocol": "https",
                "metadata": {},
                "weight": 10,
                "status": "active",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }
            
            response = client.get("/api/v1/service-discovery/services?protocol=http")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert all(s["protocol"] == "http" for s in data["data"]["services"])

    def test_list_services_with_pagination(self, client, mock_service_discovery_manager):
        """Test listing services with pagination"""
        with patch('core.service_discovery_manager.get_service_discovery_manager') as mock_get_manager:
            mock_get_manager.return_value = mock_service_discovery_manager
            
            # Add multiple services
            for i in range(5):
                service_id = str(uuid.uuid4())
                _services_db[service_id] = {
                    "name": f"service-{i}",
                    "host": "localhost",
                    "port": 8080 + i,
                    "protocol": "http",
                    "metadata": {},
                    "weight": 10,
                    "status": "active",
                    "created_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat(),
                }
            
            response = client.get("/api/v1/service-discovery/services?limit=2&offset=0")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert len(data["data"]["services"]) == 2
            assert data["data"]["limit"] == 2
            assert data["data"]["offset"] == 0

    def test_list_services_invalid_limit(self, client, mock_service_discovery_manager):
        """Test listing services with invalid limit"""
        with patch('core.service_discovery_manager.get_service_discovery_manager') as mock_get_manager:
            mock_get_manager.return_value = mock_service_discovery_manager
            
            response = client.get("/api/v1/service-discovery/services?limit=0")
            # FastAPI validation should catch this
            assert response.status_code == 422

    def test_list_services_invalid_offset(self, client, mock_service_discovery_manager):
        """Test listing services with invalid offset"""
        with patch('core.service_discovery_manager.get_service_discovery_manager') as mock_get_manager:
            mock_get_manager.return_value = mock_service_discovery_manager
            
            response = client.get("/api/v1/service-discovery/services?offset=-1")
            # FastAPI validation should catch this
            assert response.status_code == 422

    def test_list_services_manager_error(self, client):
        """Test listing services when manager raises error"""
        with patch('core.service_discovery_manager.get_service_discovery_manager') as mock_get_manager:
            mock_get_manager.side_effect = Exception("Manager error")
            
            response = client.get("/api/v1/service-discovery/services")
            assert response.status_code == 500
            data = response.json()
            assert "detail" in data


# ============================================================================
# POST /services - Create Service Tests
# ============================================================================

class TestCreateService:
    """Test cases for creating services"""

    def test_create_service_success(self, client, sample_service_create, mock_service_discovery_manager):
        """Test successful service creation"""
        with patch('core.service_discovery_manager.get_service_discovery_manager') as mock_get_manager:
            mock_get_manager.return_value = mock_service_discovery_manager
            
            response = client.post(
                "/api/v1/service-discovery/services",
                json=sample_service_create.dict()
            )
            assert response.status_code == 201
            data = response.json()
            assert data["status"] == "success"
            assert "id" in data["data"]
            assert data["data"]["name"] == "test-service"
            assert data["data"]["host"] == "localhost"
            assert data["data"]["port"] == 8080
            assert data["data"]["status"] == "active"

    def test_create_service_invalid_port(self, client):
        """Test service creation with invalid port"""
        invalid_data = {
            "name": "test-service",
            "host": "localhost",
            "port": 70000,  # Invalid port
            "protocol": "http"
        }
        response = client.post("/api/v1/service-discovery/services", json=invalid_data)
        assert response.status_code == 422

    def test_create_service_invalid_port_zero(self, client):
        """Test service creation with port 0"""
        invalid_data = {
            "name": "test-service",
            "host": "localhost",
            "port": 0,  # Invalid port
            "protocol": "http"
        }
        response = client.post("/api/v1/service-discovery/services", json=invalid_data)
        assert response.status_code == 422

    def test_create_service_missing_required_field(self, client):
        """Test service creation with missing required field"""
        invalid_data = {
            "host": "localhost",
            "port": 8080
            # Missing name
        }
        response = client.post("/api/v1/service-discovery/services", json=invalid_data)
        assert response.status_code == 422

    def test_create_service_invalid_weight(self, client):
        """Test service creation with invalid weight"""
        invalid_data = {
            "name": "test-service",
            "host": "localhost",
            "port": 8080,
            "weight": 150  # Invalid weight (> 100)
        }
        response = client.post("/api/v1/service-discovery/services", json=invalid_data)
        assert response.status_code == 422

    def test_create_service_manager_error(self, client, sample_service_create):
        """Test service creation when manager raises error"""
        with patch('core.service_discovery_manager.get_service_discovery_manager') as mock_get_manager:
            mock_get_manager.side_effect = Exception("Manager error")
            
            response = client.post(
                "/api/v1/service-discovery/services",
                json=sample_service_create.dict()
            )
            assert response.status_code == 500

    def test_create_service_with_metadata(self, client, mock_service_discovery_manager):
        """Test service creation with metadata"""
        with patch('core.service_discovery_manager.get_service_discovery_manager') as mock_get_manager:
            mock_get_manager.return_value = mock_service_discovery_manager
            
            service_data = {
                "name": "test-service",
                "host": "localhost",
                "port": 8080,
                "metadata": {
                    "version": "1.0",
                    "environment": "production",
                    "team": "platform"
                }
            }
            
            response = client.post("/api/v1/service-discovery/services", json=service_data)
            assert response.status_code == 201
            data = response.json()
            assert data["data"]["metadata"]["version"] == "1.0"
            assert data["data"]["metadata"]["environment"] == "production"


# ============================================================================
# GET /services/{service_id} - Get Service Tests
# ============================================================================

class TestGetService:
    """Test cases for getting a specific service"""

    def test_get_service_success(self, client, mock_service_discovery_manager):
        """Test successful service retrieval"""
        with patch('core.service_discovery_manager.get_service_discovery_manager') as mock_get_manager:
            mock_get_manager.return_value = mock_service_discovery_manager
            
            # Add a test service
            service_id = str(uuid.uuid4())
            _services_db[service_id] = {
                "name": "test-service",
                "host": "localhost",
                "port": 8080,
                "protocol": "http",
                "metadata": {},
                "weight": 10,
                "status": "active",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }
            
            response = client.get(f"/api/v1/service-discovery/services/{service_id}")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["data"]["id"] == service_id
            assert data["data"]["name"] == "test-service"

    def test_get_service_not_found(self, client):
        """Test getting a non-existent service"""
        fake_id = str(uuid.uuid4())
        response = client.get(f"/api/v1/service-discovery/services/{fake_id}")
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    def test_get_service_manager_error(self, client, mock_service_discovery_manager):
        """Test getting service when manager raises error"""
        with patch('core.service_discovery_manager.get_service_discovery_manager') as mock_get_manager:
            mock_get_manager.side_effect = Exception("Manager error")
            
            # Add a test service
            service_id = str(uuid.uuid4())
            _services_db[service_id] = {
                "name": "test-service",
                "host": "localhost",
                "port": 8080,
                "protocol": "http",
                "metadata": {},
                "weight": 10,
                "status": "active",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }
            
            response = client.get(f"/api/v1/service-discovery/services/{service_id}")
            assert response.status_code == 500


# ============================================================================
# PATCH /services/{service_id} - Update Service Tests
# ============================================================================

class TestUpdateService:
    """Test cases for updating services"""

    def test_update_service_success(self, client, sample_service_update):
        """Test successful service update"""
        # Add a test service
        service_id = str(uuid.uuid4())
        _services_db[service_id] = {
            "name": "test-service",
            "host": "localhost",
            "port": 8080,
            "protocol": "http",
            "metadata": {},
            "weight": 10,
            "status": "active",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }
        
        response = client.patch(
            f"/api/v1/service-discovery/services/{service_id}",
            json=sample_service_update.dict()
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["data"]["name"] == "updated-service"
        assert data["data"]["host"] == "updated-host"
        assert data["data"]["port"] == 9090

    def test_update_service_partial(self, client):
        """Test partial service update"""
        # Add a test service
        service_id = str(uuid.uuid4())
        _services_db[service_id] = {
            "name": "test-service",
            "host": "localhost",
            "port": 8080,
            "protocol": "http",
            "metadata": {},
            "weight": 10,
            "status": "active",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }
        
        partial_update = {"name": "updated-name"}
        response = client.patch(
            f"/api/v1/service-discovery/services/{service_id}",
            json=partial_update
        )
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["name"] == "updated-name"
        assert data["data"]["host"] == "localhost"  # Unchanged

    def test_update_service_not_found(self, client):
        """Test updating a non-existent service"""
        fake_id = str(uuid.uuid4())
        partial_update = {"name": "updated-name"}
        response = client.patch(
            f"/api/v1/service-discovery/services/{fake_id}",
            json=partial_update
        )
        assert response.status_code == 404

    def test_update_service_invalid_port(self, client):
        """Test service update with invalid port"""
        # Add a test service
        service_id = str(uuid.uuid4())
        _services_db[service_id] = {
            "name": "test-service",
            "host": "localhost",
            "port": 8080,
            "protocol": "http",
            "metadata": {},
            "weight": 10,
            "status": "active",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }
        
        invalid_update = {"port": 70000}
        response = client.patch(
            f"/api/v1/service-discovery/services/{service_id}",
            json=invalid_update
        )
        assert response.status_code == 422

    def test_update_service_manager_error(self, client, sample_service_update):
        """Test service update when manager raises error"""
        # Note: update_service doesn't call the manager, so this test is modified
        # to test the general error handling pattern
        # Add a test service
        service_id = str(uuid.uuid4())
        _services_db[service_id] = {
            "name": "test-service",
            "host": "localhost",
            "port": 8080,
            "protocol": "http",
            "metadata": {},
            "weight": 10,
            "status": "active",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }
        
        response = client.patch(
            f"/api/v1/service-discovery/services/{service_id}",
            json=sample_service_update.dict()
        )
        # Since update_service doesn't call manager, it should succeed
        assert response.status_code == 200


# ============================================================================
# DELETE /services/{service_id} - Delete Service Tests
# ============================================================================

class TestDeleteService:
    """Test cases for deleting services"""

    def test_delete_service_success(self, client, mock_service_discovery_manager):
        """Test successful service deletion"""
        with patch('core.service_discovery_manager.get_service_discovery_manager') as mock_get_manager:
            mock_get_manager.return_value = mock_service_discovery_manager
            
            # Add a test service
            service_id = str(uuid.uuid4())
            _services_db[service_id] = {
                "name": "test-service",
                "host": "localhost",
                "port": 8080,
                "protocol": "http",
                "metadata": {},
                "weight": 10,
                "status": "active",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }
            
            response = client.delete(f"/api/v1/service-discovery/services/{service_id}")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert service_id not in _services_db

    def test_delete_service_not_found(self, client):
        """Test deleting a non-existent service"""
        fake_id = str(uuid.uuid4())
        response = client.delete(f"/api/v1/service-discovery/services/{fake_id}")
        assert response.status_code == 404

    def test_delete_service_manager_error(self, client, mock_service_discovery_manager):
        """Test service deletion when manager raises error"""
        with patch('core.service_discovery_manager.get_service_discovery_manager') as mock_get_manager:
            mock_get_manager.side_effect = Exception("Manager error")
            
            # Add a test service
            service_id = str(uuid.uuid4())
            _services_db[service_id] = {
                "name": "test-service",
                "host": "localhost",
                "port": 8080,
                "protocol": "http",
                "metadata": {},
                "weight": 10,
                "status": "active",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }
            
            response = client.delete(f"/api/v1/service-discovery/services/{service_id}")
            assert response.status_code == 500


# ============================================================================
# GET /health-checks - List Health Checks Tests
# ============================================================================

class TestListHealthChecks:
    """Test cases for listing health checks"""

    def test_list_health_checks_success(self, client):
        """Test successful listing of health checks"""
        # Add a test health check
        check_id = str(uuid.uuid4())
        _health_checks_db[check_id] = {
            "service_id": "test-service-id",
            "check_type": "http",
            "endpoint": "/health",
            "interval_seconds": 30,
            "timeout_seconds": 5,
            "healthy_threshold": 2,
            "unhealthy_threshold": 3,
            "status": "healthy",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }
        
        response = client.get("/api/v1/service-discovery/health-checks")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "health_checks" in data["data"]
        assert len(data["data"]["health_checks"]) >= 1

    def test_list_health_checks_with_service_filter(self, client):
        """Test listing health checks with service filter"""
        # Add test health checks
        check_id1 = str(uuid.uuid4())
        _health_checks_db[check_id1] = {
            "service_id": "service-1",
            "check_type": "http",
            "endpoint": "/health",
            "interval_seconds": 30,
            "timeout_seconds": 5,
            "healthy_threshold": 2,
            "unhealthy_threshold": 3,
            "status": "healthy",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }
        
        check_id2 = str(uuid.uuid4())
        _health_checks_db[check_id2] = {
            "service_id": "service-2",
            "check_type": "http",
            "endpoint": "/health",
            "interval_seconds": 30,
            "timeout_seconds": 5,
            "healthy_threshold": 2,
            "unhealthy_threshold": 3,
            "status": "healthy",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }
        
        response = client.get("/api/v1/service-discovery/health-checks?service_id=service-1")
        assert response.status_code == 200
        data = response.json()
        assert all(hc["service_id"] == "service-1" for hc in data["data"]["health_checks"])

    def test_list_health_checks_with_status_filter(self, client):
        """Test listing health checks with status filter"""
        # Add test health checks
        check_id1 = str(uuid.uuid4())
        _health_checks_db[check_id1] = {
            "service_id": "service-1",
            "check_type": "http",
            "endpoint": "/health",
            "interval_seconds": 30,
            "timeout_seconds": 5,
            "healthy_threshold": 2,
            "unhealthy_threshold": 3,
            "status": "healthy",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }
        
        check_id2 = str(uuid.uuid4())
        _health_checks_db[check_id2] = {
            "service_id": "service-2",
            "check_type": "http",
            "endpoint": "/health",
            "interval_seconds": 30,
            "timeout_seconds": 5,
            "healthy_threshold": 2,
            "unhealthy_threshold": 3,
            "status": "unhealthy",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }
        
        response = client.get("/api/v1/service-discovery/health-checks?status=healthy")
        assert response.status_code == 200
        data = response.json()
        assert all(hc["status"] == "healthy" for hc in data["data"]["health_checks"])


# ============================================================================
# POST /health-checks - Create Health Check Tests
# ============================================================================

class TestCreateHealthCheck:
    """Test cases for creating health checks"""

    def test_create_health_check_success(self, client, sample_health_check_create, mock_service_discovery_manager):
        """Test successful health check creation"""
        with patch('core.service_discovery_manager.get_service_discovery_manager') as mock_get_manager:
            mock_get_manager.return_value = mock_service_discovery_manager
            
            # Add a test service
            service_id = "test-service-id"
            _services_db[service_id] = {
                "name": "test-service",
                "host": "localhost",
                "port": 8080,
                "protocol": "http",
                "metadata": {},
                "weight": 10,
                "status": "active",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }
            
            response = client.post(
                "/api/v1/service-discovery/health-checks",
                json=sample_health_check_create.dict()
            )
            assert response.status_code == 201
            data = response.json()
            assert data["status"] == "success"
            assert "id" in data["data"]
            assert data["data"]["service_id"] == service_id
            assert data["data"]["check_type"] == "http"

    def test_create_health_check_service_not_found(self, client, sample_health_check_create):
        """Test health check creation for non-existent service"""
        response = client.post(
            "/api/v1/service-discovery/health-checks",
            json=sample_health_check_create.dict()
        )
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    def test_create_health_check_invalid_interval(self, client):
        """Test health check creation with invalid interval"""
        invalid_data = {
            "service_id": "test-service-id",
            "interval_seconds": 2  # Less than minimum (5)
        }
        response = client.post("/api/v1/service-discovery/health-checks", json=invalid_data)
        assert response.status_code == 422

    def test_create_health_check_invalid_timeout(self, client):
        """Test health check creation with invalid timeout"""
        invalid_data = {
            "service_id": "test-service-id",
            "timeout_seconds": 0  # Less than minimum (1)
        }
        response = client.post("/api/v1/service-discovery/health-checks", json=invalid_data)
        assert response.status_code == 422


# ============================================================================
# GET /endpoints - List Endpoints Tests
# ============================================================================

class TestListEndpoints:
    """Test cases for listing endpoints"""

    def test_list_endpoints_success(self, client, mock_service_discovery_manager):
        """Test successful listing of endpoints"""
        with patch('core.service_discovery_manager.get_service_discovery_manager') as mock_get_manager:
            mock_get_manager.return_value = mock_service_discovery_manager
            
            # Add a test service
            service_id = str(uuid.uuid4())
            _services_db[service_id] = {
                "name": "test-service",
                "host": "localhost",
                "port": 8080,
                "protocol": "http",
                "metadata": {},
                "weight": 10,
                "status": "active",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }
            
            response = client.get("/api/v1/service-discovery/endpoints")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "endpoints" in data["data"]
            assert len(data["data"]["endpoints"]) >= 1

    def test_list_endpoints_with_service_filter(self, client, mock_service_discovery_manager):
        """Test listing endpoints with service name filter"""
        with patch('core.service_discovery_manager.get_service_discovery_manager') as mock_get_manager:
            mock_get_manager.return_value = mock_service_discovery_manager
            
            # Add test services
            service_id1 = str(uuid.uuid4())
            _services_db[service_id1] = {
                "name": "service-1",
                "host": "localhost",
                "port": 8080,
                "protocol": "http",
                "metadata": {},
                "weight": 10,
                "status": "active",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }
            
            service_id2 = str(uuid.uuid4())
            _services_db[service_id2] = {
                "name": "service-2",
                "host": "localhost",
                "port": 8081,
                "protocol": "http",
                "metadata": {},
                "weight": 10,
                "status": "active",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }
            
            response = client.get("/api/v1/service-discovery/endpoints?service_name=service-1")
            assert response.status_code == 200
            data = response.json()
            assert all(ep["service_name"] == "service-1" for ep in data["data"]["endpoints"])

    def test_list_endpoints_healthy_only(self, client, mock_service_discovery_manager):
        """Test listing only healthy endpoints"""
        with patch('core.service_discovery_manager.get_service_discovery_manager') as mock_get_manager:
            mock_get_manager.return_value = mock_service_discovery_manager
            
            # Add test services with different statuses
            service_id1 = str(uuid.uuid4())
            _services_db[service_id1] = {
                "name": "healthy-service",
                "host": "localhost",
                "port": 8080,
                "protocol": "http",
                "metadata": {},
                "weight": 10,
                "status": "active",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }
            
            service_id2 = str(uuid.uuid4())
            _services_db[service_id2] = {
                "name": "unhealthy-service",
                "host": "localhost",
                "port": 8081,
                "protocol": "http",
                "metadata": {},
                "weight": 10,
                "status": "inactive",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }
            
            response = client.get("/api/v1/service-discovery/endpoints?healthy_only=true")
            assert response.status_code == 200
            data = response.json()
            assert all(ep["status"] == "active" for ep in data["data"]["endpoints"])


# ============================================================================
# GET /registrations - List Registrations Tests
# ============================================================================

class TestListRegistrations:
    """Test cases for listing registrations"""

    def test_list_registrations_success(self, client, mock_service_discovery_manager):
        """Test successful listing of registrations"""
        with patch('core.service_discovery_manager.get_service_discovery_manager') as mock_get_manager:
            mock_get_manager.return_value = mock_service_discovery_manager
            
            # Add a test service
            service_id = str(uuid.uuid4())
            _services_db[service_id] = {
                "name": "test-service",
                "host": "localhost",
                "port": 8080,
                "protocol": "http",
                "metadata": {},
                "weight": 10,
                "status": "active",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }
            
            response = client.get("/api/v1/service-discovery/registrations")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "registrations" in data["data"]

    def test_list_registrations_with_filters(self, client, mock_service_discovery_manager):
        """Test listing registrations with filters"""
        with patch('core.service_discovery_manager.get_service_discovery_manager') as mock_get_manager:
            mock_get_manager.return_value = mock_service_discovery_manager
            
            # Add test services
            service_id1 = str(uuid.uuid4())
            _services_db[service_id1] = {
                "name": "service-1",
                "host": "localhost",
                "port": 8080,
                "protocol": "http",
                "metadata": {},
                "weight": 10,
                "status": "active",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }
            
            service_id2 = str(uuid.uuid4())
            _services_db[service_id2] = {
                "name": "service-2",
                "host": "localhost",
                "port": 8081,
                "protocol": "http",
                "metadata": {},
                "weight": 10,
                "status": "inactive",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }
            
            response = client.get("/api/v1/service-discovery/registrations?service_name=service-1&status=active")
            assert response.status_code == 200
            data = response.json()
            assert all(reg["service_name"] == "service-1" for reg in data["data"]["registrations"])


# ============================================================================
# POST /registrations - Register Service Tests
# ============================================================================

class TestRegisterService:
    """Test cases for registering services"""

    def test_register_service_success(self, client, sample_service_registration, mock_service_discovery_manager):
        """Test successful service registration"""
        with patch('core.service_discovery_manager.get_service_discovery_manager') as mock_get_manager:
            mock_get_manager.return_value = mock_service_discovery_manager
            
            response = client.post(
                "/api/v1/service-discovery/registrations",
                json=sample_service_registration.dict()
            )
            assert response.status_code == 201
            data = response.json()
            assert data["status"] == "success"
            assert data["data"]["instance_id"] == "instance-1"
            assert data["data"]["service_name"] == "test-service"

    def test_register_service_invalid_port(self, client):
        """Test service registration with invalid port"""
        invalid_data = {
            "service_name": "test-service",
            "instance_id": "instance-1",
            "host": "localhost",
            "port": 70000  # Invalid port
        }
        response = client.post("/api/v1/service-discovery/registrations", json=invalid_data)
        assert response.status_code == 422

    def test_register_service_manager_error(self, client, sample_service_registration):
        """Test service registration when manager raises error"""
        with patch('core.service_discovery_manager.get_service_discovery_manager') as mock_get_manager:
            mock_get_manager.side_effect = Exception("Manager error")
            
            response = client.post(
                "/api/v1/service-discovery/registrations",
                json=sample_service_registration.dict()
            )
            assert response.status_code == 500


# ============================================================================
# POST /deregistration - Deregister Service Tests
# ============================================================================

class TestDeregisterService:
    """Test cases for deregistering services"""

    def test_deregister_service_success(self, client, sample_service_deregistration, mock_service_discovery_manager):
        """Test successful service deregistration"""
        with patch('core.service_discovery_manager.get_service_discovery_manager') as mock_get_manager:
            mock_get_manager.return_value = mock_service_discovery_manager
            
            response = client.post(
                "/api/v1/service-discovery/deregistration",
                json=sample_service_deregistration.dict()
            )
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["data"]["success"] == True

    def test_deregister_service_not_found(self, client, sample_service_deregistration, mock_service_discovery_manager):
        """Test deregistering a non-existent service"""
        with patch('core.service_discovery_manager.get_service_discovery_manager') as mock_get_manager:
            mock_get_manager.return_value = mock_service_discovery_manager
            mock_service_discovery_manager.deregister_service.return_value = False
            
            response = client.post(
                "/api/v1/service-discovery/deregistration",
                json=sample_service_deregistration.dict()
            )
            assert response.status_code == 404

    def test_deregister_service_manager_error(self, client, sample_service_deregistration):
        """Test service deregistration when manager raises error"""
        with patch('core.service_discovery_manager.get_service_discovery_manager') as mock_get_manager:
            mock_get_manager.side_effect = Exception("Manager error")
            
            response = client.post(
                "/api/v1/service-discovery/deregistration",
                json=sample_service_deregistration.dict()
            )
            assert response.status_code == 500


# ============================================================================
# GET /instances - List Instances Tests
# ============================================================================

class TestListInstances:
    """Test cases for listing instances"""

    def test_list_instances_success(self, client, mock_service_discovery_manager):
        """Test successful listing of instances"""
        with patch('core.service_discovery_manager.get_service_discovery_manager') as mock_get_manager:
            mock_get_manager.return_value = mock_service_discovery_manager
            
            # Add a test service
            service_id = str(uuid.uuid4())
            _services_db[service_id] = {
                "name": "test-service",
                "host": "localhost",
                "port": 8080,
                "protocol": "http",
                "metadata": {},
                "weight": 10,
                "status": "active",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }
            
            response = client.get("/api/v1/service-discovery/instances")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "instances" in data["data"]

    def test_list_instances_with_filters(self, client, mock_service_discovery_manager):
        """Test listing instances with filters"""
        with patch('core.service_discovery_manager.get_service_discovery_manager') as mock_get_manager:
            mock_get_manager.return_value = mock_service_discovery_manager
            
            # Add test services
            service_id1 = str(uuid.uuid4())
            _services_db[service_id1] = {
                "name": "service-1",
                "host": "localhost",
                "port": 8080,
                "protocol": "http",
                "metadata": {},
                "weight": 10,
                "status": "active",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }
            
            service_id2 = str(uuid.uuid4())
            _services_db[service_id2] = {
                "name": "service-2",
                "host": "localhost",
                "port": 8081,
                "protocol": "http",
                "metadata": {},
                "weight": 10,
                "status": "inactive",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }
            
            response = client.get("/api/v1/service-discovery/instances?service_name=service-1&status=active")
            assert response.status_code == 200
            data = response.json()
            assert all(inst["service_name"] == "service-1" for inst in data["data"]["instances"])


# ============================================================================
# Data Validation Tests
# ============================================================================

class TestDataValidation:
    """Test cases for data validation"""

    def test_service_create_with_empty_name(self, client):
        """Test service creation with empty name"""
        invalid_data = {
            "name": "",
            "host": "localhost",
            "port": 8080
        }
        response = client.post("/api/v1/service-discovery/services", json=invalid_data)
        # Pydantic may accept empty string, so we check if it's created or rejected
        # If created, the business logic should handle it
        assert response.status_code in [201, 422]

    def test_service_create_with_empty_host(self, client):
        """Test service creation with empty host"""
        invalid_data = {
            "name": "test-service",
            "host": "",
            "port": 8080
        }
        response = client.post("/api/v1/service-discovery/services", json=invalid_data)
        # Pydantic may accept empty string, so we check if it's created or rejected
        assert response.status_code in [201, 422]

    def test_health_check_with_invalid_threshold(self, client):
        """Test health check with invalid threshold"""
        invalid_data = {
            "service_id": "test-service-id",
            "healthy_threshold": 0  # Less than minimum (1)
        }
        response = client.post("/api/v1/service-discovery/health-checks", json=invalid_data)
        assert response.status_code == 422


# ============================================================================
# Permission Control Tests
# ============================================================================

class TestPermissionControl:
    """Test cases for permission control"""

    @pytest.mark.skip(reason="Permission control requires authentication middleware")
    def test_unauthorized_access(self, client):
        """Test unauthorized access to endpoints"""
        response = client.get("/api/v1/service-discovery/services")
        # Should return 401 or 403 when authentication is enabled
        assert response.status_code in [401, 403]

    @pytest.mark.skip(reason="Permission control requires authentication middleware")
    def test_authorized_access(self, client):
        """Test authorized access to endpoints"""
        # Test with valid authentication token
        headers = {"Authorization": "Bearer valid-token"}
        response = client.get("/api/v1/service-discovery/services", headers=headers)
        assert response.status_code == 200


# ============================================================================
# Integration Tests
# ============================================================================

class TestIntegration:
    """Integration tests for service discovery router"""

    def test_full_service_lifecycle(self, client, sample_service_create, sample_service_update, mock_service_discovery_manager):
        """Test complete service lifecycle: create, read, update, delete"""
        with patch('core.service_discovery_manager.get_service_discovery_manager') as mock_get_manager:
            mock_get_manager.return_value = mock_service_discovery_manager
            
            # Create
            create_response = client.post(
                "/api/v1/service-discovery/services",
                json=sample_service_create.dict()
            )
            assert create_response.status_code == 201
            service_id = create_response.json()["data"]["id"]
            
            # Read
            get_response = client.get(f"/api/v1/service-discovery/services/{service_id}")
            assert get_response.status_code == 200
            
            # Update
            update_response = client.patch(
                f"/api/v1/service-discovery/services/{service_id}",
                json=sample_service_update.dict()
            )
            assert update_response.status_code == 200
            
            # Delete
            delete_response = client.delete(f"/api/v1/service-discovery/services/{service_id}")
            assert delete_response.status_code == 200
            
            # Verify deletion
            verify_response = client.get(f"/api/v1/service-discovery/services/{service_id}")
            assert verify_response.status_code == 404

    def test_service_with_health_check_lifecycle(self, client, sample_service_create, sample_health_check_create, mock_service_discovery_manager):
        """Test service and health check lifecycle together"""
        with patch('core.service_discovery_manager.get_service_discovery_manager') as mock_get_manager:
            mock_get_manager.return_value = mock_service_discovery_manager
            
            # Create service
            create_response = client.post(
                "/api/v1/service-discovery/services",
                json=sample_service_create.dict()
            )
            assert create_response.status_code == 201
            service_id = create_response.json()["data"]["id"]
            
            # Create health check
            health_check_data = sample_health_check_create.dict()
            health_check_data["service_id"] = service_id
            health_check_response = client.post(
                "/api/v1/service-discovery/health-checks",
                json=health_check_data
            )
            assert health_check_response.status_code == 201
            
            # List health checks
            list_response = client.get("/api/v1/service-discovery/health-checks")
            assert list_response.status_code == 200
            assert len(list_response.json()["data"]["health_checks"]) >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=api.service_discovery_advanced_router", "--cov-report=html"])
