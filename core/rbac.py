# -*- coding: utf-8 -*-
"""
RBAC (Role-Based Access Control)
基于角色的访问控制

实现企业级的权限管理系统
"""

from enum import Enum
from typing import Any, List, Dict, Set, Optional
from functools import wraps
from fastapi import HTTPException, Depends

try:
    from core.authentication import get_current_active_user
except ImportError:
    # Fallback if authentication module not available
    async def get_current_active_user():
        return None


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


_ROLE_ALIASES: Dict[str, "Role"] = {
    "admin": Role.ADMIN,
    "administrator": Role.ADMIN,
    "operator": Role.OPERATOR,
    "ops": Role.OPERATOR,
    "sre": Role.OPERATOR,
    "developer": Role.DEVELOPER,
    "dev": Role.DEVELOPER,
    "viewer": Role.VIEWER,
    "readonly": Role.VIEWER,
    "read-only": Role.VIEWER,
    "guest": Role.GUEST,
    "anonymous": Role.GUEST,
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


def _role_from_value(raw: Any) -> Role:
    """将原始角色值（字符串/枚举/列表）归一化为 :class:`Role`。"""
    if raw is None:
        return Role.GUEST
    if isinstance(raw, Role):
        return raw
    if isinstance(raw, (list, tuple, set)):
        for item in raw:
            candidate = _role_from_value(item)
            if candidate != Role.GUEST:
                return candidate
        return Role.GUEST
    return _ROLE_ALIASES.get(str(raw).strip().lower(), Role.VIEWER)


def _resolve_current_user(args: tuple, kwargs: Dict[str, Any]) -> Any:
    """从 FastAPI 注入的实参中解析当前用户。

    被装饰的端点通常会声明 ``current_user = Depends(get_current_active_user)``，
    FastAPI 会以关键字实参传入，因此优先从此处取；其次扫描位置实参与其余
    关键字实参，兼容 ``request.state.user`` 风格的调用。
    """
    for key in ("current_user", "user", "_current_user"):
        candidate = kwargs.get(key)
        if candidate is not None:
            return candidate

    for candidate in (*args, *kwargs.values()):
        if candidate is None:
            continue
        if hasattr(candidate, "role") or hasattr(candidate, "roles"):
            return candidate
        if isinstance(candidate, dict) and ("role" in candidate or "roles" in candidate):
            return candidate
        # Request-like object carrying an authenticated user on .state
        state = getattr(candidate, "state", None)
        if state is not None:
            state_user = getattr(state, "user", None)
            if state_user:
                return state_user
    return None


def _current_role(args: tuple, kwargs: Dict[str, Any]) -> Role:
    """解析当前请求的用户角色（真实的认证上下文，而非硬编码 VIEWER）。"""
    user = _resolve_current_user(args, kwargs)
    if isinstance(user, dict):
        return _role_from_value(user.get("role", user.get("roles")))
    return _role_from_value(getattr(user, "role", None) if user is not None else None)


def require_permission(required_permission: Permission):
    """权限检查装饰器

    从真实认证上下文解析当前用户角色后校验权限；不再恒按 ``Role.VIEWER`` 判定。
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            user_role = _current_role(args, kwargs)

            if not RBACManager.has_permission(user_role, required_permission):
                raise HTTPException(
                    status_code=403,
                    detail=(
                        f"Permission denied: {required_permission.value} required "
                        f"(role={user_role.value})"
                    ),
                )

            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_role(required_role: Role):
    """角色检查装饰器（基于真实认证上下文）"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            user_role = _current_role(args, kwargs)

            if user_role != required_role and user_role != Role.ADMIN:
                raise HTTPException(
                    status_code=403,
                    detail=f"Role denied: {required_role.value} required (role={user_role.value})",
                )

            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_any_role(*required_roles: Role):
    """多角色检查装饰器（基于真实认证上下文）"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            user_role = _current_role(args, kwargs)

            if user_role not in required_roles and user_role != Role.ADMIN:
                raise HTTPException(
                    status_code=403,
                    detail=(
                        "Role denied: one of "
                        f"{[role.value for role in required_roles]} required (role={user_role.value})"
                    ),
                )

            return await func(*args, **kwargs)
        return wrapper
    return decorator


def role_required(required_role: str):
    """FastAPI依赖函数：检查用户角色"""
    async def check_role(user=Depends(get_current_active_user)):
        if not user or user.role != required_role:
            raise HTTPException(
                status_code=403,
                detail=f"Role denied: {required_role} required"
            )
        return user
    return check_role