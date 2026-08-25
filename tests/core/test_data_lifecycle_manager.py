# -*- coding: utf-8 -*-
"""Tests for core/data_lifecycle_manager.py."""

import pytest  # noqa: F401  # Imported for test setup

from core.data_lifecycle_manager import (
    DataCategory,
    DataLifecycleManager,
    DataLifecycleRule,
    DataRetentionPolicy,
    setup_data_lifecycle,
)


def test_get_retention_days():
    manager = DataLifecycleManager()
    assert manager.get_retention_days(DataRetentionPolicy.RETAIN_7_DAYS) == 7
    assert manager.get_retention_days(DataRetentionPolicy.RETAIN_PERMANENT) == -1


@pytest.mark.asyncio
async def test_archive_old_data():
    manager = DataLifecycleManager()
    result = await manager.archive_old_data(
        DataCategory.ALERTS
    )  # noqa: F841  # Variable for test verification
    assert result["status"] == "success"
    assert result["category"] == DataCategory.ALERTS.value
    result = await manager.archive_old_data(
        DataCategory.TEMPORARY
    )  # noqa: F841  # Variable for test verification
    assert result["status"] == "skipped"
    result = await manager.archive_old_data(
        "unknown"
    )  # noqa: F841  # Variable for test verification
    assert result["status"] == "error"


@pytest.mark.asyncio
async def test_cleanup_temp_data():
    manager = DataLifecycleManager()
    result = await manager.cleanup_temp_data()  # noqa: F841  # Variable for test verification
    assert result["status"] == "success"
    assert "deleted_count" in result


@pytest.mark.asyncio
async def test_apply_retention_policy():
    manager = DataLifecycleManager()
    result = await manager.apply_retention_policy(
        DataCategory.METRICS
    )  # noqa: F841  # Variable for test verification
    assert result["status"] == "success"
    result = await manager.apply_retention_policy(
        DataCategory.CONFIGURATION
    )  # noqa: F841  # Variable for test verification
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
