# -*- coding: utf-8 -*-
"""Unit tests for previously zero-coverage core modules."""

import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

import core.backup as backup_module
import core.backup_strategy as backup_strategy
import core.enterprise_features as enterprise_features
import core.task_scheduler as task_scheduler
import core.tracing_visualization as tracing_visualization
from core.backup import BackupManager, BackupType, create_backup_manager
from core.enterprise_features import ComplianceStandard, EnterpriseFeatures
from core.tracing_visualization import (
    TimeRange,
    TraceData,
    get_tracing_visualization_manager,
)

pytestmark = [pytest.mark.core]


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _patch_backup_strategy_subprocess(monkeypatch, stdout=b"dump", stderr=b""):
    """Mock asyncio.create_subprocess_exec for backup_strategy."""
    proc = AsyncMock()
    proc.returncode = 0
    proc.communicate = AsyncMock(return_value=(stdout, stderr))
    monkeypatch.setattr(
        backup_strategy.asyncio, "create_subprocess_exec", AsyncMock(return_value=proc)
    )


def _patch_backup_subprocess(monkeypatch):
    """Mock subprocess_runner.run and boto3 for core.backup."""

    def _fake_run(*args, **kwargs):
        cmd = args[0] if args else kwargs.get("args", [])
        stdout = "ok"
        if isinstance(cmd, list):
            if "version" in cmd:
                stdout = "wal-g v1.0"
            elif "backup-list" in cmd:
                stdout = json.dumps(
                    [
                        {
                            "backup_name": "old_backup",
                            "start_time": "2020-01-01T00:00:00",
                        }
                    ]
                )
            elif "backup-delete" in cmd:
                stdout = "deleted"
        return MagicMock(returncode=0, stdout=stdout, stderr="")

    monkeypatch.setattr(backup_module.subprocess_runner, "run", _fake_run)

    mock_boto = MagicMock()
    mock_client = MagicMock()
    mock_client.get_paginator.return_value.paginate.return_value = [{"Contents": [{"Size": 1024}]}]
    mock_boto.client.return_value = mock_client
    monkeypatch.setattr(backup_module, "boto3", mock_boto, raising=False)

    mock_scheduler = MagicMock()
    monkeypatch.setattr(task_scheduler, "scheduler", mock_scheduler)


# ---------------------------------------------------------------------------
# core.backup_strategy
# ---------------------------------------------------------------------------
def _base_backup_cfg(tmp_path):
    return {
        "enabled": False,
        "backup_interval_hours": 24,
        "retention_days": 30,
        "backup_location": str(tmp_path),
        "compression_enabled": False,
        "encryption_enabled": False,
        "backup_types": ["database", "config", "logs"],
        "integrity_check_enabled": True,
        "max_backup_size_gb": 100,
        "concurrent_backups": 1,
        "backup_notification_enabled": True,
    }


def test_backup_strategy_configuration(monkeypatch, tmp_path):
    cfg = _base_backup_cfg(tmp_path)
    monkeypatch.setattr(backup_strategy, "_backup_config", cfg)
    monkeypatch.setattr(backup_strategy, "_backup_history", [])

    backup_strategy.configure_backup_strategy(
        backup_interval_hours=12,
        retention_days=7,
        backup_location=str(tmp_path / "backups"),
    )

    conf = backup_strategy.get_backup_config()
    assert conf["backup_interval_hours"] == 12
    assert conf["retention_days"] == 7
    assert conf["backup_types"] == ["database", "config", "logs"]
    assert backup_strategy.is_backup_enabled() is True


async def test_backup_strategy_database_backup(monkeypatch, tmp_path):
    cfg = _base_backup_cfg(tmp_path)
    monkeypatch.setattr(backup_strategy, "_backup_config", cfg)
    monkeypatch.setattr(backup_strategy, "_backup_history", [])
    _patch_backup_strategy_subprocess(monkeypatch, b"SELECT 1;\n")

    result = await backup_strategy.perform_database_backup()
    assert result["status"] == "success"
    assert result["type"] == "database"
    assert "backup_id" in result
    assert "manifest" in result
    assert result["manifest"]["integrity_verified"] is True

    manifest_file = os.path.join(os.path.dirname(result["path"]), "manifest.json")
    assert backup_strategy.validate_backup_manifest(manifest_file) is True

    history = backup_strategy.get_backup_history()
    assert len(history) == 1
    assert len(backup_strategy.get_recent_backups(10)) == 1

    stats = backup_strategy.get_backup_statistics()
    assert stats["total_backups"] == 1
    assert stats["successful_backups"] == 1
    assert "success_rate" in stats

    restore = await backup_strategy.restore_backup(result["backup_id"])
    assert restore["status"] == "success"
    assert restore["restored_type"] == "database"


async def test_backup_strategy_config_backup(monkeypatch, tmp_path):
    cfg = _base_backup_cfg(tmp_path)
    cfg["compression_enabled"] = True
    cfg["backup_types"] = ["config"]
    monkeypatch.setattr(backup_strategy, "_backup_config", cfg)
    monkeypatch.setattr(backup_strategy, "_backup_history", [])

    monkeypatch.setattr(backup_strategy.os.path, "isfile", lambda p: True)
    monkeypatch.setattr(backup_strategy.os.path, "isdir", lambda p: str(p).endswith("config"))
    monkeypatch.setattr(backup_strategy.shutil, "copy2", lambda *a, **k: None)
    monkeypatch.setattr(backup_strategy.shutil, "copytree", lambda *a, **k: None)
    monkeypatch.setattr(
        backup_strategy.shutil,
        "make_archive",
        lambda base, fmt, root: str(tmp_path / "config.tar.gz"),
    )
    monkeypatch.setattr(backup_strategy.os.path, "getsize", lambda p: 123)
    monkeypatch.setattr(backup_strategy, "calculate_file_hash", lambda p: "hash123")

    result = await backup_strategy.perform_config_backup()
    assert result["status"] == "success"
    assert result["type"] == "config"
    assert "path" in result


async def test_backup_strategy_logs_backup(monkeypatch, tmp_path):
    cfg = _base_backup_cfg(tmp_path)
    cfg["compression_enabled"] = True
    cfg["backup_types"] = ["logs"]
    monkeypatch.setattr(backup_strategy, "_backup_config", cfg)
    monkeypatch.setattr(backup_strategy, "_backup_history", [])

    monkeypatch.setattr(backup_strategy.os, "listdir", lambda p: ["app.log"])
    monkeypatch.setattr(backup_strategy.os.path, "isfile", lambda p: True)
    monkeypatch.setattr(backup_strategy.os.path, "isdir", lambda p: False)
    monkeypatch.setattr(backup_strategy.shutil, "copy2", lambda *a, **k: None)
    monkeypatch.setattr(
        backup_strategy.shutil,
        "make_archive",
        lambda base, fmt, root: str(tmp_path / "logs.tar.gz"),
    )
    monkeypatch.setattr(backup_strategy.os.path, "getsize", lambda p: 456)
    monkeypatch.setattr(backup_strategy, "calculate_file_hash", lambda p: "hash456")

    result = await backup_strategy.perform_logs_backup()
    assert result["status"] == "success"
    assert result["type"] == "logs"
    assert "path" in result


async def test_backup_strategy_full_and_cleanup(monkeypatch, tmp_path):
    cfg = _base_backup_cfg(tmp_path)
    cfg["backup_types"] = ["database"]
    monkeypatch.setattr(backup_strategy, "_backup_config", cfg)
    monkeypatch.setattr(backup_strategy, "_backup_history", [])
    _patch_backup_strategy_subprocess(monkeypatch, b"sql data")

    full = await backup_strategy.perform_full_backup()
    assert full["overall_status"] == "success"
    assert "database" in full["results"]

    old_record = {
        "backup_id": "old_config",
        "type": "config",
        "status": "success",
        "timestamp": (datetime.now(timezone.utc) - timedelta(days=60)).isoformat(),
        "path": str(tmp_path / "old"),
    }
    backup_strategy._backup_history.append(old_record)

    cleaned = await backup_strategy.cleanup_old_backups()
    assert cleaned == 1


def test_backup_strategy_hash_and_encryption(tmp_path):
    plain = tmp_path / "plain.txt"
    plain.write_bytes(b"hello world")

    h = backup_strategy.calculate_file_hash(str(plain))
    assert h == hashlib.sha256(b"hello world").hexdigest()
    assert backup_strategy.verify_backup_integrity(str(plain), h) is True
    assert backup_strategy.verify_backup_integrity(str(plain), "wrong") is False

    enc = tmp_path / "plain.enc"
    dec = tmp_path / "plain_dec.txt"
    assert backup_strategy.encrypt_file(str(plain), str(enc)) is True
    assert backup_strategy.decrypt_file(str(enc), str(dec)) is True
    assert dec.read_bytes() == b"hello world"


# ---------------------------------------------------------------------------
# core.enterprise_features
# ---------------------------------------------------------------------------
async def test_enterprise_features(monkeypatch):
    ef = EnterpriseFeatures()
    await ef.initialize()

    tenant = await ef.create_tenant("demo", {"region": "us"})
    assert tenant.id.startswith("tenant_")
    assert tenant.name == "demo"
    assert (await ef.get_tenant(tenant.id)).name == "demo"

    assert await ef.update_tenant(tenant.id, {"name": "demo2"}) is True
    assert (await ef.get_tenant(tenant.id)).name == "demo2"

    permission = await ef.grant_permission("user1", tenant.id, {"read", "write"}, ["admin"])
    assert permission.user_id == "user1"
    assert await ef.check_permission("user1", tenant.id, "read") is True
    assert await ef.check_permission("user1", tenant.id, "delete") is False
    assert await ef.revoke_permission("user1", tenant.id) is True
    assert await ef.check_permission("user1", tenant.id, "read") is False

    provider = await ef.configure_sso_provider("oauth2", {"name": "okta"})
    assert provider.id.startswith("sso_oauth2_")
    auth = await ef.authenticate_sso(provider.id, {"access_token": "tok"})
    assert auth is not None
    assert auth["authenticated"] is True
    assert "session_id" in auth
    assert await ef.authenticate_sso("unknown", {}) is None

    saml = await ef.configure_sso_provider("saml", {})
    assert await ef.authenticate_sso(saml.id, {}) is None

    compliance = await ef.assess_compliance(ComplianceStandard.SOC2)
    assert compliance["standard"] == "soc2"
    assert compliance["overall_status"] == "compliant"
    assert len(compliance["requirements"]) == 4

    if enterprise_features.CRYPTO_AVAILABLE:
        from cryptography.fernet import Fernet

        ef.encryption_keys["fernet"] = Fernet.generate_key()
    secret = "super-secret"
    enc = await ef.encrypt_data(secret)
    assert isinstance(enc, str)
    assert await ef.decrypt_data(enc) == secret

    logs = await ef.query_audit_logs(tenant_id=tenant.id)
    assert isinstance(logs, list)
    assert len(logs) >= 1

    stats = await ef.get_enterprise_statistics()
    assert stats["total_tenants"] == 1
    assert stats["total_permissions"] == 0

    async def _noop_cleanup(self, tenant_id):
        pass

    monkeypatch.setattr(EnterpriseFeatures, "_cleanup_tenant_data", _noop_cleanup)
    assert await ef.delete_tenant(tenant.id) is True
    assert await ef.get_tenant(tenant.id) is None


# ---------------------------------------------------------------------------
# core.backup
# ---------------------------------------------------------------------------
async def test_backup_manager_and_factory(monkeypatch):
    _patch_backup_subprocess(monkeypatch)

    manager = create_backup_manager({})
    assert isinstance(manager, BackupManager)
    assert manager._is_initialized is True

    info = await manager.create_backup(BackupType.FULL)
    assert info.status.value == "completed"
    assert info.backup_id.startswith("full_")

    status = manager.get_backup_status(info.backup_id)
    assert status["status"] == "completed"

    all_statuses = manager.get_all_backup_statuses()
    assert len(all_statuses) == 1

    backups = await manager.list_backups()
    assert isinstance(backups, list)
    assert backups[0]["backup_name"] == "old_backup"

    restore_ok = await manager.restore_backup(info.backup_id)
    assert restore_ok is True

    cleaned = await manager.cleanup_old_backups()
    assert cleaned == 1

    scheduled = manager.schedule_backup(BackupType.INCREMENTAL, "0 3 * * *")
    assert scheduled is True


# ---------------------------------------------------------------------------
# core.tracing_visualization
# ---------------------------------------------------------------------------
def test_tracing_visualization():
    manager = get_tracing_visualization_manager({})
    assert isinstance(manager, tracing_visualization.TracingVisualizationManager)

    now = datetime.now(timezone.utc)
    spans = [
        {
            "span_id": "s1",
            "parent_span_id": None,
            "operation_name": "op1",
            "service_name": "svc",
            "start_time": now.isoformat(),
            "duration_ms": 100.0,
            "status": "OK",
            "attributes": {},
        },
        {
            "span_id": "s2",
            "parent_span_id": "s1",
            "operation_name": "op2",
            "service_name": "svc",
            "start_time": now.isoformat(),
            "duration_ms": 40.0,
            "status": "OK",
            "attributes": {},
        },
    ]

    trace = TraceData(
        trace_id="trace-1",
        root_span_id="s1",
        service_name="svc",
        operation_name="op1",
        start_time=now,
        end_time=now + timedelta(milliseconds=100),
        duration_ms=100.0,
        status="OK",
        spans=spans,
    )

    manager.add_trace_data(trace)
    assert manager.total_traces == 1

    trace_view = manager.generate_trace_view("trace-1")
    assert trace_view is not None
    assert trace_view["trace_id"] == "trace-1"
    assert trace_view["visualization_type"] == "trace_view"
    assert "span_tree" in trace_view
    assert "span_statistics" in trace_view
    assert manager.generate_trace_view("missing") is None

    flame = manager.generate_flame_graph("trace-1")
    assert flame["visualization_type"] == "flame_graph"

    gantt = manager.generate_gantt_chart("trace-1")
    assert gantt["visualization_type"] == "gantt_chart"
    assert len(gantt["gantt_data"]) == 2

    service_map = manager.generate_service_map()
    assert service_map["visualization_type"] == "service_map"
    assert "nodes" in service_map
    assert service_map["total_services"] == 1

    dashboard = manager.generate_metrics_dashboard(TimeRange.LAST_24_HOURS)
    assert dashboard["visualization_type"] == "metrics_dashboard"
    assert dashboard["time_range"] == "24h"
    assert dashboard["total_traces"] == 1

    stats = manager.get_statistics()
    assert stats["total_traces"] == 1
    assert stats["total_services"] == 1
