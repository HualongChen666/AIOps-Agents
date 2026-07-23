# -*- coding: utf-8 -*-
"""Configuration audit logger (task 30.6)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from services.config_service.repository import ConfigRepository
from services.config_service.schemas import AuditLogEntry


class ConfigAuditLogger:
    """Records configuration changes."""

    def __init__(self, repo: ConfigRepository) -> None:
        self.repo = repo

    async def log(self, config_id: str, action: str, details: Dict[str, Any]) -> AuditLogEntry:
        entry = AuditLogEntry(
            log_id=f"cal-{datetime.utcnow().timestamp()}",
            config_id=config_id,
            action=action,
            details=details,
        )
        await self.repo.save_audit_log(entry)
        return entry

    async def query(self, config_id: str) -> list:
        return await self.repo.list_audit_logs(config_id)
