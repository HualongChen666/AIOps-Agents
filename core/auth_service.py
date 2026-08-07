# -*- coding: utf-8 -*-
"""Authentication and authorization helpers."""

import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
import passlib.handlers.bcrypt as _passlib_bcrypt
import bcrypt as _bcrypt_mod

# bcrypt 4.1+/5.x exposes no __about__ and rejects passlib's >72-byte probes.
_bcrypt_mod.__about__ = type("about", (), {"__version__": "5.0.0"})()
_passlib_bcrypt._BcryptCommon._finalize_backend_mixin = classmethod(
    lambda cls, backend, dryrun: setattr(cls, "_workrounds_initialized", True) or True
)

from sqlalchemy.orm import Session

import config
from core.auth_db import (
    Asset,
    SessionLocal,
    User,
    UserAssetPermission,
    get_session,
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    auto_error=False,
)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=config.JWT_ACCESS_EXPIRE_MINUTES)
    to_encode.update(
        {
            "exp": expire,
            "iat": now,
            "iss": config.JWT_ISSUER,
            "aud": config.JWT_AUDIENCE,
        }
    )
    return jwt.encode(
        to_encode,
        config.JWT_SECRET_KEY,
        algorithm=config.JWT_ALGORITHM,
    )


def get_current_user(token: Optional[str] = Depends(oauth2_scheme)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_exception
    try:
        payload = jwt.decode(
            token,
            config.JWT_SECRET_KEY,
            algorithms=[config.JWT_ALGORITHM],
            issuer=config.JWT_ISSUER,
            audience=config.JWT_AUDIENCE,
        )
        username = payload.get("sub")
        if not isinstance(username, str):
            raise credentials_exception
    except Exception as exc:
        raise credentials_exception from exc

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
    finally:
        db.close()
    if user is None or not user.is_active:
        raise credentials_exception
    return user


def has_role(user: User, *roles: str) -> bool:
    return bool(user.is_active and user.role in roles)


def require_roles(*roles: str):
    def _require(current_user: User = Depends(get_current_user)) -> User:
        if not has_role(current_user, *roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user

    return _require


def admin_count(db: Session) -> int:
    return db.query(User).filter(User.role == "admin").count()


def max_admin_check(db: Session) -> None:
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
    return _asset_permission_check(user, asset_id, ("edit",), db)


def can_view_asset(user: User, asset_id: int, db: Optional[Session] = None) -> bool:
    if user.role == "viewer":
        return True
    return _asset_permission_check(user, asset_id, ("view", "edit"), db)


def is_internal_key(request: Request) -> bool:
    return request.headers.get("X-Internal-Key") == config.INTERNAL_API_KEY
