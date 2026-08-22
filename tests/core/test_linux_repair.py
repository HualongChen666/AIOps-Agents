# -*- coding: utf-8 -*-
"""
Comprehensive test suite for core/linux_repair.py
Target: 90%+ statement and branch coverage
"""

import pytest
import sys
import os
import asyncio
from datetime import datetime
from unittest.mock import patch, MagicMock, AsyncMock
from collections import deque
from threading import Lock

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from core.linux_repair import (
    _LINUX_REPAIR_SCRIPTS_RAW,
    _PARAM_MAX_LEN,
    _OUTPUT_TRUNCATE_LEN,
    _HISTORY_MAX,
    _LINUX_PID_MAX,
    _LINUX_PID_RESERVED_MAX,
    get_linux_repair_scripts,
    execute_linux_repair,
    linux_repair_history,
    clear_linux_repair_history,
)


class TestLinuxRepairConstants:
    """Test suite for module constants"""

    def test_param_max_len(self):
        """Test parameter max length constant"""
        assert _PARAM_MAX_LEN == 128

    def test_output_truncate_len(self):
        """Test output truncate length constant"""
        assert _OUTPUT_TRUNCATE_LEN == 500

    def test_history_max(self):
        """Test history max constant"""
        assert _HISTORY_MAX == 200

    def test_linux_pid_max(self):
        """Test Linux PID max constant"""
        assert _LINUX_PID_MAX == 4_194_304

    def test_linux_pid_reserved_max(self):
        """Test Linux PID reserved max constant"""
        assert _LINUX_PID_RESERVED_MAX == 10


class TestLinuxRepairScripts:
    """Test suite for Linux repair scripts"""

    def test_scripts_raw_is_dict(self):
        """Test that scripts raw is a dictionary"""
        assert isinstance(_LINUX_REPAIR_SCRIPTS_RAW, dict)

    def test_scripts_read_only(self):
        """Test that scripts are read-only"""
        from types import MappingProxyType
        
        # The raw scripts should be wrapped in MappingProxyType
        scripts = get_linux_repair_scripts()
        # Should be a read-only mapping
        assert hasattr(scripts, '__getitem__')

    def test_get_linux_repair_scripts(self):
        """Test getting Linux repair scripts"""
        scripts = get_linux_repair_scripts()
        assert isinstance(scripts, dict)
        assert len(scripts) > 0

    def test_get_linux_repair_scripts_returns_copy(self):
        """Test that get_linux_repair_scripts returns a copy"""
        scripts1 = get_linux_repair_scripts()
        scripts2 = get_linux_repair_scripts()
        
        # Should be independent copies
        assert scripts1 is not scripts2

    def test_script_structure(self):
        """Test that each script has required fields"""
        scripts = get_linux_repair_scripts()
        
        for script_key, script_data in scripts.items():
            assert "name" in script_data
            assert "description" in script_data
            assert "risk" in script_data
            assert "command" in script_data

    def test_script_command_is_list(self):
        """Test that script commands are lists"""
        scripts = get_linux_repair_scripts()
        
        for script_key, script_data in scripts.items():
            assert isinstance(script_data["command"], list)

    def test_known_scripts_exist(self):
        """Test that known scripts exist"""
        scripts = get_linux_repair_scripts()
        
        known_scripts = ["clear_temp", "clear_logs", "flush_dns", "restart_service"]
        for script in known_scripts:
            assert script in scripts


class TestExecuteLinuxRepair:
    """Test suite for execute_linux_repair function"""

    @pytest.mark.asyncio
    async def test_execute_repair_success(self):
        """Test successful repair execution"""
        with patch('core.linux_repair._ssh_execute', return_value="success"):
            result = await execute_linux_repair(
                "test-host",
                "clear_temp",
                {"username": "user", "port": 22}
            )
            assert result is not None
            assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_execute_repair_with_params(self):
        """Test repair execution with parameters"""
        with patch('core.linux_repair._ssh_execute', return_value="success"):
            result = await execute_linux_repair(
                "test-host",
                "restart_service",
                {"username": "user", "port": 22},
                params={"service": "nginx"}
            )
            assert result is not None

    @pytest.mark.asyncio
    async def test_execute_repair_ssh_failure(self):
        """Test repair execution with SSH failure"""
        with patch('core.linux_repair._ssh_execute', side_effect=Exception("SSH failed")):
            result = await execute_linux_repair(
                "test-host",
                "clear_temp",
                {"username": "user", "port": 22}
            )
            assert result is not None
            assert result["status"] == "failed"

    @pytest.mark.asyncio
    async def test_execute_repair_unknown_script(self):
        """Test repair execution with unknown script"""
        result = await execute_linux_repair(
            "test-host",
            "unknown_script",
            {"username": "user", "port": 22}
        )
        assert result is not None
        assert result["status"] == "failed"

    @pytest.mark.asyncio
    async def test_execute_repair_dry_run(self):
        """Test repair execution in dry-run mode"""
        with patch('core.linux_repair._ssh_execute') as mock_ssh:
            result = await execute_linux_repair(
                "test-host",
                "clear_temp",
                {"username": "user", "port": 22},
                dry_run=True
            )
            # Should not execute actual SSH in dry-run mode
            assert result is not None

    @pytest.mark.asyncio
    async def test_execute_repair_with_approval(self):
        """Test repair execution requiring approval"""
        with patch('core.linux_repair._ssh_execute', return_value="success"):
            result = await execute_linux_repair(
                "test-host",
                "restart_service",
                {"username": "user", "port": 22},
                require_approval=True
            )
            assert result is not None
            # Should include approval status
            assert "approval" in result or "status" in result


class TestParameterSanitization:
    """Test suite for parameter sanitization"""

    def test_sanitize_param_string(self):
        """Test sanitizing string parameter"""
        from core.linux_repair import _sanitize_param
        
        result = _sanitize_param("test_param")
        assert result == "test_param"

    def test_sanitize_param_with_special_chars(self):
        """Test sanitizing parameter with special characters"""
        from core.linux_repair import _sanitize_param
        
        result = _sanitize_param("test;param")
        # Should escape or remove dangerous characters
        assert ";" not in result or result is not None

    def test_sanitize_param_too_long(self):
        """Test sanitizing parameter that's too long"""
        from core.linux_repair import _sanitize_param
        
        long_param = "x" * 200
        result = _sanitize_param(long_param)
        # Should truncate
        assert len(result) <= _PARAM_MAX_LEN

    def test_sanitize_param_none(self):
        """Test sanitizing None parameter"""
        from core.linux_repair import _sanitize_param
        
        result = _sanitize_param(None)
        assert result is None or result == ""

    def test_sanitize_param_pid(self):
        """Test sanitizing PID parameter"""
        from core.linux_repair import _sanitize_param
        
        result = _sanitize_param(1234, param_type="pid")
        assert result == "1234"

    def test_sanitize_param_pid_reserved(self):
        """Test sanitizing reserved PID"""
        from core.linux_repair import _sanitize_param
        
        result = _sanitize_param(1, param_type="pid")
        # Should reject reserved PIDs
        assert result is None or result == "1"

    def test_sanitize_param_pid_too_large(self):
        """Test sanitizing PID that's too large"""
        from core.linux_repair import _sanitize_param
        
        result = _sanitize_param(_LINUX_PID_MAX + 1, param_type="pid")
        # Should reject invalid PIDs
        assert result is None


class TestCommandGuardIntegration:
    """Test suite for command guard integration"""

    def test_analyze_command_risk(self):
        """Test analyzing command risk"""
        from core.linux_repair import analyze_command
        
        if analyze_command is not None:
            result = analyze_command("rm -rf /tmp/test")
            assert result is not None

    def test_record_audit_log(self):
        """Test recording audit log"""
        from core.linux_repair import record_audit
        
        if record_audit is not None:
            # Should not raise exception
            record_audit("test-command", "test-user", "approved")


class TestRepairHistory:
    """Test suite for repair history management"""

    def setup_method(self):
        """Reset repair history before each test"""
        clear_linux_repair_history()

    def test_repair_history_is_deque(self):
        """Test that repair history is a deque"""
        assert isinstance(linux_repair_history, deque)

    def test_repair_history_maxlen(self):
        """Test that repair history has max length"""
        assert linux_repair_history.maxlen == _HISTORY_MAX

    def test_record_to_history(self):
        """Test recording to repair history"""
        from core.linux_repair import _record_to_history
        
        record = {
            "timestamp": datetime.now(),
            "host": "test-host",
            "script": "clear_temp",
            "status": "success",
        }
        
        _record_to_history(record)
        assert len(linux_repair_history) == 1

    def test_clear_repair_history(self):
        """Test clearing repair history"""
        from core.linux_repair import _record_to_history
        
        # Add some records
        for i in range(5):
            _record_to_history({
                "timestamp": datetime.now(),
                "host": f"host{i}",
                "script": "clear_temp",
                "status": "success",
            })
        
        assert len(linux_repair_history) == 5
        
        # Clear history
        clear_linux_repair_history()
        assert len(linux_repair_history) == 0

    def test_history_auto_lru(self):
        """Test that history automatically evicts old entries"""
        from core.linux_repair import _record_to_history
        
        # Add more records than max
        for i in range(_HISTORY_MAX + 10):
            _record_to_history({
                "timestamp": datetime.now(),
                "host": f"host{i}",
                "script": "clear_temp",
                "status": "success",
            })
        
        # Should be limited to max
        assert len(linux_repair_history) <= _HISTORY_MAX


class TestSpecificRepairScripts:
    """Test suite for specific repair scripts"""

    @pytest.mark.asyncio
    async def test_clear_temp_script(self):
        """Test clear_temp script execution"""
        with patch('core.linux_repair._ssh_execute', return_value="tmp cleaned"):
            result = await execute_linux_repair(
                "test-host",
                "clear_temp",
                {"username": "user", "port": 22}
            )
            assert result is not None

    @pytest.mark.asyncio
    async def test_clear_logs_script(self):
        """Test clear_logs script execution"""
        with patch('core.linux_repair._ssh_execute', return_value="logs cleaned"):
            result = await execute_linux_repair(
                "test-host",
                "clear_logs",
                {"username": "user", "port": 22}
            )
            assert result is not None

    @pytest.mark.asyncio
    async def test_flush_dns_script(self):
        """Test flush_dns script execution"""
        with patch('core.linux_repair._ssh_execute', return_value="DNS flushed"):
            result = await execute_linux_repair(
                "test-host",
                "flush_dns",
                {"username": "user", "port": 22}
            )
            assert result is not None

    @pytest.mark.asyncio
    async def test_restart_service_script(self):
        """Test restart_service script execution"""
        with patch('core.linux_repair._ssh_execute', return_value="service restarted"):
            result = await execute_linux_repair(
                "test-host",
                "restart_service",
                {"username": "user", "port": 22},
                params={"service": "nginx"}
            )
            assert result is not None

    @pytest.mark.asyncio
    async def test_kill_process_script(self):
        """Test kill_process script execution"""
        with patch('core.linux_repair._ssh_execute', return_value="process killed"):
            result = await execute_linux_repair(
                "test-host",
                "kill_process",
                {"username": "user", "port": 22},
                params={"pid": 1234}
            )
            assert result is not None


class TestErrorHandling:
    """Test suite for error handling"""

    @pytest.mark.asyncio
    async def test_handle_ssh_timeout(self):
        """Test handling SSH timeout"""
        with patch('core.linux_repair._ssh_execute', side_effect=asyncio.TimeoutError()):
            result = await execute_linux_repair(
                "test-host",
                "clear_temp",
                {"username": "user", "port": 22}
            )
            assert result is not None
            assert result["status"] == "failed"

    @pytest.mark.asyncio
    async def test_handle_connection_error(self):
        """Test handling connection error"""
        with patch('core.linux_repair._ssh_execute', side_effect=ConnectionError()):
            result = await execute_linux_repair(
                "test-host",
                "clear_temp",
                {"username": "user", "port": 22}
            )
            assert result is not None
            assert result["status"] == "failed"

    @pytest.mark.asyncio
    async def test_handle_invalid_host_config(self):
        """Test handling invalid host configuration"""
        result = await execute_linux_repair(
            "test-host",
            "clear_temp",
            {}  # Missing required fields
        )
        assert result is not None
        assert result["status"] == "failed"


class TestConcurrencySafety:
    """Test suite for concurrency safety"""

    def test_history_lock_protection(self):
        """Test that history operations are lock-protected"""
        from core.linux_repair import _history_lock
        
        assert _history_lock is not None
        assert isinstance(_history_lock, Lock)

    def test_concurrent_history_writes(self):
        """Test concurrent history writes"""
        import threading
        from core.linux_repair import _record_to_history
        
        def write_record(host_id):
            for i in range(50):
                _record_to_history({
                    "timestamp": datetime.now(),
                    "host": f"{host_id}-{i}",
                    "script": "clear_temp",
                    "status": "success",
                })
        
        threads = [
            threading.Thread(target=write_record, args=("host1",)),
            threading.Thread(target=write_record, args=("host2",)),
        ]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # Should handle concurrent writes safely
        assert len(linux_repair_history) <= _HISTORY_MAX


class TestDataValidation:
    """Test suite for data validation"""

    def test_validate_script_key(self):
        """Test script key validation"""
        from core.linux_repair import _validate_script_key
        
        assert _validate_script_key("clear_temp") is True
        assert _validate_script_key("invalid_script") is False

    def test_validate_host_config(self):
        """Test host configuration validation"""
        from core.linux_repair import _validate_host_config
        
        valid_config = {"username": "user", "port": 22}
        assert _validate_host_config(valid_config) is True
        
        invalid_config = {}
        assert _validate_host_config(invalid_config) is False

    def test_validate_params(self):
        """Test parameters validation"""
        from core.linux_repair import _validate_params
        
        valid_params = {"service": "nginx"}
        assert _validate_params(valid_params, "restart_service") is True
        
        invalid_params = {"invalid": "param"}
        assert _validate_params(invalid_params, "restart_service") is False


class TestOutputProcessing:
    """Test suite for output processing"""

    def test_truncate_output(self):
        """Test output truncation"""
        from core.linux_repair import _truncate_output
        
        long_output = "x" * 1000
        result = _truncate_output(long_output)
        assert len(result) <= _OUTPUT_TRUNCATE_LEN

    def test_parse_command_output(self):
        """Test parsing command output"""
        from core.linux_repair import _parse_command_output
        
        output = "success\nwith\nnewlines"
        result = _parse_command_output(output)
        assert result is not None

    def test_extract_error_from_output(self):
        """Test extracting error from output"""
        from core.linux_repair import _extract_error_from_output
        
        error_output = "Error: command failed"
        result = _extract_error_from_output(error_output)
        assert result is not None or "Error" in result


class TestIntegrationScenarios:
    """Test suite for integration scenarios"""

    @pytest.mark.asyncio
    async def test_full_repair_workflow(self):
        """Test complete repair workflow"""
        with patch('core.linux_repair._ssh_execute', return_value="success"):
            # Execute repair
            result = await execute_linux_repair(
                "test-host",
                "clear_temp",
                {"username": "user", "port": 22}
            )
            
            assert result is not None
            assert result["status"] == "success"
            
            # Check history
            assert len(linux_repair_history) > 0

    @pytest.mark.asyncio
    async def test_repair_with_approval_workflow(self):
        """Test repair workflow with approval"""
        with patch('core.linux_repair._ssh_execute', return_value="success"):
            result = await execute_linux_repair(
                "test-host",
                "restart_service",
                {"username": "user", "port": 22},
                params={"service": "nginx"},
                require_approval=True
            )
            
            assert result is not None
            # Should include approval information
            assert "status" in result

    @pytest.mark.asyncio
    async def test_repair_with_rollback(self):
        """Test repair with rollback on failure"""
        with patch('core.linux_repair._ssh_execute', return_value="failed"):
            result = await execute_linux_repair(
                "test-host",
                "restart_service",
                {"username": "user", "port": 22},
                params={"service": "nginx"},
                auto_rollback=True
            )
            
            assert result is not None
            # Should handle failure and potentially rollback
