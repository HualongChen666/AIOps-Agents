# -*- coding: utf-8 -*-
# core/middleware/auth_middleware.py
# JWT认证中间件和RBAC权限控制系统

from __future__ import annotations

import logging
from typing import Callable, List, Optional, Set

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from core.authentication import UserInDB, verify_token
from core.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)


# RBAC权限定义
class Permission:
    """权限定义"""
    
    # 用户管理权限
    USER_READ = "user:read"
    USER_WRITE = "user:write"
    USER_DELETE = "user:delete"
    
    # 告警管理权限
    ALERT_READ = "alert:read"
    ALERT_WRITE = "alert:write"
    ALERT_DELETE = "alert:delete"
    
    # 修复执行权限
    REPAIR_EXECUTE = "repair:execute"
    REPAIR_APPROVE = "repair:approve"
    
    # 系统管理权限
    SYSTEM_ADMIN = "system:admin"
    SYSTEM_CONFIG = "system:config"
    
    # 审计日志权限
    AUDIT_READ = "audit:read"


# 角色到权限的映射
ROLE_PERMISSIONS: dict[str, Set[str]] = {
    "admin": {
        Permission.USER_READ,
        Permission.USER_WRITE,
        Permission.USER_DELETE,
        Permission.ALERT_READ,
        Permission.ALERT_WRITE,
        Permission.ALERT_DELETE,
        Permission.REPAIR_EXECUTE,
        Permission.REPAIR_APPROVE,
        Permission.SYSTEM_ADMIN,
        Permission.SYSTEM_CONFIG,
        Permission.AUDIT_READ,
    },
    "operator": {
        Permission.ALERT_READ,
        Permission.ALERT_WRITE,
        Permission.REPAIR_EXECUTE,
        Permission.AUDIT_READ,
    },
    "user": {
        Permission.ALERT_READ,
        Permission.USER_READ,
    },
    "viewer": {
        Permission.ALERT_READ,
    },
}


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> UserInDB:
    """获取当前用户（JWT认证）
    
    Args:
        request: FastAPI请求对象
        credentials: HTTP授权凭证
        
    Returns:
        当前用户对象
        
    Raises:
        HTTPException: 认证失败时抛出401错误
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供认证凭证",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    payload = verify_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证凭证",
            headers={"WWW-Authenticate": "Bearer"},
        )

    username = payload.get("sub")
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="认证凭证中缺少用户信息",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 从数据库获取用户信息
    async with UserRepository() as user_repo:
        user = await user_repo.get_by_username(username)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user.disabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户账户已被禁用",
        )

    # 转换为UserInDB对象
    user_in_db = UserInDB(
        id=user.id,
        username=user.username,
        full_name=user.full_name,
        email=user.email,
        role=user.role,
        disabled=user.disabled,
        hashed_password=user.hashed_password,
        mfa_enabled=user.mfa_enabled,
        created_at=user.created_at,
        last_login_at=user.last_login_at,
    )

    # 将用户信息存入请求状态，供后续使用
    request.state.user = user_in_db
    
    return user_in_db


def require_permission(permission: str) -> Callable:
    """权限检查依赖工厂函数
    
    Args:
        permission: 需要的权限
        
    Returns:
        依赖函数
    """
    async def permission_checker(
        request: Request,
        current_user: UserInDB = Depends(get_current_user),
    ) -> UserInDB:
        """检查用户是否具有指定权限
        
        Args:
            request: FastAPI请求对象
            current_user: 当前用户
            
        Returns:
            当前用户对象
            
        Raises:
            HTTPException: 权限不足时抛出403错误
        """
        user_permissions = ROLE_PERMISSIONS.get(current_user.role, set())
        
        if permission not in user_permissions:
            logger.warning(
                f"权限不足 | user={current_user.username} | "
                f"role={current_user.role} | required_permission={permission}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"权限不足，需要权限: {permission}",
            )
        
        return current_user
    
    return permission_checker


def require_role(*roles: str) -> Callable:
    """角色检查依赖工厂函数
    
    Args:
        *roles: 允许的角色列表
        
    Returns:
        依赖函数
    """
    async def role_checker(
        request: Request,
        current_user: UserInDB = Depends(get_current_user),
    ) -> UserInDB:
        """检查用户是否具有指定角色
        
        Args:
            request: FastAPI请求对象
            current_user: 当前用户
            
        Returns:
            当前用户对象
            
        Raises:
            HTTPException: 角色不符时抛出403错误
        """
        if current_user.role not in roles:
            logger.warning(
                f"角色不符 | user={current_user.username} | "
                f"role={current_user.role} | required_roles={roles}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"角色不符，需要角色: {', '.join(roles)}",
            )
        
        return current_user
    
    return role_checker


async def require_admin(
    request: Request,
    current_user: UserInDB = Depends(get_current_user),
) -> UserInDB:
    """要求管理员权限（快捷函数）
    
    Args:
        request: FastAPI请求对象
        current_user: 当前用户
        
    Returns:
        当前用户对象
        
    Raises:
        HTTPException: 非管理员时抛出403错误
    """
    if current_user.role != "admin":
        logger.warning(f"非管理员尝试访问管理功能 | user={current_user.username}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限",
        )
    
    return current_user


def check_permission(user_role: str, required_permission: str) -> bool:
    """检查角色是否具有权限（同步版本，用于非依赖场景）
    
    Args:
        user_role: 用户角色
        required_permission: 需要的权限
        
    Returns:
        是否具有权限
    """
    user_permissions = ROLE_PERMISSIONS.get(user_role, set())
    return required_permission in user_permissions


def check_role(user_role: str, allowed_roles: List[str]) -> bool:
    """检查角色是否在允许列表中（同步版本，用于非依赖场景）
    
    Args:
        user_role: 用户角色
        allowed_roles: 允许的角色列表
        
    Returns:
        是否在允许列表中
    """
    return user_role in allowed_roles
