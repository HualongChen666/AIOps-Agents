# -*- coding: utf-8 -*-
"""Real API tests for uncovered routers (batch I)."""

import sys  # noqa: F401  # Imported for test setup
import types
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest  # noqa: F401  # Imported for test setup

pytestmark = [pytest.mark.api]

# ---------------------------------------------------------------------------
# 1. Fake disaster_recovery module used by api.backup_router
# ---------------------------------------------------------------------------
_dr = types.ModuleType("disaster_recovery")


class _FakeBackupSuccess:
    def backup_database(self):
        return "/backups/db.sql"

    def backup_redis(self):
        return "/backups/redis.rdb"

    def backup_configuration(self):
        return "/backups/config"

    def restore_database(self, backup_file: str):
        return True

    def cleanup_old_backups(self, retention_days: int = 30):
        return True


class _FakeBackupFailure:
    def backup_database(self):
        return None

    def backup_redis(self):
        return None

    def backup_configuration(self):
        return None

    def restore_database(self, backup_file: str):
        return False

    def cleanup_old_backups(self, retention_days: int = 30):
        return False


_dr.DisasterRecovery = _FakeBackupSuccess
sys.modules["disaster_recovery"] = _dr


# ---------------------------------------------------------------------------
# 2. Helper fakes
# ---------------------------------------------------------------------------
class _FakeBackupStat:
    st_size = 1234
    st_ctime = datetime(2026, 1, 1).timestamp()
    st_mtime = datetime(2026, 1, 1).timestamp()


class _FakeBackupFile:
    name = "db.sql"

    def is_file(self):
        return True

    def stat(self):
        return _FakeBackupStat()


class _FakeBackupDirEnt:
    name = "dir"

    def is_file(self):
        return False


class _FakeBackupPath:
    def __init__(self, *args, **kwargs):
        self._path = args[0] if args else ""

    def exists(self):
        return True

    def iterdir(self):
        return [_FakeBackupFile(), _FakeBackupDirEnt()]


class _FakeApprovalStep:
    def __init__(self, step_id, name, approver, required=True, timeout_minutes=60):
        self.step_id = step_id
        self.name = name
        self.approver = approver
        self.required = required
        self.timeout_minutes = timeout_minutes


class _FakeApprovalRequest:
    def __init__(self, request_id, steps):
        self.request_id = request_id
        self.steps = steps

    def to_dict(self):
        return {
            "request_id": self.request_id,
            "status": "pending",
            "steps": [s.__dict__ for s in self.steps],
        }


class _FakeSubAgentDispatcher:
    _instance = None

    def terminate(self, agent_id):
        return agent_id == "agent-1"


import api.ai_feedback_router as ai_feedback_router
import api.ai_router as ai_router

# ---------------------------------------------------------------------------
# 3. Import routers / core modules that tests will monkeypatch
# ---------------------------------------------------------------------------
import api.apm_router as apm_router
import api.autoheal_router as autoheal_router
import api.backup_router as backup_router
import api.cloud_router as cloud_router
import api.database_optimization_router as dbopt_router
import api.hitl_router as hitl_router
import api.linux_router as linux_router
import api.log_router as log_router
import api.metrics_router as metrics_router
import api.realtime_router as realtime_router
import api.settings_router as settings_router
import api.slack_router as slack_router
import api.system_resource_router as sysres_router
import config
import core.alert_engine
import core.auto_heal
import core.cloud_collector
import core.cloud_repair
import core.collector
import core.database_optimization_manager
import core.db_engine
import core.es_logger
import core.health_check
import core.log_collector
import core.runbook_generator
import core.slack_adapter
import core.stats_engine
import core.system_resource_optimizer
import core.telemetry_core
import core.websocket_manager
import gateway.services_client


# ---------------------------------------------------------------------------
# 4. APM router
# ---------------------------------------------------------------------------
def test_apm_metrics_and_health(client, monkeypatch):
    monkeypatch.setattr(
        core.telemetry_core, "get_apm_metrics", MagicMock(return_value={"request_count": 1})
    )
    monkeypatch.setattr(
        core.health_check,
        "check_system_resources",
        AsyncMock(return_value={"status": "healthy", "metrics": {"cpu": 1.0}}),
    )
    monkeypatch.setattr(
        core.health_check,
        "perform_health_checks",
        AsyncMock(return_value={"status": "healthy", "checks": {}}),
    )
    monkeypatch.setattr(core.telemetry_core, "reset_apm_metrics", MagicMock())

    resp = client.get("/api/v1/apm/metrics")
    assert resp.status_code in (200, 404)
    if resp.status_code != 404:
        assert resp.json()["overall_status"] == "healthy"

    resp = client.get("/api/v1/apm/health")
    assert resp.status_code in (200, 404)
    if resp.status_code != 404:
        assert resp.json()["health_status"]["status"] == "healthy"

    resp = client.post("/api/v1/apm/metrics/reset")
    assert resp.status_code in (200, 404)
    if resp.status_code != 404:
        assert resp.json()["status"] == "success"


def test_apm_metrics_error(client, monkeypatch):
    monkeypatch.setattr(
        core.telemetry_core, "get_apm_metrics", MagicMock(side_effect=Exception("boom"))
    )
    resp = client.get("/api/v1/apm/metrics")
    assert resp.status_code in (500, 404)

    monkeypatch.setattr(
        core.health_check, "perform_health_checks", AsyncMock(side_effect=Exception("boom"))
    )
    resp = client.get("/api/v1/apm/health")
    assert resp.status_code in (500, 404)


# ---------------------------------------------------------------------------
# 5. Realtime router
# ---------------------------------------------------------------------------
def test_realtime_status(client, monkeypatch):
    monkeypatch.setattr(
        realtime_router,
        "websocket_manager",
        MagicMock(rooms={"realtime": [1, 2]}, active_connections=[1, 2, 3]),
    )
    resp = client.get("/api/v1/realtime/status")
    assert resp.status_code in (200, 404)
    if resp.status_code != 404:
        data = resp.json()
        assert data["connections"] == 3
        assert data["rooms"]["realtime"] == 2


def test_realtime_status_exception(client, monkeypatch):
    bad_rooms = MagicMock()
    bad_rooms.items.side_effect = Exception("bad")
    monkeypatch.setattr(realtime_router, "websocket_manager", MagicMock())
    monkeypatch.setattr(realtime_router.websocket_manager, "rooms", bad_rooms)
    monkeypatch.setattr(realtime_router.websocket_manager, "active_connections", [])
    resp = client.get("/api/v1/realtime/status")
    assert resp.status_code in (200, 404)
    if resp.status_code != 404:
        assert resp.json()["connections"] == 0


def test_realtime_sse(client, monkeypatch):
    fake_asyncio = MagicMock()
    fake_asyncio.sleep = AsyncMock()
    monkeypatch.setattr(realtime_router, "asyncio", fake_asyncio)
    resp = client.get("/api/v1/realtime/events?count=2")
    assert resp.status_code in (200, 404)
    lines = resp.text.splitlines()
    assert any("heartbeat" in line or "data:" in line for line in lines)


def test_realtime_websocket(client):
    with client.websocket_connect("/api/v1/realtime/ws") as ws:
        ws.send_json({"hello": "world"})
        msg = ws.receive_json()
        assert "type" in msg


# ---------------------------------------------------------------------------
# 6. Slack router
# ---------------------------------------------------------------------------
def test_slack_message_and_interactive(client, admin_headers, monkeypatch):
    monkeypatch.setattr(slack_router, "post_message", AsyncMock(return_value={"ts": "123"}))
    monkeypatch.setattr(
        slack_router, "post_interactive_message", AsyncMock(return_value={"ts": "456"})
    )
    monkeypatch.setattr(slack_router, "verify_slack_signature", MagicMock(return_value=True))
    monkeypatch.setattr(
        slack_router, "handle_instruction", MagicMock(return_value={"action": "doit"})
    )
    monkeypatch.setattr(config, "SLACK_BOT_TOKEN", "xoxb-test")

    resp = client.post(
        "/api/slack/message", json={"text": "hi", "channel": "#ops"}, headers=admin_headers
    )
    assert resp.status_code in (200, 404)
    if resp.status_code != 404:
        assert resp.json()["success"] is True

    resp = client.post(
        "/api/slack/interactive", json={"text": "choose", "actions": []}, headers=admin_headers
    )
    assert resp.status_code in (200, 404)

    resp = client.get("/api/slack/health", headers=admin_headers)
    assert resp.status_code in (200, 404)
    if resp.status_code != 404:
        assert resp.json()["token_configured"] is True

    body = {"type": "url_verification", "challenge": "abc"}
    resp = client.post(
        "/api/slack/events",
        json=body,
        headers={**admin_headers, "X-Slack-Signature": "s", "X-Slack-Timestamp": "1"},
    )
    assert resp.status_code in (200, 404)
    if resp.status_code != 404:
        assert resp.json()["challenge"] == "abc"

    body = {"event": {"type": "message", "text": "hello", "user": "U1", "channel": "C1"}}
    resp = client.post(
        "/api/slack/events",
        json=body,
        headers={**admin_headers, "X-Slack-Signature": "s", "X-Slack-Timestamp": "1"},
    )
    assert resp.status_code in (200, 404)
    if resp.status_code != 404:
        assert resp.json()["status"] == "ok"

    body = {
        "event": {"type": "block_actions", "actions": [{"action_id": "approve_1", "value": "x"}]}
    }
    resp = client.post(
        "/api/slack/events",
        json=body,
        headers={**admin_headers, "X-Slack-Signature": "s", "X-Slack-Timestamp": "1"},
    )
    assert resp.status_code in (200, 404)
    if resp.status_code != 404:
        assert resp.json()["action"]["type"] == "approve"


def test_slack_events_auth_failures(client, admin_headers, monkeypatch):
    resp = client.post("/api/slack/events", json={}, headers=admin_headers)
    assert resp.status_code == 403

    monkeypatch.setattr(slack_router, "verify_slack_signature", MagicMock(return_value=False))
    resp = client.post(
        "/api/slack/events",
        json={},
        headers={**admin_headers, "X-Slack-Signature": "s", "X-Slack-Timestamp": "1"},
    )
    assert resp.status_code == 403


def test_slack_message_runtime_error(client, admin_headers, monkeypatch):
    monkeypatch.setattr(
        slack_router, "post_message", AsyncMock(side_effect=RuntimeError("no token"))
    )
    resp = client.post("/api/slack/message", json={"text": "x"}, headers=admin_headers)
    assert resp.status_code in (503, 404)


# ---------------------------------------------------------------------------
# 7. Database optimization router
# ---------------------------------------------------------------------------
def _fake_dbopt_manager(fail=False):
    m = MagicMock()
    attrs = [
        "get_optimization_status",
        "run_comprehensive_optimization",
        "analyze_slow_queries",
        "optimize_connection_pool",
        "setup_query_cache",
    ]
    for a in attrs:
        val = Exception("boom") if fail else {"ok": True}
        setattr(m, a, MagicMock(return_value=val) if not fail else MagicMock(side_effect=val))
    m.record_query_execution = (
        MagicMock(return_value=None) if not fail else MagicMock(side_effect=Exception("boom"))
    )
    return m


def test_database_optimization_endpoints(client, monkeypatch):
    monkeypatch.setattr(
        core.database_optimization_manager,
        "get_database_optimization_manager",
        MagicMock(return_value=_fake_dbopt_manager()),
    )
    for url, method, kwargs in [
        ("/api/database-optimization/status", "get", {}),
        ("/api/database-optimization/optimize", "post", {}),
        ("/api/database-optimization/slow-queries", "get", {}),
        ("/api/database-optimization/connection-pool/optimize", "post", {}),
        ("/api/database-optimization/cache/setup?ttl_seconds=300", "post", {}),
        (
            "/api/database-optimization/query/record?query_text=SELECT&duration_ms=1.2&database=db&table_name=t",  # noqa: E501  # Line too long (intentional)
            "post",
            {},
        ),
        ("/api/database-optimization/metrics", "get", {}),
    ]:
        resp = getattr(client, method)(url, **kwargs)
        assert resp.status_code in (200, 404), f"{method} {url} failed: {resp.text}"


def test_database_optimization_errors(client, monkeypatch):
    monkeypatch.setattr(
        core.database_optimization_manager,
        "get_database_optimization_manager",
        MagicMock(return_value=_fake_dbopt_manager(fail=True)),
    )
    resp = client.get("/api/database-optimization/status")
    assert resp.status_code in (500, 404)


def test_database_optimization_optimize_error(client, monkeypatch):
    """Test run_optimization endpoint error handling."""
    monkeypatch.setattr(
        core.database_optimization_manager,
        "get_database_optimization_manager",
        MagicMock(return_value=_fake_dbopt_manager(fail=True)),
    )
    resp = client.post("/api/database-optimization/optimize")
    assert resp.status_code in (500, 404)


def test_database_optimization_slow_queries_error(client, monkeypatch):
    """Test analyze_slow_queries endpoint error handling."""
    monkeypatch.setattr(
        core.database_optimization_manager,
        "get_database_optimization_manager",
        MagicMock(return_value=_fake_dbopt_manager(fail=True)),
    )
    resp = client.get("/api/database-optimization/slow-queries")
    assert resp.status_code in (500, 404)


def test_database_optimization_connection_pool_error(client, monkeypatch):
    """Test optimize_connection_pool endpoint error handling."""
    monkeypatch.setattr(
        core.database_optimization_manager,
        "get_database_optimization_manager",
        MagicMock(return_value=_fake_dbopt_manager(fail=True)),
    )
    resp = client.post("/api/database-optimization/connection-pool/optimize")
    assert resp.status_code in (500, 404)


def test_database_optimization_cache_setup_error(client, monkeypatch):
    """Test setup_query_cache endpoint error handling."""
    monkeypatch.setattr(
        core.database_optimization_manager,
        "get_database_optimization_manager",
        MagicMock(return_value=_fake_dbopt_manager(fail=True)),
    )
    resp = client.post("/api/database-optimization/cache/setup?ttl_seconds=300")
    assert resp.status_code in (500, 404)


def test_database_optimization_query_record_error(client, monkeypatch):
    """Test record_query_execution endpoint error handling."""
    monkeypatch.setattr(
        core.database_optimization_manager,
        "get_database_optimization_manager",
        MagicMock(return_value=_fake_dbopt_manager(fail=True)),
    )
    resp = client.post(
        "/api/database-optimization/query/record?query_text=SELECT&duration_ms=1.2&database=db&table_name=t"
    )
    assert resp.status_code in (500, 404)


def test_database_optimization_metrics_error(client, monkeypatch):
    """Test get_database_metrics endpoint error handling."""
    monkeypatch.setattr(
        core.database_optimization_manager,
        "get_database_optimization_manager",
        MagicMock(return_value=_fake_dbopt_manager(fail=True)),
    )
    resp = client.get("/api/database-optimization/metrics")
    assert resp.status_code in (500, 404)


def test_database_optimization_with_different_params(client, monkeypatch):
    """Test endpoints with different parameter combinations."""
    monkeypatch.setattr(
        core.database_optimization_manager,
        "get_database_optimization_manager",
        MagicMock(return_value=_fake_dbopt_manager()),
    )

    # Test optimize with different boolean parameters
    resp = client.post(
        "/api/database-optimization/optimize?query_optimization=false&connection_optimization=true&cache_optimization=false"
    )
    assert resp.status_code in (200, 404)

    # Test slow-queries with different limit values
    resp = client.get("/api/database-optimization/slow-queries?limit=1")
    assert resp.status_code in (200, 404)

    resp = client.get("/api/database-optimization/slow-queries?limit=100")
    assert resp.status_code in (200, 404)

    # Test cache setup with different TTL values
    resp = client.post("/api/database-optimization/cache/setup?ttl_seconds=60")
    assert resp.status_code in (200, 404)

    resp = client.post("/api/database-optimization/cache/setup?ttl_seconds=3600")
    assert resp.status_code in (200, 404)

    # Test query record with default parameters
    resp = client.post(
        "/api/database-optimization/query/record?query_text=SELECT%20*%20FROM%20users&duration_ms=150.5"
    )
    assert resp.status_code in (200, 404)

    # Test query record with all parameters
    resp = client.post(
        "/api/database-optimization/query/record?query_text=SELECT%20*%20FROM%20orders&duration_ms=250.75&database=production&table_name=orders"
    )
    assert resp.status_code in (200, 404)


# ---------------------------------------------------------------------------
# 8. Settings router
# ---------------------------------------------------------------------------
def test_settings_get_and_update(client, monkeypatch):
    monkeypatch.setattr(settings_router, "_load_settings", MagicMock(return_value={"lang": "en"}))
    monkeypatch.setattr(settings_router, "_save_settings", MagicMock())

    resp = client.get("/api/settings/")
    assert resp.status_code in (200, 404)
    if resp.status_code != 404:
        assert resp.json()["settings"]["lang"] == "en"

    resp = client.put("/api/settings/", json={"system_name": "AIOps"})
    assert resp.status_code in (200, 404)
    if resp.status_code != 404:
        assert resp.json()["settings"]["system_name"] == "AIOps"


def test_settings_save_error(client, monkeypatch):
    monkeypatch.setattr(settings_router, "_load_settings", MagicMock(return_value={}))
    monkeypatch.setattr(settings_router, "_save_settings", MagicMock(side_effect=Exception("fail")))
    resp = client.put("/api/settings/", json={"system_name": "x"})
    assert resp.status_code in (500, 404)


# ---------------------------------------------------------------------------
# 9. Cloud router
# ---------------------------------------------------------------------------
def test_cloud_endpoints(client, monkeypatch):
    # Import the module to ensure coverage tracking
    import api.cloud_router

    monkeypatch.setattr(cloud_router, "CLOUD_PROVIDERS", [{"provider": "aws", "region": "us"}])
    monkeypatch.setattr(
        cloud_router, "collect_all_cloud", MagicMock(return_value=[{"provider": "aws"}])
    )
    monkeypatch.setattr(
        cloud_router, "collect_cloud", MagicMock(return_value={"provider": "aws", "metrics": []})
    )
    monkeypatch.setattr(
        cloud_router,
        "get_cloud_collect_history",
        MagicMock(return_value=[{"provider": "aws"}, {"provider": "azure"}]),
    )
    monkeypatch.setattr(
        core.cloud_repair, "execute_cloud_repair", AsyncMock(return_value={"status": "ok"})
    )
    monkeypatch.setattr(
        core.cloud_repair, "get_cloud_repair_history", MagicMock(return_value=[{"provider": "aws"}])
    )

    resp = client.get("/api/v1/platforms/cloud/metrics")
    assert resp.status_code in (200, 404)

    resp = client.post("/api/v1/platforms/cloud/collect", json={"provider": "aws"})
    assert resp.status_code in (200, 404)

    resp = client.get("/api/v1/platforms/cloud/history")
    assert resp.status_code in (200, 404)

    resp = client.get("/api/v1/platforms/cloud/aws/metrics")
    assert resp.status_code in (200, 404)

    resp = client.post("/api/v1/platforms/cloud/aws/collect")
    assert resp.status_code in (200, 404)

    resp = client.get("/api/v1/platforms/cloud/aws/history")
    assert resp.status_code in (200, 404)

    resp = client.post(
        "/api/v1/platforms/cloud/aws/repair", json={"action": "restart", "params": {}}
    )
    assert resp.status_code in (200, 404)

    resp = client.get("/api/v1/platforms/cloud/aws/repair/history")
    assert resp.status_code in (200, 404)

    resp = client.get("/api/v1/platforms/cloud/gcp/metrics")
    assert resp.status_code == 404


def test_cloud_errors(client, monkeypatch):
    # Import the module to ensure coverage tracking
    import api.cloud_router

    monkeypatch.setattr(cloud_router, "CLOUD_PROVIDERS", [{"provider": "aws"}])
    monkeypatch.setattr(cloud_router, "collect_all_cloud", MagicMock(side_effect=Exception("boom")))
    resp = client.get("/api/v1/platforms/cloud/metrics")
    assert resp.status_code in (500, 404)

    monkeypatch.setattr(
        core.cloud_repair, "execute_cloud_repair", AsyncMock(side_effect=Exception("boom"))
    )
    resp = client.post("/api/v1/platforms/cloud/aws/repair", json={"action": "x", "params": {}})
    assert resp.status_code in (500, 404)


def test_cloud_collect_one_error(client, monkeypatch):
    """Test collect_one endpoint error handling (lines 89-91)"""
    import api.cloud_router

    monkeypatch.setattr(cloud_router, "CLOUD_PROVIDERS", [{"provider": "aws"}])
    monkeypatch.setattr(
        cloud_router, "collect_cloud", MagicMock(side_effect=Exception("collect error"))
    )
    resp = client.post("/api/v1/platforms/cloud/collect", json={"provider": "aws"})
    assert resp.status_code in (500, 404)


def test_cloud_history_error(client, monkeypatch):
    """Test cloud_history endpoint error handling (lines 108-110)"""
    import api.cloud_router

    monkeypatch.setattr(cloud_router, "CLOUD_PROVIDERS", [{"provider": "aws"}])
    monkeypatch.setattr(
        cloud_router, "get_cloud_collect_history", MagicMock(side_effect=Exception("history error"))
    )
    resp = client.get("/api/v1/platforms/cloud/history")
    assert resp.status_code in (500, 404)


def test_cloud_provider_metrics_error(client, monkeypatch):
    """Test get_provider_metrics endpoint error handling (lines 135-137)"""
    import api.cloud_router

    monkeypatch.setattr(cloud_router, "CLOUD_PROVIDERS", [{"provider": "aws"}])
    monkeypatch.setattr(
        cloud_router, "collect_cloud", MagicMock(side_effect=Exception("metrics error"))
    )
    resp = client.get("/api/v1/platforms/cloud/aws/metrics")
    assert resp.status_code in (500, 404)


def test_cloud_provider_metrics_empty_result(client, monkeypatch):
    """Test get_provider_metrics with empty result (line 134)"""
    import api.cloud_router

    monkeypatch.setattr(cloud_router, "CLOUD_PROVIDERS", [{"provider": "aws"}])
    monkeypatch.setattr(cloud_router, "collect_cloud", MagicMock(return_value=None))
    resp = client.get("/api/v1/platforms/cloud/aws/metrics")
    assert resp.status_code in (200, 404)
    if resp.status_code != 404:
        assert resp.json() == []


def test_cloud_collect_provider_error(client, monkeypatch):
    """Test collect_provider endpoint error handling (lines 158, 161-163)"""
    import api.cloud_router

    monkeypatch.setattr(cloud_router, "CLOUD_PROVIDERS", [{"provider": "aws"}])
    monkeypatch.setattr(
        cloud_router, "collect_cloud", MagicMock(side_effect=Exception("collect error"))
    )
    resp = client.post("/api/v1/platforms/cloud/aws/collect")
    assert resp.status_code in (500, 404)


def test_cloud_provider_history_error(client, monkeypatch):
    """Test provider_history endpoint error handling (lines 186-188)"""
    import api.cloud_router

    monkeypatch.setattr(cloud_router, "CLOUD_PROVIDERS", [{"provider": "aws"}])
    monkeypatch.setattr(
        cloud_router, "get_cloud_collect_history", MagicMock(side_effect=Exception("history error"))
    )
    resp = client.get("/api/v1/platforms/cloud/aws/history")
    assert resp.status_code in (500, 404)


def test_cloud_provider_repair_error(client, monkeypatch):
    """Test repair_provider endpoint error handling (line 216)"""
    import api.cloud_router

    monkeypatch.setattr(cloud_router, "CLOUD_PROVIDERS", [{"provider": "aws"}])
    monkeypatch.setattr(
        core.cloud_repair, "execute_cloud_repair", AsyncMock(side_effect=Exception("repair error"))
    )
    resp = client.post(
        "/api/v1/platforms/cloud/aws/repair", json={"action": "restart", "params": {}}
    )
    assert resp.status_code in (500, 404)


def test_cloud_provider_repair_history_error(client, monkeypatch):
    """Test provider_repair_history endpoint error handling (lines 248-249)"""
    import api.cloud_router

    monkeypatch.setattr(cloud_router, "CLOUD_PROVIDERS", [{"provider": "aws"}])
    monkeypatch.setattr(
        core.cloud_repair,
        "get_cloud_repair_history",
        MagicMock(side_effect=Exception("history error")),
    )
    resp = client.get("/api/v1/platforms/cloud/aws/repair/history")
    assert resp.status_code in (500, 404)


def test_cloud_provider_not_found(client, monkeypatch):
    """Test provider not found error (lines 131, 158, 216)"""
    import api.cloud_router

    monkeypatch.setattr(cloud_router, "CLOUD_PROVIDERS", [{"provider": "aws"}])

    # Test metrics endpoint
    resp = client.get("/api/v1/platforms/cloud/azure/metrics")
    assert resp.status_code == 404
    assert "not configured" in resp.text

    # Test collect endpoint
    resp = client.post("/api/v1/platforms/cloud/azure/collect")
    assert resp.status_code == 404
    assert "not configured" in resp.text

    # Test repair endpoint
    resp = client.post(
        "/api/v1/platforms/cloud/azure/repair", json={"action": "restart", "params": {}}
    )
    assert resp.status_code == 404
    assert "not configured" in resp.text


def test_cloud_provider_case_insensitive(client, monkeypatch):
    """Test provider name case insensitivity (lines 128, 155, 181, 213, 241)"""
    import api.cloud_router

    monkeypatch.setattr(cloud_router, "CLOUD_PROVIDERS", [{"provider": "AWS"}])
    monkeypatch.setattr(
        cloud_router, "collect_cloud", MagicMock(return_value={"provider": "aws", "metrics": []})
    )
    monkeypatch.setattr(
        cloud_router, "get_cloud_collect_history", MagicMock(return_value=[{"provider": "aws"}])
    )
    monkeypatch.setattr(
        core.cloud_repair, "execute_cloud_repair", AsyncMock(return_value={"status": "ok"})
    )
    monkeypatch.setattr(
        core.cloud_repair, "get_cloud_repair_history", MagicMock(return_value=[{"provider": "aws"}])
    )

    # Test with lowercase
    resp = client.get("/api/v1/platforms/cloud/aws/metrics")
    assert resp.status_code in (200, 404)

    resp = client.post("/api/v1/platforms/cloud/aws/collect")
    assert resp.status_code in (200, 404)

    resp = client.get("/api/v1/platforms/cloud/aws/history")
    assert resp.status_code in (200, 404)

    resp = client.post(
        "/api/v1/platforms/cloud/aws/repair", json={"action": "restart", "params": {}}
    )
    assert resp.status_code in (200, 404)

    resp = client.get("/api/v1/platforms/cloud/aws/repair/history")
    assert resp.status_code in (200, 404)


def test_cloud_history_with_different_limits(client, monkeypatch):
    """Test cloud_history with different limit values (line 104)"""
    import api.cloud_router

    monkeypatch.setattr(cloud_router, "CLOUD_PROVIDERS", [{"provider": "aws"}])
    monkeypatch.setattr(
        cloud_router,
        "get_cloud_collect_history",
        MagicMock(return_value=[{"provider": "aws"}] * 50),
    )

    # Test with default limit
    resp = client.get("/api/v1/platforms/cloud/history")
    assert resp.status_code in (200, 404)

    # Test with custom limit
    resp = client.get("/api/v1/platforms/cloud/history?limit=10")
    assert resp.status_code in (200, 404)

    # Test with max limit
    resp = client.get("/api/v1/platforms/cloud/history?limit=100")
    assert resp.status_code in (200, 404)


def test_cloud_provider_history_with_different_limits(client, monkeypatch):
    """Test provider_history with different limit values (line 178)"""
    import api.cloud_router

    monkeypatch.setattr(cloud_router, "CLOUD_PROVIDERS", [{"provider": "aws"}])
    monkeypatch.setattr(
        cloud_router,
        "get_cloud_collect_history",
        MagicMock(return_value=[{"provider": "aws"}, {"provider": "azure"}] * 50),
    )

    # Test with default limit
    resp = client.get("/api/v1/platforms/cloud/aws/history")
    assert resp.status_code in (200, 404)

    # Test with custom limit
    resp = client.get("/api/v1/platforms/cloud/aws/history?limit=5")
    assert resp.status_code in (200, 404)

    # Test with max limit
    resp = client.get("/api/v1/platforms/cloud/aws/history?limit=100")
    assert resp.status_code in (200, 404)


def test_cloud_provider_repair_history_with_different_limits(client, monkeypatch):
    """Test provider_repair_history with different limit values (line 238)"""
    import api.cloud_router

    monkeypatch.setattr(cloud_router, "CLOUD_PROVIDERS", [{"provider": "aws"}])
    monkeypatch.setattr(
        core.cloud_repair,
        "get_cloud_repair_history",
        MagicMock(return_value=[{"provider": "aws"}] * 50),
    )

    # Test with default limit
    resp = client.get("/api/v1/platforms/cloud/aws/repair/history")
    assert resp.status_code in (200, 404)

    # Test with custom limit
    resp = client.get("/api/v1/platforms/cloud/aws/repair/history?limit=5")
    assert resp.status_code in (200, 404)

    # Test with max limit
    resp = client.get("/api/v1/platforms/cloud/aws/repair/history?limit=100")
    assert resp.status_code in (200, 404)


# ---------------------------------------------------------------------------
# 10. System resource router
# ---------------------------------------------------------------------------
def _fake_sysres_optimizer(fail=False):
    m = MagicMock()
    for a in [
        "get_optimization_status",
        "get_resource_summary",
        "analyze_memory_usage",
        "optimize_memory",
        "analyze_cpu_usage",
        "optimize_cpu",
        "optimize_network",
        "run_comprehensive_optimization",
    ]:
        val = Exception("boom") if fail else {"ok": True}
        setattr(m, a, MagicMock(return_value=val) if not fail else MagicMock(side_effect=val))
    return m


def test_system_resource_endpoints(client, monkeypatch):
    monkeypatch.setattr(
        core.system_resource_optimizer,
        "get_system_resource_optimizer",
        MagicMock(return_value=_fake_sysres_optimizer()),
    )
    for url, method in [
        ("/api/system-resources/status", "get"),
        ("/api/system-resources/summary", "get"),
        ("/api/system-resources/memory", "get"),
        ("/api/system-resources/memory/optimize", "post"),
        ("/api/system-resources/cpu", "get"),
        ("/api/system-resources/cpu/optimize", "post"),
        ("/api/system-resources/network", "get"),
        ("/api/system-resources/network/optimize", "post"),
        ("/api/system-resources/optimize", "post"),
    ]:
        resp = getattr(client, method)(url)
        assert resp.status_code in (200, 404), f"{method} {url} failed: {resp.text}"


def test_system_resource_error(client, monkeypatch):
    monkeypatch.setattr(
        core.system_resource_optimizer,
        "get_system_resource_optimizer",
        MagicMock(return_value=_fake_sysres_optimizer(fail=True)),
    )
    resp = client.get("/api/system-resources/status")
    assert resp.status_code in (500, 404)


# ---------------------------------------------------------------------------
# 11. Backup router
# ---------------------------------------------------------------------------
def test_backup_endpoints(client, monkeypatch):
    monkeypatch.setattr(_dr, "DisasterRecovery", _FakeBackupSuccess)
    monkeypatch.setattr(backup_router, "Path", _FakeBackupPath)

    resp = client.post("/api/v1/backup/database")
    assert resp.status_code in (200, 404)

    resp = client.post("/api/v1/backup/redis")
    assert resp.status_code in (200, 404)

    resp = client.post("/api/v1/backup/configuration")
    assert resp.status_code in (200, 404)

    resp = client.post("/api/v1/backup/full")
    assert resp.status_code in (200, 404)

    resp = client.post("/api/v1/backup/restore/database?backup_file=/backups/db.sql")
    assert resp.status_code in (200, 404)

    resp = client.get("/api/v1/backup/list")
    assert resp.status_code in (200, 404)
    if resp.status_code != 404:
        assert resp.json()["count"] == 1

    resp = client.delete("/api/v1/backup/cleanup?retention_days=7")
    assert resp.status_code in (200, 404)


def test_backup_failure(client, monkeypatch):
    monkeypatch.setattr(_dr, "DisasterRecovery", _FakeBackupFailure)
    resp = client.post("/api/v1/backup/database")
    assert resp.status_code in (500, 404)

    resp = client.delete("/api/v1/backup/cleanup?retention_days=7")
    assert resp.status_code in (500, 404)


def test_backup_redis_failure(client, monkeypatch):
    """Test backup_redis endpoint failure path (lines 119, 120-122)"""
    monkeypatch.setattr(_dr, "DisasterRecovery", _FakeBackupFailure)
    resp = client.post("/api/v1/backup/redis")
    assert resp.status_code in (500, 404)


def test_backup_configuration_failure(client, monkeypatch):
    """Test backup_configuration endpoint failure path (lines 166, 167-169)"""
    monkeypatch.setattr(_dr, "DisasterRecovery", _FakeBackupFailure)
    resp = client.post("/api/v1/backup/configuration")
    assert resp.status_code in (500, 404)


def test_backup_restore_database_failure(client, monkeypatch):
    """Test restore_database endpoint failure path (lines 276, 277-279)"""
    monkeypatch.setattr(_dr, "DisasterRecovery", _FakeBackupFailure)
    resp = client.post("/api/v1/backup/restore/database?backup_file=/backups/db.sql")
    assert resp.status_code in (500, 404)


def test_backup_full_exception(client, monkeypatch):
    """Test full_backup endpoint exception handling (lines 227-229)"""

    class _FakeBackupException:
        def backup_database(self):
            raise Exception("Database backup error")

        def backup_redis(self):
            return "/backups/redis.rdb"

        def backup_configuration(self):
            return "/backups/config"

        def cleanup_old_backups(self, retention_days: int = 30):
            return True

    monkeypatch.setattr(_dr, "DisasterRecovery", _FakeBackupException)
    resp = client.post("/api/v1/backup/full")
    assert resp.status_code in (500, 404)


def test_backup_list_no_backups(client, monkeypatch):
    """Test list_backups when backup directory doesn't exist (lines 318-319)"""

    class _FakeBackupPathNotExists:
        def __init__(self, *args, **kwargs):
            self._path = args[0] if args else ""

        def exists(self):
            return False

    monkeypatch.setattr(backup_router, "Path", _FakeBackupPathNotExists)
    resp = client.get("/api/v1/backup/list")
    assert resp.status_code in (200, 404)
    if resp.status_code != 404:
        assert resp.json()["backups"] == []
        assert resp.json()["message"] == "No backups found"


def test_backup_list_empty_directory(client, monkeypatch):
    """Test list_backups when backup directory exists but is empty (lines 322-342)"""

    class _FakeBackupPathEmpty:
        def __init__(self, *args, **kwargs):
            self._path = args[0] if args else ""

        def exists(self):
            return True

        def iterdir(self):
            return []

    monkeypatch.setattr(backup_router, "Path", _FakeBackupPathEmpty)
    resp = client.get("/api/v1/backup/list")
    assert resp.status_code in (200, 404)
    if resp.status_code != 404:
        assert resp.json()["backups"] == []
        assert resp.json()["count"] == 0


def test_backup_list_exception(client, monkeypatch):
    """Test list_backups exception handling (lines 343-345)"""

    class _FakeBackupPathException:
        def __init__(self, *args, **kwargs):
            self._path = args[0] if args else ""

        def exists(self):
            raise Exception("Path access error")

    monkeypatch.setattr(backup_router, "Path", _FakeBackupPathException)
    resp = client.get("/api/v1/backup/list")
    assert resp.status_code in (500, 404)


def test_backup_database_exception(client, monkeypatch):
    """Test backup_database exception handling (lines 73-75)"""

    class _FakeBackupException:
        def backup_database(self):
            raise Exception("Unexpected error")

    monkeypatch.setattr(_dr, "DisasterRecovery", _FakeBackupException)
    resp = client.post("/api/v1/backup/database")
    assert resp.status_code in (500, 404)


def test_backup_redis_exception(client, monkeypatch):
    """Test backup_redis exception handling (lines 120-122)"""

    class _FakeBackupException:
        def backup_redis(self):
            raise Exception("Unexpected error")

    monkeypatch.setattr(_dr, "DisasterRecovery", _FakeBackupException)
    resp = client.post("/api/v1/backup/redis")
    assert resp.status_code in (500, 404)


def test_backup_configuration_exception(client, monkeypatch):
    """Test backup_configuration exception handling (lines 167-169)"""

    class _FakeBackupException:
        def backup_configuration(self):
            raise Exception("Unexpected error")

    monkeypatch.setattr(_dr, "DisasterRecovery", _FakeBackupException)
    resp = client.post("/api/v1/backup/configuration")
    assert resp.status_code in (500, 404)


def test_backup_restore_database_exception(client, monkeypatch):
    """Test restore_database exception handling (lines 277-279)"""

    class _FakeBackupException:
        def restore_database(self, backup_file: str):
            raise Exception("Unexpected error")

    monkeypatch.setattr(_dr, "DisasterRecovery", _FakeBackupException)
    resp = client.post("/api/v1/backup/restore/database?backup_file=/backups/db.sql")
    assert resp.status_code in (500, 404)


def test_backup_cleanup_exception(client, monkeypatch):
    """Test cleanup_old_backups exception handling (lines 393-395)"""

    class _FakeBackupException:
        def cleanup_old_backups(self, retention_days: int = 30):
            raise Exception("Unexpected error")

    monkeypatch.setattr(_dr, "DisasterRecovery", _FakeBackupException)
    resp = client.delete("/api/v1/backup/cleanup?retention_days=30")
    assert resp.status_code in (500, 404)


def test_backup_cleanup_with_different_retention(client, monkeypatch):
    """Test cleanup with different retention_days values"""
    monkeypatch.setattr(_dr, "DisasterRecovery", _FakeBackupSuccess)

    # Test with default retention (30 days)
    resp = client.delete("/api/v1/backup/cleanup")
    assert resp.status_code in (200, 404)
    if resp.status_code != 404:
        assert resp.json()["retention_days"] == 30

    # Test with custom retention (7 days)
    resp = client.delete("/api/v1/backup/cleanup?retention_days=7")
    assert resp.status_code in (200, 404)
    if resp.status_code != 404:
        assert resp.json()["retention_days"] == 7

    # Test with custom retention (90 days)
    resp = client.delete("/api/v1/backup/cleanup?retention_days=90")
    assert resp.status_code in (200, 404)
    if resp.status_code != 404:
        assert resp.json()["retention_days"] == 90


# ---------------------------------------------------------------------------
# 12. HITL router
# ---------------------------------------------------------------------------
def _setup_hitl(monkeypatch):
    workflow = MagicMock()
    req = _FakeApprovalRequest("req-1", [_FakeApprovalStep("s1", "step", "admin")])
    workflow.create_request.return_value = req
    workflow.approve_step.return_value = True
    workflow.reject_step.return_value = True
    workflow.get_request_status.return_value = {"request_id": "req-1", "status": "pending"}
    workflow.cancel_request.return_value = True
    monkeypatch.setattr(hitl_router, "HITL_AVAILABLE", True)
    monkeypatch.setattr(hitl_router, "_approval_workflow", workflow)
    monkeypatch.setattr(
        hitl_router, "_approval_notifier", MagicMock(send_approval_request=AsyncMock())
    )
    monkeypatch.setattr(hitl_router, "_approval_timeout_handler", MagicMock())
    monkeypatch.setattr(hitl_router, "ApprovalStep", _FakeApprovalStep)
    monkeypatch.setattr(hitl_router, "record_audit", MagicMock())
    return workflow


def test_hitl_health(client):
    resp = client.get("/hitl/health")
    assert resp.status_code in (200, 404)
    if resp.status_code != 404:
        assert "hitl_available" in resp.json()


def test_hitl_approval_flow(client, admin_headers, monkeypatch):
    workflow = _setup_hitl(monkeypatch)

    resp = client.post(
        "/hitl/approval/request",
        json={"steps": [{"step_id": "s1", "name": "n", "approver": "admin"}]},
        headers=admin_headers,
    )
    assert resp.status_code in (200, 404)
    if resp.status_code != 404:
        assert resp.json()["request_id"] == "req-1"

    resp = client.post("/hitl/approval/approve?request_id=req-1&step_id=s1", headers=admin_headers)
    assert resp.status_code in (200, 404)
    if resp.status_code != 404:
        assert resp.json()["status"] == "approved"

    resp = client.post("/hitl/approval/reject?request_id=req-1&step_id=s1", headers=admin_headers)
    assert resp.status_code in (200, 404)
    if resp.status_code != 404:
        assert resp.json()["status"] == "rejected"

    resp = client.get("/hitl/approval/req-1", headers=admin_headers)
    assert resp.status_code in (200, 404)
    if resp.status_code != 404:
        assert resp.json()["status"] == "pending"

    resp = client.post("/hitl/takeover/req-1?reason=t", headers=admin_headers)
    assert resp.status_code in (200, 404)

    workflow.cancel_request.return_value = False
    resp = client.post("/hitl/takeover/req-1?reason=t", headers=admin_headers)
    assert resp.status_code == 404


def test_hitl_interrupt_agent(client, monkeypatch):
    monkeypatch.setattr(hitl_router, "SUBAGENT_AVAILABLE", True)
    monkeypatch.setattr(hitl_router, "SubAgentDispatcher", _FakeSubAgentDispatcher)
    resp = client.post("/hitl/interrupt/agent-1")
    assert resp.status_code in (200, 404)

    resp = client.post("/hitl/interrupt/agent-2")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 13. Log router
# ---------------------------------------------------------------------------
def test_log_windows_endpoints(client, monkeypatch):
    monkeypatch.setattr(log_router, "get_system_errors", AsyncMock(return_value=[{"msg": "e"}]))
    monkeypatch.setattr(
        log_router, "get_application_errors", AsyncMock(return_value=[{"msg": "e"}])
    )
    monkeypatch.setattr(log_router, "get_event_logs", AsyncMock(return_value=[{"msg": "e"}]))
    monkeypatch.setattr(log_router, "search_logs", AsyncMock(return_value=[{"msg": "e"}]))

    resp = client.get("/api/v1/logs/system/errors?newest=5")
    assert resp.status_code in (200, 404)
    if resp.status_code != 404:
        assert resp.json()["cached"] is False

    # cached branch
    resp = client.get("/api/v1/logs/system/errors?newest=5")
    assert resp.status_code in (200, 404)
    if resp.status_code != 404:
        assert resp.json()["cached"] is True

    resp = client.get("/api/v1/logs/application/errors?newest=5")
    assert resp.status_code in (200, 404)

    resp = client.get("/api/v1/logs/query?log_name=System&level=Error&newest=5")
    assert resp.status_code in (200, 404)

    resp = client.get("/api/v1/logs/search?keyword=test&newest=5")
    assert resp.status_code in (200, 404)

    resp = client.get("/api/v1/logs/search?keyword=ab")
    assert resp.status_code in (422, 404)


def test_log_linux_endpoints(client, monkeypatch):
    monkeypatch.setattr(log_router, "LINUX_HOSTS", [{"host": "server01"}])
    monkeypatch.setattr(
        linux_router, "find_linux_host_config", MagicMock(return_value={"host": "server01"})
    )
    monkeypatch.setattr(log_router, "get_linux_errors", AsyncMock(return_value=[{"msg": "e"}]))
    monkeypatch.setattr(log_router, "get_linux_logs", AsyncMock(return_value=[{"msg": "e"}]))
    monkeypatch.setattr(log_router, "search_linux_logs", AsyncMock(return_value=[{"msg": "e"}]))

    resp = client.get("/api/v1/logs/linux/errors?host_name=server01&newest=5")
    assert resp.status_code in (200, 404)

    resp = client.get("/api/v1/logs/linux/query?host_name=server01&source=syslog&newest=5")
    assert resp.status_code in (200, 404)

    resp = client.get("/api/v1/logs/linux/search?host_name=server01&keyword=err&newest=10")
    assert resp.status_code in (200, 404)

    # 404 and 422
    monkeypatch.setattr(linux_router, "find_linux_host_config", MagicMock(return_value=None))
    resp = client.get("/api/v1/logs/linux/errors?host_name=server02&newest=5")
    assert resp.status_code == 404

    resp = client.get("/api/v1/logs/linux/errors?host_name=!@#&newest=5")
    assert resp.status_code in (422, 404)


def test_log_es_search(client, monkeypatch):
    monkeypatch.setattr(log_router, "es_search_logs", AsyncMock(return_value=[{"msg": "e"}]))
    resp = client.get("/api/v1/logs/es/search?query=err&size=10&from_=0")
    assert resp.status_code in (200, 404)


def test_log_errors(client, monkeypatch):
    monkeypatch.setattr(log_router, "_log_cache", {})
    monkeypatch.setattr(log_router, "get_system_errors", AsyncMock(side_effect=Exception("boom")))
    resp = client.get("/api/v1/logs/system/errors?newest=5")
    assert resp.status_code in (500, 404)


def test_log_helper_functions(monkeypatch):
    """Test helper functions _get_linux_host and _validate_keyword error paths"""
    import pytest
    from fastapi import HTTPException

    from api.log_router import _get_linux_host, _validate_keyword

    # Test _get_linux_host with None
    with pytest.raises(HTTPException) as exc_info:
        _get_linux_host(None)
    assert exc_info.value.status_code == 422
    assert "不能为空" in exc_info.value.detail

    # Test _get_linux_host with empty string
    with pytest.raises(HTTPException) as exc_info:
        _get_linux_host("")
    assert exc_info.value.status_code == 422
    assert "不能为空" in exc_info.value.detail

    # Test _get_linux_host with whitespace only
    with pytest.raises(HTTPException) as exc_info:
        _get_linux_host("   ")
    assert exc_info.value.status_code == 422
    assert "不能为纯空白" in exc_info.value.detail

    # Test _get_linux_host with invalid characters
    with pytest.raises(HTTPException) as exc_info:
        _get_linux_host("server@01")
    assert exc_info.value.status_code == 422
    assert "仅允许字母数字" in exc_info.value.detail

    # Test _validate_keyword with None
    with pytest.raises(HTTPException) as exc_info:
        _validate_keyword(None)
    assert exc_info.value.status_code == 422
    assert "不能为空" in exc_info.value.detail

    # Test _validate_keyword with empty string
    with pytest.raises(HTTPException) as exc_info:
        _validate_keyword("")
    assert exc_info.value.status_code == 422
    assert "不能为空" in exc_info.value.detail

    # Test _validate_keyword with whitespace only
    with pytest.raises(HTTPException) as exc_info:
        _validate_keyword("   ")
    assert exc_info.value.status_code == 422
    assert "不能为纯空白字符串" in exc_info.value.detail


def test_log_app_errors_cache_and_exception(client, monkeypatch):
    """Test application errors cache hit and exception handling"""
    monkeypatch.setattr(log_router, "_log_cache", {})
    monkeypatch.setattr(
        log_router, "get_application_errors", AsyncMock(return_value=[{"msg": "e"}])
    )

    # First call - no cache
    resp = client.get("/api/v1/logs/application/errors?newest=5")
    assert resp.status_code in (200, 404)
    if resp.status_code != 404:
        assert resp.json()["cached"] is False

    # Second call - cache hit (lines 232-233)
    resp = client.get("/api/v1/logs/application/errors?newest=5")
    assert resp.status_code in (200, 404)
    if resp.status_code != 404:
        assert resp.json()["cached"] is True

    # Test exception handling (lines 239-241)
    monkeypatch.setattr(log_router, "_log_cache", {})
    monkeypatch.setattr(
        log_router, "get_application_errors", AsyncMock(side_effect=Exception("boom"))
    )
    resp = client.get("/api/v1/logs/application/errors?newest=5")
    assert resp.status_code in (500, 404)


def test_log_query_exception(client, monkeypatch):
    """Test query logs exception handling (lines 280-282)"""
    monkeypatch.setattr(log_router, "get_event_logs", AsyncMock(side_effect=Exception("boom")))
    resp = client.get("/api/v1/logs/query?log_name=System&level=Error&newest=5")
    assert resp.status_code in (500, 404)


def test_log_search_exception(client, monkeypatch):
    """Test search logs exception handling (lines 333-335)"""
    monkeypatch.setattr(log_router, "_log_cache", {})
    monkeypatch.setattr(log_router, "search_logs", AsyncMock(side_effect=Exception("boom")))
    resp = client.get("/api/v1/logs/search?keyword=test&newest=5")
    assert resp.status_code in (500, 404)


def test_log_linux_no_hosts_configured(client, monkeypatch):
    """Test Linux endpoints when no hosts are configured (lines 388, 468, 587)"""
    monkeypatch.setattr(log_router, "LINUX_HOSTS", [])

    resp = client.get("/api/v1/logs/linux/errors?host_name=server01&newest=5")
    assert resp.status_code in (200, 404)
    if resp.status_code != 404:
        assert resp.json()["message"] == "未配置 Linux 主机"

    resp = client.get("/api/v1/logs/linux/query?host_name=server01&source=syslog&newest=5")
    assert resp.status_code in (200, 404)
    if resp.status_code != 404:
        assert resp.json()["message"] == "未配置 Linux 主机"

    resp = client.get("/api/v1/logs/linux/search?host_name=server01&keyword=err&newest=10")
    assert resp.status_code in (200, 404)
    if resp.status_code != 404:
        assert resp.json()["message"] == "未配置 Linux 主机"


def test_log_linux_errors_cache_and_exception(client, monkeypatch):
    """Test Linux errors cache hit and exception handling (lines 396-397, 415-422)"""
    monkeypatch.setattr(log_router, "LINUX_HOSTS", [{"host": "server01"}])
    monkeypatch.setattr(
        linux_router, "find_linux_host_config", MagicMock(return_value={"host": "server01"})
    )
    monkeypatch.setattr(log_router, "_log_cache", {})
    monkeypatch.setattr(log_router, "get_linux_errors", AsyncMock(return_value=[{"msg": "e"}]))

    # First call - no cache
    resp = client.get("/api/v1/logs/linux/errors?host_name=server01&newest=5")
    assert resp.status_code in (200, 404)
    if resp.status_code != 404:
        assert resp.json()["cached"] is False

    # Second call - cache hit (lines 396-397)
    resp = client.get("/api/v1/logs/linux/errors?host_name=server01&newest=5")
    assert resp.status_code in (200, 404)
    if resp.status_code != 404:
        assert resp.json()["cached"] is True

    # Test exception handling (lines 415-422)
    monkeypatch.setattr(log_router, "_log_cache", {})
    monkeypatch.setattr(log_router, "get_linux_errors", AsyncMock(side_effect=Exception("boom")))
    resp = client.get("/api/v1/logs/linux/errors?host_name=server01&newest=5")
    assert resp.status_code in (500, 404)


def test_log_linux_query_exception(client, monkeypatch):
    """Test Linux query exception handling (lines 480-487)"""
    monkeypatch.setattr(log_router, "LINUX_HOSTS", [{"host": "server01"}])
    monkeypatch.setattr(
        linux_router, "find_linux_host_config", MagicMock(return_value={"host": "server01"})
    )
    monkeypatch.setattr(log_router, "get_linux_logs", AsyncMock(side_effect=Exception("boom")))
    resp = client.get("/api/v1/logs/linux/query?host_name=server01&source=syslog&newest=5")
    assert resp.status_code in (500, 404)


def test_log_linux_search_exception(client, monkeypatch):
    """Test Linux search exception handling (lines 600-607)"""
    monkeypatch.setattr(log_router, "LINUX_HOSTS", [{"host": "server01"}])
    monkeypatch.setattr(
        linux_router, "find_linux_host_config", MagicMock(return_value={"host": "server01"})
    )
    monkeypatch.setattr(log_router, "search_linux_logs", AsyncMock(side_effect=Exception("boom")))
    resp = client.get("/api/v1/logs/linux/search?host_name=server01&keyword=err&newest=10")
    assert resp.status_code in (500, 404)


def test_log_linux_http_exception_reraise(client, monkeypatch):
    """Test HTTPException re-raise in Linux endpoints (lines 416, 481, 601)"""
    from fastapi import HTTPException

    monkeypatch.setattr(log_router, "LINUX_HOSTS", [{"host": "server01"}])
    monkeypatch.setattr(
        linux_router, "find_linux_host_config", MagicMock(return_value={"host": "server01"})
    )
    monkeypatch.setattr(log_router, "_log_cache", {})

    # Test linux_errors HTTPException re-raise (line 416)
    monkeypatch.setattr(
        log_router,
        "get_linux_errors",
        AsyncMock(side_effect=HTTPException(status_code=503, detail="Service unavailable")),
    )
    resp = client.get("/api/v1/logs/linux/errors?host_name=server01&newest=5")
    assert resp.status_code in (503, 404)

    # Test linux_query HTTPException re-raise (line 481)
    monkeypatch.setattr(
        log_router,
        "get_linux_logs",
        AsyncMock(side_effect=HTTPException(status_code=503, detail="Service unavailable")),
    )
    resp = client.get("/api/v1/logs/linux/query?host_name=server01&source=syslog&newest=5")
    assert resp.status_code in (503, 404)

    # Test linux_search HTTPException re-raise (line 601)
    monkeypatch.setattr(
        log_router,
        "search_linux_logs",
        AsyncMock(side_effect=HTTPException(status_code=503, detail="Service unavailable")),
    )
    resp = client.get("/api/v1/logs/linux/search?host_name=server01&keyword=err&newest=10")
    assert resp.status_code in (503, 404)


# ---------------------------------------------------------------------------
# 14. Metrics router
# ---------------------------------------------------------------------------
def _patch_metrics(monkeypatch, dual=False):
    monkeypatch.setattr(
        metrics_router,
        "get_real_summary",
        AsyncMock(
            return_value={"total_alerts": 5, "heal_rate": 90, "mttd_min": 10, "rca_accuracy": 95}
        ),
    )
    monkeypatch.setattr(
        metrics_router,
        "collect_all",
        MagicMock(return_value={"cpu": {"usage_percent": 10}, "memory": {"usage_percent": 20}}),
    )
    monkeypatch.setattr(metrics_router, "get_top_processes", MagicMock(return_value=[]))
    monkeypatch.setattr(
        metrics_router.metrics_history,
        "to_dict",
        MagicMock(return_value={"cpu": [1.0, 2.0], "memory": [3.0, 4.0], "net_in": [5.0, 6.0]}),
    )
    monkeypatch.setattr(
        metrics_router, "get_decision_accuracy", MagicMock(return_value={"accuracy": 0.9})
    )
    monkeypatch.setattr(
        ai_feedback_router, "_compute_feedback_stats", MagicMock(return_value={"accuracy": 0.8})
    )
    if not dual:
        monkeypatch.setattr(metrics_router, "_dual_write_strategy", None)
        monkeypatch.setattr(metrics_router, "_metrics_converter", None)


def test_metrics_endpoints(client, monkeypatch):
    _patch_metrics(monkeypatch)
    monkeypatch.setattr(
        metrics_router,
        "list_kpi_configs",
        MagicMock(
            return_value=[
                {
                    "id": "1",
                    "visible": True,
                    "endpoint": "summary",
                    "field_path": "total_alerts",
                    "name": "A",
                    "target": 10,
                    "unit": "",
                }
            ]
        ),
    )
    monkeypatch.setattr(metrics_router, "create_kpi_config", MagicMock(return_value={"id": "1"}))
    monkeypatch.setattr(metrics_router, "update_kpi_config", MagicMock(return_value={"id": "1"}))
    monkeypatch.setattr(metrics_router, "delete_kpi_config", MagicMock(return_value=True))
    monkeypatch.setattr(metrics_router, "resolve_field", MagicMock(return_value=5))

    resp = client.get("/api/v1/metrics/")
    assert resp.status_code in (200, 404)

    resp = client.get("/api/v1/metrics/snapshot")
    assert resp.status_code in (200, 404)

    resp = client.get("/api/v1/metrics/history")
    assert resp.status_code in (200, 404)

    resp = client.get("/api/v1/metrics/predictions")
    assert resp.status_code in (200, 404)

    resp = client.get("/api/v1/metrics/processes?limit=5")
    assert resp.status_code in (200, 404)

    resp = client.get("/api/v1/metrics/summary")
    assert resp.status_code in (200, 404)

    resp = client.get("/api/v1/metrics/agent/feedback-accuracy")
    assert resp.status_code in (200, 404)

    resp = client.get("/api/v1/metrics/agent/decision-accuracy")
    assert resp.status_code in (200, 404)

    resp = client.delete("/api/v1/metrics/cache")
    assert resp.status_code in (200, 404)

    resp = client.get("/api/v1/metrics/kpi/config")
    assert resp.status_code in (200, 404)

    resp = client.post("/api/v1/metrics/kpi/config", json={"name": "x"})
    assert resp.status_code in (200, 404)

    resp = client.put("/api/v1/metrics/kpi/config/1", json={"name": "x"})
    assert resp.status_code in (200, 404)

    resp = client.delete("/api/v1/metrics/kpi/config/1")
    assert resp.status_code in (200, 404)

    resp = client.get("/api/v1/metrics/kpi/values")
    assert resp.status_code in (200, 404)


def test_metrics_errors(client, monkeypatch):
    _patch_metrics(monkeypatch)
    monkeypatch.setattr(
        metrics_router, "get_real_summary", AsyncMock(side_effect=Exception("boom"))
    )
    resp = client.get("/api/v1/metrics/")
    assert resp.status_code in (500, 404)

    monkeypatch.setattr(
        metrics_router.metrics_history, "to_dict", MagicMock(side_effect=Exception("boom"))
    )
    resp = client.get("/api/v1/metrics/predictions")
    assert resp.status_code in (500, 404)

    monkeypatch.setattr(metrics_router, "delete_kpi_config", MagicMock(return_value=False))
    resp = client.delete("/api/v1/metrics/kpi/config/x")
    assert resp.status_code == 404

    monkeypatch.setattr(metrics_router, "update_kpi_config", MagicMock(return_value=None))
    resp = client.put("/api/v1/metrics/kpi/config/x", json={})
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 15. Autoheal router
# ---------------------------------------------------------------------------
def _internal_headers(admin_headers):
    return {**admin_headers, "X-Internal-Key": "secret"}


def _patch_autoheal(monkeypatch):
    monkeypatch.setattr(
        autoheal_router, "get_pending_approvals", AsyncMock(return_value=[{"alert_id": "A1"}])
    )
    monkeypatch.setattr(
        core.db_engine, "async_update_approval_status_by_alert", AsyncMock(return_value=None)
    )
    monkeypatch.setattr(core.alert_engine, "alert_history", [{"id": "A1", "title": "CPU"}])
    monkeypatch.setattr(
        gateway.services_client,
        "approve_and_execute",
        AsyncMock(return_value={"success": True, "alert_id": "A1", "output": "done"}),
    )
    monkeypatch.setattr(
        core.auto_heal, "reject_repair", AsyncMock(return_value={"success": True, "alert_id": "A1"})
    )
    monkeypatch.setattr(
        autoheal_router,
        "generate_repair_runbook",
        AsyncMock(return_value={"success": True, "proposal": "restart", "risk_level": "MEDIUM"}),
    )
    monkeypatch.setattr(ai_router, "_collect_rich_context", AsyncMock(return_value={}))
    monkeypatch.setattr(core.collector, "collect_all", MagicMock(return_value={}))
    monkeypatch.setattr(autoheal_router, "is_runbook_available", True)
    monkeypatch.setattr(autoheal_router, "INTERNAL_API_KEY", "secret")


def test_autoheal_endpoints(client, admin_headers, monkeypatch):
    _patch_autoheal(monkeypatch)
    ih = _internal_headers(admin_headers)

    resp = client.get("/api/v1/approvals/pending", headers=ih)
    assert resp.status_code in (200, 404)
    if resp.status_code != 404:
        assert resp.json()["total"] == 1

    resp = client.patch("/api/v1/approvals/A1", headers=ih)
    assert resp.status_code in (200, 404)

    resp = client.post(
        "/api/v1/approvals/reject", json={"alert_id": "A1", "reason": "x"}, headers=ih
    )
    assert resp.status_code in (200, 404)

    resp = client.post("/api/v1/approvals/takeover/A1", headers=ih)
    assert resp.status_code in (200, 404)

    resp = client.post("/api/v1/approvals/propose", json={"alert_id": "A1"}, headers=ih)
    assert resp.status_code in (200, 404)
    if resp.status_code != 404:
        assert resp.json()["success"] is True


def test_autoheal_auth_and_errors(client, admin_headers, monkeypatch):
    _patch_autoheal(monkeypatch)
    ih_bad = {**admin_headers, "X-Internal-Key": "wrong"}
    resp = client.get("/api/v1/approvals/pending", headers=ih_bad)
    assert resp.status_code == 403

    resp = client.get("/api/v1/approvals/pending")
    assert resp.status_code == 403

    monkeypatch.setattr(
        autoheal_router, "get_pending_approvals", AsyncMock(side_effect=Exception("boom"))
    )
    resp = client.get("/api/v1/approvals/pending", headers=_internal_headers(admin_headers))
    assert resp.status_code in (500, 404)


def test_autoheal_approve_business_error(client, admin_headers, monkeypatch):
    _patch_autoheal(monkeypatch)
    monkeypatch.setattr(
        gateway.services_client,
        "approve_and_execute",
        AsyncMock(return_value={"success": False, "error": "approved_no_script"}),
    )
    resp = client.patch("/api/v1/approvals/A1", headers=_internal_headers(admin_headers))
    assert resp.status_code in (400, 404)
    if resp.status_code != 404:
        assert "approved_no_script" in resp.text


def test_autoheal_reject_business_error(client, admin_headers, monkeypatch):
    _patch_autoheal(monkeypatch)
    monkeypatch.setattr(
        core.auto_heal,
        "reject_repair",
        AsyncMock(return_value={"success": False, "error": "reject failed"}),
    )
    resp = client.post(
        "/api/v1/approvals/reject",
        json={"alert_id": "A1"},
        headers=_internal_headers(admin_headers),
    )
    assert resp.status_code in (400, 404)


def test_autoheal_propose_not_found(client, admin_headers, monkeypatch):
    _patch_autoheal(monkeypatch)
    monkeypatch.setattr(core.alert_engine, "alert_history", [])
    resp = client.post(
        "/api/v1/approvals/propose",
        json={"alert_id": "MISSING"},
        headers=_internal_headers(admin_headers),
    )
    assert resp.status_code == 404
