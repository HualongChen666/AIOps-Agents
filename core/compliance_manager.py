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
    
    # ------------------------------------------------------------------
    # 合规要求 -> 真实证据探测
    # ------------------------------------------------------------------
    @staticmethod
    def _probe_role_based_access_control() -> tuple:
        try:
            from core.rbac import ROLE_PERMISSIONS

            roles = sorted(role.value for role in ROLE_PERMISSIONS)
            return bool(roles), {"roles": roles, "source": "core.rbac"}
        except Exception as e:  # noqa: BLE001
            return False, {"error": str(e)}

    @staticmethod
    def _probe_least_privilege_principle() -> tuple:
        try:
            from core.rbac import Permission, ROLE_PERMISSIONS, Role

            guest = ROLE_PERMISSIONS.get(Role.GUEST, set())
            ok = Permission.WRITE not in guest and Permission.DELETE not in guest
            return ok, {"guest_permissions": sorted(p.value for p in guest), "source": "core.rbac"}
        except Exception as e:  # noqa: BLE001
            return False, {"error": str(e)}

    @staticmethod
    def _probe_multi_factor_authentication() -> tuple:
        try:
            import config

            enabled = bool(getattr(config, "MFA_ENABLED", False))
        except Exception:  # noqa: BLE001
            enabled = False
        return enabled, {"mfa_enabled": enabled, "source": "config"}

    @staticmethod
    def _probe_data_encryption_at_rest() -> tuple:
        try:
            from core import crypto

            funcs = [fn for fn in ("derive_encryption_key", "encrypt", "encrypt_file") if hasattr(crypto, fn)]
            return bool(funcs), {"module": "core.crypto", "functions": funcs}
        except Exception as e:  # noqa: BLE001
            return False, {"error": str(e)}

    @staticmethod
    def _probe_encryption_key_management() -> tuple:
        try:
            from core import key_management

            funcs = [fn for fn in ("rotate", "rotate_key", "generate_key", "get_key") if hasattr(key_management, fn)]
            return bool(funcs), {"module": "core.key_management", "functions": funcs}
        except Exception as e:  # noqa: BLE001
            return False, {"error": str(e)}

    @staticmethod
    def _probe_key_rotation_policy() -> tuple:
        try:
            from core import key_management

            has_rotation = any(hasattr(key_management, fn) for fn in ("rotate", "rotate_key"))
            return has_rotation, {"module": "core.key_management", "rotation": has_rotation}
        except Exception as e:  # noqa: BLE001
            return False, {"error": str(e)}

    @staticmethod
    def _probe_secure_cryptographic_algorithms() -> tuple:
        try:
            from core.authentication import pwd_context

            schemes = pwd_context.schemes() if hasattr(pwd_context, "schemes") else []
            return "bcrypt" in schemes, {"password_schemes": schemes, "source": "core.authentication"}
        except Exception as e:  # noqa: BLE001
            return False, {"error": str(e)}

    @staticmethod
    def _probe_audit_trail_for_all_actions() -> tuple:
        try:
            from core import audit_service  # noqa: F401

            return True, {"module": "core.audit_service"}
        except Exception:
            try:
                from services import audit_service  # noqa: F401

                return True, {"module": "services.audit_service"}
            except Exception as e:  # noqa: BLE001
                return False, {"error": str(e)}

    @staticmethod
    def _probe_log_retention_policy() -> tuple:
        try:
            import config

            days = int(getattr(config, "AUDIT_RETENTION_DAYS", 0) or 0)
        except Exception:  # noqa: BLE001
            days = 0
        return days > 0, {"retention_days": days, "source": "config"}

    @staticmethod
    def _probe_incident_detection_mechanisms() -> tuple:
        try:
            from core import incident_manager  # noqa: F401

            return True, {"module": "core.incident_manager"}
        except Exception:
            try:
                from services import alert_service  # noqa: F401

                return True, {"module": "services.alert_service"}
            except Exception as e:  # noqa: BLE001
                return False, {"error": str(e)}

    @staticmethod
    def _probe_escalation_procedures() -> tuple:
        try:
            import importlib

            mod = importlib.import_module("services.alert_service.escalator")
            return hasattr(mod, "AlertEscalator"), {"module": "services.alert_service.escalator"}
        except Exception as e:  # noqa: BLE001
            return False, {"error": str(e)}

    @staticmethod
    def _probe_response_playbook() -> tuple:
        try:
            import importlib

            mod = importlib.import_module("services.repair_service.strategy_manager")
            strategies = getattr(mod, "BUILTIN_STRATEGIES", None)
            return True, {"module": "services.repair_service.strategy_manager", "strategies": len(strategies) if strategies else None}
        except Exception as e:  # noqa: BLE001
            return False, {"error": str(e)}

    _REQUIREMENT_PROBES = {
        "role_based_access_control": _probe_role_based_access_control,
        "least_privilege_principle": _probe_least_privilege_principle,
        "multi_factor_authentication": _probe_multi_factor_authentication,
        "data_encryption_at_rest": _probe_data_encryption_at_rest,
        "encryption_at_rest_and_transit": _probe_data_encryption_at_rest,
        "encryption_key_management": _probe_encryption_key_management,
        "key_rotation_policy": _probe_key_rotation_policy,
        "secure_cryptographic_algorithms": _probe_secure_cryptographic_algorithms,
        "audit_trail_for_all_actions": _probe_audit_trail_for_all_actions,
        "log_retention_policy": _probe_log_retention_policy,
        "incident_detection_mechanisms": _probe_incident_detection_mechanisms,
        "escalation_procedures": _probe_escalation_procedures,
        "response_playbook": _probe_response_playbook,
    }

    def _requirement_evidence(self, requirement: str) -> tuple:
        """Return ``(verified, evidence)`` for a control requirement.

        Evidence is gathered from real project state (module capabilities,
        configuration). Requirements without an automated evidence source are
        reported as not verified rather than assumed compliant.
        """
        probe = self._REQUIREMENT_PROBES.get(requirement)
        if probe is None:
            return False, {
                "verified": False,
                "reason": "no automated evidence source for this control",
            }
        try:
            return probe()
        except Exception as e:  # noqa: BLE001
            return False, {"verified": False, "error": str(e)}

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
        
        # 真实合规检查：对每条要求执行基于真实项目状态的证据探测。
        # 历史问题（已修复）：此处原为 `pass` 空循环，findings 恒空 → status 恒 COMPLIANT。
        findings = []
        evidence = {}

        for requirement in policy.requirements:
            verified, req_evidence = self._requirement_evidence(requirement)
            evidence[requirement] = req_evidence
            if not verified:
                findings.append(
                    f"Requirement not verified: {requirement} "
                    f"({req_evidence.get('reason') or req_evidence.get('error', 'no evidence')})"
                )

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
_compliance_manager_instance: Optional[ComplianceManager] = None


def get_compliance_manager() -> ComplianceManager:
    """
    Get the global compliance manager instance
    
    Returns:
        ComplianceManager: Global compliance manager instance
    """
    global _compliance_manager_instance
    if _compliance_manager_instance is None:
        _compliance_manager_instance = ComplianceManager()
    return _compliance_manager_instance


# 模块级别名必须与懒加载单例指向同一实例，否则两套全局实例状态互不可见
compliance_manager = get_compliance_manager()