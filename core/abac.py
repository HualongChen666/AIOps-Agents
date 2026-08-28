# -*- coding: utf-8 -*-
"""
Attribute-Based Access Control (ABAC) for AIOps Platform
Provides fine-grained access control based on user attributes,
resource attributes, and environmental context
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class ActionType(Enum):
    """Action types for access control"""

    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    EXECUTE = "execute"
    ADMIN = "admin"


class ResourceType(Enum):
    """Resource types"""

    ANOMALY = "anomaly"
    ALERT = "alert"
    METRIC = "metric"
    CONFIGURATION = "configuration"
    POLICY = "policy"
    WORKFLOW = "workflow"
    DEPLOYMENT = "deployment"
    SERVICE = "service"


@dataclass
class Subject:
    """Represents a user/service requesting access"""

    id: str
    type: str  # user, service, system
    attributes: Dict[str, Any]
    roles: Set[str]
    groups: Set[str]

    def get_attribute(self, key: str, default: Any = None) -> Any:
        """Get attribute value"""
        return self.attributes.get(key, default)


@dataclass
class Resource:
    """Represents a resource being accessed"""

    id: str
    type: ResourceType
    attributes: Dict[str, Any]
    owner: Optional[str] = None

    def get_attribute(self, key: str, default: Any = None) -> Any:
        """Get attribute value"""
        return self.attributes.get(key, default)


@dataclass
class Environment:
    """Represents environmental context"""

    attributes: Dict[str, Any]

    def get_attribute(self, key: str, default: Any = None) -> Any:
        """Get attribute value"""
        return self.attributes.get(key, default)


@dataclass
class Policy:
    """Represents an ABAC policy"""

    id: str
    name: str
    description: str
    enabled: bool
    effect: str  # allow, deny
    subject_conditions: Dict[str, Any]
    resource_conditions: Dict[str, Any]
    environment_conditions: Dict[str, Any]
    actions: Set[ActionType]
    priority: int
    created_at: datetime
    updated_at: datetime


class ABACEngine:
    """
    Attribute-Based Access Control Engine

    Evaluates access requests based on policies stored in PostgreSQL.
    Supports complex conditions on subject, resource, and environment attributes.
    """

    def __init__(self, postgres_storage):
        """
        Initialize ABAC Engine

        Args:
            postgres_storage: PostgreSQL storage instance or SQLAlchemy session
        """
        self.storage = postgres_storage
        self._policies: Dict[str, Policy] = {}
        self._is_initialized = False
        self._is_sqlalchemy = hasattr(postgres_storage, 'execute')  # Check if it's a SQLAlchemy session

        logger.info("ABAC Engine initialized")

    def initialize(self) -> bool:
        """
        Initialize ABAC engine and load policies

        Returns:
            True if initialization successful
        """
        try:
            # Create ABAC tables
            self._create_tables()

            # Load policies from storage
            self._load_policies()

            self._is_initialized = True
            logger.info("ABAC Engine initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize ABAC Engine: {e}")
            return False

    def _create_tables(self) -> None:
        """Create ABAC-specific tables"""
        create_policies_table = """
            CREATE TABLE IF NOT EXISTS abac_policies (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) UNIQUE NOT NULL,
                description TEXT,
                enabled BOOLEAN DEFAULT TRUE,
                effect VARCHAR(10) NOT NULL CHECK (effect IN ('allow', 'deny')),
                subject_conditions JSONB NOT NULL,
                resource_conditions JSONB NOT NULL,
                environment_conditions JSONB NOT NULL,
                actions JSONB NOT NULL,
                priority INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """

        create_policy_evaluations_table = """
            CREATE TABLE IF NOT EXISTS abac_policy_evaluations (
                id SERIAL PRIMARY KEY,
                policy_id INTEGER REFERENCES abac_policies(id),
                subject_id VARCHAR(255) NOT NULL,
                resource_id VARCHAR(255) NOT NULL,
                action VARCHAR(50) NOT NULL,
                decision VARCHAR(10) NOT NULL,
                evaluated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """

        create_indexes = [
            "CREATE INDEX IF NOT EXISTS idx_abac_policies_name ON abac_policies(name)",
            "CREATE INDEX IF NOT EXISTS idx_abac_policies_enabled ON abac_policies(enabled)",
            "CREATE INDEX IF NOT EXISTS idx_abac_policies_priority ON abac_policies(priority)",
            (
                "CREATE INDEX IF NOT EXISTS idx_abac_evaluations_subject "
                "ON abac_policy_evaluations(subject_id)"
            ),
            (
                "CREATE INDEX IF NOT EXISTS idx_abac_evaluations_resource "
                "ON abac_policy_evaluations(resource_id)"
            ),
            (
                "CREATE INDEX IF NOT EXISTS idx_abac_evaluations_evaluated_at "
                "ON abac_policy_evaluations(evaluated_at)"
            ),
        ]

        if self._is_sqlalchemy:
            # Use SQLAlchemy session
            try:
                self.storage.execute(create_policies_table)
                self.storage.execute(create_policy_evaluations_table)
                for index in create_indexes:
                    self.storage.execute(index)
                self.storage.commit()
                logger.info("ABAC tables created successfully (SQLAlchemy)")
            except Exception as e:
                logger.error(f"Failed to create ABAC tables with SQLAlchemy: {e}")
                self.storage.rollback()
        else:
            # Use traditional connection
            with self.storage.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(create_policies_table)
                    cursor.execute(create_policy_evaluations_table)

                    for index in create_indexes:
                        cursor.execute(index)

                    conn.commit()
                    logger.info("ABAC tables created successfully")

    def _load_policies(self) -> None:
        """Load policies from storage"""
        query = (
            "SELECT id, name, description, enabled, effect, "
            "subject_conditions, resource_conditions, "
            "environment_conditions, actions, priority, created_at, updated_at "
            "FROM abac_policies WHERE enabled = TRUE "
            "ORDER BY priority DESC LIMIT 1000"
        )

        if self._is_sqlalchemy:
            policies_data = self.storage.execute(query)
            policies_data = [dict(row._mapping) for row in policies_data]
        else:
            policies_data = self.storage.execute_query(query)

        self._policies = {}
        for policy_data in policies_data:
            policy = Policy(
                id=str(policy_data["id"]),
                name=policy_data["name"],
                description=policy_data["description"],
                enabled=policy_data["enabled"],
                effect=policy_data["effect"],
                subject_conditions=dict(policy_data["subject_conditions"]),
                resource_conditions=dict(policy_data["resource_conditions"]),
                environment_conditions=dict(policy_data["environment_conditions"]),
                actions={ActionType(a) for a in policy_data["actions"]},
                priority=policy_data["priority"],
                created_at=policy_data["created_at"],
                updated_at=policy_data["updated_at"],
            )
            self._policies[policy.id] = policy

        logger.info(f"Loaded {len(self._policies)} policies")

    def evaluate(
        self,
        subject: Subject,
        resource: Resource,
        action: ActionType,
        environment: Optional[Environment] = None,
    ) -> bool:
        """
        Evaluate access request

        Args:
            subject: Subject requesting access
            resource: Resource being accessed
            action: Action being performed
            environment: Environmental context

        Returns:
            True if access is allowed, False otherwise
        """
        if not self._is_initialized:
            logger.warning("ABAC Engine not initialized, defaulting to deny")
            return False

        if environment is None:
            environment = Environment(attributes={})

        # Sort policies by priority (higher priority first)
        sorted_policies = sorted(self._policies.values(), key=lambda p: p.priority, reverse=True)

        for policy in sorted_policies:
            if not policy.enabled:
                continue

            if action not in policy.actions:
                continue

            # Check if policy matches
            if self._matches_policy(subject, resource, environment, policy):
                decision = policy.effect == "allow"

                # Log evaluation
                self._log_evaluation(policy.id, subject.id, resource.id, action.value, decision)

                logger.info(
                    f"Access decision: {decision} for subject={subject.id}, "
                    f"resource={resource.id}, action={action.value}, policy={policy.name}"
                )

                return decision

        # Default deny if no matching policy
        logger.info(
            f"No matching policy for subject={subject.id}, "
            f"resource={resource.id}, action={action.value}, defaulting to deny"
        )
        return False

    def _matches_policy(
        self, subject: Subject, resource: Resource, environment: Environment, policy: Policy
    ) -> bool:
        """
        Check if request matches policy conditions

        Args:
            subject: Subject
            resource: Resource
            environment: Environment
            policy: Policy to match

        Returns:
            True if matches, False otherwise
        """
        # Check subject conditions
        if not self._matches_conditions(subject.attributes, policy.subject_conditions):
            return False

        # Check resource conditions
        if not self._matches_conditions(resource.attributes, policy.resource_conditions):
            return False

        # Check environment conditions
        if not self._matches_conditions(environment.attributes, policy.environment_conditions):
            return False

        return True

    def _matches_conditions(self, attributes: Dict[str, Any], conditions: Dict[str, Any]) -> bool:
        """
        Check if attributes match conditions

        Args:
            attributes: Actual attributes
            conditions: Required conditions

        Returns:
            True if matches, False otherwise
        """
        for key, condition in conditions.items():
            if key not in attributes:
                return False

            value = attributes[key]

            # Handle different condition types
            if isinstance(condition, dict):
                # Complex condition
                if "equals" in condition:
                    if value != condition["equals"]:
                        return False
                elif "in" in condition:
                    if value not in condition["in"]:
                        return False
                elif "contains" in condition:
                    if condition["contains"] not in value:
                        return False
                elif "gt" in condition:
                    if not (value > condition["gt"]):
                        return False
                elif "lt" in condition:
                    if not (value < condition["lt"]):
                        return False
                elif "gte" in condition:
                    if not (value >= condition["gte"]):
                        return False
                elif "lte" in condition:
                    if not (value <= condition["lte"]):
                        return False
                elif "regex" in condition:
                    import re

                    if not re.match(condition["regex"], str(value)):
                        return False
            else:
                # Simple equality check
                if value != condition:
                    return False

        return True

    def _log_evaluation(
        self, policy_id: str, subject_id: str, resource_id: str, action: str, decision: bool
    ) -> None:
        """Log policy evaluation"""
        try:
            with self.storage.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO abac_policy_evaluations
                        (policy_id, subject_id, resource_id, action, decision)
                        VALUES (%s, %s, %s, %s, %s)
                    """,
                        (policy_id, subject_id, resource_id, action, decision),
                    )
        except Exception as e:
            logger.error(f"Failed to log policy evaluation: {e}")

    def create_policy(
        self,
        name: str,
        description: str,
        effect: str,
        subject_conditions: Dict[str, Any],
        resource_conditions: Dict[str, Any],
        environment_conditions: Dict[str, Any],
        actions: List[str],
        priority: int = 0,
    ) -> Optional[str]:
        """
        Create a new policy

        Args:
            name: Policy name
            description: Policy description
            effect: Policy effect (allow/deny)
            subject_conditions: Subject conditions
            resource_conditions: Resource conditions
            environment_conditions: Environment conditions
            actions: Allowed actions
            priority: Policy priority

        Returns:
            Policy ID or None if failed
        """
        try:
            with self.storage.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO abac_policies
                        (name, description, effect, subject_conditions, resource_conditions,
                         environment_conditions, actions, priority)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING id
                    """,
                        (
                            name,
                            description,
                            effect,
                            json.dumps(subject_conditions),
                            json.dumps(resource_conditions),
                            json.dumps(environment_conditions),
                            json.dumps(actions),
                            priority,
                        ),
                    )

                    policy_id = cursor.fetchone()[0]
                    conn.commit()

                    # Reload policies
                    self._load_policies()

                    logger.info(f"Created policy: {name} (ID: {policy_id})")
                    return str(policy_id)

        except Exception as e:
            logger.error(f"Failed to create policy {name}: {e}")
            return None

    def update_policy(
        self,
        policy_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        enabled: Optional[bool] = None,
        effect: Optional[str] = None,
        subject_conditions: Optional[Dict[str, Any]] = None,
        resource_conditions: Optional[Dict[str, Any]] = None,
        environment_conditions: Optional[Dict[str, Any]] = None,
        actions: Optional[List[str]] = None,
        priority: Optional[int] = None,
    ) -> bool:
        """
        Update an existing policy

        Args:
            policy_id: Policy ID
            name: New name
            description: New description
            enabled: New enabled status
            effect: New effect
            subject_conditions: New subject conditions
            resource_conditions: New resource conditions
            environment_conditions: New environment conditions
            actions: New actions
            priority: New priority

        Returns:
            True if successful
        """
        try:
            updates: List[str] = []
            params: List[Any] = []

            if name is not None:
                updates.append("name = %s")
                params.append(name)
            if description is not None:
                updates.append("description = %s")
                params.append(description)
            if enabled is not None:
                updates.append("enabled = %s")
                params.append(enabled)
            if effect is not None:
                updates.append("effect = %s")
                params.append(effect)
            if subject_conditions is not None:
                updates.append("subject_conditions = %s")
                params.append(json.dumps(subject_conditions))
            if resource_conditions is not None:
                updates.append("resource_conditions = %s")
                params.append(json.dumps(resource_conditions))
            if environment_conditions is not None:
                updates.append("environment_conditions = %s")
                params.append(json.dumps(environment_conditions))
            if actions is not None:
                updates.append("actions = %s")
                params.append(json.dumps(actions))
            if priority is not None:
                updates.append("priority = %s")
                params.append(priority)

            if not updates:
                return True

            updates.append("updated_at = CURRENT_TIMESTAMP")
            params.append(policy_id)

            with self.storage.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Security: Use parameterized query to prevent SQL injection
                    # Column names are hardcoded in the updates list, not from user input
                    query = "".join(
                        ["UPDATE abac_policies SET ", ", ".join(updates), " WHERE id = %s"]
                    )
                    cursor.execute(query, params)
                    conn.commit()

                    # Reload policies
                    self._load_policies()

                    logger.info(f"Updated policy: {policy_id}")
                    return True

        except Exception as e:
            logger.error(f"Failed to update policy {policy_id}: {e}")
            return False

    def delete_policy(self, policy_id: str) -> bool:
        """
        Delete a policy

        Args:
            policy_id: Policy ID

        Returns:
            True if successful
        """
        try:
            with self.storage.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("DELETE FROM abac_policies WHERE id = %s", (policy_id,))
                    conn.commit()

                    # Reload policies
                    self._load_policies()

                    logger.info(f"Deleted policy: {policy_id}")
                    return True

        except Exception as e:
            logger.error(f"Failed to delete policy {policy_id}: {e}")
            return False

    def list_policies(self, enabled_only: bool = True) -> List[Dict[str, Any]]:
        """
        List policies

        Args:
            enabled_only: Only return enabled policies

        Returns:
            List of policies
        """
        try:
            query = (
                "SELECT id, name, description, enabled, effect, "
                "subject_conditions, resource_conditions, "
                "environment_conditions, actions, priority, created_at, updated_at "
                "FROM abac_policies"
            )
            if enabled_only:
                query += " WHERE enabled = TRUE"
            query += " ORDER BY priority DESC LIMIT 1000"

            policies_data = self.storage.execute_query(query)

            return [
                {
                    "id": str(p["id"]),
                    "name": p["name"],
                    "description": p["description"],
                    "enabled": p["enabled"],
                    "effect": p["effect"],
                    "subject_conditions": dict(p["subject_conditions"]),
                    "resource_conditions": dict(p["resource_conditions"]),
                    "environment_conditions": dict(p["environment_conditions"]),
                    "actions": list(p["actions"]),
                    "priority": p["priority"],
                    "created_at": p["created_at"].isoformat(),
                    "updated_at": p["updated_at"].isoformat(),
                }
                for p in policies_data
            ]

        except Exception as e:
            logger.error(f"Failed to list policies: {e}")
            return []


def create_abac_engine(postgres_storage) -> Optional[ABACEngine]:
    """
    Factory function to create ABAC Engine

    Args:
        postgres_storage: PostgreSQL storage instance

    Returns:
        ABACEngine instance or None if failed
    """
    try:
        engine = ABACEngine(postgres_storage)
        if engine.initialize():
            return engine
        return None
    except Exception as e:
        logger.error(f"Failed to create ABAC Engine: {e}")
        return None
