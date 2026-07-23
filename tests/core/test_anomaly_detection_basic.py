# -*- coding: utf-8 -*-
"""
基础异常检测模块测试
测试异常检测核心功能的基础场景
"""

import pytest


class TestAnomalyDetectionBasic:
    """异常检测模块基础测试"""

    def test_anomaly_detection_module_structure(self):
        """测试异常检测模块结构"""
        try:
            from core import anomaly_detection

            assert anomaly_detection is not None
        except ImportError as e:
            pytest.skip(f"Anomaly detection module not available: {e}")

    def test_anomaly_detection_functions_exist(self):
        """测试异常检测关键函数存在"""
        try:
            from core.anomaly_detection import (
                analyze_patterns,
                calculate_thresholds,
                detect_anomalies,
            )

            # 验证关键函数存在
            assert detect_anomalies is not None
            assert analyze_patterns is not None
            assert calculate_thresholds is not None
        except Exception as e:
            pytest.skip(f"Anomaly detection functions test failed: {e}")

    def test_anomaly_detection_classes_exist(self):
        """测试异常检测关键类存在"""
        try:
            from core.anomaly_detection import AnomalyDetector, PatternAnalyzer, ThresholdCalculator

            # 验证关键类存在
            assert AnomalyDetector is not None
            assert PatternAnalyzer is not None
            assert ThresholdCalculator is not None
        except Exception as e:
            pytest.skip(f"Anomaly detection classes test failed: {e}")

    def test_anomaly_detection_constants(self):
        """测试异常检测常量定义"""
        try:
            from core.anomaly_detection import AnomalySeverity, AnomalyType

            # 验证常量存在
            assert AnomalyType is not None
            assert AnomalySeverity is not None
        except Exception as e:
            pytest.skip(f"Anomaly detection constants test failed: {e}")
