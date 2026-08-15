# -*- coding: utf-8 -*-
"""Happy-path tests for infrastructure addon services (batch A)."""

import subprocess

import pytest

from extensions.addons.infrastructure.alert_rule_service.service import (
    Service as AlertRuleService,
)
from extensions.addons.infrastructure.ansible_automation_service.service import (
    Service as AnsibleAutomationService,
)
from extensions.addons.infrastructure.api_standards_service.service import (
    Service as ApiStandardsService,
)
from extensions.addons.infrastructure.automated_deployment_service.service import (
    Service as AutomatedDeploymentService,
)
from extensions.addons.infrastructure.automated_ops_service.service import (
    Service as AutomatedOpsService,
)
from extensions.addons.infrastructure.backup_recovery_drill_service.service import (
    Service as BackupRecoveryDrillService,
)
from extensions.addons.infrastructure.cache_optimization_service.service import (
    Service as CacheOptimizationService,
)
from extensions.addons.infrastructure.cache_service.service import Service as CacheService
from extensions.addons.infrastructure.chaos_mesh_service.service import (
    Service as ChaosMeshService,
)
from extensions.addons.infrastructure.cloud_monitoring_service.service import (
    Service as CloudMonitoringService,
)
from extensions.addons.infrastructure.config_service.service import Service as ConfigService
from extensions.addons.infrastructure.data_access_service.service import (
    Service as DataAccessService,
)
from extensions.addons.infrastructure.database_optimization_service.service import (
    Service as DatabaseOptimizationService,
)
from extensions.addons.infrastructure.datacenter_visualization_service.service import (
    Service as DatacenterVisualizationService,
)
from extensions.addons.infrastructure.data_standards_service.service import (
    Service as DataStandardsService,
)


@pytest.fixture(autouse=True)
def _no_real_external_calls(monkeypatch):
    """Block real subprocess/network calls even if dry_run were disabled."""
    monkeypatch.setenv("INFRA_EXECUTE_ENABLED", "false")
    fake_result = type(
        "_CompletedProcess",
        (),
        {"stdout": "", "stderr": "", "returncode": 0},
    )()
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: fake_result)


def _assert_service_result(result, feature):
    assert isinstance(result, dict)
    assert result.get("success") is True
    assert result.get("status") == "ok"
    assert result.get("feature") == feature
    assert "result" in result
    assert "message" in result


def _assert_thin_result(result):
    assert result is not None
    assert isinstance(result, (dict, list))


def test_alert_rule_service_execute_operation():
    service = AlertRuleService()
    result = service.execute_operation(
        "configure_prometheus_alert_rules",
        {"rule_name": "cpu_high", "expr": "cpu > 80"},
    )
    _assert_service_result(result, "configure_prometheus_alert_rules")
    assert "data" in result["result"]


def test_ansible_automation_service_execute_operation():
    service = AnsibleAutomationService(dry_run=True)
    result = service.execute_operation("design_ansible_architecture", {})
    _assert_service_result(result, "design_ansible_architecture")
    assert result["result"].get("dry_run") is True


def test_api_standards_service_execute_operation():
    service = ApiStandardsService()
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "paths": {"/health": {"get": {"summary": "health check"}}},
    }
    result = service.execute_operation("lint_openapi", {"spec": spec})
    assert isinstance(result, dict)
    assert result.get("success") is True
    assert result.get("operation") == "lint_openapi"
    assert "result" in result
    assert result["result"].get("valid") is True


def test_automated_deployment_service_execute_operation():
    service = AutomatedDeploymentService(dry_run=True)
    result = service.execute_operation("implement_cicd_pipeline", {})
    _assert_service_result(result, "implement_cicd_pipeline")
    assert "command" in result["result"]


def test_automated_ops_service_execute_operation():
    service = AutomatedOpsService(dry_run=True)
    result = service.execute_operation("implement_automated_inspection", {})
    _assert_service_result(result, "implement_automated_inspection")
    assert result["result"].get("status") == "ok"


def test_backup_recovery_drill_service_execute_operation():
    service = BackupRecoveryDrillService(dry_run=True)
    result = service.execute_operation("design_drill_plan", {})
    _assert_service_result(result, "design_drill_plan")
    assert result["result"].get("dry_run") is True


def test_cache_optimization_service_execute_operation():
    service = CacheOptimizationService(dry_run=True)
    result = service.execute_operation("get_stats", {})
    _assert_thin_result(result)
    assert "cache_hits" in result


def test_cache_service_execute_operation():
    service = CacheService(dry_run=True)
    result = service.execute_operation("cache_set", {"key": "test", "value": "v"})
    _assert_thin_result(result)
    assert isinstance(result, dict)
    assert result.get("stored") is True


def test_chaos_mesh_service_execute_operation():
    service = ChaosMeshService(dry_run=True)
    result = service.execute_operation("pod_fault_injection", {})
    _assert_service_result(result, "pod_fault_injection")
    assert "chaosctl" in result["result"].get("command", "")


def test_cloud_monitoring_service_execute_operation():
    service = CloudMonitoringService()
    result = service.execute_operation(
        "integrate_aws_cloudwatch",
        {"target": "https://cloudwatch.amazonaws.com"},
    )
    _assert_service_result(result, "integrate_aws_cloudwatch")
    assert "data" in result["result"]


def test_config_service_execute_operation():
    service = ConfigService()
    result = service.execute_operation("load_config", {"key": "TEST_CONFIG_KEY"})
    assert isinstance(result, dict)
    assert result.get("success") is True
    assert result.get("operation") == "load_config"
    assert "result" in result
    assert result["result"].get("source") is None


def test_database_optimization_service_execute_operation():
    service = DatabaseOptimizationService(dry_run=True)
    result = service.execute_operation("get_stats", {})
    _assert_thin_result(result)
    assert "cache_hits" in result
    assert "db_size" in result


def test_datacenter_visualization_service_execute_operation():
    service = DatacenterVisualizationService()
    result = service.execute_operation("design_physical_model", {})
    _assert_service_result(result, "design_physical_model")
    assert "data" in result["result"]


def test_data_access_service_execute_operation():
    service = DataAccessService(dry_run=True)
    result = service.execute_operation("get_stats", {})
    _assert_thin_result(result)
    assert isinstance(result, dict)
    assert "cache_hits" in result


def test_data_standards_service_execute_operation():
    service = DataStandardsService()
    payload = {
        "obj": {"name": "example"},
        "schema": {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        },
    }
    result = service.execute_operation("validate_schema", payload)
    assert isinstance(result, dict)
    assert result.get("success") is True
    assert result.get("operation") == "validate_schema"
    assert "result" in result
    assert result["result"].get("valid") is True
