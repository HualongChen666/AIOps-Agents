# -*- coding: utf-8 -*-
"""gRPC server for Access Control Service.

Exposes the real access-control managers (RBAC/ABAC/policy enforcement) over a
genuine gRPC endpoint using the shared JSON codec.  The same handler registry
also backs the service's HTTP ``/rpc/{method}`` endpoint.
"""

import logging
import os
import sys
from typing import Any, Dict, Optional

# Make the service modules and project root importable.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from access_control_manager import AccessControlManager
from permission_checker import PermissionChecker
from policy_enforcer import PolicyEnforcer

from extensions.addons.ai_plus.json_grpc_rpc import JsonRpcServer

logger = logging.getLogger(__name__)

SERVICE_NAME = "access_control_service"
DEFAULT_PORT = int(os.getenv("GRPC_PORT", "50054"))
SERVICE_FQN = "accesscontrol.AccessControlService"


class AccessControlRPCServer(JsonRpcServer):
    """Real gRPC server delegating to the access-control managers."""

    def __init__(self, storage) -> None:
        super().__init__(SERVICE_FQN)
        self.access_control_manager = AccessControlManager(storage)
        self.access_control_manager.initialize()
        self.policy_enforcer = PolicyEnforcer(self.access_control_manager)
        self.permission_checker = PermissionChecker(self.access_control_manager)
        self._register_handlers()

    def _register_handlers(self) -> None:
        acm = self.access_control_manager
        self.register("create_permission", lambda p: acm.create_permission(
            p["name"], p.get("description", ""), p["resource_type"], p.get("actions", [])
        ))
        self.register("update_permission", lambda p: acm.update_permission(
            p["permission_id"],
            name=p.get("name"), description=p.get("description"),
            resource_type=p.get("resource_type"), actions=p.get("actions"),
        ) or {})
        self.register("delete_permission", lambda p: acm.delete_permission(p["permission_id"]))
        self.register("get_permission", lambda p: acm.get_permission(p["permission_id"]))
        self.register("list_permissions", lambda p: acm.list_permissions(
            limit=p.get("limit", 100), offset=p.get("offset", 0),
            resource_type=p.get("resource_type"),
        ))
        self.register("create_role", lambda p: acm.create_role(
            p["name"], p.get("description", ""), p.get("permission_ids", []),
            p.get("inherited_role_ids", []),
        ))
        self.register("update_role", lambda p: acm.update_role(
            p["role_id"], name=p.get("name"), description=p.get("description"),
            permission_ids=p.get("permission_ids"), inherited_role_ids=p.get("inherited_role_ids"),
        ) or {})
        self.register("delete_role", lambda p: acm.delete_role(p["role_id"]))
        self.register("get_role", lambda p: acm.get_role(p["role_id"]))
        self.register("list_roles", lambda p: acm.list_roles(
            limit=p.get("limit", 100), offset=p.get("offset", 0)
        ))
        self.register("assign_role", lambda p: acm.assign_role(p["subject_id"], p["role_id"]))
        self.register("revoke_role", lambda p: acm.revoke_role(p["subject_id"], p["role_id"]))
        self.register("get_subject_roles", lambda p: acm.get_subject_roles(p["subject_id"]))
        self.register("create_policy", lambda p: acm.create_policy(
            p["name"], p.get("description", ""), p.get("effect", "allow"),
            p.get("subject_conditions", {}), p.get("resource_conditions", {}),
            p.get("environment_conditions", {}), p.get("actions", []), p.get("priority", 0),
        ))
        self.register("update_policy", lambda p: acm.update_policy(
            p["policy_id"],
            name=p.get("name"), description=p.get("description"), enabled=p.get("enabled"),
            effect=p.get("effect"), subject_conditions=p.get("subject_conditions"),
            resource_conditions=p.get("resource_conditions"),
            environment_conditions=p.get("environment_conditions"),
            actions=p.get("actions"), priority=p.get("priority"),
        ) or {})
        self.register("delete_policy", lambda p: acm.delete_policy(p["policy_id"]))
        self.register("get_policy", lambda p: acm.get_policy(p["policy_id"]))
        self.register("list_policies", lambda p: acm.list_policies(p.get("enabled_only", True)))
        self.register("check_permission", self._check_permission)
        self.register("get_audit_logs", lambda p: self.policy_enforcer.get_audit_logs(
            subject_id=p.get("subject_id"), resource_id=p.get("resource_id"),
            start_time=p.get("start_time"), end_time=p.get("end_time"),
            limit=p.get("limit", 100), offset=p.get("offset", 0),
        ))
        self.register("health_check", lambda p: True)

    def _check_permission(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self.policy_enforcer.enforce_policy(
            subject_id=payload.get("subject_id", ""),
            subject_type=payload.get("subject_type", "user"),
            subject_attributes=payload.get("subject_attributes", {}),
            subject_roles=payload.get("subject_roles", []),
            subject_groups=payload.get("subject_groups", []),
            resource_id=payload.get("resource_id", "unknown"),
            resource_type=payload.get("resource_type", ""),
            resource_attributes=payload.get("resource_attributes", {}),
            resource_owner=payload.get("resource_owner"),
            action=payload.get("action", ""),
            environment_attributes=payload.get("environment_attributes", {}),
        )


async def serve(storage, port: int = DEFAULT_PORT) -> None:
    """Start the real gRPC server (blocking until termination)."""
    server = AccessControlRPCServer(storage)
    await server.start("0.0.0.0", port)
    logger.info(f"{SERVICE_NAME} gRPC server started on port {port}")
    await server.wait_for_termination()
