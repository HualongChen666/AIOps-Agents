# -*- coding: utf-8 -*-
"""gRPC server for the Identity Management Service.

This module exposes the identity/group managers over a *real* gRPC endpoint using
the generic (JSON) codec, so it can be started with ``python -m ...grpc.server``
and consumed by any gRPC client that speaks the JSON payload contract.  It no
longer relies on hand-rolled placeholder message classes.
"""

import asyncio
import importlib.util
import json
import logging
import os
import sys
from typing import Any, Awaitable, Callable, Dict, Mapping

# Add project root to path for core.* imports.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))


def _import_grpc():
    """Import the installed grpc library, avoiding the sibling ``grpc`` package name clash.

    This module lives inside a package literally named ``grpc``; when the service
    directory is on ``sys.path`` (e.g. running ``python grpc/server.py`` from the
    service folder) it shadows the installed library.  We temporarily strip such
    shadowing entries so ``import grpc`` resolves to the real distribution.
    """
    service_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    saved = list(sys.path)
    sys.path = [
        p for p in sys.path
        if os.path.abspath(p or ".") != service_dir
    ]
    try:
        import grpc as _grpc
        from grpc.aio import ServicerContext as _ServicerContext

        return _grpc, _ServicerContext
    finally:
        sys.path = saved


grpc, ServicerContext = _import_grpc()


def _load_sibling(module_name: str):
    """Load a sibling module (identity_manager/group_manager) by file path.

    The sibling modules rely on bare ``core.*`` imports (project root already on
    ``sys.path``) and must not drag the service directory back onto ``sys.path``
    (which would re-shadow the grpc library).
    """
    service_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    path = os.path.join(service_dir, f"{module_name}.py")
    spec = importlib.util.spec_from_file_location(f"_idm_svc_{module_name}", path)
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise ImportError(f"Cannot load sibling module {module_name} from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_identity_manager_module = _load_sibling("identity_manager")
_group_manager_module = _load_sibling("group_manager")

IdentityManager = _identity_manager_module.IdentityManager
GroupManager = _group_manager_module.GroupManager

from core.auth_service import create_access_token  # noqa: E402

logger = logging.getLogger(__name__)

SERVICE_NAME = "identity_management_service"
DEFAULT_PORT = int(os.getenv("GRPC_PORT", "50053"))

# Fully-qualified gRPC service name exposed by this server.
SERVICE_FQN = "identity.IdentityManagementService"


def _json_deserialize(payload: bytes) -> Dict[str, Any]:
    if not payload:
        return {}
    return json.loads(payload.decode("utf-8"))


def _json_serialize(message: Any) -> bytes:
    return json.dumps(message, default=str).encode("utf-8")


class IdentityManagementServicer:
    """Real gRPC servicer delegating to the identity/group managers."""

    def __init__(self) -> None:
        self.identity_manager = IdentityManager()
        self.group_manager = GroupManager()

    # ---- user handlers -------------------------------------------------
    async def CreateUser(self, request: Mapping[str, Any], context: ServicerContext) -> Dict[str, Any]:
        user = await self.identity_manager.create_user(
            username=request.get("username", ""),
            password=request.get("password", ""),
            email=request.get("email"),
            full_name=request.get("full_name"),
            role=request.get("role", "user"),
            attributes=request.get("attributes") or None,
        )
        if not user:
            await context.abort(grpc.StatusCode.INTERNAL, "Failed to create user")
        return {"user": user, "message": "User created successfully"}

    async def UpdateUser(self, request: Mapping[str, Any], context: ServicerContext) -> Dict[str, Any]:
        user = await self.identity_manager.update_user(
            username=request.get("username", ""),
            email=request.get("email"),
            full_name=request.get("full_name"),
            role=request.get("role"),
            disabled=request.get("disabled"),
            attributes=request.get("attributes") or None,
        )
        if not user:
            await context.abort(grpc.StatusCode.NOT_FOUND, "User not found")
        return {"user": user, "message": "User updated successfully"}

    async def DeleteUser(self, request: Mapping[str, Any], context: ServicerContext) -> Dict[str, Any]:
        success = await self.identity_manager.delete_user(request.get("username", ""))
        return {"success": success, "message": "User deleted successfully" if success else "Failed to delete user"}

    async def GetUser(self, request: Mapping[str, Any], context: ServicerContext) -> Dict[str, Any]:
        user = await self.identity_manager.get_user(request.get("username", ""))
        if not user:
            await context.abort(grpc.StatusCode.NOT_FOUND, "User not found")
        return {"user": user, "message": "User found"}

    async def ListUsers(self, request: Mapping[str, Any], context: ServicerContext) -> Dict[str, Any]:
        users = await self.identity_manager.list_users(
            limit=request.get("limit", 100),
            offset=request.get("offset", 0),
            role=request.get("role"),
            disabled=request.get("disabled"),
        )
        return {"users": users, "total": len(users)}

    async def SetUserAttribute(self, request: Mapping[str, Any], context: ServicerContext) -> Dict[str, Any]:
        success = await self.identity_manager.set_user_attribute(
            request.get("username", ""), request.get("key", ""), request.get("value", "")
        )
        return {"success": success, "message": "Attribute set successfully" if success else "Failed to set attribute"}

    async def DeleteUserAttribute(self, request: Mapping[str, Any], context: ServicerContext) -> Dict[str, Any]:
        success = await self.identity_manager.delete_user_attribute(
            request.get("username", ""), request.get("key", "")
        )
        return {"success": success, "message": "Attribute deleted successfully" if success else "Failed to delete attribute"}

    async def EnableMFA(self, request: Mapping[str, Any], context: ServicerContext) -> Dict[str, Any]:
        config = await self.identity_manager.enable_mfa(request.get("username", ""))
        if not config:
            await context.abort(grpc.StatusCode.NOT_FOUND, "User not found")
        return {"config": config, "message": "MFA enabled successfully"}

    async def DisableMFA(self, request: Mapping[str, Any], context: ServicerContext) -> Dict[str, Any]:
        success = await self.identity_manager.disable_mfa(request.get("username", ""))
        return {"success": success, "message": "MFA disabled successfully" if success else "Failed to disable MFA"}

    async def VerifyMFA(self, request: Mapping[str, Any], context: ServicerContext) -> Dict[str, Any]:
        verified = await self.identity_manager.verify_mfa(
            request.get("username", ""), request.get("code", "")
        )
        return {"verified": verified, "message": "MFA verified successfully" if verified else "Invalid MFA code"}

    # ---- group handlers ------------------------------------------------
    async def CreateUserGroup(self, request: Mapping[str, Any], context: ServicerContext) -> Dict[str, Any]:
        group = await self.group_manager.create_group(
            name=request.get("name", ""),
            description=request.get("description", ""),
            usernames=request.get("usernames") or None,
            attributes=request.get("attributes") or None,
        )
        if not group:
            await context.abort(grpc.StatusCode.INTERNAL, "Failed to create group")
        return {"group": group, "message": "Group created successfully"}

    async def UpdateUserGroup(self, request: Mapping[str, Any], context: ServicerContext) -> Dict[str, Any]:
        group = await self.group_manager.update_group(
            group_id=request.get("group_id", 0),
            name=request.get("name"),
            description=request.get("description"),
            usernames=request.get("usernames") or None,
            attributes=request.get("attributes") or None,
        )
        if not group:
            await context.abort(grpc.StatusCode.NOT_FOUND, "Group not found")
        return {"group": group, "message": "Group updated successfully"}

    async def DeleteUserGroup(self, request: Mapping[str, Any], context: ServicerContext) -> Dict[str, Any]:
        success = await self.group_manager.delete_group(request.get("group_id", 0))
        return {"success": success, "message": "Group deleted successfully" if success else "Failed to delete group"}

    async def GetUserGroup(self, request: Mapping[str, Any], context: ServicerContext) -> Dict[str, Any]:
        group = await self.group_manager.get_group(request.get("group_id", 0))
        if not group:
            await context.abort(grpc.StatusCode.NOT_FOUND, "Group not found")
        return {"group": group, "message": "Group found"}

    async def ListUserGroups(self, request: Mapping[str, Any], context: ServicerContext) -> Dict[str, Any]:
        groups = await self.group_manager.list_groups(
            limit=request.get("limit", 100), offset=request.get("offset", 0)
        )
        return {"groups": groups, "total": len(groups)}

    async def AddUserToGroup(self, request: Mapping[str, Any], context: ServicerContext) -> Dict[str, Any]:
        success = await self.group_manager.add_user_to_group(
            request.get("username", ""), request.get("group_id", 0)
        )
        return {"success": success, "message": "User added to group successfully" if success else "Failed to add user to group"}

    async def RemoveUserFromGroup(self, request: Mapping[str, Any], context: ServicerContext) -> Dict[str, Any]:
        success = await self.group_manager.remove_user_from_group(
            request.get("username", ""), request.get("group_id", 0)
        )
        return {"success": success, "message": "User removed from group successfully" if success else "Failed to remove user from group"}

    # ---- SSO handlers --------------------------------------------------
    async def ConfigureSSO(self, request: Mapping[str, Any], context: ServicerContext) -> Dict[str, Any]:
        config = await self.identity_manager.configure_sso(
            provider=request.get("provider", ""),
            client_id=request.get("client_id", ""),
            metadata=request.get("metadata") or None,
        )
        return {"config": config, "message": "SSO configured successfully"}

    async def SSOLogin(self, request: Mapping[str, Any], context: ServicerContext) -> Dict[str, Any]:
        result = await self.identity_manager.sso_login(
            provider=request.get("provider", ""), token=request.get("token", "")
        )
        if not result:
            return {"success": False, "user": None, "token": None, "message": "SSO login failed"}
        token = create_access_token(
            {"sub": result["username"], "role": result.get("role", "user")}
        )
        return {"success": True, "user": result, "token": token, "message": "SSO login successful"}

    async def HealthCheck(self, request: Mapping[str, Any], context: ServicerContext) -> Dict[str, Any]:
        return {"success": True, "message": "Service is healthy"}


# Public RPC methods exposed by the servicer.
_RPC_METHODS = (
    "CreateUser",
    "UpdateUser",
    "DeleteUser",
    "GetUser",
    "ListUsers",
    "SetUserAttribute",
    "DeleteUserAttribute",
    "EnableMFA",
    "DisableMFA",
    "VerifyMFA",
    "CreateUserGroup",
    "UpdateUserGroup",
    "DeleteUserGroup",
    "GetUserGroup",
    "ListUserGroups",
    "AddUserToGroup",
    "RemoveUserFromGroup",
    "ConfigureSSO",
    "SSOLogin",
    "HealthCheck",
)


def build_generic_handler(servicer: IdentityManagementServicer) -> grpc.GenericRpcHandler:
    """Build a gRPC generic handler exposing the servicer's JSON RPC methods."""
    handlers: Dict[str, grpc.RpcMethodHandler] = {}
    for name in _RPC_METHODS:
        behavior: Callable[..., Awaitable[Any]] = getattr(servicer, name)
        handlers[name] = grpc.unary_unary_rpc_method_handler(
            behavior,
            request_deserializer=_json_deserialize,
            response_serializer=_json_serialize,
        )
    return grpc.method_handlers_generic_handler(SERVICE_FQN, handlers)


async def serve(port: int = DEFAULT_PORT, host: str = "0.0.0.0") -> None:
    """Start the real gRPC server and block until termination."""
    server = grpc.aio.server()
    servicer = IdentityManagementServicer()
    server.add_generic_rpc_handlers((build_generic_handler(servicer),))

    bound_port = server.add_insecure_port(f"{host}:{port}")
    if bound_port == 0:
        raise RuntimeError(f"Failed to bind {SERVICE_NAME} gRPC server to {host}:{port}")

    await server.start()
    logger.info(f"{SERVICE_NAME} gRPC server started on {host}:{bound_port}")

    try:
        await server.wait_for_termination()
    except (KeyboardInterrupt, asyncio.CancelledError):
        logger.info("Shutting down server...")
        await server.stop(0)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(serve())
