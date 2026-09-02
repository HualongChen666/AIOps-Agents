# -*- coding: utf-8 -*-
"""
Authentication and Authorization Module
Provides JWT authentication and RBAC authorization for API endpoints
"""

from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from loguru import logger
from sqlalchemy.orm import Session

from config import JWT_ALGORITHM, JWT_AUDIENCE, JWT_ISSUER, JWT_SECRET_KEY
from core.database import get_db
from core.models import User

security = HTTPBearer()


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """
    Verify JWT token and return user ID

    Args:
        credentials: HTTP authorization credentials

    Returns:
        User ID from token

    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        token = credentials.credentials
        payload = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
            audience=JWT_AUDIENCE,
            issuer=JWT_ISSUER,
        )

        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
            )

        return user_id
    except JWTError as e:
        logger.error(f"JWT verification error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )


def get_current_user(
    user_id: str = Depends(verify_token), db: Session = Depends(get_db)
) -> User:
    """
    Get current user from database

    Args:
        user_id: User ID from token
        db: Database session

    Returns:
        User object

    Raises:
        HTTPException: If user not found or disabled
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if user.disabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )

    return user


def require_role(required_role: str):
    """
    Dependency factory to require specific role

    Args:
        required_role: Required role (admin, user, operator)

    Returns:
        Dependency function
    """

    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        """Check if user has required role"""
        if current_user.role != required_role and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required role: {required_role}",
            )
        return current_user

    return role_checker


def require_permission(resource_type: str, action: str):
    """
    Dependency factory to require specific permission

    Args:
        resource_type: Resource type (service_mesh, alert, repair, etc.)
        action: Action (create, read, update, delete, execute)

    Returns:
        Dependency function
    """

    def permission_checker(current_user: User = Depends(get_current_user)) -> User:
        """Check if user has required permission"""
        # Admin users have all permissions
        if current_user.role == "admin":
            return current_user

        # Define permission matrix
        PERMISSION_MATRIX = {
            "user": {
                "service_mesh": ["read"],
                "alert": ["read"],
                "repair": [],
                "approval": ["read"],
                "workflow": ["read"],
                "plugin": ["read"],
            },
            "operator": {
                "service_mesh": ["read", "create", "update"],
                "alert": ["read", "create", "update"],
                "repair": ["read", "execute"],
                "approval": ["read", "create"],
                "workflow": ["read", "create", "update", "delete", "execute"],
                "plugin": ["read", "create", "update", "execute"],
            },
        }

        user_permissions = PERMISSION_MATRIX.get(current_user.role, {}).get(resource_type, [])

        if action not in user_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required: {resource_type}:{action}",
            )

        return current_user

    return permission_checker


class RateLimiter:
    """Simple in-memory rate limiter"""

    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.requests: dict = {}

    def is_allowed(self, identifier: str) -> bool:
        """
        Check if request is allowed based on rate limit

        Args:
            identifier: Unique identifier (user_id or IP address)

        Returns:
            True if allowed, False otherwise
        """
        from datetime import datetime, timedelta

        now = datetime.utcnow()
        minute_ago = now - timedelta(minutes=1)

        # Clean old entries
        self.requests = {
            k: v for k, v in self.requests.items() if v > minute_ago
        }

        # Count requests in last minute
        user_requests = [
            timestamp for timestamp in self.requests.get(identifier, [])
            if timestamp > minute_ago
        ]

        if len(user_requests) >= self.requests_per_minute:
            return False

        # Add current request
        if identifier not in self.requests:
            self.requests[identifier] = []
        self.requests[identifier].append(now)

        return True


# Global rate limiter instance
rate_limiter = RateLimiter(requests_per_minute=60)


def check_rate_limit(identifier: str, requests_per_minute: int = 60):
    """
    Check rate limit for given identifier

    Args:
        identifier: Unique identifier (user_id or IP address)
        requests_per_minute: Maximum requests per minute

    Raises:
        HTTPException: If rate limit exceeded
    """
    limiter = RateLimiter(requests_per_minute=requests_per_minute)
    if not limiter.is_allowed(identifier):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please try again later.",
        )
