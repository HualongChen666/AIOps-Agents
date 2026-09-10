# -*- coding: utf-8 -*-
"""Tests for the database-backed workflow repository version/schedule methods.

Regression guard for the previously no-op'd ("not implemented in DB yet")
``save_version`` / ``list_versions`` / ``save_schedule`` / ``list_schedules``.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from core.models import WorkflowScheduleRecord, WorkflowVersionRecord
from extensions.addons.operations.workflow_service import repository as repo_mod
from extensions.addons.operations.workflow_service.repository import (
    DatabaseWorkflowRepository,
)
from extensions.addons.operations.workflow_service.schemas import (
    ScheduledTask,
    WorkflowVersion,
)


@pytest.fixture
def repo(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    WorkflowVersionRecord.__table__.create(bind=engine)
    WorkflowScheduleRecord.__table__.create(bind=engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    monkeypatch.setattr(repo_mod, "SessionLocal", session_factory)
    return DatabaseWorkflowRepository()


async def test_save_and_list_versions_round_trip(repo):
    version = WorkflowVersion(
        version="v1.0.0",
        workflow_id="wf-1",
        commit_hash="deadbeef",
        message="initial",
    )
    assert await repo.save_version("wf-1", version) == "v1.0.0"

    versions = await repo.list_versions("wf-1")
    assert len(versions) == 1
    assert versions[0].version == "v1.0.0"
    assert versions[0].commit_hash == "deadbeef"
    assert versions[0].message == "initial"


async def test_save_version_is_idempotent_and_updates_metadata(repo):
    await repo.save_version(
        "wf-2",
        WorkflowVersion(version="v1.0.0", workflow_id="wf-2", commit_hash="aaa", message="m1"),
    )
    await repo.save_version(
        "wf-2",
        WorkflowVersion(version="v1.0.0", workflow_id="wf-2", commit_hash="bbb", message="m2"),
    )
    versions = await repo.list_versions("wf-2")
    assert len(versions) == 1
    assert versions[0].commit_hash == "bbb"
    assert versions[0].message == "m2"


async def test_list_versions_isolated_per_workflow(repo):
    base = datetime(2026, 1, 1)
    await repo.save_version(
        "wf-a",
        WorkflowVersion(version="v1", workflow_id="wf-a", commit_hash="a", message="", created_at=base),
    )
    await repo.save_version(
        "wf-a",
        WorkflowVersion(
            version="v2", workflow_id="wf-a", commit_hash="b", message="", created_at=base + timedelta(days=1)
        ),
    )
    await repo.save_version(
        "wf-b",
        WorkflowVersion(version="v1", workflow_id="wf-b", commit_hash="c", message=""),
    )

    a_versions = await repo.list_versions("wf-a")
    assert [v.version for v in a_versions] == ["v2", "v1"]  # newest first
    assert len(await repo.list_versions("wf-b")) == 1
    assert await repo.list_versions("missing") == []


async def test_save_and_list_schedules_round_trip(repo):
    schedule = ScheduledTask(
        schedule_id="sched-1",
        workflow_id="wf-1",
        cron="0 * * * *",
        next_run=datetime(2026, 1, 1, 0, 0),
        enabled=True,
        params={"env": "prod"},
    )
    assert await repo.save_schedule(schedule) == "sched-1"

    schedules = await repo.list_schedules()
    assert len(schedules) == 1
    assert schedules[0].schedule_id == "sched-1"
    assert schedules[0].cron == "0 * * * *"
    assert schedules[0].params == {"env": "prod"}


async def test_save_schedule_upserts(repo):
    base = ScheduledTask(schedule_id="s", workflow_id="wf", cron="* * * * *", enabled=True)
    await repo.save_schedule(base)
    base.cron = "*/5 * * * *"
    base.enabled = False
    await repo.save_schedule(base)

    schedules = await repo.list_schedules()
    assert len(schedules) == 1
    assert schedules[0].cron == "*/5 * * * *"
    assert schedules[0].enabled is False


async def test_list_schedules_orders_by_next_run(repo):
    await repo.save_schedule(
        ScheduledTask(schedule_id="late", workflow_id="wf", cron="*", next_run=datetime(2030, 1, 1))
    )
    await repo.save_schedule(
        ScheduledTask(schedule_id="soon", workflow_id="wf", cron="*", next_run=datetime(2026, 1, 1))
    )
    schedules = await repo.list_schedules()
    assert [s.schedule_id for s in schedules] == ["soon", "late"]
