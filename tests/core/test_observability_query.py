# -*- coding: utf-8 -*-
"""Tests for core/observability_query.py."""

import pytest

from core.observability_query import (
    QueryCache,
    align_time_window,
    approx_token_count,
    build_clickhouse_query,
    get_query_semaphore,
    limit_range_samples,
    make_cache_key,
    parse_duration_to_seconds,
    prepare_for_llm,
    redact_text,
    sanitize_error_for_llm,
    validate_clickhouse_identifier,
    validate_clickhouse_metric_name,
    validate_es_query_string,
    validate_logql,
    validate_promql,
    validate_tempoql,
)


def test_validate_promql_and_logql():
    validate_promql("up{job='node'}")
    validate_logql('{job="node"}')
    with pytest.raises(ValueError):
        validate_promql("up; drop")
    with pytest.raises(ValueError):
        validate_logql("{job")


def test_validate_es_and_clickhouse():
    validate_es_query_string("kubernetes.labels.app:api")
    validate_clickhouse_identifier("metrics_table")
    validate_clickhouse_metric_name("cpu:usage")
    with pytest.raises(ValueError):
        validate_es_query_string("drop table")
    with pytest.raises(ValueError):
        validate_clickhouse_identifier("1bad")


def test_build_clickhouse_query():
    sql, params = build_clickhouse_query(
        "metrics", ["ts", "value"], ["service"], ["api"], "ts", limit=10
    )
    assert "SELECT" in sql
    assert params == ["api"]


def test_redact_and_prepare():
    assert "<REDACTED>" in redact_text("password=secret")
    data = {"user": "alice", "email": "a@b.com"}
    prepared = prepare_for_llm(data, max_tokens=1000, max_items=50)
    assert isinstance(prepared, dict)
    assert "_llm_meta" in prepared
    assert approx_token_count(prepared) > 0


def test_time_helpers():
    start, end = align_time_window(duration_seconds=3600)
    assert end > start
    assert parse_duration_to_seconds("5m") == 300.0
    assert limit_range_samples(start, end, 1.0, max_samples=10) >= 1.0


def test_sanitize_and_validate_tempoql():
    assert "query_failed" in sanitize_error_for_llm(ValueError("boom"))
    validate_tempoql('{name="value"}')


def test_cache_and_semaphore():
    cache = QueryCache(ttl=60)
    key = make_cache_key("promql", "q")
    cache.set(key, {"data": []})
    value, hit = cache.get(key)
    assert value == {"data": []}
    assert hit is True
    sem = get_query_semaphore(max_concurrent=5)
    assert sem._value == 5
