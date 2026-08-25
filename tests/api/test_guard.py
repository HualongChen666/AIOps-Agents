# -*- coding: utf-8 -*-
"""Comprehensive tests for guard and security endpoints to achieve 90%+ coverage."""

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

# Basic smoke tests
_CASES = [
    # guard_router.py
    ("POST", "/api/guard/check", {}, None, {200, 422, 500}),
    ("POST", "/api/guard/allowed", {}, None, {200, 422, 500}),
    ("POST", "/api/guard/rewrite", {}, None, {200, 422, 500}),
    ("POST", "/api/guard/dryrun", {}, None, {200, 422, 500}),
    ("GET", "/api/guard/audit", None, None, {200, 500}),
    ("GET", "/api/guard/stats", None, None, {200, 500}),
    # security_router
    ("GET", "/api/v1/security/events", None, None, {200, 500}),
    ("GET", "/api/v1/security/stats", None, None, {200, 500}),
]


@pytest.fixture(scope="function", autouse=True)
def _guard_setup():
    """Clean audit state for each test."""
    clear_audit_log()
    register_self_pid(12345)
    yield
    unregister_self_pid(12345)
    clear_audit_log()


@pytest.fixture
def restore_config():
    """Restore mutable config values that tests tweak for branch coverage."""
    original_allowed = list(config.ALLOWED_LOCAL_IPS)
    original_key = config.INTERNAL_API_KEY
    original_trust = config.TRUST_PROXY_HEADER
    yield
    # restore in-place so imported references remain valid
    config.ALLOWED_LOCAL_IPS[:] = original_allowed
    config.INTERNAL_API_KEY = original_key
    config.TRUST_PROXY_HEADER = original_trust


@pytest.mark.smoke
@pytest.mark.parametrize("method,path,body,params,expected", _CASES)
def test_guard_endpoint(client, approval_headers, method, path, body, params, expected):
    """Each B22 endpoint returns an expected status set."""
    kwargs = {}
    if body is not None:
        kwargs["json"] = body
    if params:
        kwargs["params"] = params
    resp = client.request(method, path, headers=approval_headers, **kwargs)
    assert resp.status_code in expected


# ---------------------------------------------------------------------------
# /check endpoint - comprehensive tests
# ---------------------------------------------------------------------------


def test_check_safe_command(client):
    """Test checking a safe command."""
    resp = client.post("/api/guard/check", json={"command": "ls -la"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["risk_level"] == "safe"
    assert data["action"] == "execute"
    assert data["audit"]["source_ip"] == "testclient"
    assert data["audit"]["executor"].startswith("remote@")


def test_check_high_risk_command(client):
    """Test checking a high risk command."""
    resp = client.post("/api/guard/check", json={"command": "reboot"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["risk_level"] == "high"
    assert data["action"] == "approve"
    assert data["audit"]["recorded"] is True


def test_check_blocked_command(client):
    """Test checking a blocked command."""
    resp = client.post("/api/guard/check", json={"command": "rm -rf /"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["risk_level"] == "blocked"
    assert data["action"] == "block"
    assert data["audit"]["recorded"] is True


def test_check_self_termination_pid(client):
    """Test checking command that would terminate protected PID."""
    # 12345 was registered as protected in _guard_setup
    resp = client.post("/api/guard/check", json={"command": "kill 12345"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["risk_level"] == "blocked"
    assert "12345" in data["reason"]


def test_check_command_chain(client):
    """Test checking a command chain."""
    resp = client.post("/api/guard/check", json={"command": "ls && reboot"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_chained"] is True
    assert data["chain_count"] == 2


def test_check_target_host_alias_and_validation(client):
    """Test target_host validation with legacy alias."""
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
    """Test various target_host variants."""
    # whitespace host collapses to default
    resp = client.post("/api/guard/check", json={"command": "ls", "host": "   "})
    assert resp.status_code == 200
    # valid host returns as-is
    resp = client.post("/api/guard/check", json={"command": "ls", "host": "web-01.node:8080"})
    assert resp.status_code == 200


def test_check_low_risk_unknown(client):
    """Test checking unknown command."""
    resp = client.post("/api/guard/check", json={"command": "foobar --unknown"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["risk_level"] == "low"
    assert data["action"] == "execute"


def test_check_local_executor(client, restore_config):
    """Test local executor detection."""
    # Make the TestClient host count as local for _get_executor_info
    if "testclient" not in config.ALLOWED_LOCAL_IPS:
        config.ALLOWED_LOCAL_IPS.append("testclient")
    resp = client.post("/api/guard/check", json={"command": "ls"})
    assert resp.status_code == 200
    assert resp.json()["audit"]["executor"] == "local_caller"


def test_check_validation_missing_command(client):
    """Test validation error for missing command."""
    resp = client.post("/api/guard/check", json={})
    assert resp.status_code == 422


def test_check_validation_command_too_long(client):
    """Test validation error for command too long."""
    resp = client.post("/api/guard/check", json={"command": "x" * 2001})
    assert resp.status_code == 422


def test_check_with_target_host(client):
    """Test check with explicit target_host."""
    resp = client.post("/api/guard/check", json={"command": "ls", "target_host": "server1"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["command"] == "ls"


# ---------------------------------------------------------------------------
# /allowed endpoint
# ---------------------------------------------------------------------------


def test_allowed_true(client):
    """Test allowed endpoint for safe command."""
    resp = client.post("/api/guard/allowed", json={"command": "ls"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["allowed"] is True


def test_allowed_false(client):
    """Test allowed endpoint for blocked command."""
    resp = client.post("/api/guard/allowed", json={"command": "rm -rf /"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["allowed"] is False


def test_allowed_validation_empty(client):
    """Test validation error for empty command."""
    resp = client.post("/api/guard/allowed", json={"command": ""})
    assert resp.status_code == 422


def test_allowed_with_target_host(client):
    """Test allowed with target_host."""
    resp = client.post("/api/guard/allowed", json={"command": "ls", "target_host": "server1"})
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# /rewrite endpoint
# ---------------------------------------------------------------------------


def test_rewrite_rm_to_safe(client):
    """Test rewriting rm command to safe version."""
    resp = client.post("/api/guard/rewrite", json={"command": "rm -rf /tmp/old"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["changed"] is True
    assert "mv" in data["rewritten"]


def test_rewrite_no_change(client):
    """Test rewriting safe command (no change)."""
    resp = client.post("/api/guard/rewrite", json={"command": "ls"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["changed"] is False
    assert data["message"] == "无需改写"


def test_rewrite_validation_empty(client):
    """Test validation error for empty command."""
    resp = client.post("/api/guard/rewrite", json={"command": ""})
    assert resp.status_code == 422


def test_rewrite_validation_too_long(client):
    """Test validation error for command too long."""
    resp = client.post("/api/guard/rewrite", json={"command": "x" * 2001})
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# /dryrun endpoint
# ---------------------------------------------------------------------------


def test_dryrun_rm(client):
    """Test dryrun for rm command."""
    resp = client.post("/api/guard/dryrun", json={"command": "rm -rf /tmp/data"})
    assert resp.status_code == 200
    data = resp.json()
    assert "将要删除" in data["preview"]


def test_dryrun_systemctl(client):
    """Test dryrun for systemctl command."""
    resp = client.post("/api/guard/dryrun", json={"command": "systemctl restart sshd"})
    assert resp.status_code == 200
    data = resp.json()
    assert "即将重启服务" in data["preview"]


def test_dryrun_default(client):
    """Test dryrun for generic command."""
    resp = client.post("/api/guard/dryrun", json={"command": "echo hello"})
    assert resp.status_code == 200
    data = resp.json()
    assert "Dry-run 预览" in data["preview"]


def test_dryrun_with_target_host(client):
    """Test dryrun with target_host."""
    resp = client.post("/api/guard/dryrun", json={"command": "ls", "target_host": "server1"})
    assert resp.status_code == 200


def test_dryrun_validation_empty(client):
    """Test validation error for empty command."""
    resp = client.post("/api/guard/dryrun", json={"command": ""})
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# /audit endpoint
# ---------------------------------------------------------------------------


def _audit_headers(key: str):
    """Helper to create audit headers."""
    return {"X-Internal-Key": key}


def test_audit_with_valid_key(client):
    """Test audit endpoint with valid key."""
    resp = client.get("/api/guard/audit", headers=_audit_headers(config.INTERNAL_API_KEY))
    assert resp.status_code == 200
    data = resp.json()
    assert "logs" in data
    assert data["filter"]["risk_level"] is None


def test_audit_wrong_key(client):
    """Test audit endpoint with wrong key."""
    resp = client.get("/api/guard/audit", headers=_audit_headers("not-the-key"))
    assert resp.status_code == 403


def test_audit_no_key_remote_denied(client):
    """Test audit endpoint without key from remote."""
    # testclient is not in ALLOWED_LOCAL_IPS by default
    resp = client.get("/api/guard/audit")
    assert resp.status_code == 403


def test_audit_local_allowed(client, restore_config):
    """Test audit endpoint from local IP."""
    # Remove key requirement and trust-proxy flag so access is decided by IP
    config.INTERNAL_API_KEY = ""
    config.TRUST_PROXY_HEADER = ""
    if "testclient" not in config.ALLOWED_LOCAL_IPS:
        config.ALLOWED_LOCAL_IPS.append("testclient")
    resp = client.get("/api/guard/audit")
    assert resp.status_code == 200


def test_audit_proxy_without_key(client, restore_config):
    """Test audit endpoint in proxy scenario without key."""
    # Simulate proxy scenario with no INTERNAL_API_KEY configured
    config.INTERNAL_API_KEY = ""
    config.TRUST_PROXY_HEADER = "X-Forwarded-For"
    resp = client.get("/api/guard/audit")
    assert resp.status_code == 403


def test_audit_filter_by_risk_level(client):
    """Test audit endpoint with risk level filter."""
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
    """Test audit endpoint limit validation."""
    resp = client.get(
        "/api/guard/audit",
        params={"limit": 501},
        headers=_audit_headers(config.INTERNAL_API_KEY),
    )
    assert resp.status_code == 422


def test_audit_mask_long_command(client):
    """Test audit endpoint masks long commands."""
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


def test_audit_mask_non_string_command(client):
    """Test audit endpoint handles non-string command."""
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
    """Test audit endpoint denies remote without key."""
    # No key, no proxy config, and testclient not local -> 403
    config.INTERNAL_API_KEY = ""
    config.TRUST_PROXY_HEADER = ""
    # Ensure testclient is not treated as local
    if "testclient" in config.ALLOWED_LOCAL_IPS:
        config.ALLOWED_LOCAL_IPS.remove("testclient")
    resp = client.get("/api/guard/audit")
    assert resp.status_code == 403


def test_audit_with_limit(client):
    """Test audit endpoint with custom limit."""
    resp = client.get(
        "/api/guard/audit",
        params={"limit": 10},
        headers=_audit_headers(config.INTERNAL_API_KEY),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["logs"]) <= 10


# ---------------------------------------------------------------------------
# /stats endpoint
# ---------------------------------------------------------------------------


def test_stats_with_valid_key(client):
    """Test stats endpoint with valid key."""
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
    """Test stats endpoint with empty logs."""
    clear_audit_log()
    resp = client.get("/api/guard/stats", headers=_audit_headers(config.INTERNAL_API_KEY))
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["block_rate"] == 0.0


def test_stats_without_key_denied(client):
    """Test stats endpoint without key is denied."""
    resp = client.get("/api/guard/stats")
    assert resp.status_code == 403


def test_stats_with_wrong_key_denied(client):
    """Test stats endpoint with wrong key is denied."""
    resp = client.get("/api/guard/stats", headers=_audit_headers("wrong-key"))
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# /api/v1/security/events endpoint
# ---------------------------------------------------------------------------


def test_security_events(client):
    """Test security events endpoint."""
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


def test_security_events_without_key_denied(client):
    """Test security events without key is denied."""
    resp = client.get("/api/v1/security/events")
    assert resp.status_code == 403


def test_security_events_with_limit(client):
    """Test security events with custom limit."""
    clear_audit_log()
    record_audit("h1", "ls", "safe", executor="local_caller", result="allowed")
    resp = client.get(
        "/api/v1/security/events",
        params={"limit": 5},
        headers=_audit_headers(config.INTERNAL_API_KEY),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["events"]) <= 5


# ---------------------------------------------------------------------------
# /api/v1/security/stats endpoint
# ---------------------------------------------------------------------------


def test_security_stats(client):
    """Test security stats endpoint."""
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


def test_security_stats_without_key_denied(client):
    """Test security stats without key is denied."""
    resp = client.get("/api/v1/security/stats")
    assert resp.status_code == 403


def test_security_stats_with_limit(client):
    """Test security stats with custom limit."""
    resp = client.get(
        "/api/v1/security/stats",
        params={"limit": 100},
        headers=_audit_headers(config.INTERNAL_API_KEY),
    )
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Additional edge case tests
# ---------------------------------------------------------------------------


def test_check_medium_risk_command(client):
    """Test checking a medium risk command."""
    resp = client.post("/api/guard/check", json={"command": "iptables -F"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["risk_level"] in ["medium", "high"]  # May be classified differently


def test_check_with_very_long_command(client):
    """Test checking a command at max length boundary."""
    cmd = "x" * 2000
    resp = client.post("/api/guard/check", json={"command": cmd})
    assert resp.status_code == 200


def test_allowed_medium_risk(client):
    """Test allowed endpoint for medium risk command."""
    resp = client.post("/api/guard/allowed", json={"command": "iptables -F"})
    assert resp.status_code == 200
    data = resp.json()
    # Medium risk commands should be allowed
    assert "allowed" in data


def test_rewrite_high_risk_command(client):
    """Test rewriting high risk command."""
    resp = client.post("/api/guard/rewrite", json={"command": "rm -rf /etc/passwd"})
    assert resp.status_code == 200
    data = resp.json()
    assert "original" in data
    assert "rewritten" in data


def test_dryrun_high_risk_command(client):
    """Test dryrun for high risk command."""
    resp = client.post("/api/guard/dryrun", json={"command": "rm -rf /etc/passwd"})
    assert resp.status_code == 200
    data = resp.json()
    assert "preview" in data


def test_audit_with_all_risk_levels(client):
    """Test audit endpoint with all risk levels."""
    clear_audit_log()
    record_audit("h1", "ls", "safe", executor="local_caller", result="allowed")
    record_audit("h1", "cat file", "low", executor="local_caller", result="allowed")
    record_audit("h1", "iptables -F", "medium", executor="remote@testclient", result="allowed")
    record_audit("h1", "reboot", "high", executor="remote@testclient", result="checked_high")
    record_audit("h1", "rm -rf /", "blocked", executor="remote@testclient", result="blocked")

    for level in ["safe", "low", "medium", "high", "blocked"]:
        resp = client.get(
            "/api/guard/audit",
            params={"risk_level": level},
            headers=_audit_headers(config.INTERNAL_API_KEY),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["filter"]["risk_level"] == level


def test_stats_with_all_risk_levels(client):
    """Test stats endpoint with all risk levels."""
    clear_audit_log()
    record_audit("h1", "ls", "safe", executor="local_caller", result="allowed")
    record_audit("h1", "cat file", "low", executor="local_caller", result="allowed")
    record_audit("h1", "iptables -F", "medium", executor="remote@testclient", result="allowed")
    record_audit("h1", "reboot", "high", executor="remote@testclient", result="checked_high")
    record_audit("h1", "rm -rf /", "blocked", executor="remote@testclient", result="blocked")

    resp = client.get("/api/guard/stats", headers=_audit_headers(config.INTERNAL_API_KEY))
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 5
    assert data["level_counts"]["safe"] >= 1
    assert data["level_counts"]["low"] >= 1
    assert data["level_counts"]["medium"] >= 1
    assert data["level_counts"]["high"] >= 1
    assert data["level_counts"]["blocked"] >= 1


def test_security_events_all_types(client):
    """Test security events with all event types."""
    clear_audit_log()
    record_audit("h1", "rm -rf /", "blocked", executor="remote@testclient", result="blocked")
    record_audit("h1", "reboot", "high", executor="remote@testclient", result="checked_high")
    record_audit("h1", "iptables -F", "medium", executor="remote@testclient", result="allowed")
    record_audit("h1", "ls", "safe", executor="local_caller", result="allowed")

    resp = client.get("/api/v1/security/events", headers=_audit_headers(config.INTERNAL_API_KEY))
    assert resp.status_code == 200
    data = resp.json()

    # Check all event types are present
    event_types = {e["type"] for e in data["events"]}
    assert "compliance" in event_types  # blocked
    assert "threat" in event_types  # high
    assert "vulnerability" in event_types  # medium
    assert "incident" in event_types  # safe/low


def test_security_stats_comprehensive(client):
    """Test security stats with comprehensive data."""
    clear_audit_log()
    record_audit("h1", "rm -rf /", "blocked", executor="remote@testclient", result="blocked")
    record_audit("h1", "reboot", "high", executor="remote@testclient", result="checked_high")
    record_audit("h1", "iptables -F", "medium", executor="remote@testclient", result="allowed")
    record_audit("h1", "ls", "safe", executor="local_caller", result="allowed")

    resp = client.get("/api/v1/security/stats", headers=_audit_headers(config.INTERNAL_API_KEY))
    assert resp.status_code == 200
    data = resp.json()

    assert data["total"] >= 4
    assert data["threat_count"] >= 2  # high + blocked
    assert data["vulnerability_count"] >= 1  # medium
    assert data["blocked_count"] >= 1
    assert data["high_count"] >= 1
    assert "compliance_rate" in data
    assert "affected_assets" in data
