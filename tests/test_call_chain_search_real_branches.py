# -*- coding: utf-8 -*-
"""Branch-coverage tests for core.call_chain_search using real data and calls."""

from datetime import datetime, timedelta, timezone

import pytest  # noqa: F401  # Imported for test setup

from core.call_chain_search import (
    CallChainSearchManager,
    SearchCriteria,
    SearchFilter,
    SearchOperator,
    SearchResult,
    SortOrder,
    get_call_chain_search_manager,
)


@pytest.fixture(autouse=True)
def ensure_database():
    """Override the shared DB reset fixture; these tests do not need a database."""
    yield


def _make_manager():
    """Factory helper returning a fresh CallChainSearchManager."""
    return get_call_chain_search_manager({"sample_key": "sample_value"})


def test_factory_and_statistics():
    """Exercise factory, statistics and empty manager behaviour."""
    manager = _make_manager()
    assert isinstance(manager, CallChainSearchManager)
    stats = manager.get_statistics()
    assert stats["total_searches"] == 0
    assert stats["total_results"] == 0
    assert stats["indexed_traces"] == 0
    assert stats["indexed_services"] == 0
    assert stats["indexed_operations"] == 0
    assert stats["time_index_size"] == 0

    assert manager.search_by_trace_id("none") is None
    assert manager.search_by_service_name("none") == []
    assert manager.search_by_criteria(SearchCriteria()) == []


def test_add_and_index_branches():
    """Exercise add_call_chain and _update_indexes branches."""
    manager = _make_manager()

    # Missing trace_id -> early return
    manager.add_call_chain({"service_name": "ghost"})
    assert manager.call_chains == {}

    # Minimal trace to skip all optional indexes
    manager.add_call_chain({"trace_id": "t-minimal"})
    assert "t-minimal" in manager.call_chains
    assert manager.service_index == {}
    assert manager.operation_index == {}
    assert manager.status_index == {}
    assert manager.time_index == []

    # Trace with string start_time
    manager.add_call_chain(
        {
            "trace_id": "t-1",
            "service_name": "svc-a",
            "operation_name": "op-a",
            "status": "OK",
            "start_time": "2024-01-01T10:00:00+00:00",
            "end_time": "2024-01-01T10:00:01+00:00",
            "duration_ms": 1000.0,
            "tags": {"env": "prod"},
            "metadata": {"host": "h1"},
        }
    )
    assert "svc-a" in manager.service_index
    assert "op-a" in manager.operation_index
    assert "OK" in manager.status_index
    assert len(manager.time_index) == 1

    # Trace with datetime start_time and new service/operation/status
    dt = datetime(2024, 1, 2, 10, 0, 0, tzinfo=timezone.utc)
    manager.add_call_chain(
        {
            "trace_id": "t-2",
            "service_name": "svc-b",
            "operation_name": "op-b",
            "status": "ERROR",
            "start_time": dt,
            "end_time": dt + timedelta(seconds=2),
            "duration_ms": 2000.0,
            "tags": {"env": "dev"},
            "metadata": {"host": "h2"},
        }
    )
    assert manager.time_index == sorted(manager.time_index, key=lambda x: x[0])

    # Search by trace_id hit/miss
    assert manager.search_by_trace_id("t-1") is not None
    assert manager.search_by_trace_id("t-2") is not None
    assert manager.search_by_trace_id("missing") is None

    # Search by service name with limit
    results = manager.search_by_service_name("svc-a", limit=1)
    assert len(results) == 1
    assert results[0]["trace_id"] == "t-1"

    # Stale index entry (not in call_chains) returns nothing, covering the guard branch
    manager._update_indexes("stale", {"service_name": "stale-svc"})
    assert manager.search_by_service_name("stale-svc") == []


def test_criteria_search_branches():
    """Exercise search_by_criteria and all internal filter branches."""
    manager = _make_manager()

    base = datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)  # noqa: F841  # Variable for test verification
    manager.add_call_chain(
        {
            "trace_id": "t-ok",
            "service_name": "checkout",
            "operation_name": "process",
            "status": "OK",
            "start_time": base.isoformat(),
            "end_time": (base + timedelta(seconds=1)).isoformat(),
            "duration_ms": 1000.0,
            "tags": {"env": "prod", "region": "us-east"},
            "metadata": {"host": "h1"},
        }
    )
    manager.add_call_chain(
        {
            "trace_id": "t-err",
            "service_name": "checkout",
            "operation_name": "refund",
            "status": "ERROR",
            "start_time": (base + timedelta(hours=1)).isoformat(),
            "end_time": (base + timedelta(hours=1, seconds=2)).isoformat(),
            "duration_ms": 2500.0,
            "tags": {"env": "prod"},
            "metadata": {"host": "h2"},
        }
    )
    manager.add_call_chain(
        {
            "trace_id": "t-bad-time",
            "service_name": "other",
            "operation_name": "noop",
            "status": "OK",
            "start_time": "not-a-timestamp",
            "duration_ms": 0.0,
        }
    )

    # Empty criteria -> zero score / all results
    all_results = manager.search_by_criteria(SearchCriteria())
    assert len(all_results) == 3
    assert all(r.match_score == 0.0 for r in all_results)

    # Trace_id filter
    crit = SearchCriteria(trace_id="t-ok")
    assert len(manager.search_by_criteria(crit)) == 1

    # Service + operation + status + time + duration + tags
    crit = SearchCriteria(
        service_name="checkout",
        operation_name="process",
        status="OK",
        start_time=base - timedelta(seconds=1),
        end_time=base + timedelta(minutes=1),
        min_duration_ms=500.0,
        max_duration_ms=1500.0,
        tags={"env": "prod"},
    )
    results = manager.search_by_criteria(crit)
    assert len(results) == 1
    assert results[0].trace_id == "t-ok"

    # Time range filter excludes t-ok but includes t-err
    crit = SearchCriteria(
        service_name="checkout",
        start_time=base + timedelta(minutes=30),
        end_time=base + timedelta(minutes=90),
    )
    results = manager.search_by_criteria(crit)
    assert len(results) == 1
    assert results[0].trace_id == "t-err"

    # Duration filter only
    crit = SearchCriteria(min_duration_ms=2000.0)
    results = manager.search_by_criteria(crit)
    assert len(results) == 1
    assert results[0].trace_id == "t-err"

    # Tag mismatch
    crit = SearchCriteria(tags={"env": "staging"})
    assert manager.search_by_criteria(crit) == []

    # Sort ASC by duration_ms and DESC by trace_id
    crit = SearchCriteria(sort_by="duration_ms", sort_order=SortOrder.ASC)
    results = manager.search_by_criteria(crit)
    assert results[0].duration_ms <= results[-1].duration_ms

    crit = SearchCriteria(sort_by="trace_id", sort_order=SortOrder.DESC)
    results = manager.search_by_criteria(crit)
    assert results[0].trace_id >= results[-1].trace_id

    # Sort with missing attribute falls back to start_time
    crit = SearchCriteria(sort_by="nonexistent", sort_order=SortOrder.ASC)
    results = manager.search_by_criteria(crit)
    # Should still return without error
    assert len(results) == 3

    # Pagination
    crit = SearchCriteria(limit=1, offset=1, sort_by="trace_id", sort_order=SortOrder.ASC)
    results = manager.search_by_criteria(crit)
    assert len(results) == 1


def test_custom_filter_operators_and_errors():
    """Exercise every SearchOperator branch and the except path."""
    manager = _make_manager()
    manager.add_call_chain(
        {
            "trace_id": "t-filters",
            "service_name": "svc",
            "operation_name": "op",
            "status": "OK",
            "start_time": "2024-01-01T10:00:00+00:00",
            "duration_ms": 100.0,
            "tags": {"color": "blue"},
            "payload": "hello world",
            "list_field": ["a", "b", "c"],
            "numeric": "50",
            "bad_numeric": "abc",
        }
    )

    def one(operator, value, field="payload"):
        return manager.search_by_criteria(
            SearchCriteria(
                custom_filters=[SearchFilter(field=field, operator=operator, value=value)]
            )
        )

    # EQUALS / NOT_EQUALS
    assert one(SearchOperator.EQUALS, "hello world")[0].trace_id == "t-filters"
    assert one(SearchOperator.NOT_EQUALS, "goodbye")[0].trace_id == "t-filters"

    # CONTAINS / NOT_CONTAINS
    assert one(SearchOperator.CONTAINS, "world")[0].trace_id == "t-filters"
    assert one(SearchOperator.NOT_CONTAINS, "missing")[0].trace_id == "t-filters"

    # Numeric comparisons on numeric string
    assert one(SearchOperator.GREATER_THAN, 25, field="numeric")[0].trace_id == "t-filters"
    assert one(SearchOperator.LESS_THAN, 100, field="numeric")[0].trace_id == "t-filters"
    assert one(SearchOperator.GREATER_THAN_OR_EQUAL, 50, field="numeric")[0].trace_id == "t-filters"
    assert one(SearchOperator.LESS_THAN_OR_EQUAL, 50, field="numeric")[0].trace_id == "t-filters"

    # Bad numeric triggers ValueError -> False
    assert one(SearchOperator.GREATER_THAN, 10, field="bad_numeric") == []

    # IN / NOT_IN on a scalar status field
    assert one(SearchOperator.IN, ["OK", "ERROR"], field="status")[0].trace_id == "t-filters"
    assert one(SearchOperator.NOT_IN, ["MISSING"], field="status")[0].trace_id == "t-filters"

    # REGEX
    assert one(SearchOperator.REGEX, r"^hello", field="payload")[0].trace_id == "t-filters"

    # Unknown operator falls through to True
    class FakeOperator:
        value = "fake"

    fake_filter = SearchFilter(field="payload", operator=FakeOperator(), value="x")
    assert manager._matches_filter("anything", fake_filter) is True


def test_filter_helpers_and_parse_datetime_directly():
    """Directly call filter helpers and _parse_datetime for branch coverage."""
    manager = _make_manager()

    now = datetime.now(timezone.utc)
    manager.add_call_chain(
        {
            "trace_id": "t-1",
            "service_name": "svc",
            "operation_name": "op",
            "status": "OK",
            "start_time": now.isoformat(),
            "end_time": (now + timedelta(seconds=1)).isoformat(),
            "duration_ms": 100.0,
            "tags": {"env": "prod"},
        }
    )
    # Add a second chain missing start_time so _filter_by_time_range skips it
    manager.add_call_chain(
        {
            "trace_id": "t-2",
            "service_name": "svc",
            "operation_name": "op",
            "status": "OK",
            "duration_ms": 50.0,
            "tags": {"env": "prod"},
        }
    )

    candidate_ids = {"t-1", "t-2", "missing"}

    # _filter_by_time_range branches
    assert "t-1" in manager._filter_by_time_range(
        candidate_ids, now - timedelta(seconds=1), now + timedelta(seconds=2)
    )
    assert "t-2" not in manager._filter_by_time_range(
        candidate_ids, now, now + timedelta(seconds=2)
    )
    assert "missing" not in manager._filter_by_time_range(
        candidate_ids, now, now + timedelta(seconds=2)
    )
    # end_time before trace start triggers line 336
    assert "t-1" not in manager._filter_by_time_range(
        candidate_ids, now - timedelta(seconds=2), now - timedelta(seconds=1)
    )

    # _filter_by_duration_range branches
    assert "t-1" in manager._filter_by_duration_range(candidate_ids, 50.0, 150.0)
    assert "t-2" in manager._filter_by_duration_range(candidate_ids, None, 75.0)
    assert "missing" not in manager._filter_by_duration_range(candidate_ids, None, None)

    # _filter_by_tags branches
    assert "t-1" in manager._filter_by_tags(candidate_ids, {"env": "prod"})
    assert "t-1" not in manager._filter_by_tags(candidate_ids, {"env": "dev"})
    assert "missing" not in manager._filter_by_tags(candidate_ids, {"env": "prod"})

    # _apply_custom_filter branches
    sf = SearchFilter(field="duration_ms", operator=SearchOperator.GREATER_THAN, value=75.0)
    assert "t-1" in manager._apply_custom_filter(candidate_ids, sf)
    assert "missing" not in manager._apply_custom_filter(candidate_ids, sf)

    # _parse_datetime branches
    assert manager._parse_datetime(now) is now
    parsed = manager._parse_datetime("2024-01-01T00:00:00+00:00")
    assert isinstance(parsed, datetime)
    assert manager._parse_datetime("invalid") is None
    assert manager._parse_datetime(None) is None
    assert manager._parse_datetime(123) is None


def test_match_score_and_result_dataclass():
    """Exercise _calculate_match_score and SearchResult construction."""
    manager = _make_manager()
    now = datetime.now(timezone.utc)

    trace_data = {
        "trace_id": "t-1",
        "service_name": "svc",
        "operation_name": "op",
        "status": "OK",
    }
    # No criteria -> zero score
    assert manager._calculate_match_score(trace_data, SearchCriteria()) == 0.0

    # Full match -> 1.0
    full = SearchCriteria(
        trace_id="t-1",
        service_name="svc",
        operation_name="op",
        status="OK",
    )
    assert manager._calculate_match_score(trace_data, full) == 1.0

    # Partial match
    partial = SearchCriteria(trace_id="t-1", service_name="svc", status="OTHER")
    score = manager._calculate_match_score(trace_data, partial)
    assert 0.0 < score < 1.0

    # SearchResult defaults
    result = SearchResult(  # noqa: F841  # Variable for test verification
        trace_id="x",
        service_name="s",
        operation_name="o",
        start_time=now,
        end_time=now,
        duration_ms=1.0,
        status="OK",
    )
    assert result.match_score == 0.0
    assert result.metadata == {}
