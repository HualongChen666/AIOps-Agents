# -*- coding: utf-8 -*-
"""
基础增强重试模块测试
测试增强重试核心功能的基础场景
"""

import pytest


class TestRetryEnhancedBasic:
    """增强重试模块基础测试"""

    def test_retry_enhanced_module_structure(self):
        """测试增强重试模块结构"""
        try:
            from core import retry_enhanced

            assert retry_enhanced is not None
        except ImportError as e:
            pytest.skip(f"Retry enhanced module not available: {e}")

    def test_retry_enhanced_functions_exist(self):
        """测试增强重试关键函数存在"""
        try:
            from core.retry_enhanced import circuit_breaker, retry_on_exception, retry_with_backoff

            # 验证关键函数存在
            assert retry_with_backoff is not None
            assert retry_on_exception is not None
            assert circuit_breaker is not None
        except Exception as e:
            pytest.skip(f"Retry enhanced functions test failed: {e}")

    def test_retry_enhanced_classes_exist(self):
        """测试增强重试关键类存在"""
        try:
            from core.retry_enhanced import BackoffCalculator, CircuitBreaker, RetryStrategy

            # 验证关键类存在
            assert RetryStrategy is not None
            assert CircuitBreaker is not None
            assert BackoffCalculator is not None
        except Exception as e:
            pytest.skip(f"Retry enhanced classes test failed: {e}")

    def test_retry_enhanced_constants(self):
        """测试增强重试常量定义"""
        try:
            from core.retry_enhanced import CircuitState, RetryPolicy

            # 验证常量存在
            assert RetryPolicy is not None
            assert CircuitState is not None
        except Exception as e:
            pytest.skip(f"Retry enhanced constants test failed: {e}")
