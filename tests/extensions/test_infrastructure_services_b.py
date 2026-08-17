# -*- coding: utf-8 -*-
"""Happy-path tests for infrastructure addon services (batch B)."""

import subprocess

import pytest  # noqa: F401  # Imported for test setup

from extensions.addons.infrastructure.fastapi_security_service.service import (
    Service as FastapiSecurityService,
)
from extensions.addons.infrastructure.kubernetes_orchestration_service.service import (
    Service as KubernetesOrchestrationService,
)
from extensions.addons.infrastructure.open_source_license_service.service import (
    Service as OpenSourceLicenseService,
)
from extensions.addons.infrastructure.performance_monitoring_service.service import (
    Service as PerformanceMonitoringService,
)
from extensions.addons.infrastructure.pgbackrest_backup_service.service import (
    Service as PgbackrestBackupService,
)
from extensions.addons.infrastructure.plugin_market_service.service import (
    Service as PluginMarketService,
)
from extensions.addons.infrastructure.plugin_system_service.service import (
    Service as PluginSystemService,
)
from extensions.addons.infrastructure.postgresql_shard_service.service import (
    Service as PostgresqlShardService,
)
from extensions.addons.infrastructure.qdrant_shard_service.service import (
    Service as QdrantShardService,
)
from extensions.addons.infrastructure.redis_shard_service.service import (
    Service as RedisShardService,
)
from extensions.addons.infrastructure.service_mesh_service.service import (
    Service as ServiceMeshService,
)
from extensions.addons.infrastructure.terraform_iac_service.service import (
    Service as TerraformIacService,
)
from extensions.addons.infrastructure.user_service.service import Service as UserService
from extensions.addons.infrastructure.vector_retrieval_service.service import (
    Service as VectorRetrievalService,
)
from extensions.addons.infrastructure.velero_backup_service.service import (
    Service as VeleroBackupService,
)


@pytest.fixture(autouse=True)
def _no_real_external_calls(monkeypatch):
    """Block real subprocess/network calls even if dry_run were disabled."""
    monkeypatch.setenv("INFRA_EXECUTE_ENABLED", "false")
    fake_result = type(  # noqa: F841  # Variable for test verification
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


def _assert_policy_result(result, operation):
    assert isinstance(result, dict)
    assert result.get("success") is True
    assert result.get("operation") == operation
    assert result.get("dry_run") is True
    assert "result" in result


def test_fastapi_security_service_execute_operation():
    service = FastapiSecurityService(dry_run=True)
    result = service.execute_operation("oauth2_password_auth", {})  # noqa: F841  # Variable for test verification
    _assert_service_result(result, "oauth2_password_auth")
    assert "flow" in result["result"]


def test_kubernetes_orchestration_service_execute_operation():
    service = KubernetesOrchestrationService(dry_run=True)
    result = service.execute_operation("design_k8s_cluster_architecture", {})  # noqa: F841  # Variable for test verification
    _assert_service_result(result, "design_k8s_cluster_architecture")
    assert result["result"].get("dry_run") is True


def test_open_source_license_service_execute_operation():
    service = OpenSourceLicenseService(dry_run=True)
    result = service.execute_operation("select_osi_license", {"license": "MIT"})  # noqa: F841  # Variable for test verification
    _assert_service_result(result, "select_osi_license")
    assert result["result"].get("osi_approved") is True


def test_performance_monitoring_service_execute_operation():
    service = PerformanceMonitoringService(cache={})
    result = service.execute_operation(  # noqa: F841  # Variable for test verification
        "collect_performance_metrics",
        {"target": "http://prometheus:9090", "metric": "up"},
    )
    _assert_service_result(result, "collect_performance_metrics")
    assert "data" in result["result"]


def test_pgbackrest_backup_service_execute_operation():
    service = PgbackrestBackupService(dry_run=True)
    result = service.execute_operation("postgresql_full_backup", {})  # noqa: F841  # Variable for test verification
    _assert_service_result(result, "postgresql_full_backup")
    assert "pgbackrest" in result["result"].get("command", "")


def test_plugin_market_service_execute_operation():
    service = PluginMarketService(dry_run=True)
    result = service.execute_operation("plugin_index", {})  # noqa: F841  # Variable for test verification
    _assert_policy_result(result, "plugin_index")
    assert isinstance(result["result"], list)


def test_plugin_system_service_execute_operation():
    service = PluginSystemService(dry_run=True)
    result = service.execute_operation("plugin_load", {"plugin_id": "example"})  # noqa: F841  # Variable for test verification
    _assert_policy_result(result, "plugin_load")
    assert result["result"].get("plugin_id") == "example"


def test_postgresql_shard_service_execute_operation():
    service = PostgresqlShardService(dry_run=True)
    result = service.execute_operation("get_stats", {})  # noqa: F841  # Variable for test verification
    _assert_thin_result(result)
    assert "db_size" in result


def test_qdrant_shard_service_execute_operation():
    service = QdrantShardService(dry_run=True)
    result = service.execute_operation("get_stats", {})  # noqa: F841  # Variable for test verification
    _assert_thin_result(result)
    assert "vector_count" in result


def test_redis_shard_service_execute_operation():
    service = RedisShardService(dry_run=True)
    result = service.execute_operation("get_stats", {})  # noqa: F841  # Variable for test verification
    _assert_thin_result(result)
    assert "cache_hits" in result


def test_service_mesh_service_execute_operation():
    service = ServiceMeshService(dry_run=True)
    result = service.execute_operation("evaluate_service_mesh", {})  # noqa: F841  # Variable for test verification
    _assert_service_result(result, "evaluate_service_mesh")
    assert "istioctl" in result["result"].get("command", "")


def test_terraform_iac_service_execute_operation():
    service = TerraformIacService(dry_run=True)
    result = service.execute_operation("write_terraform_configs", {})  # noqa: F841  # Variable for test verification
    _assert_service_result(result, "write_terraform_configs")
    assert "terraform" in result["result"].get("command", "")


def test_user_service_execute_operation():
    service = UserService(dry_run=True)
    result = service.execute_operation("user_lookup", {"user_id": "user-1"})  # noqa: F841  # Variable for test verification
    _assert_policy_result(result, "user_lookup")
    assert result["result"].get("found") is True


def test_vector_retrieval_service_execute_operation():
    service = VectorRetrievalService(dry_run=True)
    result = service.execute_operation("get_stats", {})  # noqa: F841  # Variable for test verification
    _assert_thin_result(result)
    assert "vector_count" in result


def test_velero_backup_service_execute_operation():
    service = VeleroBackupService(dry_run=True)
    result = service.execute_operation("k8s_resource_backup", {})  # noqa: F841  # Variable for test verification
    _assert_service_result(result, "k8s_resource_backup")
    assert "velero" in result["result"].get("command", "")
