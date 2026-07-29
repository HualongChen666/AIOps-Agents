# -*- coding: utf-8 -*-
"""User audit logger based on event sourcing (task 29.8)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from services.user_service.repository import UserRepository
from services.user_service.schemas import AuditLogEntry


class UserAuditLogger:
    """Records user actions."""

    def __init__(self, repo: UserRepository) -> None:
        self.repo = repo

    async def log(self, user_id: str, action: str, details: Dict[str, Any]) -> AuditLogEntry:
        entry = AuditLogEntry(
            log_id=f"ual-{datetime.utcnow().timestamp()}",
            user_id=user_id,
            action=action,
            details=details,
        )
        await self.repo.save_audit_log(entry)
        return entry

    async def query(self, user_id: str) -> list:
        return await self.repo.list_audit_logs(user_id)
