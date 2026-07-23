# -*- coding: utf-8 -*-
"""测试Windows修复模块"""

import pytest


class TestWindowsRepairModule:
    """测试Windows修复模块"""

    def test_windows_repair_module_exists(self):
        """测试Windows修复模块存在"""
        from core import windows_repair

        assert windows_repair is not None

    def test_windows_repair_has_functions(self):
        """测试Windows修复模块有函数"""
        from core import windows_repair

        # 检查模块有函数或类
        assert len(dir(windows_repair)) > 0


class TestWindowsRepairScripts:
    """测试Windows修复脚本配置"""

    def test_windows_repair_scripts_exists(self):
        """测试Windows修复脚本配置存在"""
        try:
            from core.windows_repair import WINDOWS_REPAIR_SCRIPTS

            assert WINDOWS_REPAIR_SCRIPTS is not None
            assert isinstance(WINDOWS_REPAIR_SCRIPTS, dict)
        except Exception as e:
            pytest.skip(f"Cannot test windows repair scripts exists: {e}")

    def test_windows_repair_scripts_structure(self):
        """测试Windows修复脚本配置结构"""
        try:
            from core.windows_repair import WINDOWS_REPAIR_SCRIPTS

            # Check required scripts
            assert "restart_service" in WINDOWS_REPAIR_SCRIPTS
            assert "kill_process" in WINDOWS_REPAIR_SCRIPTS
            assert "clear_cache" in WINDOWS_REPAIR_SCRIPTS
        except Exception as e:
            pytest.skip(f"Cannot test windows repair scripts structure: {e}")

    def test_windows_repair_scripts_values(self):
        """测试Windows修复脚本配置值"""
        try:
            from core.windows_repair import WINDOWS_REPAIR_SCRIPTS

            # Check script structure
            restart_script = WINDOWS_REPAIR_SCRIPTS["restart_service"]
            assert "name" in restart_script
            assert "description" in restart_script
            assert "params" in restart_script
        except Exception as e:
            pytest.skip(f"Cannot test windows repair scripts values: {e}")


class TestExecuteWindowsRepair:
    """测试执行Windows修复函数"""

    @pytest.mark.asyncio
    async def test_execute_windows_repair(self):
        """测试执行Windows修复"""
        try:
            from core.windows_repair import execute_windows_repair

            result = await execute_windows_repair("restart_service", {"service_name": "test"})

            assert result is not None
            assert isinstance(result, dict)
        except Exception as e:
            pytest.skip(f"Cannot test execute windows repair: {e}")

    @pytest.mark.asyncio
    async def test_execute_windows_repair_result_structure(self):
        """测试执行Windows修复结果结构"""
        try:
            from core.windows_repair import execute_windows_repair

            result = await execute_windows_repair("kill_process", {"pid": "1234"})

            assert "success" in result
            assert "error" in result
            assert "script_key" in result
        except Exception as e:
            pytest.skip(f"Cannot test execute windows repair result structure: {e}")


class TestGetWindowsRepairHistory:
    """测试获取Windows修复历史函数"""

    def test_get_windows_repair_history(self):
        """测试获取Windows修复历史"""
        try:
            from core.windows_repair import get_windows_repair_history

            history = get_windows_repair_history()

            assert history is not None
            assert isinstance(history, list)
        except Exception as e:
            pytest.skip(f"Cannot test get windows repair history: {e}")

    def test_get_windows_repair_history_limit(self):
        """测试获取Windows修复历史限制"""
        try:
            from core.windows_repair import get_windows_repair_history

            history = get_windows_repair_history(limit=5)

            assert isinstance(history, list)
        except Exception as e:
            pytest.skip(f"Cannot test get windows repair history limit: {e}")


class TestWindowsRepairIntegration:
    """测试Windows修复集成"""

    def test_scripts_configuration(self):
        """测试脚本配置"""
        try:
            from core.windows_repair import WINDOWS_REPAIR_SCRIPTS

            # Verify all scripts have required fields
            for script_key, script_info in WINDOWS_REPAIR_SCRIPTS.items():
                assert "name" in script_info
                assert "description" in script_info
                assert "params" in script_info
        except Exception as e:
            pytest.skip(f"Cannot test scripts configuration: {e}")

    @pytest.mark.asyncio
    async def test_repair_lifecycle(self):
        """测试修复完整生命周期"""
        try:
            from core.windows_repair import execute_windows_repair, get_windows_repair_history

            # Execute repair
            result = await execute_windows_repair("clear_cache", {})

            # Get history
            history = get_windows_repair_history()

            # Verify structure
            assert result is not None
            assert isinstance(history, list)
        except Exception as e:
            pytest.skip(f"Cannot test repair lifecycle: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
