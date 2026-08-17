# -*- coding: utf-8 -*-
"""Functional tests for core/ui_experience_support.py remaining branches."""

import asyncio  # noqa: F401  # Imported for test setup
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest  # noqa: F401  # Imported for test setup

import core.ui_experience_support as ui

pytestmark = [pytest.mark.core]


@pytest.fixture
def support():
    return ui.UIExperienceSupport()


async def test_initialize_schedules_background_loops(support, monkeypatch):
    """initialize() loads templates/translations and starts background tasks."""
    tasks = []

    def fake_create_task(coro):
        tasks.append(coro)
        return MagicMock()

    monkeypatch.setattr(asyncio, "create_task", fake_create_task)
    await support.initialize()
    assert len(tasks) == 2
    assert "default" in support.dashboard_templates
    assert "en" in support.translations


@pytest.mark.parametrize(
    "lang,key,expected",
    [
        ("zh", "dashboard", "仪表板"),
        ("missing_lang", "dashboard", "Dashboard"),  # fallback to English
        ("en", "missing_key", "missing_key"),  # fallback to key name
    ],
)
async def test_get_translation_fallback(support, lang, key, expected):
    await support._load_translations()
    assert support.get_translation(lang, key) == expected


async def test_connect_websocket_not_available(support, monkeypatch):
    monkeypatch.setattr(ui, "WEBSOCKET_AVAILABLE", False)
    result = await support.connect_websocket(None, "client")  # noqa: F841  # Variable for test verification
    assert result is False


async def test_connect_websocket_max_connections(support, monkeypatch):
    monkeypatch.setattr(ui, "WEBSOCKET_AVAILABLE", True)
    support.max_websocket_connections = 0
    mock_ws = AsyncMock()
    result = await support.connect_websocket(mock_ws, "client")  # noqa: F841  # Variable for test verification
    assert result is False


async def test_disconnect_websocket_missing(support):
    await support.disconnect_websocket("not_there")
    assert "not_there" not in support.websocket_connections


async def test_disconnect_websocket_without_subscriptions(support):
    support.websocket_connections["c1"] = AsyncMock()
    await support.disconnect_websocket("c1")
    assert "c1" not in support.websocket_connections
    assert "c1" not in support.connection_subscriptions


async def test_subscribe_new_client(support):
    await support.subscribe_to_updates("new_client", ["metrics", "alerts"])
    assert support.connection_subscriptions["new_client"] == ["metrics", "alerts"]


async def test_unsubscribe_missing_client_and_topic(support):
    # No errors when client or topic does not exist.
    await support.unsubscribe_from_updates("missing", ["metrics"])
    support.connection_subscriptions["c"] = ["alerts"]
    await support.unsubscribe_from_updates("c", ["metrics"])
    assert support.connection_subscriptions["c"] == ["alerts"]


async def test_broadcast_update_not_available(support, monkeypatch):
    monkeypatch.setattr(ui, "WEBSOCKET_AVAILABLE", False)
    await support.broadcast_update("topic", {})  # should short-circuit safely


async def test_broadcast_update_send_exception(support, monkeypatch):
    monkeypatch.setattr(ui, "WEBSOCKET_AVAILABLE", True)
    mock_ws = AsyncMock()
    mock_ws.send_json.side_effect = Exception("send failed")
    support.websocket_connections["c1"] = mock_ws
    support.connection_subscriptions["c1"] = ["metrics"]
    await support.broadcast_update("metrics", {"cpu": 50.0})
    mock_ws.send_json.assert_awaited()


async def test_realtime_data_push_and_alert_updates(support, monkeypatch):
    await support._push_realtime_metrics()
    assert "cpu_usage" in support.realtime_data_cache
    # Alerts list is empty so broadcast should not be called and no error occurs.
    await support._push_alert_updates()


async def test_realtime_data_push_loop_lifecycle(support, monkeypatch):
    calls = []

    async def fake_sleep(interval):
        calls.append(interval)
        if len(calls) == 1:
            return
        if len(calls) == 2:
            raise Exception("recoverable sleep error")
        raise asyncio.CancelledError()

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    with pytest.raises(asyncio.CancelledError):
        await support._realtime_data_push_loop()
    assert len(calls) >= 2


async def test_topology_update_data_and_broadcast(support):
    await support._update_topology_data()
    assert {"frontend", "api", "db", "cache"} <= set(support.topology_nodes)
    first_ts = support.topology_nodes["frontend"].properties["last_updated"]
    await support._update_topology_data()
    assert support.topology_nodes["frontend"].properties["last_updated"] >= first_ts
    await support._broadcast_topology_update()


async def test_topology_update_loop_lifecycle(support, monkeypatch):
    calls = []

    async def fake_sleep(interval):
        calls.append(interval)
        if len(calls) == 1:
            return
        if len(calls) == 2:
            raise Exception("recoverable sleep error")
        raise asyncio.CancelledError()

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    with pytest.raises(asyncio.CancelledError):
        await support._topology_update_loop()
    assert len(calls) >= 2


async def test_get_topology_data(support):
    await support._update_topology_data()
    data = await support.get_topology_data(ui.VisualizationType.FLOW)
    assert data["visualization_type"] == "flow"
    assert data["metadata"]["total_nodes"] == 4
    assert data["metadata"]["total_edges"] == 3


async def test_get_widget_data_variants(support):
    metric_none = await support._get_widget_data({"type": "metric", "data_source": None}, "1h")
    assert metric_none == {"type": "metric", "data": None}
    unknown = await support._get_widget_data({"type": "unknown"}, "1h")
    assert unknown == {"type": "unknown", "data": None}


async def test_get_metric_data_empty(support):
    result = await support._get_metric_data("missing_metric")  # noqa: F841  # Variable for test verification
    assert result == {"type": "metric", "data": None}  # noqa: F841  # Variable for test verification


async def test_get_chart_data_with_history_and_empty(support):
    now = datetime.now()
    # Data points 20 and 40 minutes ago are inside the 1-hour range; 80 minutes is outside.
    for minutes_ago, value in [(20, 1), (40, 2), (80, 3)]:
        support.realtime_data_cache["req"].append(
            {
                "value": value,
                "timestamp": (now - timedelta(minutes=minutes_ago)).isoformat(),
            }
        )
    chart = await support._get_chart_data(
        {"type": "chart", "data_source": "req", "chart_type": "line"}, "1h"
    )
    assert chart["type"] == "chart"
    assert chart["chart_type"] == "line"
    assert chart["data"]["values"] == [1, 2]
    assert 3 not in chart["data"]["values"]

    empty = await support._get_chart_data(
        {"type": "chart", "data_source": "nope", "chart_type": "bar"}, "6h"
    )
    assert empty["data"] is None


@pytest.mark.parametrize(
    "time_range, expected",
    [
        ("1h", timedelta(hours=1)),
        ("6h", timedelta(hours=6)),
        ("24h", timedelta(hours=24)),
        ("7d", timedelta(days=7)),
        ("unknown", timedelta(hours=1)),
    ],
)
def test_parse_time_range(support, time_range, expected):
    assert support._parse_time_range(time_range) == expected


async def test_get_dashboard_data_with_layout(support):
    await support._load_dashboard_templates()
    await support.set_ui_settings(
        "u1",
        {
            "theme": "dark",
            "language": "zh",
            "dashboard_layout": {
                "widgets": [
                    {"type": "metric", "data_source": None},
                    {"type": "chart", "data_source": "cpu_usage", "chart_type": "line"},
                    {"type": "topology"},
                    {"type": "unknown"},
                ]
            },
        },
    )
    data = await support.get_dashboard_data("u1", "24h")
    assert data["theme"] == "dark"
    assert len(data["widgets"]) == 4


async def test_set_ui_settings_partial_update(support):
    first = await support.set_ui_settings("u1", {"theme": "dark"})
    assert first.theme == ui.ThemeMode.DARK
    updated = await support.set_ui_settings(
        "u1",
        {
            "preferences": {"refresh": 5},
            "dashboard_layout": {"x": 0},
        },
    )
    assert updated.theme == ui.ThemeMode.DARK
    assert updated.language == "en"
    assert updated.preferences == {"refresh": 5}
    assert updated.dashboard_layout == {"x": 0}


async def test_get_ui_settings(support):
    assert await support.get_ui_settings("u1") is None
    await support.set_ui_settings("u1", {"language": "zh"})
    fetched = await support.get_ui_settings("u1")
    assert fetched.language == "zh"


async def test_get_mobile_optimized_data(support):
    dash = await support.get_mobile_optimized_data("dashboard")
    assert dash["optimized"] is True
    assert "metrics" in dash

    alerts = await support.get_mobile_optimized_data("alerts", {"page": 2, "limit": 20})
    assert alerts["page"] == 2
    assert alerts["limit"] == 20

    default = await support.get_mobile_optimized_data()
    assert default == {"optimized": False}


async def test_create_report_for_all_chart_types(support):
    for ctype in ui.ChartType:
        config = ui.ReportConfig(
            id=f"r_{ctype.value}",
            name=f"{ctype.value} report",
            type="metric",
            time_range="24h",
            metrics=["cpu"],
            chart_type=ctype,
        )
        report = await support.create_report(config)
        assert "report_id" in report
        if ctype in {ui.ChartType.LINE, ui.ChartType.BAR, ui.ChartType.PIE}:
            assert report["data"]
        else:
            assert report["data"] == {}


def test_get_ui_statistics(support):
    stats = support.get_ui_statistics()
    assert stats["websocket_connections"] == 0
    assert stats["topology_nodes"] == 0
    assert "supported_themes" in stats
