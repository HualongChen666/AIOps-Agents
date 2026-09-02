# -*- coding: utf-8 -*-
"""
Integration tests for Service Mesh API endpoints
Tests API endpoints with database integration
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from core.database import SessionLocal, engine
from core.models import Base


@pytest.fixture(scope="function")
def db_session():
    """Create a new database session for each test"""
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """Create a test client with database session"""
    from main import app

    # Override database dependency
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    from core.database import get_db

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


class TestServiceMeshConfigurationsAPI:
    """Test mesh configuration API endpoints"""

    def test_list_configurations_empty(self, client: TestClient):
        """Test listing configurations when database is empty"""
        response = client.get("/api/v1/service-mesh/configurations")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["data"]["configurations"] == []
        assert data["data"]["total"] == 0

    def test_create_configuration(self, client: TestClient):
        """Test creating a mesh configuration"""
        config_data = {
            "name": "test-config",
            "mesh_type": "istio",
            "namespace": "istio-system",
            "profile": "default",
            "auto_injection_enabled": True,
            "mtls_enabled": True,
            "resource_limits": {"cpu": "1000m", "memory": "1Gi"},
            "metadata": {"environment": "test"},
        }

        response = client.post("/api/v1/service-mesh/configurations", json=config_data)

        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "success"
        assert data["data"]["name"] == "test-config"
        assert data["data"]["mesh_type"] == "istio"
        assert data["data"]["id"] is not None
        assert data["data"]["mesh_id"] is not None

    def test_get_configuration(self, client: TestClient):
        """Test getting a configuration by ID"""
        # First create a configuration
        config_data = {
            "name": "test-config",
            "mesh_type": "istio",
            "namespace": "istio-system",
            "profile": "default",
            "auto_injection_enabled": True,
            "mtls_enabled": True,
            "resource_limits": None,
            "metadata": None,
        }

        create_response = client.post("/api/v1/service-mesh/configurations", json=config_data)
        config_id = create_response.json()["data"]["id"]

        # Get the configuration
        response = client.get(f"/api/v1/service-mesh/configurations/{config_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["data"]["id"] == config_id
        assert data["data"]["name"] == "test-config"

    def test_update_configuration(self, client: TestClient):
        """Test updating a configuration"""
        # First create a configuration
        config_data = {
            "name": "test-config",
            "mesh_type": "istio",
            "namespace": "istio-system",
            "profile": "default",
            "auto_injection_enabled": True,
            "mtls_enabled": True,
            "resource_limits": None,
            "metadata": None,
        }

        create_response = client.post("/api/v1/service-mesh/configurations", json=config_data)
        config_id = create_response.json()["data"]["id"]

        # Update the configuration
        update_data = {"name": "updated-config", "namespace": "updated-namespace"}
        response = client.patch(
            f"/api/v1/service-mesh/configurations/{config_id}", json=update_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["data"]["name"] == "updated-config"
        assert data["data"]["namespace"] == "updated-namespace"

    def test_delete_configuration(self, client: TestClient):
        """Test deleting a configuration"""
        # First create a configuration
        config_data = {
            "name": "test-config",
            "mesh_type": "istio",
            "namespace": "istio-system",
            "profile": "default",
            "auto_injection_enabled": True,
            "mtls_enabled": True,
            "resource_limits": None,
            "metadata": None,
        }

        create_response = client.post("/api/v1/service-mesh/configurations", json=config_data)
        config_id = create_response.json()["data"]["id"]

        # Delete the configuration
        response = client.delete(f"/api/v1/service-mesh/configurations/{config_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["data"]["message"] == "Configuration deleted successfully"

        # Verify deletion
        get_response = client.get(f"/api/v1/service-mesh/configurations/{config_id}")
        assert get_response.status_code == 404


class TestTrafficRulesAPI:
    """Test traffic rule API endpoints"""

    def test_list_traffic_rules_empty(self, client: TestClient):
        """Test listing traffic rules when database is empty"""
        response = client.get("/api/v1/service-mesh/traffic")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["data"]["traffic_rules"] == []
        assert data["data"]["total"] == 0

    def test_create_traffic_rule(self, client: TestClient):
        """Test creating a traffic rule"""
        rule_data = {
            "name": "test-rule",
            "service_name": "test-service",
            "match_conditions": {"headers": {"x-version": "v1"}},
            "destination": {"host": "test-service", "subset": "v1"},
            "weight": 100,
            "timeout_seconds": 30,
            "retry_policy": None,
            "fault_injection": None,
            "metadata": None,
        }

        response = client.post("/api/v1/service-mesh/traffic", json=rule_data)

        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "success"
        assert data["data"]["name"] == "test-rule"
        assert data["data"]["service_name"] == "test-service"
        assert data["data"]["id"] is not None

    def test_get_traffic_rule(self, client: TestClient):
        """Test getting a traffic rule by ID"""
        # First create a rule
        rule_data = {
            "name": "test-rule",
            "service_name": "test-service",
            "match_conditions": {},
            "destination": {},
            "weight": 100,
            "timeout_seconds": 30,
            "retry_policy": None,
            "fault_injection": None,
            "metadata": None,
        }

        create_response = client.post("/api/v1/service-mesh/traffic", json=rule_data)
        rule_id = create_response.json()["data"]["id"]

        # Get the rule
        response = client.get(f"/api/v1/service-mesh/traffic/{rule_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["data"]["id"] == rule_id
        assert data["data"]["name"] == "test-rule"

    def test_update_traffic_rule(self, client: TestClient):
        """Test updating a traffic rule"""
        # First create a rule
        rule_data = {
            "name": "test-rule",
            "service_name": "test-service",
            "match_conditions": {},
            "destination": {},
            "weight": 100,
            "timeout_seconds": 30,
            "retry_policy": None,
            "fault_injection": None,
            "metadata": None,
        }

        create_response = client.post("/api/v1/service-mesh/traffic", json=rule_data)
        rule_id = create_response.json()["data"]["id"]

        # Update the rule
        update_data = {"name": "updated-rule", "weight": 50}
        response = client.patch(f"/api/v1/service-mesh/traffic/{rule_id}", json=update_data)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["data"]["name"] == "updated-rule"
        assert data["data"]["weight"] == 50

    def test_delete_traffic_rule(self, client: TestClient):
        """Test deleting a traffic rule"""
        # First create a rule
        rule_data = {
            "name": "test-rule",
            "service_name": "test-service",
            "match_conditions": {},
            "destination": {},
            "weight": 100,
            "timeout_seconds": 30,
            "retry_policy": None,
            "fault_injection": None,
            "metadata": None,
        }

        create_response = client.post("/api/v1/service-mesh/traffic", json=rule_data)
        rule_id = create_response.json()["data"]["id"]

        # Delete the rule
        response = client.delete(f"/api/v1/service-mesh/traffic/{rule_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["data"]["message"] == "Traffic rule deleted successfully"


class TestSecurityPoliciesAPI:
    """Test security policy API endpoints"""

    def test_list_security_policies_empty(self, client: TestClient):
        """Test listing security policies when database is empty"""
        response = client.get("/api/v1/service-mesh/security")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["data"]["security_policies"] == []
        assert data["data"]["total"] == 0

    def test_create_security_policy(self, client: TestClient):
        """Test creating a security policy"""
        policy_data = {
            "name": "test-policy",
            "policy_type": "authentication",
            "target_service": "test-service",
            "mtls_mode": "STRICT",
            "allowed_principals": ["spiffe://cluster.local/ns/default/sa/test"],
            "denied_principals": [],
            "jwt_validation": None,
            "metadata": None,
        }

        response = client.post("/api/v1/service-mesh/security", json=policy_data)

        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "success"
        assert data["data"]["name"] == "test-policy"
        assert data["data"]["policy_type"] == "authentication"
        assert data["data"]["id"] is not None


class TestObservabilityConfigsAPI:
    """Test observability configuration API endpoints"""

    def test_list_observability_configs_empty(self, client: TestClient):
        """Test listing observability configs when database is empty"""
        response = client.get("/api/v1/service-mesh/observability")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["data"]["observability_configs"] == []
        assert data["data"]["total"] == 0

    def test_create_observability_config(self, client: TestClient):
        """Test creating an observability configuration"""
        config_data = {
            "name": "test-config",
            "tracing_enabled": True,
            "metrics_enabled": True,
            "access_logging_enabled": True,
            "sampling_rate": 1.0,
            "prometheus_enabled": True,
            "grafana_enabled": False,
            "metadata": None,
        }

        response = client.post("/api/v1/service-mesh/observability", json=config_data)

        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "success"
        assert data["data"]["name"] == "test-config"
        assert data["data"]["tracing_enabled"] is True
        assert data["data"]["id"] is not None


class TestPoliciesAPI:
    """Test generic policy API endpoints"""

    def test_list_policies_empty(self, client: TestClient):
        """Test listing policies when database is empty"""
        response = client.get("/api/v1/service-mesh/policies")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["data"]["policies"] == []
        assert data["data"]["total"] == 0

    def test_create_policy(self, client: TestClient):
        """Test creating a policy"""
        policy_data = {
            "name": "test-policy",
            "policy_type": "rate-limiting",
            "target_service": "test-service",
            "rules": [{"action": "allow", "condition": "rate < 100"}],
            "enabled": True,
            "metadata": None,
        }

        response = client.post("/api/v1/service-mesh/policies", json=policy_data)

        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "success"
        assert data["data"]["name"] == "test-policy"
        assert data["data"]["policy_type"] == "rate-limiting"
        assert data["data"]["id"] is not None
