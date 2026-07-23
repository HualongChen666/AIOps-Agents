# -*- coding: utf-8 -*-
"""
tenant_manager.py
----------------
多租户能力 - 租户管理模块。

功能：
- 租户生命周期管理
- 租户配置管理
- 租户计费
- 租户审计
- 租户报表
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# 1️⃣ 租户状态枚举
# ----------------------------------------------------------------------
class TenantStatus(Enum):
    """租户状态"""

    ACTIVE = "active"
    SUSPENDED = "suspended"
    TERMINATED = "terminated"
    TRIAL = "trial"


# ----------------------------------------------------------------------
# 2️⃣ 租户计划
# ----------------------------------------------------------------------
@dataclass
class TenantPlan:
    """租户计划"""

    id: str
    name: str
    price: float
    features: List[str] = field(default_factory=list)
    limits: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "price": self.price,
            "features": self.features,
            "limits": self.limits,
        }


# ----------------------------------------------------------------------
# 3️⃣ 租户信息
# ----------------------------------------------------------------------
@dataclass
class TenantInfo:
    """租户信息"""

    id: str
    name: str
    email: str
    status: TenantStatus = TenantStatus.TRIAL
    plan_id: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    trial_ends_at: Optional[str] = None
    billing_info: Dict[str, Any] = field(default_factory=dict)
    settings: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "status": self.status.value,
            "plan_id": self.plan_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "trial_ends_at": self.trial_ends_at,
            "billing_info": self.billing_info,
            "settings": self.settings,
        }


# ----------------------------------------------------------------------
# 4️⃣ 租户管理器
# ----------------------------------------------------------------------
class TenantManager:
    """租户管理器"""

    def __init__(self):
        self.tenants: Dict[str, TenantInfo] = {}
        self.plans: Dict[str, TenantPlan] = {}
        self.audit_log: List[Dict[str, Any]] = []

        self._initialize_default_plans()

    def _initialize_default_plans(self):
        """初始化默认计划"""
        self.plans["free"] = TenantPlan(
            id="free",
            name="Free",
            price=0.0,
            features=["basic_monitoring", "limited_alerts"],
            limits={"users": 1, "services": 5, "retention_days": 7},
        )

        self.plans["pro"] = TenantPlan(
            id="pro",
            name="Pro",
            price=99.0,
            features=["full_monitoring", "unlimited_alerts", "ai_analysis"],
            limits={"users": 10, "services": 50, "retention_days": 30},
        )

        self.plans["enterprise"] = TenantPlan(
            id="enterprise",
            name="Enterprise",
            price=499.0,
            features=["full_monitoring", "unlimited_alerts", "ai_analysis", "multi_region", "sla"],
            limits={"users": -1, "services": -1, "retention_days": 90},
        )

    def create_tenant(
        self,
        name: str,
        email: str,
        plan_id: str = "free",
        trial_days: int = 14,
    ) -> TenantInfo:
        """
        创建租户

        Parameters
        ----------
        name : str
            租户名称
        email : str
            邮箱
        plan_id : str
            计划 ID
        trial_days : int
            试用天数

        Returns
        -------
        TenantInfo
            租户信息
        """
        tenant_id = f"tenant-{int(datetime.now().timestamp())}"

        trial_ends = datetime.now() + timedelta(days=trial_days)

        tenant = TenantInfo(
            id=tenant_id,
            name=name,
            email=email,
            status=TenantStatus.TRIAL,
            plan_id=plan_id,
            trial_ends_at=trial_ends.isoformat(),
        )

        self.tenants[tenant_id] = tenant

        self._log_audit("create_tenant", tenant_id, {"name": name, "email": email})

        logger.info(f"Created tenant: {name} ({tenant_id})")
        return tenant

    def update_tenant(
        self,
        tenant_id: str,
        **kwargs,
    ) -> bool:
        """
        更新租户

        Parameters
        ----------
        tenant_id : str
            租户 ID
        **kwargs
            更新字段

        Returns
        -------
        bool
            是否成功
        """
        if tenant_id not in self.tenants:
            logger.warning(f"Tenant not found: {tenant_id}")
            return False

        tenant = self.tenants[tenant_id]

        for key, value in kwargs.items():
            if hasattr(tenant, key):
                setattr(tenant, key, value)

        tenant.updated_at = datetime.now().isoformat()

        self._log_audit("update_tenant", tenant_id, kwargs)

        logger.info(f"Updated tenant: {tenant_id}")
        return True

    def suspend_tenant(self, tenant_id: str, reason: str = "") -> bool:
        """
        暂停租户

        Parameters
        ----------
        tenant_id : str
            租户 ID
        reason : str
            原因

        Returns
        -------
        bool
            是否成功
        """
        if tenant_id not in self.tenants:
            return False

        self.tenants[tenant_id].status = TenantStatus.SUSPENDED
        self.tenants[tenant_id].updated_at = datetime.now().isoformat()

        self._log_audit("suspend_tenant", tenant_id, {"reason": reason})

        logger.info(f"Suspended tenant: {tenant_id}, reason: {reason}")
        return True

    def activate_tenant(self, tenant_id: str) -> bool:
        """
        激活租户

        Parameters
        ----------
        tenant_id : str
            租户 ID

        Returns
        -------
        bool
            是否成功
        """
        if tenant_id not in self.tenants:
            return False

        self.tenants[tenant_id].status = TenantStatus.ACTIVE
        self.tenants[tenant_id].updated_at = datetime.now().isoformat()

        self._log_audit("activate_tenant", tenant_id, {})

        logger.info(f"Activated tenant: {tenant_id}")
        return True

    def terminate_tenant(self, tenant_id: str, reason: str = "") -> bool:
        """
        终止租户

        Parameters
        ----------
        tenant_id : str
            租户 ID
        reason : str
            原因

        Returns
        -------
        bool
            是否成功
        """
        if tenant_id not in self.tenants:
            return False

        self.tenants[tenant_id].status = TenantStatus.TERMINATED
        self.tenants[tenant_id].updated_at = datetime.now().isoformat()

        self._log_audit("terminate_tenant", tenant_id, {"reason": reason})

        logger.info(f"Terminated tenant: {tenant_id}, reason: {reason}")
        return True

    def change_plan(
        self,
        tenant_id: str,
        new_plan_id: str,
    ) -> bool:
        """
        更改计划

        Parameters
        ----------
        tenant_id : str
            租户 ID
        new_plan_id : str
            新计划 ID

        Returns
        -------
        bool
            是否成功
        """
        if tenant_id not in self.tenants:
            return False

        if new_plan_id not in self.plans:
            logger.warning(f"Plan not found: {new_plan_id}")
            return False

        old_plan_id = self.tenants[tenant_id].plan_id
        self.tenants[tenant_id].plan_id = new_plan_id
        self.tenants[tenant_id].updated_at = datetime.now().isoformat()

        self._log_audit(
            "change_plan",
            tenant_id,
            {
                "old_plan": old_plan_id,
                "new_plan": new_plan_id,
            },
        )

        logger.info(f"Changed plan for tenant {tenant_id}: {old_plan_id} -> {new_plan_id}")
        return True

    def get_tenant(self, tenant_id: str) -> Optional[TenantInfo]:
        """获取租户"""
        return self.tenants.get(tenant_id)

    def list_tenants(
        self,
        status: Optional[TenantStatus] = None,
    ) -> List[TenantInfo]:
        """
        列出租户

        Parameters
        ----------
        status : TenantStatus, optional
            状态过滤

        Returns
        -------
        List[TenantInfo]
            租户列表
        """
        tenants = list(self.tenants.values())

        if status is not None:
            tenants = [t for t in tenants if t.status == status]

        return tenants

    def check_trial_expiration(self) -> List[str]:
        """
        检查试用过期

        Returns
        -------
        List[str]
            过期的租户 ID 列表
        """
        expired_tenants = []
        now = datetime.now()

        for tenant_id, tenant in self.tenants.items():
            if tenant.status == TenantStatus.TRIAL and tenant.trial_ends_at:
                trial_end = datetime.fromisoformat(tenant.trial_ends_at)
                if now > trial_end:
                    expired_tenants.append(tenant_id)

        return expired_tenants

    def get_plan(self, plan_id: str) -> Optional[TenantPlan]:
        """获取计划"""
        return self.plans.get(plan_id)

    def list_plans(self) -> List[TenantPlan]:
        """列出所有计划"""
        return list(self.plans.values())

    def _log_audit(
        self,
        action: str,
        tenant_id: str,
        details: Dict[str, Any],
    ):
        """记录审计日志"""
        self.audit_log.append(
            {
                "timestamp": datetime.now().isoformat(),
                "action": action,
                "tenant_id": tenant_id,
                "details": details,
            }
        )

    def get_audit_log(
        self,
        tenant_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        获取审计日志

        Parameters
        ----------
        tenant_id : str, optional
            租户 ID 过滤
        limit : int
            返回数量限制

        Returns
        -------
        List[Dict[str, Any]]
            审计日志
        """
        logs = self.audit_log

        if tenant_id is not None:
            logs = [log for log in logs if log["tenant_id"] == tenant_id]

        return logs[-limit:]

    def get_usage_report(
        self,
        tenant_id: str,
    ) -> Dict[str, Any]:
        """
        获取使用报告

        Parameters
        ----------
        tenant_id : str
            租户 ID

        Returns
        -------
        Dict[str, Any]
            使用报告
        """
        tenant = self.get_tenant(tenant_id)
        if tenant is None:
            return {}

        plan = self.get_plan(tenant.plan_id)

        return {
            "tenant_id": tenant_id,
            "tenant_name": tenant.name,
            "plan": plan.to_dict() if plan else None,
            "status": tenant.status.value,
            "created_at": tenant.created_at,
            "trial_ends_at": tenant.trial_ends_at,
        }

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        status_counts: Dict[str, int] = {}
        for tenant in self.tenants.values():
            status = tenant.status.value
            status_counts[status] = status_counts.get(status, 0) + 1

        plan_counts: Dict[str, int] = {}
        for tenant in self.tenants.values():
            plan = tenant.plan_id
            plan_counts[plan] = plan_counts.get(plan, 0) + 1

        return {
            "total_tenants": len(self.tenants),
            "status_distribution": status_counts,
            "plan_distribution": plan_counts,
            "total_plans": len(self.plans),
        }


# ----------------------------------------------------------------------
# 5️⃣ 工厂函数
# ----------------------------------------------------------------------
def create_tenant_manager() -> TenantManager:
    """创建租户管理器"""
    return TenantManager()


# ----------------------------------------------------------------------
# 6️⃣ CLI 用于快速测试
# ----------------------------------------------------------------------
if __name__ == "__main__":  # pragma: no cover

    logging.basicConfig(level=logging.INFO)

    # 测试租户管理器
    logger.info("Testing tenant manager")

    manager = create_tenant_manager()

    # 创建租户
    tenant1 = manager.create_tenant(
        name="Acme Corp",
        email="admin@acme.com",
        plan_id="pro",
        trial_days=14,
    )

    tenant2 = manager.create_tenant(
        name="Beta Inc",
        email="admin@beta.com",
        plan_id="free",
    )

    logger.info(f"Created tenants: {tenant1.name}, {tenant2.name}")

    # 更新租户
    manager.update_tenant(tenant1.id, settings={"theme": "dark"})

    # 更改计划
    manager.change_plan(tenant2.id, "pro")

    # 列出租户
    active_tenants = manager.list_tenants(status=TenantStatus.ACTIVE)
    logger.info(f"Active tenants: {len(active_tenants)}")

    # 获取使用报告
    report = manager.get_usage_report(tenant1.id)
    logger.info(f"Usage report: {report}")

    # 获取统计
    stats = manager.get_statistics()
    logger.info(f"Statistics: {stats}")

    # 获取审计日志
    audit_log = manager.get_audit_log(tenant1.id)
    logger.info(f"Audit log entries: {len(audit_log)}")

    logger.info("Test passed!")
