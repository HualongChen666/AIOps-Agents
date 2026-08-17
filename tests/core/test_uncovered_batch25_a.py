# -*- coding: utf-8 -*-
"""Coverage batch 25-a for core/security_middleware.py and core/verifier.py."""

import asyncio  # noqa: F401  # Imported for test setup
import sys  # noqa: F401  # Imported for test setup
from unittest.mock import AsyncMock, MagicMock

import pytest  # noqa: F401  # Imported for test setup

import core.security_middleware as sm
import core.verifier as verifier
from core.command_guard import RiskLevel

pytestmark = [pytest.mark.core]


async def async_noop(*args, **kwargs):
    return None


# ---------------------------------------------------------------------------
# Fake external dependencies injected via monkeypatch / sys.modules
# ---------------------------------------------------------------------------
class _FakeBcrypt:
    @staticmethod
    def hashpw(password, salt):
        return b"hashed:" + password

    @staticmethod
    def gensalt(rounds=12):
        return b"$2b$12$salt"

    @staticmethod
    def checkpw(password, hashed):
        return True


class _FakePyOTP:
    @staticmethod
    def random_base32():
        return "BASE32SECRET"

    class TOTP:
        def __init__(self, secret):
            self.secret = secret

        def verify(self, token, valid_window=1):
            return token == "123456"

        def provisioning_uri(self, name, issuer_name):
            return f"otpauth://totp/{issuer_name}:{name}?secret={self.secret}"


class _FakeDelta:
    def __init__(self, seconds):
        self.seconds = seconds

    def total_seconds(self):
        return self.seconds


class _FakeDateTime:
    ticks = 0.0

    def __init__(self, t=None):
        self.t = t if t is not None else _FakeDateTime.ticks

    @classmethod
    def now(cls):
        return cls(cls.ticks)

    def __sub__(self, other):
        return _FakeDelta(self.t - other.t)


# ---------------------------------------------------------------------------
# Verifier fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def guard_ok(monkeypatch):
    monkeypatch.setattr(verifier, "_check_command_with_guard", lambda cmd: (True, ""))


@pytest.fixture
def upsert_nop(monkeypatch):
    monkeypatch.setattr(verifier, "upsert_verify_record", lambda *a, **k: None)


@pytest.fixture
def verify_config(monkeypatch):
    monkeypatch.setattr(
        verifier,
        "VERIFY_CONFIG",
        {
            "enabled": True,
            "timeout_sec": 60.0,
            "metric_wait_sec": 1.0,
            "llm_for_custom": False,
        },
    )


@pytest.fixture
def short_wait(monkeypatch):
    monkeypatch.setattr(verifier, "_verification_wait_params", lambda: (0.15, 0.01))


@pytest.fixture
def linux_hosts(monkeypatch):
    monkeypatch.setattr(
        verifier,
        "LINUX_HOSTS",
        {"hosts": [{"name": "host1", "host": "10.0.0.1"}]},
    )


# ---------------------------------------------------------------------------
# core/security_middleware.py tests
# ---------------------------------------------------------------------------
def test_password_validate_short():
    ok, msg = sm.PasswordPolicy.validate_password("Short1!")
    assert ok is False
    assert "12" in msg


def test_password_validate_missing_upper():
    ok, msg = sm.PasswordPolicy.validate_password("strongpass1!")
    assert ok is False
    assert "uppercase" in msg


def test_password_validate_missing_lower():
    ok, msg = sm.PasswordPolicy.validate_password("STRONGPASS1!")
    assert ok is False
    assert "lowercase" in msg


def test_password_validate_missing_number():
    ok, msg = sm.PasswordPolicy.validate_password("StrongPass!!")
    assert ok is False
    assert "number" in msg


def test_password_validate_missing_special():
    ok, msg = sm.PasswordPolicy.validate_password("StrongPassword1")
    assert ok is False
    assert "special" in msg


def test_password_validate_ok():
    ok, msg = sm.PasswordPolicy.validate_password("Str0ng!P@ssword")
    assert ok is True
    assert "meets" in msg


def test_hash_password_bcrypt(monkeypatch):
    monkeypatch.setitem(sys.modules, "bcrypt", _FakeBcrypt)
    hashed = sm.PasswordPolicy.hash_password("P@ssw0rd1234")
    assert hashed.startswith("hashed:")


def test_verify_password_bcrypt(monkeypatch):
    monkeypatch.setitem(sys.modules, "bcrypt", _FakeBcrypt)
    hashed = sm.PasswordPolicy.hash_password("P@ssw0rd1234")
    assert sm.PasswordPolicy.verify_password("P@ssw0rd1234", hashed) is True
    assert sm.PasswordPolicy.verify_password("wrong", hashed) is True  # fake always True


def test_hash_password_pbkdf2_fallback(monkeypatch):
    monkeypatch.setitem(sys.modules, "bcrypt", None)
    hashed = sm.PasswordPolicy.hash_password("P@ssw0rd1234")
    assert hashed.startswith("pbkdf2:")


def test_verify_password_pbkdf2_fallback(monkeypatch):
    monkeypatch.setitem(sys.modules, "bcrypt", None)
    hashed = sm.PasswordPolicy.hash_password("P@ssw0rd1234")
    assert sm.PasswordPolicy.verify_password("P@ssw0rd1234", hashed) is True
    assert sm.PasswordPolicy.verify_password("wrong", hashed) is False
    assert sm.PasswordPolicy.verify_password("x", "not-pbkdf2:hash") is False


def test_mfa_enable_disable():
    manager = sm.MFAManager()
    assert manager._mfa_enabled is False
    manager.enable_mfa()
    assert manager._mfa_enabled is True
    manager.disable_mfa()
    assert manager._mfa_enabled is False


def test_mfa_totp_success(monkeypatch):
    monkeypatch.setitem(sys.modules, "pyotp", _FakePyOTP)
    manager = sm.MFAManager()
    manager.enable_mfa()
    secret = manager.generate_totp_secret("user1")
    assert secret == "BASE32SECRET"
    assert manager._totp_secret_cache["user1"] == "BASE32SECRET"
    assert manager.verify_totp("user1", "123456") is True
    assert manager.verify_totp("user1", "000000") is False


def test_mfa_verify_disabled():
    manager = sm.MFAManager()
    assert manager.verify_totp("any", "123") is True


def test_mfa_verify_no_secret():
    manager = sm.MFAManager()
    manager.enable_mfa()
    assert manager.verify_totp("missing", "123") is False


def test_mfa_qr_code(monkeypatch):
    monkeypatch.setitem(sys.modules, "pyotp", _FakePyOTP)
    manager = sm.MFAManager()
    uri = manager.get_totp_qr_code("user1", "BASE32SECRET")
    assert "otpauth://" in uri


def test_mfa_pyotp_import_error(monkeypatch):
    monkeypatch.setitem(sys.modules, "pyotp", None)
    manager = sm.MFAManager()
    manager._totp_secret_cache["user1"] = "SECRET"
    manager.enable_mfa()
    assert manager.verify_totp("user1", "123456") is True
    assert manager.get_totp_qr_code("user2", "SECRET") is None


def test_rate_limiter_new_client(monkeypatch):
    monkeypatch.setattr(sm, "datetime", _FakeDateTime)
    _FakeDateTime.ticks = 0.0
    limiter = sm.RateLimiter()
    allowed, retry = limiter.check_rate_limit("client-1")
    assert allowed is True
    assert retry is None


def test_rate_limiter_hits_limit_and_resets(monkeypatch):
    monkeypatch.setattr(sm, "datetime", _FakeDateTime)
    _FakeDateTime.ticks = 0.0
    limiter = sm.RateLimiter()
    # First 100 requests allowed
    for _ in range(100):
        allowed, _ = limiter.check_rate_limit("c")
        assert allowed is True
    # 101st is blocked
    allowed, retry = limiter.check_rate_limit("c")
    assert allowed is False
    assert retry > 0
    # After window passes request is allowed again
    _FakeDateTime.ticks = 70.0
    allowed, _ = limiter.check_rate_limit("c")
    assert allowed is True


def test_rate_limiter_cleanup(monkeypatch):
    monkeypatch.setattr(sm, "datetime", _FakeDateTime)
    limiter = sm.RateLimiter()
    stale = _FakeDateTime(0.0)
    limiter._request_counts = {"old": {"count": 5, "timestamp": stale}}
    _FakeDateTime.ticks = 70.0
    limiter.check_rate_limit("new")
    assert "old" not in limiter._request_counts
    assert "new" in limiter._request_counts


def test_security_headers_added():
    resp = MagicMock()
    resp.headers = {}
    out = sm.SecurityHeaders.add_security_headers(resp)
    assert out is resp
    assert "Strict-Transport-Security" in resp.headers
    assert "Content-Security-Policy" in resp.headers
    assert resp.headers["X-Frame-Options"] == "DENY"
    assert resp.headers["X-Content-Type-Options"] == "nosniff"


def test_tls_enforcer_https():
    req = MagicMock()
    req.url.scheme = "https"
    req.headers = {}
    enforcer = sm.TLSEnforcer()
    assert enforcer.check_tls(req) is True


def test_tls_enforcer_http_rejected():
    req = MagicMock()
    req.url.scheme = "http"
    req.headers = {}
    enforcer = sm.TLSEnforcer()
    assert enforcer.check_tls(req) is False


def test_tls_enforcer_http_with_forwarded_proto():
    req = MagicMock()
    req.url.scheme = "http"
    req.headers = {"X-Forwarded-Proto": "https"}
    enforcer = sm.TLSEnforcer()
    assert enforcer.check_tls(req) is True


def test_tls_enforcer_disabled_allows_http():
    req = MagicMock()
    req.url.scheme = "http"
    req.headers = {}
    enforcer = sm.TLSEnforcer(enforce_tls=False)
    assert enforcer.check_tls(req) is True


# ---------------------------------------------------------------------------
# core/verifier.py tests
# ---------------------------------------------------------------------------
def test_verification_wait_params(monkeypatch):
    monkeypatch.setattr(
        verifier,
        "SNAPSHOT_CONFIG",
        {"verify_wait_timeout": 20.0, "verify_poll_interval": 2.0},
    )
    monkeypatch.setattr(verifier, "VERIFY_CONFIG", {"timeout_sec": 30.0})
    assert verifier._verification_wait_timeout() == 20.0
    assert verifier._verification_poll_interval() == 2.0
    assert verifier._verification_wait_params() == (20.0, 2.0)


@pytest.mark.parametrize(
    "script_key, ai_runbook, expected",
    [
        ("restart_service", None, "service_status"),
        ("kill_high_cpu", None, "process_check"),
        ("free_cache", None, "metric_threshold"),
        ("cpu_high_script", None, "metric_threshold"),
        ("disk_high_script", None, "disk_usage"),
        ("clear_logs", None, "disk_usage"),
        ("flush_dns", None, "network_check"),
        ("k8s_pod_crash", None, "k8s_status"),
        ("sfc_scan", None, "none"),
        ("unknown", None, "none"),
        ("AI_DYNAMIC", {"commands": ["systemctl restart nginx"]}, "service_status"),
        ("AI_DYNAMIC", {"commands": ["kill 12345"]}, "process_check"),
        ("AI_DYNAMIC", {"commands": ["echo 3 > /proc/sys/vm/drop_caches"]}, "metric_threshold"),
        ("AI_DYNAMIC", {"commands": ["df /tmp"]}, "disk_usage"),
        ("AI_DYNAMIC", {"commands": ["ping 8.8.8.8"]}, "network_check"),
        ("AI_DYNAMIC", {"commands": ["kubectl get pods web"]}, "k8s_status"),
        ("AI_DYNAMIC", {"commands": ["echo hello"]}, "custom_command"),
        ("AI_DYNAMIC", {"commands": "not-a-list"}, "custom_command"),
    ],
)
def test_select_strategy(script_key, ai_runbook, expected):
    assert verifier._select_strategy(script_key, ai_runbook) == expected


def test_check_command_with_guard_levels(monkeypatch):
    monkeypatch.setattr(
        "core.command_guard.analyze_command",
        lambda cmd: {"risk_level": RiskLevel.SAFE, "reason": ""},
    )
    assert verifier._check_command_with_guard("ls")[0] is True

    monkeypatch.setattr(
        "core.command_guard.analyze_command",
        lambda cmd: {"risk_level": RiskLevel.LOW, "reason": ""},
    )
    assert verifier._check_command_with_guard("unknown")[0] is True

    monkeypatch.setattr(
        "core.command_guard.analyze_command",
        lambda cmd: {"risk_level": RiskLevel.MEDIUM, "reason": ""},
    )
    assert verifier._check_command_with_guard("cmd")[0] is False

    monkeypatch.setattr(
        "core.command_guard.analyze_command",
        lambda cmd: {"risk_level": RiskLevel.HIGH, "reason": "danger"},
    )
    ok, reason = verifier._check_command_with_guard("rm -rf /")
    assert ok is False
    assert "danger" in reason

    monkeypatch.setattr(
        "core.command_guard.analyze_command",
        lambda cmd: {"risk_level": RiskLevel.BLOCKED, "reason": "blocked"},
    )
    ok, reason = verifier._check_command_with_guard("rm -rf /")
    assert ok is False
    assert "blocked" in reason


def test_check_command_with_guard_import_error(monkeypatch):
    def raise_import_error(cmd):
        raise ImportError("no command guard")

    monkeypatch.setattr("core.command_guard.analyze_command", raise_import_error)
    assert verifier._check_command_with_guard("ls")[0] is True


def test_check_command_with_guard_exception(monkeypatch):
    def raise_runtime(cmd):
        raise RuntimeError("boom")

    monkeypatch.setattr("core.command_guard.analyze_command", raise_runtime)
    ok, reason = verifier._check_command_with_guard("ls")
    assert ok is False
    assert "RuntimeError" in reason


def test_build_results():
    skipped = verifier._build_skipped_result("none", "skip it")
    assert skipped["verified"] is None
    assert skipped["strategy"] == "none"

    error = verifier._build_error_result("error", "boom", duration_sec=1.0)
    assert error["verified"] is None
    assert error["error_msg"] == "boom"
    assert error["duration_sec"] == 1.0


async def test_execute_linux_verify_command(monkeypatch, linux_hosts):
    monkeypatch.setattr(
        "core.linux_collector._ssh_execute",
        AsyncMock(return_value="linux output"),
    )
    monkeypatch.setattr("core.linux_collector._get_host_semaphore", lambda host: MagicMock())
    out = await verifier._execute_linux_verify_command({"host": "host1"}, "ls")
    assert out == "linux output"

    with pytest.raises(ValueError, match="host"):
        await verifier._execute_linux_verify_command({}, "ls")

    with pytest.raises(ValueError, match="未找到"):
        await verifier._execute_linux_verify_command({"host": "missing"}, "ls")


async def test_execute_windows_verify_command(monkeypatch):
    monkeypatch.setattr(
        "core.repair_engine._run_powershell",
        lambda cmd: {"output": "windows output"},
    )
    out = await verifier._execute_windows_verify_command("Get-Service x")
    assert out == "windows output"


async def test_verify_service_status_linux_active(guard_ok, short_wait, monkeypatch):
    monkeypatch.setattr(
        verifier,
        "_execute_linux_verify_command",
        AsyncMock(return_value="active\n"),
    )
    result = await verifier._verify_service_status(  # noqa: F841  # Variable for test verification
        {"platform": "linux"}, {"service_name": "nginx"}, "linux"
    )
    assert result["verified"] is True
    assert result["strategy"] == "service_status"
    assert "nginx" in result["recommendation"]


async def test_verify_service_status_windows_running(guard_ok, short_wait, monkeypatch):
    monkeypatch.setattr(
        verifier,
        "_execute_windows_verify_command",
        AsyncMock(return_value="Running\n"),
    )
    result = await verifier._verify_service_status(  # noqa: F841  # Variable for test verification
        {"platform": "windows"},
        {},
        "windows",
        ai_runbook={"commands": ["Restart-Service -Name 'w3svc'"]},
    )
    assert result["verified"] is True
    assert result["evidence"]["service_name"] == "w3svc"


async def test_verify_service_status_transient_then_active(guard_ok, short_wait, monkeypatch):
    monkeypatch.setattr(asyncio, "sleep", async_noop)
    monkeypatch.setattr(
        verifier,
        "_execute_linux_verify_command",
        AsyncMock(side_effect=["activating\n", "active\n"]),
    )
    result = await verifier._verify_service_status(  # noqa: F841  # Variable for test verification
        {"platform": "linux"}, {"service_name": "nginx"}, "linux"
    )
    assert result["verified"] is True
    assert "nginx" in result["recommendation"]


async def test_verify_service_status_windows_startpending(guard_ok, short_wait, monkeypatch):
    monkeypatch.setattr(asyncio, "sleep", async_noop)
    monkeypatch.setattr(
        verifier,
        "_execute_windows_verify_command",
        AsyncMock(return_value="StartPending\n"),
    )
    result = await verifier._verify_service_status(  # noqa: F841  # Variable for test verification
        {"platform": "windows"}, {"service_name": "w3svc"}, "windows"
    )
    assert result["verified"] is None
    assert "启动中" in result["recommendation"]


async def test_verify_service_status_invalid_name(guard_ok, short_wait):
    result = await verifier._verify_service_status(  # noqa: F841  # Variable for test verification
        {"platform": "linux"}, {"service_name": "bad;name"}, "linux"
    )
    assert result["strategy"] == "service_status"
    assert "非法" in result["error_msg"]


async def test_verify_service_status_too_long(guard_ok, short_wait):
    long_name = "a" * 257
    result = await verifier._verify_service_status(  # noqa: F841  # Variable for test verification
        {"platform": "linux"}, {"service_name": long_name}, "linux"
    )
    assert result["strategy"] == "service_status"
    assert "超长" in result["error_msg"]


async def test_verify_service_status_missing_name():
    result = await verifier._verify_service_status({"platform": "linux"}, {}, "linux")  # noqa: F841  # Variable for test verification
    assert result["verified"] is None
    assert result["strategy"] == "skipped"


async def test_verify_service_status_guard_blocked(short_wait, monkeypatch):
    monkeypatch.setattr(verifier, "_check_command_with_guard", lambda cmd: (False, "blocked"))
    result = await verifier._verify_service_status(  # noqa: F841  # Variable for test verification
        {"platform": "linux"}, {"service_name": "nginx"}, "linux"
    )
    assert result["strategy"] == "service_status"
    assert "护栏" in result["error_msg"]


async def test_verify_service_status_execute_exception(guard_ok, short_wait, monkeypatch):
    monkeypatch.setattr(
        verifier,
        "_execute_linux_verify_command",
        AsyncMock(side_effect=RuntimeError("ssh failed")),
    )
    result = await verifier._verify_service_status(  # noqa: F841  # Variable for test verification
        {"platform": "linux"}, {"service_name": "nginx"}, "linux"
    )
    assert result["strategy"] == "service_status"
    assert "RuntimeError" in result["error_msg"]


async def test_verify_service_status_not_active(guard_ok, short_wait, monkeypatch):
    monkeypatch.setattr(
        verifier,
        "_execute_linux_verify_command",
        AsyncMock(return_value="inactive\n"),
    )
    result = await verifier._verify_service_status(  # noqa: F841  # Variable for test verification
        {"platform": "linux"}, {"service_name": "nginx"}, "linux"
    )
    assert result["verified"] is False


async def test_verify_service_status_windows_not_running(guard_ok, short_wait, monkeypatch):
    monkeypatch.setattr(
        verifier,
        "_execute_windows_verify_command",
        AsyncMock(return_value="Stopped\n"),
    )
    result = await verifier._verify_service_status(  # noqa: F841  # Variable for test verification
        {"platform": "windows"}, {"service_name": "w3svc"}, "windows"
    )
    assert result["verified"] is False


async def test_verify_process_check_linux_killed(guard_ok, monkeypatch):
    monkeypatch.setattr(verifier, "_execute_linux_verify_command", AsyncMock(return_value="0"))
    result = await verifier._verify_process_check({"platform": "linux"}, {"pid": "12345"}, "linux")  # noqa: F841  # Variable for test verification
    assert result["verified"] is True
    assert result["evidence"]["pid"] == 12345


async def test_verify_process_check_linux_alive(guard_ok, monkeypatch):
    monkeypatch.setattr(verifier, "_execute_linux_verify_command", AsyncMock(return_value="1"))
    result = await verifier._verify_process_check({"platform": "linux"}, {"pid": "12345"}, "linux")  # noqa: F841  # Variable for test verification
    assert result["verified"] is False


async def test_verify_process_check_windows_dead(guard_ok, monkeypatch):
    monkeypatch.setattr(
        verifier,
        "_execute_windows_verify_command",
        AsyncMock(return_value="DEAD"),
    )
    result = await verifier._verify_process_check({"platform": "windows"}, {"pid": "42"}, "windows")  # noqa: F841  # Variable for test verification
    assert result["verified"] is True


async def test_verify_process_check_windows_alive(guard_ok, monkeypatch):
    monkeypatch.setattr(
        verifier,
        "_execute_windows_verify_command",
        AsyncMock(return_value="ALIVE"),
    )
    result = await verifier._verify_process_check({"platform": "windows"}, {"pid": "42"}, "windows")  # noqa: F841  # Variable for test verification
    assert result["verified"] is False


async def test_verify_process_check_pid_from_runbook(guard_ok, monkeypatch):
    monkeypatch.setattr(
        verifier,
        "_execute_windows_verify_command",
        AsyncMock(return_value="DEAD"),
    )
    result = await verifier._verify_process_check(  # noqa: F841  # Variable for test verification
        {"platform": "windows"},
        {},
        "windows",
        ai_runbook={"commands": ["Stop-Process -Id 9999"]},
    )
    assert result["verified"] is True
    assert result["evidence"]["pid"] == 9999


async def test_verify_process_check_invalid_pid():
    result = await verifier._verify_process_check({"platform": "linux"}, {"pid": "abc"}, "linux")  # noqa: F841  # Variable for test verification
    assert result["verified"] is None
    assert result["strategy"] == "skipped"


async def test_verify_process_check_pid_out_of_range(guard_ok):
    result = await verifier._verify_process_check(  # noqa: F841  # Variable for test verification
        {"platform": "linux"}, {"pid": "5000000"}, "linux"
    )
    assert result["strategy"] == "process_check"
    assert "超出合法范围" in result["error_msg"]


async def test_verify_process_check_guard_blocked(monkeypatch):
    monkeypatch.setattr(verifier, "_check_command_with_guard", lambda cmd: (False, "blocked"))
    result = await verifier._verify_process_check({"platform": "linux"}, {"pid": "12345"}, "linux")  # noqa: F841  # Variable for test verification
    assert result["strategy"] == "process_check"
    assert "护栏" in result["error_msg"]


async def test_verify_process_check_execute_exception(guard_ok, monkeypatch):
    monkeypatch.setattr(
        verifier,
        "_execute_linux_verify_command",
        AsyncMock(side_effect=RuntimeError("ssh failed")),
    )
    result = await verifier._verify_process_check({"platform": "linux"}, {"pid": "12345"}, "linux")  # noqa: F841  # Variable for test verification
    assert result["strategy"] == "process_check"
    assert "RuntimeError" in result["error_msg"]


async def test_verify_metric_threshold_success(monkeypatch, verify_config):
    monkeypatch.setattr(asyncio, "sleep", async_noop)
    monkeypatch.setattr(
        "core.metrics_history.metrics_history",
        type("M", (), {"to_dict": lambda self: {"memory": [4.0, 4.0, 4.0]}})(),
    )
    result = await verifier._verify_metric_threshold("free_cache", {"memory": [10.0, 10.0, 10.0]})  # noqa: F841  # Variable for test verification
    assert result["verified"] is True
    assert result["strategy"] == "metric_threshold"
    assert result["evidence"]["delta_percent"] == 60.0


async def test_verify_metric_threshold_no_improvement(monkeypatch, verify_config):
    monkeypatch.setattr(asyncio, "sleep", async_noop)
    monkeypatch.setattr(
        "core.metrics_history.metrics_history",
        type("M", (), {"to_dict": lambda self: {"memory": [9.6, 9.6, 9.6]}})(),
    )
    result = await verifier._verify_metric_threshold("free_cache", {"memory": [10.0, 10.0, 10.0]})  # noqa: F841  # Variable for test verification
    assert result["verified"] is False
    assert "不显著" in result["recommendation"]


async def test_verify_metric_threshold_no_snapshot():
    result = await verifier._verify_metric_threshold("free_cache", None)  # noqa: F841  # Variable for test verification
    assert result["verified"] is None
    assert result["strategy"] == "skipped"


async def test_verify_metric_threshold_missing_metric_field():
    result = await verifier._verify_metric_threshold("unknown_script", {"dummy": []})  # noqa: F841  # Variable for test verification
    assert result["verified"] is None
    assert "无关联" in result["recommendation"]


async def test_verify_metric_threshold_insufficient_samples(monkeypatch, verify_config):
    monkeypatch.setattr(asyncio, "sleep", async_noop)
    monkeypatch.setattr(
        "core.metrics_history.metrics_history",
        type("M", (), {"to_dict": lambda self: {"memory": [4.0]}})(),
    )
    result = await verifier._verify_metric_threshold("free_cache", {"memory": [10.0]})  # noqa: F841  # Variable for test verification
    assert result["verified"] is None
    assert "数据点不足" in result["recommendation"]


async def test_verify_metric_threshold_post_snapshot_exception(monkeypatch, verify_config):
    monkeypatch.setattr(asyncio, "sleep", async_noop)

    class BadHistory:
        def to_dict(self):
            raise RuntimeError("metrics unavailable")

    monkeypatch.setattr("core.metrics_history.metrics_history", BadHistory())
    result = await verifier._verify_metric_threshold("free_cache", {"memory": [10.0, 10.0, 10.0]})  # noqa: F841  # Variable for test verification
    assert result["strategy"] == "metric_threshold"
    assert "RuntimeError" in result["error_msg"]


async def test_verify_metric_threshold_non_list_series():
    result = await verifier._verify_metric_threshold("free_cache", {"memory": "not-a-list"})  # noqa: F841  # Variable for test verification
    assert result["strategy"] == "metric_threshold"
    assert "序列格式异常" in result["error_msg"]


async def test_verify_metric_threshold_parse_error(monkeypatch, verify_config):
    monkeypatch.setattr(asyncio, "sleep", async_noop)
    monkeypatch.setattr(
        "core.metrics_history.metrics_history",
        type("M", (), {"to_dict": lambda self: {"memory": ["x", "y", "z"]}})(),
    )
    result = await verifier._verify_metric_threshold("free_cache", {"memory": ["x", 10.0, 10.0]})  # noqa: F841  # Variable for test verification
    assert result["strategy"] == "metric_threshold"
    assert "数值计算异常" in result["error_msg"]


async def test_verify_metric_threshold_zero_pre_avg(monkeypatch, verify_config):
    monkeypatch.setattr(asyncio, "sleep", async_noop)
    monkeypatch.setattr(
        "core.metrics_history.metrics_history",
        type("M", (), {"to_dict": lambda self: {"memory": [4.0, 4.0, 4.0]}})(),
    )
    result = await verifier._verify_metric_threshold("free_cache", {"memory": [0.0, 0.0, 0.0]})  # noqa: F841  # Variable for test verification
    assert result["evidence"]["delta_percent"] == 0.0


async def test_verify_disk_usage_linux(guard_ok, monkeypatch):
    monkeypatch.setattr(
        verifier,
        "_execute_linux_verify_command",
        AsyncMock(
            return_value=(
                "Filesystem     1K-blocks    Used Available Use% Mounted on\n"
                "/dev/sda1       100000   50000     50000  50% /"
            )
        ),
    )
    result = await verifier._verify_disk_usage({"platform": "linux"}, {"mount_point": "/"}, "linux")  # noqa: F841  # Variable for test verification
    assert result["verified"] is True
    assert result["evidence"]["usage_percent"] == 50.0


async def test_verify_disk_usage_linux_high(guard_ok, monkeypatch):
    monkeypatch.setattr(
        verifier,
        "_execute_linux_verify_command",
        AsyncMock(
            return_value=(
                "Filesystem     1K-blocks    Used Available Use% Mounted on\n"
                "/dev/sda1       100000   95000      5000  95% /"
            )
        ),
    )
    result = await verifier._verify_disk_usage(  # noqa: F841  # Variable for test verification
        {"platform": "linux"}, {"mount_point": "/", "threshold": 90.0}, "linux"
    )
    assert result["verified"] is False


async def test_verify_disk_usage_windows(guard_ok, monkeypatch):
    monkeypatch.setattr(
        verifier,
        "_execute_windows_verify_command",
        AsyncMock(return_value="C 100000 1000"),
    )
    result = await verifier._verify_disk_usage(  # noqa: F841  # Variable for test verification
        {"platform": "windows"}, {"mount_point": "C:\\"}, "windows"
    )
    assert result["verified"] is False
    assert result["evidence"]["usage_percent"] == 99.0


async def test_verify_disk_usage_invalid_mount(guard_ok):
    result = await verifier._verify_disk_usage(  # noqa: F841  # Variable for test verification
        {"platform": "linux"}, {"mount_point": ";bad"}, "linux"
    )
    assert result["strategy"] == "disk_usage"
    assert "非法挂载点" in result["error_msg"]


async def test_verify_disk_usage_mount_from_runbook(guard_ok, monkeypatch):
    monkeypatch.setattr(
        verifier,
        "_execute_linux_verify_command",
        AsyncMock(
            return_value=(
                "Filesystem     1K-blocks    Used Available Use% Mounted on\n"
                "/dev/sda1 100 50 50 50% /tmp"
            )
        ),
    )
    result = await verifier._verify_disk_usage(  # noqa: F841  # Variable for test verification
        {"platform": "linux"},
        {},
        "linux",
        ai_runbook={"commands": ["rm -rf /tmp"]},
    )
    assert result["evidence"]["mount_point"] == "/tmp"
    assert result["verified"] is True


async def test_verify_disk_usage_guard_blocked(monkeypatch):
    monkeypatch.setattr(verifier, "_check_command_with_guard", lambda cmd: (False, "blocked"))
    result = await verifier._verify_disk_usage({"platform": "linux"}, {"mount_point": "/"}, "linux")  # noqa: F841  # Variable for test verification
    assert result["strategy"] == "disk_usage"
    assert "护栏" in result["error_msg"]


async def test_verify_disk_usage_execute_exception(guard_ok, monkeypatch):
    monkeypatch.setattr(
        verifier,
        "_execute_linux_verify_command",
        AsyncMock(side_effect=RuntimeError("ssh failed")),
    )
    result = await verifier._verify_disk_usage({"platform": "linux"}, {"mount_point": "/"}, "linux")  # noqa: F841  # Variable for test verification
    assert result["strategy"] == "disk_usage"
    assert "RuntimeError" in result["error_msg"]


async def test_verify_disk_usage_parse_failure(guard_ok, monkeypatch):
    monkeypatch.setattr(
        verifier,
        "_execute_linux_verify_command",
        AsyncMock(return_value="garbage"),
    )
    result = await verifier._verify_disk_usage({"platform": "linux"}, {"mount_point": "/"}, "linux")  # noqa: F841  # Variable for test verification
    assert result["strategy"] == "disk_usage"
    assert "无法解析" in result["error_msg"]


async def test_verify_disk_usage_threshold_invalid(guard_ok, monkeypatch):
    monkeypatch.setattr(
        verifier,
        "_execute_linux_verify_command",
        AsyncMock(
            return_value=(
                "Filesystem     1K-blocks    Used Available Use% Mounted on\n"
                "/dev/sda1 100 50 50 50% /"
            )
        ),
    )
    result = await verifier._verify_disk_usage(  # noqa: F841  # Variable for test verification
        {"platform": "linux", "threshold": "not-a-number"}, {"mount_point": "/"}, "linux"
    )
    assert result["verified"] is True


async def test_verify_network_check_linux_success(guard_ok, monkeypatch):
    monkeypatch.setattr(
        verifier,
        "_execute_linux_verify_command",
        AsyncMock(return_value="1 packets received, 0% packet loss"),
    )
    result = await verifier._verify_network_check(  # noqa: F841  # Variable for test verification
        {"platform": "linux"}, {"target": "8.8.8.8"}, "linux"
    )
    assert result["verified"] is True
    assert result["evidence"]["target"] == "8.8.8.8"


async def test_verify_network_check_linux_failure(guard_ok, monkeypatch):
    monkeypatch.setattr(
        verifier,
        "_execute_linux_verify_command",
        AsyncMock(return_value="0 packets received, 100 percent packet loss"),
    )
    result = await verifier._verify_network_check(  # noqa: F841  # Variable for test verification
        {"platform": "linux"}, {"target": "8.8.8.8"}, "linux"
    )
    assert result["verified"] is False


async def test_verify_network_check_windows_up(guard_ok, monkeypatch):
    monkeypatch.setattr(
        verifier,
        "_execute_windows_verify_command",
        AsyncMock(return_value="UP"),
    )
    result = await verifier._verify_network_check(  # noqa: F841  # Variable for test verification
        {"platform": "windows"}, {"target": "myhost"}, "windows"
    )
    assert result["verified"] is True


async def test_verify_network_check_missing_target():
    result = await verifier._verify_network_check({"platform": "linux"}, {}, "linux")  # noqa: F841  # Variable for test verification
    assert result["verified"] is None
    assert result["strategy"] == "skipped"


async def test_verify_network_check_invalid_target(guard_ok):
    result = await verifier._verify_network_check(  # noqa: F841  # Variable for test verification
        {"platform": "linux"}, {"target": "bad;target"}, "linux"
    )
    assert "非法网络目标" in result["error_msg"]


async def test_verify_network_check_target_from_alert(guard_ok, monkeypatch):
    monkeypatch.setattr(
        verifier,
        "_execute_linux_verify_command",
        AsyncMock(return_value="1 packets received, 0% packet loss"),
    )
    result = await verifier._verify_network_check(  # noqa: F841  # Variable for test verification
        {"platform": "linux", "host": "8.8.8.8"}, {}, "linux"
    )
    assert result["evidence"]["target"] == "8.8.8.8"


async def test_verify_network_check_target_from_runbook(guard_ok, monkeypatch):
    monkeypatch.setattr(
        verifier,
        "_execute_linux_verify_command",
        AsyncMock(return_value="1 packets received, 0% packet loss"),
    )
    result = await verifier._verify_network_check(  # noqa: F841  # Variable for test verification
        {"platform": "linux"},
        {},
        "linux",
        ai_runbook={"commands": ["ping '8.8.8.8'"]},
    )
    assert result["evidence"]["target"] == "8.8.8.8"


async def test_verify_network_check_guard_blocked(monkeypatch):
    monkeypatch.setattr(verifier, "_check_command_with_guard", lambda cmd: (False, "blocked"))
    result = await verifier._verify_network_check(  # noqa: F841  # Variable for test verification
        {"platform": "linux"}, {"target": "8.8.8.8"}, "linux"
    )
    assert result["strategy"] == "network_check"
    assert "护栏" in result["error_msg"]


async def test_verify_network_check_execute_exception(guard_ok, monkeypatch):
    monkeypatch.setattr(
        verifier,
        "_execute_linux_verify_command",
        AsyncMock(side_effect=RuntimeError("ssh failed")),
    )
    result = await verifier._verify_network_check(  # noqa: F841  # Variable for test verification
        {"platform": "linux"}, {"target": "8.8.8.8"}, "linux"
    )
    assert result["strategy"] == "network_check"
    assert "RuntimeError" in result["error_msg"]


async def test_verify_k8s_status_running_and_ready(guard_ok, short_wait, monkeypatch):
    monkeypatch.setattr(
        verifier,
        "_execute_linux_verify_command",
        AsyncMock(
            return_value=(
                '{"status": {"phase": "Running", '
                '"conditions": [{"type": "Ready", "status": "True"}]}}'
            )
        ),
    )
    result = await verifier._verify_k8s_status(  # noqa: F841  # Variable for test verification
        {"platform": "linux"},
        {"resource": "pod", "name": "web-0"},
        "linux",
    )
    assert result["verified"] is True
    assert result["evidence"]["phase"] == "running"


async def test_verify_k8s_status_plain_text(guard_ok, short_wait, monkeypatch):
    monkeypatch.setattr(
        verifier,
        "_execute_linux_verify_command",
        AsyncMock(return_value="running"),
    )
    result = await verifier._verify_k8s_status({"platform": "linux"}, {"name": "web-0"}, "linux")  # noqa: F841  # Variable for test verification
    assert result["verified"] is True


async def test_verify_k8s_status_succeeded(guard_ok, short_wait, monkeypatch):
    monkeypatch.setattr(
        verifier,
        "_execute_linux_verify_command",
        AsyncMock(return_value='{"status": {"phase": "Succeeded"}}'),
    )
    result = await verifier._verify_k8s_status(  # noqa: F841  # Variable for test verification
        {"platform": "linux"},
        {"resource": "pod", "name": "job-1"},
        "linux",
    )
    assert result["verified"] is True


async def test_verify_k8s_status_failed(guard_ok, short_wait, monkeypatch):
    monkeypatch.setattr(
        verifier,
        "_execute_linux_verify_command",
        AsyncMock(return_value='{"status": {"phase": "Failed"}}'),
    )
    result = await verifier._verify_k8s_status(  # noqa: F841  # Variable for test verification
        {"platform": "linux"},
        {"resource": "pod", "name": "bad-0"},
        "linux",
    )
    assert result["verified"] is False


async def test_verify_k8s_status_missing_name():
    result = await verifier._verify_k8s_status({"platform": "linux"}, {}, "linux")  # noqa: F841  # Variable for test verification
    assert result["verified"] is None
    assert result["strategy"] == "skipped"


async def test_verify_k8s_status_windows_skipped():
    result = await verifier._verify_k8s_status(  # noqa: F841  # Variable for test verification
        {"platform": "windows"}, {"name": "web-0"}, "windows"
    )
    assert result["verified"] is None
    assert "仅支持 Linux" in result["recommendation"]


async def test_verify_k8s_status_guard_blocked(short_wait, monkeypatch):
    monkeypatch.setattr(verifier, "_check_command_with_guard", lambda cmd: (False, "blocked"))
    result = await verifier._verify_k8s_status({"platform": "linux"}, {"name": "web-0"}, "linux")  # noqa: F841  # Variable for test verification
    assert result["strategy"] == "k8s_status"
    assert "护栏" in result["error_msg"]


async def test_verify_k8s_status_execute_exception(guard_ok, short_wait, monkeypatch):
    monkeypatch.setattr(
        verifier,
        "_execute_linux_verify_command",
        AsyncMock(side_effect=RuntimeError("ssh failed")),
    )
    result = await verifier._verify_k8s_status({"platform": "linux"}, {"name": "web-0"}, "linux")  # noqa: F841  # Variable for test verification
    assert result["strategy"] == "k8s_status"
    assert "RuntimeError" in result["error_msg"]


async def test_verify_custom_command_disabled(verify_config):
    result = await verifier._verify_custom_command({}, {}, "linux")  # noqa: F841  # Variable for test verification
    assert result["verified"] is None
    assert result["strategy"] == "skipped"


async def test_verify_custom_command_enabled(monkeypatch, verify_config):
    monkeypatch.setattr(verifier, "VERIFY_CONFIG", {"llm_for_custom": True})
    result = await verifier._verify_custom_command({}, {}, "linux")  # noqa: F841  # Variable for test verification
    assert result["verified"] is None
    assert "LLM 验证逻辑预留" in result["recommendation"]


async def test_verify_repair_disabled(upsert_nop, monkeypatch):
    monkeypatch.setattr(verifier, "VERIFY_CONFIG", {"enabled": False})
    result = await verifier.verify_repair({}, "restart_service", {}, None, "")  # noqa: F841  # Variable for test verification
    assert result["verified"] is None
    assert result["strategy"] == "skipped"


async def test_verify_repair_invalid_alert(verify_config, upsert_nop):
    result = await verifier.verify_repair("bad", "restart_service", {}, None, "")  # noqa: F841  # Variable for test verification
    assert result["strategy"] == "error"
    assert "dict" in result["error_msg"]


async def test_verify_repair_empty_script_key(verify_config, upsert_nop):
    result = await verifier.verify_repair({"platform": "linux"}, "", {}, None, "")  # noqa: F841  # Variable for test verification
    assert result["strategy"] == "error"
    assert "不能为空" in result["error_msg"]


async def test_verify_repair_unknown_script(verify_config, upsert_nop):
    result = await verifier.verify_repair({"platform": "linux"}, "unknown", {}, None, "")  # noqa: F841  # Variable for test verification
    assert result["verified"] is None
    assert result["strategy"] == "skipped"


async def test_verify_repair_invalid_platform_defaults_windows(
    verify_config, upsert_nop, monkeypatch
):
    monkeypatch.setattr(
        verifier,
        "_execute_windows_verify_command",
        AsyncMock(return_value="Running\n"),
    )
    result = await verifier.verify_repair(  # noqa: F841  # Variable for test verification
        {"platform": "mac"}, "restart_service", {"service_name": "w3svc"}, None, ""
    )
    assert result["verified"] is True


async def test_verify_repair_metric_wait_conflict(verify_config, upsert_nop, monkeypatch):
    monkeypatch.setattr(
        verifier,
        "VERIFY_CONFIG",
        {"enabled": True, "timeout_sec": 3.0, "metric_wait_sec": 5.0},
    )
    result = await verifier.verify_repair({"platform": "linux"}, "free_cache", {}, None, "")  # noqa: F841  # Variable for test verification
    assert result["strategy"] == "skipped"
    assert "metric_wait_sec" in result["recommendation"]


async def test_verify_repair_service_status_end_to_end(
    verify_config, upsert_nop, guard_ok, short_wait, monkeypatch
):
    monkeypatch.setattr(
        verifier,
        "_execute_linux_verify_command",
        AsyncMock(return_value="active\n"),
    )
    result = await verifier.verify_repair(  # noqa: F841  # Variable for test verification
        {"platform": "linux"},
        "restart_service",
        {"service_name": "nginx"},
        None,
        "repair output text",
        repair_id=7,
    )
    assert result["verified"] is True
    assert result["strategy"] == "service_status"
    assert result["evidence"]["repair_output_preview"] == "repair output text"
    assert result["confidence"] == 0.95


async def test_verify_repair_metric_threshold_end_to_end(
    verify_config, upsert_nop, guard_ok, monkeypatch
):
    monkeypatch.setattr(asyncio, "sleep", async_noop)
    monkeypatch.setattr(
        "core.metrics_history.metrics_history",
        type("M", (), {"to_dict": lambda self: {"memory": [4.0, 4.0, 4.0]}})(),
    )
    result = await verifier.verify_repair(  # noqa: F841  # Variable for test verification
        {"platform": "linux"},
        "free_cache",
        {},
        {"memory": [10.0, 10.0, 10.0]},
        "repair text",
        repair_id=8,
    )
    assert result["verified"] is True
    assert result["strategy"] == "metric_threshold"
    assert result["evidence"]["repair_output_preview"] == "repair text"


async def test_verify_repair_process_check_end_to_end(
    verify_config, upsert_nop, guard_ok, monkeypatch
):
    monkeypatch.setattr(verifier, "_execute_linux_verify_command", AsyncMock(return_value="0"))
    result = await verifier.verify_repair(  # noqa: F841  # Variable for test verification
        {"platform": "linux"},
        "kill_high_cpu",
        {"pid": "12345"},
        None,
        "",
        repair_id=9,
    )
    assert result["verified"] is True
    assert result["strategy"] == "process_check"


async def test_verify_repair_ai_dynamic_service_status(
    verify_config, upsert_nop, guard_ok, short_wait, monkeypatch
):
    monkeypatch.setattr(
        verifier,
        "_execute_linux_verify_command",
        AsyncMock(return_value="active\n"),
    )
    result = await verifier.verify_repair(  # noqa: F841  # Variable for test verification
        {"platform": "linux"},
        "AI_DYNAMIC",
        {},
        None,
        "",
        ai_runbook={"commands": ["systemctl restart nginx"]},
        repair_id=10,
    )
    assert result["verified"] is True
    assert result["strategy"] == "service_status"


async def test_verify_repair_k8s_status_skipped_on_windows(verify_config, upsert_nop):
    result = await verifier.verify_repair(  # noqa: F841  # Variable for test verification
        {"platform": "windows"},
        "k8s_pod_crash",
        {"name": "web-0"},
        None,
        "",
        repair_id=11,
    )
    assert result["verified"] is None
    assert "仅支持 Linux" in result["recommendation"]


async def test_verify_repair_timeout(verify_config, upsert_nop, guard_ok, monkeypatch):
    monkeypatch.setattr(asyncio, "wait_for", AsyncMock(side_effect=asyncio.TimeoutError))
    result = await verifier.verify_repair(  # noqa: F841  # Variable for test verification
        {"platform": "linux"},
        "restart_service",
        {"service_name": "nginx"},
        None,
        "",
        repair_id=12,
    )
    assert result["strategy"] == "timeout"
    assert "超时" in result["error_msg"]


async def test_verify_repair_cancelled(verify_config, upsert_nop, guard_ok, monkeypatch):
    monkeypatch.setattr(asyncio, "wait_for", AsyncMock(side_effect=asyncio.CancelledError))
    with pytest.raises(asyncio.CancelledError):
        await verifier.verify_repair(
            {"platform": "linux"},
            "restart_service",
            {"service_name": "nginx"},
            None,
            "",
            repair_id=13,
        )


async def test_verify_repair_dispatch_exception(verify_config, upsert_nop, guard_ok, monkeypatch):
    monkeypatch.setattr(
        verifier,
        "_dispatch_verification",
        AsyncMock(side_effect=RuntimeError("boom")),
    )
    result = await verifier.verify_repair(  # noqa: F841  # Variable for test verification
        {"platform": "linux"},
        "restart_service",
        {"service_name": "nginx"},
        None,
        "",
        repair_id=14,
    )
    assert result["strategy"] == "error"
    assert "RuntimeError" in result["error_msg"]


async def test_verify_repair_upsert_exception(verify_config, guard_ok, monkeypatch):
    monkeypatch.setattr(
        verifier,
        "_dispatch_verification",
        AsyncMock(
            return_value={
                "verified": True,
                "strategy": "service_status",
                "confidence": 0.95,
                "evidence": {"command": "cmd"},
                "duration_sec": 1.5,
                "error_msg": "",
                "recommendation": "ok",
            }
        ),
    )
    monkeypatch.setattr(
        verifier,
        "upsert_verify_record",
        MagicMock(side_effect=RuntimeError("upsert boom")),
    )
    result = await verifier.verify_repair(  # noqa: F841  # Variable for test verification
        {"platform": "linux"},
        "restart_service",
        {"service_name": "nginx"},
        None,
        "out",
        repair_id=15,
    )
    assert result["verified"] is True
    assert result["strategy"] == "service_status"


async def test_verify_repair_coerces_input_types(verify_config, upsert_nop, guard_ok, monkeypatch):
    monkeypatch.setattr(
        verifier, "_execute_linux_verify_command", AsyncMock(return_value="active\n")
    )
    result = await verifier.verify_repair(  # noqa: F841  # Variable for test verification
        {"platform": "linux"},
        "AI_DYNAMIC",
        "not-a-dict",
        [1, 2, 3],
        12345,
        ai_runbook={"commands": ["systemctl restart nginx"]},
        repair_id=16,
    )
    assert result["verified"] is True
    assert result["evidence"]["repair_output_preview"] == "12345"


async def test_verify_repair_preview_not_overwritten(verify_config, guard_ok, monkeypatch):
    monkeypatch.setattr(
        verifier,
        "_dispatch_verification",
        AsyncMock(
            return_value={
                "verified": True,
                "strategy": "service_status",
                "confidence": 0.95,
                "evidence": {
                    "command": "cmd",
                    "repair_output_preview": "already-here",
                },
                "duration_sec": 1.5,
                "error_msg": "",
                "recommendation": "ok",
            }
        ),
    )
    monkeypatch.setattr(verifier, "upsert_verify_record", lambda *a, **k: None)
    result = await verifier.verify_repair(  # noqa: F841  # Variable for test verification
        {"platform": "linux"},
        "restart_service",
        {"service_name": "nginx"},
        None,
        "new-output",
        repair_id=17,
    )
    assert result["duration_sec"] == 1.5
    assert result["evidence"]["repair_output_preview"] == "already-here"
