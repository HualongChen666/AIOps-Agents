# -*- coding: utf-8 -*-
"""Targeted tests for core.db_engine async DB helpers and wrappers."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import core.db_engine as db_engine


def _make_session_mock(
    scalar_one_or_none=None,
    scalars_all=None,
    scalar=0,
    rowcount=1,
):
    """Return an async-session context manager mock."""
    result = MagicMock()
    result.scalar_one_or_none = MagicMock(return_value=scalar_one_or_none)
    result.scalars.return_value.all.return_value = scalars_all or []
    result.scalar.return_value = scalar
    result.rowcount = rowcount

    session = MagicMock()
    session.add = MagicMock()
    session.execute = AsyncMock(return_value=result)
    session.commit = AsyncMock()
    session.rollback = AsyncMock()

    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=session)
    cm.__aexit__ = AsyncMock(return_value=None)
    return cm, session


@pytest.fixture
def mock_session():
    cm, session = _make_session_mock()
    with patch.object(db_engine, "AsyncSessionLocal", return_value=cm):
        yield session


class TestAsyncSessionHelpers:
    @pytest.mark.asyncio
    async def test_async_get_session_commits(self) -> None:
        cm, _ = _make_session_mock()
        with patch.object(db_engine, "AsyncSessionLocal", return_value=cm):
            async with db_engine.async_get_session() as session:
                assert session is cm.__aenter__.return_value
        assert cm.__aexit__.await_count == 1

    @pytest.mark.asyncio
    async def test_async_get_session_rollbacks(self) -> None:
        cm, session = _make_session_mock()
        with patch.object(db_engine, "AsyncSessionLocal", return_value=cm):
            with pytest.raises(RuntimeError):
                async with db_engine.async_get_session() as session:
                    raise RuntimeError("boom")
        assert session.rollback.await_count == 1

    @pytest.mark.asyncio
    async def test_async_init_db(self) -> None:
        conn = MagicMock()
        conn.run_sync = AsyncMock()
        begin_cm = MagicMock()
        begin_cm.__aenter__ = AsyncMock(return_value=conn)
        begin_cm.__aexit__ = AsyncMock(return_value=None)
        mock_engine = MagicMock()
        mock_engine.begin = MagicMock(return_value=begin_cm)
        with patch.object(db_engine, "engine", mock_engine):
            await db_engine.async_init_db()
        assert conn.run_sync.await_count == 1


class TestAsyncAlertOperations:
    @pytest.mark.asyncio
    async def test_async_insert_alert(self) -> None:
        cm, session = _make_session_mock()
        with patch.object(db_engine, "AsyncSessionLocal", return_value=cm):
            alert_id = await db_engine.async_insert_alert({"level": "warning", "title": "t"})
        assert alert_id.startswith("alert-")
        assert session.add.called
        assert session.commit.await_count == 1

    @pytest.mark.asyncio
    async def test_async_query_alerts(self) -> None:
        from core.models import Alert

        alert = Alert(
            id="a1",
            level="warning",
            title="t",
            description="d",
            status="pending",
            platform="windows",
        )
        cm, _ = _make_session_mock(scalars_all=[alert])
        with patch.object(db_engine, "AsyncSessionLocal", return_value=cm):
            rows = await db_engine.async_query_alerts(
                limit=5, level="warning", status="pending", host="h1", category="c1"
            )
        assert len(rows) == 1
        assert rows[0]["id"] == "a1"

    @pytest.mark.asyncio
    async def test_async_count_alerts(self) -> None:
        cm, _ = _make_session_mock(scalar=42)
        with patch.object(db_engine, "AsyncSessionLocal", return_value=cm):
            count = await db_engine.async_count_alerts(level="warning", status="pending", host="h1")
        assert count == 42

    @pytest.mark.asyncio
    async def test_async_clear_alerts(self) -> None:
        cm, _ = _make_session_mock(rowcount=3)
        with patch.object(db_engine, "AsyncSessionLocal", return_value=cm):
            count = await db_engine.async_clear_alerts()
        assert count == 3


class TestAsyncRepairOperations:
    @pytest.mark.asyncio
    async def test_async_insert_repair_record(self) -> None:
        cm, session = _make_session_mock()
        with patch.object(db_engine, "AsyncSessionLocal", return_value=cm):
            repair_id = await db_engine.async_insert_repair_record(
                success=True,
                alert_time=datetime.now(timezone.utc).isoformat(),
                repair_time=datetime.now(timezone.utc).isoformat(),
                repair_duration_sec=1.0,
                rule_name="rule",
                script_key="script",
                platform="windows",
                output="ok",
            )
        assert repair_id.startswith("repair-")
        assert session.add.called

    @pytest.mark.asyncio
    async def test_async_query_repairs(self) -> None:
        from core.models import RepairRecord

        repair = RepairRecord(
            id="r1",
            script_key="s",
            script_name="n",
            success=True,
            status="success",
            platform="windows",
            repair_duration_sec=1.0,
        )
        cm, _ = _make_session_mock(scalars_all=[repair])
        with patch.object(db_engine, "AsyncSessionLocal", return_value=cm):
            rows = await db_engine.async_query_repairs(today_only=True, limit=5)
        assert len(rows) == 1
        assert rows[0]["id"] == "r1"


class TestAsyncApprovalOperations:
    @pytest.mark.asyncio
    async def test_async_upsert_pending_approval_create(self) -> None:
        cm, session = _make_session_mock(scalar_one_or_none=None)
        with patch.object(db_engine, "AsyncSessionLocal", return_value=cm):
            approval_id = await db_engine.async_upsert_pending_approval(
                alert_id="a1",
                rule_name="rule",
                script_key="script",
                proposal="p",
                alert_json="{}",
            )
        assert approval_id.startswith("approval-")
        assert session.add.called

    @pytest.mark.asyncio
    async def test_async_upsert_pending_approval_update(self) -> None:
        existing = MagicMock()
        existing.id = "approval-old"
        cm, _ = _make_session_mock(scalar_one_or_none=existing)
        with patch.object(db_engine, "AsyncSessionLocal", return_value=cm):
            approval_id = await db_engine.async_upsert_pending_approval(
                alert_id="a1",
                rule_name="rule",
                script_key="script",
                proposal="p",
                alert_json="{}",
            )
        assert approval_id == "approval-old"

    @pytest.mark.asyncio
    async def test_async_get_pending_approval(self) -> None:
        from core.models import PendingApproval

        approval = PendingApproval(
            id="ap1",
            alert_id="a1",
            alert_json="{}",
            rule_name="r",
            script_key="s",
            proposal="p",
            risk_level="medium",
        )
        cm, _ = _make_session_mock(scalar_one_or_none=approval)
        with patch.object(db_engine, "AsyncSessionLocal", return_value=cm):
            result = await db_engine.async_get_pending_approval("a1")
        assert result is not None
        assert result["alert_id"] == "a1"

    @pytest.mark.asyncio
    async def test_async_get_all_pending_approvals(self) -> None:
        cm, _ = _make_session_mock(scalars_all=[])
        with patch.object(db_engine, "AsyncSessionLocal", return_value=cm):
            result = await db_engine.async_get_all_pending_approvals()
        assert result == []

    @pytest.mark.asyncio
    async def test_async_update_approval_status(self) -> None:
        from core.models import PendingApproval

        approval = PendingApproval(
            id="ap1",
            alert_id="a1",
            alert_json="{}",
            rule_name="r",
            script_key="s",
            proposal="p",
            risk_level="medium",
        )
        cm, _ = _make_session_mock(scalar_one_or_none=approval)
        with patch.object(db_engine, "AsyncSessionLocal", return_value=cm):
            assert await db_engine.async_update_approval_status("ap1", "approved", "admin")


class TestSyncWrappers:
    def test_insert_alert(self) -> None:
        with patch.object(db_engine, "AsyncSessionLocal", return_value=_make_session_mock()[0]):
            db_engine.insert_alert({"level": "warning"})

    def test_query_alerts(self) -> None:
        cm, _ = _make_session_mock(scalars_all=[])
        with patch.object(db_engine, "AsyncSessionLocal", return_value=cm):
            rows = db_engine.query_alerts(limit=5)
        assert rows == []

    def test_count_alerts(self) -> None:
        cm, _ = _make_session_mock(scalar=7)
        with patch.object(db_engine, "AsyncSessionLocal", return_value=cm):
            assert db_engine.count_alerts(level="warning") == 7

    def test_clear_alerts(self) -> None:
        cm, _ = _make_session_mock(rowcount=0)
        with patch.object(db_engine, "AsyncSessionLocal", return_value=cm):
            assert db_engine.clear_alerts() == 0

    def test_insert_repair_record(self) -> None:
        cm, _ = _make_session_mock()
        with patch.object(db_engine, "AsyncSessionLocal", return_value=cm):
            result = db_engine.insert_repair_record(
                success=True,
                alert_time=datetime.now(timezone.utc).isoformat(),
                repair_time=datetime.now(timezone.utc).isoformat(),
                repair_duration_sec=1.0,
                rule_name="r",
                script_key="s",
                platform="windows",
                output="ok",
            )
        assert result == 0

    def test_query_repairs(self) -> None:
        cm, _ = _make_session_mock(scalars_all=[])
        with patch.object(db_engine, "AsyncSessionLocal", return_value=cm):
            assert db_engine.query_repairs(today_only=True) == []

    def test_upsert_pending_approval(self) -> None:
        cm, _ = _make_session_mock()
        with patch.object(db_engine, "AsyncSessionLocal", return_value=cm):
            assert db_engine.upsert_pending_approval("a1", "r", "s", "p", "{}") == 0

    def test_get_pending_approval(self) -> None:
        cm, _ = _make_session_mock(scalar_one_or_none=None)
        with patch.object(db_engine, "AsyncSessionLocal", return_value=cm):
            assert db_engine.get_pending_approval("a1") is None

    def test_get_all_pending_approvals(self) -> None:
        cm, _ = _make_session_mock(scalars_all=[])
        with patch.object(db_engine, "AsyncSessionLocal", return_value=cm):
            assert db_engine.get_all_pending_approvals() == []

    def test_update_approval_status(self) -> None:
        cm, _ = _make_session_mock()
        with patch.object(db_engine, "AsyncSessionLocal", return_value=cm):
            assert db_engine.update_approval_status("a1", "approved") is None

    def test_db_clear_alerts(self) -> None:
        cm, _ = _make_session_mock(rowcount=2)
        with patch.object(db_engine, "AsyncSessionLocal", return_value=cm):
            assert db_engine.db_clear_alerts() == 2

    def test_insert_verify_record(self) -> None:
        assert db_engine.insert_verify_record(a=1, b=2) == 0


class TestPostgreSQLAlertRepository:
    @pytest.mark.asyncio
    async def test_save(self) -> None:
        cm, _ = _make_session_mock()
        with patch.object(db_engine, "AsyncSessionLocal", return_value=cm):
            alert_id = await db_engine.alert_repository.save({"level": "warning"})
        assert alert_id.startswith("alert-")

    @pytest.mark.asyncio
    async def test_query(self) -> None:
        cm, _ = _make_session_mock(scalars_all=[])
        with patch.object(db_engine, "AsyncSessionLocal", return_value=cm):
            rows = await db_engine.alert_repository.query(filters={"level": "warning"}, limit=5)
        assert rows == []

    @pytest.mark.asyncio
    async def test_get_by_id(self) -> None:
        from core.models import Alert

        alert = Alert(id="a1", level="warning", title="t", description="d", status="pending")
        cm, _ = _make_session_mock(scalar_one_or_none=alert)
        with patch.object(db_engine, "AsyncSessionLocal", return_value=cm):
            result = await db_engine.alert_repository.get_by_id("a1")
        assert result["id"] == "a1"

    @pytest.mark.asyncio
    async def test_update_status(self) -> None:
        from core.models import Alert

        alert = Alert(id="a1", level="warning", title="t", description="d", status="pending")
        cm, _ = _make_session_mock(scalar_one_or_none=alert)
        with patch.object(db_engine, "AsyncSessionLocal", return_value=cm):
            assert await db_engine.alert_repository.update_status("a1", "resolved") is True

    @pytest.mark.asyncio
    async def test_delete(self) -> None:
        cm, _ = _make_session_mock(rowcount=1)
        with patch.object(db_engine, "AsyncSessionLocal", return_value=cm):
            assert await db_engine.alert_repository.delete("a1") is True

    @pytest.mark.asyncio
    async def test_count_and_get_recent(self) -> None:
        cm, _ = _make_session_mock(scalar=5, scalars_all=[])
        with patch.object(db_engine, "AsyncSessionLocal", return_value=cm):
            assert await db_engine.alert_repository.count() == 5
            assert await db_engine.alert_repository.get_recent(10) == []

    @pytest.mark.asyncio
    async def test_clear_all(self) -> None:
        cm, _ = _make_session_mock(rowcount=3)
        with patch.object(db_engine, "AsyncSessionLocal", return_value=cm):
            assert await db_engine.alert_repository.clear_all() is True


class TestDatabaseEngine:
    @pytest.mark.asyncio
    async def test_connect_disconnect(self) -> None:
        engine = db_engine.DatabaseEngine(connection_string="test")
        await engine.connect()
        assert engine.connected is True
        await engine.disconnect()
        assert engine.connected is False

    @pytest.mark.asyncio
    async def test_execute_and_fetchall(self) -> None:
        engine = db_engine.DatabaseEngine()
        assert await engine.execute("SELECT 1") == []
        assert await engine.fetchall("SELECT 1") == []


class TestSimpleRepairDB:
    def test_get_and_update(self) -> None:
        db = db_engine._SimpleRepairDB()
        assert db.get_repair_record("r1") is None
        db.update_repair_status("r1", "completed", "done")
        record = db.get_repair_record("r1")
        assert record["status"] == "completed"
        assert record["comment"] == "done"
