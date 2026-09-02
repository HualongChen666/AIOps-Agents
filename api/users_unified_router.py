# -*- coding: utf-8 -*-
# api/users_unified_router.py
# 统一的用户路由器 - 整合所有用户相关功能

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, cast

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from core.audit_service import audit_service
from core.authentication import (
    UserInDB,
    get_password_hash,
    validate_password_complexity,
    verify_password,
)
from core.middleware import (
    Permission,
    get_current_user,
    require_admin,
    require_permission,
)
from core.mfa_service import mfa_service
from core.user_service import user_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/users", tags=["users"])


# ============ Pydantic Models ============


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: Optional[str] = Field(None, max_length=255)
    full_name: Optional[str] = Field(None, max_length=100)
    password: str = Field(..., min_length=12)
    role: str = Field(default="user", pattern="^(admin|user|operator|viewer)$")

    model_config = {
        "extra": "ignore",
        "json_schema_extra": {
            "example": {
                "username": "example",
                "email": "user@example.com",
                "full_name": "Example User",
                "password": "SecurePassword123!",
                "role": "user",
            }
        },
    }


class UserUpdate(BaseModel):
    email: Optional[str] = Field(None, max_length=255)
    full_name: Optional[str] = Field(None, max_length=100)
    role: Optional[str] = Field(None, pattern="^(admin|user|operator|viewer)$")
    disabled: Optional[bool] = None

    model_config = {
        "extra": "ignore",
        "json_schema_extra": {
            "example": {
                "email": "newemail@example.com",
                "full_name": "New Name",
                "role": "operator",
                "disabled": False,
            }
        },
    }


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=12)

    model_config = {
        "extra": "ignore",
        "json_schema_extra": {
            "example": {
                "current_password": "OldPassword123!",
                "new_password": "NewPassword123!",
            }
        },
    }


class MFAEnableRequest(BaseModel):
    password: str

    model_config = {
        "extra": "ignore",
        "json_schema_extra": {"example": {"password": "CurrentPassword123!"}},
    }


class MFAVerifyRequest(BaseModel):
    token: str = Field(..., min_length=6, max_length=6)

    model_config = {
        "extra": "ignore",
        "json_schema_extra": {"example": {"token": "123456"}},
    }


class UserResponse(BaseModel):
    id: int
    username: str
    email: Optional[str]
    full_name: Optional[str]
    role: str
    disabled: bool
    created_at: Optional[datetime]
    last_login_at: Optional[datetime]
    mfa_enabled: bool

    model_config = {
        "extra": "ignore",
        "json_schema_extra": {
            "example": {
                "id": 1,
                "username": "example",
                "email": "user@example.com",
                "full_name": "Example User",
                "role": "user",
                "disabled": False,
                "created_at": "2024-01-01T00:00:00",
                "last_login_at": "2024-01-01T12:00:00",
                "mfa_enabled": False,
            }
        },
    }


class UserProfileUpdate(BaseModel):
    full_name: Optional[str] = Field(None, max_length=100)
    email: Optional[str] = Field(None, max_length=255)

    model_config = {
        "extra": "ignore",
        "json_schema_extra": {
            "example": {
                "full_name": "Updated Name",
                "email": "updated@example.com",
            }
        },
    }


class UserPreferences(BaseModel):
    theme: str = "light"
    language: str = "zh-CN"
    timezone: str = "Asia/Shanghai"
    notifications_enabled: bool = True

    model_config = {"extra": "ignore"}


class AuditLogResponse(BaseModel):
    id: int
    action: str
    resource_type: str
    resource_id: Optional[str]
    username: Optional[str]
    ip_address: Optional[str]
    status: str
    details: Optional[str]
    created_at: Optional[datetime]

    model_config = {
        "extra": "ignore",
        "json_schema_extra": {
            "example": {
                "id": 1,
                "action": "create_user",
                "resource_type": "user",
                "resource_id": "1",
                "username": "admin",
                "ip_address": "127.0.0.1",
                "status": "success",
                "details": "Created user: example",
                "created_at": "2024-01-01T00:00:00",
            }
        },
    }


# ============ Helper Functions ============


def get_client_ip(request: Request) -> str:
    """获取客户端IP地址"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def user_to_response(user: UserInDB) -> UserResponse:
    """将UserInDB转换为UserResponse"""
    return UserResponse(
        id=user.id if user.id else 0,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        disabled=user.disabled if user.disabled is not None else False,
        created_at=user.created_at,
        last_login_at=user.last_login_at,
        mfa_enabled=user.mfa_enabled if user.mfa_enabled is not None else False,
    )


# ============ User Management Endpoints ============


@router.post(
    "/",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建新用户",
    dependencies=[Depends(require_permission(Permission.USER_WRITE))],
    responses={
        (201): {"description": "用户创建成功"},
        (400): {"description": "密码复杂度不符合要求或用户名/邮箱已存在"},
        (401): {"description": "未授权"},
        (403): {"description": "权限不足"},
        (409): {"description": "用户名或邮箱已存在"},
        (500): {"description": "服务器内部错误"},
    },
)
async def create_user(
    user_data: UserCreate,
    request: Request,
    current_user: UserInDB = Depends(get_current_user),
) -> UserResponse:
    """创建新用户（需要用户写入权限）"""
    is_valid, error_msg = validate_password_complexity(user_data.password)
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg)

    existing = await user_service.get_user_by_username(user_data.username)
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists")

    if user_data.email:
        existing_email = await user_service.get_user_by_email(user_data.email)
        if existing_email:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists")

    hashed_password = get_password_hash(user_data.password)
    new_user = await user_service.create_user(
        username=user_data.username,
        hashed_password=hashed_password,
        email=user_data.email,
        full_name=user_data.full_name,
        role=user_data.role,
    )

    if not new_user:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create user"
        )

    await audit_service.log_action(
        action="create_user",
        resource_type="user",
        resource_id=str(new_user.id),
        user_id=current_user.id,
        username=current_user.username,
        ip_address=get_client_ip(request),
        status="success",
        details=f"Created user: {user_data.username}",
    )

    return user_to_response(
        UserInDB(
            id=new_user.id,
            username=new_user.username,
            email=new_user.email,
            full_name=new_user.full_name,
            role=new_user.role,
            disabled=new_user.disabled,
            hashed_password="",
            mfa_enabled=new_user.mfa_enabled,
            created_at=new_user.created_at,
            last_login_at=new_user.last_login_at,
        )
    )


@router.get(
    "/",
    response_model=List[UserResponse],
    summary="列出所有用户",
    dependencies=[Depends(require_permission(Permission.USER_READ))],
    responses={
        (200): {"description": "用户列表"},
        (401): {"description": "未授权"},
        (403): {"description": "权限不足"},
    },
)
async def list_users(
    limit: int = 100,
    offset: int = 0,
    current_user: UserInDB = Depends(get_current_user),
) -> List[UserResponse]:
    """列出所有用户（需要用户读取权限）"""
    users = await user_service.list_users(limit=limit, offset=offset)
    return [
        user_to_response(
            UserInDB(
                id=u.id,
                username=u.username,
                email=u.email,
                full_name=u.full_name,
                role=u.role,
                disabled=u.disabled,
                hashed_password="",
                mfa_enabled=u.mfa_enabled,
                created_at=u.created_at,
                last_login_at=u.last_login_at,
            )
        )
        for u in users
    ]


@router.get(
    "/me",
    response_model=UserResponse,
    summary="获取当前用户信息",
    responses={(200): {"description": "当前用户信息"}, (401): {"description": "未授权"}},
)
async def get_current_user_info(current_user: UserInDB = Depends(get_current_user)) -> UserResponse:
    """获取当前用户信息"""
    return user_to_response(current_user)


@router.patch(
    "/me",
    response_model=UserResponse,
    summary="更新当前用户资料",
    responses={
        (200): {"description": "用户资料更新成功"},
        (401): {"description": "未授权"},
        (400): {"description": "无效的请求数据"},
    },
)
async def update_my_profile(
    profile_update: UserProfileUpdate,
    request: Request,
    current_user: UserInDB = Depends(get_current_user),
) -> UserResponse:
    """更新当前用户的资料"""
    success = await user_service.update_user(
        username=current_user.username,
        email=profile_update.email,
        full_name=profile_update.full_name,
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to update profile"
        )

    user = await user_service.get_user_by_username(current_user.username)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    await audit_service.log_action(
        action="update_profile",
        resource_type="user",
        resource_id=str(user.id),
        user_id=current_user.id,
        username=current_user.username,
        ip_address=get_client_ip(request),
        status="success",
        details="Updated user profile",
    )

    return user_to_response(
        UserInDB(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            disabled=user.disabled,
            hashed_password="",
            mfa_enabled=user.mfa_enabled,
            created_at=user.created_at,
            last_login_at=user.last_login_at,
        )
    )


@router.get(
    "/{username}",
    response_model=UserResponse,
    summary="获取指定用户信息",
    dependencies=[Depends(require_permission(Permission.USER_READ))],
    responses={
        (200): {"description": "用户信息"},
        (401): {"description": "未授权"},
        (403): {"description": "权限不足"},
        (404): {"description": "用户不存在"},
    },
)
async def get_user_by_username_endpoint(
    username: str, current_user: UserInDB = Depends(get_current_user)
) -> UserResponse:
    """获取指定用户信息（需要用户读取权限）"""
    user = await user_service.get_user_by_username(username)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return user_to_response(
        UserInDB(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            disabled=user.disabled,
            hashed_password="",
            mfa_enabled=user.mfa_enabled,
            created_at=user.created_at,
            last_login_at=user.last_login_at,
        )
    )


@router.put(
    "/{username}",
    response_model=UserResponse,
    summary="更新用户信息",
    dependencies=[Depends(require_permission(Permission.USER_WRITE))],
    responses={
        (200): {"description": "用户信息更新成功"},
        (401): {"description": "未授权"},
        (403): {"description": "权限不足"},
        (404): {"description": "用户不存在"},
        (500): {"description": "服务器内部错误"},
    },
)
async def update_user(
    username: str,
    user_update: UserUpdate,
    request: Request,
    current_user: UserInDB = Depends(get_current_user),
) -> UserResponse:
    """更新用户信息（需要用户写入权限）"""
    success = await user_service.update_user(
        username=username,
        email=user_update.email,
        full_name=user_update.full_name,
        role=user_update.role,
        disabled=user_update.disabled,
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found or update failed"
        )

    await audit_service.log_action(
        action="update_user",
        resource_type="user",
        resource_id=username,
        user_id=current_user.id,
        username=current_user.username,
        ip_address=get_client_ip(request),
        status="success",
        details=f"Updated user: {username}",
    )

    user = await user_service.get_user_by_username(username)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found after update")

    return user_to_response(
        UserInDB(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            disabled=user.disabled,
            hashed_password="",
            mfa_enabled=user.mfa_enabled,
            created_at=user.created_at,
            last_login_at=user.last_login_at,
        )
    )


@router.delete(
    "/{username}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除用户",
    dependencies=[Depends(require_permission(Permission.USER_DELETE))],
    responses={
        (204): {"description": "用户删除成功"},
        (400): {"description": "不能删除自己的账户"},
        (401): {"description": "未授权"},
        (403): {"description": "权限不足"},
        (404): {"description": "用户不存在"},
    },
)
async def delete_user(
    username: str, request: Request, current_user: UserInDB = Depends(get_current_user)
) -> None:
    """删除用户（需要用户删除权限）"""
    if username == current_user.username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete your own account"
        )

    success = await user_service.delete_user(username)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    await audit_service.log_action(
        action="delete_user",
        resource_type="user",
        resource_id=username,
        user_id=current_user.id,
        username=current_user.username,
        ip_address=get_client_ip(request),
        status="success",
        details=f"Deleted user: {username}",
    )


# ============ Password Management Endpoints ============


@router.post(
    "/me/change-password",
    summary="修改当前用户密码",
    responses={
        (200): {
            "description": "密码修改成功",
            "content": {
                "application/json": {"example": {"message": "Password changed successfully"}}
            },
        },
        (400): {"description": "当前密码错误或新密码复杂度不符合要求"},
        (401): {"description": "未授权"},
        (500): {"description": "服务器内部错误"},
    },
)
async def change_password(
    password_change: PasswordChange,
    request: Request,
    current_user: UserInDB = Depends(get_current_user),
) -> Dict[str, str]:
    """修改当前用户密码"""
    if not verify_password(password_change.current_password, current_user.hashed_password):
        await audit_service.log_action(
            action="change_password",
            resource_type="user",
            resource_id=str(current_user.id) if current_user.id else None,
            user_id=current_user.id,
            username=current_user.username,
            ip_address=get_client_ip(request),
            status="failure",
            details="Current password incorrect",
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect"
        )

    is_valid, error_msg = validate_password_complexity(password_change.new_password)
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg)

    new_hashed_password = get_password_hash(password_change.new_password)
    success = await user_service.update_password(current_user.username, new_hashed_password)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update password"
        )

    await audit_service.log_action(
        action="change_password",
        resource_type="user",
        resource_id=str(current_user.id) if current_user.id else None,
        user_id=current_user.id,
        username=current_user.username,
        ip_address=get_client_ip(request),
        status="success",
    )

    return {"message": "Password changed successfully"}


# ============ MFA Endpoints ============


@router.post(
    "/me/mfa/enable",
    summary="启用MFA",
    responses={
        (200): {
            "description": "MFA启用成功",
            "content": {
                "application/json": {
                    "example": {
                        "secret": "JBSWY3DPEHPK3PXP",
                        "qr_code": "data:image/png;base64,...",
                        "recovery_codes": ["code1", "code2", "code3"],
                        "message": "MFA enabled. Please save your recovery codes securely.",
                    }
                }
            },
        },
        (400): {"description": "当前密码错误或MFA已启用"},
        (401): {"description": "未授权"},
        (500): {"description": "服务器内部错误"},
    },
)
async def enable_mfa(
    mfa_request: MFAEnableRequest,
    request: Request,
    current_user: UserInDB = Depends(get_current_user),
) -> Dict[str, Any]:
    """启用MFA（需要验证当前密码）"""
    if not verify_password(mfa_request.password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect"
        )

    if await mfa_service.is_mfa_enabled(current_user.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="MFA is already enabled"
        )

    secret, qr_code, recovery_codes = await mfa_service.enable_mfa_for_user(current_user.username)

    await audit_service.log_action(
        action="enable_mfa",
        resource_type="user",
        resource_id=str(current_user.id) if current_user.id else None,
        user_id=current_user.id,
        username=current_user.username,
        ip_address=get_client_ip(request),
        status="success",
    )

    return {
        "secret": secret,
        "qr_code": qr_code,
        "recovery_codes": recovery_codes,
        "message": "MFA enabled. Please save your recovery codes securely.",
    }


@router.post(
    "/me/mfa/disable",
    summary="禁用MFA",
    responses={
        (200): {
            "description": "MFA禁用成功",
            "content": {"application/json": {"example": {"message": "MFA disabled successfully"}}},
        },
        (401): {"description": "未授权"},
        (500): {"description": "服务器内部错误"},
    },
)
async def disable_mfa(
    request: Request, current_user: UserInDB = Depends(get_current_user)
) -> Dict[str, str]:
    """禁用MFA"""
    success = await mfa_service.disable_mfa_for_user(current_user.username)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to disable MFA"
        )

    await audit_service.log_action(
        action="disable_mfa",
        resource_type="user",
        resource_id=str(current_user.id) if current_user.id else None,
        user_id=current_user.id,
        username=current_user.username,
        ip_address=get_client_ip(request),
        status="success",
    )

    return {"message": "MFA disabled successfully"}


@router.get(
    "/me/mfa/status",
    summary="获取MFA状态",
    responses={
        (200): {
            "description": "MFA状态",
            "content": {"application/json": {"example": {"enabled": True, "method": "totp"}}},
        },
        (401): {"description": "未授权"},
    },
)
async def get_mfa_status(current_user: UserInDB = Depends(get_current_user)) -> Dict[str, Any]:
    """获取MFA状态"""
    return await mfa_service.get_mfa_status(current_user.username)


# ============ Audit Log Endpoints ============


@router.get(
    "/audit-logs",
    response_model=List[AuditLogResponse],
    summary="获取所有审计日志",
    dependencies=[Depends(require_permission(Permission.AUDIT_READ))],
    responses={
        (200): {"description": "审计日志列表"},
        (401): {"description": "未授权"},
        (403): {"description": "权限不足"},
    },
)
async def get_all_audit_logs(
    limit: int = 100,
    offset: int = 0,
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    current_user: UserInDB = Depends(get_current_user),
) -> List[AuditLogResponse]:
    """获取所有审计日志（需要审计读取权限）"""
    logs = await audit_service.get_audit_logs(
        limit=limit, offset=offset, action=action, resource_type=resource_type
    )
    return [AuditLogResponse(**log) for log in logs]


@router.get(
    "/me/audit-logs",
    response_model=List[AuditLogResponse],
    summary="获取当前用户的审计日志",
    responses={(200): {"description": "审计日志列表"}, (401): {"description": "未授权"}},
)
async def get_my_audit_logs(
    limit: int = 100, offset: int = 0, current_user: UserInDB = Depends(get_current_user)
) -> List[AuditLogResponse]:
    """获取当前用户的审计日志"""
    logs = await audit_service.get_audit_logs(
        limit=limit, offset=offset, username=current_user.username
    )
    return [AuditLogResponse(**log) for log in logs]


@router.get(
    "/{username}/audit-logs",
    response_model=List[AuditLogResponse],
    summary="获取指定用户的审计日志",
    dependencies=[Depends(require_permission(Permission.AUDIT_READ))],
    responses={
        (200): {"description": "审计日志列表"},
        (401): {"description": "未授权"},
        (403): {"description": "权限不足"},
    },
)
async def get_user_audit_logs(
    username: str,
    limit: int = 100,
    offset: int = 0,
    current_user: UserInDB = Depends(get_current_user),
) -> List[AuditLogResponse]:
    """获取指定用户的审计日志（需要审计读取权限）"""
    logs = await audit_service.get_audit_logs(limit=limit, offset=offset, username=username)
    return [AuditLogResponse(**log) for log in logs]
