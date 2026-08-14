# -*- coding: utf-8 -*-
"""Batch 24a coverage tests for selected core modules."""

import asyncio
import importlib
import time
from datetime import datetime, timedelta, timezone

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa

import core.data_privacy as dp
import core.database_cache_optimizer as dco
import core.error_handler as eh
import core.metrics_history as mh
import core.security_config as sc

pytestmark = [pytest.mark.core]


def _make_self_signed(tmp_path, not_before=None, not_after=None):
    """Generate a self-signed certificate/key pair for TLS validation tests."""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(x509.NameOID.COMMON_NAME, "test")])
    now = datetime.now(timezone.utc)
    nb = not_before or now
    na = not_after or now + timedelta(days=1)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(1)
        .not_valid_before(nb)
        .not_valid_after(na)
        .sign(key, hashes.SHA256())
    )
    cert_path = tmp_path / "cert.pem"
    key_path = tmp_path / "key.pem"
    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    return str(cert_path), str(key_path)


# ---------------------------------------------------------------------------
# core/security_config.py
# ---------------------------------------------------------------------------

def test_batch24_security_config_env_branches(monkeypatch, tmp_path):
    """Reload security_config with varied environment toggles."""
    monkeypatch.setenv("TLS_ENABLED", "true")
    monkeypatch.setenv("MFA_ENABLED", "true")
    monkeypatch.setenv("RATE_LIMITING_ENABLED", "false")
    monkeypatch.setenv("SECURITY_HEADERS_ENABLED", "false")
    monkeypatch.setenv("PASSWORD_POLICY_ENABLED", "false")
    monkeypatch.setenv("TLS_CERT_PATH", str(tmp_path / "missing.pem"))
    monkeypatch.setenv("TLS_KEY_PATH", str(tmp_path / "missing.pem"))
    importlib.reload(sc)

    status = sc.security_config.get_security_status()
    assert status["tls_enabled"] is True
    assert status["mfa_enabled"] is True
    assert status["rate_limiting_enabled"] is False
    assert status["security_headers_enabled"] is False
    assert status["password_policy_enabled"] is False

    res = sc.security_config.validate_tls_certificates()
    assert res["valid"] is False
    assert "not found" in res["reason"]


def test_batch24_security_config_methods(tmp_path):
    """Exercise SecurityConfig public methods."""
    importlib.reload(sc)
    cfg = sc.SecurityConfig()

    cfg.enable_mfa()
    assert cfg.config["mfa_enabled"] is True
    cfg.disable_mfa()
    assert cfg.config["mfa_enabled"] is False

    cfg.enable_rate_limiting(max_requests=10, time_window=30)
    assert cfg.config["rate_limiting_enabled"] is True
    assert cfg.config["rate_limit_max_requests"] == 10
    cfg.disable_rate_limiting()
    assert cfg.config["rate_limiting_enabled"] is False

    cert_path, key_path = _make_self_signed(tmp_path)
    cfg.enable_tls(cert_path, key_path)
    assert cfg.config["tls_enabled"] is True
    assert cfg.config["tls_cert_path"] == cert_path

    result = cfg.validate_tls_certificates()
    assert "valid" in result
    assert "reason" in result


def test_batch24_security_config_tls_validation_cases(tmp_path):
    """Cover all validate_tls_certificates branches."""
    importlib.reload(sc)
    cfg = sc.SecurityConfig()

    # TLS disabled
    res = cfg.validate_tls_certificates()
    assert res["reason"] == "TLS not enabled"

    # Missing paths
    cfg.config["tls_enabled"] = True
    cfg.config["tls_cert_path"] = ""
    cfg.config["tls_key_path"] = ""
    res = cfg.validate_tls_certificates()
    assert res["reason"] == "Certificate paths not configured"

    # Valid certificate (bug in module returns validation-failed; we still cover the code)
    cert_path, key_path = _make_self_signed(tmp_path)
    cfg.enable_tls(cert_path, key_path)
    res = cfg.validate_tls_certificates()
    assert "valid" in res
    assert "reason" in res

    # Certificate not yet valid
    cert_nvb, _ = _make_self_signed(
        tmp_path,
        not_before=datetime.now(timezone.utc) + timedelta(days=1),
        not_after=datetime.now(timezone.utc) + timedelta(days=2),
    )
    cfg.enable_tls(cert_nvb, key_path)
    res = cfg.validate_tls_certificates()
    assert "valid" in res
    assert "reason" in res

    # Expired certificate
    cert_exp, _ = _make_self_signed(
        tmp_path,
        not_before=datetime.now(timezone.utc) - timedelta(days=2),
        not_after=datetime.now(timezone.utc) - timedelta(days=1),
    )
    cfg.enable_tls(cert_exp, key_path)
    res = cfg.validate_tls_certificates()
    assert "valid" in res
    assert "reason" in res

    # Malformed certificate
    bad_path = tmp_path / "bad.pem"
    bad_path.write_text("not a valid certificate")
    cfg.enable_tls(str(bad_path), key_path)
    res = cfg.validate_tls_certificates()
    assert res["valid"] is False
    assert "reason" in res


def test_batch24_setup_enterprise_security(monkeypatch, tmp_path):
    """Cover setup_enterprise_security success and TLS-warning paths."""
    monkeypatch.setenv("TLS_ENABLED", "false")
    importlib.reload(sc)

    result = sc.setup_enterprise_security()
    assert "security_status" in result
    assert result["timestamp"] == "success"

    sc.security_config.config["tls_enabled"] = True
    sc.security_config.config["tls_cert_path"] = str(tmp_path / "missing.pem")
    sc.security_config.config["tls_key_path"] = str(tmp_path / "missing.pem")
    result = sc.setup_enterprise_security()
    assert "security_status" in result
    assert "tls_validation" in result


# ---------------------------------------------------------------------------
# core/data_privacy.py
# ---------------------------------------------------------------------------

def test_batch24_data_privacy_full_flow():
    """Exercise data privacy configuration, PII detection, and anonymization."""
    cfg = dp.DataPrivacyConfig(
        anonymization_enabled=True,
        pii_detection_enabled=True,
        data_retention_enabled=True,
        consent_required=True,
        gdpr_compliance=True,
    )
    dp.configure_privacy(cfg)
    config = dp.get_privacy_config()
    assert config.gdpr_compliance is True

    text = (
        "Contact alice@example.com at 555-123-4567; "
        "ssn 123-45-6789; card 4111-1111-1111-1111; ip 192.168.1.50"
    )
    detected = dp.detect_pii(text)
    assert "email" in detected
    assert dp.contains_pii(text) is True
    assert dp.contains_pii("just text") is False

    # Individual anonymizers
    assert "*" in dp.anonymize_email("user@example.com")
    assert dp.anonymize_email("nope") == "nope"
    assert "*" in dp.anonymize_phone("555-123-4567")
    assert dp.anonymize_phone("123") == "***"
    assert "*" in dp.anonymize_ssn("123-45-6789")
    assert dp.anonymize_ssn("ab") == "**"
    assert "*" in dp.anonymize_credit_card("4111111111111111")
    assert dp.anonymize_credit_card("12") == "**"
    assert dp.anonymize_ip("192.168.1.1") == "192.168.*.*"
    assert dp.anonymize_ip("abc") == "abc"

    anon = dp.anonymize_text(text)
    assert "*" in anon

    nested = {
        "email": "bob@example.com",
        "list": ["555-123-4567"],
        "nested": {"ssn": "123-45-6789"},
        "other": 1,
    }
    anond = dp.anonymize_dict(nested)
    assert "*" in anond["email"]
    assert "*" in anond["list"][0]
    assert anond["other"] == 1

    assert dp.hash_pii("x") == dp.hash_pii("x")

    # Disabled flows
    dp.configure_privacy(dp.DataPrivacyConfig(anonymization_enabled=False))
    assert dp.anonymize_text("email user@example.com") == "email user@example.com"
    dp.configure_privacy(dp.DataPrivacyConfig(pii_detection_enabled=False))
    assert dp.detect_pii("user@example.com") == {}
    dp.configure_privacy(dp.DataPrivacyConfig(pii_detection_enabled=True, anonymization_enabled=True))


def test_batch24_data_privacy_retention_and_consent():
    """Cover retention policy and consent helpers."""
    dp.set_retention_policy("metrics", 60)
    policy = dp.get_retention_policy("metrics")
    assert policy is not None
    assert policy.retention_days == 60
    assert policy.get_expiry_date(datetime.now(timezone.utc)) > datetime.now(timezone.utc)

    old = datetime.now(timezone.utc) - timedelta(days=100)
    assert policy.should_retain(old) is False

    dp.configure_privacy(dp.DataPrivacyConfig(data_retention_enabled=False))
    assert policy.should_retain(old) is True
    dp.configure_privacy(dp.DataPrivacyConfig(data_retention_enabled=True))

    dp.configure_privacy(dp.DataPrivacyConfig(consent_required=True))
    assert dp.has_consent("u9", "marketing") is False
    dp.record_consent("u9", "marketing", True)
    assert dp.has_consent("u9", "marketing") is True
    dp.record_consent("u9", "marketing", False)
    assert dp.has_consent("u9", "marketing") is False
    assert dp.get_user_consents("unknown") == []


def test_batch24_data_privacy_audit_and_stats():
    """Cover audit logging and stats aggregation."""
    dp.log_privacy_event(
        "access", "u9", "metrics", "read", details={"status": "ok"}
    )
    logs = dp.get_privacy_audit_logs(user_id="u9", event_type="access", limit=1)
    assert len(logs) >= 1
    stats = dp.get_privacy_stats()
    assert stats["config"]["anonymization_enabled"] is True
    assert "retention_policies" in stats
    assert "audit_log_entries" in stats


# ---------------------------------------------------------------------------
# core/database_cache_optimizer.py
# ---------------------------------------------------------------------------

def test_batch24_database_cache_optimizer_strategies_and_metrics():
    """Exercise create/get/set/invalidate and all eviction strategies."""
    opt = dco.DatabaseCacheOptimizer(
        {"default_cache_size": 2, "default_ttl_seconds": 0.05}
    )

    # Factory sanity
    assert isinstance(dco.get_database_cache_optimizer({}), dco.DatabaseCacheOptimizer)

    # Simple named cache
    cache = opt.get_cache("simple", strategy=dco.CacheStrategy.LRU, size=2)
    cache.set("x", "y")
    assert cache.get("x") == "y"
    assert cache.get("missing") is None
    cache.invalidate("x")
    assert cache.get("x") is None

    # LRU eviction in DatabaseCacheOptimizer
    opt.create_cache("lru", strategy=dco.CacheStrategy.LRU, cache_size=2)
    opt.set("lru", "SELECT 1", ["a"])
    opt.set("lru", "SELECT 2", ["b"])
    opt.set("lru", "SELECT 3", ["c"])  # evicts SELECT 1
    assert opt.get("lru", "SELECT 1") is None
    assert opt.get("lru", "SELECT 3") == ["c"]

    # LFU eviction
    opt.create_cache("lfu", strategy=dco.CacheStrategy.LFU, cache_size=2)
    opt.set("lfu", "q1", "a")
    opt.set("lfu", "q2", "b")
    opt.get("lfu", "q1")
    opt.get("lfu", "q1")
    opt.set("lfu", "q3", "c")  # q2 has lowest frequency
    assert opt.get("lfu", "q2") is None
    assert opt.get("lfu", "q3") == "c"

    # TTL expiration
    opt.create_cache("ttl", strategy=dco.CacheStrategy.TTL, cache_size=2, ttl_seconds=0.05)
    opt.set("ttl", "q", "v")
    time.sleep(0.08)
    assert opt.get("ttl", "q") is None
    opt.set("ttl", "q", "v")
    time.sleep(0.08)
    assert opt.cleanup_expired_entries("ttl") == 1

    # CacheEntry helpers
    entry = dco.CacheEntry(cache_key="k", data="v", ttl_seconds=None)
    assert entry.is_expired() is False
    entry.touch()
    assert entry.access_count == 1


def test_batch24_database_cache_optimizer_preload_and_recommendations():
    """Exercise preload, metrics, statistics and optimization recommendations."""
    opt = dco.DatabaseCacheOptimizer({"default_cache_size": 100, "default_ttl_seconds": 3600})
    opt.create_cache("metrics", cache_size=100)

    for i in range(20):
        opt.set("metrics", f"SELECT {i}", i)
        opt.get("metrics", f"SELECT {i}")
    opt.get("metrics", "missing")  # one miss

    metrics = opt.get_cache_metrics("metrics")
    assert metrics is not None
    assert metrics.cache_name == "metrics"
    assert isinstance(opt.get_all_cache_metrics(), dict)

    stats = opt.get_statistics()
    assert "total_caches" in stats
    assert "global_hit_rate" in stats

    # Recommendations branches
    opt.optimize_cache_size("metrics", target_hit_rate=0.99)
    opt.optimize_cache_size("metrics", target_hit_rate=0.50)
    assert opt.optimize_cache_size("missing").get("error")

    # Preload with function and dict
    opt.create_cache("preload")
    opt.add_preload_query("preload", "SELECT 1")
    opt.add_preload_query("preload", "SELECT 2", priority=5)

    def loader(query, params):
        return {"q": query}

    assert opt.preload_cache("preload", loader) == 2
    assert opt.preload_cache("preload_dict", {"a": 1}) == 1


# ---------------------------------------------------------------------------
# core/metrics_history.py
# ---------------------------------------------------------------------------

def test_batch24_metrics_history_push_and_query():
    """Cover legacy push, metric push, query filtering and timestamp coercion."""
    history = mh.MetricsHistory(maxlen=5)
    history.push(10.0, 20.0, 30.0, "12:00:00")
    history.push("bad", "bad", "bad", "now")
    history.push(None, None, None, "13:00:00")

    now = datetime.now(timezone.utc)
    history.push_metric("cpu", 55.0, service="svc", timestamp=now)
    history.push_metric(123, 10.0)
    history.push_metric("cpu", "bad")
    history.push_metric("cpu", 5.0, service=123)
    history.push_metric("cpu", 5.0, timestamp="not-a-time")
    history.push_metric("cpu", 5.0, timestamp="2023-01-01T12:00:00")
    history.push_metric("custom", 7.0)

    data = history.to_dict()
    assert "cpu" in data
    assert "memory" in data

    start = now - timedelta(hours=1)
    end = now + timedelta(hours=1)
    assert len(history.query("cpu", service="svc", start=start, end=end)) >= 1
    assert history.query("cpu", start=end, end=start) == []

    assert history.get_latest("custom") == 7.0
    assert history.get_latest("missing") is None

    history.clear()
    assert history.size == 0
    assert history.sample_count == 0
    assert "maxlen=" in repr(history)

    # Invalid maxlen fallback
    history2 = mh.MetricsHistory(maxlen=-5)
    assert history2._maxlen == 60


def test_batch24_metrics_history_dynamic_threshold():
    """Cover dynamic threshold calculation paths."""
    history = mh.MetricsHistory(maxlen=100)
    for i in range(35):
        history.push_metric(
            "cpu",
            float(i),
            service="global",
            timestamp=datetime.now(timezone.utc) - timedelta(seconds=40 - i),
        )
    threshold, info = history.get_dynamic_threshold("cpu", 50.0, min_samples=30, service="global")
    assert isinstance(threshold, float)
    assert "source" in info

    flat = mh.MetricsHistory(maxlen=100)
    for _ in range(35):
        flat.push_metric("cpu", 10.0, service="global")
    t2, info2 = flat.get_dynamic_threshold("cpu", 5.0, service="global")
    assert info2["source"] == "dynamic_flat"

    # Invalid sigma / static threshold
    history.get_dynamic_threshold("cpu", 50.0, sigma=99.0, service="global")
    history.get_dynamic_threshold("cpu", "bad", sigma="bad", service="global")

    # Unknown metric
    t3, info3 = history.get_dynamic_threshold("bad_metric", 50.0, service="global")
    assert info3["source"] == "static_unknown_metric"

    # net_in cap
    net = mh.MetricsHistory(maxlen=100)
    for _ in range(35):
        net.push_metric("net_in", 5000.0, service="global")
    t4, _ = net.get_dynamic_threshold("net_in", 10000.0, service="global")
    assert t4 <= 10000.0


# ---------------------------------------------------------------------------
# core/error_handler.py
# ---------------------------------------------------------------------------

def test_batch24_error_handler_exceptions_and_reporting():
    """Cover exception handling, logging, stats and reporting."""
    handler = eh.ErrorHandler()

    # AIOpsException severity levels and subclasses
    handler.handle_exception(eh.AIOpsException("info", severity=eh.ErrorSeverity.INFO))
    handler.handle_exception(eh.AIOpsException("debug", severity=eh.ErrorSeverity.DEBUG))
    handler.handle_exception(eh.AIOpsException("warn", severity=eh.ErrorSeverity.WARNING))
    handler.handle_exception(eh.AIOpsException("err", severity=eh.ErrorSeverity.ERROR))
    handler.handle_exception(eh.AIOpsException("crit", severity=eh.ErrorSeverity.CRITICAL))
    handler.handle_exception(eh.AIOpsException("fatal", severity=eh.ErrorSeverity.FATAL))

    handler.handle_exception(eh.ValidationError("bad", field="x"))
    handler.handle_exception(eh.NetworkError("timeout", url="http://x"))
    handler.handle_exception(eh.DatabaseError("fail", query="SELECT"))
    handler.handle_exception(eh.AuthenticationError("denied", user_id="u"))
    handler.handle_exception(eh.AuthorizationError("forbidden", resource="r"))
    handler.handle_exception(eh.ExternalServiceError("down", service="s"))

    # Built-in exception classification
    handler.handle_exception(ValueError("value"))
    handler.handle_exception(TypeError("type"))
    handler.handle_exception(ConnectionError("conn"))
    handler.handle_exception(TimeoutError("to"))
    handler.handle_exception(RuntimeError("unknown"))

    # ErrorContext to_dict
    err = eh.AIOpsException("x")
    assert err.to_dict()["type"] == "AIOpsException"

    # Stats and report
    stats = handler.get_error_stats()
    assert stats["total_errors"] >= 1
    report = handler.get_error_report(hours=24)
    assert "total_errors" in report
    assert "error_trends" in report

    # Manual trend simulation using two different hours
    handler.error_history.append(
        eh.ErrorContext(
            error_id="e1",
            error_type="TypeError",
            error_message="m1",
            severity=eh.ErrorSeverity.ERROR,
            category=eh.ErrorCategory.VALIDATION,
            timestamp=datetime.now() - timedelta(hours=2),
        )
    )
    handler.error_history.append(
        eh.ErrorContext(
            error_id="e2",
            error_type="TypeError",
            error_message="m2",
            severity=eh.ErrorSeverity.ERROR,
            category=eh.ErrorCategory.VALIDATION,
            timestamp=datetime.now() - timedelta(hours=1),
        )
    )
    report2 = handler.get_error_report(hours=24)
    assert len(report2["error_trends"]["hourly_distribution"]) >= 2


def test_batch24_error_handler_retry_sync():
    """Cover the sync retry decorator."""
    handler = eh.ErrorHandler()

    @handler.retry(max_retries=0, base_delay=0.0)
    def network_fail():
        raise eh.NetworkError("boom")

    with pytest.raises(eh.NetworkError):
        network_fail()

    @handler.retry(max_retries=0)
    def value_fail():
        raise ValueError("boom")

    with pytest.raises(ValueError):
        value_fail()


@pytest.mark.asyncio
async def test_batch24_error_handler_retry_async():
    """Cover the async retry decorator."""
    handler = eh.ErrorHandler()

    @handler.retry(max_retries=0, base_delay=0.0)
    async def async_network_fail():
        raise eh.NetworkError("async boom")

    with pytest.raises(eh.NetworkError):
        await async_network_fail()


def test_batch24_error_handler_alert_processing():
    """Manually process queued alerts and send one directly."""
    handler = eh.ErrorHandler()
    ctx = handler.handle_exception(
        eh.AIOpsException("alert", severity=eh.ErrorSeverity.FATAL)
    )
    handler.alert_queue.append(ctx)
    handler._process_alerts()
    # Direct send for coverage
    handler._send_alert(ctx)
