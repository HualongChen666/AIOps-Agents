# -*- coding: utf-8 -*-
# core/middleware/__init__.py
# 中间件层初始化

from .auth_middleware import (
    Permission,
    check_permission,
    check_role,
    get_current_user,
    require_admin,
    require_permission,
    require_role,
)
from .rate_limit_middleware import (
    rate_limit_dependency,
    rate_limiter,
    rate_limit_middleware,
)

__all__ = [
    "Permission",
    "check_permission",
    "check_role",
    "get_current_user",
    "require_admin",
    "require_permission",
    "require_role",
    "rate_limit_dependency",
    "rate_limit_limiter",
    "rate_limit_middleware",
]
