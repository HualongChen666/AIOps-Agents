# -*- coding: utf-8 -*-
"""
security_repository.py
-----------------------
Security数据仓储层

提供Security模块的数据库访问接口，实现所有Security相关模型的CRUD操作。
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from core.models import (
    SecurityKey,
    MfaMethod,
    AbacPolicy,
    RbacRole,
    RateLimitRule,
    HttpsCertificate,
    SnapshotEncryption,
    DataEncryptionKey,
    PrivacySubject,
    CompliancePolicy,
    ComplianceStandard,
    DatabaseSecurityInstance,
    ApiSecurityEndpoint,
    InputValidationRule,
    PenetrationTestProject,
    SecurityTest,
    VulnerabilityTicket,
    ThreatIntelligence,
    VulnerabilityScan,
    AuditReport,
    SecurityOperationRecord,
    CommandRewriteRule,
    CommandGuardRule,
)

logger = logging.getLogger(__name__)


class SecurityRepository:
    """Security数据仓储类"""

    def __init__(self, db: Session):
        self.db = db

    # ==================== Key Management ====================

    def create_key(
        self,
        name: str,
        key_type: str,
        algorithm: str = "RSA",
        key_size: int = 2048,
        encrypted_key_value: str = "",
        encrypted_key_iv: str = "",
        usage: Optional[List[str]] = None,
        expires_at: Optional[datetime] = None,
    ) -> SecurityKey:
        """创建密钥"""
        key = SecurityKey(
            id=str(uuid.uuid4()),
            name=name,
            key_type=key_type,
            algorithm=algorithm,
            key_size=key_size,
            encrypted_key_value=encrypted_key_value,
            encrypted_key_iv=encrypted_key_iv,
            status="active",
            auto_renew=False,
            created_at=datetime.now(),
            expires_at=expires_at or (datetime.now() + timedelta(days=365)),
            last_rotated_at=datetime.now(),
            usage=usage or [],
        )
        self.db.add(key)
        self.db.commit()
        self.db.refresh(key)
        logger.info(f"Created security key: {name}")
        return key

    def get_key(self, key_id: str) -> Optional[SecurityKey]:
        """获取密钥"""
        return self.db.query(SecurityKey).filter(SecurityKey.id == key_id).first()

    def get_keys(self, status: Optional[str] = None, limit: int = 100) -> List[SecurityKey]:
        """获取密钥列表"""
        query = self.db.query(SecurityKey)
        if status:
            query = query.filter(SecurityKey.status == status)
        return query.limit(limit).all()

    def update_key(
        self,
        key_id: str,
        status: Optional[str] = None,
        auto_renew: Optional[bool] = None,
    ) -> Optional[SecurityKey]:
        """更新密钥"""
        key = self.get_key(key_id)
        if not key:
            return None
        if status is not None:
            key.status = status
        if auto_renew is not None:
            key.auto_renew = auto_renew
        key.updated_at = datetime.now()
        self.db.commit()
        self.db.refresh(key)
        logger.info(f"Updated security key: {key_id}")
        return key

    def delete_key(self, key_id: str) -> bool:
        """删除密钥"""
        key = self.get_key(key_id)
        if not key:
            return False
        self.db.delete(key)
        self.db.commit()
        logger.info(f"Deleted security key: {key_id}")
        return True

    # ==================== MFA Methods ====================

    def create_mfa_method(
        self,
        method_type: str,
        name: str,
        description: str = "",
        config: Optional[Dict[str, Any]] = None,
        secret: Optional[str] = None,
        priority: int = 1,
    ) -> MfaMethod:
        """创建MFA方法"""
        method = MfaMethod(
            id=str(uuid.uuid4()),
            method_type=method_type,
            name=name,
            description=description,
            config=config or {},
            secret=secret,
            enabled=True,
            required=False,
            priority=priority,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        self.db.add(method)
        self.db.commit()
        self.db.refresh(method)
        logger.info(f"Created MFA method: {name}")
        return method

    def get_mfa_method(self, method_id: str) -> Optional[MfaMethod]:
        """获取MFA方法"""
        return self.db.query(MfaMethod).filter(MfaMethod.id == method_id).first()

    def get_mfa_methods(self, enabled: Optional[bool] = None) -> List[MfaMethod]:
        """获取MFA方法列表"""
        query = self.db.query(MfaMethod)
        if enabled is not None:
            query = query.filter(MfaMethod.enabled == enabled)
        return query.all()

    def update_mfa_method(
        self,
        method_id: str,
        enabled: Optional[bool] = None,
        required: Optional[bool] = None,
    ) -> Optional[MfaMethod]:
        """更新MFA方法"""
        method = self.get_mfa_method(method_id)
        if not method:
            return None
        if enabled is not None:
            method.enabled = enabled
        if required is not None:
            method.required = required
        method.updated_at = datetime.now()
        self.db.commit()
        self.db.refresh(method)
        logger.info(f"Updated MFA method: {method_id}")
        return method

    def delete_mfa_method(self, method_id: str) -> bool:
        """删除MFA方法"""
        method = self.get_mfa_method(method_id)
        if not method:
            return False
        self.db.delete(method)
        self.db.commit()
        logger.info(f"Deleted MFA method: {method_id}")
        return True

    # ==================== ABAC Policies ====================

    def create_abac_policy(
        self,
        name: str,
        effect: str = "allow",
        subjects: Optional[List[str]] = None,
        resources: Optional[List[str]] = None,
        actions: Optional[List[str]] = None,
        environment: Optional[Dict[str, Any]] = None,
    ) -> AbacPolicy:
        """创建ABAC策略"""
        policy = AbacPolicy(
            id=str(uuid.uuid4()),
            name=name,
            effect=effect,
            subjects=subjects,
            resources=resources,
            actions=actions,
            environment=environment,
            enabled=True,
            priority=0,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        self.db.add(policy)
        self.db.commit()
        self.db.refresh(policy)
        logger.info(f"Created ABAC policy: {name}")
        return policy

    def get_abac_policy(self, policy_id: str) -> Optional[AbacPolicy]:
        """获取ABAC策略"""
        return self.db.query(AbacPolicy).filter(AbacPolicy.id == policy_id).first()

    def get_abac_policies(self, enabled: Optional[bool] = None) -> List[AbacPolicy]:
        """获取ABAC策略列表"""
        query = self.db.query(AbacPolicy)
        if enabled is not None:
            query = query.filter(AbacPolicy.enabled == enabled)
        return query.all()

    def update_abac_policy(
        self,
        policy_id: str,
        enabled: Optional[bool] = None,
    ) -> Optional[AbacPolicy]:
        """更新ABAC策略"""
        policy = self.get_abac_policy(policy_id)
        if not policy:
            return None
        if enabled is not None:
            policy.enabled = enabled
        policy.updated_at = datetime.now()
        self.db.commit()
        self.db.refresh(policy)
        logger.info(f"Updated ABAC policy: {policy_id}")
        return policy

    def delete_abac_policy(self, policy_id: str) -> bool:
        """删除ABAC策略"""
        policy = self.get_abac_policy(policy_id)
        if not policy:
            return False
        self.db.delete(policy)
        self.db.commit()
        logger.info(f"Deleted ABAC policy: {policy_id}")
        return True

    # ==================== RBAC Roles ====================

    def create_rbac_role(
        self,
        name: str,
        description: str = "",
        permissions: Optional[List[str]] = None,
    ) -> RbacRole:
        """创建RBAC角色"""
        role = RbacRole(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            permissions=permissions or [],
            status="active",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        self.db.add(role)
        self.db.commit()
        self.db.refresh(role)
        logger.info(f"Created RBAC role: {name}")
        return role

    def get_rbac_role(self, role_id: str) -> Optional[RbacRole]:
        """获取RBAC角色"""
        return self.db.query(RbacRole).filter(RbacRole.id == role_id).first()

    def get_rbac_roles(self, status: Optional[str] = None) -> List[RbacRole]:
        """获取RBAC角色列表"""
        query = self.db.query(RbacRole)
        if status:
            query = query.filter(RbacRole.status == status)
        return query.all()

    def update_rbac_role(
        self,
        role_id: str,
        status: Optional[str] = None,
    ) -> Optional[RbacRole]:
        """更新RBAC角色"""
        role = self.get_rbac_role(role_id)
        if not role:
            return None
        if status is not None:
            role.status = status
        role.updated_at = datetime.now()
        self.db.commit()
        self.db.refresh(role)
        logger.info(f"Updated RBAC role: {role_id}")
        return role

    def delete_rbac_role(self, role_id: str) -> bool:
        """删除RBAC角色"""
        role = self.get_rbac_role(role_id)
        if not role:
            return False
        self.db.delete(role)
        self.db.commit()
        logger.info(f"Deleted RBAC role: {role_id}")
        return True

    # ==================== Rate Limit Rules ====================

    def create_rate_limit_rule(
        self,
        name: str,
        endpoint: str,
        limit: int,
        window_seconds: int = 60,
        strategy: str = "fixed_window",
    ) -> RateLimitRule:
        """创建速率限制规则"""
        rule = RateLimitRule(
            id=str(uuid.uuid4()),
            name=name,
            endpoint=endpoint,
            limit=limit,
            window_seconds=window_seconds,
            strategy=strategy,
            enabled=True,
            priority=0,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        self.db.add(rule)
        self.db.commit()
        self.db.refresh(rule)
        logger.info(f"Created rate limit rule: {name}")
        return rule

    def get_rate_limit_rule(self, rule_id: str) -> Optional[RateLimitRule]:
        """获取速率限制规则"""
        return self.db.query(RateLimitRule).filter(RateLimitRule.id == rule_id).first()

    def get_rate_limit_rules(self, enabled: Optional[bool] = None) -> List[RateLimitRule]:
        """获取速率限制规则列表"""
        query = self.db.query(RateLimitRule)
        if enabled is not None:
            query = query.filter(RateLimitRule.enabled == enabled)
        return query.all()

    def update_rate_limit_rule(
        self,
        rule_id: str,
        enabled: Optional[bool] = None,
    ) -> Optional[RateLimitRule]:
        """更新速率限制规则"""
        rule = self.get_rate_limit_rule(rule_id)
        if not rule:
            return None
        if enabled is not None:
            rule.enabled = enabled
        rule.updated_at = datetime.now()
        self.db.commit()
        self.db.refresh(rule)
        logger.info(f"Updated rate limit rule: {rule_id}")
        return rule

    def delete_rate_limit_rule(self, rule_id: str) -> bool:
        """删除速率限制规则"""
        rule = self.get_rate_limit_rule(rule_id)
        if not rule:
            return False
        self.db.delete(rule)
        self.db.commit()
        logger.info(f"Deleted rate limit rule: {rule_id}")
        return True

    # ==================== HTTPS Certificates ====================

    def create_https_certificate(
        self,
        domain: str,
        certificate_pem: str,
        private_key_encrypted: str,
        private_key_iv: str,
        algorithm: str = "RSA",
        issued_at: Optional[datetime] = None,
        expires_at: Optional[datetime] = None,
    ) -> HttpsCertificate:
        """创建HTTPS证书"""
        cert = HttpsCertificate(
            id=str(uuid.uuid4()),
            domain=domain,
            certificate_pem=certificate_pem,
            private_key_encrypted=private_key_encrypted,
            private_key_iv=private_key_iv,
            algorithm=algorithm,
            issued_at=issued_at or datetime.now(),
            expires_at=expires_at or (datetime.now() + timedelta(days=365)),
            status="valid",
            auto_renew=False,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        self.db.add(cert)
        self.db.commit()
        self.db.refresh(cert)
        logger.info(f"Created HTTPS certificate: {domain}")
        return cert

    def get_https_certificate(self, cert_id: str) -> Optional[HttpsCertificate]:
        """获取HTTPS证书"""
        return self.db.query(HttpsCertificate).filter(HttpsCertificate.id == cert_id).first()

    def get_https_certificates(self, status: Optional[str] = None) -> List[HttpsCertificate]:
        """获取HTTPS证书列表"""
        query = self.db.query(HttpsCertificate)
        if status:
            query = query.filter(HttpsCertificate.status == status)
        return query.all()

    def update_https_certificate(
        self,
        cert_id: str,
        auto_renew: Optional[bool] = None,
    ) -> Optional[HttpsCertificate]:
        """更新HTTPS证书"""
        cert = self.get_https_certificate(cert_id)
        if not cert:
            return None
        if auto_renew is not None:
            cert.auto_renew = auto_renew
        cert.updated_at = datetime.now()
        self.db.commit()
        self.db.refresh(cert)
        logger.info(f"Updated HTTPS certificate: {cert_id}")
        return cert

    # ==================== Snapshot Encryption ====================

    def create_snapshot_encryption(
        self,
        name: str,
        source: str,
        pre_state_encrypted: str,
        pre_state_iv: str,
        encryption_algorithm: str = "AES-256",
        retention_days: int = 7,
    ) -> SnapshotEncryption:
        """创建快照加密"""
        snapshot = SnapshotEncryption(
            id=str(uuid.uuid4()),
            name=name,
            source=source,
            encryption_algorithm=encryption_algorithm,
            pre_state_encrypted=pre_state_encrypted,
            pre_state_iv=pre_state_iv,
            status="active",
            retention_days=retention_days,
            expires_at=datetime.now() + timedelta(days=retention_days),
            created_at=datetime.now(),
        )
        self.db.add(snapshot)
        self.db.commit()
        self.db.refresh(snapshot)
        logger.info(f"Created snapshot encryption: {name}")
        return snapshot

    def get_snapshot_encryption(self, snapshot_id: str) -> Optional[SnapshotEncryption]:
        """获取快照加密"""
        return self.db.query(SnapshotEncryption).filter(SnapshotEncryption.id == snapshot_id).first()

    def get_snapshot_encryptions(self, status: Optional[str] = None) -> List[SnapshotEncryption]:
        """获取快照加密列表"""
        query = self.db.query(SnapshotEncryption)
        if status:
            query = query.filter(SnapshotEncryption.status == status)
        return query.all()

    def update_snapshot_encryption(
        self,
        snapshot_id: str,
        status: Optional[str] = None,
    ) -> Optional[SnapshotEncryption]:
        """更新快照加密"""
        snapshot = self.get_snapshot_encryption(snapshot_id)
        if not snapshot:
            return None
        if status is not None:
            snapshot.status = status
        self.db.commit()
        self.db.refresh(snapshot)
        logger.info(f"Updated snapshot encryption: {snapshot_id}")
        return snapshot

    # ==================== Data Encryption Keys ====================

    def create_data_encryption_key(
        self,
        name: str,
        key_encrypted: str,
        key_iv: str,
        purpose: str,
        algorithm: str = "AES-256",
        key_size: int = 256,
        scope: Optional[str] = None,
    ) -> DataEncryptionKey:
        """创建数据加密密钥"""
        key = DataEncryptionKey(
            id=str(uuid.uuid4()),
            name=name,
            key_encrypted=key_encrypted,
            key_iv=key_iv,
            algorithm=algorithm,
            key_size=key_size,
            purpose=purpose,
            scope=scope,
            status="active",
            rotation_enabled=False,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        self.db.add(key)
        self.db.commit()
        self.db.refresh(key)
        logger.info(f"Created data encryption key: {name}")
        return key

    def get_data_encryption_key(self, key_id: str) -> Optional[DataEncryptionKey]:
        """获取数据加密密钥"""
        return self.db.query(DataEncryptionKey).filter(DataEncryptionKey.id == key_id).first()

    def get_data_encryption_keys(self, status: Optional[str] = None) -> List[DataEncryptionKey]:
        """获取数据加密密钥列表"""
        query = self.db.query(DataEncryptionKey)
        if status:
            query = query.filter(DataEncryptionKey.status == status)
        return query.all()

    def update_data_encryption_key(
        self,
        key_id: str,
        status: Optional[str] = None,
    ) -> Optional[DataEncryptionKey]:
        """更新数据加密密钥"""
        key = self.get_data_encryption_key(key_id)
        if not key:
            return None
        if status is not None:
            key.status = status
        key.updated_at = datetime.now()
        self.db.commit()
        self.db.refresh(key)
        logger.info(f"Updated data encryption key: {key_id}")
        return key

    # ==================== Privacy Subjects ====================

    def create_privacy_subject(
        self,
        name: str,
        subject_type: str,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        identifier: Optional[str] = None,
        consent_level: str = "partial",
    ) -> PrivacySubject:
        """创建隐私主体"""
        subject = PrivacySubject(
            id=str(uuid.uuid4()),
            name=name,
            subject_type=subject_type,
            email=email,
            phone=phone,
            identifier=identifier,
            consent_level=consent_level,
            consent_given_at=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        self.db.add(subject)
        self.db.commit()
        self.db.refresh(subject)
        logger.info(f"Created privacy subject: {name}")
        return subject

    def get_privacy_subject(self, subject_id: str) -> Optional[PrivacySubject]:
        """获取隐私主体"""
        return self.db.query(PrivacySubject).filter(PrivacySubject.id == subject_id).first()

    def get_privacy_subjects(self, subject_type: Optional[str] = None) -> List[PrivacySubject]:
        """获取隐私主体列表"""
        query = self.db.query(PrivacySubject)
        if subject_type:
            query = query.filter(PrivacySubject.subject_type == subject_type)
        return query.all()

    def update_privacy_subject(
        self,
        subject_id: str,
        consent_level: Optional[str] = None,
    ) -> Optional[PrivacySubject]:
        """更新隐私主体"""
        subject = self.get_privacy_subject(subject_id)
        if not subject:
            return None
        if consent_level is not None:
            subject.consent_level = consent_level
            subject.consent_updated_at = datetime.now()
        subject.updated_at = datetime.now()
        self.db.commit()
        self.db.refresh(subject)
        logger.info(f"Updated privacy subject: {subject_id}")
        return subject

    # ==================== Compliance Policies ====================

    def create_compliance_policy(
        self,
        name: str,
        framework: str,
        description: str,
        requirements: List[str],
    ) -> CompliancePolicy:
        """创建合规策略"""
        policy = CompliancePolicy(
            id=str(uuid.uuid4()),
            name=name,
            framework=framework,
            description=description,
            requirements=requirements,
            status="active",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        self.db.add(policy)
        self.db.commit()
        self.db.refresh(policy)
        logger.info(f"Created compliance policy: {name}")
        return policy

    def get_compliance_policy(self, policy_id: str) -> Optional[CompliancePolicy]:
        """获取合规策略"""
        return self.db.query(CompliancePolicy).filter(CompliancePolicy.id == policy_id).first()

    def get_compliance_policies(self, framework: Optional[str] = None) -> List[CompliancePolicy]:
        """获取合规策略列表"""
        query = self.db.query(CompliancePolicy)
        if framework:
            query = query.filter(CompliancePolicy.framework == framework)
        return query.all()

    def update_compliance_policy(
        self,
        policy_id: str,
        status: Optional[str] = None,
    ) -> Optional[CompliancePolicy]:
        """更新合规策略"""
        policy = self.get_compliance_policy(policy_id)
        if not policy:
            return None
        if status is not None:
            policy.status = status
        policy.updated_at = datetime.now()
        self.db.commit()
        self.db.refresh(policy)
        logger.info(f"Updated compliance policy: {policy_id}")
        return policy

    # ==================== Compliance Standards ====================

    def create_compliance_standard(
        self,
        name: str,
        category: str = "general",
        description: str = "",
        check_criteria: Optional[Dict[str, Any]] = None,
        severity: str = "medium",
    ) -> ComplianceStandard:
        """创建合规标准"""
        standard = ComplianceStandard(
            id=str(uuid.uuid4()),
            name=name,
            category=category,
            description=description,
            check_criteria=check_criteria or {},
            severity=severity,
            status="active",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        self.db.add(standard)
        self.db.commit()
        self.db.refresh(standard)
        logger.info(f"Created compliance standard: {name}")
        return standard

    def get_compliance_standard(self, standard_id: str) -> Optional[ComplianceStandard]:
        """获取合规标准"""
        return self.db.query(ComplianceStandard).filter(ComplianceStandard.id == standard_id).first()

    def get_compliance_standards(self, category: Optional[str] = None) -> List[ComplianceStandard]:
        """获取合规标准列表"""
        query = self.db.query(ComplianceStandard)
        if category:
            query = query.filter(ComplianceStandard.category == category)
        return query.all()

    def update_compliance_standard(
        self,
        standard_id: str,
        status: Optional[str] = None,
    ) -> Optional[ComplianceStandard]:
        """更新合规标准"""
        standard = self.get_compliance_standard(standard_id)
        if not standard:
            return None
        if status is not None:
            standard.status = status
        standard.updated_at = datetime.now()
        self.db.commit()
        self.db.refresh(standard)
        logger.info(f"Updated compliance standard: {standard_id}")
        return standard

    # ==================== Database Security Instances ====================

    def create_database_security_instance(
        self,
        name: str,
        instance_type: str,
        host: str,
        port: Optional[int] = None,
    ) -> DatabaseSecurityInstance:
        """创建数据库安全实例"""
        instance = DatabaseSecurityInstance(
            id=str(uuid.uuid4()),
            name=name,
            instance_type=instance_type,
            host=host,
            port=port,
            encryption_enabled=False,
            ssl_enabled=False,
            audit_enabled=False,
            status="active",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        self.db.add(instance)
        self.db.commit()
        self.db.refresh(instance)
        logger.info(f"Created database security instance: {name}")
        return instance

    def get_database_security_instance(self, instance_id: str) -> Optional[DatabaseSecurityInstance]:
        """获取数据库安全实例"""
        return self.db.query(DatabaseSecurityInstance).filter(DatabaseSecurityInstance.id == instance_id).first()

    def get_database_security_instances(self, status: Optional[str] = None) -> List[DatabaseSecurityInstance]:
        """获取数据库安全实例列表"""
        query = self.db.query(DatabaseSecurityInstance)
        if status:
            query = query.filter(DatabaseSecurityInstance.status == status)
        return query.all()

    def update_database_security_instance(
        self,
        instance_id: str,
        status: Optional[str] = None,
    ) -> Optional[DatabaseSecurityInstance]:
        """更新数据库安全实例"""
        instance = self.get_database_security_instance(instance_id)
        if not instance:
            return None
        if status is not None:
            instance.status = status
        instance.updated_at = datetime.now()
        self.db.commit()
        self.db.refresh(instance)
        logger.info(f"Updated database security instance: {instance_id}")
        return instance

    # ==================== API Security Endpoints ====================

    def create_api_security_endpoint(
        self,
        path: str,
        method: str,
        authentication_required: bool = True,
        authorization_required: bool = True,
    ) -> ApiSecurityEndpoint:
        """创建API安全端点"""
        endpoint = ApiSecurityEndpoint(
            id=str(uuid.uuid4()),
            path=path,
            method=method,
            authentication_required=authentication_required,
            authorization_required=authorization_required,
            rate_limit_enabled=True,
            status="active",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        self.db.add(endpoint)
        self.db.commit()
        self.db.refresh(endpoint)
        logger.info(f"Created API security endpoint: {method} {path}")
        return endpoint

    def get_api_security_endpoint(self, endpoint_id: str) -> Optional[ApiSecurityEndpoint]:
        """获取API安全端点"""
        return self.db.query(ApiSecurityEndpoint).filter(ApiSecurityEndpoint.id == endpoint_id).first()

    def get_api_security_endpoints(self, status: Optional[str] = None) -> List[ApiSecurityEndpoint]:
        """获取API安全端点列表"""
        query = self.db.query(ApiSecurityEndpoint)
        if status:
            query = query.filter(ApiSecurityEndpoint.status == status)
        return query.all()

    def update_api_security_endpoint(
        self,
        endpoint_id: str,
        status: Optional[str] = None,
    ) -> Optional[ApiSecurityEndpoint]:
        """更新API安全端点"""
        endpoint = self.get_api_security_endpoint(endpoint_id)
        if not endpoint:
            return None
        if status is not None:
            endpoint.status = status
        endpoint.updated_at = datetime.now()
        self.db.commit()
        self.db.refresh(endpoint)
        logger.info(f"Updated API security endpoint: {endpoint_id}")
        return endpoint

    def delete_api_security_endpoint(self, endpoint_id: str) -> bool:
        """删除API安全端点"""
        endpoint = self.get_api_security_endpoint(endpoint_id)
        if not endpoint:
            return False
        self.db.delete(endpoint)
        self.db.commit()
        logger.info(f"Deleted API security endpoint: {endpoint_id}")
        return True

    # ==================== Input Validation Rules ====================

    def create_input_validation_rule(
        self,
        name: str,
        field: str,
        validation_type: str,
        validation_pattern: Optional[str] = None,
    ) -> InputValidationRule:
        """创建输入验证规则"""
        rule = InputValidationRule(
            id=str(uuid.uuid4()),
            name=name,
            field=field,
            validation_type=validation_type,
            validation_pattern=validation_pattern,
            enabled=True,
            priority=0,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        self.db.add(rule)
        self.db.commit()
        self.db.refresh(rule)
        logger.info(f"Created input validation rule: {name}")
        return rule

    def get_input_validation_rule(self, rule_id: str) -> Optional[InputValidationRule]:
        """获取输入验证规则"""
        return self.db.query(InputValidationRule).filter(InputValidationRule.id == rule_id).first()

    def get_input_validation_rules(self, enabled: Optional[bool] = None) -> List[InputValidationRule]:
        """获取输入验证规则列表"""
        query = self.db.query(InputValidationRule)
        if enabled is not None:
            query = query.filter(InputValidationRule.enabled == enabled)
        return query.all()

    def update_input_validation_rule(
        self,
        rule_id: str,
        enabled: Optional[bool] = None,
    ) -> Optional[InputValidationRule]:
        """更新输入验证规则"""
        rule = self.get_input_validation_rule(rule_id)
        if not rule:
            return None
        if enabled is not None:
            rule.enabled = enabled
        rule.updated_at = datetime.now()
        self.db.commit()
        self.db.refresh(rule)
        logger.info(f"Updated input validation rule: {rule_id}")
        return rule

    def delete_input_validation_rule(self, rule_id: str) -> bool:
        """删除输入验证规则"""
        rule = self.get_input_validation_rule(rule_id)
        if not rule:
            return False
        self.db.delete(rule)
        self.db.commit()
        logger.info(f"Deleted input validation rule: {rule_id}")
        return True

    # ==================== Penetration Test Projects ====================

    def create_penetration_test_project(
        self,
        name: str,
        target: str,
        test_type: str = "black_box",
    ) -> PenetrationTestProject:
        """创建渗透测试项目"""
        project = PenetrationTestProject(
            id=str(uuid.uuid4()),
            name=name,
            target=target,
            test_type=test_type,
            status="scheduled",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        self.db.add(project)
        self.db.commit()
        self.db.refresh(project)
        logger.info(f"Created penetration test project: {name}")
        return project

    def get_penetration_test_project(self, project_id: str) -> Optional[PenetrationTestProject]:
        """获取渗透测试项目"""
        return self.db.query(PenetrationTestProject).filter(PenetrationTestProject.id == project_id).first()

    def get_penetration_test_projects(self, status: Optional[str] = None) -> List[PenetrationTestProject]:
        """获取渗透测试项目列表"""
        query = self.db.query(PenetrationTestProject)
        if status:
            query = query.filter(PenetrationTestProject.status == status)
        return query.all()

    def update_penetration_test_project(
        self,
        project_id: str,
        status: Optional[str] = None,
    ) -> Optional[PenetrationTestProject]:
        """更新渗透测试项目"""
        project = self.get_penetration_test_project(project_id)
        if not project:
            return None
        if status is not None:
            project.status = status
        project.updated_at = datetime.now()
        self.db.commit()
        self.db.refresh(project)
        logger.info(f"Updated penetration test project: {project_id}")
        return project

    # ==================== Security Tests ====================

    def create_security_test(
        self,
        name: str,
        test_type: str,
        target: Optional[str] = None,
    ) -> SecurityTest:
        """创建安全测试"""
        test = SecurityTest(
            id=str(uuid.uuid4()),
            name=name,
            test_type=test_type,
            target=target,
            status="pending",
            created_at=datetime.now(),
        )
        self.db.add(test)
        self.db.commit()
        self.db.refresh(test)
        logger.info(f"Created security test: {name}")
        return test

    def get_security_test(self, test_id: str) -> Optional[SecurityTest]:
        """获取安全测试"""
        return self.db.query(SecurityTest).filter(SecurityTest.id == test_id).first()

    def get_security_tests(self, status: Optional[str] = None) -> List[SecurityTest]:
        """获取安全测试列表"""
        query = self.db.query(SecurityTest)
        if status:
            query = query.filter(SecurityTest.status == status)
        return query.all()

    def update_security_test(
        self,
        test_id: str,
        status: Optional[str] = None,
    ) -> Optional[SecurityTest]:
        """更新安全测试"""
        test = self.get_security_test(test_id)
        if not test:
            return None
        if status is not None:
            test.status = status
        self.db.commit()
        self.db.refresh(test)
        logger.info(f"Updated security test: {test_id}")
        return test

    # ==================== Vulnerability Tickets ====================

    def create_vulnerability_ticket(
        self,
        title: str,
        severity: str,
        description: str,
        cve_id: Optional[str] = None,
    ) -> VulnerabilityTicket:
        """创建漏洞工单"""
        ticket = VulnerabilityTicket(
            id=str(uuid.uuid4()),
            title=title,
            severity=severity,
            description=description,
            cve_id=cve_id,
            status="open",
            detected_at=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        self.db.add(ticket)
        self.db.commit()
        self.db.refresh(ticket)
        logger.info(f"Created vulnerability ticket: {title}")
        return ticket

    def get_vulnerability_ticket(self, ticket_id: str) -> Optional[VulnerabilityTicket]:
        """获取漏洞工单"""
        return self.db.query(VulnerabilityTicket).filter(VulnerabilityTicket.id == ticket_id).first()

    def get_vulnerability_tickets(self, status: Optional[str] = None) -> List[VulnerabilityTicket]:
        """获取漏洞工单列表"""
        query = self.db.query(VulnerabilityTicket)
        if status:
            query = query.filter(VulnerabilityTicket.status == status)
        return query.all()

    def update_vulnerability_ticket(
        self,
        ticket_id: str,
        status: Optional[str] = None,
    ) -> Optional[VulnerabilityTicket]:
        """更新漏洞工单"""
        ticket = self.get_vulnerability_ticket(ticket_id)
        if not ticket:
            return None
        if status is not None:
            ticket.status = status
        ticket.updated_at = datetime.now()
        self.db.commit()
        self.db.refresh(ticket)
        logger.info(f"Updated vulnerability ticket: {ticket_id}")
        return ticket

    # ==================== Threat Intelligence ====================

    def create_threat_intelligence(
        self,
        name: str,
        threat_type: str,
        description: str,
        severity: str = "medium",
        confidence: float = 0.5,
    ) -> ThreatIntelligence:
        """创建威胁情报"""
        threat = ThreatIntelligence(
            id=str(uuid.uuid4()),
            name=name,
            threat_type=threat_type,
            description=description,
            severity=severity,
            confidence=confidence,
            status="active",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        self.db.add(threat)
        self.db.commit()
        self.db.refresh(threat)
        logger.info(f"Created threat intelligence: {name}")
        return threat

    def get_threat_intelligence(self, threat_id: str) -> Optional[ThreatIntelligence]:
        """获取威胁情报"""
        return self.db.query(ThreatIntelligence).filter(ThreatIntelligence.id == threat_id).first()

    def get_threat_intelligences(self, status: Optional[str] = None) -> List[ThreatIntelligence]:
        """获取威胁情报列表"""
        query = self.db.query(ThreatIntelligence)
        if status:
            query = query.filter(ThreatIntelligence.status == status)
        return query.all()

    # ==================== Vulnerability Scans ====================

    def create_vulnerability_scan(
        self,
        target: str,
        scan_type: str = "full",
    ) -> VulnerabilityScan:
        """创建漏洞扫描"""
        scan = VulnerabilityScan(
            id=str(uuid.uuid4()),
            target=target,
            scan_type=scan_type,
            status="pending",
            created_at=datetime.now(),
        )
        self.db.add(scan)
        self.db.commit()
        self.db.refresh(scan)
        logger.info(f"Created vulnerability scan: {target}")
        return scan

    def get_vulnerability_scan(self, scan_id: str) -> Optional[VulnerabilityScan]:
        """获取漏洞扫描"""
        return self.db.query(VulnerabilityScan).filter(VulnerabilityScan.id == scan_id).first()

    def get_vulnerability_scans(self, status: Optional[str] = None) -> List[VulnerabilityScan]:
        """获取漏洞扫描列表"""
        query = self.db.query(VulnerabilityScan)
        if status:
            query = query.filter(VulnerabilityScan.status == status)
        return query.all()

    def update_vulnerability_scan(
        self,
        scan_id: str,
        status: Optional[str] = None,
    ) -> Optional[VulnerabilityScan]:
        """更新漏洞扫描"""
        scan = self.get_vulnerability_scan(scan_id)
        if not scan:
            return None
        if status is not None:
            scan.status = status
        self.db.commit()
        self.db.refresh(scan)
        logger.info(f"Updated vulnerability scan: {scan_id}")
        return scan

    # ==================== Audit Reports ====================

    def create_audit_report(
        self,
        title: str,
        report_type: str,
        description: Optional[str] = None,
    ) -> AuditReport:
        """创建审计报告"""
        report = AuditReport(
            id=str(uuid.uuid4()),
            title=title,
            report_type=report_type,
            description=description,
            status="draft",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        self.db.add(report)
        self.db.commit()
        self.db.refresh(report)
        logger.info(f"Created audit report: {title}")
        return report

    def get_audit_report(self, report_id: str) -> Optional[AuditReport]:
        """获取审计报告"""
        return self.db.query(AuditReport).filter(AuditReport.id == report_id).first()

    def get_audit_reports(self, status: Optional[str] = None) -> List[AuditReport]:
        """获取审计报告列表"""
        query = self.db.query(AuditReport)
        if status:
            query = query.filter(AuditReport.status == status)
        return query.all()

    def update_audit_report(
        self,
        report_id: str,
        status: Optional[str] = None,
    ) -> Optional[AuditReport]:
        """更新审计报告"""
        report = self.get_audit_report(report_id)
        if not report:
            return None
        if status is not None:
            report.status = status
            if status == "published":
                report.published_at = datetime.now()
        report.updated_at = datetime.now()
        self.db.commit()
        self.db.refresh(report)
        logger.info(f"Updated audit report: {report_id}")
        return report

    # ==================== Security Operation Records ====================

    def create_security_operation_record(
        self,
        operation: str,
        operation_type: str,
        result: str,
        executor: Optional[str] = None,
        target_resource: Optional[str] = None,
    ) -> SecurityOperationRecord:
        """创建安全操作记录"""
        record = SecurityOperationRecord(
            id=str(uuid.uuid4()),
            operation=operation,
            operation_type=operation_type,
            target_resource=target_resource,
            executor=executor,
            result=result,
            timestamp=datetime.now(),
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        logger.info(f"Created security operation record: {operation}")
        return record

    def get_security_operation_records(self, limit: int = 50) -> List[SecurityOperationRecord]:
        """获取安全操作记录列表"""
        return self.db.query(SecurityOperationRecord).order_by(
            SecurityOperationRecord.timestamp.desc()
        ).limit(limit).all()

    # ==================== Command Rewrite Rules ====================

    def create_command_rewrite_rule(
        self,
        pattern: str,
        replacement: str,
        description: Optional[str] = None,
    ) -> CommandRewriteRule:
        """创建命令改写规则"""
        rule = CommandRewriteRule(
            id=str(uuid.uuid4()),
            pattern=pattern,
            replacement=replacement,
            description=description,
            enabled=True,
            priority=0,
            usage_count=0,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        self.db.add(rule)
        self.db.commit()
        self.db.refresh(rule)
        logger.info(f"Created command rewrite rule: {pattern}")
        return rule

    def get_command_rewrite_rule(self, rule_id: str) -> Optional[CommandRewriteRule]:
        """获取命令改写规则"""
        return self.db.query(CommandRewriteRule).filter(CommandRewriteRule.id == rule_id).first()

    def get_command_rewrite_rules(self, enabled: Optional[bool] = None) -> List[CommandRewriteRule]:
        """获取命令改写规则列表"""
        query = self.db.query(CommandRewriteRule)
        if enabled is not None:
            query = query.filter(CommandRewriteRule.enabled == enabled)
        return query.all()

    def update_command_rewrite_rule(
        self,
        rule_id: str,
        enabled: Optional[bool] = None,
    ) -> Optional[CommandRewriteRule]:
        """更新命令改写规则"""
        rule = self.get_command_rewrite_rule(rule_id)
        if not rule:
            return None
        if enabled is not None:
            rule.enabled = enabled
        rule.updated_at = datetime.now()
        self.db.commit()
        self.db.refresh(rule)
        logger.info(f"Updated command rewrite rule: {rule_id}")
        return rule

    def delete_command_rewrite_rule(self, rule_id: str) -> bool:
        """删除命令改写规则"""
        rule = self.get_command_rewrite_rule(rule_id)
        if not rule:
            return False
        self.db.delete(rule)
        self.db.commit()
        logger.info(f"Deleted command rewrite rule: {rule_id}")
        return True

    # ==================== Command Guard Rules ====================

    def create_command_guard_rule(
        self,
        command: str,
        pattern: str,
        severity: str = "high",
        action: str = "block",
        description: Optional[str] = None,
    ) -> CommandGuardRule:
        """创建命令管控规则"""
        rule = CommandGuardRule(
            id=str(uuid.uuid4()),
            command=command,
            pattern=pattern,
            severity=severity,
            action=action,
            description=description,
            enabled=True,
            trigger_count=0,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        self.db.add(rule)
        self.db.commit()
        self.db.refresh(rule)
        logger.info(f"Created command guard rule: {command}")
        return rule

    def get_command_guard_rule(self, rule_id: str) -> Optional[CommandGuardRule]:
        """获取命令管控规则"""
        return self.db.query(CommandGuardRule).filter(CommandGuardRule.id == rule_id).first()

    def get_command_guard_rules(self, enabled: Optional[bool] = None) -> List[CommandGuardRule]:
        """获取命令管控规则列表"""
        query = self.db.query(CommandGuardRule)
        if enabled is not None:
            query = query.filter(CommandGuardRule.enabled == enabled)
        return query.all()

    def update_command_guard_rule(
        self,
        rule_id: str,
        enabled: Optional[bool] = None,
    ) -> Optional[CommandGuardRule]:
        """更新命令管控规则"""
        rule = self.get_command_guard_rule(rule_id)
        if not rule:
            return None
        if enabled is not None:
            rule.enabled = enabled
        rule.updated_at = datetime.now()
        self.db.commit()
        self.db.refresh(rule)
        logger.info(f"Updated command guard rule: {rule_id}")
        return rule

    def delete_command_guard_rule(self, rule_id: str) -> bool:
        """删除命令管控规则"""
        rule = self.get_command_guard_rule(rule_id)
        if not rule:
            return False
        self.db.delete(rule)
        self.db.commit()
        logger.info(f"Deleted command guard rule: {rule_id}")
        return True
