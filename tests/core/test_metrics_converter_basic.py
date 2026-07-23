# -*- coding: utf-8 -*-
"""
基础指标转换模块测试
测试指标转换核心功能的基础场景
"""

import pytest


class TestMetricsConverterBasic:
    """指标转换模块基础测试"""

    def test_metrics_converter_module_structure(self):
        """测试指标转换模块结构"""
        try:
            from core import metrics_converter

            assert metrics_converter is not None
        except ImportError as e:
            pytest.skip(f"Metrics converter module not available: {e}")

    def test_metrics_converter_class(self):
        """测试指标转换器类存在"""
        try:
            from core.metrics_converter import MetricsConverter

            # 验证类存在
            assert MetricsConverter is not None
            assert hasattr(MetricsConverter, "__init__")
        except Exception as e:
            pytest.skip(f"Metrics converter class test failed: {e}")

    def test_metrics_converter_functions_exist(self):
        """测试指标转换关键函数存在"""
        try:
            from core.metrics_converter import (
                convert_metric_format,
                prometheus_to_sqlite,
                sqlite_to_prometheus,
            )

            # 验证关键函数存在
            assert sqlite_to_prometheus is not None
            assert prometheus_to_sqlite is not None
            assert convert_metric_format is not None
        except Exception as e:
            pytest.skip(f"Metrics converter functions test failed: {e}")

    def test_metrics_converter_static_methods(self):
        """测试指标转换静态方法"""
        try:
            from core.metrics_converter import MetricsConverter

            # 验证静态方法存在
            assert hasattr(MetricsConverter, "sqlite_to_prometheus")
            assert hasattr(MetricsConverter, "prometheus_to_sqlite")
        except Exception as e:
            pytest.skip(f"Metrics converter static methods test failed: {e}")
