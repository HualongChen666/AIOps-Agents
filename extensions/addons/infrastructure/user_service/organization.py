# -*- coding: utf-8 -*-
"""Organization tree management (task 29.4)."""

from __future__ import annotations

from typing import List, Optional

from services.user_service.repository import UserRepository
from services.user_service.schemas import Organization


class OrganizationManager:
    """Manages organization tree."""

    def __init__(self, repo: UserRepository) -> None:
        self.repo = repo

    async def create(self, org: Organization) -> Organization:
        await self.repo.save_organization(org)
        return org

    async def get(self, org_id: str) -> Optional[Organization]:
        return await self.repo.get_organization(org_id)

    async def list(self, tenant_id: str) -> List[Organization]:
        return await self.repo.list_organizations(tenant_id)

    async def tree(self, tenant_id: str) -> List[dict]:
        orgs = await self.repo.list_organizations(tenant_id)
        by_parent: dict = {}
        for org in orgs:
            by_parent.setdefault(org.parent_id or "root", []).append(org)

        def build(parent_id: Optional[str], visited: set):
            nodes = []
            for org in by_parent.get(parent_id or "root", []):
                if org.org_id in visited:
                    continue
                visited.add(org.org_id)
                nodes.append(
                    {
                        "org_id": org.org_id,
                        "name": org.name,
                        "children": build(org.org_id, visited),
                    }
                )
                visited.discard(org.org_id)
            return nodes

        return build("root", set())
