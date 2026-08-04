# -*- coding: utf-8 -*-
"""Real endpoint and unit tests for api/ai_router.py."""

import json
import sys
import types
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

# Import the module object itself so we can monkeypatch its globals robustly
import api.ai_router as _ai_router
from api.ai_router import (
    router,
    _build_context_summary,
    _build_metrics_context,
    _collect_rich_context,
    _collect_snapshot_with_cache,
    _extract_disk_usage,
    _extract_gather_result,
    _safe_alert_value,
    _safe_get_metric,
)


def _valid_analysis_dict():
    return {
        "data_assessment": {"reliability_score": 0.8, "reliability_concerns": []},
        "candidates": [
            {
                "rank": 1,
                "root_cause": "high_cpu",
                "confidence": 0.9,
                "is_verifiable": True,
            }
        ],
        "escalation_recommended": False,
    }


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(
        _ai_router,
        "_collect_snapshot_with_cache",
        AsyncMock(
            return_value={
                "cpu": {"usage_percent": 12.3},
                "memory": {"usage_percent": 45.6},
                "disk": [{"usage_percent": 67.8}],
            }
        ),
    )
    monkeypatch.setattr(
        _ai_router,
        "_collect_rich_context",
        AsyncMock(
            return_value={
                "top_processes": [{"name": "python", "cpu": 10.0}],
                "recent_alerts": [{"id": "A1"}],
                "recent_repairs": [{"id": "R1"}],
            }
        ),
    )
    monkeypatch.setattr(
        _ai_router.ai_context_service,
        "collect_rich_context",
        AsyncMock(
            return_value={
                "top_processes": [{"name": "python", "cpu": 10.0}],
                "recent_alerts": [{"id": "A1"}],
                "recent_repairs": [{"id": "R1"}],
            }
        ),
    )
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


class TestAIAnalyzeEndpoint:
    """Tests for POST /api/ai/analyze."""

    def test_analyze_dict_result(self, client, monkeypatch):
        monkeypatch.setattr(
            _ai_router, "analyze", AsyncMock(return_value=_valid_analysis_dict())
        )
        response = client.post(
            "/api/ai/analyze",
            json={
                "query": "CPU high",
                "include_metrics": True,
                "platform": "windows",
                "include_rich_context": True,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["platform"] == "windows"
        assert "analysis" in data
        assert "context_summary" in data
        assert "metrics_context" in data

    def test_analyze_string_result(self, client, monkeypatch):
        monkeypatch.setattr(
            _ai_router, "analyze", AsyncMock(return_value=json.dumps(_valid_analysis_dict()))
        )
        response = client.post(
            "/api/ai/analyze",
            json={
                "query": "CPU high",
                "include_metrics": False,
                "platform": "linux",
                "include_rich_context": False,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["platform"] == "linux"
        assert data["analysis"]["data_assessment"]["reliability_score"] == 0.8

    def test_analyze_validation_empty_query(self, client):
        response = client.post(
            "/api/ai/analyze",
            json={"query": "   ", "include_metrics": False, "platform": "windows"},
        )
        assert response.status_code == 422

    def test_analyze_validation_bad_platform(self, client):
        response = client.post(
            "/api/ai/analyze",
            json={
                "query": "bad platform",
                "include_metrics": False,
                "platform": "macos",
            },
        )
        assert response.status_code == 422

    def test_analyze_http_exception_propagates(self, client, monkeypatch):
        monkeypatch.setattr(
            _ai_router,
            "analyze",
            AsyncMock(side_effect=HTTPException(status_code=503, detail="busy")),
        )
        response = client.post(
            "/api/ai/analyze",
            json={"query": "test", "include_metrics": False, "platform": "windows"},
        )
        assert response.status_code == 503

    def test_analyze_generic_exception_returns_500(self, client, monkeypatch):
        monkeypatch.setattr(
            _ai_router, "analyze", AsyncMock(side_effect=RuntimeError("ai down"))
        )
        response = client.post(
            "/api/ai/analyze",
            json={"query": "test", "include_metrics": False, "platform": "windows"},
        )
        assert response.status_code == 500
        assert "AI 引擎调用失败" in response.json()["detail"]


class TestAIHelpers:
    """Tests for pure helper functions in ai_router.py."""

    def test_safe_alert_value(self):
        assert _safe_alert_value(5) == 5
        assert _safe_alert_value(True) is True
        assert _safe_alert_value(None) is None
        assert _safe_alert_value("3.14") == 3.14
        assert _safe_alert_value("foo") == "foo"
        assert isinstance(_safe_alert_value([1, 2]), str)

    def test_safe_get_metric(self):
        assert _safe_get_metric({"cpu": {"usage_percent": 10}}, "cpu", "usage_percent") == 10
        assert _safe_get_metric({}, "cpu", "usage_percent") == "N/A"
        assert _safe_get_metric(None, "cpu", "usage_percent") == "N/A"
        assert _safe_get_metric({"cpu": []}, "cpu", "usage_percent") == "N/A"

    def test_extract_disk_usage(self):
        assert _extract_disk_usage({"disk": [{"usage_percent": 50}]}) == 50
        assert _extract_disk_usage({"disk": {"C:": {"usage_percent": 60}}}) == 60
        assert _extract_disk_usage({}) == "N/A"

    def test_build_metrics_context(self):
        snapshot = {
            "cpu": {"usage_percent": 10},
            "memory": {"usage_percent": 20},
            "disk": [{"usage_percent": 30}],
        }
        ctx = _build_metrics_context(snapshot)
        assert "CPU=10%" in ctx
        assert "内存=20%" in ctx
        assert "磁盘=30%" in ctx

    def test_build_context_summary(self):
        rich = {
            "top_processes": [1, 2],
            "recent_alerts": [1],
            "recent_repairs": [1, 2, 3],
        }
        summary = _build_context_summary(rich)
        assert summary["rich_enabled"] is True
        assert summary["process_count"] == 2
        assert summary["alert_count"] == 1
        assert summary["repair_count"] == 3
        assert _build_context_summary(None)["rich_enabled"] is False

    def test_extract_gather_result(self, caplog):
        assert _extract_gather_result([1, 2], "x", list) == [1, 2]
        assert _extract_gather_result({"a": 1}, "x", dict) == {"a": 1}
        assert _extract_gather_result(ValueError("boom"), "x", list) is None
        assert _extract_gather_result("not list", "x", list) is None


class TestAICollectionFunctions:
    """Tests for snapshot/rich-context collection helpers."""

    async def test_collect_snapshot_with_cache(self, monkeypatch):
        monkeypatch.setattr(
            _ai_router, "get_cached_snapshot", lambda: {"cpu": {"usage_percent": 5}}
        )
        snapshot = await _collect_snapshot_with_cache()
        assert snapshot == {"cpu": {"usage_percent": 5}}

    async def test_collect_rich_context_full(self, monkeypatch):
        monkeypatch.setattr(
            _ai_router.ai_context_service,
            "collect_rich_context",
            AsyncMock(return_value={"top_processes": [], "recent_alerts": [], "recent_repairs": []}),
        )
        fake_stats = types.ModuleType("core.stats_engine")
        fake_stats.get_real_summary = AsyncMock(
            return_value={"current_anomalies": 1, "total_alerts": 2, "heal_rate": 0.5, "mttr": 10}
        )
        monkeypatch.setitem(sys.modules, "core.stats_engine", fake_stats)
        monkeypatch.setattr(
            "core.db_engine.query_repairs",
            MagicMock(return_value=[{"success": True, "rule_name": "r", "script_key": "s", "platform": "windows"}]),
        )
        result = await _collect_rich_context({})
        assert result["top_processes"] == []
        assert result["stats"]["total_alerts"] == 2
        assert len(result["recent_repairs"]) == 1

    def test_analyze_rich_context_failure(self, client, monkeypatch):
        monkeypatch.setattr(
            _ai_router, "_collect_rich_context", AsyncMock(side_effect=RuntimeError("ctx fail"))
        )
        monkeypatch.setattr(_ai_router, "analyze", AsyncMock(return_value=_valid_analysis_dict()))
        response = client.post(
            "/api/ai/analyze",
            json={"query": "test", "include_metrics": False, "platform": "windows", "include_rich_context": True},
        )
        assert response.status_code == 200

    def test_analyze_invalid_string_result(self, client, monkeypatch):
        monkeypatch.setattr(_ai_router, "analyze", AsyncMock(return_value='{"invalid": "schema"}'))
        response = client.post(
            "/api/ai/analyze",
            json={"query": "test", "include_metrics": False, "platform": "windows"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "analysis" in data
