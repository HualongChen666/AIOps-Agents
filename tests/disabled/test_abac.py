# -*- coding: utf-8 -*-
"""
Unit tests for core/abac.py

Tests for Attribute-Based Access Control (ABAC) functionality.
"""

from datetime import datetime
from typing import Any, Dict, Set  # noqa: F401
from unittest.mock import MagicMock, Mock, patch

import pytest  # noqa: F401

from core.abac import (
    ABACEngine,
    ActionType,
    Environment,
    Policy,
    Resource,
    ResourceType,
    Subject,
    create_abac_engine,
)


class TestActionType:
    """Test ActionType enum."""

    def test_action_type_values(self):
        """Test that ActionType has correct values."""
        assert ActionType.READ.value == "read"
        assert ActionType.WRITE.value == "write"
        assert ActionType.DELETE.value == "delete"
        assert ActionType.EXECUTE.value == "execute"
        assert ActionType.ADMIN.value == "admin"


class TestResourceType:
    """Test ResourceType enum."""

    def test_resource_type_values(self):
        """Test that ResourceType has correct values."""
        assert ResourceType.ANOMALY.value == "anomaly"
        assert ResourceType.ALERT.value == "alert"
        assert ResourceType.METRIC.value == "metric"
        assert ResourceType.CONFIGURATION.value == "configuration"
        assert ResourceType.POLICY.value == "policy"
        assert ResourceType.WORKFLOW.value == "workflow"
        assert ResourceType.DEPLOYMENT.value == "deployment"
        assert ResourceType.SERVICE.value == "service"


class TestSubject:
    """Test Subject dataclass."""

    def test_subject_creation(self):
        """Test creating a Subject."""
        subject = Subject(
            id="user123",
            type="user",
            attributes={"department": "engineering", "level": "senior"},
            roles={"admin", "developer"},
            groups={"team-a"},
        )
        assert subject.id == "user123"
        assert subject.type == "user"
        assert subject.attributes["department"] == "engineering"
        assert "admin" in subject.roles
        assert "team-a" in subject.groups

    def test_get_attribute(self):
        """Test getting attribute from subject."""
        subject = Subject(
            id="user123",
            type="user",
            attributes={"department": "engineering"},
            roles=set(),
            groups=set(),
        )
        assert subject.get_attribute("department") == "engineering"
        assert subject.get_attribute("nonexistent", "default") == "default"


class TestResource:
    """Test Resource dataclass."""

    def test_resource_creation(self):
        """Test creating a Resource."""
        resource = Resource(
            id="alert-123",
            type=ResourceType.ALERT,
            attributes={"severity": "high", "environment": "production"},
            owner="user123",
        )
        assert resource.id == "alert-123"
        assert resource.type == ResourceType.ALERT
        assert resource.attributes["severity"] == "high"
        assert resource.owner == "user123"

    def test_get_attribute(self):
        """Test getting attribute from resource."""
        resource = Resource(
            id="alert-123",
            type=ResourceType.ALERT,
            attributes={"severity": "high"},
            owner="user123",
        )
        assert resource.get_attribute("severity") == "high"
        assert resource.get_attribute("nonexistent", "default") == "default"


class TestEnvironment:
    """Test Environment dataclass."""

    def test_environment_creation(self):
        """Test creating an Environment."""
        environment = Environment(attributes={"time": "business_hours", "location": "office"})
        assert environment.attributes["time"] == "business_hours"
        assert environment.attributes["location"] == "office"

    def test_get_attribute(self):
        """Test getting attribute from environment."""
        environment = Environment(attributes={"time": "business_hours"})
        assert environment.get_attribute("time") == "business_hours"
        assert environment.get_attribute("nonexistent", "default") == "default"


class TestPolicy:
    """Test Policy dataclass."""

    def test_policy_creation(self):
        """Test creating a Policy."""
        now = datetime.utcnow()
        policy = Policy(
            id="policy-1",
            name="Admin Policy",
            description="Allow admins to perform all actions",
            enabled=True,
            effect="allow",
            subject_conditions={"role": "admin"},
            resource_conditions={"type": "alert"},
            environment_conditions={},
            actions={ActionType.READ, ActionType.WRITE, ActionType.DELETE},
            priority=100,
            created_at=now,
            updated_at=now,
        )
        assert policy.id == "policy-1"
        assert policy.name == "Admin Policy"
        assert policy.enabled is True
        assert policy.effect == "allow"
        assert ActionType.READ in policy.actions
        assert policy.priority == 100


class TestABACEngine:
    """Test ABAC Engine functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_storage = Mock()
        self.mock_connection = MagicMock()
        self.mock_cursor = MagicMock()

        # Setup context manager properly
        self.mock_storage.get_connection.return_value = self.mock_connection
        self.mock_connection.__enter__ = Mock(return_value=self.mock_connection)
        self.mock_connection.__exit__ = Mock(return_value=False)
        self.mock_connection.cursor.return_value = self.mock_cursor
        self.mock_cursor.__enter__ = Mock(return_value=self.mock_cursor)
        self.mock_cursor.__exit__ = Mock(return_value=False)

        self.engine = ABACEngine(self.mock_storage)

    def test_engine_initialization(self):
        """Test ABAC Engine initialization."""
        assert self.engine.storage == self.mock_storage
        assert self.engine._is_initialized is False
        assert len(self.engine._policies) == 0

    def test_initialize_success(self):
        """Test successful initialization."""
        self.mock_cursor.execute.return_value = None
        self.mock_storage.execute_query.return_value = []

        result = self.engine.initialize()

        assert result is True
        assert self.engine._is_initialized is True

    def test_initialize_failure(self):
        """Test initialization failure."""
        self.mock_cursor.execute.side_effect = Exception("Database error")

        result = self.engine.initialize()

        assert result is False
        assert self.engine._is_initialized is False

    def test_evaluate_not_initialized(self):
        """Test evaluation when engine is not initialized."""
        subject = Subject(id="user1", type="user", attributes={}, roles=set(), groups=set())
        resource = Resource(id="res1", type=ResourceType.ALERT, attributes={})

        result = self.engine.evaluate(subject, resource, ActionType.READ)

        assert result is False  # Default deny

    def test_evaluate_with_matching_allow_policy(self):
        """Test evaluation with matching allow policy."""
        self.engine._is_initialized = True

        # Add a policy
        policy = Policy(
            id="policy-1",
            name="Allow Read",
            description="Allow read access",
            enabled=True,
            effect="allow",
            subject_conditions={"role": "admin"},
            resource_conditions={"type": "alert"},
            environment_conditions={},
            actions={ActionType.READ},
            priority=100,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        self.engine._policies[policy.id] = policy

        subject = Subject(
            id="user1", type="user", attributes={"role": "admin"}, roles=set(), groups=set()
        )
        resource = Resource(id="alert-1", type=ResourceType.ALERT, attributes={"type": "alert"})

        result = self.engine.evaluate(subject, resource, ActionType.READ)

        assert result is True

    def test_evaluate_with_matching_deny_policy(self):
        """Test evaluation with matching deny policy."""
        self.engine._is_initialized = True

        # Add a deny policy
        policy = Policy(
            id="policy-1",
            name="Deny Delete",
            description="Deny delete access",
            enabled=True,
            effect="deny",
            subject_conditions={"role": "user"},
            resource_conditions={"type": "alert"},
            environment_conditions={},
            actions={ActionType.DELETE},
            priority=100,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        self.engine._policies[policy.id] = policy

        subject = Subject(
            id="user1", type="user", attributes={"role": "user"}, roles=set(), groups=set()
        )
        resource = Resource(id="alert-1", type=ResourceType.ALERT, attributes={"type": "alert"})

        result = self.engine.evaluate(subject, resource, ActionType.DELETE)

        assert result is False

    def test_evaluate_no_matching_policy(self):
        """Test evaluation when no policy matches."""
        self.engine._is_initialized = True

        subject = Subject(
            id="user1", type="user", attributes={"role": "guest"}, roles=set(), groups=set()
        )
        resource = Resource(id="alert-1", type=ResourceType.ALERT, attributes={"type": "alert"})

        result = self.engine.evaluate(subject, resource, ActionType.READ)

        assert result is False  # Default deny

    def test_evaluate_disabled_policy(self):
        """Test that disabled policies are not evaluated."""
        self.engine._is_initialized = True

        # Add a disabled policy
        policy = Policy(
            id="policy-1",
            name="Disabled Policy",
            description="This policy is disabled",
            enabled=False,
            effect="allow",
            subject_conditions={"role": "admin"},
            resource_conditions={},
            environment_conditions={},
            actions={ActionType.READ},
            priority=100,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        self.engine._policies[policy.id] = policy

        subject = Subject(
            id="user1", type="user", attributes={"role": "admin"}, roles=set(), groups=set()
        )
        resource = Resource(id="alert-1", type=ResourceType.ALERT, attributes={})

        result = self.engine.evaluate(subject, resource, ActionType.READ)

        assert result is False  # Policy is disabled, default deny

    def test_evaluate_priority_ordering(self):
        """Test that higher priority policies are evaluated first."""
        self.engine._is_initialized = True

        # Add high priority deny policy
        deny_policy = Policy(
            id="policy-1",
            name="High Priority Deny",
            description="High priority deny",
            enabled=True,
            effect="deny",
            subject_conditions={"role": "admin"},
            resource_conditions={},
            environment_conditions={},
            actions={ActionType.READ},
            priority=200,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        # Add low priority allow policy
        allow_policy = Policy(
            id="policy-2",
            name="Low Priority Allow",
            description="Low priority allow",
            enabled=True,
            effect="allow",
            subject_conditions={"role": "admin"},
            resource_conditions={},
            environment_conditions={},
            actions={ActionType.READ},
            priority=100,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        self.engine._policies[deny_policy.id] = deny_policy
        self.engine._policies[allow_policy.id] = allow_policy

        subject = Subject(
            id="user1", type="user", attributes={"role": "admin"}, roles=set(), groups=set()
        )
        resource = Resource(id="alert-1", type=ResourceType.ALERT, attributes={})

        result = self.engine.evaluate(subject, resource, ActionType.READ)

        assert result is False  # High priority deny should win


class TestConditionMatching:
    """Test condition matching logic."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_storage = Mock()
        self.engine = ABACEngine(self.mock_storage)
        self.engine._is_initialized = True

    def test_matches_simple_equality(self):
        """Test simple equality condition matching."""
        attributes = {"role": "admin", "department": "engineering"}
        conditions = {"role": "admin"}

        result = self.engine._matches_conditions(attributes, conditions)

        assert result is True

    def test_matches_equality_failure(self):
        """Test equality condition when values don't match."""
        attributes = {"role": "user"}
        conditions = {"role": "admin"}

        result = self.engine._matches_conditions(attributes, conditions)

        assert result is False

    def test_matches_equals_operator(self):
        """Test equals operator in complex condition."""
        attributes = {"level": 5}
        conditions = {"level": {"equals": 5}}

        result = self.engine._matches_conditions(attributes, conditions)

        assert result is True

    def test_matches_in_operator(self):
        """Test in operator in complex condition."""
        attributes = {"role": "admin"}
        conditions = {"role": {"in": ["admin", "superadmin"]}}

        result = self.engine._matches_conditions(attributes, conditions)

        assert result is True

    def test_matches_contains_operator(self):
        """Test contains operator in complex condition."""
        attributes = {"permissions": "read,write,delete"}
        conditions = {"permissions": {"contains": "write"}}

        result = self.engine._matches_conditions(attributes, conditions)

        assert result is True

    def test_matches_gt_operator(self):
        """Test greater than operator in complex condition."""
        attributes = {"level": 10}
        conditions = {"level": {"gt": 5}}

        result = self.engine._matches_conditions(attributes, conditions)

        assert result is True

    def test_matches_lt_operator(self):
        """Test less than operator in complex condition."""
        attributes = {"level": 3}
        conditions = {"level": {"lt": 5}}

        result = self.engine._matches_conditions(attributes, conditions)

        assert result is True

    def test_matches_gte_operator(self):
        """Test greater than or equal operator in complex condition."""
        attributes = {"level": 5}
        conditions = {"level": {"gte": 5}}

        result = self.engine._matches_conditions(attributes, conditions)

        assert result is True

    def test_matches_lte_operator(self):
        """Test less than or equal operator in complex condition."""
        attributes = {"level": 5}
        conditions = {"level": {"lte": 5}}

        result = self.engine._matches_conditions(attributes, conditions)

        assert result is True

    def test_matches_regex_operator(self):
        """Test regex operator in complex condition."""
        attributes = {"email": "user@example.com"}
        conditions = {"email": {"regex": r"^[a-z]+@[a-z]+\.[a-z]+$"}}

        result = self.engine._matches_conditions(attributes, conditions)

        assert result is True

    def test_matches_missing_attribute(self):
        """Test condition when attribute is missing."""
        attributes = {"role": "admin"}
        conditions = {"department": "engineering"}

        result = self.engine._matches_conditions(attributes, conditions)

        assert result is False


class TestPolicyManagement:
    """Test policy management operations."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_storage = Mock()
        self.mock_connection = MagicMock()
        self.mock_cursor = MagicMock()

        # Setup context manager properly
        self.mock_storage.get_connection.return_value = self.mock_connection
        self.mock_connection.__enter__ = Mock(return_value=self.mock_connection)
        self.mock_connection.__exit__ = Mock(return_value=False)
        self.mock_connection.cursor.return_value = self.mock_cursor
        self.mock_cursor.__enter__ = Mock(return_value=self.mock_cursor)
        self.mock_cursor.__exit__ = Mock(return_value=False)
        self.mock_cursor.fetchone.return_value = [1]

        self.engine = ABACEngine(self.mock_storage)
        self.engine._is_initialized = True

    def test_create_policy(self):
        """Test creating a new policy."""
        self.mock_cursor.execute.return_value = None
        self.mock_storage.execute_query.return_value = []

        policy_id = self.engine.create_policy(
            name="Test Policy",
            description="Test description",
            effect="allow",
            subject_conditions={"role": "admin"},
            resource_conditions={"type": "alert"},
            environment_conditions={},
            actions=["read", "write"],
            priority=100,
        )

        assert policy_id == "1"
        assert self.mock_cursor.execute.called

    def test_create_policy_failure(self):
        """Test policy creation failure."""
        self.mock_cursor.execute.side_effect = Exception("Database error")

        policy_id = self.engine.create_policy(
            name="Test Policy",
            description="Test description",
            effect="allow",
            subject_conditions={},
            resource_conditions={},
            environment_conditions={},
            actions=["read"],
            priority=0,
        )

        assert policy_id is None

    def test_update_policy(self):
        """Test updating an existing policy."""
        self.mock_cursor.execute.return_value = None
        self.mock_storage.execute_query.return_value = []

        result = self.engine.update_policy(
            policy_id="1", name="Updated Policy", description="Updated description"
        )

        assert result is True

    def test_update_policy_no_changes(self):
        """Test updating policy with no changes."""
        result = self.engine.update_policy(policy_id="1")

        assert result is True  # Should return True even with no changes

    def test_delete_policy(self):
        """Test deleting a policy."""
        self.mock_cursor.execute.return_value = None
        self.mock_storage.execute_query.return_value = []

        result = self.engine.delete_policy(policy_id="1")

        assert result is True

    def test_list_policies(self):
        """Test listing policies."""
        self.mock_storage.execute_query.return_value = []

        policies = self.engine.list_policies(enabled_only=True)

        assert isinstance(policies, list)

    def test_list_policies_all(self):
        """Test listing all policies including disabled."""
        self.mock_storage.execute_query.return_value = []

        policies = self.engine.list_policies(enabled_only=False)

        assert isinstance(policies, list)


class TestCreateABACEngine:
    """Test ABAC Engine factory function."""

    def test_create_abac_engine_success(self):
        """Test successful ABAC Engine creation."""
        mock_storage = Mock()
        mock_engine = Mock()
        mock_engine.initialize.return_value = True

        with patch("core.abac.ABACEngine", return_value=mock_engine):
            engine = create_abac_engine(mock_storage)
            assert engine is not None

    def test_create_abac_engine_failure(self):
        """Test ABAC Engine creation failure."""
        mock_storage = Mock()
        mock_engine = Mock()
        mock_engine.initialize.return_value = False

        with patch("core.abac.ABACEngine", return_value=mock_engine):
            engine = create_abac_engine(mock_storage)
            assert engine is None

    def test_create_abac_engine_exception(self):
        """Test ABAC Engine creation with exception."""
        mock_storage = Mock()

        with patch("core.abac.ABACEngine", side_effect=Exception("Creation error")):
            engine = create_abac_engine(mock_storage)
            assert engine is None


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_subject_with_empty_attributes(self):
        """Test subject with empty attributes."""
        subject = Subject(id="user1", type="user", attributes={}, roles=set(), groups=set())
        assert subject.get_attribute("any", "default") == "default"

    def test_resource_without_owner(self):
        """Test resource without owner."""
        resource = Resource(id="res1", type=ResourceType.ALERT, attributes={})
        assert resource.owner is None

    def test_environment_with_empty_attributes(self):
        """Test environment with empty attributes."""
        environment = Environment(attributes={})
        assert environment.get_attribute("any", "default") == "default"

    def test_policy_with_empty_conditions(self):
        """Test policy with empty conditions (matches everything)."""
        policy = Policy(
            id="policy-1",
            name="Open Policy",
            description="Matches everything",
            enabled=True,
            effect="allow",
            subject_conditions={},
            resource_conditions={},
            environment_conditions={},
            actions={ActionType.READ},
            priority=100,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        assert len(policy.subject_conditions) == 0
        assert len(policy.resource_conditions) == 0
        assert len(policy.environment_conditions) == 0
