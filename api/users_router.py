# -*- coding: utf-8 -*-
"""User management API router."""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.auth_db import User, UserAssetPermission, get_session
from core.auth_service import (
    admin_count,
    get_current_user,
    has_role,
    hash_password,
    max_admin_check,
    require_roles,
)

router = APIRouter(prefix="/api/v1/users", tags=["users"])

_VALID_ROLES = {"viewer", "business", "operator", "admin"}
_VALID_PERMS = {"view", "edit"}


class _UserOut(BaseModel):
    id: int
    username: str
    role: str
    is_active: bool
    created_at: Optional[datetime]

    model_config = {"from_attributes": True}


class _PermissionItem(BaseModel):
    asset_id: int
    permission: str


class _UserCreate(BaseModel):
    username: str
    password: str
    role: str = "viewer"
    is_active: bool = True
    permissions: List[_PermissionItem] = Field(default_factory=list)


class _UserUpdate(BaseModel):
    role: Optional[str] = None
    is_active: Optional[bool] = None
    new_password: Optional[str] = None


class _PermissionsUpdate(BaseModel):
    permissions: List[_PermissionItem]


def _user_out(user: User) -> _UserOut:
    return _UserOut.model_validate(user)


@router.get("/", response_model=List[_UserOut])
def list_users(
    db: Session = Depends(get_session),
    current_user: User = Depends(require_roles("admin")),
):
    return [_user_out(u) for u in db.query(User).all()]


@router.post("/", response_model=_UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    req: _UserCreate,
    db: Session = Depends(get_session),
    current_user: User = Depends(require_roles("admin")),
):
    if req.role not in _VALID_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role. Must be one of: {', '.join(sorted(_VALID_ROLES))}",
        )
    if db.query(User).filter(User.username == req.username).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken",
        )
    if req.role == "admin":
        max_admin_check(db)
    user = User(
        username=req.username,
        password_hash=hash_password(req.password),
        role=req.role,
        is_active=req.is_active,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    for item in req.permissions:
        if item.permission not in _VALID_PERMS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid permission: {item.permission}",
            )
        db.add(
            UserAssetPermission(
                user_id=user.id,
                asset_id=item.asset_id,
                permission=item.permission,
            )
        )
    if req.permissions:
        db.commit()
    return _user_out(user)


@router.get("/me", response_model=_UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return _user_out(current_user)


@router.get("/{id}", response_model=_UserOut)
def get_user(
    id: int,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if not (has_role(current_user, "admin") or current_user.id == id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    user = db.query(User).filter(User.id == id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return _user_out(user)


@router.put("/{id}", response_model=_UserOut)
def update_user(
    id: int,
    req: _UserUpdate,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    user = db.query(User).filter(User.id == id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    is_admin = has_role(current_user, "admin")
    is_self = current_user.id == id
    if not (is_admin or is_self):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    if req.new_password is not None:
        if not (is_self or is_admin):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        merged = db.merge(user)
        merged.password_hash = hash_password(req.new_password)
        user = merged

    admin_fields = (req.role is not None) or (req.is_active is not None)
    if admin_fields and not is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")

    if req.role is not None:
        if req.role not in _VALID_ROLES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid role. Must be one of: {', '.join(sorted(_VALID_ROLES))}",
            )
        if user.role == "admin" and req.role != "admin" and admin_count(db) <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot change role of the last admin",
            )
        if req.role == "admin" and user.role != "admin":
            max_admin_check(db)
        user.role = req.role

    if req.is_active is not None:
        if not req.is_active and user.role == "admin" and admin_count(db) <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot deactivate the last admin",
            )
        user.is_active = req.is_active

    db.commit()
    db.refresh(user)
    return _user_out(user)


@router.delete("/{id}")
def delete_user(
    id: int,
    db: Session = Depends(get_session),
    current_user: User = Depends(require_roles("admin")),
):
    user = db.query(User).filter(User.id == id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.role == "admin" and admin_count(db) <= 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete the last admin",
        )
    db.delete(user)
    db.commit()
    return {"detail": "User deleted"}


@router.get("/{id}/permissions")
def get_permissions(
    id: int,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if not (has_role(current_user, "admin") or current_user.id == id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    user = db.query(User).filter(User.id == id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    perms = db.query(UserAssetPermission).filter(UserAssetPermission.user_id == id).all()
    return [
        {"asset_id": p.asset_id, "permission": p.permission, "created_at": p.created_at}
        for p in perms
    ]


@router.put("/{id}/permissions")
def set_permissions(
    id: int,
    req: _PermissionsUpdate,
    db: Session = Depends(get_session),
    current_user: User = Depends(require_roles("admin")),
):
    user = db.query(User).filter(User.id == id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    for item in req.permissions:
        if item.permission not in _VALID_PERMS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid permission: {item.permission}",
            )
    db.query(UserAssetPermission).filter(UserAssetPermission.user_id == id).delete()
    for item in req.permissions:
        db.add(
            UserAssetPermission(
                user_id=id,
                asset_id=item.asset_id,
                permission=item.permission,
            )
        )
    db.commit()
    perms = db.query(UserAssetPermission).filter(UserAssetPermission.user_id == id).all()
    return [
        {"asset_id": p.asset_id, "permission": p.permission, "created_at": p.created_at}
        for p in perms
    ]
