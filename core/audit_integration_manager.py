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


def _parse_ts(value: Any) -> datetime:
    """Coerce an ISO string (or datetime) into a timezone-aware datetime."""
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed
        except ValueError:
            pass
    return datetime.now(timezone.utc)


def _priority_from_severity(severity: Any) -> AuditPriority:
    """Map a security-audit severity to an integration-level priority."""
    text = str(getattr(severity, "value", severity) or "").lower()
    if text in {"critical", "high"}:
        return AuditPriority.HIGH
    if text in {"low", "info", "debug"}:
        return AuditPriority.LOW
    return AuditPriority.MEDIUM


def _priority_from_outcome(outcome: Any) -> AuditPriority:
    """Map a compliance/access outcome to an integration-level priority."""
    text = str(outcome or "").lower()
    if text in {"failure", "blocked", "denied", "error"}:
        return AuditPriority.HIGH
    return AuditPriority.MEDIUM


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

        # Per-source dedup: trail/event ids already ingested, so repeated
        # collection passes do not re-add the same real records.
        self._collected_ids: Dict[str, set] = {}

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
        Collect audit trails from a specific source.

        从真实的内部子系统（security_audit / compliance_manager / access_control /
        change_management）读取审计记录；外部/未注册来源不返回任何伪造数据。

        Args:
            source: Audit source

        Returns:
            List of newly collected trail IDs
        """
        trail_ids: List[str] = []

        try:
            events = await self._fetch_source_events(source.endpoint)
        except Exception as e:
            logger.error(f"Failed to collect from source {source.source_id}: {e}")
            return trail_ids

        seen = self._collected_ids.setdefault(source.source_id, set())
        for event in events:
            native_id = str(event.get("trail_id") or "")
            if not native_id or native_id in seen:
                continue
            trail = AuditTrail(
                trail_id=f"{source.source_id}:{native_id}",
                source_id=source.source_id,
                category=source.category,
                event_type=event.get("event_type", "audit_event"),
                user_id=event.get("user_id"),
                resource=event.get("resource"),
                action=event.get("action", ""),
                details=event.get("details", {}) or {},
                priority=event.get("priority", AuditPriority.MEDIUM),
                timestamp=event.get("timestamp") or datetime.now(timezone.utc),
            )
            seen.add(native_id)
            self.audit_trails.append(trail)
            trail_ids.append(trail.trail_id)
            self.total_trails += 1

        # Prune old trails
        if len(self.audit_trails) > self.max_trails:
            self.audit_trails = self.audit_trails[-self.max_trails :]

        return trail_ids

    async def _fetch_source_events(self, endpoint: str) -> List[Dict[str, Any]]:
        """Read real audit records from the subsystem backing ``endpoint``.

        Returns normalized dicts (trail_id/event_type/user_id/resource/action/
        details/timestamp/priority). Unknown or external endpoints return an
        empty list rather than fabricated samples.
        """
        if endpoint == "internal://security_audit":
            from core.security_audit_system import get_security_audit_system

            system = get_security_audit_system()
            return [
                {
                    "trail_id": e.get("event_id"),
                    "event_type": e.get("event_type", "security_event"),
                    "user_id": e.get("user_id"),
                    "resource": e.get("resource"),
                    "action": e.get("action", ""),
                    "details": e.get("details", {}),
                    "timestamp": _parse_ts(e.get("timestamp")),
                    "priority": _priority_from_severity(e.get("severity")),
                }
                for e in system.query_events(limit=self.max_trails)
            ]

        if endpoint == "internal://compliance_manager":
            from core.compliance_manager import get_compliance_manager

            manager = get_compliance_manager()
            return [
                {
                    "trail_id": entry.id,
                    "event_type": (
                        entry.action.value
                        if hasattr(entry.action, "value")
                        else str(entry.action)
                    ),
                    "user_id": entry.user_id,
                    "resource": f"{entry.resource_type}:{entry.resource_id}",
                    "action": entry.outcome,
                    "details": {
                        "tenant_id": entry.tenant_id,
                        "ip_address": entry.ip_address,
                        **(entry.metadata or {}),
                    },
                    "timestamp": _parse_ts(entry.timestamp),
                    "priority": _priority_from_outcome(entry.outcome),
                }
                for entry in manager.get_audit_logs(limit=self.max_trails)
            ]

        if endpoint == "internal://access_control":
            from core.unified_access_control import unified_access_control

            return [
                {
                    "trail_id": f"{e.get('timestamp')}::{e.get('subject_id')}::{e.get('resource')}",
                    "event_type": "access_decision",
                    "user_id": e.get("subject_id"),
                    "resource": e.get("resource"),
                    "action": e.get("action", ""),
                    "details": {
                        "granted": e.get("granted"),
                        "rule_id": e.get("rule_id"),
                        "subject_roles": e.get("subject_roles", []),
                    },
                    "timestamp": _parse_ts(e.get("timestamp")),
                    "priority": (
                        AuditPriority.MEDIUM if e.get("granted") else AuditPriority.HIGH
                    ),
                }
                for e in unified_access_control.get_audit_log(limit=self.max_trails)
            ]

        if endpoint == "internal://change_management":
            from core.change_management_engine import list_requests

            requests = await list_requests()
            events: List[Dict[str, Any]] = []
            for req in requests:
                events.append(
                    {
                        "trail_id": req.id,
                        "event_type": "change_request",
                        "user_id": req.requester,
                        "resource": req.id,
                        "action": (
                            req.status.value
                            if hasattr(req.status, "value")
                            else str(req.status)
                        ),
                        "details": {
                            "title": req.title,
                            "approver": req.approver,
                            "risk_level": (
                                req.risk_level.value
                                if hasattr(req.risk_level, "value")
                                else str(req.risk_level)
                            ),
                            "affected_services": req.affected_services,
                        },
                        "timestamp": datetime.now(timezone.utc),
                    }
                )
            return events

        # External endpoint (e.g. SIEM) without a configured connector:
        # return nothing rather than simulate.
        return []

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
