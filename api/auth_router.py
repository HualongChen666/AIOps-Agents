# -*- coding: utf-8 -*-
"""Authentication API router."""

from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core.auth_db import User, get_session
from core.auth_service import (
    create_access_token,
    decode_token,
    get_current_user,
    hash_password,
    max_admin_check,
    oauth2_scheme,
    verify_password,
)
from core.token_blacklist import blacklist_jti

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class _UserOut(BaseModel):
    id: int
    username: str
    role: str
    is_active: bool
    created_at: Optional[datetime]

    model_config = {"from_attributes": True}


class _LoginRequest(BaseModel):
    username: str
    password: str


class _ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


def _user_dict(user: User) -> _UserOut:
    """Convert User model to UserOut response model.

    Args:
        user: User database model instance

    Returns:
        UserOut: Pydantic model for API response
    """
    return _UserOut.model_validate(user)


@router.post("/login")
def login(
    req: _LoginRequest,
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    """Authenticate user and return access token.

    Args:
        req: Login request containing username and password
        db: Database session dependency

    Returns:
        Dictionary containing access token, token type, and user information

    Raises:
        HTTPException: If username or password is invalid (401)
    """
    user = db.query(User).filter(User.username == req.username).first()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    token = create_access_token({"sub": user.username, "role": user.role})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": _user_dict(user),
    }


@router.post("/register-admin", response_model=_UserOut)
def register_admin(
    req: _LoginRequest,
    db: Session = Depends(get_session),
) -> _UserOut:
    """Register the first admin user (bootstrap operation).

    This endpoint is only allowed when no users exist in the database.
    It creates an admin user with full system access.

    Args:
        req: Registration request containing username and password
        db: Database session dependency

    Returns:
        UserOut: Created user information

    Raises:
        HTTPException: If users already exist (400)
    """
    if db.query(User).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bootstrap registration only allowed when no users exist",
        )
    max_admin_check(db)
    user = User(
        username=req.username,
        password_hash=hash_password(req.password),
        role="admin",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _user_dict(user)


@router.get("/me", response_model=_UserOut)
def me(current_user: User = Depends(get_current_user)) -> _UserOut:
    """Get current authenticated user information.

    Args:
        current_user: Current authenticated user dependency

    Returns:
        UserOut: Current user information
    """
    return _user_dict(current_user)


@router.post("/change-password")
def change_password(
    req: _ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
) -> dict[str, str]:
    """Change current user's password.

    Args:
        req: Password change request containing old and new passwords
        current_user: Current authenticated user dependency
        db: Database session dependency

    Returns:
        Dictionary with success message

    Raises:
        HTTPException: If old password is incorrect (401)
    """
    if not verify_password(req.old_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Old password is incorrect",
        )
    merged = db.merge(current_user)
    merged.password_hash = hash_password(req.new_password)
    db.commit()
    db.refresh(merged)
    return {"detail": "Password updated"}


@router.post("/logout")
def logout(
    current_user: User = Depends(get_current_user),
    token: str = Depends(oauth2_scheme),
) -> dict[str, str]:
    """Logout current user and invalidate token.

    Adds the token's JTI (JWT ID) to the blacklist to prevent reuse.

    Args:
        current_user: Current authenticated user dependency
        token: Bearer token from authorization header

    Returns:
        Dictionary with success message
    """
    payload = decode_token(token)
    jti = payload.get("jti")
    exp = payload.get("exp")
    if jti:
        from datetime import datetime

        expires_at = datetime.utcfromtimestamp(exp) if exp else None
        blacklist_jti(jti, expires_at)
    return {"detail": "Logged out"}
