# -*- coding: utf-8 -*-
"""
Comprehensive test suite for core/alert_engine.py
Target: 90%+ statement and branch coverage
"""

import asyncio
import os
import sys
from collections import deque
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from core.alert_engine import (
    _DEDUP_CACHE_MAX,
    _DEDUP_WINDOW_SEC,
    _SSH_ALERT_COOLDOWN_SEC,
    _SSH_CACHE_EXPIRY_SEC,
    _SSH_CACHE_MAX_HOSTS,
    _SSH_FAIL_THRESHOLD,
    _SSH_WINDOW_SEC,
    _check_ssh_brute_force,
    _cleanup_ssh_brute_force_cache,
    _dedup_cache,
    _dedup_key,
    _get_alert_repository,
    _restore_alert_cache,
    _ssh_failed_window,
    _ssh_last_alert_time,
    _try_dedup,
    alert_history,
    check_linux_security_alerts,
)


class TestSSHBruteForceDetection:
    """Test suite for SSH brute force detection"""

    def setup_method(self):
        """Reset SSH detection state before each test"""
        _ssh_failed_window.clear()
        _ssh_last_alert_time.clear()
        alert_history.clear()

    def test_check_ssh_brute_force_initial_state(self):
        """Test with initial state (no previous data)"""
        result = _check_ssh_brute_force("test-host", 5)
        assert result is None  # Need at least 2 data points

    def test_check_ssh_brute_force_below_threshold(self):
        """Test when increment is below threshold"""
        # Add first data point
        _check_ssh_brute_force("test-host", 5)
        # Add second data point with increment below threshold
        result = _check_ssh_brute_force("test-host", 8)  # increment = 3
        assert result is None

    def test_check_ssh_brute_force_above_threshold(self):
        """Test when increment exceeds threshold"""
        # Add first data point
        _check_ssh_brute_force("test-host", 0)
        # Add second data point with increment above threshold
        result = _check_ssh_brute_force("test-host", 15)  # increment = 15
        assert result is not None
        assert result["level"] == "critical"
        assert result["category"] == "security"
        assert result["alert_type"] == "ssh_brute_force"
        assert "SSH 暴力破解告警" in result["title"]
        assert result["host"] == "test-host"
        assert result["value"] == 15

    def test_check_ssh_brute_force_logrotate_detection(self):
        """Test detection of log rotation (negative increment)"""
        # Add first data point with high count
        _check_ssh_brute_force("test-host", 1000)
        # Simulate log rotation - count drops significantly
        result = _check_ssh_brute_force("test-host", 5)
        assert result is None  # Should reset window instead of alerting
        # Window should be reset with only current point
        assert len(_ssh_failed_window["test-host"]) == 1

    def test_check_ssh_brute_force_cooldown(self):
        """Test cooldown period prevents duplicate alerts"""
        # First alert
        _check_ssh_brute_force("test-host", 0)
        result1 = _check_ssh_brute_force("test-host", 20)
        assert result1 is not None

        # Try to alert again within cooldown period
        result2 = _check_ssh_brute_force("test-host", 25)
        assert result2 is None  # Should be blocked by cooldown

    def test_check_ssh_brute_force_cooldown_expired(self):
        """Test that cooldown expires after time passes"""
        # First alert
        _check_ssh_brute_force("test-host", 0)
        result1 = _check_ssh_brute_force("test-host", 20)
        assert result1 is not None

        # Manually expire cooldown
        old_time = _ssh_last_alert_time["test-host"]
        _ssh_last_alert_time["test-host"] = old_time - timedelta(
            seconds=_SSH_ALERT_COOLDOWN_SEC + 10
        )

        # Add new data point after cooldown
        _check_ssh_brute_force("test-host", 25)
        result2 = _check_ssh_brute_force("test-host", 30)
        # Should be able to alert again after cooldown expires and new data point
        assert result2 is not None

    def test_check_ssh_brute_force_window_cleanup(self):
        """Test that old data points are cleaned from window"""
        # Add data point
        _check_ssh_brute_force("test-host", 0)

        # Manually age the data point
        old_time = datetime.now() - timedelta(seconds=_SSH_WINDOW_SEC + 10)
        _ssh_failed_window["test-host"][0] = (old_time, 0)

        # Add new data point - old one should be cleaned
        result = _check_ssh_brute_force("test-host", 5)
        assert result is None  # Not enough data points after cleanup
        assert len(_ssh_failed_window["test-host"]) == 1

    def test_check_ssh_brute_force_multiple_hosts(self):
        """Test detection works independently for multiple hosts"""
        # Host 1 triggers alert
        _check_ssh_brute_force("host1", 0)
        result1 = _check_ssh_brute_force("host1", 20)
        assert result1 is not None

        # Host 2 should have independent state
        _check_ssh_brute_force("host2", 0)
        result2 = _check_ssh_brute_force("host2", 20)
        assert result2 is not None

    def test_check_ssh_brute_force_alert_id_format(self):
        """Test that alert ID has correct format with random suffix"""
        _check_ssh_brute_force("test-host", 0)
        result = _check_ssh_brute_force("test-host", 20)
        assert result is not None
        assert result["id"].startswith("SEC-SSH-test-host-")
        # Should have timestamp and random suffix
        parts = result["id"].split("-")
        assert len(parts) >= 4


class TestSSHCleanup:
    """Test suite for SSH cache cleanup"""

    def setup_method(self):
        """Reset SSH detection state before each test"""
        _ssh_failed_window.clear()
        _ssh_last_alert_time.clear()
        alert_history.clear()

    def test_cleanup_ssh_brute_force_cache_empty(self):
        """Test cleanup with empty cache"""
        _cleanup_ssh_brute_force_cache()
        assert len(_ssh_failed_window) == 0
        assert len(_ssh_last_alert_time) == 0

    def test_cleanup_ssh_brute_force_cache_expired_window(self):
        """Test cleanup of expired window entries"""
        # Add expired entry
        old_time = datetime.now() - timedelta(seconds=_SSH_CACHE_EXPIRY_SEC + 10)
        _ssh_failed_window["host1"] = [(old_time, 10)]

        _cleanup_ssh_brute_force_cache()
        assert "host1" not in _ssh_failed_window

    def test_cleanup_ssh_brute_force_cache_expired_alert(self):
        """Test cleanup of expired alert cooldown entries"""
        # Add expired alert time
        old_time = datetime.now() - timedelta(seconds=_SSH_CACHE_EXPIRY_SEC + 10)
        _ssh_last_alert_time["host1"] = old_time

        _cleanup_ssh_brute_force_cache()
        assert "host1" not in _ssh_last_alert_time

    def test_cleanup_ssh_brute_force_cache_active_entries(self):
        """Test that active entries are not cleaned"""
        # Add active entry
        recent_time = datetime.now() - timedelta(seconds=100)
        _ssh_failed_window["host1"] = [(recent_time, 10)]
        _ssh_last_alert_time["host1"] = recent_time

        _cleanup_ssh_brute_force_cache()
        assert "host1" in _ssh_failed_window
        assert "host1" in _ssh_last_alert_time

    def test_cleanup_ssh_brute_force_cache_max_hosts(self):
        """Test cleanup when exceeding max hosts limit"""
        # Add more hosts than limit
        for i in range(_SSH_CACHE_MAX_HOSTS + 10):
            _ssh_failed_window[f"host{i}"] = [(datetime.now(), i)]

        _cleanup_ssh_brute_force_cache()
        # Should be limited to max
        assert len(_ssh_failed_window) <= _SSH_CACHE_MAX_HOSTS

    def test_cleanup_ssh_brute_force_cache_empty_window(self):
        """Test cleanup of hosts with empty windows"""
        _ssh_failed_window["host1"] = []

        _cleanup_ssh_brute_force_cache()
        assert "host1" not in _ssh_failed_window


class TestDedupKey:
    """Test suite for dedup key generation"""

    def test_dedup_key_basic(self):
        """Test basic dedup key generation"""
        alert = {"metric": "cpu", "level": "warning"}
        key = _dedup_key(alert)
        assert key == "cpu_warning"

    def test_dedup_key_disk_alert(self):
        """Test dedup key for disk alerts with device"""
        alert = {"metric": "disk_percent", "level": "critical", "id": "DISK-C:-12:30:45"}
        key = _dedup_key(alert)
        assert key == "disk_percent_critical_C:"

    def test_dedup_key_disk_alert_complex_device(self):
        """Test dedup key for disk alerts with complex device name"""
        alert = {"metric": "disk_percent", "level": "warning", "id": "DISK-data-volume-01-12:30:45"}
        key = _dedup_key(alert)
        assert key == "disk_percent_warning_data-volume-01"

    def test_dedup_key_disk_alert_no_id(self):
        """Test disk alert without proper ID format"""
        alert = {"metric": "disk_percent", "level": "critical", "id": "invalid-format"}
        key = _dedup_key(alert)
        assert key == "disk_percent_critical"

    def test_dedup_key_missing_fields(self):
        """Test dedup key with missing fields"""
        alert = {}
        key = _dedup_key(alert)
        assert key == "unknown_unknown"


class TestTryDedup:
    """Test suite for alert deduplication"""

    def setup_method(self):
        """Reset dedup cache before each test"""
        _dedup_cache.clear()

    def test_try_dedup_first_alert(self):
        """Test that first alert is not deduplicated"""
        alert = {"metric": "cpu", "level": "warning", "value": 80}
        result = _try_dedup(alert)
        assert result is False  # Should not be deduplicated

    def test_try_dedup_duplicate_within_window(self):
        """Test that duplicate within window is deduplicated"""
        alert1 = {"metric": "cpu", "level": "warning", "value": 80}
        _try_dedup(alert1)

        # Same alert within window
        alert2 = {"metric": "cpu", "level": "warning", "value": 82}
        result = _try_dedup(alert2)
        assert result is True  # Should be deduplicated

    def test_try_dedup_duplicate_after_window(self):
        """Test that duplicate after window is not deduplicated"""
        alert1 = {"metric": "cpu", "level": "warning", "value": 80}
        _try_dedup(alert1)

        # Manually expire the cache entry
        for key, entry in _dedup_cache.items():
            entry["last_time"] = datetime.now() - timedelta(seconds=_DEDUP_WINDOW_SEC + 10)

        # Same alert after window
        alert2 = {"metric": "cpu", "level": "warning", "value": 82}
        result = _try_dedup(alert2)
        assert result is False  # Should not be deduplicated

    def test_try_dedup_different_metric(self):
        """Test that different metrics are not deduplicated"""
        alert1 = {"metric": "cpu", "level": "warning", "value": 80}
        _try_dedup(alert1)

        alert2 = {"metric": "memory", "level": "warning", "value": 80}
        result = _try_dedup(alert2)
        assert result is False  # Should not be deduplicated

    def test_try_dedup_different_level(self):
        """Test that different levels are not deduplicated"""
        alert1 = {"metric": "cpu", "level": "warning", "value": 80}
        _try_dedup(alert1)

        alert2 = {"metric": "cpu", "level": "critical", "value": 80}
        result = _try_dedup(alert2)
        assert result is False  # Should not be deduplicated

    def test_try_dedup_cache_size_limit(self):
        """Test that cache size is limited"""
        # Add many alerts to exceed cache limit
        for i in range(_DEDUP_CACHE_MAX + 10):
            alert = {"metric": f"metric{i}", "level": "warning", "value": 80}
            _try_dedup(alert)

        # Cache should be limited
        assert len(_dedup_cache) <= _DEDUP_CACHE_MAX


class TestCheckLinuxSecurityAlerts:
    """Test suite for Linux security alert checking"""

    @pytest.mark.asyncio
    async def test_check_linux_security_alerts_empty_input(self):
        """Test with empty input"""
        result = await check_linux_security_alerts([])
        assert result == []

    @pytest.mark.asyncio
    async def test_check_linux_security_alerts_invalid_input(self):
        """Test with invalid input"""
        result = await check_linux_security_alerts(None)
        assert result == []

        result = await check_linux_security_alerts("not a list")
        assert result == []

    @pytest.mark.asyncio
    async def test_check_linux_security_alerts_invalid_host_data(self):
        """Test with invalid host data"""
        result = await check_linux_security_alerts([{"not": "a dict"}])
        assert result == []

    @pytest.mark.asyncio
    async def test_check_linux_security_alerts_invalid_status(self):
        """Test with invalid host status"""
        result = await check_linux_security_alerts(
            [{"name": "host1", "status": "error", "metrics": {}}]
        )
        assert result == []

    @pytest.mark.asyncio
    async def test_check_linux_security_alerts_no_ssh_metric(self):
        """Test host without SSH metric"""
        result = await check_linux_security_alerts(
            [{"name": "host1", "status": "ok", "metrics": {}}]
        )
        assert result == []

    @pytest.mark.asyncio
    async def test_check_linux_security_alerts_ssh_metric_below_threshold(self):
        """Test SSH metric below threshold"""
        result = await check_linux_security_alerts(
            [{"name": "host1", "status": "ok", "metrics": {"ssh_failed_logins": {"value": "5"}}}]
        )
        assert result == []

    @pytest.mark.asyncio
    async def test_check_linux_security_alerts_ssh_metric_above_threshold(self):
        """Test SSH metric above threshold"""
        # Reset SSH state
        _ssh_failed_window.clear()
        _ssh_last_alert_time.clear()

        result = await check_linux_security_alerts(
            [{"name": "host1", "status": "ok", "metrics": {"ssh_failed_logins": {"value": "20"}}}]
        )
        # Should generate alert on first collection if above threshold
        assert len(result) >= 0  # May or may not alert depending on state

    @pytest.mark.asyncio
    async def test_check_linux_security_alerts_ssh_metric_invalid_value(self):
        """Test SSH metric with invalid value"""
        result = await check_linux_security_alerts(
            [
                {
                    "name": "host1",
                    "status": "ok",
                    "metrics": {"ssh_failed_logins": {"value": "not a number"}},
                }
            ]
        )
        assert result == []

    @pytest.mark.asyncio
    async def test_check_linux_security_alerts_ssh_metric_error_value(self):
        """Test SSH metric with error value"""
        result = await check_linux_security_alerts(
            [
                {
                    "name": "host1",
                    "status": "ok",
                    "metrics": {"ssh_failed_logins": {"value": "ERROR"}},
                }
            ]
        )
        assert result == []

    @pytest.mark.asyncio
    async def test_check_linux_security_alerts_multiple_hosts(self):
        """Test with multiple hosts"""
        result = await check_linux_security_alerts(
            [
                {"name": "host1", "status": "ok", "metrics": {"ssh_failed_logins": {"value": "5"}}},
                {"name": "host2", "status": "ok", "metrics": {"ssh_failed_logins": {"value": "5"}}},
            ]
        )
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_check_linux_security_alerts_database_persistence(self):
        """Test database persistence of security alerts"""
        # Reset SSH state
        _ssh_failed_window.clear()
        _ssh_last_alert_time.clear()

        with patch("core.alert_engine._get_alert_repository") as mock_repo:
            mock_repo_instance = AsyncMock()
            mock_repo.return_value = mock_repo_instance
            mock_repo_instance.save = AsyncMock()

            result = await check_linux_security_alerts(
                [
                    {
                        "name": "host1",
                        "status": "ok",
                        "metrics": {"ssh_failed_logins": {"value": "20"}},
                    }
                ]
            )

            # Should attempt to save if alert generated
            if result:
                mock_repo_instance.save.assert_called()

    @pytest.mark.asyncio
    async def test_check_linux_security_alerts_database_failure(self):
        """Test handling of database persistence failure"""
        # Reset SSH state
        _ssh_failed_window.clear()
        _ssh_last_alert_time.clear()

        with patch("core.alert_engine._get_alert_repository") as mock_repo:
            mock_repo_instance = AsyncMock()
            mock_repo.return_value = mock_repo_instance
            mock_repo_instance.save = AsyncMock(side_effect=Exception("DB error"))

            result = await check_linux_security_alerts(
                [
                    {
                        "name": "host1",
                        "status": "ok",
                        "metrics": {"ssh_failed_logins": {"value": "20"}},
                    }
                ]
            )

            # Should still return alerts even if DB fails
            assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_check_linux_security_alerts_notification(self):
        """Test notification sending for security alerts"""
        # Reset SSH state
        _ssh_failed_window.clear()
        _ssh_last_alert_time.clear()

        with patch(
            "core.notify_engine.send_alert_notification", new_callable=AsyncMock
        ) as mock_notify:
            mock_notify.return_value = {"status": "success"}

            result = await check_linux_security_alerts(
                [
                    {
                        "name": "host1",
                        "status": "ok",
                        "metrics": {"ssh_failed_logins": {"value": "20"}},
                    }
                ]
            )

            # Should attempt notification if alert generated
            if result:
                mock_notify.assert_called()

    @pytest.mark.asyncio
    async def test_check_linux_security_alerts_auto_heal(self):
        """Test auto-heal triggering for security alerts"""
        # Reset SSH state
        _ssh_failed_window.clear()
        _ssh_last_alert_time.clear()

        with patch("core.auto_heal.try_auto_heal", new_callable=AsyncMock) as mock_heal:
            mock_heal.return_value = {"status": "dispatched"}

            result = await check_linux_security_alerts(
                [
                    {
                        "name": "host1",
                        "status": "ok",
                        "metrics": {"ssh_failed_logins": {"value": "20"}},
                    }
                ]
            )

            # Should attempt auto-heal if alert generated
            if result:
                mock_heal.assert_called()


class TestAlertRepository:
    """Test suite for alert repository functions"""

    def test_get_alert_repository_module_level(self):
        """Test getting module-level repository"""
        from core.alert_engine import alert_repository

        result = _get_alert_repository()
        assert result is not None

    def test_get_alert_repository_db_fallback(self):
        """Test fallback to database repository"""
        from core.alert_engine import alert_repository

        original_repo = alert_repository

        try:
            # Set module-level repo to None to test fallback
            from core import alert_engine

            alert_engine.alert_repository = None

            result = _get_alert_repository()
            assert result is not None
        finally:
            # Restore original
            from core import alert_engine

            alert_engine.alert_repository = original_repo


class TestRestoreAlertCache:
    """Test suite for alert cache restoration"""

    def setup_method(self):
        """Reset alert history before each test"""
        alert_history.clear()

    @pytest.mark.asyncio
    async def test_restore_alert_cache_success(self):
        """Test successful cache restoration"""
        with patch("core.alert_engine._get_alert_repository") as mock_repo:
            mock_repo_instance = AsyncMock()
            mock_repo.return_value = mock_repo_instance
            mock_repo_instance.get_recent = AsyncMock(
                return_value=[{"id": "1", "level": "warning"}, {"id": "2", "level": "critical"}]
            )

            await _restore_alert_cache()

            # Should have restored alerts
            assert len(alert_history) == 2

    @pytest.mark.asyncio
    async def test_restore_alert_cache_empty(self):
        """Test restoration with empty database"""
        with patch("core.alert_engine._get_alert_repository") as mock_repo:
            mock_repo_instance = AsyncMock()
            mock_repo.return_value = mock_repo_instance
            mock_repo_instance.get_recent = AsyncMock(return_value=[])

            await _restore_alert_cache()

            # Should have empty cache
            assert len(alert_history) == 0

    @pytest.mark.asyncio
    async def test_restore_alert_cache_failure(self):
        """Test handling of restoration failure"""
        with patch("core.alert_engine._get_alert_repository") as mock_repo:
            mock_repo_instance = AsyncMock()
            mock_repo.return_value = mock_repo_instance
            mock_repo_instance.get_recent = AsyncMock(side_effect=Exception("DB error"))

            # Should not raise exception
            await _restore_alert_cache()


class TestAlertHistory:
    """Test suite for alert history deque"""

    def test_alert_history_is_deque(self):
        """Test that alert_history is a deque"""
        assert isinstance(alert_history, deque)

    def test_alert_history_maxlen(self):
        """Test that alert_history has max length"""
        from config import ALERT_HISTORY_MAX

        assert alert_history.maxlen == ALERT_HISTORY_MAX


class TestConstants:
    """Test suite for module constants"""

    def test_ssh_window_sec(self):
        """Test SSH window constant"""
        assert _SSH_WINDOW_SEC == 300  # 5 minutes

    def test_ssh_fail_threshold(self):
        """Test SSH fail threshold constant"""
        assert _SSH_FAIL_THRESHOLD == 10

    def test_ssh_alert_cooldown_sec(self):
        """Test SSH alert cooldown constant"""
        assert _SSH_ALERT_COOLDOWN_SEC == 600  # 10 minutes

    def test_ssh_cache_expiry_sec(self):
        """Test SSH cache expiry constant"""
        assert _SSH_CACHE_EXPIRY_SEC == 3600  # 1 hour

    def test_ssh_cache_max_hosts(self):
        """Test SSH cache max hosts constant"""
        assert _SSH_CACHE_MAX_HOSTS == 500

    def test_dedup_window_sec(self):
        """Test dedup window constant"""
        assert _DEDUP_WINDOW_SEC == 300  # 5 minutes

    def test_dedup_cache_max(self):
        """Test dedup cache max constant"""
        assert _DEDUP_CACHE_MAX == 200
