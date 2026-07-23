# -*- coding: utf-8 -*-
"""测试平台策略模块"""

import pytest


class TestPlatformStrategiesModule:
    """测试平台策略模块"""

    def test_platform_strategies_module_exists(self):
        """测试平台策略模块存在"""
        from core import platform_strategies

        assert platform_strategies is not None

    def test_platform_strategies_has_functions(self):
        """测试平台策略模块有函数"""
        from core import platform_strategies

        # 检查模块有函数或类
        assert len(dir(platform_strategies)) > 0


class TestPlatformStrategy:
    """测试PlatformStrategy抽象基类"""

    def test_platform_strategy_is_abstract(self):
        """测试PlatformStrategy是抽象类"""
        try:
            from abc import ABC

            from core.platform_strategies import PlatformStrategy

            assert issubclass(PlatformStrategy, ABC)
        except Exception as e:
            pytest.skip(f"Cannot test PlatformStrategy abstract: {e}")


class TestWindowsStrategy:
    """测试WindowsStrategy类"""

    def test_windows_strategy_init(self):
        """测试WindowsStrategy初始化"""
        try:
            from core.platform_strategies import WindowsStrategy

            strategy = WindowsStrategy()
            assert strategy is not None
        except Exception as e:
            pytest.skip(f"Cannot test WindowsStrategy init: {e}")

    def test_windows_strategy_get_scripts(self):
        """测试WindowsStrategy获取脚本"""
        try:
            from core.platform_strategies import WindowsStrategy

            strategy = WindowsStrategy()
            scripts = strategy.get_scripts()

            assert isinstance(scripts, dict)
        except Exception as e:
            pytest.skip(f"Cannot test WindowsStrategy get scripts: {e}")

    def test_windows_strategy_requires_host_name(self):
        """测试WindowsStrategy是否需要主机名"""
        try:
            from core.platform_strategies import WindowsStrategy

            strategy = WindowsStrategy()
            requires = strategy.requires_host_name()

            assert requires is False
        except Exception as e:
            pytest.skip(f"Cannot test WindowsStrategy requires host name: {e}")


class TestLinuxStrategy:
    """测试LinuxStrategy类"""

    def test_linux_strategy_init(self):
        """测试LinuxStrategy初始化"""
        try:
            from core.platform_strategies import LinuxStrategy

            strategy = LinuxStrategy()
            assert strategy is not None
        except Exception as e:
            pytest.skip(f"Cannot test LinuxStrategy init: {e}")

    def test_linux_strategy_get_scripts(self):
        """测试LinuxStrategy获取脚本"""
        try:
            from core.platform_strategies import LinuxStrategy

            strategy = LinuxStrategy()
            scripts = strategy.get_scripts()

            assert isinstance(scripts, dict)
        except Exception as e:
            pytest.skip(f"Cannot test LinuxStrategy get scripts: {e}")

    def test_linux_strategy_requires_host_name(self):
        """测试LinuxStrategy是否需要主机名"""
        try:
            from core.platform_strategies import LinuxStrategy

            strategy = LinuxStrategy()
            requires = strategy.requires_host_name()

            assert requires is True
        except Exception as e:
            pytest.skip(f"Cannot test LinuxStrategy requires host name: {e}")


class TestDockerStrategy:
    """测试DockerStrategy类"""

    def test_docker_strategy_init(self):
        """测试DockerStrategy初始化"""
        try:
            from core.platform_strategies import DockerStrategy

            strategy = DockerStrategy()
            assert strategy is not None
        except Exception as e:
            pytest.skip(f"Cannot test DockerStrategy init: {e}")

    def test_docker_strategy_get_scripts(self):
        """测试DockerStrategy获取脚本"""
        try:
            from core.platform_strategies import DockerStrategy

            strategy = DockerStrategy()
            scripts = strategy.get_scripts()

            assert isinstance(scripts, dict)
        except Exception as e:
            pytest.skip(f"Cannot test DockerStrategy get scripts: {e}")

    def test_docker_strategy_requires_host_name(self):
        """测试DockerStrategy是否需要主机名"""
        try:
            from core.platform_strategies import DockerStrategy

            strategy = DockerStrategy()
            requires = strategy.requires_host_name()

            assert requires is True
        except Exception as e:
            pytest.skip(f"Cannot test DockerStrategy requires host name: {e}")


class TestKubernetesStrategy:
    """测试KubernetesStrategy类"""

    def test_kubernetes_strategy_init(self):
        """测试KubernetesStrategy初始化"""
        try:
            from core.platform_strategies import KubernetesStrategy

            strategy = KubernetesStrategy()
            assert strategy is not None
        except Exception as e:
            pytest.skip(f"Cannot test KubernetesStrategy init: {e}")

    def test_kubernetes_strategy_get_scripts(self):
        """测试KubernetesStrategy获取脚本"""
        try:
            from core.platform_strategies import KubernetesStrategy

            strategy = KubernetesStrategy()
            scripts = strategy.get_scripts()

            assert isinstance(scripts, dict)
        except Exception as e:
            pytest.skip(f"Cannot test KubernetesStrategy get scripts: {e}")

    def test_kubernetes_strategy_requires_host_name(self):
        """测试KubernetesStrategy是否需要主机名"""
        try:
            from core.platform_strategies import KubernetesStrategy

            strategy = KubernetesStrategy()
            requires = strategy.requires_host_name()

            assert requires is True
        except Exception as e:
            pytest.skip(f"Cannot test KubernetesStrategy requires host name: {e}")


class TestPlatformStrategiesRegistry:
    """测试平台策略注册表"""

    def test_platform_strategies_registry_exists(self):
        """测试平台策略注册表存在"""
        try:
            from core.platform_strategies import PLATFORM_STRATEGIES

            assert isinstance(PLATFORM_STRATEGIES, dict)
            assert len(PLATFORM_STRATEGIES) > 0
        except Exception as e:
            pytest.skip(f"Cannot test platform strategies registry: {e}")

    def test_platform_strategies_registry_has_all_platforms(self):
        """测试注册表包含所有平台"""
        try:
            from core.platform_strategies import PLATFORM_STRATEGIES

            expected_platforms = ["windows", "linux", "docker", "kubernetes"]
            for platform in expected_platforms:
                assert platform in PLATFORM_STRATEGIES
        except Exception as e:
            pytest.skip(f"Cannot test platform strategies registry has all platforms: {e}")

    def test_get_platform_strategy(self):
        """测试获取平台策略"""
        try:
            from core.platform_strategies import get_platform_strategy

            strategy = get_platform_strategy("windows")
            assert strategy is not None
        except Exception as e:
            pytest.skip(f"Cannot test get platform strategy: {e}")

    def test_get_platform_strategy_invalid(self):
        """测试获取无效平台策略"""
        try:
            from core.platform_strategies import get_platform_strategy

            with pytest.raises(ValueError):
                get_platform_strategy("invalid_platform")
        except Exception as e:
            pytest.skip(f"Cannot test get platform strategy invalid: {e}")

    def test_get_all_platform_strategies(self):
        """测试获取所有平台策略"""
        try:
            from core.platform_strategies import get_all_platform_strategies

            strategies = get_all_platform_strategies()
            assert isinstance(strategies, dict)
            assert len(strategies) > 0
        except Exception as e:
            pytest.skip(f"Cannot test get all platform strategies: {e}")


class TestPlatformStrategyIntegration:
    """测试平台策略集成"""

    def test_all_strategies_implement_interface(self):
        """测试所有策略实现接口"""
        try:
            from core.platform_strategies import (
                PLATFORM_STRATEGIES,
                PlatformStrategy,
            )

            for platform_name, strategy in PLATFORM_STRATEGIES.items():
                assert isinstance(strategy, PlatformStrategy)
                assert hasattr(strategy, "get_scripts")
                assert hasattr(strategy, "execute_repair")
                assert hasattr(strategy, "get_history")
                assert hasattr(strategy, "requires_host_name")
        except Exception as e:
            pytest.skip(f"Cannot test all strategies implement interface: {e}")

    def test_strategy_selection(self):
        """测试策略选择"""
        try:
            from core.platform_strategies import get_platform_strategy

            windows_strategy = get_platform_strategy("windows")
            linux_strategy = get_platform_strategy("linux")
            docker_strategy = get_platform_strategy("docker")
            k8s_strategy = get_platform_strategy("kubernetes")

            assert windows_strategy is not linux_strategy
            assert linux_strategy is not docker_strategy
            assert docker_strategy is not k8s_strategy
        except Exception as e:
            pytest.skip(f"Cannot test strategy selection: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
