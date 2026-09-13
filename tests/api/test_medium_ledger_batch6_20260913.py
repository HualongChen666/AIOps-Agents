# -*- coding: utf-8 -*-
"""Regression tests for a batch of (中) audit-ledger defects.

Covers:
- API-097 plugin_marketplace_router must use the injected DB session (no shadowing)
- API-106 plugin_marketplace_advanced_router must surface storage failures
- API-121 hardware_log_router must await the async repair engine
- API-123 vulnerability_router.create_alert must match core alert_service's signature
- API-136 assets advanced routes must not be shadowed by assets_router's /{id}
- API-142 graphql DataLoader must expose real batch/performance statistics
- API-145 disaster restore must only report success when it really restored
"""

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from core.interface.graphql.dataloader import DataLoader


# ---------------------------------------------------------------------------
# API-097 — plugin_marketplace_router uses the injected session
# ---------------------------------------------------------------------------
def test_plugin_marketplace_router_uses_injected_session():
    from api.plugin_marketplace_router import router
    from core.auth import get_current_user
    from core.database import get_db

    user = MagicMock()
    user.id = "u1"
    user.username = "tester"
    user.role = "admin"

    injected = MagicMock()
    injected_query = MagicMock()
    injected.query.return_value = injected_query
    injected_query.filter.return_value = injected_query
    injected_query.count.return_value = 0
    injected_query.offset.return_value = injected_query
    injected_query.limit.return_value = injected_query
    injected_query.all.return_value = []

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: injected

    with patch("api.plugin_marketplace_router.cache_manager") as cache:
        cache.get.return_value = None
        with patch("api.plugin_marketplace_router.check_rate_limit"):
            resp = TestClient(app).get("/api/v1/plugin-marketplace/plugins")

    assert resp.status_code == 200
    # The endpoint must have queried the injected session, not a locally-created one.
    assert injected.query.called


# ---------------------------------------------------------------------------
# API-106 — advanced marketplace surfaces storage failures (no silent [])
# ---------------------------------------------------------------------------
def test_plugin_marketplace_advanced_surfaces_storage_error():
    from api.plugin_marketplace_advanced_router import router
    from core.auth import get_current_user
    from core.database import get_db

    user = MagicMock()
    user.id = 1
    user.username = "tester"
    user.role = "admin"

    broken = MagicMock()
    broken.query.side_effect = RuntimeError("db down")

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: broken

    with patch("api.plugin_marketplace_advanced_router.check_rate_limit"):
        resp = TestClient(app).get("/api/v1/plugin/marketplace/plugins")

    # A storage outage must not be masked as "no plugins".
    assert resp.status_code == 500


# ---------------------------------------------------------------------------
# API-121 — hardware_log_router awaits the async repair engine
# ---------------------------------------------------------------------------
def test_hardware_execute_repair_direct_awaits_async_engine():
    from api.hardware_log_router import _execute_repair_direct

    alert = {"id": "a1", "script_key": "ipmi_power_cycle", "params": {"host": "h1"}}

    with patch("core.repair_engine.execute_repair", new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = {"success": True, "return_code": 0}
        result = asyncio.run(_execute_repair_direct(alert, "tenant-1", "127.0.0.1"))

    # If the coroutine were not awaited the result would be a coroutine object.
    assert result == {"success": True, "return_code": 0}
    mock_exec.assert_awaited_once_with("ipmi_power_cycle", {"host": "h1"})


# ---------------------------------------------------------------------------
# API-123 — vulnerability create_alert matches the real alert_service contract
# ---------------------------------------------------------------------------
def test_vulnerability_create_alert_uses_real_alert_service_signature():
    from api import vulnerability_router as vr

    request = vr.AlertCreationRequest(cve_id="CVE-2024-1234", severity="high")

    with patch.object(vr.alert_service, "create_alert", new_callable=AsyncMock) as mock_create, patch.object(
        vr.vulnerability_intelligence, "get_cve", new_callable=AsyncMock
    ) as mock_get:
        mock_get.return_value = {"id": "CVE-2024-1234"}
        mock_create.return_value = {"id": "alert-xyz"}

        result = asyncio.run(vr.create_alert(request))

    assert result["success"] is True
    assert result["alert_id"] == "alert-xyz"
    kwargs = mock_create.await_args.kwargs
    # core.alert_service.create_alert(severity, message, source, status) — no
    # alert_type/title/metadata (which used to raise TypeError -> 500).
    assert set(kwargs) <= {"severity", "message", "source", "status"}


# ---------------------------------------------------------------------------
# API-136 — the assets advanced router must win over assets_router's /{id}
# ---------------------------------------------------------------------------
def test_assets_inventory_route_not_shadowed_by_int_path():
    from api.assets_advanced_router import router as advanced
    from api.assets_router import router as basic
    from core.auth_service import get_current_user

    user = MagicMock()
    user.role = "admin"
    user.id = 1

    def build(order):
        app = FastAPI()
        for r in order:
            app.include_router(r)
        app.dependency_overrides[get_current_user] = lambda: user
        return TestClient(app)

    with patch("core.auth_service.has_role", return_value=True):
        # main.py registers the advanced router first (see main.py comment).
        ok = build([advanced, basic]).get("/api/v1/assets/inventory")
        # The old (buggy) order made the int-typed /{id} capture "inventory".
        broken = build([basic, advanced]).get("/api/v1/assets/inventory")

    assert ok.status_code == 200
    assert broken.status_code == 422  # documents the shadowing bug that was fixed


# ---------------------------------------------------------------------------
# API-142 — DataLoader exposes real statistics
# ---------------------------------------------------------------------------
def test_dataloader_reports_real_batch_statistics():
    async def batch_load(keys):
        return [str(k).upper() for k in keys]

    loader = DataLoader(batch_load, max_batch_size=2)

    async def scenario():
        await loader.load_many(["a", "b", "c"])
        await loader.load("a")  # cache hit
        return loader.get_stats()

    stats = asyncio.run(scenario())
    assert stats["total_batches"] == 2
    assert stats["total_items_loaded"] == 3
    assert stats["max_batch_size_used"] == 2
    assert stats["cache_hits"] == 1
    assert stats["total_load_time_ms"] > 0
    assert stats["p95_load_time_ms"] > 0


# ---------------------------------------------------------------------------
# API-145 — disaster recovery restore is real, not a success stub
# ---------------------------------------------------------------------------
def test_restore_configuration_is_real_and_guards_paths(tmp_path, monkeypatch):
    from core.disaster_recovery import DisasterRecovery

    dr = DisasterRecovery(backup_dir=str(tmp_path))
    snapshot = tmp_path / "config_20260101_000000"
    snapshot.mkdir()
    (snapshot / "manifest.json").write_text(json.dumps({"files": ["pytest.ini"]}))
    (snapshot / "pytest.ini").write_text("restored-marker\n")

    workdir = tmp_path / "work"
    workdir.mkdir()
    monkeypatch.chdir(workdir)

    assert dr.restore_configuration(str(snapshot)) is True
    assert Path("pytest.ini").read_text().strip() == "restored-marker"

    # A manifest referencing a file that is not inside the snapshot must fail.
    evil = tmp_path / "config_evil"
    evil.mkdir()
    (evil / "manifest.json").write_text(json.dumps({"files": ["../../etc/hosts"]}))
    assert dr.restore_configuration(str(evil)) is False


def test_restore_redis_rejects_non_rdb(tmp_path):
    from core.disaster_recovery import DisasterRecovery

    dr = DisasterRecovery(backup_dir=str(tmp_path))
    bogus = tmp_path / "x.rdb"
    bogus.write_bytes(b"NOTRDB")
    assert dr.restore_redis(str(bogus)) is False
    assert dr.restore_redis(str(tmp_path / "missing.rdb")) is False
