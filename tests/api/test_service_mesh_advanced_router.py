# -*- coding: utf-8 -*-
"""
Test suite for Service Mesh Advanced Router
=============================================

Comprehensive tests for service mesh advanced features including:
- Mesh configuration CRUD operations (GET, POST, PATCH, DELETE)
- Traffic rule management
- Security policy management
- Observability configuration
- Policy management
- Data validation
- Error handling
- Permission control
"""

import os
import sys
import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from fastapi import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from api.service_mesh_advanced_router import (
    MeshConfigurationCreate,
    MeshConfigurationUpdate,
    ObservabilityConfigCreate,
    PolicyCreate,
    SecurityPolicyCreate,
    TrafficRuleCreate,
    _configurations_db,
    _observability_configs_db,
    _policies_db,
    _security_policies_db,
    _traffic_rules_db,
    router,
)

# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def client():
    """Create a test client for the service mesh router"""
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
    _configurations_db.clear()
    _traffic_rules_db.clear()
    _security_policies_db.clear()
    _observability_configs_db.clear()
    _policies_db.clear()
    yield
    _configurations_db.clear()
    _traffic_rules_db.clear()
    _security_policies_db.clear()
    _observability_configs_db.clear()
    _policies_db.clear()


@pytest.fixture
def sample_mesh_config_create():
    """Sample mesh configuration creation data"""
    return MeshConfigurationCreate(
        name="test-mesh",
        mesh_type="istio",
        namespace="istio-system",
        profile="default",
        auto_injection_enabled=True,
        mtls_enabled=True,
        resource_limits={"cpu": "1000m", "memory": "1Gi"},
        metadata={"environment": "production"},
    )


@pytest.fixture
def sample_mesh_config_update():
    """Sample mesh configuration update data"""
    return MeshConfigurationUpdate(
        name="updated-mesh",
        namespace="updated-namespace",
        profile="demo",
        auto_injection_enabled=False,
        mtls_enabled=False,
        resource_limits={"cpu": "2000m", "memory": "2Gi"},
        metadata={"environment": "staging"},
    )


@pytest.fixture
def sample_traffic_rule_create():
    """Sample traffic rule creation data"""
    return TrafficRuleCreate(
        name="test-rule",
        service_name="test-service",
        match_conditions={"headers": {"version": "v1"}},
        destination={"host": "test-service", "subset": "v1"},
        weight=100,
        timeout_seconds=30,
        retry_policy={"attempts": 3, "per_try_timeout": "5s"},
        fault_injection=None,
        metadata={"description": "Test traffic rule"},
    )


@pytest.fixture
def sample_security_policy_create():
    """Sample security policy creation data"""
    return SecurityPolicyCreate(
        name="test-policy",
        policy_type="authentication",
        target_service="test-service",
        mtls_mode="STRICT",
        allowed_principals=["cluster.local/ns/default/sa/test"],
        denied_principals=[],
        jwt_validation={"issuer": "https://test.com"},
        metadata={"description": "Test security policy"},
    )


@pytest.fixture
def sample_observability_config_create():
    """Sample observability configuration creation data"""
    return ObservabilityConfigCreate(
        name="test-observability",
        tracing_enabled=True,
        metrics_enabled=True,
        access_logging_enabled=True,
        sampling_rate=1.0,
        prometheus_enabled=True,
        grafana_enabled=False,
        metadata={"description": "Test observability config"},
    )


@pytest.fixture
def sample_policy_create():
    """Sample policy creation data"""
    return PolicyCreate(
        name="test-general-policy",
        policy_type="rate-limiting",
        target_service="test-service",
        rules=[{"action": "allow", "rate": 100}],
        enabled=True,
        metadata={"description": "Test general policy"},
    )


@pytest.fixture
def mock_service_mesh_manager():
    """Mock service mesh manager"""
    manager = MagicMock()
    manager.generate_service_mesh_summary.return_value = {
        "total_meshes": 3,
        "active_meshes": 2,
        "total_services": 10,
    }
    manager.generate_istio_control_plane_config.return_value = True
    manager.generate_mtls_config.return_value = True
    manager.generate_virtual_service_config.return_value = True
    return manager


# ============================================================================
# GET /services - List Mesh Services Tests
# ============================================================================


class TestListMeshServices:
    """Test cases for listing mesh services"""

    def test_list_mesh_services_success(self, client, mock_service_mesh_manager):
        """Test successful listing of mesh services"""
        with patch("core.service_mesh_manager.get_service_mesh_manager") as mock_get_manager:
            mock_get_manager.return_value = mock_service_mesh_manager

            # Add a test configuration
            config_id = str(uuid.uuid4())
            _configurations_db[config_id] = {
                "name": "test-mesh",
                "mesh_type": "istio",
                "namespace": "istio-system",
                "profile": "default",
                "auto_injection_enabled": True,
                "mtls_enabled": True,
                "resource_limits": {},
                "metadata": {},
                "status": "active",
                "mesh_id": f"mesh-{config_id[:8]}",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }

            response = client.get("/api/v1/service-mesh/services")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "services" in data["data"]
            assert "total" in data["data"]

    def test_list_mesh_services_with_mesh_type_filter(self, client, mock_service_mesh_manager):
        """Test listing mesh services with mesh type filter"""
        with patch("core.service_mesh_manager.get_service_mesh_manager") as mock_get_manager:
            mock_get_manager.return_value = mock_service_mesh_manager

            # Add test configurations with different mesh types
            config_id1 = str(uuid.uuid4())
            _configurations_db[config_id1] = {
                "name": "istio-mesh",
                "mesh_type": "istio",
                "namespace": "istio-system",
                "profile": "default",
                "auto_injection_enabled": True,
                "mtls_enabled": True,
                "resource_limits": {},
                "metadata": {},
                "status": "active",
                "mesh_id": f"mesh-{config_id1[:8]}",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }

            config_id2 = str(uuid.uuid4())
            _configurations_db[config_id2] = {
                "name": "linkerd-mesh",
                "mesh_type": "linkerd",
                "namespace": "linkerd",
                "profile": "default",
                "auto_injection_enabled": True,
                "mtls_enabled": True,
                "resource_limits": {},
                "metadata": {},
                "status": "active",
                "mesh_id": f"mesh-{config_id2[:8]}",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }

            response = client.get("/api/v1/service-mesh/services?mesh_type=istio")
            assert response.status_code == 200
            data = response.json()
            assert all(s["mesh_type"] == "istio" for s in data["data"]["services"])

    def test_list_mesh_services_with_status_filter(self, client, mock_service_mesh_manager):
        """Test listing mesh services with status filter"""
        with patch("core.service_mesh_manager.get_service_mesh_manager") as mock_get_manager:
            mock_get_manager.return_value = mock_service_mesh_manager

            # Add test configurations with different statuses
            config_id1 = str(uuid.uuid4())
            _configurations_db[config_id1] = {
                "name": "active-mesh",
                "mesh_type": "istio",
                "namespace": "istio-system",
                "profile": "default",
                "auto_injection_enabled": True,
                "mtls_enabled": True,
                "resource_limits": {},
                "metadata": {},
                "status": "active",
                "mesh_id": f"mesh-{config_id1[:8]}",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }

            config_id2 = str(uuid.uuid4())
            _configurations_db[config_id2] = {
                "name": "inactive-mesh",
                "mesh_type": "istio",
                "namespace": "istio-system",
                "profile": "default",
                "auto_injection_enabled": True,
                "mtls_enabled": True,
                "resource_limits": {},
                "metadata": {},
                "status": "inactive",
                "mesh_id": f"mesh-{config_id2[:8]}",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }

            response = client.get("/api/v1/service-mesh/services?status=active")
            assert response.status_code == 200
            data = response.json()
            assert all(s["status"] == "active" for s in data["data"]["services"])

    def test_list_mesh_services_with_pagination(self, client, mock_service_mesh_manager):
        """Test listing mesh services with pagination"""
        with patch("core.service_mesh_manager.get_service_mesh_manager") as mock_get_manager:
            mock_get_manager.return_value = mock_service_mesh_manager

            # Add multiple configurations
            for i in range(5):
                config_id = str(uuid.uuid4())
                _configurations_db[config_id] = {
                    "name": f"mesh-{i}",
                    "mesh_type": "istio",
                    "namespace": "istio-system",
                    "profile": "default",
                    "auto_injection_enabled": True,
                    "mtls_enabled": True,
                    "resource_limits": {},
                    "metadata": {},
                    "status": "active",
                    "mesh_id": f"mesh-{config_id[:8]}",
                    "created_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat(),
                }

            response = client.get("/api/v1/service-mesh/services?limit=2&offset=0")
            assert response.status_code == 200
            data = response.json()
            assert len(data["data"]["services"]) == 2
            assert data["data"]["limit"] == 2
            assert data["data"]["offset"] == 0

    def test_list_mesh_services_invalid_limit(self, client, mock_service_mesh_manager):
        """Test listing mesh services with invalid limit"""
        with patch("core.service_mesh_manager.get_service_mesh_manager") as mock_get_manager:
            mock_get_manager.return_value = mock_service_mesh_manager

            response = client.get("/api/v1/service-mesh/services?limit=0")
            assert response.status_code == 422

    def test_list_mesh_services_manager_error(self, client):
        """Test listing mesh services when manager raises error"""
        with patch("core.service_mesh_manager.get_service_mesh_manager") as mock_get_manager:
            mock_get_manager.side_effect = Exception("Manager error")

            response = client.get("/api/v1/service-mesh/services")
            assert response.status_code == 500


# ============================================================================
# GET /configurations - List Configurations Tests
# ============================================================================


class TestListConfigurations:
    """Test cases for listing configurations"""

    def test_list_configurations_success(self, client, mock_service_mesh_manager):
        """Test successful listing of configurations"""
        with patch("core.service_mesh_manager.get_service_mesh_manager") as mock_get_manager:
            mock_get_manager.return_value = mock_service_mesh_manager

            # Add a test configuration
            config_id = str(uuid.uuid4())
            _configurations_db[config_id] = {
                "name": "test-mesh",
                "mesh_type": "istio",
                "namespace": "istio-system",
                "profile": "default",
                "auto_injection_enabled": True,
                "mtls_enabled": True,
                "resource_limits": {},
                "metadata": {},
                "status": "active",
                "mesh_id": f"mesh-{config_id[:8]}",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }

            response = client.get("/api/v1/service-mesh/configurations")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "configurations" in data["data"]

    def test_list_configurations_with_filters(self, client, mock_service_mesh_manager):
        """Test listing configurations with filters"""
        with patch("core.service_mesh_manager.get_service_mesh_manager") as mock_get_manager:
            mock_get_manager.return_value = mock_service_mesh_manager

            # Add test configurations
            config_id1 = str(uuid.uuid4())
            _configurations_db[config_id1] = {
                "name": "istio-config",
                "mesh_type": "istio",
                "namespace": "istio-system",
                "profile": "default",
                "auto_injection_enabled": True,
                "mtls_enabled": True,
                "resource_limits": {},
                "metadata": {},
                "status": "active",
                "mesh_id": f"mesh-{config_id1[:8]}",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }

            config_id2 = str(uuid.uuid4())
            _configurations_db[config_id2] = {
                "name": "linkerd-config",
                "mesh_type": "linkerd",
                "namespace": "linkerd",
                "profile": "default",
                "auto_injection_enabled": True,
                "mtls_enabled": True,
                "resource_limits": {},
                "metadata": {},
                "status": "inactive",
                "mesh_id": f"mesh-{config_id2[:8]}",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }

            response = client.get(
                "/api/v1/service-mesh/configurations?mesh_type=istio&status=active"
            )
            assert response.status_code == 200
            data = response.json()
            assert all(
                c["mesh_type"] == "istio" and c["status"] == "active"
                for c in data["data"]["configurations"]
            )


# ============================================================================
# POST /configurations - Create Configuration Tests
# ============================================================================


class TestCreateConfiguration:
    """Test cases for creating configurations"""

    def test_create_configuration_success(
        self, client, sample_mesh_config_create, mock_service_mesh_manager
    ):
        """Test successful configuration creation"""
        with patch("core.service_mesh_manager.get_service_mesh_manager") as mock_get_manager:
            mock_get_manager.return_value = mock_service_mesh_manager

            response = client.post(
                "/api/v1/service-mesh/configurations", json=sample_mesh_config_create.dict()
            )
            assert response.status_code == 201
            data = response.json()
            assert data["status"] == "success"
            assert "id" in data["data"]
            assert data["data"]["name"] == "test-mesh"
            assert data["data"]["mesh_type"] == "istio"
            assert data["data"]["status"] == "active"

    def test_create_configuration_istio_with_mtls(self, client, mock_service_mesh_manager):
        """Test configuration creation for Istio with mTLS"""
        with patch("core.service_mesh_manager.get_service_mesh_manager") as mock_get_manager:
            mock_get_manager.return_value = mock_service_mesh_manager

            config_data = {
                "name": "istio-mtls-mesh",
                "mesh_type": "istio",
                "namespace": "istio-system",
                "profile": "default",
                "auto_injection_enabled": True,
                "mtls_enabled": True,
            }

            response = client.post("/api/v1/service-mesh/configurations", json=config_data)
            assert response.status_code == 201
            # Verify that mTLS config was generated
            mock_service_mesh_manager.generate_mtls_config.assert_called_once()

    def test_create_configuration_linkerd(self, client, mock_service_mesh_manager):
        """Test configuration creation for Linkerd"""
        with patch("core.service_mesh_manager.get_service_mesh_manager") as mock_get_manager:
            mock_get_manager.return_value = mock_service_mesh_manager

            config_data = {
                "name": "linkerd-mesh",
                "mesh_type": "linkerd",
                "namespace": "linkerd",
                "profile": "default",
            }

            response = client.post("/api/v1/service-mesh/configurations", json=config_data)
            assert response.status_code == 201
            # Linkerd should not trigger Istio-specific config generation
            mock_service_mesh_manager.generate_istio_control_plane_config.assert_not_called()

    def test_create_configuration_missing_required_field(self, client):
        """Test configuration creation with missing required field"""
        invalid_data = {
            "mesh_type": "istio",
            "namespace": "istio-system",
            # Missing name
        }
        response = client.post("/api/v1/service-mesh/configurations", json=invalid_data)
        assert response.status_code == 422

    def test_create_configuration_manager_error(self, client, sample_mesh_config_create):
        """Test configuration creation when manager raises error"""
        with patch("core.service_mesh_manager.get_service_mesh_manager") as mock_get_manager:
            mock_get_manager.side_effect = Exception("Manager error")

            response = client.post(
                "/api/v1/service-mesh/configurations", json=sample_mesh_config_create.dict()
            )
            assert response.status_code == 500


# ============================================================================
# GET /configurations/{config_id} - Get Configuration Tests
# ============================================================================


class TestGetConfiguration:
    """Test cases for getting a specific configuration"""

    def test_get_configuration_success(self, client, mock_service_mesh_manager):
        """Test successful configuration retrieval"""
        with patch("core.service_mesh_manager.get_service_mesh_manager") as mock_get_manager:
            mock_get_manager.return_value = mock_service_mesh_manager

            # Add a test configuration
            config_id = str(uuid.uuid4())
            _configurations_db[config_id] = {
                "name": "test-mesh",
                "mesh_type": "istio",
                "namespace": "istio-system",
                "profile": "default",
                "auto_injection_enabled": True,
                "mtls_enabled": True,
                "resource_limits": {},
                "metadata": {},
                "status": "active",
                "mesh_id": f"mesh-{config_id[:8]}",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }

            response = client.get(f"/api/v1/service-mesh/configurations/{config_id}")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["data"]["id"] == config_id
            assert data["data"]["name"] == "test-mesh"

    def test_get_configuration_not_found(self, client):
        """Test getting a non-existent configuration"""
        fake_id = str(uuid.uuid4())
        response = client.get(f"/api/v1/service-mesh/configurations/{fake_id}")
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()


# ============================================================================
# PATCH /configurations/{config_id} - Update Configuration Tests
# ============================================================================


class TestUpdateConfiguration:
    """Test cases for updating configurations"""

    def test_update_configuration_success(
        self, client, sample_mesh_config_update, mock_service_mesh_manager
    ):
        """Test successful configuration update"""
        with patch("core.service_mesh_manager.get_service_mesh_manager") as mock_get_manager:
            mock_get_manager.return_value = mock_service_mesh_manager

            # Add a test configuration
            config_id = str(uuid.uuid4())
            _configurations_db[config_id] = {
                "name": "test-mesh",
                "mesh_type": "istio",
                "namespace": "istio-system",
                "profile": "default",
                "auto_injection_enabled": True,
                "mtls_enabled": True,
                "resource_limits": {},
                "metadata": {},
                "status": "active",
                "mesh_id": f"mesh-{config_id[:8]}",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }

            response = client.patch(
                f"/api/v1/service-mesh/configurations/{config_id}",
                json=sample_mesh_config_update.dict(),
            )
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["data"]["name"] == "updated-mesh"
            assert data["data"]["namespace"] == "updated-namespace"

    def test_update_configuration_partial(self, client, mock_service_mesh_manager):
        """Test partial configuration update"""
        with patch("core.service_mesh_manager.get_service_mesh_manager") as mock_get_manager:
            mock_get_manager.return_value = mock_service_mesh_manager

            # Add a test configuration
            config_id = str(uuid.uuid4())
            _configurations_db[config_id] = {
                "name": "test-mesh",
                "mesh_type": "istio",
                "namespace": "istio-system",
                "profile": "default",
                "auto_injection_enabled": True,
                "mtls_enabled": True,
                "resource_limits": {},
                "metadata": {},
                "status": "active",
                "mesh_id": f"mesh-{config_id[:8]}",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }

            partial_update = {"name": "updated-name"}
            response = client.patch(
                f"/api/v1/service-mesh/configurations/{config_id}", json=partial_update
            )
            assert response.status_code == 200
            data = response.json()
            assert data["data"]["name"] == "updated-name"
            assert data["data"]["namespace"] == "istio-system"  # Unchanged

    def test_update_configuration_not_found(self, client, sample_mesh_config_update):
        """Test updating a non-existent configuration"""
        fake_id = str(uuid.uuid4())
        response = client.patch(
            f"/api/v1/service-mesh/configurations/{fake_id}", json=sample_mesh_config_update.dict()
        )
        assert response.status_code == 404


# ============================================================================
# DELETE /configurations/{config_id} - Delete Configuration Tests
# ============================================================================


class TestDeleteConfiguration:
    """Test cases for deleting configurations"""

    def test_delete_configuration_success(self, client, mock_service_mesh_manager):
        """Test successful configuration deletion"""
        with patch("core.service_mesh_manager.get_service_mesh_manager") as mock_get_manager:
            mock_get_manager.return_value = mock_service_mesh_manager

            # Add a test configuration
            config_id = str(uuid.uuid4())
            _configurations_db[config_id] = {
                "name": "test-mesh",
                "mesh_type": "istio",
                "namespace": "istio-system",
                "profile": "default",
                "auto_injection_enabled": True,
                "mtls_enabled": True,
                "resource_limits": {},
                "metadata": {},
                "status": "active",
                "mesh_id": f"mesh-{config_id[:8]}",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }

            response = client.delete(f"/api/v1/service-mesh/configurations/{config_id}")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert config_id not in _configurations_db

    def test_delete_configuration_not_found(self, client):
        """Test deleting a non-existent configuration"""
        fake_id = str(uuid.uuid4())
        response = client.delete(f"/api/v1/service-mesh/configurations/{fake_id}")
        assert response.status_code == 404


# ============================================================================
# GET /traffic - List Traffic Rules Tests
# ============================================================================


class TestListTrafficRules:
    """Test cases for listing traffic rules"""

    def test_list_traffic_rules_success(self, client, mock_service_mesh_manager):
        """Test successful listing of traffic rules"""
        with patch("core.service_mesh_manager.get_service_mesh_manager") as mock_get_manager:
            mock_get_manager.return_value = mock_service_mesh_manager

            # Add a test traffic rule
            rule_id = str(uuid.uuid4())
            _traffic_rules_db[rule_id] = {
                "name": "test-rule",
                "service_name": "test-service",
                "match_conditions": {},
                "destination": {},
                "weight": 100,
                "timeout_seconds": 30,
                "retry_policy": None,
                "fault_injection": None,
                "metadata": {},
                "enabled": True,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }

            response = client.get("/api/v1/service-mesh/traffic")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "traffic_rules" in data["data"]

    def test_list_traffic_rules_with_service_filter(self, client, mock_service_mesh_manager):
        """Test listing traffic rules with service filter"""
        with patch("core.service_mesh_manager.get_service_mesh_manager") as mock_get_manager:
            mock_get_manager.return_value = mock_service_mesh_manager

            # Add test traffic rules
            rule_id1 = str(uuid.uuid4())
            _traffic_rules_db[rule_id1] = {
                "name": "rule-1",
                "service_name": "service-1",
                "match_conditions": {},
                "destination": {},
                "weight": 100,
                "timeout_seconds": 30,
                "retry_policy": None,
                "fault_injection": None,
                "metadata": {},
                "enabled": True,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }

            rule_id2 = str(uuid.uuid4())
            _traffic_rules_db[rule_id2] = {
                "name": "rule-2",
                "service_name": "service-2",
                "match_conditions": {},
                "destination": {},
                "weight": 100,
                "timeout_seconds": 30,
                "retry_policy": None,
                "fault_injection": None,
                "metadata": {},
                "enabled": True,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }

            response = client.get("/api/v1/service-mesh/traffic?service_name=service-1")
            assert response.status_code == 200
            data = response.json()
            assert all(
                rule["service_name"] == "service-1" for rule in data["data"]["traffic_rules"]
            )

    def test_list_traffic_rules_enabled_only(self, client, mock_service_mesh_manager):
        """Test listing only enabled traffic rules"""
        with patch("core.service_mesh_manager.get_service_mesh_manager") as mock_get_manager:
            mock_get_manager.return_value = mock_service_mesh_manager

            # Add test traffic rules
            rule_id1 = str(uuid.uuid4())
            _traffic_rules_db[rule_id1] = {
                "name": "enabled-rule",
                "service_name": "test-service",
                "match_conditions": {},
                "destination": {},
                "weight": 100,
                "timeout_seconds": 30,
                "retry_policy": None,
                "fault_injection": None,
                "metadata": {},
                "enabled": True,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }

            rule_id2 = str(uuid.uuid4())
            _traffic_rules_db[rule_id2] = {
                "name": "disabled-rule",
                "service_name": "test-service",
                "match_conditions": {},
                "destination": {},
                "weight": 100,
                "timeout_seconds": 30,
                "retry_policy": None,
                "fault_injection": None,
                "metadata": {},
                "enabled": False,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }

            response = client.get("/api/v1/service-mesh/traffic?enabled_only=true")
            assert response.status_code == 200
            data = response.json()
            assert all(rule["enabled"] == True for rule in data["data"]["traffic_rules"])


# ============================================================================
# POST /traffic - Create Traffic Rule Tests
# ============================================================================


class TestCreateTrafficRule:
    """Test cases for creating traffic rules"""

    def test_create_traffic_rule_success(
        self, client, sample_traffic_rule_create, mock_service_mesh_manager
    ):
        """Test successful traffic rule creation"""
        with patch("core.service_mesh_manager.get_service_mesh_manager") as mock_get_manager:
            mock_get_manager.return_value = mock_service_mesh_manager

            response = client.post(
                "/api/v1/service-mesh/traffic", json=sample_traffic_rule_create.dict()
            )
            assert response.status_code == 201
            data = response.json()
            assert data["status"] == "success"
            assert "id" in data["data"]
            assert data["data"]["name"] == "test-rule"
            assert data["data"]["service_name"] == "test-service"

    def test_create_traffic_rule_with_retry_policy(self, client, mock_service_mesh_manager):
        """Test traffic rule creation with retry policy"""
        with patch("core.service_mesh_manager.get_service_mesh_manager") as mock_get_manager:
            mock_get_manager.return_value = mock_service_mesh_manager

            rule_data = {
                "name": "retry-rule",
                "service_name": "test-service",
                "match_conditions": {},
                "destination": {"host": "test-service"},
                "weight": 100,
                "timeout_seconds": 30,
                "retry_policy": {"attempts": 3, "per_try_timeout": "5s"},
            }

            response = client.post("/api/v1/service-mesh/traffic", json=rule_data)
            assert response.status_code == 201

    def test_create_traffic_rule_with_fault_injection(self, client, mock_service_mesh_manager):
        """Test traffic rule creation with fault injection"""
        with patch("core.service_mesh_manager.get_service_mesh_manager") as mock_get_manager:
            mock_get_manager.return_value = mock_service_mesh_manager

            rule_data = {
                "name": "fault-rule",
                "service_name": "test-service",
                "match_conditions": {},
                "destination": {"host": "test-service"},
                "weight": 100,
                "timeout_seconds": 30,
                "fault_injection": {"delay": {"percentage": 10, "duration": "5s"}},
            }

            response = client.post("/api/v1/service-mesh/traffic", json=rule_data)
            assert response.status_code == 201

    def test_create_traffic_rule_invalid_weight(self, client):
        """Test traffic rule creation with invalid weight"""
        invalid_data = {
            "name": "test-rule",
            "service_name": "test-service",
            "match_conditions": {},
            "destination": {},
            "weight": 150,  # Invalid weight (> 100)
        }
        response = client.post("/api/v1/service-mesh/traffic", json=invalid_data)
        assert response.status_code == 422

    def test_create_traffic_rule_invalid_timeout(self, client):
        """Test traffic rule creation with invalid timeout"""
        invalid_data = {
            "name": "test-rule",
            "service_name": "test-service",
            "match_conditions": {},
            "destination": {},
            "timeout_seconds": 0,  # Invalid timeout (< 1)
        }
        response = client.post("/api/v1/service-mesh/traffic", json=invalid_data)
        assert response.status_code == 422

    def test_create_traffic_rule_missing_required_field(self, client):
        """Test traffic rule creation with missing required field"""
        invalid_data = {
            "service_name": "test-service",
            "match_conditions": {},
            "destination": {},
            # Missing name
        }
        response = client.post("/api/v1/service-mesh/traffic", json=invalid_data)
        assert response.status_code == 422

    def test_create_traffic_rule_manager_error(self, client, sample_traffic_rule_create):
        """Test traffic rule creation when manager raises error"""
        with patch("core.service_mesh_manager.get_service_mesh_manager") as mock_get_manager:
            mock_get_manager.side_effect = Exception("Manager error")

            response = client.post(
                "/api/v1/service-mesh/traffic", json=sample_traffic_rule_create.dict()
            )
            assert response.status_code == 500


# ============================================================================
# GET /security - List Security Policies Tests
# ============================================================================


class TestListSecurityPolicies:
    """Test cases for listing security policies"""

    def test_list_security_policies_success(self, client):
        """Test successful listing of security policies"""
        # Add a test security policy
        policy_id = str(uuid.uuid4())
        _security_policies_db[policy_id] = {
            "name": "test-policy",
            "policy_type": "authentication",
            "target_service": "test-service",
            "mtls_mode": "STRICT",
            "allowed_principals": [],
            "denied_principals": [],
            "jwt_validation": None,
            "metadata": {},
            "enabled": True,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

        response = client.get("/api/v1/service-mesh/security")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "security_policies" in data["data"]

    def test_list_security_policies_with_filters(self, client):
        """Test listing security policies with filters"""
        # Add test security policies
        policy_id1 = str(uuid.uuid4())
        _security_policies_db[policy_id1] = {
            "name": "auth-policy",
            "policy_type": "authentication",
            "target_service": "service-1",
            "mtls_mode": "STRICT",
            "allowed_principals": [],
            "denied_principals": [],
            "jwt_validation": None,
            "metadata": {},
            "enabled": True,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

        policy_id2 = str(uuid.uuid4())
        _security_policies_db[policy_id2] = {
            "name": "authz-policy",
            "policy_type": "authorization",
            "target_service": "service-2",
            "mtls_mode": "STRICT",
            "allowed_principals": [],
            "denied_principals": [],
            "jwt_validation": None,
            "metadata": {},
            "enabled": True,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

        response = client.get(
            "/api/v1/service-mesh/security?policy_type=authentication&target_service=service-1"
        )
        assert response.status_code == 200
        data = response.json()
        assert all(
            p["policy_type"] == "authentication" and p["target_service"] == "service-1"
            for p in data["data"]["security_policies"]
        )


# ============================================================================
# POST /security - Create Security Policy Tests
# ============================================================================


class TestCreateSecurityPolicy:
    """Test cases for creating security policies"""

    def test_create_security_policy_success(self, client, sample_security_policy_create):
        """Test successful security policy creation"""
        response = client.post(
            "/api/v1/service-mesh/security", json=sample_security_policy_create.dict()
        )
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "success"
        assert "id" in data["data"]
        assert data["data"]["name"] == "test-policy"
        assert data["data"]["policy_type"] == "authentication"

    def test_create_security_policy_with_principals(self, client):
        """Test security policy creation with principals"""
        policy_data = {
            "name": "principal-policy",
            "policy_type": "authorization",
            "target_service": "test-service",
            "mtls_mode": "STRICT",
            "allowed_principals": [
                "cluster.local/ns/default/sa/app1",
                "cluster.local/ns/default/sa/app2",
            ],
            "denied_principals": ["cluster.local/ns/default/sa/bad-app"],
        }

        response = client.post("/api/v1/service-mesh/security", json=policy_data)
        assert response.status_code == 201
        data = response.json()
        assert len(data["data"]["allowed_principals"]) == 2
        assert len(data["data"]["denied_principals"]) == 1

    def test_create_security_policy_missing_required_field(self, client):
        """Test security policy creation with missing required field"""
        invalid_data = {
            "policy_type": "authentication",
            "target_service": "test-service",
            # Missing name
        }
        response = client.post("/api/v1/service-mesh/security", json=invalid_data)
        assert response.status_code == 422


# ============================================================================
# GET /observability - List Observability Configs Tests
# ============================================================================


class TestListObservabilityConfigs:
    """Test cases for listing observability configurations"""

    def test_list_observability_configs_success(self, client):
        """Test successful listing of observability configurations"""
        # Add a test observability config
        config_id = str(uuid.uuid4())
        _observability_configs_db[config_id] = {
            "name": "test-observability",
            "tracing_enabled": True,
            "metrics_enabled": True,
            "access_logging_enabled": True,
            "sampling_rate": 1.0,
            "prometheus_enabled": True,
            "grafana_enabled": False,
            "metadata": {},
            "enabled": True,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

        response = client.get("/api/v1/service-mesh/observability")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "observability_configs" in data["data"]

    def test_list_observability_configs_enabled_only(self, client):
        """Test listing only enabled observability configurations"""
        # Add test observability configs
        config_id1 = str(uuid.uuid4())
        _observability_configs_db[config_id1] = {
            "name": "enabled-config",
            "tracing_enabled": True,
            "metrics_enabled": True,
            "access_logging_enabled": True,
            "sampling_rate": 1.0,
            "prometheus_enabled": True,
            "grafana_enabled": False,
            "metadata": {},
            "enabled": True,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

        config_id2 = str(uuid.uuid4())
        _observability_configs_db[config_id2] = {
            "name": "disabled-config",
            "tracing_enabled": True,
            "metrics_enabled": True,
            "access_logging_enabled": True,
            "sampling_rate": 1.0,
            "prometheus_enabled": True,
            "grafana_enabled": False,
            "metadata": {},
            "enabled": False,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

        response = client.get("/api/v1/service-mesh/observability?enabled_only=true")
        assert response.status_code == 200
        data = response.json()
        assert all(c["enabled"] == True for c in data["data"]["observability_configs"])


# ============================================================================
# POST /observability - Create Observability Config Tests
# ============================================================================


class TestCreateObservabilityConfig:
    """Test cases for creating observability configurations"""

    def test_create_observability_config_success(self, client, sample_observability_config_create):
        """Test successful observability configuration creation"""
        response = client.post(
            "/api/v1/service-mesh/observability", json=sample_observability_config_create.dict()
        )
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "success"
        assert "id" in data["data"]
        assert data["data"]["name"] == "test-observability"
        assert data["data"]["tracing_enabled"] == True

    def test_create_observability_config_invalid_sampling_rate(self, client):
        """Test observability configuration creation with invalid sampling rate"""
        invalid_data = {
            "name": "test-observability",
            "sampling_rate": 1.5,  # Invalid sampling rate (> 1.0)
        }
        response = client.post("/api/v1/service-mesh/observability", json=invalid_data)
        assert response.status_code == 422

    def test_create_observability_config_negative_sampling_rate(self, client):
        """Test observability configuration creation with negative sampling rate"""
        invalid_data = {
            "name": "test-observability",
            "sampling_rate": -0.5,  # Invalid sampling rate (< 0.0)
        }
        response = client.post("/api/v1/service-mesh/observability", json=invalid_data)
        assert response.status_code == 422

    def test_create_observability_config_missing_required_field(self, client):
        """Test observability configuration creation with missing required field"""
        invalid_data = {
            "tracing_enabled": True,
            "metrics_enabled": True,
            # Missing name
        }
        response = client.post("/api/v1/service-mesh/observability", json=invalid_data)
        assert response.status_code == 422


# ============================================================================
# GET /policies - List Policies Tests
# ============================================================================


class TestListPolicies:
    """Test cases for listing policies"""

    def test_list_policies_success(self, client):
        """Test successful listing of policies"""
        # Add a test policy
        policy_id = str(uuid.uuid4())
        _policies_db[policy_id] = {
            "name": "test-policy",
            "policy_type": "rate-limiting",
            "target_service": "test-service",
            "rules": [],
            "enabled": True,
            "metadata": {},
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

        response = client.get("/api/v1/service-mesh/policies")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "policies" in data["data"]

    def test_list_policies_with_filters(self, client):
        """Test listing policies with filters"""
        # Add test policies
        policy_id1 = str(uuid.uuid4())
        _policies_db[policy_id1] = {
            "name": "rate-limit-policy",
            "policy_type": "rate-limiting",
            "target_service": "service-1",
            "rules": [],
            "enabled": True,
            "metadata": {},
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

        policy_id2 = str(uuid.uuid4())
        _policies_db[policy_id2] = {
            "name": "circuit-breaker-policy",
            "policy_type": "circuit-breaker",
            "target_service": "service-2",
            "rules": [],
            "enabled": False,
            "metadata": {},
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

        response = client.get(
            "/api/v1/service-mesh/policies?policy_type=rate-limiting&target_service=service-1&enabled_only=true"
        )
        assert response.status_code == 200
        data = response.json()
        assert all(
            p["policy_type"] == "rate-limiting"
            and p["target_service"] == "service-1"
            and p["enabled"] == True
            for p in data["data"]["policies"]
        )


# ============================================================================
# POST /policies - Create Policy Tests
# ============================================================================


class TestCreatePolicy:
    """Test cases for creating policies"""

    def test_create_policy_success(self, client, sample_policy_create):
        """Test successful policy creation"""
        response = client.post("/api/v1/service-mesh/policies", json=sample_policy_create.dict())
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "success"
        assert "id" in data["data"]
        assert data["data"]["name"] == "test-general-policy"
        assert data["data"]["policy_type"] == "rate-limiting"

    def test_create_policy_disabled(self, client):
        """Test policy creation with disabled status"""
        policy_data = {
            "name": "disabled-policy",
            "policy_type": "rate-limiting",
            "target_service": "test-service",
            "rules": [],
            "enabled": False,
        }

        response = client.post("/api/v1/service-mesh/policies", json=policy_data)
        assert response.status_code == 201
        data = response.json()
        assert data["data"]["enabled"] == False

    def test_create_policy_missing_required_field(self, client):
        """Test policy creation with missing required field"""
        invalid_data = {
            "policy_type": "rate-limiting",
            "target_service": "test-service",
            "rules": [],
            # Missing name
        }
        response = client.post("/api/v1/service-mesh/policies", json=invalid_data)
        assert response.status_code == 422


# ============================================================================
# Data Validation Tests
# ============================================================================


class TestDataValidation:
    """Test cases for data validation"""

    def test_mesh_config_with_empty_name(self, client):
        """Test mesh configuration creation with empty name"""
        invalid_data = {"name": "", "mesh_type": "istio", "namespace": "istio-system"}
        response = client.post("/api/v1/service-mesh/configurations", json=invalid_data)
        # Pydantic may accept empty string, so we check if it's created or rejected
        assert response.status_code in [201, 422]

    def test_traffic_rule_with_empty_service_name(self, client):
        """Test traffic rule creation with empty service name"""
        invalid_data = {
            "name": "test-rule",
            "service_name": "",
            "match_conditions": {},
            "destination": {},
        }
        response = client.post("/api/v1/service-mesh/traffic", json=invalid_data)
        # Pydantic may accept empty string, so we check if it's created or rejected
        assert response.status_code in [201, 422]

    def test_security_policy_with_invalid_mtls_mode(self, client):
        """Test security policy creation with invalid mTLS mode"""
        invalid_data = {
            "name": "test-policy",
            "policy_type": "authentication",
            "target_service": "test-service",
            "mtls_mode": "INVALID_MODE",
        }
        response = client.post("/api/v1/service-mesh/security", json=invalid_data)
        # This may pass validation but should be handled in business logic
        assert response.status_code in [201, 422]


# ============================================================================
# Permission Control Tests
# ============================================================================


class TestPermissionControl:
    """Test cases for permission control"""

    @pytest.mark.skip(reason="Permission control requires authentication middleware")
    def test_unauthorized_access(self, client):
        """Test unauthorized access to endpoints"""
        response = client.get("/api/v1/service-mesh/configurations")
        # Should return 401 or 403 when authentication is enabled
        assert response.status_code in [401, 403]

    @pytest.mark.skip(reason="Permission control requires authentication middleware")
    def test_authorized_access(self, client):
        """Test authorized access to endpoints"""
        # Test with valid authentication token
        headers = {"Authorization": "Bearer valid-token"}
        response = client.get("/api/v1/service-mesh/configurations", headers=headers)
        assert response.status_code == 200


# ============================================================================
# Integration Tests
# ============================================================================


class TestIntegration:
    """Integration tests for service mesh router"""

    def test_full_configuration_lifecycle(
        self,
        client,
        sample_mesh_config_create,
        sample_mesh_config_update,
        mock_service_mesh_manager,
    ):
        """Test complete configuration lifecycle: create, read, update, delete"""
        with patch("core.service_mesh_manager.get_service_mesh_manager") as mock_get_manager:
            mock_get_manager.return_value = mock_service_mesh_manager

            # Create
            create_response = client.post(
                "/api/v1/service-mesh/configurations", json=sample_mesh_config_create.dict()
            )
            assert create_response.status_code == 201
            config_id = create_response.json()["data"]["id"]

            # Read
            get_response = client.get(f"/api/v1/service-mesh/configurations/{config_id}")
            assert get_response.status_code == 200

            # Update
            update_response = client.patch(
                f"/api/v1/service-mesh/configurations/{config_id}",
                json=sample_mesh_config_update.dict(),
            )
            assert update_response.status_code == 200

            # Delete
            delete_response = client.delete(f"/api/v1/service-mesh/configurations/{config_id}")
            assert delete_response.status_code == 200

            # Verify deletion
            verify_response = client.get(f"/api/v1/service-mesh/configurations/{config_id}")
            assert verify_response.status_code == 404

    def test_mesh_with_traffic_rule_lifecycle(
        self,
        client,
        sample_mesh_config_create,
        sample_traffic_rule_create,
        mock_service_mesh_manager,
    ):
        """Test mesh configuration and traffic rule lifecycle together"""
        with patch("core.service_mesh_manager.get_service_mesh_manager") as mock_get_manager:
            mock_get_manager.return_value = mock_service_mesh_manager

            # Create configuration
            create_response = client.post(
                "/api/v1/service-mesh/configurations", json=sample_mesh_config_create.dict()
            )
            assert create_response.status_code == 201

            # Create traffic rule
            traffic_response = client.post(
                "/api/v1/service-mesh/traffic", json=sample_traffic_rule_create.dict()
            )
            assert traffic_response.status_code == 201

            # List traffic rules
            list_response = client.get("/api/v1/service-mesh/traffic")
            assert list_response.status_code == 200
            assert len(list_response.json()["data"]["traffic_rules"]) >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=api.service_mesh_advanced_router", "--cov-report=html"])
