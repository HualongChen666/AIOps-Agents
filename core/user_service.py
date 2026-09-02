# -*- coding: utf-8 -*-
# core/user_service.py
# 🔧 用户服务层 - 使用Repository层实现数据库持久化

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from core.models import User
from core.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)


class UserService:
    """用户服务类 - 处理用户业务逻辑"""

    @staticmethod
    async def get_user_by_username(username: str) -> Optional[User]:
        """根据用户名获取用户"""
        try:
            async with UserRepository() as user_repo:
                return await user_repo.get_by_username(username)
        except Exception as e:
            logger.error(f"获取用户失败 | username={username}: {e}", exc_info=True)
            return None

    @staticmethod
    async def get_user_by_email(email: str) -> Optional[User]:
        """根据邮箱获取用户"""
        try:
            async with UserRepository() as user_repo:
                return await user_repo.get_by_email(email)
        except Exception as e:
            logger.error(f"获取用户失败 | email={email}: {e}", exc_info=True)
            return None

    @staticmethod
    async def get_user_by_id(user_id: int) -> Optional[User]:
        """根据ID获取用户"""
        try:
            async with UserRepository() as user_repo:
                return await user_repo.get_by_id(user_id)
        except Exception as e:
            logger.error(f"获取用户失败 | user_id={user_id}: {e}", exc_info=True)
            return None

    @staticmethod
    async def create_user(
        username: str,
        hashed_password: str,
        email: Optional[str] = None,
        full_name: Optional[str] = None,
        role: str = "user",
        disabled: bool = False,
    ) -> Optional[User]:
        """创建新用户"""
        try:
            async with UserRepository() as user_repo:
                return await user_repo.create(
                    username=username,
                    hashed_password=hashed_password,
                    email=email,
                    full_name=full_name,
                    role=role,
                    disabled=disabled,
                )
        except ValueError as e:
            logger.warning(f"创建用户失败（业务逻辑） | username={username}: {e}")
            return None
        except Exception as e:
            logger.error(f"创建用户失败 | username={username}: {e}", exc_info=True)
            return None

    @staticmethod
    async def update_user(
        username: str,
        email: Optional[str] = None,
        full_name: Optional[str] = None,
        role: Optional[str] = None,
        disabled: Optional[bool] = None,
    ) -> bool:
        """更新用户信息"""
        try:
            async with UserRepository() as user_repo:
                user = await user_repo.get_by_username(username)
                if not user:
                    logger.warning(f"用户不存在 | username={username}")
                    return False

                updated_user = await user_repo.update(
                    user_id=user.id,
                    email=email,
                    full_name=full_name,
                    role=role,
                    disabled=disabled,
                )
                return updated_user is not None
        except ValueError as e:
            logger.warning(f"更新用户失败（业务逻辑） | username={username}: {e}")
            return False
        except Exception as e:
            logger.error(f"更新用户失败 | username={username}: {e}", exc_info=True)
            return False

    @staticmethod
    async def update_password(username: str, hashed_password: str) -> bool:
        """更新用户密码"""
        try:
            async with UserRepository() as user_repo:
                user = await user_repo.get_by_username(username)
                if not user:
                    logger.warning(f"用户不存在 | username={username}")
                    return False

                return await user_repo.update_password(user.id, hashed_password)
        except Exception as e:
            logger.error(f"更新用户密码失败 | username={username}: {e}", exc_info=True)
            return False

    @staticmethod
    async def delete_user(username: str) -> bool:
        """删除用户"""
        try:
            async with UserRepository() as user_repo:
                user = await user_repo.get_by_username(username)
                if not user:
                    logger.warning(f"用户不存在 | username={username}")
                    return False

                return await user_repo.delete(user.id)
        except Exception as e:
            logger.error(f"删除用户失败 | username={username}: {e}", exc_info=True)
            return False

    @staticmethod
    async def list_users(limit: int = 100, offset: int = 0) -> List[User]:
        """列出所有用户"""
        try:
            async with UserRepository() as user_repo:
                return await user_repo.list_users(limit=limit, offset=offset)
        except Exception as e:
            logger.error(f"获取用户列表失败: {e}", exc_info=True)
            return []

    @staticmethod
    async def update_last_login(username: str) -> bool:
        """更新用户最后登录时间"""
        try:
            async with UserRepository() as user_repo:
                user = await user_repo.get_by_username(username)
                if not user:
                    return False

                return await user_repo.update_last_login(user.id)
        except Exception as e:
            logger.error(f"更新最后登录时间失败 | username={username}: {e}", exc_info=True)
            return False

    @staticmethod
    async def enable_mfa(username: str, secret: str, recovery_codes: List[str]) -> bool:
        """启用多因素认证"""
        try:
            async with UserRepository() as user_repo:
                user = await user_repo.get_by_username(username)
                if not user:
                    logger.warning(f"用户不存在 | username={username}")
                    return False

                return await user_repo.enable_mfa(user.id, secret, recovery_codes)
        except Exception as e:
            logger.error(f"启用MFA失败 | username={username}: {e}", exc_info=True)
            return False

    @staticmethod
    async def disable_mfa(username: str) -> bool:
        """禁用多因素认证"""
        try:
            async with UserRepository() as user_repo:
                user = await user_repo.get_by_username(username)
                if not user:
                    logger.warning(f"用户不存在 | username={username}")
                    return False

                return await user_repo.disable_mfa(user.id)
        except Exception as e:
            logger.error(f"禁用MFA失败 | username={username}: {e}", exc_info=True)
            return False

    @staticmethod
    def user_to_dict(user: User) -> Dict[str, Any]:
        """将User对象转换为字典（用于API响应）"""
        return {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "disabled": user.disabled,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "updated_at": user.updated_at.isoformat() if user.updated_at else None,
            "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
            "mfa_enabled": user.mfa_enabled,
        }


# 默认用户服务实例
user_service = UserService()
