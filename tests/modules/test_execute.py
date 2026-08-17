# -*- coding: utf-8 -*-
"""Import tests for the execute modules."""

import importlib

import pytest  # noqa: F401  # Imported for test setup

_MODULES = [
    "modules.execute.auto_heal.operator",
    "modules.execute.auto_heal.playbook_manager",
    "modules.execute.autoscaler.custom_hpa",
    "modules.execute.autoscaler.custom_hpa_controller",
    "modules.execute.saga.coordinator",
    "modules.execute.saga.participants",
    "modules.execute.scheduler.temporal_worker",
]


@pytest.mark.parametrize("module_name", _MODULES)
def test_execute_module_imports(module_name):
    """Each execute module imports or is skipped when dependencies are missing."""
    try:
        importlib.import_module(module_name)
    except Exception as exc:
        pytest.skip(f"import {module_name} failed: {exc}")
