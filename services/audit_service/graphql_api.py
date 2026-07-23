# -*- coding: utf-8 -*-
"""GraphQL-like query interface for audit (task 28.7)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from services.audit_service.repository import AuditRepository
from services.audit_service.schemas import AuditEvent


class AuditGraphQL:
    """Lightweight GraphQL query handler for audit events."""

    def __init__(self, repo: AuditRepository) -> None:
        self.repo = repo

    async def query(
        self,
        fields: List[str],
        tenant_id: Optional[str] = None,
        limit: int = 100,
    ) -> Dict[str, Any]:
        events = await self.repo.list_events(tenant_id=tenant_id, limit=limit)
        return {
            "data": [self._select(e, fields) for e in events],
            "total": len(events),
        }

    @staticmethod
    def _select(event: AuditEvent, fields: List[str]) -> Dict[str, Any]:
        data = event.model_dump()
        if not fields:
            return data
        return {field: data.get(field) for field in fields if field in data}
