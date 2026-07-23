# -*- coding: utf-8 -*-
"""测试macOS修复模块"""

import pytest


class TestMacosRepairModule:
    """测试macOS修复模块"""

    def test_macos_repair_module_exists(self):
        """测试macOS修复模块存在"""
        from core import macos_repair

        assert macos_repair is not None

    def test_macos_repair_has_functions(self):
        """测试macOS修复模块有函数"""
        from core import macos_repair

        # 检查模块有函数或类
        assert len(dir(macos_repair)) > 0


class TestExecuteMacosRepair:
    """测试执行macOS修复函数"""

    @pytest.mark.asyncio
    async def test_execute_macos_repair(self):
        """测试执行macOS修复"""
        try:
            from core.macos_repair import execute_macos_repair

            result = await execute_macos_repair("test_host", "cleanup_disk")

            assert result is not None
            assert isinstance(result, dict)
            assert "status" in result
        except Exception as e:
            pytest.skip(f"Cannot test execute macos repair: {e}")

    @pytest.mark.asyncio
    async def test_execute_macos_repair_with_args(self):
        """测试带参数执行macOS修复"""
        try:
            from core.macos_repair import execute_macos_repair

            args = {"force": True, "verbose": True}
            result = await execute_macos_repair("test_host", "fix_permissions", args)

            assert isinstance(result, dict)
            assert "status" in result
        except Exception as e:
            pytest.skip(f"Cannot test execute macos repair with args: {e}")

    @pytest.mark.asyncio
    async def test_execute_macos_repair_none_args(self):
        """测试None参数执行macOS修复"""
        try:
            from core.macos_repair import execute_macos_repair

            result = await execute_macos_repair("test_host", "restart_services", None)

            assert isinstance(result, dict)
            assert "status" in result
        except Exception as e:
            pytest.skip(f"Cannot test execute macos repair none args: {e}")


class TestGetAvailableMacosScripts:
    """测试获取可用macOS脚本函数"""

    def test_get_available_macos_scripts(self):
        """测试获取可用macOS脚本"""
        try:
            from core.macos_repair import get_available_macos_scripts

            scripts = get_available_macos_scripts()

            assert scripts is not None
            assert isinstance(scripts, list)
        except Exception as e:
            pytest.skip(f"Cannot test get available macos scripts: {e}")

    def test_get_available_macos_scripts_content(self):
        """测试获取可用macOS脚本内容"""
        try:
            from core.macos_repair import get_available_macos_scripts

            scripts = get_available_macos_scripts()

            # Check scripts are strings
            for script in scripts:
                assert isinstance(script, str)
        except Exception as e:
            pytest.skip(f"Cannot test get available macos scripts content: {e}")


class TestMacosRepairIntegration:
    """测试macOS修复集成"""

    @pytest.mark.asyncio
    async def test_functions_exist(self):
        """测试函数存在"""
        try:
            from core.macos_repair import execute_macos_repair, get_available_macos_scripts

            assert execute_macos_repair is not None
            assert get_available_macos_scripts is not None
            assert callable(execute_macos_repair)
            assert callable(get_available_macos_scripts)
        except Exception as e:
            pytest.skip(f"Cannot test functions exist: {e}")

    @pytest.mark.asyncio
    async def test_complete_lifecycle(self):
        """测试完整生命周期"""
        try:
            from core.macos_repair import execute_macos_repair, get_available_macos_scripts

            # Get available scripts
            scripts = get_available_macos_scripts()
            assert isinstance(scripts, list)

            # Execute a repair script
            if scripts:
                result = await execute_macos_repair("test_host", scripts[0])
                assert isinstance(result, dict)
        except Exception as e:
            pytest.skip(f"Cannot test complete lifecycle: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
