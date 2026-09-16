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
        expired = [e.event_id for e in events if e.timestamp < cutoff]
        deleted = 0
        for event_id in expired:
            # 真实删除超出 TTL 的事件（此前仅统计计数，数据从未被处理）。
            if await self.repo.delete_event(event_id):
                deleted += 1
        return {"deleted": deleted, "archived": 0, "tenant_id": tenant_id}

    async def archive(self, tenant_id: str, now: datetime | None = None) -> Dict[str, Any]:
        now = now or datetime.utcnow()
        policy = await self.repo.get_policy(tenant_id)
        archive_after_days = policy.archive_after_days if policy else 90
        cutoff = now - timedelta(days=archive_after_days)
        events = await self.repo.list_events(tenant_id=tenant_id, limit=100000)
        archived = 0
        for event in events:
            if event.timestamp < cutoff and event.status != AuditEventStatus.ARCHIVED:
                # 真实把过期事件标记为已归档并落库（此前仅统计计数）。
                event.status = AuditEventStatus.ARCHIVED
                await self.repo.update_event(event)
                archived += 1
        return {"archived": archived, "tenant_id": tenant_id}
