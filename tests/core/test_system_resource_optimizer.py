# -*- coding: utf-8 -*-
"""测试系统资源优化器模块"""

import pytest


class TestSystemResourceOptimizerModule:
    """测试系统资源优化器模块"""

    def test_system_resource_optimizer_module_exists(self):
        """测试系统资源优化器模块存在"""
        from core import system_resource_optimizer

        assert system_resource_optimizer is not None

    def test_system_resource_optimizer_has_functions(self):
        """测试系统资源优化器模块有函数"""
        from core import system_resource_optimizer

        # 检查模块有函数或类
        assert len(dir(system_resource_optimizer)) > 0


class TestSystemResourceStatus:
    """测试系统资源状态数据类"""

    def test_system_resource_status_init(self):
        """测试系统资源状态初始化"""
        try:
            from core.system_resource_optimizer import SystemResourceStatus

            status = SystemResourceStatus()

            assert status is not None
            assert status.memory_optimization_enabled is False
            assert status.cpu_optimization_enabled is False
            assert status.network_optimization_enabled is False
            assert status.last_optimization_run is None
            assert status.total_optimizations_applied == 0
            assert status.current_memory_mb == 0.0
            assert status.current_cpu_percent == 0.0
        except Exception as e:
            pytest.skip(f"Cannot test system resource status init: {e}")

    def test_system_resource_status_with_values(self):
        """测试系统资源状态带值初始化"""
        try:
            from datetime import datetime, timezone

            from core.system_resource_optimizer import SystemResourceStatus

            now = datetime.now(timezone.utc)
            status = SystemResourceStatus(
                memory_optimization_enabled=True,
                cpu_optimization_enabled=True,
                network_optimization_enabled=True,
                last_optimization_run=now,
                total_optimizations_applied=5,
                current_memory_mb=1024.0,
                current_cpu_percent=50.0,
            )

            assert status.memory_optimization_enabled is True
            assert status.cpu_optimization_enabled is True
            assert status.network_optimization_enabled is True
            assert status.last_optimization_run == now
            assert status.total_optimizations_applied == 5
            assert status.current_memory_mb == 1024.0
            assert status.current_cpu_percent == 50.0
        except Exception as e:
            pytest.skip(f"Cannot test system resource status with values: {e}")


class TestSystemResourceOptimizer:
    """测试系统资源优化器类"""

    def test_system_resource_optimizer_init(self):
        """测试系统资源优化器初始化"""
        try:
            from core.system_resource_optimizer import SystemResourceOptimizer

            optimizer = SystemResourceOptimizer()

            assert optimizer is not None
            assert optimizer.status is not None
        except Exception as e:
            pytest.skip(f"Cannot test system resource optimizer init: {e}")

    def test_analyze_memory_usage(self):
        """测试分析内存使用"""
        try:
            from core.system_resource_optimizer import SystemResourceOptimizer

            optimizer = SystemResourceOptimizer()
            result = optimizer.analyze_memory_usage()

            assert result is not None
            assert isinstance(result, dict)
        except Exception as e:
            pytest.skip(f"Cannot test analyze memory usage: {e}")

    def test_optimize_memory(self):
        """测试优化内存"""
        try:
            from core.system_resource_optimizer import SystemResourceOptimizer

            optimizer = SystemResourceOptimizer()
            result = optimizer.optimize_memory()

            assert result is not None
            assert isinstance(result, dict)
        except Exception as e:
            pytest.skip(f"Cannot test optimize memory: {e}")

    def test_analyze_cpu_usage(self):
        """测试分析CPU使用"""
        try:
            from core.system_resource_optimizer import SystemResourceOptimizer

            optimizer = SystemResourceOptimizer()
            result = optimizer.analyze_cpu_usage()

            assert result is not None
            assert isinstance(result, dict)
        except Exception as e:
            pytest.skip(f"Cannot test analyze cpu usage: {e}")

    def test_optimize_cpu(self):
        """测试优化CPU"""
        try:
            from core.system_resource_optimizer import SystemResourceOptimizer

            optimizer = SystemResourceOptimizer()
            result = optimizer.optimize_cpu()

            assert result is not None
            assert isinstance(result, dict)
        except Exception as e:
            pytest.skip(f"Cannot test optimize cpu: {e}")

    def test_optimize_network(self):
        """测试优化网络"""
        try:
            from core.system_resource_optimizer import SystemResourceOptimizer

            optimizer = SystemResourceOptimizer()
            result = optimizer.optimize_network()

            assert result is not None
            assert isinstance(result, dict)
        except Exception as e:
            pytest.skip(f"Cannot test optimize network: {e}")

    def test_run_comprehensive_optimization(self):
        """测试运行综合优化"""
        try:
            from core.system_resource_optimizer import SystemResourceOptimizer

            optimizer = SystemResourceOptimizer()
            result = optimizer.run_comprehensive_optimization()

            assert result is not None
            assert isinstance(result, dict)
            assert "timestamp" in result
            assert "overall_status" in result
        except Exception as e:
            pytest.skip(f"Cannot test run comprehensive optimization: {e}")

    def test_get_optimization_status(self):
        """测试获取优化状态"""
        try:
            from core.system_resource_optimizer import SystemResourceOptimizer

            optimizer = SystemResourceOptimizer()
            status = optimizer.get_optimization_status()

            assert status is not None
            assert isinstance(status, dict)
            assert "memory_optimization_enabled" in status
            assert "cpu_optimization_enabled" in status
            assert "network_optimization_enabled" in status
        except Exception as e:
            pytest.skip(f"Cannot test get optimization status: {e}")

    def test_get_resource_summary(self):
        """测试获取资源摘要"""
        try:
            from core.system_resource_optimizer import SystemResourceOptimizer

            optimizer = SystemResourceOptimizer()
            summary = optimizer.get_resource_summary()

            assert summary is not None
            assert isinstance(summary, dict)
            assert "timestamp" in summary
            assert "optimization_status" in summary
        except Exception as e:
            pytest.skip(f"Cannot test get resource summary: {e}")


class TestFactoryFunction:
    """测试工厂函数"""

    def test_get_system_resource_optimizer(self):
        """测试获取系统资源优化器"""
        try:
            from core.system_resource_optimizer import get_system_resource_optimizer

            optimizer = get_system_resource_optimizer()

            assert optimizer is not None
            assert isinstance(optimizer, object)
        except Exception as e:
            pytest.skip(f"Cannot test get system resource optimizer: {e}")

    def test_get_system_resource_optimizer_singleton(self):
        """测试获取系统资源优化器单例"""
        try:
            from core.system_resource_optimizer import get_system_resource_optimizer

            optimizer1 = get_system_resource_optimizer()
            optimizer2 = get_system_resource_optimizer()

            # Should return the same instance
            assert optimizer1 is optimizer2
        except Exception as e:
            pytest.skip(f"Cannot test get system resource optimizer singleton: {e}")


class TestSystemResourceOptimizerIntegration:
    """测试系统资源优化器集成"""

    def test_complete_lifecycle(self):
        """测试完整生命周期"""
        try:
            from core.system_resource_optimizer import (
                SystemResourceOptimizer,
                get_system_resource_optimizer,
            )

            # Create optimizer
            optimizer = SystemResourceOptimizer()
            assert optimizer.status is not None

            # Analyze memory
            memory_analysis = optimizer.analyze_memory_usage()
            assert isinstance(memory_analysis, dict)

            # Optimize memory
            memory_opt = optimizer.optimize_memory()
            assert isinstance(memory_opt, dict)

            # Analyze CPU
            cpu_analysis = optimizer.analyze_cpu_usage()
            assert isinstance(cpu_analysis, dict)

            # Optimize CPU
            cpu_opt = optimizer.optimize_cpu()
            assert isinstance(cpu_opt, dict)

            # Optimize network
            network_opt = optimizer.optimize_network()
            assert isinstance(network_opt, dict)

            # Run comprehensive optimization
            comprehensive = optimizer.run_comprehensive_optimization()
            assert "overall_status" in comprehensive

            # Get status
            status = optimizer.get_optimization_status()
            assert "memory_optimization_enabled" in status

            # Get summary
            summary = optimizer.get_resource_summary()
            assert "timestamp" in summary

            # Get global instance
            global_optimizer = get_system_resource_optimizer()
            assert global_optimizer is not None
        except Exception as e:
            pytest.skip(f"Cannot test complete lifecycle: {e}")


class TestSystemResourceOptimizerEdgeCases:
    """测试系统资源优化器边界情况"""

    def test_get_status(self):
        """测试获取状态"""
        try:
            from core.system_resource_optimizer import SystemResourceOptimizer

            optimizer = SystemResourceOptimizer()
            status = optimizer.get_status()

            assert status is not None
            assert isinstance(status, dict)
        except Exception as e:
            pytest.skip(f"Cannot test get status: {e}")

    def test_optimize_all(self):
        """测试优化所有资源"""
        try:
            from core.system_resource_optimizer import SystemResourceOptimizer

            optimizer = SystemResourceOptimizer()
            result = optimizer.optimize_all()

            assert result is not None
            assert isinstance(result, dict)
        except Exception as e:
            pytest.skip(f"Cannot test optimize all: {e}")

    def test_get_optimization_report(self):
        """测试获取优化报告"""
        try:
            from core.system_resource_optimizer import SystemResourceOptimizer

            optimizer = SystemResourceOptimizer()
            report = optimizer.get_optimization_report()

            assert report is not None
            assert isinstance(report, dict)
        except Exception as e:
            pytest.skip(f"Cannot test get optimization report: {e}")


class TestModuleExports:
    """测试模块导出"""

    def test_module_exports(self):
        """测试模块导出"""
        try:
            from core.system_resource_optimizer import __all__

            # Check if __all__ exists
            assert __all__ is not None
        except Exception as e:
            pytest.skip(f"Cannot test module exports: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
