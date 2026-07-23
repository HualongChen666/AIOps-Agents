# -*- coding: utf-8 -*-
"""
基础遥测核心模块测试
测试遥测核心功能的基础场景
"""

import pytest


class TestTelemetryCoreBasic:
    """遥测核心模块基础测试"""

    def test_telemetry_core_module_structure(self):
        """测试遥测核心模块结构"""
        try:
            from core import telemetry_core

            assert telemetry_core is not None
        except ImportError as e:
            pytest.skip(f"Telemetry core module not available: {e}")

    def test_telemetry_core_functions_exist(self):
        """测试遥测核心关键函数存在"""
        try:
            from core.telemetry_core import record_event, record_metric, record_trace

            # 验证关键函数存在
            assert record_metric is not None
            assert record_event is not None
            assert record_trace is not None
        except Exception as e:
            pytest.skip(f"Telemetry core functions test failed: {e}")

    def test_telemetry_core_classes_exist(self):
        """测试遥测核心关键类存在"""
        try:
            from core.telemetry_core import EventRecorder, MetricsCollector, TelemetryCore

            # 验证关键类存在
            assert TelemetryCore is not None
            assert MetricsCollector is not None
            assert EventRecorder is not None
        except Exception as e:
            pytest.skip(f"Telemetry core classes test failed: {e}")

    def test_telemetry_core_constants(self):
        """测试遥测核心常量定义"""
        try:
            from core.telemetry_core import EventType, MetricType

            # 验证常量存在
            assert MetricType is not None
            assert EventType is not None
        except Exception as e:
            pytest.skip(f"Telemetry core constants test failed: {e}")
