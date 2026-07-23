# -*- coding: utf-8 -*-
"""User repository abstraction."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from services.user_service.schemas import (
    AuditLogEntry,
    Organization,
    Role,
    SagaTransaction,
    Session,
    User,
)


class UserRepository:
    """Abstract user repository."""

    async def save_user(self, user: User) -> str:
        raise NotImplementedError

    async def get_user(self, user_id: str) -> Optional[User]:
        raise NotImplementedError

    async def get_user_by_username(self, username: str) -> Optional[User]:
        raise NotImplementedError

    async def list_users(self, tenant_id: str, limit: int = 100) -> List[User]:
        raise NotImplementedError

    async def delete_user(self, user_id: str) -> bool:
        raise NotImplementedError

    async def save_role(self, role: Role) -> str:
        raise NotImplementedError

    async def get_role(self, role_id: str) -> Optional[Role]:
        raise NotImplementedError

    async def list_roles(self, tenant_id: str) -> List[Role]:
        raise NotImplementedError

    async def save_organization(self, org: Organization) -> str:
        raise NotImplementedError

    async def get_organization(self, org_id: str) -> Optional[Organization]:
        raise NotImplementedError

    async def list_organizations(self, tenant_id: str) -> List[Organization]:
        raise NotImplementedError

    async def save_session(self, session: Session) -> str:
        raise NotImplementedError

    async def get_session(self, session_id: str) -> Optional[Session]:
        raise NotImplementedError

    async def delete_session(self, session_id: str) -> bool:
        raise NotImplementedError

    async def save_audit_log(self, entry: AuditLogEntry) -> str:
        raise NotImplementedError

    async def list_audit_logs(self, user_id: str) -> List[AuditLogEntry]:
        raise NotImplementedError

    async def save_saga(self, saga: SagaTransaction) -> str:
        raise NotImplementedError

    async def get_saga(self, saga_id: str) -> Optional[SagaTransaction]:
        raise NotImplementedError


class InMemoryUserRepository(UserRepository):
    """In-memory user repository for tests and local dev."""

    def __init__(self) -> None:
        self._users: Dict[str, User] = {}
        self._users_by_username: Dict[str, str] = {}
        self._roles: Dict[str, Role] = {}
        self._organizations: Dict[str, Organization] = {}
        self._sessions: Dict[str, Session] = {}
        self._audit_logs: Dict[str, List[AuditLogEntry]] = {}
        self._sagas: Dict[str, SagaTransaction] = {}

    async def save_user(self, user: User) -> str:
        user.updated_at = datetime.utcnow()
        self._users[user.user_id] = user
        self._users_by_username[user.username] = user.user_id
        return user.user_id

    async def get_user(self, user_id: str) -> Optional[User]:
        return self._users.get(user_id)

    async def get_user_by_username(self, username: str) -> Optional[User]:
        user_id = self._users_by_username.get(username)
        if user_id:
            return self._users.get(user_id)
        return None

    async def list_users(self, tenant_id: str, limit: int = 100) -> List[User]:
        users = [u for u in self._users.values() if u.tenant_id == tenant_id]
        users.sort(key=lambda u: u.created_at, reverse=True)
        return users[:limit]

    async def delete_user(self, user_id: str) -> bool:
        user = self._users.pop(user_id, None)
        if user:
            self._users_by_username.pop(user.username, None)
            return True
        return False

    async def save_role(self, role: Role) -> str:
        self._roles[role.role_id] = role
        return role.role_id

    async def get_role(self, role_id: str) -> Optional[Role]:
        return self._roles.get(role_id)

    async def list_roles(self, tenant_id: str) -> List[Role]:
        return [r for r in self._roles.values() if r.tenant_id == tenant_id]

    async def save_organization(self, org: Organization) -> str:
        self._organizations[org.org_id] = org
        return org.org_id

    async def get_organization(self, org_id: str) -> Optional[Organization]:
        return self._organizations.get(org_id)

    async def list_organizations(self, tenant_id: str) -> List[Organization]:
        return [o for o in self._organizations.values() if o.tenant_id == tenant_id]

    async def save_session(self, session: Session) -> str:
        self._sessions[session.session_id] = session
        return session.session_id

    async def get_session(self, session_id: str) -> Optional[Session]:
        return self._sessions.get(session_id)

    async def delete_session(self, session_id: str) -> bool:
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

    async def save_audit_log(self, entry: AuditLogEntry) -> str:
        self._audit_logs.setdefault(entry.user_id, []).append(entry)
        return entry.log_id

    async def list_audit_logs(self, user_id: str) -> List[AuditLogEntry]:
        return self._audit_logs.get(user_id, [])

    async def save_saga(self, saga: SagaTransaction) -> str:
        self._sagas[saga.saga_id] = saga
        return saga.saga_id

    async def get_saga(self, saga_id: str) -> Optional[SagaTransaction]:
        return self._sagas.get(saga_id)


async def get_repository(use_in_memory: bool = True) -> UserRepository:
    """Return repository instance based on configuration."""
    return InMemoryUserRepository()
