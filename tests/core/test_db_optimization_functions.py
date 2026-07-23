# -*- coding: utf-8 -*-
"""Targeted tests for core.db_optimization validation helpers and stubs."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import core.db_optimization as dbopt


def _session_factory(cm):
    """Return a simple callable that yields the given context manager."""
    return MagicMock(return_value=cm)


def _make_session_mock(rows=None, fetchone=None):
    """Build a mock async session for db_optimization functions."""
    session = MagicMock()
    result = MagicMock()
    result.fetchone = MagicMock(return_value=fetchone)
    result.fetchall = MagicMock(return_value=rows or [])
    session.execute = AsyncMock(return_value=result)
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()

    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=session)
    cm.__aexit__ = AsyncMock(return_value=None)
    return cm, session


class TestValidation:
    def test_validate_sql_identifier_ok(self) -> None:
        assert dbopt.validate_sql_identifier("valid_name") == "valid_name"

    @pytest.mark.parametrize(
        "identifier,msg",
        [
            ("", "cannot be empty"),
            ("123bad", "Invalid SQL identifier"),
            ("select", "SQL keyword"),
            ("bad--comment", "dangerous pattern"),
            ("a" * 129, "too long"),
        ],
    )
    def test_validate_sql_identifier_bad(self, identifier: str, msg: str) -> None:
        with pytest.raises(ValueError, match=msg):
            dbopt.validate_sql_identifier(identifier)

    def test_validate_sql_identifier_non_string(self) -> None:
        with pytest.raises(ValueError, match="must be string"):
            dbopt.validate_sql_identifier(123)  # type: ignore[arg-type]

    def test_validate_table_name_ok(self) -> None:
        assert dbopt.validate_table_name("alerts") == "alerts"

    def test_validate_table_name_not_allowed(self) -> None:
        with pytest.raises(ValueError, match="not in allowed whitelist"):
            dbopt.validate_table_name("forbidden_table")

    def test_validate_sql_query_structure_ok(self) -> None:
        assert dbopt.validate_sql_query_structure("SELECT 1", ["SELECT"]) is True

    def test_validate_sql_query_structure_no_allowed_op(self) -> None:
        with pytest.raises(ValueError, match="must contain one of allowed operations"):
            dbopt.validate_sql_query_structure("UPDATE x", ["SELECT"])

    def test_validate_sql_query_structure_dangerous(self) -> None:
        with pytest.raises(ValueError, match="dangerous pattern"):
            dbopt.validate_sql_query_structure("SELECT 1; DROP TABLE x", ["SELECT"])

    def test_validate_sql_query_structure_non_string(self) -> None:
        with pytest.raises(ValueError, match="Query must be a string"):
            dbopt.validate_sql_query_structure(123)  # type: ignore[arg-type]


class TestIndexSpec:
    def test_performance_indexes(self) -> None:
        assert len(dbopt.PERFORMANCE_INDEXES) > 0
        spec = dbopt.PERFORMANCE_INDEXES[0]
        assert isinstance(spec, dbopt._IndexSpec)
        assert spec.name and spec.table and spec.columns


class TestAsyncOptimization:
    @pytest.mark.asyncio
    async def test_create_performance_indexes(self) -> None:
        cm, session = _make_session_mock(fetchone=None)
        with patch.object(dbopt, "AsyncSessionLocal", _session_factory(cm)):
            result = await dbopt.create_performance_indexes()
        assert result["created"] == len(dbopt.PERFORMANCE_INDEXES)
        assert result["failed"] == 0
        assert session.commit.await_count == len(dbopt.PERFORMANCE_INDEXES)

    @pytest.mark.asyncio
    async def test_create_performance_indexes_already_exists(self) -> None:
        # fetchone returns a tuple, meaning index already exists
        cm, session = _make_session_mock(fetchone=("existing",))
        with patch.object(dbopt, "AsyncSessionLocal", _session_factory(cm)):
            result = await dbopt.create_performance_indexes()
        assert result["already_exists"] == len(dbopt.PERFORMANCE_INDEXES)
        assert result["created"] == 0

    @pytest.mark.asyncio
    async def test_create_performance_indexes_exception(self) -> None:
        cm, _ = _make_session_mock()
        cm.__aenter__ = AsyncMock(side_effect=RuntimeError("db down"))
        with patch.object(dbopt, "AsyncSessionLocal", _session_factory(cm)):
            result = await dbopt.create_performance_indexes()
        assert "error" in result

    @pytest.mark.asyncio
    async def test_analyze_query_performance(self) -> None:
        rows = [
            ("SELECT 1", 20, 1000.0, 1.5, 10.0, 1.0),
            ("SELECT 2", 20, 5000.0, 0.5, 10.0, 1.0),
            ("SELECT 3", 20, 8000.0, 6.0, 100.0, 5.0),
        ]
        cm, _ = _make_session_mock(rows=rows)
        with patch.object(dbopt, "AsyncSessionLocal", _session_factory(cm)):
            result = await dbopt.analyze_query_performance()
        assert result["total_analyzed"] == 3
        assert len(result["slow_queries"]) >= 1
        assert len(result["very_slow_queries"]) >= 1

    @pytest.mark.asyncio
    async def test_update_database_statistics(self) -> None:
        cm, _ = _make_session_mock()
        with patch.object(dbopt, "AsyncSessionLocal", _session_factory(cm)):
            result = await dbopt.update_database_statistics()
        assert result["status"] == "completed"
        assert "results" in result

    @pytest.mark.asyncio
    async def test_get_missing_indexes_suggestions(self) -> None:
        rows = [("public", "alerts", "detected_at", 0, 0, 0)]
        cm, _ = _make_session_mock(rows=rows)
        with patch.object(dbopt, "AsyncSessionLocal", _session_factory(cm)):
            result = await dbopt.get_missing_indexes_suggestions()
        assert len(result) == 1
        assert result[0]["table"] == "alerts"

    @pytest.mark.asyncio
    async def test_optimize_database_configuration(self) -> None:
        cm, _ = _make_session_mock()
        with patch.object(dbopt, "AsyncSessionLocal", _session_factory(cm)):
            result = await dbopt.optimize_database_configuration()
        assert result["status"] == "success"
        assert len(result["optimizations_applied"]) == 3

    @pytest.mark.asyncio
    async def test_run_comprehensive_optimization(self) -> None:
        cm, _ = _make_session_mock()
        with patch.object(dbopt, "AsyncSessionLocal", _session_factory(cm)):
            result = await dbopt.run_comprehensive_optimization()
        assert "steps" in result
        assert "create_indexes" in result["steps"]
        assert "update_statistics" in result["steps"]


class TestStubs:
    @pytest.mark.parametrize(
        "func,args",
        [
            (dbopt.clear_slow_queries, []),
            (dbopt.configure_db_optimization, [{}]),
            (dbopt.get_connection_pool_config, []),
            (dbopt.get_connection_pool_statistics, []),
            (dbopt.get_db_optimization_config, []),
            (dbopt.get_performance_summary, []),
            (dbopt.get_query_cache_config, []),
            (dbopt.get_query_cache_statistics, []),
            (dbopt.get_slow_queries, []),
            (dbopt.get_slow_queries, [5]),
            (dbopt.is_db_optimization_enabled, []),
            (dbopt.reset_query_cache, []),
            (dbopt.update_query_cache_config, [{}]),
            (dbopt.record_connection_pool_usage, [10, 5]),
            (dbopt.record_query_cache_hit, ["q"]),
            (dbopt.record_query_cache_miss, ["q"]),
            (dbopt.record_slow_query, ["q", 1.0]),
            (dbopt.reset_query_cache_statistics, []),
            (dbopt.suggest_optimizations, []),
        ],
    )
    def test_stub_returns_expected_type(self, func, args) -> None:
        result = func(*args)
        if func in (dbopt.get_slow_queries, dbopt.suggest_optimizations):
            assert isinstance(result, list)
        elif func is dbopt.is_db_optimization_enabled:
            assert isinstance(result, bool)
        else:
            assert isinstance(result, dict)

    def test_record_query_cache_hit_returns_query(self) -> None:
        assert dbopt.record_query_cache_hit("query1")["query"] == "query1"

    def test_record_connection_pool_usage_values(self) -> None:
        assert dbopt.record_connection_pool_usage(20, 8)["pool_size"] == 20
