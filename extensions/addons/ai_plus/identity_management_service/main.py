# -*- coding: utf-8 -*-
"""Identity Management Service - Main entry point."""

import logging
import os
import sys
from typing import Any, Dict, List, Optional

# Add project root to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

from authentication_provider import authentication_provider
from group_manager import group_manager
from identity_manager import identity_manager
from user_provisioning import user_provisioning

SERVICE_NAME = "identity_management_service"
PORT = int(os.getenv("PORT", "8000"))

app = FastAPI(title=SERVICE_NAME.replace("_", " ").title())
logger = logging.getLogger(SERVICE_NAME)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format=f"[{SERVICE_NAME}] %(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


# Request/Response Models
class CreateUserRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)
    email: Optional[str] = Field(None, max_length=100)
    full_name: Optional[str] = Field(None, max_length=100)
    role: str = Field(default="user", pattern="^(admin|operator|business|viewer|user)$")
    attributes: Optional[Dict[str, str]] = Field(default_factory=dict)


class UpdateUserRequest(BaseModel):
    email: Optional[str] = Field(None, max_length=100)
    full_name: Optional[str] = Field(None, max_length=100)
    role: Optional[str] = Field(None, pattern="^(admin|operator|business|viewer|user)$")
    disabled: Optional[bool] = None
    attributes: Optional[Dict[str, str]] = Field(default_factory=dict)


class UserResponse(BaseModel):
    id: int
    username: str
    email: Optional[str]
    full_name: Optional[str]
    role: str
    disabled: bool
    mfa_enabled: bool
    created_at: Optional[str]
    updated_at: Optional[str]
    last_login_at: Optional[str]
    attributes: Dict[str, str] = Field(default_factory=dict)


class UsersResponse(BaseModel):
    users: List[UserResponse]
    total: int


class StatusResponse(BaseModel):
    success: bool
    message: str


class MFAConfigResponse(BaseModel):
    secret: str
    recovery_codes: List[str]
    enabled: bool


class MFAVerificationRequest(BaseModel):
    code: str = Field(..., min_length=6, max_length=8)


class MFAVerificationResponse(BaseModel):
    verified: bool
    message: str


class CreateUserGroupRequest(BaseModel):
    name: str = Field(..., min_length=3, max_length=50)
    description: str = Field(default="", max_length=200)
    usernames: Optional[List[str]] = Field(default_factory=list)
    attributes: Optional[Dict[str, str]] = Field(default_factory=dict)


class UpdateUserGroupRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=3, max_length=50)
    description: Optional[str] = Field(None, max_length=200)
    usernames: Optional[List[str]] = Field(default_factory=list)
    attributes: Optional[Dict[str, str]] = Field(default_factory=dict)


class UserGroupResponse(BaseModel):
    id: int
    name: str
    description: str
    user_ids: List[int]
    attributes: Dict[str, str]
    created_at: Optional[str]


class UserGroupsResponse(BaseModel):
    groups: List[UserGroupResponse]
    total: int


class SSOConfigRequest(BaseModel):
    provider: str = Field(..., min_length=2, max_length=50)
    client_id: str = Field(..., min_length=1)
    metadata: Optional[Dict[str, str]] = Field(default_factory=dict)


class SSOConfigResponse(BaseModel):
    provider: str
    client_id: str
    metadata: Dict[str, str]
    enabled: bool


class SSOLoginRequest(BaseModel):
    provider: str = Field(..., min_length=2, max_length=50)
    token: str = Field(..., min_length=1)


class SSOLoginResponse(BaseModel):
    success: bool
    user: Optional[UserResponse]
    token: Optional[str]
    message: str


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = SERVICE_NAME


class SetAttributeRequest(BaseModel):
    key: str = Field(..., min_length=1, max_length=50)
    value: str = Field(..., max_length=200)


class AddToGroupRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    group_id: int = Field(..., gt=0)


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
            "users": "/users",
            "groups": "/groups",
            "mfa": "/users/{username}/mfa",
            "sso": "/sso",
        },
    }


# User Management Endpoints
@app.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(request: CreateUserRequest) -> UserResponse:
    """Create a new user."""
    user = await identity_manager.create_user(
        username=request.username,
        password=request.password,
        email=request.email,
        full_name=request.full_name,
        role=request.role,
        attributes=request.attributes,
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create user. Username may already exist."
        )
    return UserResponse(**user)


@app.get("/users/{username}", response_model=UserResponse)
async def get_user(username: str) -> UserResponse:
    """Get user by username."""
    user = await identity_manager.get_user(username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return UserResponse(**user)


@app.put("/users/{username}", response_model=UserResponse)
async def update_user(username: str, request: UpdateUserRequest) -> UserResponse:
    """Update user information."""
    user = await identity_manager.update_user(
        username=username,
        email=request.email,
        full_name=request.full_name,
        role=request.role,
        disabled=request.disabled,
        attributes=request.attributes,
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found or update failed"
        )
    return UserResponse(**user)


@app.delete("/users/{username}", response_model=StatusResponse)
async def delete_user(username: str) -> StatusResponse:
    """Delete a user."""
    success = await identity_manager.delete_user(username)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found or deletion failed"
        )
    return StatusResponse(success=True, message="User deleted successfully")


@app.get("/users", response_model=UsersResponse)
async def list_users(
    limit: int = 100,
    offset: int = 0,
    role: Optional[str] = None,
    disabled: Optional[bool] = None,
) -> UsersResponse:
    """List users with optional filtering."""
    users = await identity_manager.list_users(
        limit=limit,
        offset=offset,
        role=role,
        disabled=disabled,
    )
    return UsersResponse(users=[UserResponse(**u) for u in users], total=len(users))


# User Attributes Endpoints
@app.post("/users/{username}/attributes", response_model=StatusResponse)
async def set_user_attribute(username: str, request: SetAttributeRequest) -> StatusResponse:
    """Set a user attribute."""
    success = await identity_manager.set_user_attribute(username, request.key, request.value)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return StatusResponse(success=True, message="Attribute set successfully")


@app.delete("/users/{username}/attributes/{key}", response_model=StatusResponse)
async def delete_user_attribute(username: str, key: str) -> StatusResponse:
    """Delete a user attribute."""
    success = await identity_manager.delete_user_attribute(username, key)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return StatusResponse(success=True, message="Attribute deleted successfully")


# MFA Endpoints
@app.post("/users/{username}/mfa/enable", response_model=MFAConfigResponse)
async def enable_mfa(username: str) -> MFAConfigResponse:
    """Enable MFA for a user."""
    mfa_config = await identity_manager.enable_mfa(username)
    if not mfa_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return MFAConfigResponse(**mfa_config)


@app.post("/users/{username}/mfa/disable", response_model=StatusResponse)
async def disable_mfa(username: str) -> StatusResponse:
    """Disable MFA for a user."""
    success = await identity_manager.disable_mfa(username)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return StatusResponse(success=True, message="MFA disabled successfully")


@app.post("/users/{username}/mfa/verify", response_model=MFAVerificationResponse)
async def verify_mfa(username: str, request: MFAVerificationRequest) -> MFAVerificationResponse:
    """Verify MFA code for a user."""
    verified = await identity_manager.verify_mfa(username, request.code)
    return MFAVerificationResponse(
        verified=verified,
        message="MFA verified successfully" if verified else "Invalid MFA code"
    )


# User Group Endpoints
@app.post("/groups", response_model=UserGroupResponse, status_code=status.HTTP_201_CREATED)
async def create_user_group(request: CreateUserGroupRequest) -> UserGroupResponse:
    """Create a new user group."""
    group = await group_manager.create_group(
        name=request.name,
        description=request.description,
        usernames=request.usernames,
        attributes=request.attributes,
    )
    if not group:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create group. Group name may already exist."
        )
    return UserGroupResponse(**group)


@app.get("/groups/{group_id}", response_model=UserGroupResponse)
async def get_user_group(group_id: int) -> UserGroupResponse:
    """Get a group by ID."""
    group = await group_manager.get_group(group_id)
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found"
        )
    return UserGroupResponse(**group)


@app.put("/groups/{group_id}", response_model=UserGroupResponse)
async def update_user_group(group_id: int, request: UpdateUserGroupRequest) -> UserGroupResponse:
    """Update a user group."""
    group = await group_manager.update_group(
        group_id=group_id,
        name=request.name,
        description=request.description,
        usernames=request.usernames,
        attributes=request.attributes,
    )
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found"
        )
    return UserGroupResponse(**group)


@app.delete("/groups/{group_id}", response_model=StatusResponse)
async def delete_user_group(group_id: int) -> StatusResponse:
    """Delete a user group."""
    success = await group_manager.delete_group(group_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found"
        )
    return StatusResponse(success=True, message="Group deleted successfully")


@app.get("/groups", response_model=UserGroupsResponse)
async def list_user_groups(limit: int = 100, offset: int = 0) -> UserGroupsResponse:
    """List all groups."""
    groups = await group_manager.list_groups(limit=limit, offset=offset)
    return UserGroupsResponse(groups=[UserGroupResponse(**g) for g in groups], total=len(groups))


@app.post("/groups/members", response_model=StatusResponse)
async def add_user_to_group(request: AddToGroupRequest) -> StatusResponse:
    """Add a user to a group."""
    success = await group_manager.add_user_to_group(request.username, request.group_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User or group not found"
        )
    return StatusResponse(success=True, message="User added to group successfully")


@app.delete("/groups/members", response_model=StatusResponse)
async def remove_user_from_group(request: AddToGroupRequest) -> StatusResponse:
    """Remove a user from a group."""
    success = await group_manager.remove_user_from_group(request.username, request.group_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User or group not found"
        )
    return StatusResponse(success=True, message="User removed from group successfully")


# SSO Endpoints
@app.post("/sso/configure", response_model=SSOConfigResponse)
async def configure_sso(request: SSOConfigRequest) -> SSOConfigResponse:
    """Configure SSO provider."""
    config = await identity_manager.configure_sso(
        provider=request.provider,
        client_id=request.client_id,
        metadata=request.metadata,
    )
    if not config:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to configure SSO"
        )
    return SSOConfigResponse(**config)


@app.post("/sso/login", response_model=SSOLoginResponse)
async def sso_login(request: SSOLoginRequest) -> SSOLoginResponse:
    """Perform SSO login."""
    result = await identity_manager.sso_login(request.provider, request.token)
    if not result:
        return SSOLoginResponse(
            success=False,
            user=None,
            token=None,
            message="SSO login failed"
        )
    return SSOLoginResponse(
        success=True,
        user=UserResponse(**result),
        token="jwt_token_placeholder",
        message="SSO login successful"
    )


# Authentication Endpoints
@app.post("/auth/login")
async def login(username: str, password: str):
    """Authenticate a user."""
    result = await authentication_provider.authenticate_user(username, password)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    return result


@app.post("/auth/mfa")
async def mfa_login(username: str, code: str):
    """Authenticate with MFA."""
    result = await authentication_provider.authenticate_with_mfa(username, code)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid MFA code"
        )
    return result


# User Provisioning Endpoints
@app.post("/provision", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def provision_user(request: CreateUserRequest) -> UserResponse:
    """Provision a new user with complete setup."""
    user = await user_provisioning.provision_user(
        username=request.username,
        password=request.password,
        email=request.email,
        full_name=request.full_name,
        role=request.role,
        attributes=request.attributes,
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to provision user"
        )
    return UserResponse(**user)


@app.post("/deprovision/{username}", response_model=StatusResponse)
async def deprovision_user(username: str) -> StatusResponse:
    """Deprovision a user."""
    success = await user_provisioning.deprovision_user(username)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return StatusResponse(success=True, message="User deprovisioned successfully")


if __name__ == "__main__":
    import uvicorn

    logger.info(f"Starting {SERVICE_NAME} on port {PORT}")
    uvicorn.run(
        app,
        host=os.environ.get("HOST", "127.0.0.1"),
        port=PORT,
        log_level="info",
    )
