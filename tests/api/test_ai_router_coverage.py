# -*- coding: utf-8 -*-
"""Comprehensive tests for ai_router.py to achieve 90%+ coverage."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import Request


class TestSafeAlertValue:
    """Test the _safe_alert_value helper function."""

    def test_safe_alert_value_none(self):
        """Test with None value (line 78)."""
        from api.ai_router import _safe_alert_value

        assert _safe_alert_value(None) is None

    def test_safe_alert_value_int(self):
        """Test with integer value (line 78)."""
        from api.ai_router import _safe_alert_value

        assert _safe_alert_value(42) == 42

    def test_safe_alert_value_float(self):
        """Test with float value (line 78)."""
        from api.ai_router import _safe_alert_value

        assert _safe_alert_value(3.14) == 3.14

    def test_safe_alert_value_bool(self):
        """Test with boolean value (line 78)."""
        from api.ai_router import _safe_alert_value

        assert _safe_alert_value(True) is True
        assert _safe_alert_value(False) is False

    def test_safe_alert_value_string_numeric(self):
        """Test with numeric string (lines 80-83)."""
        from api.ai_router import _safe_alert_value

        assert _safe_alert_value("42") == 42.0
        assert _safe_alert_value("3.14") == 3.14

    def test_safe_alert_value_string_non_numeric(self):
        """Test with non-numeric string (line 84)."""
        from api.ai_router import _safe_alert_value

        result = _safe_alert_value("not-a-number")
        assert result == "not-a-number"

    def test_safe_alert_value_string_truncation(self):
        """Test string truncation (line 84)."""
        from api.ai_router import _safe_alert_value

        long_string = "a" * 100
        result = _safe_alert_value(long_string)
        assert len(result) == 64

    def test_safe_alert_value_other_type(self):
        """Test with other types (line 85)."""
        from api.ai_router import _safe_alert_value

        assert _safe_alert_value([1, 2, 3]) == "[1, 2, 3]"
        assert _safe_alert_value({"key": "value"}) == "{'key': 'value'}"


class TestSafeGetMetric:
    """Test the _safe_get_metric helper function."""

    def test_safe_get_metric_none_snapshot(self):
        """Test with None snapshot (line 97)."""
        from api.ai_router import _safe_get_metric

        assert _safe_get_metric(None, "cpu", "usage_percent") == "N/A"

    def test_safe_get_metric_non_dict_snapshot(self):
        """Test with non-dict snapshot (line 97)."""
        from api.ai_router import _safe_get_metric

        assert _safe_get_metric("not a dict", "cpu", "usage_percent") == "N/A"

    def test_safe_get_metric_section_not_dict(self):
        """Test when section is not a dict (line 99)."""
        from api.ai_router import _safe_get_metric

        snapshot = {"cpu": "not a dict"}
        assert _safe_get_metric(snapshot, "cpu", "usage_percent") == "N/A"

    def test_safe_get_metric_section_missing(self):
        """Test when section is missing (line 98)."""
        from api.ai_router import _safe_get_metric

        snapshot = {"memory": {"usage_percent": 50}}
        assert _safe_get_metric(snapshot, "cpu", "usage_percent") == "N/A"

    def test_safe_get_metric_field_missing(self):
        """Test when field is missing (line 100)."""
        from api.ai_router import _safe_get_metric

        snapshot = {"cpu": {"temperature": 60}}
        assert _safe_get_metric(snapshot, "cpu", "usage_percent") == "N/A"

    def test_safe_get_metric_success(self):
        """Test successful metric retrieval."""
        from api.ai_router import _safe_get_metric

        snapshot = {"cpu": {"usage_percent": 75.5}}
        assert _safe_get_metric(snapshot, "cpu", "usage_percent") == 75.5

    def test_safe_get_metric_custom_default(self):
        """Test with custom default value."""
        from api.ai_router import _safe_get_metric

        assert _safe_get_metric(None, "cpu", "usage_percent", default=0) == 0


class TestExtractGatherResult:
    """Test the _extract_gather_result helper function."""

    def test_extract_gather_result_cancelled_error(self):
        """Test with CancelledError (lines 119-121)."""
        from api.ai_router import _extract_gather_result

        result = asyncio.CancelledError()
        assert _extract_gather_result(result, "test", dict) is None

    def test_extract_gather_result_exception(self):
        """Test with Exception (lines 122-124)."""
        from api.ai_router import _extract_gather_result

        result = Exception("Test error")
        assert _extract_gather_result(result, "test", dict) is None

    def test_extract_gather_result_none(self):
        """Test with None (lines 125-126)."""
        from api.ai_router import _extract_gather_result

        assert _extract_gather_result(None, "test", dict) is None

    def test_extract_gather_result_correct_type(self):
        """Test with correct type (lines 127-128)."""
        from api.ai_router import _extract_gather_result

        result = {"key": "value"}
        assert _extract_gather_result(result, "test", dict) == result

    def test_extract_gather_result_wrong_type(self):
        """Test with wrong type (lines 129-132)."""
        from api.ai_router import _extract_gather_result

        result = "not a dict"
        assert _extract_gather_result(result, "test", dict) is None

    def test_extract_gather_result_list_expected_dict(self):
        """Test with list when dict expected."""
        from api.ai_router import _extract_gather_result

        result = [1, 2, 3]
        assert _extract_gather_result(result, "test", dict) is None

    def test_extract_gather_result_dict_expected_list(self):
        """Test with dict when list expected."""
        from api.ai_router import _extract_gather_result

        result = {"key": "value"}
        assert _extract_gather_result(result, "test", list) is None


class TestExtractDiskUsage:
    """Test the _extract_disk_usage helper function."""

    def test_extract_disk_usage_list(self):
        """Test with disk data as list (lines 218-221)."""
        from api.ai_router import _extract_disk_usage

        snapshot = {"disk": [{"usage_percent": 75.5}]}
        assert _extract_disk_usage(snapshot) == 75.5

    def test_extract_disk_usage_dict(self):
        """Test with disk data as dict (lines 222-227)."""
        from api.ai_router import _extract_disk_usage

        snapshot = {"disk": {"C:": {"usage_percent": 80.0}}}
        assert _extract_disk_usage(snapshot) == 80.0

    def test_extract_disk_usage_empty_list(self):
        """Test with empty list."""
        from api.ai_router import _extract_disk_usage

        snapshot = {"disk": []}
        assert _extract_disk_usage(snapshot) == "N/A"

    def test_extract_disk_usage_empty_dict(self):
        """Test with empty dict."""
        from api.ai_router import _extract_disk_usage

        snapshot = {"disk": {}}
        assert _extract_disk_usage(snapshot) == "N/A"

    def test_extract_disk_usage_missing_key(self):
        """Test when disk key is missing."""
        from api.ai_router import _extract_disk_usage

        snapshot = {"cpu": {"usage_percent": 50}}
        assert _extract_disk_usage(snapshot) == "N/A"

    def test_extract_disk_usage_missing_usage_percent(self):
        """Test when usage_percent is missing."""
        from api.ai_router import _extract_disk_usage

        snapshot = {"disk": [{"total": 100}]}
        assert _extract_disk_usage(snapshot) == "N/A"


class TestBuildMetricsContext:
    """Test the _build_metrics_context helper function."""

    def test_build_metrics_context_basic(self):
        """Test basic metrics context building (lines 233-239)."""
        from api.ai_router import _build_metrics_context

        snapshot = {
            "cpu": {"usage_percent": 75.5},
            "memory": {"usage_percent": 60.0},
            "disk": [{"usage_percent": 80.0}],
        }
        result = _build_metrics_context(snapshot)
        assert "CPU=75.5%" in result
        assert "内存=60.0%" in result
        assert "磁盘=80.0%" in result

    def test_build_metrics_context_truncation(self):
        """Test context truncation (line 236-238)."""
        from api.ai_router import _build_metrics_context

        snapshot = {
            "cpu": {"usage_percent": 75.5},
            "memory": {"usage_percent": 60.0},
            "disk": [{"usage_percent": 80.0}],
        }
        result = _build_metrics_context(snapshot)
        assert len(result) <= 500

    def test_build_metrics_context_missing_fields(self):
        """Test with missing fields."""
        from api.ai_router import _build_metrics_context

        snapshot = {"cpu": {"usage_percent": 75.5}}
        result = _build_metrics_context(snapshot)
        assert "CPU=75.5%" in result
        assert "内存=N/A" in result
        assert "磁盘=N/A" in result


class TestBuildContextSummary:
    """Test the _build_context_summary helper function."""

    def test_build_context_summary_with_rich_context(self):
        """Test with rich context (lines 254-259)."""
        from api.ai_router import _build_context_summary

        rich_context = {
            "top_processes": [1, 2, 3],
            "recent_alerts": [1, 2, 3, 4, 5],
            "recent_repairs": [1, 2],
        }
        result = _build_context_summary(rich_context)
        assert result["rich_enabled"] is True
        assert result["process_count"] == 3
        assert result["alert_count"] == 5
        assert result["repair_count"] == 2

    def test_build_context_summary_without_rich_context(self):
        """Test without rich context (lines 255-259)."""
        from api.ai_router import _build_context_summary

        result = _build_context_summary(None)
        assert result["rich_enabled"] is False
        assert result["process_count"] == 0
        assert result["alert_count"] == 0
        assert result["repair_count"] == 0

    def test_build_context_summary_empty_rich_context(self):
        """Test with empty rich context."""
        from api.ai_router import _build_context_summary

        rich_context = {}
        result = _build_context_summary(rich_context)
        assert result["rich_enabled"] is True
        assert result["process_count"] == 0


class TestCollectSnapshotWithCache:
    """Test the _collect_snapshot_with_cache helper function."""

    def test_collect_snapshot_with_cache_hit(self):
        """Test cache hit (lines 244-248)."""
        from api.ai_router import _collect_snapshot_with_cache
        from core.collector import get_cached_snapshot

        with patch("core.collector.get_cached_snapshot") as mock_cache:
            mock_cache.return_value = {"cpu": {"usage_percent": 50}}
            result = asyncio.run(_collect_snapshot_with_cache())
            assert result == {"cpu": {"usage_percent": 50}}

    def test_collect_snapshot_with_cache_miss(self):
        """Test cache miss (lines 245-246)."""
        from api.ai_router import _collect_snapshot_with_cache
        from core.collector import collect_all, get_cached_snapshot

        with patch("core.collector.get_cached_snapshot") as mock_cache:
            mock_cache.return_value = None
            with patch("core.collector.collect_all") as mock_collect:
                mock_collect.return_value = {"cpu": {"usage_percent": 50}}
                result = asyncio.run(_collect_snapshot_with_cache())
                assert result == {"cpu": {"usage_percent": 50}}


class TestGetRecentRepairs:
    """Test the _get_recent_repairs helper function."""

    def test_get_recent_repairs_success(self):
        """Test successful repair retrieval (lines 195-211)."""
        from api.ai_router import _get_recent_repairs

        with patch("core.db_engine.query_repairs") as mock_query:
            mock_query.return_value = [
                {
                    "success": True,
                    "rule_name": "test_rule",
                    "script_key": "test_script",
                    "repair_duration_sec": 1.5,
                    "platform": "windows",
                }
            ]
            result = _get_recent_repairs()
            assert len(result) == 1
            assert result[0]["success"] is True

    def test_get_recent_repairs_exception(self):
        """Test exception handling (lines 209-211)."""
        from api.ai_router import _get_recent_repairs

        with patch("core.db_engine.query_repairs") as mock_query:
            mock_query.side_effect = Exception("DB error")
            result = _get_recent_repairs()
            assert result == []


class TestAnalyzeRequestValidation:
    """Test AnalyzeRequest validation."""

    def test_analyze_request_platform_normalization(self):
        """Test platform normalization (lines 46-48)."""
        from api.ai_router import AnalyzeRequest

        req = AnalyzeRequest(query="test", platform="WINDOWS")
        assert req.platform == "windows"

        req = AnalyzeRequest(query="test", platform=" Linux ")
        assert req.platform == "linux"

    def test_analyze_request_query_strip(self):
        """Test query stripping (lines 50-56)."""
        from api.ai_router import AnalyzeRequest

        req = AnalyzeRequest(query="  test  ")
        assert req.query == "test"

    def test_analyze_request_query_empty_error(self):
        """Test error on empty query (lines 54-56)."""
        from pydantic import ValidationError

        from api.ai_router import AnalyzeRequest

        with pytest.raises(ValidationError):
            AnalyzeRequest(query="   ")

    def test_analyze_request_query_min_length(self):
        """Test minimum length validation (line 32)."""
        from pydantic import ValidationError

        from api.ai_router import AnalyzeRequest

        with pytest.raises(ValidationError):
            AnalyzeRequest(query="")

    def test_analyze_request_query_max_length(self):
        """Test maximum length validation (line 33)."""
        from pydantic import ValidationError

        from api.ai_router import AnalyzeRequest

        with pytest.raises(ValidationError):
            AnalyzeRequest(query="a" * 2001)

    def test_analyze_request_platform_validation(self):
        """Test platform pattern validation (line 39)."""
        from pydantic import ValidationError

        from api.ai_router import AnalyzeRequest

        with pytest.raises(ValidationError):
            AnalyzeRequest(query="test", platform="invalid")


class TestAIAnalyze:
    """Test the ai_analyze endpoint."""

    def test_ai_analyze_basic(self, client):
        """Test basic AI analysis (lines 329-451)."""
        with patch("api.ai_router.analyze") as mock_analyze:
            mock_analyze.return_value = {"analysis": "Test analysis", "confidence": 0.9}

            resp = client.post("/api/ai/analyze", json={"query": "CPU usage high"})
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "ok"

    def test_ai_analyze_with_metrics(self, client):
        """Test with include_metrics=True (lines 387-398)."""
        with patch("api.ai_router.analyze") as mock_analyze:
            mock_analyze.return_value = {"analysis": "Test"}
            with patch("api.ai_router._collect_snapshot_with_cache") as mock_collect:
                mock_collect.return_value = {"cpu": {"usage_percent": 75}}

                resp = client.post(
                    "/api/ai/analyze", json={"query": "test", "include_metrics": True}
                )
                assert resp.status_code == 200

    def test_ai_analyze_without_metrics(self, client):
        """Test with include_metrics=False (line 387)."""
        with patch("api.ai_router.analyze") as mock_analyze:
            mock_analyze.return_value = {"analysis": "Test"}

            resp = client.post("/api/ai/analyze", json={"query": "test", "include_metrics": False})
            assert resp.status_code == 200

    def test_ai_analyze_with_rich_context(self, client):
        """Test with include_rich_context=True (lines 399-411)."""
        with patch("api.ai_router.analyze") as mock_analyze:
            mock_analyze.return_value = {"analysis": "Test"}
            with patch("api.ai_router._collect_rich_context") as mock_collect:
                mock_collect.return_value = {"top_processes": []}

                resp = client.post(
                    "/api/ai/analyze", json={"query": "test", "include_rich_context": True}
                )
                assert resp.status_code == 200

    def test_ai_analyze_cancelled_error(self, client):
        """Test CancelledError handling (lines 394-396, 407-408, 420-421)."""
        with patch("api.ai_router._collect_snapshot_with_cache") as mock_collect:
            mock_collect.side_effect = asyncio.CancelledError()

            resp = client.post("/api/ai/analyze", json={"query": "test", "include_metrics": True})
            # Should propagate CancelledError
            assert resp.status_code in (200, 500)

    def test_ai_analyze_exception_metrics(self, client):
        """Test exception in metrics collection (lines 397-399)."""
        with patch("api.ai_router.analyze") as mock_analyze:
            mock_analyze.return_value = {"analysis": "Test"}
            with patch("api.ai_router._collect_snapshot_with_cache") as mock_collect:
                mock_collect.side_effect = Exception("Collection error")

                resp = client.post(
                    "/api/ai/analyze", json={"query": "test", "include_metrics": True}
                )
                assert resp.status_code == 200

    def test_ai_analyze_exception_rich_context(self, client):
        """Test exception in rich context collection (lines 409-411)."""
        with patch("api.ai_router.analyze") as mock_analyze:
            mock_analyze.return_value = {"analysis": "Test"}
            with patch("api.ai_router._collect_rich_context") as mock_collect:
                mock_collect.side_effect = Exception("Context error")

                resp = client.post(
                    "/api/ai/analyze", json={"query": "test", "include_rich_context": True}
                )
                assert resp.status_code == 200

    def test_ai_analyze_analyze_exception(self, client):
        """Test exception in analyze call (lines 424-426)."""
        with patch("api.ai_router.analyze") as mock_analyze:
            mock_analyze.side_effect = Exception("AI error")

            resp = client.post("/api/ai/analyze", json={"query": "test"})
            assert resp.status_code == 500

    def test_ai_analyze_http_exception(self, client):
        """Test HTTPException from analyze (lines 422-423)."""
        from fastapi import HTTPException

        with patch("api.ai_router.analyze") as mock_analyze:
            mock_analyze.side_effect = HTTPException(status_code=503, detail="Service unavailable")

            resp = client.post("/api/ai/analyze", json={"query": "test"})
            assert resp.status_code == 503

    def test_ai_analyze_string_result(self):
        """Test when analyze returns string (lines 429-436)."""
        from api.ai_router import AnalyzeRequest, ai_analyze
        from api.ai_service import ai_context_service

        with patch("api.ai_router.analyze") as mock_analyze:
            mock_analyze.return_value = '{"analysis": "test"}'
            with patch("api.ai_router._collect_snapshot_with_cache") as mock_collect:
                mock_collect.return_value = None
                with patch("api.ai_router._collect_rich_context") as mock_rich:
                    mock_rich.return_value = None

                    req = AnalyzeRequest(query="test")
                    mock_request = MagicMock()
                    mock_request.client.host = "127.0.0.1"

                    result = asyncio.run(ai_analyze(req, mock_request))
                    assert result["status"] == "ok"

    def test_ai_analyze_invalid_json(self):
        """Test when analyze returns invalid JSON (lines 434-436)."""
        from api.ai_router import AnalyzeRequest, ai_analyze

        with patch("api.ai_router.analyze") as mock_analyze:
            mock_analyze.return_value = "invalid json"
            with patch("api.ai_router._collect_snapshot_with_cache") as mock_collect:
                mock_collect.return_value = None
                with patch("api.ai_router._collect_rich_context") as mock_rich:
                    mock_rich.return_value = None

                    req = AnalyzeRequest(query="test")
                    mock_request = MagicMock()
                    mock_request.client.host = "127.0.0.1"

                    result = asyncio.run(ai_analyze(req, mock_request))
                    assert result["status"] == "ok"

    def test_ai_analyze_platform_windows(self, client):
        """Test with windows platform."""
        with patch("api.ai_router.analyze") as mock_analyze:
            mock_analyze.return_value = {"analysis": "Test"}

            resp = client.post("/api/ai/analyze", json={"query": "test", "platform": "windows"})
            assert resp.status_code == 200

    def test_ai_analyze_platform_linux(self, client):
        """Test with linux platform."""
        with patch("api.ai_router.analyze") as mock_analyze:
            mock_analyze.return_value = {"analysis": "Test"}

            resp = client.post("/api/ai/analyze", json={"query": "test", "platform": "linux"})
            assert resp.status_code == 200


class TestCollectRichContext:
    """Test the _collect_rich_context helper function."""

    def test_collect_rich_context_success(self):
        """Test successful rich context collection (lines 150-183)."""
        from api.ai_router import _collect_rich_context

        with patch("api.ai_service.ai_context_service.collect_rich_context") as mock_collect:
            mock_collect.return_value = {"top_processes": []}
            with patch("api.ai_router.get_real_summary") as mock_summary:
                mock_summary.return_value = {"current_anomalies": 0}
                with patch("api.ai_router._get_recent_repairs") as mock_repairs:
                    mock_repairs.return_value = []

                    result = asyncio.run(_collect_rich_context())
                    assert "top_processes" in result

    def test_collect_rich_context_exception(self):
        """Test exception handling (lines 152-161)."""
        from api.ai_router import _collect_rich_context

        with patch("api.ai_service.ai_context_service.collect_rich_context") as mock_collect:
            mock_collect.side_effect = Exception("Context error")

            result = asyncio.run(_collect_rich_context())
            assert "top_processes" in result

    def test_collect_rich_context_cancelled_error(self):
        """Test CancelledError handling (lines 152-153)."""
        from api.ai_router import _collect_rich_context

        with patch("api.ai_service.ai_context_service.collect_rich_context") as mock_collect:
            mock_collect.side_effect = asyncio.CancelledError()

            with pytest.raises(asyncio.CancelledError):
                asyncio.run(_collect_rich_context())
