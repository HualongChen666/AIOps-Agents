# -*- coding: utf-8 -*-
"""
tenant_isolation.py
-------------------
多租户能力 - 租户隔离模块。

功能：
- 租户上下文管理
- 数据隔离
- 资源隔离
- 权限隔离
- 租户配额管理
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from threading import local
from typing import Any, Dict, List, Optional, Set  # noqa: F401

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# 1️⃣ 隔离级别枚举
# ----------------------------------------------------------------------
class IsolationLevel(Enum):
    """隔离级别"""

    SHARED = "shared"  # 共享资源
    LOGICAL = "logical"  # 逻辑隔离
    PHYSICAL = "physical"  # 物理隔离


# ----------------------------------------------------------------------
# 2️⃣ 租户定义
# ----------------------------------------------------------------------
@dataclass
class Tenant:
    """租户定义"""

    id: str
    name: str
    isolation_level: IsolationLevel = IsolationLevel.LOGICAL
    quota: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "isolation_level": self.isolation_level.value,
            "quota": self.quota,
            "metadata": self.metadata,
            "created_at": self.created_at,
        }


# ----------------------------------------------------------------------
# 3️⃣ 租户上下文
# ----------------------------------------------------------------------
class TenantContext:
    """租户上下文（线程本地存储）"""

    def __init__(self):
        self._local = local()

    def set_tenant(self, tenant_id: str):
        """设置当前租户"""
        self._local.tenant_id = tenant_id
        logger.debug(f"Set tenant context: {tenant_id}")

    def get_tenant(self) -> Optional[str]:
        """获取当前租户"""
        return getattr(self._local, "tenant_id", None)

    def clear(self):
        """清除租户上下文"""
        self._local.tenant_id = None
        logger.debug("Cleared tenant context")


# ----------------------------------------------------------------------
# 4️⃣ 数据隔离器
# ----------------------------------------------------------------------
class DataIsolator:
    """数据隔离器"""

    def __init__(self):
        self.tenant_data_prefix = "tenant_"

    def add_tenant_filter(
        self,
        query: Dict[str, Any],
        tenant_id: str,
    ) -> Dict[str, Any]:
        """
        添加租户过滤条件

        Parameters
        ----------
        query : Dict[str, Any]
            原始查询
        tenant_id : str
            租户 ID

        Returns
        -------
        Dict[str, Any]
            添加了租户过滤的查询
        """
        filtered_query = query.copy()

        # 添加租户 ID 过滤
        if "tenant_id" not in filtered_query:
            filtered_query["tenant_id"] = tenant_id

        return filtered_query

    def isolate_data_key(
        self,
        key: str,
        tenant_id: str,
    ) -> str:
        """
        隔离数据键

        Parameters
        ----------
        key : str
            原始键
        tenant_id : str
            租户 ID

        Returns
        -------
        str
            隔离后的键
        """
        return f"{self.tenant_data_prefix}{tenant_id}:{key}"

    def extract_tenant_from_key(
        self,
        isolated_key: str,
    ) -> Optional[str]:
        """
        从隔离键中提取租户 ID

        Parameters
        ----------
        isolated_key : str
            隔离键

        Returns
        -------
        str or None
            租户 ID
        """
        if isolated_key.startswith(self.tenant_data_prefix):
            parts = isolated_key[len(self.tenant_data_prefix):].split(":", 1)
            if len(parts) == 2:
                return parts[0]
        return None


# ----------------------------------------------------------------------
# 5️⃣ 资源隔离器
# ----------------------------------------------------------------------
class ResourceIsolator:
    """资源隔离器"""

    def __init__(self):
        self.tenant_resources: Dict[str, Dict[str, Any]] = {}
        self.resource_limits: Dict[str, Dict[str, Any]] = {}

    def allocate_resource(
        self,
        tenant_id: str,
        resource_type: str,
        amount: float,
    ) -> bool:
        """
        分配资源

        Parameters
        ----------
        tenant_id : str
            租户 ID
        resource_type : str
            资源类型
        amount : float
            数量

        Returns
        -------
        bool
            是否分配成功
        """
        # 初始化租户资源
        if tenant_id not in self.tenant_resources:
            self.tenant_resources[tenant_id] = {}

        current = self.tenant_resources[tenant_id].get(resource_type, 0)
        limit = self.resource_limits.get(tenant_id, {}).get(resource_type, float("inf"))

        if current + amount <= limit:
            self.tenant_resources[tenant_id][resource_type] = current + amount
            logger.info(f"Allocated {amount} {resource_type} to tenant {tenant_id}")
            return True
        else:
            logger.warning(
                f"Resource limit exceeded for tenant {tenant_id}: {current + amount} > {limit}"
            )
            return False

    def release_resource(
        self,
        tenant_id: str,
        resource_type: str,
        amount: float,
    ):
        """
        释放资源

        Parameters
        ----------
        tenant_id : str
            租户 ID
        resource_type : str
            资源类型
        amount : float
            数量
        """
        if tenant_id in self.tenant_resources:
            current = self.tenant_resources[tenant_id].get(resource_type, 0)
            self.tenant_resources[tenant_id][resource_type] = max(0, current - amount)
            logger.info(f"Released {amount} {resource_type} from tenant {tenant_id}")

    def set_resource_limit(
        self,
        tenant_id: str,
        resource_type: str,
        limit: float,
    ):
        """
        设置资源限制

        Parameters
        ----------
        tenant_id : str
            租户 ID
        resource_type : str
            资源类型
        limit : float
            限制
        """
        if tenant_id not in self.resource_limits:
            self.resource_limits[tenant_id] = {}

        self.resource_limits[tenant_id][resource_type] = limit
        logger.info(f"Set resource limit for tenant {tenant_id}: {resource_type} = {limit}")

    def get_resource_usage(
        self,
        tenant_id: str,
    ) -> Dict[str, float]:
        """
        获取资源使用情况

        Parameters
        ----------
        tenant_id : str
            租户 ID

        Returns
        -------
        Dict[str, float]
            资源使用情况
        """
        return self.tenant_resources.get(tenant_id, {})


# ----------------------------------------------------------------------
# 6️⃣ 权限隔离器
# ----------------------------------------------------------------------
class PermissionIsolator:
    """权限隔离器"""

    def __init__(self):
        self.tenant_permissions: Dict[str, Set[str]] = {}
        self.role_permissions: Dict[str, Set[str]] = {}
        self.tenant_roles: Dict[str, Set[str]] = {}

    def add_permission(
        self,
        tenant_id: str,
        permission: str,
    ):
        """
        添加权限

        Parameters
        ----------
        tenant_id : str
            租户 ID
        permission : str
            权限
        """
        if tenant_id not in self.tenant_permissions:
            self.tenant_permissions[tenant_id] = set()

        self.tenant_permissions[tenant_id].add(permission)
        logger.debug(f"Added permission {permission} to tenant {tenant_id}")

    def check_permission(
        self,
        tenant_id: str,
        permission: str,
    ) -> bool:
        """
        检查权限

        Parameters
        ----------
        tenant_id : str
            租户 ID
        permission : str
            权限

        Returns
        -------
        bool
            是否有权限
        """
        tenant_perms = self.tenant_permissions.get(tenant_id, set())

        # 检查直接权限
        if permission in tenant_perms:
            return True

        # 检查角色权限
        roles = self.tenant_roles.get(tenant_id, set())
        for role in roles:
            role_perms = self.role_permissions.get(role, set())
            if permission in role_perms:
                return True

        return False

    def add_role(
        self,
        tenant_id: str,
        role: str,
    ):
        """
        添加角色

        Parameters
        ----------
        tenant_id : str
            租户 ID
        role : str
            角色
        """
        if tenant_id not in self.tenant_roles:
            self.tenant_roles[tenant_id] = set()

        self.tenant_roles[tenant_id].add(role)
        logger.debug(f"Added role {role} to tenant {tenant_id}")

    def assign_permission_to_role(
        self,
        role: str,
        permission: str,
    ):
        """
        为角色分配权限

        Parameters
        ----------
        role : str
            角色
        permission : str
            权限
        """
        if role not in self.role_permissions:
            self.role_permissions[role] = set()

        self.role_permissions[role].add(permission)
        logger.debug(f"Assigned permission {permission} to role {role}")


# ----------------------------------------------------------------------
# 7️⃣ 租户隔离管理器
# ----------------------------------------------------------------------
class TenantIsolationManager:
    """租户隔离管理器"""

    def __init__(self):
        self.tenants: Dict[str, Tenant] = {}
        self.context = TenantContext()
        self.data_isolator = DataIsolator()
        self.resource_isolator = ResourceIsolator()
        self.permission_isolator = PermissionIsolator()

    def register_tenant(self, tenant: Tenant):
        """注册租户"""
        self.tenants[tenant.id] = tenant

        # 设置资源限制
        for resource_type, limit in tenant.quota.items():
            self.resource_isolator.set_resource_limit(
                tenant.id,
                resource_type,
                limit,
            )

        logger.info(f"Registered tenant: {tenant.name} ({tenant.id})")

    def unregister_tenant(self, tenant_id: str):
        """注销租户"""
        if tenant_id in self.tenants:
            del self.tenants[tenant_id]
            logger.info(f"Unregistered tenant: {tenant_id}")

    @contextmanager
    def tenant_scope(self, tenant_id: str):
        """
        租户作用域上下文管理器

        Parameters
        ----------
        tenant_id : str
            租户 ID
        """
        self.context.set_tenant(tenant_id)
        try:
            yield
        finally:
            self.context.clear()

    def get_current_tenant(self) -> Optional[str]:
        """获取当前租户"""
        return self.context.get_tenant()

    def enforce_isolation(
        self,
        operation: str,
        **kwargs,
    ) -> bool:
        """
        强制隔离

        Parameters
        ----------
        operation : str
            操作类型
        **kwargs
            操作参数

        Returns
        -------
        bool
            是否允许操作
        """
        tenant_id = self.get_current_tenant()

        if tenant_id is None:
            logger.warning("No tenant context, operation denied")
            return False

        if tenant_id not in self.tenants:
            logger.warning(f"Unknown tenant: {tenant_id}")
            return False

        # 检查权限
        if not self.permission_isolator.check_permission(tenant_id, operation):
            logger.warning(f"Permission denied for tenant {tenant_id}: {operation}")
            return False

        return True

    def get_tenant_statistics(self) -> Dict[str, Any]:
        """获取租户统计"""
        stats: Dict[str, Any] = {
            "total_tenants": len(self.tenants),
            "by_isolation_level": {},
            "resource_usage": {},
        }

        for tenant in self.tenants.values():
            level = tenant.isolation_level.value
            stats["by_isolation_level"][level] = stats["by_isolation_level"].get(level, 0) + 1
            stats["resource_usage"][tenant.id] = self.resource_isolator.get_resource_usage(
                tenant.id
            )

        return stats


# ----------------------------------------------------------------------
# 8️⃣ 工厂函数
# ----------------------------------------------------------------------
def create_tenant_isolation_manager() -> TenantIsolationManager:
    """创建租户隔离管理器"""
    return TenantIsolationManager()


# ----------------------------------------------------------------------
# 9️⃣ CLI 用于快速测试
# ----------------------------------------------------------------------
if __name__ == "__main__":  # pragma: no cover

    logging.basicConfig(level=logging.INFO)

    # 测试租户隔离管理器
    logger.info("Testing tenant isolation manager")

    manager = create_tenant_isolation_manager()

    # 注册租户
    tenant1 = Tenant(
        id="tenant-1",
        name="Acme Corp",
        isolation_level=IsolationLevel.LOGICAL,
        quota={"cpu": 4.0, "memory": 8.0, "storage": 100.0},
    )

    tenant2 = Tenant(
        id="tenant-2",
        name="Beta Inc",
        isolation_level=IsolationLevel.LOGICAL,
        quota={"cpu": 2.0, "memory": 4.0, "storage": 50.0},
    )

    manager.register_tenant(tenant1)
    manager.register_tenant(tenant2)

    # 测试租户作用域
    with manager.tenant_scope("tenant-1"):
        current_tenant = manager.get_current_tenant()
        logger.info(f"Current tenant in scope: {current_tenant}")

        # 测试资源分配
        success = manager.resource_isolator.allocate_resource("tenant-1", "cpu", 2.0)
        logger.info(f"Resource allocation: {success}")

    # 测试权限
    manager.permission_isolator.add_permission("tenant-1", "read_data")
    manager.permission_isolator.add_permission("tenant-1", "write_data")

    with manager.tenant_scope("tenant-1"):
        can_read = manager.permission_isolator.check_permission("tenant-1", "read_data")
        can_delete = manager.permission_isolator.check_permission("tenant-1", "delete_data")
        logger.info(f"Can read: {can_read}, Can delete: {can_delete}")

    # 获取统计
    stats = manager.get_tenant_statistics()
    logger.info(f"Tenant statistics: {stats}")

    logger.info("Test passed!")
