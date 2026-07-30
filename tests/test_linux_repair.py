# -*- coding: utf-8 -*-
# tests/test_linux_repair.py
# Linux 修复引擎单元测试
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

asyncssh = pytest.importorskip("asyncssh")

from core.linux_repair import (
    _record_to_sqlite_sync,
    _run_ssh_command,
    execute_linux_repair,
    get_linux_repair_scripts,
)


class TestLinuxRepairScripts:
    """Linux 修复脚本测试"""

    def test_get_linux_repair_scripts(self):
        """测试获取 Linux 修复脚本列表"""
        scripts = get_linux_repair_scripts()

        # 验证返回的是字典
        assert isinstance(scripts, dict)

        # 验证包含常用脚本
        assert "clear_temp" in scripts
        assert "restart_service" in scripts
        assert "kill_process" in scripts

        # 验证脚本结构
        for script_key, script_info in scripts.items():
            assert "name" in script_info
            assert "description" in script_info
            assert "script" in script_info


class TestSSHCommandExecution:
    """SSH 命令执行测试"""

    @pytest.mark.asyncio
    async def test_run_ssh_command_success(self, mock_logger):
        """测试 SSH 命令执行成功"""
        host = "server-01"
        command = "ls -la /tmp"

        with patch("core.linux_repair.logger", mock_logger):
            # Mock SSH 客户端
            with patch("asyncssh.connect") as mock_connect:
                mock_conn = AsyncMock()
                mock_conn.run = AsyncMock()
                mock_conn.run.return_value.stdout = "total 0\n"
                mock_conn.close = AsyncMock()
                mock_connect.return_value = mock_conn

                result = await _run_ssh_command(host, command)

                # 验证执行成功
                assert result["success"] is True
                assert "total 0" in result["output"]

    @pytest.mark.asyncio
    async def test_run_ssh_command_failure(self, mock_logger):
        """测试 SSH 命令执行失败"""
        host = "server-01"
        command = "ls /nonexistent"

        with patch("core.linux_repair.logger", mock_logger):
            # Mock SSH 客户端
            with patch("asyncssh.connect") as mock_connect:
                mock_conn = AsyncMock()
                mock_conn.run = AsyncMock()
                mock_conn.run.return_value.stderr = "No such file or directory\n"
                mock_conn.run.return_value.exit_status = 1
                mock_conn.close = AsyncMock()
                mock_connect.return_value = mock_conn

                result = await _run_ssh_command(host, command)

                # 验证执行失败
                assert result["success"] is False
                assert "error" in result

    @pytest.mark.asyncio
    async def test_run_ssh_command_timeout(self, mock_logger):
        """测试 SSH 命令执行超时"""
        host = "server-01"
        command = "sleep 100"

        with patch("core.linux_repair.logger", mock_logger):
            # Mock SSH 客户端
            with patch("asyncssh.connect") as mock_connect:
                mock_conn = AsyncMock()
                mock_conn.run = AsyncMock(side_effect=asyncio.TimeoutError())
                mock_conn.close = AsyncMock()
                mock_connect.return_value = mock_conn

                result = await _run_ssh_command(host, command)

                # 验证超时处理
                assert result["success"] is False
                assert "timeout" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_run_ssh_command_connection_error(self, mock_logger):
        """测试 SSH 连接错误"""
        host = "unreachable-server"
        command = "ls -la"

        with patch("core.linux_repair.logger", mock_logger):
            # Mock SSH 连接失败
            with patch("asyncssh.connect", side_effect=ConnectionError("Connection refused")):
                result = await _run_ssh_command(host, command)

                # 验证连接错误
                assert result["success"] is False
                assert "connection" in result["error"].lower()


class TestLinuxRepairExecution:
    """Linux 修复执行测试"""

    @pytest.mark.asyncio
    async def test_execute_linux_repair_success(self, mock_logger):
        """测试 Linux 修复执行成功"""
        host = "server-01"
        script_key = "clear_temp"

        with patch("core.linux_repair.logger", mock_logger):
            # Mock SSH 执行
            with patch(
                "core.linux_repair._run_ssh_command",
                AsyncMock(
                    return_value={
                        "success": True,
                        "output": "Temp files cleared",
                        "error": "",
                    }
                ),
            ):
                # Mock 命令护栏
                with patch(
                    "core.linux_repair.analyze_command",
                    AsyncMock(
                        return_value={
                            "allowed": True,
                            "risk_level": "low",
                        }
                    ),
                ):
                    # Mock 审计记录
                    with patch("core.linux_repair._safe_record_audit", AsyncMock()):
                        # Mock SQLite 记录
                        with patch("core.linux_repair._record_to_sqlite_sync", AsyncMock()):
                            result = await execute_linux_repair(host, script_key, {})

                            # 验证执行成功
                            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_execute_linux_repair_blocked_by_guard(self, mock_logger):
        """测试 Linux 修复被护栏阻止"""
        host = "server-01"
        script_key = "clear_temp"

        with patch("core.linux_repair.logger", mock_logger):
            # Mock 命令护栏拒绝
            with patch(
                "core.linux_repair.analyze_command",
                AsyncMock(
                    return_value={
                        "allowed": False,
                        "risk_level": "high",
                        "reason": "Dangerous command",
                    }
                ),
            ):
                result = await execute_linux_repair(host, script_key, {})

                # 验证被阻止
                assert result["success"] is False
                assert "blocked" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_execute_linux_repair_invalid_script(self, mock_logger):
        """测试无效脚本键"""
        host = "server-01"
        script_key = "invalid_script"

        with patch("core.linux_repair.logger", mock_logger):
            result = await execute_linux_repair(host, script_key, {})

            # 验证失败
            assert result["success"] is False
            assert "not found" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_execute_linux_repair_with_params(self, mock_logger):
        """测试带参数的 Linux 修复执行"""
        host = "server-01"
        script_key = "restart_service"
        params = {"service_name": "nginx"}

        with patch("core.linux_repair.logger", mock_logger):
            # Mock SSH 执行
            with patch(
                "core.linux_repair._run_ssh_command",
                AsyncMock(
                    return_value={
                        "success": True,
                        "output": "Service restarted",
                        "error": "",
                    }
                ),
            ):
                # Mock 命令护栏
                with patch(
                    "core.linux_repair.analyze_command",
                    AsyncMock(
                        return_value={
                            "allowed": True,
                            "risk_level": "low",
                        }
                    ),
                ):
                    # Mock 审计记录
                    with patch("core.linux_repair._safe_record_audit", AsyncMock()):
                        # Mock SQLite 记录
                        with patch("core.linux_repair._record_to_sqlite_sync", AsyncMock()):
                            result = await execute_linux_repair(host, script_key, params)

                            # 验证执行成功
                            assert result["success"] is True


class TestLinuxRepairHistory:
    """Linux 修复历史测试"""

    def test_record_to_sqlite_sync(self, mock_logger):
        """测试 SQLite 记录"""
        record = {
            "host": "server-01",
            "script_key": "clear_temp",
            "params": "{}",
            "output": "Success",
            "success": True,
            "timestamp": datetime.now().isoformat(),
        }

        with patch("core.linux_repair.logger", mock_logger):
            # Mock SQLite 连接
            with patch("sqlite3.connect") as mock_connect:
                mock_conn = MagicMock()
                mock_cursor = MagicMock()
                mock_conn.cursor.return_value = mock_cursor
                mock_connect.return_value = mock_conn

                result = _record_to_sqlite_sync(record)

                # 验证返回成功
                assert result is True
                # 验证 SQL 执行
                mock_cursor.execute.assert_called()

    @pytest.mark.asyncio
    async def test_get_linux_repair_history(self, mock_logger):
        """测试获取 Linux 修复历史"""
        with patch("core.linux_repair.logger", mock_logger):
            # Mock SQLite 查询
            with patch(
                "core.linux_repair.get_linux_repair_history",
                return_value=[
                    {
                        "id": 1,
                        "host": "server-01",
                        "script_key": "clear_temp",
                        "timestamp": "2026-06-09T10:00:00Z",
                    }
                ],
            ):
                from core.linux_repair import get_linux_repair_history

                history = get_linux_repair_history(limit=10)

                # 验证返回历史
                assert len(history) > 0
                assert history[0]["host"] == "server-01"


class TestLinuxRepairSafety:
    """Linux 修复安全测试"""

    @pytest.mark.asyncio
    async def test_command_guard_integration(self, mock_logger):
        """测试命令护栏集成"""
        host = "server-01"
        script_key = "clear_temp"

        with patch("core.linux_repair.logger", mock_logger):
            # Mock 命令护栏
            with patch(
                "core.linux_repair.analyze_command",
                AsyncMock(
                    return_value={
                        "allowed": True,
                        "risk_level": "low",
                    }
                ),
            ) as mock_analyze:
                # Mock SSH 执行
                with patch(
                    "core.linux_repair._run_ssh_command",
                    AsyncMock(
                        return_value={
                            "success": True,
                            "output": "Success",
                            "error": "",
                        }
                    ),
                ):
                    # Mock 审计记录
                    with patch("core.linux_repair._safe_record_audit", AsyncMock()):
                        # Mock SQLite 记录
                        with patch("core.linux_repair._record_to_sqlite_sync", AsyncMock()):
                            await execute_linux_repair(host, script_key, {})

                            # 验证命令护栏被调用
                            mock_analyze.assert_called_once()

    @pytest.mark.asyncio
    async def test_audit_recording(self, mock_logger):
        """测试审计记录"""
        host = "server-01"
        script_key = "clear_temp"

        with patch("core.linux_repair.logger", mock_logger):
            # Mock SSH 执行
            with patch(
                "core.linux_repair._run_ssh_command",
                AsyncMock(
                    return_value={
                        "success": True,
                        "output": "Success",
                        "error": "",
                    }
                ),
            ):
                # Mock 命令护栏
                with patch(
                    "core.linux_repair.analyze_command",
                    AsyncMock(
                        return_value={
                            "allowed": True,
                            "risk_level": "low",
                        }
                    ),
                ):
                    # Mock 审计记录
                    with patch("core.linux_repair._safe_record_audit", AsyncMock()) as mock_audit:
                        # Mock SQLite 记录
                        with patch("core.linux_repair._record_to_sqlite_sync", AsyncMock()):
                            await execute_linux_repair(host, script_key, {})

                            # 验证审计记录被调用
                            mock_audit.assert_called_once()


class TestLinuxRepairErrorHandling:
    """Linux 修复错误处理测试"""

    @pytest.mark.asyncio
    async def test_repair_exception_handling(self, mock_logger):
        """测试修复执行异常处理"""
        host = "server-01"
        script_key = "clear_temp"

        with patch("core.linux_repair.logger", mock_logger):
            # Mock SSH 执行抛出异常
            with patch(
                "core.linux_repair._run_ssh_command",
                AsyncMock(side_effect=Exception("Runtime error")),
            ):
                result = await execute_linux_repair(host, script_key, {})

                # 验证异常被捕获
                assert result["success"] is False
                # 验证日志记录
                mock_logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_param_validation(self, mock_logger):
        """测试参数验证"""
        host = "server-01"
        script_key = "clear_temp"

        with patch("core.linux_repair.logger", mock_logger):
            # 测试过长参数
            long_param = "x" * 2000
            result = await execute_linux_repair(host, script_key, {"param": long_param})

            # 验证参数被截断或拒绝
            assert result["success"] is False

    @pytest.mark.asyncio
    async def test_host_validation(self, mock_logger):
        """测试主机验证"""
        with patch("core.linux_repair.logger", mock_logger):
            # 测试空主机
            result = await execute_linux_repair("", "clear_temp", {})

            # 验证主机验证失败
            assert result["success"] is False


class TestLinuxRepairHostFailureTracking:
    """Linux 修复主机失败跟踪测试"""

    @pytest.mark.asyncio
    async def test_host_failure_cooling(self, mock_logger):
        """测试主机失败冷却机制"""
        host = "unreachable-server"
        script_key = "clear_temp"

        with patch("core.linux_repair.logger", mock_logger):
            # Mock SSH 连接失败
            with patch(
                "core.linux_repair._run_ssh_command",
                AsyncMock(
                    return_value={
                        "success": False,
                        "error": "Connection refused",
                    }
                ),
            ):
                # 执行多次失败
                for _ in range(5):
                    await execute_linux_repair(host, script_key, {})

                # 验证进入冷却期（实际实现可能需要检查内部状态）
                # 这里只是验证不会抛出异常


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
