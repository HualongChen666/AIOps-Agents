# -*- coding: utf-8 -*-
"""
Enterprise Advanced API Router
==============================

Advanced API endpoints for enterprise functionality including:
- Tenant management (CRUD)
- User management (CRUD)
- Role management (CRUD)
- Permission management (CRUD)
- Audit logs
- Enterprise settings
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, status
from loguru import logger
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/v1/enterprise", tags=["企业功能"])

# Try to import enterprise functionality manager
try:
    from core.enterprise_functionality import (
        enterprise_functionality_manager,
    )

    ENTERPRISE_AVAILABLE = True
except ImportError:
    ENTERPRISE_AVAILABLE = False
    logger.warning("Enterprise functionality manager not available")


# Pydantic Models
class TenantCreate(BaseModel):
    """Request model for creating a tenant"""

    tenant_id: Optional[str] = Field(None, description="Tenant ID (auto-generated if not provided)")
    name: str = Field(..., description="Tenant name")
    domain: str = Field(..., description="Tenant domain")
    plan: str = Field(default="standard", description="Subscription plan")
    max_users: int = Field(default=100, ge=1, description="Maximum users")
    settings: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Tenant settings")

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Acme Corp",
                "domain": "acme.com",
                "plan": "enterprise",
                "max_users": 500,
            }
        }
    }


class TenantUpdate(BaseModel):
    """Request model for updating a tenant"""

    name: Optional[str] = Field(None, description="Tenant name")
    domain: Optional[str] = Field(None, description="Tenant domain")
    plan: Optional[str] = Field(None, description="Subscription plan")
    max_users: Optional[int] = Field(None, ge=1, description="Maximum users")
    status: Optional[str] = Field(None, description="Tenant status")
    settings: Optional[Dict[str, Any]] = Field(None, description="Tenant settings")

    model_config = {"json_schema_extra": {"example": {"name": "Updated Name", "status": "active"}}}


class UserCreate(BaseModel):
    """Request model for creating a user"""

    user_id: Optional[str] = Field(None, description="User ID (auto-generated if not provided)")
    tenant_id: str = Field(..., description="Tenant ID")
    username: str = Field(..., description="Username")
    email: str = Field(..., description="Email address")
    full_name: str = Field(..., description="Full name")
    role_id: Optional[str] = Field(None, description="Role ID")
    status: str = Field(default="active", description="User status")
    attributes: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="User attributes"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "tenant_id": "tenant-001",
                "username": "johndoe",
                "email": "john@acme.com",
                "full_name": "John Doe",
                "role_id": "role-001",
            }
        }
    }


class UserUpdate(BaseModel):
    """Request model for updating a user"""

    username: Optional[str] = Field(None, description="Username")
    email: Optional[str] = Field(None, description="Email address")
    full_name: Optional[str] = Field(None, description="Full name")
    role_id: Optional[str] = Field(None, description="Role ID")
    status: Optional[str] = Field(None, description="User status")
    attributes: Optional[Dict[str, Any]] = Field(None, description="User attributes")

    model_config = {
        "json_schema_extra": {"example": {"status": "active", "full_name": "John Smith"}}
    }


class RoleCreate(BaseModel):
    """Request model for creating a role"""

    role_id: Optional[str] = Field(None, description="Role ID (auto-generated if not provided)")
    tenant_id: str = Field(..., description="Tenant ID")
    name: str = Field(..., description="Role name")
    description: str = Field(..., description="Role description")
    permissions: List[str] = Field(default_factory=list, description="Permission IDs")
    is_system_role: bool = Field(default=False, description="Is system role")

    model_config = {
        "json_schema_extra": {
            "example": {
                "tenant_id": "tenant-001",
                "name": "Admin",
                "description": "Administrator role",
                "permissions": ["perm-001", "perm-002"],
            }
        }
    }


class RoleUpdate(BaseModel):
    """Request model for updating a role"""

    name: Optional[str] = Field(None, description="Role name")
    description: Optional[str] = Field(None, description="Role description")
    permissions: Optional[List[str]] = Field(None, description="Permission IDs")

    model_config = {
        "json_schema_extra": {
            "example": {
                "description": "Updated description",
                "permissions": ["perm-001", "perm-003"],
            }
        }
    }


class PermissionCreate(BaseModel):
    """Request model for creating a permission"""

    permission_id: Optional[str] = Field(
        None, description="Permission ID (auto-generated if not provided)"
    )
    name: str = Field(..., description="Permission name")
    resource: str = Field(..., description="Resource type")
    action: str = Field(..., description="Action (read, write, delete, etc.)")
    description: str = Field(..., description="Permission description")

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "document.read",
                "resource": "document",
                "action": "read",
                "description": "Read documents",
            }
        }
    }


class PermissionUpdate(BaseModel):
    """Request model for updating a permission"""

    name: Optional[str] = Field(None, description="Permission name")
    description: Optional[str] = Field(None, description="Permission description")

    model_config = {"json_schema_extra": {"example": {"description": "Updated description"}}}


class SettingsUpdate(BaseModel):
    """Request model for updating enterprise settings"""

    tenant_isolation_enabled: Optional[bool] = Field(None, description="Enable tenant isolation")
    audit_retention_days: Optional[int] = Field(None, ge=1, description="Audit log retention days")
    encryption_enabled: Optional[bool] = Field(None, description="Enable encryption")
    sso_enabled: Optional[bool] = Field(None, description="Enable SSO")
    compliance_standards: Optional[List[str]] = Field(None, description="Compliance standards")
    custom_settings: Optional[Dict[str, Any]] = Field(None, description="Custom settings")

    model_config = {
        "json_schema_extra": {
            "example": {
                "tenant_isolation_enabled": True,
                "audit_retention_days": 90,
                "encryption_enabled": True,
            }
        }
    }


# In-memory storage
tenants: Dict[str, Dict[str, Any]] = {}
users: Dict[str, Dict[str, Any]] = {}
roles: Dict[str, Dict[str, Any]] = {}
permissions: Dict[str, Dict[str, Any]] = {}
enterprise_settings: Dict[str, Any] = {
    "tenant_isolation_enabled": True,
    "audit_retention_days": 90,
    "encryption_enabled": True,
    "sso_enabled": False,
    "compliance_standards": ["gdpr"],
    "custom_settings": {},
}


@router.get(
    "/tenants",
    summary="列出所有租户",
    responses={
        200: {"description": "租户列表"},
        500: {"description": "获取失败"},
    },
)
async def list_tenants(
    status: Optional[str] = Query(None, description="按状态过滤"),
    plan: Optional[str] = Query(None, description="按计划过滤"),
    limit: int = Query(default=100, ge=1, le=500, description="返回数量限制"),
    offset: int = Query(default=0, ge=0, description="偏移量"),
) -> Dict[str, Any]:
    """
    获取租户列表，支持过滤和分页
    """
    try:
        filtered_tenants = list(tenants.values())

        # Apply filters
        if status:
            filtered_tenants = [t for t in filtered_tenants if t.get("status") == status]
        if plan:
            filtered_tenants = [t for t in filtered_tenants if t.get("plan") == plan]

        # Apply pagination
        total = len(filtered_tenants)
        paginated_tenants = filtered_tenants[offset : offset + limit]

        return {
            "status": "success",
            "data": {
                "tenants": paginated_tenants,
                "total": total,
                "limit": limit,
                "offset": offset,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error listing tenants: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/tenants",
    summary="创建新租户",
    responses={
        201: {"description": "租户创建成功"},
        400: {"description": "请求参数错误"},
        500: {"description": "创建失败"},
    },
    status_code=status.HTTP_201_CREATED,
)
async def create_tenant(request: TenantCreate) -> Dict[str, Any]:
    """
    创建新租户
    """
    try:
        # Generate tenant_id if not provided
        tenant_id = request.tenant_id or f"tenant-{uuid4().hex[:8]}"

        # Check if tenant already exists
        if tenant_id in tenants:
            raise HTTPException(status_code=400, detail="租户ID已存在")

        # Create tenant
        tenant = {
            "tenant_id": tenant_id,
            "name": request.name,
            "domain": request.domain,
            "plan": request.plan,
            "max_users": request.max_users,
            "status": "active",
            "settings": request.settings or {},
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

        tenants[tenant_id] = tenant

        # Initialize tenant isolation if enabled
        if ENTERPRISE_AVAILABLE and enterprise_settings.get("tenant_isolation_enabled"):
            enterprise_functionality_manager.tenant_data_isolation[tenant_id] = set()

        return {"status": "success", "data": tenant, "timestamp": datetime.utcnow().isoformat()}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating tenant: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/tenants/{tenant_id}",
    summary="获取租户详情",
    responses={
        200: {"description": "租户详情"},
        404: {"description": "租户未找到"},
        500: {"description": "获取失败"},
    },
)
async def get_tenant(tenant_id: str) -> Dict[str, Any]:
    """
    根据ID获取租户详情
    """
    try:
        tenant = tenants.get(tenant_id)
        if not tenant:
            raise HTTPException(status_code=404, detail="租户未找到")

        # Get user count for this tenant
        user_count = len([u for u in users.values() if u.get("tenant_id") == tenant_id])
        tenant["user_count"] = user_count

        return {"status": "success", "data": tenant, "timestamp": datetime.utcnow().isoformat()}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting tenant: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch(
    "/tenants/{tenant_id}",
    summary="更新租户",
    responses={
        200: {"description": "租户更新成功"},
        404: {"description": "租户未找到"},
        400: {"description": "请求参数错误"},
        500: {"description": "更新失败"},
    },
)
async def update_tenant(tenant_id: str, request: TenantUpdate) -> Dict[str, Any]:
    """
    更新租户信息
    """
    try:
        tenant = tenants.get(tenant_id)
        if not tenant:
            raise HTTPException(status_code=404, detail="租户未找到")

        # Update fields
        if request.name is not None:
            tenant["name"] = request.name
        if request.domain is not None:
            tenant["domain"] = request.domain
        if request.plan is not None:
            tenant["plan"] = request.plan
        if request.max_users is not None:
            tenant["max_users"] = request.max_users
        if request.status is not None:
            tenant["status"] = request.status
        if request.settings is not None:
            tenant["settings"].update(request.settings)

        tenant["updated_at"] = datetime.utcnow().isoformat()

        return {"status": "success", "data": tenant, "timestamp": datetime.utcnow().isoformat()}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating tenant: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete(
    "/tenants/{tenant_id}",
    summary="删除租户",
    responses={
        200: {"description": "租户删除成功"},
        404: {"description": "租户未找到"},
        500: {"description": "删除失败"},
    },
)
async def delete_tenant(tenant_id: str) -> Dict[str, Any]:
    """
    删除租户
    """
    try:
        tenant = tenants.get(tenant_id)
        if not tenant:
            raise HTTPException(status_code=404, detail="租户未找到")

        # Delete all users for this tenant
        users_to_delete = [uid for uid, u in users.items() if u.get("tenant_id") == tenant_id]
        for uid in users_to_delete:
            del users[uid]

        # Delete tenant
        del tenants[tenant_id]

        return {
            "status": "success",
            "data": {"tenant_id": tenant_id, "deleted": True},
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting tenant: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/users",
    summary="列出所有用户",
    responses={
        200: {"description": "用户列表"},
        500: {"description": "获取失败"},
    },
)
async def list_users(
    tenant_id: Optional[str] = Query(None, description="按租户ID过滤"),
    status: Optional[str] = Query(None, description="按状态过滤"),
    role_id: Optional[str] = Query(None, description="按角色ID过滤"),
    limit: int = Query(default=100, ge=1, le=500, description="返回数量限制"),
    offset: int = Query(default=0, ge=0, description="偏移量"),
) -> Dict[str, Any]:
    """
    获取用户列表，支持过滤和分页
    """
    try:
        filtered_users = list(users.values())

        # Apply filters
        if tenant_id:
            filtered_users = [u for u in filtered_users if u.get("tenant_id") == tenant_id]
        if status:
            filtered_users = [u for u in filtered_users if u.get("status") == status]
        if role_id:
            filtered_users = [u for u in filtered_users if u.get("role_id") == role_id]

        # Apply pagination
        total = len(filtered_users)
        paginated_users = filtered_users[offset : offset + limit]

        return {
            "status": "success",
            "data": {"users": paginated_users, "total": total, "limit": limit, "offset": offset},
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error listing users: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/users",
    summary="创建新用户",
    responses={
        201: {"description": "用户创建成功"},
        400: {"description": "请求参数错误"},
        404: {"description": "租户未找到"},
        500: {"description": "创建失败"},
    },
    status_code=status.HTTP_201_CREATED,
)
async def create_user(request: UserCreate) -> Dict[str, Any]:
    """
    创建新用户
    """
    try:
        # Check if tenant exists
        if request.tenant_id not in tenants:
            raise HTTPException(status_code=404, detail="租户未找到")

        # Generate user_id if not provided
        user_id = request.user_id or f"user-{uuid4().hex[:8]}"

        # Check if user already exists
        if user_id in users:
            raise HTTPException(status_code=400, detail="用户ID已存在")

        # Create user
        user = {
            "user_id": user_id,
            "tenant_id": request.tenant_id,
            "username": request.username,
            "email": request.email,
            "full_name": request.full_name,
            "role_id": request.role_id,
            "status": request.status,
            "attributes": request.attributes or {},
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

        users[user_id] = user

        return {"status": "success", "data": user, "timestamp": datetime.utcnow().isoformat()}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/roles",
    summary="列出所有角色",
    responses={
        200: {"description": "角色列表"},
        500: {"description": "获取失败"},
    },
)
async def list_roles(
    tenant_id: Optional[str] = Query(None, description="按租户ID过滤"),
    is_system_role: Optional[bool] = Query(None, description="是否为系统角色"),
    limit: int = Query(default=100, ge=1, le=500, description="返回数量限制"),
    offset: int = Query(default=0, ge=0, description="偏移量"),
) -> Dict[str, Any]:
    """
    获取角色列表，支持过滤和分页
    """
    try:
        filtered_roles = list(roles.values())

        # Apply filters
        if tenant_id:
            filtered_roles = [r for r in filtered_roles if r.get("tenant_id") == tenant_id]
        if is_system_role is not None:
            filtered_roles = [
                r for r in filtered_roles if r.get("is_system_role") == is_system_role
            ]

        # Apply pagination
        total = len(filtered_roles)
        paginated_roles = filtered_roles[offset : offset + limit]

        return {
            "status": "success",
            "data": {"roles": paginated_roles, "total": total, "limit": limit, "offset": offset},
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error listing roles: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/roles",
    summary="创建新角色",
    responses={
        201: {"description": "角色创建成功"},
        400: {"description": "请求参数错误"},
        404: {"description": "租户未找到"},
        500: {"description": "创建失败"},
    },
    status_code=status.HTTP_201_CREATED,
)
async def create_role(request: RoleCreate) -> Dict[str, Any]:
    """
    创建新角色
    """
    try:
        # Check if tenant exists
        if request.tenant_id not in tenants:
            raise HTTPException(status_code=404, detail="租户未找到")

        # Generate role_id if not provided
        role_id = request.role_id or f"role-{uuid4().hex[:8]}"

        # Check if role already exists
        if role_id in roles:
            raise HTTPException(status_code=400, detail="角色ID已存在")

        # Create role
        role = {
            "role_id": role_id,
            "tenant_id": request.tenant_id,
            "name": request.name,
            "description": request.description,
            "permissions": request.permissions,
            "is_system_role": request.is_system_role,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

        roles[role_id] = role

        return {"status": "success", "data": role, "timestamp": datetime.utcnow().isoformat()}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating role: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/permissions",
    summary="列出所有权限",
    responses={
        200: {"description": "权限列表"},
        500: {"description": "获取失败"},
    },
)
async def list_permissions(
    resource: Optional[str] = Query(None, description="按资源类型过滤"),
    action: Optional[str] = Query(None, description="按操作过滤"),
    limit: int = Query(default=100, ge=1, le=500, description="返回数量限制"),
    offset: int = Query(default=0, ge=0, description="偏移量"),
) -> Dict[str, Any]:
    """
    获取权限列表，支持过滤和分页
    """
    try:
        filtered_permissions = list(permissions.values())

        # Apply filters
        if resource:
            filtered_permissions = [
                p for p in filtered_permissions if p.get("resource") == resource
            ]
        if action:
            filtered_permissions = [p for p in filtered_permissions if p.get("action") == action]

        # Apply pagination
        total = len(filtered_permissions)
        paginated_permissions = filtered_permissions[offset : offset + limit]

        return {
            "status": "success",
            "data": {
                "permissions": paginated_permissions,
                "total": total,
                "limit": limit,
                "offset": offset,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error listing permissions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/permissions",
    summary="创建新权限",
    responses={
        201: {"description": "权限创建成功"},
        400: {"description": "请求参数错误"},
        500: {"description": "创建失败"},
    },
    status_code=status.HTTP_201_CREATED,
)
async def create_permission(request: PermissionCreate) -> Dict[str, Any]:
    """
    创建新权限
    """
    try:
        # Generate permission_id if not provided
        permission_id = request.permission_id or f"perm-{uuid4().hex[:8]}"

        # Check if permission already exists
        if permission_id in permissions:
            raise HTTPException(status_code=400, detail="权限ID已存在")

        # Create permission
        permission = {
            "permission_id": permission_id,
            "name": request.name,
            "resource": request.resource,
            "action": request.action,
            "description": request.description,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

        permissions[permission_id] = permission

        return {"status": "success", "data": permission, "timestamp": datetime.utcnow().isoformat()}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating permission: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/audit-logs",
    summary="列出审计日志",
    responses={
        200: {"description": "审计日志列表"},
        400: {"description": "无效的日期格式"},
        503: {"description": "企业功能管理器不可用"},
    },
)
async def list_audit_logs(
    tenant_id: Optional[str] = Query(None, description="按租户ID过滤"),
    user_id: Optional[str] = Query(None, description="按用户ID过滤"),
    action: Optional[str] = Query(None, description="按操作过滤"),
    start_date: Optional[str] = Query(None, description="开始日期 (ISO格式)"),
    end_date: Optional[str] = Query(None, description="结束日期 (ISO格式)"),
    limit: int = Query(default=100, ge=1, le=500, description="返回数量限制"),
    offset: int = Query(default=0, ge=0, description="偏移量"),
) -> Dict[str, Any]:
    """
    获取审计日志列表，支持多种过滤条件
    """
    if not ENTERPRISE_AVAILABLE:
        raise HTTPException(status_code=503, detail="企业功能管理器不可用")

    try:
        from datetime import datetime as dt

        start_dt = None
        end_dt = None
        if start_date:
            try:
                start_dt = dt.fromisoformat(start_date)
            except ValueError:
                raise HTTPException(status_code=400, detail="无效的开始日期格式")
        if end_date:
            try:
                end_dt = dt.fromisoformat(end_date)
            except ValueError:
                raise HTTPException(status_code=400, detail="无效的结束日期格式")

        logs = await enterprise_functionality_manager.query_audit_logs(
            tenant_id=tenant_id,
            user_id=user_id,
            action=action,
            start_date=start_dt,
            end_date=end_dt,
            limit=limit + offset,  # Get more for pagination
        )

        # Apply pagination
        total = len(logs)
        paginated_logs = logs[offset : offset + limit]

        return {
            "status": "success",
            "data": {
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
                    for log in paginated_logs
                ],
                "total": total,
                "limit": limit,
                "offset": offset,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing audit logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/settings",
    summary="获取企业设置",
    responses={
        200: {"description": "企业设置"},
        500: {"description": "获取失败"},
    },
)
async def get_settings() -> Dict[str, Any]:
    """
    获取企业级设置
    """
    try:
        return {
            "status": "success",
            "data": enterprise_settings,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error getting settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch(
    "/settings",
    summary="更新企业设置",
    responses={
        200: {"description": "设置更新成功"},
        400: {"description": "请求参数错误"},
        500: {"description": "更新失败"},
    },
)
async def update_settings(request: SettingsUpdate) -> Dict[str, Any]:
    """
    更新企业级设置
    """
    try:
        # Update settings
        if request.tenant_isolation_enabled is not None:
            enterprise_settings["tenant_isolation_enabled"] = request.tenant_isolation_enabled
        if request.audit_retention_days is not None:
            enterprise_settings["audit_retention_days"] = request.audit_retention_days
        if request.encryption_enabled is not None:
            enterprise_settings["encryption_enabled"] = request.encryption_enabled
        if request.sso_enabled is not None:
            enterprise_settings["sso_enabled"] = request.sso_enabled
        if request.compliance_standards is not None:
            enterprise_settings["compliance_standards"] = request.compliance_standards
        if request.custom_settings is not None:
            enterprise_settings["custom_settings"].update(request.custom_settings)

        # Update enterprise manager if available
        if ENTERPRISE_AVAILABLE:
            enterprise_functionality_manager.audit_retention_days = enterprise_settings.get(
                "audit_retention_days", 90
            )

        return {
            "status": "success",
            "data": enterprise_settings,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error updating settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))
