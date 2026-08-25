# -*- coding: utf-8 -*-
"""Targeted coverage tests for core.command_guard, core.log_collector, core.health_check."""

import asyncio  # noqa: F401  # Imported for test setup
import datetime
import json  # noqa: F401  # Imported for test setup
import os  # noqa: F401  # Imported for test setup
import re
import sys  # noqa: F401  # Imported for test setup
import types
from unittest.mock import AsyncMock, MagicMock

import pytest  # noqa: F401  # Imported for test setup

import core.command_guard as cg
import core.health_check as hc
import core.log_collector as lc

pytestmark = [pytest.mark.core]


# ---------------------------------------------------------------------------
# Global state reset
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def _reset_batch5_state(monkeypatch):
    cg._protected_pids.clear()
    cg._audit_log.clear()

    hc._health_cache = {"last_check": None, "components": {}}
    hc._health_history = []
    hc._alert_callbacks = []
    yield


# ---------------------------------------------------------------------------
# core.command_guard
# ---------------------------------------------------------------------------
def test_risk_level_serialize():
    assert cg.RiskLevel.SAFE.serialize_to_json() == "safe"
    assert cg.RiskLevel.BLOCKED.serialize_to_json() == "blocked"


def test_register_self_pid_valid_and_invalid(monkeypatch):
    monkeypatch.setattr(os, "getpid", lambda: 12345)
    cg.register_self_pid()
    assert 12345 in cg.get_protected_pids()

    cg.unregister_self_pid(12345)
    assert 12345 not in cg.get_protected_pids()

    cg.register_self_pid("bad")
    cg.register_self_pid(-1)
    assert cg.get_protected_pids() == set()


def test_check_self_pid_in_command():
    assert cg._check_self_pid_in_command("") is None
    assert cg._check_self_pid_in_command("kill 12345") is None
    cg._protected_pids.add(12345)
    assert cg._check_self_pid_in_command("taskkill /PID 12345") == 12345
    assert cg._check_self_pid_in_command("kill 112345") is None
    assert cg._check_self_pid_in_command("abc 12345 def") == 12345
    assert cg._check_self_pid_in_command("abc 1234567") is None  # too long


def test_split_command_chain_empty():
    assert cg._split_command_chain("") == []
    assert cg._split_command_chain("   ") == []


def test_split_command_chain_basic():
    assert cg._split_command_chain("ls -la") == ["ls -la"]
    assert cg._split_command_chain("a && b ; c || d | e") == ["a", "b", "c", "d", "e"]


def test_split_command_chain_quotes():
    assert cg._split_command_chain("echo 'a;b' && rm -rf /") == ["echo a;b", "rm -rf /"]


def test_split_command_chain_fallback_unmatched_quote():
    # shlex fails on unmatched quote and falls back to re.split
    result = cg._split_command_chain(
        'echo "a && ls'
    )  # noqa: F841  # Variable for test verification
    assert "echo" in result or "ls" in result


def test_split_command_chain_outer_exception(monkeypatch):
    monkeypatch.setattr(cg.shlex, "shlex", MagicMock(side_effect=TypeError("boom")))
    assert cg._split_command_chain("echo hello") == ["echo hello"]


def test_split_command_chain_fallback():
    assert cg._split_command_chain_fallback("a; b && c || d | e") == ["a", "b", "c", "d", "e"]


def test_check_empty_command():
    assert cg._check_empty_command("")["risk_level"] == cg.RiskLevel.SAFE
    assert cg._check_empty_command("  ")["risk_level"] == cg.RiskLevel.SAFE
    assert cg._check_empty_command("ls") is None


def test_check_self_termination():
    cg._protected_pids.add(9999)
    result = cg._check_self_termination("kill 9999")  # noqa: F841  # Variable for test verification
    assert result["risk_level"] == cg.RiskLevel.BLOCKED
    assert result["action"] == "block"
    assert cg._check_self_termination("ls") is None


def test_analyze_command_chain():
    safe = cg._analyze_single_command("ls -la")
    blocked = cg._analyze_single_command("rm -rf /")
    result = cg._analyze_command_chain(
        ["ls -la", "rm -rf /"], "ls -la && rm -rf /"
    )  # noqa: F841  # Variable for test verification
    assert result["risk_level"] == cg.RiskLevel.BLOCKED
    assert result["is_chained"] is True
    assert result["chain_count"] == 2

    empty = cg._analyze_command_chain([], "")
    assert empty["risk_level"] == cg.RiskLevel.LOW


def test_analyze_command():
    assert cg.analyze_command("")["risk_level"] == cg.RiskLevel.SAFE
    cg._protected_pids.add(1111)
    assert cg.analyze_command("kill 1111")["risk_level"] == cg.RiskLevel.BLOCKED
    assert cg.analyze_command("ls -la")["risk_level"] == cg.RiskLevel.SAFE
    chained = cg.analyze_command("ls -la && rm -rf /")
    assert chained["risk_level"] == cg.RiskLevel.BLOCKED


def test_check_whitelist():
    assert cg._check_whitelist("ls", "ls")["risk_name"].startswith("安全命令")
    assert cg._check_whitelist("ls -la", "ls -la")["risk_name"].startswith("安全命令")
    assert cg._check_whitelist("unknown cmd", "unknown cmd") is None


def test_check_blacklist():
    result = cg._check_blacklist(
        "rm -rf /", "rm -rf /"
    )  # noqa: F841  # Variable for test verification
    assert result["risk_level"] == cg.RiskLevel.BLOCKED
    high = cg._check_blacklist("shutdown now", "shutdown now")
    assert high["risk_level"] == cg.RiskLevel.HIGH
    assert high["action"] == "approve"
    assert cg._check_blacklist("ls", "ls") is None


def test_check_blacklist_regex_error(monkeypatch):
    first = True

    def fake_search(*args, **kwargs):
        nonlocal first
        if first:
            first = False
            raise re.error("bad")
        return None

    monkeypatch.setattr(cg.re, "search", fake_search)
    assert cg._check_blacklist("ls", "ls") is None


def test_build_default_risk_response():
    r = cg._build_default_risk_response("somecommand")
    assert r["risk_level"] == cg.RiskLevel.LOW
    assert r["action"] == "execute"


def test_analyze_single_command():
    assert cg._analyze_single_command("ls")["risk_level"] == cg.RiskLevel.SAFE
    assert cg._analyze_single_command("rm -rf /")["risk_level"] == cg.RiskLevel.BLOCKED
    assert cg._analyze_single_command("foobar")["risk_level"] == cg.RiskLevel.LOW


def test_is_command_allowed():
    assert cg.is_command_allowed("ls") is True
    assert cg.is_command_allowed("rm -rf /") is False


def test_get_safe_alternative_variants():
    assert "mkdir" in cg._get_safe_alternative("rm -rf /tmp/abc")
    assert "+5" in cg._get_safe_alternative("shutdown -h now")
    assert "iptables-save" in cg._get_safe_alternative("iptables -f")
    assert "mysqldump" in cg._get_safe_alternative("drop database app")
    assert "diskmgmt" in cg._get_safe_alternative("format C:")
    assert "reg export" in cg._get_safe_alternative("reg delete HKLM\\SYSTEM")
    assert cg._get_safe_alternative("echo hello") == ""


def test_parse_rm_command():
    assert cg._parse_rm_command("rm -rf /tmp") == ["rm", "-rf", "/tmp"]
    assert cg._parse_rm_command("ls") is None
    assert cg._parse_rm_command('rm "') is None  # shlex ValueError


def test_extract_rm_targets():
    assert cg._extract_rm_targets(["rm", "-rf", "/tmp", "-i", "/var"]) == ["/tmp", "/var"]
    assert cg._extract_rm_targets(["rm"]) == []


def test_build_mv_to_trash_command(monkeypatch):
    monkeypatch.setattr(cg.tempfile, "gettempdir", lambda: "/tmp")
    cmd = cg._build_mv_to_trash_command(["/home/a", "/tmp/b"])
    assert ".aiops_trash" in cmd
    assert "mv" in cmd


def test_rewrite_to_safe():
    assert cg.rewrite_to_safe("ls") == "ls"
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(cg.tempfile, "gettempdir", lambda: "/tmp")
    rewritten = cg.rewrite_to_safe("rm /home/a")
    assert ".aiops_trash" in rewritten
    monkeypatch.undo()
    assert cg.rewrite_to_safe("rm") == "rm"  # no targets
    assert cg.rewrite_to_safe('rm "') == 'rm "'  # parse fails


def test_build_rm_preview():
    preview = cg._build_rm_preview("rm /tmp /var")
    assert "将要删除" in preview
    assert cg._build_rm_preview("rm -rf") is None
    assert cg._build_rm_preview('rm "/bad') is not None


def test_build_systemctl_preview():
    assert "sshd" in cg._build_systemctl_preview("systemctl restart sshd")
    assert "restart" in cg._build_systemctl_preview("systemctl restart")
    assert "unknown" in cg._build_systemctl_preview("systemctl")
    assert "sshd" in cg._build_systemctl_preview("systemctl restart ssh!d")


def test_build_default_preview():
    assert "Dry-run" in cg._build_default_preview("echo hello")


def test_dry_run_preview():
    assert "ls -la" in cg.dry_run_preview("rm /tmp")
    assert "systemctl status" in cg.dry_run_preview("systemctl restart sshd")
    assert "Dry-run" in cg.dry_run_preview("echo hello")


def test_record_audit_and_get_and_clear():
    cg.record_audit("host1", "ls", "low")
    cg.record_audit("host1", "rm -rf /", "blocked")
    assert len(cg.get_audit_log(1)) == 1
    assert len(cg.get_audit_log(100)) == 2
    assert cg.get_audit_log(0)  # clamped to at least 1
    assert cg.clear_audit_log() == 2
    assert cg.get_audit_log() == []


def test_get_audit_log_limit_clamping():
    for i in range(5):
        cg.record_audit(f"h{i}", "x", "low")
    assert len(cg.get_audit_log(2)) == 2
    assert len(cg.get_audit_log(99999)) == 5


# ---------------------------------------------------------------------------
# core.log_collector
# ---------------------------------------------------------------------------
def test_sanitize_keyword():
    assert lc._sanitize_keyword("hello") == "hello"
    assert lc._sanitize_keyword(123) == ""
    assert lc._sanitize_keyword("a'b\"c`d;e&f<g>h{i}j$k(l)m\\n") == "abcdefghijklmn"
    assert lc._sanitize_keyword("\u2018bad\u2019") == "bad"  # Unicode homoglyphs stripped
    assert len(lc._sanitize_keyword("x" * 300)) <= 200


def test_clamp_newest():
    assert lc._clamp_newest(5) == 5
    assert lc._clamp_newest(999999) == lc._NEWEST_HARD_MAX
    assert lc._clamp_newest(-5) == 1
    assert lc._clamp_newest("abc", default=10) == 10


@pytest.mark.asyncio
async def test_get_event_logs(monkeypatch):
    monkeypatch.setattr(lc, "_run_ps_json", MagicMock(return_value=[{"x": 1}]))
    result = await lc.get_event_logs(
        "System", "Error", 1000
    )  # noqa: F841  # Variable for test verification
    assert result == [{"x": 1}]  # noqa: F841  # Variable for test verification
    assert lc._run_ps_json.called


@pytest.mark.asyncio
async def test_get_event_logs_exception(monkeypatch):
    monkeypatch.setattr(lc, "_run_ps_json", MagicMock(side_effect=Exception("boom")))
    assert await lc.get_event_logs() == []


@pytest.mark.asyncio
async def test_get_system_and_application_errors(monkeypatch):
    monkeypatch.setattr(lc, "get_event_logs", AsyncMock(return_value=[{"a": 1}]))
    assert await lc.get_system_errors() == [{"a": 1}]
    assert await lc.get_application_errors() == [{"a": 1}]


@pytest.mark.asyncio
async def test_search_logs(monkeypatch):
    monkeypatch.setattr(lc, "_run_ps_json", MagicMock(return_value=[{"m": 1}]))
    assert await lc.search_logs("error", 100) == [{"m": 1}]
    assert await lc.search_logs("", 100) == []
    assert await lc.search_logs("''", 100) == []  # sanitized to empty


def test_execute_powershell_with_timeout_success(monkeypatch):
    proc = MagicMock()
    proc.communicate = MagicMock(return_value=("stdout", "stderr"))
    proc.kill = MagicMock()
    monkeypatch.setattr(lc.shutil, "which", lambda x: "/bin/powershell")
    monkeypatch.setattr(lc.subprocess_runner, "Popen", MagicMock(return_value=proc))
    p, out, err = lc._execute_powershell_with_timeout("cmd")
    assert p is proc
    assert out == "stdout"


def test_execute_powershell_with_timeout_timeout(monkeypatch):
    proc = MagicMock()
    proc.communicate = MagicMock(side_effect=lc.subprocess_runner.TimeoutExpired("x", 1))
    proc.kill = MagicMock()
    monkeypatch.setattr(lc.shutil, "which", lambda x: "/bin/powershell")
    monkeypatch.setattr(lc.subprocess_runner, "Popen", MagicMock(return_value=proc))
    p, out, err = lc._execute_powershell_with_timeout("cmd")
    assert p is None
    proc.kill.assert_called()


def test_execute_powershell_with_timeout_file_not_found(monkeypatch):
    monkeypatch.setattr(
        lc.subprocess_runner, "Popen", MagicMock(side_effect=FileNotFoundError("no"))
    )
    p, out, err = lc._execute_powershell_with_timeout("cmd")
    assert p is None


def test_execute_powershell_with_timeout_generic_exception(monkeypatch):
    monkeypatch.setattr(lc.subprocess_runner, "Popen", MagicMock(side_effect=Exception("boom")))
    p, out, err = lc._execute_powershell_with_timeout("cmd")
    assert p is None


def test_execute_powershell_with_timeout_kill_error(monkeypatch):
    proc = MagicMock()
    proc.communicate = MagicMock(side_effect=lc.subprocess_runner.TimeoutExpired("x", 1))
    proc.kill = MagicMock(side_effect=Exception("kill fail"))
    monkeypatch.setattr(lc.subprocess_runner, "Popen", MagicMock(return_value=proc))
    p, out, err = lc._execute_powershell_with_timeout("cmd")
    assert p is None


def test_parse_powershell_json_output():
    assert lc._parse_powershell_json_output(json.dumps([{"a": 1}])) == [{"a": 1}]
    assert lc._parse_powershell_json_output(json.dumps({"a": 1})) == [{"a": 1}]
    assert lc._parse_powershell_json_output("not json") == []
    assert lc._parse_powershell_json_output(json.dumps("string")) == []


def test_sanitize_log_entries():
    entries = [
        {"TimeGenerated": 123, "Message": "x" * 2500},
        "not a dict",
    ]
    result = lc._sanitize_log_entries(entries)  # noqa: F841  # Variable for test verification
    assert result[0]["TimeGenerated"] == "123"
    assert "截断" in result[0]["Message"]


def test_run_ps_json(monkeypatch):
    monkeypatch.setattr(
        lc, "_execute_powershell_with_timeout", MagicMock(return_value=(MagicMock(), "out", ""))
    )
    monkeypatch.setattr(lc, "_parse_powershell_json_output", MagicMock(return_value=[{"x": 1}]))
    monkeypatch.setattr(lc, "_sanitize_log_entries", MagicMock(return_value=[{"x": 1}]))
    assert lc._run_ps_json("cmd") == [{"x": 1}]

    monkeypatch.setattr(
        lc, "_execute_powershell_with_timeout", MagicMock(return_value=(None, "", ""))
    )
    assert lc._run_ps_json("cmd") == []

    monkeypatch.setattr(
        lc, "_execute_powershell_with_timeout", MagicMock(return_value=(MagicMock(), "", ""))
    )
    assert lc._run_ps_json("cmd") == []


def test_extract_timestamp_from_line():
    assert lc._extract_timestamp_from_line("") == ""
    assert lc._extract_timestamp_from_line(123) == ""
    assert lc._extract_timestamp_from_line("Jan 15 10:30:45 host message") == "Jan 15 10:30:45"
    assert lc._extract_timestamp_from_line("2025-01-15T10:30:45 message") == "2025-01-15T10:30:45"


def _fake_linux_collector(raw_value):
    sem = MagicMock()
    return types.SimpleNamespace(
        _get_host_semaphore=MagicMock(return_value=sem),
        _ssh_execute=AsyncMock(return_value=raw_value),
    )


@pytest.mark.asyncio
async def test_get_linux_logs_normal(monkeypatch):
    raw = "Jan 15 10:30:45 host msg1\n\nJan 15 10:30:46 host msg2"
    fake = _fake_linux_collector(raw)
    monkeypatch.setitem(sys.modules, "core.linux_collector", fake)
    result = await lc.get_linux_logs(
        {"host": "h1"}, source="syslog", newest=10
    )  # noqa: F841  # Variable for test verification
    assert len(result) == 2
    assert result[0]["Platform"] == "linux"


@pytest.mark.asyncio
async def test_get_linux_logs_special_sources(monkeypatch):
    fake = _fake_linux_collector("line1\nline2")
    monkeypatch.setitem(sys.modules, "core.linux_collector", fake)
    assert await lc.get_linux_errors({"host": "h1"}, newest=5)
    assert await lc.get_linux_logs({"host": "h1"}, source="dmesg", newest=5)
    assert await lc.get_linux_logs(
        {"host": "h1"}, source="unknown", newest=5
    )  # falls back to syslog


@pytest.mark.asyncio
async def test_get_linux_logs_bad_inputs(monkeypatch):
    assert await lc.get_linux_logs("not a dict") == []
    assert await lc.get_linux_logs({"name": "h1"}, source="syslog", newest=0) == []

    # empty / sentinel / error raw values
    for raw in ("", "TIMEOUT", "SSH_NOT_FOUND", "NO_SYSLOG", "ERROR: connect"):
        fake = _fake_linux_collector(raw)
        monkeypatch.setitem(sys.modules, "core.linux_collector", fake)
        assert await lc.get_linux_logs({"host": "h1"}, source="syslog") == []


@pytest.mark.asyncio
async def test_get_linux_logs_import_error(monkeypatch):
    # Force an ImportError from the inner linux_collector import
    fake = types.SimpleNamespace()
    monkeypatch.setitem(sys.modules, "core.linux_collector", fake)
    assert await lc.get_linux_logs({"host": "h1"}, source="syslog") == []


@pytest.mark.asyncio
async def test_search_linux_logs(monkeypatch):
    fake = _fake_linux_collector("Jan 15 10:30:45 error here")
    monkeypatch.setitem(sys.modules, "core.linux_collector", fake)
    assert await lc.search_linux_logs({"host": "h1"}, "error", 50)
    assert await lc.search_linux_logs("bad", "error") == []
    assert await lc.search_linux_logs({"host": "h1"}, "") == []
    assert await lc.search_linux_logs({"host": "h1"}, "''") == []  # sanitized to empty


@pytest.mark.asyncio
async def test_search_linux_logs_empty_and_errors(monkeypatch):
    for raw in ("", "TIMEOUT", "SSH_NOT_FOUND", "ERROR: fail"):
        fake = _fake_linux_collector(raw)
        monkeypatch.setitem(sys.modules, "core.linux_collector", fake)
        result = await lc.search_linux_logs(
            {"host": "h1"}, "x", 10
        )  # noqa: F841  # Variable for test verification
        assert result == []  # noqa: F841  # Variable for test verification


# ---------------------------------------------------------------------------
# core.health_check
# ---------------------------------------------------------------------------
def test_register_alert_callback():
    async def cb(status, data):
        pass

    hc.register_alert_callback(cb)
    assert cb in hc._alert_callbacks


@pytest.mark.asyncio
async def test_check_database_health_healthy(monkeypatch):
    res1 = MagicMock(fetchone=MagicMock(return_value=(1,)))
    res2 = MagicMock(scalar=MagicMock(return_value=1024 * 1024 * 1024))  # 1 MB
    session = AsyncMock()
    session.execute = AsyncMock(side_effect=[res1, res2])
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)

    monkeypatch.setattr("core.db_engine.AsyncSessionLocal", MagicMock(return_value=session))
    result = await hc.check_database_health()  # noqa: F841  # Variable for test verification
    assert result["status"] == "healthy"
    assert "query_time_ms" in result["metrics"]


@pytest.mark.asyncio
async def test_check_database_health_degraded(monkeypatch):
    res1 = MagicMock(fetchone=MagicMock(return_value=(1,)))
    res2 = MagicMock(scalar=MagicMock(return_value=1024 * 1024 * 1024))
    session = AsyncMock()
    session.execute = AsyncMock(side_effect=[res1, res2])
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)
    monkeypatch.setattr("core.db_engine.AsyncSessionLocal", MagicMock(return_value=session))
    monkeypatch.setattr(hc.time, "time", MagicMock(side_effect=[0, 2]))  # 2000ms > threshold
    result = await hc.check_database_health()  # noqa: F841  # Variable for test verification
    assert result["status"] == "degraded"
    assert result["threshold_exceeded"] is True


@pytest.mark.asyncio
async def test_check_database_health_unhealthy(monkeypatch):
    monkeypatch.setattr(
        "core.db_engine.AsyncSessionLocal", MagicMock(side_effect=Exception("DB down"))
    )
    result = await hc.check_database_health()  # noqa: F841  # Variable for test verification
    assert result["status"] == "unhealthy"


@pytest.mark.asyncio
async def test_check_redis_health_healthy_and_degraded(monkeypatch):
    monkeypatch.setattr(hc.config, "REDIS_HOST", "localhost")
    monkeypatch.setattr(hc.config, "REDIS_PORT", 6379)
    monkeypatch.setattr(hc.config, "REDIS_DB", 0)

    client = MagicMock(
        ping=MagicMock(), info=MagicMock(return_value={"connected_clients": 1, "used_memory": 1024})
    )
    fake_redis = types.SimpleNamespace(Redis=MagicMock(return_value=client))
    monkeypatch.setitem(sys.modules, "redis", fake_redis)
    monkeypatch.setattr(hc.time, "time", MagicMock(side_effect=[0, 0.00001]))
    healthy = await hc.check_redis_health()
    assert healthy["status"] == "healthy"

    monkeypatch.setattr(hc.time, "time", MagicMock(side_effect=[0, 0.2]))
    degraded = await hc.check_redis_health()
    assert degraded["status"] == "degraded"


@pytest.mark.asyncio
async def test_check_redis_health_unhealthy(monkeypatch):
    monkeypatch.setattr(hc.config, "REDIS_HOST", "localhost")
    monkeypatch.setattr(hc.config, "REDIS_PORT", 6379)
    monkeypatch.setattr(hc.config, "REDIS_DB", 0)
    fake_redis = types.SimpleNamespace(Redis=MagicMock(side_effect=Exception("down")))
    monkeypatch.setitem(sys.modules, "redis", fake_redis)
    result = await hc.check_redis_health()  # noqa: F841  # Variable for test verification
    assert result["status"] == "unhealthy"


@pytest.mark.asyncio
async def test_check_system_resources(monkeypatch):
    monkeypatch.setattr(hc.psutil, "cpu_percent", MagicMock(return_value=5.0))
    memory = MagicMock(percent=50.0, used=1024**3, total=8 * 1024**3)
    disk = MagicMock(percent=40.0, used=20 * 1024**3, total=100 * 1024**3)
    monkeypatch.setattr(hc.psutil, "virtual_memory", MagicMock(return_value=memory))
    monkeypatch.setattr(hc.psutil, "disk_usage", MagicMock(return_value=disk))
    healthy = await hc.check_system_resources()
    assert healthy["status"] == "healthy"
    assert healthy["threshold_exceeded"] is False

    # degraded on all thresholds
    monkeypatch.setattr(hc.psutil, "cpu_percent", MagicMock(return_value=95.0))
    memory.percent = 95.0
    disk.percent = 99.0
    degraded = await hc.check_system_resources()
    assert degraded["status"] == "degraded"
    assert len(degraded["issues"]) == 3


@pytest.mark.asyncio
async def test_check_system_resources_exception(monkeypatch):
    monkeypatch.setattr(hc.psutil, "cpu_percent", MagicMock(side_effect=Exception("boom")))
    result = await hc.check_system_resources()  # noqa: F841  # Variable for test verification
    assert result["status"] == "unhealthy"


@pytest.mark.asyncio
async def test_check_metrics_health(monkeypatch):
    monkeypatch.setattr(hc.config, "METRICS_ENABLED", True)
    assert (await hc.check_metrics_health())["status"] == "healthy"
    monkeypatch.setattr(hc.config, "METRICS_ENABLED", False)
    assert (await hc.check_metrics_health())["status"] == "disabled"


@pytest.mark.asyncio
async def test_check_alert_and_repair_engine_health():
    assert (await hc.check_alert_engine_health())["status"] == "healthy"
    assert (await hc.check_repair_engine_health())["status"] == "healthy"


@pytest.mark.asyncio
async def test_perform_health_checks(monkeypatch):
    callback = AsyncMock()
    hc.register_alert_callback(callback)

    monkeypatch.setattr(
        hc,
        "check_database_health",
        AsyncMock(return_value={"status": "healthy", "threshold_exceeded": False}),
    )
    monkeypatch.setattr(
        hc,
        "check_redis_health",
        AsyncMock(return_value={"status": "healthy", "threshold_exceeded": False}),
    )
    monkeypatch.setattr(hc, "check_metrics_health", AsyncMock(return_value={"status": "healthy"}))
    monkeypatch.setattr(
        hc, "check_alert_engine_health", AsyncMock(return_value={"status": "healthy"})
    )
    monkeypatch.setattr(
        hc, "check_repair_engine_health", AsyncMock(return_value={"status": "healthy"})
    )
    monkeypatch.setattr(
        hc,
        "check_system_resources",
        AsyncMock(return_value={"status": "healthy", "threshold_exceeded": False}),
    )

    result = await hc.perform_health_checks()  # noqa: F841  # Variable for test verification
    assert result["overall_status"] == "healthy"
    callback.assert_not_awaited()


@pytest.mark.asyncio
async def test_perform_health_checks_unhealthy_and_exception(monkeypatch):
    callback = AsyncMock()
    failing_callback = AsyncMock(side_effect=Exception("cb fail"))
    hc._alert_callbacks = [callback, failing_callback]

    monkeypatch.setattr(
        hc,
        "check_database_health",
        AsyncMock(return_value={"status": "unhealthy", "message": "db bad"}),
    )
    monkeypatch.setattr(
        hc,
        "check_redis_health",
        AsyncMock(
            return_value={"status": "degraded", "threshold_exceeded": True, "message": "redis slow"}
        ),
    )
    monkeypatch.setattr(
        hc, "check_metrics_health", AsyncMock(side_effect=Exception("metrics boom"))
    )
    monkeypatch.setattr(
        hc, "check_alert_engine_health", AsyncMock(return_value={"status": "healthy"})
    )
    monkeypatch.setattr(
        hc, "check_repair_engine_health", AsyncMock(return_value={"status": "healthy"})
    )
    monkeypatch.setattr(
        hc,
        "check_system_resources",
        AsyncMock(return_value={"status": "healthy", "threshold_exceeded": False}),
    )

    result = await hc.perform_health_checks()  # noqa: F841  # Variable for test verification
    assert result["overall_status"] == "unhealthy"
    callback.assert_awaited_once()
    failing_callback.assert_awaited_once()  # the except branch catches callback failure


@pytest.mark.asyncio
async def test_trigger_health_alerts(monkeypatch):
    callback = AsyncMock()
    bad = AsyncMock(side_effect=Exception("bad"))
    hc._alert_callbacks = [callback, bad]
    await hc._trigger_health_alerts("unhealthy", {"issues": ["x"]})
    callback.assert_awaited_once()
    bad.assert_awaited_once()


def test_analyze_health_trend():
    assert hc._analyze_health_trend()["trend"] == "insufficient_data"

    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    hc._health_history = [
        {"overall_status": "healthy", "timestamp": now},
        {"overall_status": "healthy", "timestamp": now},
        {"overall_status": "healthy", "timestamp": now},
        {"overall_status": "healthy", "timestamp": now},
        {"overall_status": "healthy", "timestamp": now},
        {"overall_status": "unhealthy", "timestamp": now},
        {"overall_status": "unhealthy", "timestamp": now},
        {"overall_status": "unhealthy", "timestamp": now},
        {"overall_status": "unhealthy", "timestamp": now},
        {"overall_status": "unhealthy", "timestamp": now},
    ]
    assert hc._analyze_health_trend()["trend"] == "deteriorating"

    hc._health_history = [{"overall_status": "degraded"} for _ in range(8)]
    assert hc._analyze_health_trend()["trend"] == "degraded_stable"

    hc._health_history = [{"overall_status": "healthy"} for _ in range(9)]
    assert hc._analyze_health_trend()["trend"] == "improving"

    hc._health_history = (
        [{"overall_status": "healthy"} for _ in range(4)]
        + [{"overall_status": "degraded"} for _ in range(3)]
        + [{"overall_status": "unhealthy"} for _ in range(3)]
    )
    assert hc._analyze_health_trend()["trend"] == "stable"


def test_get_health_history():
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    old = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=25)).isoformat()
    hc._health_history = [
        {"overall_status": "healthy", "timestamp": now},
        {"overall_status": "healthy", "timestamp": old},
    ]
    assert len(hc.get_health_history(hours=24)) == 1
    assert len(hc.get_health_history(hours=48)) == 2
    hc._health_history = []
    assert hc.get_health_history() == []


def test_get_recovery_suggestions():
    db_bad = {"components": {"database": {"status": "unhealthy"}}}
    assert any("database" in s for s in hc.get_recovery_suggestions(db_bad))

    redis_bad = {"components": {"redis": {"status": "unhealthy"}}}
    assert any("Redis" in s for s in hc.get_recovery_suggestions(redis_bad))

    cpu_bad = {
        "components": {
            "system_resources": {"status": "degraded", "issues": ["High CPU usage: 95%"]}
        }
    }
    assert any("CPU" in s for s in hc.get_recovery_suggestions(cpu_bad))

    mem_bad = {
        "components": {
            "system_resources": {"status": "degraded", "issues": ["High memory usage: 95%"]}
        }
    }
    assert any("memory" in s for s in hc.get_recovery_suggestions(mem_bad))

    disk_bad = {
        "components": {
            "system_resources": {"status": "degraded", "issues": ["High disk usage: 95%"]}
        }
    }
    assert any("disk" in s or "storage" in s for s in hc.get_recovery_suggestions(disk_bad))

    alert_bad = {"components": {"alert_engine": {"status": "unhealthy"}}}
    assert any("alert engine" in s.lower() for s in hc.get_recovery_suggestions(alert_bad))

    repair_bad = {"components": {"repair_engine": {"status": "unhealthy"}}}
    assert any("repair engine" in s.lower() for s in hc.get_recovery_suggestions(repair_bad))

    healthy = {"components": {"database": {"status": "healthy"}}}
    assert any("healthy" in s for s in hc.get_recovery_suggestions(healthy))


def test_liveness_and_readiness():
    live = hc.get_liveness_status()
    assert live["status"] == "alive"

    hc._health_cache = {"last_check": None}
    assert hc.get_readiness_status()["status"] == "ready"

    hc._health_cache = {"last_check": "x", "overall_status": "healthy"}
    assert hc.get_readiness_status()["status"] == "ready"

    hc._health_cache = {"last_check": "x", "overall_status": "unhealthy"}
    assert hc.get_readiness_status()["status"] == "not_ready"


def test_get_detailed_health():
    hc._health_cache = {"foo": "bar"}
    assert hc.get_detailed_health()["foo"] == "bar"
