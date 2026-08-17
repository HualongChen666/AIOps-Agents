# -*- coding: utf-8 -*-
"""Batch 27b coverage tests for zero-coverage core modules."""

import asyncio
import json
from datetime import datetime, timezone

import pytest
from fastapi import Response
from pydantic import ValidationError

from core.error_handling import (
    AIEngineError,
    AIOpsException,
    AIOpsHTTPException,
    AuthenticationError,
    DatabaseError,
    ErrorCode,
    NotFoundError,
    PermissionDeniedError,
)
from core.error_handling import ValidationError as AIOpsValidationError
from core.error_handling import (
    create_error_response,
    handle_aiops_exception,
    handle_generic_exception,
    log_error,
)
from core.frontend_cache_strategy import (
    CacheStrategy,
    FrontendCacheStrategies,
    apply_cache_headers,
    cache_response,
    get_etag_for_data,
    setup_cache_headers_middleware,
)
from core.observability_schema import (
    CommonLabels,
    LogRecord,
    MetricInfo,
    TraceContext,
    build_log_record,
)
from core.test_automation_manager import (
    AutomationStatus,
    TestAutomationManager,
    get_automation_manager,
)
from core.test_coverage_manager import (
    CoverageLevel,
    TestCoverageManager,
    get_coverage_manager,
)

pytestmark = [pytest.mark.core]


# ---------------------------------------------------------------------------
# core.test_automation_manager
# ---------------------------------------------------------------------------
class TestTestAutomationManager:
    def test_init_defaults(self):
        manager = TestAutomationManager()
        assert manager.automation_jobs == {}
        assert manager.total_jobs == 0
        assert manager.cicd_config["enabled"] is False

    def test_create_and_run_job(self):
        manager = TestAutomationManager({"notification_enabled": True})
        assert manager.create_automation_job("j1", "job-one", "unit") is True
        assert manager.create_automation_job("j1", "job-one", "unit") is False
        assert manager.run_automation_job("missing") is False
        assert manager.run_automation_job("j1") is True
        assert manager.automation_jobs["j1"].status == AutomationStatus.COMPLETED
        assert manager.successful_jobs == 1

    def test_generate_pipelines(self, tmp_path):
        manager = TestAutomationManager()
        gh = tmp_path / "gh.yml"
        gl = tmp_path / "gl.yml"
        jk = tmp_path / "jk.txt"
        assert manager.generate_ci_cd_pipeline(str(gh), "github_actions") is True
        assert "unit-tests" in gh.read_text()
        assert manager.generate_ci_cd_pipeline(str(gl), "gitlab_ci") is True
        assert "stages" in gl.read_text()
        assert manager.generate_ci_cd_pipeline(str(jk), "jenkins") is True
        assert "pipeline" in jk.read_text()
        assert manager.generate_ci_cd_pipeline(str(gh), "azure") is False

        bad_path = tmp_path / "missing" / "file.yml"
        assert manager.generate_ci_cd_pipeline(str(bad_path), "github_actions") is False

    def test_generate_reports(self, tmp_path):
        manager = TestAutomationManager()
        manager.create_automation_job("r1", "report-job", "e2e")
        manager.run_automation_job("r1")
        html = tmp_path / "report.html"
        jsonf = tmp_path / "report.json"
        xmlf = tmp_path / "report.xml"
        assert manager.generate_test_report("html", str(html)) is True
        assert "<!DOCTYPE html>" in html.read_text()
        assert manager.generate_test_report("json", str(jsonf)) is True
        assert json.loads(jsonf.read_text())["summary"]["total_jobs"] == 1
        assert manager.generate_test_report("xml", str(xmlf)) is True
        assert "<testsuite" in xmlf.read_text()
        assert manager.generate_test_report("yaml", str(tmp_path / "bad.yml")) is False

        bad_path = tmp_path / "missing" / "report.html"
        assert manager.generate_test_report("html", str(bad_path)) is False

    def test_notification_and_summary(self):
        manager = TestAutomationManager({"notification_enabled": True})
        assert manager.send_notification("j1", "completed", "ok") is True
        manager.notification_config.enabled = False
        assert manager.send_notification("j1", "completed", "ok") is False

        summary = manager.get_automation_summary()
        assert summary["success_rate"] == 0.0

        manager.create_automation_job("j2", "job-two", "unit")
        manager.run_automation_job("j2")
        summary = manager.get_automation_summary()
        assert summary["total_jobs"] == 1
        assert summary["success_rate"] == 100.0

    def test_global_manager(self, monkeypatch):
        import core.test_automation_manager as tam

        monkeypatch.setattr(tam, "_automation_manager", None)
        m1 = get_automation_manager()
        m2 = get_automation_manager()
        assert m1 is m2


# ---------------------------------------------------------------------------
# core.test_coverage_manager
# ---------------------------------------------------------------------------
class TestTestCoverageManager:
    def test_init_and_thresholds(self):
        manager = TestCoverageManager({"default_threshold": 90.0})
        assert "core" in manager.coverage_thresholds
        assert manager.default_threshold == 90.0

    def test_add_and_query(self):
        manager = TestCoverageManager()
        assert manager.add_module_coverage("m1", "mod1", 0, 0) is False
        assert manager.add_module_coverage("m1", "mod1", 100, 95) is True
        assert manager.module_coverage["m1"].coverage_level == CoverageLevel.EXCELLENT
        assert manager.add_module_coverage("m2", "mod2", 100, 85) is True
        assert manager.module_coverage["m2"].coverage_level == CoverageLevel.GOOD
        assert manager.add_module_coverage("m3", "mod3", 100, 75) is True
        assert manager.module_coverage["m3"].coverage_level == CoverageLevel.ACCEPTABLE
        assert manager.add_module_coverage("m4", "mod4", 100, 65) is True
        assert manager.module_coverage["m4"].coverage_level == CoverageLevel.NEEDS_IMPROVEMENT

    def test_threshold_checks(self):
        manager = TestCoverageManager()
        assert manager.check_coverage_threshold("nope", "core")["meets_threshold"] is False
        manager.add_module_coverage("c1", "core1", 100, 85)
        result = manager.check_coverage_threshold("c1", "core")
        assert result["meets_minimum"] is True
        assert result["meets_target"] is True
        result = manager.check_coverage_threshold("c1", "unknown")
        assert result["minimum_coverage"] == 80.0

    def test_summary_and_report(self):
        manager = TestCoverageManager()
        report = manager.get_coverage_report()
        assert "summary" in report
        assert len(report["recommendations"]) == 1

        manager.add_module_coverage("h1", "high", 100, 95)
        manager.add_module_coverage("h2", "high2", 100, 95)
        summary = manager.get_coverage_summary()
        assert summary["total_modules"] == 2
        assert summary["average_coverage"] == 95.0
        report = manager.get_coverage_report()
        assert not report["modules_below_threshold"]

    def test_global_manager(self, monkeypatch):
        import core.test_coverage_manager as tcm

        monkeypatch.setattr(tcm, "_coverage_manager", None)
        m1 = get_coverage_manager()
        m2 = get_coverage_manager()
        assert m1 is m2


# ---------------------------------------------------------------------------
# core.frontend_cache_strategy
# ---------------------------------------------------------------------------
class TestFrontendCacheStrategy:
    def test_cache_strategy_directives(self):
        no_store = CacheStrategy(no_store=True)
        assert "no-store" in no_store.to_cache_control_header()

        no_cache = CacheStrategy(no_cache=True)
        assert "no-cache" in no_cache.to_cache_control_header()

        normal = CacheStrategy(
            max_age=300,
            stale_while_revalidate=60,
            stale_if_error=86400,
            must_revalidate=True,
            private=True,
        )
        header = normal.to_cache_control_header()
        assert "max-age=300" in header
        assert "stale-while-revalidate=60" in header
        assert "stale-if-error=86400" in header
        assert "must-revalidate" in header
        assert "private" in header

        public = CacheStrategy(max_age=60, stale_while_revalidate=0, stale_if_error=0)
        assert "public" in public.to_cache_control_header()

    def test_endpoint_strategies(self):
        assert (
            FrontendCacheStrategies.get_strategy_for_endpoint("/api/v1/alerts")
            is FrontendCacheStrategies.ALERT_LIST
        )
        assert (
            FrontendCacheStrategies.get_strategy_for_endpoint("/api/v1/metrics")
            is FrontendCacheStrategies.DASHBOARD_DATA
        )
        assert (
            FrontendCacheStrategies.get_strategy_for_endpoint("/api/v1/realtime")
            is FrontendCacheStrategies.REALTIME_DATA
        )
        assert (
            FrontendCacheStrategies.get_strategy_for_endpoint("/api/v1/config")
            is FrontendCacheStrategies.USER_CONFIG
        )
        assert (
            FrontendCacheStrategies.get_strategy_for_endpoint("/api/v1/health")
            is FrontendCacheStrategies.REALTIME_DATA
        )
        assert (
            FrontendCacheStrategies.get_strategy_for_endpoint("/api/v1/auth")
            is FrontendCacheStrategies.SENSITIVE_DATA
        )
        assert (
            FrontendCacheStrategies.get_strategy_for_endpoint("/api/v1/other")
            is FrontendCacheStrategies.DASHBOARD_DATA
        )

    def test_apply_cache_headers_and_etag(self):
        response = Response(content="hello")
        strategy = CacheStrategy(max_age=120)
        last = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        apply_cache_headers(response, strategy, etag="abc", last_modified=last)
        assert "max-age=120" in response.headers["Cache-Control"]
        assert response.headers["ETag"] == "abc"
        assert "Last-Modified" in response.headers
        assert "Expires" in response.headers

    def test_get_etag(self):
        assert get_etag_for_data({"a": 1, "b": 2}) == get_etag_for_data({"b": 2, "a": 1})
        assert get_etag_for_data(["a", "b"]) is not None
        assert get_etag_for_data("plain") is not None

    def test_setup_middleware(self):
        result = setup_cache_headers_middleware()
        assert result["status"] == "success"
        assert "STATIC_RESOURCES" in result["strategies"]

    def test_cache_response_decorator(self):
        strategy = CacheStrategy(max_age=60)

        @cache_response(strategy)
        async def endpoint():
            return Response(content='{"ok": true}', media_type="application/json")

        result = asyncio.run(endpoint())
        assert "Cache-Control" in result.headers


# ---------------------------------------------------------------------------
# core.error_handling
# ---------------------------------------------------------------------------
class TestErrorHandling:
    def test_error_codes(self):
        assert ErrorCode.INTERNAL_ERROR == "GEN_1000"
        assert ErrorCode.AUTH_INVALID_TOKEN == "AUTH_4000"

    def test_exceptions(self):
        exc = AIOpsException("boom", details={"x": 1})
        assert exc.to_dict()["error_code"] == "GEN_1000"

        assert AIOpsValidationError("bad").status_code == 400
        assert NotFoundError("missing").status_code == 404
        assert PermissionDeniedError("no").status_code == 403
        assert AIEngineError("ai fail").status_code == 500
        assert DatabaseError("db fail").status_code == 500
        assert AuthenticationError("auth fail").status_code == 401

    def test_handlers(self):
        exc = AIOpsException("test", error_code=ErrorCode.INVALID_REQUEST)
        result = handle_aiops_exception(exc)
        assert result["error_code"] == "GEN_1001"

        result = handle_generic_exception(ValueError("oops"))
        assert result["error_code"] == "GEN_1000"

    def test_create_and_log_error(self, caplog):
        http_exc = create_error_response(
            ErrorCode.NOT_FOUND, "not found", details={"id": 1}, status_code=404
        )
        assert http_exc.status_code == 404

        with caplog.at_level("ERROR"):
            log_error(ErrorCode.DB_CONNECTION_ERROR, "db down")
        assert "DB_3000" in caplog.text


# ---------------------------------------------------------------------------
# core.observability_schema
# ---------------------------------------------------------------------------
class TestObservabilitySchema:
    def test_common_labels(self):
        labels = CommonLabels(service="svc", env="dev", region="us", tenant="t1", instance="pod-1")
        assert labels.env == "dev"

    def test_common_labels_validation_error(self):
        with pytest.raises(ValidationError):
            CommonLabels(service="svc", env="invalid", region="us", instance="x")

    def test_log_record_and_build(self):
        payload = {
            "level": "INFO",
            "message": "hello",
            "service": "svc",
            "env": "staging",
            "region": "us",
            "instance": "pod-1",
            "extra": {"foo": "bar"},
        }
        record = build_log_record(payload)
        assert record.message == "hello"
        assert record.level == "INFO"

        with pytest.raises(ValidationError):
            build_log_record({**payload, "level": "BAD"})

    def test_metric_info(self):
        info = MetricInfo(
            name="my_metric",
            description="desc",
            unit="seconds",
            type="counter",
            labels=["x"],
        )
        assert info.type == "counter"

        with pytest.raises(ValidationError):
            MetricInfo(name="m", description="d", type="wrong")

    def test_trace_context(self):
        trace_id = "0" * 32
        span_id = "0" * 16
        ctx = TraceContext(trace_id=trace_id, span_id=span_id)
        header = ctx.to_header()
        assert header == f"00-{trace_id}-{span_id}-01"
