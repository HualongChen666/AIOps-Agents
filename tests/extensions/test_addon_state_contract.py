# -*- coding: utf-8 -*-
"""State-contract regression tests for the governance addon service wrappers.

Every wrapper declares ``BASE_METHODS`` (get_state / backup_state /
restore_state / get_stats / list_methods). These must delegate to the real
engine state layer — they previously returned ``{"message": "not implemented"}``.
"""

from __future__ import annotations

import importlib

import pytest

# (module, class, is_instance_wrapper)
WRAPPERS = [
    ("extensions.addons.infrastructure.config_service.service", "ConfigService", False),
    ("extensions.addons.infrastructure.user_service.service", "UserService", False),
    (
        "extensions.addons.infrastructure.data_standards_service.service",
        "DataStandardsService",
        False,
    ),
    (
        "extensions.addons.infrastructure.plugin_system_service.service",
        "PluginSystemService",
        False,
    ),
    (
        "extensions.addons.infrastructure.api_standards_service.service",
        "APIStandardsService",
        False,
    ),
    (
        "extensions.addons.infrastructure.plugin_market_service.service",
        "PluginMarketService",
        False,
    ),
    (
        "extensions.addons.documentation.sphinx_documentation_service.service",
        "SphinxDocumentationService",
        True,
    ),
]

BASE_METHODS = ["get_state", "backup_state", "restore_state", "get_stats", "list_methods"]


def _load(mod_name: str, cls_name: str, is_instance: bool):
    module = importlib.import_module(mod_name)
    cls = getattr(module, cls_name)
    return cls() if is_instance else cls


def _call(service, op: str, params=None):
    # classmethod wrappers expose execute_operation on the class; instance
    # wrappers on the instance. Both are callable the same way.
    return service.execute_operation(op, params or {})


@pytest.mark.parametrize("mod_name,cls_name,is_instance", WRAPPERS)
def test_all_base_methods_are_implemented(mod_name, cls_name, is_instance):
    obj = _load(mod_name, cls_name, is_instance)

    state = _call(obj, "get_state")
    assert state["success"] is True
    assert "state" in state["result"]

    backup = _call(obj, "backup_state", {"label": "t"})
    backup_id = backup["result"]["backup_id"]
    assert backup_id.startswith("backup-")

    restored = _call(obj, "restore_state", {"backup_id": backup_id})
    assert restored["result"]["restored"] is True

    stats = _call(obj, "get_stats")
    assert stats["result"]["total_operations"] >= 1

    methods = _call(obj, "list_methods")
    assert isinstance(methods["result"], list) and methods["result"]


@pytest.mark.parametrize("mod_name,cls_name,is_instance", WRAPPERS)
def test_no_operation_returns_not_implemented(mod_name, cls_name, is_instance):
    obj = _load(mod_name, cls_name, is_instance)
    _call(obj, "backup_state")  # so restore_state has something to restore
    for op in BASE_METHODS:
        result = _call(obj, op)
        assert result["success"] is True
        assert result["result"] != {"message": "not implemented"}
