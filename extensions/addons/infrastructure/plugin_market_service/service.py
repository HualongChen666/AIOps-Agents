# -*- coding: utf-8 -*-
"""Thin wrapper around PolicyEngine for the Plugin Market governance addon."""

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
    "plugin_index",
    "implement_plugin_search",
    "design_market_architecture",
]


class PluginMarketService(BasePolicyService):
    """Service wrapper delegating plugin market operations to PolicyEngine."""

    ENGINE = PolicyEngine
    OPERATIONS = OPERATIONS
    OP_MAP: Dict[str, Callable[[PolicyEngine, Dict[str, Any]], Any]] = {
        "plugin_index": lambda engine, params: engine.plugin_index(),
        "implement_plugin_search": lambda engine, params: engine.plugin_index(),
        "design_market_architecture": lambda engine, params: engine.plugin_index(),
    }


Service = PluginMarketService
