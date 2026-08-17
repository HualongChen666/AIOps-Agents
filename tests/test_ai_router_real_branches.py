# -*- coding: utf-8 -*-
"""Real branch-coverage tests for api/ai_router.py.

These tests exercise the missing branches using real business logic and the
real FastAPI router.  No mocks are used; inputs are real request/response data
or direct function arguments.
"""

import asyncio
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.ai_router import (
    AnalyzeRequest,
    router,
    _build_context_summary,
    _build_metrics_context,
    _collect_rich_context,
    _collect_snapshot_with_cache,
    _extract_disk_usage,
    _extract_gather_result,
    _get_recent_repairs,
    _safe_alert_value,
    _safe_get_metric,
)

# Real app with the real ai_router mounted
app = FastAPI()
app.include_router(router)
client = TestClient(app)


# ---------------------------------------------------------------------------
# Request model / validation branches
# ---------------------------------------------------------------------------
def test_analyze_request_query_stripping() -> None:
    req = AnalyzeRequest(query="  CPU high  ")
    assert req.query == "CPU high"


def test_analyze_request_invalid_platform() -> None:
    with pytest.raises(ValueError):
        AnalyzeRequest(query="x", platform="macos")


def test_analyze_request_whitespace_query() -> None:
    with pytest.raises(ValueError):
        AnalyzeRequest(query="   ")


def test_platform_and_query_normalizers_direct() -> None:
    # Direct classmethod calls exercise the normalization branches
    assert AnalyzeRequest._normalize_platform(" LINUX ") == "linux"
    assert AnalyzeRequest._normalize_platform("") == "windows"
    assert AnalyzeRequest._normalize_platform(None) == "windows"
    assert AnalyzeRequest._strip_query("  CPU high  ") == "CPU high"
    with pytest.raises(ValueError, match="query"):
        AnalyzeRequest._strip_query("   ")


# ---------------------------------------------------------------------------
# Helper function branches
# ---------------------------------------------------------------------------
def test_safe_alert_value_all_type_branches() -> None:
    assert _safe_alert_value(None) is None
    assert _safe_alert_value(42) == 42
    assert _safe_alert_value(1.5) == 1.5
    assert _safe_alert_value(True) is True
    # numeric string -> float
    assert _safe_alert_value("3.14") == 3.14
    # non-numeric string -> truncated original
    long_str = "x" * 100
    assert _safe_alert_value(long_str) == "x" * 64
    # other type -> str() truncated
    assert _safe_alert_value([1, 2]) == "[1, 2]"


def test_safe_get_metric_branches() -> None:
    snapshot: dict[str, Any] = {
        "cpu": {"usage_percent": 12.5},
        "memory": "broken",
        "disk": {},
    }
    assert _safe_get_metric(snapshot, "cpu", "usage_percent") == 12.5
    assert _safe_get_metric(snapshot, "cpu", "missing") == "N/A"
    assert _safe_get_metric(snapshot, "memory", "usage_percent") == "N/A"
    assert _safe_get_metric(snapshot, "disk", "usage_percent") == "N/A"
    assert _safe_get_metric("notadict", "cpu", "usage_percent") == "N/A"


def test_extract_gather_result_branches() -> None:
    assert _extract_gather_result(asyncio.CancelledError(), "x", dict) is None
    assert _extract_gather_result(ValueError("boom"), "x", list) is None
    assert _extract_gather_result(None, "x", dict) is None
    assert _extract_gather_result({"a": 1}, "x", dict) == {"a": 1}
    assert _extract_gather_result([1, 2], "x", list) == [1, 2]
    assert _extract_gather_result("unexpected", "x", dict) is None


def test_extract_disk_usage_branches() -> None:
    assert _extract_disk_usage({}) == "N/A"
    assert _extract_disk_usage({"disk": []}) == "N/A"
    assert _extract_disk_usage({"disk": [{"usage_percent": 55.0}]}) == 55.0
    # first element is not a dict -> covers the 220->228 branch
    assert _extract_disk_usage({"disk": ["bad"]}) == "N/A"
    assert _extract_disk_usage({"disk": [{"not": "usage_percent"}]}) == "N/A"
    assert _extract_disk_usage({"disk": {"C:": {"usage_percent": 80.0}}}) == 80.0
    # empty dict disk map -> covers 224->228 branch
    assert _extract_disk_usage({"disk": {}}) == "N/A"
    assert _extract_disk_usage({"disk": {"C:": 80.0}}) == "N/A"


def test_build_metrics_context() -> None:
    snapshot: dict[str, Any] = {
        "cpu": {"usage_percent": 10.5},
        "memory": {"usage_percent": 60.0},
        "disk": [{"usage_percent": 30.0}],
    }
    ctx = _build_metrics_context(snapshot)
    assert "CPU=10.5%" in ctx
    assert "内存=60.0%" in ctx
    assert "磁盘=30.0%" in ctx


def test_build_context_summary() -> None:
    assert _build_context_summary(None) == {
        "rich_enabled": False,
        "process_count": 0,
        "alert_count": 0,
        "repair_count": 0,
    }
    rich = {
        "top_processes": [1],
        "recent_alerts": [1, 2],
        "recent_repairs": [1, 2, 3],
    }
    assert _build_context_summary(rich) == {
        "rich_enabled": True,
        "process_count": 1,
        "alert_count": 2,
        "repair_count": 3,
    }


def test_get_recent_repairs_real() -> None:
    # Real call; if the SQLite/Postgres backend is unavailable this returns [].
    repairs = _get_recent_repairs()
    assert isinstance(repairs, list)


# ---------------------------------------------------------------------------
# Snapshot / rich-context collection branches
# ---------------------------------------------------------------------------
async def test_collect_snapshot_with_cache_miss_and_hit() -> None:
    # First call may miss the cache and run a real collect_all
    snap1 = await _collect_snapshot_with_cache()
    assert isinstance(snap1, dict)
    # Immediate second call should reuse the cached snapshot (TTL window)
    snap2 = await _collect_snapshot_with_cache()
    assert isinstance(snap2, dict)


async def test_collect_rich_context_cancellation() -> None:
    # A real cancellation must propagate through the re-raise branch.
    task = asyncio.create_task(_collect_rich_context(None))
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task


# ---------------------------------------------------------------------------
# FastAPI endpoint branches
# ---------------------------------------------------------------------------
def test_analyze_endpoint_minimal() -> None:
    # No metric/rich collection -> covers the need_collect=False and rich=False branches
    resp = client.post(
        "/api/ai/analyze",
        json={
            "query": "CPU high",
            "include_metrics": False,
            "include_rich_context": False,
            "platform": "linux",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["platform"] == "linux"
    assert data["metrics_context"] == ""
    assert data["context_summary"]["rich_enabled"] is False
    assert "analysis" in data


def test_analyze_endpoint_metrics_and_cache() -> None:
    # Triggers real snapshot collection and metrics context building
    resp = client.post(
        "/api/ai/analyze",
        json={
            "query": "Memory is high",
            "include_metrics": True,
            "include_rich_context": False,
            "platform": "windows",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["platform"] == "windows"
    # The metric string may contain real values or N/A; just verify it is a string
    assert isinstance(data["metrics_context"], str)
    assert data["context_summary"]["rich_enabled"] is False


async def test_analyze_endpoint_rich_context() -> None:
    # Triggers real rich-context collection (repairs/stats may fail and are logged)
    resp = client.post(
        "/api/ai/analyze",
        json={
            "query": "Disk is full",
            "include_metrics": False,
            "include_rich_context": True,
            "platform": "linux",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["context_summary"]["rich_enabled"] is True


@pytest.mark.parametrize(
    "payload",
    [
        {"query": ""},
        {"query": "   "},
        {"query": "x", "platform": "macos"},
        {"query": "x" * 2001},
    ],
)
def test_analyze_endpoint_validation_errors(payload: dict[str, Any]) -> None:
    resp = client.post("/api/ai/analyze", json=payload)
    assert resp.status_code == 422
