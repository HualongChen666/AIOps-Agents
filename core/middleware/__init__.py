# -*- coding: utf-8 -*-
"""Package initializer for ``core.middleware``.

Contents (from package tree, nothing is re-exported here yet):
- submodules: auth_middleware, rate_limit_middleware"""

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
    "rate_limiter",
    "rate_limit_middleware",
]
