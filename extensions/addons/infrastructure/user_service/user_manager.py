# -*- coding: utf-8 -*-
"""User CRUD manager (task 29.2)."""

from __future__ import annotations

from typing import List, Optional

from services.user_service.repository import UserRepository
from services.user_service.schemas import User, UserCreate, UserUpdate


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
