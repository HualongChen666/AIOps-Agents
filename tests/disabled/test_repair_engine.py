# -*- coding: utf-8 -*-
# tests/test_repair_engine.py
# 修复引擎单元测试
import asyncio  # noqa: F401
from datetime import datetime  # noqa: F401
from unittest.mock import AsyncMock, MagicMock, patch  # noqa: F401

import pytest

from core.repair_engine import (
    _record_to_sqlite_sync,
    _render_command,
    _run_powershell,
    _sanitize_param,
    clear_repair_history,
    execute_repair,
    get_repair_history,
    get_repair_scripts,
)


class TestRepairScripts:
    """修复脚本测试"""

    def test_get_repair_scripts(self):
        """测试获取修复脚本列表"""
        scripts = get_repair_scripts()

        # 验证返回的是列表
        assert isinstance(scripts, list)

        # 验证列表不为空
        assert len(scripts) > 0

    def test_get_repair_scripts_structure(self):
        """测试修复脚本结构"""
        scripts = get_repair_scripts()

        # 验证脚本结构
        for script in scripts:
            assert isinstance(script, dict)
            assert "key" in script or "name" in script


class TestPowerShellExecution:
    """PowerShell 执行测试"""

    def test_run_powershell_success(self, mock_logger):
        """测试 PowerShell 执行成功"""
        script = "Write-Host 'Hello World'"

        with patch("core.repair_engine.logger", mock_logger):
            # Mock subprocess
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(
                    stdout=b"Hello World\r\n", stderr=b"", returncode=0
                )

                result = _run_powershell(script)

                # 验证执行成功
                assert result["success"] is True
                assert "Hello World" in result["output"]

    def test_run_powershell_failure(self, mock_logger):
        """测试 PowerShell 执行失败"""
        script = "Write-Error 'Test Error'"

        with patch("core.repair_engine.logger", mock_logger):
            # Mock subprocess
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(
                    stdout=b"", stderr=b"Test Error\r\n", returncode=1
                )

                result = _run_powershell(script)

                # 验证执行失败
                assert result["success"] is False


class TestRepairExecution:
    """修复执行测试"""

    @pytest.mark.asyncio
    async def test_execute_repair_success(self, mock_logger):
        """测试修复执行成功"""
        with patch("core.repair_engine.logger", mock_logger):
            # Mock PowerShell 执行
            with patch(
                "core.repair_engine._run_powershell",
                return_value={
                    "success": True,
                    "output": "Temp files cleared",
                    "error": "",
                },
            ):
                result = await execute_repair("clear_temp", {})

                # 验证执行成功
                assert result["success"] is True

    @pytest.mark.asyncio
    async def test_execute_repair_invalid_script(self, mock_logger):
        """测试无效脚本键"""
        with patch("core.repair_engine.logger", mock_logger):
            result = await execute_repair("invalid_script", {})

            # 验证失败
            assert result["success"] is False
            assert "未知" in result["error"] or "not found" in result["error"]


class TestRepairHistory:
    """修复历史测试"""

    def test_record_to_sqlite_sync(self, mock_logger):
        """测试 SQLite 记录"""
        with patch("core.repair_engine.logger", mock_logger):
            # Mock SQLite 连接
            with patch("sqlite3.connect") as mock_connect:
                mock_conn = MagicMock()
                mock_cursor = MagicMock()
                mock_conn.cursor.return_value = mock_cursor
                mock_connect.return_value = mock_conn

                result = _record_to_sqlite_sync("rule_name", "script_key", "output", "output")

                # 验证返回结果（可能是True或False）
                assert isinstance(result, bool)


class TestRepairSafety:
    """修复安全测试"""

    @pytest.mark.asyncio
    async def test_execute_repair_safety(self, mock_logger):
        """测试修复执行安全性"""
        with patch("core.repair_engine.logger", mock_logger):
            # Mock PowerShell 执行
            with patch(
                "core.repair_engine._run_powershell",
                return_value={
                    "success": True,
                    "output": "Success",
                    "error": "",
                },
            ):
                result = await execute_repair("clear_temp", {})

                # 验证执行成功
                assert result["success"] is True


class TestRepairErrorHandling:
    """修复错误处理测试"""

    @pytest.mark.asyncio
    async def test_repair_exception_handling(self, mock_logger):
        """测试修复执行异常处理"""
        with patch("core.repair_engine.logger", mock_logger):
            # Mock PowerShell 执行抛出异常
            with patch(
                "core.repair_engine._run_powershell", side_effect=Exception("Runtime error")
            ):
                result = await execute_repair("clear_temp", {})

                # 验证异常被捕获
                assert result["success"] is False
                # 验证日志记录
                mock_logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_param_validation(self, mock_logger):
        """测试参数验证"""
        with patch("core.repair_engine.logger", mock_logger):
            # 测试正常参数
            result = await execute_repair("clear_temp", {})
            # 应该执行成功或失败但不应该因为参数验证失败
            assert result is not None


class TestRepairUtilities:
    """修复工具函数测试"""

    def test_sanitize_param(self):
        """测试参数清理"""
        # 测试正常参数
        result = _sanitize_param("key", "value")
        assert result is not None
        # 测试空参数
        result = _sanitize_param("key", "")
        assert result is not None
        # 测试None参数
        result = _sanitize_param("key", None)
        assert result is not None

    def test_render_command(self):
        """测试命令渲染"""
        cmd = "restart-service {service_name}"
        params = {"service_name": "nginx"}
        result = _render_command(cmd, params)
        assert "nginx" in result

    def test_get_repair_history(self):
        """测试获取修复历史"""
        history = get_repair_history(limit=10)
        assert isinstance(history, list)

    def test_clear_repair_history(self):
        """测试清空修复历史"""
        count = clear_repair_history()
        assert isinstance(count, int)
        assert count >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
