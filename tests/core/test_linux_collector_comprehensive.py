# -*- coding: utf-8 -*-
"""
Comprehensive test suite for core/linux_collector.py
Target: 90%+ statement and branch coverage
"""

import pytest
import asyncio
import sys
import os
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime
import time

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from core.linux_collector import (
    _get_host_semaphore,
    get_last_snapshot,
    _is_host_in_cooldown,
    _record_host_failure,
    _record_host_success,
    get_host_cooldown_status,
    _ssh_execute,
    COLLECT_COMMANDS,
    _SSH_CONCURRENCY_PER_HOST,
    _SSH_BATCH_SIZE,
    _HOST_COOLDOWN_SEC,
    _HOST_MAX_FAILURES,
)


class TestGetHostSemaphore:
    """Test suite for _get_host_semaphore function"""

    def test_get_host_semaphore_new_host(self):
        """Test creating semaphore for new host"""
        sem = _get_host_semaphore("new_host")
        assert sem is not None
        assert sem._value == _SSH_CONCURRENCY_PER_HOST

    def test_get_host_semaphore_existing_host(self):
        """Test returning existing semaphore for host"""
        sem1 = _get_host_semaphore("existing_host")
        sem2 = _get_host_semaphore("existing_host")
        assert sem1 is sem2

    def test_get_host_semaphore_thread_safety(self):
        """Test semaphore creation is thread-safe"""
        import threading
        
        results = []
        def create_semaphore():
            sem = _get_host_semaphore("thread_test_host")
            results.append(sem)
        
        threads = [threading.Thread(target=create_semaphore) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # All should return the same semaphore instance
        assert all(sem is results[0] for sem in results)


class TestGetLastSnapshot:
    """Test suite for get_last_snapshot function"""

    def test_get_last_snapshot_empty(self):
        """Test getting snapshot when cache is empty"""
        from core.linux_collector import _last_collect_cache
        _last_collect_cache.clear()
        
        result = get_last_snapshot()
        assert result == {}

    def test_get_last_snapshot_with_data(self):
        """Test getting snapshot with cached data"""
        from core.linux_collector import _last_collect_cache
        _last_collect_cache.clear()
        _last_collect_cache["host1"] = {"cpu": 50}
        _last_collect_cache["host2"] = {"cpu": 60}
        
        result = get_last_snapshot()
        assert result == {"host1": {"cpu": 50}, "host2": {"cpu": 60}}
        # Should return a copy
        assert result is not _last_collect_cache


class TestHostCooldownMechanism:
    """Test suite for host cooldown mechanism functions"""

    def test_is_host_in_cooldown_no_tracker(self):
        """Test cooldown check when host has no tracker"""
        from core.linux_collector import _host_failure_tracker
        _host_failure_tracker.clear()
        
        result = _is_host_in_cooldown("test_host")
        assert result is False

    def test_is_host_in_cooldown_below_threshold(self):
        """Test cooldown check when failure count below threshold"""
        from core.linux_collector import _host_failure_tracker
        _host_failure_tracker.clear()
        _host_failure_tracker["test_host"] = {"count": 1, "last_fail": time.monotonic()}
        
        result = _is_host_in_cooldown("test_host")
        assert result is False

    def test_is_host_in_cooldown_in_cooldown(self):
        """Test cooldown check when host is in cooldown"""
        from core.linux_collector import _host_failure_tracker
        _host_failure_tracker.clear()
        _host_failure_tracker["test_host"] = {
            "count": _HOST_MAX_FAILURES,
            "last_fail": time.monotonic()
        }
        
        result = _is_host_in_cooldown("test_host")
        assert result is True

    def test_is_host_in_cooldown_expired(self):
        """Test cooldown check when cooldown period has expired"""
        from core.linux_collector import _host_failure_tracker
        _host_failure_tracker.clear()
        old_time = time.monotonic() - (_HOST_COOLDOWN_SEC + 100)
        _host_failure_tracker["test_host"] = {
            "count": _HOST_MAX_FAILURES,
            "last_fail": old_time
        }
        
        result = _is_host_in_cooldown("test_host")
        assert result is False
        assert "test_host" not in _host_failure_tracker

    def test_is_host_in_cooldown_time_regression(self):
        """Test cooldown check handles time regression"""
        from core.linux_collector import _host_failure_tracker
        _host_failure_tracker.clear()
        future_time = time.monotonic() + 1000
        _host_failure_tracker["test_host"] = {
            "count": _HOST_MAX_FAILURES,
            "last_fail": future_time
        }
        
        result = _is_host_in_cooldown("test_host")
        assert result is False
        assert "test_host" not in _host_failure_tracker

    def test_record_host_failure_new_host(self):
        """Test recording failure for new host"""
        from core.linux_collector import _host_failure_tracker
        _host_failure_tracker.clear()
        
        _record_host_failure("test_host")
        
        assert "test_host" in _host_failure_tracker
        assert _host_failure_tracker["test_host"]["count"] == 1

    def test_record_host_failure_existing_host(self):
        """Test recording failure for existing host"""
        from core.linux_collector import _host_failure_tracker
        _host_failure_tracker.clear()
        _host_failure_tracker["test_host"] = {"count": 2, "last_fail": time.monotonic()}
        
        _record_host_failure("test_host")
        
        assert _host_failure_tracker["test_host"]["count"] == 3

    def test_record_host_failure_threshold_reached(self):
        """Test recording failure when threshold is reached"""
        from core.linux_collector import _host_failure_tracker
        _host_failure_tracker.clear()
        _host_failure_tracker["test_host"] = {
            "count": _HOST_MAX_FAILURES - 1,
            "last_fail": time.monotonic()
        }
        
        _record_host_failure("test_host")
        
        assert _host_failure_tracker["test_host"]["count"] == _HOST_MAX_FAILURES

    def test_record_host_success(self):
        """Test recording host success"""
        from core.linux_collector import _host_failure_tracker
        _host_failure_tracker.clear()
        _host_failure_tracker["test_host"] = {"count": 5, "last_fail": time.monotonic()}
        
        _record_host_success("test_host")
        
        assert "test_host" not in _host_failure_tracker

    def test_get_host_cooldown_status_empty(self):
        """Test getting cooldown status when no hosts tracked"""
        from core.linux_collector import _host_failure_tracker
        _host_failure_tracker.clear()
        
        result = get_host_cooldown_status()
        assert result["total_tracked"] == 0
        assert result["stale_hosts"] == []

    def test_get_host_cooldown_status_with_stale_hosts(self):
        """Test getting cooldown status with stale hosts"""
        from core.linux_collector import _host_failure_tracker
        _host_failure_tracker.clear()
        _host_failure_tracker["host1"] = {
            "count": _HOST_MAX_FAILURES,
            "last_fail": time.monotonic() - 100
        }
        _host_failure_tracker["host2"] = {
            "count": 1,
            "last_fail": time.monotonic()
        }
        
        result = get_host_cooldown_status()
        
        assert result["total_tracked"] == 2
        assert len(result["stale_hosts"]) == 1
        assert result["stale_hosts"][0]["host"] == "host1"


class TestSshExecute:
    """Test suite for _ssh_execute function"""

    @pytest.mark.asyncio
    async def test_ssh_execute_success(self):
        """Test successful SSH execution"""
        host_config = {
            "host": "testhost",
            "port": 22,
            "username": "testuser",
            "key_file": "/path/to/key"
        }
        
        with patch('asyncio.create_subprocess_exec') as mock_subprocess:
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.communicate = AsyncMock(return_value=(b"output", b""))
            mock_subprocess.return_value = mock_process
            
            result = await _ssh_execute(host_config, "test command")
            
            assert result == "output"

    @pytest.mark.asyncio
    async def test_ssh_execute_invalid_host_config(self):
        """Test SSH execute with invalid host config"""
        result = await _ssh_execute(None, "test command")
        assert result == "ERROR: invalid host_config"

    @pytest.mark.asyncio
    async def test_ssh_execute_empty_command(self):
        """Test SSH execute with empty command"""
        host_config = {"host": "testhost", "username": "testuser"}
        result = await _ssh_execute(host_config, "")
        assert result == ""

    @pytest.mark.asyncio
    async def test_ssh_execute_missing_host(self):
        """Test SSH execute with missing host field"""
        host_config = {"username": "testuser"}
        result = await _ssh_execute(host_config, "test command")
        assert "ERROR: host field missing" in result

    @pytest.mark.asyncio
    async def test_ssh_execute_missing_username(self):
        """Test SSH execute with missing username"""
        host_config = {"host": "testhost"}
        result = await _ssh_execute(host_config, "test command")
        assert "ERROR: username field missing" in result

    @pytest.mark.asyncio
    async def test_ssh_execute_timeout(self):
        """Test SSH execute with timeout"""
        host_config = {
            "host": "testhost",
            "port": 22,
            "username": "testuser",
            "key_file": "/path/to/key"
        }
        
        with patch('asyncio.create_subprocess_exec') as mock_subprocess:
            mock_process = AsyncMock()
            mock_process.communicate = AsyncMock(side_effect=asyncio.TimeoutError)
            mock_subprocess.return_value = mock_process
            
            result = await _ssh_execute(host_config, "test command")
            
            assert result == "TIMEOUT"

    @pytest.mark.asyncio
    async def test_ssh_execute_file_not_found(self):
        """Test SSH execute when SSH command not found"""
        host_config = {
            "host": "testhost",
            "port": 22,
            "username": "testuser",
            "password": "testpass"
        }
        
        with patch('asyncio.create_subprocess_exec') as mock_subprocess:
            mock_subprocess.side_effect = FileNotFoundError()
            
            result = await _ssh_execute(host_config, "test command")
            
            assert "NOT_FOUND" in result

    @pytest.mark.asyncio
    async def test_ssh_execute_with_password(self):
        """Test SSH execute with password authentication"""
        host_config = {
            "host": "testhost",
            "port": 22,
            "username": "testuser",
            "password": "testpass"
        }
        
        with patch('asyncio.create_subprocess_exec') as mock_subprocess:
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.communicate = AsyncMock(return_value=(b"output", b""))
            mock_subprocess.return_value = mock_process
            
            result = await _ssh_execute(host_config, "test command")
            
            assert result == "output"

    @pytest.mark.asyncio
    async def test_ssh_execute_non_zero_returncode(self):
        """Test SSH execute with non-zero return code"""
        host_config = {
            "host": "testhost",
            "port": 22,
            "username": "testuser",
            "key_file": "/path/to/key"
        }
        
        with patch('asyncio.create_subprocess_exec') as mock_subprocess:
            mock_process = AsyncMock()
            mock_process.returncode = 1
            mock_process.communicate = AsyncMock(return_value=(b"", b"error message"))
            mock_subprocess.return_value = mock_process
            
            result = await _ssh_execute(host_config, "test command")
            
            assert result == ""


class TestCollectCommands:
    """Test suite for COLLECT_COMMANDS constant"""

    def test_collect_commands_structure(self):
        """Test that COLLECT_COMMANDS has expected structure"""
        assert isinstance(COLLECT_COMMANDS, dict)
        assert len(COLLECT_COMMANDS) > 0
        
        for key, value in COLLECT_COMMANDS.items():
            assert isinstance(key, str)
            assert isinstance(value, dict)
            assert "cmd" in value
            assert "desc" in value

    def test_collect_commands_cpu_commands(self):
        """Test CPU-related commands exist"""
        assert "cpu_usage" in COLLECT_COMMANDS
        assert "load_avg" in COLLECT_COMMANDS
        assert "cpu_cores" in COLLECT_COMMANDS

    def test_collect_commands_memory_commands(self):
        """Test memory-related commands exist"""
        assert "memory" in COLLECT_COMMANDS
        assert "swap" in COLLECT_COMMANDS
        assert "oom_count" in COLLECT_COMMANDS

    def test_collect_commands_disk_commands(self):
        """Test disk-related commands exist"""
        assert "disk_usage" in COLLECT_COMMANDS
        assert "inode_usage" in COLLECT_COMMANDS
        assert "disk_readonly" in COLLECT_COMMANDS

    def test_collect_commands_network_commands(self):
        """Test network-related commands exist"""
        assert "network_errors" in COLLECT_COMMANDS
        assert "tcp_connections" in COLLECT_COMMANDS
        assert "listening_ports" in COLLECT_COMMANDS

    def test_collect_commands_process_commands(self):
        """Test process-related commands exist"""
        assert "process_count" in COLLECT_COMMANDS
        assert "zombie_count" in COLLECT_COMMANDS
        assert "file_descriptors" in COLLECT_COMMANDS


class TestConstants:
    """Test suite for module constants"""

    def test_ssh_concurrency_per_host(self):
        """Test SSH concurrency constant"""
        assert isinstance(_SSH_CONCURRENCY_PER_HOST, int)
        assert _SSH_CONCURRENCY_PER_HOST > 0

    def test_ssh_batch_size(self):
        """Test SSH batch size constant"""
        assert isinstance(_SSH_BATCH_SIZE, int)
        assert 5 <= _SSH_BATCH_SIZE <= 50

    def test_host_cooldown_sec(self):
        """Test host cooldown seconds constant"""
        assert isinstance(_HOST_COOLDOWN_SEC, int)
        assert 30 <= _HOST_COOLDOWN_SEC <= 3600

    def test_host_max_failures(self):
        """Test host max failures constant"""
        assert isinstance(_HOST_MAX_FAILURES, int)
        assert 1 <= _HOST_MAX_FAILURES <= 20


class TestEdgeCases:
    """Test suite for edge cases and error handling"""

    @pytest.mark.asyncio
    async def test_ssh_execute_unicode_command(self):
        """Test SSH execute with unicode characters in command"""
        host_config = {
            "host": "testhost",
            "port": 22,
            "username": "testuser",
            "key_file": "/path/to/key"
        }
        
        with patch('asyncio.create_subprocess_exec') as mock_subprocess:
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.communicate = AsyncMock(return_value=(b"output", b""))
            mock_subprocess.return_value = mock_process
            
            result = await _ssh_execute(host_config, "test 命令")
            
            assert result == "output"

    @pytest.mark.asyncio
    async def test_ssh_execute_unicode_output(self):
        """Test SSH execute with unicode output"""
        host_config = {
            "host": "testhost",
            "port": 22,
            "username": "testuser",
            "key_file": "/path/to/key"
        }
        
        with patch('asyncio.create_subprocess_exec') as mock_subprocess:
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.communicate = AsyncMock(return_value=(b"output \xe4\xb8\xad\xe6\x96\x87", b""))
            mock_subprocess.return_value = mock_process
            
            result = await _ssh_execute(host_config, "test command")
            
            assert isinstance(result, str)

    def test_host_cooldown_concurrent_access(self):
        """Test cooldown mechanism with concurrent access"""
        import threading
        
        from core.linux_collector import _host_failure_tracker
        _host_failure_tracker.clear()
        
        def record_failures():
            for _ in range(10):
                _record_host_failure("concurrent_host")
        
        threads = [threading.Thread(target=record_failures) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # Should have recorded all failures
        assert _host_failure_tracker["concurrent_host"]["count"] == 50
