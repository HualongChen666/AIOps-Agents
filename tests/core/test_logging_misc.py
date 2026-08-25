# -*- coding: utf-8 -*-
"""Tests for observability_query, log_router and logging modules."""

from datetime import datetime, timezone

import pytest  # noqa: F401  # Imported for test setup

import core.log_router
import core.logging.analysis.log_alerting
import core.logging.analysis.log_analyzer
import core.logging.context.context_manager
import core.logging.level.level_manager
import core.observability_query


def test_observability_query_validation():
    core.observability_query.validate_promql("up")
    core.observability_query.validate_logql('{job="test"}')
    core.observability_query.validate_es_query_string("cpu usage")
    core.observability_query.validate_clickhouse_identifier("metrics")
    core.observability_query.validate_clickhouse_metric_name("cpu_usage")

    with pytest.raises(ValueError):
        core.observability_query.validate_promql("bad!char")


def test_observability_query_build_and_helpers():
    sql, params = core.observability_query.build_clickhouse_query(
        "metrics", ["timestamp", "value"], ["host"], ["h1"], "timestamp", 10
    )
    assert "SELECT" in sql
    assert params == ["h1"]

    assert "password=<REDACTED>" in core.observability_query.redact_text("password=secret")
    assert core.observability_query.approx_token_count({"a": 1}) > 0
    assert core.observability_query.parse_duration_to_seconds("1h") == 3600.0
    assert isinstance(core.observability_query.sanitize_error_for_llm(ValueError("x")), str)

    result = core.observability_query.prepare_for_llm(
        {"key": "value"}
    )  # noqa: F841  # Variable for test verification
    assert isinstance(result, dict)
    assert result["_llm_meta"]["redacted"] is True


def test_observability_query_limit_and_align():
    now = datetime.now(timezone.utc)
    start = datetime.now(timezone.utc)
    step = core.observability_query.limit_range_samples(start, now, 1.0, max_samples=1000)
    assert step > 0
    end, start = core.observability_query.align_time_window(now, 3600.0)
    assert isinstance(end, datetime) and isinstance(start, datetime)


async def test_observability_cached_query():
    cache = core.observability_query.QueryCache()

    async def dummy():
        return {"value": 42}

    result = await core.observability_query.cached_query(
        cache, "k", dummy()
    )  # noqa: F841  # Variable for test verification
    assert result == {"value": 42}  # noqa: F841  # Variable for test verification

    result2 = await core.observability_query.cached_query(cache, "k", dummy())
    assert result2 == {"value": 42}


def test_log_router():
    router = core.log_router.create_log_router({"destinations": []})
    assert router is not None
    entry = core.log_router.LogEntry(
        timestamp=datetime.now(timezone.utc),
        level=core.log_router.LogLevel.INFO,
        message="test",
        service="s",
        host="h",
        environment="e",
        labels={},
        extra={},
    )
    assert "streams" in entry.to_loki_format()
    assert isinstance(entry.to_dict(), dict)


def test_log_analyzer():
    analyzer = core.logging.analysis.log_analyzer.get_log_analyzer()
    analyzer.clear_buffer()
    analyzer.add_log(
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "message": "error happened",
            "level": "ERROR",
        }
    )
    assert analyzer.get_buffer_size() == 1
    stats = analyzer.calculate_statistics()
    assert stats.total_logs == 1
    patterns = analyzer.detect_patterns(min_occurrences=1)
    assert isinstance(patterns, list)


def test_log_alerting():
    analyzer = core.logging.analysis.log_analyzer.get_log_analyzer()
    manager = core.logging.analysis.log_alerting.get_alert_manager(analyzer)
    alert = core.logging.analysis.log_alerting.ThresholdAlert(
        name="high_error",
        metric="error_rate",
        threshold=0.5,
    )
    manager.add_threshold_alert(alert)
    assert len(manager.get_alert_history()) == 0
    manager.clear_alert_history()


def test_logging_context():
    mgr = core.logging.context.context_manager.get_logging_context_manager()
    assert mgr is not None
    ctx = core.logging.context.context_manager.get_logging_context()
    assert ctx is not None
    assert core.logging.context.context_manager.get_current_trace_id() is None or isinstance(
        core.logging.context.context_manager.get_current_trace_id(), str
    )


def test_logging_level():
    mgr = core.logging.level.level_manager.get_level_manager()
    assert mgr.get_default_level() is not None
    level = core.logging.level.level_manager.get_log_level("core")
    assert level is not None
