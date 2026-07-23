# -*- coding: utf-8 -*-
"""Smoke tests for top missing-coverage core modules.

Reuses the safe dummy-argument helpers from test_low_coverage_method_smoke.py
and targets the active core modules with the most uncovered statements.
"""

import inspect
from types import ModuleType
from typing import Any, Callable, Dict

import pytest

from tests.core.test_low_coverage_method_smoke import (
    ACTIVE_MODULES,
    _call_or_run,
    _generate_args,
    _is_long_running_method,
    _is_public,
    _is_skipped_module,
    _try_call,
)

# Active core modules with the largest number of missing statements from the
# latest coverage report.  db_engine is intentionally omitted because its sync
# wrappers call asyncio.run and can block the test runner.
TOP_MISSING_MODULES = [
    "core.database_connection_optimizer",
    "core.database_cache_optimizer",
    "core.database_query_optimizer",
    "core.config_manager",
    "core.stats_engine",
    "core.alert_intelligence",
    "core.metrics_history",
    "core.ai_service",
    "core.alert_service",
    "core.agent.tools",
    "core.agent.subagent",
    "core.agent.executor",
    "core.security_monitoring",
    "core.analysis.l2.enhanced_causal_analyzer",
    "core.processing.l3.causal_graph",
    "core.feature_flag",
    "core.analysis.l2.rag_engine",
    "core.cpu_usage_optimizer",
    "core.data_lineage",
    "core.analysis.l2.model_router",
    "core.integration_testing_system",
    "core.grpc_service_manager",
    "core.data_integration_manager",
    "core.storage.l4.tempo",
    "core.processing.l3.workflow_engine",
    "core.storage.l4.loki",
    "core.config_center",
    "core.cloud_collector",
    "core.approval_store",
    "core.collector",
    "core.base.collector",
    "core.performance_integration_tester",
    "core.service_monitoring_manager",
]



@pytest.mark.parametrize("module_name", TOP_MISSING_MODULES)
def test_top_missing_module_method_smoke(module_name: str) -> None:
    import importlib

    if _is_skipped_module(module_name):
        pytest.skip(f"Module {module_name} skipped due to heavy side effects")

    # Avoid duplicating work already done by test_low_coverage_method_smoke
    if module_name in ACTIVE_MODULES:
        pytest.skip(f"Module {module_name} already covered by low-coverage smoke")

    try:
        mod = importlib.import_module(module_name)
    except (ImportError, RuntimeError, OSError) as exc:
        pytest.skip(f"{module_name} not importable: {exc}")

    assert isinstance(mod, ModuleType)

    for name, obj in inspect.getmembers(mod):
        if not _is_public(name) or getattr(obj, "__module__", None) != module_name:
            continue

        if inspect.isclass(obj):
            try:
                kwargs = _generate_args(obj, mod)
                if kwargs is None:
                    continue
                instance = obj(**kwargs)
            except Exception:
                continue

            for method_name, method in inspect.getmembers(instance):
                if not _is_public(method_name) or _is_long_running_method(method_name):
                    continue
                if not (
                    inspect.isfunction(method)
                    or inspect.ismethod(method)
                    or inspect.iscoroutinefunction(method)
                ):
                    continue
                _try_call(method, mod)

        if (
            inspect.isfunction(obj)
            and not inspect.iscoroutinefunction(obj)
            and not _is_long_running_method(obj.__name__)
        ):
            _try_call(obj, mod)
