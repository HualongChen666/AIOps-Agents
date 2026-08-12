# -*- coding: utf-8 -*-
"""Tests for core/ui_experience_support.py."""

from unittest.mock import AsyncMock

import pytest

import core.ui_experience_support as ui


@pytest.fixture
def support():
    return ui.UIExperienceSupport()


async def test_load_templates_and_dashboard_data(support):
    await support._load_dashboard_templates()
    data = await support.get_dashboard_data("user1")
    assert data["theme"] == "light"
    assert "widgets" in data
    assert len(data["widgets"]) == 4


async def test_topology_data(support):
    await support._update_topology_data()
    data = await support.get_topology_data(ui.VisualizationType.TOPOLOGY)
    assert data["metadata"]["total_nodes"] == 4
    assert data["metadata"]["total_edges"] == 3
    assert data["visualization_type"] == "topology"


async def test_report_generation(support):
    for chart_type in ui.ChartType:
        config = ui.ReportConfig(
            id=f"r_{chart_type.value}",
            name=f"{chart_type.value} report",
            type="metric",
            time_range="24h",
            metrics=["cpu"],
            chart_type=chart_type,
        )
        report = await support.create_report(config)
        assert "report_id" in report
        assert report["data"] is not None


async def test_settings_and_translations(support):
    await support._load_translations()
    assert support.get_translation("zh", "dashboard") == "仪表板"
    assert support.get_translation("en", "alerts") == "Alerts"
    assert support.get_translation("xx", "unknown") == "unknown"

    settings = await support.set_ui_settings(
        "user1", {"theme": "dark", "language": "zh", "preferences": {"refresh": 5}}
    )
    assert settings.theme == ui.ThemeMode.DARK
    assert settings.language == "zh"
    assert settings.preferences["refresh"] == 5

    fetched = await support.get_ui_settings("user1")
    assert fetched is not None
    assert fetched.theme.value == "dark"


async def test_mobile_optimized_data(support):
    dashboard = await support.get_mobile_optimized_data("dashboard")
    assert dashboard["optimized"] is True

    alerts = await support.get_mobile_optimized_data("alerts", {"page": 2, "limit": 20})
    assert alerts["page"] == 2
    assert alerts["limit"] == 20

    other = await support.get_mobile_optimized_data("unknown")
    assert other["optimized"] is False


async def test_websocket_flow(support):
    from fastapi import WebSocket

    mock_ws = AsyncMock(spec=WebSocket)
    connected = await support.connect_websocket(mock_ws, "client1")
    assert connected is True

    await support.subscribe_to_updates("client1", ["metrics", "topology"])
    assert "metrics" in support.connection_subscriptions["client1"]

    await support.broadcast_update("metrics", {"cpu": 50.0})
    mock_ws.send_json.assert_awaited()

    await support.unsubscribe_from_updates("client1", ["metrics"])
    assert "metrics" not in support.connection_subscriptions["client1"]

    await support.disconnect_websocket("client1")
    assert "client1" not in support.websocket_connections


async def test_ui_statistics(support):
    await support._load_translations()
    await support._load_dashboard_templates()
    stats = support.get_ui_statistics()
    assert "websocket_connections" in stats
    assert "supported_languages" in stats
    assert "supported_themes" in stats
