# -*- coding: utf-8 -*-
"""Tests for core/health_check.py."""

import pytest

import core.health_check as health_check
from core.health_check import (
    get_detailed_health,
    get_health_history,
    get_liveness_status,
    get_readiness_status,
    get_recovery_suggestions,
    register_alert_callback,
)


def test_liveness_and_readiness():
    live = get_liveness_status()
    assert live["status"] == "alive"
    ready = get_readiness_status()
    assert ready["status"] in ("ready", "not_ready")


def test_detailed_health_and_history():
    detailed = get_detailed_health()
    assert "last_check" in detailed
    history = get_health_history(hours=24)
    assert isinstance(history, list)


def test_recovery_suggestions():
    healthy = {"components": {"database": {"status": "healthy"}}}
    assert "healthy" in get_recovery_suggestions(healthy)[0]

    unhealthy = {"components": {"database": {"status": "unhealthy"}}}
    assert any("database" in s for s in get_recovery_suggestions(unhealthy))


@pytest.mark.asyncio
async def test_register_alert_callback():
    async def callback(alert, data):
        pass

    register_alert_callback(callback)
    assert callback in health_check._alert_callbacks
