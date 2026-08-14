# -*- coding: utf-8 -*-
"""Functional coverage tests for core batch 22-a modules."""

import asyncio
import gzip
import json
import os
import secrets
import shutil
import types
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.testclient import TestClient

import core.agent.observability_client as oc
import core.api_response_middleware as arm
import core.backup_strategy as bs
import core.security_testing_system as sts
from core.database_connection_optimizer import (
    ConnectionStatus,
    DatabaseConnectionOptimizer,
    PoolStrategy,
    ReadWriteStrategy,
    TransactionIsolationLevel,
    get_database_connection_optimizer,
)
from core.security_testing_system import (
    SecurityTest,
    SecurityTestingSystem,
    SeverityLevel,
    TestStatus,
    TestType,
    get_security_testing_system,
)

pytestmark = [pytest.mark.core]


# ---------------------------------------------------------------------------
# core.agent.observability_client
# ---------------------------------------------------------------------------
class _FakeResponse:
    def __init__(self, data=None, content=None, status_code=200, raise_on_call=False):
        self.json_data = data
        self.content = content if content is not None else (
            json.dumps(data).encode("utf-8") if data is not None else b""
        )
        self.status_code = status_code
        self.raise_on_call = raise_on_call
        self.raise_for_status = MagicMock()

    def json(self):
        if self.raise_on_call:
            raise RuntimeError("boom")
        return self.json_data


def _make_fake_httpx(default=None):
    """Return a minimal fake ``httpx`` module for observability_client."""
    default_resp = default if default is not None else _FakeResponse({"data": {"result": []}})

    class Client:
        response = default_resp

        def __init__(self, *args, **kwargs):
            pass

        def get(self, url, *args, **kwargs):
            return self.response

    class Limits:
        def __init__(self, *, max_connections, max_keepalive_connections):
            pass

    return types.SimpleNamespace(Client=Client, Limits=Limits)


@pytest.fixture
def fake_observability(monkeypatch):
    fake = _make_fake_httpx()
    monkeypatch.setattr(oc, "httpx", fake)
    monkeypatch.setattr(oc, "HTTPX_AVAILABLE", True)
    monkeypatch.setattr(oc, "_HTTP_CLIENT", None)
    monkeypatch.setattr(oc, "validate_promql", lambda q: None)
    monkeypatch.setattr(oc, "validate_logql", lambda q: None)
    monkeypatch.setattr(oc, "parse_duration_to_seconds", lambda d: 15.0)
    monkeypatch.setattr(oc, "limit_range_samples", lambda *a, **k: 15.0)
    return fake


def test_observability_helpers():
    assert oc._sanitize_url_for_log("http://x") == "http://x"
    assert oc._safe_label("web-frontend_v1") == "web-frontend_v1"
    with pytest.raises(ValueError):
        oc._safe_label("a" * 201)
    with pytest.raises(ValueError):
        oc._safe_label("bad;value")
    with pytest.raises(ValueError):
        oc._safe_label(123)


def test_read_and_env(monkeypatch, tmp_path):
    f = tmp_path / "token"
    f.write_text("tok")
    assert oc._read_file(str(f)) == "tok"

    monkeypatch.setenv("AIOPS_KUBERNETES_TOKEN", "tok")
    assert oc.get_kubernetes_token() == "tok"
    monkeypatch.delenv("AIOPS_KUBERNETES_TOKEN", raising=False)

    monkeypatch.setenv("AIOPS_KUBERNETES_CA", "ca.crt")
    assert oc.get_kubernetes_ca() == "ca.crt"
    monkeypatch.delenv("AIOPS_KUBERNETES_CA", raising=False)

    monkeypatch.setenv("AIOPS_KUBERNETES_VERIFY", "false")
    assert oc._should_verify_ssl() is False
    monkeypatch.setenv("AIOPS_KUBERNETES_VERIFY", "yes")
    assert oc._should_verify_ssl() is True


def test_headers_and_verify(monkeypatch):
    monkeypatch.setenv("AIOPS_PROMETHEUS_TOKEN", "prom-token")
    assert oc._prom_headers().get("Authorization") == "Bearer prom-token"
    monkeypatch.setenv("AIOPS_KUBERNETES_TOKEN", "k8s-token")
    assert oc._k8s_headers()["Authorization"] == "Bearer k8s-token"

    monkeypatch.setenv("AIOPS_KUBERNETES_VERIFY", "false")
    assert oc._k8s_verify() is False
    monkeypatch.setenv("AIOPS_KUBERNETES_VERIFY", "true")
    monkeypatch.setenv("AIOPS_KUBERNETES_CA", "ca.crt")
    assert oc._k8s_verify() == "ca.crt"


def test_http_get_json_success(fake_observability, monkeypatch):
    monkeypatch.setenv("AIOPS_PROMETHEUS_URL", "http://prom")
    fake_observability.Client.response = _FakeResponse({"data": {"result": []}})
    data, error = oc._http_get_json("http://prom/api/v1/query")
    assert data is not None
    assert error is None


def test_http_get_json_errors(fake_observability, monkeypatch):
    monkeypatch.setenv("AIOPS_PROMETHEUS_URL", "http://prom")
    fake_observability.Client.response = _FakeResponse(
        content=b"x" * (oc._MAX_RESPONSE_BYTES + 1)
    )
    data, error = oc._http_get_json("http://prom/api/v1/query")
    assert data is None
    assert "large" in error.lower()


def test_query_prometheus_branches(fake_observability, monkeypatch):
    assert oc.query_prometheus("up") is None
    monkeypatch.setenv("AIOPS_PROMETHEUS_URL", "http://prom")
    fake_observability.Client.response = _FakeResponse({"data": {"result": []}})
    assert oc.query_prometheus("up") is not None

    monkeypatch.setattr(oc, "validate_promql", lambda q: (_ for _ in ()).throw(ValueError("bad")))
    assert oc.query_prometheus("up") is None


def test_query_prometheus_range(fake_observability, monkeypatch):
    monkeypatch.setenv("AIOPS_PROMETHEUS_URL", "http://prom")
    fake_observability.Client.response = _FakeResponse({"data": {"result": []}})
    result = oc.query_prometheus_range("up", 1.0, 2.0, step="15s")
    assert isinstance(result, dict)


def test_extract_scalar_and_metrics(fake_observability, monkeypatch):
    assert oc._extract_prom_scalar_value(None) is None
    assert oc._extract_prom_scalar_value({}) is None
    assert oc._extract_prom_scalar_value({"data": {"result": [{"value": [1, "abc"]}]}}) is None
    assert oc._extract_prom_scalar_value({"data": {"result": [{"value": [1, "12.5"]}]}}) == 12.5

    monkeypatch.setenv("AIOPS_PROMETHEUS_URL", "http://prom")
    fake_observability.Client.response = _FakeResponse(
        {"data": {"result": [{"value": [1, "9.9"]}]}}
    )
    metrics = oc.query_service_metrics("web")
    assert metrics["available"] is True
    assert metrics["request_rate"] == 9.9

    network = oc.query_network_metrics("1.2.3.4")
    assert network["available"] is True
    assert network["target"] == "1.2.3.4"


def test_query_loki(fake_observability, monkeypatch):
    assert oc.query_loki("{app=\"x\"}") is None
    monkeypatch.setenv("AIOPS_LOKI_URL", "http://loki")
    fake_observability.Client.response = _FakeResponse({"data": {"result": []}})
    result = oc.query_loki("{app=\"x\"}", limit=5)
    assert isinstance(result, dict)


def test_query_kubernetes(monkeypatch, fake_observability):
    monkeypatch.setenv("AIOPS_KUBERNETES_API_URL", "http://k8s")
    fake_observability.Client.response = _FakeResponse({
        "items": [
            {
                "type": "Warning",
                "reason": "Failed",
                "message": "m",
                "involvedObject": {"name": "pod1", "kind": "Pod"},
                "metadata": {"namespace": "ns"},
                "lastTimestamp": "t",
            }
        ]
    })
    events = oc.query_kubernetes_events(namespace="ns", field_selector="type=Warning")
    assert len(events) == 1
    assert events[0]["object"] == "pod1"

    pod = oc.query_kubernetes_pod("pod1", namespace="ns")
    assert pod["available"] is True

    node = oc.query_kubernetes_node("node1")
    assert node["available"] is True


def test_query_change_events(tmp_path, monkeypatch, fake_observability):
    events_file = tmp_path / "events.json"
    events_file.write_text(json.dumps([{"id": "file-1"}]))
    monkeypatch.setenv("AIOPS_CHANGE_EVENTS_FILE", str(events_file))
    assert oc.query_change_events("svc")[0]["id"] == "file-1"

    monkeypatch.setenv("AIOPS_CHANGE_EVENTS_URL", "http://changes")
    fake_observability.Client.response = _FakeResponse([{"id": "api-1"}])
    events = oc.query_change_events("svc", hours=1)
    assert any(e["id"] == "api-1" for e in events)


# ---------------------------------------------------------------------------
# core.backup_strategy
# ---------------------------------------------------------------------------
@pytest.fixture
def fresh_backup_state(monkeypatch):
    monkeypatch.setattr(bs, "_backup_history", [])
    monkeypatch.setattr(
        bs,
        "_backup_config",
        {
            "enabled": False,
            "backup_interval_hours": 24,
            "retention_days": 30,
            "backup_location": "/backups",
            "compression_enabled": True,
            "encryption_enabled": False,
            "backup_types": ["database", "config", "logs"],
            "integrity_check_enabled": True,
            "backup_notification_enabled": True,
            "max_backup_size_gb": 100,
            "concurrent_backups": 1,
        },
    )


@pytest.fixture
def fake_pg_config(monkeypatch, tmp_path):
    class Cfg:
        POSTGRES_DB = "db"
        POSTGRES_USER = "user"
        POSTGRES_HOST = "localhost"
        POSTGRES_PORT = "5432"
        POSTGRES_PASSWORD = "pw"
        __file__ = str(tmp_path / "config.py")

    (tmp_path / "config.py").write_text("# config")
    monkeypatch.setattr(bs, "config", Cfg())
    return Cfg


@pytest.fixture
def fake_subprocess_backup(monkeypatch):
    process = AsyncMock()
    process.communicate = AsyncMock(return_value=(b"-- sql", b""))
    process.returncode = 0
    fake_asyncio = types.SimpleNamespace(
        create_subprocess_exec=AsyncMock(return_value=process),
        subprocess=types.SimpleNamespace(PIPE=-1, STDOUT=-2, DEVNULL=-3),
    )
    monkeypatch.setattr(bs, "asyncio", fake_asyncio)
    return process


def test_backup_config(fresh_backup_state):
    bs.configure_backup_strategy(
        backup_interval_hours=12,
        retention_days=7,
        backup_location="/tmp/backups",
        compression_enabled=False,
    )
    cfg = bs.get_backup_config()
    assert cfg["enabled"] is True
    assert cfg["backup_interval_hours"] == 12
    assert bs.is_backup_enabled() is True


@pytest.mark.asyncio
async def test_perform_database_backup_success(fresh_backup_state, fake_pg_config, fake_subprocess_backup, tmp_path):
    bs._backup_config["backup_location"] = str(tmp_path)
    bs._backup_config["compression_enabled"] = True
    bs._backup_config["encryption_enabled"] = True
    bs._backup_config["integrity_check_enabled"] = False
    result = await bs.perform_database_backup()
    assert result["status"] == "success"
    assert result["path"].endswith(".gz.enc")


@pytest.mark.asyncio
async def test_perform_database_backup_failure(fresh_backup_state, fake_pg_config, fake_subprocess_backup, tmp_path):
    fake_subprocess_backup.returncode = 1
    fake_subprocess_backup.communicate = AsyncMock(return_value=(b"", b"pg_dump failed"))
    bs._backup_config["backup_location"] = str(tmp_path)
    result = await bs.perform_database_backup()
    assert result["status"] == "failed"
    assert "pg_dump" in result["error"]


@pytest.mark.asyncio
async def test_perform_config_backup(fresh_backup_state, fake_pg_config, tmp_path, monkeypatch):
    bs._backup_config["backup_location"] = str(tmp_path)
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("x=1")
    (tmp_path / ".env.example").write_text("x=2")
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "app.py").write_text("# app")
    result = await bs.perform_config_backup()
    assert result["status"] == "success"
    assert result["path"].endswith(".tar.gz")


@pytest.mark.asyncio
async def test_perform_logs_backup(fresh_backup_state, tmp_path, monkeypatch):
    bs._backup_config["backup_location"] = str(tmp_path)
    monkeypatch.chdir(tmp_path)
    (tmp_path / "logs").mkdir()
    (tmp_path / "logs" / "app.log").write_text("log")
    (tmp_path / "system.log").write_text("system")
    result = await bs.perform_logs_backup()
    assert result["status"] == "success"
    assert result["path"].endswith(".tar.gz")


@pytest.mark.asyncio
async def test_perform_full_backup(fresh_backup_state, fake_pg_config, fake_subprocess_backup, tmp_path, monkeypatch):
    bs._backup_config["backup_location"] = str(tmp_path)
    bs._backup_config["integrity_check_enabled"] = False
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("x=1")
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "app.py").write_text("# app")
    (tmp_path / "logs").mkdir()
    (tmp_path / "logs" / "app.log").write_text("log")
    result = await bs.perform_full_backup()
    assert "database" in result["results"]
    assert result["overall_status"] == "success"


@pytest.mark.asyncio
async def test_backup_history_and_cleanup(fresh_backup_state, tmp_path):
    old_time = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
    keep_file = tmp_path / "keep.txt"
    keep_file.write_text("keep")
    old_file = tmp_path / "old.txt"
    old_file.write_text("old")
    bs._backup_config["retention_days"] = 1
    bs._backup_history.extend([
        {"backup_id": "old", "timestamp": old_time, "path": str(old_file), "status": "success"},
        {"backup_id": "keep", "timestamp": datetime.now(timezone.utc).isoformat(), "path": str(keep_file), "status": "success"},
        {"backup_id": "missing", "timestamp": old_time, "path": "/nonexistent", "status": "success"},
    ])
    cleaned = await bs.cleanup_old_backups()
    assert cleaned >= 2
    assert len(bs.get_backup_history()) == 1
    assert bs.get_recent_backups(1)[0]["backup_id"] == "keep"
    stats = bs.get_backup_statistics()
    assert stats["total_backups"] == 1


def test_hash_and_integrity(tmp_path):
    f = tmp_path / "data.txt"
    f.write_text("hello")
    h = bs.calculate_file_hash(str(f), "sha256")
    assert len(h) == 64
    assert bs.verify_backup_integrity(str(f), h) is True
    assert bs.verify_backup_integrity(str(f), "bad") is False
    f.write_text("changed")
    assert bs.verify_backup_integrity(str(f), h) is False


def test_encrypt_decrypt(tmp_path, monkeypatch):
    monkeypatch.setenv("BACKUP_ENCRYPTION_KEY", "secret")
    src = tmp_path / "plain.txt"
    enc = tmp_path / "plain.txt.enc"
    dec = tmp_path / "plain.txt.dec"
    src.write_text("hello")
    assert bs.encrypt_file(str(src), str(enc)) is True
    assert enc.exists()
    assert bs.decrypt_file(str(enc), str(dec)) is True
    assert dec.read_text() == "hello"
    bad = tmp_path / "bad.enc"
    bad.write_bytes(b"not-valid-fernet")
    assert bs.decrypt_file(str(bad), str(tmp_path / "bad.dec")) is False


def test_validate_manifest(tmp_path):
    f = tmp_path / "db.sql"
    f.write_text("sql")
    h = bs.calculate_file_hash(str(f))
    manifest = {
        "backup_id": "b1",
        "type": "database",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "file_path": str(f),
        "file_size_bytes": f.stat().st_size,
        "file_hash": h,
    }
    mpath = tmp_path / "manifest.json"
    mpath.write_text(json.dumps(manifest))
    assert bs.validate_backup_manifest(str(mpath)) is True

    bad = mpath.with_suffix(".bad.json")
    bad.write_text(json.dumps({k: v for k, v in manifest.items() if k != "file_hash"}))
    assert bs.validate_backup_manifest(str(bad)) is False

    missing = dict(manifest)
    missing["file_path"] = "/nonexistent"
    bad2 = tmp_path / "missing.json"
    bad2.write_text(json.dumps(missing))
    assert bs.validate_backup_manifest(str(bad2)) is False


@pytest.mark.asyncio
async def test_restore_database_backup_success(fresh_backup_state, fake_pg_config, fake_subprocess_backup, tmp_path):
    backup_dir = tmp_path / "db_1"
    backup_dir.mkdir()
    gz_path = backup_dir / "db.sql.gz"
    with gzip.open(gz_path, "wb") as f_out:
        f_out.write(b"CREATE TABLE t;")
    h = bs.calculate_file_hash(str(gz_path))
    manifest = {
        "backup_id": "db_1",
        "type": "database",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "file_path": str(gz_path),
        "file_size_bytes": gz_path.stat().st_size,
        "file_hash": h,
        "compressed": True,
        "encrypted": False,
        "integrity_verified": True,
    }
    (backup_dir / "manifest.json").write_text(json.dumps(manifest))
    bs._backup_history.append({
        "backup_id": "db_1",
        "type": "database",
        "path": str(gz_path),
        "compressed": True,
        "encrypted": False,
        "manifest": manifest,
    })
    bs._backup_config["integrity_check_enabled"] = True
    result = await bs.restore_database_backup("db_1")
    assert result["status"] == "success"


@pytest.mark.asyncio
async def test_restore_backup_logs(fresh_backup_state, tmp_path):
    log_file = tmp_path / "log.tar.gz"
    log_file.write_text("log")
    bs._backup_history.append({
        "backup_id": "log_1",
        "type": "logs",
        "path": str(log_file),
    })
    result = await bs.restore_backup("log_1")
    assert result["status"] == "success"


@pytest.mark.asyncio
async def test_restore_backup_config(fresh_backup_state, tmp_path):
    cfg_dir = tmp_path / "cfg"
    cfg_dir.mkdir()
    (cfg_dir / "a.txt").write_text("a")
    archive_path = shutil.make_archive(str(tmp_path / "config"), "gztar", str(cfg_dir))
    bs._backup_history.append({
        "backup_id": "cfg_1",
        "type": "config",
        "path": archive_path,
    })
    result = await bs.restore_backup("cfg_1")
    assert result["status"] == "success"
    assert "restored_path" in result


# ---------------------------------------------------------------------------
# core.database_connection_optimizer
# ---------------------------------------------------------------------------
@pytest.fixture
def opt():
    return DatabaseConnectionOptimizer({
        "default_pool_size": 20,
        "max_overflow": 10,
        "pool_recycle_seconds": 3600,
    })


def test_optimizer_factory():
    o = get_database_connection_optimizer({"default_pool_size": 5})
    assert o.default_pool_size == 5


def test_pool_lifecycle(opt):
    opt.create_pool("primary", pool_size=2, strategy=PoolStrategy.FIXED)
    assert len(opt.pools["primary"]["connections"]) == 2
    opt.create_pool("primary", pool_size=5)
    assert len(opt.pools["primary"]["connections"]) == 2

    conn = opt.get_connection("missing")
    assert conn is None
    conn = opt.get_connection("primary")
    assert conn is not None
    opt.release_connection("primary", conn, query_duration_ms=10.0)
    assert opt.connection_metrics[conn].total_queries == 1

    opt.release_connection("primary", "missing")
    opt.close_connection("primary", conn)
    assert conn not in opt.connection_metrics
    opt.close_connection("primary", "missing")


def test_overflow_and_queue(opt):
    opt.create_pool("p", pool_size=1, max_overflow=1, strategy=PoolStrategy.FIXED)
    c1 = opt.get_connection("p")
    c2 = opt.get_connection("p")
    assert c2 is not None
    c3 = opt.get_connection("p")
    assert c3 is None
    assert len(opt.pools["p"]["waiting_queue"]) == 1
    opt.release_connection("p", c1)
    assert len(opt.pools["p"]["waiting_queue"]) == 0


def test_recycle_and_metrics(opt):
    opt.create_pool("p", pool_size=1, strategy=PoolStrategy.FIXED)
    conn = opt.get_connection("p")
    opt.release_connection("p", conn)
    old = datetime.now(timezone.utc) - timedelta(days=1)
    opt.connection_metrics[conn].created_at = old
    recycled = opt.recycle_old_connections("p")
    assert recycled == 1

    opt.create_pool("p2", pool_size=2, strategy=PoolStrategy.FIXED)
    c = opt.get_connection("p2")
    opt.release_connection("p2", c, query_duration_ms=20.0)
    metrics = opt.get_pool_metrics("p2")
    assert metrics.total_connections == 2
    assert metrics.avg_duration_ms == 10.0


def test_optimize_pool_size(opt):
    opt.create_pool("p", pool_size=20, strategy=PoolStrategy.FIXED)
    result = opt.optimize_pool_size("p")
    assert "error" in result
    from core.database_connection_optimizer import PoolMetrics
    opt.pool_metrics_history["p"].append(PoolMetrics(pool_name="p", active_connections=0, waiting_requests=5))
    result = opt.optimize_pool_size("p")
    assert result["recommendations"][0]["type"] == "increase_pool_size"
    for _ in range(5):
        opt.pool_metrics_history["p"].append(PoolMetrics(pool_name="p", active_connections=1, waiting_requests=0))
    result = opt.optimize_pool_size("p")
    assert any(r["type"] == "decrease_pool_size" for r in result["recommendations"])


def test_monitor_health(opt):
    opt.create_pool("p", pool_size=2, strategy=PoolStrategy.FIXED)
    conn = opt.get_connection("p")
    opt.release_connection("p", conn)
    opt.connection_metrics[conn].created_at = datetime.now(timezone.utc) - timedelta(days=2)
    health = opt.monitor_connection_health("p")
    assert health["status"] == "warning"
    opt.connection_metrics[conn].status = ConnectionStatus.ERROR
    health = opt.monitor_connection_health("p")
    assert health["status"] == "critical"


def test_replicas_and_read_write(opt):
    opt.create_pool("primary", pool_size=2, strategy=PoolStrategy.FIXED)
    opt.add_replica_config("r1", "host1", 5432, "db", lag_ms=10)
    opt.add_replica_config("r2", "host2", 5432, "db", lag_ms=20, weight=3)
    lag = opt.monitor_replication_lag()
    assert len(lag["replicas"]) == 2
    assert lag["healthy"] is True

    opt.read_write_strategy = ReadWriteStrategy.NONE
    assert opt.get_read_connection("select").startswith("primary")
    opt.read_write_strategy = ReadWriteStrategy.PRIMARY_REPLICA
    assert opt.get_read_connection("select").startswith("replica")
    opt.read_write_strategy = ReadWriteStrategy.ROUND_ROBIN
    assert opt.get_read_connection("select") is not None
    opt.read_write_strategy = ReadWriteStrategy.WEIGHTED
    assert opt.get_read_connection("select") is not None
    assert opt.get_read_connection("insert").startswith("primary")


def test_aliases_and_splitting(opt):
    pool = opt.create_connection_pool("alias_pool", url="postgresql://x")
    assert pool["name"] == "alias_pool"
    stats = opt.get_pool_stats("alias_pool")
    assert "total_connections" in stats
    health = opt.check_pool_health("alias_pool")
    assert "status" in health

    opt.configure_read_write_splitting(
        "alias_pool",
        replicas=["r1", "r2"],
        strategy="round_robin",
    )
    assert opt.read_write_strategy == ReadWriteStrategy.ROUND_ROBIN


def test_transactions(opt):
    txn = opt.begin_transaction()
    assert txn in opt.active_transactions
    assert opt.commit_transaction(txn) is True
    assert txn not in opt.active_transactions
    assert opt.commit_transaction("missing") is False

    txn2 = opt.begin_transaction(pool_name="p", isolation_level=TransactionIsolationLevel.SERIALIZABLE)
    assert opt.rollback_transaction(txn2) is True
    stats = opt.get_transaction_stats()
    assert stats["total_transactions"] == 2


def test_get_statistics(opt):
    opt.create_pool("p", pool_size=2, strategy=PoolStrategy.FIXED)
    stats = opt.get_statistics()
    assert stats["total_pools"] == 1
    assert stats["total_connections"] == 2


# ---------------------------------------------------------------------------
# core.security_testing_system
# ---------------------------------------------------------------------------
@pytest.fixture
def security_system(monkeypatch):
    class FakeRandom:
        def randint(self, a, b):
            return 2

        def choice(self, seq):
            return seq[0] if seq else None

    monkeypatch.setattr(secrets, "SystemRandom", FakeRandom)
    fake_asyncio = types.SimpleNamespace(
        sleep=AsyncMock(),
        create_task=asyncio.create_task,
    )
    monkeypatch.setattr(sts, "asyncio", fake_asyncio)
    return SecurityTestingSystem()


def test_security_factory():
    assert isinstance(get_security_testing_system(), SecurityTestingSystem)


def test_register_and_get(security_system):
    t = SecurityTest(test_id="t1", test_name="T", test_type=TestType.SAST, target="x")
    security_system.register_test(t)
    assert "t1" in security_system.security_tests


@pytest.mark.asyncio
async def test_run_security_test(security_system, monkeypatch):
    with pytest.raises(ValueError):
        await security_system.run_security_test("missing")
    result_id = await security_system.run_security_test("sast_scan")
    assert result_id == "sast_scan"
    await security_system._execute_test("sast_scan")
    result = security_system.get_test_result("sast_scan")
    assert result is not None
    assert result["status"] == TestStatus.COMPLETED.value


@pytest.mark.asyncio
async def test_run_all_and_report(security_system, monkeypatch):
    await security_system.run_security_test("sca_scan")
    await asyncio.sleep(0.05)
    vulns = security_system.get_vulnerabilities()
    assert isinstance(vulns, list)

    report = await security_system.generate_security_report()
    assert report["total_tests"] > 0
    assert report["total_vulnerabilities"] >= 0

    security_system.security_tests["sast_scan"].enabled = False
    monkeypatch.setattr(security_system, "run_security_test", AsyncMock(return_value="id"))
    ids = await security_system.run_all_tests()
    assert "id" in ids
    ids_sast = await security_system.run_all_tests(test_type=TestType.DAST)
    assert "id" in ids_sast


def test_security_statistics(security_system):
    stats = security_system.get_statistics()
    assert stats["registered_tests"] == len(security_system.security_tests)


@pytest.mark.asyncio
async def test_auto_scan_loop(security_system):
    security_system.auto_scan_enabled = False
    await security_system.start_auto_scan_loop()
    assert True


# ---------------------------------------------------------------------------
# core.api_response_middleware
# ---------------------------------------------------------------------------
@pytest.fixture
def arm_mw():
    app = FastAPI()
    return arm.APIResponseMiddleware(app)


@pytest.mark.asyncio
async def test_middleware_options_and_excluded(arm_mw):
    async def call_next(request):
        return JSONResponse(content={"ok": True})

    req = Request({
        "type": "http",
        "method": "OPTIONS",
        "path": "/api/test",
        "headers": [],
        "query_string": b"",
    })
    resp = await arm_mw.dispatch(req, call_next)
    assert isinstance(resp, JSONResponse)

    req = Request({
        "type": "http",
        "method": "GET",
        "path": "/health",
        "headers": [],
        "query_string": b"",
    })
    resp = await arm_mw.dispatch(req, call_next)
    assert isinstance(resp, JSONResponse)

    req = Request({
        "type": "http",
        "method": "GET",
        "path": "/static/x",
        "headers": [],
        "query_string": b"",
    })
    resp = await arm_mw.dispatch(req, call_next)
    assert isinstance(resp, JSONResponse)


@pytest.mark.asyncio
async def test_middleware_wrap_and_already_formatted(arm_mw):
    async def call_next(request):
        return JSONResponse(content={"key": "value"})

    req = Request({
        "type": "http",
        "method": "GET",
        "path": "/api/test",
        "headers": [],
        "query_string": b"",
    })
    resp = await arm_mw.dispatch(req, call_next)
    body = resp.body
    payload = json.loads(body.decode("utf-8"))
    assert payload["success"] is True
    assert payload["data"] == {"key": "value"}

    async def call_wrapped(request):
        return JSONResponse(content={"success": True, "data": 1})

    resp2 = await arm_mw.dispatch(req, call_wrapped)
    payload2 = json.loads(resp2.body.decode("utf-8"))
    assert payload2["success"] is True
    assert payload2["data"] == 1


@pytest.mark.asyncio
async def test_middleware_non_json_and_exception(arm_mw):
    async def call_text(request):
        return PlainTextResponse("ok")

    req = Request({
        "type": "http",
        "method": "GET",
        "path": "/api/text",
        "headers": [],
        "query_string": b"",
    })
    resp = await arm_mw.dispatch(req, call_text)
    assert resp.body == b"ok"

    bad = JSONResponse(content={"x": 1})
    bad.body = b"not json"

    async def call_bad(request):
        return bad

    resp = await arm_mw.dispatch(req, call_bad)
    assert resp.body == b"not json"

    async def call_fail(request):
        raise ValueError("boom")

    resp = await arm_mw.dispatch(req, call_fail)
    assert resp.status_code == 500
    payload = json.loads(resp.body.decode("utf-8"))
    assert payload["success"] is False


def test_setup_api_response_middleware():
    app = FastAPI()

    @app.get("/api/x")
    def x():
        return {"x": 1}

    arm.setup_api_response_middleware(app)
    client = TestClient(app)
    resp = client.get("/api/x")
    assert resp.status_code == 200
    assert isinstance(resp.json(), dict)
