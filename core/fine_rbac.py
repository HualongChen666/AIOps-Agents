# -*- coding: utf-8 -*-
"""Fine‑grained RBAC (tenant‑resource‑action).

A lightweight in‑memory implementation suitable for development and CI.
In production the policy store would be a PostgreSQL table populated by an
admin UI.

Usage example in a router:

```python
from fastapi import Depends, APIRouter
from core.fine_rbac import require_permission

router = APIRouter()

@router.get("/secure-data")
async def get_secure_data(
    permission: None = Depends(require_permission(resource="data", action="read")):
    return {"msg": "you have access"}
```
"""

from __future__ import annotations

from typing import Dict, Set, Tuple

from fastapi import Depends, HTTPException, status

# ---------------------------------------------------------------------------
# In‑memory policy store.
# Key: (tenant_id, resource, action) -> set of roles allowed
# ---------------------------------------------------------------------------
_POLICY_STORE: Dict[Tuple[str, str, str], Set[str]] = {}


def grant_permission(tenant_id: str, resource: str, action: str, role: str) -> None:
    """Grant *role* permission to perform *action* on *resource* within *tenant*."""
    key = (tenant_id, resource, action)
    _POLICY_STORE.setdefault(key, set()).add(role)


def revoke_permission(tenant_id: str, resource: str, action: str, role: str) -> None:
    """Revoke a previously granted permission."""
    key = (tenant_id, resource, action)
    roles = _POLICY_STORE.get(key)
    if roles:
        roles.discard(role)
        if not roles:
            _POLICY_STORE.pop(key, None)


def check_permission(tenant_id: str, resource: str, action: str, role: str) -> bool:
    """Return ``True`` if *role* is allowed for the given triple."""
    allowed = _POLICY_STORE.get((tenant_id, resource, action), set())
    return role in allowed


def require_permission(resource: str, action: str):
    """FastAPI dependency that enforces fine‑grained RBAC.

    It extracts the current user via ``core.auth.get_current_user`` (which
    already validates the JWT) and determines the tenant via ``core.rbac.
    get_user_tenant``.  If the tenant cannot be resolved or the role is not
    permitted, a ``403`` error is raised.
    """

    async def _dependency(current_user=Depends(__import__("core.auth").auth.get_current_user)):
        # Resolve tenant – fallback to a default tenant if none is found.
        from core.rbac import get_user_tenant

        tenant = get_user_tenant(current_user.username) or "default"
        role = getattr(current_user, "role", "user")
        if not check_permission(tenant, resource, action, role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied for role '{role}' on {resource}:{action}",
            )
        return None

    return _dependency


# ---------------------------------------------------------------------------
# Example default policies – loaded at import time for demo purposes.
# ---------------------------------------------------------------------------
def _load_demo_policies():
    # Admins have full access on all resources.
    for res in ["*"]:
        grant_permission("default", res, "*", "admin")
    # Users can read "metrics" and "logs".
    grant_permission("default", "metrics", "read", "user")
    grant_permission("default", "logs", "read", "user")


_load_demo_policies()

__all__ = [
    "grant_permission",
    "revoke_permission",
    "check_permission",
    "require_permission",
]
