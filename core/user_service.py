# -*- coding: utf-8 -*-
# core/user_service.py
# 🔧 P0-18: 真实的用户数据库服务
# 替换authentication.py中的假内存数据库为真实的PostgreSQL数据库操作

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, cast

from sqlalchemy import delete, select, update

from core.db_engine import AsyncSessionLocal
from core.models import User

logger = logging.getLogger(__name__)


class UserService:
    """用户服务类 - 处理用户数据库操作"""

    @staticmethod
    async def get_user_by_username(username: str) -> Optional[User]:
        """根据用户名获取用户"""
        try:
            async with AsyncSessionLocal() as session:
                stmt = select(User).where(User.username == username)
                result = await session.execute(stmt)
                return cast(Optional[User], result.scalar_one_or_none())
        except Exception as e:
            logger.error(f"获取用户失败 | username={username}: {e}", exc_info=True)
            return None

    @staticmethod
    async def get_user_by_email(email: str) -> Optional[User]:
        """根据邮箱获取用户"""
        try:
            async with AsyncSessionLocal() as session:
                stmt = select(User).where(User.email == email)
                result = await session.execute(stmt)
                return cast(Optional[User], result.scalar_one_or_none())
        except Exception as e:
            logger.error(f"获取用户失败 | email={email}: {e}", exc_info=True)
            return None

    @staticmethod
    async def get_user_by_id(user_id: int) -> Optional[User]:
        """根据ID获取用户"""
        try:
            async with AsyncSessionLocal() as session:
                stmt = select(User).where(User.id == user_id)
                result = await session.execute(stmt)
                return cast(Optional[User], result.scalar_one_or_none())
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
            async with AsyncSessionLocal() as session:
                # 检查用户名是否已存在
                existing = await UserService.get_user_by_username(username)
                if existing:
                    logger.warning(f"用户名已存在 | username={username}")
                    return None

                # 检查邮箱是否已存在
                if email:
                    existing_email = await UserService.get_user_by_email(email)
                    if existing_email:
                        logger.warning(f"邮箱已存在 | email={email}")
                        return None

                new_user = User(
                    username=username,
                    hashed_password=hashed_password,
                    email=email,
                    full_name=full_name,
                    role=role,
                    disabled=disabled,
                    mfa_enabled=False,
                )
                session.add(new_user)
                await session.commit()
                await session.refresh(new_user)
                logger.info(f"✅ 用户创建成功 | username={username} | id={new_user.id}")
                return new_user
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
            async with AsyncSessionLocal() as session:
                stmt = select(User).where(User.username == username)
                result = await session.execute(stmt)
                user = result.scalar_one_or_none()

                if not user:
                    logger.warning(f"用户不存在 | username={username}")
                    return False

                update_data: Dict[str, Any] = {}
                if email is not None:
                    update_data["email"] = email
                if full_name is not None:
                    update_data["full_name"] = full_name
                if role is not None:
                    update_data["role"] = role
                if disabled is not None:
                    update_data["disabled"] = disabled

                if update_data:
                    update_stmt = (
                        update(User).where(User.username == username).values(**update_data)
                    )
                    await session.execute(update_stmt)
                    await session.commit()
                    logger.info(f"✅ 用户信息更新成功 | username={username}")
                    return True
                return False
        except Exception as e:
            logger.error(f"更新用户失败 | username={username}: {e}", exc_info=True)
            return False

    @staticmethod
    async def update_password(username: str, hashed_password: str) -> bool:
        """更新用户密码"""
        try:
            async with AsyncSessionLocal() as session:
                stmt = select(User).where(User.username == username)
                result = await session.execute(stmt)
                user = result.scalar_one_or_none()

                if not user:
                    logger.warning(f"用户不存在 | username={username}")
                    return False

                user.hashed_password = hashed_password  # type: ignore[assignment]
                await session.commit()
                logger.info(f"✅ 用户密码更新成功 | username={username}")
                return True
        except Exception as e:
            logger.error(f"更新用户密码失败 | username={username}: {e}", exc_info=True)
            return False

    @staticmethod
    async def delete_user(username: str) -> bool:
        """删除用户"""
        try:
            async with AsyncSessionLocal() as session:
                stmt = delete(User).where(User.username == username)
                result = await session.execute(stmt)
                await session.commit()
                # In SQLAlchemy 2.0, use cursor.rowcount from the underlying connection
                count = result.rowcount if hasattr(result, "rowcount") else 0
                if count > 0:
                    logger.info(f"✅ 用户删除成功 | username={username}")
                    return True
                logger.warning(f"用户不存在 | username={username}")
                return False
        except Exception as e:
            logger.error(f"删除用户失败 | username={username}: {e}", exc_info=True)
            return False

    @staticmethod
    async def list_users(limit: int = 100, offset: int = 0) -> List[User]:
        """列出所有用户"""
        try:
            async with AsyncSessionLocal() as session:
                stmt = select(User).offset(offset).limit(limit)
                result = await session.execute(stmt)
                return cast(List[User], list(result.scalars().all()))
        except Exception as e:
            logger.error(f"获取用户列表失败: {e}", exc_info=True)
            return []

    @staticmethod
    async def update_last_login(username: str) -> bool:
        """更新用户最后登录时间"""
        try:
            async with AsyncSessionLocal() as session:
                stmt = select(User).where(User.username == username)
                result = await session.execute(stmt)
                user = result.scalar_one_or_none()

                if user:
                    user.last_login_at = datetime.now()  # type: ignore[assignment]
                    await session.commit()
                    return True
                return False
        except Exception as e:
            logger.error(f"更新最后登录时间失败 | username={username}: {e}", exc_info=True)
            return False

    @staticmethod
    async def enable_mfa(username: str, secret: str, recovery_codes: List[str]) -> bool:
        """启用多因素认证"""
        try:
            async with AsyncSessionLocal() as session:
                stmt = select(User).where(User.username == username)
                result = await session.execute(stmt)
                user = result.scalar_one_or_none()

                if not user:
                    logger.warning(f"用户不存在 | username={username}")
                    return False

                import json

                user.mfa_enabled = True  # type: ignore[assignment]
                user.mfa_secret = secret  # type: ignore[assignment]
                user.recovery_codes = json.dumps(recovery_codes)  # type: ignore[assignment]
                await session.commit()
                logger.info(f"✅ MFA已启用 | username={username}")
                return True
        except Exception as e:
            logger.error(f"启用MFA失败 | username={username}: {e}", exc_info=True)
            return False

    @staticmethod
    async def disable_mfa(username: str) -> bool:
        """禁用多因素认证"""
        try:
            async with AsyncSessionLocal() as session:
                stmt = select(User).where(User.username == username)
                result = await session.execute(stmt)
                user = result.scalar_one_or_none()

                if not user:
                    logger.warning(f"用户不存在 | username={username}")
                    return False

                user.mfa_enabled = False  # type: ignore[assignment]
                user.mfa_secret = None  # type: ignore[assignment]
                user.recovery_codes = None  # type: ignore[assignment]
                await session.commit()
                logger.info(f"✅ MFA已禁用 | username={username}")
                return True
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
