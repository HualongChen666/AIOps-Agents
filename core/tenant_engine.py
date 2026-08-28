# -*- coding: utf-8 -*-
"""Simple in-memory + JSON-backed multi-tenant engine."""

from __future__ import annotations

import json
import logging
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, List, Optional

logger = logging.getLogger(__name__)
DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "tenants.json"
DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
_LOCK = threading.RLock()


@dataclass
class Quota:
    cpu: float = 0.0
    memory: float = 0.0
    disk: float = 0.0
    maxUsers: int = 0
    maxServices: int = 0
    maxAlerts: int = 0
    maxStorage: int = 0


@dataclass
class Usage:
    cpu: float = 0.0
    memory: float = 0.0
    disk: float = 0.0
    users: int = 0
    services: int = 0
    alerts: int = 0
    storage: int = 0


@dataclass
class Billing:
    cycle: str = "monthly"
    amount: float = 0.0
    currency: str = "CNY"
    nextBillingDate: str = ""


@dataclass
class Tenant:
    id: str
    name: str
    status: str = "active"
    contact: str = ""
    plan: str = "basic"
    quota: Quota = field(default_factory=Quota)
    usage: Usage = field(default_factory=Usage)
    billing: Billing = field(default_factory=Billing)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


_TENANTS: List[Tenant] = []

_PLAN_LIMITS = {
    "free": {
        "cpu": 20.0,
        "memory": 40.0,
        "disk": 100.0,
        "maxUsers": 5,
        "maxServices": 2,
        "maxAlerts": 100,
        "maxStorage": 10,
        "amount": 0,
    },
    "basic": {
        "cpu": 40.0,
        "memory": 80.0,
        "disk": 500.0,
        "maxUsers": 10,
        "maxServices": 5,
        "maxAlerts": 1000,
        "maxStorage": 100,
        "amount": 500,
    },
    "pro": {
        "cpu": 80.0,
        "memory": 160.0,
        "disk": 1000.0,
        "maxUsers": 50,
        "maxServices": 25,
        "maxAlerts": 5000,
        "maxStorage": 500,
        "amount": 2000,
    },
    "enterprise": {
        "cpu": 200.0,
        "memory": 400.0,
        "disk": 5000.0,
        "maxUsers": 100,
        "maxServices": 50,
        "maxAlerts": 10000,
        "maxStorage": 1000,
        "amount": 5000,
    },
}


def _next_billing_date() -> str:
    return (datetime.utcnow() + timedelta(days=30)).date().isoformat()


def _compute_quota(plan: str) -> Quota:
    limits = _PLAN_LIMITS.get(plan, _PLAN_LIMITS["basic"])
    return Quota(
        cpu=limits["cpu"],
        memory=limits["memory"],
        disk=limits["disk"],
        maxUsers=int(limits["maxUsers"]),
        maxServices=int(limits["maxServices"]),
        maxAlerts=int(limits["maxAlerts"]),
        maxStorage=int(limits["maxStorage"]),
    )


def _compute_billing(plan: str) -> Billing:
    limits = _PLAN_LIMITS.get(plan, _PLAN_LIMITS["basic"])
    return Billing(amount=limits["amount"], nextBillingDate=_next_billing_date())


def _dict_to_tenant(d: dict[str, Any]) -> Tenant:
    return Tenant(
        id=d.get("id", f"tenant-{uuid.uuid4().hex[:8]}"),
        name=d.get("name", ""),
        status=d.get("status", "active"),
        contact=d.get("contact", ""),
        plan=d.get("plan", "basic"),
        quota=Quota(**d.get("quota", {})),
        usage=Usage(**d.get("usage", {})),
        billing=Billing(**d.get("billing", {})),
        created_at=d.get("created_at", datetime.utcnow().isoformat()),
    )


def _load() -> None:
    global _TENANTS
    if not DATA_FILE.exists():
        _TENANTS = []
        return
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)
        if not isinstance(raw, list):
            raw = []
        _TENANTS = [_dict_to_tenant(item) for item in raw]
    except (json.JSONDecodeError, OSError) as exc:
        logger.error(f"Failed to load tenant data from {DATA_FILE}: {exc}")
        _TENANTS = []
    except Exception as exc:
        logger.error(f"Failed to load tenant data: {exc}")
        _TENANTS = []


def _save() -> None:
    import os
    import stat

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump([asdict(t) for t in _TENANTS], f, ensure_ascii=False, indent=2)

    # Set restrictive permissions for tenant data file (600 - owner read/write only)
    try:
        os.chmod(DATA_FILE, stat.S_IRUSR | stat.S_IWUSR)
    except (OSError, AttributeError):
        # chmod may fail on Windows or non-Unix systems
        pass


def list_tenants() -> List[Tenant]:
    with _LOCK:
        _load()
        return _TENANTS.copy()


def get_tenant(tenant_id: str) -> Optional[Tenant]:
    with _LOCK:
        _load()
        for t in _TENANTS:
            if t.id == tenant_id:
                return t
        return None


def create_tenant(
    name: str,
    plan: str = "basic",
    status: str = "active",
    contact: str = "",
) -> Tenant:
    with _LOCK:
        _load()
        tenant = Tenant(
            id=f"tenant-{uuid.uuid4().hex[:8]}",
            name=name,
            status=status,
            contact=contact,
            plan=plan,
            quota=_compute_quota(plan),
            usage=Usage(),
            billing=_compute_billing(plan),
        )
        _TENANTS.append(tenant)
        _save()
        return tenant


def update_tenant(tenant_id: str, **kwargs: Any) -> Optional[Tenant]:
    with _LOCK:
        _load()
        for t in _TENANTS:
            if t.id == tenant_id:
                if "name" in kwargs:
                    t.name = kwargs["name"]
                if "status" in kwargs:
                    t.status = kwargs["status"]
                if "contact" in kwargs:
                    t.contact = kwargs["contact"]
                if "plan" in kwargs and kwargs["plan"] != t.plan:
                    t.plan = kwargs["plan"]
                    t.quota = _compute_quota(t.plan)
                    t.billing = _compute_billing(t.plan)
                if "quota" in kwargs and isinstance(kwargs["quota"], dict):
                    for key, value in kwargs["quota"].items():
                        if hasattr(t.quota, key):
                            setattr(t.quota, key, value)
                if "usage" in kwargs and isinstance(kwargs["usage"], dict):
                    for key, value in kwargs["usage"].items():
                        if hasattr(t.usage, key):
                            setattr(t.usage, key, value)
                if "billing" in kwargs and isinstance(kwargs["billing"], dict):
                    for key, value in kwargs["billing"].items():
                        if hasattr(t.billing, key):
                            setattr(t.billing, key, value)
                _save()
                return t
        return None


def delete_tenant(tenant_id: str) -> bool:
    with _LOCK:
        _load()
        original = len(_TENANTS)
        _TENANTS[:] = [t for t in _TENANTS if t.id != tenant_id]
        if len(_TENANTS) != original:
            _save()
            return True
        return False
