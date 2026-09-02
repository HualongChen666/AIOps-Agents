# -*- coding: utf-8 -*-
"""
Unit tests for Service Mesh Repository
Tests database operations for service mesh entities
"""

import pytest
from datetime import datetime
from sqlalchemy.orm import Session

from core.database import SessionLocal, engine
from core.models import (
    MeshConfiguration,
    ObservabilityConfig,
    Policy,
    SecurityPolicy,
    TrafficRule,
)
from core.service_mesh_repository import ServiceMeshRepository


@pytest.fixture(scope="function")
def db_session():
    """Create a new database session for each test"""
    # Create all tables
    from core.models import Base

    Base.metadata.create_all(bind=engine)

    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        # Drop all tables after test
        Base.metadata.drop_all(bind=engine)


class TestMeshConfigurationRepository:
    """Test mesh configuration repository operations"""

    def test_create_mesh_configuration(self, db_session: Session):
        """Test creating a mesh configuration"""
        repo = ServiceMeshRepository(db_session)

        config = repo.create_mesh_configuration(
            name="test-config",
            mesh_type="istio",
            namespace="istio-system",
            profile="default",
            auto_injection_enabled=True,
            mtls_enabled=True,
            resource_limits={"cpu": "1000m", "memory": "1Gi"},
            config_metadata={"environment": "test"},
        )

        assert config is not None
        assert config.name == "test-config"
        assert config.mesh_type == "istio"
        assert config.status == "active"
        assert config.mesh_id is not None
        assert config.id is not None

    def test_get_mesh_configuration(self, db_session: Session):
        """Test getting a mesh configuration by ID"""
        repo = ServiceMeshRepository(db_session)

        created_config = repo.create_mesh_configuration(
            name="test-config",
            mesh_type="istio",
            namespace="istio-system",
            profile="default",
            auto_injection_enabled=True,
            mtls_enabled=True,
            resource_limits=None,
            config_metadata=None,
        )

        retrieved_config = repo.get_mesh_configuration(created_config.id)

        assert retrieved_config is not None
        assert retrieved_config.id == created_config.id
        assert retrieved_config.name == "test-config"

    def test_list_mesh_configurations(self, db_session: Session):
        """Test listing mesh configurations"""
        repo = ServiceMeshRepository(db_session)

        # Create multiple configurations
        repo.create_mesh_configuration(
            name="config-1",
            mesh_type="istio",
            namespace="istio-system",
            profile="default",
            auto_injection_enabled=True,
            mtls_enabled=True,
            resource_limits=None,
            config_metadata=None,
        )

        repo.create_mesh_configuration(
            name="config-2",
            mesh_type="linkerd",
            namespace="linkerd",
            profile="default",
            auto_injection_enabled=False,
            mtls_enabled=False,
            resource_limits=None,
            config_metadata=None,
        )

        configs = repo.list_mesh_configurations()

        assert len(configs) == 2

        # Test filtering
        istio_configs = repo.list_mesh_configurations(mesh_type="istio")
        assert len(istio_configs) == 1
        assert istio_configs[0].mesh_type == "istio"

    def test_update_mesh_configuration(self, db_session: Session):
        """Test updating a mesh configuration"""
        repo = ServiceMeshRepository(db_session)

        config = repo.create_mesh_configuration(
            name="test-config",
            mesh_type="istio",
            namespace="istio-system",
            profile="default",
            auto_injection_enabled=True,
            mtls_enabled=True,
            resource_limits=None,
            config_metadata=None,
        )

        updated_config = repo.update_mesh_configuration(
            config.id, name="updated-config", namespace="updated-namespace"
        )

        assert updated_config is not None
        assert updated_config.name == "updated-config"
        assert updated_config.namespace == "updated-namespace"

    def test_delete_mesh_configuration(self, db_session: Session):
        """Test deleting a mesh configuration"""
        repo = ServiceMeshRepository(db_session)

        config = repo.create_mesh_configuration(
            name="test-config",
            mesh_type="istio",
            namespace="istio-system",
            profile="default",
            auto_injection_enabled=True,
            mtls_enabled=True,
            resource_limits=None,
            config_metadata=None,
        )

        success = repo.delete_mesh_configuration(config.id)

        assert success is True

        # Verify deletion
        deleted_config = repo.get_mesh_configuration(config.id)
        assert deleted_config is None


class TestTrafficRuleRepository:
    """Test traffic rule repository operations"""

    def test_create_traffic_rule(self, db_session: Session):
        """Test creating a traffic rule"""
        repo = ServiceMeshRepository(db_session)

        rule = repo.create_traffic_rule(
            name="test-rule",
            service_name="test-service",
            match_conditions={"headers": {"x-version": "v1"}},
            destination={"host": "test-service", "subset": "v1"},
            weight=100,
            timeout_seconds=30,
            retry_policy=None,
            fault_injection=None,
            rule_metadata=None,
        )

        assert rule is not None
        assert rule.name == "test-rule"
        assert rule.service_name == "test-service"
        assert rule.weight == 100
        assert rule.enabled is True

    def test_get_traffic_rule(self, db_session: Session):
        """Test getting a traffic rule by ID"""
        repo = ServiceMeshRepository(db_session)

        created_rule = repo.create_traffic_rule(
            name="test-rule",
            service_name="test-service",
            match_conditions={},
            destination={},
            weight=100,
            timeout_seconds=30,
            retry_policy=None,
            fault_injection=None,
            rule_metadata=None,
        )

        retrieved_rule = repo.get_traffic_rule(created_rule.id)

        assert retrieved_rule is not None
        assert retrieved_rule.id == created_rule.id
        assert retrieved_rule.name == "test-rule"

    def test_list_traffic_rules(self, db_session: Session):
        """Test listing traffic rules"""
        repo = ServiceMeshRepository(db_session)

        repo.create_traffic_rule(
            name="rule-1",
            service_name="service-1",
            match_conditions={},
            destination={},
            weight=100,
            timeout_seconds=30,
            retry_policy=None,
            fault_injection=None,
            rule_metadata=None,
        )

        repo.create_traffic_rule(
            name="rule-2",
            service_name="service-2",
            match_conditions={},
            destination={},
            weight=100,
            timeout_seconds=30,
            retry_policy=None,
            fault_injection=None,
            rule_metadata=None,
        )

        rules = repo.list_traffic_rules()

        assert len(rules) == 2

        # Test filtering
        service_1_rules = repo.list_traffic_rules(service_name="service-1")
        assert len(service_1_rules) == 1
        assert service_1_rules[0].service_name == "service-1"

    def test_update_traffic_rule(self, db_session: Session):
        """Test updating a traffic rule"""
        repo = ServiceMeshRepository(db_session)

        rule = repo.create_traffic_rule(
            name="test-rule",
            service_name="test-service",
            match_conditions={},
            destination={},
            weight=100,
            timeout_seconds=30,
            retry_policy=None,
            fault_injection=None,
            rule_metadata=None,
        )

        updated_rule = repo.update_traffic_rule(rule.id, name="updated-rule", weight=50)

        assert updated_rule is not None
        assert updated_rule.name == "updated-rule"
        assert updated_rule.weight == 50

    def test_delete_traffic_rule(self, db_session: Session):
        """Test deleting a traffic rule"""
        repo = ServiceMeshRepository(db_session)

        rule = repo.create_traffic_rule(
            name="test-rule",
            service_name="test-service",
            match_conditions={},
            destination={},
            weight=100,
            timeout_seconds=30,
            retry_policy=None,
            fault_injection=None,
            rule_metadata=None,
        )

        success = repo.delete_traffic_rule(rule.id)

        assert success is True

        # Verify deletion
        deleted_rule = repo.get_traffic_rule(rule.id)
        assert deleted_rule is None


class TestSecurityPolicyRepository:
    """Test security policy repository operations"""

    def test_create_security_policy(self, db_session: Session):
        """Test creating a security policy"""
        repo = ServiceMeshRepository(db_session)

        policy = repo.create_security_policy(
            name="test-policy",
            policy_type="authentication",
            target_service="test-service",
            mtls_mode="STRICT",
            allowed_principals=["spiffe://cluster.local/ns/default/sa/test"],
            denied_principals=[],
            jwt_validation=None,
            policy_metadata=None,
        )

        assert policy is not None
        assert policy.name == "test-policy"
        assert policy.policy_type == "authentication"
        assert policy.mtls_mode == "STRICT"
        assert policy.enabled is True

    def test_get_security_policy(self, db_session: Session):
        """Test getting a security policy by ID"""
        repo = ServiceMeshRepository(db_session)

        created_policy = repo.create_security_policy(
            name="test-policy",
            policy_type="authorization",
            target_service="test-service",
            mtls_mode="PERMISSIVE",
            allowed_principals=[],
            denied_principals=[],
            jwt_validation=None,
            policy_metadata=None,
        )

        retrieved_policy = repo.get_security_policy(created_policy.id)

        assert retrieved_policy is not None
        assert retrieved_policy.id == created_policy.id
        assert retrieved_policy.name == "test-policy"

    def test_list_security_policies(self, db_session: Session):
        """Test listing security policies"""
        repo = ServiceMeshRepository(db_session)

        repo.create_security_policy(
            name="policy-1",
            policy_type="authentication",
            target_service="service-1",
            mtls_mode="STRICT",
            allowed_principals=[],
            denied_principals=[],
            jwt_validation=None,
            policy_metadata=None,
        )

        repo.create_security_policy(
            name="policy-2",
            policy_type="authorization",
            target_service="service-2",
            mtls_mode="PERMISSIVE",
            allowed_principals=[],
            denied_principals=[],
            jwt_validation=None,
            policy_metadata=None,
        )

        policies = repo.list_security_policies()

        assert len(policies) == 2

        # Test filtering
        auth_policies = repo.list_security_policies(policy_type="authentication")
        assert len(auth_policies) == 1
        assert auth_policies[0].policy_type == "authentication"


class TestObservabilityConfigRepository:
    """Test observability configuration repository operations"""

    def test_create_observability_config(self, db_session: Session):
        """Test creating an observability configuration"""
        repo = ServiceMeshRepository(db_session)

        config = repo.create_observability_config(
            name="test-config",
            tracing_enabled=True,
            metrics_enabled=True,
            access_logging_enabled=True,
            sampling_rate=1.0,
            prometheus_enabled=True,
            grafana_enabled=False,
            config_metadata=None,
        )

        assert config is not None
        assert config.name == "test-config"
        assert config.tracing_enabled is True
        assert config.sampling_rate == 1.0
        assert config.enabled is True

    def test_get_observability_config(self, db_session: Session):
        """Test getting an observability configuration by ID"""
        repo = ServiceMeshRepository(db_session)

        created_config = repo.create_observability_config(
            name="test-config",
            tracing_enabled=True,
            metrics_enabled=True,
            access_logging_enabled=True,
            sampling_rate=1.0,
            prometheus_enabled=True,
            grafana_enabled=False,
            config_metadata=None,
        )

        retrieved_config = repo.get_observability_config(created_config.id)

        assert retrieved_config is not None
        assert retrieved_config.id == created_config.id
        assert retrieved_config.name == "test-config"


class TestPolicyRepository:
    """Test generic policy repository operations"""

    def test_create_policy(self, db_session: Session):
        """Test creating a policy"""
        repo = ServiceMeshRepository(db_session)

        policy = repo.create_policy(
            name="test-policy",
            policy_type="rate-limiting",
            target_service="test-service",
            rules=[{"action": "allow", "condition": "rate < 100"}],
            enabled=True,
            policy_metadata=None,
        )

        assert policy is not None
        assert policy.name == "test-policy"
        assert policy.policy_type == "rate-limiting"
        assert policy.enabled is True

    def test_get_policy(self, db_session: Session):
        """Test getting a policy by ID"""
        repo = ServiceMeshRepository(db_session)

        created_policy = repo.create_policy(
            name="test-policy",
            policy_type="circuit-breaker",
            target_service="test-service",
            rules=[],
            enabled=True,
            policy_metadata=None,
        )

        retrieved_policy = repo.get_policy(created_policy.id)

        assert retrieved_policy is not None
        assert retrieved_policy.id == created_policy.id
        assert retrieved_policy.name == "test-policy"

    def test_list_policies(self, db_session: Session):
        """Test listing policies"""
        repo = ServiceMeshRepository(db_session)

        repo.create_policy(
            name="policy-1",
            policy_type="rate-limiting",
            target_service="service-1",
            rules=[],
            enabled=True,
            policy_metadata=None,
        )

        repo.create_policy(
            name="policy-2",
            policy_type="circuit-breaker",
            target_service="service-2",
            rules=[],
            enabled=True,
            policy_metadata=None,
        )

        policies = repo.list_policies()

        assert len(policies) == 2

        # Test filtering
        rate_limit_policies = repo.list_policies(policy_type="rate-limiting")
        assert len(rate_limit_policies) == 1
        assert rate_limit_policies[0].policy_type == "rate-limiting"
