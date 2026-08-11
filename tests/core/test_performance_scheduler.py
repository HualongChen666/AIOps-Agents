# -*- coding: utf-8 -*-
"""Tests for core/performance_scheduler.py."""

import pytest

pytest.importorskip("apscheduler")

from core.performance_scheduler import (  # noqa: E402
    PerformanceTaskScheduler,
    get_task_scheduler,
)


def test_get_task_scheduler():
    sched = get_task_scheduler()
    assert isinstance(sched, PerformanceTaskScheduler)


def test_setup_jobs():
    sched = PerformanceTaskScheduler()
    sched.setup_jobs()
    job_ids = {job.id for job in sched.scheduler.get_jobs()}
    assert "collect_daily_metrics" in job_ids
    assert "detect_daily_regressions" in job_ids
    assert "generate_daily_report" in job_ids
    assert "generate_weekly_report" in job_ids
    assert "generate_monthly_report" in job_ids
    sched.scheduler.shutdown(wait=False)
