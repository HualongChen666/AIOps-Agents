# -*- coding: utf-8 -*-
"""User orchestrator domain logic."""

from __future__ import annotations

from typing import Optional

from services.user_service.audit_logger import UserAuditLogger
from services.user_service.auth import AuthManager
from services.user_service.organization import OrganizationManager
from services.user_service.rbac import RBACManager
from services.user_service.repository import UserRepository
from services.user_service.saga import UserSagaOrchestrator
from services.user_service.schemas import (
    AuthToken,
    Organization,
    Role,
    SagaTransaction,
    Session,
    User,
    UserCreate,
)
from services.user_service.session import SessionManager
from services.user_service.user_manager import UserManager


class UserOrchestrator:
    """Coordinates user microservice operations."""

    def __init__(self, repo: UserRepository) -> None:
        self.repo = repo
        self.users = UserManager(repo)
        self.rbac = RBACManager(repo)
        self.organizations = OrganizationManager(repo)
        self.auth = AuthManager(repo)
        self.sessions = SessionManager(repo)
        self.audit = UserAuditLogger(repo)

    async def create_user(self, data: UserCreate) -> User:
        user = await self.users.create(data)
        await self.audit.log(user.user_id, "user_created", {"username": user.username})
        return user

    async def login(self, username: str, password: str) -> Optional[AuthToken]:
        return await self.auth.login(username, password)

    async def create_role(self, role: Role) -> Role:
        return await self.rbac.create_role(role)

    async def create_organization(self, org: Organization) -> Organization:
        return await self.organizations.create(org)

    async def create_session(self, user_id: str) -> Session:
        return await self.sessions.create(user_id)

    async def run_saga(self, saga: SagaTransaction) -> SagaTransaction:
        orchestrator = UserSagaOrchestrator(self.repo)
        return await orchestrator.execute(saga)
