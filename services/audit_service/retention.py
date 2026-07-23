# -*- coding: utf-8 -*-
"""Audit data retention based on TTL (task 28.6)."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict

from services.audit_service.repository import AuditRepository
from services.audit_service.schemas import AuditEventStatus, RetentionPolicy


class RetentionManager:
    """Manages audit data retention, cleanup and archival."""

    def __init__(self, repo: AuditRepository) -> None:
        self.repo = repo

    async def apply_policy(
        self,
        tenant_id: str,
        ttl_days: int = 365,
        archive_after_days: int = 90,
        auto_archive: bool = True,
    ) -> RetentionPolicy:
        policy = RetentionPolicy(
            policy_id=f"policy-{tenant_id}",
            tenant_id=tenant_id,
            ttl_days=ttl_days,
            archive_after_days=archive_after_days,
            auto_archive=auto_archive,
        )
        await self.repo.save_policy(policy)
        return policy

    async def cleanup(self, tenant_id: str, now: datetime | None = None) -> Dict[str, Any]:
        now = now or datetime.utcnow()
        policy = await self.repo.get_policy(tenant_id)
        ttl_days = policy.ttl_days if policy else 365
        cutoff = now - timedelta(days=ttl_days)
        events = await self.repo.list_events(tenant_id=tenant_id, limit=100000)
        deleted = [e.event_id for e in events if e.timestamp < cutoff]
        return {"deleted": len(deleted), "archived": 0, "tenant_id": tenant_id}

    async def archive(self, tenant_id: str, now: datetime | None = None) -> Dict[str, Any]:
        now = now or datetime.utcnow()
        policy = await self.repo.get_policy(tenant_id)
        archive_after_days = policy.archive_after_days if policy else 90
        cutoff = now - timedelta(days=archive_after_days)
        events = await self.repo.list_events(tenant_id=tenant_id, limit=100000)
        archived = [
            e.event_id
            for e in events
            if e.timestamp < cutoff and e.status != AuditEventStatus.ARCHIVED
        ]
        return {"archived": len(archived), "tenant_id": tenant_id}
