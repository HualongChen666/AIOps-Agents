# -*- coding: utf-8 -*-
"""
RBAC权限检查中间件
提供基于角色的访问控制（RBAC）权限检查功能
"""

import logging
from typing import List, Optional

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.database import get_db
from core.models import User
from api.middleware.auth_middleware import get_current_active_user

logger = logging.getLogger(__name__)


# Role permissions mapping
ROLE_PERMISSIONS = {
    "admin": ["*"],  # Admin has all permissions
    "operator": [
        "alerts:read", "alerts:write", "repairs:read", "repairs:write",
        "approvals:read", "approvals:write", "metrics:read",
        "security:read", "security:write",
    ],
    "user": [
        "alerts:read", "metrics:read", "security:read",
    ],
}


def check_permission(user: User, required_permission: str) -> bool:
    """检查用户是否具有所需权限"""
    user_role = user.role
    
    # Admin has all permissions
    if user_role == "admin":
        return True
    
    # Get permissions for user's role
    role_perms = ROLE_PERMISSIONS.get(user_role, [])
    
    # Check if role has wildcard permission
    if "*" in role_perms:
        return True
    
    # Check if role has the specific permission
    return required_permission in role_perms


def require_permission(required_permission: str):
    """权限检查依赖项工厂函数"""
    
    async def permission_checker(
        current_user: User = Depends(get_current_active_user),
    ) -> User:
        """检查用户权限"""
        if not check_permission(current_user, required_permission):
            logger.warning(
                f"Permission denied: user={current_user.username}, "
                f"role={current_user.role}, required={required_permission}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"权限不足: 需要 {required_permission} 权限",
            )
        return current_user
    
    return permission_checker


def require_roles(allowed_roles: List[str]):
    """角色检查依赖项工厂函数"""
    
    async def role_checker(
        current_user: User = Depends(get_current_active_user),
    ) -> User:
        """检查用户角色"""
        if current_user.role not in allowed_roles:
            logger.warning(
                f"Role denied: user={current_user.username}, "
                f"role={current_user.role}, allowed={allowed_roles}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"权限不足: 需要以下角色之一 {', '.join(allowed_roles)}",
            )
        return current_user
    
    return role_checker


def require_admin():
    """要求管理员角色的便捷函数"""
    return require_roles(["admin"])


def require_operator_or_admin():
    """要求操作员或管理员角色的便捷函数"""
    return require_roles(["admin", "operator"])


class PermissionChecker:
    """权限检查器类，用于更复杂的权限检查逻辑"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def check_user_permission(self, user_id: int, permission: str) -> bool:
        """检查用户权限（通过用户ID）"""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return False
        return check_permission(user, permission)
    
    def get_user_permissions(self, user_id: int) -> List[str]:
        """获取用户的所有权限"""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return []
        
        role_perms = ROLE_PERMISSIONS.get(user.role, [])
        if "*" in role_perms:
            return ["*"]
        return role_perms.copy()
    
    def check_resource_access(
        self,
        user: User,
        resource_type: str,
        resource_id: Optional[str] = None,
        action: str = "read",
    ) -> bool:
        """
        检查用户对特定资源的访问权限
        
        Args:
            user: 用户对象
            resource_type: 资源类型（如: alert, repair, approval）
            resource_id: 资源ID（可选，用于更细粒度的控制）
            action: 操作类型（read, write, delete）
        
        Returns:
            是否有权限
        """
        # Admin has all access
        if user.role == "admin":
            return True
        
        # Build permission string
        permission = f"{resource_type}:{action}"
        
        # Check permission
        return check_permission(user, permission)


def get_permission_checker(db: Session = Depends(get_db)) -> PermissionChecker:
    """获取权限检查器实例"""
    return PermissionChecker(db)
