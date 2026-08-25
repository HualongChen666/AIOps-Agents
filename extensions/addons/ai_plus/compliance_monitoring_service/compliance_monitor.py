# -*- coding: utf-8 -*-
"""Compliance Monitor - Main monitoring logic."""

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from loguru import logger

# Import compliance manager from core
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))
from core.compliance_manager import (
    ComplianceManager,
    ComplianceFramework,
    ComplianceStatus,
    RiskLevel,
    ComplianceRule,
    ComplianceCheck,
    ComplianceReport,
)


class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ComplianceAlert:
    """Compliance violation alert"""
    alert_id: str
    rule_id: str
    rule_name: str
    severity: AlertSeverity
    message: str
    framework: ComplianceFramework
    triggered_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    details: Dict[str, Any] = field(default_factory=dict)
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None


@dataclass
class TrendDataPoint:
    """Trend data point for analysis"""
    timestamp: datetime
    total_checks: int
    passed_checks: int
    failed_checks: int
    compliance_rate: float


class ComplianceMonitor:
    """Compliance monitoring system with real business logic"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize compliance monitor

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}

        # Initialize compliance manager
        self.compliance_manager = ComplianceManager(config)

        # Alert storage
        self.alerts: List[ComplianceAlert] = []
        self.alert_storage_path = Path(self.config.get("alert_storage_path", "./alerts"))
        self.alert_storage_path.mkdir(parents=True, exist_ok=True)

        # Trend data storage
        self.trend_data: List[TrendDataPoint] = []
        self.trend_storage_path = Path(self.config.get("trend_storage_path", "./trends"))
        self.trend_storage_path.mkdir(parents=True, exist_ok=True)

        # Notification handlers
        self.notification_handlers: List[Callable] = []

        # Monitoring configuration
        self.auto_monitor_enabled = self.config.get("auto_monitor_enabled", True)
        self.monitor_interval = self.config.get("monitor_interval", 3600)  # 1 hour
        self.alert_threshold = self.config.get("alert_threshold", 0.8)  # 80% compliance rate

        # Load existing data
        self._load_alerts()
        self._load_trend_data()

        logger.info("Compliance monitor initialized")

    def _load_alerts(self) -> None:
        """Load alerts from storage"""
        alert_file = self.alert_storage_path / "alerts.json"
        if alert_file.exists():
            try:
                with open(alert_file, "r") as f:
                    data = json.load(f)
                    for alert_data in data:
                        alert = ComplianceAlert(
                            alert_id=alert_data["alert_id"],
                            rule_id=alert_data["rule_id"],
                            rule_name=alert_data["rule_name"],
                            severity=AlertSeverity(alert_data["severity"]),
                            message=alert_data["message"],
                            framework=ComplianceFramework(alert_data["framework"]),
                            triggered_at=datetime.fromisoformat(alert_data["triggered_at"]),
                            details=alert_data.get("details", {}),
                            acknowledged=alert_data.get("acknowledged", False),
                            acknowledged_by=alert_data.get("acknowledged_by"),
                            acknowledged_at=datetime.fromisoformat(alert_data["acknowledged_at"]) if alert_data.get("acknowledged_at") else None,
                        )
                        self.alerts.append(alert)
                logger.info(f"Loaded {len(self.alerts)} alerts from storage")
            except Exception as e:
                logger.error(f"Failed to load alerts: {e}")

    def _save_alerts(self) -> None:
        """Save alerts to storage"""
        alert_file = self.alert_storage_path / "alerts.json"
        try:
            data = []
            for alert in self.alerts:
                alert_dict = {
                    "alert_id": alert.alert_id,
                    "rule_id": alert.rule_id,
                    "rule_name": alert.rule_name,
                    "severity": alert.severity.value,
                    "message": alert.message,
                    "framework": alert.framework.value,
                    "triggered_at": alert.triggered_at.isoformat(),
                    "details": alert.details,
                    "acknowledged": alert.acknowledged,
                    "acknowledged_by": alert.acknowledged_by,
                    "acknowledged_at": alert.acknowledged_at.isoformat() if alert.acknowledged_at else None,
                }
                data.append(alert_dict)

            with open(alert_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save alerts: {e}")

    def _load_trend_data(self) -> None:
        """Load trend data from storage"""
        trend_file = self.trend_storage_path / "trends.json"
        if trend_file.exists():
            try:
                with open(trend_file, "r") as f:
                    data = json.load(f)
                    for trend_data in data:
                        trend = TrendDataPoint(
                            timestamp=datetime.fromisoformat(trend_data["timestamp"]),
                            total_checks=trend_data["total_checks"],
                            passed_checks=trend_data["passed_checks"],
                            failed_checks=trend_data["failed_checks"],
                            compliance_rate=trend_data["compliance_rate"],
                        )
                        self.trend_data.append(trend)
                logger.info(f"Loaded {len(self.trend_data)} trend data points from storage")
            except Exception as e:
                logger.error(f"Failed to load trend data: {e}")

    def _save_trend_data(self) -> None:
        """Save trend data to storage"""
        trend_file = self.trend_storage_path / "trends.json"
        try:
            data = []
            for trend in self.trend_data:
                trend_dict = {
                    "timestamp": trend.timestamp.isoformat(),
                    "total_checks": trend.total_checks,
                    "passed_checks": trend.passed_checks,
                    "failed_checks": trend.failed_checks,
                    "compliance_rate": trend.compliance_rate,
                }
                data.append(trend_dict)

            with open(trend_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save trend data: {e}")

    async def run_monitoring_cycle(self) -> List[ComplianceCheck]:
        """
        Run a complete monitoring cycle

        Returns:
            List of compliance checks performed
        """
        logger.info("Starting compliance monitoring cycle")

        # Run compliance checks
        checks = await self.compliance_manager.run_compliance_check()

        # Process results and generate alerts
        await self._process_check_results(checks)

        # Record trend data
        await self._record_trend_data(checks)

        # Save data
        self._save_alerts()
        self._save_trend_data()

        logger.info(f"Completed monitoring cycle with {len(checks)} checks")

        return checks

    async def _process_check_results(self, checks: List[ComplianceCheck]) -> None:
        """
        Process compliance check results and generate alerts

        Args:
            checks: Compliance check results
        """
        for check in checks:
            if check.status != ComplianceStatus.COMPLIANT:
                # Get rule details
                rule = self.compliance_manager.compliance_rules.get(check.rule_id)
                if not rule:
                    continue

                # Determine alert severity based on rule severity
                severity_map = {
                    RiskLevel.CRITICAL: AlertSeverity.CRITICAL,
                    RiskLevel.HIGH: AlertSeverity.ERROR,
                    RiskLevel.MEDIUM: AlertSeverity.WARNING,
                    RiskLevel.LOW: AlertSeverity.INFO,
                }
                alert_severity = severity_map.get(rule.severity, AlertSeverity.WARNING)

                # Create alert
                alert_id = f"alert_{check.check_id}"
                alert = ComplianceAlert(
                    alert_id=alert_id,
                    rule_id=check.rule_id,
                    rule_name=rule.rule_name,
                    severity=alert_severity,
                    message=f"Compliance violation: {rule.rule_name}",
                    framework=rule.framework,
                    details={
                        "check_id": check.check_id,
                        "findings": check.findings,
                        "recommendations": check.recommendations,
                        "evidence": check.evidence,
                    },
                )

                self.alerts.append(alert)

                # Notify handlers
                await self._notify_alert(alert)

                logger.warning(f"Generated compliance alert: {alert_id}")

    async def _record_trend_data(self, checks: List[ComplianceCheck]) -> None:
        """
        Record trend data for analysis

        Args:
            checks: Compliance check results
        """
        total_checks = len(checks)
        passed_checks = len([c for c in checks if c.status == ComplianceStatus.COMPLIANT])
        failed_checks = total_checks - passed_checks
        compliance_rate = passed_checks / total_checks if total_checks > 0 else 0.0

        trend = TrendDataPoint(
            timestamp=datetime.now(timezone.utc),
            total_checks=total_checks,
            passed_checks=passed_checks,
            failed_checks=failed_checks,
            compliance_rate=compliance_rate,
        )

        self.trend_data.append(trend)

        # Keep only last 90 days of data
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=90)
        self.trend_data = [t for t in self.trend_data if t.timestamp > cutoff_date]

        logger.debug(f"Recorded trend data: {compliance_rate:.2%} compliance rate")

    async def _notify_alert(self, alert: ComplianceAlert) -> None:
        """
        Notify about compliance alert

        Args:
            alert: Compliance alert
        """
        for handler in self.notification_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(alert)
                else:
                    handler(alert)
            except Exception as e:
                logger.error(f"Notification handler failed: {e}")

    def register_notification_handler(self, handler: Callable) -> None:
        """
        Register notification handler

        Args:
            handler: Handler function
        """
        self.notification_handlers.append(handler)
        logger.info("Registered compliance notification handler")

    def get_alerts(
        self,
        severity: Optional[AlertSeverity] = None,
        framework: Optional[ComplianceFramework] = None,
        acknowledged: Optional[bool] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Get compliance alerts

        Args:
            severity: Filter by severity
            framework: Filter by framework
            acknowledged: Filter by acknowledgment status
            limit: Maximum number of results

        Returns:
            List of alerts
        """
        alerts = self.alerts

        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        if framework:
            alerts = [a for a in alerts if a.framework == framework]
        if acknowledged is not None:
            alerts = [a for a in alerts if a.acknowledged == acknowledged]

        alerts = alerts[-limit:]

        return [
            {
                "alert_id": a.alert_id,
                "rule_id": a.rule_id,
                "rule_name": a.rule_name,
                "severity": a.severity.value,
                "message": a.message,
                "framework": a.framework.value,
                "triggered_at": a.triggered_at.isoformat(),
                "details": a.details,
                "acknowledged": a.acknowledged,
                "acknowledged_by": a.acknowledged_by,
                "acknowledged_at": a.acknowledged_at.isoformat() if a.acknowledged_at else None,
            }
            for a in alerts
        ]

    def acknowledge_alert(self, alert_id: str, acknowledged_by: str) -> bool:
        """
        Acknowledge a compliance alert

        Args:
            alert_id: Alert identifier
            acknowledged_by: User acknowledging the alert

        Returns:
            True if successful
        """
        for alert in self.alerts:
            if alert.alert_id == alert_id:
                alert.acknowledged = True
                alert.acknowledged_by = acknowledged_by
                alert.acknowledged_at = datetime.now(timezone.utc)
                self._save_alerts()
                logger.info(f"Acknowledged alert: {alert_id}")
                return True
        return False

    def get_trend_analysis(
        self,
        framework: Optional[ComplianceFramework] = None,
        days: int = 30,
    ) -> Dict[str, Any]:
        """
        Get compliance trend analysis

        Args:
            framework: Filter by framework
            days: Number of days to analyze

        Returns:
            Trend analysis data
        """
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        recent_trends = [t for t in self.trend_data if t.timestamp > cutoff_date]

        if not recent_trends:
            return {
                "trend_data": [],
                "overall_trend": "insufficient_data",
                "average_compliance_rate": 0.0,
                "total_checks": 0,
            }

        # Calculate trend
        trend_points = [
            {
                "timestamp": t.timestamp.isoformat(),
                "total_checks": t.total_checks,
                "passed_checks": t.passed_checks,
                "failed_checks": t.failed_checks,
                "compliance_rate": t.compliance_rate,
            }
            for t in recent_trends
        ]

        # Calculate overall trend
        if len(recent_trends) >= 2:
            first_rate = recent_trends[0].compliance_rate
            last_rate = recent_trends[-1].compliance_rate
            if last_rate > first_rate + 0.05:
                overall_trend = "improving"
            elif last_rate < first_rate - 0.05:
                overall_trend = "declining"
            else:
                overall_trend = "stable"
        else:
            overall_trend = "insufficient_data"

        # Calculate average compliance rate
        avg_rate = sum(t.compliance_rate for t in recent_trends) / len(recent_trends)
        total_checks = sum(t.total_checks for t in recent_trends)

        return {
            "trend_data": trend_points,
            "overall_trend": overall_trend,
            "average_compliance_rate": avg_rate,
            "total_checks": total_checks,
        }

    async def start_auto_monitoring(self) -> None:
        """Start automatic monitoring loop"""
        if not self.auto_monitor_enabled:
            return

        async def monitor_loop():
            while True:
                try:
                    await self.run_monitoring_cycle()
                    await asyncio.sleep(self.monitor_interval)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Auto monitoring loop error: {e}")
                    await asyncio.sleep(self.monitor_interval)

        asyncio.create_task(monitor_loop())
        logger.info("Auto compliance monitoring loop started")

    def get_statistics(self) -> Dict[str, Any]:
        """Get monitoring statistics"""
        active_alerts = len([a for a in self.alerts if not a.acknowledged])
        critical_alerts = len([a for a in self.alerts if a.severity == AlertSeverity.CRITICAL and not a.acknowledged])

        return {
            "total_alerts": len(self.alerts),
            "active_alerts": active_alerts,
            "critical_alerts": critical_alerts,
            "trend_data_points": len(self.trend_data),
            "auto_monitoring_enabled": self.auto_monitor_enabled,
            "monitor_interval": self.monitor_interval,
        }
