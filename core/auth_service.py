# -*- coding: utf-8 -*-
"""Authentication and authorization helpers."""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Optional

import bcrypt as _bcrypt_mod
import jwt
import passlib.handlers.bcrypt as _passlib_bcrypt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from sqlalchemy.orm import Session

import config
from core.auth_db import (
    SessionLocal,
    User,
    UserAssetPermission,
)
from core.token_blacklist import is_blacklisted

# bcrypt 4.1+/5.x exposes no __about__ and rejects passlib's >72-byte probes.
_bcrypt_mod.__about__ = type("about", (), {"__version__": "5.0.0"})()
_passlib_bcrypt._BcryptCommon._finalize_backend_mixin = classmethod(
    lambda cls, backend, dryrun: setattr(cls, "_workrounds_initialized", True) or True
)


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    auto_error=False,
)


def hash_password(password: str) -> str:
    """Hash a password using bcrypt.

    Args:
        password: Plain text password

    Returns:
        Hashed password string
    """
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plain text password against a hashed password.

    Args:
        plain: Plain text password to verify
        hashed: Hashed password to compare against

    Returns:
        True if password matches, False otherwise
    """
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict) -> str:
    """Create a JWT access token with standard claims.

    Args:
        data: Dictionary containing custom claims (e.g., sub, role)

    Returns:
        Encoded JWT token string

    Note:
        Automatically adds jti (JWT ID), exp (expiration), iat (issued at),
        iss (issuer), aud (audience), and tenant_id claims.
    """
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=config.JWT_ACCESS_EXPIRE_MINUTES)
    to_encode.update(
        {
            "jti": str(uuid.uuid4()),
            "exp": expire,
            "iat": now,
            "iss": config.JWT_ISSUER,
            "aud": config.JWT_AUDIENCE,
        }
    )
    # Ensure tenant is encoded in the token for multi-tenant endpoints.
    if "tenant_id" not in to_encode:
        to_encode["tenant_id"] = "default"
    return jwt.encode(
        to_encode,
        config.JWT_SECRET_KEY,
        algorithm=config.JWT_ALGORITHM,
    )


def decode_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT access token.

    Args:
        token: JWT token string to decode

    Returns:
        Decoded token payload as dictionary

    Raises:
        HTTPException: If token is invalid or expired (401)
        HTTPException: If token has been revoked/blacklisted (401)
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token,
            config.JWT_SECRET_KEY,
            algorithms=[config.JWT_ALGORITHM],
            issuer=config.JWT_ISSUER,
            audience=config.JWT_AUDIENCE,
        )
    except Exception as exc:
        raise credentials_exception from exc
    jti = payload.get("jti")
    if jti and is_blacklisted(jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload


def get_current_user(token: Optional[str] = Depends(oauth2_scheme)) -> User:
    """Get current authenticated user from JWT token.

    Args:
        token: Bearer token from authorization header (optional)

    Returns:
        User: Current authenticated user with tenant_id attached

    Raises:
        HTTPException: If token is missing, invalid, or user not found (401)
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_exception
    payload = decode_token(token)
    username = payload.get("sub")
    if not isinstance(username, str):
        raise credentials_exception

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
    finally:
        db.close()
    if user is None or not user.is_active:
        raise credentials_exception
    # Attach tenant_id from token so downstream code can enforce multi-tenant isolation.
    user.tenant_id = str(payload.get("tenant_id", "default"))
    return user


def has_role(user: User, *roles: str) -> bool:
    """Check if user has any of the specified roles.

    Args:
        user: User object to check
        *roles: One or more role names to check against

    Returns:
        True if user is active and has at least one of the specified roles
    """
    return bool(user.is_active and user.role in roles)


def require_roles(*roles: str) -> Callable[[User], User]:
    """FastAPI dependency that rejects requests from users without one of the allowed roles.

    Args:
        *roles: One or more role names that are allowed to access the endpoint

    Returns:
        Dependency function that returns the user if authorized

    Raises:
        HTTPException: If user lacks required roles (403)
    """

    def checker(user: User = Depends(get_current_user)) -> User:
        if not has_role(user, *roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of roles: {', '.join(roles)}",
            )
        return user

    return checker


def require_permission(permission: str, resource_type: str = "asset") -> Callable[[User], User]:
    """FastAPI dependency that checks a user's ABAC permission for a resource type.

    Args:
        permission: Permission name to check (e.g., "read", "write", "delete")
        resource_type: Type of resource (default: "asset")

    Returns:
        Dependency function that returns the user if authorized

    Raises:
        HTTPException: If user lacks required permission (403)
    """

    def checker(user: User = Depends(get_current_user)) -> User:
        if has_role(user, "admin"):
            return user
        db = SessionLocal()
        try:
            perms = (
                db.query(UserAssetPermission)
                .filter(
                    UserAssetPermission.user_id == user.id,
                    UserAssetPermission.tenant_id == getattr(user, "tenant_id", "default"),
                    UserAssetPermission.permission == permission,
                    UserAssetPermission.resource_type == resource_type,
                )
                .all()
            )
        finally:
            db.close()
        if not perms:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing permission: {permission} on {resource_type}",
            )
        return user

    return checker


def admin_count(db: Session) -> int:
    """Count the number of admin users in the database.

    Args:
        db: Database session

    Returns:
        Number of users with role "admin"
    """
    return db.query(User).filter(User.role == "admin").count()


def max_admin_check(db: Session) -> None:
    """Check if maximum admin limit has been reached.

    Args:
        db: Database session

    Raises:
        HTTPException: If there are already 3 or more admin users (400)
    """
    if admin_count(db) >= 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum number of admins (3) reached",
        )


def _asset_permission_check(
    user: User,
    asset_id: int,
    permissions: tuple,
    db: Optional[Session] = None,
) -> bool:
    """Check if user has specified permissions for an asset.

    Args:
        user: User object to check
        asset_id: Asset ID to check permissions for
        permissions: Tuple of permission names to check
        db: Optional database session (creates local session if None)

    Returns:
        True if user has any of the specified permissions for the asset
    """
    if user.role in ("admin", "operator"):
        return True
    if user.role == "business":
        local = db is None
        if local:
            db = SessionLocal()
        try:
            return (
                db.query(UserAssetPermission)
                .filter(
                    UserAssetPermission.user_id == user.id,
                    UserAssetPermission.asset_id == asset_id,
                    UserAssetPermission.permission.in_(permissions),
                )
                .first()
                is not None
            )
        finally:
            if local:
                db.close()
    return False


def can_edit_asset(user: User, asset_id: int, db: Optional[Session] = None) -> bool:
    """Check if user can edit an asset.

    Args:
        user: User object to check
        asset_id: Asset ID to check
        db: Optional database session

    Returns:
        True if user has edit permission for the asset
    """
    return _asset_permission_check(user, asset_id, ("edit",), db)


def can_view_asset(user: User, asset_id: int, db: Optional[Session] = None) -> bool:
    """Check if user can view an asset.

    Args:
        user: User object to check
        asset_id: Asset ID to check
        db: Optional database session

    Returns:
        True if user has view or edit permission for the asset
    """
    if user.role == "viewer":
        return True
    return _asset_permission_check(user, asset_id, ("view", "edit"), db)


def is_internal_key(request: Request) -> bool:
    """Check if request contains valid internal API key.

    Args:
        request: FastAPI request object

    Returns:
        True if X-Internal-Key header matches configured internal key
    """
    return request.headers.get("X-Internal-Key") == config.INTERNAL_API_KEY
