# -*- coding: utf-8 -*-
"""Access control for secret management."""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set

try:
    from .config import Config
except ImportError:
    from config import Config
from loguru import logger


class AccessPermission:
    """Represents an access permission for a secret."""

    def __init__(
        self,
        secret_id: str,
        principal: str,
        principal_type: str,
        permissions: List[str],
        granted_by: str,
        granted_at: int = None,
    ):
        """Initialize access permission.

        Args:
            secret_id: Secret identifier
            principal: User or service account
            principal_type: Type of principal (user, service, role)
            permissions: List of permissions (read, write, delete, rotate)
            granted_by: Who granted this permission
            granted_at: Timestamp when granted
        """
        self.secret_id = secret_id
        self.principal = principal
        self.principal_type = principal_type
        self.permissions = set(permissions)
        self.granted_by = granted_by
        self.granted_at = granted_at or int(datetime.now().timestamp() * 1000)

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "secret_id": self.secret_id,
            "principal": self.principal,
            "principal_type": self.principal_type,
            "permissions": list(self.permissions),
            "granted_by": self.granted_by,
            "granted_at": self.granted_at,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "AccessPermission":
        """Create from dictionary."""
        return cls(
            secret_id=data["secret_id"],
            principal=data["principal"],
            principal_type=data["principal_type"],
            permissions=data["permissions"],
            granted_by=data["granted_by"],
            granted_at=data.get("granted_at"),
        )

    def has_permission(self, permission: str) -> bool:
        """Check if has a specific permission."""
        return permission in self.permissions

    def add_permission(self, permission: str) -> bool:
        """Add a permission."""
        if permission not in self.permissions:
            self.permissions.add(permission)
            return True
        return False

    def remove_permission(self, permission: str) -> bool:
        """Remove a permission."""
        if permission in self.permissions:
            self.permissions.remove(permission)
            return True
        return False


class AccessControl:
    """Access control manager for secrets."""

    VALID_PERMISSIONS = {"read", "write", "delete", "rotate", "grant", "revoke"}
    VALID_PRINCIPAL_TYPES = {"user", "service", "role"}

    def __init__(self, storage_path: str = None):
        """Initialize access control.

        Args:
            storage_path: Path to store access control data
        """
        self.storage_path = Path(storage_path or Config.STORAGE_PATH)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self._permissions: Dict[str, Dict[str, AccessPermission]] = {}
        # Structure: {secret_id: {principal: AccessPermission}}

        self._load_permissions()

        # Initialize default admin if not exists
        if Config.ENABLE_ACCESS_CONTROL:
            self._ensure_default_admin()

    def _load_permissions(self):
        """Load permissions from storage."""
        try:
            permissions_file = self.storage_path / "access_permissions.json"
            if permissions_file.exists():
                with open(permissions_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for secret_id, principals in data.items():
                        self._permissions[secret_id] = {}
                        for principal, perm_data in principals.items():
                            self._permissions[secret_id][principal] = AccessPermission.from_dict(perm_data)
                logger.info(f"Loaded access permissions for {len(self._permissions)} secrets")
            else:
                logger.info("No existing access permissions found")
        except Exception as e:
            logger.error(f"Failed to load access permissions: {e}")
            self._permissions = {}

    def _save_permissions(self) -> bool:
        """Save permissions to storage."""
        try:
            permissions_file = self.storage_path / "access_permissions.json"
            data = {}
            for secret_id, principals in self._permissions.items():
                data[secret_id] = {
                    principal: perm.to_dict()
                    for principal, perm in principals.items()
                }

            with open(permissions_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            # Set file permissions
            try:
                import stat
                os.chmod(permissions_file, stat.S_IRUSR | stat.S_IWUSR)
            except Exception:
                pass

            logger.debug("Saved access permissions")
            return True
        except Exception as e:
            logger.error(f"Failed to save access permissions: {e}")
            return False

    def _ensure_default_admin(self):
        """Ensure default admin has full access."""
        admin = Config.DEFAULT_ADMIN_PRINCIPAL
        # Grant admin all permissions on all secrets (will be checked dynamically)
        logger.debug(f"Default admin principal: {admin}")

    def _validate_permissions(self, permissions: List[str]) -> bool:
        """Validate permission list."""
        invalid = set(permissions) - self.VALID_PERMISSIONS
        if invalid:
            raise ValueError(f"Invalid permissions: {invalid}")
        return True

    def _validate_principal_type(self, principal_type: str) -> bool:
        """Validate principal type."""
        if principal_type not in self.VALID_PRINCIPAL_TYPES:
            raise ValueError(f"Invalid principal type: {principal_type}")
        return True

    def grant_access(
        self,
        secret_id: str,
        principal: str,
        principal_type: str,
        permissions: List[str],
        granted_by: str,
    ) -> bool:
        """Grant access to a secret.

        Args:
            secret_id: Secret identifier
            principal: User or service account
            principal_type: Type of principal
            permissions: List of permissions to grant
            granted_by: Who is granting this access

        Returns:
            True if successful
        """
        try:
            self._validate_permissions(permissions)
            self._validate_principal_type(principal_type)

            if secret_id not in self._permissions:
                self._permissions[secret_id] = {}

            # Check if permission already exists
            if principal in self._permissions[secret_id]:
                # Update existing permissions
                existing = self._permissions[secret_id][principal]
                existing.permissions.update(permissions)
                logger.info(f"Updated access for {principal} on {secret_id}")
            else:
                # Create new permission
                self._permissions[secret_id][principal] = AccessPermission(
                    secret_id=secret_id,
                    principal=principal,
                    principal_type=principal_type,
                    permissions=permissions,
                    granted_by=granted_by,
                )
                logger.info(f"Granted access for {principal} on {secret_id}")

            return self._save_permissions()

        except Exception as e:
            logger.error(f"Failed to grant access: {e}")
            raise

    def revoke_access(self, secret_id: str, principal: str, revoked_by: str) -> bool:
        """Revoke access to a secret.

        Args:
            secret_id: Secret identifier
            principal: User or service account
            revoked_by: Who is revoking this access

        Returns:
            True if successful
        """
        try:
            if secret_id not in self._permissions:
                logger.warning(f"No permissions found for secret {secret_id}")
                return False

            if principal not in self._permissions[secret_id]:
                logger.warning(f"No permissions found for {principal} on {secret_id}")
                return False

            del self._permissions[secret_id][principal]
            logger.info(f"Revoked access for {principal} on {secret_id} by {revoked_by}")

            # Clean up empty secret entries
            if not self._permissions[secret_id]:
                del self._permissions[secret_id]

            return self._save_permissions()

        except Exception as e:
            logger.error(f"Failed to revoke access: {e}")
            raise

    def check_permission(
        self, secret_id: str, principal: str, required_permission: str
    ) -> bool:
        """Check if a principal has a specific permission.

        Args:
            secret_id: Secret identifier
            principal: User or service account
            required_permission: Permission to check

        Returns:
            True if has permission
        """
        # Admin bypass
        if principal == Config.DEFAULT_ADMIN_PRINCIPAL:
            return True

        # Check if access control is enabled
        if not Config.ENABLE_ACCESS_CONTROL:
            return True

        # Check specific permission
        if secret_id in self._permissions:
            if principal in self._permissions[secret_id]:
                perm = self._permissions[secret_id][principal]
                return perm.has_permission(required_permission)

        return False

    def get_permissions(self, secret_id: str) -> List[Dict]:
        """Get all permissions for a secret.

        Args:
            secret_id: Secret identifier

        Returns:
            List of permission dictionaries
        """
        if secret_id not in self._permissions:
            return []

        return [perm.to_dict() for perm in self._permissions[secret_id].values()]

    def get_principal_permissions(self, principal: str) -> Dict[str, List[str]]:
        """Get all permissions for a principal across all secrets.

        Args:
            principal: User or service account

        Returns:
            Dictionary of {secret_id: [permissions]}
        """
        result = {}
        for secret_id, principals in self._permissions.items():
            if principal in principals:
                result[secret_id] = list(principals[principal].permissions)
        return result

    def list_principals(self, secret_id: str = None) -> List[str]:
        """List all principals with access.

        Args:
            secret_id: Optional secret ID to filter by

        Returns:
            List of principal identifiers
        """
        if secret_id:
            if secret_id in self._permissions:
                return list(self._permissions[secret_id].keys())
            return []

        # Get all unique principals
        principals = set()
        for secret_perms in self._permissions.values():
            principals.update(secret_perms.keys())
        return list(principals)

    def delete_secret_permissions(self, secret_id: str) -> bool:
        """Delete all permissions for a secret.

        Args:
            secret_id: Secret identifier

        Returns:
            True if successful
        """
        try:
            if secret_id in self._permissions:
                del self._permissions[secret_id]
                logger.info(f"Deleted all permissions for secret {secret_id}")
                return self._save_permissions()
            return True
        except Exception as e:
            logger.error(f"Failed to delete secret permissions: {e}")
            return False
