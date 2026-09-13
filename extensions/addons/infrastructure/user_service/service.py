# -*- coding: utf-8 -*-
"""Thin wrapper around PolicyEngine for the User governance addon."""

from __future__ import annotations

from typing import Any, Callable, Dict, List

from extensions.addons.engines.doc_policy_engine import PolicyEngine
from extensions.addons.engines.service_contract import BasePolicyService

BASE_METHODS: List[str] = [
    "get_state",
    "backup_state",
    "restore_state",
    "get_stats",
    "list_methods",
]

OPERATIONS: List[str] = [
    "user_lookup",
]


class UserService(BasePolicyService):
    """Service wrapper delegating user operations to PolicyEngine."""

    ENGINE = PolicyEngine
    OPERATIONS = OPERATIONS
    OP_MAP: Dict[str, Callable[[PolicyEngine, Dict[str, Any]], Any]] = {
        "user_lookup": lambda engine, params: engine.user_lookup(params.get("user_id", "")),
    }


Service = UserService
