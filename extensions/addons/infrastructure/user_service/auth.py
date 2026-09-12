# -*- coding: utf-8 -*-
"""OAuth2 and JWT authentication (tasks 29.5 and 29.6)."""

from __future__ import annotations

import hmac
import os
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, cast

from jose import JWTError, jwt

from .config import settings
from .repository import UserRepository
from .schemas import AuthToken, User


class AuthManager:
    """Manages OAuth2/JWT authentication."""

    def __init__(self, repo: UserRepository) -> None:
        self.repo = repo

    async def authenticate(self, username: str, password: str) -> Optional[User]:
        user = await self.repo.get_user_by_username(username)
        if not user:
            return None

        # Prefer the user's stored password hash when present (real credentials).
        stored_hash = getattr(user, "password_hash", None)
        if stored_hash:
            try:
                from core.authentication import verify_password

                return user if verify_password(password, stored_hash) else None
            except Exception:  # noqa: BLE001 - verifier unavailable -> deny
                return None

        # Fallback: explicitly configured demo password. MUST be set and non-empty —
        # the previous default of "" allowed empty-password login for any user.
        expected = os.environ.get("AIOPS_DEMO_PASSWORD", "")
        if not expected:
            return None
        if password and hmac.compare_digest(password, expected):
            return user
        return None

    def create_access_token(self, user: User) -> str:
        payload = {
            "sub": user.user_id,
            "role": user.role,
            "tenant": user.tenant_id,
            "exp": datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes),
        }
        return cast(str, jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm))

    def decode_token(self, token: str) -> Optional[Dict[str, Any]]:
        try:
            return cast(
                Dict[str, Any],
                jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]),
            )
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
            token_type=os.environ.get("DEFAULT_TOKEN_TYPE", "bearer"),
            expires_in=settings.access_token_expire_minutes * 60,
            refresh_token=refresh,
        )
