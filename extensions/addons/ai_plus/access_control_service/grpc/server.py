# -*- coding: utf-8 -*-
"""gRPC server for Access Control Service."""

import asyncio
import logging
import sys
import os
from datetime import datetime
from typing import Any, Dict

# Add project root to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))

import grpc
from grpc.aio import ServicerContext

from access_control_manager import AccessControlManager
from policy_enforcer import PolicyEnforcer
from permission_checker import PermissionChecker

logger = logging.getLogger(__name__)

SERVICE_NAME = "access_control_service"
DEFAULT_PORT = 50054


# Simple message classes (in production, these would be generated from proto)
class Permission:
    def __init__(
        self,
        id: str = "",
        name: str = "",
        description: str = "",
        resource_type: str = "",
        actions: list = None,
        created_at: int = 0,
        updated_at: int = 0,
    ):
        self.id = id
        self.name = name
        self.description = description
        self.resource_type = resource_type
        self.actions = actions or []
        self.created_at = created_at
        self.updated_at = updated_at


class Role:
    def __init__(
        self,
        id: str = "",
        name: str = "",
        description: str = "",
        permission_ids: list = None,
        inherited_role_ids: list = None,
        created_at: int = 0,
        updated_at: int = 0,
    ):
        self.id = id
        self.name = name
        self.description = description
        self.permission_ids = permission_ids or []
        self.inherited_role_ids = inherited_role_ids or []
        self.created_at = created_at
        self.updated_at = updated_at


class Policy:
    def __init__(
        self,
        id: str = "",
        name: str = "",
        description: str = "",
        enabled: bool = True,
        effect: str = "allow",
        subject_conditions: Dict[str, str] = None,
        resource_conditions: Dict[str, str] = None,
        environment_conditions: Dict[str, str] = None,
        actions: list = None,
        priority: int = 0,
        created_at: int = 0,
        updated_at: int = 0,
    ):
        self.id = id
        self.name = name
        self.description = description
        self.enabled = enabled
        self.effect = effect
        self.subject_conditions = subject_conditions or {}
        self.resource_conditions = resource_conditions or {}
        self.environment_conditions = environment_conditions or {}
        self.actions = actions or []
        self.priority = priority
        self.created_at = created_at
        self.updated_at = updated_at


class AccessRequest:
    def __init__(
        self,
        subject_id: str = "",
        subject_type: str = "",
        subject_attributes: Dict[str, str] = None,
        subject_roles: list = None,
        subject_groups: list = None,
        resource_id: str = "",
        resource_type: str = "",
        resource_attributes: Dict[str, str] = None,
        resource_owner: str = "",
        action: str = "",
        environment_attributes: Dict[str, str] = None,
    ):
        self.subject_id = subject_id
        self.subject_type = subject_type
        self.subject_attributes = subject_attributes or {}
        self.subject_roles = subject_roles or []
        self.subject_groups = subject_groups or []
        self.resource_id = resource_id
        self.resource_type = resource_type
        self.resource_attributes = resource_attributes or {}
        self.resource_owner = resource_owner
        self.action = action
        self.environment_attributes = environment_attributes or {}


class AccessDecision:
    def __init__(
        self,
        allowed: bool = False,
        decision_type: str = "",
        reason: str = "",
        matched_policies: list = None,
        matched_roles: list = None,
        evaluated_at: int = 0,
    ):
        self.allowed = allowed
        self.decision_type = decision_type
        self.reason = reason
        self.matched_policies = matched_policies or []
        self.matched_roles = matched_roles or []
        self.evaluated_at = evaluated_at


class AuditLog:
    def __init__(
        self,
        id: str = "",
        subject_id: str = "",
        resource_id: str = "",
        action: str = "",
        allowed: bool = False,
        decision_type: str = "",
        reason: str = "",
        metadata: Dict[str, str] = None,
        timestamp: int = 0,
    ):
        self.id = id
        self.subject_id = subject_id
        self.resource_id = resource_id
        self.action = action
        self.allowed = allowed
        self.decision_type = decision_type
        self.reason = reason
        self.metadata = metadata or {}
        self.timestamp = timestamp


class AccessControlServicer:
    """gRPC servicer for Access Control Service."""

    def __init__(self, storage):
        """
        Initialize servicer.

        Args:
            storage: Storage instance
        """
        self.access_control_manager = AccessControlManager(storage)
        self.policy_enforcer = PolicyEnforcer(self.access_control_manager)
        self.permission_checker = PermissionChecker(self.access_control_manager)

        # Initialize the manager
        if not self.access_control_manager.initialize():
            logger.error("Failed to initialize Access Control Manager")

    async def CreatePermission(self, request, context: ServicerContext):
        """Create a new permission."""
        try:
            permission_id = self.access_control_manager.create_permission(
                name=request.name,
                description=request.description if hasattr(request, 'description') else "",
                resource_type=request.resource_type,
                actions=list(request.actions) if hasattr(request, 'actions') else [],
            )

            if permission_id:
                permission = self.access_control_manager.get_permission(permission_id)
                return PermissionResponse(
                    permission=Permission(
                        id=permission["id"],
                        name=permission["name"],
                        description=permission["description"],
                        resource_type=permission["resource_type"],
                        actions=permission["actions"],
                        created_at=int(permission["created_at"].timestamp()) if permission["created_at"] else 0,
                        updated_at=int(permission["updated_at"].timestamp()) if permission["updated_at"] else 0,
                    ),
                    message="Permission created successfully"
                )
            else:
                context.set_code(grpc.StatusCode.INTERNAL)
                context.set_details("Failed to create permission")
                return PermissionResponse(permission=Permission(), message="Failed to create permission")

        except Exception as e:
            logger.error(f"Error creating permission: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return PermissionResponse(permission=Permission(), message=str(e))

    async def UpdatePermission(self, request, context: ServicerContext):
        """Update an existing permission."""
        try:
            success = self.access_control_manager.update_permission(
                permission_id=request.permission_id,
                name=request.name if hasattr(request, 'name') else None,
                description=request.description if hasattr(request, 'description') else None,
                resource_type=request.resource_type if hasattr(request, 'resource_type') else None,
                actions=list(request.actions) if hasattr(request, 'actions') else None,
            )

            if success:
                permission = self.access_control_manager.get_permission(request.permission_id)
                return PermissionResponse(
                    permission=Permission(
                        id=permission["id"],
                        name=permission["name"],
                        description=permission["description"],
                        resource_type=permission["resource_type"],
                        actions=permission["actions"],
                        created_at=int(permission["created_at"].timestamp()) if permission["created_at"] else 0,
                        updated_at=int(permission["updated_at"].timestamp()) if permission["updated_at"] else 0,
                    ),
                    message="Permission updated successfully"
                )
            else:
                context.set_code(grpc.StatusCode.INTERNAL)
                context.set_details("Failed to update permission")
                return PermissionResponse(permission=Permission(), message="Failed to update permission")

        except Exception as e:
            logger.error(f"Error updating permission: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return PermissionResponse(permission=Permission(), message=str(e))

    async def DeletePermission(self, request, context: ServicerContext):
        """Delete a permission."""
        try:
            success = self.access_control_manager.delete_permission(request.permission_id)
            if success:
                return StatusResponse(success=True, message="Permission deleted successfully")
            else:
                context.set_code(grpc.StatusCode.INTERNAL)
                context.set_details("Failed to delete permission")
                return StatusResponse(success=False, message="Failed to delete permission")

        except Exception as e:
            logger.error(f"Error deleting permission: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return StatusResponse(success=False, message=str(e))

    async def GetPermission(self, request, context: ServicerContext):
        """Get a permission by ID."""
        try:
            permission = self.access_control_manager.get_permission(request.permission_id)
            if permission:
                return PermissionResponse(
                    permission=Permission(
                        id=permission["id"],
                        name=permission["name"],
                        description=permission["description"],
                        resource_type=permission["resource_type"],
                        actions=permission["actions"],
                        created_at=int(permission["created_at"].timestamp()) if permission["created_at"] else 0,
                        updated_at=int(permission["updated_at"].timestamp()) if permission["updated_at"] else 0,
                    ),
                    message="Permission retrieved successfully"
                )
            else:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details("Permission not found")
                return PermissionResponse(permission=Permission(), message="Permission not found")

        except Exception as e:
            logger.error(f"Error getting permission: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return PermissionResponse(permission=Permission(), message=str(e))

    async def ListPermissions(self, request, context: ServicerContext):
        """List permissions."""
        try:
            limit = request.limit if hasattr(request, 'limit') else 100
            offset = request.offset if hasattr(request, 'offset') else 0
            resource_type = request.resource_type if hasattr(request, 'resource_type') else None

            permissions = self.access_control_manager.list_permissions(
                limit=limit, offset=offset, resource_type=resource_type
            )

            return PermissionsResponse(
                permissions=[
                    Permission(
                        id=p["id"],
                        name=p["name"],
                        description=p["description"],
                        resource_type=p["resource_type"],
                        actions=p["actions"],
                        created_at=int(p["created_at"].timestamp()) if p["created_at"] else 0,
                        updated_at=int(p["updated_at"].timestamp()) if p["updated_at"] else 0,
                    )
                    for p in permissions
                ],
                total=len(permissions)
            )

        except Exception as e:
            logger.error(f"Error listing permissions: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return PermissionsResponse(permissions=[], total=0)

    async def CreateRole(self, request, context: ServicerContext):
        """Create a new role."""
        try:
            role_id = self.access_control_manager.create_role(
                name=request.name,
                description=request.description if hasattr(request, 'description') else "",
                permission_ids=list(request.permission_ids) if hasattr(request, 'permission_ids') else [],
                inherited_role_ids=list(request.inherited_role_ids) if hasattr(request, 'inherited_role_ids') else [],
            )

            if role_id:
                role = self.access_control_manager.get_role(role_id)
                return RoleResponse(
                    role=Role(
                        id=role["id"],
                        name=role["name"],
                        description=role["description"],
                        permission_ids=role["permission_ids"],
                        inherited_role_ids=role["inherited_role_ids"],
                        created_at=int(role["created_at"].timestamp()) if role["created_at"] else 0,
                        updated_at=int(role["updated_at"].timestamp()) if role["updated_at"] else 0,
                    ),
                    message="Role created successfully"
                )
            else:
                context.set_code(grpc.StatusCode.INTERNAL)
                context.set_details("Failed to create role")
                return RoleResponse(role=Role(), message="Failed to create role")

        except Exception as e:
            logger.error(f"Error creating role: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return RoleResponse(role=Role(), message=str(e))

    async def UpdateRole(self, request, context: ServicerContext):
        """Update an existing role."""
        try:
            success = self.access_control_manager.update_role(
                role_id=request.role_id,
                name=request.name if hasattr(request, 'name') else None,
                description=request.description if hasattr(request, 'description') else None,
                permission_ids=list(request.permission_ids) if hasattr(request, 'permission_ids') else None,
                inherited_role_ids=list(request.inherited_role_ids) if hasattr(request, 'inherited_role_ids') else None,
            )

            if success:
                role = self.access_control_manager.get_role(request.role_id)
                return RoleResponse(
                    role=Role(
                        id=role["id"],
                        name=role["name"],
                        description=role["description"],
                        permission_ids=role["permission_ids"],
                        inherited_role_ids=role["inherited_role_ids"],
                        created_at=int(role["created_at"].timestamp()) if role["created_at"] else 0,
                        updated_at=int(role["updated_at"].timestamp()) if role["updated_at"] else 0,
                    ),
                    message="Role updated successfully"
                )
            else:
                context.set_code(grpc.StatusCode.INTERNAL)
                context.set_details("Failed to update role")
                return RoleResponse(role=Role(), message="Failed to update role")

        except Exception as e:
            logger.error(f"Error updating role: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return RoleResponse(role=Role(), message=str(e))

    async def DeleteRole(self, request, context: ServicerContext):
        """Delete a role."""
        try:
            success = self.access_control_manager.delete_role(request.role_id)
            if success:
                return StatusResponse(success=True, message="Role deleted successfully")
            else:
                context.set_code(grpc.StatusCode.INTERNAL)
                context.set_details("Failed to delete role")
                return StatusResponse(success=False, message="Failed to delete role")

        except Exception as e:
            logger.error(f"Error deleting role: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return StatusResponse(success=False, message=str(e))

    async def GetRole(self, request, context: ServicerContext):
        """Get a role by ID."""
        try:
            role = self.access_control_manager.get_role(request.role_id)
            if role:
                return RoleResponse(
                    role=Role(
                        id=role["id"],
                        name=role["name"],
                        description=role["description"],
                        permission_ids=role["permission_ids"],
                        inherited_role_ids=role["inherited_role_ids"],
                        created_at=int(role["created_at"].timestamp()) if role["created_at"] else 0,
                        updated_at=int(role["updated_at"].timestamp()) if role["updated_at"] else 0,
                    ),
                    message="Role retrieved successfully"
                )
            else:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details("Role not found")
                return RoleResponse(role=Role(), message="Role not found")

        except Exception as e:
            logger.error(f"Error getting role: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return RoleResponse(role=Role(), message=str(e))

    async def ListRoles(self, request, context: ServicerContext):
        """List roles."""
        try:
            limit = request.limit if hasattr(request, 'limit') else 100
            offset = request.offset if hasattr(request, 'offset') else 0

            roles = self.access_control_manager.list_roles(limit=limit, offset=offset)

            return RolesResponse(
                roles=[
                    Role(
                        id=r["id"],
                        name=r["name"],
                        description=r["description"],
                        permission_ids=r["permission_ids"],
                        inherited_role_ids=r["inherited_role_ids"],
                        created_at=int(r["created_at"].timestamp()) if r["created_at"] else 0,
                        updated_at=int(r["updated_at"].timestamp()) if r["updated_at"] else 0,
                    )
                    for r in roles
                ],
                total=len(roles)
            )

        except Exception as e:
            logger.error(f"Error listing roles: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return RolesResponse(roles=[], total=0)

    async def AssignRole(self, request, context: ServicerContext):
        """Assign a role to a subject."""
        try:
            success = self.access_control_manager.assign_role(request.subject_id, request.role_id)
            if success:
                return StatusResponse(success=True, message="Role assigned successfully")
            else:
                context.set_code(grpc.StatusCode.INTERNAL)
                context.set_details("Failed to assign role")
                return StatusResponse(success=False, message="Failed to assign role")

        except Exception as e:
            logger.error(f"Error assigning role: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return StatusResponse(success=False, message=str(e))

    async def RevokeRole(self, request, context: ServicerContext):
        """Revoke a role from a subject."""
        try:
            success = self.access_control_manager.revoke_role(request.subject_id, request.role_id)
            if success:
                return StatusResponse(success=True, message="Role revoked successfully")
            else:
                context.set_code(grpc.StatusCode.INTERNAL)
                context.set_details("Failed to revoke role")
                return StatusResponse(success=False, message="Failed to revoke role")

        except Exception as e:
            logger.error(f"Error revoking role: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return StatusResponse(success=False, message=str(e))

    async def GetSubjectRoles(self, request, context: ServicerContext):
        """Get all roles for a subject."""
        try:
            roles = self.access_control_manager.get_subject_roles(request.subject_id)
            return SubjectRolesResponse(
                roles=[
                    Role(
                        id=r["id"],
                        name=r["name"],
                        description=r["description"],
                        permission_ids=r["permission_ids"],
                        inherited_role_ids=r["inherited_role_ids"],
                        created_at=int(r["created_at"].timestamp()) if r["created_at"] else 0,
                        updated_at=int(r["updated_at"].timestamp()) if r["updated_at"] else 0,
                    )
                    for r in roles
                ],
                role_ids=[r["id"] for r in roles]
            )

        except Exception as e:
            logger.error(f"Error getting subject roles: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return SubjectRolesResponse(roles=[], role_ids=[])

    async def CreatePolicy(self, request, context: ServicerContext):
        """Create a new ABAC policy."""
        try:
            policy_id = self.access_control_manager.create_policy(
                name=request.name,
                description=request.description if hasattr(request, 'description') else "",
                effect=request.effect,
                subject_conditions=dict(request.subject_conditions) if hasattr(request, 'subject_conditions') else {},
                resource_conditions=dict(request.resource_conditions) if hasattr(request, 'resource_conditions') else {},
                environment_conditions=dict(request.environment_conditions) if hasattr(request, 'environment_conditions') else {},
                actions=list(request.actions) if hasattr(request, 'actions') else [],
                priority=request.priority if hasattr(request, 'priority') else 0,
            )

            if policy_id:
                policy = self.access_control_manager.get_policy(policy_id)
                return PolicyResponse(
                    policy=Policy(
                        id=policy["id"],
                        name=policy["name"],
                        description=policy["description"],
                        enabled=policy["enabled"],
                        effect=policy["effect"],
                        subject_conditions=policy["subject_conditions"],
                        resource_conditions=policy["resource_conditions"],
                        environment_conditions=policy["environment_conditions"],
                        actions=policy["actions"],
                        priority=policy["priority"],
                        created_at=int(datetime.fromisoformat(policy["created_at"]).timestamp()) if policy["created_at"] else 0,
                        updated_at=int(datetime.fromisoformat(policy["updated_at"]).timestamp()) if policy["updated_at"] else 0,
                    ),
                    message="Policy created successfully"
                )
            else:
                context.set_code(grpc.StatusCode.INTERNAL)
                context.set_details("Failed to create policy")
                return PolicyResponse(policy=Policy(), message="Failed to create policy")

        except Exception as e:
            logger.error(f"Error creating policy: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return PolicyResponse(policy=Policy(), message=str(e))

    async def UpdatePolicy(self, request, context: ServicerContext):
        """Update an existing ABAC policy."""
        try:
            success = self.access_control_manager.update_policy(
                policy_id=request.policy_id,
                name=request.name if hasattr(request, 'name') else None,
                description=request.description if hasattr(request, 'description') else None,
                enabled=request.enabled if hasattr(request, 'enabled') else None,
                effect=request.effect if hasattr(request, 'effect') else None,
                subject_conditions=dict(request.subject_conditions) if hasattr(request, 'subject_conditions') else None,
                resource_conditions=dict(request.resource_conditions) if hasattr(request, 'resource_conditions') else None,
                environment_conditions=dict(request.environment_conditions) if hasattr(request, 'environment_conditions') else None,
                actions=list(request.actions) if hasattr(request, 'actions') else None,
                priority=request.priority if hasattr(request, 'priority') else None,
            )

            if success:
                policy = self.access_control_manager.get_policy(request.policy_id)
                return PolicyResponse(
                    policy=Policy(
                        id=policy["id"],
                        name=policy["name"],
                        description=policy["description"],
                        enabled=policy["enabled"],
                        effect=policy["effect"],
                        subject_conditions=policy["subject_conditions"],
                        resource_conditions=policy["resource_conditions"],
                        environment_conditions=policy["environment_conditions"],
                        actions=policy["actions"],
                        priority=policy["priority"],
                        created_at=int(datetime.fromisoformat(policy["created_at"]).timestamp()) if policy["created_at"] else 0,
                        updated_at=int(datetime.fromisoformat(policy["updated_at"]).timestamp()) if policy["updated_at"] else 0,
                    ),
                    message="Policy updated successfully"
                )
            else:
                context.set_code(grpc.StatusCode.INTERNAL)
                context.set_details("Failed to update policy")
                return PolicyResponse(policy=Policy(), message="Failed to update policy")

        except Exception as e:
            logger.error(f"Error updating policy: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return PolicyResponse(policy=Policy(), message=str(e))

    async def DeletePolicy(self, request, context: ServicerContext):
        """Delete an ABAC policy."""
        try:
            success = self.access_control_manager.delete_policy(request.policy_id)
            if success:
                return StatusResponse(success=True, message="Policy deleted successfully")
            else:
                context.set_code(grpc.StatusCode.INTERNAL)
                context.set_details("Failed to delete policy")
                return StatusResponse(success=False, message="Failed to delete policy")

        except Exception as e:
            logger.error(f"Error deleting policy: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return StatusResponse(success=False, message=str(e))

    async def GetPolicy(self, request, context: ServicerContext):
        """Get an ABAC policy by ID."""
        try:
            policy = self.access_control_manager.get_policy(request.policy_id)
            if policy:
                return PolicyResponse(
                    policy=Policy(
                        id=policy["id"],
                        name=policy["name"],
                        description=policy["description"],
                        enabled=policy["enabled"],
                        effect=policy["effect"],
                        subject_conditions=policy["subject_conditions"],
                        resource_conditions=policy["resource_conditions"],
                        environment_conditions=policy["environment_conditions"],
                        actions=policy["actions"],
                        priority=policy["priority"],
                        created_at=int(datetime.fromisoformat(policy["created_at"]).timestamp()) if policy["created_at"] else 0,
                        updated_at=int(datetime.fromisoformat(policy["updated_at"]).timestamp()) if policy["updated_at"] else 0,
                    ),
                    message="Policy retrieved successfully"
                )
            else:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details("Policy not found")
                return PolicyResponse(policy=Policy(), message="Policy not found")

        except Exception as e:
            logger.error(f"Error getting policy: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return PolicyResponse(policy=Policy(), message=str(e))

    async def ListPolicies(self, request, context: ServicerContext):
        """List ABAC policies."""
        try:
            limit = request.limit if hasattr(request, 'limit') else 100
            offset = request.offset if hasattr(request, 'offset') else 0
            enabled_only = request.enabled_only if hasattr(request, 'enabled_only') else True

            policies = self.access_control_manager.list_policies(enabled_only=enabled_only)
            policies = policies[offset : offset + limit]

            return PoliciesResponse(
                policies=[
                    Policy(
                        id=p["id"],
                        name=p["name"],
                        description=p["description"],
                        enabled=p["enabled"],
                        effect=p["effect"],
                        subject_conditions=p["subject_conditions"],
                        resource_conditions=p["resource_conditions"],
                        environment_conditions=p["environment_conditions"],
                        actions=p["actions"],
                        priority=p["priority"],
                        created_at=int(datetime.fromisoformat(p["created_at"]).timestamp()) if p["created_at"] else 0,
                        updated_at=int(datetime.fromisoformat(p["updated_at"]).timestamp()) if p["updated_at"] else 0,
                    )
                    for p in policies
                ],
                total=len(policies)
            )

        except Exception as e:
            logger.error(f"Error listing policies: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return PoliciesResponse(policies=[], total=0)

    async def CheckPermission(self, request, context: ServicerContext):
        """Check access permission."""
        try:
            access_request = request.access_request if hasattr(request, 'access_request') else request

            decision = self.policy_enforcer.enforce_policy(
                subject_id=access_request.subject_id,
                subject_type=access_request.subject_type,
                subject_attributes=dict(access_request.subject_attributes) if hasattr(access_request, 'subject_attributes') else {},
                subject_roles=list(access_request.subject_roles) if hasattr(access_request, 'subject_roles') else [],
                subject_groups=list(access_request.subject_groups) if hasattr(access_request, 'subject_groups') else [],
                resource_id=access_request.resource_id,
                resource_type=access_request.resource_type,
                resource_attributes=dict(access_request.resource_attributes) if hasattr(access_request, 'resource_attributes') else {},
                resource_owner=access_request.resource_owner if hasattr(access_request, 'resource_owner') else None,
                action=access_request.action,
                environment_attributes=dict(access_request.environment_attributes) if hasattr(access_request, 'environment_attributes') else {},
            )

            return CheckPermissionResponse(
                decision=AccessDecision(
                    allowed=decision["allowed"],
                    decision_type=decision["decision_type"],
                    reason=decision["reason"],
                    matched_policies=decision["matched_policies"],
                    matched_roles=decision["matched_roles"],
                    evaluated_at=int(decision["evaluated_at"]),
                )
            )

        except Exception as e:
            logger.error(f"Error checking permission: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return CheckPermissionResponse(
                decision=AccessDecision(
                    allowed=False,
                    decision_type="error",
                    reason=str(e),
                    matched_policies=[],
                    matched_roles=[],
                    evaluated_at=0
                )
            )

    async def GetAuditLogs(self, request, context: ServicerContext):
        """Get audit logs."""
        try:
            subject_id = request.subject_id if hasattr(request, 'subject_id') else None
            resource_id = request.resource_id if hasattr(request, 'resource_id') else None
            start_time = request.start_time if hasattr(request, 'start_time') else None
            end_time = request.end_time if hasattr(request, 'end_time') else None
            limit = request.limit if hasattr(request, 'limit') else 100
            offset = request.offset if hasattr(request, 'offset') else 0

            logs = self.policy_enforcer.get_audit_logs(
                subject_id=subject_id,
                resource_id=resource_id,
                start_time=start_time,
                end_time=end_time,
                limit=limit,
                offset=offset,
            )

            return AuditLogsResponse(
                logs=[
                    AuditLog(
                        id=log["id"],
                        subject_id=log["subject_id"],
                        resource_id=log["resource_id"],
                        action=log["action"],
                        allowed=log["allowed"],
                        decision_type=log["decision_type"],
                        reason=log["reason"],
                        metadata={
                            "matched_policies": ",".join(log["matched_policies"]),
                            "matched_roles": ",".join(log["matched_roles"]),
                        },
                        timestamp=int(log["timestamp"]),
                    )
                    for log in logs
                ],
                total=len(logs)
            )

        except Exception as e:
            logger.error(f"Error getting audit logs: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return AuditLogsResponse(logs=[], total=0)

    async def HealthCheck(self, request, context: ServicerContext):
        """Health check."""
        return StatusResponse(success=True, message="Access Control Service is healthy")


async def serve(storage, port: int = DEFAULT_PORT):
    """
    Start the gRPC server.

    Args:
        storage: Storage instance
        port: Port to listen on
    """
    server = grpc.aio.server()

    servicer = AccessControlServicer(storage)
    
    # In production, we would add the generated servicer here
    # access_control_pb2.add_AccessControlServiceServicer_to_server(servicer, server)
    
    server.add_insecure_port(f"[::]:{port}")
    
    logger.info(f"Starting Access Control Service gRPC server on port {port}")
    await server.start()
    
    try:
        await server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("Shutting down server...")
        await server.stop(grace=5)


if __name__ == "__main__":
    # This would be called from main.py with proper storage
    logging.basicConfig(level=logging.INFO)
    logger.info("Access Control gRPC Server (standalone mode)")
