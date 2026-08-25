# -*- coding: utf-8 -*-
"""Access Control Manager - Core access control logic."""

import logging
import sys
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

# Add project root to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))

from core.rbac import get_user_tenant, set_user_tenant
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

logger = logging.getLogger(__name__)


class RBACManager:
    """Role-Based Access Control Manager."""

    def __init__(self, storage):
        """
        Initialize RBAC Manager.

        Args:
            storage: Storage instance for persistence
        """
        self.storage = storage
        self._permissions: Dict[str, Dict[str, Any]] = {}
        self._roles: Dict[str, Dict[str, Any]] = {}
        self._subject_roles: Dict[str, Set[str]] = {}
        self._is_initialized = False

    def initialize(self) -> bool:
        """
        Initialize RBAC manager and create tables.

        Returns:
            True if initialization successful
        """
        try:
            self._create_tables()
            self._load_permissions()
            self._load_roles()
            self._load_subject_roles()
            self._is_initialized = True
            logger.info("RBAC Manager initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize RBAC Manager: {e}")
            return False

    def _create_tables(self) -> None:
        """Create RBAC-specific tables."""
        create_permissions_table = """
            CREATE TABLE IF NOT EXISTS rbac_permissions (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) UNIQUE NOT NULL,
                description TEXT,
                resource_type VARCHAR(100) NOT NULL,
                actions JSONB NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """

        create_roles_table = """
            CREATE TABLE IF NOT EXISTS rbac_roles (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) UNIQUE NOT NULL,
                description TEXT,
                permission_ids JSONB NOT NULL,
                inherited_role_ids JSONB NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """

        create_subject_roles_table = """
            CREATE TABLE IF NOT EXISTS rbac_subject_roles (
                id SERIAL PRIMARY KEY,
                subject_id VARCHAR(255) NOT NULL,
                role_id INTEGER NOT NULL REFERENCES rbac_roles(id),
                assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(subject_id, role_id)
            )
        """

        create_indexes = [
            "CREATE INDEX IF NOT EXISTS idx_rbac_permissions_name ON rbac_permissions(name)",
            "CREATE INDEX IF NOT EXISTS idx_rbac_permissions_resource_type ON rbac_permissions(resource_type)",
            "CREATE INDEX IF NOT EXISTS idx_rbac_roles_name ON rbac_roles(name)",
            "CREATE INDEX IF NOT EXISTS idx_rbac_subject_roles_subject ON rbac_subject_roles(subject_id)",
            "CREATE INDEX IF NOT EXISTS idx_rbac_subject_roles_role ON rbac_subject_roles(role_id)",
        ]

        with self.storage.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(create_permissions_table)
                cursor.execute(create_roles_table)
                cursor.execute(create_subject_roles_table)

                for index in create_indexes:
                    cursor.execute(index)

                conn.commit()
                logger.info("RBAC tables created successfully")

    def _load_permissions(self) -> None:
        """Load permissions from storage."""
        permissions_data = self.storage.execute_query(
            "SELECT id, name, description, resource_type, actions, created_at, updated_at "
            "FROM rbac_permissions LIMIT 1000"
        )

        self._permissions = {}
        for perm_data in permissions_data:
            self._permissions[str(perm_data["id"])] = {
                "id": str(perm_data["id"]),
                "name": perm_data["name"],
                "description": perm_data["description"],
                "resource_type": perm_data["resource_type"],
                "actions": list(perm_data["actions"]),
                "created_at": perm_data["created_at"],
                "updated_at": perm_data["updated_at"],
            }

        logger.info(f"Loaded {len(self._permissions)} permissions")

    def _load_roles(self) -> None:
        """Load roles from storage."""
        roles_data = self.storage.execute_query(
            "SELECT id, name, description, permission_ids, inherited_role_ids, created_at, updated_at "
            "FROM rbac_roles LIMIT 1000"
        )

        self._roles = {}
        for role_data in roles_data:
            self._roles[str(role_data["id"])] = {
                "id": str(role_data["id"]),
                "name": role_data["name"],
                "description": role_data["description"],
                "permission_ids": list(role_data["permission_ids"]),
                "inherited_role_ids": list(role_data["inherited_role_ids"]),
                "created_at": role_data["created_at"],
                "updated_at": role_data["updated_at"],
            }

        logger.info(f"Loaded {len(self._roles)} roles")

    def _load_subject_roles(self) -> None:
        """Load subject-role mappings from storage."""
        subject_roles_data = self.storage.execute_query(
            "SELECT subject_id, role_id FROM rbac_subject_roles LIMIT 10000"
        )

        self._subject_roles = {}
        for mapping in subject_roles_data:
            subject_id = mapping["subject_id"]
            role_id = str(mapping["role_id"])
            if subject_id not in self._subject_roles:
                self._subject_roles[subject_id] = set()
            self._subject_roles[subject_id].add(role_id)

        logger.info(f"Loaded {len(self._subject_roles)} subject-role mappings")

    def create_permission(
        self,
        name: str,
        description: str,
        resource_type: str,
        actions: List[str],
    ) -> Optional[str]:
        """
        Create a new permission.

        Args:
            name: Permission name
            description: Permission description
            resource_type: Resource type
            actions: List of allowed actions

        Returns:
            Permission ID or None if failed
        """
        try:
            with self.storage.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO rbac_permissions (name, description, resource_type, actions)
                        VALUES (%s, %s, %s, %s)
                        RETURNING id
                    """,
                        (name, description, resource_type, actions),
                    )

                    permission_id = cursor.fetchone()[0]
                    conn.commit()

                    # Reload permissions
                    self._load_permissions()

                    logger.info(f"Created permission: {name} (ID: {permission_id})")
                    return str(permission_id)

        except Exception as e:
            logger.error(f"Failed to create permission {name}: {e}")
            return None

    def update_permission(
        self,
        permission_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        resource_type: Optional[str] = None,
        actions: Optional[List[str]] = None,
    ) -> bool:
        """
        Update an existing permission.

        Args:
            permission_id: Permission ID
            name: New name
            description: New description
            resource_type: New resource type
            actions: New actions

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
            if resource_type is not None:
                updates.append("resource_type = %s")
                params.append(resource_type)
            if actions is not None:
                updates.append("actions = %s")
                params.append(actions)

            if not updates:
                return True

            updates.append("updated_at = CURRENT_TIMESTAMP")
            params.append(permission_id)

            with self.storage.get_connection() as conn:
                with conn.cursor() as cursor:
                    query = "".join(
                        ["UPDATE rbac_permissions SET ", ", ".join(updates), " WHERE id = %s"]
                    )
                    cursor.execute(query, params)
                    conn.commit()

                    # Reload permissions
                    self._load_permissions()

                    logger.info(f"Updated permission: {permission_id}")
                    return True

        except Exception as e:
            logger.error(f"Failed to update permission {permission_id}: {e}")
            return False

    def delete_permission(self, permission_id: str) -> bool:
        """
        Delete a permission.

        Args:
            permission_id: Permission ID

        Returns:
            True if successful
        """
        try:
            with self.storage.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("DELETE FROM rbac_permissions WHERE id = %s", (permission_id,))
                    conn.commit()

                    # Reload permissions
                    self._load_permissions()

                    logger.info(f"Deleted permission: {permission_id}")
                    return True

        except Exception as e:
            logger.error(f"Failed to delete permission {permission_id}: {e}")
            return False

    def get_permission(self, permission_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a permission by ID.

        Args:
            permission_id: Permission ID

        Returns:
            Permission data or None if not found
        """
        return self._permissions.get(permission_id)

    def list_permissions(
        self, limit: int = 100, offset: int = 0, resource_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List permissions.

        Args:
            limit: Maximum number of results
            offset: Offset for pagination
            resource_type: Filter by resource type

        Returns:
            List of permissions
        """
        permissions = list(self._permissions.values())

        if resource_type:
            permissions = [p for p in permissions if p["resource_type"] == resource_type]

        return permissions[offset : offset + limit]

    def create_role(
        self,
        name: str,
        description: str,
        permission_ids: List[str],
        inherited_role_ids: List[str],
    ) -> Optional[str]:
        """
        Create a new role.

        Args:
            name: Role name
            description: Role description
            permission_ids: List of permission IDs
            inherited_role_ids: List of inherited role IDs

        Returns:
            Role ID or None if failed
        """
        try:
            with self.storage.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO rbac_roles (name, description, permission_ids, inherited_role_ids)
                        VALUES (%s, %s, %s, %s)
                        RETURNING id
                    """,
                        (name, description, permission_ids, inherited_role_ids),
                    )

                    role_id = cursor.fetchone()[0]
                    conn.commit()

                    # Reload roles
                    self._load_roles()

                    logger.info(f"Created role: {name} (ID: {role_id})")
                    return str(role_id)

        except Exception as e:
            logger.error(f"Failed to create role {name}: {e}")
            return None

    def update_role(
        self,
        role_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        permission_ids: Optional[List[str]] = None,
        inherited_role_ids: Optional[List[str]] = None,
    ) -> bool:
        """
        Update an existing role.

        Args:
            role_id: Role ID
            name: New name
            description: New description
            permission_ids: New permission IDs
            inherited_role_ids: New inherited role IDs

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
            if permission_ids is not None:
                updates.append("permission_ids = %s")
                params.append(permission_ids)
            if inherited_role_ids is not None:
                updates.append("inherited_role_ids = %s")
                params.append(inherited_role_ids)

            if not updates:
                return True

            updates.append("updated_at = CURRENT_TIMESTAMP")
            params.append(role_id)

            with self.storage.get_connection() as conn:
                with conn.cursor() as cursor:
                    query = "".join(
                        ["UPDATE rbac_roles SET ", ", ".join(updates), " WHERE id = %s"]
                    )
                    cursor.execute(query, params)
                    conn.commit()

                    # Reload roles
                    self._load_roles()

                    logger.info(f"Updated role: {role_id}")
                    return True

        except Exception as e:
            logger.error(f"Failed to update role {role_id}: {e}")
            return False

    def delete_role(self, role_id: str) -> bool:
        """
        Delete a role.

        Args:
            role_id: Role ID

        Returns:
            True if successful
        """
        try:
            with self.storage.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Delete subject-role mappings first
                    cursor.execute("DELETE FROM rbac_subject_roles WHERE role_id = %s", (role_id,))
                    # Delete role
                    cursor.execute("DELETE FROM rbac_roles WHERE id = %s", (role_id,))
                    conn.commit()

                    # Reload roles and subject roles
                    self._load_roles()
                    self._load_subject_roles()

                    logger.info(f"Deleted role: {role_id}")
                    return True

        except Exception as e:
            logger.error(f"Failed to delete role {role_id}: {e}")
            return False

    def get_role(self, role_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a role by ID.

        Args:
            role_id: Role ID

        Returns:
            Role data or None if not found
        """
        return self._roles.get(role_id)

    def list_roles(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """
        List roles.

        Args:
            limit: Maximum number of results
            offset: Offset for pagination

        Returns:
            List of roles
        """
        roles = list(self._roles.values())
        return roles[offset : offset + limit]

    def assign_role(self, subject_id: str, role_id: str) -> bool:
        """
        Assign a role to a subject.

        Args:
            subject_id: Subject ID
            role_id: Role ID

        Returns:
            True if successful
        """
        try:
            with self.storage.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO rbac_subject_roles (subject_id, role_id)
                        VALUES (%s, %s)
                        ON CONFLICT (subject_id, role_id) DO NOTHING
                    """,
                        (subject_id, role_id),
                    )
                    conn.commit()

                    # Reload subject roles
                    self._load_subject_roles()

                    logger.info(f"Assigned role {role_id} to subject {subject_id}")
                    return True

        except Exception as e:
            logger.error(f"Failed to assign role {role_id} to subject {subject_id}: {e}")
            return False

    def revoke_role(self, subject_id: str, role_id: str) -> bool:
        """
        Revoke a role from a subject.

        Args:
            subject_id: Subject ID
            role_id: Role ID

        Returns:
            True if successful
        """
        try:
            with self.storage.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "DELETE FROM rbac_subject_roles WHERE subject_id = %s AND role_id = %s",
                        (subject_id, role_id),
                    )
                    conn.commit()

                    # Reload subject roles
                    self._load_subject_roles()

                    logger.info(f"Revoked role {role_id} from subject {subject_id}")
                    return True

        except Exception as e:
            logger.error(f"Failed to revoke role {role_id} from subject {subject_id}: {e}")
            return False

    def get_subject_roles(self, subject_id: str) -> List[Dict[str, Any]]:
        """
        Get all roles for a subject.

        Args:
            subject_id: Subject ID

        Returns:
            List of roles
        """
        role_ids = self._subject_roles.get(subject_id, set())
        roles = []
        for role_id in role_ids:
            role = self._roles.get(role_id)
            if role:
                roles.append(role)
        return roles

    def get_effective_permissions(self, subject_id: str) -> Set[str]:
        """
        Get all effective permissions for a subject (including inherited).

        Args:
            subject_id: Subject ID

        Returns:
            Set of permission IDs
        """
        role_ids = self._subject_roles.get(subject_id, set())
        all_permissions = set()

        # Process each role and its inherited roles
        processed_roles = set()
        to_process = list(role_ids)

        while to_process:
            role_id = to_process.pop(0)
            if role_id in processed_roles:
                continue
            processed_roles.add(role_id)

            role = self._roles.get(role_id)
            if role:
                # Add direct permissions
                all_permissions.update(role["permission_ids"])
                # Add inherited roles to process
                to_process.extend(role["inherited_role_ids"])

        return all_permissions

    def check_permission(
        self, subject_id: str, resource_type: str, action: str
    ) -> bool:
        """
        Check if a subject has permission for an action on a resource type.

        Args:
            subject_id: Subject ID
            resource_type: Resource type
            action: Action

        Returns:
            True if allowed
        """
        effective_permissions = self.get_effective_permissions(subject_id)

        for perm_id in effective_permissions:
            perm = self._permissions.get(perm_id)
            if perm and perm["resource_type"] == resource_type and action in perm["actions"]:
                return True

        return False


class AccessControlManager:
    """Main Access Control Manager combining RBAC and ABAC."""

    def __init__(self, storage):
        """
        Initialize Access Control Manager.

        Args:
            storage: Storage instance for persistence
        """
        self.storage = storage
        self.rbac_manager = RBACManager(storage)
        self.abac_engine: Optional[ABACEngine] = None
        self._is_initialized = False

    def initialize(self) -> bool:
        """
        Initialize access control manager.

        Returns:
            True if initialization successful
        """
        try:
            # Initialize RBAC
            if not self.rbac_manager.initialize():
                logger.error("Failed to initialize RBAC Manager")
                return False

            # Initialize ABAC
            self.abac_engine = create_abac_engine(self.storage)
            if not self.abac_engine:
                logger.warning("Failed to initialize ABAC Engine, RBAC only mode")

            self._is_initialized = True
            logger.info("Access Control Manager initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize Access Control Manager: {e}")
            return False

    def check_access(
        self,
        subject_id: str,
        subject_type: str,
        subject_attributes: Dict[str, Any],
        subject_roles: List[str],
        subject_groups: List[str],
        resource_id: str,
        resource_type: str,
        resource_attributes: Dict[str, Any],
        resource_owner: Optional[str],
        action: str,
        environment_attributes: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Check access using combined RBAC and ABAC.

        Args:
            subject_id: Subject ID
            subject_type: Subject type
            subject_attributes: Subject attributes
            subject_roles: Subject roles
            subject_groups: Subject groups
            resource_id: Resource ID
            resource_type: Resource type
            resource_attributes: Resource attributes
            resource_owner: Resource owner
            action: Action
            environment_attributes: Environment attributes

        Returns:
            Access decision
        """
        if not self._is_initialized:
            logger.warning("Access Control Manager not initialized, defaulting to deny")
            return {
                "allowed": False,
                "decision_type": "none",
                "reason": "Access control not initialized",
                "matched_policies": [],
                "matched_roles": [],
                "evaluated_at": datetime.utcnow().timestamp(),
            }

        # Try RBAC first
        rbac_allowed = self.rbac_manager.check_permission(subject_id, resource_type, action)
        matched_roles = self.rbac_manager.get_subject_roles(subject_id)

        if rbac_allowed:
            logger.info(
                f"RBAC allowed: subject={subject_id}, resource={resource_id}, action={action}"
            )
            return {
                "allowed": True,
                "decision_type": "rbac",
                "reason": "RBAC permission granted",
                "matched_policies": [],
                "matched_roles": [r["name"] for r in matched_roles],
                "evaluated_at": datetime.utcnow().timestamp(),
            }

        # If RBAC denied, try ABAC
        if self.abac_engine:
            try:
                # Map resource type string to enum
                resource_type_enum = self._map_resource_type(resource_type)
                action_enum = self._map_action(action)

                subject = Subject(
                    id=subject_id,
                    type=subject_type,
                    attributes=subject_attributes,
                    roles=set(subject_roles),
                    groups=set(subject_groups),
                )

                resource = Resource(
                    id=resource_id,
                    type=resource_type_enum,
                    attributes=resource_attributes,
                    owner=resource_owner,
                )

                environment = Environment(attributes=environment_attributes)

                abac_allowed = self.abac_engine.evaluate(subject, resource, action_enum, environment)

                if abac_allowed:
                    logger.info(
                        f"ABAC allowed: subject={subject_id}, resource={resource_id}, action={action}"
                    )
                    return {
                        "allowed": True,
                        "decision_type": "abac",
                        "reason": "ABAC policy granted",
                        "matched_policies": ["ABAC policy"],
                        "matched_roles": [r["name"] for r in matched_roles],
                        "evaluated_at": datetime.utcnow().timestamp(),
                    }

            except Exception as e:
                logger.error(f"ABAC evaluation failed: {e}")

        # Default deny
        logger.info(
            f"Access denied: subject={subject_id}, resource={resource_id}, action={action}"
        )
        return {
            "allowed": False,
            "decision_type": "combined",
            "reason": "No matching RBAC or ABAC policy",
            "matched_policies": [],
            "matched_roles": [r["name"] for r in matched_roles],
            "evaluated_at": datetime.utcnow().timestamp(),
        }

    def _map_resource_type(self, resource_type: str) -> ResourceType:
        """Map string resource type to enum."""
        try:
            return ResourceType(resource_type.lower())
        except ValueError:
            return ResourceType.SERVICE

    def _map_action(self, action: str) -> ActionType:
        """Map string action to enum."""
        try:
            return ActionType(action.lower())
        except ValueError:
            return ActionType.READ

    # RBAC delegation methods
    def create_permission(self, name: str, description: str, resource_type: str, actions: List[str]):
        return self.rbac_manager.create_permission(name, description, resource_type, actions)

    def update_permission(self, permission_id: str, **kwargs):
        return self.rbac_manager.update_permission(permission_id, **kwargs)

    def delete_permission(self, permission_id: str):
        return self.rbac_manager.delete_permission(permission_id)

    def get_permission(self, permission_id: str):
        return self.rbac_manager.get_permission(permission_id)

    def list_permissions(self, limit: int = 100, offset: int = 0, resource_type: Optional[str] = None):
        return self.rbac_manager.list_permissions(limit, offset, resource_type)

    def create_role(self, name: str, description: str, permission_ids: List[str], inherited_role_ids: List[str]):
        return self.rbac_manager.create_role(name, description, permission_ids, inherited_role_ids)

    def update_role(self, role_id: str, **kwargs):
        return self.rbac_manager.update_role(role_id, **kwargs)

    def delete_role(self, role_id: str):
        return self.rbac_manager.delete_role(role_id)

    def get_role(self, role_id: str):
        return self.rbac_manager.get_role(role_id)

    def list_roles(self, limit: int = 100, offset: int = 0):
        return self.rbac_manager.list_roles(limit, offset)

    def assign_role(self, subject_id: str, role_id: str):
        return self.rbac_manager.assign_role(subject_id, role_id)

    def revoke_role(self, subject_id: str, role_id: str):
        return self.rbac_manager.revoke_role(subject_id, role_id)

    def get_subject_roles(self, subject_id: str):
        return self.rbac_manager.get_subject_roles(subject_id)

    # ABAC delegation methods
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
    ):
        if self.abac_engine:
            return self.abac_engine.create_policy(
                name, description, effect, subject_conditions, resource_conditions,
                environment_conditions, actions, priority
            )
        return None

    def update_policy(self, policy_id: str, **kwargs):
        if self.abac_engine:
            return self.abac_engine.update_policy(policy_id, **kwargs)
        return False

    def delete_policy(self, policy_id: str):
        if self.abac_engine:
            return self.abac_engine.delete_policy(policy_id)
        return False

    def get_policy(self, policy_id: str):
        if self.abac_engine:
            policies = self.abac_engine.list_policies(enabled_only=False)
            for policy in policies:
                if policy["id"] == policy_id:
                    return policy
        return None

    def list_policies(self, enabled_only: bool = True):
        if self.abac_engine:
            return self.abac_engine.list_policies(enabled_only)
        return []
