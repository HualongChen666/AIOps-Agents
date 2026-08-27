# -*- coding: utf-8 -*-
"""
RBAC (Role-Based Access Control)
基于角色的访问控制

实现企业级的权限管理系统
"""

from enum import Enum
from typing import List, Dict, Set, Optional
from functools import wraps
from fastapi import HTTPException, Depends


class Permission(str, Enum):
    """权限枚举"""
    # 基础权限
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    
    # 业务影响分析权限
    BUSINESS_IMPACT_READ = "business_impact:read"
    BUSINESS_IMPACT_WRITE = "business_impact:write"
    BUSINESS_IMPACT_DELETE = "business_impact:delete"
    
    # 混沌工程权限
    CHAOS_READ = "chaos:read"
    CHAOS_WRITE = "chaos:write"
    CHAOS_DELETE = "chaos:delete"
    CHAOS_EXECUTE = "chaos:execute"
    
    # AI功能权限
    AI_READ = "ai:read"
    AI_WRITE = "ai:write"
    AI_TRAIN = "ai:train"
    AI_DEPLOY = "ai:deploy"
    
    # 插件市场权限
    PLUGIN_READ = "plugin:read"
    PLUGIN_UPLOAD = "plugin:upload"
    PLUGIN_INSTALL = "plugin:install"
    
    # 管理权限
    USER_MANAGE = "user:manage"
    SYSTEM_CONFIG = "system:config"
    AUDIT_LOG = "audit:log"


class Role(str, Enum):
    """角色枚举"""
    ADMIN = "admin"
    OPERATOR = "operator"
    DEVELOPER = "developer"
    VIEWER = "viewer"
    GUEST = "guest"


# 角色权限映射
ROLE_PERMISSIONS: Dict[Role, Set[Permission]] = {
    Role.ADMIN: {
        # 管理员拥有所有权限
        Permission.READ, Permission.WRITE, Permission.DELETE,
        Permission.BUSINESS_IMPACT_READ, Permission.BUSINESS_IMPACT_WRITE, Permission.BUSINESS_IMPACT_DELETE,
        Permission.CHAOS_READ, Permission.CHAOS_WRITE, Permission.CHAOS_DELETE, Permission.CHAOS_EXECUTE,
        Permission.AI_READ, Permission.AI_WRITE, Permission.AI_TRAIN, Permission.AI_DEPLOY,
        Permission.PLUGIN_READ, Permission.PLUGIN_UPLOAD, Permission.PLUGIN_INSTALL,
        Permission.USER_MANAGE, Permission.SYSTEM_CONFIG, Permission.AUDIT_LOG,
    },
    Role.OPERATOR: {
        # 运维人员权限
        Permission.READ, Permission.WRITE,
        Permission.BUSINESS_IMPACT_READ, Permission.BUSINESS_IMPACT_WRITE,
        Permission.CHAOS_READ, Permission.CHAOS_WRITE, Permission.CHAOS_EXECUTE,
        Permission.AI_READ, Permission.AI_WRITE,
        Permission.PLUGIN_READ, Permission.PLUGIN_INSTALL,
    },
    Role.DEVELOPER: {
        # 开发人员权限
        Permission.READ, Permission.WRITE,
        Permission.BUSINESS_IMPACT_READ, Permission.BUSINESS_IMPACT_WRITE,
        Permission.CHAOS_READ, Permission.CHAOS_WRITE,
        Permission.AI_READ, Permission.AI_WRITE, Permission.AI_TRAIN,
        Permission.PLUGIN_READ, Permission.PLUGIN_UPLOAD,
    },
    Role.VIEWER: {
        # 只读权限
        Permission.READ,
        Permission.BUSINESS_IMPACT_READ,
        Permission.CHAOS_READ,
        Permission.AI_READ,
        Permission.PLUGIN_READ,
    },
    Role.GUEST: {
        # 访客权限
        Permission.READ,
        Permission.BUSINESS_IMPACT_READ,
    },
}


class RBACManager:
    """RBAC管理器"""
    
    @staticmethod
    def has_permission(user_role: Role, required_permission: Permission) -> bool:
        """检查用户是否具有指定权限"""
        user_permissions = ROLE_PERMISSIONS.get(user_role, set())
        return required_permission in user_permissions
    
    @staticmethod
    def has_any_permission(user_role: Role, required_permissions: List[Permission]) -> bool:
        """检查用户是否具有任一指定权限"""
        user_permissions = ROLE_PERMISSIONS.get(user_role, set())
        return any(perm in user_permissions for perm in required_permissions)
    
    @staticmethod
    def has_all_permissions(user_role: Role, required_permissions: List[Permission]) -> bool:
        """检查用户是否具有所有指定权限"""
        user_permissions = ROLE_PERMISSIONS.get(user_role, set())
        return all(perm in user_permissions for perm in required_permissions)
    
    @staticmethod
    def get_user_permissions(user_role: Role) -> Set[Permission]:
        """获取用户的所有权限"""
        return ROLE_PERMISSIONS.get(user_role, set()).copy()


def require_permission(required_permission: Permission):
    """权限检查装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 这里应该从请求上下文中获取用户角色
            # 简化实现，实际应该从JWT token或session中获取
            user_role = Role.VIEWER  # 默认角色
            
            if not RBACManager.has_permission(user_role, required_permission):
                raise HTTPException(
                    status_code=403,
                    detail=f"Permission denied: {required_permission.value} required"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_role(required_role: Role):
    """角色检查装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 这里应该从请求上下文中获取用户角色
            user_role = Role.VIEWER  # 默认角色
            
            if user_role != required_role and user_role != Role.ADMIN:
                raise HTTPException(
                    status_code=403,
                    detail=f"Role denied: {required_role.value} required"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_any_role(*required_roles: Role):
    """多角色检查装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 这里应该从请求上下文中获取用户角色
            user_role = Role.VIEWER  # 默认角色
            
            if user_role not in required_roles and user_role != Role.ADMIN:
                raise HTTPException(
                    status_code=403,
                    detail=f"Role denied: one of {[role.value for role in required_roles]} required"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator