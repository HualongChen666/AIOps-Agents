# -*- coding: utf-8 -*-
"""Targeted coverage tests for core.fine_rbac, core.gitops_manager, core.graphql_engine, core.grpc_service_manager."""

import asyncio
import os
import subprocess
import sys
import types
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

import core

# Make graphql_engine importable: upstream modules are missing the names it imports.
import core.db_engine as _db_engine_mod
import core.fine_rbac as fine_rbac
import core.rbac

if not hasattr(_db_engine_mod, "get_incident_history"):
    _db_engine_mod.get_incident_history = lambda **kwargs: []
import core.metrics_history as _metrics_history_mod

if not hasattr(_metrics_history_mod, "get_metrics_history"):
    _metrics_history_mod.get_metrics_history = lambda limit: []
import core.gitops_manager as gitops
import core.graphql_engine as ge
import core.grpc_service_manager as grpc

pytestmark = [pytest.mark.core]


@pytest.fixture(autouse=True)
def _clean_policy_store():
    """Reset the in-memory policy store around every fine_rbac test."""
    fine_rbac._POLICY_STORE.clear()
    fine_rbac._load_demo_policies()
    yield
    fine_rbac._POLICY_STORE.clear()
    fine_rbac._load_demo_policies()


@pytest.fixture
def rbac_auth(monkeypatch):
    """Inject a fake core.auth module so require_permission can be unit tested."""
    auth_mod = types.ModuleType("core.auth")
    auth_mod.get_current_user = lambda: None
    monkeypatch.setattr(core, "auth", auth_mod, raising=False)
    monkeypatch.setitem(sys.modules, "core.auth", auth_mod)
    return auth_mod


# ---------------------------------------------------------------------------
# core.fine_rbac
# ---------------------------------------------------------------------------
def test_grant_and_check_permission():
    fine_rbac.grant_permission("tenant-a", "resource", "read", "eng")
    assert fine_rbac.check_permission("tenant-a", "resource", "read", "eng") is True
    assert fine_rbac.check_permission("tenant-a", "resource", "read", "ops") is False
    assert fine_rbac.check_permission("missing-tenant", "resource", "read", "eng") is False


def test_revoke_permission():
    fine_rbac.grant_permission("tenant-b", "svc", "write", "eng")
    fine_rbac.grant_permission("tenant-b", "svc", "write", "ops")
    fine_rbac.revoke_permission("tenant-b", "svc", "write", "eng")
    assert fine_rbac.check_permission("tenant-b", "svc", "write", "eng") is False
    assert fine_rbac.check_permission("tenant-b", "svc", "write", "ops") is True
    # key is removed when the last role is revoked
    fine_rbac.revoke_permission("tenant-b", "svc", "write", "ops")
    assert ("tenant-b", "svc", "write") not in fine_rbac._POLICY_STORE
    # revoking a non-existent grant is safe
    fine_rbac.revoke_permission("tenant-b", "svc", "write", "eng")


def test_require_permission_allowed(rbac_auth, monkeypatch):
    monkeypatch.setattr(core.rbac, "get_user_tenant", lambda username: "default")
    user = types.SimpleNamespace(username="admin", role="admin")
    dep = fine_rbac.require_permission("*", "*")
    result = asyncio.run(dep(current_user=user))
    assert result is None


def test_require_permission_denied(rbac_auth, monkeypatch):
    monkeypatch.setattr(core.rbac, "get_user_tenant", lambda username: "default")
    user = types.SimpleNamespace(username="bob", role="user")
    dep = fine_rbac.require_permission("secrets", "write")
    with pytest.raises(fine_rbac.HTTPException) as exc:
        asyncio.run(dep(current_user=user))
    assert exc.value.status_code == 403
    assert "user" in exc.value.detail


def test_require_permission_default_tenant_fallback(rbac_auth, monkeypatch):
    monkeypatch.setattr(core.rbac, "get_user_tenant", lambda username: None)
    user = types.SimpleNamespace(username="user", role="user")
    dep = fine_rbac.require_permission("metrics", "read")
    assert asyncio.run(dep(current_user=user)) is None


def test_require_permission_role_fallback(rbac_auth, monkeypatch):
    monkeypatch.setattr(core.rbac, "get_user_tenant", lambda username: "default")
    user = types.SimpleNamespace(username="user")  # no role attribute
    dep = fine_rbac.require_permission("logs", "read")
    assert asyncio.run(dep(current_user=user)) is None


# ---------------------------------------------------------------------------
# core.gitops_manager
# ---------------------------------------------------------------------------
@pytest.fixture
def gitops_run(monkeypatch):
    """Replace subprocess calls so GitOps operations stay deterministic."""
    run_mock = MagicMock(
        return_value=subprocess.CompletedProcess(args=[], returncode=0, stdout="ok", stderr="")
    )
    monkeypatch.setattr("core.gitops_manager.subprocess_runner.run", run_mock)
    monkeypatch.setattr("core.gitops_manager.shutil.which", lambda name: "/fake/" + name)
    return run_mock


def test_ensure_kubeconfig_env(tmp_path, monkeypatch):
    kc = tmp_path / "kubeconfig"
    kc.write_text("x")
    monkeypatch.setenv("KUBECONFIG", str(kc))
    assert gitops._ensure_kubeconfig() == str(kc)


def test_ensure_kubeconfig_default(tmp_path, monkeypatch):
    monkeypatch.delenv("KUBECONFIG", raising=False)
    kc = tmp_path / "config"
    kc.write_text("x")
    monkeypatch.setattr("os.path.expanduser", lambda p: str(kc))
    assert gitops._ensure_kubeconfig() == str(kc)


def test_ensure_kubeconfig_missing(monkeypatch):
    monkeypatch.delenv("KUBECONFIG", raising=False)
    monkeypatch.setattr("core.gitops_manager.os.path.isfile", lambda p: False)
    assert gitops._ensure_kubeconfig() == ""


def test_gitops_manager_init(gitops_run, monkeypatch, tmp_path):
    kc = tmp_path / "kubeconfig"
    kc.write_text("x")
    monkeypatch.setenv("KUBECONFIG", str(kc))
    mgr = gitops.GitOpsManager()
    assert mgr._kubectl == "/fake/kubectl"
    assert mgr._argo == "/fake/argo"
    assert mgr.kubeconfig == str(kc)


def test_apply_manifest_file_not_found(gitops_run):
    mgr = gitops.GitOpsManager()
    assert mgr.apply_manifest("/nonexistent/manifest.yaml") is False


def test_apply_manifest_success(gitops_run, tmp_path):
    manifest = tmp_path / "manifest.yaml"
    manifest.write_text("apiVersion: v1")
    mgr = gitops.GitOpsManager()
    assert mgr.apply_manifest(str(manifest)) is True
    args = gitops_run.call_args[0][0]
    assert "apply" in args and "-f" in args and str(manifest) in args


def test_apply_manifest_failure(gitops_run, tmp_path):
    manifest = tmp_path / "manifest.yaml"
    manifest.write_text("x")
    gitops_run.return_value = subprocess.CompletedProcess(
        args=[], returncode=1, stdout="", stderr="fail"
    )
    mgr = gitops.GitOpsManager()
    assert mgr.apply_manifest(str(manifest)) is False


def test_apply_manifest_no_kubectl(monkeypatch, tmp_path):
    manifest = tmp_path / "manifest.yaml"
    manifest.write_text("x")
    monkeypatch.setattr("core.gitops_manager.shutil.which", lambda name: None)
    mgr = gitops.GitOpsManager()
    assert mgr.apply_manifest(str(manifest)) is False


def test_get_rollout_status_success(gitops_run):
    gitops_run.return_value = subprocess.CompletedProcess(
        args=[], returncode=0, stdout="status: healthy\n" * 15, stderr=""
    )
    mgr = gitops.GitOpsManager()
    status = mgr.get_rollout_status("my-rollout", namespace="default")
    assert status is not None
    assert len(status.splitlines()) <= 20


def test_get_rollout_status_failure(gitops_run):
    gitops_run.return_value = subprocess.CompletedProcess(
        args=[], returncode=1, stdout="", stderr="fail"
    )
    mgr = gitops.GitOpsManager()
    assert mgr.get_rollout_status("my-rollout") is None


def test_get_rollout_status_no_argo(monkeypatch):
    monkeypatch.setattr(
        "core.gitops_manager.shutil.which", lambda name: None if name == "argo" else "/fake/" + name
    )
    mgr = gitops.GitOpsManager()
    assert mgr.get_rollout_status("my-rollout") is None


def test_rollback_without_revision(gitops_run):
    mgr = gitops.GitOpsManager()
    assert mgr.rollback("svc") is True
    args = gitops_run.call_args[0][0]
    assert "undo" in args and "svc" in args
    assert "--revision" not in args


def test_rollback_with_revision(gitops_run):
    mgr = gitops.GitOpsManager()
    assert mgr.rollback("svc", to_revision=3) is True
    args = gitops_run.call_args[0][0]
    assert "--revision" in args and "3" in args


def test_rollback_no_argo(monkeypatch):
    monkeypatch.setattr(
        "core.gitops_manager.shutil.which", lambda name: None if name == "argo" else "/fake/" + name
    )
    mgr = gitops.GitOpsManager()
    assert mgr.rollback("svc") is False


def test_get_resource_success(gitops_run):
    gitops_run.return_value = subprocess.CompletedProcess(
        args=[], returncode=0, stdout="yaml content", stderr=""
    )
    mgr = gitops.GitOpsManager()
    assert mgr.get_resource("pods", "web", namespace="prod") == "yaml content"
    args = gitops_run.call_args[0][0]
    assert "get" in args and "pods" in args and "web" in args and "-n" in args and "prod" in args


def test_get_resource_failure(gitops_run):
    gitops_run.return_value = subprocess.CompletedProcess(
        args=[], returncode=1, stdout="", stderr="fail"
    )
    mgr = gitops.GitOpsManager()
    assert mgr.get_resource("pods", "web") is None


def test_get_resource_no_kubectl(monkeypatch):
    monkeypatch.setattr(
        "core.gitops_manager.shutil.which",
        lambda name: None if name == "kubectl" else "/fake/" + name,
    )
    mgr = gitops.GitOpsManager()
    assert mgr.get_resource("pods", "web") is None


def test_run_cmd_command_not_found(gitops_run):
    gitops_run.side_effect = FileNotFoundError("not found")
    result = gitops._run_cmd(["/fake/kubectl", "get", "pods"])
    assert result.returncode == 127
    assert "not found" in result.stderr


def test_disaster_recover_status_none(gitops_run):
    gitops_run.return_value = subprocess.CompletedProcess(
        args=[], returncode=1, stdout="", stderr="fail"
    )
    mgr = gitops.GitOpsManager()
    assert mgr.disaster_recover("svc") is False


def test_disaster_recover_healthy(gitops_run):
    gitops_run.return_value = subprocess.CompletedProcess(
        args=[], returncode=0, stdout="status: healthy", stderr=""
    )
    mgr = gitops.GitOpsManager()
    assert mgr.disaster_recover("svc") is True


def test_disaster_recover_paused_rollback_success(gitops_run):
    gitops_run.side_effect = [
        subprocess.CompletedProcess(args=[], returncode=0, stdout="status: Paused", stderr=""),
        subprocess.CompletedProcess(args=[], returncode=0, stdout="undo ok", stderr=""),
        subprocess.CompletedProcess(args=[], returncode=0, stdout="status: healthy", stderr=""),
    ]
    mgr = gitops.GitOpsManager()
    assert mgr.disaster_recover("svc") is True
    assert gitops_run.call_count == 3


def test_disaster_recover_paused_rollback_failure(gitops_run):
    gitops_run.side_effect = [
        subprocess.CompletedProcess(args=[], returncode=0, stdout="status: progressing", stderr=""),
        subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="undo failed"),
    ]
    mgr = gitops.GitOpsManager()
    assert mgr.disaster_recover("svc") is False


def test_get_manager():
    assert gitops.get_manager() is gitops._gitops_manager


# ---------------------------------------------------------------------------
# core.graphql_engine
# ---------------------------------------------------------------------------
def test_graphql_host_health_success(monkeypatch):
    async def _mock(host_id):
        return {"status": "healthy", "timestamp": datetime.now(timezone.utc), "details": "all good"}

    monkeypatch.setattr(ge, "get_host_health", _mock)
    r = asyncio.run(
        ge.schema.execute('{ hostHealth(hostId: "h1") { hostId status lastChecked details } }')
    )
    assert r.errors is None
    assert r.data["hostHealth"]["hostId"] == "h1"
    assert r.data["hostHealth"]["status"] == "healthy"
    assert r.data["hostHealth"]["details"] == "all good"


def test_graphql_host_health_error(monkeypatch):
    async def _mock(host_id):
        raise RuntimeError("host down")

    monkeypatch.setattr(ge, "get_host_health", _mock)
    r = asyncio.run(ge.schema.execute('{ hostHealth(hostId: "h1") { hostId } }'))
    assert r.errors
    assert "host down" in str(r.errors[0])


def test_graphql_metrics_success(monkeypatch):
    now = datetime.now(timezone.utc)

    def _mock(limit=20):
        return [{"timestamp": now, "name": "cpu", "value": 12.5, "host_id": "h1"}]

    monkeypatch.setattr(ge, "get_metrics_history", _mock)
    r = asyncio.run(ge.schema.execute("{ metrics(limit: 5) { timestamp name value hostId } }"))
    assert r.errors is None
    assert r.data["metrics"][0]["name"] == "cpu"


def test_graphql_metrics_error(monkeypatch):
    def _mock(limit=20):
        raise RuntimeError("metrics boom")

    monkeypatch.setattr(ge, "get_metrics_history", _mock)
    r = asyncio.run(ge.schema.execute("{ metrics { name } }"))
    assert r.errors
    assert "metrics boom" in str(r.errors[0])


def test_graphql_incidents_success(monkeypatch):
    now = datetime.now(timezone.utc)

    def _mock(host_id=None, limit=20):
        return [
            {
                "id": "i1",
                "host_id": "h1",
                "alert_id": "a1",
                "script_key": "s1",
                "created_at": now,
                "status": "open",
                "severity": "critical",
            }
        ]

    monkeypatch.setattr(ge, "get_incident_history", _mock)
    r = asyncio.run(
        ge.schema.execute(
            '{ incidents(hostId: "h1", limit: 10) { incidentId hostId alertId scriptKey status severity } }'
        )
    )
    assert r.errors is None
    assert r.data["incidents"][0]["incidentId"] == "i1"


def test_graphql_incidents_error(monkeypatch):
    def _mock(host_id=None, limit=20):
        raise RuntimeError("incidents boom")

    monkeypatch.setattr(ge, "get_incident_history", _mock)
    r = asyncio.run(ge.schema.execute("{ incidents { incidentId } }"))
    assert r.errors
    assert "incidents boom" in str(r.errors[0])


# ---------------------------------------------------------------------------
# core.grpc_service_manager
# ---------------------------------------------------------------------------
def test_grpc_service_manager_init_config():
    mgr = grpc.GRPCServiceManager()
    assert mgr.config == {}
    mgr2 = grpc.GRPCServiceManager({"debug": True})
    assert mgr2.config == {"debug": True}


def test_grpc_proto_templates():
    mgr = grpc.GRPCServiceManager()
    assert "service_header" in mgr.proto_templates
    assert "method_unary" in mgr.proto_templates


def test_grpc_create_service_with_streaming_and_messages():
    mgr = grpc.GRPCServiceManager()
    methods = [
        grpc.GRPCMethod("Get", "Req", "Resp", "unary", "get data"),
        grpc.GRPCMethod("Stream", "Req", "Resp", "server_streaming", "stream data"),
        grpc.GRPCMethod("Upload", "Req", "Resp", "client_streaming", "upload data"),
        grpc.GRPCMethod("Bidi", "Req", "Resp", "bidi_streaming", "bidi data"),
        grpc.GRPCMethod("Unknown", "Req", "Resp", "unknown", "fallback to unary"),
    ]
    messages = {"Req": {"field1": "string", "field2": "int32"}}
    service = mgr.create_service("TestSvc", "testpkg", methods, messages)
    assert service.service_name == "TestSvc"
    assert "rpc Get(Req) returns (Resp);" in service.proto_content
    assert "stream Resp" in service.proto_content
    assert "stream Req" in service.proto_content
    assert "message Req" in service.proto_content
    assert "TestSvcServicer" in service.python_content
    assert mgr.total_services_defined == 1
    assert mgr.total_methods_defined == len(methods)


def test_grpc_create_monitoring_alert_repair_services():
    mgr = grpc.GRPCServiceManager()
    m = mgr.create_monitoring_service()
    a = mgr.create_alert_service()
    r = mgr.create_repair_service()
    for svc in [m, a, r]:
        assert svc.status == grpc.ServiceStatus.DEFINED
    summary = mgr.get_service_summary()
    assert summary["total_services"] == 3
    assert summary["total_methods"] == 7
    assert any(s["name"] == "MonitoringService" for s in summary["services"])


def test_grpc_export_proto_and_python_files(tmp_path):
    mgr = grpc.GRPCServiceManager()
    mgr.create_monitoring_service()
    proto_file = tmp_path / "m.proto"
    mgr.export_proto_file("MonitoringService", str(proto_file))
    assert proto_file.read_text().startswith('syntax = "proto3"')
    py_file = tmp_path / "m.py"
    mgr.export_python_file("MonitoringService", str(py_file))
    assert "MonitoringServiceServicer" in py_file.read_text()


def test_grpc_export_proto_python_missing_service():
    mgr = grpc.GRPCServiceManager()
    with pytest.raises(ValueError):
        mgr.export_proto_file("Missing", "x.proto")
    with pytest.raises(ValueError):
        mgr.export_python_file("Missing", "x.py")


def test_grpc_export_proto_file_write_error(tmp_path):
    mgr = grpc.GRPCServiceManager()
    mgr.create_monitoring_service()
    bad_path = tmp_path / "missing_dir" / "m.proto"
    with pytest.raises(OSError):
        mgr.export_proto_file("MonitoringService", str(bad_path))


def test_grpc_get_manager_singleton():
    m1 = grpc.get_grpc_service_manager()
    m2 = grpc.get_grpc_service_manager()
    assert m1 is m2
