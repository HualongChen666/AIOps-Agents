# -*- coding: utf-8 -*-
"""Tests for core/data_lifecycle_manager.py."""

import gzip
import json
import os

import pytest

from core.data_lifecycle_manager import (
    DataCategory,
    DataLifecycleManager,
    DataLifecycleRule,
    DataRetentionPolicy,
    setup_data_lifecycle,
)


class _FakeRow:
    """Row proxy exposing the ``_mapping`` attribute used by the manager."""

    def __init__(self, data):
        self._mapping = data


class _FakeResult:
    """Result proxy exposing ``fetchall``/``rowcount``."""

    def __init__(self, rows):
        self._rows = rows
        self.rowcount = len(rows)

    def fetchall(self):
        return [_FakeRow(row) for row in self._rows]


class _RecordingSession:
    """Async session double that records the SQL statements it is asked to run."""

    def __init__(self, rows=None):
        self.rows = rows or []
        self.statements = []
        self.committed = False

    async def execute(self, statement, params=None):
        self.statements.append((str(statement), params))
        return _FakeResult(self.rows)

    async def commit(self):
        self.committed = True

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc_info):
        return False


def test_get_retention_days():
    manager = DataLifecycleManager()
    assert manager.get_retention_days(DataRetentionPolicy.RETAIN_7_DAYS) == 7
    assert manager.get_retention_days(DataRetentionPolicy.RETAIN_PERMANENT) == -1


@pytest.mark.asyncio
async def test_archive_old_data(tmp_path):
    rows = [{"id": "alert-1", "detected_at": "2020-01-01T00:00:00"}]
    session = _RecordingSession(rows)
    manager = DataLifecycleManager(archive_root=str(tmp_path), session_factory=lambda: session)

    result = await manager.archive_old_data(DataCategory.ALERTS)

    assert result["status"] == "success"
    assert result["archived_count"] == 1
    # Real SQL against the columns declared in core/models.py.
    assert any(
        "SELECT * FROM alerts" in sql and "detected_at < :cutoff" in sql
        for sql, _ in session.statements
    )
    assert any("DELETE FROM alerts" in sql for sql, _ in session.statements)
    assert session.committed is True

    # The expired rows were written to a real gzip-compressed archive on disk.
    archives = list((tmp_path / "alerts").glob("*.jsonl.gz"))
    assert len(archives) == 1
    with gzip.open(archives[0], "rt", encoding="utf-8") as handle:
        archived = [json.loads(line) for line in handle if line.strip()]
    assert archived == rows

    result = await manager.archive_old_data(DataCategory.TEMPORARY)
    assert result["status"] == "skipped"

    result = await manager.archive_old_data("unknown")
    assert result["status"] == "error"


@pytest.mark.asyncio
async def test_archive_reports_backend_failure():
    """A failing storage backend is surfaced, never masked as success."""

    def _unavailable():
        raise RuntimeError("database unavailable")

    manager = DataLifecycleManager(session_factory=_unavailable)
    result = await manager.archive_old_data(DataCategory.ALERTS)
    assert result["status"] == "error"
    assert "database unavailable" in result["error"]


@pytest.mark.asyncio
async def test_delete_expired_rows(tmp_path):
    session = _RecordingSession([])
    manager = DataLifecycleManager(archive_root=str(tmp_path), session_factory=lambda: session)

    result = await manager._delete_expired_data(DataCategory.METRICS, 30)

    assert result["status"] == "success"
    assert result["deleted_count"] == 0
    assert any(
        "DELETE FROM metrics" in sql and "timestamp < :cutoff" in sql
        for sql, _ in session.statements
    )


@pytest.mark.asyncio
async def test_cleanup_temp_data(monkeypatch, tmp_path):
    monkeypatch.setenv("TEMPORARY_DATA_DIR", str(tmp_path))
    manager = DataLifecycleManager()
    result = await manager.cleanup_temp_data()
    assert result["status"] == "success"
    assert "deleted_count" in result


def test_purge_directory_removes_only_expired_files(tmp_path):
    from datetime import datetime, timedelta, timezone

    old_file = tmp_path / "old.log"
    new_file = tmp_path / "new.log"
    old_file.write_text("stale", encoding="utf-8")
    new_file.write_text("fresh", encoding="utf-8")

    now = datetime.now(timezone.utc)
    stale_time = (now - timedelta(days=10)).timestamp()
    os.utime(old_file, (stale_time, stale_time))

    removed = DataLifecycleManager._purge_directory(tmp_path, now - timedelta(days=1))

    assert removed == 1
    assert not old_file.exists()
    assert new_file.exists()


@pytest.mark.asyncio
async def test_apply_retention_policy(monkeypatch, tmp_path):
    monkeypatch.setenv("TEMPORARY_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("BACKUP_LOCATION", str(tmp_path))
    session = _RecordingSession([])
    manager = DataLifecycleManager(archive_root=str(tmp_path), session_factory=lambda: session)

    result = await manager.apply_retention_policy(DataCategory.METRICS)
    assert result["status"] == "success"

    result = await manager.apply_retention_policy(DataCategory.CONFIGURATION)
    assert result["status"] == "success"


def test_rules_and_stats():
    manager = DataLifecycleManager()
    rules = manager.get_rules()
    assert DataCategory.ALERTS in rules
    stats = manager.get_cleanup_stats()
    assert "total_archived" in stats
    new_rule = DataLifecycleRule(
        category=DataCategory.TEMPORARY,
        retention_policy=DataRetentionPolicy.RETAIN_7_DAYS,
        archive_enabled=False,
    )
    manager.add_rule(new_rule)
    assert manager.get_rules()[DataCategory.TEMPORARY].archive_enabled is False


@pytest.mark.asyncio
async def test_setup_data_lifecycle():
    result = await setup_data_lifecycle()  # noqa: F841  # Variable for test verification
    assert result["status"] == "success"
    assert "rules_count" in result
