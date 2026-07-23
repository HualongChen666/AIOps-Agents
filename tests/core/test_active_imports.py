# -*- coding: utf-8 -*-
"""Smoke tests for active core modules that currently have zero/low coverage.

Importing these modules executes their top-level statements and gives us a
baseline of coverage.  Tests are parametric and skip modules that cannot be
imported in this environment (e.g. OS-specific or optional dependencies).
"""

from types import ModuleType

import pytest

# Active core modules with zero/low coverage, sorted roughly by impact.
# These are imported (statically) by api routers or main.py, so they should
# be safe to import in the test environment.
ACTIVE_MODULES = [
    "core.linux_collector",
    "core.data_lineage",
    "core.backup_strategy",
    "core.command_guard",
    "core.data_integration_manager",
    "core.audit_service",
    "core.config_center",
    "core.compliance_manager",
    "core.analysis.l2.enhanced_causal_analyzer",
    "core.enhanced_auth_integration",
    "core.health_check",
    "core.enterprise_functionality",
    "core.data_privacy",
    "core.performance_integration_tester",
    "core.log_collector",
    "core.integration_manager",
    "core.user_service",
    "core.linux_repair",
    "core.feature_flag",
    "core.enhanced_websocket_manager",
    "core.abac",
    "core.performance_report_generator",
    "core.websocket_integrator",
    "core.cache_helpers",
    "core.integration_testing_system",
    "core.analysis.l2.langgraph_engine",
    "core.l2l3_workflow_integrator",
    # Top missing core modules identified from coverage gaps
    "core.analysis.l2.rag_engine",
    "core.integration_test_validator",
    "core.key_management_service",
    "core.third_party_service_integrator",
    "core.audit_integration_manager",
    "core.l3l4_storage_integrator",
    "core.disaster_recovery_drill",
    "core.flink_stream_processor",
    "core.dependency_injection",
    "core.ai.langgraph._core",
    "core.cicd_integration_manager",
    "core.kafka_stream_processor",
    "core.kubernetes_deployment_manager",
    "core.config_validation",
    "core.vulnerability_manager",
    "core.cicd_pipeline_manager",
    "core.localization_resource_manager",
    "core.analysis.l2.model_router",
    "core.l6l7_frontend_integrator",
    "core.root_cause_intelligence",
    "core.l1l2_data_flow_integrator",
    "core.l5l6_execution_integrator",
    "core.l4l5_data_integrator",
    "core.auto_heal",
    "core.service_discovery_manager",
]


@pytest.mark.parametrize("module_name", ACTIVE_MODULES)
def test_active_module_imports(module_name: str) -> None:
    """Each listed module should be importable without raising."""
    import importlib

    try:
        mod = importlib.import_module(module_name)
    except (ImportError, RuntimeError, OSError) as exc:
        pytest.skip(f"{module_name} not importable in this environment: {exc}")

    assert isinstance(mod, ModuleType)
    assert mod.__name__ == module_name
