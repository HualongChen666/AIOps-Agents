# -*- coding: utf-8 -*-
"""Real instantiation branch-coverage tests for modules/rum/data_collector.py.

These tests exercise every branch using real class instances and concrete data
without mocks or internal monkeypatching.
"""

from datetime import datetime, timedelta

import pytest  # noqa: F401  # Imported for test setup

from modules.rum.data_collector import (
    RUMDataAggregator,
    RUMDataCollector,
    RUMDataReceiver,
    RUMDataValidator,
    RUMEvent,
    RUMEventType,
    RUMRealTimeAnalyzer,
    SessionAggregation,
    create_rum_data_collector,
)


def _now_iso() -> str:
    return datetime.now().isoformat()


# ----------------------------------------------------------------------
# dataclass to_dict branches
# ----------------------------------------------------------------------
def test_event_to_dict():
    event = RUMEvent(
        event_id="evt-1",
        event_type=RUMEventType.PAGE_VIEW,
        session_id="session-12345",
        user_id="user-1",
        timestamp=datetime.now(),
        data={"foo": "bar"},
    )
    d = event.to_dict()
    assert d["event_id"] == "evt-1"
    assert d["event_type"] == "page_view"


def test_session_aggregation_to_dict_with_and_without_end_time():
    agg = SessionAggregation(
        session_id="session-12345",
        user_id="user-1",
        start_time=datetime.now(),
    )
    assert agg.to_dict()["end_time"] is None

    agg.end_time = datetime.now()
    assert agg.to_dict()["end_time"] is not None


# ----------------------------------------------------------------------
# Validator branches
# ----------------------------------------------------------------------
def test_validator_valid_event():
    validator = RUMDataValidator()
    event = {
        "session_id": "session-12345",
        "timestamp": _now_iso(),
    }
    ok, errors = validator.validate_event(event)
    assert ok is True
    assert errors == []


def test_validator_missing_required_and_type_and_timestamp_and_session_id():
    validator = RUMDataValidator()

    # missing session_id
    ok, errors = validator.validate_event({"timestamp": _now_iso()})
    assert ok is False
    assert any("session_id" in e for e in errors)

    # missing timestamp
    ok, errors = validator.validate_event({"session_id": "session-12345"})
    assert ok is False
    assert any("timestamp" in e for e in errors)

    # timestamp is not a string
    ok, errors = validator.validate_event(
        {
            "session_id": "session-12345",
            "timestamp": 12345,
        }
    )
    assert ok is False
    assert any("Invalid type for timestamp" in e for e in errors)

    # invalid timestamp format
    ok, errors = validator.validate_event(
        {
            "session_id": "session-12345",
            "timestamp": "not-a-timestamp",
        }
    )
    assert ok is False
    assert any("Invalid timestamp format" in e for e in errors)

    # session_id too short
    ok, errors = validator.validate_event(
        {
            "session_id": "short",
            "timestamp": _now_iso(),
        }
    )
    assert ok is False
    assert any("Invalid session_id format" in e for e in errors)

    # session_id not a string
    ok, errors = validator.validate_event(
        {
            "session_id": 1234567890,
            "timestamp": _now_iso(),
        }
    )
    assert ok is False
    assert any("Invalid session_id format" in e for e in errors)


def test_validator_sanitize_data():
    validator = RUMDataValidator()

    long_value = "x" * 1200
    data = {
        "password": "secret123",
        "token": None,
        "note": "safe",
        "long": long_value,
        "number": 42,
        "keep": "b" * 1000,
    }
    sanitized = validator.sanitize_data(data)
    assert sanitized["password"] == "***REDACTED***"
    assert sanitized["token"] == "***REDACTED***"
    assert sanitized["note"] == "safe"
    assert sanitized["long"].endswith("...[truncated]")
    assert len(sanitized["long"]) < 1200
    assert sanitized["number"] == 42
    assert len(sanitized["keep"]) == 1000


# ----------------------------------------------------------------------
# Receiver branches
# ----------------------------------------------------------------------
def test_receiver_valid_and_invalid_and_batch_and_statistics():
    receiver = RUMDataReceiver()

    valid = {
        "type": "page_view",
        "session_id": "session-12345",
        "user_id": "user-1",
        "timestamp": _now_iso(),
        "pageUrl": "/home",
    }
    invalid = {
        "type": "page_view",
        "session_id": "session-12345",
        # missing timestamp
    }

    event = receiver.receive_event(valid)
    assert event is not None
    assert event.event_type == RUMEventType.PAGE_VIEW

    rejected = receiver.receive_event(invalid)
    assert rejected is None
    assert len(receiver.rejected_events) == 1

    stats = receiver.get_statistics()
    assert stats["total_received"] == 1
    assert stats["total_rejected"] == 1
    assert stats["by_type"] == {"page_view": 1}

    batch = receiver.receive_batch([invalid, valid])
    assert len(batch) == 1
    assert batch[0].event_type == RUMEventType.PAGE_VIEW


# ----------------------------------------------------------------------
# Aggregator branches
# ----------------------------------------------------------------------
def test_aggregator_all_event_types_and_browsers_and_stats():
    aggregator = RUMDataAggregator()

    # empty stats
    assert aggregator.get_aggregation_statistics() == {}

    base = _now_iso()  # noqa: F841  # Variable for test verification
    page_view = RUMEvent(
        event_id="evt-pv",
        event_type=RUMEventType.PAGE_VIEW,
        session_id="session-page",
        user_id="user-pv",
        timestamp=datetime.now(),
        data={"userAgent": "Mozilla Chrome/91", "platform": "web"},
    )
    aggregator.aggregate_event(page_view)

    error = RUMEvent(
        event_id="evt-err",
        event_type=RUMEventType.ERROR,
        session_id="session-page",
        user_id="user-pv",
        timestamp=datetime.now(),
        data={},
    )
    aggregator.aggregate_event(error)

    # existing session
    page_load = RUMEvent(
        event_id="evt-pl",
        event_type=RUMEventType.PAGE_LOAD,
        session_id="session-page",
        user_id="user-pv",
        timestamp=datetime.now(),
        data={"load_time": 2500},
    )
    aggregator.aggregate_event(page_load)

    # zero load_time branch
    page_load_zero = RUMEvent(
        event_id="evt-pl0",
        event_type=RUMEventType.PAGE_LOAD,
        session_id="session-page",
        user_id="user-pv",
        timestamp=datetime.now(),
        data={"load_time": 0},
    )
    aggregator.aggregate_event(page_load_zero)

    # custom/other event type
    custom = RUMEvent(
        event_id="evt-cust",
        event_type=RUMEventType.CUSTOM,
        session_id="session-page",
        user_id="user-pv",
        timestamp=datetime.now(),
        data={"info": "x"},
    )
    aggregator.aggregate_event(custom)

    assert aggregator.get_session_aggregation("session-page") is not None
    assert aggregator.get_session_aggregation("missing") is None

    all_aggs = aggregator.get_all_aggregations()
    assert len(all_aggs) == 1

    stats = aggregator.get_aggregation_statistics()
    assert stats["total_sessions"] == 1
    assert stats["total_page_views"] == 1
    assert stats["total_errors"] == 1
    assert stats["error_rate"] == 1.0
    assert stats["avg_page_load_time"] > 0


def test_aggregator_browser_variants():
    aggregator = RUMDataAggregator()
    now = datetime.now()

    browsers = [
        ("Mozilla/5.0 Chrome/91.0", "Chrome"),
        ("Mozilla/5.0 Firefox/90.0", "Firefox"),
        ("Mozilla/5.0 Safari/605.1", "Safari"),
        ("Mozilla/5.0 Edge/91.0", "Edge"),
        ("Mozilla/5.0 (compatible; Bot/1.0)", "Unknown"),
    ]

    for idx, (ua, expected) in enumerate(browsers):
        evt = RUMEvent(
            event_id=f"evt-{idx}",
            event_type=RUMEventType.PAGE_VIEW,
            session_id=f"session-{idx:03d}",
            user_id="u",
            timestamp=now,
            data={"userAgent": ua} if ua else {},
        )
        aggregator.aggregate_event(evt)
        agg = aggregator.get_session_aggregation(f"session-{idx:03d}")
        assert agg is not None
        assert agg.browser == expected

    # platform present and absent already covered by previous tests
    platform_evt = RUMEvent(
        event_id="evt-plat",
        event_type=RUMEventType.PAGE_VIEW,
        session_id="session-plat",
        user_id="u",
        timestamp=now,
        data={"platform": "ios"},
    )
    aggregator.aggregate_event(platform_evt)
    assert aggregator.get_session_aggregation("session-plat").platform == "ios"


def test_aggregation_statistics_error_rate_zero_page_views():
    aggregator = RUMDataAggregator()
    now = datetime.now()

    # session with page_load (avg_load_time > 0) but zero page views
    load_only = RUMEvent(
        event_id="evt-load",
        event_type=RUMEventType.PAGE_LOAD,
        session_id="session-load",
        user_id="u",
        timestamp=now,
        data={"load_time": 1500},
    )
    aggregator.aggregate_event(load_only)

    # session with only an error, no page views
    error_only = RUMEvent(
        event_id="evt-err-only",
        event_type=RUMEventType.ERROR,
        session_id="session-err",
        user_id="u",
        timestamp=now,
        data={},
    )
    aggregator.aggregate_event(error_only)

    stats = aggregator.get_aggregation_statistics()
    assert stats["total_page_views"] == 0
    assert stats["error_rate"] == 0
    assert stats["avg_page_load_time"] > 0


# ----------------------------------------------------------------------
# Analyzer branches
# ----------------------------------------------------------------------
def test_analyzer_page_load_and_error_alerts():
    analyzer = RUMRealTimeAnalyzer()

    slow_load = RUMEvent(
        event_id="evt-slow",
        event_type=RUMEventType.PAGE_LOAD,
        session_id="session-abc",
        user_id="u",
        timestamp=datetime.now(),
        data={"load_time": 5000},
    )
    analyzer.analyze_event(slow_load)
    assert any(a["alert_type"] == "slow_page_load" for a in analyzer.alerts)

    fast_load = RUMEvent(
        event_id="evt-fast",
        event_type=RUMEventType.PAGE_LOAD,
        session_id="session-abc",
        user_id="u",
        timestamp=datetime.now(),
        data={"load_time": 100},
    )
    analyzer.analyze_event(fast_load)

    error = RUMEvent(
        event_id="evt-err",
        event_type=RUMEventType.ERROR,
        session_id="session-abc",
        user_id="u",
        timestamp=datetime.now(),
        data={"errorMessage": "boom"},
    )
    analyzer.analyze_event(error)
    assert any(a["alert_type"] == "error_detected" for a in analyzer.alerts)

    custom = RUMEvent(
        event_id="evt-cust",
        event_type=RUMEventType.CUSTOM,
        session_id="session-abc",
        user_id="u",
        timestamp=datetime.now(),
        data={},
    )
    analyzer.analyze_event(custom)

    # get_alerts filters by cutoff
    old = {
        "alert_type": "old",
        "message": "old alert",
        "session_id": "session-abc",
        "timestamp": (datetime.now() - timedelta(hours=2)).isoformat(),
    }
    analyzer.alerts.append(old)

    recent = analyzer.get_alerts(hours=1)
    assert all(a["alert_type"] != "old" for a in recent)


def test_analyzer_aggregation_error_rate_branches():
    analyzer = RUMRealTimeAnalyzer()

    # page_views == 0
    no_views = SessionAggregation(
        session_id="s-empty",
        user_id="u",
        start_time=datetime.now(),
    )
    analyzer.analyze_aggregation(no_views)

    # high error rate
    high = SessionAggregation(
        session_id="s-high",
        user_id="u",
        start_time=datetime.now(),
        page_views=1,
        errors=1,
    )
    analyzer.analyze_aggregation(high)
    assert any(a["alert_type"] == "high_error_rate" for a in analyzer.alerts)

    # low error rate
    low = SessionAggregation(
        session_id="s-low",
        user_id="u",
        start_time=datetime.now(),
        page_views=100,
        errors=1,
    )
    analyzer.analyze_aggregation(low)


# ----------------------------------------------------------------------
# Collector / factory branches
# ----------------------------------------------------------------------
def test_collector_end_to_end():
    collector = create_rum_data_collector()

    now = _now_iso()

    valid_page = {
        "type": "page_view",
        "session_id": "session-top",
        "user_id": "user-1",
        "timestamp": now,
        "userAgent": "Mozilla/5.0 Chrome/91.0",
        "platform": "web",
    }
    collector.process_event(valid_page)

    valid_load = {
        "type": "page_load",
        "session_id": "session-top",
        "user_id": "user-1",
        "timestamp": now,
        "load_time": 6000,
    }
    collector.process_event(valid_load)

    invalid = {
        "type": "page_view",
        "session_id": "session-top",
        "user_id": "user-1",
        # missing timestamp
    }
    assert collector.process_event(invalid) is None

    # batch with mixed validity
    batch = [
        {
            "type": "error",
            "session_id": "session-top2",
            "user_id": "u",
            "timestamp": now,
            "errorMessage": "x",
        },
        {"type": "page_view", "session_id": "short", "timestamp": now},  # invalid session id
    ]
    processed = collector.process_batch(batch)
    assert len(processed) == 1

    dashboard = collector.get_dashboard_data()
    assert "receiver_stats" in dashboard
    assert "aggregation_stats" in dashboard
    assert "recent_alerts" in dashboard
    assert "top_sessions" in dashboard
    assert isinstance(dashboard["top_sessions"], list)


def test_collector_instantiation():
    collector = RUMDataCollector()
    assert collector.receiver is not None
    assert collector.aggregator is not None
    assert collector.analyzer is not None
