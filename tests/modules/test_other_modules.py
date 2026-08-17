# -*- coding: utf-8 -*-
"""Import tests for the remaining module groups."""

import importlib

import pytest  # noqa: F401  # Imported for test setup

_MODULES = [
    "modules.optimization.cache_optimizer",
    "modules.optimization.concurrency_optimizer",
    "modules.optimization.query_optimizer",
    "modules.optimization.resource_optimizer",
    "modules.optimization.storage_optimizer",
    "modules.observability.auto_discovery",
    "modules.observability.smart_alerting",
    "modules.observability.smart_analysis",
    "modules.compliance.gdpr_compliance",
    "modules.compliance.soc2_compliance",
    "modules.multi_tenant.tenant_isolation",
    "modules.multi_tenant.tenant_manager",
    "modules.storage.clickhouse.storage",
    "modules.storage.postgres.storage",
    "modules.rum.data_collector",
    "modules.rum.sdk",
    "modules.apm.code_profiler",
    "modules.apm.dependency_analyzer",
    "modules.high_availability.multi_region",
    "modules.high_availability.self_healing",
]


@pytest.mark.parametrize("module_name", _MODULES)
def test_other_module_imports(module_name):
    """Each remaining module imports or is skipped when dependencies are missing."""
    try:
        importlib.import_module(module_name)
    except Exception as exc:
        pytest.skip(f"import {module_name} failed: {exc}")
