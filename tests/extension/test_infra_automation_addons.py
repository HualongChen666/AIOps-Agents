# -*- coding: utf-8 -*-
"""Tests for Group 3 infrastructure-automation addon services."""

import subprocess

import pytest

from extensions.addons.infrastructure.ansible_automation_service.service import (
    Service as AnsibleService,
)
from extensions.addons.infrastructure.automated_deployment_service.service import (
    Service as DeploymentService,
)
from extensions.addons.infrastructure.automated_ops_service.service import Service as OpsService
from extensions.addons.infrastructure.backup_recovery_drill_service.service import (
    Service as DrillService,
)
from extensions.addons.infrastructure.chaos_mesh_service.service import Service as ChaosMeshService
from extensions.addons.infrastructure.kubernetes_orchestration_service.service import (
    Service as KubernetesService,
)
from extensions.addons.infrastructure.pgbackrest_backup_service.service import (
    Service as PgBackRestService,
)
from extensions.addons.infrastructure.service_mesh_service.service import (
    Service as ServiceMeshService,
)
from extensions.addons.infrastructure.terraform_iac_service.service import (
    Service as TerraformService,
)
from extensions.addons.infrastructure.velero_backup_service.service import Service as VeleroService


@pytest.fixture(autouse=True)
def enable_real_execution(monkeypatch):
    """Enable real subprocess calls so the monkeypatched run is exercised."""
    monkeypatch.setenv("INFRA_EXECUTE_ENABLED", "true")


@pytest.fixture(autouse=True)
def fake_subprocess_run(monkeypatch):
    """Return deterministic, realistic stdout for every command."""

    def _run(*args, **kwargs):
        cmd = args[0] if args else kwargs.get("args", [])
        operation = cmd[-1] if isinstance(cmd, list) and cmd else "unknown"
        stdout = f'{{"status": "ok", "operation": "{operation}"}}'
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout=stdout, stderr="")

    monkeypatch.setattr(subprocess, "run", _run)


ADDON_CASES = [
    ("ansible", AnsibleService, "design_ansible_architecture"),
    ("terraform", TerraformService, "design_terraform_modules"),
    ("kubernetes", KubernetesService, "design_k8s_cluster_architecture"),
    ("deployment", DeploymentService, "implement_cicd_pipeline"),
    ("ops", OpsService, "implement_automated_inspection"),
    ("velero", VeleroService, "k8s_resource_backup"),
    ("pgbackrest", PgBackRestService, "postgresql_full_backup"),
    ("drill", DrillService, "design_drill_plan"),
    ("chaos_mesh", ChaosMeshService, "pod_fault_injection"),
    ("service_mesh", ServiceMeshService, "evaluate_service_mesh"),
]


@pytest.mark.parametrize("name, service_cls, operation", ADDON_CASES)
def test_addon_execute_operation(name, service_cls, operation):
    """Each addon Service.execute_operation should run its mapped command."""
    service = service_cls()
    result = service.execute_operation(operation, {})

    assert result["success"] is True
    assert result["status"] == "ok"
    assert result["feature"] == operation
    assert "command" in result["result"]
    assert result["result"]["returncode"] == 0
    assert operation in result["result"]["stdout"] or '"status": "ok"' in result["result"]["stdout"]


@pytest.mark.parametrize("name, service_cls, operation", ADDON_CASES)
def test_addon_dry_run_default(name, service_cls, operation, monkeypatch):
    """Without INFRA_EXECUTE_ENABLED the command is built but not executed."""
    monkeypatch.delenv("INFRA_EXECUTE_ENABLED", raising=False)
    service = service_cls()
    result = service.execute_operation(operation, {})

    assert result["success"] is True
    assert result["result"].get("dry_run") is True
    assert "command" in result["result"]
