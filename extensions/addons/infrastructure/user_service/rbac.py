# -*- coding: utf-8 -*-
"""Role-based access control (task 29.3)."""

from __future__ import annotations

from typing import Dict, List, Optional

from services.user_service.repository import UserRepository
from services.user_service.schemas import Permission, Role, User


class RBACManager:
    """Manages roles and permissions."""

    DEFAULT_PERMISSIONS: List[Permission] = [
        Permission(permission_id="p1", resource="user", action="read", description="Read users"),
        Permission(permission_id="p2", resource="user", action="write", description="Write users"),
        Permission(permission_id="p3", resource="role", action="read", description="Read roles"),
        Permission(permission_id="p4", resource="role", action="write", description="Write roles"),
        Permission(permission_id="p5", resource="org", action="read", description="Read orgs"),
        Permission(permission_id="p6", resource="org", action="write", description="Write orgs"),
        Permission(permission_id="p7", resource="config", action="read", description="Read config"),
        Permission(
            permission_id="p8", resource="config", action="write", description="Write config"
        ),
    ]

    def __init__(self, repo: UserRepository) -> None:
        self.repo = repo
        self._permissions: Dict[str, Permission] = {
            p.permission_id: p for p in self.DEFAULT_PERMISSIONS
        }

    async def create_role(self, role: Role) -> Role:
        await self.repo.save_role(role)
        return role

    async def get_role(self, role_id: str) -> Optional[Role]:
        return await self.repo.get_role(role_id)

    async def list_roles(self, tenant_id: str) -> List[Role]:
        return await self.repo.list_roles(tenant_id)

    async def assign_permissions(self, role_id: str, permission_ids: List[str]) -> Optional[Role]:
        role = await self.repo.get_role(role_id)
        if not role:
            return None
        role.permissions = [p for p in permission_ids if p in self._permissions]
        await self.repo.save_role(role)
        return role

    def check_permission(self, user: User, resource: str, action: str) -> bool:
        # Simplified: role name equals permission set
        if user.role == "admin":
            return True
        if user.role == "operator" and action in ("read", "write"):
            return True
        if user.role == "viewer" and action == "read":
            return True
        return False
