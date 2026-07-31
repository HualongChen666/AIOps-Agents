# -*- coding: utf-8 -*-
"""
Compliance Management System (Phase 4)
Enterprise-grade compliance management with regulatory frameworks and audit trails
"""

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from loguru import logger


class ComplianceFramework(Enum):
    """Compliance framework types"""

    GDPR = "gdpr"  # General Data Protection Regulation
    HIPAA = "hipaa"  # Health Insurance Portability and Accountability Act
    PCI_DSS = "pci_dss"  # Payment Card Industry Data Security Standard
    SOC2 = "soc2"  # Service Organization Control 2
    ISO27001 = "iso27001"  # ISO/IEC 27001
    NIST = "nist"  # NIST Cybersecurity Framework


class ComplianceStatus(Enum):
    """Compliance status"""

    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    PARTIALLY_COMPLIANT = "partially_compliant"
    PENDING_REVIEW = "pending_review"
    UNKNOWN = "unknown"


class RiskLevel(Enum):
    """Risk level for compliance violations"""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class ComplianceRule:
    """Compliance rule configuration"""

    rule_id: str
    rule_name: str
    framework: ComplianceFramework
    description: str
    severity: RiskLevel = RiskLevel.MEDIUM
    enabled: bool = True
    check_frequency: int = 86400  # 24 hours
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ComplianceCheck:
    """Compliance check result"""

    check_id: str
    rule_id: str
    status: ComplianceStatus
    checked_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    findings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    evidence: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ComplianceReport:
    """Compliance report"""

    report_id: str
    framework: ComplianceFramework
    period_start: datetime
    period_end: datetime
    overall_status: ComplianceStatus
    total_checks: int = 0
    passed_checks: int = 0
    failed_checks: int = 0
    checks: List[ComplianceCheck] = field(default_factory=list)
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)


class ComplianceManager:
    """Enterprise-grade compliance management system"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize compliance manager

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}

        # Compliance rules
        self.compliance_rules: Dict[str, ComplianceRule] = {}
        self._initialize_default_rules()

        # Compliance checks history
        self.check_history: List[ComplianceCheck] = []

        # Compliance reports
        self.compliance_reports: Dict[str, ComplianceReport] = {}

        # Audit trail storage
        self.audit_trail_dir = Path(self.config.get("audit_trail_dir", "./audit_trail"))
        self.audit_trail_dir.mkdir(parents=True, exist_ok=True)

        # Notification handlers
        self.notification_handlers: List[Callable] = []

        # Configuration
        self.auto_check_enabled = self.config.get("auto_check_enabled", True)
        self.check_interval = self.config.get("check_interval", 86400)  # 24 hours

        # Statistics
        self.total_checks = 0
        self.total_violations = 0

        logger.info("Compliance manager initialized")

    def _initialize_default_rules(self):
        """Initialize default compliance rules"""
        # GDPR rules
        self.compliance_rules["gdpr_data_minimization"] = ComplianceRule(
            rule_id="gdpr_data_minimization",
            rule_name="GDPR Data Minimization",
            framework=ComplianceFramework.GDPR,
            description="Ensure only necessary personal data is collected and processed",
            severity=RiskLevel.HIGH,
        )

        self.compliance_rules["gdpr_consent_management"] = ComplianceRule(
            rule_id="gdpr_consent_management",
            rule_name="GDPR Consent Management",
            framework=ComplianceFramework.GDPR,
            description="Ensure proper consent collection and management",
            severity=RiskLevel.CRITICAL,
        )

        self.compliance_rules["gdpr_data_subject_rights"] = ComplianceRule(
            rule_id="gdpr_data_subject_rights",
            rule_name="GDPR Data Subject Rights",
            framework=ComplianceFramework.GDPR,
            description="Ensure data subject rights are implemented",
            severity=RiskLevel.HIGH,
        )

        # HIPAA rules
        self.compliance_rules["hipaa_phi_protection"] = ComplianceRule(
            rule_id="hipaa_phi_protection",
            rule_name="HIPAA PHI Protection",
            framework=ComplianceFramework.HIPAA,
            description="Ensure Protected Health Information is properly protected",
            severity=RiskLevel.CRITICAL,
        )

        self.compliance_rules["hipaa_access_control"] = ComplianceRule(
            rule_id="hipaa_access_control",
            rule_name="HIPAA Access Control",
            framework=ComplianceFramework.HIPAA,
            description="Ensure proper access controls for PHI",
            severity=RiskLevel.HIGH,
        )

        # PCI DSS rules
        self.compliance_rules["pci_data_encryption"] = ComplianceRule(
            rule_id="pci_data_encryption",
            rule_name="PCI DSS Data Encryption",
            framework=ComplianceFramework.PCI_DSS,
            description="Ensure cardholder data is encrypted",
            severity=RiskLevel.CRITICAL,
        )

        self.compliance_rules["pci_network_security"] = ComplianceRule(
            rule_id="pci_network_security",
            rule_name="PCI DSS Network Security",
            framework=ComplianceFramework.PCI_DSS,
            description="Ensure network security controls are in place",
            severity=RiskLevel.HIGH,
        )

        # SOC 2 rules
        self.compliance_rules["soc2_access_logging"] = ComplianceRule(
            rule_id="soc2_access_logging",
            rule_name="SOC 2 Access Logging",
            framework=ComplianceFramework.SOC2,
            description="Ensure comprehensive access logging",
            severity=RiskLevel.MEDIUM,
        )

        self.compliance_rules["soc2_change_management"] = ComplianceRule(
            rule_id="soc2_change_management",
            rule_name="SOC 2 Change Management",
            framework=ComplianceFramework.SOC2,
            description="Ensure proper change management processes",
            severity=RiskLevel.MEDIUM,
        )

        # ISO 27001 rules
        self.compliance_rules["iso27001_asset_management"] = ComplianceRule(
            rule_id="iso27001_asset_management",
            rule_name="ISO 27001 Asset Management",
            framework=ComplianceFramework.ISO27001,
            description="Ensure proper asset management",
            severity=RiskLevel.MEDIUM,
        )

        self.compliance_rules["iso27001_security_policy"] = ComplianceRule(
            rule_id="iso27001_security_policy",
            rule_name="ISO 27001 Security Policy",
            framework=ComplianceFramework.ISO27001,
            description="Ensure comprehensive security policy",
            severity=RiskLevel.MEDIUM,
        )

        # NIST rules
        self.compliance_rules["nist_identify"] = ComplianceRule(
            rule_id="nist_identify",
            rule_name="NIST Identify",
            framework=ComplianceFramework.NIST,
            description="Ensure proper asset identification",
            severity=RiskLevel.MEDIUM,
        )

        self.compliance_rules["nist_protect"] = ComplianceRule(
            rule_id="nist_protect",
            rule_name="NIST Protect",
            framework=ComplianceFramework.NIST,
            description="Ensure proper security controls",
            severity=RiskLevel.HIGH,
        )

        logger.info(f"Initialized {len(self.compliance_rules)} default compliance rules")

    def register_rule(self, rule: ComplianceRule) -> None:
        """
        Register custom compliance rule

        Args:
            rule: Compliance rule
        """
        self.compliance_rules[rule.rule_id] = rule
        logger.info(f"Registered compliance rule: {rule.rule_id}")

    async def run_compliance_check(
        self, rule_id: Optional[str] = None, framework: Optional[ComplianceFramework] = None
    ) -> List[ComplianceCheck]:
        """
        Run compliance check

        Args:
            rule_id: Specific rule ID (optional)
            framework: Framework to check (optional)

        Returns:
            List of compliance check results
        """
        checks = []

        # Determine which rules to check
        rules_to_check = []
        if rule_id:
            if rule_id in self.compliance_rules:
                rules_to_check.append(self.compliance_rules[rule_id])
        elif framework:
            rules_to_check = [r for r in self.compliance_rules.values() if r.framework == framework]
        else:
            rules_to_check = [r for r in self.compliance_rules.values() if r.enabled]

        # Run checks
        for rule in rules_to_check:
            check = await self._check_rule(rule)
            checks.append(check)
            self.check_history.append(check)
            self.total_checks += 1

            if check.status != ComplianceStatus.COMPLIANT:
                self.total_violations += 1

        # Notify handlers
        await self._notify_violations(checks)

        logger.info(f"Completed {len(checks)} compliance checks")

        return checks

    async def _check_rule(self, rule: ComplianceRule) -> ComplianceCheck:
        """
        Check individual compliance rule

        Args:
            rule: Compliance rule

        Returns:
            Compliance check result
        """
        check_id = f"check_{rule.rule_id}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"

        try:
            # Simulate compliance check
            # In real implementation, would perform actual compliance checks
            await asyncio.sleep(0.5)

            # Simulate check result (random for demonstration)
            import secrets

            _random = secrets.SystemRandom()
            is_compliant = _random.random() > 0.3  # 70% chance of compliance

            status = ComplianceStatus.COMPLIANT if is_compliant else ComplianceStatus.NON_COMPLIANT

            findings = []
            recommendations = []

            if not is_compliant:
                findings.append(f"Rule {rule.rule_name} violation detected")
                recommendations.append(f"Address {rule.rule_name} requirements")

            check = ComplianceCheck(
                check_id=check_id,
                rule_id=rule.rule_id,
                status=status,
                findings=findings,
                recommendations=recommendations,
                evidence={"checked_at": datetime.now(timezone.utc).isoformat()},
            )

            return check

        except Exception as e:
            logger.error(f"Compliance check failed for rule {rule.rule_id}: {e}")
            return ComplianceCheck(
                check_id=check_id,
                rule_id=rule.rule_id,
                status=ComplianceStatus.UNKNOWN,
                findings=[f"Check failed: {str(e)}"],
                evidence={"error": str(e)},
            )

    async def generate_compliance_report(
        self, framework: ComplianceFramework, period_start: datetime, period_end: datetime
    ) -> ComplianceReport:
        """
        Generate compliance report

        Args:
            framework: Compliance framework
            period_start: Report period start
            period_end: Report period end

        Returns:
            Compliance report
        """
        report_id = (
            f"report_{framework.value}_{period_start.strftime('%Y%m%d')}_"
            f"{period_end.strftime('%Y%m%d')}"
        )

        # Run compliance checks
        checks = await self.run_compliance_check(framework=framework)

        # Calculate overall status
        passed = len([c for c in checks if c.status == ComplianceStatus.COMPLIANT])
        failed = len([c for c in checks if c.status != ComplianceStatus.COMPLIANT])

        if failed == 0:
            overall_status = ComplianceStatus.COMPLIANT
        elif passed > failed:
            overall_status = ComplianceStatus.PARTIALLY_COMPLIANT
        else:
            overall_status = ComplianceStatus.NON_COMPLIANT

        report = ComplianceReport(
            report_id=report_id,
            framework=framework,
            period_start=period_start,
            period_end=period_end,
            overall_status=overall_status,
            total_checks=len(checks),
            passed_checks=passed,
            failed_checks=failed,
            checks=checks,
        )

        self.compliance_reports[report_id] = report

        # Save report
        await self._save_report(report)

        logger.info(f"Generated compliance report: {report_id}")

        return report

    async def _save_report(self, report: ComplianceReport) -> None:
        """
        Save compliance report

        Args:
            report: Compliance report
        """
        report_path = self.audit_trail_dir / f"{report.report_id}.json"

        report_dict = {
            "report_id": report.report_id,
            "framework": report.framework.value,
            "period_start": report.period_start.isoformat(),
            "period_end": report.period_end.isoformat(),
            "overall_status": report.overall_status.value,
            "total_checks": report.total_checks,
            "passed_checks": report.passed_checks,
            "failed_checks": report.failed_checks,
            "generated_at": report.generated_at.isoformat(),
            "checks": [
                {
                    "check_id": check.check_id,
                    "rule_id": check.rule_id,
                    "status": check.status.value,
                    "findings": check.findings,
                    "recommendations": check.recommendations,
                    "checked_at": check.checked_at.isoformat(),
                }
                for check in report.checks
            ],
        }

        with open(report_path, "w") as f:
            json.dump(report_dict, f, indent=2)

        logger.info(f"Saved compliance report: {report_path}")

    async def _notify_violations(self, checks: List[ComplianceCheck]) -> None:
        """
        Notify about compliance violations

        Args:
            checks: Compliance checks
        """
        violations = [c for c in checks if c.status != ComplianceStatus.COMPLIANT]

        if not violations:
            return

        for handler in self.notification_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(violations)
                else:
                    handler(violations)
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

    def get_compliance_rules(
        self, framework: Optional[ComplianceFramework] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Get compliance rules

        Args:
            framework: Filter by framework (optional)

        Returns:
            Compliance rules dictionary
        """
        rules = {}

        for rule_id, rule in self.compliance_rules.items():
            if framework and rule.framework != framework:
                continue

            rules[rule_id] = {
                "rule_id": rule.rule_id,
                "rule_name": rule.rule_name,
                "framework": rule.framework.value,
                "description": rule.description,
                "severity": rule.severity.value,
                "enabled": rule.enabled,
            }

        return rules

    def get_check_history(
        self, rule_id: Optional[str] = None, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get check history

        Args:
            rule_id: Filter by rule ID (optional)
            limit: Maximum number of records

        Returns:
            Check history
        """
        history = self.check_history[-limit:]

        if rule_id:
            history = [c for c in history if c.rule_id == rule_id]

        return [
            {
                "check_id": check.check_id,
                "rule_id": check.rule_id,
                "status": check.status.value,
                "checked_at": check.checked_at.isoformat(),
                "findings": check.findings,
                "recommendations": check.recommendations,
            }
            for check in history
        ]

    async def start_auto_check_loop(self) -> None:
        """Start automatic compliance check loop"""
        if not self.auto_check_enabled:
            return

        async def check_loop():
            while True:
                try:
                    # Run compliance checks
                    await self.run_compliance_check()

                    await asyncio.sleep(self.check_interval)

                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Auto check loop error: {e}")
                    await asyncio.sleep(self.check_interval)

        asyncio.create_task(check_loop())
        logger.info("Auto compliance check loop started")

    def get_statistics(self) -> Dict[str, Any]:
        """Get compliance statistics"""
        return {
            "total_rules": len(self.compliance_rules),
            "enabled_rules": len([r for r in self.compliance_rules.values() if r.enabled]),
            "total_checks": self.total_checks,
            "total_violations": self.total_violations,
            "violation_rate": (
                self.total_violations / self.total_checks if self.total_checks > 0 else 0.0
            ),
            "total_reports": len(self.compliance_reports),
        }


def get_compliance_manager(config: Optional[Dict[str, Any]] = None) -> ComplianceManager:
    """
    Factory function to get compliance manager instance

    Args:
        config: Optional configuration dictionary

    Returns:
        ComplianceManager: Manager instance
    """
    return ComplianceManager(config)
