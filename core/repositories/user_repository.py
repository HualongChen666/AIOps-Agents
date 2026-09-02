# -*- coding: utf-8 -*-
# core/repositories/user_repository.py
# 统一的用户Repository层 - 实现数据库持久化

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from core.db_engine import AsyncSessionLocal
from core.models import User

logger = logging.getLogger(__name__)


class UserRepository:
    """用户Repository - 处理所有用户相关的数据库操作"""

    def __init__(self, session: Optional[AsyncSession] = None):
        """初始化Repository
        
        Args:
            session: 可选的数据库会话，如果未提供则创建新会话
        """
        self._session = session
        self._owns_session = session is None

    async def __aenter__(self):
        """异步上下文管理器入口"""
        if self._owns_session:
            self._session = AsyncSessionLocal()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器退出"""
        if self._owns_session and self._session:
            await self._session.close()

    @property
    def session(self) -> AsyncSession:
        """获取数据库会话"""
        if not self._session:
            raise RuntimeError("Session not initialized. Use async context manager or provide session.")
        return self._session

    async def get_by_id(self, user_id: int) -> Optional[User]:
        """根据ID获取用户
        
        Args:
            user_id: 用户ID
            
        Returns:
            User对象或None
        """
        try:
            stmt = select(User).where(User.id == user_id)
            result = await self.session.execute(stmt)
            user = result.scalar_one_or_none()
            logger.debug(f"获取用户 | user_id={user_id} | found={user is not None}")
            return user
        except Exception as e:
            logger.error(f"获取用户失败 | user_id={user_id}: {e}", exc_info=True)
            raise

    async def get_by_username(self, username: str) -> Optional[User]:
        """根据用户名获取用户
        
        Args:
            username: 用户名
            
        Returns:
            User对象或None
        """
        try:
            stmt = select(User).where(User.username == username)
            result = await self.session.execute(stmt)
            user = result.scalar_one_or_none()
            logger.debug(f"获取用户 | username={username} | found={user is not None}")
            return user
        except Exception as e:
            logger.error(f"获取用户失败 | username={username}: {e}", exc_info=True)
            raise

    async def get_by_email(self, email: str) -> Optional[User]:
        """根据邮箱获取用户
        
        Args:
            email: 邮箱地址
            
        Returns:
            User对象或None
        """
        try:
            stmt = select(User).where(User.email == email)
            result = await self.session.execute(stmt)
            user = result.scalar_one_or_none()
            logger.debug(f"获取用户 | email={email} | found={user is not None}")
            return user
        except Exception as e:
            logger.error(f"获取用户失败 | email={email}: {e}", exc_info=True)
            raise

    async def create(
        self,
        username: str,
        hashed_password: str,
        email: Optional[str] = None,
        full_name: Optional[str] = None,
        role: str = "user",
        disabled: bool = False,
    ) -> User:
        """创建新用户
        
        Args:
            username: 用户名
            hashed_password: 哈希后的密码
            email: 邮箱地址
            full_name: 全名
            role: 角色
            disabled: 是否禁用
            
        Returns:
            创建的User对象
            
        Raises:
            ValueError: 如果用户名或邮箱已存在
        """
        try:
            # 检查用户名是否已存在
            existing = await self.get_by_username(username)
            if existing:
                raise ValueError(f"用户名已存在: {username}")

            # 检查邮箱是否已存在
            if email:
                existing_email = await self.get_by_email(email)
                if existing_email:
                    raise ValueError(f"邮箱已存在: {email}")

            new_user = User(
                username=username,
                hashed_password=hashed_password,
                email=email,
                full_name=full_name,
                role=role,
                disabled=disabled,
                mfa_enabled=False,
            )
            self.session.add(new_user)
            await self.session.commit()
            await self.session.refresh(new_user)
            logger.info(f"✅ 用户创建成功 | username={username} | id={new_user.id}")
            return new_user
        except ValueError:
            raise
        except Exception as e:
            await self.session.rollback()
            logger.error(f"创建用户失败 | username={username}: {e}", exc_info=True)
            raise

    async def update(
        self,
        user_id: int,
        email: Optional[str] = None,
        full_name: Optional[str] = None,
        role: Optional[str] = None,
        disabled: Optional[bool] = None,
    ) -> Optional[User]:
        """更新用户信息
        
        Args:
            user_id: 用户ID
            email: 新邮箱
            full_name: 新全名
            role: 新角色
            disabled: 是否禁用
            
        Returns:
            更新后的User对象或None
        """
        try:
            user = await self.get_by_id(user_id)
            if not user:
                return None

            update_data: Dict[str, Any] = {}
            if email is not None:
                # 检查邮箱是否被其他用户使用
                existing = await self.get_by_email(email)
                if existing and existing.id != user_id:
                    raise ValueError(f"邮箱已被其他用户使用: {email}")
                update_data["email"] = email
            if full_name is not None:
                update_data["full_name"] = full_name
            if role is not None:
                update_data["role"] = role
            if disabled is not None:
                update_data["disabled"] = disabled

            if update_data:
                stmt = update(User).where(User.id == user_id).values(**update_data)
                await self.session.execute(stmt)
                await self.session.commit()
                await self.session.refresh(user)
                logger.info(f"✅ 用户信息更新成功 | user_id={user_id}")
            return user
        except ValueError:
            raise
        except Exception as e:
            await self.session.rollback()
            logger.error(f"更新用户失败 | user_id={user_id}: {e}", exc_info=True)
            raise

    async def update_password(self, user_id: int, hashed_password: str) -> bool:
        """更新用户密码
        
        Args:
            user_id: 用户ID
            hashed_password: 新的哈希密码
            
        Returns:
            是否更新成功
        """
        try:
            user = await self.get_by_id(user_id)
            if not user:
                return False

            user.hashed_password = hashed_password  # type: ignore[assignment]
            await self.session.commit()
            logger.info(f"✅ 用户密码更新成功 | user_id={user_id}")
            return True
        except Exception as e:
            await self.session.rollback()
            logger.error(f"更新用户密码失败 | user_id={user_id}: {e}", exc_info=True)
            return False

    async def delete(self, user_id: int) -> bool:
        """删除用户
        
        Args:
            user_id: 用户ID
            
        Returns:
            是否删除成功
        """
        try:
            stmt = delete(User).where(User.id == user_id)
            result = await self.session.execute(stmt)
            await self.session.commit()
            count = result.rowcount if hasattr(result, "rowcount") else 0
            if count > 0:
                logger.info(f"✅ 用户删除成功 | user_id={user_id}")
                return True
            return False
        except Exception as e:
            await self.session.rollback()
            logger.error(f"删除用户失败 | user_id={user_id}: {e}", exc_info=True)
            return False

    async def list_users(
        self, limit: int = 100, offset: int = 0, role: Optional[str] = None
    ) -> List[User]:
        """列出用户
        
        Args:
            limit: 返回数量限制
            offset: 偏移量
            role: 角色过滤
            
        Returns:
            用户列表
        """
        try:
            stmt = select(User)
            if role:
                stmt = stmt.where(User.role == role)
            stmt = stmt.offset(offset).limit(limit)
            result = await self.session.execute(stmt)
            users = list(result.scalars().all())
            logger.debug(f"获取用户列表 | count={len(users)}")
            return users
        except Exception as e:
            logger.error(f"获取用户列表失败: {e}", exc_info=True)
            raise

    async def count(self, role: Optional[str] = None) -> int:
        """统计用户数量
        
        Args:
            role: 角色过滤
            
        Returns:
            用户数量
        """
        try:
            from sqlalchemy import func

            stmt = select(func.count(User.id))
            if role:
                stmt = stmt.where(User.role == role)
            result = await self.session.execute(stmt)
            count = result.scalar()
            logger.debug(f"统计用户数量 | count={count}")
            return count if count else 0
        except Exception as e:
            logger.error(f"统计用户数量失败: {e}", exc_info=True)
            raise

    async def update_last_login(self, user_id: int) -> bool:
        """更新用户最后登录时间
        
        Args:
            user_id: 用户ID
            
        Returns:
            是否更新成功
        """
        try:
            user = await self.get_by_id(user_id)
            if user:
                user.last_login_at = datetime.now()  # type: ignore[assignment]
                await self.session.commit()
                return True
            return False
        except Exception as e:
            await self.session.rollback()
            logger.error(f"更新最后登录时间失败 | user_id={user_id}: {e}", exc_info=True)
            return False

    async def enable_mfa(
        self, user_id: int, secret: str, recovery_codes: List[str]
    ) -> bool:
        """启用多因素认证
        
        Args:
            user_id: 用户ID
            secret: MFA密钥
            recovery_codes: 恢复码列表
            
        Returns:
            是否启用成功
        """
        try:
            import json

            user = await self.get_by_id(user_id)
            if not user:
                return False

            user.mfa_enabled = True  # type: ignore[assignment]
            user.mfa_secret = secret  # type: ignore[assignment]
            user.recovery_codes = json.dumps(recovery_codes)  # type: ignore[assignment]
            await self.session.commit()
            logger.info(f"✅ MFA已启用 | user_id={user_id}")
            return True
        except Exception as e:
            await self.session.rollback()
            logger.error(f"启用MFA失败 | user_id={user_id}: {e}", exc_info=True)
            return False

    async def disable_mfa(self, user_id: int) -> bool:
        """禁用多因素认证
        
        Args:
            user_id: 用户ID
            
        Returns:
            是否禁用成功
        """
        try:
            user = await self.get_by_id(user_id)
            if not user:
                return False

            user.mfa_enabled = False  # type: ignore[assignment]
            user.mfa_secret = None  # type: ignore[assignment]
            user.recovery_codes = None  # type: ignore[assignment]
            await self.session.commit()
            logger.info(f"✅ MFA已禁用 | user_id={user_id}")
            return True
        except Exception as e:
            await self.session.rollback()
            logger.error(f"禁用MFA失败 | user_id={user_id}: {e}", exc_info=True)
            return False

    async def batch_create(
        self, users_data: List[Dict[str, Any]], batch_size: int = 50
    ) -> List[User]:
        """批量创建用户（分批处理以避免系统过载）
        
        Args:
            users_data: 用户数据列表
            batch_size: 每批处理数量
            
        Returns:
            创建的用户列表
        """
        created_users = []
        total = len(users_data)

        for i in range(0, total, batch_size):
            batch = users_data[i : i + batch_size]
            logger.info(f"批量创建用户 | batch={i // batch_size + 1} | size={len(batch)}")

            try:
                for user_data in batch:
                    user = await self.create(
                        username=user_data["username"],
                        hashed_password=user_data["hashed_password"],
                        email=user_data.get("email"),
                        full_name=user_data.get("full_name"),
                        role=user_data.get("role", "user"),
                        disabled=user_data.get("disabled", False),
                    )
                    created_users.append(user)
            except Exception as e:
                logger.error(f"批量创建用户失败 | batch={i // batch_size + 1}: {e}", exc_info=True)
                # 继续处理下一批

        logger.info(f"✅ 批量创建用户完成 | total={total} | created={len(created_users)}")
        return created_users

    def to_dict(self, user: User) -> Dict[str, Any]:
        """将User对象转换为字典
        
        Args:
            user: User对象
            
        Returns:
            用户字典
        """
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
