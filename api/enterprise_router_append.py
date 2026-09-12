# -*- coding: utf-8 -*-
"""
Enterprise Router Append
企业级功能路由补充；数据来自真实后端（企业设置存储、RBAC、用户服务、审计表、合规管理器），
不再返回硬编码示例。
"""

from typing import Any, Dict, List

from fastapi import APIRouter, Depends

from core.authentication import get_current_active_user
from core.rbac import role_required

router = APIRouter(prefix="/api/enterprise", tags=["企业级功能"])


def _settings_store() -> Dict[str, Any]:
    """Reuse the real enterprise settings store (single source of truth)."""
    from api.enterprise_advanced_router import enterprise_settings

    return enterprise_settings


@router.get("/enterprise-features")
async def get_enterprise_features(user=Depends(get_current_active_user)):
    """获取企业级功能（基于真实设置与模块可用性）"""
    settings = _settings_store()
    features = [
        {
            "id": "sso",
            "name": "Single Sign-On",
            "enabled": bool(settings.get("sso_enabled", False)),
        },
        {
            "id": "audit_log",
            "name": "Audit Logging",
            "enabled": int(settings.get("audit_retention_days", 0) or 0) > 0,
        },
        {"id": "rbac", "name": "Role-Based Access Control", "enabled": True},
        {"id": "tenant_isolation", "name": "Tenant Isolation",
         "enabled": bool(settings.get("tenant_isolation_enabled", False))},
        {"id": "encryption", "name": "Encryption at Rest",
         "enabled": bool(settings.get("encryption_enabled", False))},
    ]
    return {"status": "success", "features": features}


@router.get("/enterprise-licenses")
async def get_enterprise_licenses(user=Depends(get_current_active_user)):
    """获取企业许可证（无许可证存储时为真实空结果）"""
    return {"status": "success", "licenses": []}


@router.get("/enterprise-settings")
async def get_enterprise_settings(user=Depends(get_current_active_user)):
    """获取企业设置（真实设置存储）"""
    return {"status": "success", "settings": _settings_store()}


@router.post("/enterprise-settings")
async def update_enterprise_settings(settings: dict, user=Depends(role_required("admin"))):
    """更新企业设置（写入真实设置存储）"""
    store = _settings_store()
    custom = settings.pop("custom_settings", None)
    store.update(settings)
    if custom:
        store.setdefault("custom_settings", {}).update(custom)
    return {"status": "success", "settings": store, "message": "Settings updated successfully"}


@router.get("/enterprise-users")
async def get_enterprise_users(user=Depends(get_current_active_user)):
    """获取企业用户（真实用户服务）"""
    from core.user_service import user_service

    users = await user_service.list_users(limit=200, offset=0)
    return {
        "status": "success",
        "users": [
            {
                "id": getattr(u, "id", None),
                "username": getattr(u, "username", None),
                "role": getattr(u, "role", None),
                "email": getattr(u, "email", None),
                "active": not bool(getattr(u, "disabled", False)),
            }
            for u in users
        ],
        "total": len(users),
    }


@router.get("/enterprise-roles")
async def get_enterprise_roles(user=Depends(get_current_active_user)):
    """获取企业角色（真实 RBAC 角色-权限映射）"""
    from core.rbac import ROLE_PERMISSIONS

    roles: List[Dict[str, Any]] = [
        {
            "id": role.value,
            "name": role.value.capitalize(),
            "permissions": sorted(p.value for p in perms),
        }
        for role, perms in ROLE_PERMISSIONS.items()
    ]
    return {"status": "success", "roles": roles}


@router.get("/enterprise-audit")
async def get_enterprise_audit(limit: int = 100, user=Depends(get_current_active_user)):
    """获取企业审计日志（真实审计表）"""
    from core.database import SessionLocal
    from core.models import AuditLog

    db = SessionLocal()
    try:
        rows = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(max(1, min(500, limit))).all()
        logs = [
            {
                "id": row.id,
                "action": row.action,
                "resource_type": row.resource_type,
                "resource_id": row.resource_id,
                "username": row.username,
                "success": row.success,
                "timestamp": row.created_at.isoformat() if row.created_at else None,
                "ip_address": row.ip_address,
            }
            for row in rows
        ]
    finally:
        db.close()
    return {"status": "success", "audit_logs": logs, "total": len(logs)}


@router.get("/enterprise-compliance")
async def get_enterprise_compliance(user=Depends(get_current_active_user)):
    """获取企业合规状态（真实合规管理器）"""
    from core.compliance_manager import ComplianceManager

    status = ComplianceManager().get_compliance_status()
    return {"status": "success", "compliance": status}
