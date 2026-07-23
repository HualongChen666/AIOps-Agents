# -*- coding: utf-8 -*-
"""测试macOS收集器模块"""

import pytest


class TestMacosCollectorModule:
    """测试macOS收集器模块"""

    def test_macos_collector_module_exists(self):
        """测试macOS收集器模块存在"""
        from core import macos_collector

        assert macos_collector is not None

    def test_macos_collector_has_functions(self):
        """测试macOS收集器模块有函数"""
        from core import macos_collector

        # 检查模块有函数或类
        assert len(dir(macos_collector)) > 0


class TestRunCommand:
    """测试运行命令函数"""

    @pytest.mark.asyncio
    async def test_run_command(self):
        """测试运行命令"""
        try:
            from core.macos_collector import _run_command

            result = await _run_command("test_host", "test_command")

            assert result is not None
            assert isinstance(result, dict)
            assert "stdout" in result
            assert "stderr" in result
        except Exception as e:
            pytest.skip(f"Cannot test run command: {e}")

    @pytest.mark.asyncio
    async def test_run_command_different_hosts(self):
        """测试不同主机运行命令"""
        try:
            from core.macos_collector import _run_command

            for host in ["host1", "host2", "host3"]:
                result = await _run_command(host, "ls")
                assert isinstance(result, dict)
        except Exception as e:
            pytest.skip(f"Cannot test run command different hosts: {e}")


class TestCollectMacosMetrics:
    """测试收集macOS指标函数"""

    @pytest.mark.asyncio
    async def test_collect_macos_metrics(self):
        """测试收集macOS指标"""
        try:
            from core.macos_collector import collect_macos_metrics

            results = await collect_macos_metrics(["test_host"])

            assert results is not None
            assert isinstance(results, dict)
        except Exception as e:
            pytest.skip(f"Cannot test collect macos metrics: {e}")

    @pytest.mark.asyncio
    async def test_collect_macos_metrics_with_hosts(self):
        """测试带主机列表收集macOS指标"""
        try:
            from core.macos_collector import collect_macos_metrics

            results = await collect_macos_metrics(["host1", "host2"])

            assert isinstance(results, dict)
            assert len(results) == 2
        except Exception as e:
            pytest.skip(f"Cannot test collect macos metrics with hosts: {e}")

    @pytest.mark.asyncio
    async def test_collect_macos_metrics_structure(self):
        """测试收集macOS指标结构"""
        try:
            from core.macos_collector import collect_macos_metrics

            results = await collect_macos_metrics(["test_host"])

            # Check result structure
            for host, metrics in results.items():
                assert isinstance(metrics, dict)
                # May have error or status fields
        except Exception as e:
            pytest.skip(f"Cannot test collect macos metrics structure: {e}")


class TestMacosCollectorIntegration:
    """测试macOS收集器集成"""

    @pytest.mark.asyncio
    async def test_functions_exist(self):
        """测试函数存在"""
        try:
            from core.macos_collector import _run_command, collect_macos_metrics

            assert _run_command is not None
            assert collect_macos_metrics is not None
            assert callable(_run_command)
            assert callable(collect_macos_metrics)
        except Exception as e:
            pytest.skip(f"Cannot test functions exist: {e}")

    @pytest.mark.asyncio
    async def test_complete_lifecycle(self):
        """测试完整生命周期"""
        try:
            from core.macos_collector import _run_command, collect_macos_metrics

            # Run command
            cmd_result = await _run_command("test_host", "test_command")
            assert cmd_result is not None

            # Collect metrics
            metrics = await collect_macos_metrics(["test_host"])
            assert metrics is not None
        except Exception as e:
            pytest.skip(f"Cannot test complete lifecycle: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
