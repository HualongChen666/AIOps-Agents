# -*- coding: utf-8 -*-
"""Functional tests for core.alert_providers.grafana, core.alert_providers.zabbix,
core.websocket_integrator, core.teams_adapter and core.causal.preprocessing."""

import asyncio
import re
import warnings
from unittest.mock import AsyncMock, MagicMock

import numpy as np
import pandas as pd
import pytest

import core.teams_adapter as teams_adapter
from core.alert_providers.grafana import GrafanaAlertProvider, _first_numeric, _safe_float
from core.alert_providers.zabbix import ZabbixAlertProvider
from core.causal.preprocessing import TimeSeriesPreprocessor
from core.websocket_integrator import WebSocketIntegrator, get_websocket_integrator

pytestmark = [pytest.mark.core]


# ---------------------------------------------------------------------------
# core.alert_providers.grafana
# ---------------------------------------------------------------------------
def test_grafana_safe_float():
    assert _safe_float("12.34") == 12.34
    assert _safe_float(None) == 0.0
    assert _safe_float("not-a-number") == 0.0
    assert _safe_float("", default=-1.0) == -1.0


def test_grafana_first_numeric():
    assert _first_numeric({"a": 1, "b": "x"}) == 1.0
    assert _first_numeric({"a": "x", "b": 2.0}) == 2.0
    assert _first_numeric("not-a-dict") == 0.0
    assert _first_numeric({}) == 0.0
    assert _first_numeric({"a": "bad"}) == 0.0


def test_grafana_normalize_payload_variants():
    provider = GrafanaAlertProvider()

    assert provider.normalize(123) == []
    assert provider.normalize("invalid") == []
    assert provider.normalize(["invalid"]) == []

    single_alert = {
        "status": "firing",
        "labels": {
            "alertname": "HighCPU",
            "severity": "critical",
            "instance": "srv-01",
            "job": "cpu",
            "platform": "linux",
        },
        "annotations": {"summary": "CPU high", "description": "CPU > 80%"},
        "startsAt": "2024-01-01T00:00:00Z",
        "values": {"B": 99.5},
    }
    alerts = provider.normalize(single_alert)
    assert len(alerts) == 1
    assert alerts[0]["source"] == "grafana"
    assert alerts[0]["status"] == "firing"
    assert alerts[0]["value"] == 99.5
    assert alerts[0]["title"] == "CPU high"
    assert alerts[0]["host"] == "srv-01"

    multi = {"alerts": [single_alert, "invalid"]}
    assert len(provider.normalize(multi)) == 1

    list_payload = [single_alert]
    assert len(provider.normalize(list_payload)) == 1


def test_grafana_resolve_and_fallbacks():
    provider = GrafanaAlertProvider()
    raw = {
        "status": "resolved",
        "labels": "bad-labels",
        "annotations": 123,
        "fingerprint": "fp-123",
        "values": None,
    }
    alert = provider._normalize_one(raw)
    assert alert["status"] == "resolved"
    assert alert["labels"] == {}
    assert alert["annotations"] == {}
    assert alert["fingerprint"] == "fp-123"

    raw_no_values = {
        "status": "firing",
        "labels": {"alertname": "Mem", "value": "88.8"},
        "annotations": {},
    }
    alert2 = provider._normalize_one(raw_no_values)
    assert alert2["value"] == 88.8
    assert alert2["title"] == "Mem"
    assert alert2["status"] == "firing"


# ---------------------------------------------------------------------------
# core.alert_providers.zabbix
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "status_input,expected",
    [
        ("0", "resolved"),
        ("ok", "resolved"),
        ("resolved", "resolved"),
        ("recovery", "resolved"),
        ("recovered", "resolved"),
        ("1", "firing"),
        ("problem", "firing"),
        ("firing", "firing"),
        ("trigger", "firing"),
    ],
)
def test_zabbix_status_resolution(status_input, expected):
    provider = ZabbixAlertProvider()
    raw = {
        "subject": f"{status_input} alert",
        "status": status_input,
        "hostname": "host-01",
        "itemname": "CPU",
        "itemvalue": "95.5",
        "eventid": "evt-1",
    }
    alert = provider._normalize_one(raw)
    assert alert["status"] == expected


def test_zabbix_subject_recovery_fallback():
    provider = ZabbixAlertProvider()
    raw = {
        "subject": "Recovery: something",
        "message": "message body",
        "hostname": "host-02",
        "itemvalue": "0",
    }
    alert = provider._normalize_one(raw)
    assert alert["status"] == "resolved"
    assert alert["title"] == "Recovery: something"


def test_zabbix_severity_and_ids():
    provider = ZabbixAlertProvider()
    raw = {
        "summary": "High memory",
        "message": "Memory usage exceeded\nLine two",
        "severity": "High (critical)",
        "hostname": "host-03",
        "itemname": "vm.memory.util",
        "itemvalue": "88",
        "eventid": "event-xyz",
        "trigger_name": "Trigger-1",
        "platform": "windows",
        "service": "memory-service",
    }
    alert = provider._normalize_one(raw)
    assert alert["source"] == "zabbix"
    assert alert["severity"] == "highcritical"
    assert re.sub(r"[^a-z]", "", str(raw["severity"]).lower()) == "highcritical"
    assert alert["id"].startswith("ZABB-")
    assert alert["metric"] == "vm.memory.util"
    assert alert["value"] == 88.0
    assert alert["labels"]["trigger"] == "Trigger-1"
    assert alert["platform"] == "windows"
    assert alert["service"] == "memory-service"
    assert alert["title"] == "High memory"
    assert alert["desc"] == raw["message"]


def test_zabbix_normalize_variants():
    provider = ZabbixAlertProvider()
    assert provider.normalize(None) == []
    assert provider.normalize("bad") == []
    assert provider.normalize(["bad"]) == []

    raw = {
        "subject": "Zabbix problem",
        "status": "1",
        "hostname": "h1",
        "itemname": "cpu",
        "itemvalue": "70",
        "eventid": "e1",
    }
    assert len(provider.normalize([raw])) == 1
    assert len(provider.normalize(raw)) == 1


def test_zabbix_title_from_message():
    provider = ZabbixAlertProvider()
    raw = {
        "message": "First line\nSecond line",
        "hostname": "h2",
        "itemname": "disk",
        "itemvalue": "bad",
        "eventid": "e2",
    }
    alert = provider._normalize_one(raw)
    assert alert["title"] == "First line"
    assert alert["value"] == 0.0


# ---------------------------------------------------------------------------
# core.websocket_integrator
# ---------------------------------------------------------------------------
@pytest.fixture
def fake_websocket_manager(monkeypatch):
    """Provide a deterministic fake WebSocket manager."""
    manager = MagicMock()
    manager.start_heartbeat = AsyncMock()
    manager.stop_heartbeat = AsyncMock()
    manager.register_message_handler = MagicMock()
    manager.broadcast = AsyncMock(return_value=3)
    monkeypatch.setattr(
        "core.enhanced_websocket_manager.get_enhanced_websocket_manager",
        lambda config=None: manager,
    )
    return manager


def test_websocket_integrator_init_and_factory(fake_websocket_manager):
    integrator = WebSocketIntegrator()
    assert integrator.websocket_manager is fake_websocket_manager
    assert not integrator.is_running

    factory = get_websocket_integrator()
    assert isinstance(factory, WebSocketIntegrator)


def test_websocket_start_stop(fake_websocket_manager):
    integrator = WebSocketIntegrator()

    async def _run():
        await integrator.start()
        assert integrator.is_running
        await integrator.start()  # already running branch
        await integrator.stop()
        assert not integrator.is_running

    asyncio.run(_run())
    fake_websocket_manager.start_heartbeat.assert_awaited_once()
    fake_websocket_manager.stop_heartbeat.assert_awaited_once()


def test_websocket_stop_when_not_running(fake_websocket_manager):
    integrator = WebSocketIntegrator()
    asyncio.run(integrator.stop())
    assert not integrator.is_running
    fake_websocket_manager.stop_heartbeat.assert_not_awaited()


def test_websocket_register_handlers():
    integrator = WebSocketIntegrator()

    alert_h = AsyncMock()
    metric_h = AsyncMock()
    log_h = AsyncMock()
    status_h = AsyncMock()

    integrator.register_alert_handler(alert_h)
    integrator.register_metrics_handler(metric_h)
    integrator.register_log_handler(log_h)
    integrator.register_status_handler(status_h)

    assert len(integrator.alert_handlers) == 1
    assert len(integrator.metrics_handlers) == 1
    assert len(integrator.log_handlers) == 1
    assert len(integrator.status_handlers) == 1

    status = integrator.get_integration_status()
    assert status["handlers"]["alert_handlers"] == 1
    assert status["config"]["alert_channel"] == "alerts"


def test_websocket_message_handlers_are_registered(fake_websocket_manager):
    from core.enhanced_websocket_manager import MessageType

    integrator = WebSocketIntegrator()
    asyncio.run(integrator.start())

    calls = fake_websocket_manager.register_message_handler.call_args_list
    types = {c.args[0] for c in calls}
    assert MessageType.ALERT in types
    assert MessageType.METRIC in types
    assert MessageType.LOG in types

    asyncio.run(integrator.stop())


def test_websocket_alert_handler_invokes_callback(fake_websocket_manager):
    from core.enhanced_websocket_manager import MessageType

    integrator = WebSocketIntegrator()
    handler = AsyncMock()
    integrator.register_alert_handler(handler)

    # Trigger the actual wrapper registered by the integrator
    asyncio.run(integrator.start())
    calls = fake_websocket_manager.register_message_handler.call_args_list
    alert_wrapper = [c for c in calls if c.args[0] == MessageType.ALERT][0].args[1]

    class _FakeMsg:
        data = {"id": "a1"}

    asyncio.run(alert_wrapper(None, _FakeMsg()))
    handler.assert_awaited_once_with({"id": "a1"})
    asyncio.run(integrator.stop())


def test_websocket_register_message_handlers_branches():
    integrator = WebSocketIntegrator()
    integrator.websocket_manager = None
    integrator._register_message_handlers()  # no manager branch

    no_handler_mgr = MagicMock()
    no_handler_mgr.broadcast = AsyncMock()
    integrator.websocket_manager = no_handler_mgr
    integrator._register_message_handlers()  # no register method branch


def test_websocket_register_message_handlers_exception(fake_websocket_manager):
    fake_websocket_manager.register_message_handler.side_effect = RuntimeError("boom")
    integrator = WebSocketIntegrator()
    integrator._register_message_handlers()  # exception branch


def test_websocket_broadcast_variants(fake_websocket_manager):
    integrator = WebSocketIntegrator()

    async def _run():
        await integrator.start()
        assert await integrator.broadcast_alert({"id": "a"}) == 3
        assert await integrator.broadcast_metrics({"cpu": 0.5}) == 3
        assert await integrator.broadcast_log({"msg": "hello"}) == 3
        await integrator.stop()

    asyncio.run(_run())
    assert fake_websocket_manager.broadcast.await_count == 3


def test_websocket_broadcast_not_running_or_no_manager():
    integrator = WebSocketIntegrator()
    assert asyncio.run(integrator.broadcast_alert({"id": "a"})) == 0

    integrator.is_running = True
    integrator.websocket_manager = None
    assert asyncio.run(integrator.broadcast_alert({"id": "a"})) == 0


def test_websocket_broadcast_exception(fake_websocket_manager):
    fake_websocket_manager.broadcast.side_effect = RuntimeError("send failed")
    integrator = WebSocketIntegrator()
    asyncio.run(integrator.start())
    assert asyncio.run(integrator.broadcast_alert({"id": "a"})) == 0
    asyncio.run(integrator.stop())


def test_websocket_status_broadcasting_one_iteration(fake_websocket_manager, monkeypatch):
    async def _patched_sleep(delay):
        integrator.is_running = False

    monkeypatch.setattr("core.websocket_integrator.asyncio.sleep", _patched_sleep)

    integrator = WebSocketIntegrator()
    integrator.is_running = True
    asyncio.run(integrator._status_broadcasting_loop())
    fake_websocket_manager.broadcast.assert_awaited_once()


def test_websocket_status_broadcasting_failure(fake_websocket_manager, monkeypatch):
    fake_websocket_manager.broadcast.side_effect = RuntimeError("broadcast failure")

    async def _patched_sleep(delay):
        integrator.is_running = False

    monkeypatch.setattr("core.websocket_integrator.asyncio.sleep", _patched_sleep)

    integrator = WebSocketIntegrator()
    integrator.is_running = True
    asyncio.run(integrator._status_broadcasting_loop())
    fake_websocket_manager.broadcast.assert_awaited_once()


def test_websocket_get_system_status():
    integrator = WebSocketIntegrator()
    status = asyncio.run(integrator._get_system_status())
    assert status["status"] == "healthy"
    assert "metrics" in status


def test_websocket_background_loops_cancel_and_exit(monkeypatch):
    async def _patched_sleep(delay):
        integrator.is_running = False

    monkeypatch.setattr("core.websocket_integrator.asyncio.sleep", _patched_sleep)

    integrator = WebSocketIntegrator()
    integrator.is_running = True
    asyncio.run(integrator._alert_monitoring_loop())
    asyncio.run(integrator._metrics_streaming_loop())
    asyncio.run(integrator._log_streaming_loop())


def test_websocket_background_loop_exception(monkeypatch):
    async def _bad_sleep(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr("core.websocket_integrator.asyncio.sleep", _bad_sleep)

    integrator = WebSocketIntegrator()
    integrator.is_running = True
    # Exercises the generic Exception handler path
    asyncio.run(integrator._alert_monitoring_loop())


def test_websocket_integration_status():
    integrator = WebSocketIntegrator()
    status = integrator.get_integration_status()
    assert "is_running" in status
    assert status["websocket_manager_available"] is True
    assert "config" in status
    assert "handlers" in status


# ---------------------------------------------------------------------------
# core.teams_adapter
# ---------------------------------------------------------------------------
@pytest.fixture
def fake_teams_client():
    """Deterministic fake httpx client for Teams tests."""
    response = MagicMock()
    response.status_code = 202
    response.text = "Accepted"
    response.raise_for_status = MagicMock()

    client = MagicMock()
    client.is_closed = False
    client.aclose = AsyncMock()
    client.post = AsyncMock(return_value=response)
    return client


def test_teams_build_message():
    msg = teams_adapter._build_message("hello")
    assert msg["@type"] == "MessageCard"
    assert msg["text"] == "hello"
    assert "title" not in msg

    titled = teams_adapter._build_message("body", title="Title", color="FF0000")
    assert titled["title"] == "Title"
    assert titled["themeColor"] == "FF0000"


def test_teams_build_adaptive_card():
    card = teams_adapter._build_adaptive_card("desc")
    assert card["type"] == "message"
    assert len(card["attachments"]) == 1

    actions = [
        {"type": "Action.OpenUrl", "title": "Open", "url": "https://x"},
        {"type": "Action.Submit", "title": "Submit", "action": "ack", "value": 1},
    ]
    card2 = teams_adapter._build_adaptive_card(
        "description", title="My Title", actions=actions, color="red"
    )
    assert card2["attachments"][0]["content"]["body"][0]["text"] == "My Title"
    assert card2["attachments"][0]["content"]["actions"][0]["type"] == "Action.OpenUrl"
    assert card2["attachments"][0]["content"]["actions"][1]["type"] == "Action.Submit"
    assert "summary" in card2


def test_teams_post_message_success(monkeypatch, fake_teams_client):
    monkeypatch.setattr(teams_adapter, "TEAMS_WEBHOOK_URL", "https://webhook.office.com/test")
    monkeypatch.setattr(
        teams_adapter, "_get_http_client", AsyncMock(return_value=fake_teams_client)
    )

    result = asyncio.run(teams_adapter.post_message("alert!", title="A", color="FF0000"))
    assert result["status"] == "ok"
    assert result["http_status"] == 202
    fake_teams_client.post.assert_awaited_once()


def test_teams_post_interactive_message_success(monkeypatch, fake_teams_client):
    monkeypatch.setattr(teams_adapter, "TEAMS_WEBHOOK_URL", "https://webhook.office.com/test")
    monkeypatch.setattr(
        teams_adapter, "_get_http_client", AsyncMock(return_value=fake_teams_client)
    )

    actions = [{"type": "Action.OpenUrl", "title": "View", "url": "https://x"}]
    result = asyncio.run(
        teams_adapter.post_interactive_message(
            "Title", "Description", actions, color="green"
        )
    )
    assert result["status"] == "ok"
    assert result["http_status"] == 202


def test_teams_post_not_configured():
    monkeypatch_placeholder = None  # no env changes at module level
    with pytest.raises(RuntimeError, match="not configured"):
        asyncio.run(teams_adapter.post_message("will fail"))


def test_teams_client_close_and_singleton(monkeypatch, fake_teams_client):
    monkeypatch.setattr(teams_adapter, "_HTTP_CLIENT", fake_teams_client)
    asyncio.run(teams_adapter.close_teams_client())
    fake_teams_client.aclose.assert_awaited_once()

    already_closed = MagicMock()
    already_closed.is_closed = True
    already_closed.aclose = AsyncMock()
    monkeypatch.setattr(teams_adapter, "_HTTP_CLIENT", already_closed)
    asyncio.run(teams_adapter.close_teams_client())
    already_closed.aclose.assert_not_awaited()


# ---------------------------------------------------------------------------
# core.causal.preprocessing
# ---------------------------------------------------------------------------
@pytest.fixture
def sample_ts_data():
    rng = pd.date_range("2024-01-01", periods=20, freq="h")
    df = pd.DataFrame(
        {
            "cpu": np.linspace(10, 90, 20) + np.random.default_rng(42).normal(0, 2, 20),
            "mem": np.linspace(20, 80, 20) + np.random.default_rng(43).normal(0, 1, 20),
        },
        index=rng,
    )
    df.iloc[3, 0] = np.nan
    df.iloc[15, 1] = np.nan
    return df


def test_preprocessor_init():
    pp = TimeSeriesPreprocessor(handle_missing="drop", normalize=False, detect_outliers=False)
    assert pp.handle_missing == "drop"
    assert not pp.normalize
    assert not pp.detect_outliers


def test_preprocess_interpolate_and_normalize(sample_ts_data):
    pp = TimeSeriesPreprocessor(handle_missing="interpolate", normalize=True, detect_outliers=True)
    result = pp.preprocess(sample_ts_data)
    assert isinstance(result, np.ndarray)
    assert result.shape == (20, 2)
    assert not np.isnan(result).any()


def test_preprocess_drop_and_no_normalize(sample_ts_data):
    pp = TimeSeriesPreprocessor(handle_missing="drop", normalize=False, detect_outliers=False)
    result = pp.preprocess(sample_ts_data, target_columns=["cpu"])
    assert result.shape[0] < 20
    assert result.shape[1] == 1


def test_preprocess_forward_fill_warns(sample_ts_data):
    pp = TimeSeriesPreprocessor(handle_missing="forward_fill")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        with pytest.raises(TypeError):
            pp.preprocess(sample_ts_data)


def test_handle_missing_values_unknown(sample_ts_data):
    pp = TimeSeriesPreprocessor(handle_missing="unknown")
    result = pp._handle_missing_values(sample_ts_data)
    # Unknown method returns the data as-is; NaNs remain
    assert result.isna().sum().sum() == sample_ts_data.isna().sum().sum()


def test_select_lags(sample_ts_data):
    pp = TimeSeriesPreprocessor()
    data = pp.preprocess(sample_ts_data, target_columns=["cpu"])

    aic_lags = pp.select_lags(data, max_lag=5, method="aic")
    assert aic_lags == [1, 2, 3, 4]

    bic_lags = pp.select_lags(data, max_lag=3, method="bic")
    assert bic_lags == [1, 2, 3]

    auto_lags = pp.select_lags(data, max_lag=5, method="auto")
    assert isinstance(auto_lags, list)


def test_create_lagged_features():
    pp = TimeSeriesPreprocessor()
    data = np.arange(20, dtype=float).reshape(10, 2)
    lags = [1, 2]
    result = pp.create_lagged_features(data, lags)
    assert result.shape == (8, 6)

    no_lags = pp.create_lagged_features(data, [])
    assert np.array_equal(no_lags, data)
