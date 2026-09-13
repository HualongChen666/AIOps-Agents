# -*- coding: utf-8 -*-
"""Thin wrapper around PolicyEngine for the Config governance addon."""

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
    "load_config",
]


class ConfigService(BasePolicyService):
    """Service wrapper delegating config operations to PolicyEngine."""

    ENGINE = PolicyEngine
    OPERATIONS = OPERATIONS
    OP_MAP: Dict[str, Callable[[PolicyEngine, Dict[str, Any]], Any]] = {
        "load_config": lambda engine, params: engine.load_config(params.get("key", "")),
    }


Service = ConfigService
