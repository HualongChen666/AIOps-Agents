# -*- coding: utf-8 -*-
"""Thin wrapper around PolicyEngine for the Plugin System governance addon."""

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
    "plugin_load",
    "plugin_unload",
    "implement_plugin_loader",
    "implement_plugin_lifecycle",
]


class PluginSystemService(BasePolicyService):
    """Service wrapper delegating plugin system operations to PolicyEngine."""

    ENGINE = PolicyEngine
    OPERATIONS = OPERATIONS
    OP_MAP: Dict[str, Callable[[PolicyEngine, Dict[str, Any]], Any]] = {
        "plugin_load": lambda engine, params: engine.plugin_load(params.get("plugin_id", "")),
        "plugin_unload": lambda engine, params: engine.plugin_unload(params.get("plugin_id", "")),
        "implement_plugin_loader": lambda engine, params: engine.plugin_load(
            params.get("plugin_id", "")
        ),
        "implement_plugin_lifecycle": lambda engine, params: engine.plugin_unload(
            params.get("plugin_id", "")
        ),
    }


Service = PluginSystemService
