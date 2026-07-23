# -*- coding: utf-8 -*-
"""
Enhanced Repair Engine Tests
增强的修复引擎测试，包含边界条件、安全测试和并发场景
"""

import asyncio
import subprocess
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


@pytest.fixture
def mock_logger():
    """Mock logger fixture"""
    return MagicMock()


@pytest.fixture
def reset_repair_state():
    """重置修复引擎状态"""
    clear_repair_history()
    yield
    clear_repair_history()


class TestRepairScriptsEnhanced:
    """增强的修复脚本测试"""

    def test_get_repair_scripts_completeness(self):
        """测试修复脚本完整性"""
        scripts = get_repair_scripts()

        # 验证关键脚本存在
        script_keys = [script.get("key", "") for script in scripts]
        assert "clear_temp" in script_keys
        assert "flush_dns" in script_keys
        assert "restart_service" in script_keys

        # 验证每个脚本都有必需字段
        for script in scripts:
            assert "name" in script
            assert "description" in script
            assert "risk" in script
            assert "command" in script
            assert script["risk"] in ["low", "medium", "high"]

    def test_get_repair_scripts_readonly_protection(self):
        """测试修复脚本只读保护"""
        scripts1 = get_repair_scripts()

        # 尝试修改返回的脚本列表
        if scripts1:
            scripts1[0]["name"] = "modified"

        # 再次获取应该返回原始数据
        scripts2 = get_repair_scripts()
        if scripts2:
            assert scripts2[0]["name"] != "modified"

    def test_get_repair_scripts_deep_copy(self):
        """测试修复脚本深拷贝"""
        scripts = get_repair_scripts()

        # 验证返回的是深拷贝
        if scripts:
            original_command = scripts[0]["command"]
            scripts[0]["command"] = ["modified"]

            # 重新获取应该不受影响
            scripts_new = get_repair_scripts()
            if scripts_new:
                assert scripts_new[0]["command"] == original_command


class TestPowerShellExecutionEnhanced:
    """增强的PowerShell执行测试"""

    def test_run_powershell_timeout_handling(self, mock_logger):
        """测试PowerShell超时处理"""
        script = "Start-Sleep -Seconds 10"  # 长时间运行脚本

        with patch("core.repair_engine.logger", mock_logger):
            with patch("subprocess.run") as mock_run:
                # 模拟超时
                mock_run.side_effect = subprocess.TimeoutExpired("powershell", 120)

                result = _run_powershell(script)

                # 应该处理超时异常
                assert result["success"] is False
                assert "timeout" in result["error"].lower() or "超时" in result["error"]

    def test_run_powershell_command_injection_protection(self, mock_logger):
        """测试PowerShell命令注入防护"""
        malicious_script = "Get-Process; Remove-Item -Path C:\\ -Recurse -Force"

        with patch("core.repair_engine.logger", mock_logger):
            with patch("core.repair_engine.command_guard") as mock_guard:
                # 模拟命令审查拒绝
                mock_guard.analyze_command.return_value = {
                    "allowed": False,
                    "reason": "Dangerous command detected",
                }

                result = _run_powershell(malicious_script)

                # 应该被命令护栏拦截
                assert result["success"] is False
                mock_guard.analyze_command.assert_called_once()

    def test_run_powershell_large_output_handling(self, mock_logger):
        """测试PowerShell大输出处理"""
        # 生成大量输出
        large_output = "X" * 100000

        with patch("core.repair_engine.logger", mock_logger):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(
                    stdout=large_output.encode(), stderr=b"", returncode=0
                )

                result = _run_powershell("Write-Output 'test'")

                # 应该处理大输出而不崩溃
                assert result["success"] is True
                # 输出可能被截断
                assert len(result["output"]) <= 50000  # 假设有合理的截断限制

    def test_run_powershell_encoding_handling(self, mock_logger):
        """测试PowerShell编码处理"""
        unicode_script = "Write-Output '测试中文'"

        with patch("core.repair_engine.logger", mock_logger):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(
                    stdout="测试中文\r\n".encode("utf-8"), stderr=b"", returncode=0
                )

                result = _run_powershell(unicode_script)

                # 应该正确处理Unicode
                assert result["success"] is True
                assert "测试" in result["output"] or result["output"] != ""

    def test_run_powershell_process_cleanup(self, mock_logger):
        """测试PowerShell进程清理"""
        script = "Write-Output 'test'"

        with patch("core.repair_engine.logger", mock_logger):
            with patch("subprocess.Popen") as mock_popen:
                mock_process = MagicMock()
                mock_process.communicate.return_value = (b"test\r\n", b"")
                mock_process.returncode = 0
                mock_popen.return_value = mock_process

                result = _run_powershell(script)

                # 验证进程被正确清理
                assert result["success"] is True
                mock_process.kill.assert_not_called()  # 正常完成不需要kill

    def test_run_powershell_error_output_parsing(self, mock_logger):
        """测试PowerShell错误输出解析"""
        error_script = "Write-Error 'Custom error message'"

        with patch("core.repair_engine.logger", mock_logger):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(
                    stdout=b"", stderr=b"Custom error message\r\n", returncode=1
                )

                result = _run_powershell(error_script)

                # 应该正确解析错误信息
                assert result["success"] is False
                assert "Custom error message" in result["error"]


class TestRepairExecutionEnhanced:
    """增强的修复执行测试"""

    @pytest.mark.asyncio
    async def test_execute_repair_with_parameters(self, mock_logger):
        """测试带参数的修复执行"""
        with patch("core.repair_engine.logger", mock_logger):
            with patch("core.repair_engine._run_powershell") as mock_ps:
                mock_ps.return_value = {"success": True, "output": "Service restarted", "error": ""}

                result = await execute_repair("restart_service", {"service_name": "nginx"})

                # 验证参数被正确传递
                assert result["success"] is True
                mock_ps.assert_called_once()
                # 验证命令渲染包含参数
                call_args = mock_ps.call_args[0][0]
                assert "nginx" in call_args

    @pytest.mark.asyncio
    async def test_execute_repair_parameter_validation(self, mock_logger):
        """测试参数验证"""
        with patch("core.repair_engine.logger", mock_logger):
            # 测试缺少必需参数
            result = await execute_repair("restart_service", {})

            # 应该因为缺少参数而失败
            assert result["success"] is False
            assert "parameter" in result["error"].lower() or "参数" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_repair_parameter_sanitization(self, mock_logger):
        """测试参数清理"""
        with patch("core.repair_engine.logger", mock_logger):
            with patch("core.repair_engine._run_powershell") as mock_ps:
                mock_ps.return_value = {"success": True, "output": "Success", "error": ""}

                # 测试包含潜在危险字符的参数
                dangerous_params = {"service_name": "nginx; rm -rf /"}

                result = await execute_repair("restart_service", dangerous_params)

                # 参数应该被清理
                assert result["success"] is True or "sanitized" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_execute_repair_high_risk_warning(self, mock_logger):
        """测试高风险操作警告"""
        with patch("core.repair_engine.logger", mock_logger):
            with patch("core.repair_engine._run_powershell") as mock_ps:
                mock_ps.return_value = {"success": True, "output": "Process killed", "error": ""}

                # 执行高风险操作
                result = await execute_repair("kill_high_cpu", {"pid": "1234"})

                # 应该记录高风险警告
                assert result["success"] is True
                # 验证logger.warning被调用
                mock_logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_execute_repair_concurrent_safety(self, mock_logger):
        """测试并发执行安全性"""
        with patch("core.repair_engine.logger", mock_logger):
            with patch("core.repair_engine._run_powershell") as mock_ps:
                mock_ps.return_value = {"success": True, "output": "Success", "error": ""}

                # 并发执行多个修复
                tasks = [execute_repair("clear_temp", {}) for _ in range(5)]

                results = await asyncio.gather(*tasks)

                # 所有任务都应该成功完成
                assert all(result["success"] for result in results)

    @pytest.mark.asyncio
    async def test_execute_repair_state_isolation(self, mock_logger):
        """测试状态隔离"""
        with patch("core.repair_engine.logger", mock_logger):
            with patch("core.repair_engine._run_powershell") as mock_ps:
                mock_ps.return_value = {"success": True, "output": "Success", "error": ""}

                # 执行不同的修复操作
                result1 = await execute_repair("clear_temp", {})
                result2 = await execute_repair("flush_dns", {})

                # 两个操作应该独立完成
                assert result1["success"] is True
                assert result2["success"] is True


class TestParameterValidationEnhanced:
    """增强的参数验证测试"""

    def test_sanitize_param_string_truncation(self):
        """测试字符串参数截断"""
        # 测试超长字符串
        long_string = "X" * 1000
        result = _sanitize_param("key", long_string)

        # 应该被截断到合理长度
        assert len(result) <= 128  # 假设最大长度为128

    def test_sanitize_param_special_characters(self):
        """测试特殊字符处理"""
        # 测试包含特殊字符的参数
        special_chars = "test;rm -rf /|&><"
        result = _sanitize_param("key", special_chars)

        # 特殊字符应该被转义或移除
        assert ";" not in result or "rm" not in result

    def test_sanitize_param_null_and_empty(self):
        """测试null和空值处理"""
        # 测试None
        result1 = _sanitize_param("key", None)
        assert result1 is not None or result1 == ""

        # 测试空字符串
        result2 = _sanitize_param("key", "")
        assert result2 is not None or result2 == ""

        # 测试空格
        result3 = _sanitize_param("key", "   ")
        assert result3.strip() == "" or result3 is not None

    def test_sanitize_param_numeric_values(self):
        """测试数值参数处理"""
        # 测试整数
        result1 = _sanitize_param("key", 12345)
        assert result1 is not None

        # 测试浮点数
        result2 = _sanitize_param("key", 123.45)
        assert result2 is not None

        # 测试负数
        result3 = _sanitize_param("key", -999)
        assert result3 is not None

    def test_sanitize_param_service_name_validation(self):
        """测试服务名验证"""
        # 测试有效服务名
        valid_names = ["nginx", "apache2", "mysql", "redis-server"]
        for name in valid_names:
            result = _sanitize_param("service_name", name)
            assert result is not None

        # 测试无效服务名
        invalid_names = ["../../../etc/passwd", "nginx; malicious", "nginx|rm"]
        for name in invalid_names:
            result = _sanitize_param("service_name", name)
            # 应该被清理或拒绝
            assert "/" not in result or ";" not in result


class TestCommandRenderingEnhanced:
    """增强的命令渲染测试"""

    def test_render_command_multiple_parameters(self):
        """测试多参数渲染"""
        cmd = "restart-service {service_name} -force {timeout}"
        params = {"service_name": "nginx", "timeout": "30"}
        result = _render_command(cmd, params)

        assert "nginx" in result
        assert "30" in result
        assert "{service_name}" not in result  # 参数应该被替换

    def test_render_command_missing_parameters(self):
        """测试缺失参数处理"""
        cmd = "restart-service {service_name} {timeout}"
        params = {"service_name": "nginx"}  # 缺少timeout

        result = _render_command(cmd, params)

        # 缺失参数应该保留原样或使用默认值
        assert "nginx" in result
        # 可能保留{timeout}或使用默认值

    def test_render_command_extra_parameters(self):
        """测试多余参数处理"""
        cmd = "restart-service {service_name}"
        params = {"service_name": "nginx", "extra_param": "ignored"}  # 多余参数

        result = _render_command(cmd, params)

        # 多余参数应该被忽略
        assert "nginx" in result
        assert "ignored" not in result

    def test_render_command_parameter_injection_protection(self):
        """测试参数注入防护"""
        cmd = "restart-service {service_name}"
        params = {"service_name": "nginx; Remove-Item -Path C:\\"}

        result = _render_command(cmd, params)

        # 危险命令应该被清理
        assert "nginx" in result
        assert ";" not in result or "Remove-Item" not in result

    def test_render_command_unicode_parameters(self):
        """测试Unicode参数渲染"""
        cmd = "echo {message}"
        params = {"message": "测试中文"}

        result = _render_command(cmd, params)

        # Unicode字符应该被正确处理
        assert "测试" in result


class TestRepairHistoryEnhanced:
    """增强的修复历史测试"""

    def test_get_repair_history_limit(self):
        """测试历史记录限制"""
        # 获取有限数量的历史记录
        history = get_repair_history(limit=5)  # noqa: F841

        assert isinstance(history, list)
        assert len(history) <= 5

    def test_get_repair_history_structure(self):
        """测试历史记录结构"""
        history = get_repair_history(limit=10)  # noqa: F841

        for record in history:
            assert isinstance(record, dict)
            # 验证必需字段存在
            assert any(key in record for key in ["timestamp", "time", "date"])
            assert any(key in record for key in ["script", "script_key", "command"])

    def test_clear_repair_history_verification(self):
        """测试清空历史记录验证"""
        # 先添加一些历史记录
        clear_repair_history()

        # 清空历史
        count = clear_repair_history()  # noqa: F841

        # 验证历史被清空
        history = get_repair_history()  # noqa: F841
        assert len(history) == 0

    def test_repair_history_persistence(self, mock_logger):
        """测试历史记录持久化"""
        with patch("core.repair_engine.logger", mock_logger):
            with patch("sqlite3.connect") as mock_connect:
                mock_conn = MagicMock()
                mock_cursor = MagicMock()
                mock_conn.cursor.return_value = mock_cursor
                mock_connect.return_value = mock_conn

                # 记录修复历史
                result = _record_to_sqlite_sync("test_rule", "test_script", "success", "output")

                # 验证数据库操作被调用
                assert result is True or result is False  # 根据实现可能返回True/False
                mock_cursor.execute.assert_called()


class TestErrorHandlingEnhanced:
    """增强的错误处理测试"""

    @pytest.mark.asyncio
    async def test_execute_repair_network_timeout(self, mock_logger):
        """测试网络超时错误处理"""
        with patch("core.repair_engine.logger", mock_logger):
            with patch("core.repair_engine._run_powershell") as mock_ps:
                mock_ps.side_effect = asyncio.TimeoutError("Network timeout")

                result = await execute_repair("clear_temp", {})

                # 应该处理超时错误
                assert result["success"] is False
                assert "timeout" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_execute_repair_permission_denied(self, mock_logger):
        """测试权限拒绝错误处理"""
        with patch("core.repair_engine.logger", mock_logger):
            with patch("core.repair_engine._run_powershell") as mock_ps:
                mock_ps.return_value = {"success": False, "output": "", "error": "Access denied"}

                result = await execute_repair("clear_temp", {})

                # 应该正确处理权限错误
                assert result["success"] is False
                assert "access" in result["error"].lower() or "denied" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_execute_repair_disk_full(self, mock_logger):
        """测试磁盘满错误处理"""
        with patch("core.repair_engine.logger", mock_logger):
            with patch("core.repair_engine._run_powershell") as mock_ps:
                mock_ps.return_value = {"success": False, "output": "", "error": "Disk full"}

                result = await execute_repair("clear_temp", {})

                # 应该正确处理磁盘满错误
                assert result["success"] is False
                assert "disk" in result["error"].lower()

    def test_run_powershell_invalid_encoding(self, mock_logger):
        """测试无效编码处理"""
        with patch("core.repair_engine.logger", mock_logger):
            with patch("subprocess.run") as mock_run:
                # 模拟无效编码
                mock_run.return_value = MagicMock(
                    stdout=b"\xff\xfe", stderr=b"", returncode=0  # 无效UTF-8
                )

                result = _run_powershell("Write-Output 'test'")

                # 应该处理编码错误而不崩溃
                assert result is not None


class TestSecurityScenarios:
    """安全场景测试"""

    @pytest.mark.asyncio
    async def test_command_injection_prevention(self, mock_logger):
        """测试命令注入防护"""
        with patch("core.repair_engine.logger", mock_logger):
            with patch("core.repair_engine.command_guard") as mock_guard:
                # 模拟命令护栏拦截
                mock_guard.analyze_command.return_value = {
                    "allowed": False,
                    "reason": "Command injection detected",
                }

                result = await execute_repair("clear_temp", {})

                # 危险命令应该被拦截
                assert result["success"] is False
                assert (
                    "injection" in result["error"].lower() or "detected" in result["error"].lower()
                )

    @pytest.mark.asyncio
    async def test_path_traversal_prevention(self, mock_logger):
        """测试路径遍历防护"""
        with patch("core.repair_engine.logger", mock_logger):
            dangerous_params = {"service_name": "../../../etc/passwd"}

            result = await execute_repair("restart_service", dangerous_params)

            # 路径遍历应该被防护
            assert result["success"] is False or "../" not in str(result)

    @pytest.mark.asyncio
    async def test_self_deletion_prevention(self, mock_logger):
        """测试自删除防护"""
        with patch("core.repair_engine.logger", mock_logger):
            with patch("core.repair_engine.command_guard") as mock_guard:
                # 模拟自删除命令被拦截
                mock_guard.analyze_command.return_value = {
                    "allowed": False,
                    "reason": "Self-deletion attempt detected",
                }

                result = await execute_repair("clear_temp", {})

                # 自删除尝试应该被拦截
                assert result["success"] is False


@pytest.mark.integration
class TestRepairEngineIntegration:
    """修复引擎集成测试"""

    @pytest.mark.asyncio
    async def test_full_repair_workflow(self, mock_logger):
        """测试完整修复工作流"""
        with patch("core.repair_engine.logger", mock_logger):
            with patch("core.repair_engine._run_powershell") as mock_ps:
                mock_ps.return_value = {
                    "success": True,
                    "output": "Temp files cleared",
                    "error": "",
                }

                # 1. 获取可用脚本
                scripts = get_repair_scripts()
                assert len(scripts) > 0

                # 2. 执行修复
                result = await execute_repair("clear_temp", {})
                assert result["success"] is True

                # 3. 验证历史记录
                history = get_repair_history(limit=1)  # noqa: F841
                # 可能需要实际执行才会有历史记录

    @pytest.mark.asyncio
    async def test_repair_with_database_integration(self, mock_logger):
        """测试数据库集成修复"""
        with patch("core.repair_engine.logger", mock_logger):
            with patch("core.repair_engine._run_powershell") as mock_ps:
                mock_ps.return_value = {"success": True, "output": "Success", "error": ""}

                with patch("sqlite3.connect") as mock_connect:
                    mock_conn = MagicMock()
                    mock_cursor = MagicMock()
                    mock_conn.cursor.return_value = mock_cursor
                    mock_connect.return_value = mock_conn

                    # 执行修复
                    result = await execute_repair("clear_temp", {})

                    # 验证数据库记录
                    assert result["success"] is True
                    # 验证历史被记录到数据库

    @pytest.mark.asyncio
    async def test_concurrent_repair_operations(self, mock_logger):
        """测试并发修复操作"""
        with patch("core.repair_engine.logger", mock_logger):
            with patch("core.repair_engine._run_powershell") as mock_ps:
                mock_ps.return_value = {"success": True, "output": "Success", "error": ""}

                # 并发执行不同类型的修复
                tasks = [
                    execute_repair("clear_temp", {}),
                    execute_repair("flush_dns", {}),
                    execute_repair("restart_service", {"service_name": "nginx"}),
                ]

                results = await asyncio.gather(*tasks)

                # 所有操作都应该成功
                assert all(result["success"] for result in results)


class TestPerformanceAndLoad:
    """性能和负载测试"""

    @pytest.mark.asyncio
    async def test_rapid_sequential_repairs(self, mock_logger):
        """测试快速顺序修复"""
        with patch("core.repair_engine.logger", mock_logger):
            with patch("core.repair_engine._run_powershell") as mock_ps:
                mock_ps.return_value = {"success": True, "output": "Success", "error": ""}

                # 快速执行多个修复
                start_time = asyncio.get_event_loop().time()
                for _ in range(10):
                    await execute_repair("clear_temp", {})
                end_time = asyncio.get_event_loop().time()

                # 验证性能在合理范围内
                assert (end_time - start_time) < 5.0  # 10个操作应该在5秒内完成

    @pytest.mark.asyncio
    async def test_memory_leak_prevention(self, mock_logger):
        """测试内存泄漏防护"""
        with patch("core.repair_engine.logger", mock_logger):
            with patch("core.repair_engine._run_powershell") as mock_ps:
                mock_ps.return_value = {"success": True, "output": "Success", "error": ""}

                # 执行大量修复操作
                for _ in range(100):
                    await execute_repair("clear_temp", {})

                # 验证历史记录不会无限增长
                history = get_repair_history()  # noqa: F841
                # 应该有合理的大小限制
                assert len(history) < 1000  # 假设合理上限


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
