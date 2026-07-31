import os

# -*- coding: utf-8 -*-
"""
GraphQL Authentication and Authorization
Implements permission control for GraphQL operations
"""

from functools import wraps
from typing import Any, Dict, List

from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from loguru import logger

security = HTTPBearer()


class Permission:
    """Permission enumeration"""

    READ_METRICS = "read:metrics"
    READ_ALERTS = "read:alerts"
    WRITE_ALERTS = "write:alerts"
    EXECUTE_REPAIRS = "execute:repairs"
    ADMIN = "admin"


class Role:
    """Role enumeration"""

    VIEWER = "viewer"
    OPERATOR = "operator"
    ADMIN = "admin"


ROLE_PERMISSIONS = {
    Role.VIEWER: [Permission.READ_METRICS, Permission.READ_ALERTS],
    Role.OPERATOR: [Permission.READ_METRICS, Permission.READ_ALERTS, Permission.WRITE_ALERTS],
    Role.ADMIN: [Permission.ADMIN],  # Admin has all permissions
}


class AuthContext:
    """Authentication context"""

    def __init__(self, user_id: str, role: str, permissions: List[str]):
        """
        Initialize auth context

        Args:
            user_id: User ID
            role: User role
            permissions: User permissions
        """
        self.user_id = user_id
        self.role = role
        self.permissions = permissions

    def has_permission(self, permission: str) -> bool:
        """
        Check if user has permission

        Args:
            permission: Permission to check

        Returns:
            True if has permission
        """
        return permission in self.permissions or Permission.ADMIN in self.permissions


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> AuthContext:
    """
    Get current user from credentials

    Args:
        credentials: HTTP authorization credentials

    Returns:
        Auth context

    Raises:
        HTTPException: If authentication fails
    """
    token = credentials.credentials

    # Validate token and get user info
    try:
        # default_value - integrate with actual authentication system
        user_info = validate_token(token)

        return AuthContext(
            user_id=user_info["user_id"],
            role=user_info["role"],
            permissions=user_info["permissions"],
        )
    except Exception as e:
        logger.error(f"Authentication failed: {e}")
        raise HTTPException(status_code=401, detail="Invalid authentication")


def validate_token(token: str) -> Dict[str, Any]:
    """
    Validate JWT token

    Args:
        token: JWT token string

    Returns:
        User information

    Raises:
        ValueError: If token is invalid
    """
    # default_value - implement actual JWT validation
    # For now, return mock user info
    if token == os.environ.get("MOCK_TOKEN", ""):
        return {"user_id": "user-1", "role": Role.ADMIN, "permissions": [Permission.ADMIN]}

    raise ValueError("Invalid token")


def require_permission(permission: str):
    """
    Decorator to require specific permission

    Args:
        permission: Required permission
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, auth: AuthContext, **kwargs):
            if not auth.has_permission(permission):
                raise HTTPException(status_code=403, detail=f"Permission required: {permission}")
            return await func(*args, auth=auth, **kwargs)

        return wrapper

    return decorator


def require_role(role: str):
    """
    Decorator to require specific role

    Args:
        role: Required role
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, auth: AuthContext, **kwargs):
            if auth.role != role and auth.role != Role.ADMIN:
                raise HTTPException(status_code=403, detail=f"Role required: {role}")
            return await func(*args, auth=auth, **kwargs)

        return wrapper

    return decorator
