# -*- coding: utf-8 -*-
"""
Enterprise Functionality Router
================================

API endpoints for enterprise-level features including:
- Multi-tenant isolation management
- Compliance checks and reporting
- Encryption and data protection
- Audit logging and querying
- Privacy and consent management
"""

import logging
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/enterprise", tags=["企业功能"])
try:
    from core.enterprise_functionality import (
        ComplianceStandard,
        DataClassification,
        enterprise_functionality_manager,
    )

    ENTERPRISE_AVAILABLE = True
except ImportError:
    ENTERPRISE_AVAILABLE = False
    logger.warning("Enterprise functionality manager not available")


class TenantIsolationRequest(BaseModel):
    """Request for tenant isolation check"""

    tenant_id: str
    resource_id: str
    resource_type: str

    model_config = {
        "extra": "ignore",
        "json_schema_extra": {
            "example": {
                "tenant_id": "example",
                "resource_id": "example",
                "resource_type": "example",
            }
        },
    }


class ComplianceCheckRequest(BaseModel):
    """Request for compliance check"""

    standard: str

    model_config = {"extra": "ignore", "json_schema_extra": {"example": {"standard": "example"}}}


class EncryptionRequest(BaseModel):
    """Request for data encryption"""

    data: str
    classification: str = "internal"

    model_config = {
        "extra": "ignore",
        "json_schema_extra": {"example": {"data": "example", "classification": "example"}},
    }


class AuditLogRequest(BaseModel):
    """Request for audit log creation"""

    tenant_id: str
    user_id: str
    action: str
    resource_type: str
    resource_id: str
    outcome: str
    ip_address: str = "unknown"
    user_agent: str = "unknown"
    metadata: Optional[dict[str, Any]] = None
    data_classification: str = "internal"

    model_config = {
        "extra": "ignore",
        "json_schema_extra": {
            "example": {
                "tenant_id": "example",
                "user_id": "example",
                "action": "example",
                "resource_type": "example",
                "resource_id": "example",
                "outcome": "example",
                "ip_address": "example",
                "user_agent": "example",
                "metadata": "example",
                "data_classification": "example",
            }
        },
    }


class ConsentRequest(BaseModel):
    """Request for consent management"""

    user_id: str
    consent_given: bool
    consent_purpose: str

    model_config = {
        "extra": "ignore",
        "json_schema_extra": {
            "example": {"user_id": "example", "consent_given": True, "consent_purpose": "example"}
        },
    }


@router.post(
    "/tenant/isolation/check",
    summary="检查租户隔离",
    responses={
        (200): {
            "description": "租户隔离检查结果",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "allowed": True,
                        "tenant_id": "tenant-001",
                        "resource_id": "resource-001",
                        "resource_type": "database",
                    }
                }
            },
        },
        (503): {"description": "企业功能管理器不可用"},
    },
)
async def check_tenant_isolation(request: TenantIsolationRequest) -> dict[str, Any]:
    """
    检查租户隔离状态，验证资源访问权限
    """
    if not ENTERPRISE_AVAILABLE:
        raise HTTPException(status_code=503, detail="企业功能管理器不可用")
    is_allowed: bool = enterprise_functionality_manager.enforce_tenant_isolation(
        request.tenant_id, request.resource_id, request.resource_type
    )
    return {
        "status": "success",
        "allowed": is_allowed,
        "tenant_id": request.tenant_id,
        "resource_id": request.resource_id,
        "resource_type": request.resource_type,
    }


@router.post(
    "/tenant/resource/assign",
    summary="分配资源到租户",
    responses={
        (200): {
            "description": "资源分配成功",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "message": "资源 resource-001 已分配到租户 tenant-001",
                    }
                }
            },
        },
        (503): {"description": "企业功能管理器不可用"},
    },
)
async def assign_resource_to_tenant(tenant_id: str, resource_id: str) -> dict[str, Any]:
    """
    将资源分配到指定租户，实现数据隔离
    """
    if not ENTERPRISE_AVAILABLE:
        raise HTTPException(status_code=503, detail="企业功能管理器不可用")
    enterprise_functionality_manager.assign_resource_to_tenant(tenant_id, resource_id)
    return {"status": "success", "message": f"资源 {resource_id} 已分配到租户 {tenant_id}"}


@router.post(
    "/compliance/check",
    summary="合规性检查",
    responses={
        (200): {
            "description": "合规性检查结果",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "compliance_check": {
                            "standard": "GDPR",
                            "check_id": "check-001",
                            "description": "GDPR合规检查",
                            "passed": True,
                            "findings": [],
                            "severity": "low",
                            "checked_at": "2026-07-02T10:30:00Z",
                        },
                    }
                }
            },
        },
        (400): {"description": "无效的合规标准"},
        (503): {"description": "企业功能管理器不可用"},
    },
)
async def run_compliance_check(request: ComplianceCheckRequest) -> dict[str, Any]:
    """
    执行指定标准的合规性检查
    """
    if not ENTERPRISE_AVAILABLE:
        raise HTTPException(status_code=503, detail="企业功能管理器不可用")
    try:
        standard: ComplianceStandard = ComplianceStandard(request.standard)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"无效的合规标准: {request.standard}")
    check = await enterprise_functionality_manager.run_compliance_check(standard)
    return {
        "status": "success",
        "compliance_check": {
            "standard": check.standard.value,
            "check_id": check.check_id,
            "description": check.description,
            "passed": check.passed,
            "findings": check.findings,
            "severity": check.severity,
            "checked_at": check.checked_at.isoformat(),
        },
    }


@router.post(
    "/compliance/report",
    summary="生成合规报告",
    responses={
        (200): {
            "description": "合规报告",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "compliance_report": {"standard": "GDPR", "summary": "合规", "details": {}},
                    }
                }
            },
        },
        (400): {"description": "无效的合规标准"},
        (503): {"description": "企业功能管理器不可用"},
    },
)
async def generate_compliance_report(request: ComplianceCheckRequest) -> dict[str, Any]:
    """
    生成详细的合规性报告
    """
    if not ENTERPRISE_AVAILABLE:
        raise HTTPException(status_code=503, detail="企业功能管理器不可用")
    try:
        standard: ComplianceStandard = ComplianceStandard(request.standard)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"无效的合规标准: {request.standard}")
    report: dict[str, Any] = await enterprise_functionality_manager.generate_compliance_report(
        standard
    )
    return {"status": "success", "compliance_report": report}


@router.post(
    "/encryption/encrypt",
    summary="加密数据",
    responses={
        (200): {
            "description": "加密结果",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "encrypted_data": "encrypted_string",
                        "classification": "confidential",
                        "original_length": 10,
                        "encrypted_length": 50,
                    }
                }
            },
        },
        (400): {"description": "无效的数据分类"},
        (503): {"description": "企业功能管理器不可用"},
    },
)
async def encrypt_data(request: EncryptionRequest) -> dict[str, Any]:
    """
    根据数据分类级别加密数据
    """
    if not ENTERPRISE_AVAILABLE:
        raise HTTPException(status_code=503, detail="企业功能管理器不可用")
    try:
        classification: DataClassification = DataClassification(request.classification)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"无效的数据分类: {request.classification}")
    encrypted: str = enterprise_functionality_manager.encrypt_data(request.data, classification)
    return {
        "status": "success",
        "encrypted_data": encrypted,
        "classification": classification.value,
        "original_length": len(request.data),
        "encrypted_length": len(encrypted),
    }


@router.post(
    "/encryption/decrypt",
    summary="解密数据",
    responses={
        (200): {
            "description": "解密结果",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "decrypted_data": "original_string",
                        "original_length": 50,
                        "decrypted_length": 10,
                    }
                }
            },
        },
        (503): {"description": "企业功能管理器不可用"},
    },
)
async def decrypt_data(encrypted_data: str) -> dict[str, Any]:
    """
    解密数据
    """
    if not ENTERPRISE_AVAILABLE:
        raise HTTPException(status_code=503, detail="企业功能管理器不可用")
    decrypted: str = enterprise_functionality_manager.decrypt_data(encrypted_data)
    return {
        "status": "success",
        "decrypted_data": decrypted,
        "original_length": len(encrypted_data),
        "decrypted_length": len(decrypted),
    }


@router.post(
    "/audit/log",
    summary="创建审计日志",
    responses={
        (200): {
            "description": "审计日志创建成功",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "audit_entry": {
                            "entry_id": "audit-001",
                            "tenant_id": "tenant-001",
                            "user_id": "user-001",
                            "action": "read",
                            "resource_type": "database",
                            "resource_id": "resource-001",
                            "outcome": "success",
                            "timestamp": "2026-07-02T10:30:00Z",
                            "data_classification": "internal",
                        },
                    }
                }
            },
        },
        (400): {"description": "无效的数据分类"},
        (503): {"description": "企业功能管理器不可用"},
    },
)
async def create_audit_log(request: AuditLogRequest) -> dict[str, Any]:
    """
    创建增强的审计日志条目
    """
    if not ENTERPRISE_AVAILABLE:
        raise HTTPException(status_code=503, detail="企业功能管理器不可用")
    try:
        classification: DataClassification = DataClassification(request.data_classification)
    except ValueError:
        raise HTTPException(
            status_code=400, detail=f"无效的数据分类: {request.data_classification}"
        )
    audit_entry = enterprise_functionality_manager.create_audit_log(
        tenant_id=request.tenant_id,
        user_id=request.user_id,
        action=request.action,
        resource_type=request.resource_type,
        resource_id=request.resource_id,
        outcome=request.outcome,
        ip_address=request.ip_address,
        user_agent=request.user_agent,
        metadata=request.metadata,
        data_classification=classification,
    )
    return {
        "status": "success",
        "audit_entry": {
            "entry_id": audit_entry.entry_id,
            "tenant_id": audit_entry.tenant_id,
            "user_id": audit_entry.user_id,
            "action": audit_entry.action,
            "resource_type": audit_entry.resource_type,
            "resource_id": audit_entry.resource_id,
            "outcome": audit_entry.outcome,
            "timestamp": audit_entry.timestamp.isoformat(),
            "data_classification": audit_entry.data_classification.value,
        },
    }


@router.get(
    "/audit/logs",
    summary="查询审计日志",
    responses={
        (200): {
            "description": "审计日志列表",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "total_logs": 10,
                        "logs": [
                            {
                                "entry_id": "audit-001",
                                "tenant_id": "tenant-001",
                                "user_id": "user-001",
                                "action": "read",
                                "resource_type": "database",
                                "resource_id": "resource-001",
                                "outcome": "success",
                                "timestamp": "2026-07-02T10:30:00Z",
                                "data_classification": "internal",
                            }
                        ],
                    }
                }
            },
        },
        (400): {"description": "无效的日期格式"},
        (503): {"description": "企业功能管理器不可用"},
    },
)
async def query_audit_logs(
    tenant_id: Optional[str] = None,
    user_id: Optional[str] = None,
    action: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = Query(default=100, ge=1, le=500),
) -> dict[str, Any]:
    """
    查询审计日志，支持多种过滤条件
    """
    if not ENTERPRISE_AVAILABLE:
        raise HTTPException(status_code=503, detail="企业功能管理器不可用")
    start_dt = None
    end_dt = None
    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="无效的开始日期格式")
    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="无效的结束日期格式")
    logs = await enterprise_functionality_manager.query_audit_logs(
        tenant_id=tenant_id,
        user_id=user_id,
        action=action,
        start_date=start_dt,
        end_date=end_dt,
        limit=limit,
    )
    return {
        "status": "success",
        "total_logs": len(logs),
        "logs": [
            {
                "entry_id": log.entry_id,
                "tenant_id": log.tenant_id,
                "user_id": log.user_id,
                "action": log.action,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "outcome": log.outcome,
                "ip_address": log.ip_address,
                "user_agent": log.user_agent,
                "timestamp": log.timestamp.isoformat(),
                "data_classification": log.data_classification.value,
                "metadata": log.metadata,
            }
            for log in logs
        ],
    }


@router.post(
    "/audit/cleanup",
    summary="清理旧审计日志",
    responses={
        (200): {
            "description": "清理成功",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "removed_logs_count": 100,
                        "retention_days": 90,
                    }
                }
            },
        },
        (503): {"description": "企业功能管理器不可用"},
    },
)
async def cleanup_old_audit_logs() -> dict[str, Any]:
    """
    清理超过保留期限的旧审计日志
    """
    if not ENTERPRISE_AVAILABLE:
        raise HTTPException(status_code=503, detail="企业功能管理器不可用")
    removed_count = await enterprise_functionality_manager.cleanup_old_audit_logs()
    return {
        "status": "success",
        "removed_logs_count": removed_count,
        "retention_days": enterprise_functionality_manager.audit_retention_days,
    }


@router.post(
    "/privacy/consent",
    summary="管理用户同意",
    responses={
        (200): {
            "description": "同意管理成功",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "user_id": "user-001",
                        "consent_purpose": "analytics",
                        "consent_given": True,
                    }
                }
            },
        },
        (503): {"description": "企业功能管理器不可用"},
    },
)
async def manage_consent(request: ConsentRequest) -> dict[str, Any]:
    """
    管理用户的数据处理同意
    """
    if not ENTERPRISE_AVAILABLE:
        raise HTTPException(status_code=503, detail="企业功能管理器不可用")
    enterprise_functionality_manager.manage_consent(
        request.user_id, request.consent_given, request.consent_purpose
    )
    return {
        "status": "success",
        "user_id": request.user_id,
        "consent_purpose": request.consent_purpose,
        "consent_given": request.consent_given,
    }


@router.get(
    "/privacy/consent/{user_id}",
    summary="检查用户同意",
    responses={
        (200): {
            "description": "用户同意状态",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "user_id": "user-001",
                        "consent_purpose": "analytics",
                        "consent_given": True,
                    }
                }
            },
        },
        (503): {"description": "企业功能管理器不可用"},
    },
)
async def check_consent(user_id: str, consent_purpose: str) -> dict[str, Any]:
    """
    检查用户是否对指定目的给予了同意
    """
    if not ENTERPRISE_AVAILABLE:
        raise HTTPException(status_code=503, detail="企业功能管理器不可用")
    consent_given = enterprise_functionality_manager.check_consent(user_id, consent_purpose)
    return {
        "status": "success",
        "user_id": user_id,
        "consent_purpose": consent_purpose,
        "consent_given": consent_given,
    }


@router.post(
    "/privacy/mask",
    summary="屏蔽敏感数据",
    responses={
        (200): {
            "description": "屏蔽后的数据",
            "content": {
                "application/json": {
                    "example": {"status": "success", "masked_data": {"email": "***@***.com"}}
                }
            },
        },
        (503): {"description": "企业功能管理器不可用"},
    },
)
async def mask_sensitive_data(data: dict[str, Any]) -> dict[str, Any]:
    """
    根据数据分类屏蔽敏感数据
    """
    if not ENTERPRISE_AVAILABLE:
        raise HTTPException(status_code=503, detail="企业功能管理器不可用")
    masked_data = enterprise_functionality_manager.mask_sensitive_data(data)
    return {"status": "success", "masked_data": masked_data}


@router.get(
    "/summary",
    summary="获取企业功能摘要",
    responses={
        (200): {
            "description": "企业功能摘要",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "enterprise_summary": {
                            "tenant_count": 10,
                            "compliance_checks": 100,
                            "encryption_enabled": True,
                        },
                    }
                }
            },
        },
        (503): {"description": "企业功能管理器不可用"},
    },
)
async def get_enterprise_summary() -> dict[str, Any]:
    """
    获取企业功能的整体摘要信息
    """
    if not ENTERPRISE_AVAILABLE:
        raise HTTPException(status_code=503, detail="企业功能管理器不可用")
    summary = enterprise_functionality_manager.get_enterprise_summary()
    return {"status": "success", "enterprise_summary": summary}


@router.get(
    "/compliance/standards",
    summary="获取支持的合规标准",
    responses={
        (200): {
            "description": "支持的合规标准列表",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "supported_standards": ["GDPR", "HIPAA", "SOC2"],
                        "enabled_standards": ["GDPR"],
                    }
                }
            },
        },
        (503): {"description": "企业功能管理器不可用"},
    },
)
async def get_compliance_standards() -> dict[str, Any]:
    """
    获取支持的合规标准列表
    """
    if not ENTERPRISE_AVAILABLE:
        raise HTTPException(status_code=503, detail="企业功能管理器不可用")
    standards = [s.value for s in ComplianceStandard]
    return {
        "status": "success",
        "supported_standards": standards,
        "enabled_standards": [
            s.value for s in enterprise_functionality_manager.compliance_standards
        ],
    }


@router.get(
    "/encryption/status",
    summary="获取加密状态",
    responses={
        (200): {
            "description": "加密状态",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "encryption_status": {
                            "enabled": True,
                            "level": "AES-256",
                            "keys_count": 5,
                            "cipher_available": True,
                        },
                    }
                }
            },
        },
        (503): {"description": "企业功能管理器不可用"},
    },
)
async def get_encryption_status() -> dict[str, Any]:
    """
    获取加密功能的状态信息
    """
    if not ENTERPRISE_AVAILABLE:
        raise HTTPException(status_code=503, detail="企业功能管理器不可用")
    return {
        "status": "success",
        "encryption_status": {
            "enabled": enterprise_functionality_manager.encryption_enabled,
            "level": enterprise_functionality_manager.encryption_level.value,
            "keys_count": len(enterprise_functionality_manager.encryption_keys),
            "cipher_available": enterprise_functionality_manager.cipher_suite is not None,
        },
    }


@router.get(
    "/data/classification/rules",
    summary="获取数据分类规则",
    responses={
        (200): {
            "description": "数据分类规则",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "classification_rules": {"email": "confidential", "phone": "sensitive"},
                    }
                }
            },
        },
        (503): {"description": "企业功能管理器不可用"},
    },
)
async def get_data_classification_rules() -> dict[str, Any]:
    """
    获取数据分类规则
    """
    if not ENTERPRISE_AVAILABLE:
        raise HTTPException(status_code=503, detail="企业功能管理器不可用")
    rules = {
        key: classification.value
        for key, classification in (
            enterprise_functionality_manager.data_classification_rules.items()
        )
    }
    return {"status": "success", "classification_rules": rules}


@router.post(
    "/data/classify",
    summary="分类数据",
    responses={
        (200): {
            "description": "数据分类结果",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "data_key": "email",
                        "classification": "confidential",
                    }
                }
            },
        },
        (503): {"description": "企业功能管理器不可用"},
    },
)
async def classify_data(data_key: str) -> dict[str, Any]:
    """
    根据键分类数据
    """
    if not ENTERPRISE_AVAILABLE:
        raise HTTPException(status_code=503, detail="企业功能管理器不可用")
    classification = enterprise_functionality_manager.classify_data(data_key)
    return {"status": "success", "data_key": data_key, "classification": classification.value}
