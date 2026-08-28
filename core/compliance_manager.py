# -*- coding: utf-8 -*-
"""
Compliance Management Module

This module provides compliance management for enterprise deployments,
including audit logging, policy execution, and compliance tracking.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set
from enum import Enum
from collections import defaultdict, deque

from loguru import logger


class ComplianceStandard(Enum):
    """Compliance standard enumeration"""
    
    SOC2 = "soc2"
    GDPR = "gdpr"
    ISO27001 = "iso27001"
    HIPAA = "hipaa"
    PCI_DSS = "pci_dss"


class ComplianceStatus(Enum):
    """Compliance status enumeration"""
    
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    PARTIAL = "partial"
    PENDING = "pending"
    EXEMPT = "exempt"


class PolicyType(Enum):
    """Policy type enumeration"""
    
    ACCESS_CONTROL = "access_control"
    DATA_PROTECTION = "data_protection"
    INCIDENT_RESPONSE = "incident_response"
    CHANGE_MANAGEMENT = "change_management"
    AUDIT_LOGGING = "audit_logging"
    ENCRYPTION = "encryption"
    PRIVACY = "privacy"


class ActionType(Enum):
    """Audit action type enumeration"""
    
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    LOGOUT = "logout"
    EXPORT = "export"
    IMPORT = "import"
    APPROVE = "approve"
    REJECT = "reject"
    EXECUTE = "execute"


@dataclass
class AuditLogEntry:
    """Audit log entry"""
    
    id: str
    tenant_id: str
    user_id: str
    action: ActionType
    resource_type: str
    resource_id: str
    outcome: str  # success, failure, blocked
    timestamp: datetime
    ip_address: str
    user_agent: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "action": self.action.value,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "outcome": self.outcome,
            "timestamp": self.timestamp.isoformat(),
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "metadata": self.metadata
        }


@dataclass
class CompliancePolicy:
    """Compliance policy definition"""
    
    id: str
    name: str
    standard: ComplianceStandard
    policy_type: PolicyType
    description: str
    requirements: List[str]
    enabled: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "name": self.name,
            "standard": self.standard.value,
            "policy_type": self.policy_type.value,
            "description": self.description,
            "requirements": self.requirements,
            "enabled": self.enabled,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }


@dataclass
class ComplianceCheck:
    """Compliance check result"""
    
    policy_id: str
    policy_name: str
    status: ComplianceStatus
    findings: List[str]
    evidence: Dict[str, Any]
    checked_at: datetime
    checked_by: str
    next_check: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "policy_id": self.policy_id,
            "policy_name": self.policy_name,
            "status": self.status.value,
            "findings": self.findings,
            "evidence": self.evidence,
            "checked_at": self.checked_at.isoformat(),
            "checked_by": self.checked_by,
            "next_check": self.next_check.isoformat()
        }


class ComplianceManager:
    """Compliance management system"""
    
    def __init__(self):
        """Initialize compliance manager"""
        self.policies: Dict[str, CompliancePolicy] = {}
        self.compliance_checks: Dict[str, List[ComplianceCheck]] = {}
        self.audit_logs: deque = deque(maxlen=100000)  # Long-term storage
        self.audit_index: Dict[str, Set[str]] = defaultdict(set)  # Index for fast lookup
        
        # Configuration
        self.audit_retention_days = 365
        self.compliance_check_interval = timedelta(days=30)
        
        # Initialize default policies
        self._initialize_default_policies()
    
    def _initialize_default_policies(self):
        """Initialize default compliance policies"""
        # SOC2 policies
        self.policies["soc2_access_control"] = CompliancePolicy(
            id="soc2_access_control",
            name="SOC2 Access Control",
            standard=ComplianceStandard.SOC2,
            policy_type=PolicyType.ACCESS_CONTROL,
            description="Ensure proper access controls are in place",
            requirements=[
                "multi_factor_authentication",
                "role_based_access_control",
                "regular_access_reviews",
                "least_privilege_principle"
            ]
        )
        
        self.policies["soc2_incident_response"] = CompliancePolicy(
            id="soc2_incident_response",
            name="SOC2 Incident Response",
            standard=ComplianceStandard.SOC2,
            policy_type=PolicyType.INCIDENT_RESPONSE,
            description="Ensure incident response procedures are defined",
            requirements=[
                "incident_detection_mechanisms",
                "response_playbook",
                "escalation_procedures",
                "post_incident_review"
            ]
        )
        
        # GDPR policies
        self.policies["gdpr_data_protection"] = CompliancePolicy(
            id="gdpr_data_protection",
            name="GDPR Data Protection",
            standard=ComplianceStandard.GDPR,
            policy_type=PolicyType.DATA_PROTECTION,
            description="Ensure personal data is protected",
            requirements=[
                "data_encryption_at_rest",
                "data_encryption_in_transit",
                "data_minimization",
                "right_to_be_forgotten"
            ]
        )
        
        self.policies["gdpr_audit_logging"] = CompliancePolicy(
            id="gdpr_audit_logging",
            name="GDPR Audit Logging",
            standard=ComplianceStandard.GDPR,
            policy_type=PolicyType.AUDIT_LOGGING,
            description="Ensure comprehensive audit logging",
            requirements=[
                "audit_trail_for_all_actions",
                "log_retention_policy",
                "log_integrity_protection",
                "regular_log_reviews"
            ]
        )
        
        # ISO27001 policies
        self.policies["iso27001_encryption"] = CompliancePolicy(
            id="iso27001_encryption",
            name="ISO27001 Encryption",
            standard=ComplianceStandard.ISO27001,
            policy_type=PolicyType.ENCRYPTION,
            description="Ensure proper encryption standards",
            requirements=[
                "encryption_key_management",
                "secure_cryptographic_algorithms",
                "key_rotation_policy",
                "encryption_at_rest_and_transit"
            ]
        )
        
        logger.info(f"Initialized {len(self.policies)} default compliance policies")
    
    def add_policy(self, policy: CompliancePolicy) -> bool:
        """Add a compliance policy"""
        if policy.id in self.policies:
            logger.warning(f"Policy already exists: {policy.id}")
            return False
        
        self.policies[policy.id] = policy
        logger.info(f"Added compliance policy: {policy.id}")
        return True
    
    def get_policy(self, policy_id: str) -> Optional[CompliancePolicy]:
        """Get a compliance policy"""
        return self.policies.get(policy_id)
    
    def get_policies_by_standard(self, standard: ComplianceStandard) -> List[CompliancePolicy]:
        """Get all policies for a compliance standard"""
        return [p for p in self.policies.values() if p.standard == standard]
    
    def enable_policy(self, policy_id: str) -> bool:
        """Enable a compliance policy"""
        policy = self.get_policy(policy_id)
        if not policy:
            logger.error(f"Policy not found: {policy_id}")
            return False
        
        policy.enabled = True
        policy.updated_at = datetime.now()
        logger.info(f"Enabled compliance policy: {policy_id}")
        return True
    
    def disable_policy(self, policy_id: str) -> bool:
        """Disable a compliance policy"""
        policy = self.get_policy(policy_id)
        if not policy:
            logger.error(f"Policy not found: {policy_id}")
            return False
        
        policy.enabled = False
        policy.updated_at = datetime.now()
        logger.info(f"Disabled compliance policy: {policy_id}")
        return True
    
    def log_audit_event(
        self,
        tenant_id: str,
        user_id: str,
        action: ActionType,
        resource_type: str,
        resource_id: str,
        outcome: str,
        ip_address: str,
        user_agent: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AuditLogEntry:
        """Log an audit event"""
        import uuid
        
        entry = AuditLogEntry(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            outcome=outcome,
            timestamp=datetime.now(),
            ip_address=ip_address,
            user_agent=user_agent,
            metadata=metadata or {}
        )
        
        self.audit_logs.append(entry)
        
        # Update index
        self.audit_index[tenant_id].add(entry.id)
        self.audit_index[user_id].add(entry.id)
        self.audit_index[resource_type].add(entry.id)
        
        return entry
    
    def get_audit_logs(
        self,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[AuditLogEntry]:
        """Get audit logs with filters"""
        filtered_logs = list(self.audit_logs)
        
        # Apply filters
        if tenant_id:
            filtered_logs = [log for log in filtered_logs if log.tenant_id == tenant_id]
        
        if user_id:
            filtered_logs = [log for log in filtered_logs if log.user_id == user_id]
        
        if resource_type:
            filtered_logs = [log for log in filtered_logs if log.resource_type == resource_type]
        
        if start_time:
            filtered_logs = [log for log in filtered_logs if log.timestamp >= start_time]
        
        if end_time:
            filtered_logs = [log for log in filtered_logs if log.timestamp <= end_time]
        
        # Sort by timestamp descending
        filtered_logs.sort(key=lambda x: x.timestamp, reverse=True)
        
        # Apply limit
        return filtered_logs[:limit]
    
    def run_compliance_check(
        self,
        policy_id: str,
        checked_by: str
    ) -> ComplianceCheck:
        """Run a compliance check for a policy"""
        policy = self.get_policy(policy_id)
        if not policy:
            raise ValueError(f"Policy not found: {policy_id}")
        
        if not policy.enabled:
            return ComplianceCheck(
                policy_id=policy_id,
                policy_name=policy.name,
                status=ComplianceStatus.EXEMPT,
                findings=["Policy is disabled"],
                evidence={},
                checked_at=datetime.now(),
                checked_by=checked_by,
                next_check=datetime.now() + self.compliance_check_interval
            )
        
        # Simulate compliance check
        # In production, this would run actual checks against the system
        findings = []
        evidence = {}
        
        for requirement in policy.requirements:
            # Simulate check (in production, this would be real checks)
            # For now, we'll mark all as compliant
            pass
        
        status = ComplianceStatus.COMPLIANT if not findings else ComplianceStatus.PARTIAL
        
        check = ComplianceCheck(
            policy_id=policy_id,
            policy_name=policy.name,
            status=status,
            findings=findings,
            evidence=evidence,
            checked_at=datetime.now(),
            checked_by=checked_by,
            next_check=datetime.now() + self.compliance_check_interval
        )
        
        # Store check result
        if policy_id not in self.compliance_checks:
            self.compliance_checks[policy_id] = []
        
        self.compliance_checks[policy_id].append(check)
        
        # Keep only last 100 checks per policy
        if len(self.compliance_checks[policy_id]) > 100:
            self.compliance_checks[policy_id] = self.compliance_checks[policy_id][-100:]
        
        logger.info(f"Completed compliance check for policy {policy_id}: {status.value}")
        
        return check
    
    def get_compliance_status(self, standard: Optional[ComplianceStandard] = None) -> Dict[str, Any]:
        """Get overall compliance status"""
        if standard:
            policies = self.get_policies_by_standard(standard)
        else:
            policies = list(self.policies.values())
        
        total_policies = len(policies)
        compliant_policies = 0
        partial_policies = 0
        non_compliant_policies = 0
        
        for policy in policies:
            if not policy.enabled:
                continue
            
            checks = self.compliance_checks.get(policy.id, [])
            if not checks:
                continue
            
            latest_check = checks[-1]
            if latest_check.status == ComplianceStatus.COMPLIANT:
                compliant_policies += 1
            elif latest_check.status == ComplianceStatus.PARTIAL:
                partial_policies += 1
            else:
                non_compliant_policies += 1
        
        return {
            "standard": standard.value if standard else "all",
            "total_policies": total_policies,
            "compliant_policies": compliant_policies,
            "partial_policies": partial_policies,
            "non_compliant_policies": non_compliant_policies,
            "compliance_rate": (compliant_policies / total_policies * 100) if total_policies > 0 else 0
        }
    
    def purge_old_audit_logs(self, retention_days: Optional[int] = None):
        """Purge audit logs older than retention period"""
        retention = retention_days or self.audit_retention_days
        cutoff_date = datetime.now() - timedelta(days=retention)
        
        original_count = len(self.audit_logs)
        
        # Remove old logs
        self.audit_logs = deque(
            [log for log in self.audit_logs if log.timestamp >= cutoff_date],
            maxlen=100000
        )
        
        # Rebuild index
        self.audit_index.clear()
        for log in self.audit_logs:
            self.audit_index[log.tenant_id].add(log.id)
            self.audit_index[log.user_id].add(log.id)
            self.audit_index[log.resource_type].add(log.id)
        
        removed_count = original_count - len(self.audit_logs)
        logger.info(f"Purged {removed_count} old audit logs (older than {retention_days} days)")


# Global compliance manager instance
compliance_manager = ComplianceManager()