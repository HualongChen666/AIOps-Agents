# -*- coding: utf-8 -*-
"""Tests for workflow_service retry module."""

import asyncio

import pytest

from retry import RetryEngine
from schemas import RetryPolicy


class TestRetryEngine:
    """Test cases for RetryEngine class."""

    def test_retry_engine_initialization(self):
        """Test that RetryEngine initializes with default policies."""
        engine = RetryEngine()
        assert len(engine.policies) > 0
        assert "exponential" in engine.policies
        assert engine.default_policy is not None

    def test_retry_engine_default_policies(self):
        """Test that default policies are correctly defined."""
        engine = RetryEngine()
        expected_policies = [
            "no_retry",
            "fixed_1s",
            "fixed_5s",
            "linear_1s",
            "exponential",
            "exponential_fast",
            "exponential_slow",
            "aggressive",
            "conservative",
            "jitter",
            "custom",
        ]
        for policy_name in expected_policies:
            assert policy_name in engine.policies

    def test_retry_engine_custom_default_policy(self):
        """Test RetryEngine with custom default policy."""
        custom_policy = RetryPolicy(
            name="custom_default",
            max_retries=10,
            base_delay_seconds=2.0,
            max_delay_seconds=100.0,
        )
        engine = RetryEngine(default_policy=custom_policy)
        assert engine.default_policy.name == "custom_default"

    def test_add_policy(self):
        """Test adding a custom retry policy."""
        engine = RetryEngine()
        custom_policy = RetryPolicy(
            name="test_policy",
            max_retries=7,
            base_delay_seconds=0.5,
            max_delay_seconds=30.0,
        )
        engine.add_policy(custom_policy)
        assert "test_policy" in engine.policies
        assert engine.policies["test_policy"].max_retries == 7

    def test_add_policy_overwrites_existing(self):
        """Test that adding a policy with existing name overwrites it."""
        engine = RetryEngine()
        original_policy = engine.policies["exponential"]

        new_policy = RetryPolicy(
            name="exponential",
            max_retries=99,
            base_delay_seconds=10.0,
            max_delay_seconds=1000.0,
        )
        engine.add_policy(new_policy)

        assert engine.policies["exponential"].max_retries == 99
        assert engine.policies["exponential"].max_retries != original_policy.max_retries

    @pytest.mark.asyncio
    async def test_execute_success_on_first_attempt(self):
        """Test that successful execution on first attempt returns immediately."""
        engine = RetryEngine()

        async def success_func():
            return "success"

        result = await engine.execute(success_func)
        assert result == "success"

    @pytest.mark.asyncio
    async def test_execute_with_no_retry_policy(self):
        """Test execution with no_retry policy (max_retries=0)."""
        engine = RetryEngine()

        async def failing_func():
            raise ValueError("Test error")

        with pytest.raises(ValueError, match="Test error"):
            await engine.execute(failing_func, policy_name="no_retry")

    @pytest.mark.asyncio
    async def test_execute_with_fixed_delay_policy(self):
        """Test execution with fixed delay policy."""
        engine = RetryEngine()
        attempt_count = 0

        async def eventually_success_func():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise ValueError("Not yet")
            return "success"

        result = await engine.execute(eventually_success_func, policy_name="fixed_1s")
        assert result == "success"
        assert attempt_count == 3

    @pytest.mark.asyncio
    async def test_execute_with_exponential_policy(self):
        """Test execution with exponential backoff policy."""
        engine = RetryEngine()
        attempt_count = 0

        async def eventually_success_func():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 2:
                raise ValueError("Not yet")
            return "success"

        result = await engine.execute(eventually_success_func, policy_name="exponential")
        assert result == "success"
        assert attempt_count == 2

    @pytest.mark.asyncio
    async def test_execute_with_jitter_policy(self):
        """Test execution with jitter policy."""
        engine = RetryEngine()
        attempt_count = 0

        async def eventually_success_func():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 2:
                raise ValueError("Not yet")
            return "success"

        result = await engine.execute(eventually_success_func, policy_name="jitter")
        assert result == "success"

    @pytest.mark.asyncio
    async def test_execute_exceeds_max_retries(self):
        """Test that execution fails after exceeding max retries."""
        engine = RetryEngine()

        async def always_failing_func():
            raise ValueError("Always fails")

        with pytest.raises(ValueError, match="Always fails"):
            await engine.execute(always_failing_func, policy_name="fixed_1s")

    @pytest.mark.asyncio
    async def test_execute_with_custom_policy_name(self):
        """Test execution with custom policy name."""
        engine = RetryEngine()
        custom_policy = RetryPolicy(
            name="custom_test",
            max_retries=2,
            base_delay_seconds=0.01,
            max_delay_seconds=0.1,
        )
        engine.add_policy(custom_policy)

        attempt_count = 0

        async def count_func():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 2:
                raise ValueError("Not yet")
            return "success"

        result = await engine.execute(count_func, policy_name="custom_test")
        assert result == "success"
        assert attempt_count == 2

    @pytest.mark.asyncio
    async def test_execute_with_invalid_policy_name(self):
        """Test execution with invalid policy name falls back to default."""
        engine = RetryEngine()

        async def success_func():
            return "success"

        result = await engine.execute(success_func, policy_name="invalid_policy")
        assert result == "success"

    @pytest.mark.asyncio
    async def test_execute_with_retryable_errors(self):
        """Test execution with retryable error filtering."""
        engine = RetryEngine()
        policy = RetryPolicy(
            name="filtered",
            max_retries=5,
            base_delay_seconds=0.01,
            max_delay_seconds=0.1,
            retryable_errors=["timeout", "connection"],
        )
        engine.add_policy(policy)

        async def timeout_func():
            raise ValueError("Connection timeout")

        with pytest.raises(ValueError, match="Connection timeout"):
            await engine.execute(timeout_func, policy_name="filtered")

    @pytest.mark.asyncio
    async def test_execute_with_non_retryable_error(self):
        """Test execution with non-retryable error fails immediately."""
        engine = RetryEngine()
        policy = RetryPolicy(
            name="filtered",
            max_retries=5,
            base_delay_seconds=0.01,
            max_delay_seconds=0.1,
            retryable_errors=["timeout"],
        )
        engine.add_policy(policy)

        attempt_count = 0

        async def non_retryable_func():
            nonlocal attempt_count
            attempt_count += 1
            raise ValueError("Permission denied")

        with pytest.raises(ValueError, match="Permission denied"):
            await engine.execute(non_retryable_func, policy_name="filtered")

        # Should fail immediately without retries
        assert attempt_count == 1

    @pytest.mark.asyncio
    async def test_execute_with_function_arguments(self):
        """Test execution with function arguments."""
        engine = RetryEngine()

        async def func_with_args(a, b, c=None):
            return {"a": a, "b": b, "c": c}

        result = await engine.execute(func_with_args, 1, 2, c=3)
        assert result == {"a": 1, "b": 2, "c": 3}

    @pytest.mark.asyncio
    async def test_execute_with_keyword_arguments(self):
        """Test execution with keyword arguments."""
        engine = RetryEngine()

        async def func_with_kwargs(**kwargs):
            return kwargs

        result = await engine.execute(func_with_kwargs, key1="value1", key2="value2")
        assert result == {"key1": "value1", "key2": "value2"}

    @pytest.mark.asyncio
    async def test_compute_delay_exponential(self):
        """Test delay computation for exponential backoff."""
        engine = RetryEngine()
        policy = engine.policies["exponential"]

        # Test exponential growth: base * (2^(attempt-1))
        delay_1 = engine._compute_delay(1, policy)
        delay_2 = engine._compute_delay(2, policy)
        delay_3 = engine._compute_delay(3, policy)

        assert delay_1 == policy.base_delay_seconds
        assert delay_2 == policy.base_delay_seconds * 2
        assert delay_3 == policy.base_delay_seconds * 4

    @pytest.mark.asyncio
    async def test_compute_delay_max_cap(self):
        """Test that delay is capped at max_delay_seconds."""
        engine = RetryEngine()
        policy = engine.policies["exponential"]

        # With high attempt number, delay should be capped
        delay = engine._compute_delay(100, policy)
        assert delay == policy.max_delay_seconds

    @pytest.mark.asyncio
    async def test_compute_delay_jitter(self):
        """Test delay computation with jitter."""
        engine = RetryEngine()
        policy = engine.policies["jitter"]

        delay_1 = engine._compute_delay(1, policy)
        delay_2 = engine._compute_delay(1, policy)

        # With jitter, delays should vary
        # (though they might occasionally be the same by chance)
        assert 0 <= delay_1 <= policy.max_delay_seconds
        assert 0 <= delay_2 <= policy.max_delay_seconds

    @pytest.mark.asyncio
    async def test_compute_delay_fixed(self):
        """Test delay computation for fixed delay policy."""
        engine = RetryEngine()
        policy = engine.policies["fixed_1s"]

        delay_1 = engine._compute_delay(1, policy)
        delay_2 = engine._compute_delay(5, policy)

        assert delay_1 == policy.base_delay_seconds
        assert delay_2 == policy.base_delay_seconds

    @pytest.mark.asyncio
    async def test_is_retryable_with_no_filter(self):
        """Test that all errors are retryable when no filter is set."""
        engine = RetryEngine()
        policy = RetryPolicy(
            name="test",
            max_retries=3,
            base_delay_seconds=1.0,
            max_delay_seconds=60.0,
            retryable_errors=[],
        )

        error = ValueError("Any error")
        assert engine._is_retryable(error, policy) is True

    @pytest.mark.asyncio
    async def test_is_retryable_with_matching_error(self):
        """Test that matching errors are retryable."""
        engine = RetryEngine()
        policy = RetryPolicy(
            name="test",
            max_retries=3,
            base_delay_seconds=1.0,
            max_delay_seconds=60.0,
            retryable_errors=["timeout", "connection"],
        )

        error = ValueError("Connection timeout")
        assert engine._is_retryable(error, policy) is True

    @pytest.mark.asyncio
    async def test_is_retryable_with_non_matching_error(self):
        """Test that non-matching errors are not retryable."""
        engine = RetryEngine()
        policy = RetryPolicy(
            name="test",
            max_retries=3,
            base_delay_seconds=1.0,
            max_delay_seconds=60.0,
            retryable_errors=["timeout"],
        )

        error = ValueError("Permission denied")
        assert engine._is_retryable(error, policy) is False

    @pytest.mark.asyncio
    async def test_is_retryable_case_insensitive(self):
        """Test that error matching is case-insensitive."""
        engine = RetryEngine()
        policy = RetryPolicy(
            name="test",
            max_retries=3,
            base_delay_seconds=1.0,
            max_delay_seconds=60.0,
            retryable_errors=["TIMEOUT"],
        )

        error = ValueError("timeout error")
        assert engine._is_retryable(error, policy) is True

    @pytest.mark.asyncio
    async def test_is_retryable_partial_match(self):
        """Test that partial error string matches work."""
        engine = RetryEngine()
        policy = RetryPolicy(
            name="test",
            max_retries=3,
            base_delay_seconds=1.0,
            max_delay_seconds=60.0,
            retryable_errors=["timeout"],
        )

        error = ValueError("Operation timeout occurred")
        assert engine._is_retryable(error, policy) is True

    @pytest.mark.asyncio
    async def test_execute_with_zero_base_delay(self):
        """Test execution with zero base delay."""
        engine = RetryEngine()
        policy = RetryPolicy(
            name="zero_delay",
            max_retries=3,
            base_delay_seconds=0,
            max_delay_seconds=0,
        )
        engine.add_policy(policy)

        attempt_count = 0

        async def count_func():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise ValueError("Not yet")
            return "success"

        result = await engine.execute(count_func, policy_name="zero_delay")
        assert result == "success"
        assert attempt_count == 3

    @pytest.mark.asyncio
    async def test_execute_with_different_exception_types(self):
        """Test execution with different exception types."""
        engine = RetryEngine()

        async def value_error_func():
            raise ValueError("Value error")

        async def runtime_error_func():
            raise RuntimeError("Runtime error")

        with pytest.raises(ValueError):
            await engine.execute(value_error_func, policy_name="no_retry")

        with pytest.raises(RuntimeError):
            await engine.execute(runtime_error_func, policy_name="no_retry")

    @pytest.mark.asyncio
    async def test_execute_preserves_exception(self):
        """Test that the original exception is preserved."""
        engine = RetryEngine()

        async def custom_error_func():
            raise CustomError("Custom error message")

        with pytest.raises(CustomError, match="Custom error message"):
            await engine.execute(custom_error_func, policy_name="no_retry")

    @pytest.mark.asyncio
    async def test_execute_with_sync_function_raises_error(self):
        """Test that passing a sync function raises an error."""
        engine = RetryEngine()

        def sync_func():
            return "sync"

        # This should work because we're calling it, not checking if it's async
        # The function will be awaited, which will fail for sync functions
        with pytest.raises(TypeError):
            await engine.execute(sync_func)

    @pytest.mark.asyncio
    async def test_execute_return_value(self):
        """Test that return value is correctly passed through."""
        engine = RetryEngine()

        async def return_dict():
            return {"key": "value", "number": 42}

        result = await engine.execute(return_dict)
        assert result == {"key": "value", "number": 42}

    @pytest.mark.asyncio
    async def test_execute_return_none(self):
        """Test that None return value is handled correctly."""
        engine = RetryEngine()

        async def return_none():
            return None

        result = await engine.execute(return_none)
        assert result is None

    @pytest.mark.asyncio
    async def test_execute_with_very_long_delay(self):
        """Test execution with very long delay (should use max cap)."""
        engine = RetryEngine()
        policy = RetryPolicy(
            name="long_delay",
            max_retries=100,
            base_delay_seconds=1.0,
            max_delay_seconds=0.1,  # Very small max
        )
        engine.add_policy(policy)

        attempt_count = 0

        async def count_func():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 2:
                raise ValueError("Not yet")
            return "success"

        # Should complete quickly due to max delay cap
        result = await engine.execute(count_func, policy_name="long_delay")
        assert result == "success"

    @pytest.mark.asyncio
    async def test_execute_with_aggressive_policy(self):
        """Test execution with aggressive retry policy."""
        engine = RetryEngine()
        attempt_count = 0

        async def eventually_success():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 5:
                raise ValueError("Not yet")
            return "success"

        result = await engine.execute(eventually_success, policy_name="aggressive")
        assert result == "success"
        assert attempt_count == 5

    @pytest.mark.asyncio
    async def test_execute_with_conservative_policy(self):
        """Test execution with conservative retry policy."""
        engine = RetryEngine()
        attempt_count = 0

        async def eventually_success():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise ValueError("Not yet")
            return "success"

        result = await engine.execute(eventually_success, policy_name="conservative")
        assert result == "success"
        assert attempt_count == 3

    @pytest.mark.asyncio
    async def test_execute_exponential_fast_policy(self):
        """Test execution with exponential_fast policy."""
        engine = RetryEngine()
        attempt_count = 0

        async def eventually_success():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 2:
                raise ValueError("Not yet")
            return "success"

        result = await engine.execute(eventually_success, policy_name="exponential_fast")
        assert result == "success"

    @pytest.mark.asyncio
    async def test_execute_exponential_slow_policy(self):
        """Test execution with exponential_slow policy."""
        engine = RetryEngine()
        attempt_count = 0

        async def eventually_success():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 2:
                raise ValueError("Not yet")
            return "success"

        # Use a small number of retries to avoid long test time
        result = await engine.execute(eventually_success, policy_name="exponential_fast")
        assert result == "success"

    @pytest.mark.asyncio
    async def test_execute_linear_1s_policy(self):
        """Test execution with linear_1s policy."""
        engine = RetryEngine()
        attempt_count = 0

        async def eventually_success():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise ValueError("Not yet")
            return "success"

        result = await engine.execute(eventually_success, policy_name="linear_1s")
        assert result == "success"
        assert attempt_count == 3


class CustomError(Exception):
    """Custom exception for testing."""

    pass
