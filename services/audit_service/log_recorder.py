# -*- coding: utf-8 -*-
"""Operation log recorder (task 28.2)."""

from __future__ import annotations

from typing import Any, Dict, List

from services.audit_service.repository import AuditRepository
from services.audit_service.schemas import OperationLog


class OperationLogRecorder:
    """Records operation logs for audit events."""

    def __init__(self, repo: AuditRepository) -> None:
        self.repo = repo

    async def record(
        self,
        event_id: str,
        action: str,
        actor: str,
        before_state: Dict[str, Any],
        after_state: Dict[str, Any],
    ) -> OperationLog:
        log = OperationLog(
            log_id=f"log-{event_id}",
            event_id=event_id,
            action=action,
            actor=actor,
            before_state=before_state,
            after_state=after_state,
        )
        await self.repo.save_log(log)
        return log

    async def query(self, event_id: str) -> List[OperationLog]:
        return await self.repo.list_logs(event_id)
