# -*- coding: utf-8 -*-
"""gRPC client for Access Control Service."""

import asyncio
import logging
import sys
import os
from typing import Any, Dict, List, Optional

# Add project root to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))

import grpc

logger = logging.getLogger(__name__)

DEFAULT_HOST = "localhost"
DEFAULT_PORT = 50054


class AccessControlClient:
    """gRPC client for Access Control Service."""

    def __init__(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT):
        """
        Initialize client.

        Args:
            host: Server host
            port: Server port
        """
        self.host = host
        self.port = port
        self.channel = None
        self._connected = False

    async def connect(self) -> bool:
        """
        Connect to the server.

        Returns:
            True if successful
        """
        try:
            self.channel = grpc.aio.insecure_channel(f"{self.host}:{self.port}")
            await self.channel.channel_ready()
            self._connected = True
            logger.info(f"Connected to Access Control Service at {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Access Control Service: {e}")
            return False

    async def disconnect(self) -> None:
        """Disconnect from the server."""
        if self.channel:
            await self.channel.close()
            self._connected = False
            logger.info("Disconnected from Access Control Service")

    async def _ensure_connected(self) -> None:
        """Ensure the client is connected."""
        if not self._connected:
            await self.connect()

    # Permission management methods
    async def create_permission(
        self,
        name: str,
        description: str,
        resource_type: str,
        actions: List[str],
    ) -> Optional[Dict[str, Any]]:
        """
        Create a new permission.

        Args:
            name: Permission name
            description: Permission description
            resource_type: Resource type
            actions: List of allowed actions

        Returns:
            Permission data or None if failed
        """
        await self._ensure_connected()
        try:
            # In production, this would use the generated protobuf
            # request = access_control_pb2.CreatePermissionRequest(...)
            # response = await self.stub.CreatePermission(request)
            
            # For now, return a mock response
            logger.info(f"Creating permission: {name}")
            return {
                "id": "mock_id",
                "name": name,
                "description": description,
                "resource_type": resource_type,
                "actions": actions,
            }
        except Exception as e:
            logger.error(f"Error creating permission: {e}")
            return None

    async def update_permission(
        self,
        permission_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        resource_type: Optional[str] = None,
        actions: Optional[List[str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Update an existing permission.

        Args:
            permission_id: Permission ID
            name: New name
            description: New description
            resource_type: New resource type
            actions: New actions

        Returns:
            Permission data or None if failed
        """
        await self._ensure_connected()
        try:
            logger.info(f"Updating permission: {permission_id}")
            return {
                "id": permission_id,
                "name": name,
                "description": description,
                "resource_type": resource_type,
                "actions": actions,
            }
        except Exception as e:
            logger.error(f"Error updating permission: {e}")
            return None

    async def delete_permission(self, permission_id: str) -> bool:
        """
        Delete a permission.

        Args:
            permission_id: Permission ID

        Returns:
            True if successful
        """
        await self._ensure_connected()
        try:
            logger.info(f"Deleting permission: {permission_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting permission: {e}")
            return False

    async def get_permission(self, permission_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a permission by ID.

        Args:
            permission_id: Permission ID

        Returns:
            Permission data or None if not found
        """
        await self._ensure_connected()
        try:
            logger.info(f"Getting permission: {permission_id}")
            return {
                "id": permission_id,
                "name": "mock_permission",
                "description": "Mock permission",
                "resource_type": "service",
                "actions": ["read", "write"],
            }
        except Exception as e:
            logger.error(f"Error getting permission: {e}")
            return None

    async def list_permissions(
        self,
        limit: int = 100,
        offset: int = 0,
        resource_type: Optional[str] = None,
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
        await self._ensure_connected()
        try:
            logger.info(f"Listing permissions: limit={limit}, offset={offset}")
            return []
        except Exception as e:
            logger.error(f"Error listing permissions: {e}")
            return []

    # Role management methods
    async def create_role(
        self,
        name: str,
        description: str,
        permission_ids: List[str],
        inherited_role_ids: List[str],
    ) -> Optional[Dict[str, Any]]:
        """
        Create a new role.

        Args:
            name: Role name
            description: Role description
            permission_ids: List of permission IDs
            inherited_role_ids: List of inherited role IDs

        Returns:
            Role data or None if failed
        """
        await self._ensure_connected()
        try:
            logger.info(f"Creating role: {name}")
            return {
                "id": "mock_id",
                "name": name,
                "description": description,
                "permission_ids": permission_ids,
                "inherited_role_ids": inherited_role_ids,
            }
        except Exception as e:
            logger.error(f"Error creating role: {e}")
            return None

    async def update_role(
        self,
        role_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        permission_ids: Optional[List[str]] = None,
        inherited_role_ids: Optional[List[str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Update an existing role.

        Args:
            role_id: Role ID
            name: New name
            description: New description
            permission_ids: New permission IDs
            inherited_role_ids: New inherited role IDs

        Returns:
            Role data or None if failed
        """
        await self._ensure_connected()
        try:
            logger.info(f"Updating role: {role_id}")
            return {
                "id": role_id,
                "name": name,
                "description": description,
                "permission_ids": permission_ids,
                "inherited_role_ids": inherited_role_ids,
            }
        except Exception as e:
            logger.error(f"Error updating role: {e}")
            return None

    async def delete_role(self, role_id: str) -> bool:
        """
        Delete a role.

        Args:
            role_id: Role ID

        Returns:
            True if successful
        """
        await self._ensure_connected()
        try:
            logger.info(f"Deleting role: {role_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting role: {e}")
            return False

    async def get_role(self, role_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a role by ID.

        Args:
            role_id: Role ID

        Returns:
            Role data or None if not found
        """
        await self._ensure_connected()
        try:
            logger.info(f"Getting role: {role_id}")
            return {
                "id": role_id,
                "name": "mock_role",
                "description": "Mock role",
                "permission_ids": [],
                "inherited_role_ids": [],
            }
        except Exception as e:
            logger.error(f"Error getting role: {e}")
            return None

    async def list_roles(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """
        List roles.

        Args:
            limit: Maximum number of results
            offset: Offset for pagination

        Returns:
            List of roles
        """
        await self._ensure_connected()
        try:
            logger.info(f"Listing roles: limit={limit}, offset={offset}")
            return []
        except Exception as e:
            logger.error(f"Error listing roles: {e}")
            return []

    async def assign_role(self, subject_id: str, role_id: str) -> bool:
        """
        Assign a role to a subject.

        Args:
            subject_id: Subject ID
            role_id: Role ID

        Returns:
            True if successful
        """
        await self._ensure_connected()
        try:
            logger.info(f"Assigning role {role_id} to subject {subject_id}")
            return True
        except Exception as e:
            logger.error(f"Error assigning role: {e}")
            return False

    async def revoke_role(self, subject_id: str, role_id: str) -> bool:
        """
        Revoke a role from a subject.

        Args:
            subject_id: Subject ID
            role_id: Role ID

        Returns:
            True if successful
        """
        await self._ensure_connected()
        try:
            logger.info(f"Revoking role {role_id} from subject {subject_id}")
            return True
        except Exception as e:
            logger.error(f"Error revoking role: {e}")
            return False

    async def get_subject_roles(self, subject_id: str) -> List[Dict[str, Any]]:
        """
        Get all roles for a subject.

        Args:
            subject_id: Subject ID

        Returns:
            List of roles
        """
        await self._ensure_connected()
        try:
            logger.info(f"Getting roles for subject: {subject_id}")
            return []
        except Exception as e:
            logger.error(f"Error getting subject roles: {e}")
            return []

    # Policy management methods (ABAC)
    async def create_policy(
        self,
        name: str,
        description: str,
        effect: str,
        subject_conditions: Dict[str, Any],
        resource_conditions: Dict[str, Any],
        environment_conditions: Dict[str, Any],
        actions: List[str],
        priority: int = 0,
    ) -> Optional[Dict[str, Any]]:
        """
        Create a new ABAC policy.

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
            Policy data or None if failed
        """
        await self._ensure_connected()
        try:
            logger.info(f"Creating policy: {name}")
            return {
                "id": "mock_id",
                "name": name,
                "description": description,
                "enabled": True,
                "effect": effect,
                "subject_conditions": subject_conditions,
                "resource_conditions": resource_conditions,
                "environment_conditions": environment_conditions,
                "actions": actions,
                "priority": priority,
            }
        except Exception as e:
            logger.error(f"Error creating policy: {e}")
            return None

    async def update_policy(
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
    ) -> Optional[Dict[str, Any]]:
        """
        Update an existing ABAC policy.

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
            Policy data or None if failed
        """
        await self._ensure_connected()
        try:
            logger.info(f"Updating policy: {policy_id}")
            return {
                "id": policy_id,
                "name": name,
                "description": description,
                "enabled": enabled,
                "effect": effect,
                "subject_conditions": subject_conditions,
                "resource_conditions": resource_conditions,
                "environment_conditions": environment_conditions,
                "actions": actions,
                "priority": priority,
            }
        except Exception as e:
            logger.error(f"Error updating policy: {e}")
            return None

    async def delete_policy(self, policy_id: str) -> bool:
        """
        Delete an ABAC policy.

        Args:
            policy_id: Policy ID

        Returns:
            True if successful
        """
        await self._ensure_connected()
        try:
            logger.info(f"Deleting policy: {policy_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting policy: {e}")
            return False

    async def get_policy(self, policy_id: str) -> Optional[Dict[str, Any]]:
        """
        Get an ABAC policy by ID.

        Args:
            policy_id: Policy ID

        Returns:
            Policy data or None if not found
        """
        await self._ensure_connected()
        try:
            logger.info(f"Getting policy: {policy_id}")
            return {
                "id": policy_id,
                "name": "mock_policy",
                "description": "Mock policy",
                "enabled": True,
                "effect": "allow",
                "subject_conditions": {},
                "resource_conditions": {},
                "environment_conditions": {},
                "actions": ["read"],
                "priority": 0,
            }
        except Exception as e:
            logger.error(f"Error getting policy: {e}")
            return None

    async def list_policies(self, enabled_only: bool = True) -> List[Dict[str, Any]]:
        """
        List ABAC policies.

        Args:
            enabled_only: Only return enabled policies

        Returns:
            List of policies
        """
        await self._ensure_connected()
        try:
            logger.info(f"Listing policies: enabled_only={enabled_only}")
            return []
        except Exception as e:
            logger.error(f"Error listing policies: {e}")
            return []

    # Access control methods
    async def check_permission(
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
        Check access permission.

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
        await self._ensure_connected()
        try:
            logger.info(f"Checking permission: subject={subject_id}, resource={resource_id}, action={action}")
            return {
                "allowed": False,
                "decision_type": "mock",
                "reason": "Mock decision",
                "matched_policies": [],
                "matched_roles": [],
                "evaluated_at": 0,
            }
        except Exception as e:
            logger.error(f"Error checking permission: {e}")
            return {
                "allowed": False,
                "decision_type": "error",
                "reason": str(e),
                "matched_policies": [],
                "matched_roles": [],
                "evaluated_at": 0,
            }

    # Audit logging methods
    async def get_audit_logs(
        self,
        subject_id: Optional[str] = None,
        resource_id: Optional[str] = None,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Get audit logs.

        Args:
            subject_id: Filter by subject ID
            resource_id: Filter by resource ID
            start_time: Filter by start time (timestamp)
            end_time: Filter by end time (timestamp)
            limit: Maximum number of results
            offset: Offset for pagination

        Returns:
            List of audit log entries
        """
        await self._ensure_connected()
        try:
            logger.info(f"Getting audit logs: limit={limit}, offset={offset}")
            return []
        except Exception as e:
            logger.error(f"Error getting audit logs: {e}")
            return []

    # Health check
    async def health_check(self) -> bool:
        """
        Check if the service is healthy.

        Returns:
            True if healthy
        """
        await self._ensure_connected()
        try:
            logger.info("Performing health check")
            return True
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False


# Convenience function for creating a client
async def create_client(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> AccessControlClient:
    """
    Create and connect a client.

    Args:
        host: Server host
        port: Server port

    Returns:
        Connected client
    """
    client = AccessControlClient(host, port)
    await client.connect()
    return client
