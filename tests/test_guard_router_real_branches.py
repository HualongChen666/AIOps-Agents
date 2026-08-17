# -*- coding: utf-8 -*-
"""Real-payload branch-coverage tests for api/guard_router.py."""

import pytest  # noqa: F401  # Imported for test setup

import config
from core.command_guard import (
    _audit_log,
    clear_audit_log,
    get_audit_log,
    record_audit,
    register_self_pid,
    unregister_self_pid,
)


@pytest.fixture(scope="module", autouse=True)
def _guard_setup():
    """Seed a known protected PID and clean audit state once for the module."""
    clear_audit_log()
    register_self_pid(12345)
    yield
    unregister_self_pid(12345)
    clear_audit_log()


@pytest.fixture
def restore_config():
    """Restore mutable config values that tests tweak for branch coverage."""
    original_allowed = list(config.ALLOWED_LOCAL_IPS)  # noqa: F841  # Variable for test verification
    original_key = config.INTERNAL_API_KEY  # noqa: F841  # Variable for test verification
    original_trust = config.TRUST_PROXY_HEADER  # noqa: F841  # Variable for test verification
    yield
    # restore in-place so imported references remain valid
    config.ALLOWED_LOCAL_IPS[:] = original_allowed  # noqa: F841  # Variable for test verification
    config.INTERNAL_API_KEY = original_key  # noqa: F841  # Variable for test verification
    config.TRUST_PROXY_HEADER = original_trust  # noqa: F841  # Variable for test verification


# ---------------------------------------------------------------------------
# /check endpoint
# ---------------------------------------------------------------------------
def test_check_safe_command(client):
    resp = client.post("/api/guard/check", json={"command": "ls -la"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["risk_level"] == "safe"
    assert data["action"] == "execute"
    assert data["audit"]["source_ip"] == "testclient"
    assert data["audit"]["executor"].startswith("remote@")


def test_check_high_risk_command(client):
    resp = client.post("/api/guard/check", json={"command": "reboot"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["risk_level"] == "high"
    assert data["action"] == "approve"
    assert data["audit"]["recorded"] is True


def test_check_blocked_command(client):
    resp = client.post("/api/guard/check", json={"command": "rm -rf /"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["risk_level"] == "blocked"
    assert data["action"] == "block"
    assert data["audit"]["recorded"] is True


def test_check_self_termination_pid(client):
    # 12345 was registered as protected in _guard_setup
    resp = client.post("/api/guard/check", json={"command": "kill 12345"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["risk_level"] == "blocked"
    assert "12345" in data["reason"]


def test_check_command_chain(client):
    resp = client.post("/api/guard/check", json={"command": "ls && reboot"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_chained"] is True
    assert data["chain_count"] == 2


def test_check_target_host_alias_and_validation(client):
    # valid target_host, plus legacy alias "host" with special chars
    resp = client.post(
        "/api/guard/check",
        json={"command": "ls", "host": "web-01!node"},
    )
    assert resp.status_code == 200
    data = resp.json()
    # cleaned to allowed chars
    assert data["command"] == "ls"


def test_check_target_host_variants(client):
    # whitespace host collapses to default
    resp = client.post("/api/guard/check", json={"command": "ls", "host": "   "})
    assert resp.status_code == 200
    # valid host returns as-is
    resp = client.post("/api/guard/check", json={"command": "ls", "host": "web-01.node:8080"})
    assert resp.status_code == 200


def test_check_low_risk_unknown(client):
    resp = client.post("/api/guard/check", json={"command": "foobar --unknown"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["risk_level"] == "low"
    assert data["action"] == "execute"


def test_check_local_executor(client, restore_config):
    # Make the TestClient host count as local for _get_executor_info
    if "testclient" not in config.ALLOWED_LOCAL_IPS:
        config.ALLOWED_LOCAL_IPS.append("testclient")
    resp = client.post("/api/guard/check", json={"command": "ls"})
    assert resp.status_code == 200
    assert resp.json()["audit"]["executor"] == "local_caller"


def test_check_unknown_client(client):
    # request.client is None -> source_ip == "unknown" -> local_caller
    import asyncio  # noqa: F401  # Imported for test setup

    import httpx  # noqa: F401  # Imported for test setup

    async def _call():
        transport = httpx.ASGITransport(app=client.app, client=None)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as ac:
            return await ac.post("/api/guard/check", json={"command": "ls"})

    resp = asyncio.run(_call())
    assert resp.status_code == 200
    data = resp.json()
    assert data["audit"]["source_ip"] == "unknown"
    assert data["audit"]["executor"] == "local_caller"


def test_check_validation_missing_command(client):
    resp = client.post("/api/guard/check", json={})
    assert resp.status_code == 422


def test_check_validation_command_too_long(client):
    resp = client.post("/api/guard/check", json={"command": "x" * 2001})
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# /allowed endpoint
# ---------------------------------------------------------------------------
def test_allowed_true(client):
    resp = client.post("/api/guard/allowed", json={"command": "ls"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["allowed"] is True


def test_allowed_false(client):
    resp = client.post("/api/guard/allowed", json={"command": "rm -rf /"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["allowed"] is False


def test_allowed_validation_empty(client):
    resp = client.post("/api/guard/allowed", json={"command": ""})
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# /rewrite endpoint
# ---------------------------------------------------------------------------
def test_rewrite_rm_to_safe(client):
    resp = client.post("/api/guard/rewrite", json={"command": "rm -rf /tmp/old"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["changed"] is True
    assert "mv" in data["rewritten"]


def test_rewrite_no_change(client):
    resp = client.post("/api/guard/rewrite", json={"command": "ls"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["changed"] is False
    assert data["message"] == "无需改写"


# ---------------------------------------------------------------------------
# /dryrun endpoint
# ---------------------------------------------------------------------------
def test_dryrun_rm(client):
    resp = client.post("/api/guard/dryrun", json={"command": "rm -rf /tmp/data"})
    assert resp.status_code == 200
    data = resp.json()
    assert "将要删除" in data["preview"]


def test_dryrun_systemctl(client):
    resp = client.post("/api/guard/dryrun", json={"command": "systemctl restart sshd"})
    assert resp.status_code == 200
    data = resp.json()
    assert "即将重启服务" in data["preview"]


def test_dryrun_default(client):
    resp = client.post("/api/guard/dryrun", json={"command": "echo hello"})
    assert resp.status_code == 200
    data = resp.json()
    assert "Dry-run 预览" in data["preview"]


# ---------------------------------------------------------------------------
# /audit endpoint
# ---------------------------------------------------------------------------
def _audit_headers(key: str):
    return {"X-Internal-Key": key}


def test_audit_with_valid_key(client):
    resp = client.get("/api/guard/audit", headers=_audit_headers(config.INTERNAL_API_KEY))
    assert resp.status_code == 200
    data = resp.json()
    assert "logs" in data
    assert data["filter"]["risk_level"] is None


def test_audit_wrong_key(client):
    resp = client.get("/api/guard/audit", headers=_audit_headers("not-the-key"))
    assert resp.status_code == 403


def test_audit_no_key_remote_denied(client):
    # testclient is not in ALLOWED_LOCAL_IPS by default
    resp = client.get("/api/guard/audit")
    assert resp.status_code == 403


def test_audit_local_allowed(client, restore_config):
    # Remove key requirement and trust-proxy flag so access is decided by IP
    config.INTERNAL_API_KEY = ""
    config.TRUST_PROXY_HEADER = ""
    if "testclient" not in config.ALLOWED_LOCAL_IPS:
        config.ALLOWED_LOCAL_IPS.append("testclient")
    resp = client.get("/api/guard/audit")
    assert resp.status_code == 200


def test_audit_proxy_without_key(client, restore_config):
    # Simulate proxy scenario with no INTERNAL_API_KEY configured
    config.INTERNAL_API_KEY = ""
    config.TRUST_PROXY_HEADER = "X-Forwarded-For"
    resp = client.get("/api/guard/audit")
    assert resp.status_code == 403


def test_audit_filter_by_risk_level(client):
    # seed audit logs directly
    clear_audit_log()
    record_audit("h1", "reboot", "high", executor="remote@testclient", result="checked_high")
    record_audit("h1", "ls", "safe", executor="local_caller", result="allowed")
    resp = client.get(
        "/api/guard/audit",
        params={"risk_level": "high"},
        headers=_audit_headers(config.INTERNAL_API_KEY),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert all(log["risk_level"] == "high" for log in data["logs"])
    assert data["total"] >= 1


def test_audit_limit_validation(client):
    resp = client.get(
        "/api/guard/audit",
        params={"limit": 501},
        headers=_audit_headers(config.INTERNAL_API_KEY),
    )
    assert resp.status_code == 422


def test_audit_mask_long_command(client):
    # Directly append a log containing the key "command" to exercise mask_sensitive
    _audit_log.append(
        {
            "timestamp": "2026-07-02T10:30:00Z",
            "who": "tester",
            "where": "h1",
            "what": "x" * 80,
            "command": "a" * 80,
            "risk_level": "high",
            "result": "checked_high",
        }
    )
    resp = client.get(
        "/api/guard/audit",
        params={"limit": 1},
        headers=_audit_headers(config.INTERNAL_API_KEY),
    )
    assert resp.status_code == 200
    data = resp.json()
    # the masked entry should end with ...
    long_cmd = [log for log in data["logs"] if log.get("command", "").endswith("...")]
    assert long_cmd


# ---------------------------------------------------------------------------
# /stats endpoint
# ---------------------------------------------------------------------------
def test_audit_mask_non_string_command(client):
    # Log with a non-string "command" exercises the isinstance branch
    _audit_log.append(
        {
            "timestamp": "2026-07-02T10:30:00Z",
            "who": "tester",
            "where": "h1",
            "what": "ls",
            "command": 12345,
            "risk_level": "low",
            "result": "allowed",
        }
    )
    resp = client.get(
        "/api/guard/audit",
        params={"limit": 1},
        headers=_audit_headers(config.INTERNAL_API_KEY),
    )
    assert resp.status_code == 200


def test_audit_remote_denied(client, restore_config):
    # No key, no proxy config, and testclient not local -> 403
    config.INTERNAL_API_KEY = ""
    config.TRUST_PROXY_HEADER = ""
    # Ensure testclient is not treated as local
    if "testclient" in config.ALLOWED_LOCAL_IPS:
        config.ALLOWED_LOCAL_IPS.remove("testclient")
    resp = client.get("/api/guard/audit")
    assert resp.status_code == 403


def test_stats_with_valid_key(client):
    clear_audit_log()
    record_audit("h1", "rm -rf /", "blocked", executor="remote@testclient", result="blocked")
    record_audit("h1", "reboot", "high", executor="remote@testclient", result="checked_high")
    resp = client.get("/api/guard/stats", headers=_audit_headers(config.INTERNAL_API_KEY))
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 2
    assert data["level_counts"].get("blocked", 0) >= 1
    assert data["level_counts"].get("high", 0) >= 1
    assert "block_rate" in data


def test_stats_empty_logs(client):
    clear_audit_log()
    resp = client.get("/api/guard/stats", headers=_audit_headers(config.INTERNAL_API_KEY))
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["block_rate"] == 0.0


# ---------------------------------------------------------------------------
# /api/v1/security endpoints
# ---------------------------------------------------------------------------
def test_security_events(client):
    clear_audit_log()
    record_audit("h1", "rm -rf /", "blocked", executor="remote@testclient", result="blocked")
    record_audit("h1", "reboot", "high", executor="remote@testclient", result="resolved")
    record_audit("h1", "iptables -F", "medium", executor="remote@testclient", result="allowed")
    record_audit("h1", "ls", "safe", executor="local_caller", result="allowed")
    resp = client.get(
        "/api/v1/security/events",
        headers=_audit_headers(config.INTERNAL_API_KEY),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["events"]) >= 4
    # check risk -> event type / severity / status branches
    blocked_events = [e for e in data["events"] if e["type"] == "compliance"]
    high_events = [e for e in data["events"] if e["type"] == "threat"]
    medium_events = [e for e in data["events"] if e["type"] == "vulnerability"]
    safe_events = [e for e in data["events"] if e["type"] == "incident"]
    assert blocked_events and high_events and medium_events and safe_events


def test_security_stats(client):
    clear_audit_log()
    record_audit("h1", "rm -rf /", "blocked", executor="remote@testclient", result="blocked")
    record_audit("h1", "reboot", "high", executor="remote@testclient", result="checked_high")
    resp = client.get(
        "/api/v1/security/stats",
        headers=_audit_headers(config.INTERNAL_API_KEY),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["blocked_count"] >= 1
    assert data["high_count"] >= 1
    assert "compliance_rate" in data
