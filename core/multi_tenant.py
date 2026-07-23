# -*- coding: utf-8 -*-
"""Multi-tenant support for the AIOps Agent.

This module provides tenant isolation, context management,
and tenant-specific configuration for multi-tenant deployments.
"""

from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, cast

from loguru import logger

# Tenant context (coroutine-safe)
_current_tenant: ContextVar[Optional[str]] = ContextVar("current_tenant", default=None)

# Tenant storage
_tenant_configs: Dict[str, Dict[str, Any]] = {}
_tenant_users: Dict[str, List[str]] = {}  # tenant_id -> list of user_ids


class Tenant:
    """Tenant representation."""

    def __init__(
        self,
        tenant_id: str,
        name: str,
        description: str = "",
        config: Optional[Dict[str, Any]] = None,
        is_active: bool = True,
    ):
        self.tenant_id = tenant_id
        self.name = name
        self.description = description
        self.config = config or {}
        self.is_active = is_active
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Any]:
        """Convert tenant to dictionary."""
        return {
            "tenant_id": self.tenant_id,
            "name": self.name,
            "description": self.description,
            "config": self.config,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


def create_tenant(
    tenant_id: str,
    name: str,
    description: str = "",
    config: Optional[Dict[str, Any]] = None,
) -> bool:
    """Create a new tenant.

    Args:
        tenant_id: Unique tenant identifier
        name: Tenant name
        description: Tenant description
        config: Tenant-specific configuration

    Returns:
        True if successful
    """
    if tenant_id in _tenant_configs:
        logger.warning(f"Tenant already exists: {tenant_id}")
        return False

    tenant = Tenant(
        tenant_id=tenant_id,
        name=name,
        description=description,
        config=config,
    )

    _tenant_configs[tenant_id] = tenant.to_dict()
    _tenant_users[tenant_id] = []

    logger.info(f"Created tenant: {tenant_id}")
    return True


def get_tenant(tenant_id: str) -> Optional[Dict[str, Any]]:
    """Get tenant information.

    Args:
        tenant_id: Tenant identifier

    Returns:
        Tenant dictionary or None if not found
    """
    return _tenant_configs.get(tenant_id)


def update_tenant(
    tenant_id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None,
    is_active: Optional[bool] = None,
) -> bool:
    """Update tenant information.

    Args:
        tenant_id: Tenant identifier
        name: New name (optional)
        description: New description (optional)
        config: New configuration (optional)
        is_active: New active status (optional)

    Returns:
        True if successful
    """
    if tenant_id not in _tenant_configs:
        logger.error(f"Tenant not found: {tenant_id}")
        return False

    tenant_data = _tenant_configs[tenant_id]

    if name is not None:
        tenant_data["name"] = name
    if description is not None:
        tenant_data["description"] = description
    if config is not None:
        tenant_data["config"] = config
    if is_active is not None:
        tenant_data["is_active"] = is_active

    tenant_data["updated_at"] = datetime.now(timezone.utc).isoformat()

    logger.info(f"Updated tenant: {tenant_id}")
    return True


def delete_tenant(tenant_id: str) -> bool:
    """Delete a tenant.

    Args:
        tenant_id: Tenant identifier

    Returns:
        True if successful
    """
    if tenant_id not in _tenant_configs:
        logger.error(f"Tenant not found: {tenant_id}")
        return False

    del _tenant_configs[tenant_id]
    del _tenant_users[tenant_id]

    logger.info(f"Deleted tenant: {tenant_id}")
    return True


def list_tenants(active_only: bool = False) -> List[Dict[str, Any]]:
    """List all tenants.

    Args:
        active_only: Only return active tenants

    Returns:
        List of tenant dictionaries
    """
    tenants = list(_tenant_configs.values())

    if active_only:
        tenants = [t for t in tenants if t.get("is_active", True)]

    return tenants


def set_tenant_context(tenant_id: str) -> None:
    """Set the current tenant context.

    Args:
        tenant_id: Tenant identifier
    """
    if tenant_id not in _tenant_configs:
        logger.warning(f"Tenant not found: {tenant_id}")
        return

    if not _tenant_configs[tenant_id].get("is_active", True):
        logger.warning(f"Tenant is not active: {tenant_id}")
        return

    _current_tenant.set(tenant_id)
    logger.debug(f"Set tenant context: {tenant_id}")


def get_tenant_context() -> Optional[str]:
    """Get the current tenant context.

    Returns:
        Current tenant ID or None
    """
    return _current_tenant.get()


def clear_tenant_context() -> None:
    """Clear the current tenant context."""
    _current_tenant.set(None)
    logger.debug("Cleared tenant context")


def add_user_to_tenant(tenant_id: str, user_id: str) -> bool:
    """Add a user to a tenant.

    Args:
        tenant_id: Tenant identifier
        user_id: User identifier

    Returns:
        True if successful
    """
    if tenant_id not in _tenant_configs:
        logger.error(f"Tenant not found: {tenant_id}")
        return False

    if user_id in _tenant_users[tenant_id]:
        logger.warning(f"User already in tenant: {user_id} in {tenant_id}")
        return False

    _tenant_users[tenant_id].append(user_id)
    logger.info(f"Added user {user_id} to tenant {tenant_id}")
    return True


def remove_user_from_tenant(tenant_id: str, user_id: str) -> bool:
    """Remove a user from a tenant.

    Args:
        tenant_id: Tenant identifier
        user_id: User identifier

    Returns:
        True if successful
    """
    if tenant_id not in _tenant_configs:
        logger.error(f"Tenant not found: {tenant_id}")
        return False

    if user_id not in _tenant_users[tenant_id]:
        logger.warning(f"User not in tenant: {user_id} in {tenant_id}")
        return False

    _tenant_users[tenant_id].remove(user_id)
    logger.info(f"Removed user {user_id} from tenant {tenant_id}")
    return True


def get_tenant_users(tenant_id: str) -> List[str]:
    """Get users in a tenant.

    Args:
        tenant_id: Tenant identifier

    Returns:
        List of user IDs
    """
    return _tenant_users.get(tenant_id, []).copy()


def get_user_tenants(user_id: str) -> List[str]:
    """Get tenants for a user.

    Args:
        user_id: User identifier

    Returns:
        List of tenant IDs
    """
    return [tenant_id for tenant_id, users in _tenant_users.items() if user_id in users]


def get_tenant_config(tenant_id: str) -> Dict[str, Any]:
    """Get tenant-specific configuration.

    Args:
        tenant_id: Tenant identifier

    Returns:
        Tenant configuration dictionary
    """
    tenant = _tenant_configs.get(tenant_id)
    if tenant:
        return cast(Dict[str, Any], tenant.get("config", {}).copy())
    return {}


def is_user_in_tenant(user_id: str, tenant_id: str) -> bool:
    """Check if a user is in a tenant.

    Args:
        user_id: User identifier
        tenant_id: Tenant identifier

    Returns:
        True if user is in tenant
    """
    return user_id in _tenant_users.get(tenant_id, [])


def get_tenant_stats() -> Dict[str, Any]:
    """Get tenant statistics.

    Returns:
        Statistics dictionary
    """
    total_tenants = len(_tenant_configs)
    active_tenants = len([t for t in _tenant_configs.values() if t.get("is_active", True)])
    total_users = sum(len(users) for users in _tenant_users.values())

    return {
        "total_tenants": total_tenants,
        "active_tenants": active_tenants,
        "inactive_tenants": total_tenants - active_tenants,
        "total_users": total_users,
        "avg_users_per_tenant": total_users / total_tenants if total_tenants > 0 else 0,
    }


__all__ = [
    "Tenant",
    "create_tenant",
    "get_tenant",
    "update_tenant",
    "delete_tenant",
    "list_tenants",
    "set_tenant_context",
    "get_tenant_context",
    "clear_tenant_context",
    "add_user_to_tenant",
    "remove_user_from_tenant",
    "get_tenant_users",
    "get_user_tenants",
    "get_tenant_config",
    "is_user_in_tenant",
    "get_tenant_stats",
]
