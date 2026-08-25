# -*- coding: utf-8 -*-
"""Access Control Service - Main entry point."""

import asyncio
import logging
import os
import sys
from typing import Any, Dict, List, Optional

# Add project root to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field
from datetime import datetime

from access_control_manager import AccessControlManager
from policy_enforcer import PolicyEnforcer
from permission_checker import PermissionChecker
from grpc.server import serve as grpc_serve

# Import storage
from core.storage.postgres_storage import PostgreSQLStorage

SERVICE_NAME = "access_control_service"
HTTP_PORT = int(os.getenv("PORT", "8001"))
GRPC_PORT = int(os.getenv("GRPC_PORT", "50054"))

app = FastAPI(title=SERVICE_NAME.replace("_", " ").title())
logger = logging.getLogger(SERVICE_NAME)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format=f"[{SERVICE_NAME}] %(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# Initialize storage and managers
storage = PostgreSQLStorage()
access_control_manager = AccessControlManager(storage)
policy_enforcer = PolicyEnforcer(access_control_manager)
permission_checker = PermissionChecker(access_control_manager)

# Initialize on startup
@app.on_event("startup")
async def startup_event():
    """Initialize the service on startup."""
    logger.info(f"Starting {SERVICE_NAME}")
    
    # Initialize storage
    try:
        if not storage.initialize():
            logger.error("Failed to initialize storage")
            return
    except Exception as e:
        logger.error(f"Error initializing storage: {e}")
        return
    
    # Initialize access control manager
    if not access_control_manager.initialize():
        logger.error("Failed to initialize Access Control Manager")
        return
    
    logger.info(f"{SERVICE_NAME} initialized successfully")


# Request/Response Models
class PermissionRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str = Field(default="", max_length=500)
    resource_type: str = Field(..., min_length=1, max_length=100)
    actions: List[str] = Field(..., min_items=1)


class PermissionUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=500)
    resource_type: Optional[str] = Field(None, min_length=1, max_length=100)
    actions: Optional[List[str]] = Field(None, min_items=1)


class PermissionResponse(BaseModel):
    id: str
    name: str
    description: str
    resource_type: str
    actions: List[str]
    created_at: Optional[str]
    updated_at: Optional[str]


class RoleRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str = Field(default="", max_length=500)
    permission_ids: List[str] = Field(default_factory=list)
    inherited_role_ids: List[str] = Field(default_factory=list)


class RoleUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=500)
    permission_ids: Optional[List[str]] = None
    inherited_role_ids: Optional[List[str]] = None


class RoleResponse(BaseModel):
    id: str
    name: str
    description: str
    permission_ids: List[str]
    inherited_role_ids: List[str]
    created_at: Optional[str]
    updated_at: Optional[str]


class PolicyRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str = Field(default="", max_length=500)
    effect: str = Field(..., regex="^(allow|deny)$")
    subject_conditions: Dict[str, str] = Field(default_factory=dict)
    resource_conditions: Dict[str, str] = Field(default_factory=dict)
    environment_conditions: Dict[str, str] = Field(default_factory=dict)
    actions: List[str] = Field(..., min_items=1)
    priority: int = Field(default=0, ge=0)


class PolicyUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=500)
    enabled: Optional[bool] = None
    effect: Optional[str] = Field(None, regex="^(allow|deny)$")
    subject_conditions: Optional[Dict[str, str]] = None
    resource_conditions: Optional[Dict[str, str]] = None
    environment_conditions: Optional[Dict[str, str]] = None
    actions: Optional[List[str]] = Field(None, min_items=1)
    priority: Optional[int] = Field(None, ge=0)


class PolicyResponse(BaseModel):
    id: str
    name: str
    description: str
    enabled: bool
    effect: str
    subject_conditions: Dict[str, str]
    resource_conditions: Dict[str, str]
    environment_conditions: Dict[str, str]
    actions: List[str]
    priority: int
    created_at: Optional[str]
    updated_at: Optional[str]


class AccessRequest(BaseModel):
    subject_id: str = Field(..., min_length=1)
    subject_type: str = Field(default="user", regex="^(user|service|system)$")
    subject_attributes: Dict[str, str] = Field(default_factory=dict)
    subject_roles: List[str] = Field(default_factory=list)
    subject_groups: List[str] = Field(default_factory=list)
    resource_id: str = Field(..., min_length=1)
    resource_type: str = Field(..., min_length=1)
    resource_attributes: Dict[str, str] = Field(default_factory=dict)
    resource_owner: Optional[str] = None
    action: str = Field(..., min_length=1)
    environment_attributes: Dict[str, str] = Field(default_factory=dict)


class AccessDecisionResponse(BaseModel):
    allowed: bool
    decision_type: str
    reason: str
    matched_policies: List[str]
    matched_roles: List[str]
    evaluated_at: int


class StatusResponse(BaseModel):
    success: bool
    message: str


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = SERVICE_NAME


class AssignRoleRequest(BaseModel):
    subject_id: str = Field(..., min_length=1)
    role_id: str = Field(..., min_length=1)


# Health Check Endpoints
@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(status="ok", service=SERVICE_NAME)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": SERVICE_NAME,
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "permissions": "/permissions",
            "roles": "/roles",
            "policies": "/policies",
            "check": "/check",
            "audit": "/audit",
        },
    }


# Permission Management Endpoints
@app.post("/permissions", response_model=PermissionResponse, status_code=status.HTTP_201_CREATED)
async def create_permission(request: PermissionRequest) -> PermissionResponse:
    """Create a new permission."""
    permission_id = access_control_manager.create_permission(
        name=request.name,
        description=request.description,
        resource_type=request.resource_type,
        actions=request.actions,
    )
    if not permission_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create permission. Name may already exist."
        )
    permission = access_control_manager.get_permission(permission_id)
    return PermissionResponse(
        id=permission["id"],
        name=permission["name"],
        description=permission["description"],
        resource_type=permission["resource_type"],
        actions=permission["actions"],
        created_at=permission["created_at"].isoformat() if permission["created_at"] else None,
        updated_at=permission["updated_at"].isoformat() if permission["updated_at"] else None,
    )


@app.get("/permissions/{permission_id}", response_model=PermissionResponse)
async def get_permission(permission_id: str) -> PermissionResponse:
    """Get a permission by ID."""
    permission = access_control_manager.get_permission(permission_id)
    if not permission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Permission not found"
        )
    return PermissionResponse(
        id=permission["id"],
        name=permission["name"],
        description=permission["description"],
        resource_type=permission["resource_type"],
        actions=permission["actions"],
        created_at=permission["created_at"].isoformat() if permission["created_at"] else None,
        updated_at=permission["updated_at"].isoformat() if permission["updated_at"] else None,
    )


@app.put("/permissions/{permission_id}", response_model=PermissionResponse)
async def update_permission(permission_id: str, request: PermissionUpdateRequest) -> PermissionResponse:
    """Update a permission."""
    success = access_control_manager.update_permission(
        permission_id=permission_id,
        name=request.name,
        description=request.description,
        resource_type=request.resource_type,
        actions=request.actions,
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Permission not found or update failed"
        )
    permission = access_control_manager.get_permission(permission_id)
    return PermissionResponse(
        id=permission["id"],
        name=permission["name"],
        description=permission["description"],
        resource_type=permission["resource_type"],
        actions=permission["actions"],
        created_at=permission["created_at"].isoformat() if permission["created_at"] else None,
        updated_at=permission["updated_at"].isoformat() if permission["updated_at"] else None,
    )


@app.delete("/permissions/{permission_id}", response_model=StatusResponse)
async def delete_permission(permission_id: str) -> StatusResponse:
    """Delete a permission."""
    success = access_control_manager.delete_permission(permission_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Permission not found or deletion failed"
        )
    return StatusResponse(success=True, message="Permission deleted successfully")


@app.get("/permissions", response_model=List[PermissionResponse])
async def list_permissions(
    limit: int = 100,
    offset: int = 0,
    resource_type: Optional[str] = None,
) -> List[PermissionResponse]:
    """List permissions."""
    permissions = access_control_manager.list_permissions(
        limit=limit, offset=offset, resource_type=resource_type
    )
    return [
        PermissionResponse(
            id=p["id"],
            name=p["name"],
            description=p["description"],
            resource_type=p["resource_type"],
            actions=p["actions"],
            created_at=p["created_at"].isoformat() if p["created_at"] else None,
            updated_at=p["updated_at"].isoformat() if p["updated_at"] else None,
        )
        for p in permissions
    ]


# Role Management Endpoints
@app.post("/roles", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
async def create_role(request: RoleRequest) -> RoleResponse:
    """Create a new role."""
    role_id = access_control_manager.create_role(
        name=request.name,
        description=request.description,
        permission_ids=request.permission_ids,
        inherited_role_ids=request.inherited_role_ids,
    )
    if not role_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create role. Name may already exist."
        )
    role = access_control_manager.get_role(role_id)
    return RoleResponse(
        id=role["id"],
        name=role["name"],
        description=role["description"],
        permission_ids=role["permission_ids"],
        inherited_role_ids=role["inherited_role_ids"],
        created_at=role["created_at"].isoformat() if role["created_at"] else None,
        updated_at=role["updated_at"].isoformat() if role["updated_at"] else None,
    )


@app.get("/roles/{role_id}", response_model=RoleResponse)
async def get_role(role_id: str) -> RoleResponse:
    """Get a role by ID."""
    role = access_control_manager.get_role(role_id)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    return RoleResponse(
        id=role["id"],
        name=role["name"],
        description=role["description"],
        permission_ids=role["permission_ids"],
        inherited_role_ids=role["inherited_role_ids"],
        created_at=role["created_at"].isoformat() if role["created_at"] else None,
        updated_at=role["updated_at"].isoformat() if role["updated_at"] else None,
    )


@app.put("/roles/{role_id}", response_model=RoleResponse)
async def update_role(role_id: str, request: RoleUpdateRequest) -> RoleResponse:
    """Update a role."""
    success = access_control_manager.update_role(
        role_id=role_id,
        name=request.name,
        description=request.description,
        permission_ids=request.permission_ids,
        inherited_role_ids=request.inherited_role_ids,
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found or update failed"
        )
    role = access_control_manager.get_role(role_id)
    return RoleResponse(
        id=role["id"],
        name=role["name"],
        description=role["description"],
        permission_ids=role["permission_ids"],
        inherited_role_ids=role["inherited_role_ids"],
        created_at=role["created_at"].isoformat() if role["created_at"] else None,
        updated_at=role["updated_at"].isoformat() if role["updated_at"] else None,
    )


@app.delete("/roles/{role_id}", response_model=StatusResponse)
async def delete_role(role_id: str) -> StatusResponse:
    """Delete a role."""
    success = access_control_manager.delete_role(role_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found or deletion failed"
        )
    return StatusResponse(success=True, message="Role deleted successfully")


@app.get("/roles", response_model=List[RoleResponse])
async def list_roles(limit: int = 100, offset: int = 0) -> List[RoleResponse]:
    """List roles."""
    roles = access_control_manager.list_roles(limit=limit, offset=offset)
    return [
        RoleResponse(
            id=r["id"],
            name=r["name"],
            description=r["description"],
            permission_ids=r["permission_ids"],
            inherited_role_ids=r["inherited_role_ids"],
            created_at=r["created_at"].isoformat() if r["created_at"] else None,
            updated_at=r["updated_at"].isoformat() if r["updated_at"] else None,
        )
        for r in roles
    ]


@app.post("/roles/assign", response_model=StatusResponse)
async def assign_role(request: AssignRoleRequest) -> StatusResponse:
    """Assign a role to a subject."""
    success = access_control_manager.assign_role(request.subject_id, request.role_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to assign role"
        )
    return StatusResponse(success=True, message="Role assigned successfully")


@app.post("/roles/revoke", response_model=StatusResponse)
async def revoke_role(request: AssignRoleRequest) -> StatusResponse:
    """Revoke a role from a subject."""
    success = access_control_manager.revoke_role(request.subject_id, request.role_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to revoke role"
        )
    return StatusResponse(success=True, message="Role revoked successfully")


@app.get("/subjects/{subject_id}/roles", response_model=List[RoleResponse])
async def get_subject_roles(subject_id: str) -> List[RoleResponse]:
    """Get all roles for a subject."""
    roles = access_control_manager.get_subject_roles(subject_id)
    return [
        RoleResponse(
            id=r["id"],
            name=r["name"],
            description=r["description"],
            permission_ids=r["permission_ids"],
            inherited_role_ids=r["inherited_role_ids"],
            created_at=r["created_at"].isoformat() if r["created_at"] else None,
            updated_at=r["updated_at"].isoformat() if r["updated_at"] else None,
        )
        for r in roles
    ]


# Policy Management Endpoints (ABAC)
@app.post("/policies", response_model=PolicyResponse, status_code=status.HTTP_201_CREATED)
async def create_policy(request: PolicyRequest) -> PolicyResponse:
    """Create a new ABAC policy."""
    policy_id = access_control_manager.create_policy(
        name=request.name,
        description=request.description,
        effect=request.effect,
        subject_conditions=request.subject_conditions,
        resource_conditions=request.resource_conditions,
        environment_conditions=request.environment_conditions,
        actions=request.actions,
        priority=request.priority,
    )
    if not policy_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create policy. Name may already exist."
        )
    policy = access_control_manager.get_policy(policy_id)
    return PolicyResponse(
        id=policy["id"],
        name=policy["name"],
        description=policy["description"],
        enabled=policy["enabled"],
        effect=policy["effect"],
        subject_conditions=policy["subject_conditions"],
        resource_conditions=policy["resource_conditions"],
        environment_conditions=policy["environment_conditions"],
        actions=policy["actions"],
        priority=policy["priority"],
        created_at=policy["created_at"],
        updated_at=policy["updated_at"],
    )


@app.get("/policies/{policy_id}", response_model=PolicyResponse)
async def get_policy(policy_id: str) -> PolicyResponse:
    """Get a policy by ID."""
    policy = access_control_manager.get_policy(policy_id)
    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Policy not found"
        )
    return PolicyResponse(
        id=policy["id"],
        name=policy["name"],
        description=policy["description"],
        enabled=policy["enabled"],
        effect=policy["effect"],
        subject_conditions=policy["subject_conditions"],
        resource_conditions=policy["resource_conditions"],
        environment_conditions=policy["environment_conditions"],
        actions=policy["actions"],
        priority=policy["priority"],
        created_at=policy["created_at"],
        updated_at=policy["updated_at"],
    )


@app.put("/policies/{policy_id}", response_model=PolicyResponse)
async def update_policy(policy_id: str, request: PolicyUpdateRequest) -> PolicyResponse:
    """Update a policy."""
    success = access_control_manager.update_policy(
        policy_id=policy_id,
        name=request.name,
        description=request.description,
        enabled=request.enabled,
        effect=request.effect,
        subject_conditions=request.subject_conditions,
        resource_conditions=request.resource_conditions,
        environment_conditions=request.environment_conditions,
        actions=request.actions,
        priority=request.priority,
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Policy not found or update failed"
        )
    policy = access_control_manager.get_policy(policy_id)
    return PolicyResponse(
        id=policy["id"],
        name=policy["name"],
        description=policy["description"],
        enabled=policy["enabled"],
        effect=policy["effect"],
        subject_conditions=policy["subject_conditions"],
        resource_conditions=policy["resource_conditions"],
        environment_conditions=policy["environment_conditions"],
        actions=policy["actions"],
        priority=policy["priority"],
        created_at=policy["created_at"],
        updated_at=policy["updated_at"],
    )


@app.delete("/policies/{policy_id}", response_model=StatusResponse)
async def delete_policy(policy_id: str) -> StatusResponse:
    """Delete a policy."""
    success = access_control_manager.delete_policy(policy_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Policy not found or deletion failed"
        )
    return StatusResponse(success=True, message="Policy deleted successfully")


@app.get("/policies", response_model=List[PolicyResponse])
async def list_policies(enabled_only: bool = True) -> List[PolicyResponse]:
    """List policies."""
    policies = access_control_manager.list_policies(enabled_only=enabled_only)
    return [
        PolicyResponse(
            id=p["id"],
            name=p["name"],
            description=p["description"],
            enabled=p["enabled"],
            effect=p["effect"],
            subject_conditions=p["subject_conditions"],
            resource_conditions=p["resource_conditions"],
            environment_conditions=p["environment_conditions"],
            actions=p["actions"],
            priority=p["priority"],
            created_at=p["created_at"],
            updated_at=p["updated_at"],
        )
        for p in policies
    ]


# Access Control Endpoints
@app.post("/check", response_model=AccessDecisionResponse)
async def check_permission(request: AccessRequest) -> AccessDecisionResponse:
    """Check access permission."""
    decision = policy_enforcer.enforce_policy(
        subject_id=request.subject_id,
        subject_type=request.subject_type,
        subject_attributes=request.subject_attributes,
        subject_roles=request.subject_roles,
        subject_groups=request.subject_groups,
        resource_id=request.resource_id,
        resource_type=request.resource_type,
        resource_attributes=request.resource_attributes,
        resource_owner=request.resource_owner,
        action=request.action,
        environment_attributes=request.environment_attributes,
    )
    return AccessDecisionResponse(**decision)


# Audit Logging Endpoints
@app.get("/audit")
async def get_audit_logs(
    subject_id: Optional[str] = None,
    resource_id: Optional[str] = None,
    start_time: Optional[int] = None,
    end_time: Optional[int] = None,
    limit: int = 100,
    offset: int = 0,
):
    """Get audit logs."""
    logs = policy_enforcer.get_audit_logs(
        subject_id=subject_id,
        resource_id=resource_id,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
        offset=offset,
    )
    return {
        "logs": logs,
        "total": len(logs),
    }


# Permission Checker Endpoints
@app.get("/subjects/{subject_id}/permissions")
async def get_subject_permissions(subject_id: str, resource_type: Optional[str] = None):
    """Get all permissions for a subject."""
    permissions = permission_checker.get_permissions(subject_id, resource_type)
    return {
        "subject_id": subject_id,
        "permissions": list(permissions),
        "total": len(permissions),
    }


@app.get("/subjects/{subject_id}/roles/effective")
async def get_subject_effective_roles(subject_id: str):
    """Get all effective roles for a subject (including inherited)."""
    roles = permission_checker.get_subject_effective_roles(subject_id)
    return {
        "subject_id": subject_id,
        "roles": roles,
        "total": len(roles),
    }


if __name__ == "__main__":
    import uvicorn

    logger.info(f"Starting {SERVICE_NAME} HTTP server on port {HTTP_PORT}")
    logger.info(f"Starting {SERVICE_NAME} gRPC server on port {GRPC_PORT}")
    
    # Start both HTTP and gRPC servers
    async def run_servers():
        # Start gRPC server in background
        grpc_task = asyncio.create_task(grpc_serve(storage, GRPC_PORT))
        
        # Start HTTP server (this will block)
        config = uvicorn.Config(
            app,
            host=os.environ.get("HOST", "127.0.0.1"),
            port=HTTP_PORT,
            log_level="info",
        )
        server = uvicorn.Server(config)
        await server.serve()
    
    asyncio.run(run_servers())
