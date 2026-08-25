# -*- coding: utf-8 -*-
"""Functional coverage tests for batch14_b core modules."""

import asyncio  # noqa: F401  # Imported for test setup
import itertools
import json  # noqa: F401  # Imported for test setup
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest  # noqa: F401  # Imported for test setup
from fastapi import FastAPI
from fastapi.testclient import TestClient

import core.api_performance as api_performance
import core.es_logger as es_logger
import core.plugin_system_manager as plugin_system
import core.rate_limiter as rate_limiter
from core.error_logging.alerting import (
    EmailAlertChannel,
    ErrorAlertManager,
    SlackAlertChannel,
    check_error_alerts,
    get_error_alert_manager,
)
from core.rate_limiter import (
    AdvancedRateLimiter,
    ConcurrencyLimiter,
    SessionLimiter,
    add_concurrency_middleware,
    check_rate_limit,
    get_advanced_rate_limiter,
    get_concurrency_limiter,
    get_limiter,
    get_rate_limit_for_endpoint,
    get_session_limiter,
)

pytestmark = [pytest.mark.core]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def _reset_es_logger(monkeypatch):
    """Reset ES logger singleton and cache between tests."""
    monkeypatch.setattr(es_logger, "_es_client", None)
    monkeypatch.setattr(es_logger, "_es_query_cache", es_logger.QueryCache())


@pytest.fixture
def fresh_limiters(monkeypatch):
    """Provide fresh concurrency/session limiters."""
    con = ConcurrencyLimiter()
    sess = SessionLimiter()
    monkeypatch.setattr(rate_limiter, "_global_concurrency_limiter", con)
    monkeypatch.setattr(rate_limiter, "_global_session_limiter", sess)
    return con, sess


# ---------------------------------------------------------------------------
# core.rate_limiter
# ---------------------------------------------------------------------------
def test_get_limiter_initializes_and_singleton(monkeypatch):
    monkeypatch.setattr(rate_limiter, "_limiter", None)
    limiter = get_limiter()
    assert limiter is not None
    assert get_limiter() is limiter


def test_get_limiter_failure_returns_none(monkeypatch):
    import slowapi

    monkeypatch.setattr(rate_limiter, "_limiter", None)
    monkeypatch.setattr(slowapi, "Limiter", MagicMock(side_effect=Exception("no limiter")))
    assert get_limiter() is None


def test_get_rate_limit_for_endpoint_categories(monkeypatch):
    monkeypatch.setattr("config.RATE_LIMIT_AUTH_PER_MINUTE", 5, raising=False)
    monkeypatch.setattr("config.RATE_LIMIT_SENSITIVE_PER_MINUTE", 3, raising=False)
    monkeypatch.setattr("config.RATE_LIMIT_ADMIN_PER_MINUTE", 200, raising=False)
    monkeypatch.setattr("config.RATE_LIMIT_AI_PER_MINUTE", 25, raising=False)
    monkeypatch.setattr("config.RATE_LIMIT_API_PER_MINUTE", 60, raising=False)

    assert get_rate_limit_for_endpoint("/auth/login") == "5/minute"
    assert get_rate_limit_for_endpoint("/api/v1/repairs/execute") == "3/minute"
    assert get_rate_limit_for_endpoint("/admin/dashboard") == "200/minute"
    assert get_rate_limit_for_endpoint("/api/ai/predict") == "25/minute"
    assert get_rate_limit_for_endpoint("/api/health") == "60/minute"


def test_check_rate_limit(monkeypatch):
    request = MagicMock()
    request.url.path = "/api/health"

    monkeypatch.setattr("config.RATE_LIMIT_ENABLED", False, raising=False)
    assert check_rate_limit(request) is True

    monkeypatch.setattr("config.RATE_LIMIT_ENABLED", True, raising=False)
    monkeypatch.setattr(rate_limiter, "_limiter", None)
    monkeypatch.setattr(rate_limiter, "get_limiter", MagicMock(side_effect=Exception("boom")))
    assert check_rate_limit(request) is True


@pytest.mark.asyncio
async def test_advanced_rate_limiter_algorithms():
    limiter = AdvancedRateLimiter()

    allowed, _ = await limiter.check_rate_limit_advanced("k1", 2, window=60)
    assert allowed is True
    allowed, _ = await limiter.check_rate_limit_advanced("k1", 2, window=60)
    assert allowed is True
    allowed, msg = await limiter.check_rate_limit_advanced("k1", 2, window=60)
    assert allowed is False
    assert "exceeded" in msg

    allowed, _ = await limiter.check_rate_limit_advanced(
        "k2", 2, window=60, algorithm="token_bucket"
    )
    assert allowed is True

    allowed, _ = await limiter.check_rate_limit_advanced("k2", 2, window=60, algorithm="unknown")
    assert allowed is True

    limiter.reset_key("k1")
    assert limiter.get_stats("k1")["request_count"] == 0


@pytest.mark.asyncio
async def test_advanced_rate_limiter_blocked():
    limiter = AdvancedRateLimiter()
    now = 1000.0
    monkeypatch_local = pytest.MonkeyPatch()
    monkeypatch_local.setattr(rate_limiter.time, "time", lambda: now)
    try:
        limiter._blocked["k3"] = now + 10
        allowed, msg = await limiter.check_rate_limit_advanced("k3", 2)
        assert allowed is False
        assert "Try again" in msg
    finally:
        monkeypatch_local.undo()


@pytest.mark.asyncio
async def test_concurrency_limiter():
    con = ConcurrencyLimiter()
    assert await con.acquire("host", 2) is True
    assert await con.acquire("host", 2) is True
    assert await con.acquire("host", 2) is False
    await con.release("host")
    await con.release("host")
    await con.release("host")


@pytest.mark.asyncio
async def test_session_limiter(fresh_limiters, monkeypatch):
    _, sess = fresh_limiters
    exporter = MagicMock()
    exporter.record_active_sessions = MagicMock()
    monkeypatch.setattr(rate_limiter, "get_metrics_exporter", lambda: exporter)
    assert await sess.check_and_register("user1", 1) is True
    assert await sess.check_and_register("user1", 1) is False
    await sess.unregister("user1")
    assert await sess.check_and_register("user1", 1) is True
    assert exporter.record_active_sessions.called


def test_add_concurrency_middleware(fresh_limiters, monkeypatch):
    con, _ = fresh_limiters
    monkeypatch.setenv("AIOPS_MAX_CONCURRENT", "0")
    monkeypatch.setenv("AIOPS_MAX_SESSIONS", "5")

    app = FastAPI()
    add_concurrency_middleware(app)

    @app.get("/test")
    def route():
        return {"ok": True}

    client = TestClient(app)
    resp = client.get("/test")
    assert resp.status_code == 503

    # Options preflight should bypass the limiter.
    resp_options = client.options("/test")
    assert resp_options.status_code in (200, 405)


# ---------------------------------------------------------------------------
# core.es_logger
# ---------------------------------------------------------------------------
def test_get_es_client_instantiates(monkeypatch):
    monkeypatch.setattr(es_logger, "AsyncElasticsearch", MagicMock)
    monkeypatch.setattr(es_logger, "_es_client", None)
    client = es_logger.get_es_client()
    assert client is not None
    assert es_logger.get_es_client() is client


@pytest.mark.asyncio
async def test_index_log_with_client(monkeypatch):
    fake_client = MagicMock()
    fake_client.index = AsyncMock(return_value={"_id": "doc-123"})
    monkeypatch.setattr(es_logger, "_es_client", fake_client)
    doc_id = await es_logger.index_log("logs", {"msg": "hello"})
    assert doc_id == "doc-123"
    fake_client.index.assert_awaited_once()


@pytest.mark.asyncio
async def test_index_log_fallback_and_search(tmp_path, monkeypatch):
    # Simulate ES being unavailable by having the client constructor return None.
    monkeypatch.setattr(es_logger, "_es_client", None)
    monkeypatch.setattr(es_logger, "AsyncElasticsearch", MagicMock(return_value=None))
    monkeypatch.setattr(
        es_logger,
        "Path",
        lambda p: tmp_path / p,
    )

    doc_id = await es_logger.index_log("logs", {"msg": "fallback"})
    assert doc_id is not None
    fallback_file = tmp_path / "data" / "es_fallback" / "logs.ndjson"
    assert fallback_file.exists()

    result = await es_logger.es_search_logs(
        "logs", query="~", size=10
    )  # noqa: F841  # Variable for test verification
    assert result == []  # noqa: F841  # Variable for test verification


@pytest.mark.asyncio
async def test_es_search_logs_with_client(monkeypatch):
    fake_client = MagicMock()
    fake_client.search = AsyncMock(
        return_value={"hits": {"hits": [{"_source": {"message": "ok"}}]}}
    )
    monkeypatch.setattr(es_logger, "_es_client", fake_client)

    result = await es_logger.es_search_logs(
        "logs", query="*", size=10
    )  # noqa: F841  # Variable for test verification
    assert len(result) >= 1
    fake_client.search.assert_awaited_once()


@pytest.mark.asyncio
async def test_es_search_logs_not_found(monkeypatch):
    fake_client = MagicMock()
    fake_client.search = AsyncMock(side_effect=Exception("not found"))
    monkeypatch.setattr(es_logger, "_es_client", fake_client)
    result = await es_logger.es_search_logs(
        "logs", query="*", size=10
    )  # noqa: F841  # Variable for test verification
    assert result == []  # noqa: F841  # Variable for test verification


# ---------------------------------------------------------------------------
# core.error_logging.alerting
# ---------------------------------------------------------------------------
def test_email_alert_channel_success(monkeypatch):
    class FakeSMTP:
        def __init__(self, host, port):
            self.host = host
            self.port = port

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        starttls = MagicMock()
        login = MagicMock()
        send_message = MagicMock()

    monkeypatch.setattr("core.error_logging.alerting.smtplib.SMTP", FakeSMTP)
    ch = EmailAlertChannel(
        "smtp.example.com",
        587,
        "u",
        "p",
        "from@example.com",
        ["to@example.com"],
    )
    ch.send_alert("boom")
    assert FakeSMTP.starttls.called
    FakeSMTP.login.assert_called_once_with("u", "p")
    assert FakeSMTP.send_message.called


def test_email_alert_channel_failure(monkeypatch):
    monkeypatch.setattr(
        "core.error_logging.alerting.smtplib.SMTP",
        MagicMock(side_effect=Exception("smtp down")),
    )
    ch = EmailAlertChannel(
        "smtp.example.com",
        587,
        "u",
        "p",
        "from@example.com",
        ["to@example.com"],
    )
    ch.send_alert("boom")  # should not raise


def test_slack_alert_channel_success(monkeypatch):
    post = MagicMock()
    monkeypatch.setattr("requests.post", post)
    ch = SlackAlertChannel("https://hooks.slack.com/test", "#alerts")
    ch.send_alert("boom", {"k1": "v1"})
    post.assert_called_once()


def test_slack_alert_channel_failure(monkeypatch):
    post = MagicMock(side_effect=Exception("slack down"))
    monkeypatch.setattr("requests.post", post)
    ch = SlackAlertChannel("https://hooks.slack.com/test", "#alerts")
    ch.send_alert("boom")  # should not raise


def test_error_alert_manager_check_alerts():
    handler = MagicMock()
    handler.get_error_count.return_value = 1000
    handler.get_error_rate.return_value = 25.0
    handler.get_top_errors.return_value = [("E500", 100)]

    manager = ErrorAlertManager(handler)
    manager.set_threshold("total_errors", 1)
    manager.set_threshold("error_rate", 1)
    manager.set_threshold("specific_error", 1)

    channel = MagicMock()
    manager.add_alert_channel(channel)
    manager.check_alerts()

    assert channel.send_alert.call_count == 3


def test_get_error_alert_manager_and_check_error_alerts(monkeypatch):
    handler = MagicMock()
    handler.get_error_count.return_value = 50
    handler.get_error_rate.return_value = 0.0
    handler.get_top_errors.return_value = []

    monkeypatch.setattr("core.error_logging.get_error_log_handler", lambda: handler)
    monkeypatch.setattr("core.error_logging.alerting._error_alert_manager", None)
    manager = get_error_alert_manager()
    assert manager is not None
    check_error_alerts()


# ---------------------------------------------------------------------------
# core.api_performance
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_monitor_api_performance(monkeypatch):
    times = itertools.cycle([0.0, 0.3, 0.0, 2.5])
    monkeypatch.setattr(api_performance.time, "time", lambda: next(times))

    @api_performance.monitor_api_performance
    async def fast_fn():
        return "ok"

    @api_performance.monitor_api_performance
    async def slow_fn():
        return "slow"

    try:
        assert await fast_fn() == "ok"
        assert "fast_fn" in api_performance.API_PERFORMANCE_STATS

        assert await slow_fn() == "slow"
        assert "slow_fn" in api_performance.API_PERFORMANCE_STATS
    finally:
        api_performance.API_PERFORMANCE_STATS.clear()


# ---------------------------------------------------------------------------
# core.plugin_system_manager
# ---------------------------------------------------------------------------
def test_plugin_interface_spec():
    psm = plugin_system.PluginSystemManager()
    psm.define_plugin_interface(
        "int-1",
        "My Interface",
        [{"name": "m1"}],
        [{"name": "e1"}],
        {"cfg": {}},
    )

    assert psm.generate_plugin_interface_spec("monitoring")["interface_type"] == "monitoring"
    assert psm.generate_plugin_interface_spec("integration")["interface_type"] == "integration"
    assert psm.generate_plugin_interface_spec("ai")["interface_type"] == "ai"
    assert psm.generate_plugin_interface_spec("custom")["interface_type"] == "custom"


def test_plugin_register_enable_disable():
    psm = plugin_system.PluginSystemManager()

    meta = plugin_system.PluginMetadata(
        plugin_id="p1",
        name="Plugin One",
        version="1.0.0",
        description="d",
        author="a",
        plugin_type=plugin_system.PluginType.MONITORING,
    )
    assert psm.register_plugin("p1", meta) is True
    assert psm.register_plugin("p1", meta) is False  # duplicate

    meta_bad = plugin_system.PluginMetadata(
        plugin_id="bad",
        name="",
        version="1.0.0",
        description="d",
        author="a",
        plugin_type=plugin_system.PluginType.AI,
    )
    assert psm.register_plugin("bad", meta_bad) is False

    meta_old = plugin_system.PluginMetadata(
        plugin_id="old",
        name="Old",
        version="1.0.0",
        description="d",
        author="a",
        plugin_type=plugin_system.PluginType.AI,
        min_system_version="2.0",
    )
    assert psm.register_plugin("old", meta_old) is False

    assert psm.enable_plugin("p1") is True
    assert psm.disable_plugin("p1") is True
    assert psm.get_plugin_info("p1")["status"] == "disabled"


def test_plugin_dependencies_and_info():
    psm = plugin_system.PluginSystemManager()
    dep = plugin_system.PluginMetadata(
        plugin_id="dep1",
        name="Dep",
        version="1.0.0",
        description="d",
        author="a",
        plugin_type=plugin_system.PluginType.MONITORING,
    )
    main = plugin_system.PluginMetadata(
        plugin_id="main",
        name="Main",
        version="1.0.0",
        description="d",
        author="a",
        plugin_type=plugin_system.PluginType.INTEGRATION,
        dependencies=["dep1>=1.0.0"],
    )
    psm.register_plugin("dep1", dep)
    psm.register_plugin("main", main)

    # Dependency not enabled yet -> enable fails.
    assert psm.enable_plugin("main") is False
    psm.enable_plugin("dep1")
    assert psm.enable_plugin("main") is True

    assert psm.get_plugin_info("none") is None
    info = psm.get_plugin_info("main")
    assert info["plugin_id"] == "main"
    assert info["status"] == "enabled"


def test_plugin_list_and_summary():
    psm = plugin_system.PluginSystemManager()
    for i in range(3):
        meta = plugin_system.PluginMetadata(
            plugin_id=f"p{i}",
            name=f"P{i}",
            version="1.0.0",
            description="d",
            author="a",
            plugin_type=[
                plugin_system.PluginType.MONITORING,
                plugin_system.PluginType.AI,
                plugin_system.PluginType.CUSTOM,
            ][i],
        )
        psm.register_plugin(f"p{i}", meta)
    psm.enable_plugin("p0")

    all_plugins = psm.list_plugins()
    assert len(all_plugins) == 3
    assert len(psm.list_plugins(plugin_type=plugin_system.PluginType.AI)) == 1
    assert len(psm.list_plugins(status=plugin_system.PluginStatus.ENABLED)) == 1

    summary = psm.get_system_summary()
    assert summary["total_plugins_registered"] == 3
    assert summary["total_plugins_enabled"] == 1
    assert "monitoring" in summary["plugins_by_type"]
    assert "enabled" in summary["plugins_by_status"]


def test_get_plugin_system_manager(monkeypatch):
    monkeypatch.setattr(plugin_system, "_plugin_system_manager", None)
    manager = plugin_system.get_plugin_system_manager()
    assert isinstance(manager, plugin_system.PluginSystemManager)
    assert plugin_system.get_plugin_system_manager() is manager
