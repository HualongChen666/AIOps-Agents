# -*- coding: utf-8 -*-
"""Basic RBAC utilities for AIOps Agent.

This module provides basic role-based access control utilities
to complement the fine-grained RBAC in fine_rbac.py.
"""

from typing import Dict, Optional

from loguru import logger

# Simple in-memory user-to-tenant mapping
# In production, this would be stored in a database
_USER_TENANT_MAPPING: Dict[str, str] = {
    "admin": "default",
    "user": "default",
}


def get_user_tenant(username: str) -> Optional[str]:
    """Get the tenant ID for a given username.

    Args:
        username: The username to look up

    Returns:
        The tenant ID if found, None otherwise
    """
    return _USER_TENANT_MAPPING.get(username)


def set_user_tenant(username: str, tenant_id: str) -> None:
    """Set the tenant ID for a given username.

    Args:
        username: The username to update
        tenant_id: The tenant ID to assign
    """
    _USER_TENANT_MAPPING[username] = tenant_id
    logger.info(f"Set tenant '{tenant_id}' for user '{username}'")


def get_all_user_tenants() -> Dict[str, str]:
    """Get all user-to-tenant mappings.

    Returns:
        Dictionary mapping usernames to tenant IDs
    """
    return _USER_TENANT_MAPPING.copy()


__all__ = [
    "get_user_tenant",
    "set_user_tenant",
    "get_all_user_tenants",
]
