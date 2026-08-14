# -*- coding: utf-8 -*-
"""Tests for core modules batch 22b."""

import asyncio
import json
import os
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import core.api_resource_optimizer as aro
import core.feature_flag as ff
import core.macos_repair as macos
import core.mcp_server as mcp_server
import core.rbac as rbac

pytestmark = [pytest.mark.core]


# ---------------------------------------------------------------------------
# core.api_resource_optimizer
# ---------------------------------------------------------------------------


@pytest.fixture
def optimizer():
    return aro.APIResourceOptimizer(
        config={"monitoring_interval_seconds": 0.0, "default_cpu_limit": 50.0}
    )


def test_optimizer_init_and_factory():
    opt = aro.get_api_resource_optimizer({"default_cpu_limit": 70.0})
    assert opt.default_cpu_limit == 70.0
    assert isinstance(opt.get_statistics(), dict)


def test_track_and_get_usage(optimizer):
    optimizer.track_resource_usage(
        aro.ResourceType.CPU, "/api/a", "GET", 10.0, "percent"
    )
    metrics = optimizer.get_resource_usage(aro.ResourceType.CPU, "/api/a", "GET")
    assert metrics["current_usage"] == 10.0
    assert metrics["peak_usage"] == 10.0
    assert metrics["avg_usage"] == 10.0
    assert optimizer.get_all_resource_usage()


def test_resource_limits_and_checks(optimizer):
    # no metrics
    assert optimizer.check_resource_limit(aro.ResourceType.CPU, "/api/a", "GET")[
        "allowed"
    ]

    optimizer.track_resource_usage(
        aro.ResourceType.CPU, "/api/a", "GET", 60.0, "percent"
    )
    # no limit
    assert optimizer.check_resource_limit(aro.ResourceType.CPU, "/api/a", "GET")[
        "reason"
    ] == "No limit configured"

    # reject
    optimizer.set_resource_limit(
        aro.ResourceType.CPU,
        "/api/a",
        50.0,
        aro.ResourceLimitType.HARD,
        action_on_exceed="reject",
    )
    res = optimizer.check_resource_limit(aro.ResourceType.CPU, "/api/a", "GET")
    assert res["allowed"] is False
    assert res["action"] == "reject"

    # throttle
    optimizer.set_resource_limit(
        aro.ResourceType.CPU,
        "/api/a",
        50.0,
        aro.ResourceLimitType.SOFT,
        action_on_exceed="throttle",
    )
    res = optimizer.check_resource_limit(aro.ResourceType.CPU, "/api/a", "GET")
    assert res["allowed"] is True
    assert res["action"] == "throttle"

    # alert
    optimizer.set_resource_limit(
        aro.ResourceType.CPU,
        "/api/a",
        50.0,
        aro.ResourceLimitType.DYNAMIC,
        action_on_exceed="alert",
    )
    res = optimizer.check_resource_limit(aro.ResourceType.CPU, "/api/a", "GET")
    assert res["allowed"] is True
    assert res["action"] == "alert"

    # within limits
    optimizer.track_resource_usage(
        aro.ResourceType.CPU, "/api/a", "GET", 20.0, "percent"
    )
    res = optimizer.check_resource_limit(aro.ResourceType.CPU, "/api/a", "GET")
    assert res["reason"] == "Within limits"


def test_allocate_and_release(optimizer):
    optimizer.set_resource_limit(
        aro.ResourceType.MEMORY, "/api/b", 100.0, aro.ResourceLimitType.HARD
    )
    assert optimizer.allocate_resource(aro.ResourceType.MEMORY, "/api/b", 70.0) is True
    assert optimizer.allocate_resource(aro.ResourceType.MEMORY, "/api/b", 40.0) is False
    optimizer.release_resource(aro.ResourceType.MEMORY, "/api/b", 30.0)
    assert optimizer.allocate_resource(aro.ResourceType.MEMORY, "/api/b", 20.0) is True
    optimizer.release_resource(aro.ResourceType.MEMORY, "/api/b", 200.0)
    optimizer.release_resource(aro.ResourceType.MEMORY, "/api/missing", 10.0)


def test_schedules(optimizer):
    now = datetime.now(timezone.utc)
    optimizer.add_resource_schedule(
        aro.ResourceType.CPU,
        "/api/c",
        now - timedelta(seconds=10),
        now + timedelta(seconds=10),
        10.0,
        priority=5,
    )
    optimizer.set_resource_limit(
        aro.ResourceType.MEMORY, "/api/d", 500.0, aro.ResourceLimitType.HARD
    )
    optimizer.add_resource_schedule(
        aro.ResourceType.MEMORY,
        "/api/d",
        now - timedelta(seconds=10),
        now + timedelta(seconds=10),
        1000.0,
        priority=10,
    )
    assert optimizer.execute_schedules() == 1
    # second call should skip already-executed today
    assert optimizer.execute_schedules() == 0

    # lower priority gets nothing because allocation would fail
    stats = optimizer.get_statistics()
    assert stats["total_schedules_executed"] == 1


def test_optimize_recommendations(optimizer):
    # reduce allocation
    for value in [100.0, 10.0, 10.0]:
        optimizer.track_resource_usage(
            aro.ResourceType.CPU, "/api/e", "POST", value, "percent"
        )
    recs = optimizer.optimize_resource_allocation(aro.ResourceType.CPU)
    assert recs["total_endpoints"] == 1
    assert recs["recommendations"][0]["type"] == "reduce_allocation"

    # increase allocation
    optimizer2 = aro.APIResourceOptimizer()
    for value in [100.0, 99.0, 95.0]:
        optimizer2.track_resource_usage(
            aro.ResourceType.MEMORY, "/api/f", "POST", value, "percent"
        )
    recs = optimizer2.optimize_resource_allocation(aro.ResourceType.MEMORY)
    assert recs["recommendations"][0]["type"] == "increase_allocation"

    # no usage
    optimizer3 = aro.APIResourceOptimizer()
    assert "error" in optimizer3.optimize_resource_allocation(aro.ResourceType.DISK_IO)


def test_monitor_resources(optimizer):
    optimizer.track_resource_usage(
        aro.ResourceType.NETWORK_IO, "/api/g", "GET", 42.0, "mbps"
    )
    status = optimizer.monitor_resources()
    assert "network_io:GET:/api/g" in status["resources"]
    assert status["resources"]["network_io:GET:/api/g"]["unit"] == "mbps"


@pytest.mark.asyncio
async def test_start_monitoring(optimizer):
    optimizer.add_resource_schedule(
        aro.ResourceType.CPU,
        "/api/h",
        datetime.now(timezone.utc) - timedelta(seconds=5),
        datetime.now(timezone.utc) + timedelta(seconds=5),
        1.0,
    )
    await optimizer.start_monitoring()
    await asyncio.sleep(0.05)
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    for t in tasks:
        t.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
    assert optimizer.get_statistics()["total_schedules_executed"] >= 1


# ---------------------------------------------------------------------------
# core.macos_repair
# ---------------------------------------------------------------------------


class _FakeProc:
    def __init__(self, returncode, stdout=b"ok", stderr=b""):
        self.returncode = returncode
        self.communicate = AsyncMock(return_value=(stdout, stderr))


class _FakeOSPath:
    @staticmethod
    def isfile(path):
        p = str(path)
        return "/exists" in p or p.endswith(".sh")

    @staticmethod
    def abspath(path):
        return str(path)

    @staticmethod
    def isdir(path):
        return str(path).endswith("macos")

    @staticmethod
    def join(*parts):
        return os.path.join(*parts)

    @staticmethod
    def splitext(path):
        return os.path.splitext(str(path))


class _FakeOS:
    path = _FakeOSPath()
    environ = {"PATH": "fake"}

    @staticmethod
    def listdir(path):
        return ["repair.sh", "cleanup.sh"]


@pytest.fixture
def fake_os(monkeypatch):
    monkeypatch.setattr(macos, "os", _FakeOS())


@pytest.mark.asyncio
async def test_execute_macos_repair_remote():
    result = await macos.execute_macos_repair("remote", "repair.sh")
    assert result["status"] == "error"
    assert "Remote macOS" in result["output"]


@pytest.mark.asyncio
async def test_execute_macos_repair_found_script(monkeypatch, fake_os):
    async def create_shell(cmd, **kwargs):
        assert "AIOPS_ARGS" in kwargs["env"]
        assert kwargs["env"]["AIOPS_ARG_KEY"] == "value"
        return _FakeProc(0, b"fixed")

    monkeypatch.setattr(macos.asyncio, "create_subprocess_shell", create_shell)
    result = await macos.execute_macos_repair(
        "localhost", "/exists/repair.sh", {"key": "value"}
    )
    assert result["status"] == "success"
    assert result["output"] == "fixed"
    assert result["exit_code"] == 0


@pytest.mark.asyncio
async def test_execute_macos_repair_fallback(monkeypatch, fake_os):
    async def create_shell(cmd, **kwargs):
        return _FakeProc(1, b"", b"fail")

    monkeypatch.setattr(macos.asyncio, "create_subprocess_shell", create_shell)
    result = await macos.execute_macos_repair("localhost", "missing_cmd")
    assert result["status"] == "error"
    assert result["exit_code"] == 1


def test_get_available_macos_scripts(monkeypatch, fake_os):
    scripts = macos.get_available_macos_scripts()
    assert "repair" in scripts
    assert "cleanup" in scripts

    monkeypatch.setattr(macos.os.path, "isdir", lambda p: False)
    assert macos.get_available_macos_scripts() == []


# ---------------------------------------------------------------------------
# core.rbac
# ---------------------------------------------------------------------------


@pytest.fixture
def rbac_mapping(monkeypatch):
    mapping = {}
    monkeypatch.setattr(rbac, "_USER_TENANT_MAPPING", mapping)
    return mapping


def test_rbac_operations(rbac_mapping):
    assert rbac.get_user_tenant("admin") is None
    rbac.set_user_tenant("admin", "t1")
    assert rbac.get_user_tenant("admin") == "t1"
    assert rbac.get_all_user_tenants() == {"admin": "t1"}


# ---------------------------------------------------------------------------
# core.feature_flag
# ---------------------------------------------------------------------------


class _BrokenStorage:
    def load(self, *args, **kwargs):
        raise RuntimeError("boom")

    def save(self, *args, **kwargs):
        raise RuntimeError("boom")


def _flag_dict(key="flag1"):
    now = datetime.now().isoformat()
    return {
        "key": key,
        "name": "Test",
        "description": "desc",
        "flag_type": ff.FlagType.BOOLEAN.value,
        "status": ff.FlagStatus.ENABLED.value,
        "fallback_value": False,
        "rules": [],
        "created_at": now,
        "updated_at": now,
        "metadata": {},
    }


def test_flag_rule_matches():
    rule = ff.FlagRule("r", {"env": "prod"})
    assert rule.matches({"env": "prod"})
    assert not rule.matches({"env": "dev"})
    assert not rule.matches({})

    rule2 = ff.FlagRule(
        "r2",
        {
            "user": {"equals": "alice"},
            "group": {"in": ["a", "b"]},
            "email": {"contains": "@x.com"},
            "score": {"gt": 5, "lt": 100},
        },
    )
    assert rule2.matches(
        {"user": "alice", "group": "b", "email": "a@x.com", "score": 50}
    )
    assert not rule2.matches(
        {"user": "alice", "group": "b", "email": "a@x.com", "score": 101}
    )


def test_feature_flag_to_dict():
    flag = ff.FeatureFlag(
        key="f",
        name="F",
        description="",
        flag_type=ff.FlagType.BOOLEAN,
        status=ff.FlagStatus.ENABLED,
        fallback_value=False,
        rules=[ff.FlagRule("r", {"a": 1})],
        created_at=datetime.now(),
        updated_at=datetime.now(),
        metadata={},
    )
    d = flag.to_dict()
    assert d["key"] == "f"
    assert d["rules"][0]["name"] == "r"


def test_manager_lifecycle(monkeypatch):
    storage = MagicMock()
    storage.load.return_value = {"flag1": _flag_dict()}
    manager = ff.create_feature_flag_manager(storage)
    assert manager is not None
    assert manager.get_flag("flag1") is not None
    assert len(manager.list_flags()) == 1

    # initialize failure from _load_flags_from_storage raising through initialize
    manager2 = ff.FeatureFlagManager(MagicMock())

    def _boom():
        raise RuntimeError("boom")

    monkeypatch.setattr(manager2, "_load_flags_from_storage", _boom)
    assert manager2.initialize() is False


def test_manager_create_update_delete():
    manager = ff.FeatureFlagManager()
    assert manager.initialize()
    flag = manager.create_flag("f1", "Flag", "desc", ff.FlagType.BOOLEAN, fallback_value=True)
    assert flag is not None
    assert manager.create_flag("f1", "x", "x", ff.FlagType.BOOLEAN) is None

    assert manager.update_flag("f1", name="Updated")
    assert not manager.update_flag("missing", name="x")

    assert manager.add_rule("f1", ff.FlagRule("rule1", {"env": "prod"}))
    assert not manager.add_rule("missing", ff.FlagRule("r", {}))

    assert manager.remove_rule("f1", "rule1")
    assert manager.remove_rule("f1", "missing")
    assert not manager.remove_rule("missing", "rule1")

    assert manager.delete_flag("f1")
    assert not manager.delete_flag("f1")


def test_manager_evaluate_boolean():
    manager = ff.FeatureFlagManager()
    manager.initialize()
    manager.create_flag("f2", "F2", "", ff.FlagType.BOOLEAN, fallback_value=False)
    assert manager.evaluate("missing") is False
    assert manager.is_enabled("f2") is False

    manager.update_flag("f2", status=ff.FlagStatus.DISABLED)
    assert manager.is_enabled("f2") is False

    manager.update_flag("f2", status=ff.FlagStatus.ARCHIVED)
    assert manager.is_enabled("f2") is False

    manager.update_flag("f2", status=ff.FlagStatus.ENABLED, fallback_value=True)
    assert manager.is_enabled("f2") is True

    manager.add_rule("f2", ff.FlagRule("r", {"env": "prod"}))
    assert manager.is_enabled("f2", context={"env": "prod"}) is True
    assert manager.is_enabled("f2", context={"env": "dev"}) is True  # fallback True


def test_manager_evaluate_percentage():
    manager = ff.FeatureFlagManager()
    manager.initialize()
    manager.create_flag(
        "pct", "Pct", "", ff.FlagType.PERCENTAGE, fallback_value=1.0
    )
    assert manager.evaluate("pct", user_id="u1") is True

    # invalid percentage fallback
    manager.update_flag("pct", fallback_value="not a number")
    assert manager.evaluate("pct", user_id="u2") is False


def test_manager_evaluate_multivariate():
    manager = ff.FeatureFlagManager()
    manager.initialize()
    manager.create_flag(
        "mv",
        "MV",
        "",
        ff.FlagType.MULTIVARIATE,
        fallback_value="control",
        metadata={
            "variants": [
                {"value": "A", "percentage": 0.5},
                {"value": "B", "percentage": 0.5},
            ]
        },
    )
    variant = manager.get_variant("mv", user_id="u1")
    assert variant in ("A", "B", "control")

    # empty variants
    manager.update_flag("mv", metadata={"variants": []})
    assert manager.get_variant("mv", user_id="u1") == "control"


def test_manager_storage_save_errors():
    storage = MagicMock()
    storage.save.side_effect = RuntimeError("save fail")
    manager = ff.FeatureFlagManager(storage)
    manager.initialize()
    manager.create_flag("x", "X", "", ff.FlagType.BOOLEAN)
    manager.update_flag("x", name="Y")
    manager.add_rule("x", ff.FlagRule("r", {}))
    manager.remove_rule("x", "r")
    # no exceptions should propagate


def test_manager_list_by_status():
    manager = ff.FeatureFlagManager()
    manager.initialize()
    manager.create_flag("fa", "A", "", ff.FlagType.BOOLEAN)
    manager.create_flag("fb", "B", "", ff.FlagType.BOOLEAN)
    manager.update_flag("fb", status=ff.FlagStatus.DISABLED)
    enabled = manager.list_flags(status=ff.FlagStatus.ENABLED)
    assert all(f["status"] == ff.FlagStatus.ENABLED.value for f in enabled)


# ---------------------------------------------------------------------------
# core.mcp_server
# ---------------------------------------------------------------------------


@pytest.fixture
def mcp_client(monkeypatch):
    app = FastAPI()
    app.include_router(mcp_server.router)

    monkeypatch.setattr(mcp_server, "get_host_health", AsyncMock(return_value={"ok": True}))
    monkeypatch.setattr(
        mcp_server, "trigger_repair_with_hitl", AsyncMock(return_value={"id": "r1"})
    )
    monkeypatch.setattr(
        mcp_server, "search_incident_history", AsyncMock(return_value=[{"id": "i1"}])
    )
    monkeypatch.setattr(
        mcp_server, "get_metrics", AsyncMock(return_value={"cpu": 0.5})
    )
    monkeypatch.setattr(
        mcp_server, "approve_repair", AsyncMock(return_value={"approved": True})
    )
    return TestClient(app)


def test_mcp_get_host_health_success(mcp_client):
    resp = mcp_client.post("/mcp/get_host_health", json={"host_id": "h1"})
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


def test_mcp_get_host_health_error(monkeypatch, mcp_client):
    monkeypatch.setattr(
        mcp_server, "get_host_health", AsyncMock(side_effect=Exception("down"))
    )
    resp = mcp_client.post("/mcp/get_host_health", json={"host_id": "h1"})
    assert resp.status_code == 500


def test_mcp_trigger_repair_success(mcp_client):
    resp = mcp_client.post(
        "/mcp/trigger_repair_with_hitl",
        json={"alert_id": "a1", "user": "u1"},
    )
    assert resp.status_code == 200
    assert resp.json()["id"] == "r1"


def test_mcp_trigger_repair_error(monkeypatch, mcp_client):
    monkeypatch.setattr(
        mcp_server,
        "trigger_repair_with_hitl",
        AsyncMock(side_effect=Exception("fail")),
    )
    resp = mcp_client.post(
        "/mcp/trigger_repair_with_hitl",
        json={"alert_id": "a1", "user": "u1"},
    )
    assert resp.status_code == 500


def test_mcp_search_incident_success(mcp_client):
    resp = mcp_client.post("/mcp/search_incident_history", json={"query": "cpu"})
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_mcp_search_incident_error(monkeypatch, mcp_client):
    monkeypatch.setattr(
        mcp_server,
        "search_incident_history",
        AsyncMock(side_effect=Exception("fail")),
    )
    resp = mcp_client.post("/mcp/search_incident_history", json={"query": "cpu"})
    assert resp.status_code == 500


def test_mcp_get_metrics_success(mcp_client):
    resp = mcp_client.post(
        "/mcp/get_metrics",
        json={"host_id": "h1", "metrics": ["cpu"]},
    )
    assert resp.status_code == 200
    assert resp.json()["cpu"] == 0.5


def test_mcp_get_metrics_error(monkeypatch, mcp_client):
    monkeypatch.setattr(
        mcp_server, "get_metrics", AsyncMock(side_effect=Exception("fail"))
    )
    resp = mcp_client.post(
        "/mcp/get_metrics",
        json={"host_id": "h1", "metrics": ["cpu"]},
    )
    assert resp.status_code == 500


def test_mcp_approve_repair_success(mcp_client):
    resp = mcp_client.post(
        "/mcp/approve_repair",
        json={"repair_id": "r1", "approved": True},
    )
    assert resp.status_code == 200


def test_mcp_approve_repair_error(monkeypatch, mcp_client):
    monkeypatch.setattr(
        mcp_server, "approve_repair", AsyncMock(side_effect=Exception("fail"))
    )
    resp = mcp_client.post(
        "/mcp/approve_repair",
        json={"repair_id": "r1", "approved": False},
    )
    assert resp.status_code == 500
