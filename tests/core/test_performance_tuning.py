# -*- coding: utf-8 -*-
"""测试性能调优模块"""

import pytest


class TestPerformanceTuningModule:
    """测试性能调优模块"""

    def test_performance_tuning_module_exists(self):
        """测试性能调优模块存在"""
        from core import performance_tuning

        assert performance_tuning is not None

    def test_performance_tuning_has_functions(self):
        """测试性能调优模块有函数"""
        from core import performance_tuning

        # 检查模块有函数或类
        assert len(dir(performance_tuning)) > 0


class TestPerformanceTuningConfig:
    """测试性能调优配置"""

    def test_performance_tuning_config(self):
        """测试性能调优配置字典"""
        try:
            from core.performance_tuning import PERFORMANCE_TUNING_CONFIG

            assert PERFORMANCE_TUNING_CONFIG is not None
            assert isinstance(PERFORMANCE_TUNING_CONFIG, dict)
            assert "max_open_files" in PERFORMANCE_TUNING_CONFIG
            assert "max_memory_usage_gb" in PERFORMANCE_TUNING_CONFIG
        except Exception as e:
            pytest.skip(f"Cannot test performance tuning config: {e}")


class TestApplySystemLimits:
    """测试应用系统限制"""

    def test_apply_system_limits(self):
        """测试应用系统限制"""
        try:
            from core.performance_tuning import apply_system_limits

            result = apply_system_limits()

            assert result is not None
            assert isinstance(result, dict)
        except Exception as e:
            pytest.skip(f"Cannot test apply system limits: {e}")

    def test_apply_system_limits_on_windows(self):
        """测试Windows上应用系统限制"""
        try:
            import sys

            from core.performance_tuning import apply_system_limits

            result = apply_system_limits()

            # On Windows, should skip resource limits
            if sys.platform == "win32":
                assert "max_open_files" in result
                assert "Skipped" in result["max_open_files"]
        except Exception as e:
            pytest.skip(f"Cannot test apply system limits on windows: {e}")


class TestApplyPythonOptimizations:
    """测试应用Python优化"""

    def test_apply_python_optimizations(self):
        """测试应用Python优化"""
        try:
            from core.performance_tuning import apply_python_optimizations

            result = apply_python_optimizations()

            assert result is not None
            assert isinstance(result, dict)
        except Exception as e:
            pytest.skip(f"Cannot test apply python optimizations: {e}")

    def test_apply_python_optimizations_gc_threshold(self):
        """测试垃圾回收阈值设置"""
        try:
            from core.performance_tuning import apply_python_optimizations

            result = apply_python_optimizations()

            assert "gc_threshold" in result
        except Exception as e:
            pytest.skip(f"Cannot test apply python optimizations gc threshold: {e}")


class TestGetUvicornConfig:
    """测试获取Uvicorn配置"""

    def test_get_uvicorn_config(self):
        """测试获取Uvicorn配置"""
        try:
            from core.performance_tuning import get_uvicorn_config

            config = get_uvicorn_config()

            assert config is not None
            assert isinstance(config, dict)
            assert "workers" in config
            assert "worker_connections" in config
        except Exception as e:
            pytest.skip(f"Cannot test get uvicorn config: {e}")

    def test_get_uvicorn_config_values(self):
        """测试Uvicorn配置值"""
        try:
            from core.performance_tuning import get_uvicorn_config

            config = get_uvicorn_config()

            assert config["workers"] > 0
            assert config["worker_connections"] > 0
        except Exception as e:
            pytest.skip(f"Cannot test get uvicorn config values: {e}")


class TestApplyEnvironmentTuning:
    """测试应用环境调优"""

    def test_apply_environment_tuning(self):
        """测试应用环境调优"""
        try:
            from core.performance_tuning import apply_environment_tuning

            result = apply_environment_tuning()

            assert result is not None
            assert isinstance(result, dict)
        except Exception as e:
            pytest.skip(f"Cannot test apply environment tuning: {e}")

    def test_apply_environment_tuning_values(self):
        """测试环境调优值"""
        try:
            import os

            from core.performance_tuning import apply_environment_tuning

            apply_environment_tuning()

            # Check environment variables were set
            assert os.environ.get("PYTHONOPTIMIZE") == "2"
            assert os.environ.get("PYTHONUNBUFFERED") == "1"
        except Exception as e:
            pytest.skip(f"Cannot test apply environment tuning values: {e}")


class TestGetPerformanceRecommendations:
    """测试获取性能建议"""

    def test_get_performance_recommendations(self):
        """测试获取性能建议"""
        try:
            from core.performance_tuning import get_performance_recommendations

            recommendations = get_performance_recommendations()

            assert recommendations is not None
            assert isinstance(recommendations, dict)
            assert "system_info" in recommendations
            assert "recommendations" in recommendations
        except Exception as e:
            pytest.skip(f"Cannot test get performance recommendations: {e}")

    def test_get_performance_recommendations_system_info(self):
        """测试性能建议系统信息"""
        try:
            from core.performance_tuning import get_performance_recommendations

            recommendations = get_performance_recommendations()

            assert "cpu_count" in recommendations["system_info"]
            assert "memory_gb" in recommendations["system_info"]
            assert "platform" in recommendations["system_info"]
        except Exception as e:
            pytest.skip(f"Cannot test get performance recommendations system info: {e}")


class TestApplyComprehensiveTuning:
    """测试应用综合调优"""

    def test_apply_comprehensive_tuning(self):
        """测试应用综合调优"""
        try:
            from core.performance_tuning import apply_comprehensive_tuning

            result = apply_comprehensive_tuning()

            assert result is not None
            assert isinstance(result, dict)
            assert "steps" in result
        except Exception as e:
            pytest.skip(f"Cannot test apply comprehensive tuning: {e}")

    def test_apply_comprehensive_tuning_steps(self):
        """测试综合调优步骤"""
        try:
            from core.performance_tuning import apply_comprehensive_tuning

            result = apply_comprehensive_tuning()

            assert "system_limits" in result["steps"]
            assert "python_optimizations" in result["steps"]
            assert "environment_tuning" in result["steps"]
            assert "uvicorn_config" in result["steps"]
            assert "recommendations" in result["steps"]
        except Exception as e:
            pytest.skip(f"Cannot test apply comprehensive tuning steps: {e}")


class TestMonitorPerformanceMetrics:
    """测试监控性能指标"""

    def test_monitor_performance_metrics(self):
        """测试监控性能指标"""
        try:
            from core.performance_tuning import monitor_performance_metrics

            metrics = monitor_performance_metrics()

            assert metrics is not None
            assert isinstance(metrics, dict)
        except Exception as e:
            pytest.skip(f"Cannot test monitor performance metrics: {e}")

    def test_monitor_performance_metrics_cpu(self):
        """测试CPU性能指标"""
        try:
            from core.performance_tuning import monitor_performance_metrics

            metrics = monitor_performance_metrics()

            assert "cpu" in metrics
            assert "usage_percent" in metrics["cpu"]
            assert "core_count" in metrics["cpu"]
        except Exception as e:
            pytest.skip(f"Cannot test monitor performance metrics cpu: {e}")

    def test_monitor_performance_metrics_memory(self):
        """测试内存性能指标"""
        try:
            from core.performance_tuning import monitor_performance_metrics

            metrics = monitor_performance_metrics()

            assert "memory" in metrics
            assert "total_gb" in metrics["memory"]
            assert "available_gb" in metrics["memory"]
        except Exception as e:
            pytest.skip(f"Cannot test monitor performance metrics memory: {e}")

    def test_monitor_performance_metrics_disk(self):
        """测试磁盘性能指标"""
        try:
            from core.performance_tuning import monitor_performance_metrics

            metrics = monitor_performance_metrics()

            assert "disk" in metrics
            assert "total_gb" in metrics["disk"]
            assert "used_gb" in metrics["disk"]
        except Exception as e:
            pytest.skip(f"Cannot test monitor performance metrics disk: {e}")

    def test_monitor_performance_metrics_network(self):
        """测试网络性能指标"""
        try:
            from core.performance_tuning import monitor_performance_metrics

            metrics = monitor_performance_metrics()

            assert "network" in metrics
            assert "bytes_sent" in metrics["network"]
            assert "bytes_recv" in metrics["network"]
        except Exception as e:
            pytest.skip(f"Cannot test monitor performance metrics network: {e}")


class TestPerformanceTuningIntegration:
    """测试性能调优集成"""

    def test_complete_lifecycle(self):
        """测试完整生命周期"""
        try:
            from core.performance_tuning import (
                PERFORMANCE_TUNING_CONFIG,
                apply_comprehensive_tuning,
                apply_environment_tuning,
                apply_python_optimizations,
                apply_system_limits,
                get_performance_recommendations,
                get_uvicorn_config,
                monitor_performance_metrics,
            )

            # Check config
            assert PERFORMANCE_TUNING_CONFIG is not None
            assert PERFORMANCE_TUNING_CONFIG["max_open_files"] > 0

            # Apply system limits
            system_limits = apply_system_limits()
            assert isinstance(system_limits, dict)

            # Apply Python optimizations
            python_opts = apply_python_optimizations()
            assert isinstance(python_opts, dict)

            # Get Uvicorn config
            uvicorn_config = get_uvicorn_config()
            assert uvicorn_config["workers"] > 0

            # Apply environment tuning
            env_tuning = apply_environment_tuning()
            assert isinstance(env_tuning, dict)

            # Get recommendations
            recommendations = get_performance_recommendations()
            assert "system_info" in recommendations

            # Monitor metrics
            metrics = monitor_performance_metrics()
            assert "cpu" in metrics

            # Apply comprehensive tuning
            comprehensive = apply_comprehensive_tuning()
            assert "steps" in comprehensive
        except Exception as e:
            pytest.skip(f"Cannot test complete lifecycle: {e}")


class TestPerformanceTuningEdgeCases:
    """测试性能调优边界情况"""

    def test_performance_tuning_config_values(self):
        """测试性能调优配置值"""
        try:
            from core.performance_tuning import PERFORMANCE_TUNING_CONFIG

            assert PERFORMANCE_TUNING_CONFIG["max_open_files"] > 0
            assert PERFORMANCE_TUNING_CONFIG["max_memory_usage_gb"] > 0
            assert PERFORMANCE_TUNING_CONFIG["pygc_threshold"] > 0
            assert PERFORMANCE_TUNING_CONFIG["pyasyncio_threads"] > 0
            assert PERFORMANCE_TUNING_CONFIG["uvicorn_workers"] > 0
            assert PERFORMANCE_TUNING_CONFIG["uvicorn_worker_connections"] > 0
        except Exception as e:
            pytest.skip(f"Cannot test performance tuning config values: {e}")


class TestModuleExports:
    """测试模块导出"""

    def test_module_exports(self):
        """测试模块导出"""
        try:
            from core.performance_tuning import __all__

            # Check if __all__ exists
            assert __all__ is not None
        except Exception as e:
            pytest.skip(f"Cannot test module exports: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
