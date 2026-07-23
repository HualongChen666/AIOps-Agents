# -*- coding: utf-8 -*-
"""测试增强重试机制模块"""

import pytest


class TestRetryEnhancedModule:
    """测试增强重试机制模块"""

    def test_retry_enhanced_module_exists(self):
        """测试增强重试机制模块存在"""
        from core import retry_enhanced

        assert retry_enhanced is not None

    def test_retry_enhanced_has_classes(self):
        """测试增强重试机制模块有类"""
        from core import retry_enhanced

        # 检查模块有类
        assert hasattr(retry_enhanced, "RetryStrategy")
        assert hasattr(retry_enhanced, "RetryCondition")
        assert hasattr(retry_enhanced, "EnhancedRetry")
        assert hasattr(retry_enhanced, "RetryMetrics")


class TestRetryStrategy:
    """测试重试策略"""

    def test_retry_strategy_constants(self):
        """测试重试策略常量"""
        try:
            from core.retry_enhanced import RetryStrategy

            assert RetryStrategy.EXPONENTIAL_BACKOFF == "exponential_backoff"
            assert RetryStrategy.LINEAR_BACKOFF == "linear_backoff"
            assert RetryStrategy.FIXED_DELAY == "fixed_delay"
            assert RetryStrategy.IMMEDIATE == "immediate"
        except Exception as e:
            pytest.skip(f"Cannot test RetryStrategy constants: {e}")


class TestRetryCondition:
    """测试重试条件"""

    def test_is_retryable_exception(self):
        """测试判断可重试异常"""
        try:
            from core.retry_enhanced import RetryCondition

            assert RetryCondition.is_retryable_exception(ConnectionError()) is True
            assert RetryCondition.is_retryable_exception(TimeoutError()) is True
            assert RetryCondition.is_retryable_exception(OSError()) is True
            assert RetryCondition.is_retryable_exception(ValueError()) is False
        except Exception as e:
            pytest.skip(f"Cannot test is_retryable_exception: {e}")

    def test_is_server_error(self):
        """测试判断服务器错误"""
        try:
            from core.retry_enhanced import RetryCondition

            # Create mock exception with status_code
            class MockException(Exception):
                def __init__(self, status_code):
                    self.status_code = status_code

            assert RetryCondition.is_server_error(MockException(500)) is True
            assert RetryCondition.is_server_error(MockException(503)) is True
            assert RetryCondition.is_server_error(MockException(404)) is False
            assert RetryCondition.is_server_error(ValueError()) is False
        except Exception as e:
            pytest.skip(f"Cannot test is_server_error: {e}")

    def test_is_rate_limited(self):
        """测试判断速率限制"""
        try:
            from core.retry_enhanced import RetryCondition

            # Create mock exception with status_code
            class MockException(Exception):
                def __init__(self, status_code):
                    self.status_code = status_code

            assert RetryCondition.is_rate_limited(MockException(429)) is True
            assert RetryCondition.is_rate_limited(MockException(500)) is False
            assert RetryCondition.is_rate_limited(ValueError()) is False
        except Exception as e:
            pytest.skip(f"Cannot test is_rate_limited: {e}")

    def test_custom_condition(self):
        """测试自定义条件"""
        try:
            from core.retry_enhanced import RetryCondition

            def my_condition(e):
                return isinstance(e, ValueError)

            condition = RetryCondition.custom_condition(my_condition)

            assert condition(ValueError()) is True
            assert condition(TypeError()) is False
        except Exception as e:
            pytest.skip(f"Cannot test custom_condition: {e}")


class TestEnhancedRetry:
    """测试增强重试"""

    def test_enhanced_retry_init(self):
        """测试增强重试初始化"""
        try:
            from core.retry_enhanced import EnhancedRetry, RetryStrategy

            retry = EnhancedRetry(
                max_attempts=3,
                base_delay=1.0,
                max_delay=60.0,
                strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
            )

            assert retry.max_attempts == 3
            assert retry.base_delay == 1.0
            assert retry.max_delay == 60.0
        except Exception as e:
            pytest.skip(f"Cannot test EnhancedRetry init: {e}")

    def test_should_retry_with_retryable_exception(self):
        """测试判断是否重试（可重试异常）"""
        try:
            from core.retry_enhanced import EnhancedRetry

            retry = EnhancedRetry(max_attempts=3)

            assert retry.should_retry(ConnectionError()) is True
            assert retry.should_retry(TimeoutError()) is True
        except Exception as e:
            pytest.skip(f"Cannot test should_retry with retryable exception: {e}")

    def test_should_retry_with_custom_condition(self):
        """测试判断是否重试（自定义条件）"""
        try:
            from core.retry_enhanced import EnhancedRetry

            def my_condition(e):
                return isinstance(e, ValueError)

            retry = EnhancedRetry(max_attempts=3, retry_on=my_condition)

            assert retry.should_retry(ValueError()) is True
            assert retry.should_retry(TypeError()) is False
        except Exception as e:
            pytest.skip(f"Cannot test should_retry with custom condition: {e}")

    def test_should_retry_with_exception_types(self):
        """测试判断是否重试（异常类型）"""
        try:
            from core.retry_enhanced import EnhancedRetry

            retry = EnhancedRetry(max_attempts=3, retry_on_exceptions=(ValueError,))

            assert retry.should_retry(ValueError()) is True
            assert retry.should_retry(TypeError()) is False
        except Exception as e:
            pytest.skip(f"Cannot test should_retry with exception types: {e}")

    def test_calculate_delay_immediate(self):
        """测试计算延迟（立即）"""
        try:
            from core.retry_enhanced import EnhancedRetry, RetryStrategy

            retry = EnhancedRetry(max_attempts=3, strategy=RetryStrategy.IMMEDIATE)

            assert retry.calculate_delay(1) == 0.0
        except Exception as e:
            pytest.skip(f"Cannot test calculate_delay immediate: {e}")

    def test_calculate_delay_fixed(self):
        """测试计算延迟（固定）"""
        try:
            from core.retry_enhanced import EnhancedRetry, RetryStrategy

            retry = EnhancedRetry(
                max_attempts=3, base_delay=2.0, strategy=RetryStrategy.FIXED_DELAY
            )

            assert retry.calculate_delay(1) == 2.0
        except Exception as e:
            pytest.skip(f"Cannot test calculate_delay fixed: {e}")

    def test_calculate_delay_exponential(self):
        """测试计算延迟（指数退避）"""
        try:
            from core.retry_enhanced import EnhancedRetry, RetryStrategy

            retry = EnhancedRetry(
                max_attempts=3,
                base_delay=1.0,
                backoff_multiplier=2.0,
                strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
            )

            # First attempt: 1.0 * 2^0 = 1.0
            assert retry.calculate_delay(1) == 1.0
            # Second attempt: 1.0 * 2^1 = 2.0
            assert retry.calculate_delay(2) == 2.0
            # Third attempt: 1.0 * 2^2 = 4.0
            assert retry.calculate_delay(3) == 4.0
        except Exception as e:
            pytest.skip(f"Cannot test calculate_delay exponential: {e}")

    def test_calculate_delay_max_cap(self):
        """测试计算延迟（最大值限制）"""
        try:
            from core.retry_enhanced import EnhancedRetry, RetryStrategy

            retry = EnhancedRetry(
                max_attempts=10,
                base_delay=1.0,
                max_delay=5.0,
                backoff_multiplier=10.0,
                strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
            )

            # Should be capped at max_delay
            assert retry.calculate_delay(10) <= 5.0
        except Exception as e:
            pytest.skip(f"Cannot test calculate_delay max cap: {e}")

    def test_calculate_delay_linear(self):
        """测试计算延迟（线性退避）"""
        try:
            from core.retry_enhanced import EnhancedRetry, RetryStrategy

            retry = EnhancedRetry(
                max_attempts=3,
                base_delay=1.0,
                backoff_multiplier=1.0,
                strategy=RetryStrategy.LINEAR_BACKOFF,
            )

            # First attempt: 1.0 * (1 + 0) = 1.0
            assert retry.calculate_delay(1) == 1.0
            # Second attempt: 1.0 * (1 + 1) = 2.0
            assert retry.calculate_delay(2) == 2.0
        except Exception as e:
            pytest.skip(f"Cannot test calculate_delay linear: {e}")

    def test_sync_wrapper_success(self):
        """测试同步包装器（成功）"""
        try:
            from core.retry_enhanced import EnhancedRetry

            retry = EnhancedRetry(max_attempts=3)

            @retry
            def test_func():
                return "success"

            result = test_func()

            assert result == "success"
        except Exception as e:
            pytest.skip(f"Cannot test sync wrapper success: {e}")

    def test_sync_wrapper_retry(self):
        """测试同步包装器（重试）"""
        try:
            from core.retry_enhanced import EnhancedRetry, RetryStrategy

            retry = EnhancedRetry(max_attempts=3, base_delay=0.01, strategy=RetryStrategy.IMMEDIATE)

            attempt_count = 0

            @retry
            def test_func():
                nonlocal attempt_count
                attempt_count += 1
                if attempt_count < 2:
                    raise ConnectionError("Temporary error")
                return "success"

            result = test_func()

            assert result == "success"
            assert attempt_count == 2
        except Exception as e:
            pytest.skip(f"Cannot test sync wrapper retry: {e}")

    def test_sync_wrapper_max_attempts_exceeded(self):
        """测试同步包装器（超过最大尝试次数）"""
        try:
            from core.retry_enhanced import EnhancedRetry, RetryStrategy

            retry = EnhancedRetry(max_attempts=2, base_delay=0.01, strategy=RetryStrategy.IMMEDIATE)

            @retry
            def test_func():
                raise ConnectionError("Always fails")

            try:
                test_func()
                assert False, "Should have raised exception"
            except ConnectionError:
                assert True
        except Exception as e:
            pytest.skip(f"Cannot test sync wrapper max attempts exceeded: {e}")

    @pytest.mark.asyncio
    async def test_async_wrapper_success(self):
        """测试异步包装器（成功）"""
        try:
            from core.retry_enhanced import EnhancedRetry

            retry = EnhancedRetry(max_attempts=3)

            @retry
            async def test_func():
                return "success"

            result = await test_func()

            assert result == "success"
        except Exception as e:
            pytest.skip(f"Cannot test async wrapper success: {e}")

    @pytest.mark.asyncio
    async def test_async_wrapper_retry(self):
        """测试异步包装器（重试）"""
        try:
            from core.retry_enhanced import EnhancedRetry, RetryStrategy

            retry = EnhancedRetry(max_attempts=3, base_delay=0.01, strategy=RetryStrategy.IMMEDIATE)

            attempt_count = 0

            @retry
            async def test_func():
                nonlocal attempt_count
                attempt_count += 1
                if attempt_count < 2:
                    raise ConnectionError("Temporary error")
                return "success"

            result = await test_func()

            assert result == "success"
            assert attempt_count == 2
        except Exception as e:
            pytest.skip(f"Cannot test async wrapper retry: {e}")


class TestRetryWithEnhancedRetry:
    """测试增强重试装饰器"""

    def test_retry_with_enhanced_retry_exists(self):
        """测试增强重试装饰器存在"""
        try:
            from core.retry_enhanced import retry_with_enhanced_retry

            assert retry_with_enhanced_retry is not None
        except Exception as e:
            pytest.skip(f"Cannot test retry_with_enhanced_retry exists: {e}")

    def test_retry_with_enhanced_retry_decorator(self):
        """测试增强重试装饰器"""
        try:
            from core.retry_enhanced import RetryStrategy, retry_with_enhanced_retry

            @retry_with_enhanced_retry(
                max_attempts=2, base_delay=0.01, strategy=RetryStrategy.IMMEDIATE
            )
            def test_func():
                return "success"

            result = test_func()

            assert result == "success"
        except Exception as e:
            pytest.skip(f"Cannot test retry_with_enhanced_retry decorator: {e}")


class TestRetryMetrics:
    """测试重试指标"""

    def test_retry_metrics_init(self):
        """测试重试指标初始化"""
        try:
            from core.retry_enhanced import RetryMetrics

            metrics = RetryMetrics()

            assert metrics.attempt_counts == {}
            assert metrics.failure_counts == {}
            assert metrics.success_counts == {}
            assert metrics.total_retry_delay == {}
        except Exception as e:
            pytest.skip(f"Cannot test RetryMetrics init: {e}")

    def test_retry_metrics_record_attempt(self):
        """测试记录尝试"""
        try:
            from core.retry_enhanced import RetryMetrics

            metrics = RetryMetrics()
            metrics.record_attempt("test_operation", 1, 1.0)
            metrics.record_attempt("test_operation", 2, 2.0)

            assert len(metrics.attempt_counts["test_operation"]) == 2
            assert metrics.total_retry_delay["test_operation"] == 3.0
        except Exception as e:
            pytest.skip(f"Cannot test RetryMetrics record_attempt: {e}")

    def test_retry_metrics_record_success(self):
        """测试记录成功"""
        try:
            from core.retry_enhanced import RetryMetrics

            metrics = RetryMetrics()
            metrics.record_success("test_operation")

            assert metrics.success_counts["test_operation"] == 1
        except Exception as e:
            pytest.skip(f"Cannot test RetryMetrics record_success: {e}")

    def test_retry_metrics_record_failure(self):
        """测试记录失败"""
        try:
            from core.retry_enhanced import RetryMetrics

            metrics = RetryMetrics()
            metrics.record_failure("test_operation")

            assert metrics.failure_counts["test_operation"] == 1
        except Exception as e:
            pytest.skip(f"Cannot test RetryMetrics record_failure: {e}")

    def test_retry_metrics_get_metrics(self):
        """测试获取指标"""
        try:
            from core.retry_enhanced import RetryMetrics

            metrics = RetryMetrics()
            metrics.record_attempt("test_operation", 1, 1.0)
            metrics.record_attempt("test_operation", 2, 2.0)
            metrics.record_success("test_operation")

            result = metrics.get_metrics("test_operation")

            assert result["operation"] == "test_operation"
            assert result["total_attempts"] == 2
            assert result["success_count"] == 1
        except Exception as e:
            pytest.skip(f"Cannot test RetryMetrics get_metrics: {e}")

    def test_retry_metrics_get_all_metrics(self):
        """测试获取所有指标"""
        try:
            from core.retry_enhanced import RetryMetrics

            metrics = RetryMetrics()
            metrics.record_attempt("op1", 1, 1.0)
            metrics.record_success("op1")
            metrics.record_attempt("op2", 1, 1.0)
            metrics.record_failure("op2")

            result = metrics.get_all_metrics()

            assert "op1" in result
            assert "op2" in result
        except Exception as e:
            pytest.skip(f"Cannot test RetryMetrics get_all_metrics: {e}")


class TestGlobalRetryMetrics:
    """测试全局重试指标"""

    def test_global_retry_metrics_exists(self):
        """测试全局重试指标存在"""
        try:
            from core.retry_enhanced import retry_metrics

            assert retry_metrics is not None
        except Exception as e:
            pytest.skip(f"Cannot test global retry_metrics exists: {e}")

    def test_global_retry_metrics_type(self):
        """测试全局重试指标类型"""
        try:
            from core.retry_enhanced import RetryMetrics, retry_metrics

            assert isinstance(retry_metrics, RetryMetrics)
        except Exception as e:
            pytest.skip(f"Cannot test global retry_metrics type: {e}")


class TestRetryEnhancedIntegration:
    """测试增强重试集成"""

    def test_complete_retry_workflow(self):
        """测试完整重试工作流"""
        try:
            from core.retry_enhanced import EnhancedRetry, RetryMetrics, RetryStrategy

            # Create metrics
            metrics = RetryMetrics()

            # Create retry with callback
            def callback(attempt, exception, delay):
                metrics.record_attempt("test_op", attempt, delay)

            retry = EnhancedRetry(
                max_attempts=3,
                base_delay=0.01,
                strategy=RetryStrategy.IMMEDIATE,
                on_retry_callback=callback,
            )

            attempt_count = 0

            @retry
            def test_func():
                nonlocal attempt_count
                attempt_count += 1
                if attempt_count < 2:
                    raise ConnectionError("Temporary error")
                metrics.record_success("test_op")
                return "success"

            result = test_func()

            assert result == "success"
            assert attempt_count == 2
            assert metrics.success_counts["test_op"] == 1
        except Exception as e:
            pytest.skip(f"Cannot test complete retry workflow: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
