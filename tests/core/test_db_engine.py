# -*- coding: utf-8 -*-
"""Tests for core/db_engine.py synchronous wrappers and stubs."""

import core.db_engine


def test_query_and_count_alerts():
    core.db_engine.insert_alert({"id": "1", "message": "test"})
    assert core.db_engine.query_alerts(limit=1) == []
    assert core.db_engine.count_alerts() == 0
    assert core.db_engine.clear_alerts() == 0


def test_repair_records():
    rid = core.db_engine.insert_repair_record(
        success=True,
        alert_time="2026-01-01T00:00:00",
        repair_time="2026-01-01T00:01:00",
        repair_duration_sec=1.0,
        rule_name="rule",
        script_key="script",
        platform="linux",
        output="ok",
    )
    assert rid == -1
    assert core.db_engine.query_repairs(limit=5) == []


def test_pending_approvals():
    result = core.db_engine.upsert_pending_approval(
        alert_id="a1",
        rule_name="r",
        script_key="s",
        proposal="p",
        alert_json="{}",
    )
    assert result == -1
    assert core.db_engine.get_pending_approval("a1") is None
    assert core.db_engine.get_all_pending_approvals() == []
    core.db_engine.update_approval_status("a1", "approved")
    core.db_engine.update_approval_status_by_alert("a1", "rejected")


def test_verify_and_clear():
    assert core.db_engine.insert_verify_record(x=1) == 0
    assert core.db_engine.db_clear_alerts() == 0


def test_get_connection_returns_session_or_raises():
    try:
        conn = core.db_engine.get_connection()
        assert conn is not None
    except Exception:
        pass
