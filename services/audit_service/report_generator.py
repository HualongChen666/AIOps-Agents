# -*- coding: utf-8 -*-
"""Compliance report generator (task 28.4)."""

from __future__ import annotations

from datetime import datetime

from services.audit_service.compliance import ComplianceTemplate
from services.audit_service.repository import AuditRepository
from services.audit_service.schemas import AuditReport


class ReportGenerator:
    """Generates compliance reports from audit data."""

    def __init__(self, repo: AuditRepository) -> None:
        self.repo = repo

    async def generate(
        self,
        report_type: str,
        tenant_id: str,
        start_time: datetime,
        end_time: datetime,
    ) -> AuditReport:
        events = await self.repo.list_events(tenant_id=tenant_id, limit=10000)
        filtered = [e for e in events if start_time <= e.timestamp <= end_time]
        context = {
            "tenant_id": tenant_id,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "total": len(filtered),
        }
        rendered = ComplianceTemplate.render(report_type, context)
        report = AuditReport(
            report_id=f"{tenant_id}-{report_type}-{datetime.utcnow().isoformat()}",
            report_type=report_type,
            tenant_id=tenant_id,
            start_time=start_time,
            end_time=end_time,
            content=rendered,
            rendered_template=rendered,
        )
        await self.repo.save_report(report)
        return report
