# -*- coding: utf-8 -*-
"""OAuth2 and JWT authentication (tasks 29.5 and 29.6)."""

from __future__ import annotations

import hmac
import os
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from jose import JWTError, jwt

from services.user_service.config import settings
from services.user_service.repository import UserRepository
from services.user_service.schemas import AuthToken, User


class AuthManager:
    """Manages OAuth2/JWT authentication."""

    def __init__(self, repo: UserRepository) -> None:
        self.repo = repo

    async def authenticate(self, username: str, password: str) -> Optional[User]:
        user = await self.repo.get_user_by_username(username)
        if not user:
            return None
        # Secure demo password check: compare against environment variable
        expected = os.environ.get("AIOPS_DEMO_PASSWORD", "")
        if hmac.compare_digest(password, expected):
            return user
        return None

    def create_access_token(self, user: User) -> str:
        payload = {
            "sub": user.user_id,
            "role": user.role,
            "tenant": user.tenant_id,
            "exp": datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes),
        }
        return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

    def decode_token(self, token: str) -> Optional[Dict[str, Any]]:
        try:
            return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        except JWTError:
            return None

    async def login(self, username: str, password: str) -> Optional[AuthToken]:
        user = await self.authenticate(username, password)
        if not user:
            return None
        access = self.create_access_token(user)
        refresh = self.create_access_token(user)  # reuse for simplicity
        return AuthToken(
            access_token=access,
            token_type="bearer",  # nosec B106
            expires_in=settings.access_token_expire_minutes * 60,
            refresh_token=refresh,
        )
