# -*- coding: utf-8 -*-
"""Regression tests for the 8th batch of medium-severity ledger fixes (2026-09-14).

Covered ledger items:

* API-138 ``api/cost_management_router.py`` — ``total_realized_savings`` is now
  derived from the optimizations that were actually approved/implemented (never
  extrapolated as ``potential * 0.3``); the anomaly/report summaries aggregate
  the real database rows instead of returning hard-coded zeros; and the
  optimization/anomaly/report "create" endpoints persist their records so the
  summaries (and the approve endpoint) operate on real data.
* API-083 ``api/backup_router.py`` / ``core/disaster_recovery.py`` — a database
  restore only ever reads a file that lives inside the configured backup
  directory (arbitrary-path / path-traversal restore is refused).
"""

import asyncio

import pytest

import api.cost_management_router as cm
from core.disaster_recovery import DisasterRecovery


# ---------------------------------------------------------------------------
# Helpers for the cost-management database paths
# ---------------------------------------------------------------------------
class _Row:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class _FakeQuery:
    def __init__(self, rows):
        self._rows = rows

    def all(self):  # noqa: ANN001
        return self._rows


class _FakeSession:
    def __init__(self, rows=None):
        self._rows = rows or []
        self.added = []

    def query(self, *args, **kwargs):  # noqa: ANN001
        return _FakeQuery(self._rows)

    def add(self, obj):  # noqa: ANN001
        self.added.append(obj)

    def commit(self):
        return None

    def close(self):
        return None


# ---------------------------------------------------------------------------
# API-138 — savings summary
# ---------------------------------------------------------------------------
def test_savings_summary_never_extrapolates_realized(monkeypatch):
    """Without persistence the realized figure is genuinely 0 (not potential*0.3)."""
    monkeypatch.setattr(cm, "SessionLocal", None)
    monkeypatch.setattr(cm, "CostOptimizationDB", None)
    monkeypatch.setattr(
        cm,
        "get_optimization_suggestions",
        lambda: [{"potential_savings": 200.0, "priority": "high"}],
    )

    summary = asyncio.run(cm.get_savings_summary(period="monthly", user=None))

    assert summary["status"] == "success"
    assert summary["total_potential_savings"] == 200.0
    assert summary["total_realized_savings"] == 0.0
    assert summary["by_priority"]["high"] == 200.0
    assert summary["source"] == "live_suggestions"


def test_savings_summary_realized_from_approved_rows(monkeypatch):
    """Realized savings come from approved/implemented optimizations only."""
    rows = [
        _Row(potential_savings=100.0, priority="high", status="approved"),
        _Row(potential_savings=40.0, priority="high", status="implemented"),
        _Row(potential_savings=60.0, priority="low", status="pending"),
    ]
    monkeypatch.setattr(cm, "SessionLocal", lambda: _FakeSession(rows))
    monkeypatch.setattr(cm, "CostOptimizationDB", object)

    summary = asyncio.run(cm.get_savings_summary(period="monthly", user=None))

    assert summary["total_potential_savings"] == 200.0
    assert summary["total_realized_savings"] == 140.0
    assert summary["optimization_count"] == 3
    assert summary["source"] == "database"


# ---------------------------------------------------------------------------
# API-138 — anomaly / report summaries aggregate real rows
# ---------------------------------------------------------------------------
def test_anomaly_summary_aggregates_rows(monkeypatch):
    rows = [
        _Row(severity="high", status="open", affected_amount=10.0),
        _Row(severity="high", status="resolved", affected_amount=5.0),
        _Row(severity="medium", status="open", affected_amount=2.0),
    ]
    monkeypatch.setattr(cm, "SessionLocal", lambda: _FakeSession(rows))
    monkeypatch.setattr(cm, "CostAnomalyDB", object)

    summary = asyncio.run(cm.get_anomaly_summary(period="monthly", user=None))

    assert summary["total_anomalies"] == 3
    assert summary["by_severity"]["high"] == 2
    assert summary["by_severity"]["medium"] == 1
    assert summary["by_status"]["open"] == 2
    assert summary["by_status"]["resolved"] == 1
    assert summary["total_affected_amount"] == 17.0


def test_reports_summary_aggregates_rows(monkeypatch):
    rows = [
        _Row(report_type="summary", status="completed", total_cost=120.0),
        _Row(report_type="forecast", status="failed", total_cost=0.0),
    ]
    monkeypatch.setattr(cm, "SessionLocal", lambda: _FakeSession(rows))
    monkeypatch.setattr(cm, "CostReportDB", object)

    summary = asyncio.run(cm.get_reports_summary(period="monthly", user=None))

    assert summary["total_reports"] == 2
    assert summary["by_type"]["summary"] == 1
    assert summary["by_type"]["forecast"] == 1
    assert summary["by_status"]["completed"] == 1
    assert summary["by_status"]["failed"] == 1
    assert summary["total_cost_covered"] == 120.0


def test_create_optimization_persists_record(monkeypatch):
    session = _FakeSession([])
    monkeypatch.setattr(cm, "SessionLocal", lambda: session)
    monkeypatch.setattr(cm, "CostOptimizationDB", lambda **kwargs: kwargs)

    payload = cm.CostOptimizationCreate(
        service="payments",
        optimization_type="rightsizing",
        potential_savings=25.0,
        implementation_effort="low",
        priority="high",
    )
    result = asyncio.run(cm.create_optimization(optimization_data=payload, user=None))

    assert result["optimization"]["persisted"] is True
    assert len(session.added) == 1
    assert session.added[0]["status"] == "pending"
    assert session.added[0]["potential_savings"] == 25.0


# ---------------------------------------------------------------------------
# API-083 — restore is confined to the backup directory
# ---------------------------------------------------------------------------
def test_resolve_within_backup_dir(tmp_path):
    backups = tmp_path / "backups"
    backups.mkdir()
    dr = DisasterRecovery(backup_dir=str(backups))

    inside = backups / "db_backup.sql"
    inside.write_text("SELECT 1;")

    assert dr._resolve_within_backup_dir(str(inside)) == inside.resolve()
    assert dr._resolve_within_backup_dir(str(tmp_path / "other.sql")) is None
    assert dr._resolve_within_backup_dir(str(backups / ".." / "escape.sql")) is None


def test_restore_database_rejects_outside_backup_dir(tmp_path):
    backups = tmp_path / "backups"
    backups.mkdir()
    dr = DisasterRecovery(backup_dir=str(backups))

    outside = tmp_path / "evil.sql"
    outside.write_text("DROP TABLE users;")

    # The path exists but escapes the backup directory -> refused.
    assert dr.restore_database(str(outside)) is False


def test_restore_database_rejects_traversal_within_name(tmp_path):
    backups = tmp_path / "backups"
    backups.mkdir()
    dr = DisasterRecovery(backup_dir=str(backups))

    evil = tmp_path / "secret.sql"
    evil.write_text("SELECT 1;")

    assert dr.restore_database(str(backups / ".." / "secret.sql")) is False


# ---------------------------------------------------------------------------
# API-154 — execution coverage is read from the persisted column
# ---------------------------------------------------------------------------
def test_execution_maps_coverage_from_db():
    from datetime import datetime
    from types import SimpleNamespace

    from api.test_automation_advanced_router import _db_to_execution

    row = SimpleNamespace(
        id="exec-1",
        suite_id="suite-1",
        suite_name="Regression",
        status="completed",
        started_at=datetime.now(),
        completed_at=datetime.now(),
        total_tests=10,
        passed_tests=9,
        failed_tests=1,
        skipped_tests=0,
        coverage=87.5,
        triggered_by="alice",
        trigger_type="manual",
    )

    result = _db_to_execution(row)

    assert result.coverage == 87.5
