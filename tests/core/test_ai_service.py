# -*- coding: utf-8 -*-
"""Tests for core/ai_service.py."""

import pytest  # noqa: F401  # Imported for test setup

from core.ai_service import (
    AIContextService,
    _extract_gather_result,
    _safe_alert_value,
    _safe_get_metric,
)


def test_safe_alert_value():
    assert _safe_alert_value(None) is None
    assert _safe_alert_value(42) == 42
    assert len(_safe_alert_value("too long string " * 20)) == 64


def test_safe_get_metric():
    assert _safe_get_metric({}, "cpu", "usage") == "N/A"
    assert _safe_get_metric({"cpu": {"usage": 80}}, "cpu", "usage") == 80
    assert _safe_get_metric({"cpu": None}, "cpu", "usage", default=0) == 0


def test_extract_gather_result():
    assert _extract_gather_result({"a": 1}, "test", dict) == {"a": 1}
    assert _extract_gather_result("not a dict", "test", dict) is None
    assert _extract_gather_result(RuntimeError("boom"), "test", dict) is None
    assert _extract_gather_result(None, "test", dict) is None


@pytest.mark.asyncio
async def test_collect_rich_context():
    service = AIContextService()
    ctx = await service.collect_rich_context(
        snapshot={
            "top_processes": [{"name": "a"}],
            "cpu": {"usage": 50},
        }
    )
    assert isinstance(ctx, dict)
    assert "top_processes" in ctx
    assert "recent_alerts" in ctx
    assert "stats" in ctx
