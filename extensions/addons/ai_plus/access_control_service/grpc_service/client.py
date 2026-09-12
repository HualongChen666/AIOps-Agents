# -*- coding: utf-8 -*-
"""gRPC client for Access Control Service (real JSON-over-gRPC transport)."""

import logging
import os
import sys
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))

from extensions.addons.ai_plus.json_grpc_rpc import JsonRpcClient

logger = logging.getLogger(__name__)

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = int(os.getenv("GRPC_PORT", "50054"))
SERVICE_FQN = "accesscontrol.AccessControlService"


class AccessControlClient(JsonRpcClient):
    """Real gRPC client for the Access Control Service."""

    def __init__(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT):
        super().__init__(SERVICE_FQN, host, port)

    async def connect(self) -> bool:
        await super().connect()
        return True

    async def disconnect(self) -> None:
        await super().disconnect()

    async def _ensure_connected(self) -> None:
        if self._channel is None:
            await self.connect()

    async def _invoke(self, method: str, payload: Optional[Dict[str, Any]] = None) -> Any:
        await self._ensure_connected()
        return await self.call(method, payload or {})

    # Permission management
    async def create_permission(
        self, name: str, description: str, resource_type: str, actions: List[str]
    ) -> Optional[Dict[str, Any]]:
        return await self._invoke("create_permission", {
            "name": name, "description": description,
            "resource_type": resource_type, "actions": actions,
        })

    async def update_permission(
        self, permission_id: str, name: Optional[str] = None, description: Optional[str] = None,
        resource_type: Optional[str] = None, actions: Optional[List[str]] = None,
    ) -> Optional[Dict[str, Any]]:
        return await self._invoke("update_permission", {
            "permission_id": permission_id, "name": name, "description": description,
            "resource_type": resource_type, "actions": actions,
        })

    async def delete_permission(self, permission_id: str) -> bool:
        return await self._invoke("delete_permission", {"permission_id": permission_id})

    async def get_permission(self, permission_id: str) -> Optional[Dict[str, Any]]:
        return await self._invoke("get_permission", {"permission_id": permission_id})

    async def list_permissions(
        self, limit: int = 100, offset: int = 0, resource_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        return await self._invoke("list_permissions", {
            "limit": limit, "offset": offset, "resource_type": resource_type,
        })

    # Role management
    async def create_role(
        self, name: str, description: str, permission_ids: List[str],
        inherited_role_ids: List[str],
    ) -> Optional[Dict[str, Any]]:
        return await self._invoke("create_role", {
            "name": name, "description": description,
            "permission_ids": permission_ids, "inherited_role_ids": inherited_role_ids,
        })

    async def update_role(
        self, role_id: str, name: Optional[str] = None, description: Optional[str] = None,
        permission_ids: Optional[List[str]] = None, inherited_role_ids: Optional[List[str]] = None,
    ) -> Optional[Dict[str, Any]]:
        return await self._invoke("update_role", {
            "role_id": role_id, "name": name, "description": description,
            "permission_ids": permission_ids, "inherited_role_ids": inherited_role_ids,
        })

    async def delete_role(self, role_id: str) -> bool:
        return await self._invoke("delete_role", {"role_id": role_id})

    async def get_role(self, role_id: str) -> Optional[Dict[str, Any]]:
        return await self._invoke("get_role", {"role_id": role_id})

    async def list_roles(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        return await self._invoke("list_roles", {"limit": limit, "offset": offset})

    async def assign_role(self, subject_id: str, role_id: str) -> bool:
        return await self._invoke("assign_role", {"subject_id": subject_id, "role_id": role_id})

    async def revoke_role(self, subject_id: str, role_id: str) -> bool:
        return await self._invoke("revoke_role", {"subject_id": subject_id, "role_id": role_id})

    async def get_subject_roles(self, subject_id: str) -> List[Dict[str, Any]]:
        return await self._invoke("get_subject_roles", {"subject_id": subject_id})

    # Policy management
    async def create_policy(
        self, name: str, description: str, effect: str, subject_conditions: Dict[str, Any],
        resource_conditions: Dict[str, Any], environment_conditions: Dict[str, Any],
        actions: List[str], priority: int = 0,
    ) -> Optional[Dict[str, Any]]:
        return await self._invoke("create_policy", {
            "name": name, "description": description, "effect": effect,
            "subject_conditions": subject_conditions, "resource_conditions": resource_conditions,
            "environment_conditions": environment_conditions, "actions": actions, "priority": priority,
        })

    async def update_policy(
        self, policy_id: str, name: Optional[str] = None, description: Optional[str] = None,
        enabled: Optional[bool] = None, effect: Optional[str] = None,
        subject_conditions: Optional[Dict[str, Any]] = None,
        resource_conditions: Optional[Dict[str, Any]] = None,
        environment_conditions: Optional[Dict[str, Any]] = None,
        actions: Optional[List[str]] = None, priority: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        return await self._invoke("update_policy", {
            "policy_id": policy_id, "name": name, "description": description, "enabled": enabled,
            "effect": effect, "subject_conditions": subject_conditions,
            "resource_conditions": resource_conditions,
            "environment_conditions": environment_conditions,
            "actions": actions, "priority": priority,
        })

    async def delete_policy(self, policy_id: str) -> bool:
        return await self._invoke("delete_policy", {"policy_id": policy_id})

    async def get_policy(self, policy_id: str) -> Optional[Dict[str, Any]]:
        return await self._invoke("get_policy", {"policy_id": policy_id})

    async def list_policies(self, enabled_only: bool = True) -> List[Dict[str, Any]]:
        return await self._invoke("list_policies", {"enabled_only": enabled_only})

    # Access check & audit
    async def check_permission(
        self, subject_id: str, subject_type: str, subject_attributes: Dict[str, Any],
        subject_roles: List[str], subject_groups: List[str], resource_id: str,
        resource_type: str, resource_attributes: Dict[str, Any],
        resource_owner: Optional[str], action: str, environment_attributes: Dict[str, Any],
    ) -> Dict[str, Any]:
        return await self._invoke("check_permission", {
            "subject_id": subject_id, "subject_type": subject_type,
            "subject_attributes": subject_attributes, "subject_roles": subject_roles,
            "subject_groups": subject_groups, "resource_id": resource_id,
            "resource_type": resource_type, "resource_attributes": resource_attributes,
            "resource_owner": resource_owner, "action": action,
            "environment_attributes": environment_attributes,
        })

    async def get_audit_logs(
        self, subject_id: Optional[str] = None, resource_id: Optional[str] = None,
        start_time: Optional[int] = None, end_time: Optional[int] = None,
        limit: int = 100, offset: int = 0,
    ) -> List[Dict[str, Any]]:
        return await self._invoke("get_audit_logs", {
            "subject_id": subject_id, "resource_id": resource_id,
            "start_time": start_time, "end_time": end_time, "limit": limit, "offset": offset,
        })

    async def health_check(self) -> bool:
        return await self._invoke("health_check", {})


async def create_client(
    host: str = DEFAULT_HOST, port: int = DEFAULT_PORT
) -> AccessControlClient:
    """Create and connect an AccessControlClient."""
    client = AccessControlClient(host, port)
    await client.connect()
    return client
