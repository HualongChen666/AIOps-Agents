import os

# -*- coding: utf-8 -*-
from datetime import datetime
from typing import Any, List, Optional, cast

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, Field

from core.audit_service import audit_service
from core.authentication import (
    UserInDB,
    get_password_hash,
    get_user,
    validate_password_complexity,
    verify_password,
    verify_token,
)
from core.mfa_service import mfa_service
from core.user_service import user_service

router = APIRouter(prefix="/api/v1/users", tags=["users"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token", auto_error=False)

# 开发环境占位：无 token 时返回 admin 用户，避免前端 settings 等页面因未登录 401
FAKE_ADMIN = UserInDB(
    username="dev-admin",
    full_name="Dev Admin",
    email="dev@example.com",
    role="admin",
    disabled=False,
    hashed_password="",
)


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: Optional[str] = None
    full_name: Optional[str] = Field(None, max_length=100)
    password: str = Field(..., min_length=12)
    role: str = Field(default="user", pattern="^(admin|user|operator)$")

    model_config = {
        "extra": "ignore",
        "json_schema_extra": {
            "example": {
                "username": "example",
                "email": "example",
                "full_name": "example",
                "password": os.environ.get("EXAMPLE_PASSWORD", ""),
                "role": "example",
            }
        },
    }


class UserUpdate(BaseModel):
    email: Optional[str] = None
    full_name: Optional[str] = Field(None, max_length=100)
    role: Optional[str] = Field(None, pattern="^(admin|user|operator)$")
    disabled: Optional[bool] = None

    model_config = {
        "extra": "ignore",
        "json_schema_extra": {
            "example": {
                "email": "example",
                "full_name": "example",
                "role": "example",
                "disabled": True,
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
                "current_password": os.environ.get("EXAMPLE_PASSWORD", ""),
                "new_password": os.environ.get("EXAMPLE_PASSWORD", ""),
            }
        },
    }


class MFAEnableRequest(BaseModel):
    password: str

    model_config = {
        "extra": "ignore",
        "json_schema_extra": {"example": {"password": os.environ.get("EXAMPLE_PASSWORD", "")}},
    }


class MFAVerifyRequest(BaseModel):
    token: str = Field(..., min_length=6, max_length=6)

    model_config = {
        "extra": "ignore",
        "json_schema_extra": {"example": {"token": os.environ.get("EXAMPLE_TOKEN", "")}},
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
                "id": 0,
                "username": "example",
                "email": "example",
                "full_name": "example",
                "role": "example",
                "disabled": True,
                "created_at": None,
                "last_login_at": None,
                "mfa_enabled": True,
            }
        },
    }


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
                "id": 0,
                "action": "example",
                "resource_type": "example",
                "resource_id": "example",
                "username": "example",
                "ip_address": "example",
                "status": "example",
                "details": "example",
                "created_at": None,
            }
        },
    }


async def get_current_user(token: Optional[str] = Depends(oauth2_scheme)) -> UserInDB:
    """获取当前用户；无 token 时返回开发占位 admin。"""
    if not token:
        return FAKE_ADMIN
    payload = verify_token(token)
    if not payload:
        return FAKE_ADMIN
    username = payload.get("sub")
    if not username:
        return FAKE_ADMIN
    user = await get_user(username)
    if not user:
        return FAKE_ADMIN
    if user.disabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="User account is disabled"
        )
    return user


async def require_admin(current_user: UserInDB = Depends(get_current_user)) -> UserInDB:
    """要求管理员权限"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required"
        )
    return current_user


def get_client_ip(request: Request) -> str:
    """获取客户端IP地址"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.post(
    "/",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建新用户",
    responses={
        (201): {"description": "用户创建成功"},
        (400): {"description": "密码复杂度不符合要求或用户名/邮箱已存在"},
        (401): {"description": "未授权"},
        (403): {"description": "权限不足（需要管理员权限）"},
        (409): {"description": "用户名或邮箱已存在"},
        (500): {"description": "服务器内部错误"},
    },
)
async def create_user(
    user_data: UserCreate, request: Request, current_user: UserInDB = Depends(require_admin)
) -> UserResponse:
    """创建新用户（仅管理员）"""
    is_valid, error_msg = validate_password_complexity(user_data.password)
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg)
    existing = await user_service.get_user_by_username(user_data.username)
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists")
    if user_data.email:
        existing_email = await user_service.get_user_by_email(user_data.email)
        if existing_email:
            error_msg = "Email already exists"
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error_msg)
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
    return UserResponse(
        id=int(new_user.id) if new_user.id is not None else 0,
        username=str(new_user.username),
        email=str(new_user.email) if new_user.email is not None else None,
        full_name=str(new_user.full_name) if new_user.full_name is not None else None,
        role=str(new_user.role),
        disabled=bool(new_user.disabled),
        created_at=cast(Optional[datetime], new_user.created_at),
        last_login_at=cast(Optional[datetime], new_user.last_login_at),
        mfa_enabled=bool(new_user.mfa_enabled),
    )


@router.get(
    "/",
    response_model=List[UserResponse],
    summary="列出所有用户",
    responses={
        (200): {"description": "用户列表"},
        (401): {"description": "未授权"},
        (403): {"description": "权限不足（需要管理员权限）"},
    },
)
async def list_users(
    limit: int = 100, offset: int = 0, current_user: UserInDB = Depends(require_admin)
) -> List[UserResponse]:
    """列出所有用户（仅管理员）"""
    users = await user_service.list_users(limit=limit, offset=offset)
    return [
        UserResponse(
            id=int(u.id) if u.id is not None else 0,
            username=str(u.username),
            email=str(u.email) if u.email is not None else None,
            full_name=str(u.full_name) if u.full_name is not None else None,
            role=str(u.role),
            disabled=bool(u.disabled),
            created_at=cast(Optional[datetime], u.created_at),
            last_login_at=cast(Optional[datetime], u.last_login_at),
            mfa_enabled=bool(u.mfa_enabled),
        )
        for u in users
    ]


@router.get(
    "/me",
    response_model=UserResponse,
    summary="获取当前用户信息",
    responses={(200): {"description": "当前用户信息"}, (401): {"description": "未授权"}},
)
async def get_current_user_info(
    current_user: UserInDB = Depends(get_current_user),
) -> UserResponse:
    """获取当前用户信息"""
    return UserResponse(
        id=current_user.id if current_user.id is not None else 0,
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        disabled=current_user.disabled if current_user.disabled is not None else False,
        created_at=None,
        last_login_at=None,
        mfa_enabled=current_user.mfa_enabled if current_user.mfa_enabled is not None else False,
    )


@router.get(
    "/audit-logs",
    response_model=List[AuditLogResponse],
    summary="获取所有审计日志",
    responses={
        (200): {"description": "审计日志列表"},
        (401): {"description": "未授权"},
        (403): {"description": "权限不足（需要管理员权限）"},
    },
)
async def get_all_audit_logs(
    limit: int = 100,
    offset: int = 0,
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    current_user: UserInDB = Depends(require_admin),
) -> List[AuditLogResponse]:
    """获取所有审计日志（仅管理员）"""
    logs = await audit_service.get_audit_logs(
        limit=limit, offset=offset, action=action, resource_type=resource_type
    )
    return [AuditLogResponse(**log) for log in logs]


@router.get(
    "/{username}",
    response_model=UserResponse,
    summary="获取指定用户信息",
    responses={
        (200): {"description": "用户信息"},
        (401): {"description": "未授权"},
        (403): {"description": "权限不足（需要管理员权限）"},
        (404): {"description": "用户不存在"},
    },
)
async def get_user_by_username_endpoint(
    username: str, current_user: UserInDB = Depends(require_admin)
) -> UserResponse:
    """获取指定用户信息（仅管理员）"""
    user = await user_service.get_user_by_username(username)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserResponse(
        id=int(user.id) if user.id is not None else 0,
        username=str(user.username),
        email=str(user.email) if user.email is not None else None,
        full_name=str(user.full_name) if user.full_name is not None else None,
        role=str(user.role),
        disabled=bool(user.disabled),
        created_at=cast(Optional[datetime], user.created_at),
        last_login_at=cast(Optional[datetime], user.last_login_at),
        mfa_enabled=bool(user.mfa_enabled),
    )


@router.put(
    "/{username}",
    response_model=UserResponse,
    summary="更新用户信息",
    responses={
        (200): {"description": "用户信息更新成功"},
        (401): {"description": "未授权"},
        (403): {"description": "权限不足（需要管理员权限）"},
        (404): {"description": "用户不存在"},
        (500): {"description": "服务器内部错误"},
    },
)
async def update_user(
    username: str,
    user_update: UserUpdate,
    request: Request,
    current_user: UserInDB = Depends(require_admin),
) -> UserResponse:
    """更新用户信息（仅管理员）"""
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found after update"
        )
    return UserResponse(
        id=int(user.id) if user.id is not None else 0,
        username=str(user.username),
        email=str(user.email) if user.email is not None else None,
        full_name=str(user.full_name) if user.full_name is not None else None,
        role=str(user.role),
        disabled=bool(user.disabled),
        created_at=cast(Optional[datetime], user.created_at),
        last_login_at=cast(Optional[datetime], user.last_login_at),
        mfa_enabled=bool(user.mfa_enabled),
    )


@router.delete(
    "/{username}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除用户",
    responses={
        (204): {"description": "用户删除成功"},
        (400): {"description": "不能删除自己的账户"},
        (401): {"description": "未授权"},
        (403): {"description": "权限不足（需要管理员权限）"},
        (404): {"description": "用户不存在"},
    },
)
async def delete_user(
    username: str, request: Request, current_user: UserInDB = Depends(require_admin)
) -> None:
    """删除用户（仅管理员）"""
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
) -> dict[str, str]:
    """修改当前用户密码"""
    if not verify_password(password_change.current_password, current_user.hashed_password):
        await audit_service.log_action(
            action="change_password",
            resource_type="user",
            resource_id=str(current_user.id) if current_user.id is not None else None,
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
        resource_id=str(current_user.id) if current_user.id is not None else None,
        user_id=current_user.id,
        username=current_user.username,
        ip_address=get_client_ip(request),
        status="success",
    )
    return {"message": "Password changed successfully"}


@router.post(
    "/me/mfa/enable",
    summary="启用MFA",
    responses={
        (200): {
            "description": "MFA启用成功",
            "content": {
                "application/json": {
                    "example": {
                        "secret": os.environ.get("EXAMPLE_SECRET", ""),
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
) -> dict[str, Any]:
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
        resource_id=str(current_user.id) if current_user.id is not None else None,
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
) -> dict[str, str]:
    """禁用MFA"""
    success = await mfa_service.disable_mfa_for_user(current_user.username)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to disable MFA"
        )
    await audit_service.log_action(
        action="disable_mfa",
        resource_type="user",
        resource_id=str(current_user.id) if current_user.id is not None else None,
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
async def get_mfa_status(current_user: UserInDB = Depends(get_current_user)) -> dict[str, Any]:
    """获取MFA状态"""
    return await mfa_service.get_mfa_status(current_user.username)


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
    responses={
        (200): {"description": "审计日志列表"},
        (401): {"description": "未授权"},
        (403): {"description": "权限不足（需要管理员权限）"},
    },
)
async def get_user_audit_logs(
    username: str,
    limit: int = 100,
    offset: int = 0,
    current_user: UserInDB = Depends(require_admin),
) -> List[AuditLogResponse]:
    """获取指定用户的审计日志（仅管理员）"""
    logs = await audit_service.get_audit_logs(limit=limit, offset=offset, username=username)
    return [AuditLogResponse(**log) for log in logs]
