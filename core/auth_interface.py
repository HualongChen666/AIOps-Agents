# -*- coding: utf-8 -*-
"""
auth_interface.py
-----------------
认证服务抽象接口

定义认证服务的标准接口，用于解耦具体实现与使用方。
所有 API 路由应依赖此接口而非 core.auth 的具体实现。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, Optional


class Permission(str, Enum):
    """权限枚举"""

    READ = "read"
    WRITE = "write"
    ADMIN = "admin"
    EXECUTE = "execute"


class AuthService(ABC):
    """认证服务抽象接口"""

    @abstractmethod
    async def get_current_user(self, token: str) -> Optional[Dict[str, Any]]:
        """
        根据令牌获取当前用户信息

        Args:
            token: 认证令牌

        Returns:
            用户信息字典，如果令牌无效返回 None
        """

    @abstractmethod
    async def verify_permission(self, user: Dict[str, Any], permission: Permission) -> bool:
        """
        验证用户是否具有指定权限

        Args:
            user: 用户信息字典
            permission: 需要验证的权限

        Returns:
            如果用户具有权限返回 True，否则返回 False
        """

    @abstractmethod
    async def verify_role(self, user: Dict[str, Any], role: str) -> bool:
        """
        验证用户是否具有指定角色

        Args:
            user: 用户信息字典
            role: 需要验证的角色

        Returns:
            如果用户具有角色返回 True，否则返回 False
        """

    @abstractmethod
    def create_access_token(self, data: Dict[str, Any], expires_delta: Optional[int] = None) -> str:
        """
        创建访问令牌

        Args:
            data: 令牌数据
            expires_delta: 过期时间（秒），可选

        Returns:
            访问令牌字符串
        """

    @abstractmethod
    async def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """
        验证用户凭据

        Args:
            username: 用户名
            password: 密码

        Returns:
            用户信息字典，如果验证失败返回 None
        """
