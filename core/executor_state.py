# -*- coding: utf-8 -*-
"""Executor pause/resume state.

The ``executor`` page can *pause* the workflow execution queue: while paused,
new executions are created in a ``pending`` (queued) state rather than being
launched, and *resume* drains the queue.  This tiny module owns that durable
flag so both the executor page and the workflow-execution page agree on it.
"""

from __future__ import annotations

from core.persistent_store import PersistentStore
from core.workflow_page_support import STORE_DOMAIN

_KIND = "executor_state"
_RECORD = "state"


def _store(tenant_id: str) -> PersistentStore:
    return PersistentStore(STORE_DOMAIN, _KIND, tenant_id=tenant_id)


def is_paused(tenant_id: str = "default") -> bool:
    """Return whether the execution queue is currently paused for *tenant_id*."""
    state = _store(tenant_id).get(_RECORD) or {}
    return bool(state.get("paused", False))


def set_paused(tenant_id: str, paused: bool) -> bool:
    """Persist the paused flag; returns the new value."""
    store = _store(tenant_id)
    store[_RECORD] = {"paused": bool(paused)}
    return bool(paused)
