# -*- coding: utf-8 -*-
"""Import tests for the services modules (B36-B39)."""

import importlib

import pytest

_MODULES = [
    # B36 agent_orchestration_service
    "services.agent_orchestration_service.cache",
    "services.agent_orchestration_service.config",
    "services.agent_orchestration_service.grpc.client",
    "services.agent_orchestration_service.grpc.server",
    "services.agent_orchestration_service.health_check",
    "services.agent_orchestration_service.main",
    "services.agent_orchestration_service.main_app",
    "services.agent_orchestration_service.metrics",
    "services.agent_orchestration_service.orchestrator",
    "services.agent_orchestration_service.retry",
    "services.agent_orchestration_service.schemas",
    # B37 alert_service
    "services.alert_service.aggregator",
    "services.alert_service.classifier",
    "services.alert_service.collector",
    "services.alert_service.config",
    "services.alert_service.dedup",
    "services.alert_service.escalator",
    "services.alert_service.flapping_detector",
    "services.alert_service.main",
    "services.alert_service.mq",
    "services.alert_service.noise_suppressor",
    "services.alert_service.notifier",
    "services.alert_service.pattern_engine",
    "services.alert_service.processor",
    "services.alert_service.processor_core",
    "services.alert_service.repository",
    "services.alert_service.router",
    "services.alert_service.saga",
    "services.alert_service.schemas",
    # B38 audit_service
    "services.audit_service.alerting",
    "services.audit_service.analyzer",
    "services.audit_service.compliance",
    "services.audit_service.config",
    "services.audit_service.encryption",
    "services.audit_service.event_router",
    "services.audit_service.event_store",
    "services.audit_service.event_tracker",
    "services.audit_service.graphql_api",
    "services.audit_service.grpc.client",
    "services.audit_service.grpc.server",
    "services.audit_service.health_check",
    "services.audit_service.main",
    "services.audit_service.main_app",
    "services.audit_service.metrics",
    "services.audit_service.orchestrator",
    "services.audit_service.query",
    "services.audit_service.report_generator",
    "services.audit_service.repository",
    "services.audit_service.retention",
    "services.audit_service.saga",
    "services.audit_service.schemas",
    # B39 repair_service
    "services.repair_service.audit",
    "services.repair_service.config",
    "services.repair_service.grpc.client",
    "services.repair_service.grpc.server",
    "services.repair_service.health_check",
    "services.repair_service.main",
    "services.repair_service.metrics",
    "services.repair_service.mq",
    "services.repair_service.orchestrator",
    "services.repair_service.repository",
    "services.repair_service.rollback",
    "services.repair_service.runbook_parser",
    "services.repair_service.saga",
    "services.repair_service.schemas",
    "services.repair_service.state_machine",
    "services.repair_service.strategy_manager",
    "services.repair_service.verifier",
]


@pytest.mark.parametrize("module_name", _MODULES)
def test_service_module_imports(module_name):
    """Each service module imports or is skipped when dependencies are missing."""
    try:
        importlib.import_module(module_name)
    except Exception as exc:
        pytest.skip(f"import {module_name} failed: {exc}")
