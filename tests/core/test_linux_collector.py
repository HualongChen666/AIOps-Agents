# -*- coding: utf-8 -*-
"""
Comprehensive test suite for core/linux_collector.py
Target: 90%+ statement and branch coverage
"""

import pytest
import sys
import os
import asyncio
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, AsyncMock
from threading import Lock

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Disable database fixtures for this test file
pytestmark = [pytest.mark.skip_db, pytest.mark.core]

from core.linux_collector import (
    _host_failure_tracker,
    _host_failure_lock,
    _last_collect_cache,
    _last_collect_cache_lock,
    _is_host_in_cooldown,
    _record_host_failure,
    _record_host_success,
    get_host_cooldown_status,
    _HOST_MAX_FAILURES,
    _HOST_COOLDOWN_SEC,
    _get_host_semaphore,
    get_last_snapshot,
    get_available_metrics,
    get_configured_hosts,
    collect_linux_host,
    collect_all_linux,
    COLLECT_COMMANDS,
)


class TestHostFailureTracking:
    """Test suite for host failure tracking mechanism"""

    def setup_method(self):
        """Reset failure tracking state before each test"""
        _host_failure_tracker.clear()
        _last_collect_cache.clear()

    def test_record_host_failure_first_failure(self):
        """Test recording first host failure"""
        _record_host_failure("test-host")
        assert "test-host" in _host_failure_tracker
        assert _host_failure_tracker["test-host"]["count"] == 1

    def test_record_host_failure_multiple_failures(self):
        """Test recording multiple host failures"""
        for _ in range(3):
            _record_host_failure("test-host")
        assert _host_failure_tracker["test-host"]["count"] == 3

    def test_record_host_failure_enters_cooldown(self):
        """Test that host enters cooldown after max failures"""
        for _ in range(_HOST_MAX_FAILURES + 1):
            _record_host_failure("test-host")

        assert _is_host_in_cooldown("test-host") is True

    def test_record_host_success_resets_counter(self):
        """Test that host success resets failure counter"""
        # Record some failures
        for _ in range(3):
            _record_host_failure("test-host")

        # Record success
        _record_host_success("test-host")

        # Counter should be reset
        assert "test-host" not in _host_failure_tracker

    def test_is_host_in_cooldown_false_initially(self):
        """Test that host is not in cooldown initially"""
        assert _is_host_in_cooldown("test-host") is False

    def test_is_host_in_cooldown_true_after_failures(self):
        """Test that host enters cooldown after failures"""
        for _ in range(_HOST_MAX_FAILURES + 1):
            _record_host_failure("test-host")

        assert _is_host_in_cooldown("test-host") is True

    def test_is_host_in_cooldown_expires(self):
        """Test that cooldown expires after time"""
        import time

        # Record failures to enter cooldown
        for _ in range(_HOST_MAX_FAILURES + 1):
            _record_host_failure("test-host")

        # Manually set last_fail to past (beyond cooldown period)
        _host_failure_tracker["test-host"]["last_fail"] = time.monotonic() - _HOST_COOLDOWN_SEC - 10

        assert _is_host_in_cooldown("test-host") is False

    def test_get_host_cooldown_status_all_hosts(self):
        """Test getting cooldown status for all hosts"""
        _record_host_failure("host1")
        _record_host_failure("host2")

        for _ in range(_HOST_MAX_FAILURES + 1):
            _record_host_failure("host1")

        status = get_host_cooldown_status()
        assert status["total_tracked"] >= 1
        assert len(status["stale_hosts"]) >= 1

    def test_get_host_cooldown_status_empty(self):
        """Test getting cooldown status when no hosts are tracked"""
        _host_failure_tracker.clear()
        status = get_host_cooldown_status()
        assert status["total_tracked"] == 0
        assert len(status["stale_hosts"]) == 0


class TestCollectCache:
    """Test suite for collection cache mechanism"""

    def setup_method(self):
        """Reset cache state before each test"""
        _last_collect_cache.clear()

    def test_cache_write_and_read(self):
        """Test writing to and reading from cache"""
        test_data = {"cpu": 80, "memory": 50}
        _last_collect_cache["test-host"] = test_data

        assert _last_collect_cache["test-host"] == test_data

    def test_cache_lock_protection(self):
        """Test that cache operations are lock-protected"""
        # This is more of a design verification
        assert _last_collect_cache_lock is not None
        assert hasattr(_last_collect_cache_lock, 'acquire')
        assert hasattr(_last_collect_cache_lock, 'release')

    def test_cache_concurrent_access(self):
        """Test cache concurrent access safety"""
        import threading

        def write_to_cache(host_id):
            for i in range(100):
                _last_collect_cache[f"{host_id}-{i}"] = {"value": i}

        threads = [
            threading.Thread(target=write_to_cache, args=("host1",)),
            threading.Thread(target=write_to_cache, args=("host2",)),
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should have written all values without corruption
        assert len(_last_collect_cache) == 200


class TestLinuxCollectorConstants:
    """Test suite for module constants"""

    def test_host_max_failures(self):
        """Test _HOST_MAX_FAILURES constant"""
        assert isinstance(_HOST_MAX_FAILURES, int)
        assert _HOST_MAX_FAILURES > 0

    def test_host_cooldown_seconds(self):
        """Test _HOST_COOLDOWN_SEC constant"""
        assert isinstance(_HOST_COOLDOWN_SEC, int)
        assert _HOST_COOLDOWN_SEC > 0


class TestSSHCommandExecution:
    """Test suite for SSH command execution"""

    @pytest.mark.asyncio
    async def test_ssh_execute_success(self):
        """Test successful SSH command execution"""
        from core.linux_collector import _ssh_execute

        host_config = {
            "host": "test-host",
            "port": 22,
            "username": "test-user",
            "password": "test-pass"
        }

        with patch('core.linux_collector.asyncio.create_subprocess_exec') as mock_exec:
            mock_process = AsyncMock()
            mock_process.communicate = AsyncMock(return_value=(b"output", b""))
            mock_process.returncode = 0
            mock_exec.return_value = mock_process

            result = await _ssh_execute(host_config, "echo test")
            assert result == "output"

    @pytest.mark.asyncio
    async def test_ssh_execute_failure(self):
        """Test SSH command execution failure"""
        from core.linux_collector import _ssh_execute

        host_config = {
            "host": "test-host",
            "port": 22,
            "username": "test-user",
            "password": "test-pass"
        }

        with patch('core.linux_collector.asyncio.create_subprocess_exec') as mock_exec:
            mock_process = AsyncMock()
            mock_process.communicate = AsyncMock(return_value=(b"", b"error"))
            mock_process.returncode = 1
            mock_exec.return_value = mock_process

            result = await _ssh_execute(host_config, "echo test")
            assert result == ""

    @pytest.mark.asyncio
    async def test_ssh_execute_timeout(self):
        """Test SSH command execution timeout"""
        from core.linux_collector import _ssh_execute

        host_config = {
            "host": "test-host",
            "port": 22,
            "username": "test-user",
            "password": "test-pass"
        }

        with patch('core.linux_collector.asyncio.create_subprocess_exec') as mock_exec:
            mock_process = AsyncMock()
            mock_process.communicate = AsyncMock(side_effect=asyncio.TimeoutError())
            mock_process.kill = AsyncMock()
            mock_process.wait = AsyncMock()
            mock_exec.return_value = mock_process

            result = await _ssh_execute(host_config, "echo test")
            assert result == "TIMEOUT"

    @pytest.mark.asyncio
    async def test_ssh_execute_connection_error(self):
        """Test SSH connection error"""
        from core.linux_collector import _ssh_execute

        host_config = {
            "host": "test-host",
            "port": 22,
            "username": "test-user",
            "password": "test-pass"
        }

        with patch('core.linux_collector.asyncio.create_subprocess_exec') as mock_exec:
            mock_exec.side_effect = ConnectionError("Connection refused")

            result = await _ssh_execute(host_config, "echo test")
            assert "ERROR" in result

    @pytest.mark.asyncio
    async def test_ssh_execute_invalid_host_config(self):
        """Test SSH execute with invalid host config"""
        from core.linux_collector import _ssh_execute

        result = await _ssh_execute(None, "echo test")
        assert "ERROR" in result

        result = await _ssh_execute("not-a-dict", "echo test")
        assert "ERROR" in result

    @pytest.mark.asyncio
    async def test_ssh_execute_missing_host_field(self):
        """Test SSH execute with missing host field"""
        from core.linux_collector import _ssh_execute

        host_config = {"port": 22, "username": "test-user"}
        result = await _ssh_execute(host_config, "echo test")
        assert "ERROR" in result

    @pytest.mark.asyncio
    async def test_ssh_execute_missing_username(self):
        """Test SSH execute with missing username"""
        from core.linux_collector import _ssh_execute

        host_config = {"host": "test-host", "port": 22}
        result = await _ssh_execute(host_config, "echo test")
        assert "ERROR" in result

    @pytest.mark.asyncio
    async def test_ssh_execute_empty_command(self):
        """Test SSH execute with empty command"""
        from core.linux_collector import _ssh_execute

        host_config = {
            "host": "test-host",
            "port": 22,
            "username": "test-user",
            "password": "test-pass"
        }

        result = await _ssh_execute(host_config, "")
        assert result == ""

        result = await _ssh_execute(host_config, None)
        assert result == ""


class TestLinuxMetricsCollection:
    """Test suite for Linux metrics collection"""

    @pytest.mark.asyncio
    async def test_collect_linux_host_success(self):
        """Test successful Linux host collection"""
        host_name = "test-host-success"
        host_config = {
            "name": host_name,
            "host": "192.168.1.100",
            "port": 22,
            "username": "test-user",
            "password": "test-pass"
        }

        # Mock the batch execution to return successful results for all metrics
        async def mock_batch_execute(host_config, commands, semaphore):
            # Return valid data for each metric type
            results = {}
            for metric_name in commands.keys():
                if metric_name == "cpu_usage":
                    results[metric_name] = "80.5"
                elif metric_name == "memory":
                    results[metric_name] = "8000 4000 4000 50.0"
                elif metric_name == "load_avg":
                    results[metric_name] = "1.0 2.0 3.0"
                elif metric_name == "swap":
                    results[metric_name] = "2000 1000 50.0"
                else:
                    results[metric_name] = "valid_data"
            return results

        with patch('core.linux_collector._ssh_execute_batch', side_effect=mock_batch_execute):
            result = await collect_linux_host(host_config, metrics=["cpu_usage", "memory", "load_avg", "swap"])
            assert result is not None
            assert result["status"] == "ok"
            assert result["name"] == host_name
            assert "metrics" in result

        # Cleanup
        _record_host_success(host_name)

    @pytest.mark.asyncio
    async def test_collect_linux_host_no_auth(self):
        """Test collection with no authentication"""
        host_config = {
            "name": "test-host",
            "host": "192.168.1.100",
            "port": 22
        }

        result = await collect_linux_host(host_config)
        assert result["status"] == "skipped"
        assert "未配置 SSH 认证" in result["error"]

    @pytest.mark.asyncio
    async def test_collect_linux_host_invalid_config(self):
        """Test collection with invalid config"""
        result = await collect_linux_host(None)
        assert result["status"] == "error"

        result = await collect_linux_host("not-a-dict")
        assert result["status"] == "error"

    @pytest.mark.asyncio
    async def test_collect_linux_host_in_cooldown(self):
        """Test collection when host is in cooldown"""
        # Put host in cooldown
        for _ in range(_HOST_MAX_FAILURES + 1):
            _record_host_failure("test-host")

        # Add cached data
        _last_collect_cache["test-host"] = {
            "name": "test-host",
            "host": "192.168.1.100",
            "status": "ok",
            "timestamp": "2024-01-01T00:00:00",
            "metrics": {}
        }

        host_config = {
            "name": "test-host",
            "host": "192.168.1.100",
            "port": 22,
            "username": "test-user",
            "password": "test-pass"
        }

        result = await collect_linux_host(host_config)
        assert result["status"] == "cached_stale"
        assert "stale_at" in result

    @pytest.mark.asyncio
    async def test_collect_linux_host_cooldown_no_cache(self):
        """Test collection when host is in cooldown with no cache"""
        # Use a unique host name to avoid conflicts
        host_name = "test-host-no-cache"
        # Put host in cooldown
        for _ in range(_HOST_MAX_FAILURES + 1):
            _record_host_failure(host_name)

        host_config = {
            "name": host_name,
            "host": "192.168.1.100",
            "port": 22,
            "username": "test-user",
            "password": "test-pass"
        }

        result = await collect_linux_host(host_config)
        assert result["status"] == "cooldown"

        # Cleanup
        _record_host_success(host_name)

    @pytest.mark.asyncio
    async def test_collect_linux_host_partial_failure(self):
        """Test collection with partial metric failures"""
        host_name = "test-host-partial"
        host_config = {
            "name": host_name,
            "host": "192.168.1.100",
            "port": 22,
            "username": "test-user",
            "password": "test-pass"
        }

        async def mock_batch_execute(host_config, commands, semaphore):
            # Return mix of success and failure
            results = {}
            for k in commands.keys():
                if k == "cpu_usage":
                    results[k] = "80.5"
                else:
                    results[k] = "ERROR: command failed"
            return results

        with patch('core.linux_collector._ssh_execute_batch', side_effect=mock_batch_execute):
            result = await collect_linux_host(host_config, metrics=["cpu_usage", "memory", "load_avg"])
            assert result["status"] in ["degraded", "error"]

        # Cleanup
        _record_host_success(host_name)

    @pytest.mark.asyncio
    async def test_collect_linux_host_massive_failure(self):
        """Test collection with massive metric failures (>80%)"""
        host_name = "test-host-massive"
        host_config = {
            "name": host_name,
            "host": "192.168.1.100",
            "port": 22,
            "username": "test-user",
            "password": "test-pass"
        }

        async def mock_batch_execute(host_config, commands, semaphore):
            # Return all failures to trigger >80% error condition
            results = {}
            for k in commands.keys():
                results[k] = "ERROR: command failed"
            return results

        with patch('core.linux_collector._ssh_execute_batch', side_effect=mock_batch_execute):
            result = await collect_linux_host(host_config, metrics=["cpu_usage", "memory", "load_avg", "disk_usage", "swap"])
            assert result["status"] == "error"
            # Should record failure
            assert host_name in _host_failure_tracker

        # Cleanup
        _record_host_success(host_name)


class TestBatchCollection:
    """Test suite for batch collection functionality"""

    @pytest.mark.asyncio
    async def test_collect_all_linux_success(self):
        """Test collecting from all Linux hosts"""
        with patch('core.linux_collector.LINUX_HOSTS') as mock_hosts:
            mock_hosts.get.return_value = [
                {"name": "host1", "host": "192.168.1.1", "port": 22, "username": "user", "password": "pass"},
                {"name": "host2", "host": "192.168.1.2", "port": 22, "username": "user", "password": "pass"},
            ]

            async def mock_collect(host_config, metrics):
                return {"status": "ok", "name": host_config.get("name", "test")}

            with patch('core.linux_collector.collect_linux_host', side_effect=mock_collect):
                result = await collect_all_linux()
                assert result is not None
                assert len(result) == 2

    @pytest.mark.asyncio
    async def test_collect_all_linux_empty_hosts(self):
        """Test collecting with no hosts configured"""
        with patch('core.linux_collector.LINUX_HOSTS') as mock_hosts:
            mock_hosts.get.return_value = []

            result = await collect_all_linux()
            assert result == []

    @pytest.mark.asyncio
    async def test_collect_all_linux_with_exception(self):
        """Test collecting with host collection exception"""
        with patch('core.linux_collector.LINUX_HOSTS') as mock_hosts:
            mock_hosts.get.return_value = [
                {"name": "host1", "host": "192.168.1.1", "port": 22, "username": "user", "password": "pass"},
            ]

            async def mock_collect(host_config, metrics):
                raise Exception("Collection failed")

            with patch('core.linux_collector.collect_linux_host', side_effect=mock_collect):
                result = await collect_all_linux()
                assert result is not None
                assert len(result) == 1
                assert result[0]["status"] == "error"

    @pytest.mark.asyncio
    async def test_ssh_execute_batch_success(self):
        """Test batch SSH execution success"""
        from core.linux_collector import _ssh_execute_batch

        host_config = {
            "host": "test-host",
            "port": 22,
            "username": "test-user",
            "password": "test-pass"
        }

        commands = {
            "cpu_usage": "echo 80.5",
            "memory": "echo 50.0"
        }

        async def mock_ssh(host_config, command, semaphore):
            # Simulate batch output with nonce separators
            return "===AIOPS123METRIC:cpu_usage:123===AIOPSEND===\n80.5\n===AIOPS123METRIC:memory:123===AIOPSEND===\n50.0"

        with patch('core.linux_collector._ssh_execute', side_effect=mock_ssh):
            result = await _ssh_execute_batch(host_config, commands)
            assert result is not None
            assert "cpu_usage" in result
            assert "memory" in result

    @pytest.mark.asyncio
    async def test_ssh_execute_batch_empty_commands(self):
        """Test batch execution with empty commands"""
        from core.linux_collector import _ssh_execute_batch

        host_config = {
            "host": "test-host",
            "port": 22,
            "username": "test-user",
            "password": "test-pass"
        }

        result = await _ssh_execute_batch(host_config, {})
        assert result == {}

    @pytest.mark.asyncio
    async def test_ssh_execute_batch_ssh_failure(self):
        """Test batch execution with SSH failure"""
        from core.linux_collector import _ssh_execute_batch

        host_config = {
            "host": "test-host",
            "port": 22,
            "username": "test-user",
            "password": "test-pass"
        }

        commands = {
            "cpu_usage": "echo 80.5",
            "memory": "echo 50.0"
        }

        async def mock_ssh(host_config, command, semaphore):
            return "TIMEOUT"

        with patch('core.linux_collector._ssh_execute', side_effect=mock_ssh):
            result = await _ssh_execute_batch(host_config, commands)
            assert result["cpu_usage"] == "TIMEOUT"
            assert result["memory"] == "TIMEOUT"


class TestMetricsParsing:
    """Test suite for metrics parsing functions"""

    def test_parse_structured_metrics_cpu(self):
        """Test parsing CPU metrics"""
        from core.linux_collector import _parse_structured_metrics

        result = {
            "metrics": {
                "cpu_usage": {
                    "value": "80.5",
                    "desc": "CPU 使用率(%)"
                }
            }
        }

        _parse_structured_metrics(result)
        assert "parsed" in result["metrics"]["cpu_usage"]
        assert result["metrics"]["cpu_usage"]["parsed"]["usage_percent"] == 80.5

    def test_parse_structured_metrics_memory(self):
        """Test parsing memory metrics"""
        from core.linux_collector import _parse_structured_metrics

        result = {
            "metrics": {
                "memory": {
                    "value": "8000 4000 4000 50.0",
                    "desc": "内存使用率"
                }
            }
        }

        _parse_structured_metrics(result)
        assert "parsed" in result["metrics"]["memory"]
        assert result["metrics"]["memory"]["parsed"]["total_mb"] == 8000
        assert result["metrics"]["memory"]["parsed"]["used_mb"] == 4000
        assert result["metrics"]["memory"]["parsed"]["usage_percent"] == 50.0

    def test_parse_structured_metrics_load(self):
        """Test parsing load average metrics"""
        from core.linux_collector import _parse_structured_metrics

        result = {
            "metrics": {
                "load_avg": {
                    "value": "1.0 2.0 3.0",
                    "desc": "系统负载"
                }
            }
        }

        _parse_structured_metrics(result)
        assert "parsed" in result["metrics"]["load_avg"]
        assert result["metrics"]["load_avg"]["parsed"]["load_1min"] == 1.0
        assert result["metrics"]["load_avg"]["parsed"]["load_5min"] == 2.0
        assert result["metrics"]["load_avg"]["parsed"]["load_15min"] == 3.0

    def test_parse_structured_metrics_swap(self):
        """Test parsing swap metrics"""
        from core.linux_collector import _parse_structured_metrics

        result = {
            "metrics": {
                "swap": {
                    "value": "2000 1000 50.0",
                    "desc": "Swap 使用率"
                }
            }
        }

        _parse_structured_metrics(result)
        assert "parsed" in result["metrics"]["swap"]
        assert result["metrics"]["swap"]["parsed"]["total_mb"] == 2000
        assert result["metrics"]["swap"]["parsed"]["used_mb"] == 1000
        assert result["metrics"]["swap"]["parsed"]["usage_percent"] == 50.0

    def test_parse_structured_metrics_invalid_data(self):
        """Test parsing with invalid data"""
        from core.linux_collector import _parse_structured_metrics

        result = {
            "metrics": {
                "cpu_usage": {
                    "value": "invalid",
                    "desc": "CPU 使用率(%)"
                }
            }
        }

        _parse_structured_metrics(result)
        # Should not crash, just not add parsed field
        assert "parsed" not in result["metrics"]["cpu_usage"] or result["metrics"]["cpu_usage"]["parsed"] is None

    def test_parse_structured_metrics_empty_value(self):
        """Test parsing with empty value"""
        from core.linux_collector import _parse_structured_metrics

        result = {
            "metrics": {
                "cpu_usage": {
                    "value": "",
                    "desc": "CPU 使用率(%)"
                }
            }
        }

        _parse_structured_metrics(result)
        # Should not crash
        assert "metrics" in result


class TestHostConfiguration:
    """Test suite for host configuration handling"""

    def test_get_configured_hosts(self):
        """Test getting configured hosts"""
        with patch('core.linux_collector.LINUX_HOSTS') as mock_hosts:
            mock_hosts.get.return_value = [
                {
                    "name": "host1",
                    "host": "192.168.1.1",
                    "port": 22,
                    "username": "user",
                    "password": "pass",
                    "role": "app",
                    "layer": 3,
                    "downstream": ["host2"]
                }
            ]

            hosts = get_configured_hosts()
            assert isinstance(hosts, list)
            assert len(hosts) == 1
            assert hosts[0]["name"] == "host1"
            assert hosts[0]["auth"] == "password"
            assert hosts[0]["role"] == "app"
            assert hosts[0]["layer"] == 3

    def test_get_configured_hosts_key_auth(self):
        """Test getting configured hosts with key authentication"""
        with patch('core.linux_collector.LINUX_HOSTS') as mock_hosts:
            mock_hosts.get.return_value = [
                {
                    "name": "host1",
                    "host": "192.168.1.1",
                    "port": 22,
                    "username": "user",
                    "key_file": "/path/to/key"
                }
            ]

            hosts = get_configured_hosts()
            assert hosts[0]["auth"] == "key"

    def test_get_configured_hosts_no_auth(self):
        """Test getting configured hosts with no authentication"""
        with patch('core.linux_collector.LINUX_HOSTS') as mock_hosts:
            mock_hosts.get.return_value = [
                {
                    "name": "host1",
                    "host": "192.168.1.1",
                    "port": 22
                }
            ]

            hosts = get_configured_hosts()
            assert hosts[0]["auth"] == "none"

    def test_get_available_metrics(self):
        """Test getting available metrics"""
        metrics = get_available_metrics()
        assert isinstance(metrics, list)
        assert len(metrics) > 0
        assert all("key" in m and "desc" in m for m in metrics)

    def test_get_last_snapshot(self):
        """Test getting last collection snapshot"""
        # Add some data to cache
        _last_collect_cache["test-host"] = {
            "name": "test-host",
            "status": "ok"
        }

        snapshot = get_last_snapshot()
        assert isinstance(snapshot, dict)
        assert "test-host" in snapshot


class TestSemaphoreManagement:
    """Test suite for semaphore management"""

    def test_get_host_semaphore(self):
        """Test getting host semaphore"""
        sem1 = _get_host_semaphore("host1")
        sem2 = _get_host_semaphore("host1")
        sem3 = _get_host_semaphore("host2")

        # Same host should return same semaphore
        assert sem1 is sem2
        # Different host should return different semaphore
        assert sem1 is not sem3

    def test_get_host_semaphore_concurrent(self):
        """Test concurrent semaphore access"""
        import threading

        semaphores = []

        def get_sem(host):
            sem = _get_host_semaphore(host)
            semaphores.append(sem)

        threads = [
            threading.Thread(target=get_sem, args=("host1",)),
            threading.Thread(target=get_sem, args=("host1",)),
            threading.Thread(target=get_sem, args=("host2",)),
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All host1 requests should get same semaphore
        assert semaphores[0] is semaphores[1]
        # host2 should get different semaphore
        assert semaphores[0] is not semaphores[2]


class TestCollectCommands:
    """Test suite for collect commands definition"""

    def test_collect_commands_structure(self):
        """Test that COLLECT_COMMANDS has proper structure"""
        assert isinstance(COLLECT_COMMANDS, dict)
        assert len(COLLECT_COMMANDS) > 0

        for key, value in COLLECT_COMMANDS.items():
            assert isinstance(key, str)
            assert isinstance(value, dict)
            assert "cmd" in value
            assert "desc" in value

    def test_collect_commands_cpu_metrics(self):
        """Test CPU-related commands exist"""
        assert "cpu_usage" in COLLECT_COMMANDS
        assert "load_avg" in COLLECT_COMMANDS
        assert "cpu_cores" in COLLECT_COMMANDS

    def test_collect_commands_memory_metrics(self):
        """Test memory-related commands exist"""
        assert "memory" in COLLECT_COMMANDS
        assert "swap" in COLLECT_COMMANDS
        assert "oom_count" in COLLECT_COMMANDS

    def test_collect_commands_disk_metrics(self):
        """Test disk-related commands exist"""
        assert "disk_usage" in COLLECT_COMMANDS
        assert "inode_usage" in COLLECT_COMMANDS
        assert "disk_readonly" in COLLECT_COMMANDS

    def test_collect_commands_network_metrics(self):
        """Test network-related commands exist"""
        assert "network_errors" in COLLECT_COMMANDS
        assert "tcp_connections" in COLLECT_COMMANDS
        assert "listening_ports" in COLLECT_COMMANDS


class TestEdgeCases:
    """Test suite for edge cases and boundary conditions"""

    def _get_valid_mock_data(self):
        """Helper function to generate valid mock data for all metrics"""
        return {
            "cpu_usage": "80.5",
            "memory": "8000 4000 4000 50.0",
            "load_avg": "1.0 2.0 3.0",
            "swap": "2000 1000 50.0",
            "cpu_cores": "4",
            "context_switches": "1000",
            "io_wait": "5.0",
            "top_cpu_procs": "process1 10.0 5.0",
            "oom_count": "0",
            "top_mem_procs": "process1 10.0 1000",
            "disk_usage": "/dev/sda1 50G 20G 30G 40%",
            "inode_usage": "/dev/sda1 100000 50000 50000 50%",
            "disk_readonly": "",
            "large_files": "100M /var/log/app.log",
            "network_errors": "",
            "tcp_connections": "TCP: 100",
            "time_wait_count": "10",
            "listening_ports": "0.0.0.0:80",
            "process_count": "150",
            "zombie_count": "0",
            "d_state_count": "0",
            "file_descriptors": "1000 2000 50.0",
            "failed_services": "",
            "kernel_errors": "",
            "segfault_count": "0",
            "io_errors": "0",
            "ssh_failed_logins": "5",
            "current_users": "user1 pts/0",
            "time_sync": "synchronized",
            "log_size": "1G",
            "http_check": "200",
            "hostname": "test-host",
            "os_version": "Ubuntu 22.04",
            "uptime": "up 1 day",
            "kernel_version": "5.15.0",
        }

    @pytest.mark.asyncio
    async def test_collect_linux_host_with_specific_metrics(self):
        """Test collecting specific metrics only"""
        host_name = "test-host-specific"
        host_config = {
            "name": host_name,
            "host": "192.168.1.100",
            "port": 22,
            "username": "test-user",
            "password": "test-pass"
        }

        async def mock_batch_execute(host_config, commands, semaphore):
            valid_data = self._get_valid_mock_data()
            return {k: valid_data.get(k, "valid_data") for k in commands.keys()}

        with patch('core.linux_collector._ssh_execute_batch', side_effect=mock_batch_execute):
            result = await collect_linux_host(host_config, metrics=["cpu_usage"])
            assert result is not None
            assert "cpu_usage" in result["metrics"]
            # Should only have requested metric
            assert len(result["metrics"]) == 1

        # Cleanup
        _record_host_success(host_name)

    @pytest.mark.asyncio
    async def test_collect_linux_host_invalid_metrics(self):
        """Test collecting with invalid metric names"""
        host_name = "test-host-invalid"
        host_config = {
            "name": host_name,
            "host": "192.168.1.100",
            "port": 22,
            "username": "test-user",
            "password": "test-pass"
        }

        async def mock_batch_execute(host_config, commands, semaphore):
            return {}

        with patch('core.linux_collector._ssh_execute_batch', side_effect=mock_batch_execute):
            result = await collect_linux_host(host_config, metrics=["invalid_metric"])
            assert result["status"] == "error"

        # Cleanup
        _record_host_success(host_name)

    def test_host_cooldown_time_regression(self):
        """Test cooldown handles time regression"""
        import time

        # Record failures
        for _ in range(_HOST_MAX_FAILURES + 1):
            _record_host_failure("test-host")

        # Manually set last_fail to future (time regression)
        _host_failure_tracker["test-host"]["last_fail"] = time.monotonic() + 1000

        # Should detect regression and reset
        result = _is_host_in_cooldown("test-host")
        assert result is False

    @pytest.mark.asyncio
    async def test_collect_linux_host_key_auth(self):
        """Test collection with key authentication"""
        host_name = "test-host-key"
        host_config = {
            "name": host_name,
            "host": "192.168.1.100",
            "port": 22,
            "username": "test-user",
            "key_file": "/path/to/key"
        }

        async def mock_batch_execute(host_config, commands, semaphore):
            # Return valid data for each metric type
            results = {}
            for metric_name in commands.keys():
                if metric_name == "cpu_usage":
                    results[metric_name] = "80.5"
                elif metric_name == "memory":
                    results[metric_name] = "8000 4000 4000 50.0"
                elif metric_name == "load_avg":
                    results[metric_name] = "1.0 2.0 3.0"
                elif metric_name == "swap":
                    results[metric_name] = "2000 1000 50.0"
                else:
                    results[metric_name] = "valid_data"
            return results

        with patch('core.linux_collector._ssh_execute_batch', side_effect=mock_batch_execute):
            result = await collect_linux_host(host_config, metrics=["cpu_usage", "memory", "load_avg", "swap"])
            assert result is not None
            assert result["status"] == "ok"

        # Cleanup
        _record_host_success(host_name)

    @pytest.mark.asyncio
    async def test_collect_linux_host_both_auth(self):
        """Test collection with both key and password (key should win)"""
        host_name = "test-host-both"
        host_config = {
            "name": host_name,
            "host": "192.168.1.100",
            "port": 22,
            "username": "test-user",
            "key_file": "/path/to/key",
            "password": "test-pass"
        }

        async def mock_batch_execute(host_config, commands, semaphore):
            # Return valid data for each metric type
            results = {}
            for metric_name in commands.keys():
                if metric_name == "cpu_usage":
                    results[metric_name] = "80.5"
                elif metric_name == "memory":
                    results[metric_name] = "8000 4000 4000 50.0"
                elif metric_name == "load_avg":
                    results[metric_name] = "1.0 2.0 3.0"
                elif metric_name == "swap":
                    results[metric_name] = "2000 1000 50.0"
                else:
                    results[metric_name] = "valid_data"
            return results

        with patch('core.linux_collector._ssh_execute_batch', side_effect=mock_batch_execute):
            result = await collect_linux_host(host_config, metrics=["cpu_usage", "memory", "load_avg", "swap"])
            assert result is not None
            assert result["status"] == "ok"

        # Cleanup
        _record_host_success(host_name)
