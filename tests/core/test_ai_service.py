# -*- coding: utf-8 -*-
"""Unit tests for core/ai_service.py."""

import pytest

from core.ai_service import (
    AIContextService,
    _extract_gather_result,
    _safe_alert_value,
    _safe_get_metric,
)


def test_safe_alert_value():
    assert _safe_alert_value(1.5) == 1.5
    assert _safe_alert_value("1.5") == 1.5
    assert (
        _safe_alert_value("long string that exceeds limit") == "long string that exceeds limit"[:64]
    )
    assert _safe_alert_value(None) is None


def test_safe_get_metric():
    assert _safe_get_metric({"cpu": {"usage": 90}}, "cpu", "usage") == 90
    assert _safe_get_metric({}, "cpu", "usage", default=0) == 0
    assert _safe_get_metric(None, "cpu", "usage") == "N/A"


def test_extract_gather_result():
    assert _extract_gather_result([1, 2], "test", list) == [1, 2]
    assert _extract_gather_result(ValueError("err"), "test", list) is None
    assert _extract_gather_result(None, "test", list) is None
    assert _extract_gather_result("not list", "test", list) is None


@pytest.mark.asyncio
async def test_ai_context_service_collect():
    service = AIContextService()
    ctx = await service.collect_rich_context(snapshot={}, service_name="svc")
    assert isinstance(ctx, dict)
    assert "top_processes" in ctx
