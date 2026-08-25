# -*- coding: utf-8 -*-
"""Policy Checker - Validates compliance against defined policies."""

import asyncio
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from loguru import logger

# Import compliance manager from core
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))
from core.compliance_manager import (
    ComplianceFramework,
    ComplianceStatus,
    RiskLevel,
)


class PolicyType(Enum):
    """Policy check types"""
    DATA_RETENTION = "data_retention"
    ACCESS_CONTROL = "access_control"
    ENCRYPTION = "encryption"
    AUDIT_LOGGING = "audit_logging"
    PRIVACY = "privacy"
    SECURITY = "security"
    BUSINESS_CONTINUITY = "business_continuity"


@dataclass
class PolicyCheckResult:
    """Result of a policy check"""
    policy_id: str
    policy_name: str
    policy_type: PolicyType
    passed: bool
    checked_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    findings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    evidence: Dict[str, Any] = field(default_factory=dict)
    severity: RiskLevel = RiskLevel.MEDIUM


@dataclass
class PolicyDefinition:
    """Policy definition"""
    policy_id: str
    policy_name: str
    policy_type: PolicyType
    framework: ComplianceFramework
    description: str
    check_function: Callable
    severity: RiskLevel = RiskLevel.MEDIUM
    enabled: bool = True
    parameters: Dict[str, Any] = field(default_factory=dict)


class PolicyChecker:
    """Policy checker for compliance validation"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize policy checker

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}

        # Policy definitions
        self.policies: Dict[str, PolicyDefinition] = {}

        # Check history
        self.check_history: List[PolicyCheckResult] = []

        # Initialize default policies
        self._initialize_default_policies()

        logger.info("Policy checker initialized")

    def _initialize_default_policies(self) -> None:
        """Initialize default compliance policies"""

        # GDPR - Data Minimization Policy
        self.policies["gdpr_data_minimization"] = PolicyDefinition(
            policy_id="gdpr_data_minimization",
            policy_name="GDPR Data Minimization Policy",
            policy_type=PolicyType.PRIVACY,
            framework=ComplianceFramework.GDPR,
            description="Ensure only necessary personal data is collected and processed",
            check_function=self._check_data_minimization,
            severity=RiskLevel.HIGH,
            parameters={"max_data_fields": 10},
        )

        # GDPR - Consent Management Policy
        self.policies["gdpr_consent_management"] = PolicyDefinition(
            policy_id="gdpr_consent_management",
            policy_name="GDPR Consent Management Policy",
            policy_type=PolicyType.PRIVACY,
            framework=ComplianceFramework.GDPR,
            description="Ensure proper consent collection and management",
            check_function=self._check_consent_management,
            severity=RiskLevel.CRITICAL,
        )

        # HIPAA - PHI Protection Policy
        self.policies["hipaa_phi_protection"] = PolicyDefinition(
            policy_id="hipaa_phi_protection",
            policy_name="HIPAA PHI Protection Policy",
            policy_type=PolicyType.SECURITY,
            framework=ComplianceFramework.HIPAA,
            description="Ensure Protected Health Information is properly protected",
            check_function=self._check_phi_protection,
            severity=RiskLevel.CRITICAL,
        )

        # PCI DSS - Data Encryption Policy
        self.policies["pci_data_encryption"] = PolicyDefinition(
            policy_id="pci_data_encryption",
            policy_name="PCI DSS Data Encryption Policy",
            policy_type=PolicyType.ENCRYPTION,
            framework=ComplianceFramework.PCI_DSS,
            description="Ensure cardholder data is encrypted at rest and in transit",
            check_function=self._check_data_encryption,
            severity=RiskLevel.CRITICAL,
        )

        # PCI DSS - Network Security Policy
        self.policies["pci_network_security"] = PolicyDefinition(
            policy_id="pci_network_security",
            policy_name="PCI DSS Network Security Policy",
            policy_type=PolicyType.SECURITY,
            framework=ComplianceFramework.PCI_DSS,
            description="Ensure network security controls are in place",
            check_function=self._check_network_security,
            severity=RiskLevel.HIGH,
        )

        # SOC 2 - Access Logging Policy
        self.policies["soc2_access_logging"] = PolicyDefinition(
            policy_id="soc2_access_logging",
            policy_name="SOC 2 Access Logging Policy",
            policy_type=PolicyType.AUDIT_LOGGING,
            framework=ComplianceFramework.SOC2,
            description="Ensure comprehensive access logging is enabled",
            check_function=self._check_access_logging,
            severity=RiskLevel.MEDIUM,
        )

        # SOC 2 - Change Management Policy
        self.policies["soc2_change_management"] = PolicyDefinition(
            policy_id="soc2_change_management",
            policy_name="SOC 2 Change Management Policy",
            policy_type=PolicyType.AUDIT_LOGGING,
            framework=ComplianceFramework.SOC2,
            description="Ensure proper change management processes",
            check_function=self._check_change_management,
            severity=RiskLevel.MEDIUM,
        )

        # ISO 27001 - Asset Management Policy
        self.policies["iso27001_asset_management"] = PolicyDefinition(
            policy_id="iso27001_asset_management",
            policy_name="ISO 27001 Asset Management Policy",
            policy_type=PolicyType.SECURITY,
            framework=ComplianceFramework.ISO27001,
            description="Ensure proper asset management and inventory",
            check_function=self._check_asset_management,
            severity=RiskLevel.MEDIUM,
        )

        # ISO 27001 - Security Policy Policy
        self.policies["iso27001_security_policy"] = PolicyDefinition(
            policy_id="iso27001_security_policy",
            policy_name="ISO 27001 Security Policy",
            policy_type=PolicyType.SECURITY,
            framework=ComplianceFramework.ISO27001,
            description="Ensure comprehensive security policy is in place",
            check_function=self._check_security_policy,
            severity=RiskLevel.MEDIUM,
        )

        # NIST - Identify Policy
        self.policies["nist_identify"] = PolicyDefinition(
            policy_id="nist_identify",
            policy_name="NIST Identify Policy",
            policy_type=PolicyType.SECURITY,
            framework=ComplianceFramework.NIST,
            description="Ensure proper asset identification",
            check_function=self._check_asset_identification,
            severity=RiskLevel.MEDIUM,
        )

        # NIST - Protect Policy
        self.policies["nist_protect"] = PolicyDefinition(
            policy_id="nist_protect",
            policy_name="NIST Protect Policy",
            policy_type=PolicyType.SECURITY,
            framework=ComplianceFramework.NIST,
            description="Ensure proper security controls",
            check_function=self._check_security_controls,
            severity=RiskLevel.HIGH,
        )

        logger.info(f"Initialized {len(self.policies)} default policies")

    def register_policy(self, policy: PolicyDefinition) -> None:
        """
        Register a custom policy

        Args:
            policy: Policy definition
        """
        self.policies[policy.policy_id] = policy
        logger.info(f"Registered policy: {policy.policy_id}")

    async def check_policy(
        self,
        policy_id: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> PolicyCheckResult:
        """
        Check a specific policy

        Args:
            policy_id: Policy identifier
            context: Additional context for the check

        Returns:
            Policy check result
        """
        if policy_id not in self.policies:
            return PolicyCheckResult(
                policy_id=policy_id,
                policy_name="Unknown Policy",
                policy_type=PolicyType.SECURITY,
                passed=False,
                findings=["Policy not found"],
                severity=RiskLevel.LOW,
            )

        policy = self.policies[policy_id]

        if not policy.enabled:
            return PolicyCheckResult(
                policy_id=policy_id,
                policy_name=policy.policy_name,
                policy_type=policy.policy_type,
                passed=True,
                findings=["Policy is disabled"],
                severity=policy.severity,
            )

        try:
            # Execute policy check function
            result = await policy.check_function(context or {}, policy.parameters)

            # Store in history
            self.check_history.append(result)

            return result

        except Exception as e:
            logger.error(f"Policy check failed for {policy_id}: {e}")
            return PolicyCheckResult(
                policy_id=policy_id,
                policy_name=policy.policy_name,
                policy_type=policy.policy_type,
                passed=False,
                findings=[f"Check failed with error: {str(e)}"],
                severity=policy.severity,
            )

    async def check_all_policies(
        self,
        framework: Optional[ComplianceFramework] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[PolicyCheckResult]:
        """
        Check all policies

        Args:
            framework: Filter by framework
            context: Additional context for checks

        Returns:
            List of policy check results
        """
        results = []

        for policy_id, policy in self.policies.items():
            if framework and policy.framework != framework:
                continue

            if not policy.enabled:
                continue

            result = await self.check_policy(policy_id, context)
            results.append(result)

        return results

    # Policy check functions

    async def _check_data_minimization(
        self,
        context: Dict[str, Any],
        parameters: Dict[str, Any],
    ) -> PolicyCheckResult:
        """Check data minimization policy"""
        findings = []
        recommendations = []
        passed = True

        # Simulate checking data collection
        data_fields = context.get("data_fields", [])
        max_fields = parameters.get("max_data_fields", 10)

        if len(data_fields) > max_fields:
            passed = False
            findings.append(f"Collecting {len(data_fields)} data fields exceeds limit of {max_fields}")
            recommendations.append("Review and reduce data collection to only necessary fields")

        # Check for sensitive data
        sensitive_fields = ["ssn", "credit_card", "bank_account", "medical_record"]
        for field in data_fields:
            if any(sensitive in field.lower() for sensitive in sensitive_fields):
                findings.append(f"Sensitive field detected: {field}")
                recommendations.append(f"Ensure proper consent and protection for {field}")

        return PolicyCheckResult(
            policy_id="gdpr_data_minimization",
            policy_name="GDPR Data Minimization Policy",
            policy_type=PolicyType.PRIVACY,
            passed=passed,
            findings=findings,
            recommendations=recommendations,
            evidence={"data_field_count": len(data_fields)},
        )

    async def _check_consent_management(
        self,
        context: Dict[str, Any],
        parameters: Dict[str, Any],
    ) -> PolicyCheckResult:
        """Check consent management policy"""
        findings = []
        recommendations = []
        passed = True

        # Check if consent is being tracked
        has_consent_tracking = context.get("has_consent_tracking", False)
        if not has_consent_tracking:
            passed = False
            findings.append("No consent tracking mechanism detected")
            recommendations.append("Implement consent tracking and management system")

        # Check consent expiration
        consent_expiry_days = context.get("consent_expiry_days", 0)
        if consent_expiry_days == 0:
            findings.append("No consent expiration policy defined")
            recommendations.append("Define consent expiration and renewal policy")

        return PolicyCheckResult(
            policy_id="gdpr_consent_management",
            policy_name="GDPR Consent Management Policy",
            policy_type=PolicyType.PRIVACY,
            passed=passed,
            findings=findings,
            recommendations=recommendations,
            evidence={"has_consent_tracking": has_consent_tracking},
        )

    async def _check_phi_protection(
        self,
        context: Dict[str, Any],
        parameters: Dict[str, Any],
    ) -> PolicyCheckResult:
        """Check PHI protection policy"""
        findings = []
        recommendations = []
        passed = True

        # Check encryption
        phi_encrypted = context.get("phi_encrypted", False)
        if not phi_encrypted:
            passed = False
            findings.append("PHI is not encrypted")
            recommendations.append("Enable encryption for all PHI at rest and in transit")

        # Check access controls
        has_access_controls = context.get("has_access_controls", False)
        if not has_access_controls:
            passed = False
            findings.append("No access controls for PHI")
            recommendations.append("Implement role-based access controls for PHI")

        # Check audit logging
        has_audit_logging = context.get("has_audit_logging", False)
        if not has_audit_logging:
            findings.append("No audit logging for PHI access")
            recommendations.append("Enable comprehensive audit logging for PHI access")

        return PolicyCheckResult(
            policy_id="hipaa_phi_protection",
            policy_name="HIPAA PHI Protection Policy",
            policy_type=PolicyType.SECURITY,
            passed=passed,
            findings=findings,
            recommendations=recommendations,
            evidence={
                "phi_encrypted": phi_encrypted,
                "has_access_controls": has_access_controls,
                "has_audit_logging": has_audit_logging,
            },
        )

    async def _check_data_encryption(
        self,
        context: Dict[str, Any],
        parameters: Dict[str, Any],
    ) -> PolicyCheckResult:
        """Check data encryption policy"""
        findings = []
        recommendations = []
        passed = True

        # Check encryption at rest
        encryption_at_rest = context.get("encryption_at_rest", False)
        if not encryption_at_rest:
            passed = False
            findings.append("Data is not encrypted at rest")
            recommendations.append("Enable encryption for data at rest")

        # Check encryption in transit
        encryption_in_transit = context.get("encryption_in_transit", False)
        if not encryption_in_transit:
            passed = False
            findings.append("Data is not encrypted in transit")
            recommendations.append("Enable TLS/SSL for data in transit")

        # Check encryption strength
        encryption_strength = context.get("encryption_strength", "")
        if encryption_strength and encryption_strength not in ["AES-256", "RSA-4096"]:
            findings.append(f"Encryption strength {encryption_strength} may not meet requirements")
            recommendations.append("Use AES-256 or RSA-4096 encryption")

        return PolicyCheckResult(
            policy_id="pci_data_encryption",
            policy_name="PCI DSS Data Encryption Policy",
            policy_type=PolicyType.ENCRYPTION,
            passed=passed,
            findings=findings,
            recommendations=recommendations,
            evidence={
                "encryption_at_rest": encryption_at_rest,
                "encryption_in_transit": encryption_in_transit,
                "encryption_strength": encryption_strength,
            },
        )

    async def _check_network_security(
        self,
        context: Dict[str, Any],
        parameters: Dict[str, Any],
    ) -> PolicyCheckResult:
        """Check network security policy"""
        findings = []
        recommendations = []
        passed = True

        # Check firewall
        has_firewall = context.get("has_firewall", False)
        if not has_firewall:
            passed = False
            findings.append("No firewall configured")
            recommendations.append("Configure and enable firewall")

        # Check intrusion detection
        has_ids = context.get("has_intrusion_detection", False)
        if not has_ids:
            findings.append("No intrusion detection system")
            recommendations.append("Implement intrusion detection system")

        # Check network segmentation
        has_segmentation = context.get("has_network_segmentation", False)
        if not has_segmentation:
            findings.append("No network segmentation")
            recommendations.append("Implement network segmentation for sensitive systems")

        return PolicyCheckResult(
            policy_id="pci_network_security",
            policy_name="PCI DSS Network Security Policy",
            policy_type=PolicyType.SECURITY,
            passed=passed,
            findings=findings,
            recommendations=recommendations,
            evidence={
                "has_firewall": has_firewall,
                "has_intrusion_detection": has_ids,
                "has_network_segmentation": has_segmentation,
            },
        )

    async def _check_access_logging(
        self,
        context: Dict[str, Any],
        parameters: Dict[str, Any],
    ) -> PolicyCheckResult:
        """Check access logging policy"""
        findings = []
        recommendations = []
        passed = True

        # Check if logging is enabled
        logging_enabled = context.get("logging_enabled", False)
        if not logging_enabled:
            passed = False
            findings.append("Access logging is not enabled")
            recommendations.append("Enable comprehensive access logging")

        # Check log retention
        log_retention_days = context.get("log_retention_days", 0)
        if log_retention_days < 90:
            findings.append(f"Log retention period ({log_retention_days} days) is less than 90 days")
            recommendations.append("Configure log retention for at least 90 days")

        return PolicyCheckResult(
            policy_id="soc2_access_logging",
            policy_name="SOC 2 Access Logging Policy",
            policy_type=PolicyType.AUDIT_LOGGING,
            passed=passed,
            findings=findings,
            recommendations=recommendations,
            evidence={"logging_enabled": logging_enabled, "log_retention_days": log_retention_days},
        )

    async def _check_change_management(
        self,
        context: Dict[str, Any],
        parameters: Dict[str, Any],
    ) -> PolicyCheckResult:
        """Check change management policy"""
        findings = []
        recommendations = []
        passed = True

        # Check if change management process exists
        has_change_process = context.get("has_change_process", False)
        if not has_change_process:
            passed = False
            findings.append("No change management process defined")
            recommendations.append("Implement formal change management process")

        # Check approval workflow
        has_approval_workflow = context.get("has_approval_workflow", False)
        if not has_approval_workflow:
            findings.append("No approval workflow for changes")
            recommendations.append("Implement approval workflow for all changes")

        return PolicyCheckResult(
            policy_id="soc2_change_management",
            policy_name="SOC 2 Change Management Policy",
            policy_type=PolicyType.AUDIT_LOGGING,
            passed=passed,
            findings=findings,
            recommendations=recommendations,
            evidence={
                "has_change_process": has_change_process,
                "has_approval_workflow": has_approval_workflow,
            },
        )

    async def _check_asset_management(
        self,
        context: Dict[str, Any],
        parameters: Dict[str, Any],
    ) -> PolicyCheckResult:
        """Check asset management policy"""
        findings = []
        recommendations = []
        passed = True

        # Check if asset inventory exists
        has_asset_inventory = context.get("has_asset_inventory", False)
        if not has_asset_inventory:
            passed = False
            findings.append("No asset inventory maintained")
            recommendations.append("Implement and maintain asset inventory")

        # Check asset classification
        has_asset_classification = context.get("has_asset_classification", False)
        if not has_asset_classification:
            findings.append("No asset classification system")
            recommendations.append("Implement asset classification based on sensitivity")

        return PolicyCheckResult(
            policy_id="iso27001_asset_management",
            policy_name="ISO 27001 Asset Management Policy",
            policy_type=PolicyType.SECURITY,
            passed=passed,
            findings=findings,
            recommendations=recommendations,
            evidence={
                "has_asset_inventory": has_asset_inventory,
                "has_asset_classification": has_asset_classification,
            },
        )

    async def _check_security_policy(
        self,
        context: Dict[str, Any],
        parameters: Dict[str, Any],
    ) -> PolicyCheckResult:
        """Check security policy"""
        findings = []
        recommendations = []
        passed = True

        # Check if security policy exists
        has_security_policy = context.get("has_security_policy", False)
        if not has_security_policy:
            passed = False
            findings.append("No security policy document")
            recommendations.append("Create and maintain comprehensive security policy")

        # Check policy review frequency
        policy_review_days = context.get("policy_review_days", 0)
        if policy_review_days > 365:
            findings.append(f"Security policy review interval ({policy_review_days} days) exceeds 1 year")
            recommendations.append("Review security policy at least annually")

        return PolicyCheckResult(
            policy_id="iso27001_security_policy",
            policy_name="ISO 27001 Security Policy",
            policy_type=PolicyType.SECURITY,
            passed=passed,
            findings=findings,
            recommendations=recommendations,
            evidence={
                "has_security_policy": has_security_policy,
                "policy_review_days": policy_review_days,
            },
        )

    async def _check_asset_identification(
        self,
        context: Dict[str, Any],
        parameters: Dict[str, Any],
    ) -> PolicyCheckResult:
        """Check asset identification policy"""
        findings = []
        recommendations = []
        passed = True

        # Check asset discovery
        has_asset_discovery = context.get("has_asset_discovery", False)
        if not has_asset_discovery:
            passed = False
            findings.append("No automated asset discovery")
            recommendations.append("Implement automated asset discovery")

        return PolicyCheckResult(
            policy_id="nist_identify",
            policy_name="NIST Identify Policy",
            policy_type=PolicyType.SECURITY,
            passed=passed,
            findings=findings,
            recommendations=recommendations,
            evidence={"has_asset_discovery": has_asset_discovery},
        )

    async def _check_security_controls(
        self,
        context: Dict[str, Any],
        parameters: Dict[str, Any],
    ) -> PolicyCheckResult:
        """Check security controls policy"""
        findings = []
        recommendations = []
        passed = True

        # Check access control
        has_access_control = context.get("has_access_control", False)
        if not has_access_control:
            passed = False
            findings.append("No access control system")
            recommendations.append("Implement access control system")

        # Check authentication
        has_mfa = context.get("has_mfa", False)
        if not has_mfa:
            findings.append("Multi-factor authentication not enabled")
            recommendations.append("Enable multi-factor authentication")

        return PolicyCheckResult(
            policy_id="nist_protect",
            policy_name="NIST Protect Policy",
            policy_type=PolicyType.SECURITY,
            passed=passed,
            findings=findings,
            recommendations=recommendations,
            evidence={
                "has_access_control": has_access_control,
                "has_mfa": has_mfa,
            },
        )

    def get_policies(
        self,
        framework: Optional[ComplianceFramework] = None,
        policy_type: Optional[PolicyType] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get policies

        Args:
            framework: Filter by framework
            policy_type: Filter by policy type

        Returns:
            List of policies
        """
        policies = []

        for policy_id, policy in self.policies.items():
            if framework and policy.framework != framework:
                continue
            if policy_type and policy.policy_type != policy_type:
                continue

            policies.append(
                {
                    "policy_id": policy.policy_id,
                    "policy_name": policy.policy_name,
                    "policy_type": policy.policy_type.value,
                    "framework": policy.framework.value,
                    "description": policy.description,
                    "severity": policy.severity.value,
                    "enabled": policy.enabled,
                    "parameters": policy.parameters,
                }
            )

        return policies

    def get_check_history(
        self,
        policy_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Get check history

        Args:
            policy_id: Filter by policy ID
            limit: Maximum number of records

        Returns:
            Check history
        """
        history = self.check_history[-limit:]

        if policy_id:
            history = [h for h in history if h.policy_id == policy_id]

        return [
            {
                "policy_id": h.policy_id,
                "policy_name": h.policy_name,
                "policy_type": h.policy_type.value,
                "passed": h.passed,
                "checked_at": h.checked_at.isoformat(),
                "findings": h.findings,
                "recommendations": h.recommendations,
                "severity": h.severity.value,
            }
            for h in history
        ]
