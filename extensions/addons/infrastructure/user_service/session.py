# -*- coding: utf-8 -*-
"""User session management based on Redis (task 29.7)."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from services.user_service.config import settings
from services.user_service.repository import UserRepository
from services.user_service.schemas import Session


class SessionManager:
    """Manages user sessions."""

    def __init__(self, repo: UserRepository) -> None:
        self.repo = repo

    async def create(self, user_id: str) -> Session:
        session = Session(
            session_id=f"sess-{user_id}-{datetime.utcnow().timestamp()}",
            user_id=user_id,
            token=self._generate_token(user_id),
            expires_at=datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days),
        )
        await self.repo.save_session(session)
        return session

    async def get(self, session_id: str) -> Optional[Session]:
        return await self.repo.get_session(session_id)

    async def delete(self, session_id: str) -> bool:
        return await self.repo.delete_session(session_id)

    def _generate_token(self, user_id: str) -> str:
        return f"token-{user_id}"
