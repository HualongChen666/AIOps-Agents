# -*- coding: utf-8 -*-
"""gRPC server for Identity Management Service."""

import asyncio
import logging
import sys
import os
from typing import Any, Dict

# Add project root to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))

import grpc
from grpc.aio import ServicerContext

# Import generated protobuf classes (these would be generated from the proto file)
# For now, we'll create simple message classes
from identity_manager import IdentityManager
from group_manager import GroupManager

logger = logging.getLogger(__name__)

SERVICE_NAME = "identity_management_service"
DEFAULT_PORT = 50053


# Simple message classes (in production, these would be generated from proto)
class User:
    def __init__(
        self,
        id: int = 0,
        username: str = "",
        email: str = "",
        full_name: str = "",
        role: str = "",
        disabled: bool = False,
        mfa_enabled: bool = False,
        created_at: int = 0,
        updated_at: int = 0,
        last_login_at: int = 0,
        attributes: Dict[str, str] = None,
    ):
        self.id = id
        self.username = username
        self.email = email
        self.full_name = full_name
        self.role = role
        self.disabled = disabled
        self.mfa_enabled = mfa_enabled
        self.created_at = created_at
        self.updated_at = updated_at
        self.last_login_at = last_login_at
        self.attributes = attributes or {}


class UserGroup:
    def __init__(
        self,
        id: int = 0,
        name: str = "",
        description: str = "",
        user_ids: list = None,
        attributes: Dict[str, str] = None,
        created_at: int = 0,
    ):
        self.id = id
        self.name = name
        self.description = description
        self.user_ids = user_ids or []
        self.attributes = attributes or {}
        self.created_at = created_at


class IdentityManagementServicer:
    """gRPC servicer for Identity Management Service."""

    def __init__(self):
        self.identity_manager = IdentityManager()
        self.group_manager = GroupManager()

    async def CreateUser(self, request, context: ServicerContext):
        """Create a new user."""
        try:
            user = await self.identity_manager.create_user(
                username=request.username,
                password=request.password,
                email=request.email if hasattr(request, 'email') else None,
                full_name=request.full_name if hasattr(request, 'full_name') else None,
                role=request.role if hasattr(request, 'role') else "user",
                attributes=dict(request.attributes) if hasattr(request, 'attributes') else None,
            )
            
            if user:
                return UserResponse(
                    user=User(**user),
                    message="User created successfully"
                )
            else:
                context.set_code(grpc.StatusCode.INTERNAL)
                context.set_details("Failed to create user")
                return UserResponse()
        except Exception as e:
            logger.error(f"Error in CreateUser: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return UserResponse()

    async def UpdateUser(self, request, context: ServicerContext):
        """Update user information."""
        try:
            user = await self.identity_manager.update_user(
                username=request.username,
                email=request.email if hasattr(request, 'email') else None,
                full_name=request.full_name if hasattr(request, 'full_name') else None,
                role=request.role if hasattr(request, 'role') else None,
                disabled=request.disabled if hasattr(request, 'disabled') else None,
                attributes=dict(request.attributes) if hasattr(request, 'attributes') else None,
            )
            
            if user:
                return UserResponse(
                    user=User(**user),
                    message="User updated successfully"
                )
            else:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details("User not found")
                return UserResponse()
        except Exception as e:
            logger.error(f"Error in UpdateUser: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return UserResponse()

    async def DeleteUser(self, request, context: ServicerContext):
        """Delete a user."""
        try:
            success = await self.identity_manager.delete_user(request.username)
            return StatusResponse(
                success=success,
                message="User deleted successfully" if success else "Failed to delete user"
            )
        except Exception as e:
            logger.error(f"Error in DeleteUser: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return StatusResponse(success=False, message=str(e))

    async def GetUser(self, request, context: ServicerContext):
        """Get user by username."""
        try:
            user = await self.identity_manager.get_user(request.username)
            if user:
                return UserResponse(
                    user=User(**user),
                    message="User found"
                )
            else:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details("User not found")
                return UserResponse()
        except Exception as e:
            logger.error(f"Error in GetUser: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return UserResponse()

    async def ListUsers(self, request, context: ServicerContext):
        """List users with optional filtering."""
        try:
            users = await self.identity_manager.list_users(
                limit=request.limit if hasattr(request, 'limit') else 100,
                offset=request.offset if hasattr(request, 'offset') else 0,
                role=request.role if hasattr(request, 'role') else None,
                disabled=request.disabled if hasattr(request, 'disabled') else None,
            )
            return UsersResponse(
                users=[User(**u) for u in users],
                total=len(users)
            )
        except Exception as e:
            logger.error(f"Error in ListUsers: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return UsersResponse()

    async def SetUserAttribute(self, request, context: ServicerContext):
        """Set a user attribute."""
        try:
            success = await self.identity_manager.set_user_attribute(
                request.username,
                request.key,
                request.value
            )
            return StatusResponse(
                success=success,
                message="Attribute set successfully" if success else "Failed to set attribute"
            )
        except Exception as e:
            logger.error(f"Error in SetUserAttribute: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return StatusResponse(success=False, message=str(e))

    async def DeleteUserAttribute(self, request, context: ServicerContext):
        """Delete a user attribute."""
        try:
            success = await self.identity_manager.delete_user_attribute(
                request.username,
                request.key
            )
            return StatusResponse(
                success=success,
                message="Attribute deleted successfully" if success else "Failed to delete attribute"
            )
        except Exception as e:
            logger.error(f"Error in DeleteUserAttribute: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return StatusResponse(success=False, message=str(e))

    async def EnableMFA(self, request, context: ServicerContext):
        """Enable MFA for a user."""
        try:
            mfa_config = await self.identity_manager.enable_mfa(request.username)
            if mfa_config:
                return MFAConfigResponse(
                    config=MFAConfig(**mfa_config),
                    message="MFA enabled successfully"
                )
            else:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details("User not found")
                return MFAConfigResponse()
        except Exception as e:
            logger.error(f"Error in EnableMFA: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return MFAConfigResponse()

    async def DisableMFA(self, request, context: ServicerContext):
        """Disable MFA for a user."""
        try:
            success = await self.identity_manager.disable_mfa(request.username)
            return StatusResponse(
                success=success,
                message="MFA disabled successfully" if success else "Failed to disable MFA"
            )
        except Exception as e:
            logger.error(f"Error in DisableMFA: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return StatusResponse(success=False, message=str(e))

    async def VerifyMFA(self, request, context: ServicerContext):
        """Verify MFA code for a user."""
        try:
            verified = await self.identity_manager.verify_mfa(request.username, request.code)
            return MFAVerificationResponse(
                verified=verified,
                message="MFA verified successfully" if verified else "Invalid MFA code"
            )
        except Exception as e:
            logger.error(f"Error in VerifyMFA: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return MFAVerificationResponse(verified=False, message=str(e))

    async def CreateUserGroup(self, request, context: ServicerContext):
        """Create a user group."""
        try:
            group = await self.group_manager.create_group(
                name=request.name,
                description=request.description if hasattr(request, 'description') else "",
                usernames=list(request.usernames) if hasattr(request, 'usernames') else None,
                attributes=dict(request.attributes) if hasattr(request, 'attributes') else None,
            )
            if group:
                return UserGroupResponse(
                    group=UserGroup(**group),
                    message="Group created successfully"
                )
            else:
                context.set_code(grpc.StatusCode.INTERNAL)
                context.set_details("Failed to create group")
                return UserGroupResponse()
        except Exception as e:
            logger.error(f"Error in CreateUserGroup: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return UserGroupResponse()

    async def UpdateUserGroup(self, request, context: ServicerContext):
        """Update a user group."""
        try:
            group = await self.group_manager.update_group(
                group_id=request.group_id,
                name=request.name if hasattr(request, 'name') else None,
                description=request.description if hasattr(request, 'description') else None,
                usernames=list(request.usernames) if hasattr(request, 'usernames') else None,
                attributes=dict(request.attributes) if hasattr(request, 'attributes') else None,
            )
            if group:
                return UserGroupResponse(
                    group=UserGroup(**group),
                    message="Group updated successfully"
                )
            else:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details("Group not found")
                return UserGroupResponse()
        except Exception as e:
            logger.error(f"Error in UpdateUserGroup: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return UserGroupResponse()

    async def DeleteUserGroup(self, request, context: ServicerContext):
        """Delete a user group."""
        try:
            success = await self.group_manager.delete_group(request.group_id)
            return StatusResponse(
                success=success,
                message="Group deleted successfully" if success else "Failed to delete group"
            )
        except Exception as e:
            logger.error(f"Error in DeleteUserGroup: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return StatusResponse(success=False, message=str(e))

    async def GetUserGroup(self, request, context: ServicerContext):
        """Get a group by ID."""
        try:
            group = await self.group_manager.get_group(request.group_id)
            if group:
                return UserGroupResponse(
                    group=UserGroup(**group),
                    message="Group found"
                )
            else:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details("Group not found")
                return UserGroupResponse()
        except Exception as e:
            logger.error(f"Error in GetUserGroup: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return UserGroupResponse()

    async def ListUserGroups(self, request, context: ServicerContext):
        """List all groups."""
        try:
            groups = await self.group_manager.list_groups(
                limit=request.limit if hasattr(request, 'limit') else 100,
                offset=request.offset if hasattr(request, 'offset') else 0,
            )
            return UserGroupsResponse(
                groups=[UserGroup(**g) for g in groups],
                total=len(groups)
            )
        except Exception as e:
            logger.error(f"Error in ListUserGroups: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return UserGroupsResponse()

    async def AddUserToGroup(self, request, context: ServicerContext):
        """Add a user to a group."""
        try:
            success = await self.group_manager.add_user_to_group(
                request.username,
                request.group_id
            )
            return StatusResponse(
                success=success,
                message="User added to group successfully" if success else "Failed to add user to group"
            )
        except Exception as e:
            logger.error(f"Error in AddUserToGroup: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return StatusResponse(success=False, message=str(e))

    async def RemoveUserFromGroup(self, request, context: ServicerContext):
        """Remove a user from a group."""
        try:
            success = await self.group_manager.remove_user_from_group(
                request.username,
                request.group_id
            )
            return StatusResponse(
                success=success,
                message="User removed from group successfully" if success else "Failed to remove user from group"
            )
        except Exception as e:
            logger.error(f"Error in RemoveUserFromGroup: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return StatusResponse(success=False, message=str(e))

    async def ConfigureSSO(self, request, context: ServicerContext):
        """Configure SSO provider."""
        try:
            config = await self.identity_manager.configure_sso(
                provider=request.provider,
                client_id=request.client_id,
                metadata=dict(request.metadata) if hasattr(request, 'metadata') else None,
            )
            return SSOConfigResponse(
                config=SSOConfig(**config),
                message="SSO configured successfully"
            )
        except Exception as e:
            logger.error(f"Error in ConfigureSSO: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return SSOConfigResponse()

    async def SSOLogin(self, request, context: ServicerContext):
        """Perform SSO login."""
        try:
            result = await self.identity_manager.sso_login(
                provider=request.provider,
                token=request.token
            )
            if result:
                return SSOLoginResponse(
                    success=True,
                    user=User(**result),
                    token="jwt_token_placeholder",
                    message="SSO login successful"
                )
            else:
                return SSOLoginResponse(
                    success=False,
                    message="SSO login failed"
                )
        except Exception as e:
            logger.error(f"Error in SSOLogin: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return SSOLoginResponse(success=False, message=str(e))

    async def HealthCheck(self, request, context: ServicerContext):
        """Health check endpoint."""
        return StatusResponse(
            success=True,
            message="Service is healthy"
        )


# Response classes (simplified - in production these would be generated from proto)
class UserResponse:
    def __init__(self, user=None, message=""):
        self.user = user
        self.message = message


class UsersResponse:
    def __init__(self, users=None, total=0):
        self.users = users or []
        self.total = total


class StatusResponse:
    def __init__(self, success=False, message=""):
        self.success = success
        self.message = message


class MFAConfig:
    def __init__(self, secret="", recovery_codes=None, enabled=False):
        self.secret = secret
        self.recovery_codes = recovery_codes or []
        self.enabled = enabled


class MFAConfigResponse:
    def __init__(self, config=None, message=""):
        self.config = config
        self.message = message


class MFAVerificationResponse:
    def __init__(self, verified=False, message=""):
        self.verified = verified
        self.message = message


class UserGroupResponse:
    def __init__(self, group=None, message=""):
        self.group = group
        self.message = message


class UserGroupsResponse:
    def __init__(self, groups=None, total=0):
        self.groups = groups or []
        self.total = total


class SSOConfig:
    def __init__(self, provider="", client_id="", metadata=None, enabled=False):
        self.provider = provider
        self.client_id = client_id
        self.metadata = metadata or {}
        self.enabled = enabled


class SSOConfigResponse:
    def __init__(self, config=None, message=""):
        self.config = config
        self.message = message


class SSOLoginResponse:
    def __init__(self, success=False, user=None, token="", message=""):
        self.success = success
        self.user = user
        self.token = token
        self.message = message


async def serve(port: int = DEFAULT_PORT) -> None:
    """Start the gRPC server."""
    server = grpc.aio.server()
    servicer = IdentityManagementServicer()
    
    # In production, we would add the servicer to the server using generated protobuf code
    # For now, we'll just log that the server is starting
    logger.info(f"Starting {SERVICE_NAME} gRPC server on port {port}")
    
    # Start the server (simplified - in production would use actual gRPC binding)
    await server.start()
    logger.info(f"{SERVICE_NAME} gRPC server started on port {port}")
    
    try:
        await server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("Shutting down server...")
        await server.stop(0)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(serve())
