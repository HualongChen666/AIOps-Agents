# -*- coding: utf-8 -*-
"""
安全管理高级API路由
实现25个安全管理相关的API端点
使用数据库持久化存储
"""

import json
import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.command_guard import analyze_command, get_audit_log
from core.database import get_db
from core.repositories.security_repository import SecurityRepository

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/security", tags=["安全管理高级API"])


def _verify_access(request: Request, x_internal_key: Optional[str] = None) -> None:
    # Wave2 #25: no silent fallback that disables the access check on import
    # failure — let an ImportError propagate instead.
    from config import ALLOWED_LOCAL_IPS, INTERNAL_API_KEY
    source_ip = request.client.host if request.client else "unknown"
    if INTERNAL_API_KEY:
        if x_internal_key != INTERNAL_API_KEY:
            raise HTTPException(status_code=403, detail="需要有效的X-Internal-Key")
        return
    if source_ip not in ALLOWED_LOCAL_IPS:
        raise HTTPException(status_code=403, detail="仅供本地调用")


def _get_repository(db: Session) -> SecurityRepository:
    """获取Security Repository实例"""
    return SecurityRepository(db)


# 1. Key Management
class KeyCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    type: Literal["api_key", "secret_key", "jwt", "ssh", "certificate"] = Field(default="api_key")
    algorithm: str = Field(default="RSA")
    keySize: int = Field(default=2048, ge=1024, le=4096)
    usage: List[str] = Field(default_factory=list)


class KeyUpdateRequest(BaseModel):
    status: Optional[Literal["active", "inactive", "expired", "revoked"]] = None
    autoRenew: Optional[bool] = None


@router.get("/key-management/keys")
async def get_keys(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    repo = _get_repository(db)
    keys = repo.get_keys(status=status)
    return {
        "keys": [
            {
                "id": k.id,
                "name": k.name,
                "type": k.key_type,
                "algorithm": k.algorithm,
                "keySize": k.key_size,
                "status": k.status,
                "createdAt": k.created_at.isoformat() if k.created_at else None,
                "expiresAt": k.expires_at.isoformat() if k.expires_at else None,
                "lastRotated": k.last_rotated_at.isoformat() if k.last_rotated_at else None,
                "lastUsed": k.last_used_at.isoformat() if k.last_used_at else None,
                "autoRenew": k.auto_renew,
                "usage": k.usage,
            }
            for k in keys
        ],
        "total": len(keys),
    }


@router.post("/key-management/keys")
async def create_key(
    req: KeyCreateRequest,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    repo = _get_repository(db)
    # Generate encrypted key value (in production, use proper encryption)
    import secrets
    import os
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.backends import default_backend
    
    # Generate a random key
    key_value = secrets.token_urlsafe(32)
    
    # Encrypt the key (simplified - in production use proper key management)
    encryption_key = os.getenv("ENCRYPTION_KEY", "default-encryption-key-32-bytes-long!!")
    iv = os.urandom(16)
    cipher = Cipher(algorithms.AES(encryption_key[:32].encode()), modes.CFB(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    encrypted_key = encryptor.update(key_value.encode()) + encryptor.finalize()
    
    key = repo.create_key(
        name=req.name,
        key_type=req.type,
        algorithm=req.algorithm,
        key_size=req.keySize,
        encrypted_key_value=encrypted_key.hex(),
        encrypted_key_iv=iv.hex(),
        usage=req.usage,
    )
    
    logger.info(f"创建密钥: {req.name}")
    return {
        "id": key.id,
        "name": key.name,
        "type": key.key_type,
        "algorithm": key.algorithm,
        "keySize": key.key_size,
        "status": key.status,
        "createdAt": key.created_at.isoformat() if key.created_at else None,
        "expiresAt": key.expires_at.isoformat() if key.expires_at else None,
        "lastRotated": key.last_rotated_at.isoformat() if key.last_rotated_at else None,
        "lastUsed": key.last_used_at.isoformat() if key.last_used_at else None,
        "autoRenew": key.auto_renew,
        "usage": key.usage,
    }


@router.patch("/key-management/keys/{key_id}")
async def update_key(
    key_id: str,
    req: KeyUpdateRequest,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    repo = _get_repository(db)
    key = repo.update_key(key_id, status=req.status, auto_renew=req.autoRenew)
    if not key:
        raise HTTPException(status_code=404, detail="密钥不存在")
    logger.info(f"更新密钥: {key_id}")
    return {
        "id": key.id,
        "name": key.name,
        "type": key.key_type,
        "algorithm": key.algorithm,
        "keySize": key.key_size,
        "status": key.status,
        "createdAt": key.created_at.isoformat() if key.created_at else None,
        "expiresAt": key.expires_at.isoformat() if key.expires_at else None,
        "lastRotated": key.last_rotated_at.isoformat() if key.last_rotated_at else None,
        "lastUsed": key.last_used_at.isoformat() if key.last_used_at else None,
        "autoRenew": key.auto_renew,
        "usage": key.usage,
    }


# 2. MFA
class MfaMethodCreateRequest(BaseModel):
    type: Literal["totp", "sms", "email", "hardware_token", "biometric"]
    name: str = Field(..., min_length=1, max_length=128)
    description: str = Field(default="", max_length=512)
    priority: int = Field(default=1, ge=1, le=10)


class MfaMethodUpdateRequest(BaseModel):
    enabled: Optional[bool] = None
    required: Optional[bool] = None


@router.get("/mfa/methods")
async def get_mfa_methods(
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    repo = _get_repository(db)
    methods = repo.get_mfa_methods()
    return {
        "methods": [
            {
                "id": m.id,
                "type": m.method_type,
                "name": m.name,
                "description": m.description,
                "enabled": m.enabled,
                "required": m.required,
                "priority": m.priority,
            }
            for m in methods
        ]
    }


@router.post("/mfa/methods")
async def create_mfa_method(
    req: MfaMethodCreateRequest,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    repo = _get_repository(db)
    method = repo.create_mfa_method(
        method_type=req.type,
        name=req.name,
        description=req.description,
        priority=req.priority,
    )
    logger.info(f"创建MFA方法: {req.name}")
    return {
        "id": method.id,
        "type": method.method_type,
        "name": method.name,
        "description": method.description,
        "enabled": method.enabled,
        "required": method.required,
        "priority": method.priority,
    }


@router.patch("/mfa/methods/{method_id}")
async def update_mfa_method(
    method_id: str,
    req: MfaMethodUpdateRequest,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    repo = _get_repository(db)
    method = repo.update_mfa_method(method_id, enabled=req.enabled, required=req.required)
    if not method:
        raise HTTPException(status_code=404, detail="MFA方法不存在")
    logger.info(f"更新MFA方法: {method_id}")
    return {
        "id": method.id,
        "type": method.method_type,
        "name": method.name,
        "description": method.description,
        "enabled": method.enabled,
        "required": method.required,
        "priority": method.priority,
    }


# 3. ABAC
class AbacPolicyCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    effect: Literal["allow", "deny"] = Field(default="allow")
    resources: List[str] = Field(default_factory=list)
    actions: List[str] = Field(default_factory=list)


class AbacPolicyUpdateRequest(BaseModel):
    enabled: Optional[bool] = None


@router.get("/abac/policies")
async def get_abac_policies(
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    repo = _get_repository(db)
    policies = repo.get_abac_policies()
    return {
        "policies": [
            {
                "id": p.id,
                "name": p.name,
                "effect": p.effect,
                "resources": p.resources,
                "actions": p.actions,
                "enabled": p.enabled,
            }
            for p in policies
        ],
        "total": len(policies),
    }


@router.post("/abac/policies")
async def create_abac_policy(
    req: AbacPolicyCreateRequest,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    repo = _get_repository(db)
    policy = repo.create_abac_policy(
        name=req.name,
        effect=req.effect,
        resources=req.resources,
        actions=req.actions,
    )
    logger.info(f"创建ABAC策略: {req.name}")
    return {
        "id": policy.id,
        "name": policy.name,
        "effect": policy.effect,
        "resources": policy.resources,
        "actions": policy.actions,
        "enabled": policy.enabled,
    }


@router.patch("/abac/policies/{policy_id}")
async def update_abac_policy(
    policy_id: str,
    req: AbacPolicyUpdateRequest,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    repo = _get_repository(db)
    policy = repo.update_abac_policy(policy_id, enabled=req.enabled)
    if not policy:
        raise HTTPException(status_code=404, detail="策略不存在")
    logger.info(f"更新ABAC策略: {policy_id}")
    return {
        "id": policy.id,
        "name": policy.name,
        "effect": policy.effect,
        "resources": policy.resources,
        "actions": policy.actions,
        "enabled": policy.enabled,
    }


@router.delete("/abac/policies/{policy_id}")
async def delete_abac_policy(
    policy_id: str,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    repo = _get_repository(db)
    success = repo.delete_abac_policy(policy_id)
    if not success:
        raise HTTPException(status_code=404, detail="策略不存在")
    logger.info(f"删除ABAC策略: {policy_id}")
    return {"success": True}


# 4. RBAC
class RbacRoleCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    permissions: List[str] = Field(default_factory=list)


class RbacRoleUpdateRequest(BaseModel):
    status: Optional[Literal["active", "inactive"]] = None


@router.get("/rbac/roles")
async def get_rbac_roles(
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    repo = _get_repository(db)
    roles = repo.get_rbac_roles()
    return {
        "roles": [
            {
                "id": r.id,
                "name": r.name,
                "permissions": r.permissions,
                "status": r.status,
            }
            for r in roles
        ],
        "total": len(roles),
    }


@router.post("/rbac/roles")
async def create_rbac_role(
    req: RbacRoleCreateRequest,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    repo = _get_repository(db)
    role = repo.create_rbac_role(
        name=req.name,
        permissions=req.permissions,
    )
    logger.info(f"创建RBAC角色: {req.name}")
    return {
        "id": role.id,
        "name": role.name,
        "permissions": role.permissions,
        "status": role.status,
    }


@router.patch("/rbac/roles/{role_id}")
async def update_rbac_role(
    role_id: str,
    req: RbacRoleUpdateRequest,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    repo = _get_repository(db)
    role = repo.update_rbac_role(role_id, status=req.status)
    if not role:
        raise HTTPException(status_code=404, detail="角色不存在")
    logger.info(f"更新RBAC角色: {role_id}")
    return {
        "id": role.id,
        "name": role.name,
        "permissions": role.permissions,
        "status": role.status,
    }


@router.delete("/rbac/roles/{role_id}")
async def delete_rbac_role(
    role_id: str,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    repo = _get_repository(db)
    success = repo.delete_rbac_role(role_id)
    if not success:
        raise HTTPException(status_code=404, detail="角色不存在")
    logger.info(f"删除RBAC角色: {role_id}")
    return {"success": True}


# 5. Rate Limit
class RateLimitRuleCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    endpoint: str = Field(..., min_length=1, max_length=256)
    limit: int = Field(default=100, ge=1, le=10000)


class RateLimitRuleUpdateRequest(BaseModel):
    enabled: Optional[bool] = None


@router.get("/rate-limit/rules")
async def get_rate_limit_rules(
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    repo = _get_repository(db)
    rules = repo.get_rate_limit_rules()
    return {
        "rules": [
            {
                "id": r.id,
                "name": r.name,
                "endpoint": r.endpoint,
                "limit": r.limit,
                "windowSeconds": r.window_seconds,
                "strategy": r.strategy,
                "enabled": r.enabled,
            }
            for r in rules
        ],
        "total": len(rules),
    }


@router.post("/rate-limit/rules")
async def create_rate_limit_rule(
    req: RateLimitRuleCreateRequest,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    repo = _get_repository(db)
    rule = repo.create_rate_limit_rule(
        name=req.name,
        endpoint=req.endpoint,
        limit=req.limit,
    )
    logger.info(f"创建速率限制规则: {req.name}")
    return {
        "id": rule.id,
        "name": rule.name,
        "endpoint": rule.endpoint,
        "limit": rule.limit,
        "windowSeconds": rule.window_seconds,
        "strategy": rule.strategy,
        "enabled": rule.enabled,
    }


@router.patch("/rate-limit/rules/{rule_id}")
async def update_rate_limit_rule(
    rule_id: str,
    req: RateLimitRuleUpdateRequest,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    repo = _get_repository(db)
    rule = repo.update_rate_limit_rule(rule_id, enabled=req.enabled)
    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")
    logger.info(f"更新速率限制规则: {rule_id}")
    return {
        "id": rule.id,
        "name": rule.name,
        "endpoint": rule.endpoint,
        "limit": rule.limit,
        "windowSeconds": rule.window_seconds,
        "strategy": rule.strategy,
        "enabled": rule.enabled,
    }


@router.delete("/rate-limit/rules/{rule_id}")
async def delete_rate_limit_rule(
    rule_id: str,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    repo = _get_repository(db)
    success = repo.delete_rate_limit_rule(rule_id)
    if not success:
        raise HTTPException(status_code=404, detail="规则不存在")
    logger.info(f"删除速率限制规则: {rule_id}")
    return {"success": True}


# 6. HTTPS Certificates
class CertificateCreateRequest(BaseModel):
    domain: str = Field(..., min_length=1, max_length=256)
    algorithm: str = Field(default="RSA")


class CertificateUpdateRequest(BaseModel):
    autoRenew: Optional[bool] = None


@router.get("/https/certificates")
async def get_certificates(
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    repo = _get_repository(db)
    certs = repo.get_https_certificates()
    return {
        "certificates": [
            {
                "id": c.id,
                "domain": c.domain,
                "status": c.status,
                "algorithm": c.algorithm,
                "issuer": c.issuer,
                "issuedAt": c.issued_at.isoformat() if c.issued_at else None,
                "expiresAt": c.expires_at.isoformat() if c.expires_at else None,
                "autoRenew": c.auto_renew,
            }
            for c in certs
        ],
        "total": len(certs),
    }


@router.post("/https/certificates")
async def create_certificate(
    req: CertificateCreateRequest,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    repo = _get_repository(db)
    # Generate a real self-signed X.509 certificate and seal its private key.
    from core.certificate_manager import (
        CertificateError,
        generate_self_signed_certificate,
        seal_private_key,
    )

    try:
        material = generate_self_signed_certificate(req.domain, req.algorithm)
    except CertificateError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    sealed = seal_private_key(material["private_key_pem"])

    cert = repo.create_https_certificate(
        domain=req.domain,
        certificate_pem=material["certificate_pem"],
        private_key_encrypted=sealed["ciphertext"],
        private_key_iv=sealed["iv"],
        algorithm=req.algorithm,
        issued_at=material["issued_at"].astimezone(timezone.utc).replace(tzinfo=None),
        expires_at=material["expires_at"].astimezone(timezone.utc).replace(tzinfo=None),
        issuer=material["issuer"],
    )
    logger.info("创建SSL证书: %s", req.domain)
    return {
        "id": cert.id,
        "domain": cert.domain,
        "status": cert.status,
        "algorithm": cert.algorithm,
        "issuer": cert.issuer,
        "issuedAt": cert.issued_at.isoformat() if cert.issued_at else None,
        "expiresAt": cert.expires_at.isoformat() if cert.expires_at else None,
        "autoRenew": cert.auto_renew,
    }


@router.patch("/https/certificates/{cert_id}")
async def update_certificate(
    cert_id: str,
    req: CertificateUpdateRequest,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    repo = _get_repository(db)
    cert = repo.update_https_certificate(cert_id, auto_renew=req.autoRenew)
    if not cert:
        raise HTTPException(status_code=404, detail="证书不存在")
    logger.info(f"更新SSL证书: {cert_id}")
    return {
        "id": cert.id,
        "domain": cert.domain,
        "status": cert.status,
        "algorithm": cert.algorithm,
        "issuer": cert.issuer,
        "issuedAt": cert.issued_at.isoformat() if cert.issued_at else None,
        "expiresAt": cert.expires_at.isoformat() if cert.expires_at else None,
        "autoRenew": cert.auto_renew,
    }
# 7. Snapshot Encryption
class SnapshotCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    source: str = Field(..., min_length=1, max_length=256)
    encryptionAlgorithm: str = Field(default="AES-256", max_length=50)
    retentionDays: int = Field(default=7, ge=1, le=3650)


class SnapshotUpdateRequest(BaseModel):
    status: Optional[Literal["active", "archived", "completed", "failed"]] = None


def _seal_state(payload: Dict[str, Any]) -> tuple[str, str]:
    """Seal a snapshot pre/post-state with the platform AES key.

    Returns ``(ciphertext_hex, iv_hex)`` suitable for the ``*_encrypted`` /
    ``*_iv`` columns.  Uses a process-wide cipher so the master key stays
    stable across calls (env ``ENCRYPTION_MASTER_KEY`` in production).
    """
    ciphertext, iv = _get_state_cipher().encrypt(json.dumps(payload, sort_keys=True, default=str))
    return ciphertext, iv


_state_cipher: Optional[Any] = None


def _get_state_cipher() -> Any:
    global _state_cipher
    if _state_cipher is None:
        from core.key_management import KeyEncryptionService

        _state_cipher = KeyEncryptionService()
    return _state_cipher


@router.get("/snapshot-encryption/snapshots")
async def get_snapshots(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    repo = _get_repository(db)
    snapshots = repo.get_snapshot_encryptions(status=status)
    return {
        "snapshots": [
            {
                "id": s.id,
                "name": s.name,
                "source": s.source,
                "status": s.status,
                "encryptionAlgorithm": s.encryption_algorithm,
                "retentionDays": s.retention_days,
                "expiresAt": s.expires_at.isoformat() if s.expires_at else None,
                "createdAt": s.created_at.isoformat() if s.created_at else None,
            }
            for s in snapshots
        ],
        "total": len(snapshots),
    }


@router.post("/snapshot-encryption/snapshots")
async def create_snapshot(
    req: SnapshotCreateRequest,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    repo = _get_repository(db)
    pre_state = {
        "name": req.name,
        "source": req.source,
        "captured_at": datetime.now(timezone.utc).isoformat(),
    }
    ciphertext, iv = _seal_state(pre_state)
    snapshot = repo.create_snapshot_encryption(
        name=req.name,
        source=req.source,
        pre_state_encrypted=ciphertext,
        pre_state_iv=iv,
        encryption_algorithm=req.encryptionAlgorithm,
        retention_days=req.retentionDays,
    )
    logger.info("创建加密快照: %s", req.name)
    return {
        "id": snapshot.id,
        "name": snapshot.name,
        "source": snapshot.source,
        "status": snapshot.status,
        "encryptionAlgorithm": snapshot.encryption_algorithm,
        "retentionDays": snapshot.retention_days,
        "expiresAt": snapshot.expires_at.isoformat() if snapshot.expires_at else None,
        "createdAt": snapshot.created_at.isoformat() if snapshot.created_at else None,
    }


@router.patch("/snapshot-encryption/snapshots/{snapshot_id}")
async def update_snapshot(
    snapshot_id: str,
    req: SnapshotUpdateRequest,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    repo = _get_repository(db)
    snapshot = repo.update_snapshot_encryption(snapshot_id, status=req.status)
    if not snapshot:
        raise HTTPException(status_code=404, detail="快照不存在")
    logger.info("更新加密快照: %s", snapshot_id)
    return {
        "id": snapshot.id,
        "name": snapshot.name,
        "source": snapshot.source,
        "status": snapshot.status,
        "encryptionAlgorithm": snapshot.encryption_algorithm,
        "retentionDays": snapshot.retention_days,
        "expiresAt": snapshot.expires_at.isoformat() if snapshot.expires_at else None,
        "createdAt": snapshot.created_at.isoformat() if snapshot.created_at else None,
    }


# 8. Data Encryption
class DataKeyCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    purpose: str = Field(default="database", max_length=50)
    algorithm: str = Field(default="AES-256", max_length=50)
    keySize: int = Field(default=256, ge=128, le=512)
    scope: Optional[str] = Field(default=None, max_length=256)


class DataKeyUpdateRequest(BaseModel):
    status: Optional[Literal["active", "disabled", "rotated"]] = None


@router.get("/data-encryption/keys")
async def get_data_keys(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    repo = _get_repository(db)
    keys = repo.get_data_encryption_keys(status=status)
    return {
        "keys": [
            {
                "id": k.id,
                "name": k.name,
                "purpose": k.purpose,
                "algorithm": k.algorithm,
                "keySize": k.key_size,
                "scope": k.scope,
                "status": k.status,
                "rotationEnabled": k.rotation_enabled,
                "createdAt": k.created_at.isoformat() if k.created_at else None,
            }
            for k in keys
        ],
        "total": len(keys),
    }


@router.post("/data-encryption/keys")
async def create_data_key(
    req: DataKeyCreateRequest,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    repo = _get_repository(db)
    # Generate a real random key and seal it with the platform master key.
    raw_key = secrets.token_hex(max(16, req.keySize // 8))
    ciphertext, iv = _get_state_cipher().encrypt(raw_key)
    key = repo.create_data_encryption_key(
        name=req.name,
        key_encrypted=ciphertext,
        key_iv=iv,
        purpose=req.purpose,
        algorithm=req.algorithm,
        key_size=req.keySize,
        scope=req.scope,
    )
    logger.info("创建数据加密密钥: %s", req.name)
    return {
        "id": key.id,
        "name": key.name,
        "purpose": key.purpose,
        "algorithm": key.algorithm,
        "keySize": key.key_size,
        "scope": key.scope,
        "status": key.status,
        "rotationEnabled": key.rotation_enabled,
        "createdAt": key.created_at.isoformat() if key.created_at else None,
    }


@router.patch("/data-encryption/keys/{key_id}")
async def update_data_key(
    key_id: str,
    req: DataKeyUpdateRequest,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    repo = _get_repository(db)
    key = repo.update_data_encryption_key(key_id, status=req.status)
    if not key:
        raise HTTPException(status_code=404, detail="密钥不存在")
    logger.info("更新数据加密密钥: %s", key_id)
    return {
        "id": key.id,
        "name": key.name,
        "purpose": key.purpose,
        "algorithm": key.algorithm,
        "keySize": key.key_size,
        "scope": key.scope,
        "status": key.status,
        "rotationEnabled": key.rotation_enabled,
        "createdAt": key.created_at.isoformat() if key.created_at else None,
    }


# 9. Data Privacy
class PrivacySubjectCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    type: Literal["user", "customer"] = Field(default="user")
    email: Optional[str] = Field(default=None, max_length=255)
    phone: Optional[str] = Field(default=None, max_length=50)
    identifier: Optional[str] = Field(default=None, max_length=255)
    consentLevel: Literal["full", "partial", "none"] = Field(default="partial")


class PrivacySubjectUpdateRequest(BaseModel):
    consentLevel: Optional[Literal["full", "partial", "none"]] = None


@router.get("/data-privacy/subjects")
async def get_privacy_subjects(
    subject_type: Optional[str] = None,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    repo = _get_repository(db)
    subjects = repo.get_privacy_subjects(subject_type=subject_type)
    return {
        "subjects": [
            {
                "id": s.id,
                "name": s.name,
                "type": s.subject_type,
                "email": s.email,
                "phone": s.phone,
                "identifier": s.identifier,
                "consentLevel": s.consent_level,
                "consentGivenAt": s.consent_given_at.isoformat() if s.consent_given_at else None,
                "createdAt": s.created_at.isoformat() if s.created_at else None,
            }
            for s in subjects
        ],
        "total": len(subjects),
    }


@router.post("/data-privacy/subjects")
async def create_privacy_subject(
    req: PrivacySubjectCreateRequest,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    repo = _get_repository(db)
    subject = repo.create_privacy_subject(
        name=req.name,
        subject_type=req.type,
        email=req.email,
        phone=req.phone,
        identifier=req.identifier,
        consent_level=req.consentLevel,
    )
    logger.info("创建隐私主体: %s", req.name)
    return {
        "id": subject.id,
        "name": subject.name,
        "type": subject.subject_type,
        "email": subject.email,
        "phone": subject.phone,
        "identifier": subject.identifier,
        "consentLevel": subject.consent_level,
        "consentGivenAt": subject.consent_given_at.isoformat() if subject.consent_given_at else None,
        "createdAt": subject.created_at.isoformat() if subject.created_at else None,
    }


@router.patch("/data-privacy/subjects/{subject_id}")
async def update_privacy_subject(
    subject_id: str,
    req: PrivacySubjectUpdateRequest,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    repo = _get_repository(db)
    subject = repo.update_privacy_subject(subject_id, consent_level=req.consentLevel)
    if not subject:
        raise HTTPException(status_code=404, detail="隐私主体不存在")
    logger.info("更新隐私主体: %s", subject_id)
    return {
        "id": subject.id,
        "name": subject.name,
        "type": subject.subject_type,
        "email": subject.email,
        "phone": subject.phone,
        "identifier": subject.identifier,
        "consentLevel": subject.consent_level,
        "consentUpdatedAt": (
            subject.consent_updated_at.isoformat() if subject.consent_updated_at else None
        ),
    }


# 10. Compliance Management
class CompliancePolicyCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    framework: Literal["GDPR", "HIPAA", "SOC2", "ISO27001"] = Field(default="GDPR")
    description: Optional[str] = None
    requirements: Optional[List[str]] = None


class CompliancePolicyUpdateRequest(BaseModel):
    status: Optional[Literal["active", "inactive"]] = None


_FRAMEWORK_REQUIREMENTS: Optional[Dict[str, List[str]]] = None


def _framework_requirements(framework: str) -> List[str]:
    """Return the canonical requirement list for *framework*.

    Sourced from :class:`core.compliance_manager.ComplianceManager`'s default
    policies (real, in-repo definitions) rather than invented data.
    """
    global _FRAMEWORK_REQUIREMENTS
    if _FRAMEWORK_REQUIREMENTS is None:
        from core.compliance_manager import ComplianceManager

        mapping: Dict[str, List[str]] = {}
        for policy in ComplianceManager().policies.values():
            key = policy.standard.value.lower()
            bucket = mapping.setdefault(key, [])
            for requirement in policy.requirements:
                if requirement not in bucket:
                    bucket.append(requirement)
        _FRAMEWORK_REQUIREMENTS = mapping
    return list(_FRAMEWORK_REQUIREMENTS.get(framework.lower(), []))


def _compliance_policy_dict(policy: Any) -> Dict[str, Any]:
    return {
        "id": policy.id,
        "name": policy.name,
        "framework": policy.framework,
        "description": policy.description,
        "requirements": policy.requirements,
        "controls": policy.controls,
        "status": policy.status,
        "lastAuditDate": policy.last_audit_date.isoformat() if policy.last_audit_date else None,
        "createdAt": policy.created_at.isoformat() if policy.created_at else None,
    }


@router.get("/compliance-management/policies")
async def get_compliance_policies(
    framework: Optional[str] = None,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    repo = _get_repository(db)
    policies = repo.get_compliance_policies(framework=framework)
    return {"policies": [_compliance_policy_dict(p) for p in policies], "total": len(policies)}


@router.post("/compliance-management/policies")
async def create_compliance_policy(
    req: CompliancePolicyCreateRequest,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    repo = _get_repository(db)
    requirements = req.requirements or _framework_requirements(req.framework)
    description = req.description or f"{req.framework} compliance policy: {req.name}"
    policy = repo.create_compliance_policy(
        name=req.name,
        framework=req.framework,
        description=description,
        requirements=requirements,
    )
    logger.info("创建合规策略: %s", req.name)
    return _compliance_policy_dict(policy)


@router.patch("/compliance-management/policies/{policy_id}")
async def update_compliance_policy(
    policy_id: str,
    req: CompliancePolicyUpdateRequest,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    repo = _get_repository(db)
    policy = repo.update_compliance_policy(policy_id, status=req.status)
    if not policy:
        raise HTTPException(status_code=404, detail="合规策略不存在")
    logger.info("更新合规策略: %s", policy_id)
    return _compliance_policy_dict(policy)


# 11. Compliance Check
class ComplianceStandardCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    category: str = Field(default="general", max_length=50)
    description: Optional[str] = None
    severity: Literal["low", "medium", "high", "critical"] = Field(default="medium")
    checkCriteria: Optional[Dict[str, Any]] = None


class ComplianceStandardUpdateRequest(BaseModel):
    status: Optional[Literal["active", "inactive"]] = None


def _compliance_standard_dict(standard: Any) -> Dict[str, Any]:
    return {
        "id": standard.id,
        "name": standard.name,
        "category": standard.category,
        "description": standard.description,
        "checkCriteria": standard.check_criteria,
        "severity": standard.severity,
        "status": standard.status,
        "createdAt": standard.created_at.isoformat() if standard.created_at else None,
    }


@router.get("/compliance-check/standards")
async def get_compliance_standards(
    category: Optional[str] = None,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    repo = _get_repository(db)
    standards = repo.get_compliance_standards(category=category)
    return {
        "standards": [_compliance_standard_dict(s) for s in standards],
        "total": len(standards),
    }


@router.post("/compliance-check/standards")
async def create_compliance_standard(
    req: ComplianceStandardCreateRequest,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    repo = _get_repository(db)
    check_criteria = req.checkCriteria or {
        "category": req.category,
        "severity": req.severity,
        "evidence_required": True,
    }
    standard = repo.create_compliance_standard(
        name=req.name,
        category=req.category,
        description=req.description or f"{req.category} compliance standard: {req.name}",
        check_criteria=check_criteria,
        severity=req.severity,
    )
    logger.info("创建合规检查标准: %s", req.name)
    return _compliance_standard_dict(standard)


@router.patch("/compliance-check/standards/{standard_id}")
async def update_compliance_standard(
    standard_id: str,
    req: ComplianceStandardUpdateRequest,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    repo = _get_repository(db)
    standard = repo.update_compliance_standard(standard_id, status=req.status)
    if not standard:
        raise HTTPException(status_code=404, detail="合规标准不存在")
    logger.info("更新合规检查标准: %s", standard_id)
    return _compliance_standard_dict(standard)


# 12. Database Security
class DatabaseInstanceCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    type: Literal["postgresql", "mysql"] = Field(default="postgresql")
    host: str = Field(..., min_length=1, max_length=256)
    port: Optional[int] = Field(default=None, ge=1, le=65535)


class DatabaseInstanceUpdateRequest(BaseModel):
    status: Optional[Literal["active", "inactive"]] = None


def _database_instance_dict(instance: Any) -> Dict[str, Any]:
    return {
        "id": instance.id,
        "name": instance.name,
        "type": instance.instance_type,
        "host": instance.host,
        "port": instance.port,
        "encryptionEnabled": instance.encryption_enabled,
        "sslEnabled": instance.ssl_enabled,
        "auditEnabled": instance.audit_enabled,
        "status": instance.status,
        "createdAt": instance.created_at.isoformat() if instance.created_at else None,
    }


@router.get("/database-security/instances")
async def get_database_instances(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    repo = _get_repository(db)
    instances = repo.get_database_security_instances(status=status)
    return {
        "instances": [_database_instance_dict(i) for i in instances],
        "total": len(instances),
    }


@router.post("/database-security/instances")
async def create_database_instance(
    req: DatabaseInstanceCreateRequest,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    repo = _get_repository(db)
    instance = repo.create_database_security_instance(
        name=req.name,
        instance_type=req.type,
        host=req.host,
        port=req.port,
    )
    logger.info("创建数据库实例: %s", req.name)
    return _database_instance_dict(instance)


@router.patch("/database-security/instances/{instance_id}")
async def update_database_instance(
    instance_id: str,
    req: DatabaseInstanceUpdateRequest,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    repo = _get_repository(db)
    instance = repo.update_database_security_instance(instance_id, status=req.status)
    if not instance:
        raise HTTPException(status_code=404, detail="数据库实例不存在")
    logger.info("更新数据库实例: %s", instance_id)
    return _database_instance_dict(instance)


# 13. API Security
class ApiEndpointCreateRequest(BaseModel):
    path: str = Field(..., min_length=1, max_length=256)
    method: str = Field(default="GET", max_length=10)
    authenticationRequired: bool = Field(default=True)
    authorizationRequired: bool = Field(default=True)


class ApiEndpointUpdateRequest(BaseModel):
    status: Optional[Literal["active", "disabled"]] = None


def _api_endpoint_dict(endpoint: Any) -> Dict[str, Any]:
    return {
        "id": endpoint.id,
        "path": endpoint.path,
        "method": endpoint.method,
        "authenticationRequired": endpoint.authentication_required,
        "authorizationRequired": endpoint.authorization_required,
        "rateLimitEnabled": endpoint.rate_limit_enabled,
        "status": endpoint.status,
        "createdAt": endpoint.created_at.isoformat() if endpoint.created_at else None,
    }


@router.get("/api-security/endpoints")
async def get_api_endpoints(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    repo = _get_repository(db)
    endpoints = repo.get_api_security_endpoints(status=status)
    return {
        "endpoints": [_api_endpoint_dict(e) for e in endpoints],
        "total": len(endpoints),
    }


@router.post("/api-security/endpoints")
async def create_api_endpoint(
    req: ApiEndpointCreateRequest,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    repo = _get_repository(db)
    endpoint = repo.create_api_security_endpoint(
        path=req.path,
        method=req.method.upper(),
        authentication_required=req.authenticationRequired,
        authorization_required=req.authorizationRequired,
    )
    logger.info("创建API端点: %s %s", req.method, req.path)
    return _api_endpoint_dict(endpoint)


@router.patch("/api-security/endpoints/{endpoint_id}")
async def update_api_endpoint(
    endpoint_id: str,
    req: ApiEndpointUpdateRequest,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    repo = _get_repository(db)
    endpoint = repo.update_api_security_endpoint(endpoint_id, status=req.status)
    if not endpoint:
        raise HTTPException(status_code=404, detail="API端点不存在")
    logger.info("更新API端点: %s", endpoint_id)
    return _api_endpoint_dict(endpoint)


@router.delete("/api-security/endpoints/{endpoint_id}")
async def delete_api_endpoint(
    endpoint_id: str,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    repo = _get_repository(db)
    success = repo.delete_api_security_endpoint(endpoint_id)
    if not success:
        raise HTTPException(status_code=404, detail="API端点不存在")
    logger.info("删除API端点: %s", endpoint_id)
    return {"success": True}


# 14. Input Validation
class InputValidationRuleCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    field: str = Field(..., min_length=1, max_length=128)
    validationType: Literal["regex", "length", "type", "range", "custom"] = Field(
        default="regex"
    )
    validationPattern: Optional[str] = Field(default=None, max_length=500)


class InputValidationRuleUpdateRequest(BaseModel):
    enabled: Optional[bool] = None


def _validation_rule_dict(rule: Any) -> Dict[str, Any]:
    return {
        "id": rule.id,
        "name": rule.name,
        "field": rule.field,
        "validationType": rule.validation_type,
        "validationPattern": rule.validation_pattern,
        "enabled": rule.enabled,
        "createdAt": rule.created_at.isoformat() if rule.created_at else None,
    }


@router.get("/input-validation/rules")
async def get_input_validation_rules(
    enabled: Optional[bool] = None,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    repo = _get_repository(db)
    rules = repo.get_input_validation_rules(enabled=enabled)
    return {"rules": [_validation_rule_dict(r) for r in rules], "total": len(rules)}


@router.post("/input-validation/rules")
async def create_input_validation_rule(
    req: InputValidationRuleCreateRequest,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    repo = _get_repository(db)
    rule = repo.create_input_validation_rule(
        name=req.name,
        field=req.field,
        validation_type=req.validationType,
        validation_pattern=req.validationPattern,
    )
    logger.info("创建输入验证规则: %s", req.name)
    return _validation_rule_dict(rule)


@router.patch("/input-validation/rules/{rule_id}")
async def update_input_validation_rule(
    rule_id: str,
    req: InputValidationRuleUpdateRequest,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    repo = _get_repository(db)
    rule = repo.update_input_validation_rule(rule_id, enabled=req.enabled)
    if not rule:
        raise HTTPException(status_code=404, detail="验证规则不存在")
    logger.info("更新输入验证规则: %s", rule_id)
    return _validation_rule_dict(rule)


@router.delete("/input-validation/rules/{rule_id}")
async def delete_input_validation_rule(
    rule_id: str,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    repo = _get_repository(db)
    success = repo.delete_input_validation_rule(rule_id)
    if not success:
        raise HTTPException(status_code=404, detail="验证规则不存在")
    logger.info("删除输入验证规则: %s", rule_id)
    return {"success": True}


# 15. Penetration Testing
class PenetrationTestProjectCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    target: str = Field(..., min_length=1, max_length=256)
    testType: Literal["black_box", "white_box", "gray_box"] = Field(default="black_box")


class PenetrationTestProjectUpdateRequest(BaseModel):
    status: Optional[Literal["scheduled", "in_progress", "completed"]] = None


def _penetration_project_dict(project: Any) -> Dict[str, Any]:
    return {
        "id": project.id,
        "name": project.name,
        "target": project.target,
        "testType": project.test_type,
        "status": project.status,
        "riskScore": project.risk_score,
        "createdAt": project.created_at.isoformat() if project.created_at else None,
    }


@router.get("/penetration-testing/projects")
async def get_penetration_projects(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    repo = _get_repository(db)
    projects = repo.get_penetration_test_projects(status=status)
    return {
        "projects": [_penetration_project_dict(p) for p in projects],
        "total": len(projects),
    }


@router.post("/penetration-testing/projects")
async def create_penetration_project(
    req: PenetrationTestProjectCreateRequest,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    repo = _get_repository(db)
    project = repo.create_penetration_test_project(
        name=req.name,
        target=req.target,
        test_type=req.testType,
    )
    logger.info("创建渗透测试项目: %s", req.name)
    return _penetration_project_dict(project)


@router.patch("/penetration-testing/projects/{project_id}")
async def update_penetration_project(
    project_id: str,
    req: PenetrationTestProjectUpdateRequest,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    repo = _get_repository(db)
    project = repo.update_penetration_test_project(project_id, status=req.status)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    logger.info("更新渗透测试项目: %s", project_id)
    return _penetration_project_dict(project)


# 16. Security Testing
class SecurityTestCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    testType: str = Field(default="sast", max_length=50)
    target: Optional[str] = Field(default=None, max_length=256)


class SecurityTestUpdateRequest(BaseModel):
    status: Optional[Literal["pending", "running", "completed", "failed"]] = None


def _security_test_dict(test: Any) -> Dict[str, Any]:
    return {
        "id": test.id,
        "name": test.name,
        "testType": test.test_type,
        "target": test.target,
        "status": test.status,
        "vulnerabilitiesFound": test.vulnerabilities_found,
        "createdAt": test.created_at.isoformat() if test.created_at else None,
    }


@router.get("/security-testing/tests")
async def get_security_tests(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    repo = _get_repository(db)
    tests = repo.get_security_tests(status=status)
    return {"tests": [_security_test_dict(t) for t in tests], "total": len(tests)}


@router.post("/security-testing/tests")
async def create_security_test(
    req: SecurityTestCreateRequest,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    repo = _get_repository(db)
    test = repo.create_security_test(
        name=req.name,
        test_type=req.testType,
        target=req.target,
    )
    logger.info("创建安全测试: %s", req.name)
    return _security_test_dict(test)


@router.patch("/security-testing/tests/{test_id}")
async def update_security_test(
    test_id: str,
    req: SecurityTestUpdateRequest,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    repo = _get_repository(db)
    test = repo.update_security_test(test_id, status=req.status)
    if not test:
        raise HTTPException(status_code=404, detail="测试不存在")
    logger.info("更新安全测试: %s", test_id)
    return _security_test_dict(test)


# 17. Vulnerability Management
class VulnerabilityTicketCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=128)
    severity: Literal["low", "medium", "high", "critical"] = Field(default="medium")
    description: Optional[str] = None
    cveId: Optional[str] = Field(default=None, max_length=50)


class VulnerabilityTicketUpdateRequest(BaseModel):
    status: Optional[Literal["open", "in_progress", "resolved"]] = None


def _vulnerability_ticket_dict(ticket: Any) -> Dict[str, Any]:
    return {
        "id": ticket.id,
        "title": ticket.title,
        "severity": ticket.severity,
        "description": ticket.description,
        "cveId": ticket.cve_id,
        "cvssScore": ticket.cvss_score,
        "status": ticket.status,
        "detectedAt": ticket.detected_at.isoformat() if ticket.detected_at else None,
    }


@router.get("/vulnerability-management/tickets")
async def get_vulnerability_tickets(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    repo = _get_repository(db)
    tickets = repo.get_vulnerability_tickets(status=status)
    return {
        "tickets": [_vulnerability_ticket_dict(t) for t in tickets],
        "total": len(tickets),
    }


@router.post("/vulnerability-management/tickets")
async def create_vulnerability_ticket(
    req: VulnerabilityTicketCreateRequest,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    repo = _get_repository(db)
    ticket = repo.create_vulnerability_ticket(
        title=req.title,
        severity=req.severity,
        description=req.description or f"{req.severity} severity vulnerability: {req.title}",
        cve_id=req.cveId,
    )
    logger.info("创建漏洞工单: %s", req.title)
    return _vulnerability_ticket_dict(ticket)


@router.patch("/vulnerability-management/tickets/{ticket_id}")
async def update_vulnerability_ticket(
    ticket_id: str,
    req: VulnerabilityTicketUpdateRequest,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    repo = _get_repository(db)
    ticket = repo.update_vulnerability_ticket(ticket_id, status=req.status)
    if not ticket:
        raise HTTPException(status_code=404, detail="工单不存在")
    logger.info("更新漏洞工单: %s", ticket_id)
    return _vulnerability_ticket_dict(ticket)


# 18. Vulnerability Intelligence
class ThreatCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    threatType: str = Field(default="malware", max_length=50)
    description: Optional[str] = None
    severity: Literal["low", "medium", "high", "critical"] = Field(default="medium")
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


def _threat_dict(threat: Any) -> Dict[str, Any]:
    return {
        "id": threat.id,
        "name": threat.name,
        "threatType": threat.threat_type,
        "description": threat.description,
        "severity": threat.severity,
        "confidence": threat.confidence,
        "status": threat.status,
        "createdAt": threat.created_at.isoformat() if threat.created_at else None,
    }


@router.get("/vulnerability-intelligence/threats")
async def get_threats(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    repo = _get_repository(db)
    threats = repo.get_threat_intelligences(status=status)
    return {"threats": [_threat_dict(t) for t in threats], "total": len(threats)}


@router.post("/vulnerability-intelligence/threats")
async def create_threat(
    req: ThreatCreateRequest,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    repo = _get_repository(db)
    threat = repo.create_threat_intelligence(
        name=req.name,
        threat_type=req.threatType,
        description=req.description or f"{req.threatType} threat intelligence: {req.name}",
        severity=req.severity,
        confidence=req.confidence,
    )
    logger.info("创建威胁情报: %s", req.name)
    return _threat_dict(threat)


# 19. Vulnerability Scan
class VulnerabilityScanCreateRequest(BaseModel):
    target: str = Field(..., min_length=1, max_length=256)
    scanType: Literal["full", "quick", "custom"] = Field(default="full")


class VulnerabilityScanUpdateRequest(BaseModel):
    status: Optional[Literal["pending", "running", "completed", "failed"]] = None


def _vulnerability_scan_dict(scan: Any) -> Dict[str, Any]:
    return {
        "id": scan.id,
        "target": scan.target,
        "scanType": scan.scan_type,
        "status": scan.status,
        "vulnerabilitiesFound": scan.vulnerabilities_found,
        "createdAt": scan.created_at.isoformat() if scan.created_at else None,
    }


@router.get("/vulnerability-scan/vulnerabilities")
async def get_vulnerability_scans(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    repo = _get_repository(db)
    scans = repo.get_vulnerability_scans(status=status)
    return {
        "vulnerabilities": [_vulnerability_scan_dict(s) for s in scans],
        "total": len(scans),
    }


@router.post("/vulnerability-scan/vulnerabilities")
async def create_vulnerability_scan(
    req: VulnerabilityScanCreateRequest,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    repo = _get_repository(db)
    scan = repo.create_vulnerability_scan(target=req.target, scan_type=req.scanType)
    logger.info("创建漏洞扫描: %s", req.target)
    return _vulnerability_scan_dict(scan)


@router.patch("/vulnerability-scan/vulnerabilities/{scan_id}")
async def update_vulnerability_scan(
    scan_id: str,
    req: VulnerabilityScanUpdateRequest,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    repo = _get_repository(db)
    scan = repo.update_vulnerability_scan(scan_id, status=req.status)
    if not scan:
        raise HTTPException(status_code=404, detail="扫描不存在")
    logger.info("更新漏洞扫描: %s", scan_id)
    return _vulnerability_scan_dict(scan)


# 20. Audit Center
class AuditReportCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=128)
    reportType: str = Field(default="security", max_length=50)
    description: Optional[str] = None


class AuditReportUpdateRequest(BaseModel):
    status: Optional[Literal["draft", "published"]] = None


def _audit_report_dict(report: Any) -> Dict[str, Any]:
    return {
        "id": report.id,
        "title": report.title,
        "reportType": report.report_type,
        "description": report.description,
        "status": report.status,
        "publishedAt": report.published_at.isoformat() if report.published_at else None,
        "createdAt": report.created_at.isoformat() if report.created_at else None,
    }


@router.get("/audit-center/reports")
async def get_audit_reports(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    repo = _get_repository(db)
    reports = repo.get_audit_reports(status=status)
    return {"reports": [_audit_report_dict(r) for r in reports], "total": len(reports)}


@router.post("/audit-center/reports")
async def create_audit_report(
    req: AuditReportCreateRequest,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    repo = _get_repository(db)
    report = repo.create_audit_report(
        title=req.title,
        report_type=req.reportType,
        description=req.description,
    )
    logger.info("创建审计报告: %s", req.title)
    return _audit_report_dict(report)


@router.patch("/audit-center/reports/{report_id}")
async def update_audit_report(
    report_id: str,
    req: AuditReportUpdateRequest,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    repo = _get_repository(db)
    report = repo.update_audit_report(report_id, status=req.status)
    if not report:
        raise HTTPException(status_code=404, detail="报告不存在")
    logger.info("更新审计报告: %s", report_id)
    return _audit_report_dict(report)


# 21. Operation Records
@router.get("/operation-records")
async def get_operation_records(
    limit: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    repo = _get_repository(db)
    records = repo.get_security_operation_records(limit=limit)
    return {
        "records": [
            {
                "id": r.id,
                "operation": r.operation,
                "operationType": r.operation_type,
                "targetResource": r.target_resource,
                "executor": r.executor,
                "result": r.result,
                "timestamp": r.timestamp.isoformat() if r.timestamp else None,
                "durationMs": r.duration_ms,
            }
            for r in records
        ],
        "total": len(records),
    }


# 22. Audit Logs
@router.get("/audit/logs")
async def get_audit_logs(limit: int = Query(default=50, ge=1, le=500)) -> Dict[str, Any]:
    logs = get_audit_log(limit)
    return {"logs": logs, "total": len(logs)}


# 23. Command Rewrite
class CommandRewriteRuleCreateRequest(BaseModel):
    pattern: str = Field(..., min_length=1, max_length=256)
    replacement: str = Field(..., min_length=1, max_length=256)
    description: Optional[str] = None


class CommandRewriteRuleUpdateRequest(BaseModel):
    enabled: Optional[bool] = None


def _command_rewrite_dict(rule: Any) -> Dict[str, Any]:
    return {
        "id": rule.id,
        "pattern": rule.pattern,
        "replacement": rule.replacement,
        "description": rule.description,
        "enabled": rule.enabled,
        "priority": rule.priority,
        "usageCount": rule.usage_count,
    }


@router.get("/command-rewrite/rules")
async def get_command_rewrite_rules(
    enabled: Optional[bool] = None,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    repo = _get_repository(db)
    rules = repo.get_command_rewrite_rules(enabled=enabled)
    return {"rules": [_command_rewrite_dict(r) for r in rules], "total": len(rules)}


@router.post("/command-rewrite/rules")
async def create_command_rewrite_rule(
    req: CommandRewriteRuleCreateRequest,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    repo = _get_repository(db)
    rule = repo.create_command_rewrite_rule(
        pattern=req.pattern,
        replacement=req.replacement,
        description=req.description,
    )
    logger.info("创建命令改写规则: %s", req.pattern)
    return _command_rewrite_dict(rule)


@router.patch("/command-rewrite/rules/{rule_id}")
async def update_command_rewrite_rule(
    rule_id: str,
    req: CommandRewriteRuleUpdateRequest,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    repo = _get_repository(db)
    rule = repo.update_command_rewrite_rule(rule_id, enabled=req.enabled)
    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")
    logger.info("更新命令改写规则: %s", rule_id)
    return _command_rewrite_dict(rule)


@router.delete("/command-rewrite/rules/{rule_id}")
async def delete_command_rewrite_rule(
    rule_id: str,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    repo = _get_repository(db)
    success = repo.delete_command_rewrite_rule(rule_id)
    if not success:
        raise HTTPException(status_code=404, detail="规则不存在")
    logger.info("删除命令改写规则: %s", rule_id)
    return {"success": True}


# 24. Command Check
class SecurityAdvancedCommandCheckRequest(BaseModel):
    command: str = Field(..., min_length=1, max_length=2000)


@router.post("/command-check/check")
async def check_command(req: SecurityAdvancedCommandCheckRequest) -> Dict[str, Any]:
    result = analyze_command(req.command)
    return {
        "command": req.command,
        "risk_level": result["risk_level"].value,
        "risk_name": result.get("risk_name", ""),
        "reason": result.get("reason", ""),
        "action": result.get("action", ""),
        "safe_alternative": result.get("safe_alternative", ""),
    }


# 25. Command Guard
class CommandGuardRuleCreateRequest(BaseModel):
    command: str = Field(..., min_length=1, max_length=256)
    pattern: str = Field(..., min_length=1, max_length=256)
    severity: Literal["critical", "high", "medium", "low"] = Field(default="high")
    action: Literal["block", "warn", "allow"] = Field(default="block")
    description: Optional[str] = None


class CommandGuardRuleUpdateRequest(BaseModel):
    enabled: Optional[bool] = None


def _command_guard_dict(rule: Any) -> Dict[str, Any]:
    return {
        "id": rule.id,
        "command": rule.command,
        "pattern": rule.pattern,
        "severity": rule.severity,
        "action": rule.action,
        "description": rule.description,
        "enabled": rule.enabled,
        "triggerCount": rule.trigger_count,
    }


@router.get("/command-guard/rules")
async def get_command_guard_rules(
    enabled: Optional[bool] = None,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    repo = _get_repository(db)
    rules = repo.get_command_guard_rules(enabled=enabled)
    return {"rules": [_command_guard_dict(r) for r in rules], "total": len(rules)}


@router.post("/command-guard/rules")
async def create_command_guard_rule(
    req: CommandGuardRuleCreateRequest,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    repo = _get_repository(db)
    rule = repo.create_command_guard_rule(
        command=req.command,
        pattern=req.pattern,
        severity=req.severity,
        action=req.action,
        description=req.description,
    )
    logger.info("创建命令管控规则: %s", req.command)
    return _command_guard_dict(rule)


@router.patch("/command-guard/rules/{rule_id}")
async def update_command_guard_rule(
    rule_id: str,
    req: CommandGuardRuleUpdateRequest,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    repo = _get_repository(db)
    rule = repo.update_command_guard_rule(rule_id, enabled=req.enabled)
    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")
    logger.info("更新命令管控规则: %s", rule_id)
    return _command_guard_dict(rule)


@router.delete("/command-guard/rules/{rule_id}")
async def delete_command_guard_rule(
    rule_id: str,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    repo = _get_repository(db)
    success = repo.delete_command_guard_rule(rule_id)
    if not success:
        raise HTTPException(status_code=404, detail="规则不存在")
    logger.info("删除命令管控规则: %s", rule_id)
    return {"success": True}
