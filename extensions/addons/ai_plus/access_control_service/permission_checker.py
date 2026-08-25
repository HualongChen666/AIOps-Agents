# -*- coding: utf-8 -*-
"""Permission Checker - Helper for permission checking."""

import logging
import sys
import os
from typing import Any, Dict, List, Optional, Set

# Add project root to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))

logger = logging.getLogger(__name__)


class PermissionChecker:
    """Permission Checker for simplified permission validation."""

    def __init__(self, access_control_manager):
        """
        Initialize Permission Checker.

        Args:
            access_control_manager: AccessControlManager instance
        """
        self.access_control_manager = access_control_manager

    def check(
        self,
        subject_id: str,
        resource_type: str,
        action: str,
        resource_id: Optional[str] = None,
        subject_attributes: Optional[Dict[str, Any]] = None,
        resource_attributes: Optional[Dict[str, Any]] = None,
        environment_attributes: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Simple permission check.

        Args:
            subject_id: Subject ID
            resource_type: Resource type
            action: Action
            resource_id: Resource ID (optional)
            subject_attributes: Subject attributes (optional)
            resource_attributes: Resource attributes (optional)
            environment_attributes: Environment attributes (optional)

        Returns:
            True if allowed
        """
        decision = self.access_control_manager.check_access(
            subject_id=subject_id,
            subject_type="user",
            subject_attributes=subject_attributes or {},
            subject_roles=[],
            subject_groups=[],
            resource_id=resource_id or "unknown",
            resource_type=resource_type,
            resource_attributes=resource_attributes or {},
            resource_owner=None,
            action=action,
            environment_attributes=environment_attributes or {},
        )

        return decision["allowed"]

    def check_batch(
        self,
        subject_id: str,
        checks: List[Dict[str, Any]],
    ) -> Dict[str, bool]:
        """
        Batch permission check.

        Args:
            subject_id: Subject ID
            checks: List of check dictionaries with keys:
                    - resource_type: Resource type
                    - action: Action
                    - resource_id: Resource ID (optional)
                    - subject_attributes: Subject attributes (optional)
                    - resource_attributes: Resource attributes (optional)
                    - environment_attributes: Environment attributes (optional)

        Returns:
            Dictionary mapping check index to boolean result
        """
        results = {}
        for i, check in enumerate(checks):
            results[str(i)] = self.check(
                subject_id=subject_id,
                resource_type=check.get("resource_type", "unknown"),
                action=check.get("action", "read"),
                resource_id=check.get("resource_id"),
                subject_attributes=check.get("subject_attributes"),
                resource_attributes=check.get("resource_attributes"),
                environment_attributes=check.get("environment_attributes"),
            )
        return results

    def get_permissions(
        self,
        subject_id: str,
        resource_type: Optional[str] = None,
    ) -> Set[str]:
        """
        Get all permissions for a subject.

        Args:
            subject_id: Subject ID
            resource_type: Filter by resource type (optional)

        Returns:
            Set of permission strings in format "resource_type:action"
        """
        permissions = set()

        # Get effective permissions from RBAC
        effective_permissions = self.access_control_manager.rbac_manager.get_effective_permissions(
            subject_id
        )

        for perm_id in effective_permissions:
            perm = self.access_control_manager.rbac_manager.get_permission(perm_id)
            if perm:
                if resource_type is None or perm["resource_type"] == resource_type:
                    for action in perm["actions"]:
                        permissions.add(f"{perm['resource_type']}:{action}")

        return permissions

    def has_any_permission(
        self,
        subject_id: str,
        resource_type: str,
        actions: List[str],
    ) -> bool:
        """
        Check if subject has any of the specified permissions.

        Args:
            subject_id: Subject ID
            resource_type: Resource type
            actions: List of actions to check

        Returns:
            True if subject has any of the permissions
        """
        for action in actions:
            if self.check(subject_id, resource_type, action):
                return True
        return False

    def has_all_permissions(
        self,
        subject_id: str,
        resource_type: str,
        actions: List[str],
    ) -> bool:
        """
        Check if subject has all of the specified permissions.

        Args:
            subject_id: Subject ID
            resource_type: Resource type
            actions: List of actions to check

        Returns:
            True if subject has all of the permissions
        """
        for action in actions:
            if not self.check(subject_id, resource_type, action):
                return False
        return True

    def get_role_permissions(self, role_id: str) -> Set[str]:
        """
        Get all permissions for a role (including inherited).

        Args:
            role_id: Role ID

        Returns:
            Set of permission strings in format "resource_type:action"
        """
        permissions = set()
        role = self.access_control_manager.rbac_manager.get_role(role_id)

        if not role:
            return permissions

        # Process role and inherited roles
        processed_roles = set()
        to_process = [role_id]

        while to_process:
            current_role_id = to_process.pop(0)
            if current_role_id in processed_roles:
                continue
            processed_roles.add(current_role_id)

            current_role = self.access_control_manager.rbac_manager.get_role(current_role_id)
            if current_role:
                # Add direct permissions
                for perm_id in current_role["permission_ids"]:
                    perm = self.access_control_manager.rbac_manager.get_permission(perm_id)
                    if perm:
                        for action in perm["actions"]:
                            permissions.add(f"{perm['resource_type']}:{action}")

                # Add inherited roles to process
                to_process.extend(current_role["inherited_role_ids"])

        return permissions

    def get_subject_effective_roles(self, subject_id: str) -> List[str]:
        """
        Get all effective roles for a subject (including inherited).

        Args:
            subject_id: Subject ID

        Returns:
            List of role names
        """
        role_ids = self.access_control_manager.rbac_manager.get_subject_roles(subject_id)
        role_names = [role["name"] for role in role_ids]

        # Add inherited roles
        processed_roles = set()
        to_process = [role["id"] for role in role_ids]

        while to_process:
            current_role_id = to_process.pop(0)
            if current_role_id in processed_roles:
                continue
            processed_roles.add(current_role_id)

            current_role = self.access_control_manager.rbac_manager.get_role(current_role_id)
            if current_role:
                for inherited_role_id in current_role["inherited_role_ids"]:
                    inherited_role = self.access_control_manager.rbac_manager.get_role(inherited_role_id)
                    if inherited_role and inherited_role["name"] not in role_names:
                        role_names.append(inherited_role["name"])
                        to_process.append(inherited_role_id)

        return role_names
