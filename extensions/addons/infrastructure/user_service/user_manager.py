# -*- coding: utf-8 -*-
"""User CRUD manager (task 29.2)."""

from __future__ import annotations

from typing import List, Optional

from .repository import UserRepository
from .schemas import User, UserCreate, UserUpdate


class UserManager:
    """Manages user CRUD operations."""

    def __init__(self, repo: UserRepository) -> None:
        self.repo = repo

    async def create(self, data: UserCreate) -> User:
        user = User(
            user_id=f"user-{data.username}",
            username=data.username,
            email=data.email,
            full_name=data.full_name,
            role=data.role,
            organization_id=data.organization_id,
            tenant_id=data.tenant_id,
        )
        # Persist a real password hash (previously the password was silently dropped).
        password = getattr(data, "password", "") or ""
        if password:
            try:
                from core.authentication import hash_password

                user.password_hash = hash_password(password)
            except Exception as e:  # noqa: BLE001 - never store plaintext; fail loudly in logs
                import logging

                logging.getLogger(__name__).error(f"Failed to hash user password: {e}")
        await self.repo.save_user(user)
        return user

    async def get(self, user_id: str) -> Optional[User]:
        return await self.repo.get_user(user_id)

    async def list(self, tenant_id: str, limit: int = 100) -> List[User]:
        return await self.repo.list_users(tenant_id, limit)

    async def update(self, user_id: str, data: UserUpdate) -> Optional[User]:
        user = await self.repo.get_user(user_id)
        if not user:
            return None
        update = data.model_dump(exclude_none=True)
        for key, value in update.items():
            setattr(user, key, value)
        await self.repo.save_user(user)
        return user

    async def delete(self, user_id: str) -> bool:
        return await self.repo.delete_user(user_id)
