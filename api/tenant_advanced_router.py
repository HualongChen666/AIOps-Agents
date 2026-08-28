# -*- coding: utf-8 -*-
"""Advanced Tenant API router for config, limits, usage, billing, members."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, Field

from core.authentication import UserInDB, get_user, verify_token
from core.api_helpers import create_success_response, create_error_response
from core.database import get_db
from core.models import TenantConfigDB, TenantSettingsDB, TenantMemberDB
from core.tenant_engine import (
    _PLAN_LIMITS,
    get_tenant,
    update_tenant,
)
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/tenant", tags=["tenant-advanced"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token", auto_error=False)

# 开发环境占位
FAKE_ADMIN = UserInDB(
    username="dev-admin",
    full_name="Dev Admin",
    email="dev@example.com",
    role="admin",
    disabled=False,
    hashed_password="",
)


async def get_current_user(token: Optional[str] = Depends(oauth2_scheme)) -> UserInDB:
    """获取当前用户；无 token 时返回开发占位 admin。"""
    if not token:
        return FAKE_ADMIN
    payload = verify_token(token)
    if not payload:
        return FAKE_ADMIN
    username = payload.get("sub")
    if not username:
        return FAKE_ADMIN
    user = await get_user(username)
    if not user:
        return FAKE_ADMIN
    if user.disabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="User account is disabled"
        )
    return user


async def require_admin(current_user: UserInDB = Depends(get_current_user)) -> UserInDB:
    """要求管理员权限"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required"
        )
    return current_user


def get_client_ip(request: Request) -> str:
    """获取客户端IP地址"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


# ============ Config Models ============
class TenantConfig(BaseModel):
    tenant_id: str
    name: str
    domain: Optional[str] = None
    logo_url: Optional[str] = None
    primary_color: Optional[str] = "#0066cc"
    secondary_color: Optional[str] = "#004499"
    custom_css: Optional[str] = None
    custom_js: Optional[str] = None
    branding_enabled: bool = False
    sso_enabled: bool = False
    sso_provider: Optional[str] = None
    sso_config: Optional[Dict[str, Any]] = None
    audit_logging_enabled: bool = True
    data_retention_days: int = 90
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    model_config = {"extra": "ignore"}


# ============ Settings Models ============
class TenantSettings(BaseModel):
    tenant_id: str
    notification_enabled: bool = True
    notification_channels: List[str] = Field(default_factory=list)
    alert_thresholds: Dict[str, Any] = Field(default_factory=dict)
    maintenance_windows: List[Dict[str, Any]] = Field(default_factory=list)
    backup_schedule: Optional[str] = None
    security_policies: Dict[str, Any] = Field(default_factory=dict)
    compliance_settings: Dict[str, Any] = Field(default_factory=dict)
    integration_settings: Dict[str, Any] = Field(default_factory=dict)

    model_config = {"extra": "ignore"}


class TenantSettingsUpdate(BaseModel):
    notification_enabled: Optional[bool] = None
    notification_channels: Optional[List[str]] = None
    alert_thresholds: Optional[Dict[str, Any]] = None
    maintenance_windows: Optional[List[Dict[str, Any]]] = None
    backup_schedule: Optional[str] = None
    security_policies: Optional[Dict[str, Any]] = None
    compliance_settings: Optional[Dict[str, Any]] = None
    integration_settings: Optional[Dict[str, Any]] = None

    model_config = {"extra": "ignore"}


class TenantConfigUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    domain: Optional[str] = Field(None, max_length=255)
    logo_url: Optional[str] = Field(None, max_length=500)
    primary_color: Optional[str] = Field(None, pattern="^#[0-9A-Fa-f]{6}$")
    secondary_color: Optional[str] = Field(None, pattern="^#[0-9A-Fa-f]{6}$")
    custom_css: Optional[str] = None
    custom_js: Optional[str] = None
    branding_enabled: Optional[bool] = None
    sso_enabled: Optional[bool] = None
    sso_provider: Optional[str] = Field(None, max_length=50)
    sso_config: Optional[Dict[str, Any]] = None
    audit_logging_enabled: Optional[bool] = None
    data_retention_days: Optional[int] = Field(None, ge=7, le=3650)

    model_config = {"extra": "ignore"}


# ============ Limits Models ============
class TenantLimits(BaseModel):
    tenant_id: str
    plan: str
    quota: Dict[str, Any]
    limits: Dict[str, Any]
    enforcement_enabled: bool = True
    overage_action: str = "block"  # block, throttle, charge
    warning_threshold: float = 0.8

    model_config = {"extra": "ignore"}


# ============ Usage Models ============
class ResourceUsage(BaseModel):
    resource: str
    used: float
    total: float
    percentage: float
    unit: str


class TenantUsage(BaseModel):
    tenant_id: str
    period: str
    resources: List[ResourceUsage]
    cost: float
    forecast: Optional[Dict[str, Any]] = None

    model_config = {"extra": "ignore"}


# ============ Billing Models ============
class BillingInfo(BaseModel):
    tenant_id: str
    plan: str
    cycle: str
    amount: float
    currency: str
    status: str
    next_billing_date: str
    payment_method: Optional[str] = None
    payment_method_details: Optional[Dict[str, Any]] = None
    invoices: List[Dict[str, Any]]
    usage_summary: Dict[str, Any]

    model_config = {"extra": "ignore"}


# ============ Member Models ============
class TenantMember(BaseModel):
    id: str
    tenant_id: str
    user_id: int
    username: str
    full_name: Optional[str] = None
    email: Optional[str] = None
    role: str  # owner, admin, member, viewer
    permissions: List[str]
    status: str  # active, pending, suspended
    invited_by: Optional[str] = None
    invited_at: Optional[str] = None
    joined_at: Optional[str] = None

    model_config = {"extra": "ignore"}


class TenantMemberCreate(BaseModel):
    user_id: int
    role: str = Field(..., pattern="^(owner|admin|member|viewer)$")
    permissions: List[str] = Field(default_factory=list)

    model_config = {"extra": "ignore"}


class TenantMemberUpdate(BaseModel):
    role: Optional[str] = Field(None, pattern="^(owner|admin|member|viewer)$")
    permissions: Optional[List[str]] = None
    status: Optional[str] = Field(None, pattern="^(active|pending|suspended)$")

    model_config = {"extra": "ignore"}


# ============ Database Helper Functions ============
def _get_tenant_config(db: Session, tenant_id: str) -> TenantConfig:
    """获取租户配置"""
    config = db.query(TenantConfigDB).filter(TenantConfigDB.tenant_id == tenant_id).first()
    
    if not config:
        # 如果数据库中没有，从tenant_engine获取并创建
        tenant = get_tenant(tenant_id)
        if not tenant:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
        
        config = TenantConfigDB(
            tenant_id=tenant_id,
            name=tenant.name,
            domain=None,
            logo_url=None,
            primary_color="#0066cc",
            secondary_color="#004499",
            custom_css=None,
            custom_js=None,
            branding_enabled=False,
            sso_enabled=False,
            sso_provider=None,
            sso_config=None,
            audit_logging_enabled=True,
            data_retention_days=90,
        )
        db.add(config)
        db.commit()
        db.refresh(config)
    
    return TenantConfig(
        tenant_id=config.tenant_id,
        name=config.name,
        domain=config.domain,
        logo_url=config.logo_url,
        primary_color=config.primary_color,
        secondary_color=config.secondary_color,
        custom_css=config.custom_css,
        custom_js=config.custom_js,
        branding_enabled=config.branding_enabled,
        sso_enabled=config.sso_enabled,
        sso_provider=config.sso_provider,
        sso_config=config.sso_config,
        audit_logging_enabled=config.audit_logging_enabled,
        data_retention_days=config.data_retention_days,
        created_at=config.created_at.isoformat() if config.created_at else None,
        updated_at=config.updated_at.isoformat() if config.updated_at else None,
    )


def _get_tenant_members(db: Session, tenant_id: str) -> List[TenantMember]:
    """获取租户成员"""
    members = db.query(TenantMemberDB).filter(TenantMemberDB.tenant_id == tenant_id).all()
    
    if not members:
        # 创建默认成员
        default_member = TenantMemberDB(
            id=f"member-{tenant_id}-1",
            tenant_id=tenant_id,
            user_id="1",
            role="owner",
            email="admin@example.com",
            full_name="系统管理员",
        )
        db.add(default_member)
        db.commit()
        db.refresh(default_member)
        members = [default_member]
    
    return [
        TenantMember(
            id=m.id,
            tenant_id=m.tenant_id,
            user_id=int(m.user_id) if m.user_id.isdigit() else 1,
            username=m.user_id,
            full_name=m.full_name,
            email=m.email,
            role=m.role,
            permissions=["*"] if m.role == "owner" else ["read"],
            status="active",
            invited_by="system",
            invited_at=m.created_at.isoformat() if m.created_at else None,
            joined_at=m.created_at.isoformat() if m.created_at else None,
        )
        for m in members
    ]


def _get_tenant_settings(db: Session, tenant_id: str) -> TenantSettings:
    """获取租户设置"""
    settings = db.query(TenantSettingsDB).filter(TenantSettingsDB.tenant_id == tenant_id).first()
    
    if not settings:
        # 创建默认设置
        settings = TenantSettingsDB(
            tenant_id=tenant_id,
            notification_enabled=True,
            notification_channels=["email", "slack"],
            alert_thresholds={"cpu": 80, "memory": 85, "disk": 90},
            maintenance_windows=[],
            backup_schedule="daily",
            security_policies={"password_min_length": 12, "mfa_required": False},
            compliance_settings={"audit_log_retention": 90},
            integration_settings={},
        )
        db.add(settings)
        db.commit()
        db.refresh(settings)
    
    return TenantSettings(
        tenant_id=settings.tenant_id,
        notification_enabled=settings.notification_enabled,
        notification_channels=settings.notification_channels or [],
        alert_thresholds=settings.alert_thresholds or {},
        maintenance_windows=settings.maintenance_windows or [],
        backup_schedule=settings.backup_schedule,
        security_policies=settings.security_policies or {},
        compliance_settings=settings.compliance_settings or {},
        integration_settings=settings.integration_settings or {},
    )


def _calculate_usage_percentage(used: float, total: float) -> float:
    """计算使用百分比"""
    if total == 0:
        return 0.0
    return round((used / total) * 100, 2)


# ============ Config Endpoints ============
@router.get(
    "/configurations",
    response_model=TenantConfig,
    summary="获取租户配置",
    responses={
        (200): {"description": "租户配置"},
        (401): {"description": "未授权"},
        (403): {"description": "权限不足"},
        (404): {"description": "租户不存在"},
    },
)
async def get_tenant_configurations(
    current_user: UserInDB = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TenantConfig:
    """获取当前租户的配置信息"""
    # 使用默认租户ID（实际应该从用户上下文获取）
    tenant_id = "default"
    return _get_tenant_config(db, tenant_id)


@router.patch(
    "/configurations",
    response_model=TenantConfig,
    summary="更新租户配置",
    responses={
        (200): {"description": "租户配置更新成功"},
        (401): {"description": "未授权"},
        (403): {"description": "权限不足"},
        (404): {"description": "租户不存在"},
    },
)
async def update_tenant_configurations(
    config_update: TenantConfigUpdate,
    request: Request,
    current_user: UserInDB = Depends(require_admin),
    db: Session = Depends(get_db),
) -> TenantConfig:
    """更新当前租户的配置"""
    tenant_id = "default"
    config_db = db.query(TenantConfigDB).filter(TenantConfigDB.tenant_id == tenant_id).first()
    
    if not config_db:
        # 如果不存在，先创建
        config = _get_tenant_config(db, tenant_id)
        config_db = db.query(TenantConfigDB).filter(TenantConfigDB.tenant_id == tenant_id).first()

    update_data = config_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if hasattr(config_db, key):
            setattr(config_db, key, value)

    db.commit()
    db.refresh(config_db)

    logger.info(
        f"Tenant config updated | tenant_id={tenant_id} | user={current_user.username} "
        f"| ip={get_client_ip(request)}"
    )

    return _get_tenant_config(db, tenant_id)


# ============ Settings Endpoints ============
@router.get(
    "/settings",
    response_model=TenantSettings,
    summary="获取租户设置",
    responses={
        (200): {"description": "租户设置"},
        (401): {"description": "未授权"},
        (403): {"description": "权限不足"},
    },
)
async def get_tenant_settings_endpoint(
    current_user: UserInDB = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TenantSettings:
    """获取当前租户的设置"""
    tenant_id = "default"
    return _get_tenant_settings(db, tenant_id)


@router.patch(
    "/settings",
    response_model=TenantSettings,
    summary="更新租户设置",
    responses={
        (200): {"description": "租户设置更新成功"},
        (401): {"description": "未授权"},
        (403): {"description": "权限不足"},
    },
)
async def update_tenant_settings_endpoint(
    settings_update: TenantSettingsUpdate,
    request: Request,
    current_user: UserInDB = Depends(require_admin),
    db: Session = Depends(get_db),
) -> TenantSettings:
    """更新当前租户的设置"""
    tenant_id = "default"
    settings_db = db.query(TenantSettingsDB).filter(TenantSettingsDB.tenant_id == tenant_id).first()
    
    if not settings_db:
        # 如果不存在，先创建
        settings = _get_tenant_settings(db, tenant_id)
        settings_db = db.query(TenantSettingsDB).filter(TenantSettingsDB.tenant_id == tenant_id).first()

    update_data = settings_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if hasattr(settings_db, key):
            setattr(settings_db, key, value)

    db.commit()
    db.refresh(settings_db)

    logger.info(
        f"Tenant settings updated | tenant_id={tenant_id} | user={current_user.username} "
        f"| ip={get_client_ip(request)}"
    )

    return _get_tenant_settings(db, tenant_id)


@router.patch(
    "/config",
    response_model=TenantConfig,
    summary="更新租户配置",
    responses={
        (200): {"description": "租户配置更新成功"},
        (401): {"description": "未授权"},
        (403): {"description": "权限不足"},
        (404): {"description": "租户不存在"},
    },
)
async def update_tenant_config(
    tenant_id: str,
    config_update: TenantConfigUpdate,
    request: Request,
    current_user: UserInDB = Depends(require_admin),
    db: Session = Depends(get_db),
) -> TenantConfig:
    """更新指定租户的配置"""
    config_db = db.query(TenantConfigDB).filter(TenantConfigDB.tenant_id == tenant_id).first()
    
    if not config_db:
        # 如果不存在，先创建
        config = _get_tenant_config(db, tenant_id)
        config_db = db.query(TenantConfigDB).filter(TenantConfigDB.tenant_id == tenant_id).first()

    update_data = config_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if hasattr(config_db, key):
            setattr(config_db, key, value)

    db.commit()
    db.refresh(config_db)

    logger.info(
        f"Tenant config updated | tenant_id={tenant_id} | user={current_user.username} "
        f"| ip={get_client_ip(request)}"
    )

    return _get_tenant_config(db, tenant_id)


# ============ Limits Endpoints ============
@router.get(
    "/limits",
    response_model=TenantLimits,
    summary="获取租户限制",
    responses={
        (200): {"description": "租户限制"},
        (401): {"description": "未授权"},
        (404): {"description": "租户不存在"},
    },
)
async def get_tenant_limits(
    tenant_id: str,
    current_user: UserInDB = Depends(get_current_user),
) -> TenantLimits:
    """获取指定租户的资源限制"""
    tenant = get_tenant(tenant_id)
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

    plan_limits = _PLAN_LIMITS.get(tenant.plan, _PLAN_LIMITS["basic"])

    return TenantLimits(
        tenant_id=tenant_id,
        plan=tenant.plan,
        quota={
            "cpu": tenant.quota.cpu,
            "memory": tenant.quota.memory,
            "disk": tenant.quota.disk,
            "maxUsers": tenant.quota.maxUsers,
            "maxServices": tenant.quota.maxServices,
            "maxAlerts": tenant.quota.maxAlerts,
            "maxStorage": tenant.quota.maxStorage,
        },
        limits={
            "cpu": plan_limits["cpu"],
            "memory": plan_limits["memory"],
            "disk": plan_limits["disk"],
            "maxUsers": plan_limits["maxUsers"],
            "maxServices": plan_limits["maxServices"],
            "maxAlerts": plan_limits["maxAlerts"],
            "maxStorage": plan_limits["maxStorage"],
        },
        enforcement_enabled=True,
        overage_action="block",
        warning_threshold=0.8,
    )


# ============ Quotas Endpoints ============
@router.get(
    "/quotas",
    response_model=TenantLimits,
    summary="获取租户配额",
    responses={
        (200): {"description": "租户配额"},
        (401): {"description": "未授权"},
    },
)
async def get_tenant_quotas(
    current_user: UserInDB = Depends(get_current_user),
) -> TenantLimits:
    """获取当前租户的配额信息"""
    tenant_id = "default"
    return await get_tenant_limits(tenant_id, current_user)


@router.patch(
    "/quotas",
    response_model=TenantLimits,
    summary="更新租户配额",
    responses={
        (200): {"description": "租户配额更新成功"},
        (401): {"description": "未授权"},
        (403): {"description": "权限不足"},
    },
)
async def update_tenant_quotas(
    quota_update: Dict[str, Any],
    request: Request,
    current_user: UserInDB = Depends(require_admin),
) -> TenantLimits:
    """更新当前租户的配额"""
    tenant_id = "default"
    tenant = get_tenant(tenant_id)
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

    # 更新配额
    for key, value in quota_update.items():
        if hasattr(tenant.quota, key):
            setattr(tenant.quota, key, value)

    success = update_tenant(tenant_id, quota=tenant.quota.__dict__)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update quota"
        )

    logger.info(
        f"Tenant quota updated | tenant_id={tenant_id} | user={current_user.username} "
        f"| ip={get_client_ip(request)}"
    )

    return await get_tenant_limits(tenant_id, current_user)


# ============ Usage Endpoints ============
@router.get(
    "/usage",
    response_model=TenantUsage,
    summary="获取租户使用情况",
    responses={
        (200): {"description": "租户使用情况"},
        (401): {"description": "未授权"},
        (404): {"description": "租户不存在"},
    },
)
async def get_tenant_usage_endpoint(
    period: str = "current",
    current_user: UserInDB = Depends(get_current_user),
) -> TenantUsage:
    """获取当前租户的资源使用情况"""
    tenant_id = "default"
    tenant = get_tenant(tenant_id)
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

    resources = [
        ResourceUsage(
            resource="CPU",
            used=tenant.usage.cpu,
            total=tenant.quota.cpu,
            percentage=_calculate_usage_percentage(tenant.usage.cpu, tenant.quota.cpu),
            unit="cores",
        ),
        ResourceUsage(
            resource="Memory",
            used=tenant.usage.memory,
            total=tenant.quota.memory,
            percentage=_calculate_usage_percentage(tenant.usage.memory, tenant.quota.memory),
            unit="GB",
        ),
        ResourceUsage(
            resource="Storage",
            used=tenant.usage.storage,
            total=tenant.quota.maxStorage,
            percentage=_calculate_usage_percentage(tenant.usage.storage, tenant.quota.maxStorage),
            unit="GB",
        ),
        ResourceUsage(
            resource="Users",
            used=float(tenant.usage.users),
            total=float(tenant.quota.maxUsers),
            percentage=_calculate_usage_percentage(
                float(tenant.usage.users), float(tenant.quota.maxUsers)
            ),
            unit="count",
        ),
        ResourceUsage(
            resource="Services",
            used=float(tenant.usage.services),
            total=float(tenant.quota.maxServices),
            percentage=_calculate_usage_percentage(
                float(tenant.usage.services), float(tenant.quota.maxServices)
            ),
            unit="count",
        ),
    ]

    plan_limits = _PLAN_LIMITS.get(tenant.plan, _PLAN_LIMITS["basic"])
    cost = plan_limits.get("amount", 0)

    return TenantUsage(
        tenant_id=tenant_id,
        period=period,
        resources=resources,
        cost=float(cost),
        forecast={
            "cpu_next_month": tenant.usage.cpu * 1.1,
            "memory_next_month": tenant.usage.memory * 1.1,
            "storage_next_month": tenant.usage.storage * 1.05,
        },
    )


# ============ Metrics Endpoints ============
@router.get(
    "/metrics",
    summary="获取租户指标",
    responses={
        (200): {"description": "租户指标"},
        (401): {"description": "未授权"},
    },
)
async def get_tenant_metrics(
    period: str = "7d",
    current_user: UserInDB = Depends(get_current_user),
) -> Dict[str, Any]:
    """获取当前租户的性能指标"""
    tenant_id = "default"
    tenant = get_tenant(tenant_id)
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

    # 生成模拟指标数据
    import random
    from datetime import datetime

    now = datetime.now()
    metrics = {
        "tenant_id": tenant_id,
        "period": period,
        "timestamp": now.isoformat(),
        "cpu_usage": {
            "current": tenant.usage.cpu,
            "average": tenant.usage.cpu * 0.9,
            "peak": tenant.usage.cpu * 1.2,
            "unit": "cores",
        },
        "memory_usage": {
            "current": tenant.usage.memory,
            "average": tenant.usage.memory * 0.85,
            "peak": tenant.usage.memory * 1.1,
            "unit": "GB",
        },
        "request_rate": {
            "current": random.randint(100, 500),
            "average": random.randint(80, 400),
            "peak": random.randint(300, 600),
            "unit": "req/s",
        },
        "response_time": {
            "p50": random.randint(50, 100),
            "p95": random.randint(150, 300),
            "p99": random.randint(300, 500),
            "unit": "ms",
        },
        "error_rate": {
            "current": random.uniform(0.1, 0.5),
            "average": random.uniform(0.1, 0.3),
            "unit": "%",
        },
        "uptime": {
            "current": 99.9,
            "sla_target": 99.5,
            "unit": "%",
        },
    }

    return metrics


# ============ Billing Endpoints ============
@router.get(
    "/billing",
    response_model=BillingInfo,
    summary="获取租户账单信息",
    responses={
        (200): {"description": "账单信息"},
        (401): {"description": "未授权"},
        (403): {"description": "权限不足"},
        (404): {"description": "租户不存在"},
    },
)
async def get_tenant_billing_endpoint(
    current_user: UserInDB = Depends(get_current_user),
) -> BillingInfo:
    """获取当前租户的账单信息"""
    tenant_id = "default"
    tenant = get_tenant(tenant_id)
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

    # 生成模拟发票
    invoices = []
    for i in range(3):
        invoice_date = datetime.now() - timedelta(days=30 * (i + 1))
        invoices.append(
            {
                "id": f"INV-{tenant_id}-{i+1:04d}",
                "date": invoice_date.isoformat(),
                "amount": tenant.billing.amount,
                "currency": tenant.billing.currency,
                "status": "paid" if i > 0 else "pending",
                "download_url": f"/api/v1/tenant/{tenant_id}/billing/invoices/{i+1}",
            }
        )

    return BillingInfo(
        tenant_id=tenant_id,
        plan=tenant.plan,
        cycle=tenant.billing.cycle,
        amount=tenant.billing.amount,
        currency=tenant.billing.currency,
        status="active",
        next_billing_date=tenant.billing.nextBillingDate,
        payment_method="credit_card",
        payment_method_details={
            "type": "visa",
            "last4": "4242",
            "expiry": "12/25",
        },
        invoices=invoices,
        usage_summary={
            "current_month_cost": tenant.billing.amount,
            "previous_month_cost": tenant.billing.amount,
            "forecast_next_month": tenant.billing.amount * 1.1,
        },
    )


# ============ Members Endpoints ============
@router.get(
    "/members",
    response_model=List[TenantMember],
    summary="获取租户成员列表",
    responses={
        (200): {"description": "成员列表"},
        (401): {"description": "未授权"},
        (403): {"description": "权限不足"},
        (404): {"description": "租户不存在"},
    },
)
async def get_tenant_members(
    tenant_id: str,
    current_user: UserInDB = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[TenantMember]:
    """获取指定租户的成员列表"""
    # 验证租户存在
    tenant = get_tenant(tenant_id)
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

    return _get_tenant_members(db, tenant_id)


@router.post(
    "/members",
    response_model=TenantMember,
    status_code=status.HTTP_201_CREATED,
    summary="添加租户成员",
    responses={
        (201): {"description": "成员添加成功"},
        (400): {"description": "无效的请求数据"},
        (401): {"description": "未授权"},
        (403): {"description": "权限不足"},
        (404): {"description": "租户不存在"},
    },
)
async def add_tenant_member(
    tenant_id: str,
    member_create: TenantMemberCreate,
    request: Request,
    current_user: UserInDB = Depends(require_admin),
    db: Session = Depends(get_db),
) -> TenantMember:
    """向指定租户添加新成员"""
    # 验证租户存在
    tenant = get_tenant(tenant_id)
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

    # 检查用户是否已是成员
    existing = db.query(TenantMemberDB).filter(
        TenantMemberDB.tenant_id == tenant_id,
        TenantMemberDB.user_id == str(member_create.user_id)
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="User is already a member"
        )

    # 获取用户信息
    from core.user_service import user_service

    user = await user_service.get_user_by_id(member_create.user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # 创建新成员
    new_member_db = TenantMemberDB(
        id=f"member-{tenant_id}-{member_create.user_id}",
        tenant_id=tenant_id,
        user_id=str(member_create.user_id),
        role=member_create.role,
        email=user.email,
        full_name=user.full_name,
    )
    db.add(new_member_db)
    db.commit()
    db.refresh(new_member_db)

    logger.info(
        f"Tenant member added | tenant_id={tenant_id} | user_id={member_create.user_id} | "
        f"invited_by={current_user.username} | ip={get_client_ip(request)}"
    )

    return TenantMember(
        id=new_member_db.id,
        tenant_id=new_member_db.tenant_id,
        user_id=member_create.user_id,
        username=user.username,
        full_name=new_member_db.full_name,
        email=new_member_db.email,
        role=new_member_db.role,
        permissions=member_create.permissions if member_create.permissions else ["read"],
        status="pending",
        invited_by=current_user.username,
        invited_at=new_member_db.created_at.isoformat() if new_member_db.created_at else None,
        joined_at=None,
    )


@router.patch(
    "/members/{member_id}",
    response_model=TenantMember,
    summary="更新租户成员",
    responses={
        (200): {"description": "成员更新成功"},
        (401): {"description": "未授权"},
        (403): {"description": "权限不足"},
        (404): {"description": "成员不存在"},
    },
)
async def update_tenant_member(
    tenant_id: str,
    member_id: str,
    member_update: TenantMemberUpdate,
    request: Request,
    current_user: UserInDB = Depends(require_admin),
    db: Session = Depends(get_db),
) -> TenantMember:
    """更新指定租户成员的信息"""
    member_db = db.query(TenantMemberDB).filter(
        TenantMemberDB.tenant_id == tenant_id,
        TenantMemberDB.id == member_id
    ).first()

    if not member_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")

    update_data = member_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if hasattr(member_db, key):
            setattr(member_db, key, value)

    db.commit()
    db.refresh(member_db)

    logger.info(
        f"Tenant member updated | tenant_id={tenant_id} | member_id={member_id} | "
        f"user={current_user.username} | ip={get_client_ip(request)}"
    )

    members = _get_tenant_members(db, tenant_id)
    for member in members:
        if member.id == member_id:
            return member

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")


@router.delete(
    "/members/{member_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除租户成员",
    responses={
        (204): {"description": "成员删除成功"},
        (401): {"description": "未授权"},
        (403): {"description": "权限不足"},
        (404): {"description": "成员不存在"},
    },
)
async def delete_tenant_member(
    tenant_id: str,
    member_id: str,
    request: Request,
    current_user: UserInDB = Depends(require_admin),
    db: Session = Depends(get_db),
) -> None:
    """从指定租户删除成员"""
    member_db = db.query(TenantMemberDB).filter(
        TenantMemberDB.tenant_id == tenant_id,
        TenantMemberDB.id == member_id
    ).first()

    if not member_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")

    db.delete(member_db)
    db.commit()

    logger.info(
        f"Tenant member deleted | tenant_id={tenant_id} | member_id={member_id} | "
        f"user={current_user.username} | ip={get_client_ip(request)}"
    )
