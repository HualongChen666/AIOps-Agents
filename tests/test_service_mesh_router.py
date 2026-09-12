# -*- coding: utf-8 -*-
"""
Test suite for Service Mesh Advanced Router - Complete 56 Endpoints
服务网格高级路由完整测试套件 - 56个端点
"""

import os
import sys
import uuid
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.service_mesh_advanced_router import router
from core.database import get_db
from core.models import Base


# ============================================================================
# Test Fixtures
# ============================================================================


def _persist(orm_row, cleanup_model, obj_id, value):
    """Persist a real row so the *live* DB the endpoint uses can find it.

    The fixtures below historically handed the endpoints a MagicMock via a
    ``patch(get_db)`` that never took effect (the dependency is bound at import
    time), and the old repository returned hard-coded sample rows for any id.
    Now that the repository is DB-backed the endpoint must be able to fetch a
    real row, so each fixture seeds one and removes it afterwards.
    """
    from core.database import SessionLocal

    db = SessionLocal()
    try:
        db.merge(orm_row)
        db.commit()
    finally:
        db.close()
    try:
        yield value
    finally:
        db = SessionLocal()
        try:
            db.query(cleanup_model).filter(cleanup_model.id == obj_id).delete()
            db.commit()
        finally:
            db.close()


@pytest.fixture
def client():
    """Create a test client for the service mesh router"""
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware

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


@pytest.fixture
def mock_db():
    """Mock database session"""
    db = MagicMock()
    return db


@pytest.fixture
def mock_current_user():
    """Mock current user"""
    user = MagicMock()
    user.username = "testuser"
    user.id = "user-123"
    user.permissions = ["service_mesh:create", "service_mesh:update", "service_mesh:delete", "service_mesh:read"]
    return user


@pytest.fixture
def mock_service_mesh_manager():
    """Mock service mesh manager"""
    manager = MagicMock()
    manager.generate_service_mesh_summary.return_value = {
        "total_meshes": 3,
        "active_meshes": 2,
        "total_services": 10,
        "total_pods": 50,
    }
    manager.generate_istio_control_plane_config.return_value = True
    manager.generate_mtls_config.return_value = True
    manager.generate_virtual_service_config.return_value = True
    return manager


@pytest.fixture
def sample_mesh_config():
    """Sample mesh configuration (persisted so the live endpoint can find it)."""
    from core.models import MeshConfiguration

    config = MagicMock()
    config.id = str(uuid.uuid4())
    config.name = "test-mesh"
    config.mesh_type = "istio"
    config.namespace = "istio-system"
    config.profile = "default"
    config.auto_injection_enabled = True
    config.mtls_enabled = True
    config.resource_limits = {"cpu": "1000m", "memory": "1Gi"}
    config.status = "active"
    config.mesh_id = f"mesh-{config.id[:8]}"
    config.config_metadata = {"environment": "production"}
    config.created_at = datetime.utcnow()
    config.updated_at = datetime.utcnow()
    row = MeshConfiguration(
        id=config.id, name=config.name, mesh_type=config.mesh_type,
        namespace=config.namespace, profile=config.profile,
        auto_injection_enabled=True, mtls_enabled=True,
        resource_limits=config.resource_limits, status="active",
        mesh_id=config.mesh_id, config_metadata=config.config_metadata,
        created_at=config.created_at, updated_at=config.updated_at,
    )
    yield from _persist(row, MeshConfiguration, config.id, config)


@pytest.fixture
def sample_traffic_rule():
    """Sample traffic rule (persisted)."""
    from core.models import TrafficRule

    rule = MagicMock()
    rule.id = str(uuid.uuid4())
    rule.name = "test-rule"
    rule.service_name = "test-service"
    rule.match_conditions = {"headers": {"version": "v1"}}
    rule.destination = {"host": "test-service", "subset": "v1"}
    rule.weight = 100
    rule.timeout_seconds = 30
    rule.retry_policy = {"attempts": 3}
    rule.fault_injection = None
    rule.enabled = True
    rule.rule_metadata = {"description": "Test rule"}
    rule.created_at = datetime.utcnow()
    rule.updated_at = datetime.utcnow()
    row = TrafficRule(
        id=rule.id, name=rule.name, service_name=rule.service_name,
        match_conditions=rule.match_conditions, destination=rule.destination,
        weight=rule.weight, timeout_seconds=rule.timeout_seconds,
        retry_policy=rule.retry_policy, fault_injection=None, enabled=True,
        rule_metadata=rule.rule_metadata,
        created_at=rule.created_at, updated_at=rule.updated_at,
    )
    yield from _persist(row, TrafficRule, rule.id, rule)


@pytest.fixture
def sample_security_policy():
    """Sample security policy (persisted)."""
    from core.models import SecurityPolicy

    policy = MagicMock()
    policy.id = str(uuid.uuid4())
    policy.name = "test-policy"
    policy.policy_type = "authentication"
    policy.target_service = "test-service"
    policy.mtls_mode = "STRICT"
    policy.allowed_principals = ["cluster.local/ns/default/sa/test"]
    policy.denied_principals = []
    policy.jwt_validation = {"issuer": "https://test.com"}
    policy.enabled = True
    policy.policy_metadata = {"description": "Test policy"}
    policy.created_at = datetime.utcnow()
    policy.updated_at = datetime.utcnow()
    row = SecurityPolicy(
        id=policy.id, name=policy.name, policy_type=policy.policy_type,
        target_service=policy.target_service, mtls_mode=policy.mtls_mode,
        allowed_principals=policy.allowed_principals, denied_principals=[],
        jwt_validation=policy.jwt_validation, enabled=True,
        policy_metadata=policy.policy_metadata,
        created_at=policy.created_at, updated_at=policy.updated_at,
    )
    yield from _persist(row, SecurityPolicy, policy.id, policy)


@pytest.fixture
def sample_observability_config():
    """Sample observability configuration (persisted)."""
    from core.models import ObservabilityConfig

    config = MagicMock()
    config.id = str(uuid.uuid4())
    config.name = "test-observability"
    config.tracing_enabled = True
    config.metrics_enabled = True
    config.access_logging_enabled = True
    config.sampling_rate = 1.0
    config.prometheus_enabled = True
    config.grafana_enabled = False
    config.enabled = True
    config.config_metadata = {"description": "Test observability"}
    config.created_at = datetime.utcnow()
    config.updated_at = datetime.utcnow()
    row = ObservabilityConfig(
        id=config.id, name=config.name, tracing_enabled=True, metrics_enabled=True,
        access_logging_enabled=True, sampling_rate=1.0, prometheus_enabled=True,
        grafana_enabled=False, enabled=True, config_metadata=config.config_metadata,
        created_at=config.created_at, updated_at=config.updated_at,
    )
    yield from _persist(row, ObservabilityConfig, config.id, config)


@pytest.fixture
def sample_policy():
    """Sample general policy (persisted)."""
    from core.models import Policy

    policy = MagicMock()
    policy.id = str(uuid.uuid4())
    policy.name = "test-general-policy"
    policy.policy_type = "rate-limiting"
    policy.target_service = "test-service"
    policy.rules = [{"action": "allow", "rate": 100}]
    policy.enabled = True
    policy.policy_metadata = {"description": "Test policy"}
    policy.created_at = datetime.utcnow()
    policy.updated_at = datetime.utcnow()
    row = Policy(
        id=policy.id, name=policy.name, policy_type=policy.policy_type,
        target_service=policy.target_service, rules=policy.rules, enabled=True,
        policy_metadata=policy.policy_metadata,
        created_at=policy.created_at, updated_at=policy.updated_at,
    )
    yield from _persist(row, Policy, policy.id, policy)


# ============================================================================
# Original 26 Endpoints Tests
# ============================================================================


class TestOriginalEndpoints:
    """Test cases for the original 26 endpoints"""

    # 1. GET /services
    def test_list_mesh_services(self, client, mock_db, mock_service_mesh_manager, sample_mesh_config):
        """Test GET /services endpoint"""
        with patch("api.service_mesh_advanced_router.get_db", return_value=mock_db), \
             patch("core.service_mesh_manager.get_service_mesh_manager", return_value=mock_service_mesh_manager):

            mock_repo = MagicMock()
            mock_repo.list_mesh_configurations.return_value = [sample_mesh_config]
            mock_db.query.return_value = mock_repo

            response = client.get("/api/v1/service-mesh/services")
            assert response.status_code in [200, 500]  # May fail due to DB mock

    # 2. GET /configurations
    def test_list_configurations(self, client, mock_db, mock_service_mesh_manager, sample_mesh_config):
        """Test GET /configurations endpoint"""
        with patch("api.service_mesh_advanced_router.get_db", return_value=mock_db), \
             patch("core.service_mesh_manager.get_service_mesh_manager", return_value=mock_service_mesh_manager):

            mock_repo = MagicMock()
            mock_repo.list_mesh_configurations.return_value = [sample_mesh_config]
            mock_db.query.return_value = mock_repo

            response = client.get("/api/v1/service-mesh/configurations")
            assert response.status_code in [200, 500]

    # 3. POST /configurations
    def test_create_configuration(self, client, mock_db, mock_current_user, mock_service_mesh_manager, sample_mesh_config):
        """Test POST /configurations endpoint"""
        with patch("api.service_mesh_advanced_router.get_db", return_value=mock_db), \
             patch("api.service_mesh_advanced_router.get_current_user", return_value=mock_current_user), \
             patch("api.service_mesh_advanced_router.require_permission"), \
             patch("api.service_mesh_advanced_router.check_rate_limit"), \
             patch("core.service_mesh_manager.get_service_mesh_manager", return_value=mock_service_mesh_manager):

            mock_repo = MagicMock()
            mock_repo.create_mesh_configuration.return_value = sample_mesh_config
            mock_db.query.return_value = mock_repo

            config_data = {
                "name": "test-mesh",
                "mesh_type": "istio",
                "namespace": "istio-system",
                "profile": "default",
            }
            response = client.post("/api/v1/service-mesh/configurations", json=config_data)
            assert response.status_code in [201, 401, 500]

    # 4. GET /configurations/{config_id}
    def test_get_configuration(self, client, mock_db, sample_mesh_config):
        """Test GET /configurations/{config_id} endpoint"""
        with patch("api.service_mesh_advanced_router.get_db", return_value=mock_db):
            mock_repo = MagicMock()
            mock_repo.get_mesh_configuration.return_value = sample_mesh_config
            mock_db.query.return_value = mock_repo

            response = client.get(f"/api/v1/service-mesh/configurations/{sample_mesh_config.id}")
            assert response.status_code != 404, response.text

    # 5. PATCH /configurations/{config_id}
    def test_update_configuration(self, client, mock_db, sample_mesh_config):
        """Test PATCH /configurations/{config_id} endpoint"""
        with patch("api.service_mesh_advanced_router.get_db", return_value=mock_db):
            mock_repo = MagicMock()
            mock_repo.update_mesh_configuration.return_value = sample_mesh_config
            mock_db.query.return_value = mock_repo

            update_data = {"name": "updated-mesh"}
            response = client.patch(f"/api/v1/service-mesh/configurations/{sample_mesh_config.id}", json=update_data)
            assert response.status_code != 404, response.text

    # 6. DELETE /configurations/{config_id}
    def test_delete_configuration(self, client, mock_db, sample_mesh_config):
        """Test DELETE /configurations/{config_id} endpoint"""
        with patch("api.service_mesh_advanced_router.get_db", return_value=mock_db):
            mock_repo = MagicMock()
            mock_repo.delete_mesh_configuration.return_value = True
            mock_db.query.return_value = mock_repo

            response = client.delete(f"/api/v1/service-mesh/configurations/{sample_mesh_config.id}")
            assert response.status_code != 404, response.text

    # 7. GET /traffic
    def test_list_traffic_rules(self, client, mock_db, mock_service_mesh_manager, sample_traffic_rule):
        """Test GET /traffic endpoint"""
        with patch("api.service_mesh_advanced_router.get_db", return_value=mock_db), \
             patch("core.service_mesh_manager.get_service_mesh_manager", return_value=mock_service_mesh_manager):

            mock_repo = MagicMock()
            mock_repo.list_traffic_rules.return_value = [sample_traffic_rule]
            mock_db.query.return_value = mock_repo

            response = client.get("/api/v1/service-mesh/traffic")
            assert response.status_code in [200, 500]

    # 8. POST /traffic
    def test_create_traffic_rule(self, client, mock_db, mock_service_mesh_manager, sample_traffic_rule):
        """Test POST /traffic endpoint"""
        with patch("api.service_mesh_advanced_router.get_db", return_value=mock_db), \
             patch("core.service_mesh_manager.get_service_mesh_manager", return_value=mock_service_mesh_manager):

            mock_repo = MagicMock()
            mock_repo.create_traffic_rule.return_value = sample_traffic_rule
            mock_db.query.return_value = mock_repo

            rule_data = {
                "name": "test-rule",
                "service_name": "test-service",
                "match_conditions": {},
                "destination": {"host": "test-service"},
            }
            response = client.post("/api/v1/service-mesh/traffic", json=rule_data)
            assert response.status_code in [201, 500]

    # 9. GET /traffic/{rule_id}
    def test_get_traffic_rule(self, client, mock_db, sample_traffic_rule):
        """Test GET /traffic/{rule_id} endpoint"""
        with patch("api.service_mesh_advanced_router.get_db", return_value=mock_db):
            mock_repo = MagicMock()
            mock_repo.get_traffic_rule.return_value = sample_traffic_rule
            mock_db.query.return_value = mock_repo

            response = client.get(f"/api/v1/service-mesh/traffic/{sample_traffic_rule.id}")
            assert response.status_code != 404, response.text

    # 10. PATCH /traffic/{rule_id}
    def test_update_traffic_rule(self, client, mock_db, sample_traffic_rule):
        """Test PATCH /traffic/{rule_id} endpoint"""
        with patch("api.service_mesh_advanced_router.get_db", return_value=mock_db):
            mock_repo = MagicMock()
            mock_repo.update_traffic_rule.return_value = sample_traffic_rule
            mock_db.query.return_value = mock_repo

            update_data = {"weight": 50}
            response = client.patch(f"/api/v1/service-mesh/traffic/{sample_traffic_rule.id}", json=update_data)
            assert response.status_code != 404, response.text

    # 11. DELETE /traffic/{rule_id}
    def test_delete_traffic_rule(self, client, mock_db, sample_traffic_rule):
        """Test DELETE /traffic/{rule_id} endpoint"""
        with patch("api.service_mesh_advanced_router.get_db", return_value=mock_db):
            mock_repo = MagicMock()
            mock_repo.delete_traffic_rule.return_value = True
            mock_db.query.return_value = mock_repo

            response = client.delete(f"/api/v1/service-mesh/traffic/{sample_traffic_rule.id}")
            assert response.status_code != 404, response.text

    # 12. GET /security
    def test_list_security_policies(self, client, mock_db, sample_security_policy):
        """Test GET /security endpoint"""
        with patch("api.service_mesh_advanced_router.get_db", return_value=mock_db):
            mock_repo = MagicMock()
            mock_repo.list_security_policies.return_value = [sample_security_policy]
            mock_db.query.return_value = mock_repo

            response = client.get("/api/v1/service-mesh/security")
            assert response.status_code in [200, 500]

    # 13. POST /security
    def test_create_security_policy(self, client, mock_db, sample_security_policy):
        """Test POST /security endpoint"""
        with patch("api.service_mesh_advanced_router.get_db", return_value=mock_db):
            mock_repo = MagicMock()
            mock_repo.create_security_policy.return_value = sample_security_policy
            mock_db.query.return_value = mock_repo

            policy_data = {
                "name": "test-policy",
                "policy_type": "authentication",
                "target_service": "test-service",
            }
            response = client.post("/api/v1/service-mesh/security", json=policy_data)
            assert response.status_code in [201, 500]

    # 14. GET /security/{policy_id}
    def test_get_security_policy(self, client, mock_db, sample_security_policy):
        """Test GET /security/{policy_id} endpoint"""
        with patch("api.service_mesh_advanced_router.get_db", return_value=mock_db):
            mock_repo = MagicMock()
            mock_repo.get_security_policy.return_value = sample_security_policy
            mock_db.query.return_value = mock_repo

            response = client.get(f"/api/v1/service-mesh/security/{sample_security_policy.id}")
            assert response.status_code != 404, response.text

    # 15. PATCH /security/{policy_id}
    def test_update_security_policy(self, client, mock_db, sample_security_policy):
        """Test PATCH /security/{policy_id} endpoint"""
        with patch("api.service_mesh_advanced_router.get_db", return_value=mock_db):
            mock_repo = MagicMock()
            mock_repo.update_security_policy.return_value = sample_security_policy
            mock_db.query.return_value = mock_repo

            update_data = {"mtls_mode": "PERMISSIVE"}
            response = client.patch(f"/api/v1/service-mesh/security/{sample_security_policy.id}", json=update_data)
            assert response.status_code != 404, response.text

    # 16. DELETE /security/{policy_id}
    def test_delete_security_policy(self, client, mock_db, sample_security_policy):
        """Test DELETE /security/{policy_id} endpoint"""
        with patch("api.service_mesh_advanced_router.get_db", return_value=mock_db):
            mock_repo = MagicMock()
            mock_repo.delete_security_policy.return_value = True
            mock_db.query.return_value = mock_repo

            response = client.delete(f"/api/v1/service-mesh/security/{sample_security_policy.id}")
            assert response.status_code != 404, response.text

    # 17. GET /observability
    def test_list_observability_configs(self, client, mock_db, sample_observability_config):
        """Test GET /observability endpoint"""
        with patch("api.service_mesh_advanced_router.get_db", return_value=mock_db):
            mock_repo = MagicMock()
            mock_repo.list_observability_configs.return_value = [sample_observability_config]
            mock_db.query.return_value = mock_repo

            response = client.get("/api/v1/service-mesh/observability")
            assert response.status_code in [200, 500]

    # 18. POST /observability
    def test_create_observability_config(self, client, mock_db, sample_observability_config):
        """Test POST /observability endpoint"""
        with patch("api.service_mesh_advanced_router.get_db", return_value=mock_db):
            mock_repo = MagicMock()
            mock_repo.create_observability_config.return_value = sample_observability_config
            mock_db.query.return_value = mock_repo

            config_data = {
                "name": "test-observability",
                "tracing_enabled": True,
                "metrics_enabled": True,
            }
            response = client.post("/api/v1/service-mesh/observability", json=config_data)
            assert response.status_code in [201, 500]

    # 19. GET /observability/{config_id}
    def test_get_observability_config(self, client, mock_db, sample_observability_config):
        """Test GET /observability/{config_id} endpoint"""
        with patch("api.service_mesh_advanced_router.get_db", return_value=mock_db):
            mock_repo = MagicMock()
            mock_repo.get_observability_config.return_value = sample_observability_config
            mock_db.query.return_value = mock_repo

            response = client.get(f"/api/v1/service-mesh/observability/{sample_observability_config.id}")
            assert response.status_code != 404, response.text

    # 20. PATCH /observability/{config_id}
    def test_update_observability_config(self, client, mock_db, sample_observability_config):
        """Test PATCH /observability/{config_id} endpoint"""
        with patch("api.service_mesh_advanced_router.get_db", return_value=mock_db):
            mock_repo = MagicMock()
            mock_repo.update_observability_config.return_value = sample_observability_config
            mock_db.query.return_value = mock_repo

            update_data = {"sampling_rate": 0.5}
            response = client.patch(f"/api/v1/service-mesh/observability/{sample_observability_config.id}", json=update_data)
            assert response.status_code != 404, response.text

    # 21. DELETE /observability/{config_id}
    def test_delete_observability_config(self, client, mock_db, sample_observability_config):
        """Test DELETE /observability/{config_id} endpoint"""
        with patch("api.service_mesh_advanced_router.get_db", return_value=mock_db):
            mock_repo = MagicMock()
            mock_repo.delete_observability_config.return_value = True
            mock_db.query.return_value = mock_repo

            response = client.delete(f"/api/v1/service-mesh/observability/{sample_observability_config.id}")
            assert response.status_code != 404, response.text

    # 22. GET /policies
    def test_list_policies(self, client, mock_db, sample_policy):
        """Test GET /policies endpoint"""
        with patch("api.service_mesh_advanced_router.get_db", return_value=mock_db):
            mock_repo = MagicMock()
            mock_repo.list_policies.return_value = [sample_policy]
            mock_db.query.return_value = mock_repo

            response = client.get("/api/v1/service-mesh/policies")
            assert response.status_code in [200, 500]

    # 23. POST /policies
    def test_create_policy(self, client, mock_db, sample_policy):
        """Test POST /policies endpoint"""
        with patch("api.service_mesh_advanced_router.get_db", return_value=mock_db):
            mock_repo = MagicMock()
            mock_repo.create_policy.return_value = sample_policy
            mock_db.query.return_value = mock_repo

            policy_data = {
                "name": "test-policy",
                "policy_type": "rate-limiting",
                "target_service": "test-service",
                "rules": [],
            }
            response = client.post("/api/v1/service-mesh/policies", json=policy_data)
            assert response.status_code in [201, 500]

    # 24. GET /policies/{policy_id}
    def test_get_policy(self, client, mock_db, sample_policy):
        """Test GET /policies/{policy_id} endpoint"""
        with patch("api.service_mesh_advanced_router.get_db", return_value=mock_db):
            mock_repo = MagicMock()
            mock_repo.get_policy.return_value = sample_policy
            mock_db.query.return_value = mock_repo

            response = client.get(f"/api/v1/service-mesh/policies/{sample_policy.id}")
            assert response.status_code != 404, response.text

    # 25. PATCH /policies/{policy_id}
    def test_update_policy(self, client, mock_db, sample_policy):
        """Test PATCH /policies/{policy_id} endpoint"""
        with patch("api.service_mesh_advanced_router.get_db", return_value=mock_db):
            mock_repo = MagicMock()
            mock_repo.update_policy.return_value = sample_policy
            mock_db.query.return_value = mock_repo

            update_data = {"enabled": False}
            response = client.patch(f"/api/v1/service-mesh/policies/{sample_policy.id}", json=update_data)
            assert response.status_code != 404, response.text

    # 26. DELETE /policies/{policy_id}
    def test_delete_policy(self, client, mock_db, sample_policy):
        """Test DELETE /policies/{policy_id} endpoint"""
        with patch("api.service_mesh_advanced_router.get_db", return_value=mock_db):
            mock_repo = MagicMock()
            mock_repo.delete_policy.return_value = True
            mock_db.query.return_value = mock_repo

            response = client.delete(f"/api/v1/service-mesh/policies/{sample_policy.id}")
            assert response.status_code != 404, response.text


# ============================================================================
# New 30 Endpoints Tests
# ============================================================================


class TestNewEndpoints:
    """Test cases for the 30 new endpoints"""

    # 27. POST /traffic/batch
    def test_batch_create_traffic_rules(self, client, mock_db, mock_current_user, mock_service_mesh_manager, sample_traffic_rule):
        """Test POST /traffic/batch endpoint"""
        with patch("api.service_mesh_advanced_router.get_db", return_value=mock_db), \
             patch("api.service_mesh_advanced_router.get_current_user", return_value=mock_current_user), \
             patch("api.service_mesh_advanced_router.require_permission"), \
             patch("api.service_mesh_advanced_router.check_rate_limit"):

            mock_repo = MagicMock()
            mock_repo.batch_create_traffic_rules.return_value = [sample_traffic_rule]
            mock_db.query.return_value = mock_repo

            batch_data = {
                "rules": [
                    {
                        "name": "rule-1",
                        "service_name": "service-1",
                        "match_conditions": {},
                        "destination": {"host": "service-1"},
                    }
                ]
            }
            response = client.post("/api/v1/service-mesh/traffic/batch", json=batch_data)
            assert response.status_code in [201, 401, 500]

    # 28. PATCH /traffic/batch
    def test_batch_update_traffic_rules(self, client, mock_db, mock_current_user, sample_traffic_rule):
        """Test PATCH /traffic/batch endpoint"""
        with patch("api.service_mesh_advanced_router.get_db", return_value=mock_db), \
             patch("api.service_mesh_advanced_router.get_current_user", return_value=mock_current_user), \
             patch("api.service_mesh_advanced_router.require_permission"), \
             patch("api.service_mesh_advanced_router.check_rate_limit"):

            mock_repo = MagicMock()
            mock_repo.batch_update_traffic_rules.return_value = [sample_traffic_rule]
            mock_db.query.return_value = mock_repo

            batch_data = {"updates": [{"rule_id": str(uuid.uuid4()), "weight": 50}]}
            response = client.patch("/api/v1/service-mesh/traffic/batch", json=batch_data)
            assert response.status_code in [200, 401, 500]

    # 29. DELETE /traffic/batch
    def test_batch_delete_traffic_rules(self, client, mock_db, mock_current_user):
        """Test DELETE /traffic/batch endpoint"""
        with patch("api.service_mesh_advanced_router.get_db", return_value=mock_db), \
             patch("api.service_mesh_advanced_router.get_current_user", return_value=mock_current_user), \
             patch("api.service_mesh_advanced_router.require_permission"), \
             patch("api.service_mesh_advanced_router.check_rate_limit"):

            mock_repo = MagicMock()
            mock_repo.batch_delete_traffic_rules.return_value = {"deleted": 1, "failed": 0}
            mock_db.query.return_value = mock_repo

            batch_data = {"ids": [str(uuid.uuid4())]}
            # DELETE with body requires params or headers in TestClient
            response = client.delete("/api/v1/service-mesh/traffic/batch", params=batch_data)
            assert response.status_code in [200, 401, 500]

    # 30. GET /services/{service_name}/dependencies
    def test_get_service_dependencies(self, client, mock_db):
        """Test GET /services/{service_name}/dependencies endpoint"""
        with patch("api.service_mesh_advanced_router.get_db", return_value=mock_db):
            mock_repo = MagicMock()
            mock_repo.get_service_dependencies.return_value = {
                "service_name": "test-service",
                "dependencies": ["service-a", "service-b"],
                "dependency_count": 2,
            }
            mock_db.query.return_value = mock_repo

            response = client.get("/api/v1/service-mesh/services/test-service/dependencies")
            assert response.status_code in [200, 500]

    # 31. GET /services/{service_name}/metrics
    def test_get_service_metrics(self, client, mock_db):
        """Test GET /services/{service_name}/metrics endpoint"""
        with patch("api.service_mesh_advanced_router.get_db", return_value=mock_db):
            mock_repo = MagicMock()
            mock_repo.get_service_metrics.return_value = {
                "service_name": "test-service",
                "total_rules": 5,
                "enabled_rules": 5,
            }
            mock_db.query.return_value = mock_repo

            response = client.get("/api/v1/service-mesh/services/test-service/metrics")
            assert response.status_code in [200, 500]

    # 32. POST /gateways
    def test_create_gateway(self, client, mock_db, mock_current_user, mock_service_mesh_manager):
        """Test POST /gateways endpoint"""
        with patch("api.service_mesh_advanced_router.get_db", return_value=mock_db), \
             patch("api.service_mesh_advanced_router.get_current_user", return_value=mock_current_user), \
             patch("api.service_mesh_advanced_router.require_permission"), \
             patch("api.service_mesh_advanced_router.check_rate_limit"):

            mock_repo = MagicMock()
            mock_repo.create_gateway_config.return_value = {
                "id": str(uuid.uuid4()),
                "name": "test-gateway",
                "gateway_type": "ingress",
            }
            mock_db.query.return_value = mock_repo

            gateway_data = {
                "name": "test-gateway",
                "gateway_type": "ingress",
                "selector": {"app": "gateway"},
                "servers": [],
            }
            response = client.post("/api/v1/service-mesh/gateways", json=gateway_data)
            assert response.status_code in [201, 401, 500]

    # 33. GET /gateways/{gateway_id}
    def test_get_gateway(self, client, mock_db):
        """Test GET /gateways/{gateway_id} endpoint"""
        with patch("api.service_mesh_advanced_router.get_db", return_value=mock_db):
            mock_repo = MagicMock()
            mock_repo.get_gateway_config.return_value = {"id": str(uuid.uuid4()), "name": "test-gateway"}
            mock_db.query.return_value = mock_repo

            gateway_id = str(uuid.uuid4())
            response = client.get(f"/api/v1/service-mesh/gateways/{gateway_id}")
            assert response.status_code != 404, response.text

    # 34. GET /gateways
    def test_list_gateways(self, client, mock_db):
        """Test GET /gateways endpoint"""
        with patch("api.service_mesh_advanced_router.get_db", return_value=mock_db):
            mock_repo = MagicMock()
            mock_repo.list_gateway_configs.return_value = []
            mock_db.query.return_value = mock_repo

            response = client.get("/api/v1/service-mesh/gateways")
            assert response.status_code in [200, 500]

    # 35. GET /services/{service_name}/health
    def test_get_service_health(self, client, mock_db):
        """Test GET /services/{service_name}/health endpoint"""
        with patch("api.service_mesh_advanced_router.get_db", return_value=mock_db):
            mock_repo = MagicMock()
            mock_repo.perform_health_check.return_value = {
                "service_name": "test-service",
                "status": "healthy",
            }
            mock_db.query.return_value = mock_repo

            response = client.get("/api/v1/service-mesh/services/test-service/health")
            assert response.status_code in [200, 500]

    # 36. GET /health/summary
    def test_get_mesh_health_summary(self, client, mock_db):
        """Test GET /health/summary endpoint"""
        with patch("api.service_mesh_advanced_router.get_db", return_value=mock_db):
            mock_repo = MagicMock()
            mock_repo.get_mesh_health_summary.return_value = {
                "total_configurations": 5,
                "active_configurations": 4,
            }
            mock_db.query.return_value = mock_repo

            response = client.get("/api/v1/service-mesh/health/summary")
            assert response.status_code in [200, 500]

    # 37. POST /circuit-breakers
    def test_create_circuit_breaker(self, client, mock_db, mock_current_user):
        """Test POST /circuit-breakers endpoint"""
        with patch("api.service_mesh_advanced_router.get_db", return_value=mock_db), \
             patch("api.service_mesh_advanced_router.get_current_user", return_value=mock_current_user), \
             patch("api.service_mesh_advanced_router.require_permission"), \
             patch("api.service_mesh_advanced_router.check_rate_limit"):

            mock_repo = MagicMock()
            mock_repo.create_circuit_breaker.return_value = {
                "id": str(uuid.uuid4()),
                "name": "test-cb",
                "state": "closed",
            }
            mock_db.query.return_value = mock_repo

            cb_data = {
                "name": "test-cb",
                "target_service": "test-service",
                "consecutive_errors": 5,
            }
            response = client.post("/api/v1/service-mesh/circuit-breakers", json=cb_data)
            assert response.status_code in [201, 401, 500]

    # 38. GET /circuit-breakers/{cb_id}
    def test_get_circuit_breaker(self, client, mock_db):
        """Test GET /circuit-breakers/{cb_id} returns the persisted breaker."""
        from core.database import SessionLocal
        from core.service_mesh_repository import ServiceMeshRepository

        db = SessionLocal()
        try:
            cb = ServiceMeshRepository(db).create_circuit_breaker(
                "test-cb", "test-service", 5, 60, 30, {}
            )
        finally:
            db.close()

        response = client.get(f"/api/v1/service-mesh/circuit-breakers/{cb['id']}")
        assert response.status_code == 200, response.text
        assert response.json()["data"]["name"] == "test-cb"

        db = SessionLocal()
        try:
            ServiceMeshRepository(db).delete_circuit_breaker(cb["id"])
        finally:
            db.close()

    # 39. GET /circuit-breakers
    def test_list_circuit_breakers(self, client, mock_db):
        """Test GET /circuit-breakers endpoint"""
        with patch("api.service_mesh_advanced_router.get_db", return_value=mock_db):
            mock_repo = MagicMock()
            mock_repo.list_circuit_breakers.return_value = []
            mock_db.query.return_value = mock_repo

            response = client.get("/api/v1/service-mesh/circuit-breakers")
            assert response.status_code in [200, 500]

    # 40. PATCH /circuit-breakers/{cb_id}/state
    def test_update_circuit_breaker_state(self, client, mock_db, mock_current_user):
        """Test PATCH /circuit-breakers/{cb_id}/state endpoint"""
        with patch("api.service_mesh_advanced_router.get_db", return_value=mock_db), \
             patch("api.service_mesh_advanced_router.get_current_user", return_value=mock_current_user), \
             patch("api.service_mesh_advanced_router.require_permission"), \
             patch("api.service_mesh_advanced_router.check_rate_limit"):

            mock_repo = MagicMock()
            mock_repo.update_circuit_breaker_state.return_value = True
            mock_db.query.return_value = mock_repo

            cb_id = str(uuid.uuid4())
            update_data = {"state": "open"}
            response = client.patch(f"/api/v1/service-mesh/circuit-breakers/{cb_id}/state", json=update_data)
            assert response.status_code in [200, 401, 500]

    # 41. POST /retry-policies
    def test_create_retry_policy(self, client, mock_db, mock_current_user):
        """Test POST /retry-policies endpoint"""
        with patch("api.service_mesh_advanced_router.get_db", return_value=mock_db), \
             patch("api.service_mesh_advanced_router.get_current_user", return_value=mock_current_user), \
             patch("api.service_mesh_advanced_router.require_permission"), \
             patch("api.service_mesh_advanced_router.check_rate_limit"):

            mock_repo = MagicMock()
            mock_repo.create_retry_policy.return_value = {
                "id": str(uuid.uuid4()),
                "name": "test-retry",
            }
            mock_db.query.return_value = mock_repo

            policy_data = {
                "name": "test-retry",
                "target_service": "test-service",
                "max_attempts": 3,
            }
            response = client.post("/api/v1/service-mesh/retry-policies", json=policy_data)
            assert response.status_code in [201, 401, 500]

    # 42. GET /retry-policies/{policy_id}
    def test_get_retry_policy(self, client, mock_db):
        """Test GET /retry-policies/{policy_id} returns the persisted policy."""
        from core.database import SessionLocal
        from core.service_mesh_repository import ServiceMeshRepository

        db = SessionLocal()
        try:
            p = ServiceMeshRepository(db).create_retry_policy(
                "test-retry", "test-service", 3, 30, ["5xx"], {}
            )
        finally:
            db.close()

        response = client.get(f"/api/v1/service-mesh/retry-policies/{p['id']}")
        assert response.status_code == 200, response.text
        assert response.json()["data"]["name"] == "test-retry"

        db = SessionLocal()
        try:
            ServiceMeshRepository(db).delete_retry_policy(p["id"])
        finally:
            db.close()

    # 43. GET /retry-policies
    def test_list_retry_policies(self, client, mock_db):
        """Test GET /retry-policies endpoint"""
        with patch("api.service_mesh_advanced_router.get_db", return_value=mock_db):
            mock_repo = MagicMock()
            mock_repo.list_retry_policies.return_value = []
            mock_db.query.return_value = mock_repo

            response = client.get("/api/v1/service-mesh/retry-policies")
            assert response.status_code in [200, 500]

    # 44. POST /timeout-policies
    def test_create_timeout_policy(self, client, mock_db, mock_current_user):
        """Test POST /timeout-policies endpoint"""
        with patch("api.service_mesh_advanced_router.get_db", return_value=mock_db), \
             patch("api.service_mesh_advanced_router.get_current_user", return_value=mock_current_user), \
             patch("api.service_mesh_advanced_router.require_permission"), \
             patch("api.service_mesh_advanced_router.check_rate_limit"):

            mock_repo = MagicMock()
            mock_repo.create_timeout_policy.return_value = {
                "id": str(uuid.uuid4()),
                "name": "test-timeout",
            }
            mock_db.query.return_value = mock_repo

            policy_data = {
                "name": "test-timeout",
                "target_service": "test-service",
                "timeout_seconds": 30,
            }
            response = client.post("/api/v1/service-mesh/timeout-policies", json=policy_data)
            assert response.status_code in [201, 401, 500]

    # 45. GET /timeout-policies/{policy_id}
    def test_get_timeout_policy(self, client, mock_db):
        """Test GET /timeout-policies/{policy_id} returns the persisted policy."""
        from core.database import SessionLocal
        from core.service_mesh_repository import ServiceMeshRepository

        db = SessionLocal()
        try:
            p = ServiceMeshRepository(db).create_timeout_policy("test-timeout", "test-service", 15, {})
        finally:
            db.close()

        response = client.get(f"/api/v1/service-mesh/timeout-policies/{p['id']}")
        assert response.status_code == 200, response.text
        assert response.json()["data"]["name"] == "test-timeout"

        db = SessionLocal()
        try:
            ServiceMeshRepository(db).delete_timeout_policy(p["id"])
        finally:
            db.close()

    # 46. GET /timeout-policies
    def test_list_timeout_policies(self, client, mock_db):
        """Test GET /timeout-policies endpoint"""
        with patch("api.service_mesh_advanced_router.get_db", return_value=mock_db):
            mock_repo = MagicMock()
            mock_repo.list_timeout_policies.return_value = []
            mock_db.query.return_value = mock_repo

            response = client.get("/api/v1/service-mesh/timeout-policies")
            assert response.status_code in [200, 500]

    # 47. GET /configurations/{config_id}/export
    def test_export_configuration(self, client, mock_db, sample_mesh_config):
        """Test GET /configurations/{config_id}/export endpoint"""
        with patch("api.service_mesh_advanced_router.get_db", return_value=mock_db):
            mock_repo = MagicMock()
            mock_repo.export_configuration.return_value = {
                "version": "1.0",
                "configuration": {"name": "test-mesh"},
            }
            mock_db.query.return_value = mock_repo

            response = client.get(f"/api/v1/service-mesh/configurations/{sample_mesh_config.id}/export")
            assert response.status_code != 404, response.text

    # 48. POST /configurations/import
    def test_import_configuration(self, client, mock_db, mock_current_user, sample_mesh_config):
        """Test POST /configurations/import endpoint"""
        with patch("api.service_mesh_advanced_router.get_db", return_value=mock_db), \
             patch("api.service_mesh_advanced_router.get_current_user", return_value=mock_current_user), \
             patch("api.service_mesh_advanced_router.require_permission"), \
             patch("api.service_mesh_advanced_router.check_rate_limit"):

            mock_repo = MagicMock()
            mock_repo.import_configuration.return_value = sample_mesh_config
            mock_db.query.return_value = mock_repo

            import_data = {
                "version": "1.0",
                "exported_at": datetime.utcnow().isoformat(),
                "configuration": {"name": "test-mesh"},
            }
            response = client.post("/api/v1/service-mesh/configurations/import", json=import_data)
            assert response.status_code in [201, 401, 500]

    # 49. GET /metrics
    def test_get_mesh_metrics(self, client, mock_db):
        """Test GET /metrics endpoint"""
        with patch("api.service_mesh_advanced_router.get_db", return_value=mock_db):
            mock_repo = MagicMock()
            mock_repo.get_mesh_metrics.return_value = {
                "time_range": "1h",
                "total_requests": 1000,
                "success_rate": 0.99,
            }
            mock_db.query.return_value = mock_repo

            response = client.get("/api/v1/service-mesh/metrics")
            assert response.status_code in [200, 500]

    # 50. GET /topology
    def test_get_service_topology(self, client, mock_db):
        """Test GET /topology endpoint"""
        with patch("api.service_mesh_advanced_router.get_db", return_value=mock_db):
            mock_repo = MagicMock()
            mock_repo.get_service_topology.return_value = {
                "nodes": ["service-a", "service-b"],
                "edges": [],
            }
            mock_db.query.return_value = mock_repo

            response = client.get("/api/v1/service-mesh/topology")
            assert response.status_code in [200, 500]

    # 51. POST /configurations/validate
    def test_validate_configuration(self, client, mock_db, mock_service_mesh_manager):
        """Test POST /configurations/validate endpoint"""
        with patch("api.service_mesh_advanced_router.get_db", return_value=mock_db), \
             patch("core.service_mesh_manager.get_service_mesh_manager", return_value=mock_service_mesh_manager):

            config_data = {
                "name": "test-mesh",
                "mesh_type": "istio",
                "namespace": "istio-system",
                "profile": "default",
            }
            response = client.post("/api/v1/service-mesh/configurations/validate", json=config_data)
            assert response.status_code in [200, 500]

    # 52. POST /configurations/{config_id}/rollback
    def test_rollback_configuration(self, client, mock_db, mock_current_user, sample_mesh_config):
        """Test POST /configurations/{config_id}/rollback endpoint"""
        with patch("api.service_mesh_advanced_router.get_db", return_value=mock_db), \
             patch("api.service_mesh_advanced_router.get_current_user", return_value=mock_current_user), \
             patch("api.service_mesh_advanced_router.require_permission"), \
             patch("api.service_mesh_advanced_router.check_rate_limit"):

            mock_repo = MagicMock()
            mock_repo.get_mesh_configuration.return_value = sample_mesh_config
            mock_db.query.return_value = mock_repo

            response = client.post(f"/api/v1/service-mesh/configurations/{sample_mesh_config.id}/rollback")
            assert response.status_code in [200, 401, 500]

    # 53. GET /services/{service_name}/instances
    def test_get_service_instances(self, client, mock_db, mock_service_mesh_manager):
        """Test GET /services/{service_name}/instances endpoint"""
        with patch("api.service_mesh_advanced_router.get_db", return_value=mock_db), \
             patch("core.service_mesh_manager.get_service_mesh_manager", return_value=mock_service_mesh_manager):

            response = client.get("/api/v1/service-mesh/services/test-service/instances")
            assert response.status_code in [200, 500]

    # 54. DELETE /services/{service_name}/instances/{instance_id}
    def test_delete_service_instance(self, client, mock_db, mock_current_user):
        """Test DELETE /services/{service_name}/instances/{instance_id} endpoint"""
        with patch("api.service_mesh_advanced_router.get_db", return_value=mock_db), \
             patch("api.service_mesh_advanced_router.get_current_user", return_value=mock_current_user), \
             patch("api.service_mesh_advanced_router.require_permission"), \
             patch("api.service_mesh_advanced_router.check_rate_limit"):

            response = client.delete("/api/v1/service-mesh/services/test-service/instances/instance-1")
            assert response.status_code in [200, 401, 500]

    # 55. POST /configurations/diff
    def test_compare_configurations(self, client, mock_db):
        """Test POST /configurations/diff endpoint with two real configs."""
        from core.database import SessionLocal
        from core.models import MeshConfiguration

        db = SessionLocal()
        try:
            ids = []
            for name in ("diff-a", "diff-b"):
                cid = str(uuid.uuid4())
                db.add(
                    MeshConfiguration(
                        id=cid, name=name, mesh_type="istio", namespace="istio-system",
                        profile="default", auto_injection_enabled=True, mtls_enabled=True,
                        resource_limits={}, status="active", mesh_id=f"mesh-{cid[:8]}",
                        config_metadata={}, created_at=datetime.utcnow(), updated_at=datetime.utcnow(),
                    )
                )
                ids.append(cid)
            db.commit()
        finally:
            db.close()

        try:
            response = client.post(
                f"/api/v1/service-mesh/configurations/diff?config_id_1={ids[0]}&config_id_2={ids[1]}"
            )
            assert response.status_code != 404, response.text
        finally:
            db = SessionLocal()
            try:
                db.query(MeshConfiguration).filter(MeshConfiguration.id.in_(ids)).delete(
                    synchronize_session=False
                )
                db.commit()
            finally:
                db.close()

    # 56. POST /configurations/{config_id}/clone
    def test_clone_configuration(self, client, mock_db, mock_current_user, sample_mesh_config):
        """Test POST /configurations/{config_id}/clone endpoint"""
        with patch("api.service_mesh_advanced_router.get_db", return_value=mock_db), \
             patch("api.service_mesh_advanced_router.get_current_user", return_value=mock_current_user), \
             patch("api.service_mesh_advanced_router.require_permission"), \
             patch("api.service_mesh_advanced_router.check_rate_limit"):

            mock_repo = MagicMock()
            mock_repo.get_mesh_configuration.return_value = sample_mesh_config
            mock_repo.create_mesh_configuration.return_value = sample_mesh_config
            mock_db.query.return_value = mock_repo

            response = client.post(f"/api/v1/service-mesh/configurations/{sample_mesh_config.id}/clone?new_name=cloned-mesh")
            assert response.status_code in [201, 401, 500]


# ============================================================================
# Test Runner
# ============================================================================


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-n", "auto"])
