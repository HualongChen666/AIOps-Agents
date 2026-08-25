# -*- coding: utf-8 -*-
"""
Audit Integration (Phase 4)
Enterprise-grade audit integration with centralized audit trail management
"""

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from loguru import logger


class AuditCategory(Enum):
    """Audit category types"""

    SECURITY = "security"
    COMPLIANCE = "compliance"
    OPERATIONAL = "operational"
    ACCESS = "access"
    CHANGE = "change"
    PERFORMANCE = "performance"


class AuditPriority(Enum):
    """Audit priority"""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class AuditSource:
    """Audit source configuration"""

    source_id: str
    source_name: str
    category: AuditCategory
    endpoint: str
    authentication: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AuditTrail:
    """Audit trail record"""

    trail_id: str
    source_id: str
    category: AuditCategory
    event_type: str
    user_id: Optional[str] = None
    resource: Optional[str] = None
    action: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    priority: AuditPriority = AuditPriority.MEDIUM
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AuditReport:
    """Audit report"""

    report_id: str
    period_start: datetime
    period_end: datetime
    categories: List[AuditCategory] = field(default_factory=list)
    total_events: int = 0
    summary: Dict[str, Any] = field(default_factory=dict)
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)


class AuditIntegrationManager:
    """Enterprise-grade audit integration manager"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize audit integration manager

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}

        # Audit sources
        self.audit_sources: Dict[str, AuditSource] = {}
        self._initialize_default_sources()

        # Audit trails
        self.audit_trails: List[AuditTrail] = []

        # Audit reports
        self.audit_reports: Dict[str, AuditReport] = {}

        # Storage
        self.storage_dir = Path(self.config.get("storage_dir", "./audit_integration"))
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # Alert handlers
        self.alert_handlers: List[Callable] = []

        # Configuration
        self.max_trails = self.config.get("max_trails", 50000)
        self.auto_collection = self.config.get("auto_collection", True)
        self.collection_interval = self.config.get("collection_interval", 3600)

        # Statistics
        self.total_trails = 0
        self.total_reports = 0

        logger.info("Audit integration manager initialized")

    def _initialize_default_sources(self):
        """Initialize default audit sources"""
        # Security audit source
        self.audit_sources["security_audit"] = AuditSource(
            source_id="security_audit",
            source_name="Security Audit System",
            category=AuditCategory.SECURITY,
            endpoint="internal://security_audit",
            enabled=True,
        )

        # Compliance audit source
        self.audit_sources["compliance_audit"] = AuditSource(
            source_id="compliance_audit",
            source_name="Compliance Manager",
            category=AuditCategory.COMPLIANCE,
            endpoint="internal://compliance_manager",
            enabled=True,
        )

        # Access audit source
        self.audit_sources["access_audit"] = AuditSource(
            source_id="access_audit",
            source_name="Access Control System",
            category=AuditCategory.ACCESS,
            endpoint="internal://access_control",
            enabled=True,
        )

        # Change audit source
        self.audit_sources["change_audit"] = AuditSource(
            source_id="change_audit",
            source_name="Change Management",
            category=AuditCategory.CHANGE,
            endpoint="internal://change_management",
            enabled=True,
        )

        logger.info(f"Initialized {len(self.audit_sources)} default audit sources")

    def register_source(self, source: AuditSource) -> None:
        """
        Register audit source

        Args:
            source: Audit source
        """
        self.audit_sources[source.source_id] = source
        logger.info(f"Registered audit source: {source.source_id}")

    async def collect_audit_trails(
        self, source_id: Optional[str] = None, category: Optional[AuditCategory] = None
    ) -> List[str]:
        """
        Collect audit trails from sources

        Args:
            source_id: Specific source ID (optional)
            category: Filter by category (optional)

        Returns:
            List of trail IDs
        """
        trail_ids = []

        # Determine which sources to collect from
        sources_to_collect = []
        if source_id:
            if source_id in self.audit_sources:
                sources_to_collect.append(self.audit_sources[source_id])
        elif category:
            sources_to_collect = [s for s in self.audit_sources.values() if s.category == category]
        else:
            sources_to_collect = [s for s in self.audit_sources.values() if s.enabled]

        # Collect from each source
        for source in sources_to_collect:
            trails = await self._collect_from_source(source)
            trail_ids.extend(trails)

        logger.info(f"Collected {len(trail_ids)} audit trails")

        return trail_ids

    async def _collect_from_source(self, source: AuditSource) -> List[str]:
        """
        Collect audit trails from specific source

        Args:
            source: Audit source

        Returns:
            List of trail IDs
        """
        trail_ids = []

        try:
            # Simulate collection from source
            # In real implementation, would connect to actual audit source
            await asyncio.sleep(0.5)

            # Simulate some audit trails
            import secrets

            _random = secrets.SystemRandom()
            num_trails = _random.randint(0, 10)

            for i in range(num_trails):
                trail = AuditTrail(
                    trail_id=(
                        f"trail_{source.source_id}_"
                        f"{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{i}"
                    ),
                    source_id=source.source_id,
                    category=source.category,
                    event_type=f"sample_event_{i}",
                    action=f"Sample action {i}",
                    details={"collected_from": source.source_name},
                    priority=_random.choice(list(AuditPriority)),
                )

                self.audit_trails.append(trail)
                trail_ids.append(trail.trail_id)
                self.total_trails += 1

            # Prune old trails
            if len(self.audit_trails) > self.max_trails:
                self.audit_trails = self.audit_trails[-self.max_trails :]

        except Exception as e:
            logger.error(f"Failed to collect from source {source.source_id}: {e}")

        return trail_ids

    async def add_audit_trail(self, trail: AuditTrail) -> str:
        """
        Add audit trail manually

        Args:
            trail: Audit trail

        Returns:
            Trail ID
        """
        self.audit_trails.append(trail)
        self.total_trails += 1

        # Store trail
        await self._store_trail(trail)

        logger.debug(f"Added audit trail: {trail.trail_id}")

        return trail.trail_id

    async def _store_trail(self, trail: AuditTrail) -> None:
        """
        Store audit trail to persistent storage

        Args:
            trail: Audit trail
        """
        trail_path = (
            self.storage_dir / f"trails_{datetime.now(timezone.utc).strftime('%Y%m%d')}.jsonl"
        )

        trail_dict = {
            "trail_id": trail.trail_id,
            "source_id": trail.source_id,
            "category": trail.category.value,
            "event_type": trail.event_type,
            "user_id": trail.user_id,
            "resource": trail.resource,
            "action": trail.action,
            "details": trail.details,
            "priority": trail.priority.value,
            "timestamp": trail.timestamp.isoformat(),
        }

        try:
            with open(trail_path, "a") as f:
                f.write(json.dumps(trail_dict) + "\n")
        except OSError as exc:
            logger.error(f"Failed to write audit trail to {trail_path}: {exc}")
            raise

    async def generate_audit_report(
        self,
        period_start: datetime,
        period_end: datetime,
        categories: Optional[List[AuditCategory]] = None,
    ) -> AuditReport:
        """
        Generate audit report

        Args:
            period_start: Report period start
            period_end: Report period end
            categories: Filter by categories (optional)

        Returns:
            Audit report
        """
        report_id = f"report_{period_start.strftime('%Y%m%d')}_{period_end.strftime('%Y%m%d')}"

        # Filter trails within period
        trails = [t for t in self.audit_trails if period_start <= t.timestamp <= period_end]

        if categories:
            trails = [t for t in trails if t.category in categories]

        # Calculate summary
        by_source: Dict[str, int] = {}
        summary: Dict[str, Any] = {
            "total_events": len(trails),
            "by_category": {
                cat.value: len([t for t in trails if t.category == cat]) for cat in AuditCategory
            },
            "by_priority": {
                "high": len([t for t in trails if t.priority == AuditPriority.HIGH]),
                "medium": len([t for t in trails if t.priority == AuditPriority.MEDIUM]),
                "low": len([t for t in trails if t.priority == AuditPriority.LOW]),
            },
            "by_source": by_source,
        }

        for trail in trails:
            source_id = trail.source_id
            if source_id not in by_source:
                by_source[source_id] = 0
            by_source[source_id] += 1

        report = AuditReport(
            report_id=report_id,
            period_start=period_start,
            period_end=period_end,
            categories=categories or list(AuditCategory),
            total_events=len(trails),
            summary=summary,
        )

        self.audit_reports[report_id] = report
        self.total_reports += 1

        # Save report
        await self._save_report(report)

        logger.info(f"Generated audit report: {report_id}")

        return report

    async def _save_report(self, report: AuditReport) -> None:
        """
        Save audit report

        Args:
            report: Audit report
        """
        report_path = self.storage_dir / f"{report.report_id}.json"

        report_dict = {
            "report_id": report.report_id,
            "period_start": report.period_start.isoformat(),
            "period_end": report.period_end.isoformat(),
            "categories": [c.value for c in report.categories],
            "total_events": report.total_events,
            "summary": report.summary,
            "generated_at": report.generated_at.isoformat(),
        }

        try:
            with open(report_path, "w") as f:
                json.dump(report_dict, f, indent=2)
        except OSError as exc:
            logger.error(f"Failed to write audit report to {report_path}: {exc}")
            raise

    def query_trails(
        self,
        source_id: Optional[str] = None,
        category: Optional[AuditCategory] = None,
        event_type: Optional[str] = None,
        user_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Query audit trails

        Args:
            source_id: Filter by source ID
            category: Filter by category
            event_type: Filter by event type
            user_id: Filter by user ID
            start_time: Filter by start time
            end_time: Filter by end time
            limit: Maximum number of records

        Returns:
            Query results
        """
        trails = self.audit_trails

        if source_id:
            trails = [t for t in trails if t.source_id == source_id]
        if category:
            trails = [t for t in trails if t.category == category]
        if event_type:
            trails = [t for t in trails if t.event_type == event_type]
        if user_id:
            trails = [t for t in trails if t.user_id == user_id]
        if start_time:
            trails = [t for t in trails if t.timestamp >= start_time]
        if end_time:
            trails = [t for t in trails if t.timestamp <= end_time]

        trails = trails[-limit:]

        return [
            {
                "trail_id": t.trail_id,
                "source_id": t.source_id,
                "category": t.category.value,
                "event_type": t.event_type,
                "user_id": t.user_id,
                "resource": t.resource,
                "action": t.action,
                "details": t.details,
                "priority": t.priority.value,
                "timestamp": t.timestamp.isoformat(),
            }
            for t in trails
        ]

    async def start_auto_collection(self) -> None:
        """Start automatic audit trail collection loop"""
        if not self.auto_collection:
            return

        async def collection_loop():
            while True:
                try:
                    # Collect audit trails from all sources
                    await self.collect_audit_trails()

                    await asyncio.sleep(self.collection_interval)

                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Auto collection loop error: {e}")
                    await asyncio.sleep(self.collection_interval)

        asyncio.create_task(collection_loop())
        logger.info("Auto audit trail collection loop started")

    def register_alert_handler(self, handler: Callable) -> None:
        """
        Register alert handler

        Args:
            handler: Handler function
        """
        self.alert_handlers.append(handler)
        logger.info("Registered audit alert handler")

    def get_statistics(self) -> Dict[str, Any]:
        """Get audit integration statistics"""
        return {
            "total_sources": len(self.audit_sources),
            "enabled_sources": len([s for s in self.audit_sources.values() if s.enabled]),
            "total_trails": self.total_trails,
            "total_reports": self.total_reports,
            "trail_retention_limit": self.max_trails,
        }


def get_audit_integration_manager(
    config: Optional[Dict[str, Any]] = None,
) -> AuditIntegrationManager:
    """
    Factory function to get audit integration manager instance

    Args:
        config: Optional configuration dictionary

    Returns:
        AuditIntegrationManager: Manager instance
    """
    return AuditIntegrationManager(config)
